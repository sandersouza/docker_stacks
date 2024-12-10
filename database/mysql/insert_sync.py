#!./venv/bin/python3
import mysql.connector
import random
import json
from datetime import datetime, timedelta

# Conexão com o MySQL
try:
    connection = mysql.connector.connect(
        host="localhost",
        user="user",
        password="user123",
        database="testdb"
    )
    cursor = connection.cursor()
    print("Conectado ao MySQL com sucesso.")
except mysql.connector.Error as e:
    print(f"Erro ao conectar ao MySQL: {e}")
    exit(1)

# Função para gerar dados aleatórios
def generate_random_data():
    # Gerando um timestamp aleatório
    random_time = datetime.now() + timedelta(seconds=random.randint(0, 1000))
    timestamp = random_time.strftime("%Y-%m-%d %H:%M:%S.%f")  # Timestamp com microsegundos

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

# Inserindo registros aleatórios no MySQL
try:
    for i in range(num_records):
        # Gerando timestamp e JSON
        timestamp, value = generate_random_data()

        # Documento a ser inserido
        is_success = value["isSuccess"]
        is_technical_error = value["isTechnicalError"]

        # Query de inserção
        query = """
        INSERT INTO operation_results (is_success, is_technical_error, timestamp_field)
        VALUES (%s, %s, %s)
        """
        cursor.execute(query, (is_success, is_technical_error, timestamp))

        # Log do progresso
        if i % 100 == 0:  # Log a cada 100 registros
            print(f"{i} registros inseridos.")

    # Commit das alterações no banco
    connection.commit()
    print(f"{num_records} registros adicionados à tabela 'operation_results'.")

except mysql.connector.Error as e:
    print(f"Erro ao inserir dados no MySQL: {e}")
finally:
    # Fechando conexão com o banco
    cursor.close()
    connection.close()
