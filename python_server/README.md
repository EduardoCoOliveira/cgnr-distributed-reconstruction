# Servidor Python

## Instalação

```bash
cd /Users/eduardooliveira/codigos/cgnr-distributed-reconstruction/python_server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Execução

```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

## Endpoint

```bash
curl -X POST http://localhost:8000/reconstruct \
  -H "Content-Type: application/json" \
  -d '{"signal_file":"data/G-1.csv","model_file":"data/H-1.csv","apply_gain":true,"algorithm":"cgnr"}'
```

## BLAS

```bash
python blas_tests.py --size 512 --output ../results/python_blas_report.json
```
