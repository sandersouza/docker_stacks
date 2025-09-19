# Observability Stack - Grafana + Prometheus + Fake Metrics Generator

Stack compacta para estudos e experimentos envolvendo métricas. Ela entrega Grafana provisionado com datasources e um dashboard
base, com o Prometheus coletando métricas do Fake Metrics Generator. Ideal para simular um parque de servidores fake, avaliar
comportamento de workloads e preparar integrações com pipelines de IA.

## Serviços incluídos
| Serviço | Porta | Função |
|---------|-------|--------|
| Grafana | 3000  | Visualização central com dashboards provisionados automaticamente |
| Prometheus | 9090 | Coleta e armazena métricas do Fake Metrics Generator |
| Fake Metrics Generator | 5001 | Gera métricas fake expostas em `/metrics` e escreve logs para observabilidade |

## Pré-requisitos
- Docker 20+
- Docker Compose v2
- Host Linux (recomendado) ou ambiente compatível com Docker

## Estrutura de diretórios
```plaintext
grafana/observability
├── docker-compose.yml
├── grafana
│   └── provisioning
│       ├── dashboards
│       │   └── fake_metrics_observability.json
│       └── datasources
│           └── datasources.yml
├── prometheus
│   └── prometheus.yml
└── fake-metrics-generator
    └── Dockerfile
```

## Como subir a stack
1. Na raiz do repositório execute:
   ```bash
   cd grafana/observability
   docker compose build
   docker compose up -d
   ```
   > A primeira execução baixa o código do Fake Metrics Generator diretamente do GitHub para montar a imagem local.

2. (Opcional) Ajuste as credenciais do Grafana exportando variáveis antes do `docker compose up`:
   ```bash
   export GRAFANA_ADMIN_USER=admin
   export GRAFANA_ADMIN_PASSWORD=senhaSuperSecreta
   ```

## Acessos rápidos
- Grafana: http://localhost:3000 (login padrão `admin`/`admin` caso não altere via ambiente)
- Prometheus: http://localhost:9090
- Fake Metrics Generator: http://localhost:5001/metrics

## O que já vem configurado
- **Datasources do Grafana** → Prometheus cadastrado automaticamente (uid `PROMETHEUS_DS`).
- **Dashboard "Fake Metrics Observability"** → Painel com visão rápida do volume de métricas fake e séries geradas.
- **Prometheus** → Scrape de `prometheus:9090` e `fake-metrics-generator:5001/metrics` a cada 15s.

## Próximos passos sugeridos
- Ajustar o arquivo `src/config/config.json` (dentro do container do Fake Metrics Generator) para alterar quantidade de métricas/labels.
- Criar dashboards adicionais no Grafana, duplicando o JSON em `grafana/provisioning/dashboards`.
- Integrar a stack a um servidor MCP ou agentes de IA consumindo as APIs do Grafana/Prometheus.

## Finalizando
Para desligar tudo e remover os containers:
```bash
docker compose down
```

Se desejar limpar os volumes persistentes (dados do Grafana e Prometheus):
```bash
docker compose down -v
```
