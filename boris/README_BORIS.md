# SO-101 follower: prompt → Astra → drawing (Pilot #001) — EXPERIMENTAL

> **Status (2026-10-07): EXPERIMENTAL, not ready to run.** The proven, supported feature of this
> repository is **leader → follower teleoperation** (root `README.md`, `scripts/teleop_official.py`).
> Everything below was developed and tested with the **previous** follower calibration
> (`f48d50d5…`). Both arms were recalibrated on 2026-10-07 (follower `03b26c33…`, leader `183455cd…`),
> so `controller.py` still pins the previous follower hash and **refuses to start** (fail-closed).
> The drawing parameters (leads, wrist direction, pose assumptions) must be re-commissioned under an
> ENYOLAB GO before the pin is changed. Do **not** override `FOLLOWER_CALIBRATION_SHA256` to bypass it.

Plug the follower arm and the cameras into your Mac, run **one command**, type what to draw.
Astra (OpenAI Responses API) looks at the camera image and the robot state and answers with **one
constrained drawing command**. A local safety controller draws it with two joints, then switches the
torque OFF. **Astra never reaches the motors, the serial port or any servo register.**

```sh
python run_boris.py "draw a simple Golden Gate Bridge"
```

## What happens when you run it

1. **Read-only checks.** The script checks both cameras and the robot: identity, servo IDs 1–6, torque OFF, calibration registers equal to the calibration file, pose. Nothing is written to the arm.
2. **Fresh camera frames and robot state.**
3. **Astra** returns exactly one JSON command. Anything else is rejected before planning:
   - a known template (`golden_gate_bridge`, `house`, `zigzag`, `line`) with a scale;
   - one continuous path of up to 60 points in a normalised 0–1 square;
   - or a refusal.
4. **Plan.** Only `shoulder_pan` (horizontal) and `wrist_flex` (vertical) are used. The drawing is shrunk automatically to stay within ±8° of the start pose. The plan is printed.
5. **You place the pen** lightly on the paper where the drawing starts (the left end of the bridge deck), then type `GO`.
6. **Drawing.** The arm runs the proven safe startup (torque ON) and draws, at most 2° of push per control step. Torque is then switched OFF and read back on all six servos.
7. **Result.** Photos of the result are saved; the summary goes to `logs/run-*.json`.

Rehearse without motors or credits:

```sh
python run_boris.py "draw a bridge" --offline-astra --dry-run
```

## What was shown on this arm (2026-10-06/07, previous follower calibration; evidence in `evidence/`)

