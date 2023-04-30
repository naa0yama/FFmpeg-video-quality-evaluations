#!/usr/bin/env bash

set -eu

find /source /dist -name '*.mp4' -print0 -exec bash /app/plotbitrate.sh {} \;
