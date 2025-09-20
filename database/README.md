<img src="banner.png" alt="Stacks de banco de dados" style="width:100%;">

## Database Stacks
Coleção de ambientes prontos para comparar operações de escrita/leitura em diferentes engines. Cada stack possui scripts para
popular dados sintéticos e medir throughput.

### Stacks disponíveis
- [`mongodb`](mongodb/README.md): MongoDB 4.4 + Mongo Express com scripts síncronos e assíncronos de carga.
- [`mysql`](mysql/README.md): MySQL 8 + Adminer, com scripts para inserções em batch e limpeza da tabela.
- [`redisinsight`](redisinsight/README.md): Redis + RedisInsight com script para gerar hashes com payload JSON.

### Como começar
1. Entre no diretório da stack desejada.
2. Copie ou ajuste o arquivo `.env` quando existir.
3. Suba os containers com `docker compose up -d`.
4. Utilize os scripts Python fornecidos (ativando o virtualenv via `./virtualenv.sh create`).

Cada stack descreve credenciais, portas expostas e como controlar o volume de dados gerados. Lembre-se de sempre executar os
comandos a partir da pasta da stack correspondente.
