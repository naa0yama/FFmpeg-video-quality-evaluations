# Bast parameter hunting

h264_qsv, hevc_qsv, av1_qsv のエンコードパラメータで容量が小さく、 VMAF が優れているパラメータを模索する方法。

## Environment

## 現状のベスト

### h264_qsv

```bash
>  File size, bitrate, compress_rate, ssim_harmonic_mean,vmaf_min, vmaf_harmonic_mean
> 128,750.08, 8581.91,          0.50,                  1,   76.40,              96.61 (default)
> 108,452.88, 7228.99,          0.58,               0.99,   73.42,              95.70 本設定

ffmpeg -y -threads 4 -hide_banner -ignore_unknown -fflags +discardcorrupt+genpts -analyzeduration 30M -probesize 100M \
    -hwaccel_output_format qsv \
    -map 0:v -hwaccel qsv -c:v mpeg2_qsv -i base.mkv \
    -c:v h264_qsv -preset:v veryslow \
    -global_quality 25 -look_ahead 1 -look_ahead_depth 60 -look_ahead_downsampling off \
    -aspect 16:9 -gop 256 -bf 16 -refs 9 -b_strategy 1 \
    -color_range tv -color_primaries bt709 -color_trc bt709 -colorspace bt709 -max_muxing_queue_size 4000 \
    -movflags faststart -f mkv \
    -map 0:a -c:a aac -ar 48000 -ab 256k -ac 2 -bsf:a aac_adtstoasc \
    \
    out.mkv

```

### hevc_qsv

hevc_qsv は VMAF min/mean の値から h264_qsv と同程度にすると `-global_quality 22` が基準になりそうためこれを使ってテストする  
それでも h264 に比べて 38% 圧縮されるのは優秀と思う。

```bash
h264_qsv -global_quality 25 128,750kB, VMAF min/mean 76.400/96.610
hevc_qsv -global_quality 22  78,567kB, VMAF min/mean 77.739/96.204

ffmpeg -y -threads 4 -hide_banner -ignore_unknown -fflags +discardcorrupt+genpts -analyzeduration 30M -probesize 100M \
    -hwaccel_output_format qsv \
    -map 0:v -hwaccel qsv -c:v mpeg2_qsv -i videos/source/BBB_JapanTV_MPEG-2_1920x1080_30p.m2ts \
    -c:v hevc_qsv -preset:v veryslow \
    -global_quality 22 -look_ahead 1 -bf 14 -refs 8 -extbrc 1 -look_ahead_depth 60 \
    -aspect 16:9 -gop 256 -bf 14 -refs 8 -b_strategy 1 \
    -color_range tv -color_primaries bt709 -color_trc bt709 -colorspace bt709 -max_muxing_queue_size 4000 \
    -movflags faststart -f mkv \
    -map 0:a -c:a aac -ar 48000 -ab 256k -ac 2 -bsf:a aac_adtstoasc \
    \
    out.mkv

```

```bash
# LA-ICQ
ffmpeg -loglevel verbose -y -threads 4 -hwaccel_output_format qsv -hwaccel qsv \
  -c:v mpeg2_qsv -i videos/dist/hevc_qsv-bf-refs/base.mkv \
  -global_quality 22 -look_ahead 1 -bf 14 -refs 8 \
  -extbrc 1 -look_ahead_depth 40 -c:v hevc_qsv -preset:v veryslow -f null -




ffmpeg -loglevel verbose -y -threads 4 -hwaccel_output_format qsv -hwaccel qsv \
  -c:v mpeg2_qsv -i videos/dist/hevc_qsv-bf-refs/base.mkv \
  -global_quality 22 -look_ahead_depth 40 -bf 14 -refs 8 \
  -c:v hevc_qsv -preset:v veryslow -f null -

```

```bash
  -c:v hevc_nvenc -preset slow -profile:v main10 -pix_fmt yuv420p10le 
  -bf 3 -refs 9
  -color_range tv -color_primaries bt709 -color_trc bt709 -colorspace bt709
  -vf yadif=mode=send_frame:parity=auto:deint=all,scale=w=-2:h=720 -max_muxing_queue_size 4000
  -movflag faststart -f mp4
  -map 0:a -c:a aac -ar 48000 -ab 256k -ac 2 -bsf:a aac_adtstoasc

  '-hide_banner', '-ignore_unknown',
  '-fflags', '+discardcorrupt+genpts', '-analyzeduration', '30M', '-probesize', '100M',
  '-map', '0:v', '-aspect', '16:9', '-c:v', 'hevc_nvenc', '-preset', 'slow', '-profile:v', 'main10',
  '-pix_fmt', 'yuv420p10le', '-rc:v', 'constqp', '-rc-lookahead', 20, '-spatial-aq', 0, '-temporal-aq', 1,
  '-multipass', 'qres', '-g', 250, '-b_ref_mode', 'each', '-bf', 3, '-refs', 9,
  '-color_range', 'tv', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
  '-vf', 'yadif=mode=send_frame:parity=auto:deint=all,scale=w=-2:h=720',
  '-max_muxing_queue_size', 4000,
  '-tag:v', 'hvc1', '-movflags', 'faststart', '-f', 'mp4',

  '-map', '0:a'
  '-c:a', 'aac', '-ar', '48000', '-ab', '256k', '-ac', '2'
  '-bsf:a', 'aac_adtstoasc'

```

