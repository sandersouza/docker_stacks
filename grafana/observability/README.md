# Observability Stack - Grafana + Prometheus + Loki + Fake Metrics Generator

Stack completa para estudos e experimentos envolvendo métricas e logs. Ela entrega Grafana provisionado com datasources e um dashboard
base, Prometheus coletando métricas do Fake Metrics Generator e Loki recebendo logs via Promtail. Ideal para simular um parque de
servidores fake, avaliar comportamento de workloads e preparar integrações com pipelines de IA.

## Serviços incluídos
| Serviço | Porta | Função |
|---------|-------|--------|
| Grafana | 3000  | Visualização central com dashboards provisionados automaticamente |
| Prometheus | 9090 | Coleta e armazena métricas do Fake Metrics Generator |
| Loki | 3100 | Armazena logs recebidos do Promtail |
| Promtail | 3101 | Backend/agent responsável por enviar logs dos containers Docker para o Loki |
| Fake Metrics Generator | 5000 | Gera métricas fake expostas em `/metrics` e escreve logs para observabilidade |

## Pré-requisitos
- Docker 20+
- Docker Compose v2
- Host Linux (Promtail monta o socket do Docker para coletar logs; em Windows/macOS usar WSL2 ou adaptar o caminho do socket)

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
├── loki
│   └── config.yaml
├── prometheus
│   └── prometheus.yml
├── promtail
│   └── promtail-config.yml
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
- Loki API: http://localhost:3100/ready
- Fake Metrics Generator: http://localhost:5000/metrics

## O que já vem configurado
- **Datasources do Grafana** → Prometheus e Loki cadastrados automaticamente (uids `PROMETHEUS_DS` e `LOKI_DS`).
- **Dashboard "Fake Metrics Observability"** → Painel com visão rápida do volume de métricas fake, séries geradas e logs do gerador.
- **Prometheus** → Scrape de `prometheus:9090` e `fake-metrics-generator:5000/metrics` a cada 15s.
- **Loki + Promtail** → Promtail monitora os logs dos containers Docker (via socket) e envia tudo para o Loki.

## Próximos passos sugeridos
- Ajustar o arquivo `src/config/config.json` (dentro do container do Fake Metrics Generator) para alterar quantidade de métricas/labels.
- Criar dashboards adicionais no Grafana, duplicando o JSON em `grafana/provisioning/dashboards`.
- Integrar a stack a um servidor MCP ou agentes de IA consumindo as APIs do Grafana/Prometheus.

## Finalizando
Para desligar tudo e remover os containers:
```bash
docker compose down
```

Se desejar limpar os volumes persistentes (dados do Grafana, Prometheus e Loki):
```bash
docker compose down -v
```
