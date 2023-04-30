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

```bash
# Download Installer for Linux Debian 11 x86_64
wget https://developer.download.nvidia.com/compute/cuda/repos/debian11/x86_64/cuda-keyring_1.0-1_all.deb
sudo dpkg -i cuda-keyring_1.0-1_all.deb
sudo add-apt-repository contrib
sudo apt-get update
sudo apt-get -y install cuda

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

|      | CRF |
| :--- ||
|      |

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
    * h265_nvenc
    * h265_qsv
    * h265_vaapi


```bash
# plotbitrate
cd ~/FFmpeg-video-quality-evaluations/tools/plotbitrate/ && docker build -t plotbitrate . && cd ../../
docker run --rm -it -v $PWD/videos/source:/source -v $PWD/videos/dist:/dist plotbitrate

# ffmpeg
cd ~/FFmpeg-video-quality-evaluations/tools/ffmpeg-vqe/ && docker build -t ffmpeg-vqe . && cd ../../
docker run --rm -it -v $PWD/videos/source:/source -v $PWD/videos/dist:/dist --device "/dev/dri:/dev/dri" ffmpeg-vqe

```

```bash
# base
ffmpeg -t 300 -i /source/bbb_original.mp4 -vcodec copy -an -y /dist/base.mp4

# x264
ffmpeg -i /dist/base.mp4 -y /dist/x264_x264_crf23_medium.mp4 -crf 23 -preset medium -c:v libx264

# h264_nvenc
ffmpeg -i /dist/base.mp4 -y /dist/x264_nvenc_crf23_medium.mp4 -crf 23 -preset medium -c:v h264_nvenc -hwaccel cuda -hwaccel_output_format cuda

# h264_qsv
ffmpeg -i /dist/base.mp4 -y /dist/x264_qsv_crf23_medium.mp4 -crf 23 -preset medium -c:v h264_qsv -hwaccel qsv -hwaccel_output_format qsv

# h264_vaapi
ffmpeg -i /dist/base.mp4 -y /dist/x264_vaapi_crf23_medium.mp4 -crf 23 -preset medium -c:v h264_vaapi -hwaccel vaapi -hwaccel_output_format vaapi


# x265
ffmpeg -i /dist/base.mp4 -y /dist/x265_x265_crf28_medium.mp4 -crf 28 -preset medium -c:v libx265 -tag:v hvc1

# h265_nvenc
ffmpeg -i /dist/base.mp4 -y /dist/x265_nvenc_crf23_medium.mp4 -crf 23 -preset medium -c:v h265_nvenc -hwaccel cuda -hwaccel_output_format cuda

# h265_qsv
ffmpeg -i /dist/base.mp4 -y /dist/x265_qsv_crf23_medium.mp4 -crf 23 -preset medium -c:v h265_qsv -hwaccel qsv -hwaccel_output_format qsv

# h265_vaapi
ffmpeg -i /dist/base.mp4 -y /dist/x265_vaapi_crf23_medium.mp4 -crf 23 -preset medium -c:v h265_vaapi -hwaccel vaapi -hwaccel_output_format vaapi

```

[FFmpeg Filters Documentation](https://ffmpeg.org/ffmpeg-filters.html#Examples-91)
