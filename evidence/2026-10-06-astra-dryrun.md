# Astra vision to action dry run — 2026-10-06

**PROVEN: one real `gpt-6-astra` response, one proposal, zero motor execution.**
This is a vision/proposal/schema test, not a physical controller validation.

## CAMERA_FRAME_USABLE

**NO for drawing positioning.** Named wrist camera captured a valid 640×480
image of a plush toy in front of a window/shutter. No identifiable drawing
surface, pen/tool tip or useful drawing target was visible. Astra independently
returned `camera_frame_usable: false`.

- Frame: `video/wrist-20261006T214726901207Z-b50cd926.png` (local, Git-ignored).
- SHA-256: `de8646caaff2fb708e20a55761a08d66505f3b310321f00950ec79b07f610dbf`.
- Metadata: `video/wrist-20261006T214726901207Z-b50cd926.json`.
- Capture UTC: 21:47:26.901207 to 21:47:28.439407; elapsed 1.538 s.

## CURRENT_POSE_READONLY

**PROVEN at measurement time**, 23:48:11.530846–23:48:12.343397 CEST.

| Joint | Raw | Calibration-relative value |
|---|---:|---:|
| shoulder_pan | 2036 | -2.241758 degrees |
| shoulder_lift | 2028 | -1.714286 degrees |
| elbow_flex | 2048 | +0.043956 degrees |
| wrist_flex | 1559 | +26.945055 degrees |
| wrist_roll | 953 | -96.219780 degrees |
| gripper | 2140 | 7.346128 percent |

Artifact: `2026-10-06-astra-dryrun-readonly-pose.json`.
The audited existing probe hash was verified before execution. USB enumeration
uniquely matched the follower serial; lsof found no owner before the probe.
Read-only packet guard allowed **PING ×7 and READ ×72 only**. Write calls: **0**.
IDs 1–6 reported model 777; calibration mismatches: none. All six torques read
zero and remained unchanged. The port was closed directly, bypassing the normal
disconnect path that can write torque registers. No motor script was launched.

Angles use the inspected LeRobot 0.6.1 conversion:
`(raw - (range_min + range_max)/2) * 360/4095`.
Gripper uses `(raw-range_min)/(range_max-range_min)*100`. These are not measured
Cartesian coordinates or tool orientation. No new calibration was performed.

## ASTRA_PROPOSED_ACTION

```json
{
  "session_id": "astra-dryrun-20261006T214726901207Z-b50cd926",
  "action_id": "astra-dryrun-20261006T214726901207Z-b50cd926-one",
  "observation_id": "20261006T214726901207Z-b50cd926",
  "action": {"type": "hold"}
}
```

Actual API model: `gpt-6-astra`; response status `completed`; one HTTP attempt;
elapsed 7.107 s. No tools or execution backend were supplied. `store: false`.
The camera image was sent to the OpenAI API as authorized for this dry run.

Artifacts:
- `2026-10-06-astra-dryrun-proposal.request.json`: exact textual instructions,
  image path/hash, measured pose, schema, timestamps and input hashes; no key,
  authorization headers or image base64 retained.
- `2026-10-06-astra-dryrun-proposal.json`: actual model identifier/response ID,
  concise reasoning summary, proposal, schema result and offline disposition.

## ACTION_SCHEMA_VALID

**YES.** Validated against `config/astra-action.schema.json` with
`jsonschema 4.25.1`; no errors; all supplied IDs matched. No model retry or second
proposal was requested. The isolated validator environment did not change the
robot project's dependencies.

## CONTROLLER_WOULD_ACCEPT

**NO — offline contract assessment.** The documented `hold()` operation retains
an already validated setpoint under monitored torque **only when armed**.
This session is DISARMED with all torques read zero. Accepting the proposal as an
active hold would require unauthorized arming. A benign decision to remain idle
is understandable, but is not a valid invocation of that controller operation.
No handler, including `hold` or `stop`, was dispatched. No register was written.

## WHY

Astra's concise rationale: a positioning move is unjustified without visible
tool/target and validated camera-to-joint geometry; the image and pose are stale
and unsynchronized. It selected hold to avoid torque activation.

Freshness limitation of this preparation run: the camera and pose were sampled
separately, and the one-shot API harness was prepared afterward. At request
preparation, the frame was 135.675 s old and the pose 90.233 s old. They are
real observations from this run, but cannot authorize live movement under the
planned 20 s image / 250 ms pose gates. No freshness threshold was relaxed.

## NEXT_SAFE_STEP

With motors still disabled, have the human arrange the camera/scene so the
work surface, tool tip and a clearly designated target are visible. Clarify
`hold` versus `stop` semantics in future proposer instructions, then perform a
separately authorized dry run using the prepared harness immediately after
fresh observations. A future executing controller must re-read pose at dispatch
and monitor the pose throughout image/model latency. Do not infer permission to
move from passing a schema check.

Credential setup: `OPENAI_API_KEY` set in ignored `.env.local`, permissions 0600;
no secret displayed or included in these artifacts. `.gitignore` already covers
`.env.*` and was unchanged. No commit made. **STOPPED after one proposal.**
