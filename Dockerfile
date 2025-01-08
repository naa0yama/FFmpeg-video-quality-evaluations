#- -------------------------------------------------------------------------------------------------
#- Runner
#-
FROM ghcr.io/naa0yama/join_logo_scp_trial:v25.01.0500-beta4-ubuntu2404

ARG DEBIAN_FRONTEND=noninteractive \
    DEFAULT_USERNAME=user \
    \
    ASDF_VERSION="v0.14.1" \
    POETRY_VERSION="1.8.2"

SHELL ["/bin/bash", "-c"]
RUN mkdir -p /app

# Script dep
RUN set -eux && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    bash \
    binutils \
    ca-certificates \
    curl \
    fish \
    git \
    gpg-agent \
    jq \
    nano \
    openssh-client \
    software-properties-common \
    sudo \
    tzdata \
    vainfo \
    wget && \
    \
    # Cleanup \
    apt -y autoremove && \
    apt -y clean && \
    rm -rf /var/lib/apt/lists/*

# Create user
RUN set -eux && \
    groupadd --gid 1001 vscode && \
    useradd -s /bin/bash --uid 1001 --gid 1001 -m vscode && \
    echo vscode:password | chpasswd && \
    passwd -d vscode && \
    echo -e "vscode\tALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/vscode

COPY --chown=vscode --chmod=644 .tool-versions /home/vscode/.tool-versions

# Install asdf
USER vscode
RUN set -eux && \
    git clone https://github.com/asdf-vm/asdf.git ~/.asdf \
    --depth 1 --branch ${ASDF_VERSION} && \
    mkdir -p ~/.config/fish && \
    echo "source ~/.asdf/asdf.fish" > ~/.config/fish/config.fish && \
    echo ". \"\$HOME/.asdf/asdf.sh\"" >> ~/.bashrc && \
    echo ". \"\$HOME/.asdf/completions/asdf.bash\"" >> ~/.bashrc

# asdf update
RUN set -eux && \
    source $HOME/.asdf/asdf.sh && \
    asdf update

# Dependencies Python
USER root
RUN set -eux && \
    apt-get -y update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libbz2-dev \
    libffi-dev \
    liblzma-dev \
    libncursesw5-dev \
    libreadline-dev \
    libsqlite3-dev \
    libssl-dev \
    libxml2-dev \
    libxmlsec1-dev \
    tk-dev \
    xz-utils \
    zlib1g-dev && \
    \
    # Cleanup \
    apt-get -y autoremove && \
    apt-get -y clean && \
    rm -rf /var/lib/apt/lists/*

# asdf install plugin python
USER vscode
RUN set -eux && \
    source $HOME/.asdf/asdf.sh && \
    asdf plugin-add python

# asdf install plugin poetry
RUN set -eux && \
    source $HOME/.asdf/asdf.sh && \
    asdf plugin-add poetry

# plugin install
RUN set -eux && \
    source $HOME/.asdf/asdf.sh && \
    asdf install python && \
    asdf install

### Scripts
COPY tools/ffmpeg-vqe/pyproject.toml                 /app
COPY tools/ffmpeg-vqe/poetry.lock                    /app
WORKDIR                                              /app

COPY tools/ffmpeg-vqe/src/ffmpegvqe/entrypoint.py    /app/entrypoint.py
COPY tools/ffmpeg-vqe/plotbitrate.sh                 /app/plotbitrate.sh

RUN set -eux && \
    source $HOME/.asdf/asdf.sh && \
    type poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --only=main -C /app

ENTRYPOINT [ "/bin/bash", "-c" ]
CMD [ "" ]
