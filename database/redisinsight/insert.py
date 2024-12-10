#!./venv/bin/python3
import redis
import random
import json
from datetime import datetime, timedelta

# Conexão com o Redis
client = redis.StrictRedis(
    host='localhost',
    port=6385,
    password='7zEzcCJGDnZFxiIp8z',
    decode_responses=True  # Para retornar strings em vez de bytes
)

# Verificar conexão com Redis
try:
    client.ping()
    print("Conectado ao Redis com sucesso.")
except redis.exceptions.ConnectionError as e:
    print(f"Erro ao conectar ao Redis: {e}")
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

# Inserindo registros aleatórios no Redis
for i in range(num_records):
    # Gerando timestamp e JSON
    timestamp, value = generate_random_data()
    
    # Criando o campo "Field" no formato especificado
    field = f"results::{timestamp}_{i}"
    
    # Convertendo o JSON para string
    value_str = json.dumps(value)
    
    # Inserindo no Redis
    client.hset("operation-results-table", field, value_str)

    print(f"Adicionado: Field='{field}', Value='{value_str}'")

print(f"{num_records} registros adicionados à hash 'operation-results-table'.")