ARG PYTHONUNBUFFERED=1
ARG DEBIAN_FRONTEND noninteractive
ARG DEBCONF_NOWARNINGS yes

#- -------------------------------------------------------------------------------------------------
#- Builder
#-
FROM python:3.10-bullseye as builder

ARG PYTHONUNBUFFERED
ARG DEBIAN_FRONTEND
ARG DEBCONF_NOWARNINGS

RUN set -eux && \
    apt-get update -qq && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN set -eux && \
    pip install -U pip && \
    pip install plotbitrate


#- -------------------------------------------------------------------------------------------------
#- Runner
#-
FROM python:3.10-slim-bullseye

ARG PYTHONUNBUFFERED
ARG DEBIAN_FRONTEND
ARG DEBCONF_NOWARNINGS

RUN set -eux && \
    apt-get update -qq && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir app
WORKDIR /app

COPY --from=builder   /usr/local/lib/python3.10/site-packages     /usr/local/lib/python3.10/site-packages
COPY                  entrypoint.sh                               /app/entrypoint.sh
COPY                  plotbitrate.sh                              /app/plotbitrate.sh
COPY --from=mwader/static-ffmpeg:6.0  /ffmpeg     /usr/local/bin/
COPY --from=mwader/static-ffmpeg:6.0  /ffprobe    /usr/local/bin/

ENTRYPOINT ["bash", "/app/entrypoint.sh"]
CMD [""]
