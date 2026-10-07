"""Offline fault-injection tests of controller.py against a simulated bus. No hardware, no port.

Run:  python sim_test.py      (exit code 0 = all checks passed)
The simulated servo reproduces the measured static error (stops ~5 counts short of its goal).
"""
import sys
import os
import types
import math
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import controller as C  # noqa: E402

CAL = {"shoulder_pan": (857, 3266), "shoulder_lift": (0, 4095), "elbow_flex": (0, 4095),
       "wrist_flex": (91, 2414), "wrist_roll": (0, 4095), "gripper": (2029, 3540)}
START = {"shoulder_pan": 2061, "shoulder_lift": 3276, "elbow_flex": 1976, "wrist_flex": 108,
         "wrist_roll": 955, "gripper": 2072}
ADDR = {"Torque_Enable": 40, "Goal_Position": 42, "Present_Position": 56}


class Cal:
    def __init__(self, lo, hi):
        self.range_min, self.range_max = lo, hi


class PH:  # packet handler: the controller's write guard wraps these two
    def __init__(self, bus):
        self.bus = bus

    def writeTxRx(self, port, scs_id, address, length, data):
        val = data[0] if length == 1 else (data[0] | (data[1] << 8))
        self.bus._apply(scs_id, address, val)
        return 0, 0

    def syncWriteTxOnly(self, port, start_address, data_length, param, param_length):
        return 0


class Port:
    def __init__(self):
        self.is_open, self.is_using = True, False

    def clearPort(self):
        pass

    def closePort(self):
        self.is_open = False


class FakeBus:
    def __init__(self, faults):
        self.f = faults
        self.motors = {n: types.SimpleNamespace(id=i) for i, n in enumerate(C.NAMES, 1)}
        self.ids = {i: n for n, m in self.motors.items() for i in [m.id]}
        self.present = dict(START)
        self.goal = {n: 0 for n in C.NAMES}               # stale goal, as found on 2026-10-06
        self.torque = {n: 1 if faults.get("torque_on_at_start") else 0 for n in C.NAMES}
        self.packet_handler = PH(self)
        self.port_handler = Port()
        self.is_connected = False
        self.reads = 0
        self.moves = 0                                     # faults below trigger after the first goal write

    def connect(self):
        self.is_connected = True

    def ping(self, i):
        return 778 if (self.f.get("bad_model") and i == 3) else 777

    def _apply(self, scs_id, addr, val):
        n = self.ids[scs_id]
        if addr == 40:
            self.torque[n] = val
        elif addr == 42:
            self.goal[n] = val

    def _physics(self):
        for n in C.NAMES:
            if self.torque[n] != 1:
                continue
            e = self.goal[n] - self.present[n]
            if n == self.f.get("stuck") or (n == "elbow_flex" and self.f.get("drift") and self.moves >= 1):
                continue
            if n == self.f.get("reverse") and self.moves >= 1:
                if abs(e) > 5:
                    self.present[n] -= 4 if e > 0 else -4      # moves AWAY from its goal
                continue
            if self.f.get("contact_short"):
                if abs(e) > self.f["contact_short"]:
                    self.present[n] = self.goal[n] - (self.f["contact_short"] if e > 0 else -self.f["contact_short"])
                continue
            if self.f.get("neg_short") and n == "wrist_flex" and e < 0:
                if -e > self.f["neg_short"]:
                    self.present[n] = self.goal[n] + self.f["neg_short"]
                continue
            if self.f.get("exact") or (self.f.get("neg_short") and n == "wrist_flex"):
                self.present[n] = self.goal[n]
            elif abs(e) > 5:
                self.present[n] = self.goal[n] - (5 if e > 0 else -5)
        if self.f.get("drift") and self.moves >= 1:
            self.present["elbow_flex"] += 3                    # sagging joint, not restored

    def sync_read(self, reg, motors=None, *, normalize=True, num_retry=0):
        self.reads += 1
        if self.f.get("comm_fail") and self.moves >= 2:
            raise ConnectionError("Incorrect status packet (simulated)")
        self._physics()
        src = {"Torque_Enable": self.torque, "Goal_Position": self.goal, "Present_Position": self.present}[reg]
        names = C.NAMES if motors is None else ([motors] if isinstance(motors, str) else list(motors))
        out = {n: src[n] for n in names}
        if self.f.get("missing_axis") and reg == "Present_Position" and self.moves >= 2:
            out.pop("wrist_roll", None)
        return out

    def sync_write(self, reg, values, *, normalize=True, num_retry=0):
        self.packet_handler.syncWriteTxOnly(None, ADDR[reg], 2, b"", 3 * len(values))
        self.moves += 1
        for n, v in values.items():
            if reg == "Goal_Position":
                self.goal[n] = v

    def write(self, reg, motor, value, *, normalize=True, num_retry=0):
        a = {"Torque_Enable": 40, "Goal_Position": 42, "Lock": 55, "P_Coefficient": 21}[reg]
        self.packet_handler.writeTxRx(None, self.motors[motor].id, a, 1 if a in (40, 55, 21) else 2,
                                      [value & 0xFF, value >> 8])

    def enable_torque(self, motors=None, num_retry=0):
        for n in C.NAMES:
            if self.f.get("partial_enable") and n == "gripper":
                continue
            self.write("Torque_Enable", n, 1)


