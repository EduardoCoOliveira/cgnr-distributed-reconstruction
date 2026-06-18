# Servidor C++

## Dependências

- C++17
- CMake 3.16+
- OpenBLAS com CBLAS

macOS com Homebrew:

```bash
brew install openblas cmake
```

## Build

```bash
cd /Users/eduardooliveira/codigos/cgnr-distributed-reconstruction/cpp_server
cmake -S . -B build
cmake --build build -j
```

Se o CMake não encontrar OpenBLAS no macOS:

```bash
cmake -S . -B build -DBLAS_LIBRARIES="$(brew --prefix openblas)/lib/libopenblas.dylib"
```

## Execução

```bash
./build/cpp_reconstruction_server
```

O servidor escuta `http://localhost:8001` por padrão.

## Endpoint

```bash
curl -X POST http://localhost:8001/reconstruct \
  -H "Content-Type: application/json" \
  -d '{"signal_file":"data/G-1.csv","model_file":"data/H-1.csv","apply_gain":true,"algorithm":"cgnr"}'
```

## BLAS

```bash
./build/cpp_reconstruction_server --blas-tests ../results/cpp_blas_report.json
```
