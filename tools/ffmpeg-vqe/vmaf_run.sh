#!/usr/bin/env bash
set -eu

# VMAF
find /dist ! -name 'base.mp4' -name '*.mp4' -print0 -exec bash vmaf.sh {} \;
