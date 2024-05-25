#- -------------------------------------------------------------------------------------------------
#- Runner
#-
FROM ghcr.io/naa0yama/docker-mirakurun-epgstation/epgstation:9569e00

ARG POETRY_VERSION=1.8.2

# Scripts
RUN mkdir -p         /app
COPY pyproject.toml  /app
COPY poetry.lock     /app
WORKDIR              /app

RUN set -eux && \
    apt-get update -qq && \
    apt-get install -y --no-install-recommends \
    python3 \
    python3-pip && \
    pip3 install --upgrade pip setuptools wheel && \
    pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --only main

SHELL ["/bin/bash", "-c"]

# FFmpeg runtime
RUN set -eux && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    $(cat /ffmpeg_runtime.txt) && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

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
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN set -eux && \
    pip3 install -U pip setuptools wheel

### Scripts
COPY                src/ffmpegvqe/entrypoint.py                 /app/entrypoint.py
COPY                plotbitrate.sh                              /app/plotbitrate.sh

# Create user
RUN set -eux && \
    groupadd --gid 1000 vscode && \
    useradd -s /bin/bash --uid 1000 --gid 1000 -m vscode && \
    echo vscode:password | chpasswd && \
    passwd -d vscode && \
    echo -e "vscode\tALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/vscode

RUN set -eux && \
    pip install "poetry==${POETRY_VERSION}" && \
    type poetry
