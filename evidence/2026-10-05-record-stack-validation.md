# Validation logicielle — pile d'enregistrement (lerobot-record) LeRobot 0.6.1

- **Date** : 2026-10-05 22:35 CEST
- **Hôte** : Mac ENYOLAB (bring-up), arm64, `.venv` du dépôt
- **Dépendance** : `lerobot[core_scripts,feetech]==0.6.1`. Dans le `pyproject.toml` amont @ v0.6.1, `core_scripts` = `dataset` + `hardware` + `viz`, extra associé à `lerobot-record` / `lerobot-teleoperate` / `lerobot-calibrate`. Aucun extra d'entraînement ni de policy.
- **Portée** : versions et imports uniquement. `lerobot-record` n'a **pas** été exécuté ; aucun port série ouvert.

## Sortie brute (chemins machine remplacés par `<repo>` / `~`)

```text
$ shasum -a 256 pyproject.toml uv.lock
ca9b410658a8c698751b26b22e9f150d2574b289a80bb8cb70d698cfd215cb84  pyproject.toml
3b247e885c2c0990f84187351367d21461e6574ad7eb01a9892a3ade1e074a59  uv.lock
$ uv lock --check --python 3.12
Resolved 99 packages in 24ms
$ ffmpeg -version | head -1
ffmpeg version 8.1.1 Copyright (c) 2000-2026 the FFmpeg developers
$ ffmpeg -encoders | grep -E "libsvtav1|libx264 |h264_videotoolbox|hevc_videotoolbox"
 V..... libsvtav1            SVT-AV1(Scalable Video Technology for AV1) encoder (codec av1)
 V....D libx264              libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 (codec h264)
 V....D libx264rgb           libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 RGB (codec h264)
 V....D h264_videotoolbox    VideoToolbox H.264 Encoder (codec h264)
 V....D hevc_videotoolbox    VideoToolbox H.265 Encoder (codec hevc)
$ .venv/bin/python <record-stack-check>
lerobot 0.6.1
av 15.1.0
torchcodec 0.11.1
opencv-python-headless 4.13.0.92
datasets 4.8.5
pyarrow 25.0.1
rerun-sdk 0.33.1
pynput 1.8.2
torch 2.11.0
feetech-servo-sdk 1.0.0
import av OK | codecs: ['libsvtav1', 'libx264', 'h264_videotoolbox']
import cv2 OK | 4.13.0
import torchcodec OK | 0.11.1
lerobot.datasets (lerobot_dataset, video_utils) OK
lerobot.cameras.opencv OK
lerobot.scripts.lerobot_record import OK (non execute)
RGBEncoderConfig().vcodec default = libsvtav1
```

## Lecture

- FFmpeg système : présent (Homebrew). Le guide d'installation amont (`docs/source/installation.mdx` @ v0.6.1, option uv) indique que TorchCodec ≥ 0.10 s'appuie sur un FFmpeg **système** (`brew install ffmpeg` sur macOS) : prérequis à reproduire sur le Mac de Boris.
- Codec RGB par défaut de LeRobot 0.6.1 : `libsvtav1`, disponible dans PyAV.
- Avertissement macOS au chargement : classes Objective-C dupliquées entre les `libavdevice` embarqués par `av` et `cv2` et le FFmpeg Homebrew. Impact non évalué.
