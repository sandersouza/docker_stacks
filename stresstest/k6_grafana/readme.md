Setup de Testes de Performance com K6, Grafana e InfluxDB
---
Este guia passo a passo mostra como configurar e usar um ambiente Dockerizado para testes de performance com K6, Grafana e InfluxDB.

Pré-requisitos
- Docker
- Docker Compose

Clone o Repositório
---
```
$ git clone <URL_DO_REPOSITORIO>
````

Arquivos de Configuração
---
Certifique-se de que todos os arquivos de configuração estão no diretório correto:
- docker-compose.yml
- Diretórios e arquivos de provisionamento do Grafana (./grafana/provisioning)
- Diretório para scripts do K6 (./scripts)

Arquivo .env
---
Configure as variáveis de ambiente necessárias no arquivo .env na raiz do projeto:
```
INFLUXDB_ADMIN_USER=admin
INFLUXDB_ADMIN_PASSWORD=password
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=senha123
```

Iniciando o Ambiente
---
Execute o seguinte comando no diretório do projeto para iniciar todos os serviços:
```
$ docker-compose up
````

Após os serviços estarem rodando, você pode acessar o Grafana em http://localhost:3000 e o InfluxDB em http://localhost:8086.

Executando Testes com K6
---
Crie um arquivo chamado test_script.js no diretório ./scripts com o seguinte conteúdo:
```
javascript
Copy code
import http from 'k6/http';
import { sleep } from 'k6';

export let options = {
    stages: [
        { duration: '1m', target: 20 }, // Simula 20 usuários por 1 minuto
    ],
};

export default function () {
    http.get('http://test.k6.io');
    sleep(1);
}
```
Executando o Script
---
Para executar o script K6, use o seguinte comando:
```
$ docker-compose run k6 run /scripts/test_script.js
````

Monitoramento com Grafana
---
Acesse http://localhost:3000 no navegador.
Use o usuário e senha definidos no arquivo .env.

Visualizar Dashboards
---
Navegue pelos dashboards disponíveis para monitorar os resultados dos testes de performance.
Conclusão