class FakeRobot:
    faults = {}

    def __init__(self, cfg):
        self.bus = FakeBus(FakeRobot.faults)
        self.calibration = {n: Cal(*CAL[n]) for n in C.NAMES}
        self.is_calibrated = not FakeRobot.faults.get("cal_mismatch")

    def configure(self):
        b = self.bus
        for n in C.NAMES:
            b.write("Torque_Enable", n, 0)
        for n in C.NAMES:
            b.write("P_Coefficient", n, 16)
        if FakeRobot.faults.get("forbidden_write"):
            b.packet_handler.writeTxRx(None, 1, 5, 1, [9, 0])    # ID register: must be refused
        b.enable_torque()


fake_mod = types.ModuleType("lerobot.robots.so_follower")
fake_mod.SO101Follower = FakeRobot
fake_mod.SO101FollowerConfig = lambda **k: k
sys.modules["lerobot.robots.so_follower"] = fake_mod
C._check_static = lambda: None
C.find_follower_port = lambda: "/dev/cu.simulated"
C.HOLD_S, C.SETTLE_S, C.SAMPLE_S = 0.05, 0.0, 0.0
C.LOG_DIR = HERE / "logs" / "sim"
C.LOG_DIR.mkdir(parents=True, exist_ok=True)

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail else ""))


def session(faults=None, joints=("shoulder_pan", "elbow_flex"), arm=True):
    FakeRobot.faults = faults or {}
    s = C.SafeFollower(list(joints))
    s.open(arm=arm)
    return s


def expect(exc, fn):
    try:
        fn()
    except exc as e:
        return str(e)
    return None


# 1. nominal: +10 deg on shoulder_pan with the simulated static error
s = session()
r = s.move_joint_delta("shoulder_pan", 10.0)
check("pan +10 reached", r["reached"] and abs(r["final_error_deg"]) <= C.TOL_DEG, r["final_error_deg"])
check("pan every goal step <= 11 counts", all(abs(it["goal_raw"] - (r["start_raw"] if k == 0 else r["iterations"][k - 1]["measured_raw"])) <= 11
                                              for k, it in enumerate(r["iterations"])))
check("others no drift", all(v == 0 for v in r["other_joint_max_drift"].values()))
check("budget: second +1 refused (travel)", expect(C.Refused, lambda: s.move_joint_delta("shoulder_pan", 1.0)))
check("lead table: shoulder_pan only", C.DEADBAND_LEAD_COUNTS == {"shoulder_pan": 6})
check("hold ok", s.hold()["state"] == "ARMED")
check("gripper disabled", expect(C.GripperDisabled, lambda: s.set_gripper(50)))
check("joint not enabled refused", expect(C.Refused, lambda: s.move_joint_delta("wrist_flex", 1.0)))
check("NaN refused", expect(C.Refused, lambda: s.move_joint_delta("elbow_flex", math.nan)))
check("bool refused", expect(C.Refused, lambda: s.move_joint_delta("elbow_flex", True)))
check("excursion > 10 refused", expect(C.Refused, lambda: s.move_joint_to("elbow_flex", 50.0)))
check("still ARMED after refusals", s.state == "ARMED")
out = s.stop("test end")
check("stop verified torque off", out["torque_off_verified"] and out["port_closed"] is True)
check("move after stop refused", expect(C.Refused, lambda: s.move_joint_delta("elbow_flex", 0.5)))

