#!./venv/bin/python3
from pymongo import MongoClient
import random
import json
from datetime import datetime, timedelta

# Conexão com o MongoDB
client = MongoClient("mongodb://root:senha123@localhost:27017/")
db = client["operation-results-table"]
collection = db["operation_results_table"]

# Verificar conexão com MongoDB
try:
    client.admin.command("ping")
    print("Conectado ao MongoDB com sucesso.")
except Exception as e:
    print(f"Erro ao conectar ao MongoDB: {e}")
    exit(1)

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

# Número de registros aleatórios a serem adicionados
num_records = 10000

# Inserindo registros aleatórios no MongoDB
for i in range(num_records):
    # Gerando timestamp e JSON
    timestamp, value = generate_random_data()
    
    # Criando o campo "Field" no formato especificado
    field = f"results::{timestamp}_{i}"
    
    # Documento para inserir no MongoDB
    document = {
        "field": field,
        "value": value
    }
    
    # Inserindo no MongoDB
    collection.insert_one(document)

    print(f"Adicionado: Field='{field}', Value='{json.dumps(value)}'")

print(f"{num_records} registros adicionados à coleção 'operation_results_table'.")
