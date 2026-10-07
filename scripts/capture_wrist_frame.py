#!/usr/bin/env python3
"""Capture one local named-camera PNG. No LeRobot, serial, motor, or API access.

Uses a unique nonnumeric AVFoundation name, never a guessed camera index.
Use capture_identified_camera.py for numeric camera names.
Frames stay in Git-ignored evidence/video; metadata can be reviewed separately.
"""

import datetime as dt
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time
import uuid


DEVICE = "Innomaker-U20CAM-1080p-S1"
ROOT = Path(__file__).resolve().parents[1]


def capture(device=DEVICE, width=640, height=480):
    # FFmpeg parses a leading number as a device/screen index, even in a name.
    # Use the exact-ID native helper for these names, never index guessing.
    if device.lstrip()[:1].isdigit() or device.lstrip().startswith(("+", "-")):
        raise ValueError("Numeric camera name requires scripts/capture_identified_camera.py")
    requested_size = (width, height)
    if not all(type(value) is int and 1 <= value <= 4096 for value in requested_size):
        raise ValueError("Requested camera dimensions must be integers from 1 to 4096")
    if sys.platform != "darwin":
        raise RuntimeError("This camera-only helper requires macOS AVFoundation")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is unavailable")
    inventory = subprocess.run(
        ["system_profiler", "SPCameraDataType", "-json"],
        capture_output=True, check=True, timeout=10,
    )
    devices = json.loads(inventory.stdout).get("SPCameraDataType", [])
    matches = [d for d in devices if d.get("_name") == device]
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one {device!r}; found {len(matches)}")

    # AVFoundation opens by name; :none explicitly excludes audio.
    # Discard 15 decoded frames for exposure startup, then return one PNG.
    cmd = [
        ffmpeg, "-hide_banner", "-loglevel", "warning", "-nostdin",
        "-f", "avfoundation", "-framerate", "30", "-video_size", f"{width}x{height}",
        "-pixel_format", "uyvy422", "-i", f"{device}:none",
        "-an", "-vf", "select=gte(n\\,15)", "-frames:v", "1",
        "-f", "image2pipe", "-c:v", "png", "pipe:1",
    ]
    started = dt.datetime.now(dt.timezone.utc)
    start_mono = time.monotonic()
    result = subprocess.run(cmd, capture_output=True, timeout=15, check=True)
    finished = dt.datetime.now(dt.timezone.utc)
    png = result.stdout
    if png[:8] != b"\x89PNG\r\n\x1a\n" or png[12:16] != b"IHDR":
        raise RuntimeError("Camera did not return a PNG")
    width, height = struct.unpack(">II", png[16:24])
    if (width, height) != requested_size:
        raise RuntimeError(f"Unexpected frame size: {width}x{height}")

    frame_id = started.strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex[:8]
    folder = ROOT / "evidence" / "video"
    folder.mkdir(parents=True, exist_ok=True)
    prefix = "wrist" if device == DEVICE else "camera"
    path = folder / f"{prefix}-{frame_id}.png"
    metadata = {
        "status": "PROVEN_CAPTURE_ONLY",
        "frame_id": frame_id,
        "device_name": device,
        "device_unique_id": matches[0].get("spcamera_unique-id", "UNKNOWN"),
        "backend": "ffmpeg/AVFoundation; name selection; audio disabled",
        "capture_started_utc": started.isoformat(),
        "capture_finished_utc": finished.isoformat(),
        "host_elapsed_s": round(time.monotonic() - start_mono, 3),
        "sensor_exposure_timestamp": "UNKNOWN; host interval only",
        "width": width, "height": height,
        "requested_fps": 30, "measured_fps": None,
        "discarded_frames": 15,
        "rotation_applied_degrees": 0,
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(png).hexdigest(),
        "bytes": len(png),
        "ffmpeg_warnings": result.stderr.decode(errors="replace"),
        "robot_access": "NONE; camera-only subprocess",
    }
    with path.open("xb") as stream:
        stream.write(png)
    with path.with_suffix(".json").open("x") as stream:
        json.dump(metadata, stream, indent=2)
        stream.write("\n")
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default=DEVICE, help="Exact unique macOS camera name")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    args = parser.parse_args()
    try:
        print(json.dumps(capture(args.device, args.width, args.height), indent=2))
    except (RuntimeError, OSError, ValueError, subprocess.SubprocessError) as exc:
        # Timeout kills/reaps the camera subprocess. No retry or camera fallback.
        print(f"CAMERA_CAPTURE_FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
