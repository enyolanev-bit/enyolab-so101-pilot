# `wrist_flex` : essai de retour seul — 2026-10-07 10:06 CEST — WRIST_FLEX_REVERSE_PROVEN = NO

- **GO** : HQ, une seule tentative, puis STOP.
- Opérateur présent, pinceau dégagé, coupure 12 V à portée : confirmé par l'opérateur avant le couple.

## Conditions de l'essai

- `controller.py` **inchangé** (sha256 `d71caba0…1a73`). Pas d'avance de consigne sur `wrist_flex`, gain P inchangé (16).
- Script `2026-10-07-wrist_flex_reverse_test.py` (sha256 `d0d352f2…99c3`).
  - Pour ce seul processus, l'écart de consigne maximal passe à **22 pas codeur = 1,934°** (≤ 2,0°).
  - Seule articulation activée : `wrist_flex`.
- Contrôle hors ligne : la seule consigne générée est 1370, jamais au-delà de la cible.
- Démarrage : maintien de 4 s, dérive **0** sur les 6 servos.

## Résultats

| | Brut | Degrés |
|---|---|---|
| Départ | 1391 | 12,176 |
| Cible | 1370 | 10,330 |
| Final, couple actif | **1383** | 11,473 |
| Après coupure du couple (lecture seule) | 1383 | 11,473 |

**Consignes envoyées → mesures (brut)** :

| Itération | Consigne | Mesuré | Mouvement |
|---|---|---|---|
| 1 | 1370 | 1383 | **−8 pas** |
| 2 | 1370 | 1383 | 0 |
| 3 | 1370 | 1383 | 0 |
| 4 | 1370 | 1383 | 0 |

- **Mouvement mesuré** : **−8 pas codeur = −0,70°**, sur −1,85° demandés. Le sens est correct, sans dépassement.
- **Erreur finale** : **−1,143°** (13 pas codeur au-dessus de la cible).
- **Arrêt** : aucun progrès sur 3 itérations → arrêt de sécurité, comme prévu.
- **Dérive des autres articulations** : 0,0.
- **Écritures** : 4 écritures groupées de consigne (toutes à 1370), toutes dans la liste blanche.
- **Couple** : relu à 0 ×6, port fermé. La lecture seule après coupure confirme le couple à 0 et la position 1383.

## Lecture

- **WRIST_FLEX_REVERSE_PROVEN = NO.** Avec un écart de consigne de 1,93°, le servo bouge dans le sens − mais s'arrête environ 13 pas (1,1°) avant sa consigne.
- **Asymétrie** : dans le sens +, l'arrêt se fait à environ 0 à 2 pas de la consigne ; dans le sens −, environ 13 pas.
  - Cohérent avec une charge (gravité ou frottement) qui s'oppose au sens − (**ASSUMED**).
  - Avec P = 16 et I = 0, l'erreur statique dans ce sens dépasse 1°.
- **Position du poignet** : 1383 brut, à 13 pas de la pose d'origine 1370.
- **Visuel** : à confirmer par l'opérateur.

## Preuves (`evidence/boris/`)

| Fichier | sha256 |
|---|---|
| `2026-10-07-wrist-flex-reverse-100628.json` | `b58fcdd8…dc5` |
| `2026-10-07-session-20261007T100628427040-26763.jsonl` | `be3e50e2…978153` |
| `2026-10-07-demo-check-20261007T100641875705.json` (lecture seule après l'essai) | `c8a877ef…` |
