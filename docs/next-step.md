# Next Step

Próximo passo principal: comparar a galeria gerada com as imagens 2 e 3 de referência e, se necessário, ajustar finamente os parâmetros do `spot map`.

```bash
cd /Users/eduardooliveira/codigos/cgnr-distributed-reconstruction
./scripts/run_python.sh
```

Em outro terminal:

```bash
cd /Users/eduardooliveira/codigos/cgnr-distributed-reconstruction
./scripts/run_cpp.sh
```

Depois rodar o cliente com os dados reais:

```bash
cd /Users/eduardooliveira/codigos/cgnr-distributed-reconstruction
python_server/.venv/bin/python client/client.py \
  --requests 1 \
  --signals data/G-1.csv data/G-2.csv \
  --model data/H-1.csv \
  --output results/client_comparison_60x60.json \
  --timeout 600
```

Observação: a matriz 60x60 é grande (`H-1.csv` tem cerca de 648 MB), então a execução pode consumir bastante memória e tempo.

Já foi executada reconstrução real corrigida com:

- `data/H-1.csv`
- `data/G-1.csv`
- `algorithm=cgnr`
- `apply_gain=true`

Resultados principais:

- `results/python_cgnr_G-1_20260618T022100124238Z.png`
- `results/python_cgnr_G-1_20260618T022100124238Z_visualization.png`
- `results/cpp_cgnr_1781749354619.png`
- `results/cpp_cgnr_1781749354619_visualization.png`
- `results/three_images_visualization_gallery.png`
- `results/three_images_reconstruction_summary.json`
- `results/real_reconstruction_comparison.png`
- `results/real_reconstruction_comparison_summary.json`

Validação rápida:

```bash
./scripts/run_all_tests.sh
```