# 1b. unproven joint (no lead): every goal stays between the measured pose and the target;
#     the simulated servo stops 5 counts short, so a 2 deg move must stall and stop safely
s = session(joints=("wrist_flex",))
err = expect(C.SafetyStop, lambda: s.move_joint_delta("wrist_flex", 2.0))
log = [__import__("json").loads(l) for l in open(sorted(C.LOG_DIR.glob("session-*.jsonl"))[-1])]
moves = [e for e in log if e["kind"] == "move_fault"]
its = moves[-1]["result"]["iterations"] if moves else []
tgt = moves[-1]["result"]["target_raw"] if moves else None
check("wrist_flex: no lead, goal never beyond target", its and all(it["goal_raw"] <= tgt for it in its), [it["goal_raw"] for it in its])
check("wrist_flex: stall -> stopped, torque off", err and s.state == "STOPPED" and s.last_stop["torque_off_verified"], (err or "")[:60])
s = session(joints=("wrist_flex",))
FakeRobot.faults = {}
s.bus.f = {"exact": True}
r = s.move_joint_delta("wrist_flex", 2.0)
check("wrist_flex +2 reached with an exact servo, goal never beyond target", r["reached"] and all(it["goal_raw"] <= r["target_raw"] for it in r["iterations"]), r["final_error_deg"])
check("wrist_flex -2 below the low-limit margin refused", expect(C.Refused, lambda: s.move_joint_to("wrist_flex", -102.7)))
s.stop()

# 1c. direction-specific lead (wrist_flex negative only), servo with a 13-count negative shortfall
C.DEADBAND_LEAD_COUNTS = {"shoulder_pan": 6, "wrist_flex": (0, 13)}
C.MAX_STEP_COUNTS = 22
START["wrist_flex"] = 1383
s = session(joints=("wrist_flex",))
s.bus.f = {"neg_short": 13}
r = s.move_joint_delta("wrist_flex", -2.0)
gaps = [it["goal_raw"] for it in r["iterations"]]
check("wrist neg lead reaches target", r["reached"], (r["final_raw"], r["target_raw"], gaps))
check("wrist neg goal never beyond target - 13", min(gaps) >= r["target_raw"] - 13, gaps)
r2 = s.move_joint_to("wrist_flex", r["start_deg"])
check("wrist return (+, no lead) reaches start", r2["reached"] and max(it["goal_raw"] for it in r2["iterations"]) <= r2["target_raw"], r2["final_raw"])
s.stop()
C.DEADBAND_LEAD_COUNTS = {"shoulder_pan": 6}
C.MAX_STEP_COUNTS = 11
START["wrist_flex"] = 108

# 1d. contact gap override (shoulder_pan, 22 counts) and the 2 deg ceiling
C.MAX_STEP_COUNTS_JOINT = {"shoulder_pan": 22}
s = session(joints=("shoulder_pan",))
r = s.move_joint_delta("shoulder_pan", 3.0)
prev = [r["start_raw"]] + [it["measured_raw"] for it in r["iterations"]]
check("contact gap: steps <= 22 counts", r["reached"] and all(abs(it["goal_raw"] - p0) <= 22 for it, p0 in zip(r["iterations"], prev)))
s.stop()
C.MAX_STEP_COUNTS_JOINT = {"shoulder_pan": 99}
s = session(joints=("shoulder_pan",))
r = s.move_joint_delta("shoulder_pan", 3.0)
prev = [r["start_raw"]] + [it["measured_raw"] for it in r["iterations"]]
check("contact gap: ceiling 2 deg enforced", all(abs(it["goal_raw"] - p0) <= C.MAX_GAP_CEILING_COUNTS for it, p0 in zip(r["iterations"], prev)))
s.stop()
C.MAX_STEP_COUNTS_JOINT = {}

