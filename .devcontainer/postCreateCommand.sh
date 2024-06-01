#!/usr/bin/env bash
set -eux

rm -rf .venv/
poetry install --no-interaction -C tools/ffmpeg-vqe
