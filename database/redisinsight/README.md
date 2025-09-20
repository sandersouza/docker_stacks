![Redis stack](banner.png)
# Redis + RedisInsight

Experimente workloads de escrita no Redis e visualize chaves/estruturas usando o RedisInsight.

## Serviços
| Serviço | Porta | Descrição |
|---------|-------|-----------|
| Redis   | 6385  | Instância Redis com `requirepass` definido em `redis.conf` |
| RedisInsight | 5540 | Interface GUI oficial para gerenciamento e análise |

Credenciais padrão:
- Redis: senha `7zEzcCJGDnZFxiIp8z` (definida em `redis.conf`).
- RedisInsight: configure a conexão manualmente apontando para `localhost:6385` + senha acima.

## Subindo a stack
```bash
# a partir de database/redisinsight/
docker compose up -d
```
Volumes Docker mantêm os dados mesmo após `down`. Para reiniciar, derrube os containers e remova o volume `cache` (`docker compose down -v`).

## Script de carga
1. Crie/prepare o virtualenv:
   ```bash
   ./virtualenv.sh create
   source venv/bin/activate
   ```
2. Ajuste `num_records` em `insert.py` se quiser controlar o volume (default `10000`).
3. Execute o script:
   ```bash
   ./insert.py
   deactivate
   ```

Cada execução popula a hash `operation-results-table` com chaves `results::<timestamp>_<index>` e payload JSON aleatório.

## Encerrando
```bash
docker compose down          # mantém dados
# docker compose down -v     # remove o volume "cache"
```
Para limpeza manual, você também pode abrir o RedisInsight e excluir a hash criada.