### av1_qsv

## 画質探索の極意

私の知識で、簡単に動画ファイルの圧縮について記述します。  
[FFmpeg](https://www.ffmpeg.org) を利用します、 Windows などでは [HandBrake](https://handbrake.fr) など GUI で優れたエンコードソフトウェアがありますが、私の環境では Linux を主に利用しており、 Linux/Windows で同じ設定を利用出来ないと品質を維持して利用することが出来ません。  

「動画の圧縮」と一言で言っても方法が多く、広義の方法として言われる事が多いため実現したい事を定義する。世の中には地上波放送を録画して楽しむ文化がある。総称として DTV が用いられるため以下はそうする。 DTV は地上波放送を録画する関係で MPEG-2 のコーディックで配信されてくる音声、映像データを保存するため 7GB/時間となる。  
そのため、アニメやドラマを全録するような利用をすると 2600番組/年程度録画することになり単純な容量では 18TB 程度必要になる。これでは毎年高額な HDD を足す運用になり維持管理が難しいため映像を圧縮して容量を削減するのが目的である。

映像を圧縮するには codec を指定する、今回は Intel QSV を利用するため h264, hevc, av1 に対応しており圧縮率は h264 -> hevc -> av1 の順番でよくなり秒間あたりの bitrate が削減できるため動画全体として容量を圧縮できる。一方、圧縮時間は圧縮率が高い codec になるほど時間がかかるため av1 が最も優れているが、処理時間とトレードオフになる事もある。

エンコードすると多少なりとも映像は劣化する。がそれを定量的に確認する術がなく、「なんか画質悪くなった」というようなケースがあったんではなかろうか。そのため今回は結構なパターンを検証することもあり [VMAF](https://github.com/Netflix/vmaf/tree/master) を利用したスコアを確認する。 VMAF のスコアは 1080p をベースに算出され、 0-100 での数値で表記される。 全フレームの平均が採用されるが、最低値を確認する方法として `min` も存在するがこれは フレームに対して記録された最低値のため容易に 0 が記録される事がある。オプションを設定することで 調和平均(`harmonic_mean`) を確認することができる。のでこちらを利用する。

テストの目標は平均 VMAF 96 以上、容量はできるだけ小さくを目標にする。  
アニメ 1話 200MB 以下、1クオーター 500GB 前後になるようにしたい。  

FFmpeg を利用して圧縮する場合は GOP, B-Frame, 参照 B-Frame あたりのオプションが効いてくる。調べた限りでは h264_qsv の設定は `-g 256 -bf 2 -refs 3` である。 GOP は必要十分であるので変更せず、 `-bf`, `-refs` の設定を詰める事になるだろう。

画質、 VMAF については Intel QSV を利用するなら LA-ICQ (Look-Ahead Intelligent Constant Quality) を前提に考えると良いだろう。 FFmpeg で利用する場合は `-global_quality <int>` `-look_ahead 1` を設定すると LA-ICQ でエンコードされる。  

Intel QSV のエンコードの特性として、 `libx264` でよく利用される CRF(Constant Rate Factor) と同等にしたければ `-global_quality 25` とすればよい。それだけでは各 Frame の下限値を設定出来ないため、`-min_qp_i`, `-min_qp_p`, `-min_qp_b` を設定し画質の低下を調整すると画質を向上させつつ容量の削減ができる

* q(Constant Quantizer): エンコード時に出る `q=XX.X` の数値で `-global_quality` に合わせて前後する。
  * `libx264` の `-crf 23` は `q=29.0` となる
  * LA-ICQ で合わせるなら `-global_quality 25` が同等となる。
* qp(Quantization Parameter): 固定品質パラメータ、各 Frame の最低値設定などで利用する

## Global

※詳細は、各パラメーターに譲るがが抜粋

| type     | option                                    | `<default>, <>`           | Description                                                                       |
| :------- | :---------------------------------------- | :------------------------ | :-------------------------------------------------------------------------------- |
| Global   | `-y`                                      |                           | 確認せずに上書きする                                                              |
|          | `-threads 4`                              | `<cpu core>*1.5`          | FFmpeg のスレッド数を指定、試験環境は VMAF の関係で超多コア(60 Core)のため指定    |
|          | `-hide_banner`                            |                           | バナーを非教示に                                                                  |
|          | `-ignore_unknown`                         |                           | 不明コーデックをコピーしない                                                      |
|          | `-fflags +discardcorrupt+genpts`          |                           | 破損パケットを破棄(`+discardcorrupt`), DTS が存在する場合は PTS を生成(`+genpts`) |
|          | `-analyzeduration 30M`                    | 5M us(5秒)                | 映像解析時間を指定 (μs 単位)                                                      |
|          | `-probesize 100M`                         | 5MB                       | 映像解析容量の上限                                                                |
|          |                                           |                           |                                                                                   |
|          |                                           |                           |                                                                                   |
|          |                                           |                           |                                                                                   |
| Hardware | `-hwaccel_output_format qsv`              |                           | 出力フォーマットを Hardware QSV にする                                            |
|          |                                           |                           |                                                                                   |
| Input    | `-hwaccel qsv -c:v mpeg2_qsv -i base.mkv` |                           | Intel QSV の decoder を指定し Input を読み込む                                    |
|          | `-map 0:v`                                |                           | 映像を input からマッピング                                                       |
|          | `-c:v h264_qsv`                           |                           |                                                                                   |
|          | `-preset:v veryslow`                      |                           | preset                                                                            |
|          | `-global_quality 25 -look_ahead 1`        |                           | LA-ICQ でエンコードする                                                           |
|          | `-look_ahead_depth 60`                    | 0, 0-100                  | 先行読み込みフレームを 60 枚(約2秒)にする                                         |
|          | `-look_ahead_downsampling off`            | unknown, (auto,off,2x,4x) | 先行読み込み時にダウンサンプリングをしない                                        |
|          | `-gop`                                    | 256                       | GOP長、Iフレーム間の距離                                                          |
|          | `-bf 16`                                  | 2                         | I-Frame と P-Frame 間の B-Frame の数                                              |
|          | `-refs 9`                                 | 3                         | B-Frame 動き補正を考慮する参照フレーム数                                          |
|          | `-b_strategy 1`                           | `-1`, 0, 1                | B-Frame を 参照 B-Frame として使用することを制御します。                          |
|          | `-aspect:v 16:9`                          |                           | アスペクト比を 16:9 に設定                                                        |
|          | `-movflags faststart`                     |                           | メタデータをファイルの先頭にする                                                  |
|          | `-tag:v hvc1`                             |                           | Apple 製品で再生出来ないため `hvc1` 方式であることを明示する (HEVC の時のみ)      |
|          | `-f mkv`                                  |                           | ファイルフォーマットは MKV にする                                                 |
|          |                                           |                           |                                                                                   |
| Audio    | `-c:a aac`                                |                           | AAC に変換                                                                        |
|          | `-ar 48000`                               |                           | サンプリングレート 48kHz                                                          |
|          | `-ab 256k`                                |                           | ビットレート 256kbps                                                              |
|          | `-bsf:a aac_adtstoasc`                    |                           | MPEG-2 から MPEG-4 に変更するオプション                                           |

* [FFmpeg Codecs Documentation](https://ffmpeg.org/ffmpeg-codecs.html#Global-Options-_002d_003e-MSDK-Options)
* [HWAccelIntro – FFmpeg](https://trac.ffmpeg.org/wiki/HWAccelIntro)
* [Hardware/QuickSync – FFmpeg](https://trac.ffmpeg.org/wiki/Hardware/QuickSync)
* [Hardware/VAAPI – FFmpeg](https://trac.ffmpeg.org/wiki/Hardware/VAAPI)

```bash
$ ffmpeg -loglevel debug -i base.mkv -c:v h264_qsv -global_quality 25 -look_ahead 1 -preset veryslow -f null -

[h264_qsv @ 0x6003e69b3bc0] Initialized an internal MFX session using hardware accelerated implementation
[h264_qsv @ 0x6003e69b3bc0] Using the intelligent constant quality with lookahead (LA_ICQ) ratecontrol method
[h264_qsv @ 0x6003e69b3bc0] profile: avc high; level: 40
[h264_qsv @ 0x6003e69b3bc0] GopPicSize: 256; GopRefDist: 4; GopOptFlag: closed; IdrInterval: 0
[h264_qsv @ 0x6003e69b3bc0] TargetUsage: 1; RateControlMethod: ICQ
[h264_qsv @ 0x6003e69b3bc0] ICQQuality: 25
[h264_qsv @ 0x6003e69b3bc0] NumSlice: 1; NumRefFrame: 3
[h264_qsv @ 0x6003e69b3bc0] RateDistortionOpt: OFF
[h264_qsv @ 0x6003e69b3bc0] RecoveryPointSEI: OFF
[h264_qsv @ 0x6003e69b3bc0] VDENC: ON
[h264_qsv @ 0x6003e69b3bc0] Entropy coding: CABAC; MaxDecFrameBuffering: 3
[h264_qsv @ 0x6003e69b3bc0] NalHrdConformance: OFF; SingleSeiNalUnit: ON; VuiVclHrdParameters: OFF VuiNalHrdParameters: OFF
[h264_qsv @ 0x6003e69b3bc0] FrameRateExtD: 1001; FrameRateExtN: 30000 
[h264_qsv @ 0x6003e69b3bc0] IntRefType: 0; IntRefCycleSize: 0; IntRefQPDelta: 0
[h264_qsv @ 0x6003e69b3bc0] MaxFrameSize: 783360; MaxSliceSize: 0
[h264_qsv @ 0x6003e69b3bc0] BitrateLimit: OFF; MBBRC: ON; ExtBRC: OFF
[h264_qsv @ 0x6003e69b3bc0] Trellis: auto
[h264_qsv @ 0x6003e69b3bc0] RepeatPPS: OFF; NumMbPerSlice: 0; LookAheadDS: 2x
[h264_qsv @ 0x6003e69b3bc0] AdaptiveI: OFF; AdaptiveB: OFF; BRefType:pyramid
[h264_qsv @ 0x6003e69b3bc0] MinQPI: 0; MaxQPI: 0; MinQPP: 0; MaxQPP: 0; MinQPB: 0; MaxQPB: 0
[h264_qsv @ 0x6003e69b3bc0] DisableDeblockingIdc: 0 
[h264_qsv @ 0x6003e69b3bc0] SkipFrame: no_skip
[h264_qsv @ 0x6003e69b3bc0] PRefType: default
[h264_qsv @ 0x6003e69b3bc0] TransformSkip: unknown 
[h264_qsv @ 0x6003e69b3bc0] IntRefCycleDist: 0
[h264_qsv @ 0x6003e69b3bc0] LowDelayBRC: OFF
[h264_qsv @ 0x6003e69b3bc0] MaxFrameSizeI: 0; MaxFrameSizeP: 0
[h264_qsv @ 0x6003e69b3bc0] ScenarioInfo: 0

```

### Encode type

Intel QSV では下記のエンコードモードに対応している

* CQP (Constant Quantization Parameter)
* ICQ (Intelligent Constant Quality)
* LA-ICQ (Look-Ahead Intelligent Constant Quality)
* VBR (Variable Bit Rate)

libx265 でおなじみ CRF(Constant Rate Factor) は QSV には存在しない  
画質は、 LA-ICQ が最も良く ICQ、CQP、VBR の順になる

* q / CRF は手元の環境でテストし VMAF min/mean が下限 70/93 を超えるパラメーターを採用する
* VBR はアーカイブ目的では用途に合わないためテストしていない
* `hevc_qsv`, `av1_qsv` では 2025/02 現在では LA_ICQ の実装はない
  * [[Bug]: VA_RC_ICQ not available in AV1 encoder on DG2 · Issue #1597 · intel/media-driver](https://github.com/intel/media-driver/issues/1597)
* [Encode Features for Intel® Discrete Graphics](https://www.intel.com/content/www/us/en/docs/onevpl/developer-reference-media-intel-hardware/1-0/features-and-formats.html#ENCODE-DISCRETE)
* MSSIM(Mean SSIM / 構造的類似性) 画像の類似性を計測する値、1に近いほうが元画像に近い

* [VMAF - Video Multi-Method Assessment Fusion](https://github.com/Netflix/vmaf/tree/master)
  * Netflix が配信映像の主観的品質評価を目的に開発したライブラリー
  * 機械学習を利用して人間の映像品質の識別を教師データとして学習しているため、人間の知覚に近い
  * 0-100 で算出され一般に 93-96 は元映像の見分けが付かず、 95 以上はオリジナルより余剰容量(Bitrate)となる
    * スコア差 2 は人間では見分けが付かず、3を超えると知覚が鋭敏な人は気づく (18人のテストで半分が気づく)

| codev       | BRC modes     | BBB / Nature | q / CRF |  File size |   bitrate | encode time | compress_rate | MSSIM | VMAF min/mean | Options            |
| :---------- | :------------ | :----------: | ------: | ---------: | --------: | ----------: | ------------: | ----: | ------------: | :----------------- |
| `libx264`   | CRF (default) |     BBB      |     *23 | 111,602.92 |  7,438.95 |    00:00:39 |          0.58 |  1.00 | 81.79 / 96.49 |                    |
|             |               |    Nature    |     *23 | 139,559.08 |  9,305.02 |    00:00:41 |          0.42 |  1.00 | 86.39 / 93.64 |                    |
|             |               |     BBB      |      27 |  57,195.14 |  3,812.37 |    00:00:37 |          0.79 |  1.00 | 74.89 / 93.24 |                    |
|             |               |    Nature    |      23 | 139,559.08 |  9,305.02 |    00:00:41 |          0.42 |  1.00 | 86.39 / 93.64 |                    |
|             |               |              |         |            |           |             |               |       |               |                    |
| `libx265`   | CRF (default) |     BBB      |     *28 | 129,002.66 |  8,598.74 |    00:02:45 |          0.52 |  1.00 | 80.72 / 96.82 |                    |
|             |               |    Nature    |     *28 | 141,539.03 |  9,437.04 |    00:03:13 |          0.41 |  1.00 | 81.82 / 92.88 |                    |
|             |               |     BBB      |      28 |  62,748.73 |  4,182.55 |    00:02:16 |          0.77 |  0.99 | 73.75 / 93.76 |                    |
|             |               |    Nature    |      22 | 159,526.35 | 10,636.33 |    00:03:22 |          0.33 |  1.00 | 83.54 / 93.73 |                    |
|             |               |              |         |            |           |             |               |       |               |                    |
| `libsvtav1` | CRF (default) |     BBB      |     *35 |  52,693.30 |  3,512.30 |    00:01:16 |          0.80 |  1.00 | 79.60 / 96.01 | -preset:v 6        |
|             |               |    Nature    |     *35 |  80,559.35 |  5,371.25 |    00:01:37 |          0.66 |  1.00 | 81.53 / 90.81 | -preset:v 6        |
|             |               |     BBB      |      47 |  15,252.00 |  1,016.63 |    00:01:17 |          0.94 |  0.99 | 73.09 / 93.10 | -preset:v 6        |
|             |               |    Nature    |      30 | 126,206.23 |  8,414.73 |    00:01:39 |          0.47 |  1.00 | 84.66 / 93.45 | -preset:v 6        |
|             |               |              |         |            |           |             |               |       |               |                    |
| `h264_qsv`  | CQP (default) |     BBB      |     *23 | 108,539.71 |  7,234.77 |    00:00:11 |          0.60 |  1.00 | 74.14 / 96.42 | -q:v 23            |
|             |               |    Nature    |     *23 | 132,860.40 |  8,858.39 |    00:00:11 |          0.44 |  1.00 | 83.08 / 92.77 | -q:v 23            |
|             |               |     BBB      |      27 |  57,243.75 |  3,815.61 |    00:00:11 |          0.79 |  0.99 | 62.90 / 93.67 | -q:v 27            |
|             |               |    Nature    |      22 | 160,570.95 | 10,705.98 |    00:00:11 |          0.33 |  1.00 | 85.55 / 94.18 | -q:v 22            |
|             | ICQ           |     BBB      |     *23 |            |           |             |               |       |               |                    |
|             |               |    Nature    |     *23 |            |           |             |               |       |               |                    |
|             | LA_ICQ        |     BBB      |     *23 |            |           |             |               |       |               |                    |
|             |               |    Nature    |     *23 |            |           |             |               |       |               |                    |
|             |               |              |         |            |           |             |               |       |               |                    |
| `hevc_qsv`  | CQP (default) |     BBB      |     *28 |            |           |             |               |       |               |                    |
|             |               |    Nature    |     *28 |            |           |             |               |       |               |                    |
|             | ICQ           |     BBB      |     *28 |            |           |             |               |       |               |                    |
|             |               |    Nature    |     *28 |            |           |             |               |       |               |                    |
|             |               |              |         |            |           |             |               |       |               |                    |
| `av1_qsv`   | CQP (default) |     BBB      |      97 |  36,428.38 |  2,428.15 |    00:00:11 |          0.86 |  0.99 | 70.21 / 93.27 | -q:v 97            |
|             |               |    Nature    |      57 | 140,222.14 |  9,349.23 |    00:00:11 |          0.41 |  1.00 | 84.96 / 93.06 | -q:v 57            |
|             | ICQ           |     BBB      |      28 |  51,367.01 |  3,423.90 |    00:00:12 |          0.81 |  0.99 | 71.60 / 93.76 | -global_quality 28 |
|             |               |    Nature    |      23 | 142,999.55 |  9,534.42 |    00:00:12 |          0.40 |  1.00 | 84.01 / 93.42 | -global_quality 23 |

* `h264_qsv`
  * CQP `bbb` VMAF min/mean 70/93 としようとしたら `-q:v 27` だが、 VMAF min が足りないため調整
* `av1_qsv`
  * CQP `bbb` はまだ `-q:v` を下げても行けるがサンプルに合わせた設定になりそうなため参考値
  * ICQ `nature` でも VMAF 値が足りないが、これ以上品質を高くしてもファイルサイズだけ嵩むためここで中止

```bash
CQP     -q:v 25
ICQ     -global_quality 25
LA-ICQ  -global_quality 25 -look_ahead 1
VBR     -b:v 8.5M -maxrate 10M

>        File size, bitrate, encode time, compress_rate, ssim_harmonic_mean,vmaf_min, vmaf_harmonic_mean
CQP      82,209.45, 5479.72,    00:00:11,          0.68,               0.99,   69.44,              95.31
ICQ     128,750.08, 8581.91,    00:00:12,          0.50,               1.00,   76.40,              96.61
LA-ICQ  128,750.08, 8581.91,    00:00:12,          0.50,               1.00,   76.40,              96.61  (default 以降はこれが基準)
VBR     118,807.07, 7919.15,    00:00:12,          0.54,               1.00,   79.76,              97.77

libx264 111,973.04, 7463.63,    00:00:40,          0.56,               1.00,   81.62,              96.49  "-crf 23"

```

#### CQP (Constant Quantization Parameter)

**Intel QSV での h264_qsv, hevc_qsv, av1_qsv のデフォルトモード**  
一定品質を維持する設定のため、単調なシーンでは過剰、複雑なシーンではビットレート不足となる

```bash
ffmpeg -hwaccel qsv -i input.mp4 \
    -c:v h264_qsv -preset veryslow \
    -q:v 25 \
    output.mp4

```

#### ICQ (Intelligent Constant Quality)

このモードは画質を一定に保ちながら、シーンの複雑さに応じてビットレートを調整します。

```bash
ffmpeg -hwaccel qsv -i input.mp4 \
  -c:v h264_qsv -preset veryslow \
  -global_quality 25 \
  output.mp4

```

#### LA-ICQ (Look-Ahead Intelligent Constant Quality)

先読み解析により画質制御がされ適切なビットレートを割り当てることで、画質と容量のバランスを取ります  
**`hevc_qsv`, `av1_qsv` では未実装のため利用出来ない**

```bash
ffmpeg -hwaccel qsv -i input.mp4 \
  -c:v h264_qsv -preset veryslow \
  -look_ahead 1 -global_quality 25 \
  output.mp4

```

#### VBR (Variable Bit Rate)

平均ビットレートによる制御のため画質に関係なく、同容量のサイズにするには優れている  
VBR は正直やる意味が無いので計測しない

```bash
ffmpeg -hwaccel qsv -i input.mp4 \
  -c:v h264_qsv -preset veryslow \
  -b:v 8.5M -maxrate 10M \
  output.mp4

```

### -preset

`-preset` は非常に強力で、デフォルトは `medium` が利用される `veryslow` に向かうにつれより高負荷(時間がかかる)処理が追加されていき、高圧縮・低用量となる。今回は Intel QSV を利用して Hardware offload するため `veryslow` を利用する

```bash
- -global_quality 25 -look_ahead 1

>  preset,    File size, bitrate, encode time, compress_rate, ssim_harmonic_mean,vmaf_min, vmaf_harmonic_mean
 veryfast,   120,911.39, 8059.42,    00:00:06,          0.53,                  1,   75.75,              95.96
   medium,   119,872.17, 7990.15,    00:00:07,          0.53,                  1,   75.81,              96.00
 veryslow,   128,750.08, 8581.91,    00:00:12,          0.50,                  1,   76.40,              96.61  (default 以降はこれが基準)

```

### -bf -refs

`-bf` は B-Frame の数、 `-refs` は B-Frame 作成時に動き補正を考慮するフレーム数である。  
試しに、 `-bf {1..20}`, `-refs {1..20}` を出力したのが下記のグラフ。

どの `-bf` でも `-refs` の関係は下記

* `-refs 1`: 容量と bitrate が急上昇する
* `-refs 2-5`: 容量と bitrate が一定になる
* `-refs 6-15`: 容量と bitrate が一定になる、 `-refs 2-5` より容量が削減できる
* `-refs 16` 以降は min VMAF の劣化が著しいため利用しない

![-bf -refs](3aaa346e4b39.png)

そのため、下記を採用する

```bash
- -global_quality 25 -look_ahead 1 -bf 16 -refs 9

>  File size, bitrate, compress_rate, ssim_harmonic_mean,vmaf_min, vmaf_harmonic_mean
> 128,750.08, 8581.91,          0.50,                  1,   76.40,              96.61 (default)
> 108,452.88, 7228.99,          0.58,               0.99,   73.42,              95.70

```

また、今回採用した `-bf 16 -refs 9` を設定すると `q=33.0` になるためこの後 `qp` を設定する場合は考慮が必要

```text
-global_quality 25 -look_ahead 1                 ICQQuality: 25, q=28.0
-global_quality 25 -look_ahead 1 -bf 16 -refs 9, ICQQuality: 25, q=33.0
-global_quality   q=
13                21
14                22
15-16             24
17                25
18                26
19                27
20-23             26
24-25             28
26                29
27                30
28                31
29-31             33
32                34
33                35

```

#### hevc_qsv

```text
>  File size, bitrate, compress_rate, ssim_harmonic_mean,vmaf_min, vmaf_harmonic_mean
>  80,452.69, 5362.62,          0.69,                  1,   77.74,               96.20 (default)
>  76,031.02, 5067.89,          0.70,                  1,   76.75,               95.93 -bf 14 -refs 8 (-bf 16 -refs 9 の比率に近い)

```

hevc_qsv では `-bf 16` 以上は `-refs 3` 以上には出来ない、 `-bf 15 -refs 20` は通る

```bash
$ ffmpeg -y -threads 4 -hwaccel_output_format qsv \
    -hwaccel qsv -c:v mpeg2_qsv -i videos/dist/hevc_qsv-bf-refs/base.mkv \
    -global_quality 22 -look_ahead 1 -bf 16 -refs 4 -c:v hevc_qsv -preset:v veryslow -f null -

[hevc_qsv @ 0x59894042fec0] Invalid FrameType:0.
[vost#0:0/hevc_qsv @ 0x5989404311c0] Error submitting video frame to the encoder
[vost#0:0/hevc_qsv @ 0x5989404311c0] Error encoding a frame: Invalid data found when processing input
[vost#0:0/hevc_qsv @ 0x5989404311c0] Task finished with error code: -1094995529 (Invalid data found when processing input)
[vost#0:0/hevc_qsv @ 0x5989404311c0] Terminating thread with return code -1094995529 (Invalid data found when processing input)
[out#0/null @ 0x598940435800] video:8024KiB audio:0KiB subtitle:0KiB other streams:0KiB global headers:0KiB muxing overhead: unknown
frame=   67 fps=0.0 q=-0.0 Lsize=N/A time=00:00:02.16 bitrate=N/A speed=6.04x    
Conversion failed!

```

### -b_strategy

Strategy to choose between I/P/B-frames (from -1 to 1) (default -1)  
B-Frame の挿入位置を適応補完で決定する  
`-b_strategy 1` を設定することでファイルサイズが圧縮される、 `-preset:v veryslow` ではデフォルトで On の模様

```bash
- -global_quality 25 -look_ahead 1 -bf 16 -refs 9 -b_strategy 0
- -global_quality 25 -look_ahead 1 -bf 16 -refs 9 -b_strategy 1

> -b_strategy,  File size, bitrate, compress_rate, ssim_harmonic_mean,vmaf_min, vmaf_harmonic_mean
>              128,750.08, 8581.91,          0.50,                  1,   76.40,              96.61 (normal)
>           0, 143,151.53, 9541.84,          0.44,               0.99,   74.70,              95.80
>           1, 108,452.88, 7228.99,          0.58,               0.99,   73.42,              95.70

```

### -min_qp_i, -min_qp_p, -min_qp_b

* `-min_qp_i`: Maximum video quantizer scale for I frame
* `-min_qp_p`: Maximum video quantizer scale for P frame
* `-min_qp_b`: Maximum video quantizer scale for B frame

`-min_qp_i`, `-min_qp_p`, `-min_qp_b` を設定する  
デフォルトの設定で出力した、データだと `-global_quality 20` までは VMAF mean の数値がブレないためそのあたりが品質の上限が良さそう。  
qp は `-global_quality 25` を下回って設定しても効果が無いようである。また、 `-global_quality 25 -look_ahead 1 -bf 16 -refs 9` を使った場合。 q=33.0 となるため q=28 - q=38 をターゲットに試験した。  
結果は、下記の通りだが、 `-min_qp_i` の上下のみで VMAF min, VMAF mean の変化があるため `-min_qp_p`, `-min_qp_b` の効果を確認出来なかった。また、I25 - I29 でのファイルサイズ差は 約10MBで、そこまで頑張って設定しても旨味がなさそう

```text
>               File size, bitrate, compress_rate, ssim_harmonic_mean,vmaf_min, vmaf_harmonic_mean
>              128,750.08, 8581.91,          0.50,                  1,   76.40,              96.61 (normal)
>              108,452.88, 7228.99,          0.58,               0.99,   73.42,              95.70 (default)

> I25:P25:B25  108,438.35, 7228.02,          0.58,               0.99,   73.42,              95.70
> I26:P26:B26  108,310.00, 7219.46,          0.58,               0.99,   73.14,              95.68
> I27:P27:B27  107,448.87, 7162.06,          0.58,               0.99,   72.88,              95.50
> I28:P28:B28  102,625.93, 6840.59,          0.60,               0.99,   71.42,              95.15
> I29:P29:B29   98,810.38, 6586.26,          0.61,               0.99,   70.16,              94.69

ここから下は使えないだろう...
> I30:P30:B30   90,632.87, 6041.18,          0.65,               0.99,   68.60,              93.94
> I31:P31:B31   82,588.07, 5504.95,          0.68,               0.99,   67.26,              93.05
> I32:P32:B32   73,254.13, 4882.79,          0.71,               0.99,   64.29,              91.99
> I33:P33:B33   63,608.83, 4239.88,          0.75,               0.99,   59.49,              90.55
> I34:P34:B34   51,465.86, 3430.49,          0.80,               0.98,   55.26,              88.75
> I35:P35:B35   43,258.03, 2883.39,          0.83,               0.98,   51.50,              87.05
> I36:P36:B36   35,406.80, 2360.06,          0.86,               0.98,   47.29,              84.96
> I37:P37:B37   28,417.56, 1894.19,          0.89,               0.98,   43.52,              82.69
> I38:P38:B38   23,438.38, 1562.30,          0.91,               0.97,   39.65,              80.15

```

### `-look_ahead_depth`, `-look_ahead_downsampling`

* `-look_ahead_depth` は LA-ICQ で適切な bitrate 割当のために設定する、が `-preset:v veryslow` の場合は設定されているようで、動作に変更が無い
* `-look_ahead_downsampling` こちらも同じ、でサンプルでは効果がなかった
* hevc_qsv の場合は `-extbrc 1 -look_ahead_depth 60` としているするひつよがあった

全くのズレがない、横一列

### -threads

[FFmpeg Threads Command: 品質とパフォーマンスに与える影響 - ストリーミング ラーニング センター](https://streaminglearningcenter.com/blogs/ffmpeg-command-threads-how-it-affects-quality-and-performance.html)

ffmpeg の `-threads X` でフレームあたりの VMAF 品質低下があると記事を見たので計測、結果全く誤差が無い
完全一致なので thread による影響はない

* ffmpeg 7.1
* Lavc61.19.100
* VMAF 3.0.0, vmaf_v0.6.1

|            |            auto (min) |        thread 1 (min) |        thread 4 (min) |        thread 8 (min) |       thread 15 (min) |
| :--------- | --------------------: | --------------------: | --------------------: | --------------------: | --------------------: |
| mpeg2ts    | 93.594580 (66.704512) | 93.594580 (66.704512) | 93.594580 (66.704512) | 93.594580 (66.704512) | 93.594580 (66.704512) |
| libx264    | 90.300860 (72.486087) | 90.300860 (66.067915) | 90.300860 (66.067915) | 90.300860 (66.067915) | 90.300860 (66.067915) |
| libx265    | 88.317820 (71.885449) | 88.317820 (65.279336) | 88.317820 (65.279336) | 88.317820 (65.279336) | 88.317820 (65.279336) |
| libaom-av1 | 90.866412 (72.324044) | 90.866412 (65.867695) | 90.866412 (65.867695) | 90.866412 (65.867695) | 90.866412 (65.867695) |

### 使用しない

* B-Frame を使うと使用不可
  * `-int_ref_type`
  * `-p_strategy`
  * `-adaptive_b`
  * `-adaptive_i`

* 設定が byte 単位なので今回は利用せず
  * `-max_frame_size`
  * `-max_frame_size_i`
  * `-max_frame_size_p`
  * `-max_slice_size`
  * `-bitrate_limit`

* 数値に違いがないため、効果がわからず
  * `hevc_qsv`
    * `-rdo`
    * `-mbbrc`
    * `-extbrc`
    * `-b_strategy`
