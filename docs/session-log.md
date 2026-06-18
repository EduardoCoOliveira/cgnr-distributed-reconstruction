# Session Log

## 2026-06-11

- Criada a estrutura inicial do projeto acadêmico.
- Registrado ambiente Mac e modo executor.
- Identificados arquivos de dados disponíveis no Downloads.
- Confirmado que os dados 60x60 estão disponíveis e que os arquivos 30x30 não foram encontrados no Downloads.
- Implementação planejada para Python FastAPI e C++ HTTP independente.
- Documentação obrigatória criada desde o início para permitir continuidade entre máquinas.
- Implementado servidor Python com FastAPI, CGNR, CGNE, ganho de sinal, métricas, PNG/CSV e controle de saturação.
- Implementado servidor C++ HTTP independente com CBLAS/OpenBLAS, CGNR, CGNE, PNG/CSV e controle de saturação.
- Implementado cliente com retry, timeout, comparação Python vs C++ e teste de saturação.
- Criados scripts automáticos, Docker Compose, Dockerfiles e gerador de relatório.
- Copiados para `data/` os arquivos 60x60 disponíveis e extraído `H-1.csv`.
- Criado `.venv` Python local e instaladas dependências.
- Validação executada: sintaxe Python passou; teste BLAS Python pequeno passou; relatório inicial foi gerado.
- Validação pendente: build C++ nativo não foi concluído porque `cmake` e `openblas` não estavam instalados e a instalação via Homebrew ficou presa no download do GCC.

## 2026-06-17

- Confirmado ambiente Mac e modo executor.
- Verificado que `cmake` está instalado em `/opt/homebrew/bin/cmake`.
- Verificado que OpenBLAS está instalado em `/opt/homebrew/opt/openblas` e que `cblas.h` existe.
- Configurado CMake com OpenBLAS explícito:
  `-DBLAS_LIBRARIES=/opt/homebrew/opt/openblas/lib/libopenblas.dylib`.
- Build C++ nativo concluído com sucesso.
- `./scripts/run_all_tests.sh` executado com sucesso.
- Gerados relatórios `results/python_blas_report.json` e `results/cpp_blas_report.json`.
- Criado dataset de fumaça em `data/smoke/` com matriz identidade 900x900 e sinal 900x1 para validação rápida de ponta a ponta.
- Servidor Python validado em `/health` e `/reconstruct` com dataset de fumaça.
- Servidor C++ validado em `/health` e `/reconstruct` com dataset de fumaça.
- Cliente comparativo executado com sucesso contra os dois servidores.
- Testes de saturação executados para Python e C++ com níveis 1, 2, 4, 8, 16 e 32.
- Confirmado controle de saturação com HTTP 429 nos dois servidores.
- `reports/report.md` regenerado com os resultados disponíveis.
- Esclarecido que as imagens em gradiente vinham do dataset sintético `data/smoke/`, usado apenas para validação de integração.
- Ajustada a fórmula de ganho em Python e C++ para `gamma_l = 100 + (1/20) * l * sqrt(l)`, alinhada ao material visual de referência.
- Validação após ajuste: `py_compile` passou e o binário C++ recompilou com sucesso.
- Executada reconstrução real 60x60 com `data/H-1.csv` e `data/G-1.csv`, `algorithm=cgnr`, `apply_gain=true`.
- Resultado Python real:
  `results/python_cgnr_G-1_20260618T010923835694Z.png`,
  `results/python_cgnr_G-1_20260618T010923835694Z.csv`,
  `results/python_cgnr_G-1_20260618T010923835694Z_metadata.json`.
- Resultado C++ real:
  `results/cpp_cgnr_1781745051379.png`,
  `results/cpp_cgnr_1781745051379.csv`,
  `results/cpp_cgnr_1781745051379_metadata.json`.
