# Premier pont autonome reconnaissable — 2026-10-07 — FIRST_RECOGNIZABLE_BRIDGE = PROVEN (opérateur)

- Mode d'exécution : HQ « BORIS PILOT ». Pas d'appel à l'API Astra : planificateur hors ligne (`--offline-astra`).
- Le pinceau est remplacé par un marqueur. L'opérateur le place sur le papier avant chaque essai et confirme la présence, la zone dégagée et la coupure 12 V à portée.

## Jalons

| Heure | Essai | Résultat |
|---|---|---|
| 11:15 | `shoulder_pan` +3° en contact (écart de consigne 1°) | +10 pas, puis blocage par frottement. **FIRST_AUTONOMOUS_MARK = PROVEN** (trait d'environ 3 mm, confirmé par l'opérateur) |
| 11:16 | idem, contact allégé | +3 pas, blocage |
| 11:17 | écart de consigne de 2° (approuvé par l'opérateur) | +30 pas (+2,64° sur 3°), blocage à 0,35° de la cible |
| 11:22 | pont n° 1 | tablier tracé ; oscillation de ±5 pas au premier changement de sens (avance > erreur réelle) → arrêt |
| 11:25 | pont n° 2 (avance divisée par deux à chaque franchissement de la cible) | 55 mouvements, segments 1 à 8 sur 11, puis arrêt : blocage de `wrist_flex` à 0,62° (tolérance 0,6°) |
| 11:28 | **pont n° 3** (tolérance de contact 1,0°) | **DRAWN** : 78/78 points de passage, 11/11 segments, 83,5 s, 70 mouvements, 180 écritures groupées de consigne. **Pont reconnaissable, confirmé par l'opérateur** |

## Pont n° 3 (`logs/run-20261007T112835.json`, session `20261007T112841`)

- **Pose de départ** : pan 10,4°, lift −2,5°, elbow −93,7°, wrist_flex 87,2°, roll −97,7°.
- **Plan** : gabarit `golden_gate_bridge`, environ 27 × 12 mm (facteur d'ajustement 0,667), excursion pan 8,00° et wrist 3,24°.
- **Erreur maximale aux points de passage** : pan 0,376°, wrist 0,552°. 31 blocages par frottement acceptés à moins de 1,0°.
- **Dérive des autres articulations** : 1 pas codeur au plus (0,088°). Maintien de départ : dérive 0.
- **Écritures** : configuration et recalage prouvés ; couple à 1 une seule fois au point autorisé ; ensuite uniquement des écritures groupées de consigne (180). Arrêt : couple **relu à 0** ×6.
- **Logiciel** :
  - `controller.py` sha256 `de7f72d7…`, avec l'avance divisée par deux à chaque franchissement de la cible ;
  - `painter.py` `602676ac…` (mode contact : écart ≤ 22 pas ; avances pan 10/10, wrist +6/−13 ; tolérance 1,0°) ;
  - `run_boris.py` `64d8e7d3…`.
- **Tests hors ligne** : `sim_test.py` **69/69**.

## Preuves (`evidence/boris/`)

`run-20261007T112246.json`, `run-20261007T112532.json`, `run-20261007T112835.json`, ainsi que les journaux de session correspondants (`2026-10-07-session-20261007T1122…`, `…T1125…`, `…T1128…`). Les images avant et après restent dans `boris/frames/` (locales, ignorées par Git).
