![TSDB Exporter](images/banner.png)
# TSDB Exporter

Ferramentas para enviar métricas personalizadas (por exemplo, respostas HTTP/3) para o InfluxDB. Útil quando a ferramenta de
teste não possui integração nativa com a stack de observabilidade.

## O que está incluído
- `exporter.py`: lê JSON da entrada padrão, converte para o formato line protocol e escreve no InfluxDB (`http://localhost:8086/write?db=metrics`).
- `experiment.sh`: exemplo de laço que dispara requisições `curl --http3` e encaminha a saída para o exporter.
- `virtualenv.sh`: script auxiliar para criar/apagar o ambiente virtual Python.

## Pré-requisitos
- Python 3.10+
- Dependências listadas em `requirements.txt` (`requests` etc.)
- InfluxDB acessível (ex.: o serviço da stack `k6_grafana`).

## Como usar
```bash
# dentro de stresstest/tsdb_exporter/
./virtualenv.sh create
source venv/bin/activate
```

Envie qualquer payload JSON para o exporter. Exemplo com `curl` e label adicional (`--label` adiciona uma tag):
```bash
curl -s -k -o /dev/null \
  -X GET https://localhost:4433/quizzes/ \
  --write-out '%{json}' | ./exporter.py --label curl-http
```
O script gera pontos como `metric_name,label=curl-http value=123` e grava no InfluxDB (`db=metrics`, usuário `admin`, senha `senha123`).

Para rodar o experimento completo durante 5 minutos:
```bash
chmod +x experiment.sh
./experiment.sh
```
Ajuste o token, o endpoint e a concorrência direto no script conforme sua necessidade.

Finalize o ambiente virtual com `deactivate` e, se quiser, limpe tudo rodando `./virtualenv.sh cleanup`.
