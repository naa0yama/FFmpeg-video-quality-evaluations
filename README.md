# FFmpeg-video-quality-evaluations

Video encoding quality evaluation project using VMAF and SSIM

## tools

* [plotbitrate](https://github.com/zeroepoch/plotbitrate)
* FFmpeg
* FFprobe

## 準備

### Device settings

```bash
tee /etc/udev/rules.d/99-render.rules <<EOF
KERNEL=="render*" GROUP="render", MODE="0666"

EOF

```

### Intel HD (vaapi, Quick Sync Video)

```bash
sudo apt install hwinfo intel-gpu-tools vainfo

```

Version check

```bash
> sudo vainfo
error: XDG_RUNTIME_DIR is invalid or not set in the environment.
error: can't connect to X server!
libva info: VA-API version 1.20.0
libva info: Trying to open /usr/lib/x86_64-linux-gnu/dri/iHD_drv_video.so
libva info: Found init function __vaDriverInit_1_20
libva info: va_openDriver() returns 0
vainfo: VA-API version: 1.20 (libva 2.12.0)
vainfo: Driver version: Intel iHD driver for Intel(R) Gen Graphics - 24.1.0 ()
vainfo: Supported profile and entrypoints
      VAProfileNone                   : VAEntrypointVideoProc
      VAProfileNone                   : VAEntrypointStats
      VAProfileMPEG2Simple            : VAEntrypointVLD
      VAProfileMPEG2Main              : VAEntrypointVLD
      VAProfileH264Main               : VAEntrypointVLD
      VAProfileH264Main               : VAEntrypointEncSliceLP
      VAProfileH264High               : VAEntrypointVLD
      VAProfileH264High               : VAEntrypointEncSliceLP
      VAProfileJPEGBaseline           : VAEntrypointVLD
      VAProfileJPEGBaseline           : VAEntrypointEncPicture
      VAProfileH264ConstrainedBaseline: VAEntrypointVLD
      VAProfileH264ConstrainedBaseline: VAEntrypointEncSliceLP
      VAProfileHEVCMain               : VAEntrypointVLD
      VAProfileHEVCMain               : VAEntrypointEncSliceLP
      VAProfileHEVCMain10             : VAEntrypointVLD
      VAProfileHEVCMain10             : VAEntrypointEncSliceLP
      VAProfileVP9Profile0            : VAEntrypointVLD
      VAProfileVP9Profile0            : VAEntrypointEncSliceLP
      VAProfileVP9Profile1            : VAEntrypointVLD
      VAProfileVP9Profile1            : VAEntrypointEncSliceLP
      VAProfileVP9Profile2            : VAEntrypointVLD
      VAProfileVP9Profile2            : VAEntrypointEncSliceLP
      VAProfileVP9Profile3            : VAEntrypointVLD
      VAProfileVP9Profile3            : VAEntrypointEncSliceLP
      VAProfileHEVCMain12             : VAEntrypointVLD
      VAProfileHEVCMain422_10         : VAEntrypointVLD
      VAProfileHEVCMain422_10         : VAEntrypointEncSliceLP
      VAProfileHEVCMain422_12         : VAEntrypointVLD
      VAProfileHEVCMain444            : VAEntrypointVLD
      VAProfileHEVCMain444            : VAEntrypointEncSliceLP
      VAProfileHEVCMain444_10         : VAEntrypointVLD
      VAProfileHEVCMain444_10         : VAEntrypointEncSliceLP
      VAProfileHEVCMain444_12         : VAEntrypointVLD
      VAProfileHEVCSccMain            : VAEntrypointVLD
      VAProfileHEVCSccMain            : VAEntrypointEncSliceLP
      VAProfileHEVCSccMain10          : VAEntrypointVLD
      VAProfileHEVCSccMain10          : VAEntrypointEncSliceLP
      VAProfileHEVCSccMain444         : VAEntrypointVLD
      VAProfileHEVCSccMain444         : VAEntrypointEncSliceLP
      VAProfileAV1Profile0            : VAEntrypointVLD
      VAProfileAV1Profile0            : VAEntrypointEncSliceLP
      VAProfileHEVCSccMain444_10      : VAEntrypointVLD
      VAProfileHEVCSccMain444_10      : VAEntrypointEncSliceLP

```

### Docker Engine

Ref: [Install Docker Engine | Docker Documentation](https://docs.docker.com/engine/install/)

```bash
curl https://get.docker.com | sh \
  && sudo systemctl --now enable docker

```

## 映像の準備

本プロジェクトでは長期的にリファレンス映像を利用する可能性が高そうに思えたため CC-BY 4.0 で配布されている [Big Buck Bunny](http://www.bigbuckbunny.org) をベースに Release に保管することで永続化しています。  

地上デジタル放送の映像に近づけるため、下記の設定で出力した映像としています。  
映像設定の詳細は [Releases · naa0yama/FFmpeg-video-quality-evaluations](https://github.com/naa0yama/FFmpeg-video-quality-evaluations/releases) のAssetにある encode.ps1 で確認できます。  
すべてダウンロードする場合は `videos/source/reference_downloads.sh` にスクリプトを用意してあります。

| Type          | size      | frame rate | p/i         | bitrate avg / max            | Filename                                              |
| :------------ | :-------- | :--------- | :---------- | :--------------------------- | :---------------------------------------------------- |
| Source        | 1280x720  | 24000/1001 | progressive | `-b:v 10M`<br>`-maxrate 15M` | `BBB_JapanTV_MPEG-2_1280x720_24p.m2ts`                |
|               |           | 30000/1001 | progressive | `-b:v 10M`<br>`-maxrate 15M` | `BBB_JapanTV_MPEG-2_1280x720_30p.m2ts`                |
|               |           |            | interlace   | `-b:v 10M`<br>`-maxrate 15M` | `BBB_JapanTV_MPEG-2_1280x720_30i.m2ts`                |
|               | 1440x1080 | 24000/1001 | progressive | `-b:v 14M`<br>`-maxrate 20M` | `BBB_JapanTV_MPEG-2_1440x1080_24p.m2ts`               |
|               |           | 30000/1001 | progressive | `-b:v 14M`<br>`-maxrate 20M` | `BBB_JapanTV_MPEG-2_1440x1080_30p.m2ts`               |
|               |           |            | interlace   | `-b:v 14M`<br>`-maxrate 20M` | `BBB_JapanTV_MPEG-2_1440x1080_30i.m2ts`               |
| telecine 23   |           |            | interlace   | `-b:v 14M`<br>`-maxrate 20M` | `BBB_JapanTV_MPEG-2_1440x1080_30i_telecine_23.m2ts`   |
| telecine 2332 |           |            | interlace   | `-b:v 14M`<br>`-maxrate 20M` | `BBB_JapanTV_MPEG-2_1440x1080_30i_telecine_2332.m2ts` |
|               |           |            |             |                              |                                                       |
|               | 1920x1080 | 24000/1001 | progressive | `-b:v 18M`<br>`-maxrate 24M` | `BBB_JapanTV_MPEG-2_1920x1080_24p.m2ts`               |
|               |           | 30000/1001 | progressive | `-b:v 18M`<br>`-maxrate 24M` | `BBB_JapanTV_MPEG-2_1920x1080_30p.m2ts`               |
|               |           |            | interlace   | `-b:v 18M`<br>`-maxrate 24M` | `BBB_JapanTV_MPEG-2_1920x1080_30i.m2ts`               |
| telecine 23   |           |            | interlace   | `-b:v 18M`<br>`-maxrate 24M` | `BBB_JapanTV_MPEG-2_1920x1080_30i_telecine_23.m2ts`   |
| telecine 2332 |           |            | interlace   | `-b:v 18M`<br>`-maxrate 24M` | `BBB_JapanTV_MPEG-2_1920x1080_30i_telecine_2332.m2ts` |


## エンコードとテスト

* CQP (Constant Quantization Parameter)
* ICQ (Intelligent Constant Quality)
* LA-ICQ (Look-Ahead Intelligent Constant Quality)
* VBR (Variable Bit Rate)

libx265 でおなじみ CRF(Constant Rate Factor) は QSV には存在しない  
画質は、 LA-ICQ が最も良く ICQ、CQP、VBR の順になる

```bash
# コンテナーの build
docker build -t ffmpeg-vqe .

# コンテナへのログイン
docker run --user $(id -u):$(id -g) --rm -it \
  -v $PWD/videos/source:/source \
  -v $PWD/videos/dist:/dist \
  -v $PWD/tools/ffmpeg-vqe:/src \
  --device "/dev/dri:/dev/dri" \
  ffmpeg-vqe /bin/bash

```

```bash
# /dist を初期化して、エンコードを開始
rm -rfv /dist/*.* && \
python3 /app/entrypoint.py --encode -fss 180 -ft 60 && \
bash /app/plotbitrate.sh

```

```bash
# 結果を assets に移動して *_vmaf.json を圧縮
mkdir -p assets/BigBuckBunny
cp -ar videos/dist assets/BigBuckBunny
cd assets/BigBuckBunny
tar -Jcvf BigBuckBunny_vmaf.tar.xz *_vmaf.json
rm -rf *_vmaf.json

```

### CQP (Constant Quantization Parameter)

一定品質を維持する設定のため、単調なシーンでは過剰、複雑なシーンではビットレート不足となる

```bash
ffmpeg -hwaccel qsv -i input.mp4 \
    -c:v hevc_qsv -preset veryfast \
    -q:v 23 \
    output.mp4

```

### ICQ (Intelligent Constant Quality)

このモードは画質を一定に保ちながら、シーンの複雑さに応じてビットレートを調整します。

```bash
ffmpeg -hwaccel qsv -i input.mp4 \
  -c:v hevc_qsv -preset veryfast \
  -global_quality 20 \
  output.mp4

```

### LA-ICQ (Look-Ahead Intelligent Constant Quality)

先読み解析により画質制御がされ適切なビットレートを割り当てることで、画質と容量のバランスを取ります

```bash
ffmpeg -hwaccel qsv -i input.mp4 \
  -c:v hevc_qsv -preset veryfast \
  -look_ahead 1 -look_ahead_depth 30 -global_quality 20 \
  output.mp4
```

### VBR (Variable Bit Rate)

平均ビットレートによる制御のため画質に関係なく、同容量のサイズにするには優れている

```bash
ffmpeg -hwaccel qsv -i input.mp4 \
  -c:v hevc_qsv -preset veryfast \
  -b:v 2000k -maxrate 2000k \
  output.mp4

```

| type           | option                        | Description                                                  |
| :------------- | :---------------------------- | :----------------------------------------------------------- |
| Hardware       | `-hwaccel cuda`               | ハードウェアデコーダー                                       |
|                | `-hwaccel_output_format cuda` | ハードウェア支援を受けたデコードの出力フォーマット           |
|                |                               |                                                              |
| Format Options | `-fflags +discardcorrupt`     | 破損frameの破棄                                              |
|                | `-movflags faststart`         | メタデータをファイルの先頭にする                             |
|                | `-tag:v hvc1`                 | Apple 製品で再生出来ないため `hvc1` 方式であることを明示する |
|                | `-f mkv`                      | ファイルフォーマットは MKV にする                            |
|                | `-map 0:v`                    | 映像を input からマッピング                                  |
|                | `-ignore_unknown`             | 不明コーデックをコピーしない                                 |
|                | `-y`                          | 確認せずに上書き                                             |
|                | `-g 250`                      | GOP サイズの指定 (Default nvenc_hevc: 250)                   |
|                | `-bf 5`                       | 非 B-frame 間の B-frame 数(Default: 3, Max 5)                |
|                | `-refs 9`                     | 参照フレーム                                                 |
|                | `-b_ref_mode each`            | 参照 B-frame として使う (Default: (B-frames)/2)              |
|                | `-rc-lookahead 20`            | 先読みフレーム数(Default: 0, Min: (B-frames)+1, Max: 20)     |
|                | `-temporal-aq 1`              | フレーム間(時間方向)の適応的量子化を有効にする (Default 0)   |
|                |                               |                                                              |
| Video          | `-aspect:v 16:9`              | アスペクト比を 16:9 に設定                                   |
|                | `-c:v hevc_nvenc`             | エンコーダーを NVENC HEVC (x265) に設定                      |
|                | `-preset:v p4`                | preset を指定                                                |
|                | `-profile:v main10`           | 10-bit 4:2:0 プロファイル                                    |
|                | `-tune hq`                    | 画質最適化指定                                               |
|                |                               |                                                              |
| Audio          | `-c:a aac`                    | AAC に変換                                                   |
|                | `-ar 48000`                   | サンプリングレート 48kHz                                     |
|                | `-ab 256k`                    | ビットレート 256kbps                                         |
|                | `-bsf:a aac_adtstoasc`        | MPEG-2 から MPEG-4 に変更するオプション                      |

* [HWAccelIntro – FFmpeg](https://trac.ffmpeg.org/wiki/HWAccelIntro)
* [Hardware/QuickSync – FFmpeg](https://trac.ffmpeg.org/wiki/Hardware/QuickSync)
* [Hardware/VAAPI – FFmpeg](https://trac.ffmpeg.org/wiki/Hardware/VAAPI)
* [Using FFmpeg with NVIDIA GPU Hardware Acceleration - NVIDIA Docs](https://docs.nvidia.com/video-technologies/video-codec-sdk/12.2/ffmpeg-with-nvidia-gpu/index.html)
* [libvmaf with CUDA -- how to build and use · Issue #1227 · Netflix/vmaf](https://github.com/Netflix/vmaf/issues/1227)

## Memos

### dist Summary csv gen

TBA

### マニュアル生成

```bash
mkdir -p /source/{decoders,encoders,filters}
for decoder in av1 av1_qsv h264 h264_qsv hevc hevc_qsv mpeg2_qsv vp9_qsv
do
  ffmpeg -hide_banner -h decoder=${decoder}    > /source/decoders/decoder_${decoder}.txt
done

for encoder in libaom-av1 av1_qsv libx264 h264_qsv libx265 hevc_qsv mpeg2_qsv vp9_qsv
do
  ffmpeg -hide_banner -h encoder=${encoder}    > /source/encoders/encoder_${encoder}.txt
done

for filter in \
  deinterlace_qsv \
  fieldmatch \
  libvmaf \
  overlay_qsv \
  sab \
  scale \
  scale_qsv \
  vpp_qsv \
  yadif
do
  ffmpeg -hide_banner -h filter=${filter}    > /source/filters/filter_${filter}.txt
done

```

### VMAF cuda

```bash
ffmpeg -hide_banner \
  -hwaccel cuda -hwaccel_output_format cuda -c:v hevc_cuvid  -i /dist/tmp.mp4 \
  -hwaccel cuda -hwaccel_output_format cuda -c:v mpeg2_cuvid -i /source/BBB_JapanTV_MPEG-2_1440x1080_30i.m2ts \
  -filter_complex "
    [0:v:0]scale_npp=format=yuv420p:w=1440:h=1080[dis],
    [1:v:0]scale_npp=format=yuv420p[ref],
    [dis][ref]libvmaf_cuda=model=version=vmaf_v0.6.1\\:pool=harmonic_mean:feature=name=psnr|name=float_ssim:log_fmt=json:log_path=/dist/tmp_vmaf.json:shortest=1:repeatlast=0" -f null -

```

[FFmpeg Filters Documentation](https://ffmpeg.org/ffmpeg-filters.html#Examples-91)

### 映像の準備

今回は、 CC-BY 4.0 で配布されている [Big Buck Bunny](http://www.bigbuckbunny.org) を利用する。  
ミラーとして [Xiph.org :: Test Media](https://media.xiph.org/) で配布されているのでこちらから元 png 画像をダウンロードした。

```bash{name="ダウンロードの例"}
#!/usr/bin/env bash
set -eux

curl -sfSL https://media.xiph.org/BBB/BBB-1080-png/MD5SUMS.txt | \
awk '{print $2}' | \
sed -e 's@^@https://media.xiph.org/BBB/BBB-1080-png/@g' > pnglist.txt

mkdir -p src/

aria2c --dir=./src/ \
  --input-file=pnglist.txt \
  --max-concurrent-downloads=4 \
  --connect-timeout=60 \
  --max-connection-per-server=16 \
  --split=3 \
  --min-split-size=5M \
  --human-readable=true \
  --download-result=full \
  --file-allocation=none

```
