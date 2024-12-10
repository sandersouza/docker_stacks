#!./venv/bin/python3
import random
import json
from datetime import datetime, timedelta
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

# Configuração de conexão com o MongoDB
MONGO_URI = "mongodb://root:senha123@localhost:27017/"
DATABASE_NAME = "operation-results-table"
COLLECTION_NAME = "operation_results_table"

# Função para gerar dados aleatórios
def generate_random_data():
    # Gerando um timestamp aleatório
    random_time = datetime.now() + timedelta(seconds=random.randint(0, 1000))
    timestamp = random_time.isoformat()

    # Estrutura do JSON para o campo "Value"
    value = {
        "isSuccess": random.choice([True, False]),
        "isTechnicalError": random.choice([True, False]),
        "timestamp": {
            "date": {
                "year": random_time.year,
                "month": random_time.month,
                "day": random_time.day
            },
            "time": {
                "hour": random_time.hour,
                "minute": random_time.minute,
                "second": random_time.second,
                "nano": random_time.microsecond * 1000  # Nano é microsegundos * 1000
            }
        }
    }
    return timestamp, value

# Função para inserir registros no MongoDB
async def insert_records(num_records):
    # Conectando ao MongoDB
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection = db[COLLECTION_NAME]

    # Verificar conexão com o MongoDB
    try:
        await client.admin.command("ping")
        print("Conectado ao MongoDB com sucesso.")
    except Exception as e:
        print(f"Erro ao conectar ao MongoDB: {e}")
        return

    # Lista de documentos para inserção
    documents = []

    for i in range(num_records):
        # Gerar timestamp e JSON
        timestamp, value = generate_random_data()

        # Criar o campo "Field" no formato especificado
        field = f"results::{timestamp}_{i}"

        # Documento a ser inserido
        document = {
            "field": field,
            "value": value
        }

        documents.append(document)

        # Exibe progresso a cada 1000 registros
        if len(documents) % 1000 == 0:
            print(f"Preparados {len(documents)} documentos para inserção...")

    # Inserir todos os documentos em lote
    try:
        result = await collection.insert_many(documents)
        print(f"{len(result.inserted_ids)} registros adicionados à coleção '{COLLECTION_NAME}'.")
    except Exception as e:
        print(f"Erro ao inserir documentos: {e}")
    finally:
        client.close()

# Função principal para executar o script
async def main():
    num_records = 10000  # Defina o número de registros a serem adicionados
    await insert_records(num_records)

# Executar o script
if __name__ == "__main__":
    asyncio.run(main())
