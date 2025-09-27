FROM codercom/code-server:latest

USER root

ARG USER_UID=1000
ARG USER_GID=1000

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        zsh \
        python3 \
        python3-pip \
        python3-venv \
        curl \
        ca-certificates \
        fonts-powerline \
    && rm -rf /var/lib/apt/lists/*

ENV UV_INSTALL_DIR=/usr/local
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

RUN if getent group ${USER_GID} >/dev/null; then \
        usermod -g ${USER_GID} coder; \
    else \
        groupmod -g ${USER_GID} coder; \
    fi \
    && usermod -u ${USER_UID} coder \
    && usermod --shell /usr/bin/zsh coder \
    && chown -R ${USER_UID}:${USER_GID} /home/coder

ENV PATH="/usr/local/bin:/home/coder/.local/bin:${PATH}"

USER coder
WORKDIR /home/coder
