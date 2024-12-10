#!/bin/bash
# Substitui as variáveis de ambiente no datasources.yaml
envsubst < /etc/grafana/provisioning/datasources/datasources.template > /etc/grafana/provisioning/datasources/datasources.yaml

# Continua para o comando original do Grafana
exec /run.sh "$@"