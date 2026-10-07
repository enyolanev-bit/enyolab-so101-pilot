# Bridge painter MVP : préparation, sans exécution — 2026-10-07 10:24 CEST

- **GO** : HQ.
- **Aucune exécution matérielle** : seule une lecture de pose a eu lieu (session sans écriture, couple 0). Pas d'Astra.

## Script et contrôles

- **Script** : `boris/bridge_painter.py`, sha256 `07aeefe42753a2256e09fb27602ab0cc66c96880c04fc287e520c1be7a7b7a1a`.
- **Commandes** :
  - `--dry-run` : plan, après une lecture seule de la pose ;
  - `--dry-run --offline` : plan à partir de la dernière pose connue, sans accès au bras ;
  - `--go` : **désactivé** (`GO_ENABLED = False`) tant que `wrist_flex` n'est pas prouvé dans les deux sens.
- **Interface Astra** : JSON strict `{"task": "draw", "template": "golden_gate_bridge", "scale": x}`.
  - Clés exactes ; NaN refusé ; échelle entre 0,5 et 1,25.
  - Astra n'atteint ni les articulations ni les registres.
- **`sim_test.py`** : **54/54**, dont 7 contrôles du peintre de pont.

## Plan (pose de départ lue en lecture seule : pan −0,484°, wrist_flex 11,473°)

- **Gains** issus de la FK LeRobot officielle : **6,036 mm par degré de `shoulder_pan`** (axe u, horizontal) et **2,779 mm par degré de `wrist_flex`** (axe v, vertical ; v vers le haut = `wrist_flex` négatif).
  - Ces deux déplacements sont perpendiculaires à l'axe de l'outil. Le plan **suppose une feuille face au pinceau**.
- **Gabarit** : un seul tracé continu de 11 traits (le pinceau ne se lève jamais).
  - Traits : tablier ; câble latéral droit ; tour droite (descente, puis remontée en repassant) ; câble porteur en chaînette (4 points) ; tour gauche (descente, puis remontée en repassant) ; câble latéral gauche.
  - Taille : **40 × 18 mm** à l'échelle 1,0.
- **103 points de passage**, au plus 0,5° par articulation entre deux points. Chaque point est exécuté par mouvements d'une seule articulation (pan, puis poignet) : les diagonales deviennent de fins escaliers.
- **Excursion maximale** : pan **6,63°**, wrist_flex **4,86°** (borne du script 8°, plafond du contrôleur 10°).
- **Parcours** : pan 13,3°, wrist_flex **42,1°** (les tours sont repassées).
  - Pour cette seule session de dessin, le budget de parcours du contrôleur est porté à ceil(1,25 × max) + 1 = **54°**, plafonné à 60° : **à revoir par HQ**.
- **Traits qui exigent `wrist_flex` négatif** (sens non prouvé) : **2, 4, 7, 8, 10**.

## Preuves

| Fichier | sha256 |
|---|---|
| `evidence/2026-10-07-bridge-dry-run.txt` | `c4401757…5cd` |
| `evidence/boris/2026-10-07-bridge-plan-20261007T102346031971.json` | `0fabc5c1…` |