- Comparação Python vs C++ real gerada em `results/real_reconstruction_comparison.png`.
- Diferença máxima absoluta entre os CSVs Python e C++: aproximadamente `8.73e-11`.
- Diferença média absoluta entre os CSVs Python e C++: aproximadamente `2.90e-12`.
- `reports/report.md` regenerado depois da reconstrução real.
- Ajustado o salvamento de imagem para orientação column-major em Python e C++.
- Adicionadas duas saídas de imagem por reconstrução:
  - `png_raw`: imagem pura, sem eixos.
  - `png_visualization`: visualização em escala logarítmica com título/eixos.
- Validado com dataset de fumaça que Python e C++ retornam `png_raw` e `png_visualization`.
- Rerodada reconstrução real 60x60 com orientação corrigida:
  - Python: `results/python_cgnr_G-1_20260618T020111324391Z.png`
  - Python visualização: `results/python_cgnr_G-1_20260618T020111324391Z_visualization.png`
  - C++: `results/cpp_cgnr_1781748149259.png`
  - C++ visualização: `results/cpp_cgnr_1781748149259_visualization.png`
- Comparação atualizada em `results/real_reconstruction_comparison.png`.
- Equivalência mantida: diferença máxima absoluta Python vs C++ aproximadamente `8.73e-11`.
- Ajustada a visualização para usar fundo preto com `log(abs(f))` e contraste seletivo por percentis 75 e 99.9, reduzindo aparência de estática.
- Rerodada reconstrução real após ajuste de visualização:
  - Python visualização final: `results/python_cgnr_G-1_20260618T020811004449Z_visualization.png`
  - C++ visualização final: `results/cpp_cgnr_1781748596114_visualization.png`
- `results/real_reconstruction_comparison_summary.json` e `reports/report.md` atualizados.
- Refinada novamente a visualização para reduzir pixels avulsos: percentis 82 e 99.8, corte de fundo fraco e remoção de pixels isolados sem vizinhos fortes.
- Validação após refinamento: `py_compile` passou e C++ recompilou com sucesso.
- Substituída a visualização por um `spot map`: detecção de máximos locais fortes em `log(abs(f))`, supressão por distância mínima e desenho apenas dos refletores relevantes.
- Rerodada reconstrução real Python e C++ para `G-1/H-1` com o `spot map`.
- Visualização Python limpa gerada em `results/python_cgnr_G-1_20260618T022100124238Z_visualization.png`.
- Visualização C++ limpa gerada em `results/cpp_cgnr_1781749354619_visualization.png`.
- Equivalência Python vs C++ mantida: diferença máxima absoluta aproximadamente `8.73e-11`.
- Ajustado título da visualização C++ para `LOG` com glifos mais claros; C++ recompilou com sucesso.
- Copiados novos sinais de referência:
  - `/Users/eduardooliveira/Downloads/G-2 (1).csv` para `data/G-2-image2.csv`
  - `/Users/eduardooliveira/Downloads/A-60x60-1 (1).csv` para `data/A-60x60-image3.csv`
- Executadas reconstruções Python e C++ para imagem 2 e imagem 3.
- Gerada galeria comparativa em `results/three_images_visualization_gallery.png`.
- Gerado resumo comparativo em `results/three_images_reconstruction_summary.json`.
- Para imagem 2 (`G-2`), Python e C++ ficaram equivalentes com diferença máxima absoluta aproximadamente `1.16e-10`.
- Para imagem 3 (`A-60x60`), Python e C++ ficaram equivalentes em escala relativa, mas o sinal tem amplitude muito maior; diferença máxima absoluta aproximadamente `0.00390625`.
- Ajustados parâmetros do `spot map` para a imagem 2: threshold reduzido, limite de pontos aumentado e distância mínima menor para recuperar refletores médios que estavam sendo descartados.
- Regenerada `results/three_images_visualization_gallery.png` com a visualização refinada.
- Implementado cache no servidor C++ para matriz de modelo `H` e fator de redução, evitando reler e recalcular a matriz em requisições subsequentes com o mesmo `model_file`.
- C++ recompilou com sucesso após a otimização de cache.
