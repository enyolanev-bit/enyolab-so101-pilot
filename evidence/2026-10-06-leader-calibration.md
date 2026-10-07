# Calibration LEADER `pilot001_leader` — 2026-10-06

> **Commit soumis à revue HQ** (AGENTS.md règle 6 : un fichier de calibration propre à une machine n'est pas commité sans revue HQ). Ce rapport reproduit le **contenu** du fichier. Le fichier lui-même n'est ni copié ni déplacé.

## Déroulé

| Heure (CEST) | Événement | Source |
|---|---|---|
| 19:57:02-06 | Premier lancement par l'agent (GO HQ). Connexion OK, arrêt sur l'invite « milieu de course ». | log agent |
| 20:28:45 | Annulation par SIGINT : `SOLeader disconnected.`, code de sortie 130, **aucun fichier créé**, port libéré (`lsof`), avant toute écriture de calibration. | log agent |
| ≤ 20:37:45 | **Calibration complète menée par l'opérateur dans son propre terminal** : LeRobot a affiché « calibration saved » et s'est déconnecté proprement. | **HUMAN_OBSERVED** (log console non fourni à l'agent) |
| 20:37:45 | `pilot001_leader.json` écrit (horodatage du fichier) | constaté |

Extrait du log du premier lancement annulé (chemins machine retirés) :

```text
INFO 2026-10-06 19:57:06 calibrate.py:89 {'robot': None, 'teleop': {'calibration_dir': None, 'id': 'pilot001_leader', 'num_read_retries': 2, 'port': '/dev/cu.usbmodem5B7B0154401', 'use_degrees': True}}
INFO 2026-10-06 19:57:06 so_leader.py:78 pilot001_leader SOLeader connected.
INFO 2026-10-06 19:57:06 so_leader.py:95 Running calibration of pilot001_leader SOLeader
Move pilot001_leader SOLeader to the middle of its range of motion and press ENTER....
INFO 2026-10-06 20:28:45 so_leader.py:163 pilot001_leader SOLeader disconnected.
KeyboardInterrupt   (SIGINT, exit code 130)
```

## Fichier — vérifié par l'agent, lecture seule

| Élément | Valeur |
|---|---|
| Chemin | `~/.cache/huggingface/lerobot/calibration/teleoperators/so_leader/pilot001_leader.json` |
| Taille | 912 octets |
| Modifié | 2026-10-06 20:37:45 |
| SHA-256 | `5fbbdb26af036610d9120e6be8063fb1aa0e63aaa13842bad6b5b6c553270f1a` |
| Contenu dans le dossier | ce seul fichier ; aucun autre id créé |

| Moteur | ID | drive_mode | homing_offset | range_min | range_max | Étendue |
|---|---|---|---|---|---|---|
| shoulder_pan | 1 | 0 | −2000 | 781 | 3512 | 2731 |
| shoulder_lift | 2 | 0 | 1063 | **1** | **4095** | **4094** |
| elbow_flex | 3 | 0 | −1431 | **0** | **4095** | **4095** |
| wrist_flex | 4 | 0 | −349 | **0** | **4095** | **4095** |
| wrist_roll | 5 | 0 | 1928 | 0 | 4095 | imposé par LeRobot (attendu) |
| gripper | 6 | 0 | −1828 | 2010 | 3251 | 1241 |

## Lecture

- **Procédure** : terminée. Fichier présent, 6 moteurs, IDs 1 à 6 ; message de sauvegarde et déconnexion propre selon l'opérateur.
- **`wrist_roll` 0..4095** : attendu. LeRobot l'impose, rotation continue.
- **`shoulder_pan` et `gripper`** : plages partielles, `MIN < 2047 < MAX`. Rien à signaler.
- ⚠️ **`shoulder_lift`, `elbow_flex`, `wrist_flex`** : plage enregistrée ≈ **tout le codeur** (0/1..4095).
  - Après `set_half_turn_homings`, la position vaut 2047 au « milieu ». Atteindre 0 **et** 4095 suppose ≈ ±180°, soit environ 360° de course, ce que ces articulations n'offrent pas mécaniquement.
  - Lecture la plus probable, **ASSUMED** : la position a **franchi la frontière 0/4095** pendant l'enregistrement (milieu décentré ou course traversant la frontière). `record_ranges_of_motion` a alors retenu les deux extrêmes.
  - C'est le même motif que celui qui a fait classer la calibration follower historique en TO_REVALIDATE (`shoulder_lift` et `elbow_flex` à `[0, 4095]`).
  - Conséquence possible, **non vérifiée** : en téléopération, une valeur leader qui saute de ≈ 4095 à ≈ 0 au passage de la frontière se traduirait par un **saut de consigne** côté follower.
- **Statut proposé** : `LEADER_CALIBRATION` = **procédure PASS**, **plages TO_REVALIDATE** pour les IDs 2, 3 et 4, à trancher par HQ avant toute téléopération. Le fichier reste en place, inchangé.

## Non vérifié

- Log console de la calibration réussie : opérateur, non transmis.
- Position réelle « milieu » utilisée.
- Comportement de la téléopération au passage de la frontière.

## Sauvegarde historique — 2026-10-06 21:22:45 CEST

| Élément | Valeur |
|---|---|
| Original (actif, **non modifié**) | `~/.cache/huggingface/lerobot/calibration/teleoperators/so_leader/pilot001_leader.json` |
| Copie (hors chemin actif, ignorée par Git) | `calibration/staging/pilot001_leader.2026-10-06T203745.json` |
| SHA-256, original et copie | `5fbbdb26af036610d9120e6be8063fb1aa0e63aaa13842bad6b5b6c553270f1a` |
| Identité octet à octet (`cmp`) | oui |
| Horodatage du fichier (préservé par `cp -p`) | 2026-10-06 20:37:45 |

La copie est conservée comme preuve historique. Elle n'est enregistrée sous aucun id LeRobot actif.

## Seconde calibration du leader détectée — 2026-10-06 22:03:41 (non signalée à l'agent)

Lors de la revue du lanceur de téléopération, le fichier actif `pilot001_leader.json` a été trouvé **réécrit**, soit **une seconde calibration** effectuée hors de la session de l'agent :

| Élément | Valeur |
|---|---|
| Fichier actif | `~/.cache/huggingface/lerobot/calibration/teleoperators/so_leader/pilot001_leader.json` |
| Modifié | 2026-10-06 22:03:41 |
| SHA-256 | `974f819f98567cb7c88fb746d389a9424f88a6fc531fb0587343e5285e4c0dae` |
| Sauvegarde (ignorée par Git, octet à octet identique) | `calibration/staging/pilot001_leader.2026-10-06T220341.json` |
| Version précédente conservée | `calibration/staging/pilot001_leader.2026-10-06T203745.json` (`5fbbdb26…`) |

| Moteur | 22:03 homing / min / max | 20:37 homing / min / max |
|---|---|---|
| shoulder_pan | −1912 / 696 / 3322 | −2000 / 781 / 3512 |
| shoulder_lift | 1065 / **0 / 4089** | 1063 / 1 / 4095 |
| elbow_flex | −1335 / **0 / 4095** | −1431 / 0 / 4095 |
| wrist_flex | 1681 / **3 / 4088** | −349 / 0 / 4095 |
| wrist_roll | 1900 / 0 / 4095 | 1928 / 0 / 4095 |
| gripper | −1860 / 2024 / 3367 | −1828 / 2010 / 3251 |

- Le motif des **plages complètes persiste** sur `shoulder_lift`, `elbow_flex` et `wrist_flex` : TO_REVALIDATE ; franchissement non testé.
- Écart des milieux entre bras, ASSUMED : `wrist_flex` leader milieu 2045,5 contre follower 1252,5, soit ≈ 70° de décalage, à mesurer en pose concordante.
- Concordance registres ↔ fichier non revérifiée depuis 22:03 (la sonde de 20:57 portait sur l'ancienne version).