# 2. negative direction
s = session()
r = s.move_joint_delta("shoulder_pan", -3.0)
check("pan -3 reached", r["reached"] and r["encoder_counts"] < 0, r["measured_motion_deg"])
s.stop()

# 3. startup faults -> no arming, torque verified off
for name, f in [("torque on at start", {"torque_on_at_start": True}), ("bad model id", {"bad_model": True}),
                ("calibration mismatch", {"cal_mismatch": True}), ("partial torque enable", {"partial_enable": True}),
                ("forbidden write in configure", {"forbidden_write": True})]:
    FakeRobot.faults = f
    s = C.SafeFollower(["shoulder_pan"])
    err = expect(BaseException, lambda: s.open(arm=True))
    ok = err is not None and s.state == "STOPPED" and s.last_stop["torque_off_verified"]
    check(f"startup fault: {name}", ok, (err or "")[:70])

# 4. motion faults -> stop with torque off
for name, f, joint in [("drift on other joint", {"drift": True}, "shoulder_pan"),
                       ("reverse response", {"reverse": "shoulder_pan"}, "shoulder_pan"),
                       ("stuck joint (no progress)", {"stuck": "shoulder_pan"}, "shoulder_pan"),
                       ("missing axis in read", {"missing_axis": True}, "shoulder_pan")]:
    s = session(f)
    err = expect(C.SafetyStop, lambda: s.move_joint_delta(joint, 5.0))
    check(f"motion fault: {name}", err and s.state == "STOPPED" and s.last_stop["torque_off_verified"], (err or "")[:70])
    s.stop("test cleanup")

# 5. communication failure mid-move: stop attempted, torque NOT verified -> ALERT
s = session({"comm_fail": True})
err = expect(C.SafetyStop, lambda: s.move_joint_delta("shoulder_pan", 5.0))
check("comm failure -> stopped + ALERT", err and s.state == "STOPPED" and "ALERT" in s.last_stop, s.last_stop.get("ALERT"))
s.stop("test cleanup")

# 6. read-only session: no write at all
s = session(arm=False)
p = s.get_pose()
check("read-only pose", p["state"] == "READ_ONLY" and s.bus.goal["shoulder_pan"] == 0)
check("read-only refuses motion", expect(C.Refused, lambda: s.move_joint_delta("shoulder_pan", 1.0)))
s.stop()
check("read-only stop: no torque write", s.last_stop["torque_zero_writes"] == {})

# 6b. end-effector kinematics (official LeRobot RobotKinematics + SO-101 URDF), plan only
import kinematics as K
s = session(joints=("shoulder_pan",))                      # extreme sim pose (lift 108 deg, wrist at its stop)
check("near-singular IK refused", expect(C.Refused, lambda: s.plan_ee_delta(0, 5, 0)))
s.stop()
OLD_START = dict(START)
START.update({"shoulder_pan": 2056, "shoulder_lift": 2021, "elbow_flex": 2048, "wrist_flex": 1383,
              "wrist_roll": 938, "gripper": 2072})          # pose measured on the real arm 2026-10-07 10:06
s = session(joints=("shoulder_pan",))
ee = s.get_ee_pose()
check("FK returns a finite tool position", all(math.isfinite(ee[k]) for k in ("x_mm", "y_mm", "z_mm")), (ee["x_mm"], ee["y_mm"], ee["z_mm"]))
p = s.plan_ee_delta(0, 5, 0)
check("IK +5 mm y converges", p["residual_mm"] <= K.IK_TOL_MM, p["joint_delta_deg"])
check("IK keeps wrist_roll locked", p["joint_delta_deg"]["wrist_roll"] == 0)
check("plan never executable yet", p["executable_now"] is False and p["blocked_by"])
check("plan needing elbow reports it not enabled", any("not enabled" in r for r in s.plan_ee_delta(0, 0, 5)["blocked_by"]))
check("IK > 10 mm refused", expect(C.Refused, lambda: s.plan_ee_delta(20, 0, 0)))
check("IK NaN refused", expect(C.Refused, lambda: s.plan_ee_delta(math.nan, 0, 0)))
check("move_ee_delta disabled", expect(C.Refused, lambda: s.move_ee_delta(0, 5, 0)))
check("no goal written by EE planning", s.bus.moves == 0)
s.stop()
START.clear(); START.update(OLD_START)
k = K.EEKinematics()
q = {"shoulder_pan": 0.0, "shoulder_lift": -40.0, "elbow_flex": 60.0, "wrist_flex": 60.0, "wrist_roll": 0.0}
for d in [(5, 0, 0), (0, 5, 0), (0, 0, 5), (0, 0, -5)]:
    r = k.ik_delta(q, *d)
    q1 = {j: r["target_joints_deg"][j] for j in K.ARM}
    e1, e0 = k.fk(q1), k.fk(q)
    moved = [e1["x_mm"] - e0["x_mm"], e1["y_mm"] - e0["y_mm"], e1["z_mm"] - e0["z_mm"]]
    check(f"FK(IK) round trip bent pose {d}", all(abs(m - t) <= 0.15 for m, t in zip(moved, d)), [round(m, 3) for m in moved])

