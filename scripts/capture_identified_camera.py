#!/usr/bin/env python3
"""Capture by exact macOS camera ID/name through AVFoundation; no robot access."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]


def capture(name, not_before_unix_s=None):
    inventory = subprocess.run(['system_profiler', 'SPCameraDataType', '-json'],
                               capture_output=True, check=True, timeout=10)
    matches = [d for d in json.loads(inventory.stdout)['SPCameraDataType'] if d['_name'] == name]
    if len(matches) != 1:
        raise RuntimeError('Camera name is missing or ambiguous')
    uid = matches[0]['spcamera_unique-id']
    started = dt.datetime.now(dt.timezone.utc)
    clock = time.monotonic()
    command = ['swift', '-swift-version', '5', str(ROOT/'scripts/capture_camera_by_id.swift'), uid, name]
    if not_before_unix_s is not None:
        command.append(str(not_before_unix_s))
    result = subprocess.run(command,
                            capture_output=True, check=True, timeout=60)
    finished = dt.datetime.now(dt.timezone.utc)
    png = result.stdout
    if png[:8] != b'\x89PNG\r\n\x1a\n' or png[12:16] != b'IHDR':
        raise RuntimeError('Expected PNG camera frame')
    width, height = struct.unpack('>II', png[16:24])
    frame_id = started.strftime('%Y%m%dT%H%M%S%fZ') + '-' + uuid.uuid4().hex[:8]
    path = ROOT/'evidence/video'/f'camera-{frame_id}.png'
    messages = result.stderr.decode(errors='replace').splitlines()
    timing_rows = [json.loads(line.removeprefix('CAPTURE_TIMING_JSON:')) for line in messages
                   if line.startswith('CAPTURE_TIMING_JSON:')]
    if len(timing_rows) != 1 or timing_rows[0]['device_unique_id'] != uid or timing_rows[0]['device_name'] != name:
        raise RuntimeError('Missing or mismatched native capture identity/timing')
    metadata = {'status':'CAPTURED_BY_EXACT_DEVICE_ID', 'frame_id':frame_id,
                'device_name':name, 'device_unique_id':uid,
                'backend':'native AVFoundation exact uniqueID and localizedName match; video only',
                'capture_started_utc':started.isoformat(), 'capture_finished_utc':finished.isoformat(),
                'host_elapsed_s':round(time.monotonic()-clock,3),
                'sensor_exposure_timestamp':'UNKNOWN; native frame PTS and host receipt timestamps recorded separately',
                'native_capture':timing_rows[0],
                'width':width,'height':height,'discarded_frames':15,'rotation_applied_degrees':0,
                'path':path.relative_to(ROOT).as_posix(), 'sha256':hashlib.sha256(png).hexdigest(),
                'bytes':len(png),'robot_access':'NONE',
                'warnings':'\n'.join(line.replace(str(ROOT),'<repo>') for line in messages
                                    if not line.startswith('CAPTURE_TIMING_JSON:'))}
    with path.open('xb') as f: f.write(png)
    with path.with_suffix('.json').open('x') as f: json.dump(metadata,f,indent=2);f.write('\n')
    return metadata


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device',required=True)
    args=parser.parse_args()
    try:
        print(json.dumps(capture(args.device),indent=2))
    except subprocess.CalledProcessError as exc:
        print('CAMERA_CAPTURE_FAILED:',exc.stderr.decode(errors='replace'))
        raise SystemExit(1)
