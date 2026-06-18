# AI Context

## Projeto

Sistema distribuído cliente-servidor para reconstrução de imagens de ultrassom usando métodos iterativos em álgebra linear.

## Ambiente Atual

- Ambiente informado pelo usuário: Mac
- Modo de trabalho informado pelo usuário: executor
- Diretório do projeto: `/Users/eduardooliveira/codigos/cgnr-distributed-reconstruction`
- Data da criação desta base: 2026-06-11

## Objetivo Técnico

Implementar duas versões equivalentes de reconstrução:

- Python 3.12+ com NumPy/OpenBLAS, FastAPI, Uvicorn, Pandas, Matplotlib e psutil.
- C++17 com OpenBLAS/CBLAS e CMake.

Ambas implementam manualmente CGNR e também CGNE como opção adicional. Nenhuma versão usa biblioteca pronta de CGNR/CGNE.

## Dados

Arquivos 60x60 informados e encontrados em `/Users/eduardooliveira/Downloads`:

- `H-1.csv.zip`
- `G-1.csv`
- `G-2.csv`
- `A-60x60-1.csv`
- `02-CSM30-Problema.pdf`

Arquivos 30x30 mencionados no enunciado, mas não encontrados durante a criação inicial:

- `H-2.csv`
- `g-30x30-1.csv`
- `g-30x30-2.csv`
- `A-30x30-1.csv`

O código aceita ambos os tamanhos. A execução completa com 30x30 depende da inclusão desses arquivos em `data/`.

## Arquitetura

- `python_server/`: serviço REST FastAPI com endpoint `POST /reconstruct`.
- `cpp_server/`: serviço HTTP independente em C++17 com endpoint `POST /reconstruct`.
- `client/`: cliente Python que envia os mesmos sinais para os dois serviços, com timeout, retry e relatório comparativo.
- `reports/`: gerador automático de `report.md`.
- `results/`: destino de métricas, imagens reconstruídas, CSVs e JSONs.
- `data/`: arquivos CSV/ZIP de entrada.
- `scripts/`: scripts para rodar servidores, testes e relatório.

## Contrato REST

Endpoint:

```http
POST /reconstruct
Content-Type: application/json
```

Payload:

```json
{
  "signal_file": "data/G-1.csv",
  "model_file": "data/H-1.csv",
  "apply_gain": true,
  "algorithm": "cgnr"
}
```

`algorithm` aceita `cgnr` e `cgne`.

## Critério Numérico

- `f0 = 0`
- parada quando `abs(||r(i+1)||2 - ||r(i)||2) < 1e-4` ou `iterations = 10`
- ganho opcional: `gamma_l = 100 + (1/20) * l * sqrt(l)`, conforme a fórmula exibida no material de referência
- fator de redução estimado por iteração de potência sobre `H^T H`
- regularização calculada como `lambda = max(abs(H^T g)) * 0.10` e registrada nos metadados

## Decisões Importantes

- O C++ usa servidor HTTP próprio para evitar dependência externa não solicitada.
- O C++ escreve PNG com encoder mínimo de grayscale sem bibliotecas de imagem.
- Saturação é controlada por semáforo no Python e por contador atômico no C++.
- Em caso de saturação, o servidor deve retornar HTTP 429.
- A conversão do vetor reconstruído para imagem usa orientação column-major, compatível com `reshape` do MATLAB/Octave. Isso evita a imagem aparecer rotacionada em relação às referências da disciplina.
- Cada reconstrução salva duas imagens: `png_raw`, sem eixos, e `png_visualization`, com escala logarítmica, título e eixos para relatório.

## Continuidade

Ao retomar o projeto, leia primeiro:

1. `docs/ai-context.md`
2. `docs/session-log.md`
3. `docs/next-step.md`
4. `docs/decisions.md`

Não dependa do histórico de chat para continuidade.