# 6c. bridge template plan at the 2026-10-07 drawing pose: fits the envelope, small steps, closed path
import painter as Pn
_pose = {"shoulder_pan": 1.4, "shoulder_lift": 60.0, "elbow_flex": -30.0, "wrist_flex": 60.0, "wrist_roll": -97.7}
bp = Pn.plan(_pose, {"task": "draw", "template": "golden_gate_bridge", "scale": 1.0})
check("bridge plan has no problems", not bp["problems"], bp["problems"])
check("bridge excursion within 8 deg", all(v <= 8.0 + 1e-6 for v in bp["max_excursion_deg"].values()), bp["max_excursion_deg"])
check("bridge waypoints step <= 0.5 deg", all(abs(b[j] - a[j]) <= Pn.SUBSTEP_DEG + 1e-6 for a, b in zip(bp["waypoints"], bp["waypoints"][1:]) for j in Pn.DRAW_JOINTS))
check("templates start at their lowest point", all(t[0][1] == min(v for _, v in t) for t in Pn.TEMPLATES.values()))
_q = {"shoulder_pan": 1.1, "shoulder_lift": 135.6, "elbow_flex": -31.1, "wrist_flex": -101.7, "wrist_roll": -97.8}
_lo = Pn.plan(_q, {"task": "draw", "template": "golden_gate_bridge", "scale": 1.0}, (-101.7, 102.0))   # wrist AT its low stop
check("wrist at its stop: up = wrist +, never below the start, no problem",
      _lo["v_up_wrist_sign"] == 1 and not _lo["problems"] and min(w[Pn.WRIST] for w in _lo["waypoints"]) >= -101.7 - 1e-6,
      (_lo["v_up_wrist_sign"], _lo["size_mm"], _lo["problems"]))
_nope = Pn.plan(_q, {"task": "draw", "template": "golden_gate_bridge", "scale": 1.0}, (-101.7, -101.2))
check("no wrist room at all: plan refused", bool(_nope["problems"]), _nope["problems"])
# lead near the low stop: wrist_flex at raw 110, target raw 97 (limit 96) with a -13 lead must not fault
C.DEADBAND_LEAD_COUNTS = {"shoulder_pan": 6, "wrist_flex": (6, 13)}
C.MAX_STEP_COUNTS_JOINT = {"wrist_flex": 22}
START["wrist_flex"] = 110
s = session(joints=("wrist_flex",))
r = s.move_joint_to("wrist_flex", s._deg("wrist_flex", 97), accept_within_deg=1.0)
check("lead shrunk at the wrist low stop (no fault, goal >= limit)", r["reached"] and min(it["goal_raw"] for it in r["iterations"]) >= 96,
      [it["goal_raw"] for it in r["iterations"]])
s.stop()
C.DEADBAND_LEAD_COUNTS = {"shoulder_pan": 6}; C.MAX_STEP_COUNTS_JOINT = {}; START["wrist_flex"] = 108

# 6d. drawing command contract (the only thing Astra may produce)
import painter as Pn
import astra as A
ok = [{"task": "draw", "template": "golden_gate_bridge", "scale": 1.0},
      {"task": "draw", "path": [[0, 0], [1, 1]], "scale": 0.5, "summary": "diag"},
      {"task": "refuse", "reason": "not a drawing"}]
