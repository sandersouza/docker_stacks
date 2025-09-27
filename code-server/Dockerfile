FROM codercom/code-server:latest

USER root

ARG USER_NAME=coder
ARG USER_UID=1000
ARG USER_GID=1000

ENV USER_NAME=${USER_NAME} \
    USER_HOME=/home/${USER_NAME} \
    USER=${USER_NAME} \
    HOME=/home/${USER_NAME}

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

RUN set -eux; \
    DEFAULT_HOME="$(getent passwd coder | cut -d: -f6)"; \
    if getent group "${USER_GID}" >/dev/null; then \
        TARGET_GROUP="$(getent group "${USER_GID}" | cut -d: -f1)"; \
        if [ "${TARGET_GROUP}" != "${USER_NAME}" ]; then \
            groupmod -n "${USER_NAME}" "${TARGET_GROUP}"; \
        fi; \
    elif getent group "${USER_NAME}" >/dev/null; then \
        groupmod -g "${USER_GID}" "${USER_NAME}"; \
    else \
        groupadd -g "${USER_GID}" "${USER_NAME}"; \
    fi; \
    usermod -u "${USER_UID}" coder; \
    usermod -g "${USER_GID}" coder; \
    if [ "${USER_NAME}" != "coder" ]; then \
        usermod -l "${USER_NAME}" coder; \
        if [ -f /etc/sudoers.d/nopasswd ]; then \
            sed -i "s/^coder /${USER_NAME} /" /etc/sudoers.d/nopasswd; \
        fi; \
    fi; \
    usermod --shell /usr/bin/zsh "${USER_NAME}"; \
    if [ "${DEFAULT_HOME}" != "${USER_HOME}" ]; then \
        if [ -d "${USER_HOME}" ]; then \
            cp -aT "${DEFAULT_HOME}" "${USER_HOME}"; \
            rm -rf "${DEFAULT_HOME}"; \
        else \
            mv "${DEFAULT_HOME}" "${USER_HOME}"; \
        fi; \
    fi; \
    mkdir -p "${USER_HOME}/.local/share"; \
    usermod -d "${USER_HOME}" "${USER_NAME}"; \
    chown -R "${USER_UID}:${USER_GID}" "${USER_HOME}"; \
    ln -sfn "${USER_HOME}" /home/coder; \
    printf "user: %s\\ngroup: %s\\n" "${USER_NAME}" "${USER_NAME}" > /etc/fixuid/config.yml

ENV PATH="/usr/local/bin:${USER_HOME}/.local/bin:${PATH}"

USER ${USER_NAME}
WORKDIR ${USER_HOME}
