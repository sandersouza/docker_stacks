#!/bin/bash
VENV_DIR="venv"
REQUIREMENTS_FILE="requirements.txt"

if [[ ! -f "$REQUIREMENTS_FILE" ]]; then
    echo "Arquivo requirements.txt não encontrado!"
    exit 1
fi

function setup_venv() {
    if [[ ! -d "$VENV_DIR" ]]; then
        echo "Criando ambiente virtual..."
        python3 -m venv "$VENV_DIR"
        echo "Ambiente virtual criado em $VENV_DIR."
    fi

    echo "Ativando ambiente virtual..."
    source "$VENV_DIR/bin/activate"
}

function install_requirements() {
    echo "Instalando dependências do $REQUIREMENTS_FILE..."
    pip install --upgrade pip
    pip install -r "$REQUIREMENTS_FILE"
    echo "Dependências instaladas."
}

setup_venv

echo "Verificando dependências..."
source "$VENV_DIR/bin/activate"

pip freeze | grep -f "$REQUIREMENTS_FILE" >/dev/null 2>&1
if [[ $? -ne 0 ]]; then
    install_requirements
else
    echo "Todas as dependências já estão instaladas."
fi

deactivate
echo "Configuração concluída!"
