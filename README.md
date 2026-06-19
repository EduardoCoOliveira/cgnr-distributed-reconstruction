# CGNR Distributed Reconstruction

Projeto acadêmico de reconstrução de imagens por CGNR/CGNE em arquitetura cliente-servidor.

## Estrutura

```text
data/
python_server/
cpp_server/
client/
reports/
results/
docs/
scripts/
```

## Dados

Coloque os arquivos CSV em `data/`.

Para o conjunto 60x60:

```bash
cp /Users/eduardooliveira/Downloads/G-1.csv data/
cp /Users/eduardooliveira/Downloads/G-2.csv data/
cp /Users/eduardooliveira/Downloads/A-60x60-1.csv data/
cp /Users/eduardooliveira/Downloads/H-1.csv.zip data/
unzip -o data/H-1.csv.zip -d data
```

Arquivos esperados para a bateria completa:

- `data/H-1.csv`
- `data/H-2.csv`
- `data/g-30x30-1.csv`
- `data/g-30x30-2.csv`
- `data/G-1.csv`
- `data/G-2.csv`
- `data/A-30x30-1.csv`
- `data/A-60x60-1.csv`

## Preparar Ambiente

Em Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip build-essential cmake libopenblas-dev pkg-config
```

Depois, na raiz do projeto:

```bash
python3 -m venv python_server/.venv
source python_server/.venv/bin/activate
pip install -r python_server/requirements.txt
```

## Servidor Python

```bash
./scripts/run_python.sh
```

O servidor Python sobe em `http://localhost:8000`.

## Servidor C++

```bash
./scripts/run_cpp.sh
```

O servidor C++ sobe em `http://localhost:8001`.

## Cliente

Com os dois servidores ativos:

```bash
python client/client.py \
  --requests 6 \
  --signals data/g-30x30-1.csv data/g-30x30-2.csv data/G-1.csv data/G-2.csv data/A-30x30-1.csv data/A-60x60-1.csv \
  --models data/H-1.csv data/H-2.csv \
  --output results/client_comparison.json
```

O cliente monta uma sequência única de sinais e envia os mesmos payloads para Python e C++.
O ganho (`apply_gain`), o algoritmo e o modelo compatível com o sinal são escolhidos aleatoriamente.

## Galerias Focadas

Com os dois servidores ativos, gere as galerias comparativas Python/C++:

```bash
python_server/.venv/bin/python scripts/run_gabarito_focus.py \
  --case-group gabarito \
  --output-json results/gabarito_focus_results.json \
  --output-index results/gabarito_focus_index.md \
  --output-gallery results/gabarito_focus_gallery.png
```

```bash
python_server/.venv/bin/python scripts/run_gabarito_focus.py \
  --case-group sem-gabarito \
  --output-json results/sem_gabarito_focus_results.json \
  --output-index results/sem_gabarito_focus_index.md \
  --output-gallery results/sem_gabarito_focus_gallery.png
```

## Testes

```bash
./scripts/run_all_tests.sh
```

Para teste de sobrecarga com os servidores já ativos:

```bash
python client/saturation_test.py \
  --url http://localhost:8000/reconstruct \
  --signal data/G-1.csv \
  --model data/H-1.csv \
  --apply-gain \
  --output results/python_saturation.json
```

```bash
python client/saturation_test.py \
  --url http://localhost:8001/reconstruct \
  --signal data/G-1.csv \
  --model data/H-1.csv \
  --apply-gain \
  --output results/cpp_saturation.json
```

## Relatório

```bash
./scripts/generate_report.sh
```

O relatório final fica em `reports/report.md`.

## Docker Compose

```bash
docker compose up --build
```

## Documentação de Continuidade

Antes de continuar em outra máquina, leia:

- `docs/ai-context.md`
- `docs/session-log.md`
- `docs/next-step.md`
- `docs/decisions.md`
