# Dados

Este diretório inclui sinais pequenos usados nos testes e reconstruções.

Arquivos grandes de modelo não são versionados no Git:

- `H-1.csv`
- `H-1.csv.zip`

Para executar a reconstrução 60x60, coloque `H-1.csv` neste diretório ou extraia:

```bash
unzip -o data/H-1.csv.zip -d data
```

Os scripts assumem `data/H-1.csv` como matriz de modelo.
