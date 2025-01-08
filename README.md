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

* check

```bash
$ cat /etc/udev/rules.d/99-render.rules 
KERNEL=="render*" GROUP="render", MODE="0666"

```

### Intel HD (vaapi, Quick Sync Video)

```bash
sudo apt install vainfo intel-gpu-tools

```

* version check

```bash
sudo vainfo

```

* output

```bash
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

リファレンスデータを作成する。
リファレンス用は下記の2つ

## エンコードとテスト

```bash
# FFmpeg
docker build -t ffmpeg-vqe .

docker run --user $(id -u):$(id -g) --rm -it \
  -v $PWD/videos/source:/source \
  -v $PWD/videos/dist:/dist \
  -v $PWD/tools/ffmpeg-vqe:/src \
  --device "/dev/dri:/dev/dri" \
  ffmpeg-vqe /bin/bash

```

```bash
rm -rfv /dist/*.* && \
python3 /app/entrypoint.py --encode -fss 180 -ft 60 && \
bash /app/plotbitrate.sh

```

```bash
mkdir -p assets/BigBuckBunny
cp -ar videos/dist assets/BigBuckBunny
cd assets/BigBuckBunny
tar -Jcvf BigBuckBunny_vmaf.tar.xz *_vmaf.json
rm -rf *_vmaf.json

```

* CRF(Constant Rate Factor)
* QP(Constant quantization parameter)
* CQ(Constant Quality mode in VBR)

* preset は標準, 標準から -3, +3 を試す

| codec       |  CRF  |  QP   |      CQ       | preset default        | 試す preset                         |
| :---------- | :---: | :---: | :-----------: | :-------------------- | :---------------------------------- |
| **libx264** |   O   |   O   |               | medium                | veryfast ,medium, veryslow          |
| h264_nvenc  |       |   O   |       O       | 15(p4)                | 12(p2), 15(p4), 18(p7)              |
| h264_qsv    |       |       |               | 4(medium) (default 0) | 7(veryfast), 4(medium), 1(veryslow) |
| h264_vaapi  |       |   O   | O (rc_mode 1) | `-`                   |                                     |
|             |       |       |               |                       |                                     |
| **libx265** |   O   |   O   |               | medium                | veryfast ,medium, veryslow          |
| hevc_nvenc  |       |   O   |       O       | 15(p4)                | 12(p2), 15(p4), 18(p7)              |
| hevc_qsv    |       |       |               | 4(medium) (default 0) | 7(veryfast), 4(medium), 1(veryslow) |
| hevc_vaapi  |       |   O   | O (rc_mode 1) | `-`                   |                                     |

|                    |      |      |                      |
| :----------------- | :--- | :--- | :------------------- |
| **Global options** |      |      |                      |
|                    |      | `-y` | 出力ファイルの上書き |

* ``
* `-rc-lookahead`: B-frame+1, MAX 20

* [NVIDIA GeForce RTX 2060 Super](https://www.elsa-jp.co.jp/products/detail/elsa-geforce-rtx-2060-super-s-a-c/) 向けに最適化をする

|              |                    |
| :----------- | :----------------- |
| GPU Name     | TU106              |
| GPU Variant  | TU106-410-A1       |
| Architecture | Turing             |
|              |                    |
| DirectX      | 12 Ultimate (12_2) |
| OpenGL       | 4.6                |
| OpenCL       | 3.0                |
| Vulkan       | 1.3                |
| CUDA         | 7.5                |
| Shader Model | 6.7                |

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

* `-i_qfactor 0.75`
* `-b_qfactor 1.1`

* -vf yadif=0:-1:1,hqdn3d=4.0,scale=1280:720:flags=lanczos+accurate_rnd,unsharp=3:3:0.5:3:3:0.5:0
* -map 0:p:%SID10%:0
* -map 0:p:%SID10%:1
* -map 0:p:%SID10%:2
* -sn
* -dn

```bash
for i in decoders encoders; do echo ${i}:; ffmpeg -hide_banner -${i} | \
    egrep -i "[x|h]264|[x|h]265|av1|cuvid|hevc|libmfx|nv[dec|enc]|qsv|vaapi|vp9"; done

```

* [HWAccelIntro – FFmpeg](https://trac.ffmpeg.org/wiki/HWAccelIntro)
* [Hardware/QuickSync – FFmpeg](https://trac.ffmpeg.org/wiki/Hardware/QuickSync)
* [Hardware/VAAPI – FFmpeg](https://trac.ffmpeg.org/wiki/Hardware/VAAPI)
* [Using FFmpeg with NVIDIA GPU Hardware Acceleration - NVIDIA Docs](https://docs.nvidia.com/video-technologies/video-codec-sdk/12.2/ffmpeg-with-nvidia-gpu/index.html)
* [libvmaf with CUDA -- how to build and use · Issue #1227 · Netflix/vmaf](https://github.com/Netflix/vmaf/issues/1227)

```bash
docker run --user $(id -u):$(id -g) --rm -it --gpus all ffmpeg-vqe /bin/bash

```

```bash
for decoder in av1 av1_qsv h264 h264_qsv hevc hevc_qsv mpeg2_qsv vp9_qsv
do
  ffmpeg -hide_banner -h decoder=${decoder}    > /source/decoder_${decoder}.txt
done

for encoder in libaom-av1 av1_qsv libx264 h264_qsv libx265 hevc_qsv mpeg2_qsv vp9_qsv
do
  ffmpeg -hide_banner -h encoder=${encoder}    > /source/encoder_${encoder}.txt
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
  ffmpeg -hide_banner -h filter=${filter}    > /source/filter_${filter}.txt
done

```

## Tools

### dist Summary csv gen

TBA

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
