# Bast parameter hunting

h264_qsv, hevc_qsv, av1_qsv のエンコードパラメータで容量が小さく、 VMAF が優れているパラメータを模索する方法。

## Environment

## Global

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

### -b_strategy

Strategy to choose between I/P/B-frames (from -1 to 1) (default -1)  
B-Frame の挿入位置を適応補完で決定する  
`-b_strategy 1` を設定することでファイルサイズが圧縮される、 `-preset:v veryslow` ではデフォルトで On の模様
