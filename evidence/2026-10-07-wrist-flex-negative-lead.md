# `wrist_flex` sens négatif avec avance de consigne — 2026-10-07 10:30 CEST — WRIST_FLEX_NEGATIVE_PROVEN = NO (essai non réalisé : erreur de bus au démarrage)

- **GO** : HQ, une seule tentative.
- Avant le couple, l'opérateur a confirmé : pinceau entièrement dégagé, présence, coupure 12 V à portée.
- Pas d'Astra, aucune autre articulation.

## Préparation

- **Avance calculée à partir des journaux** (écarts de consigne en sens négatif) :

  | Écart de consigne | Mouvement |
  |---|---|
  | −11 pas | 0 pas |
  | −13 pas | 0 pas |
  | −21 pas | −8 pas, puis blocage à 13 pas de la consigne |

  → avance négative minimale **13 pas codeur** ; avance positive 0. Écart de consigne maximal 22 pas (1,934°), enveloppe ±8°.
- **`controller.py`** (sha256 `92264cd6…`) : prise en charge d'une avance par sens, sous forme de tuple (positif, négatif). La table par défaut est inchangée (`{"shoulder_pan": 6}`).
  - `sim_test.py` : **57/57**. Avec un servo simulé à 13 pas d'erreur négative, les consignes sont 1361 → 1352 → 1347 ; la cible 1360 est atteinte et le retour aussi (1382).
- **Script** : `2026-10-07-wrist_flex_negative_lead_test.py` (sha256 `d66dc2b5…893e`). Les réglages ne s'appliquent qu'à ce processus.

## Déroulé (session `20261007T103035`)

- Lecture seule préalable : pose brute 2056 / 2021 / 2048 / **1383** / 938 / 2072, couple 0.
- Démarrage : contrôles OK, puis `configure()` (écritures dans la liste blanche). Recalage de la consigne sur la position présente :
  - servos 1 à 4 écrits ;
  - écriture de la consigne du **servo 5 (`wrist_roll`, valeur 938)** : **`ConnectionError … There is no status packet!`**.
- **Le couple n'a jamais été activé** : aucune écriture `Torque_Enable = 1` au journal. Faute → arrêt.
- **Arrêt** : `Torque_Enable = 0` écrit ×6, **relu à 0** ×6, port fermé. Le bus répondait de nouveau à l'arrêt.
- **Aucun mouvement commandé.**

## Résultats demandés

- **Avance utilisée** : 13 pas (sens négatif), prévue mais **non appliquée** (aucune consigne de mouvement envoyée).
- **Mouvement demandé** : −2,0° (cible 1360). **Mouvement mesuré** : aucun (essai non atteint).
- **Retour** : non applicable.
- **Dérive des autres articulations** : aucune mesure de mouvement ; couple jamais actif.
- **Couple** : **relu à 0** ×6.
- **WRIST_FLEX_NEGATIVE_PROVEN = NO** : tentative unique consommée par une erreur de bus avant le couple.

## Lecture

- Première erreur de bus en écriture depuis l'ajout des relances de lecture du 2026-10-06 : une absence d'accusé, isolée, sur le servo 5. Toutes les écritures précédentes de la session ont réussi, de même que l'arrêt.
- Cause **UNKNOWN** : câble ou connecteur du bus côté poignet, alimentation, parasite. **ASSUMED** : le câble du servo 5 a pu être sollicité pendant les manipulations du poignet.
- La règle d'abandon a fonctionné avant toute mise sous couple.
- **Décision HQ** : nouvelle tentative du même essai (inchangé), éventuellement après vérification du câblage du servo 5, ou une relance bornée à 1 sur les écritures du recalage.

## Preuves (`evidence/boris/`)

| Fichier | sha256 |
|---|---|
| `2026-10-07-wrist-flex-negative-lead-103035.json` | `4da24766…3370` |
| `2026-10-07-session-20261007T103035798774-40862.jsonl` | `1c9b59b1…1955` |

---

## Nouvelle tentative — 10:39 CEST — WRIST_FLEX_NEGATIVE_PROVEN = YES (dans cette pose)

- **GO** : opérateur, nouvelle tentative du même essai après vérification du câble du servo 5. Script et `controller.py` **inchangés** (`d66dc2b5…`, `92264cd6…`).
- **Contrôle du bus en lecture seule** (session `103831`, 0 écriture) : **0 échec sur 200 lectures groupées**, servo 5 répond 20/20 aux pings (modèle 777).
- **Pose changée pendant la vérification du câble** (brut) : 2034 / 2019 / **982** / **2276** / 936 / 2072. Le coude est à −94° et `wrist_flex` à +90°.
  - L'opérateur a choisi de lancer l'essai depuis cette pose, pinceau dégagé.
- **Démarrage** : recalage de la consigne sans erreur, couple activé, maintien de 4 s avec dérive **0**. Toutes les écritures sont dans la liste blanche.

| Mouvement | Demandé | Consignes envoyées → mesures (brut) | Mesuré | Erreur finale |
|---|---|---|---|---|
| −2° (2276 → 2253) | −2,0° (−23 pas) | 2254 → 2268 (−8) ; 2246 → 2260 (−8) ; 2240 → 2254 (−6) | **−22 pas = −1,934°** | −0,088° |
| retour (→ 2276) | +1,934° | 2276 → 2275 (+21) | **+21 pas = +1,846°** | +0,088° |

- **Avance négative 13 pas** utilisée. La consigne n'a jamais dépassé la cible de plus de 13 pas (2240 pour une cible de 2253). Pas de dépassement.
- **Retour réussi** : 2275, à 1 pas de 2276. Pas d'avance dans le sens positif ; la consigne ne dépasse pas la cible.
- **Dérive des autres articulations** : 0,0, sauf `elbow_flex` : **0,088° (1 pas codeur)** au maximum pendant le retour.
- **Arrêt** : couple **relu à 0** ×6, port fermé.

**Lecture**
- **Sens négatif PROVEN dans cette pose** : coude −94°, poignet +90°. L'erreur négative mesurée ici est d'environ 14 pas (écart de 22 → arrêt à 14 pas), proche des 13 pas de l'ancienne pose.
- **Non prouvé** dans la pose de dessin (`wrist_flex` ≈ 1383) : la charge de gravité y diffère (**ASSUMED**).
- Confirmation visuelle : à l'opérateur.

| Fichier | sha256 |
|---|---|
| `boris/2026-10-07-wrist-flex-negative-lead-103908.json` | `f89647d2…298e` |
| `boris/2026-10-07-session-20261007T103908284385-45583.jsonl` | `6fa686f0…9955` |
| `boris/2026-10-07-session-20261007T103831600990-45435.jsonl` (contrôle du bus) | `caf9037b…dbcc` |
