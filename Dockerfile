FROM python:3.12-slim

WORKDIR /app
ENV PYTHONPATH=/app

RUN pip install --no-cache-dir kopf==1.44.6 kubernetes==36.0.2 pydantic==2.13.3

COPY workload_operator/ ./workload_operator/

CMD ["kopf", "run", "-m", "workload_operator.handlers", "--namespace", "default", "--standalone"]
