FROM debian:bookworm-slim AS build

RUN apt-get update && apt-get install -y --no-install-recommends build-essential cmake libopenblas-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY cpp_server /app/cpp_server
WORKDIR /app/cpp_server
RUN cmake -S . -B build && cmake --build build -j

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends libopenblas0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=build /app/cpp_server/build/cpp_reconstruction_server /app/cpp_server/cpp_reconstruction_server
COPY cpp_server /app/cpp_server
EXPOSE 8001
WORKDIR /app/cpp_server
CMD ["./cpp_reconstruction_server"]
