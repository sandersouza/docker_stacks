# syntax=docker/dockerfile:1

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instala dependências de runtime
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação
COPY k8s_fake_metrics ./k8s_fake_metrics
COPY dynamicMetrics.json ./

# Copia configurações padrão (pode ser sobrescrito via ConfigMap/Secret)
COPY .env ./

# Cria usuário não-root para execução segura em Pods
RUN addgroup --system app && adduser --system --ingroup app app \
    && chown -R app:app /app
USER app

EXPOSE 8000

ENTRYPOINT ["python", "-m", "k8s_fake_metrics"]
