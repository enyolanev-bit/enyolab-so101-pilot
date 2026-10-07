# Concordance des poses leader / follower — lecture seule — 2026-10-06 22:59:55 CEST

- **GO** : HQ, contrôle final en lecture seule. Ni téléopération, ni activation du couple.
- **Script** : `2026-10-06-pose_match_probe.py`, sha256 `e327eb69011ace62ddb4bb991515d75c9b07ea0d63d76d6587aa6fab66e447b1`.
  - Un bras à la fois ; `FeetechMotorsBus` direct ; `connect(handshake=False)` ; ping ; `read(normalize=True)` avec la calibration **chargée depuis le fichier** (SHA vérifié) ; normalisation identique à LeRobot (DEGREES, pince RANGE_0_100) ; 10 échantillons par articulation.
  - Gardes PING/READ ; `closePort()` direct.
- **Log** : `2026-10-06T225954-pose-match.json`, sha256 `782fffb4d467b89a8d9374435155a5edbb0b3fdb950a9cfd966c37baf6fba692`.

## Sécurité

- Écritures : **0** (follower PING 6 / READ 156 ; leader PING 6 / READ 156).
- `Torque_Enable` = 0 sur les 6 servos de chaque bras, au début et à la fin.
- Registres de calibration == fichiers, pour les deux bras.
- Ports fermés.

## Mesures (moyennes de 10 échantillons ; écart entre échantillons = 0 partout)

| Articulation | Leader | Follower | \|Écart\| | > 5 ? | Leader brut / milieu | Follower brut / milieu |
|---|---|---|---|---|---|---|
| shoulder_pan | 1,41° | 2,07° | 0,66 | non | 2025 / 2009 | 2085 / 2061,5 |
| shoulder_lift | −0,13° | −2,07° | 1,93 | non | 2043 / 2044,5 | 2024 / 2047,5 |
| elbow_flex | −0,13° | −0,04° | 0,09 | non | 2046 / 2047,5 | 2047 / 2047,5 |
| wrist_flex | −0,13° | **−101,23°** | **101,10** | **oui** | 2044 / 2045,5 | **101** / 1252,5 |
| wrist_roll | 2,33° | **−96,40°** | **98,73** | **oui** | 2074 / 2047,5 | **951** / 2047,5 |
| gripper | 1,56 % | 7,35 % | 5,78 | oui (de peu) | 2045 / 2695,5 | 2140 / 2784,5 |

## Lecture

- **`shoulder_pan`, `shoulder_lift`, `elbow_flex` : concordants** (≤ 2°).
- **Le follower n'a vraisemblablement pas bougé.** Ses valeurs brutes (2085 / 2024 / 2047 / 101 / 951 / 2140) sont **identiques** à celles des mesures de 22:20 et 22:56. Seul le leader a changé (`shoulder_pan` 2025). La pose « aussi proche que possible » n'a donc pas été atteinte côté follower.
- **`wrist_flex`** : le follower est à 101 brut, à 10 pas de son `range_min` (91), c'est-à-dire **en butée basse par gravité** ; le leader est à son milieu. **Écart physique probable (ASSUMED).**
  - Par ailleurs, les repères diffèrent : pour une même valeur brute, le follower lit ≈ 70° de plus que le leader, car son milieu calibré est à 1252,5 contre 2045,5 pour le leader. Ce décalage brut n'est pas en soi une erreur : chaque bras a son propre `Homing_Offset`.
  - **Cause : non tranchée.**
- **`wrist_roll`** : le follower est à 951 brut (−96°), le leader près de son milieu (+2°). Rotation continue ; un écart physique d'environ 99° est **plausible** (ASSUMED).
- **`gripper`** : 5,8 %, juste au-dessus de la tolérance.

**Verdict : NON CONCLUANT pour `wrist_flex` et `wrist_roll`.** On ne peut pas attribuer l'écart à la calibration tant que le follower n'a pas été amené dans la même pose physique que le leader. Avec les poses actuelles, l'écart est **cohérent avec une différence physique** : poignet du follower en butée, rotation différente.

## Pour trancher (lecture seule, même sonde, nouveau fichier de sortie)

1. Amener le **leader** dans la pose du follower : `wrist_flex` en butée basse, comme le follower au repos ; tourner `wrist_roll` pour l'aligner visuellement sur le follower ; pince aux mêmes ouvertures. Ou soutenir le follower au milieu de sa course.
2. Relire. Si l'écart tombe sous 5°, l'écart venait des poses. S'il reste (≈ 70° sur `wrist_flex`), c'est un **décalage de calibration**.
3. Photo des deux bras pendant la mesure, comme preuve de la pose.
