# FFmpeg-video-quality-evaluations

Video encoding quality evaluation project using VMAF and SSIM

## tools

* [plotbitrate](https://github.com/zeroepoch/plotbitrate)
* FFmpeg
* FFprobe

## 暫定利用方法

レポジトリーを clone して devcontainer で起動する

* 設定ファイルを作成
  * `--config` は設定ファイル名でフォルダーを切り管理しやすくするため必須
  * `patterns` と `presets` のリストをループで処理する
    * その時、パラメータとして `outfile.options` の list を分解し `encodes` として生成する。
    * 生成したデータを `datafile` のファイルに保存する

  ```bash
  python src/ffmpegvqe/entrypoint.py --config videos/h264_default-qq13-14.yml

  ```

* エンコードテスト
  * `--encode` をつける事で設定ファイルの pattern 分エンコードし、 VMAF を計測後、 datafile に書き込む

  ```bash
  python src/ffmpegvqe/entrypoint.py --config videos/h264_default-qq13-14.yml --encode

  ```

* グラフを表示
  * `--args --config videos/h264_default-qq13-14.yml` を設定する事で config を読み込ませる

  ```bash
  bokeh serve src/ffmpegvqe/graph.py --show --args --config videos/h264_default-qq13-14.yml

  ```

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
映像設定の詳細は [Releases · naa0yama/FFmpeg-video-quality-evaluations](https://github.com/naa0yama/FFmpeg-video-quality-evaluations/releases) の Asset にある encode.ps1 で確認できます。  
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

圧縮率、エンコード時間は下記のようになる。これは 30p を SW エンコードした比較のため参考程度にするが、傾向として libx264 と libx265 は比例しており、 libx265 の方が約1/2に圧縮できることがわかった。 また、 bitrate が半分になることで、ファイルサイズの縮小にも大きく寄与している。VMAF スコアは 30p の場合横並びでばらつきも少ないためよく出来ているのだと思う。  

エンコード速度については libx264 が軽量なため高速で処理される傾向があり、次に libx265, libaom-av1 と続く結果になった。 libaom-av1 はデフォルト設定では遅すぎため `-cpu-used 5` を追加しての計測だがそれでも早いとは言えない、せめて 1x で捌けるようにはなってほしいものだ。
libx265 と libaom-av1 では圧縮比率はそこまで変わらないため、無理に libaom-av1 を使わなくても良さそうである。  

| size                 | codec      | fps/s | File Size(KiB) | 圧縮率(%) |      VMAF | bitrate avg (kbits/s) |  speed |
| :------------------- | :--------- | ----: | -------------: | --------: | --------: | --------------------: | -----: |
| 1280x720             | mpeg2ts    |   157 |        148,542 |     ----- | 86.186533 |               10141.6 |  5.24x |
|                      | libx264    |   281 |         58,001 |     39.04 | 82.002744 |                3961.1 |  9.37x |
|                      | libx265    |    93 |         36,816 |     24.78 | 79.970688 |                2514.3 |  3.10x |
|                      | libaom-av1 |   5.9 |         31,657 |     21.31 | 83.092612 |                2160.8 | 0.197x |
|                      |            |       |                |           |           |                       |        |
| 1440x1080            | mpeg2ts    |   123 |        208,914 |     ----- | 93.594580 |               14263.5 |  4.09x |
|                      | libx264    |   175 |         83,357 |     39.90 | 90.300860 |                5692.7 |  5.84x |
|                      | libx265    |    69 |         49,853 |     23.86 | 88.317820 |                3404.6 |  2.31x |
|                      | libaom-av1 |   7.2 |         38,933 |     18.63 | 90.866412 |                2657.4 | 0.241x |
|                      |            |       |                |           |           |                       |        |
| 1920x1080            | mpeg2ts    |   149 |        268,476 |     ----- | 97.678510 |               18330.0 |  4.98x |
|                      | libx264    |   131 |        106,758 |     39.76 | 94.863299 |                7290.9 |  4.38x |
|                      | libx265    |    55 |         63,401 |     23.61 | 93.062256 |                4329.8 |  1.85x |
|                      | libaom-av1 |   4.0 |         50,667 |     18.87 | 95.346336 |                3458.3 | 0.133x |
|                      |            |       |                |           |           |                       |        |
| **番外編**           |            |       |                |           |           |                       |        |
| 1440x1080 -> 960x720 | mpeg2ts    |   200 |         90,744 |     ----- | 77.208454 |                6195.5 |  6.68x |
|                      | libx264    |   366 |         47,579 |     52.43 | 73.318637 |                3249.3 |  12.2x |
|                      | libx265    |   108 |         30,809 |     33.95 | 71.313107 |                2104.0 |  3.61x |
|                      | libaom-av1 |   7.1 |         26,414 |     29.10 | 74.324002 |                1802.9 |  0.237 |

* ログは [normal_sw_encode.log](docs/normal_sw_encode.log) にある
* 960x720 の VMAF は解像度をリサイズフィルターで戻して計測している点に注意
* `1時間で約(MB)` は `(14.4Mbps/8)*3600=` を元に計算
* 年間容量は週間90本(30min 80本、60min 10本) x52週間 = 年間 2,600時間を元に計算

番外編として、筆者の考えでは YouTube などの主要配信サービスがアップロードする動画のビットレートとして 720p 5-6Mbps、1080p 8-12Mbps を推奨しているため bitrate が 1440x1080 では足りないのでは? と思っている。  
また、 1280x720 にすると 4:3 を 16:9 に変更するため余計な処理がされる気がしているのとアスペクト比は `-aspect 16:9` で設定できるため縦幅 720 に固定することで 960x720 の 4:3 を作りエンコード時間と容量を削減する設定を試してみた。

## Memos

### マニュアル生成

```bash
mkdir -p ./videos/source/{decoders,encoders,filters}
for decoder in libaom-av1 libdav1d av1 av1_qsv h264 h264_qsv hevc hevc_qsv mpeg2video mpeg2_qsv vp9_qsv
do
  ffmpeg -hide_banner -h decoder=${decoder}    > ./videos/source/decoders/decoder_${decoder}.txt
done

for encoder in libaom-av1 libsvtav1 av1_qsv libx264 h264_qsv libx265 hevc_qsv mpeg2_qsv vp9_qsv
do
  ffmpeg -hide_banner -h encoder=${encoder}    > ./videos/source/encoders/encoder_${encoder}.txt
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
  ffmpeg -hide_banner -h filter=${filter}    > ./videos/source/filters/filter_${filter}.txt
done

```

[FFmpeg Filters Documentation](https://ffmpeg.org/ffmpeg-filters.html#Examples-91)

### assets の初期化

```bash
$ du -sh .git
263M    .git

```

変更オブジェクトがない状態で実施する必要がある

```bash
git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch -r assets/' -- --all
git gc --aggressive --prune=now
git push --all --force origin

mkdir -p assets
touch assets/.gitkeep

```

### データを利用する

#### 解凍

```bash
mkdir -p logs
tar -xvf logs_archive.tar.xz -C logs/

```

#### 圧縮

```bash
tar -Jcvf logs_archive.tar.xz logs/

```

### 生データのダウンロード

今回は CC-BY で配布されている [Films - Blender Studio](https://studio.blender.org/films/) を利用する。  
ミラーとして [Xiph.org :: Test Media](https://media.xiph.org/) で配布されているのでこちらから元 png 画像をダウンロードした。

スクリプトにまとめてあるため `videos/source/bbb_download.sh` を参照。  
エンコードした、Reference 動画のダウンロードは `videos/source/reference_downloads.sh` を参照。

| Name                                          |           aspect | License                                                                 | Description    |
| :-------------------------------------------- | ---------------: | :---------------------------------------------------------------------- | :------------- |
| [Big Buck Bunny](http://www.bigbuckbunny.org) |   16:9 1920x1080 | [CC BY 3.0](https://peach.blender.org/about/)                           | 明るめのアニメ |
| [Sintel](https://durian.blender.org/)         | 2.35:1 1920x 818 | [CC BY 3.0](https://durian.blender.org/sharing/)                        | 暗めのアニメ   |
| [Tears of Steel](https://mango.blender.org/)  | 2.40:1 1920x 800 | [CC BY 3.0](https://mango.blender.org/sharing/)                         | SF系           |
| Army                                          |   16:9 1920x1080 | [Pixabay Content License](https://pixabay.com/service/license-summary/) | 自然 陸 実写   |
| Navy                                          |   16:9 1920x1080 | [Pixabay Content License](https://pixabay.com/service/license-summary/) | 自然 海 実写   |
| Air                                           |   16:9 1920x1080 | [Pixabay Content License](https://pixabay.com/service/license-summary/) | 自然 空 実写   |

実写の映像については Pixabay で提供されている再配布可能な映像に 解像度, fps, フレーム番号 を記載することでオリジナリティがあると思う

* Army Edition ～ Special Thanks to the creators on Pixabay ～
  * [0:00.00 - 0:14.45](https://pixabay.com/videos/canyon-river-mist-early-morning-226762/)
  * [0:14.48 - 0:24.46](https://pixabay.com/videos/trees-lake-fall-reflection-water-186405/)
  * [0:24.49 - 0:39.44](https://pixabay.com/videos/grand-canyon-river-mountains-nature-185678/)
  * [0:39.47 - 0:54.45](https://pixabay.com/videos/poppy-violet-blossoms-flower-field-167027/)
  * [0:54.49 - 1:09.47](https://pixabay.com/videos/canyon-water-fluent-rock-fall-94005/)
  * [1:09.50 - 1:24.48](https://pixabay.com/videos/lava-volcano-lava-flow-fire-crater-219833/)
  * [1:24.52 - 1:39.50](https://pixabay.com/videos/lava-volcano-lava-flow-fire-crater-219834/)
  * [1:39.53 - 1:49.94](https://pixabay.com/videos/mountains-sea-of-clouds-hotakadake-232408/)

* Navy ～ Special Thanks to the creators on Pixabay ～
  * [0:00.00 - 0:14.98](https://pixabay.com/videos/beach-secluded-sand-bay-ocean-sea-10884/)
  * [0:15.02 - 0:26.99](https://pixabay.com/videos/lake-fireworks-night-view-city-225661/)
  * [0:27.03 - 0.42.01](https://pixabay.com/videos/sea-ocean-animal-wild-wildlife-13704/)
  * [0:42.04 - 0:57.02](https://pixabay.com/videos/sea-ocean-seagulls-birds-sunset-140111/)
  * [0:57.06 - 1:09.87](https://pixabay.com/videos/nature-waves-ocean-sea-rock-31377/)
  * [1:09.90 - 1:19.88](https://pixabay.com/videos/jellyfish-sea-dangerous-underwater-26818/)
  * [1:19.91 - 1:34.93](https://pixabay.com/videos/sea-ocean-nhatrang-vietnam-173374/)
  * [1:34.96 - 1:49.94](https://pixabay.com/videos/sea-lion-wildlife-ocean-sea-life-139246/)

* Air Edition ～ Special Thanks to the creators on Pixabay ～
  * [0:00.00 - 0:09.91](https://pixabay.com/videos/volcano-nature-iceland-landscape-253436/)
  * [0:09.94 - 0:34.90](https://pixabay.com/videos/crane-heron-bird-path-flying-27279/)
  * [0:34.93 - 0:53.69](https://pixabay.com/videos/clouds-cumulus-weather-blue-sky-68254/)
  * [0:53.72 - 1:19.98](https://pixabay.com/videos/hot-air-balloon-ballooning-start-167/)
  * [1:20.01 - 1:49.94](https://pixabay.com/videos/volcano-sea-active-volcano-danger-200214/)
