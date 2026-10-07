# Astra camera-guided follower: inspection and preparation

Status: **PLANNED controller; NOT_READY_FOR_MOTION.** Preparation on 2026-10-06.
No serial port was opened in this pass. No motor script was imported or run,
no register was written, no calibration was changed, and no model call was made.
The only hardware test was a camera capture. A leader is unnecessary for this
experiment. Existing teleoperation/recording blocks remain in place.

## CURRENT_CAPABILITIES

Evidence inspected, including actual event JSON rather than report titles:

| Status | Capability | Artifact |
|---|---|---|
| PROVEN, historical | IDs 1–6 report STS3215 model 777; calibration registers match saved file | `../evidence/2026-10-06T221031-follower-readonly-probe.json` |
| PROVEN, file inspection this pass | Active calibration SHA-256 is `f48d50d5ba8c220f13575f13c1d6562d9431391fb1e726541abdaf2c4e714a9d` | File hash read locally; matches the preceding probe and standalone scripts |
| PROVEN, historical | Goal/Present alignment before torque; four-second hold with zero sampled drift; single +1 degree request produced +0.615 degrees; all six torques read back zero at exit | `../evidence/2026-10-06T230932-follower-step.events.json` |
| PROVEN, historical | Five +1 degree requests produced +2.725 degrees; other joints stable; torque-off verified | `../evidence/2026-10-06T231536-follower-5step.events.json` |
| PROVEN, historical | Fixed +10 degree target produced +9.494 degrees / 108 counts, no sampled drift elsewhere, torque-off verified | `../evidence/2026-10-06T232403-follower-10deg.events.json` |
| PROVEN as operator report | Physical motion visually confirmed | User statement in this preparation chat; no new video captured |
| UNKNOWN | Current live pose, torque, temperature and bus health | No robot connection during this pass |

The +10 degree log remains **BLOCKED**: final error 0.505 degrees exceeded its
0.5 degree tolerance after 20 iterations. This does not negate the measured
motion, and does not constitute a successful convergence test. Sub-degree
positioning, reverse-direction response and painting remain NOT_PROVEN.

Existing standalone scripts (inspect as text; **do not import**):

- `../evidence/2026-10-06-follower_standalone_step.py`: one bounded +1 degree
  shoulder-pan request, startup checks, alignment, hold, verified shutdown.
- `../evidence/2026-10-06-follower_standalone_5step.py`: five measured-pose-relative
  +1 degree requests with feedback/drift checks.
- `../evidence/2026-10-06-follower_standalone_10deg.py`: fixed target, at most
  20 bounded updates, direction/progress/overshoot checks and shutdown.
- `../evidence/2026-10-06-follower_readonly_probe.py`: lower-level guarded
  read-only probe; useful reference for a future read-only pose adapter.
- `../evidence/2026-10-06-follower_goal_check.py`: existing goal/present diagnostic
  reference. It was not executed in this pass.

These are useful tested building blocks, **not a reusable safe agent controller**:

- They run at module top level and `--go` starts a physical sequence.
- The write-address whitelist permits configuration writes; it does not provide
  a semantic, bounded agent API. Never expose this bus/whitelist to the model.
- Startup checks cover calibrated ranges; motion needs target checks at every
  step, before serialization. A small relative cap alone is insufficient.
- Source inspection of installed LeRobot 0.6.1 `SOFollower.connect/configure`
  shows calibration/configuration and torque effects. Neither is a read-only
  pose/camera entrypoint, including `connect(calibrate=False)`.
- `SerialMotorsBus._unnormalize` in degree mode does **not** clamp to calibration
  ranges. `ensure_safe_goal_position` only clips the relative target.
- In these standalone scripts, the serial check compares hardcoded strings;
  re-enumerating the actual adapter identity and taking an exclusive lock are
  still necessary for a new controller.
- `MAX_DURATION_S` is declared but unused in the +10 degree script. There is no
  independent controller watchdog or host-power-loss protection. Shutdown in
  `finally` cannot guarantee an off state on unplug, SIGKILL, or a frozen host.

Calibration agreement is narrower than mechanical validation. Lift/elbow limits
are still 0–4095, as is wrist roll; these do not establish collision-free joint
travel. The last trials held wrist flex near its lower limit (raw 101, minimum
91). Do not generalize the pan result to these axes or silently relax margins.
The repo also contains a Standard/5 V description versus a 12 V operator report
and historical C047 identification. Actual variant markings remain unproven in
the inspected evidence. Reconcile this before a new hardware session; no supply
change is prescribed here.

## CAMERA_STATUS

**PROVEN:** named `Innomaker-U20CAM-1080p-S1` is detected and produces PNG frames
through FFmpeg AVFoundation on this Mac. See the new camera evidence report:
`../evidence/video/2026-10-06-astra-camera-preparation.md`.

