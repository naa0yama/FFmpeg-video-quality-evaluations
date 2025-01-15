#!/bin/bash
set -eux

# GitHubリポジトリ情報
OWNER="naa0yama"
REPO="FFmpeg-video-quality-evaluations"

# 必要なコマンドがインストールされているか確認
if ! command -v jq &> /dev/null; then
  echo "jq がインストールされていません。インストールしてください。"
  exit 1
fi

if ! command -v aria2c &> /dev/null; then
  echo "aria2 がインストールされていません。インストールしてください。"
  exit 1
fi

# APIエンドポイント
API_URL="https://api.github.com/repos/$OWNER/$REPO/releases/latest"

# リリース情報を取得
response=$(curl -s -H "Accept: application/vnd.github+json" $API_URL)

# アセットのURLを抽出
asset_urls=$(echo $response | jq -r '.assets[].browser_download_url')

# アセットを順番にダウンロード
for url in $asset_urls; do
  echo "Downloading $url..."
  aria2c --max-concurrent-downloads=4 \
  --connect-timeout=5 \
  --max-connection-per-server=16 \
  --split=3 \
  --min-split-size=5M \
  --human-readable=true \
  --download-result=full \
  --file-allocation=none \
  $url
done

echo "All assets downloaded."
