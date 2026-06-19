# Relatório Comparativo

Gerado em 2026-06-19T01:06:21.461886+00:00.

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

| Operação | Tempo (s) | Dimensão | Memória RSS (bytes) |
|---|---:|---|---:|
| MN = M * N | 0.000310 | [128, 128] | 40960000 |
| aM = a * M (scalar) | 0.000064 | [128, 128] | 41156608 |
| aM = a * M (vector left) | 0.000013 | [128] | 41193472 |
| Ma = M * a (scalar) | 0.000009 | [128, 128] | 41193472 |
| Ma = M * a (vector right) | 0.000004 | [128] | 41193472 |


## Resultados dos Testes BLAS - C++

| Operação | Tempo (s) | Dimensão | Memória RSS (bytes) |
|---|---:|---|---:|
| MN = M * N | 0.002101 | 512x512 | 17821696 |
| aM = a * M (scalar) | 0.000166 | 512x512 | 17952768 |
| aM = a * M (vector left) | 0.000059 | 1x512 | 17952768 |
| Ma = M * a (scalar) | 0.000146 | 512x512 | 17952768 |
| Ma = M * a (vector right) | 0.000048 | 512x1 | 17952768 |


## Resultados CGNR/CGNE e Comparação Python vs C++

| Serviço | Algoritmo | Status | Iterações | Tempo total (s) | Latência cliente (s) |
|---|---|---|---:|---:|---:|
| python | CGNR | ok | 1 | 15.123008 | 15.130473 |
| cpp | CGNR | ok | 1 | 19.928005 | 19.930465 |
| python | CGNR | ok | 1 | 1.793088 | 1.797414 |
| cpp | CGNR | ok | 1 | 2.975076 | 2.976904 |


## Reconstruções com Gabarito

| Caso | Modelo | Iter. Py | Iter. C++ | Tempo Py (s) | Tempo C++ (s) | Diff máx. | Diff média |
|---|---|---:|---:|---:|---:|---:|---:|
| `data/g-30x30-1.csv` | `data/H-2.csv` | 10 | 10 | 0.139796 | 0.123614 | 2.91038e-11 | 9.84776e-13 |
| `data/g-30x30-2.csv` | `data/H-2.csv` | 10 | 10 | 0.137905 | 0.160935 | 2.91038e-11 | 1.08937e-12 |
| `data/G-1.csv` | `data/H-1.csv` | 10 | 10 | 0.891481 | 0.813838 | 5.82077e-11 | 2.13143e-12 |
| `data/G-2.csv` | `data/H-1.csv` | 10 | 10 | 0.881286 | 0.979363 | 8.73115e-11 | 4.26074e-12 |


Galeria visual: `results/gabarito_focus_gallery.png`.
Índice detalhado: `results/gabarito_focus_index.md`.

## Reconstruções sem Gabarito

| Caso | Modelo | Iter. Py | Iter. C++ | Tempo Py (s) | Tempo C++ (s) | Diff máx. | Diff média |
|---|---|---:|---:|---:|---:|---:|---:|
| `data/A-30x30-1.csv` | `data/H-2.csv` | 10 | 10 | 0.197419 | 0.165685 | 0.4375 | 0.0265846 |
| `data/A-60x60-1.csv` | `data/H-1.csv` | 10 | 10 | 0.864147 | 1.011152 | 0.00219727 | 0.000135789 |


Galeria visual: `results/sem_gabarito_focus_gallery.png`.
Índice detalhado: `results/sem_gabarito_focus_index.md`.

## Reconstrução Real 60x60

Quando `results/real_reconstruction_comparison_summary.json` estiver presente, a comparação direta é:

A comparação 60x60 está consolidada nas tabelas de reconstruções com e sem gabarito. O arquivo opcional `results/real_reconstruction_comparison_summary.json` não é necessário para validar a entrega atual.


As reconstruções usam orientação column-major para compatibilidade com a visualização típica em MATLAB/Octave. Cada execução salva uma imagem pura (`png_raw`) e uma imagem de visualização (`png_visualization`) com escala logarítmica e eixos.
As visualizações incluem identificação do algoritmo, data/hora de início, data/hora de término da reconstrução, tamanho em pixels e número de iterações. Os mesmos dados também ficam salvos no JSON de metadados de cada imagem.

## Testes de Saturação - Python

| Concorrência | Tempo médio (s) | Tempo máx. (s) | Throughput (req/s) | Erros |
|---:|---:|---:|---:|---:|
| 1 | 0.102618 | 0.102618 | 9.683318 | 0 |
| 2 | 0.283031 | 0.335627 | 5.896139 | 0 |
| 4 | 0.110593 | 0.291405 | 13.468763 | 2 |
| 8 | 0.082900 | 0.353494 | 22.574623 | 6 |
| 16 | 0.052677 | 0.527631 | 30.010050 | 14 |
| 32 | 0.021702 | 0.229069 | 138.953808 | 30 |


## Testes de Saturação - C++

| Concorrência | Tempo médio (s) | Tempo máx. (s) | Throughput (req/s) | Erros |
|---:|---:|---:|---:|---:|
| 1 | 0.080997 | 0.080997 | 12.166265 | 0 |
| 2 | 0.009027 | 0.010414 | 170.633978 | 0 |
| 4 | 0.007475 | 0.011682 | 238.477626 | 2 |
| 8 | 0.013399 | 0.040531 | 171.171758 | 6 |
| 16 | 0.011273 | 0.055297 | 191.173208 | 11 |
| 32 | 0.010281 | 0.038277 | 501.799673 | 27 |


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
