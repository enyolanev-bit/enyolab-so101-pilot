# Téléopération leader → follower officielle LeRobot — 2026-10-07 15:31–15:47 — OPÉRATIONNELLE (confirmée par l'opérateur)

GO opérateur : recalibration du follower, puis `lerobot-teleoperate`.

## Ce qui a été fait

1. **Sauvegarde** de l'ancienne calibration du follower : `calibration/staging/follower_nevil.2026-10-07T153128.before-recal.json` (sha256 `f48d50d5…`).
2. **Recalibration officielle** `lerobot-calibrate --robot.type=so101_follower --robot.id=follower_nevil` : pose milieu et courses faites par l'opérateur.
   - Nouveau `follower_nevil.json` : sha256 **`03b26c3328b557d69b5146d5f316b5f23b760dd13fe7341d7e0b3ebe6b6425c9`**.
   - Plages : pan 847–3427, lift 1–4091, elbow 1–4093, wrist_flex 2–4094, roll 0–4095, pince 1962–3534.
3. **Contrôle en lecture seule**, les deux bras posés au milieu (`evidence/boris/2026-10-07-pose-check-after-recal-153801.json`, 0 écriture) :
   - **wrist_flex : −0,13° d'écart** (environ 100° avant) ; elbow : 0,40° ;
   - pan 9°, lift 17,5°, roll 18,7° : écarts dus à la pose posée à la main.
4. **Garde contre la consigne périmée** : `Goal_Position := Present_Position` sur les 6 servos, couple coupé, relu ; puis `lerobot-teleoperate` lancé aussitôt (`evidence/2026-10-07-teleop_official.py`).
5. **Passage 1** : 60 s, `max_relative_target = 2°`, 15 Hz → le follower suit lentement (**confirmé par l'opérateur**). Coude bloqué avec 2° d'écart.
6. **Passage 2** : 90 s, `max_relative_target = 5°`, 30 Hz → **suit normalement (confirmé par l'opérateur)**.
   - Écart final < 1,3° sur toutes les articulations.
   - Amplitudes atteintes par le follower : pan −60 à 82°, lift 0 à 148°, elbow −163 à 8°, wrist_flex −1 à 171°.
7. Après chaque passage : couple du follower **relu à 0** ×6.

## Risque connu (à traiter)

- **Calibration du leader en course complète** (0–4095) sur lift, elbow et wrist_flex : ses lectures ont couvert **−179° à +180°**.
- Si le leader franchit ±180°, la consigne du follower saute de 360° ; `max_relative_target` limite le pas mais pas le sens. Aucun mouvement anormal n'a été vu au passage 2 (opérateur).
- **Correctif** : recalibrer le leader avec la même procédure (pose milieu identique à celle du follower) ; en attendant, éviter de replier le leader à fond.
- `boris/controller.py` épingle l'ancienne calibration (`f48d50d5…`) : il refusera de démarrer tant que `FOLLOWER_CALIBRATION_SHA256` n'est pas mis à jour (comportement voulu).

## Relancer

```
TELEOP_MAX_REL=5 TELEOP_FPS=30 .venv/bin/python evidence/2026-10-07-teleop_official.py 300
```

---

## Recalibration du leader et passage 3 — 15:50–15:58 — SUIVI FLUIDE (confirmé par l'opérateur)

- **Ancienne calibration du leader** sauvegardée : `calibration/staging/pilot001_leader.2026-10-07T155045.before-recal.json` (`974f819f…`).
- **`lerobot-calibrate` du leader**, même pose milieu que le follower → nouveau `pilot001_leader.json`, sha256 **`183455cd72f827f5084fed6127a2397bff45615f5897cda53276d97e663f5e41`**.
  - Plages : pan 700–3341 ; lift, elbow, wrist_flex et roll 0–4095 (course complète enregistrée, comme sur le follower) ; poignée 1916–3254.
- **Contrôle en lecture seule** (deux bras en L, 0 écriture, `evidence/boris/2026-10-07-pose-check-both-recal-155606.json`) :
  - lift 0,09°, elbow 0,57°, wrist_flex 0,83°, roll 4,4°, pan 10° (pose posée à la main) ;
  - pince 3 % contre 52 % : l'opérateur a été prévenu avant le lancement.
- **Passage 3** : 90 s, 5°/pas, 30 Hz.
  - **61 bridages** seulement (2128 au passage 2) : pince et rattrapage initial de la base ; aucun sur lift, elbow ou wrist ; **aucune lecture à ±180°**.
  - Couple **relu à 0** ×6. **Suivi fluide, confirmé par l'opérateur.**
- **Reste ouvert (ASSUMED)** : la course complète enregistrée sur lift, elbow et wrist des deux bras ; un bouclage reste théoriquement possible à ±180° de la pose milieu.
- **Journal** : `evidence/boris/2026-10-07-teleop-official-run3.log`.
