FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r --no-cache-dir requirements.txt

COPY . .
