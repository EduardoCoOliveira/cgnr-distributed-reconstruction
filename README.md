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

## Servidor Python

```bash
cd /Users/eduardooliveira/codigos/cgnr-distributed-reconstruction
python3 -m venv python_server/.venv
source python_server/.venv/bin/activate
pip install -r python_server/requirements.txt
./scripts/run_python.sh
```

## Servidor C++

```bash
cd /Users/eduardooliveira/codigos/cgnr-distributed-reconstruction
./scripts/run_cpp.sh
```

## Cliente

Com os dois servidores ativos:

```bash
cd /Users/eduardooliveira/codigos/cgnr-distributed-reconstruction/client
python client.py --requests 2 --signals data/G-1.csv data/G-2.csv --model data/H-1.csv
```

## Testes

```bash
./scripts/run_all_tests.sh
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
