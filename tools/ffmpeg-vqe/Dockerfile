ARG NVIDIA_CODECSDK_VER=n12.0.16.0
ARG NVIDIA_CUDA_VER=12.1.1-devel-ubuntu22.04

ARG DEBIAN_FRONTEND noninteractive
ARG DEBCONF_NOWARNINGS yes
ARG PYTHONUNBUFFERED=1
ARG TZ "Asia/Tokyo"
#- -------------------------------------------------------------------------------------------------
#- Builder
#-
FROM nvidia/cuda:${NVIDIA_CUDA_VER} as builder

ENV DEBIAN_FRONTEND=${DEBIAN_FRONTEND}
ENV DEBCONF_NOWARNINGS=${DEBCONF_NOWARNINGS}
ENV PYTHONUNBUFFERED=${PYTHONUNBUFFERED}
ENV TZ=${TZ}

## NVIDIA
ENV NVIDIA_VISIBLE_DEVICES all
ENV NVIDIA_DRIVER_CAPABILITIES ${NVIDIA_DRIVER_CAPABILITIES},video
ENV LD_LIBRARY_PATH "/usr/local/cuda/compat:/usr/local/cuda/lib64:$LD_LIBRARY_PATH"
ENV PATH "/usr/local/cuda/bin:$PATH"
# https://docs.nvidia.com/cuda/cuda-compiler-driver-nvcc/index.html#virtual-architecture-feature-list
ENV CUDA_CC="70 72 75 80 86 87 89 90 90a"
ARG NVIDIA_CODECSDK_VER
ARG NVIDIA_CUDA_VER

## VMAF
ARG VMAF_VERSION=2.3.1
ARG VMAF_URL="https://github.com/Netflix/vmaf/archive/refs/tags/v${VMAF_VERSION}.tar.gz"
ARG VMAF_SHA256=8d60b1ddab043ada25ff11ced821da6e0c37fd7730dd81c24f1fc12be7293ef2

## FFmpeg
ARG FFMPEG_VERSION=6.0
ARG FFMPEG_URL="https://ffmpeg.org/releases/ffmpeg-${FFMPEG_VERSION}.tar.bz2"
ARG FFMPEG_SHA256=47d062731c9f66a78380e35a19aac77cebceccd1c7cc309b9c82343ffc430c3d

# retry dns and some http codes that might be transient errors
ARG WGET_OPTS="--retry-on-host-error --retry-on-http-error=429,500,502,503"

# Build Dependencies
RUN set -eux && \
    apt-get update -qq && \
    apt-get install -y --no-install-recommends \
    autoconf \
    automake \
    build-essential \
    cmake \
    git-core \
    libass-dev \
    libfreetype6-dev \
    libgnutls28-dev \
    libunistring-dev \
    libmp3lame-dev \
    libtool \
    libvorbis-dev \
    meson \
    ninja-build \
    pkg-config \
    texinfo \
    wget \
    yasm \
    zlib1g-dev

# working directory
RUN mkdir -p ~/ffmpeg_sources ~/bin

# vmaf
RUN apt-get -y install --no-install-recommends doxygen xxd

# NASM
RUN apt-get -y install --no-install-recommends nasm

# libx264
RUN apt-get -y install --no-install-recommends libx264-dev

# libx265
RUN apt-get -y install --no-install-recommends libx265-dev libnuma-dev

# libvpx
RUN apt-get -y install --no-install-recommends libvpx-dev

# libfdk-aac
RUN apt-get -y install --no-install-recommends libfdk-aac-dev

# libopus
RUN apt-get -y install --no-install-recommends libopus-dev

# libaom
RUN apt-get -y install --no-install-recommends libaom-dev libdav1d-dev

# libaribb24
RUN apt-get -y install --no-install-recommends libaribb24-dev

# Intel Media SDK
RUN sed -i -e's/ main/ main contrib non-free/g' /etc/apt/sources.list && \
    set -eux && \
    apt-get update -qq && \
    apt-get install -y --no-install-recommends \
    libmfx-dev \
    libva-dev \
    intel-media-va-driver-non-free

# libvmaf
RUN set -eux && \
    cd ~/ffmpeg_sources && \
    wget ${WGET_OPTS} -O vmaf.tar.gz "${VMAF_URL}" && \
    echo "${VMAF_SHA256}  vmaf.tar.gz" | sha256sum --status -c - && \
    tar xf vmaf.tar.gz && \
    cd vmaf-*/libvmaf && \
    meson build --buildtype=release -Ddefault_library=static -Dbuilt_in_models=true -Denable_tests=false -Denable_docs=false -Denable_avx512=true -Denable_float=true && \
    ninja -vC build && \
    ninja -vC build install

# NVIDIA Video Codec SDK
RUN set -eux && \
    cd ~/ffmpeg_sources && \
    git -C nv-codec-headers pull 2> /dev/null || \
    git clone https://github.com/FFmpeg/nv-codec-headers -b ${NVIDIA_CODECSDK_VER} --depth 1 && \
    cd nv-codec-headers && \
    make -j$(nproc) && \
    make install

# FFmpeg
SHELL ["/bin/bash", "-c"]
RUN set -eux && \
    type nvcc && \
    nvcc --version

