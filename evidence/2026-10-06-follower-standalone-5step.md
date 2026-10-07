# Mouvement autonome visible du follower — 5 pas de +1° sur `shoulder_pan`, sans leader — 2026-10-06 23:15:36 CEST — RÉSULTAT : PASS

- **GO** : HQ.
- **Script** : `2026-10-06-follower_standalone_5step.py`, sha256 `fbb802aca25f0fd83a2a12829a1af349f9699f457714b1d7d1b857eff12746a1`.
  - Dérivé du script à un pas qui a passé à 23:09 (`f2d5a935…`). Le diff ne touche que le bloc de mouvement, `SETTLE_S` (0,5 s), `N_STEPS = 5`, le docstring et l'affichage.
  - Démarrage, gardes, relances de lecture (`num_retry=2`) et arrêt sont **identiques**.
  - Essais à blanc OK.
- **Calibration** : `follower_nevil.json`, sha256 `f48d50d5…`.
- **Journaux** :
  - `2026-10-06T231536-follower-5step.events.json`, sha256 `6ce80f8a1e9c5f1a757810c84f91c9120eae06916b7a2cc5823605a33bc83656` ;
  - `2026-10-06T231536-follower-5step.steps.jsonl`, sha256 `15df95aa66ebd4a2ce43b9fd18673473adb8511fa081b941dbf7d95a3896a593`.

## Démarrage

- Pose initiale (brut) : 2092 / 2024 / 2047 / 101 / 951 / 2140. `shoulder_pan` est resté à 2092 depuis la fin de l'essai de 23:09.
- Recalage : écrit = relu, 0 mouvement sur les 6 servos.
- Activation du couple : 23:15:37.399.
- Maintien de 4 s : dérive max **0 pas** sur les 6 servos.

## Pas (consigne = dernière pose mesurée + 1,0°, une écriture groupée `Goal_Position` par pas, stabilisation 0,5 s)

| Pas | Consigne | Avant | Après | Δ (°) | Brut avant → après | Pas codeur | Dérive des autres articulations |
|---|---|---|---|---|---|---|---|
| 1 | 3,681° | 2,681° | 3,297° | +0,615 | 2092 → 2099 | **+7** | 0,0 |
| 2 | 4,297° | 3,297° | 3,824° | +0,527 | 2099 → 2105 | **+6** | 0,0 |
| 3 | 4,824° | 3,824° | 4,352° | +0,527 | 2105 → 2111 | **+6** | 0,0 |
| 4 | 5,352° | 4,352° | 4,879° | +0,527 | 2111 → 2117 | **+6** | 0,0 |
| 5 | 5,879° | 4,879° | 5,407° | +0,527 | 2117 → 2123 | **+6** | 0,0 |

- **Total mesuré** : **+2,725°**, soit **+31 pas codeur** (2092 → 2123), pour ≈ +5° visés.
- **Dérive des autres articulations** (lift, elbow, wrist_flex, wrist_roll, pince) : **0,0**, à chaque pas et au total.
- Écritures : 5 écritures groupées `Goal_Position` dans la boucle ; toutes les écritures sont dans la liste blanche.

## Arrêt

40=0 ×6 ; couple **relu à 0** ×6 ; port fermé.

## Lecture

- **PROVEN** : 5 mouvements autonomes successifs, monotones, dans le bon sens, sur une seule articulation, sans dérive des autres.
- **Sous-atteinte systématique** : environ 0,53° par pas pour 1,0° demandé ; le servo s'arrête environ 5 pas codeur avant la consigne, à chaque pas.
  - Comme chaque consigne part de la **pose mesurée**, l'erreur ne se rattrape pas d'un pas à l'autre, d'où un total d'environ 2,7° au lieu de 5°.
  - Cause probable (**ASSUMED**) : zone morte ou erreur statique du servo avec P = 16, sans terme I (`I_Coefficient = 0`), sur `shoulder_pan` du bras C047 / 12 V.
  - À caractériser avant des consignes fines (par exemple : réponse sur une consigne absolue plus grande, ou avec un gain différent, sur GO).
- **Visibilité** : environ 2,7° de rotation de la base. La confirmation visuelle revient à l'opérateur (non observable par l'agent).

**RESULT = PASS.**