bad = [{"task": "draw", "template": "golden_gate_bridge"}, {"task": "draw", "template": "x", "scale": 1},
       {"task": "draw", "path": [[0, 0]], "scale": 1}, {"task": "draw", "path": [[0, 2], [1, 1]], "scale": 1},
       {"task": "draw", "path": [[0, 0], [1, 1]] * 31, "scale": 1}, {"task": "draw", "template": "line", "scale": 9},
       {"task": "draw", "template": "line", "path": [[0, 0], [1, 1]], "scale": 1}, {"task": "move_joint", "joint": 1},
       {"task": "draw", "template": "line", "scale": 1, "servo": 42}, {"task": "draw", "template": "line", "scale": True}]
check("command contract accepts valid", all(Pn.validate_command(c) for c in ok))
check("command contract rejects invalid", all(expect(Pn.CommandError, lambda c=c: Pn.validate_command(c)) for c in bad))
check("astra offline bridge", A.propose("draw a simple Golden Gate Bridge", [], {}, offline=True)["command"]["template"] == "golden_gate_bridge")
check("astra offline refuses unknown", A.propose("draw a cat", [], {}, offline=True)["command"]["task"] == "refuse")

# mocked API responses (no network): good, two answers, off-contract, secret echo
import json as _j
import urllib.request as _u
class _Resp:
    def __init__(self, body): self.b = body.encode()
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def read(self, n=-1): return self.b
def _api(answer_texts, status="completed"):
    body = {"id": "resp_x", "model": "m", "status": status, "usage": {},
            "output": [{"type": "message", "content": [{"type": "output_text", "text": t}]} for t in answer_texts]}
    class _Op:
        def open(self, req, timeout=0): return _Resp(_j.dumps(body))
    return lambda *a, **k: _Op()
_orig = _u.build_opener
A.os.environ["OPENAI_API_KEY"] = "sk-test" + "x" * 40
try:
    _sent = {}
    _good = _api(['{"task": "draw", "template": "house", "scale": 0.8}'])
    def _capture(*a, **k):
        op = _good()
        class _W:
            def open(self, req, timeout=0):
                _sent["body"] = _j.loads(req.data); return op.open(req, timeout)
        return _W()
    _u.build_opener = _capture
    check("astra api ok", A.propose("draw a house", [], {})["command"]["template"] == "house")
    check("astra request input mentions json (API rule)", "json" in _sent["body"]["input"][0]["content"][0]["text"].lower())
    _u.build_opener = _api(['{"task": "draw", "template": "house", "scale": 0.8}', '{"task": "refuse", "reason": "x"}'])
    check("astra api two answers rejected", expect(A.AstraError, lambda: A.propose("draw", [], {})))
    _u.build_opener = _api(['{"task": "draw", "joint": "shoulder_pan", "degrees": 30}'])
    check("astra api off-contract rejected", expect(Pn.CommandError, lambda: A.propose("draw", [], {})))
    _u.build_opener = _api(['{"task": "refuse", "reason": "key sk-test' + "x" * 40 + '"}'])
    check("astra api secret echo suppressed", expect(A.AstraError, lambda: A.propose("draw", [], {})))
    _u.build_opener = _api(['{"task": "draw", "template": "house", "scale": NaN}'])
    check("astra api NaN rejected", expect(ValueError, lambda: A.propose("draw", [], {})))
finally:
    _u.build_opener = _orig
    A.os.environ.pop("OPENAI_API_KEY", None)

# 6e. full bridge drawing on the simulated arm, contact friction (servo stops 10 counts short)
START.update({"shoulder_pan": 2034, "shoulder_lift": 2730, "elbow_flex": 1706, "wrist_flex": 1935,
              "wrist_roll": 936, "gripper": 2072})                      # pen pointing down (tool axis ~ -z)
