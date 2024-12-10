![Descrição da Imagem](banner.png)
# MongoDB & Mongo Express 🛠️

Esta stack inclui **MongoDB**, um banco de dados NoSQL altamente escalável e popular, perfeito para armazenar dados em formato JSON-like, e **Mongo Express**, uma interface web leve para gerenciar suas coleções diretamente do navegador. Todos os comandos devem ser executados na raiz do diretório da stack.

```sh
# Criar a stack
# ---
$ docker-compose up -d
```
```sh
# Destruir a stack
# ---
$ docker-compose down
```
```sh
# Montar venv e executar script de carga & stress de dados
# na linha 47 do script insert.py, você poderá definir a quantidade de registros a inserir
# ---
$ ./setup-env.sh
$ source venv/bin/activate
$ ./insert.py
$ deactive
```

**Obs:** O virtualenv, só precisa ser criado 1 vez, se ele já existir, basta ativá-lo ( ___source venv/bin/activate___ ), executar o script ( ___./insert.py___ ) e desativa-lo ( ___deactive___ )


🔔 **Atenção**: O Mongo Express é ótimo para ambientes de teste e desenvolvimento, mas não é recomendado para produção devido a limitações de segurança. Use-o com cuidado!