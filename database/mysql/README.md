# MySQL + Adminer

Stack para avaliar operações de escrita no MySQL 8 utilizando scripts Python síncronos e em batch. Inclui o Adminer como UI
minimalista para inspeção.

## Serviços
| Serviço | Porta | Descrição |
|---------|-------|-----------|
| mysql_db | 3306 | Instância MySQL com dados persistidos em `db/data` |
| adminer_ui | 8080 | Interface web para administração (login usando as credenciais do `.env`) |

Credenciais padrão (`.env`):
- `MYSQL_ROOT_PASSWORD=senha123`
- `MYSQL_DATABASE=testdb`
- `MYSQL_USER=user`
- `MYSQL_PASSWORD=user123`

## Preparando o ambiente
```bash
# dentro de database/mysql/
docker compose up -d
```
> Se quiser personalizar as variáveis, copie `.env` para `.env.local`, ajuste e execute `docker compose --env-file .env.local up -d`.
A stack cria automaticamente a tabela `operation_results` definida em `db/schema.sql`.

## Scripts de teste
1. Crie o virtualenv e instale dependências:
   ```bash
   ./virtualenv.sh create
   source venv/bin/activate
   ```
2. Escolha um fluxo:
   - `insert_sync.py`: inserções linha a linha (`num_records = 10000`).
   - `insert_async.py`: gera batches e insere em paralelo via `ThreadPoolExecutor` (ajuste `batch_size`, `num_threads`).
   - `clear.py`: remove todos os registros e reseta o `AUTO_INCREMENT`.

   Ajuste as variáveis no topo dos scripts conforme necessário e execute:
   ```bash
   ./insert_async.py      # ou ./insert_sync.py / ./clear.py
   deactivate
   ```

## Finalizando
```bash
docker compose down            # mantém os dados em db/data
# docker compose down -v       # remove a base e o volume persistente
```
Use o Adminer (http://localhost:8080) para inspecionar resultados ou exportar dados após os testes.
