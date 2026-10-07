# Cinématique officielle LeRobot pour le contrôleur Boris — 2026-10-07 10:12 CEST

- **GO** : HQ.
- **Aucun mouvement matériel.** Seules opérations sur le bras : 1 session en lecture seule (0 écriture, couple 0). Pas d'Astra.

## KINEMATICS_AVAILABLE_IN_0_6_1 = YES (extra `kinematics` requis)

Présents dans le LeRobot 0.6.1 installé :

- `lerobot/model/kinematics.py` : `RobotKinematics` (placo) ;
- `lerobot/robots/so_follower/robot_kinematic_processor.py` : `EEReferenceAndDelta`, `EEBoundsAndSafety`, `InverseKinematicsEEToJoints`, `GripperVelocityToJoint`.
  - `ForwardKinematicsJointsToEE` : absent sous ce nom. Non nécessaire : `RobotKinematics.forward_kinematics` suffit.

Exemples amont au tag `v0.6.1` (commit `7e241bd6`) : `examples/phone_to_so100/teleoperate.py` et `examples/so100_to_so100_EE/teleoperate.py`, lus.

- Ils branchent la chaîne sur `robot.connect()` / `send_action()`. **Non repris** : nous gardons notre démarrage prouvé.
- `EEBoundsAndSafety` **rogne silencieusement** les positions hors bornes. **Non repris** : notre politique est de refuser.

**Seule dépendance manquante** : `placo`.

- Ajoutée par l'extra officiel `lerobot[...,kinematics]==0.6.1` (`pyproject.toml` + `uv.lock`) : **uniquement des ajouts**, aucun paquet existant modifié. Vérifié par le diff du lock (seule la ligne des extras de lerobot change).
- Installés : placo 0.9.15, lerobot 0.6.1 inchangé. Les empreintes des sources LeRobot auditées passent toujours.

## URDF_READY = PARTIAL

- `boris/urdf/SO101/so101_new_calib.urdf`, TheRobotStudio/SO-ARM100, commit `385e8d7c` (2025-07-02), sha256 `3a65d2d3…022c`. Maillages STL (13, 15 Mo) et licence Apache-2.0 inclus.
- Chargement par placo en 1,1 s. Noms d'articulations identiques aux noms des moteurs.
- Avertissements placo d'auto-collision en position neutre (maillages adjacents) : sans effet sur FK/IK.
- **Non vérifié physiquement** : correspondance entre les degrés LeRobot de notre calibration et le zéro de l'URDF.
  - La FK de la pose actuelle donne la pointe à x = 384,5 mm, y = 10,6 mm, z = 216,6 mm, outil vers l'avant et environ 9° vers le bas (bras en « L »).
  - **À confirmer au mètre ruban ou sur photo de côté.**
  - Point de vigilance : `wrist_flex` a une plage asymétrique (91..2414). Son zéro LeRobot (milieu de plage 1252,5) diffère du recentrage de calibration (2047) d'environ 70°. Cohérent avec une course de ±102° centrée, mais **ASSUMED**.

## Intégration réalisée (hors ligne)

- **`boris/kinematics.py`** : enveloppe de `RobotKinematics` (aucune IK maison). L'URDF est épinglé par son SHA.
  - IK **position seule**. Avec `orientation_weight = 0.01` (valeur amont par défaut), l'IK diverge près de la pose actuelle (coude à −97° pour 5 mm). La position seule converge en 1 à 3 itérations.
  - Itérée jusqu'à moins de 0,1 mm, au plus 20 itérations ; `wrist_roll` bloqué (`mask_dof`).
  - Refus : delta de plus de 10 mm, NaN, non-convergence, plus de 1,5° par mm sur une articulation (près d'une singularité).
- **`boris/controller.py`** (le démarrage, les bornes, le chien de garde et l'arrêt sont inchangés) :
  - `get_ee_pose()` : fonctionne aussi en lecture seule ;
  - `plan_ee_delta(dx, dy, dz)` : IK seulement, n'écrit jamais, renvoie `executable_now = False` avec les raisons ;
  - `move_ee_delta()` : **désactivé** (Refused).
- **`boris/requirements.txt`** : `lerobot[feetech,kinematics]==0.6.1`. README : section sur l'état de l'API en millimètres.

## Tests

- `sim_test.py` : **47/47**, dont 14 nouveaux contrôles cinématiques :
  - IK quasi singulière refusée ;
  - FK finie ;
  - convergence de l'IK, `wrist_roll` bloqué ;
  - plan jamais exécutable, articulations non activées signalées ;
  - refus au-delà de 10 mm et sur NaN ;
  - `move_ee_delta` désactivé, 0 écriture de consigne ;
  - aller-retour FK(IK) à ±0,15 mm sur 4 directions.
- **Bras réel, lecture seule** : `get_ee_pose` et `plan_ee_delta(0, 0, +5)` sur la pose 2056 / 2021 / 2048 / 1383 / 938 / 2072. Session sans aucune écriture (`open`, `precheck_ok`, `stop`).
  - **+5 mm en z** demande : lift −0,17°, elbow −0,59°, wrist_flex −0,38° (résidu 0,04 mm).
  - **+5 mm en x** demande : lift +2,28°, elbow −1,66°, wrist_flex −1,49°.
  - **+5 mm en y** demande : pan −0,83°.

## READY_FOR_5MM_AIR_TEST = NO

Un mouvement de 5 mm en x ou z exige `shoulder_lift`, `elbow_flex` et `wrist_flex` ensemble, dans les deux sens. Or :

- `shoulder_lift` n'a jamais été testé ;
- `elbow_flex` est bloqué (0,09° pour 1° demandé) ;
- `wrist_flex` ne fonctionne qu'en montée (descente : arrêt à 1,1° de la consigne).

L'erreur statique de ces servos (P = 16, I = 0) vaut 0,5 à 1,1° par articulation, soit de l'ordre de 2 à 5 mm en bout d'outil, donc l'ordre de grandeur du mouvement lui-même.

Il manque aussi l'exécuteur multi-articulations (consignes synchronisées, ≤ 1° par pas et par articulation) et la vérification physique FK ↔ réel.

**Exception possible** : +5 mm en **y** n'exige que `shoulder_pan` (−0,83°), la seule articulation prouvée. Un essai « y seul » est faisable avec l'exécuteur actuel (`move_joint_delta`), après un GO.
