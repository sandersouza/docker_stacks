#!/bin/zsh

install_golang() {
    if ! command -v go &>/dev/null; then
        echo "fzf não está instalado. Detectando sistema operacional..."
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            echo "Sistema operacional detectado: Linux"
            if command -v apt &>/dev/null; then
                echo "Gerenciador de pacotes: apt"
                sudo apt update
                sudo apt install -y golang
            elif command -v yum &>/dev/null; then
                echo "Gerenciador de pacotes: yum"
                sudo yum install -y golang
            elif command -v dnf &>/dev/null; then
                echo "Gerenciador de pacotes: dnf"
                sudo dnf install -y golang
            elif command -v pacman &>/dev/null; then
                echo "Gerenciador de pacotes: pacman"
                sudo pacman -Syu --noconfirm go
            else
                echo "Gerenciador de pacotes não suportado. Instale manualmente o Go Lang."
                return 1
            fi
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            echo "Sistema operacional detectado: macOS"
            if command -v brew &>/dev/null; then
                echo "Gerenciador de pacotes: Homebrew"
                brew install go
            else
                echo "Homebrew não está instalado. Instale-o primeiro: https://brew.sh/"
                return 1
            fi
        else
            echo "Sistema operacional não suportado. Instale o Go Lang manualmente: https://go.dev/doc/install"
            return 1
        fi

        # Verifica a instalação do Go
        if command -v go &>/dev/null; then
            echo "Go Lang instalado com sucesso!"
            go version
        else
            echo "Falha ao instalar o Go Lang. Verifique os erros acima."
            return 1
        fi
    fi
}

install_fzf() {
    if ! command -v fzf &>/dev/null; then
        echo "fzf não está instalado. Detectando sistema operacional..."

        # Detecta o sistema operacional e gerenciador de pacotes
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            if command -v apt &>/dev/null; then
                echo "Instalando fzf com apt..."
                sudo apt update && sudo apt install -y fzf
            elif command -v yum &>/dev/null; then
                echo "Instalando fzf com yum..."
                sudo yum install -y fzf
            elif command -v dnf &>/dev/null; then
                echo "Instalando fzf com dnf..."
                sudo dnf install -y fzf
            elif command -v pacman &>/dev/null; then
                echo "Instalando fzf com pacman..."
                sudo pacman -Syu --noconfirm fzf
            else
                echo "Gerenciador de pacotes não suportado. Instale o fzf manualmente."
                exit 1
            fi
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            if command -v brew &>/dev/null; then
                echo "Instalando fzf com Homebrew..."
                brew install fzf
            else
                echo "Homebrew não está instalado. Instale o Homebrew primeiro: https://brew.sh/"
                exit 1
            fi
        else
            echo "Sistema operacional não suportado. Instale o fzf manualmente."
            exit 1
        fi

        echo "fzf instalado com sucesso."
    fi
}

install_k6() {
    if [[ ! -f "./k6" ]]; then
        echo "Executável do k6 não encontrado. Iniciando o processo de compilação..."

        # Verifica se o Go está instalado
        if ! command -v go &>/dev/null; then
            echo "Go não está instalado. Instale o Go Lang antes de continuar."
            return 1
        fi

        # Instala o xk6 se necessário
        if ! command -v xk6 &>/dev/null; then
            echo "Instalando o xk6..."
            go install go.k6.io/xk6/cmd/xk6@latest || {
                echo "Falha ao instalar o xk6. Verifique sua instalação do Go."
                return 1
            }
            echo "xk6 instalado com sucesso."
        fi

        # Compila o k6 com a extensão xk6-exec
        echo "Compilando o k6 com a extensão xk6-exec..."
        xk6 build --with github.com/grafana/xk6-exec@latest || {
            echo "Falha ao compilar o k6 com a extensão xk6-exec."
            return 1
        }

        echo "k6 compilado com sucesso e disponível como ./k6."
    fi
}

# Verifica e instala as dependências se ouverem
install_golang
install_fzf
install_k6

# Resto do script
clear
export FZF_DEFAULT_OPTS='--layout=reverse --border --preview-window=80% --info=inline --prompt="Navigate: "'

# Navegar entre diretórios
current_dir="./scripts"
while true; do
    # Adiciona .. para voltar ao diretório anterior e garante que diretórios venham primeiro
    items=$(find "$current_dir" -mindepth 1 -maxdepth 1 | sed "s|^$current_dir/||")
    directories=$(find "$current_dir" -type d -mindepth 1 -maxdepth 1 | sed "s|^$current_dir/||" | xargs -n1 -I{} sh -c 'echo "\033[1;31m{}\033[0m"')
    files=$(find "$current_dir" -type f -mindepth 1 -maxdepth 1 | sed "s|^$current_dir/||" | sort)

    if [ -z "$directories" ]; then
        items="..\n$files"
    else
        items="..\n$directories\n$files"
    fi

    selected_item=$(echo "$items" | fzf --ansi --preview="[ -f $current_dir/{} ] && cat $current_dir/{} || ls -1 $current_dir/{}" --prompt="Select an item: "  --tmux 80% --border)

    if [[ -z "$selected_item" ]]; then
        echo "No selection made. Exiting."
        exit 0
    fi

    selected_item=$(echo "$selected_item" | sed 's|^D ||') # Remove prefixo de diretório

    if [[ "$selected_item" == ".." ]]; then
        current_dir=$(dirname "$current_dir")
    elif [[ -d "$current_dir/$selected_item" ]]; then
        current_dir="$current_dir/$selected_item"
    elif [[ "$selected_item" == *.js ]]; then
        response=$(echo -e "Yes\nNo" | fzf --prompt="Do you want to execute $selected_item with K6? " --layout=reverse --border --tmux center,50%,50% --info=inline)

        if [[ "$response" == "Yes" ]]; then
            echo "Executing $selected_item with K6..."
            ./k6 run "$current_dir/$selected_item" --out experimental-prometheus-rw=http://localhost:9090/api/v1/write
        else
            echo "Execution canceled."
        fi
    else
        echo "Invalid selection."
    fi
done
