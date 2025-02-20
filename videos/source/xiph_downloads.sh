#!/usr/bin/env bash
set -eux


mkdir -p ./src/{bbb,sintel,tearsofsteel}

if [ "${1}" == "bbb"];then
  curl -sfSL https://media.xiph.org/BBB/BBB-1080-png/MD5SUMS.txt | \
    awk '{print $2}' | sed -e 's@^@https://media.xiph.org/BBB/BBB-1080-png/@g' > pnglist.txt
  aria2c --dir=./src/bbb \
    --input-file=pnglist.txt \
    --max-concurrent-downloads=4 \
    --connect-timeout=5 \
    --max-connection-per-server=16 \
    --split=3 \
    --min-split-size=5M \
    --human-readable=true \
    --download-result=full \
    --file-allocation=none
fi

if [ "${1}" == "sintel"];then
  curl -sfSL https://media.xiph.org/sintel/sintel-1080-png/MD5SUMS.txt | \
    awk '{print $2}' | sed -e 's@^@https://media.xiph.org/sintel/sintel-1080-png/@g' > pnglist.txt
  aria2c --dir=./src/sintel \
    --input-file=pnglist.txt \
    --max-concurrent-downloads=4 \
    --connect-timeout=5 \
    --max-connection-per-server=16 \
    --split=3 \
    --min-split-size=5M \
    --human-readable=true \
    --download-result=full \
    --file-allocation=none
fi

if [ "${1}" == "tearsofsteel"];then
  curl -sfSL https://media.xiph.org/tearsofsteel/tearsofsteel-1080bis-png/SHA1SUMS.txt | \
    awk '{print $2}' | sed -e 's@^@https://media.xiph.org/tearsofsteel/tearsofsteel-1080bis-png/@g' > pnglist.txt
  aria2c --dir=./src/tearsofsteel \
    --input-file=pnglist.txt \
    --max-concurrent-downloads=4 \
    --connect-timeout=5 \
    --max-connection-per-server=16 \
    --split=3 \
    --min-split-size=5M \
    --human-readable=true \
    --download-result=full \
    --file-allocation=none
fi
