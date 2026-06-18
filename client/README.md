# Cliente

O cliente envia a mesma sequência de sinais para os servidores Python e C++.

## Execução

```bash
cd /Users/eduardooliveira/codigos/cgnr-distributed-reconstruction/client
python client.py --requests 2 --signals data/G-1.csv data/G-2.csv --model data/H-1.csv
```

Para Docker Compose, use os nomes de serviço:

```bash
python client.py \
  --python-url http://python_server:8000/reconstruct \
  --cpp-url http://cpp_server:8001/reconstruct
```

## Teste de saturação

```bash
python saturation_test.py --url http://localhost:8000/reconstruct --output ../results/python_saturation.json
python saturation_test.py --url http://localhost:8001/reconstruct --output ../results/cpp_saturation.json
```
