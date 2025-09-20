## Stress Test Stacks
Ferramentas para gerar e inspecionar cargas de trabalho. Use estas stacks para validar performance de aplicações, coletar
métricas e enviar resultados para timeseries databases.

### Diretórios
- [`k6_grafana`](k6_grafana/README.md): ambiente completo com Prometheus, Grafana e InfluxDB para acompanhar execuções do k6.
- [`tsdb_exporter`](tsdb_exporter/README.md): scripts e utilitários para enviar métricas customizadas (HTTP/3, curl, etc.) para InfluxDB.

Leia o README específico de cada stack para configurar variáveis, compilar dependências opcionais e executar os testes.
