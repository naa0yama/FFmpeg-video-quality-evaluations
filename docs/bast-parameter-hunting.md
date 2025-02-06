# Bast parameter hunting

h264_qsv, hevc_qsv, av1_qsv のエンコードパラメータで容量が小さく、 VMAF が優れているパラメータを模索する方法。

## Environment

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

|                                         |          | Description                                              |
| :-------------------------------------- | :------- | :------------------------------------------------------- |
| `-global_quality <int>` `-look_ahead 1` |          |                                                          |
| `-look_ahead_depth`                     |          |                                                          |
| `-look_ahead_downsampling`              |          |                                                          |
| `-gop`                                  |          |                                                          |
| `-bf`                                   |          |                                                          |
| `-refs`                                 |          |                                                          |
| `-min_qp_i`                             | -1 - 51  | Maximum video quantizer scale for I frame                |
| `-min_qp_p`                             | -1 - 51  | Maximum video quantizer scale for P frame                |
| `-min_qp_b`                             | -1 - 51  | Maximum video quantizer scale for B frame                |
|                                         |          |                                                          |
|                                         |          |                                                          |
|                                         |          |                                                          |
|                                         |          |                                                          |
| `-preset`                               | `medium` | preset                                                   |
| `-rdo`                                  | `-1`     | レート歪みの最適化を有効にする                           |
| `-mbbrc`                                | `-1`     | マクロビットレベルのビットレート制御                     |
| `-extbrc`                               | `-1`     | 拡張ビットレート制御                                     |
| `-b_strategy`                           | `-1`     | B-Frame を 参照 B-Frame として使用することを制御します。 |

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

### -bf -refs

### -b_strategy

Strategy to choose between I/P/B-frames (from -1 to 1) (default -1)  
B-Frame の挿入位置を適応補完で決定する  
`-b_strategy 1` を設定することでファイルサイズが圧縮される、 `-preset:v veryslow` ではデフォルトで On の模様

## h264_qsv

h264_qsv では標準設定で、下記に設定されているようだった。
そのため、 `-g` は十分であり、 `-bf`, `-refs` のいい感じの場所を模索したところ、旨味は `-bf 16 -refs 9` あたりが最も効率が良い、 `-preset` での変化がなかったことから h264_qsv のデフォルトだと思われる。

* `-g 256`
* `-bf 2`
* `-refs 3`

```bash
# テストしたコマンド
ffmpeg -y -threads 4 -hwaccel_output_format qsv \
  -hwaccel qsv -c:v mpeg2_qsv -i ./videos/dist/base.mkv \
  -global_quality 13 -look_ahead 1 -c:v h264_qsv \
  -preset:v veryslow ./videos/dist/<outfile.mkv>

```
