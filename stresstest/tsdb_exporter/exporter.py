#!./venv/bin/python3
import json
import sys
import requests
import argparse

# Configuração do InfluxDB
INFLUXDB_URL = "http://localhost:8086/write"
INFLUXDB_DB = "metrics"
INFLUXDB_USER = "admin"
INFLUXDB_PASSWORD = "senha123"

def sanitize_value(value):
    """ Formata valores para serem aceitos pelo InfluxDB """
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        # Substitui valores booleanos no formato string
        if value.lower() == "true":
            return "1"
        elif value.lower() == "false":
            return "0"
        # Retorna valores textuais escapados
        return f'"{value}"'
    return f'"{str(value)}"'

def process_json(json_input, label=None):
    try:
        # Parse JSON input
        data = json.loads(json_input)

        # Converter métricas para o formato de linha do InfluxDB com ou sem labels
        influx_data = []
        for key, value in data.items():
            if isinstance(value, (int, float)):
                # Numérico, usa campo padrão "value"
                field_name = "value"
                sanitized_value = value
            else:
                # Não numérico, cria campo "value_text"
                field_name = "value_text"
                sanitized_value = f'"{value}"'

            if label:
                influx_line = f"{key},label={label} {field_name}={sanitized_value}"
            else:
                influx_line = f"{key} {field_name}={sanitized_value}"
            influx_data.append(influx_line)

        if not influx_data:
            print("No valid metrics to send.", file=sys.stderr)
            sys.exit(1)

        # Enviar métricas para o InfluxDB
        influx_payload = "\n".join(influx_data)
        response = requests.post(
            f"{INFLUXDB_URL}?db={INFLUXDB_DB}",
            auth=(INFLUXDB_USER, INFLUXDB_PASSWORD),
            data=influx_payload,
            headers={"Content-Type": "text/plain"},
        )

        if response.status_code == 204:
            print("Metrics successfully written to InfluxDB")
        else:
            print(f"Failed to write metrics to InfluxDB: {response.status_code}, {response.text}", file=sys.stderr)

    except Exception as e:
        print(f"Error processing JSON: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    # Configurar parser de argumentos
    parser = argparse.ArgumentParser(description="Process JSON metrics and write to InfluxDB.")
    parser.add_argument(
        "--label",
        type=str,
        required=False,
        help="Optional label to be added to the metrics (e.g., environment=production)."
    )
    args = parser.parse_args()

    # Verificar entrada via PIPE
    if not sys.stdin.isatty():
        json_input = sys.stdin.read().strip()
        process_json(json_input, args.label)
    else:
        print("No input provided. Use as: curl ... | ./exporter.py [--label <label>]", file=sys.stderr)
        sys.exit(1)
