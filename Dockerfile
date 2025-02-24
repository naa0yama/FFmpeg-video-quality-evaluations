#- -------------------------------------------------------------------------------------------------
#- Runner
#-
FROM ghcr.io/naa0yama/join_logo_scp_trial:v25.02.24-beta1-ubuntu2404

ARG DEBIAN_FRONTEND=noninteractive \
    DEFAULT_USERNAME=user \
    \
    ASDF_VERSION="v0.14.1" \
    BIOME_VERSION="cli/v1.8.3"

SHELL ["/bin/bash", "-c"]
RUN mkdir -p /app

# Script dep
RUN set -eux && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    bash \
    binutils \
    btop \
    ca-certificates \
    curl \
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

# Add Biome latest install
RUN set -eux && \
    if [ -z "${BIOME_VERSION}" ]; then echo "BIOME_VERSION is blank"; else echo "BIOME_VERSION is set to '$BIOME_VERSION'"; fi && \
    curl -fSL -o /usr/local/bin/biome "$(curl -sfSL https://api.github.com/repos/biomejs/biome/releases/tags/${BIOME_VERSION} | \
    jq -r '.assets[] | select(.name | endswith("linux-x64")) | .browser_download_url')" && \
    chmod +x /usr/local/bin/biome && \
    type -p biome

# Create user
RUN set -eux && \
    userdel -r ubuntu && \
    groupadd --gid 60001 vscode && \
    useradd -s /bin/bash --uid 60001 --gid 60001 -m vscode && \
    echo vscode:password | chpasswd && \
    passwd -d vscode && \
    echo -e "vscode\tALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/vscode

COPY --chown=vscode --chmod=644 .tool-versions /home/vscode/.tool-versions

# Install asdf
USER vscode
RUN set -eux && \
    git clone https://github.com/asdf-vm/asdf.git ~/.asdf \
    --depth 1 --branch ${ASDF_VERSION} && \
    echo ". \"\$HOME/.asdf/asdf.sh\"" >> ~/.bashrc && \
    echo ". \"\$HOME/.asdf/completions/asdf.bash\"" >> ~/.bashrc

# asdf update
# Broken stable release
# Ref: https://github.com/asdf-vm/asdf/issues/1821
# RUN set -eux && \
#     source $HOME/.asdf/asdf.sh && \
#     asdf update

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

ENTRYPOINT [ "/bin/bash", "-c" ]
CMD [ "" ]
