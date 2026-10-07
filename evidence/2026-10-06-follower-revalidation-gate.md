# Porte d'inspection humaine — FOLLOWER — avant toute mise sous tension

> **FOLLOWER_POWER_AUTHORIZED = NO.** Ne pas alimenter le follower, ne pas ouvrir son port série, ne lancer ni connect, ni calibrate, ni teleop tant que cette porte n'est pas remplie et revue par HQ.

## Référence historique (à comparer, pas à présumer)

| Élément | Historique | Source |
|---|---|---|
| Servos | 6 × **ST-3215-C047** (30 kg·cm, gamme **12 V**) | `lab-hardware/sessions/2026-07-26-session-015-so101-servo-id-follower.md` |
| Alimentation | bloc **12 V** (étiqueté « A ») | idem |
| IDs | 1 à 6, attribués un par un | idem |
| Calibration | `~/.cache/huggingface/lerobot/calibration/robots/so_follower/follower_nevil.json`, SHA-256 `f48d50d5ba8c220f13575f13c1d6562d9431391fb1e726541abdaf2c4e714a9d` (inchangé au 2026-10-06), TO_REVALIDATE | `calibration/README.md` |
| Documentation de ce dépôt | follower Standard 6 × C001 sur 5 V | **contradiction ouverte** (ENYO-14) |

## À relever par l'opérateur, follower **hors tension**

| # | Contrôle | Relevé (à remplir) | Conforme à l'historique ? |
|---|---|---|---|
| 1 | Marquage lu sur **au moins un** servo du follower (photo si possible) : `C047` ? `C001` ? autre ? | | |
| 2 | Étiquette **OUTPUT** du bloc d'alimentation destiné au follower (tension et courant) | | |
| 3 | Les **6** câbles servo sont branchés : base → 1 → … → 6, et carte → premier servo | | |
| 4 | Aucun câble abîmé, pincé, tendu ; mou visible à chaque articulation, en particulier base → servo 2 | | |
| 5 | Bras mécaniquement libre (pas de point dur à la main) ; coupure d'alimentation à portée ; arrêt immédiat possible | | |
| 6 | Le bloc 12 V éventuel est **physiquement séparé** du leader et ne peut pas être branché sur la carte leader par erreur | | |

## Règles de décision

- **C047 et bloc 12 V** : concorde avec l'historique. HQ corrige la documentation du dépôt (follower = Pro / 12 V), puis décide de la suite.
- **C001 et bloc 5 V** : concorde avec la documentation du dépôt, mais **pas** avec l'historique. La calibration `follower_nevil.json` ne provient alors peut-être **pas** de ce bras : décision HQ requise.
- **Marquage et tension incohérents** (ex. C047 sur 5 V, ou C001 avec un bloc 12 V) : **STOP**. Ne rien alimenter. C'est une ambiguïté au sens de la règle 9 d'AGENTS.md.
- Contrôle 3, 4 ou 5 non conforme : **STOP**.

## Après la porte (non autorisé aujourd'hui)

Premier contact bus follower = même sonde en **lecture seule** que pour le leader, dans une **v2** qui refuse d'écraser un fichier existant et vérifie le numéro de série du port (follower : `5B7B015207`). Attendus : `Present_Voltage` cohérent avec le bloc relevé ; jamais de `connect()` normal, qui réactive le couple du follower.
