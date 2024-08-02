#- -------------------------------------------------------------------------------------------------
#- Runner
#-
FROM ghcr.io/naa0yama/docker-mirakurun-epgstation/epgstation:9569e00

ARG POETRY_VERSION=1.8.2

SHELL ["/bin/bash", "-c"]

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
    python3 \
    python3-pip \
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

# Add Biome latest install
RUN set -eux && \
    curl -fSL -o /usr/local/bin/biome "$(curl -sfSL https://api.github.com/repos/biomejs/biome/releases/latest | \
    jq -r '.assets[] | select(.name | endswith("linux-x64")) | .browser_download_url')" && \
    chmod +x /usr/local/bin/biome && \
    type -p biome

### Scripts
RUN mkdir -p                                         /app
COPY tools/ffmpeg-vqe/pyproject.toml                 /app
COPY tools/ffmpeg-vqe/poetry.lock                    /app
WORKDIR                                              /app

RUN set -eux && \
    pip3 install -U pip setuptools wheel && \
    pip install "poetry==${POETRY_VERSION}" && \
    type poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --only=main -C /app

COPY tools/ffmpeg-vqe/src/ffmpegvqe/entrypoint.py    /app/entrypoint.py
COPY tools/ffmpeg-vqe/plotbitrate.sh                 /app/plotbitrate.sh

ENTRYPOINT []
CMD []
