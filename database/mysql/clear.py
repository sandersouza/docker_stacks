#!./venv/bin/python3
import mysql.connector

# Conexão com o MySQL
try:
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="senha123",
        database="testdb"
    )
    cursor = connection.cursor()
    print("Conectado ao MySQL com sucesso.")
except mysql.connector.Error as e:
    print(f"Erro ao conectar ao MySQL: {e}")
    exit(1)

try:
    # Deletar todos os registros de uma só vez
    cursor.execute("DELETE FROM operation_results;")
    print("Todos os registros foram apagados da tabela 'operation_results'.")

    # Reiniciar a chave primária (AUTO_INCREMENT)
    cursor.execute("ALTER TABLE operation_results AUTO_INCREMENT = 1;")
    print("A chave primária foi reiniciada.")

    # Commit para garantir as alterações
    connection.commit()

except mysql.connector.Error as e:
    print(f"Erro durante a limpeza: {e}")
    connection.rollback()
finally:
    # Fechar conexão
    cursor.close()
    connection.close()
    print("Conexão com o MySQL encerrada.")
