FROM ghcr.io/mlflow/mlflow:latest

RUN pip install "psycopg[binary]" boto3
