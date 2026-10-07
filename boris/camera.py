"""Camera capture for the SO-101 drawing setup (macOS, AVFoundation). No robot access.

Cameras are selected by their exact AVFoundation unique ID, never by an index (index order
is not stable on macOS). The unique ID encodes the USB port: on another Mac or another USB
port it changes. Run `python camera.py --list` and put the IDs in .env.

    tool_camera     primary   InnoMaker U20CAM-1080p  (PRIMARY_CAMERA_ID)
    context_camera  secondary InnoMaker U20CAM-720P   (SECONDARY_CAMERA_ID)

    capture(camera="tool_camera")   -> dict(path, sha256, width, height, timings, device ...)
    capture_for_astra()             -> fresh primary frame, downscaled copy + data URL, for the
                                       moment just BEFORE a model call (no model is called here)
    list_cameras()                  -> every video device AVFoundation sees

Usage:  python camera.py --list | python camera.py [--camera tool_camera|context_camera]
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json
import os
import pathlib
import shutil
import struct
import subprocess
import sys
import time
import uuid

HERE = pathlib.Path(__file__).resolve().parent
SWIFT_SRC = HERE / "capture_camera_by_id.swift"
BUILD_DIR = HERE / ".build"
FRAMES_DIR = HERE / "frames"


def _load_env(path: pathlib.Path = HERE / ".env") -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env()

CAMERAS = {
    "tool_camera": {"unique_id": os.environ.get("PRIMARY_CAMERA_ID", "0x11100000c456366"),
                    "name_prefix": "Innomaker-U20CAM-1080p"},
    "context_camera": {"unique_id": os.environ.get("SECONDARY_CAMERA_ID", "0x11200000c456367"),
                       "name_prefix": "Innomaker-U20CAM-720P"},
    "side_camera": {"unique_id": os.environ.get("SIDE_CAMERA_ID", "0x114000032e40335"),
                    "name_prefix": "5MP USB Camera"},
}
ALIASES = {"primary": "tool_camera", "secondary": "context_camera", "paper_context_camera": "context_camera",
           "workspace_camera": "side_camera", "tool_camera_left": "tool_camera",
           "tool_camera_right": "context_camera"}


class CameraError(RuntimeError):
    pass


def _helper() -> list[str]:
    """Compiled helper (fast, cached by source hash) or the Swift interpreter as fallback."""
    src_hash = hashlib.sha256(SWIFT_SRC.read_bytes()).hexdigest()[:12]
    binary = BUILD_DIR / f"capture_camera_{src_hash}"
    if binary.exists():
        return [str(binary)]
    if shutil.which("swiftc"):
        BUILD_DIR.mkdir(exist_ok=True)
        r = subprocess.run(["swiftc", "-O", "-swift-version", "5", str(SWIFT_SRC), "-o", str(binary)],
                           capture_output=True, timeout=300)
        if r.returncode == 0 and binary.exists():
            return [str(binary)]
    if shutil.which("swift"):
        return ["swift", "-swift-version", "5", str(SWIFT_SRC)]
    raise CameraError("Swift toolchain missing: run `xcode-select --install` (README_BORIS.md, step 4)")


def list_cameras() -> list[dict]:
    r = subprocess.run(_helper() + ["--list"], capture_output=True, timeout=60)
    if r.returncode != 0:
        raise CameraError(f"camera listing failed: {r.stderr.decode(errors='replace')}")
    return json.loads(r.stdout)


def _resolve(camera: str) -> dict:
    role = ALIASES.get(camera, camera)
    if role not in CAMERAS:
        raise CameraError(f"unknown camera {camera!r}; use one of {sorted(CAMERAS)}")
    want = CAMERAS[role]
    devices = list_cameras()
    hits = [d for d in devices if d["unique_id"] == want["unique_id"]]
    if len(hits) != 1:
        seen = [(d["name"], d["unique_id"]) for d in devices]
        raise CameraError(f"{role}: unique ID {want['unique_id']} not found (seen: {seen}). "
                          f"Run `python camera.py --list` and set the ID in .env")
    dev = hits[0]
    if not dev["name"].strip().startswith(want["name_prefix"]):
        raise CameraError(f"{role}: ID {want['unique_id']} is {dev['name']!r}, expected {want['name_prefix']}*")
    return {"role": role, **dev}


def capture(camera: str = "tool_camera", out_dir: pathlib.Path = FRAMES_DIR) -> dict:
    dev = _resolve(camera)
    started = dt.datetime.now(dt.timezone.utc)
    t0 = time.monotonic()
    # The helper re-checks the exact unique ID AND the exact name (trailing spaces included).
    r = subprocess.run(_helper() + [dev["unique_id"], dev["name"]], capture_output=True, timeout=60)
    if r.returncode != 0:
        raise CameraError(f"{dev['role']}: capture failed: {r.stderr.decode(errors='replace').strip()} "
                          f"(camera permission for this terminal? cable?)")
    png = r.stdout
    if png[:8] != b"\x89PNG\r\n\x1a\n" or png[12:16] != b"IHDR":
        raise CameraError("helper did not return a PNG")
    width, height = struct.unpack(">II", png[16:24])
    timing = [json.loads(l.removeprefix("CAPTURE_TIMING_JSON:")) for l in r.stderr.decode(errors="replace").splitlines()
              if l.startswith("CAPTURE_TIMING_JSON:")]
    if len(timing) != 1 or timing[0]["device_unique_id"] != dev["unique_id"]:
        raise CameraError("capture identity/timing record missing or mismatched")
    out_dir.mkdir(parents=True, exist_ok=True)
    frame_id = started.strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex[:8]
    path = out_dir / f"{dev['role']}-{frame_id}.png"
    with open(path, "xb") as f:
        f.write(png)
    meta = {"frame_id": frame_id, "camera": dev["role"], "device_name": dev["name"],
            "device_unique_id": dev["unique_id"], "path": str(path), "width": width, "height": height,
            "sha256": hashlib.sha256(png).hexdigest(), "bytes": len(png),
            "capture_started_utc": started.isoformat(),
            "frame_received_unix_s": timing[0]["last_receipt_unix_s"],
            "host_elapsed_s": round(time.monotonic() - t0, 3), "discarded_warmup_frames": 15,
            "rotation_applied_degrees": 0}
    with open(path.with_suffix(".json"), "x") as f:
        json.dump(meta, f, indent=2)
    return meta


def capture_for_astra(max_side: int = 1280, camera_name: str = "tool_camera") -> dict:
    """Capture a named camera right before a model call. Does NOT call any model.

    Returns the capture metadata plus a downscaled JPEG (macOS `sips`) as a data URL ready to
    be attached to an image-capable model request, and the frame age at return time.
    """
    meta = capture(camera_name)
    src = pathlib.Path(meta["path"])
    small = src.with_name(src.stem + f".astra{max_side}.jpg")
    r = subprocess.run(["sips", "-Z", str(max_side), "-s", "format", "jpeg", str(src), "--out", str(small)],
                       capture_output=True, timeout=30)
    if r.returncode != 0 or not small.exists():
        raise CameraError(f"downscale failed: {r.stderr.decode(errors='replace')}")
    data = small.read_bytes()
    meta.update({"astra_image_path": str(small), "astra_image_sha256": hashlib.sha256(data).hexdigest(),
                 "astra_image_data_url": "data:image/jpeg;base64," + base64.b64encode(data).decode(),
                 "age_s_at_return": round(time.time() - meta["frame_received_unix_s"], 3)})
    return meta


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--camera", default="tool_camera")
    a = ap.parse_args()
    try:
        if a.list:
            print(json.dumps(list_cameras(), indent=2))
        else:
            print(json.dumps(capture(a.camera), indent=2))
    except CameraError as e:
        print(f"CAMERA_ERROR: {e}", file=sys.stderr)
        sys.exit(1)
