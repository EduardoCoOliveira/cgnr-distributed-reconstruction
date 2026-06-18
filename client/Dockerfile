FROM python:3.12-slim

WORKDIR /app
COPY python_server/requirements.txt /app/python_server/requirements.txt
RUN pip install --no-cache-dir -r /app/python_server/requirements.txt
COPY . /app
WORKDIR /app