Simplest independent capture:

```sh
.venv/bin/python scripts/capture_wrist_frame.py
```

This helper opens only the uniquely named camera, excludes audio, discards 15
startup frames, times out after 15 seconds of capture, checks PNG dimensions,
and saves a new 640×480 PNG plus UTC timestamps, hash and metadata. It refuses
missing/duplicate names and never falls back to the laptop camera. PNGs remain
local and Git-ignored. Importing the helper does not open the camera.

**PROVEN:** the captured view shows the ceiling/light, not the tip or paper.
**UNKNOWN:** working-distance focus, tip visibility, desired image rotation,
camera-to-tool transform, exposure timestamp and image age inside the driver.
The image has not been rotated or corrected. Mounting on the wrist is reported
by the user; a frame alone does not independently prove the physical mount.

The measured capture subprocess took 5.763 s including startup. Requested
30 fps is not a measured frame rate. Use named, on-demand snapshots initially;
later a camera worker can keep the stream open and publish only recent frames.
OpenCV CAP_AVFOUNDATION worked historically, but its index must be identified
again by image content; FFmpeg indices are not OpenCV indices. The historical
`config/cameras.yaml` index 0 must not be trusted as a permanent identity.

## PROPOSED_SAFE_API

All entries below are **PLANNED**, except the standalone camera helper above.
The agent receives a narrow message interface, never Python execution, shell,
serial handles, register addresses, calibration editing, gains, torque-enable,
power controls, policy editing or arbitrary paths. The controller owns identity,
authorization, limits, raw conversion, rate, timeout, state and audit records.

| API | Contract | First trial |
|---|---|---|
| `get_robot_pose()` | Read all six axes; return joint degrees, separate gripper percent, monotonic timestamp, torque state, communication status, calibration hash, session ID. A failed read returns an error, never fabricated or cached-as-live data. | Future read-only adapter |
| `get_camera_frame()` | Return image plus frame ID/hash, acquisition interval, orientation and freshness status; pair with pose reads bracketing acquisition. Reject observations acquired while moving. | Camera helper available |
| `move_joint_delta(joint, degrees, observation_id, action_id)` | One finite, bounded delta from fresh measured pose, frozen once; wait for measured result, no automatic retries/chaining. | Pan only; at most 1 degree; permitted sign separately commissioned |
| `move_to_joint_pose(...)` | Full typed pose; calibrated/raw and path checks on every interpolated segment, velocity/acceleration limits, joint and collision envelope. Never a teleport or implicit unbounded loop. | DISABLED |
| `set_gripper(percent, ...)` | Calibrated 0–100 percent, separate step/total/current limits; report measured aperture proxy. Percent is not degrees, millimeters or force. | DISABLED; manually secured tool |
| `hold()` | Suspend new goals; retain last validated setpoint under monitored torque only if already armed, for the remaining controller-owned lease. Never enable torque or reset a deadline. | Future; NOT an emergency stop |
| `stop()` | Preempt, cancel pending work, latch fault/stopped, bounded best-effort torque-off per servo, verify all six, require human re-arm. Missing acknowledgement = OFF_UNCONFIRMED. | Future; physical power cutoff is independent |

Stop must also have a separate priority path that does not depend on the last
image ID, model response, motion queue, or a healthy camera. A malformed normal
proposal stops the trial; it must not obstruct the hardware stop path.

`../config/astra-action.schema.json` is an **offline proposal contract only**.
It permits one pan delta, hold or stop, and rejects extra keys. It is not a
runtime controller or proof of physical safety. JSON schema is one validation
layer; reject duplicate JSON keys, NaN/Infinity, booleans used as numbers, stale
IDs, unauthorized signs, and out-of-state requests in controller code too.
Read operations can be supplied by the orchestrator without additional model
tool calls. General pose/gripper calls are intentionally absent from this first
proposal schema. A future provider-specific strict tool schema needs its own
compatibility check.

Mandatory controller invariants:

1. **Human arming:** an out-of-band, session-scoped, expiring permission defines
   the exact joint, direction, workspace, maximum action count and budgets.
   Neither a model message nor `--go` supplied by the model can create it.
   Refuse absent/expired permission and unknown hardware identity.
2. **Preflight:** exclusive ownership of the verified USB adapter; IDs/models;
   approved calibration hash and matching registers; all six torque states;
   actual pose in reviewed limits; voltage/temperature plausibility. Never
   auto-calibrate or repair configuration. Resolve hardware ambiguity first.
3. **Startup:** after human GO, use a reviewed version of the proven alignment
   sequence; bound configuration writes by phase, align Goal to fresh Present,
   verify goal readback and goal-vs-latest-present error immediately before
   torque, then enable only at this point. Verify torque and watch a bounded
   initial hold. Any partial enable/error enters fault shutdown.
