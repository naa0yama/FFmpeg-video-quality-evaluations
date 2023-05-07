# FFmpeg-video-quality-evaluations
Video encoding quality evaluation project using VMAF and SSIM

## tools

* [plotbitrate](https://github.com/zeroepoch/plotbitrate)
* FFmpeg
* FFprobe

## 準備

### Intel HD (vaapi, Quick Sync Video)

```bash
sudo apt install intel-media-va-driver vainfo

```

* version check

```bash
sudo vainfo

```

* output

```bash
error: can't connect to X server!
libva info: VA-API version 1.10.0
libva info: Trying to open /usr/lib/x86_64-linux-gnu/dri/iHD_drv_video.so
libva info: Found init function __vaDriverInit_1_10
libva info: va_openDriver() returns 0
vainfo: VA-API version: 1.10 (libva 2.10.0)
vainfo: Driver version: Intel iHD driver for Intel(R) Gen Graphics - 21.1.1 ()
vainfo: Supported profile and entrypoints
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
      VAProfileVP8Version0_3          : VAEntrypointVLD
      VAProfileHEVCMain               : VAEntrypointVLD
      VAProfileHEVCMain10             : VAEntrypointVLD
      VAProfileVP9Profile0            : VAEntrypointVLD
      VAProfileVP9Profile2            : VAEntrypointVLD
```

### NVIDIA

Ref: [CUDA Toolkit 12.1 Update 1 Downloads | NVIDIA Developer](https://developer.nvidia.com/cuda-downloads)

`sudo apt-get -y install cuda` の箇所はドライバーのみインストールされれば問題ないため変更しています

```bash
# Download Installer for Linux Debian 11 x86_64
wget https://developer.download.nvidia.com/compute/cuda/repos/debian11/x86_64/cuda-keyring_1.0-1_all.deb
sudo dpkg -i cuda-keyring_1.0-1_all.deb
sudo add-apt-repository contrib
sudo apt-get update
sudo apt-get -y install cuda-drivers

```

* version check

```bash
sudo nvidia-smi

```

* output

```bash
Sat Apr 29 08:49:28 2023       
+---------------------------------------------------------------------------------------+
| NVIDIA-SMI 530.30.02              Driver Version: 530.30.02    CUDA Version: 12.1     |
|-----------------------------------------+----------------------+----------------------+
| GPU  Name                  Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf            Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|                                         |                      |               MIG M. |
|=========================================+======================+======================|
|   0  NVIDIA GeForce RTX 2060 S...    On | 00000000:01:00.0 Off |                  N/A |
|  0%   40C    P8               16W / 175W|      1MiB /  8192MiB |      0%      Default |
|                                         |                      |                  N/A |
+-----------------------------------------+----------------------+----------------------+
                                                                                         
+---------------------------------------------------------------------------------------+
| Processes:                                                                            |
|  GPU   GI   CI        PID   Type   Process name                            GPU Memory |
|        ID   ID                                                             Usage      |
|=======================================================================================|
|  No running processes found                                                           |
+---------------------------------------------------------------------------------------+
```

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

**please restart**

### Device recognition confirmation

| dev                   | Hardware               |
| :-------------------- | :--------------------- |
| `/dev/dri/renderD128` | Intel UHD Graphics 630 |
| `/dev/dri/renderD129` | GeForce RTX 2060 SUPER |

```bash
# ls -l /dev/dri/by-path/
total 0
lrwxrwxrwx 1 root root  8 Apr 28 23:39 pci-0000:00:02.0-card -> ../card0
lrwxrwxrwx 1 root root 13 Apr 28 23:39 pci-0000:00:02.0-render -> ../renderD128
lrwxrwxrwx 1 root root  8 Apr 28 23:39 pci-0000:01:00.0-card -> ../card1
lrwxrwxrwx 1 root root 13 Apr 28 23:39 pci-0000:01:00.0-render -> ../renderD129

```

```bash
# lspci -s 0000:00:02.0
00:02.0 VGA compatible controller: Intel Corporation CometLake-S GT2 [UHD Graphics 630]

# lspci -s 0000:01:00.0
01:00.0 VGA compatible controller: NVIDIA Corporation TU106 [GeForce RTX 2060 SUPER] (rev a1)
```

### SystemD change multi-user.target

```bash
# Check current settings
$ systemctl get-default
graphical.target

# Change to multi-user.target
$ sudo systemctl set-default multi-user.target

```

### Docker Engine

Ref: [Install Docker Engine | Docker Documentation](https://docs.docker.com/engine/install/)

```bash
curl https://get.docker.com | sh \
  && sudo systemctl --now enable docker

```

### Container Toolkit

詳しくは記事を参考にして欲しいが、ホストマシーンにインストールされたDriver類を自動でmountしてくるためこれを使わないとうまく動かなかった。

[NVIDIA Container Toolkit (NVIDIA Docker) は何をしてくれるか - Qiita](https://qiita.com/tkusumi/items/f275f0737fb5b261a868)
[NVIDIA Docker って今どうなってるの？ (20.09 版) | by Kuninobu Sasaki | NVIDIA Japan | Medium](https://medium.com/nvidiajapan/nvidia-docker-%E3%81%A3%E3%81%A6%E4%BB%8A%E3%81%A9%E3%81%86%E3%81%AA%E3%81%A3%E3%81%A6%E3%82%8B%E3%81%AE-20-09-%E7%89%88-558fae883f44)

インストール自体は [Installation Guide — NVIDIA Cloud Native Technologies documentation](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html#docker) の Docker の箇所をすれば問題ない

```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID) \
      && curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
      && curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
            sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
            sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

```

## Sample move

Internet archive host download

```bash
cd videos/source
wget 'https://archive.org/download/BigBuckBunnyFULLHD60FPS/Big%20Buck%20Bunny%20-%20FULL%20HD%2060FPS.mp4'
mv Big\ Buck\ Bunny\ -\ FULL\ HD\ 60FPS.mp4 bbb_original.mp4

```

* check sha256

```bash
$ sha256sum bbb_original.mp4 
658cb0019af04f7016b9686a6329e9120f97cb7d0cb67ab5fa0af6dd4f519e40  bbb_original.mp4

```


* crf
  * 18-34
  * 23(libx264 default)
  * 28(libx265 default)

* hwaccel
  * cuda(nvenv)
  * vaapi
  * qsv

* encoders
  * x264
    * libx264
    * h264_nvenc
    * h264_qsv
    * h264_vaapi
  * x265
    * libx265
    * hevc_nvenc
    * h265_qsv
    * h265_vaapi

```bash
# FFmpeg
cd ~/FFmpeg-video-quality-evaluations/tools/ffmpeg-vqe/ && docker build -t ffmpeg-vqe . && cd ../../

docker run --rm -it --gpus all \
  -v $PWD/videos/source:/source \
  -v $PWD/videos/dist:/dist \
  -v $PWD/tools/ffmpeg-vqe:/opt \
  --device "/dev/dri:/dev/dri" \
  ffmpeg-vqe \
  python3 /app/entrypoint.py --encode && \
  bash /app/plotbitrate.sh

```

* crf(constant quality mode)
* qp(Constant quantization parameter)
* cq(constant quality mode in VBR)

* preset は標準, 標準から -3, +3 を試す

| codec       |  crf  |  qp   |      cq       | preset default        | 試す preset                         |
| :---------- | :---: | :---: | :-----------: | :-------------------- | :---------------------------------- |
| **libx264** |   O   |   O   |               | medium                | veryfast ,medium, veryslow          |
| h264_nvenc  |       |   O   |       O       | 15(p4)                | 12(p2), 15(p4), 18(p7)              |
| h264_qsv    |       |       |               | 4(medium) (default 0) | 7(veryfast), 4(medium), 1(veryslow) |
| h264_vaapi  |       |   O   | O (rc_mode 1) | `-`                   |
|             |       |       |               |                       |
| **libx265** |   O   |   O   |               | medium                | veryfast ,medium, veryslow          |
| hevc_nvenc  |       |   O   |       O       | 15(p4)                | 12(p2), 15(p4), 18(p7)              |
| hevc_qsv    |       |       |               | 4(medium) (default 0) | 7(veryfast), 4(medium), 1(veryslow) |
| hevc_vaapi  |       |   O   | O (rc_mode 1) | `-`                   |

|                    |      |      |                      |
| :----------------- | :--- | :--- | :------------------- |
| **Global options** |      |      |                      |
|                    |      | `-y` | 出力ファイルの上書き |


* [Hardware/QuickSync – FFmpeg](https://trac.ffmpeg.org/wiki/Hardware/QuickSync)
* [Hardware/VAAPI – FFmpeg](https://trac.ffmpeg.org/wiki/Hardware/VAAPI)

```bash
ffmpeg -hide_banner -h encoder=libx264    > libx264.txt
ffmpeg -hide_banner -h encoder=h264_nvenc > h264_nvenc.txt
ffmpeg -hide_banner -h encoder=h264_qsv   > .txt
ffmpeg -hide_banner -h encoder=h264_qsv   > h264_qsv.txt
ffmpeg -hide_banner -h encoder=h264_vaapi > h264_vaapi.txt
ffmpeg -hide_banner -h encoder=libx265    > libx265.txt
ffmpeg -hide_banner -h encoder=hevc_nvenc > hevc_nvenc.txt
ffmpeg -hide_banner -h encoder=hevc_qsv   > hevc_qsv.txt
ffmpeg -hide_banner -h encoder=hevc_vaapi > hevc_vaapi.txt

ffmpeg [options] [[infile options] -i infile]... {[outfile options] outfile}...


# base
ffmpeg -t 15 -i /source/bbb_original.mp4 -vcodec copy -an -y /dist/base.mp4

# x264
ffmpeg -y \
  -i /dist/base.mp4 \
  -c:v libx264 -preset medium \
  /dist/x264_x264_default_medium.mp4

# h264_nvenc
ffmpeg -y \
  -hwaccel cuda -hwaccel_output_format cuda \
  -i /dist/base.mp4 \
  -c:v h264_nvenc -preset 15 \
  /dist/x264_nvenc_default_p4.mp4

# h264_qsv
ffmpeg -y \
  -hwaccel qsv -hwaccel_output_format qsv \
  -i /dist/base.mp4 \
  -c:v h264_qsv -preset 4 \
  /dist/x264_qsv_default_medium.mp4

# h264_vaapi
ffmpeg -y \
  -hwaccel vaapi -hwaccel_output_format vaapi \
  -i /dist/base.mp4 \
  -c:v h264_vaapi \
   /dist/x264_vaapi_default_none.mp4


# x265
ffmpeg -y \
  -i /dist/base.mp4 \
  -c:v libx265 -preset medium \
  -tag:v hvc1 \
  /dist/x265_x265_default_medium.mp4

# hevc_nvenc
ffmpeg -y \
  -hwaccel cuda -hwaccel_output_format cuda \
  -i /dist/base.mp4 \
  -c:v hevc_nvenc -preset 15 \
  -tag:v hvc1 \
  /dist/x265_nvenc_default_p4.mp4

# hevc_qsv
ffmpeg -y \
  -hwaccel qsv -hwaccel_output_format qsv \
  -i /dist/base.mp4 \
  -c:v hevc_qsv -preset 4 \
  -tag:v hvc1 \
  /dist/x265_qsv_default_medium.mp4

# hevc_vaapi
ffmpeg -y \
  -hwaccel vaapi -hwaccel_output_format vaapi \
  -i /dist/base.mp4 \
  -c:v hevc_vaapi \
  -tag:v hvc1 \
   /dist/x265_vaapi_default_none.mp4

```

[FFmpeg Filters Documentation](https://ffmpeg.org/ffmpeg-filters.html#Examples-91)
