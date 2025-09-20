![Descrição da Imagem](banner.png)
# Performance & Stress Testing Stacks 🚀

Repositório para montar laboratórios locais de bancos de dados, observabilidade e testes de carga. Cada stack fica isolada em
um diretório com `docker-compose.yml`, scripts auxiliares e um `README.md` próprio explicando como executar workloads e limpar
os ambientes.

## Pré-requisitos básicos
- Docker 20+
- Docker Compose v2
- Python 3.10+ (para scripts de carga/debug)
- Acesso a internet na primeira execução quando for necessário baixar imagens ou clonar dependências externas

## Organização
```plaintext
.
├── database
│   ├── mongodb
│   ├── mysql
│   └── redisinsight
├── monitoring
│   ├── docker-compose.yml
│   └── grafana/prometheus/k8s-fakeMetrics
└── stresstest
    ├── k6_grafana
    └── tsdb_exporter
```

- `database/` agrupa stacks para carregar dados sintéticos em MongoDB, MySQL e Redis + RedisInsight.
- `monitoring/` contém a stack de observabilidade (Grafana + Prometheus + Fake Metrics Generator) com dashboards provisionados.
- `stresstest/` oferece ferramentas de teste de carga (k6 + Grafana/InfluxDB + Prometheus) e utilitários para enviar métricas
  de ferramentas externas para um TSDB.

## Como usar
1. Escolha a stack de interesse na estrutura acima.
2. Leia o `README.md` do diretório da stack para conhecer variáveis de ambiente, portas expostas e scripts disponíveis.
3. Execute `docker compose up -d` (ou `docker-compose`, conforme sua versão) a partir da pasta da stack.
4. Use os scripts fornecidos para gerar dados, rodar testes ou limpar tabelas.
5. Finalize com `docker compose down` (adicione `-v` se quiser descartar volumes).

Cada README específico também descreve credenciais padrão e como personalizar o ambiente antes de subir os containers.

---

🎉 Explore, adapte às suas necessidades e contribua com novas stacks quando quiser!