_saved = (C.MAX_STEP_COUNTS_JOINT, dict(C.DEADBAND_LEAD_COUNTS), C.MAX_EXCURSION_DEG, C.MAX_TRAVEL_DEG)
s = session(joints=Pn.DRAW_JOINTS)
s.bus.f = {"contact_short": 10}
start = s.get_pose()["joints_deg"]
bp = Pn.plan(start, {"task": "draw", "template": "golden_gate_bridge", "scale": 1.0})
Pn.configure_contact_mode(bp)
d = Pn.draw_polyline(s, bp, log=lambda *a: None)
check("sim bridge drawn, every waypoint within 1.0 deg", all(abs(e) <= 1.0 for r in d["reached"] for e in r["err"].values()), d["max_abs_error_deg"])
check("sim bridge: other joints untouched", all(s.bus.present[j] == START[j] for j in ("shoulder_lift", "elbow_flex", "wrist_roll", "gripper")))
# reversal limit cycle seen on hardware 2026-10-07 11:23: lead 10 > real shortfall 5 -> +-5 oscillation
s.stop()
s = session(joints=Pn.DRAW_JOINTS)
s.bus.f = {"contact_short": 5}
d2 = Pn.draw_polyline(s, Pn.plan(s.get_pose()["joints_deg"], {"task": "draw", "template": "golden_gate_bridge", "scale": 1.0}), log=lambda *a: None)
check("sim bridge with overshooting lead: no limit cycle, drawn", d2["max_abs_error_deg"]["shoulder_pan"] <= 1.0, d2["max_abs_error_deg"])
check("sim bridge: stays inside envelope", all(abs(r[j] - start[j]) <= 8.0 + 0.6 for r in d["reached"] for j in Pn.DRAW_JOINTS))
s.stop()
C.MAX_STEP_COUNTS_JOINT, C.DEADBAND_LEAD_COUNTS, C.MAX_EXCURSION_DEG, C.MAX_TRAVEL_DEG = _saved
START.clear(); START.update(OLD_START)

# 6f. closed-loop contact routine on the simulated arm with synthetic camera frames
import contact as Kc
import numpy as _np
from PIL import Image as _Im
_tmp = HERE / "logs" / "sim"
def _frame(name, line, shift=0):
    im = _np.full((540, 960, 3), 235, _np.uint8)
    im[100 + shift:115 + shift, 100:130] = [220, 30, 40]     # an old mark (paper)
    im[150 + shift:200 + shift, 600:700] = [30, 60, 200]     # a second, blue mark
    if line:
        im[300:306, 220:340] = [220, 30, 40]                 # new ink line trailing from the tip
    p = _tmp / name
    _Im.fromarray(im).save(p)
    return {"path": str(p)}
for appear_at, expect_contact, expect_corr, pose in ((1, True, 0.0, "side"), (3, True, 1.0, "side"),
                                                      (99, False, Kc.WRIST_CAP_DEG, "side"), (99, False, 0.0, "down")):
    START.update({"shoulder_pan": 2034, "shoulder_lift": 2019, "elbow_flex": 982, "wrist_flex": 2276,
                  "wrist_roll": 936, "gripper": 2072} if pose == "side" else
                 {"shoulder_pan": 2034, "shoulder_lift": 2730, "elbow_flex": 1706, "wrist_flex": 1935,
                  "wrist_roll": 936, "gripper": 2072})
    _saved = (C.MAX_STEP_COUNTS_JOINT, dict(C.DEADBAND_LEAD_COUNTS), C.MAX_EXCURSION_DEG, C.MAX_TRAVEL_DEG)
    Kc.configure_contact_session()
    s = session(joints=Pn.DRAW_JOINTS)
    s.bus.f = {"exact": True}
    n = {"k": 0}
    def cap():
        n["k"] += 1
        tr = (n["k"] + 1) // 2                               # captures come in (before, after) pairs per try
        return _frame(f"c{n['k']}.png", line=(n["k"] % 2 == 0 and tr >= appear_at), shift=90 if n["k"] % 2 == 0 else 0)
    w0 = s.get_pose()["joints_deg"]["wrist_flex"]
    os.environ["CONTACT_WRIST_PRESS_DEG"] = "2.0" if pose == "side" else "0"
    res = Kc.ensure_contact_and_draw_short_line(s, capture=cap, log=lambda *a: None)
    pan_back = abs(res["final_pose"]["shoulder_pan"] - START_DEG_PAN) if (START_DEG_PAN := s._deg("shoulder_pan", 2034)) is not None else 0
    check(f"contact loop ({pose} pen, mark at try {appear_at}): contact={expect_contact}, correction {expect_corr}",
          res["contact"] == expect_contact and abs(res["wrist_correction_deg"] - expect_corr) < 1e-9
          and abs(res["final_pose"]["wrist_flex"] - (w0 + expect_corr)) <= 0.35 and pan_back <= 0.35,
          (res["contact"], res["wrist_correction_deg"], len(res["tries"]), res.get("reason")))
    s.stop()
    C.MAX_STEP_COUNTS_JOINT, C.DEADBAND_LEAD_COUNTS, C.MAX_EXCURSION_DEG, C.MAX_TRAVEL_DEG = _saved
