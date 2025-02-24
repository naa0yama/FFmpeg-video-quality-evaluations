#- -------------------------------------------------------------------------------------------------
#- Runner
#-
FROM ghcr.io/naa0yama/join_logo_scp_trial:v25.02.24-beta5-ubuntu2404
ARG DEBIAN_FRONTEND=noninteractive \
    DEFAULT_USERNAME=vscode \
    \
    ASDF_VERSION="v0.16.4" \
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
    groupadd --gid 60001 "${DEFAULT_USERNAME}" && \
    useradd -s /bin/bash --uid 60001 --gid 60001 -m "${DEFAULT_USERNAME}" && \
    echo "${DEFAULT_USERNAME}:password" | chpasswd && \
    passwd -d "${DEFAULT_USERNAME}" && \
    echo -e "${DEFAULT_USERNAME}\tALL=(ALL) NOPASSWD:ALL" > "/etc/sudoers.d/${DEFAULT_USERNAME}"

COPY --chown=${DEFAULT_USERNAME} --chmod=644 .tool-versions /home/${DEFAULT_USERNAME}/.tool-versions

# Add asdf install
RUN set -eux && \
    cd /tmp && \
    if [ -z "${ASDF_VERSION}" ]; then echo "ASDF_VERSION is blank"; else echo "ASDF_VERSION is set to '$ASDF_VERSION'"; fi && \
    curl -fSL -o /tmp/asdf.tar.gz "$(curl -sfSL https://api.github.com/repos/asdf-vm/asdf/releases/tags/${ASDF_VERSION} | \
    jq -r '.assets[] | select(.name | endswith("linux-amd64.tar.gz")) | .browser_download_url')" && \
    tar -xf /tmp/asdf.tar.gz && \
    mv -v /tmp/asdf /usr/local/bin/asdf && \
    type -p asdf && \
    asdf version

USER ${DEFAULT_USERNAME}
RUN <<EOF
cat <<- _DOC_ >> ~/.bashrc

#asdf command
export PATH="\${ASDF_DATA_DIR:-$HOME/.asdf}/shims:\$PATH"
. <(asdf completion bash)

_DOC_
EOF

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
ARG PATH="/home/${DEFAULT_USERNAME}/.asdf/shims:${PATH}"
RUN set -eux && \
    asdf plugin add python

# asdf install plugin poetry
RUN set -eux && \
    asdf plugin add poetry

# plugin install
RUN set -eux && \
    asdf install python && \
    asdf install

ENTRYPOINT [ "/bin/bash", "-c" ]
CMD [ "" ]