RUN set -ex && \
    cd ~/ffmpeg_sources && \
    wget ${WGET_OPTS} -O ffmpeg.tar.bz2 "${FFMPEG_URL}" && \
    echo "${FFMPEG_SHA256}  ffmpeg.tar.bz2" | sha256sum --status -c - && \
    tar xf ffmpeg.tar.bz2 && \
    cd ffmpeg-* && \
    set +x && \
    ary=($(echo ${CUDA_CC})) && \
    for i in $(seq 1 ${#ary[@]}); do gencode="-gencode arch=compute_${ary[$i-1]},code=sm_${ary[$i-1]} $gencode"; done && \
    set -x && \
    CUDA_OPTION="${gencode} -O2" && \
    sed -i -e 's/$nvccflags -ptx/$nvccflags/g' ./configure && \
    ./configure \
    --disable-debug \
    --disable-doc \
    --disable-ffplay \
    --extra-libs="-lpthread -lm" \
    \
    --ld="g++" \
    --enable-small \
    --pkg-config-flags="--static" \
    --extra-cflags="-fopenmp" \
    --extra-ldflags="-fopenmp -Wl,-z,stack-size=2097152" \
    --toolchain=hardened \
    --enable-static \
    --disable-shared \
    \
    --enable-cuda-nvcc \
    --extra-cflags="-I /usr/local/cuda/include" \
    --extra-ldflags="-L /usr/local/cuda/compat -L /usr/local/cuda/lib64" \
    # CC指定フラグ追加 (https://github.com/NVIDIA/cuda-samples/issues/46#issuecomment-863835984)
    --nvccflags="${CUDA_OPTION}" \
    \
    --enable-gpl \
    --enable-libaom \
    --enable-libaribb24 \
    --enable-libass \
    --enable-libdav1d \
    --enable-libfdk-aac \
    --enable-libfreetype \
    --enable-libmfx \
    --enable-libmp3lame \
    --enable-libopus \
    --enable-libvmaf \
    --enable-libvorbis \
    --enable-libvpx \
    --enable-libx264 \
    --enable-libx265 \
    --enable-nonfree \
    --enable-vaapi \
    --enable-version3 && \
    make -j$(nproc) install && \
    hash -r

# FFmpeg runtime package list saved
RUN set -eux && \
    ldd /usr/local/bin/ffmpeg /usr/local/bin/ffprobe | \
    awk -F ' => ' '{print $1}' | \
    grep -v -E '(ld-linux-x86-64.so.2|linux-vdso.so.1|ffmpeg:|ffprobe:)' | \
    tr -d '\t' | sort | uniq | xargs -I'{}' dpkg -S {} | \
    awk -F':' '{print $1}' | sort | uniq > /ffmpeg_runtime.txt

RUN set -eux && \
    ls -lah /usr/local/bin && \
    ffmpeg -version

RUN set -eux && \
    ffmpeg -hide_banner -hwaccels && \
    ffmpeg -hide_banner -buildconf && \
    for i in decoders encoders; do echo ${i}:; ffmpeg -hide_banner -${i} | egrep -i "av1|[x|h]264|[x|h]265|hevc|vp9|qsv|vaapi|nvenc|libmfx"; done

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

#- -------------------------------------------------------------------------------------------------
#- Runner
#-
FROM ubuntu:jammy

ENV DEBIAN_FRONTEND=${DEBIAN_FRONTEND}
ENV DEBCONF_NOWARNINGS=${DEBCONF_NOWARNINGS}
ENV PYTHONUNBUFFERED=${PYTHONUNBUFFERED}
ENV TZ=${TZ}

SHELL ["/bin/bash", "-c"]

# Intel Media SDK
RUN set -eux && \
    apt-get update -qq && \
    apt-get install -y --no-install-recommends \
    intel-media-va-driver-non-free &&\
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# NVENC Video Encoding runtime library
RUN set -eux && \
    apt-get update -qq && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    wget && \
    wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.0-1_all.deb && \
    dpkg -i cuda-keyring_1.0-1_all.deb && \
    apt-get update -qq && \
    apt-get install -y --no-install-recommends \
    libnvidia-encode-530 \
    libnvidia-decode-530 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    rm -f cuda-keyring_1.0-1_all.deb

# FFmpeg runtime
COPY --from=builder /usr/local/bin/ffmpeg                   /usr/local/bin/ffmpeg
COPY --from=builder /usr/local/bin/ffprobe                  /usr/local/bin/ffprobe
COPY --from=builder /ffmpeg_runtime.txt                     /ffmpeg_runtime.txt
RUN set -eux && \
    apt-get update -qq && \
    apt-get install -y --no-install-recommends \
    $(cat /ffmpeg_runtime.txt) && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Script dep
RUN set -eux && \
    apt-get update -qq && \
    apt-get install -y --no-install-recommends \
    tzdata \
    binutils \
    jq \
    python3 \
    python3-pip \
    vainfo && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN set -eux && \
    pip3 install -U pip setuptools wheel

### Scripts
COPY --from=builder /usr/local/lib/python3.10/dist-packages     /usr/local/lib/python3.10/dist-packages
COPY --from=builder /usr/local/bin/plotbitrate                  /usr/local/bin/plotbitrate
COPY                src/ffmpegvqe/entrypoint.py                 /app/entrypoint.py
COPY                plotbitrate.sh                              /app/plotbitrate.sh

RUN set -eux && \
    readelf -d /usr/local/bin/ffmpeg

# ENTRYPOINT ["bash"]
# CMD [""]
