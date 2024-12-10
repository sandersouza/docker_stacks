#!./venv/bin/python3
from concurrent.futures import ThreadPoolExecutor
import mysql.connector
from datetime import datetime, timedelta
import random

# Função para criar uma conexão com o MySQL
def create_connection():
    return mysql.connector.connect(
        host="localhost",
        user="user",
        password="user123",
        database="testdb"
    )

# Função para gerar um batch de dados
def generate_batch(batch_size):
    batch = []
    for _ in range(batch_size):
        random_time = datetime.now() + timedelta(seconds=random.randint(0, 1000))
        timestamp = random_time.strftime("%Y-%m-%d %H:%M:%S.%f")  # Timestamp com microsegundos
        batch.append((random.choice([True, False]), random.choice([True, False]), timestamp))
    return batch

# Função para inserir um batch no MySQL
def insert_batch(batch):
    connection = create_connection()
    cursor = connection.cursor()
    query = """
    INSERT INTO operation_results (is_success, is_technical_error, timestamp_field)
    VALUES (%s, %s, %s)
    """
    try:
        cursor.executemany(query, batch)
        connection.commit()
        print(f"Batch de {len(batch)} registros inserido com sucesso.")
    except mysql.connector.Error as e:
        print(f"Erro ao inserir batch: {e}")
        connection.rollback()
    finally:
        cursor.close()
        connection.close()

# Configurações
num_records = 10000  # Número total de registros
batch_size = 1000    # Tamanho de cada batch
num_threads = 4      # Número de threads para inserções paralelas

# Gerar os batches
batches = [generate_batch(batch_size) for _ in range(num_records // batch_size)]

# Inserir os dados em paralelo usando ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=num_threads) as executor:
    executor.map(insert_batch, batches)

print(f"{num_records} registros inseridos com sucesso.")
