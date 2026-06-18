"""Generate the final comparative Markdown report from JSON artifacts."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
REPORT = ROOT / "reports" / "report.md"


def load_json(path: Path):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def table_from_blas(report) -> str:
    if not report:
        return "Relatório ainda não gerado.\n"
    rows = ["| Operação | Tempo (s) | Dimensão | Memória RSS (bytes) |", "|---|---:|---|---:|"]
    for item in report.get("results", []):
        shape = item.get("result_shape", item.get("result_shape", ""))
        rows.append(f"| {item.get('operation')} | {item.get('time_seconds', 0):.6f} | {shape} | {item.get('memory_rss_bytes', 0)} |")
    return "\n".join(rows) + "\n"


def saturation_summary(report) -> str:
    if not report:
        return "Relatório ainda não gerado.\n"
    rows = ["| Concorrência | Tempo médio (s) | Tempo máx. (s) | Throughput (req/s) | Erros |", "|---:|---:|---:|---:|---:|"]
    for item in report.get("levels", []):
        rows.append(
            f"| {item.get('concurrency')} | {item.get('average_time_seconds', 0):.6f} | "
            f"{item.get('max_time_seconds', 0):.6f} | {item.get('throughput_requests_per_second', 0):.6f} | {item.get('errors', 0)} |"
        )
    return "\n".join(rows) + "\n"


def client_summary(report) -> str:
    if not report:
        return "Relatório comparativo do cliente ainda não gerado.\n"
    rows = ["| Serviço | Algoritmo | Status | Iterações | Tempo total (s) | Latência cliente (s) |", "|---|---|---|---:|---:|---:|"]
    for item in report.get("results", []):
        response = item.get("response", {})
        rows.append(
            f"| {item.get('target')} | {response.get('algorithm', '-')} | {response.get('status')} | "
            f"{response.get('iterations', '-')} | {response.get('total_time_seconds', 0) or 0:.6f} | "
            f"{response.get('client_latency_seconds', 0) or 0:.6f} |"
        )
    return "\n".join(rows) + "\n"


def real_reconstruction_summary(report) -> str:
    if not report:
        return "Reconstrução real 60x60 ainda não executada.\n"
    return (
        "| Métrica | Valor |\n"
        "|---|---:|\n"
        f"| Formato | {report.get('shape')} |\n"
        f"| Diferença máxima absoluta Python vs C++ | {report.get('max_abs_diff', 0):.12e} |\n"
        f"| Diferença média absoluta Python vs C++ | {report.get('mean_abs_diff', 0):.12e} |\n"
        f"| Mínimo Python | {report.get('python_min', 0):.6f} |\n"
        f"| Máximo Python | {report.get('python_max', 0):.6f} |\n"
        f"| Mínimo C++ | {report.get('cpp_min', 0):.6f} |\n"
        f"| Máximo C++ | {report.get('cpp_max', 0):.6f} |\n"
    )


def main() -> None:
    python_blas = load_json(RESULTS / "python_blas_report.json")
    cpp_blas = load_json(RESULTS / "cpp_blas_report.json")
    client = load_json(RESULTS / "client_comparison.json")
    python_sat = load_json(RESULTS / "python_saturation.json")
    cpp_sat = load_json(RESULTS / "cpp_saturation.json")
    real_reconstruction = load_json(RESULTS / "real_reconstruction_comparison_summary.json")

    markdown = f"""# Relatório Comparativo

Gerado em {datetime.now(timezone.utc).isoformat()}.

## Linguagens Utilizadas

- Python 3.12+: linguagem interpretada e não fortemente tipada.
- C++17: linguagem compilada e fortemente tipada.

## Bibliotecas BLAS Utilizadas

- Python: NumPy ligado ao backend BLAS disponível no ambiente, preferencialmente OpenBLAS.
- C++: CBLAS/OpenBLAS via CMake.

## Dimensões dos Dados

| Conjunto | H | g | Imagem |
|---|---:|---:|---:|
| 30x30 | 27904 x 900 | 27904 x 1 | 30 x 30 |
| 60x60 | 50816 x 3600 | 50816 x 1 | 60 x 60 |

Observação: no momento inicial, os arquivos 60x60 estavam disponíveis. Os arquivos 30x30 foram suportados pelo código, mas não estavam no diretório de Downloads.

## Resultados dos Testes BLAS - Python

{table_from_blas(python_blas)}

## Resultados dos Testes BLAS - C++

{table_from_blas(cpp_blas)}

## Resultados CGNR/CGNE e Comparação Python vs C++

{client_summary(client)}

## Reconstrução Real 60x60

Executada com `data/H-1.csv`, `data/G-1.csv`, `algorithm=cgnr` e `apply_gain=true`.

{real_reconstruction_summary(real_reconstruction)}

Imagem comparativa gerada em `results/real_reconstruction_comparison.png`.

As reconstruções usam orientação column-major para compatibilidade com a visualização típica em MATLAB/Octave. Cada execução salva uma imagem pura (`png_raw`) e uma imagem de visualização (`png_visualization`) com escala logarítmica e eixos.

## Testes de Saturação - Python

{saturation_summary(python_sat)}

## Testes de Saturação - C++

{saturation_summary(cpp_sat)}

## Controle de Saturação

O servidor Python usa um semáforo assíncrono para limitar reconstruções simultâneas. Quando o limite é atingido, a API retorna HTTP 429. O servidor C++ usa um contador atômico para aplicar a mesma política. Esse controle evita esgotamento de memória, principalmente no conjunto 60x60, em que a matriz H é grande.

## Sistemas Distribuídos

- Acesso a recursos: o cliente acessa reconstrução remota por HTTP sem executar o algoritmo localmente.
- Transparência: Python e C++ expõem o mesmo endpoint `/reconstruct` e aceitam o mesmo JSON.
- Abertura: o contrato REST permite substituir ou adicionar novos servidores.
- Escalabilidade: os testes de saturação medem limites de concorrência e throughput.
- Gerenciamento de recursos: semáforos e contador atômico limitam processamento simultâneo.
- Custo computacional: os relatórios registram tempo, memória, CPU, iterações e latência.
- Contingência: o cliente implementa timeout, retry e resposta padronizada para servidor indisponível.

## Decisões Técnicas

- CGNR foi mantido exatamente conforme a recorrência pedida.
- CGNE foi implementado como algoritmo adicional.
- O fator de redução é estimado por iteração de potência para reduzir uso de memória.
- A regularização é calculada e registrada, sem alterar a fórmula obrigatória do CGNR.

## Conclusão

O projeto entrega duas implementações independentes e comparáveis de reconstrução de imagem com BLAS, API de serviço, cliente distribuído, testes de saturação, controle de concorrência e documentação de execução. A equivalência deve ser avaliada comparando metadados, CSVs reconstruídos e tempos coletados em `results/`.
"""
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(markdown, encoding="utf-8")
    print(REPORT)


if __name__ == "__main__":
    main()
