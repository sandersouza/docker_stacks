#!/bin/bash

arg=$1
DIRECTORY="."  # Diretório padrão é o atual
VENV_DIR="venv"
REQUIREMENTS_FILE="requirements.txt"

if ! command -v python3 &> /dev/null; then
    echo "Python 3 não está instalado. Por favor, instale antes de continuar."
    exit 1
fi

# Processa argumentos adicionais
while [[ $# -gt 0 ]]; do
    case "$1" in
        -d)
            DIRECTORY="$2"
            shift 2
            ;;
        create|cleanup|--help|-h)
            arg="$1"
            shift
            ;;
        *)
            echo "Opção inválida: $1"
            show_help
            exit 1
            ;;
    esac
done

# Ajusta o VENV_DIR e REQUIREMENTS_FILE com base no diretório especificado
VENV_DIR="$DIRECTORY/venv"
REQUIREMENTS_FILE="$DIRECTORY/requirements.txt"

function cleanup() {
    if [[ ! -d "$VENV_DIR" ]]; then
        echo "Não há ambiente virtual no diretório especificado."
        return
    fi

    echo "Preparando desativação e apagamento do ambiente virtual Python."
    
    env_status=$(which deactivate | grep "deactivate ()")
    if [[ -n "$env_status" ]]; then
        echo "Ambiente virtual ativo. Desativando..."
        deactivate
        echo "ok."
    else
        echo "Ambiente virtual já está inativo."
    fi

    echo -n "Apagando ambiente virtual..."
    rm -Rf "$VENV_DIR"
    echo "ok."

    echo -n "Limpando os caches do Python no diretório $DIRECTORY..."
    find "$DIRECTORY" -type d -name "__pycache__" -depth -exec rm -r {} +
    echo "ok."
    echo "Limpeza concluída!"
}

function create() {
    if [[ ! -f "$REQUIREMENTS_FILE" ]]; then
        echo "Arquivo requirements.txt não encontrado no diretório especificado!"
        exit 1
    fi

    # Cria ambiente virtual
    if [[ ! -d "$VENV_DIR" ]]; then
        echo -n "Criando ambiente virtual em $VENV_DIR..."
        python3 -m venv "$VENV_DIR"
        echo "ok."
    fi

    echo -n "Ativando ambiente virtual..."
    source "$VENV_DIR/bin/activate"
    echo "ok."

    # Instala as dependências
    pip freeze | grep -f "$REQUIREMENTS_FILE" >/dev/null 2>&1
    if [[ $? -ne 0 ]]; then
        echo -n "Instalando dependências do $REQUIREMENTS_FILE..."
        pip install --upgrade pip > /dev/null 2>&1
        pip install -r "$REQUIREMENTS_FILE" -q
        echo "ok."
    else
        echo "Todas as dependências já estão instaladas."
    fi

    echo -n "Verificando dependências..."
    source "$VENV_DIR/bin/activate"
    echo "ok."

    deactivate
    echo -e "Configuração concluída!\n"
    echo -e "Para ativar o ambiente, use 'source $VENV_DIR/bin/activate'."
}

show_help() {
    echo -e "\nUso: $0 [ create | cleanup ] [-d <diretório>]"
    echo -e "\nOpções:"
    echo -e "  -h, --help      Mostra esta ajuda"
    echo -e "  -d <diretório>  Especifica o diretório do ambiente virtual"
    echo -e "  create          Cria o ambiente virtual e instala as dependências (ver requirements.txt)"
    echo -e "  cleanup         Limpa o ambiente virtual e caches"
}

case "$arg" in
    create)
        create
        ;;
    cleanup)
        cleanup
        ;;
    --help|-h)
        show_help
        exit 0
        ;;
    *)
        if [ -z "$arg" ]; then
            echo "Não há opção selecionada."
            show_help
        else
            echo "Opção inválida: $arg"
            show_help
        fi
        exit 1
        ;;
esac