| Item | Status |
|---|---|
| `controller.py` safe startup + torque-OFF verification, many sessions | PROVEN with the previous calibration; **not re-run since the recalibration** |
| `shoulder_pan` ±10° in air, both directions, ±0.1° | PROVEN (encoders), previous calibration |
| First autonomous pen mark on paper | PROVEN once (operator-confirmed), previous calibration |
| `wrist_flex` −2° / +2° with a direction-specific lead | PROVEN (encoders) at ONE folded pose only, previous calibration |
| Recognizable bridge on paper (local planner, no Astra; 78/78 waypoints) | Operator-confirmed **once** (attempt #3); **not repeatable** so far |
| Prompt → real Astra API → drawing | **NOT_PROVEN**: Astra returned a valid command and the arm executed it, but the paper stayed **blank** |
| Two-stroke "L" mini drawing (later, different pose) | **NOT_PROVEN** (executed by encoders, no operator confirmation) |
| Official URDF forward kinematics vs the real arm | **Disagrees by ~90°** with the operator's view of the brush (likely `wrist_flex`); not used to refuse plans |
| `elbow_flex`, `shoulder_lift`, gripper | not used for drawing (the gripper holds the pen) |

The drawing is crude and small (about 27 × 12 mm for the bridge).

## 1. Connect the follower USB

Plug **only the follower** controller board into the Mac:

```sh
ls /dev/cu.usbmodem*          # expect one port with serial 5B7B015207
```

The controller finds the arm by its USB **serial number**. If no adapter, or two, carry that serial, it refuses to start.

## 2. Connect the 12 V power supply

- Use the follower's own **12 V** supply.
- Keep its switch **within reach**: it is the real emergency stop.
- Torque stays OFF until you type `GO`.

## 3. Connect the cameras

| Role | Camera | Note |
|---|---|---|
| `tool_camera` (primary, sent to Astra) | InnoMaker U20CAM-1080p on the wrist | must see the pen tip and the paper |
| `context_camera` | InnoMaker U20CAM-720P | sees the paper |

The camera IDs depend on the USB port (step 5).

## 4. Install (once)

```sh
xcode-select --install                               # Swift compiler for the camera helper
curl -LsSf https://astral.sh/uv/install.sh | sh      # if you do not have uv
cd boris
uv venv --python 3.12 .venv && source .venv/bin/activate
uv pip install -r requirements.txt                   # lerobot[feetech,kinematics]==0.6.1
cp .env.example .env
```

**Calibration file.** ENYOLAB gives you `follower_nevil.json` separately; it is never in Git.

```sh
mkdir -p ~/.cache/huggingface/lerobot/calibration/robots/so_follower
cp follower_nevil.json ~/.cache/huggingface/lerobot/calibration/robots/so_follower/
shasum -a 256 ~/.cache/huggingface/lerobot/calibration/robots/so_follower/follower_nevil.json
# approved file (2026-10-07): 03b26c3328b557d69b5146d5f316b5f23b760dd13fe7341d7e0b3ebe6b6425c9
# controller.py still expects the PREVIOUS file (f48d50d5…) and will refuse: drawing is not re-commissioned
```

Offline self-test, no hardware: `python sim_test.py` must end with `84/84 checks passed`.

## 5. Verify the cameras

```sh
python camera.py --list           # copy the two InnoMaker "unique_id" values into .env
python demo_move.py camera        # -> CAMERA_OK; check the PNG in frames/
```

The first run compiles the helper (about 1 min). Allow camera access for your terminal when macOS asks.

## 6. Verify the robot (read-only)

```sh
python demo_move.py check         # -> ROBOT_OK, torque 0 on all six servos; writes nothing
```

## 7. Safe movement demo (no paper contact)

With the pen held away from the paper:

```sh
python demo_move.py move --joint shoulder_pan --delta 3 --return
```

Type `GO`. Expect `MOVE_OK`.

## 8. Configure `OPENAI_API_KEY`

Put the key in `boris/.env` (`OPENAI_API_KEY=...`). Optional: `ASTRA_MODEL` (default `gpt-6-astra`).

- `.env` is ignored by Git.
- The key is only read by `astra.py` and is never logged.
- Each `run_boris.py` run without `--offline-astra` makes **exactly one** API call. There are no retries.

## 9. Where Astra plugs in

`astra.py` is the only module that talks to the model:

- `INSTRUCTIONS` is the drawing contract given to the model;
- `propose()` sends the prompt, the tool-camera image and the robot state, and returns the validated command.

`painter.validate_command()` is the gate: strict keys, finite numbers, coordinates 0–1, at most 60 points. To add shapes, add a template in `painter.TEMPLATES`. The motion limits live in `controller.py` and `painter.py`; changing them is an ENYOLAB decision.

If the drawing comes out mirrored or upside down on your setup, set `DRAW_FLIP_U=1` or `DRAW_FLIP_V=1` in `.env`.

## 10. Emergency stop

1. **Cut the 12 V power.** It always works. Expect the arm to sag.
2. **`Ctrl+C`.** The controller switches torque OFF on all six servos and reads it back.
3. **Automatic stops.** Any fault stops the arm: wrong direction, overshoot, drift of another joint, no progress, bus error, 120 s idle, 15 min session.
4. **`TORQUE OFF NOT CONFIRMED -> CUT THE 12 V POWER NOW`** means: cut the power at once.

After a stop, read `logs/` before running again. Never run `lerobot-calibrate`, never edit the calibration file, never raise the limits without ENYOLAB.

## Troubleshooting

| Message | Meaning / fix |
|---|---|
| `expected exactly one adapter with serial ...` | follower USB missing, or a different board |
| `calibration ... != pinned` | wrong calibration file (step 4) |
| `LeRobot source ... changed since audit` | wrong LeRobot version: reinstall `requirements.txt` in a clean venv |
| `communication failure ... Incorrect status packet` before torque | intermittent bus at startup: nothing moved; check the servo cables and run again |
| `no measurable progress` | pen pressed too hard on the paper: lighten the contact |
| `unique ID ... not found` | camera on another USB port: `python camera.py --list`, update `.env` |
| `OPENAI_API_KEY is not set` | step 8, or use `--offline-astra` |

## Files

| File | Role |
|---|---|
| `run_boris.py` | the one command |
| `astra.py` | model call and drawing contract (no robot access) |
| `painter.py` | templates, command validation, 2-joint plan, contact-mode drawing |
| `controller.py` | the only code that talks to the arm: safe startup, bounded moves, watchdog, verified torque OFF |
| `kinematics.py` | official LeRobot `RobotKinematics`; `urdf/SO101/` holds the official TheRobotStudio URDF (Apache-2.0) |
| `camera.py`, `capture_camera_by_id.swift` | camera capture by exact device ID |
| `demo_move.py`, `bridge_painter.py` | manual checks; bridge without Astra |
| `sim_test.py` | offline fault-injection tests |
