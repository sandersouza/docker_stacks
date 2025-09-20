# syntax=docker/dockerfile:1

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Instala git para obter o código diretamente do repositório
RUN apt-get update \
    && apt-get install --no-install-recommends -y git \
    && rm -rf /var/lib/apt/lists/*

# Baixa o código da aplicação direto do GitHub
RUN git clone --depth 1 https://github.com/sandersouza/k8s-fakeMetrics.git /app

WORKDIR /app

# Instala dependências declaradas no repositório
RUN pip install --no-cache-dir -r requirements.txt

# Cria usuário não-root para execução segura em Pods
RUN addgroup --system app && adduser --system --ingroup app app \
    && chown -R app:app /app
USER app

EXPOSE 5500

ENTRYPOINT ["python", "-m", "k8s_fake_metrics"]
