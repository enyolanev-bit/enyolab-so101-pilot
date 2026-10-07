# Astra preparation: current wrist-camera capture

Status: **PROVEN_CAPTURE_ONLY**, 2026-10-06 23:31 CEST. No robot port opened.

- Camera enumerated by macOS: `Innomaker-U20CAM-1080p-S1`, UVC vendor 3141,
  product 25446; one exact-name match. AVFoundation index was 1 in the first
  enumeration; named selection was used because enumeration order changes.
- Command executed: `.venv/bin/python scripts/capture_wrist_frame.py`.
- Frame: `wrist-20261006T213127346817Z-f9382e92.png` (LOCAL_ONLY, Git-ignored).
- Metadata: `wrist-20261006T213127346817Z-f9382e92.json`.
- SHA-256: `b7882b28a4754204447e82939cb6c7a6222bcf168249551d67685cf0ca07a228`.
- Size: 176901 bytes; decoded view 640×480.
- Capture interval UTC: 21:31:27.346817 to 21:31:33.109684; 5.763 seconds
  including FFmpeg startup; no warnings; no audio; 15 startup frames discarded.
- Requested 30 fps; throughput and sensor exposure timestamp **UNKNOWN**.
- Visual inspection: ceiling/wall decor and a bright lamp; no visible pen tip,
  paper or drawing workspace. Capture is valid, current task framing is not.
- Orientation transform applied: none. Correct working orientation and
  working-distance focus **UNKNOWN**. Current mount on follower: user-reported.
- No model API called and no frame uploaded to an external model in this pass.

This proves camera accessibility now, not robot vision calibration, streaming
latency, useful painting coverage or autonomous control readiness.
