# Relatório Comparativo

Gerado em 2026-06-18T13:31:15.100187+00:00.

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

Relatório ainda não gerado.


## Resultados dos Testes BLAS - C++

Relatório ainda não gerado.


## Resultados CGNR/CGNE e Comparação Python vs C++

Relatório comparativo do cliente ainda não gerado.


## Reconstrução Real 60x60

Executada com `data/H-1.csv`, `data/G-1.csv`, `algorithm=cgnr` e `apply_gain=true`.

| Métrica | Valor |
|---|---:|
| Formato | [60, 60] |
| Diferença máxima absoluta Python vs C++ | 8.731149137020e-11 |
| Diferença média absoluta Python vs C++ | 2.901826236862e-12 |
| Mínimo Python | 0.000000 |
| Máximo Python | 0.000000 |
| Mínimo C++ | 0.000000 |
| Máximo C++ | 0.000000 |


Imagem comparativa gerada em `results/real_reconstruction_comparison.png`.

As reconstruções usam orientação column-major para compatibilidade com a visualização típica em MATLAB/Octave. Cada execução salva uma imagem pura (`png_raw`) e uma imagem de visualização (`png_visualization`) com escala logarítmica e eixos.

## Testes de Saturação - Python

Relatório ainda não gerado.


## Testes de Saturação - C++

Relatório ainda não gerado.


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