4. **Limits before writes:** intersect calibrated raw limits plus margins,
   human-reviewed mechanical/cable envelope, and session envelope. Transform
   degree targets to raw ticks with pinned LeRobot semantics and recheck the
   quantized target. No wrap/shortest-path shortcuts; reject out-of-range raw
   readings before normalization can hide them. No silent clipping/replanning.
5. **Step and total limits:** bound each command from latest measured pose;
   also bound excursion from the immutable session-start pose and cumulative
   absolute travel. Charge commanded budget before dispatch; reconcile with
   measured travel without refunds. Returning toward the start does not reset
   travel/action/time budgets. Measure all joints throughout; locked joints
   retain their original accepted goals, not successively drifting measured
   positions. Budget state belongs exclusively to the controller.
6. **Timing and dynamics:** one action in flight, no queue, reviewed low speed
   and acceleration, bounded sampling/settling/action/session/hold durations.
   Small displacement does not imply low speed. Read all six axes before,
   during and after execution; monitor drift, wrong direction, overshoot,
   following error and no progress. A camera/network/model wait never blocks
   the controller watchdog or extends the lease.
7. **Communication:** finite bounded read retries within a hard deadline; bad
   packets, missing axes, stalled reads or inconsistent data fail closed. A
   successful broadcast write is not an acknowledgement: verify goals and
   measured motion. No blind motion resend after uncertain delivery. Deduplicate
   action IDs; a retry returns the recorded result without executing again.
8. **Failure:** invalidate requests, latch FAULT, attempt each torque-off write
   independently with bounded retries, verify every torque bit and close the
   port. Never label disconnected as torque-off. If communication is lost,
   software cannot guarantee de-energization: operator cuts physical servo power.
   Support/rest clearance must accommodate gravity fall on torque-off, without
   putting hands into the moving envelope. Hardware watchdog/power interruption
   is needed for an unattended claim; this first trial stays supervised.
9. **Audit:** append observation hashes/times, request, validation/rejection,
   accepted immutable target, commanded and measured trajectories, budgets,
   faults and torque-off verification. Log failure itself blocks further motion.

Illustrative review values, **PLANNED and not authorized**: pan step <=1 degree;
excursion <=3 degrees from start; cumulative commanded and measured path budgets
<=3 degrees each; at most 3 movement actions; all other joints locked. Start with
the previously tested positive sign; reverse correction requires a separate
bounded response test. Sensor sampling target 20 Hz; pose age <=250 ms at
dispatch; image age <=20 s from acquisition start, with image/pose consistency
checked again before acting; action settling deadline <=2 s; session hard cap
60 s including all camera/model waits. Exact drift, speed, acceleration,
following-error and raw-limit margins need commissioning before arming. These
numbers alone do not form an approved safety configuration.

## ASTRA_CONTROL_LOOP

**PLANNED smallest architecture:** one camera helper/worker, one local controller
process owning the bus and watchdog, and one orchestrator doing image/model I/O.
Use a local socket or restricted IPC request channel; no ROS, training pipeline,
dataset, leader, or general-purpose agent shell is required.

```text
camera image + measured pose + budgets + observation ID
                  -> Astra: propose ONE bounded action
                  -> schema + state + physical-limit validation
                  -> safe controller: one action, monitor, settle, return result
                  -> NEW image + measured pose + actual motion
                  -> Astra: stop / hold / one correction

human stop + independent watchdog ------> controller FAULT / torque-off attempt
physical power cutoff -----------------> servo supply (independent of software)
```

Controller states: DISARMED -> human-authorized PREFLIGHT -> ARMED_HOLD ->
EXECUTING -> ARMED_HOLD; any fault/expiry/stop -> latched STOPPED or FAULT.
No automatic re-arm, reconnect/resume, homing, return-to-start or auto-calibration.
Observation frames have a nonce/sequence and cannot authorize two moves. Reject
responses based on stale pose/frame state, concurrent calls, action lists or
requests after a timeout. Report actual measured motion, not requested motion,
to Astra. A stalled move must not provoke increasingly large corrective steps.

