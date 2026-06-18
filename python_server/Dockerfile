FROM python:3.12-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libopenblas0 && rm -rf /var/lib/apt/lists/*
COPY python_server/requirements.txt /app/python_server/requirements.txt
RUN pip install --no-cache-dir -r /app/python_server/requirements.txt
COPY . /app
WORKDIR /app/python_server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
