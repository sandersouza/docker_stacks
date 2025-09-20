![K6 stack](banner.png)
# k6 + Grafana + Prometheus + InfluxDB

Ambiente completo para executar testes de carga com k6 e visualizar métricas em tempo real. A stack inclui Prometheus (para
receber métricas via remote write), Grafana (dashboards provisionados) e InfluxDB 1.8 para armazenar resultados históricos.

## Serviços
| Serviço | Porta | Descrição |
|---------|-------|-----------|
| grafana | 3000  | UI com dashboards e datasources provisionados |
| prometheus | 9090 | Recebe métricas (`--web.enable-remote-write-receiver`) |
| influxdb | 8086 | Armazenamento de métricas do k6 via `--out influxdb` (credenciais em `.env`) |

## Subindo a stack
```bash
# dentro de stresstest/k6_grafana/
docker compose up -d
```
> Para alterar credenciais ou portas, copie `.env` para `.env.local`, ajuste e rode `docker compose --env-file .env.local up -d`.

## Executando testes
### Opção 1 – Usando container oficial do k6
```bash
docker compose run --rm \
  -e K6_PROMETHEUS_RW_SERVER_URL=http://prometheus:9090/api/v1/write \
  -v "$PWD/scripts:/scripts" grafana/k6 run /scripts/example.js \
  --out influxdb=http://admin:senha123@influxdb:8086/metrics \
  --out experimental-prometheus-rw=http://prometheus:9090/api/v1/write
```
Ajuste o script em `scripts/example.js` ou monte os seus em `scripts/`.

### Opção 2 – Utilitário `runk6.sh`
O script `runk6.sh` compila um binário k6 com a extensão `xk6-exec` (via `go` + `xk6`) e usa `fzf` para navegar pelos scripts.
Execute apenas se desejar usar o binário local:
```bash
./runk6.sh
```
> O script tenta instalar `go`, `fzf` e `xk6` automaticamente (exige permissões sudo quando necessário).

## Dashboards e métricas
- Grafana: http://localhost:3000 (login do `.env`).
- Prometheus: http://localhost:9090 (consulta das séries enviadas pelo k6).
- InfluxDB: use a API em `http://localhost:8086` ou clientes compatíveis (banco `metrics`).

O Prometheus está configurado para raspar `host.docker.internal:6565`; edite `prometheus/prometheus.yml` para adequar ao seu fluxo.

## Encerramento
```bash
docker compose down            # mantém volumes (dashboards e dados InfluxDB)
# docker compose down -v       # limpa tudo
```
