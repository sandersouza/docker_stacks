![MongoDB stack](banner.png)
# MongoDB + Mongo Express

Stack para testar inserções síncronas/assíncronas no MongoDB 4.4 com visualização via Mongo Express.

## Serviços e portas
| Serviço | Porta | Descrição |
|---------|-------|-----------|
| mongodb | 27017 | Banco de dados com volumes persistentes em `mongo/data` |
| mongodb-express | 8081 | UI web para navegação básica e operações CRUD |

Credenciais default (`.env`): `root` / `senha123`.

## Subindo o ambiente
```bash
# dentro de database/mongodb/
docker compose up -d
```
> Copie `.env` para `.env.local` se quiser personalizar credenciais antes de subir (`docker compose --env-file .env.local up -d`). Caso altere portas ou usuário/senha, lembre-se de ajustar também os scripts Python.

## Scripts de carga
1. Prepare o ambiente virtual (somente na primeira vez):
   ```bash
   ./virtualenv.sh create
   source venv/bin/activate
   ```
2. Escolha um script de carga:
   - `insert_sync.py`: inserções sequenciais (`num_records = 10000`).
   - `insert_async.py`: usa `motor` para inserir em lote de forma assíncrona.

   Edite a variável `num_records` conforme necessário antes de executar.

3. Execute o script desejado:
   ```bash
   ./insert_sync.py      # ou ./insert_async.py
   deactivate
   ```

Os scripts geram documentos no formato `field: results::<timestamp>_<index>` com payload JSON aleatório.

## Limpeza e encerramento
```bash
docker compose down              # mantém volumes
# docker compose down -v         # remove dados persistidos
```
Volumetria fica em `mongo/data` e `mongo/config`; você pode apagá-los manualmente se quiser começar do zero.