**PROVEN from official documentation:** GPT-6 Astra supports image input and
function calling/structured outputs. The proposed integration uses the Responses
API with one action proposal per observation and parallel tool calls disabled.
Account access, credentials, latency and end-to-end behavior remain **UNKNOWN**;
no API credential was inspected and no image was uploaded to a model this pass.
Sources: [model documentation](https://developers.openai.com/api/docs/models/gpt-6-astra),
[function calling](https://developers.openai.com/api/docs/guides/function-calling).
This is a conceptual integration, not an API-backed application implementation.

## Action representation for painting

**Recommendation / PLANNED:** start the vision/control bring-up with a single
bounded **joint delta**, explicitly `shoulder_pan` in calibration-relative
degrees. Do not call it image-left/image-right until the sign has been observed.
The wrist camera moves with the robot, so pixels are not a fixed world frame.
Degree zero is the calibration range midpoint, not a proven geometric zero;
the current conversion uses `(raw - midpoint) * 360 / 4095`.

For the first actual mark on paper, expose a small set of reviewed **high-level
primitives**, such as `pen_up`, `hover_at_paper_point`, `short_stroke`, `pen_up`.
After tool/plane/kinematic validation, primitive internals can use bounded
Cartesian deltas in a named paper frame (millimeters, +Z away from paper) with
fixed tool orientation and short verified paths. Until then these primitives
remain disabled. Plain joint deltas cannot promise a straight line or constant
pen height. Uncalibrated Cartesian deltas hide inverse-kinematic, singularity,
collision and tool-contact assumptions. No model may choose contact force or
invent pixel-to-millimeter conversions. A compliant pen holder or validated
force/contact method is required before touching paper.

## MISSING_PIECES

Before a supervised camera-guided **pan-only** experiment:

- Point the wrist view at a fixed high-contrast target in a cleared workspace;
  verify orientation, focus, target visibility and cable slack at the approved
  pose. The current ceiling view is a blocker.
- Reconcile follower servo variant/supply documentation and confirm identity;
  define the full-arm safe rest/torque-off envelope and pan corridor. Matching
  calibration registers alone cannot approve full mechanical ranges.
- Implement/review the isolated controller above, including target checks,
  exclusive device ownership, real deadlines, watchdog, priority stop, verified
  torque-off, idempotency and evidence logging. None exists as a reusable API yet.
- Offline fault-injection validation: limit crossing, repeated tiny actions,
  oscillations, malformed/nonfinite requests, stale images/poses, duplicate IDs,
  missing motor reads, ambiguous write outcome, blocked camera/network, timer
  expiry, partial torque enable, failed torque-off and logging failure.
- Human-authorized hardware commissioning of timeout/stop behavior, reviewed
  speed/acceleration and drift thresholds, positive response in the new pose;
  negative response before allowing bidirectional corrections. Do not tune
  servo gains or change convergence tolerance merely to mark an old test PASS.
- Wire Astra image/proposal transport after credential choice and access check;
  first run observe-and-propose with no motor backend. Measure latency against
  the observation and hold deadlines.
- Session-specific human GO, physical power cutoff reachable, fixed base,
  clear area and direct supervision as required by `safety.md`.

Additional blockers for **painting/contact**: tool tip and paper visible; tool
mount/TCP, paper plane, scale and camera calibration; kinematic model and signs;
validated remaining joints and path/collision limits; contact/compliance method;
pen lift/retract clearance; task-level success metric. An overhead camera is
optional if the wrist view adequately covers the task; it is not required for
the initial one-joint experiment. Historical leader/two-camera requirements in
`tasks/drawing.md` describe the earlier imitation-learning workflow.

## FIRST_SAFE_EXPERIMENT

**PLANNED stage 0:** fix the view with human handling while robot motion is
disabled; capture frames; ask Astra to locate a high-contrast fiducial and propose
one pan action; validate and log the proposal with execution unavailable. This
tests perception and contracts without torque.

**PLANNED first powered trial, separate future GO:** no pen contact, no gripper
motion. Human approves a collision-free pose and at most three <=1 degree pan
actions with <=3 degree travel budgets. A supervised commissioning step first
establishes which permitted direction shifts a target toward an image reticle.
Then Astra chooses one approved nudge, controller executes/settles, a new image
is captured, and Astra decides whether to stop or make one bounded correction.
Reverse correction is disabled until that sign is commissioned. A correction
that needs an unavailable axis/sign ends the trial. No automatic return move.

Freeze before GO: target/reticle, pixel error metric and acceptance band based
on static-image jitter; robot limits; drift and deadline thresholds. Success
requires fresh paired images, a reduction of the defined pixel error, verified
bounded encoder motion, stable locked joints, no safety faults and verified
torque-off, all saved as artifacts. Visibility/confidence loss, no progress,
unexpected motion or budget exhaustion stops the trial without chasing the
target. Passing this does not validate painting or unattended autonomy.

## FILES_CREATED_OR_CHANGED

New camera helper, offline proposal schema, this design, and camera evidence
report/metadata/frame only. Existing motor scripts, calibration, robot config,
teleop/record blocks, README and safety rules are untouched. Existing untracked
evidence is preserved. No commit was made.

## READY_FOR_HUMAN_REVIEW

**YES for preparation/design review. NO for motor execution.** The camera helper
is tested; the safe controller and Astra loop are specifications, not deployed
capabilities. This pass stops at preparation.
