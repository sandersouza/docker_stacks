# Observability Stack - Grafana + Prometheus + Fake Metrics Generator

Stack compacta para estudos de observabilidade. Ela sobe o **Fake Metrics Generator** (simulando um cluster Kubernetes),
coleta tudo com **Prometheus** e exibe em dashboards provisionados no **Grafana**.

## Serviços
| Serviço | Porta local | Descrição |
|---------|-------------|-----------|
| Grafana | 3000        | Painel com datasources/dashboards provisionados automaticamente |
| Prometheus | 9090     | Coletor TSDB com scrape dos alvos internos |
| Fake Metrics Generator | 5500 (padrão) | Gera métricas e logs sintéticos imitando vários clusters |

## Estrutura de diretórios
```plaintext
monitoring
├── docker-compose.yml
├── grafana
│   └── provisioning
│       ├── datasources/datasources.yml
│       └── dashboards/dashboard.json
├── prometheus
│   └── prometheus.yml
└── k8s-fakeMetrics
    └── Dockerfile  (clona https://github.com/sandersouza/k8s-fakeMetrics)
```

## Subindo a stack
```bash
# a partir de monitoring/
docker compose up -d
```
A primeira execução baixa as imagens do Docker Hub e clona o repositório `k8s-fakeMetrics` durante o build.

### Variáveis úteis
- `GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD`: credenciais do Grafana (padrão `admin`/`admin`).
- `METRICS_PORT`: porta exposta pelo Fake Metrics Generator (padrão 5500). Altere no `.env` ou exporte no shell antes do `docker compose up`.
- Demais variáveis do Fake Metrics Generator permitem controlar número de clusters, nodes, pods, intervalo de atualização etc. Consulte o `docker-compose.yml` para os defaults.

## Acessos rápidos
- Grafana: http://localhost:3000 (credenciais acima)
- Prometheus: http://localhost:9090
- Métricas sintéticas: http://localhost:5500/metrics

## Encerrando e limpeza
```bash
docker compose down        # Para containers
# docker compose down -v   # (opcional) remove volumes de dados do Grafana/Prometheus
```

Ajuste dashboards duplicando o JSON em `grafana/provisioning/dashboards/` ou conecte outros exporters apontando para o Prometheus.
