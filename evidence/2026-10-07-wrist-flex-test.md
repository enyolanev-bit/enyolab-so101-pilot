# `wrist_flex` ±2° — 2026-10-07 10:00 CEST — WRIST_FLEX_PROVEN = NO

- **GO** : HQ. Opérateur présent ; pinceau **visiblement dégagé** du papier, confirmé par l'opérateur avant le couple ; coupure 12 V à portée.
- Pas d'Astra, pas de `shoulder_lift`.

## Correction préalable du contrôleur

- L'avance de 6 pas codeur s'applique **uniquement à `shoulder_pan`** : `DEADBAND_LEAD_COUNTS = {"shoulder_pan": 6}`.
- Pour les autres articulations, la consigne ne dépasse jamais la cible.
- `controller.py` : sha256 `d71caba0bd8dbdd34a453ea65d444a2314315e4a63eff1787341d95893b81a73`.
- `sim_test.py` : **33/33**, sans régression (4 nouveaux contrôles `wrist_flex` : pas d'avance, consigne jamais au-delà de la cible, refus sous la marge de butée basse).

## Essai (session `20261007T100013`, pose de départ brute 2056 / 2021 / 2048 / **1370** / 938 / 2072)

- Démarrage : maintien de 4 s, dérive **0** sur les 6 servos.

| Mouvement | Demandé | Consignes envoyées → mesuré (brut) | Résultat |
|---|---|---|---|
| +2° | 10,330° → **12,330°** (cible brute 1393, +23 pas) | 1381 → 1379 (+9) ; 1390 → 1390 (+11) | **atteint** : **+20 pas = +1,758°**, erreur finale +0,264° (≤ 0,3°) |
| retour −2° | 12,088° → **10,330°** (cible brute 1370) | 1379 → **1390, 0 pas** ×3 | **ÉCHEC** : aucun progrès sur 3 itérations, **arrêt de sécurité** |

- **Dérive des autres articulations** : **0,0** (pan, lift, elbow, roll, pince) pendant les deux mouvements.
- **Écritures** : 5 écritures groupées de consigne, toutes dans la liste blanche.
- **Arrêt** : couple **relu à 0** ×6, port fermé.
- **Après coupure du couple** (lecture seule, 0 écriture) : `wrist_flex` brut **1391** (+12,18°). Le poignet n'est **pas revenu** à sa pose de départ (1370) : il est resté environ 2° plus haut.

## Lecture

- **WRIST_FLEX_PROVEN = NO.**
  - Sens + (brut croissant) : mouvement prouvé ; le servo atteint sa consigne et la dépasse même d'environ 2 pas.
  - Sens − : aucun mouvement avec une consigne à 11 pas (1°) devant.
- Asymétrie cohérente avec une charge par gravité qui aide le sens + et s'oppose au sens − (**ASSUMED** : sens physique non observé par l'agent).
- Mêmes symptômes que `elbow_flex` : avec 1° maximum entre consigne et pose, P = 16 et I = 0, le servo ne vainc pas une charge statique.
- **Options pour HQ** : avance ou pas plus grands pour cette articulation et ce sens, gain P, ou retour manuel couple coupé. Aucune nouvelle tentative de l'agent.
- **Visuel** : à confirmer par l'opérateur.

## Preuves (`evidence/boris/`)

| Fichier | sha256 |
|---|---|
| `2026-10-07-demo-move-20261007T100021502576.json` | `54c10265…e3bb` |
| `2026-10-07-session-20261007T100013231619-23095.jsonl` | `35b5bdc5…b676` |
| `2026-10-07-demo-check-20261007T095925222979.json` (avant) | `0b368a21…a584a3a` |
| `2026-10-07-demo-check-20261007T100030932778.json` (après) | `33f0d1d6…e3fc7a` |
| `2026-10-07-session-20261007T100030232272-23151.jsonl` (après) | `f42ffbfc…3442ffc04f782a1a3079ae645` |
