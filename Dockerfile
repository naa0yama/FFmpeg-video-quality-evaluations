ARG NVIDIA_CODECSDK_VER=n12.0.16.0
ARG NVIDIA_CUDA_VER=12.1.0-devel-ubuntu22.04

#- -------------------------------------------------------------------------------------------------
#- Builder
#-
FROM nvidia/cuda:${NVIDIA_CUDA_VER} as builder

ENV DEBIAN_FRONTEND noninteractive
ENV DEBCONF_NOWARNINGS yes

ENV NVIDIA_VISIBLE_DEVICES all
ENV NVIDIA_DRIVER_CAPABILITIES ${NVIDIA_DRIVER_CAPABILITIES},video
ARG NVIDIA_CODECSDK_VER
ARG NVIDIA_CUDA_VER

ARG VMAF_VERSION=2.3.1
ARG VMAF_URL="https://github.com/Netflix/vmaf/archive/refs/tags/v${VMAF_VERSION}.tar.gz"
ARG VMAF_SHA256=8d60b1ddab043ada25ff11ced821da6e0c37fd7730dd81c24f1fc12be7293ef2

ARG FFMPEG_VERSION=6.0
ARG FFMPEG_URL="https://ffmpeg.org/releases/ffmpeg-${FFMPEG_VERSION}.tar.bz2"
ARG FFMPEG_SHA256=47d062731c9f66a78380e35a19aac77cebceccd1c7cc309b9c82343ffc430c3d

# retry dns and some http codes that might be transient errors
ARG WGET_OPTS="--retry-on-host-error --retry-on-http-error=429,500,502,503"

# Build Dependencies
RUN set -eux && \
    apt-get update -qq && \
    apt-get -y install \
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

# NASM
RUN apt-get -y install nasm

# libx264
RUN apt-get -y install libx264-dev

# libx265
RUN apt-get -y install libx265-dev libnuma-dev

# libvpx
RUN apt-get -y install libvpx-dev

# libfdk-aac
RUN apt-get -y install libfdk-aac-dev

# libopus
RUN apt-get -y install libopus-dev

# libaom
RUN apt-get -y install libaom-dev libdav1d-dev

# Intel Media SDK
RUN apt-get -y install libmfx-dev libva-dev

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
RUN set -ex && \
    PATH=$PATH:/usr/local/cuda/bin && \
    cd ~/ffmpeg_sources && \
    type nvcc && \
    nvcc --version && \
    wget ${WGET_OPTS} -O ffmpeg.tar.bz2 "${FFMPEG_URL}" && \
    echo "${FFMPEG_SHA256}  ffmpeg.tar.bz2" | sha256sum --status -c - && \
    tar xf ffmpeg.tar.bz2 && \
    cd ffmpeg-* && \
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
    --extra-cflags="-I/usr/local/cuda/include" \
    --extra-ldflags="-L/usr/local/cuda/lib64" \
    \
    --enable-gpl \
    --enable-libaom \
    --enable-libdav1d \
    --enable-libass \
    --enable-libfdk-aac \
    --enable-libfreetype \
    --enable-libmp3lame \
    --enable-libopus \
    --enable-libvorbis \
    --enable-libvpx \
    --enable-libx264 \
    --enable-libx265 \
    --enable-libvmaf \
    --enable-vaapi \
    --enable-libmfx \
    --enable-nonfree && \
    make -j$(nproc) install && \
    hash -r

RUN set -eux && \
    ls -lah /usr/local/bin && \
    ffmpeg -version

RUN set -eux && \
    ffmpeg -hide_banner -hwaccels && \
    ffmpeg -hide_banner -buildconf && \
    for i in decoders encoders; do echo ${i}:; ffmpeg -hide_banner -${i} | egrep -i "av1|[x|h]264|[x|h]265|hevc|vp9|qsv|vaapi|nvenc|libmfx"; done


#- -------------------------------------------------------------------------------------------------
#- Runner
#-
FROM ubuntu:jammy

RUN set -eux && \
    apt-get update -qq && \
    apt-get -y install \
    binutils \
    libc6 \
    libass9 \
    libfreetype6 \
    zlib1g \
    libva2 \
    libmfx1 \
    libstdc++6 \
    libvpx7 \
    libdav1d5 \
    libaom3 \
    libfdk-aac2 \
    libmp3lame0 \
    libopus0 \
    libvorbis0a \
    libvorbisenc2 \
    libx264-163 \
    libx265-199 \
    libgcc-s1 \
    libva-drm2 \
    libc6 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/bin/ffmpeg       /usr/local/bin/ffmpeg
COPY --from=builder /usr/local/bin/ffprobe      /usr/local/bin/ffprobe

RUN set -eux && \
    readelf -d /usr/local/bin/ffmpeg
