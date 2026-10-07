"""End-effector kinematics for the Boris controller, built on the OFFICIAL LeRobot 0.6.1 solver.

Reuses `lerobot.model.kinematics.RobotKinematics` (placo) and the official SO-101 URDF from
TheRobotStudio (urdf/SO101/so101_new_calib.urdf, commit 385e8d7c, Apache-2.0). No IK of our own:
this module only adds the checks that the upstream teleop loop gets implicitly from running at
30 Hz (iterate to convergence) and refuses anything that does not converge cleanly.

Conventions (as in the upstream phone / EE teleop examples):
  * joint angles = LeRobot DEGREES normalisation of our calibration (controller.get_pose());
  * frame = URDF base_link: x forward, y left, z up; positions reported in millimetres;
  * tool frame = "gripper_frame_link".
Position-only IK (orientation_weight = 0): the SO-101 has 5 arm joints; upstream's default soft
orientation weight (0.01) diverged near our current pose in offline tests (elbow -97 deg).
wrist_roll is locked (masked) during IK: it is unproven and does not help a pen-tip position.
Nothing here talks to hardware.
"""
from __future__ import annotations

import pathlib

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
URDF = HERE / "urdf/SO101/so101_new_calib.urdf"
URDF_SHA256 = "3a65d2d35e68a8d2f0c2cc176d19b884506543c93ba72980145b80abe276022c"
ARM = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll"]
IK_LOCKED = ("wrist_roll",)
IK_MAX_ITERS = 20
IK_TOL_MM = 0.1
MAX_EE_DELTA_MM = 10.0                 # one request; a drawing move is made of several
MAX_JOINT_CHANGE_PER_MM = 1.5          # degrees per mm requested; above -> refuse (near-singular / divergence)


class KinematicsError(ValueError):
    pass


class EEKinematics:
    def __init__(self, urdf: pathlib.Path = URDF):
        import hashlib
        got = hashlib.sha256(pathlib.Path(urdf).read_bytes()).hexdigest()
        if got != URDF_SHA256:
            raise KinematicsError(f"URDF sha256 {got[:12]} != pinned {URDF_SHA256[:12]}")
        from lerobot.model.kinematics import RobotKinematics      # official solver (placo)
        self.k = RobotKinematics(str(urdf), target_frame_name="gripper_frame_link", joint_names=ARM)
        for j in IK_LOCKED:
            self.k.solver.mask_dof(j)

    @staticmethod
    def _q(joints_deg: dict) -> np.ndarray:
        return np.array([float(joints_deg[j]) for j in ARM], dtype=float)

    def fk(self, joints_deg: dict) -> dict:
        T = self.k.forward_kinematics(self._q(joints_deg))
        return {"x_mm": round(float(T[0, 3]) * 1000, 3), "y_mm": round(float(T[1, 3]) * 1000, 3),
                "z_mm": round(float(T[2, 3]) * 1000, 3), "tool_z_axis": [round(float(v), 4) for v in T[:3, 2]],
                "frame": "URDF base_link (x fwd, y left, z up)"}

    def ik_delta(self, joints_deg: dict, dx_mm: float, dy_mm: float, dz_mm: float) -> dict:
        d = np.array([dx_mm, dy_mm, dz_mm], dtype=float)
        if not np.all(np.isfinite(d)):
            raise KinematicsError("delta must be finite")
        n = float(np.linalg.norm(d))
        if n > MAX_EE_DELTA_MM:
            raise KinematicsError(f"|delta| {n:.2f} mm > {MAX_EE_DELTA_MM} mm per request")
        q0 = self._q(joints_deg)
        T0 = self.k.forward_kinematics(q0)
        Td = T0.copy()
        Td[:3, 3] += d / 1000.0
        q = q0.copy()
        err = None
        for it in range(1, IK_MAX_ITERS + 1):
            q = self.k.inverse_kinematics(q, Td, position_weight=1.0, orientation_weight=0.0)
            err = float(np.linalg.norm(self.k.forward_kinematics(q)[:3, 3] - Td[:3, 3]) * 1000)
            if err <= IK_TOL_MM:
                break
        dq = q - q0
        if err is None or err > IK_TOL_MM:
            raise KinematicsError(f"IK did not converge: residual {err:.3f} mm after {IK_MAX_ITERS} iterations")
        for j in IK_LOCKED:
            if abs(dq[ARM.index(j)]) > 1e-6:
                raise KinematicsError(f"locked joint {j} moved in IK ({dq[ARM.index(j)]:.4f} deg)")
        worst = float(np.max(np.abs(dq)))
        if n > 0 and worst > MAX_JOINT_CHANGE_PER_MM * max(n, 1.0):
            raise KinematicsError(f"IK asks {worst:.2f} deg on one joint for {n:.2f} mm (near-singular): refused")
        T1 = self.k.forward_kinematics(q)
        R0, R1 = T0[:3, :3], T1[:3, :3]
        tilt = float(np.degrees(np.arccos(np.clip((np.trace(R0.T @ R1) - 1) / 2, -1, 1))))
        return {"target_joints_deg": {j: round(float(v), 4) for j, v in zip(ARM, q)},
                "joint_delta_deg": {j: round(float(v), 4) for j, v in zip(ARM, dq)},
                "ik_iterations": it, "residual_mm": round(err, 4), "tool_tilt_change_deg": round(tilt, 3),
                "ee_start_mm": [round(float(v) * 1000, 3) for v in T0[:3, 3]],
                "ee_target_mm": [round(float(v) * 1000, 3) for v in Td[:3, 3]]}
