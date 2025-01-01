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
            if [[ ! -d "$DIRECTORY" ]]; then
                echo "Erro: O diretório especificado ($DIRECTORY) não existe."
                exit 1
            fi
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
        echo "Não há ambiente virtual no diretório especificado ($DIRECTORY)."
        return
    fi

    echo "Preparando para desativar e apagar o ambiente virtual Python ($VENV_DIR)."
    
    if [[ -n "$VIRTUAL_ENV" && "$VIRTUAL_ENV" == "$(realpath "$VENV_DIR")" ]]; then
        echo "Ambiente virtual ativo. Desativando..."
        deactivate
    else
        echo "Ambiente virtual já está inativo."
    fi

    echo "Apagando o ambiente virtual..."
    rm -rf "$VENV_DIR"
    echo "Ambiente virtual removido."

    echo "Limpando os caches do Python no diretório $DIRECTORY..."
    find "$DIRECTORY" -type d -name "__pycache__" -exec rm -rf {} +
    echo "Caches removidos."
    echo "Limpeza concluída!"
}

function create() {
    if [[ ! -f "$REQUIREMENTS_FILE" ]]; then
        echo "Arquivo requirements.txt não encontrado no diretório especificado ($DIRECTORY)."
        exit 1
    fi

    if [[ ! -d "$VENV_DIR" ]]; then
        echo "Criando ambiente virtual em $VENV_DIR..."
        python3 -m venv "$VENV_DIR"
        echo "Ambiente virtual criado."
    else
        echo "Ambiente virtual já existe em $VENV_DIR."
    fi

    echo "Ativando o ambiente virtual..."
    source "$VENV_DIR/bin/activate"

    echo "Instalando dependências do $REQUIREMENTS_FILE..."
    pip install --upgrade pip > /dev/null
    pip install -r "$REQUIREMENTS_FILE"
    echo "Dependências instaladas."

    deactivate
    echo -e "Configuração concluída!\nPara ativar o ambiente, use:\n  source $VENV_DIR/bin/activate"
}

function show_help() {
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
        if [[ -z "$arg" ]]; then
            echo "Nenhuma opção selecionada."
            show_help
        else
            echo "Opção inválida: $arg"
            show_help
        fi
        exit 1
        ;;
esac