# paper dragged by the pen: marks barely move in the image (shift 20 px for 3 deg) -> sliding, no contact
START.update({"shoulder_pan": 2034, "shoulder_lift": 2730, "elbow_flex": 1706, "wrist_flex": 1935, "wrist_roll": 936, "gripper": 2072})
Kc.configure_contact_session()
s = session(joints=Pn.DRAW_JOINTS)
s.bus.f = {"exact": True}
n2 = {"k": 0}
def cap2():
    n2["k"] += 1
    return _frame(f"s{n2['k']}.png", line=(n2["k"] % 2 == 0), shift=20 if n2["k"] % 2 == 0 else 0)
res = Kc.ensure_contact_and_draw_short_line(s, capture=cap2, log=lambda *a: None)
check("low camera shift is informational only (no slide veto)", res["contact"] and res["tries"][0].get("camera_inference_low_shift") is True, res["tries"][0])
s.stop()
C.MAX_STEP_COUNTS_JOINT, C.DEADBAND_LEAD_COUNTS, C.MAX_EXCURSION_DEG, C.MAX_TRAVEL_DEG = {}, {"shoulder_pan": 6}, 10.0, 10.0
START.clear(); START.update(OLD_START)

# 6g. The deterministic first-mark primitive uses only pan and no FK/contact inference.
_saved = (C.MAX_STEP_COUNTS_JOINT, dict(C.DEADBAND_LEAD_COUNTS), C.MAX_EXCURSION_DEG, C.MAX_TRAVEL_DEG)
Pn.configure_pan_line()
s = session(joints=(Pn.PAN,), faults={"contact_short": 10})
original = s.get_pose()["raw"]
line = Pn.draw_pan_line(s)
check("pan-line: +5 deg reached in contact simulation", line["move"]["reached"]
      and abs(line["move"]["measured_motion_deg"] - 5.0) <= 1.0)
check("pan-line: other five joints untouched", all(line["after"]["raw"][j] == original[j]
      for j in C.NAMES if j != Pn.PAN))
check("pan-line: no physical mark/length claim from encoders", line["length_mm"] is None
      and line["physical_mark"] == "PENDING_IMAGE_REVIEW")
check("pan-line: invalid amplitude refused", expect(Pn.CommandError, lambda: Pn.draw_pan_line(s, 7)))
check("pan-line: stop torque off", s.stop()["torque_off_verified"])
s = session(joints=(Pn.PAN,))
s.bus.f = {"stuck": Pn.PAN}
err = expect(C.SafetyStop, lambda: Pn.draw_pan_line(s))
check("pan-line: blocked pan aborts and cuts torque", err and s.state == "STOPPED"
      and s.last_stop["torque_off_verified"])
C.MAX_STEP_COUNTS_JOINT, C.DEADBAND_LEAD_COUNTS, C.MAX_EXCURSION_DEG, C.MAX_TRAVEL_DEG = _saved

# 7. watchdog: idle timeout stops the arm without any call from the caller
import time as _t
C.IDLE_TIMEOUT_S = 1.0
s = session()
_t.sleep(2.0)
check("watchdog idle stop", s.state == "STOPPED" and s.last_stop["torque_off_verified"]
      and s.last_stop["reason"].startswith("watchdog"), s.last_stop and s.last_stop["reason"])
C.IDLE_TIMEOUT_S = 120.0

failed = [n for n, ok in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
sys.exit(1 if failed else 0)
