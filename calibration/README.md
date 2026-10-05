# calibration/

Statut : **aucun fichier de calibration n'est versionne dans ce depot.**

## Ce qu'est un fichier de calibration LeRobot

LeRobot ecrit un JSON par bras. Pour chacun des 6 moteurs il conserve :

| champ | role |
|---|---|
| `id` | identifiant du servo sur le bus (1..6) |
| `homing_offset` | decalage entre le zero electrique du servo et le zero mecanique du bras |
| `range_min` / `range_max` | bornes de course observees pendant la calibration |
| `drive_mode` | sens de rotation |

Sans ce fichier, LeRobot ne sait pas ou se trouve le bras. Avec un fichier
**faux**, il croit le savoir : il commande des positions hors de la course reelle
et force contre les butees. C'est le mode de panne le plus couteux de ce projet.

## Emplacement

Ces fichiers ne vivent pas dans le depot, mais dans le cache utilisateur :

```
~/.cache/huggingface/lerobot/calibration/robots/so_follower/<nom>.json     # follower
~/.cache/huggingface/lerobot/calibration/teleoperators/so_leader/<nom>.json # leader
```

Le `<nom>` est celui passe a `--robot.id` / `--teleop.id`. Les repertoires
`so_follower` / `so_leader` sont les noms internes LeRobot et **ne changent pas** ;
les **types** a passer en CLI sont `--robot.type=so101_follower` et
`--teleop.type=so101_leader` (identiques en LeRobot 0.5.1 et 0.6.1).

Les ids du Pilote #001 sont fixes par HQ et vivent dans le `config/robot.yaml`
local (non versionne). Fichiers attendus : `robots/so_follower/<id follower>.json`
et `teleoperators/so_leader/<id leader>.json`. Aucun des deux n'existe encore.
L'artefact existant `follower_nevil.json` n'est **pas** la calibration du Pilote
#001 ; produire celle-ci (nouvelle calibration ou copie approuvee) est une
decision humaine / HQ (AGENTS.md regle 4).

Ce cache est **local a l'hote qui execute LeRobot**. Hote de bring-up (decision
HQ) : **Mac ENYOLAB** ; hote de deploiement : **Mac de Boris**, ou les
calibrations utilisees devront exister. Une calibration est liee au **bras
physique** (et a la version LeRobot qui l'a produite), pas a l'hote. Qui la
produit et en presence de qui : **UNKNOWN — a decider par HQ**. Le transfert
d'une calibration du **meme** bras vers un autre hote est **autorise par HQ
(2026-10-05)**, original conserve, empreinte verifiee — voir la copie stagee
ci-dessous.

## Etat constate — audit ENYO-14, 2026-10-05

### Follower

Un artefact de calibration follower **existe** et a ete conserve :
6 moteurs renseignes, ecrit le **2026-09-11**.

> **Sa validite physique est TO_REVALIDATE.**
> Trois axes y portent une course `[0, 4095]`, soit la plage entiere du codeur
> 12 bits (axes releves dans l'audit ENYO-14, table moteur du fichier
> `follower_nevil.json`, sha256
> `f48d50d5ba8c220f13575f13c1d6562d9431391fb1e726541abdaf2c4e714a9d`). Ils ne sont pas tous dans le meme
> cas :
>
> | Axe | Course `[0, 4095]` | Statut |
> |---|---|---|
> | `wrist_roll` | **attendue** — lors d'une nouvelle calibration, la methode `calibrate()` de LeRobot fixe `wrist_roll` a `0–4095` (moteur a tour complet) et n'enregistre pas sa course | EXPECTED (plage seule) |
> | `shoulder_lift` | enregistree comme course de mouvement | **TO_REVALIDATE** |
> | `elbow_flex` | enregistree comme course de mouvement | **TO_REVALIDATE** |
>
> Source du comportement `wrist_roll` : methode `calibrate()`
> (`full_turn_motor = "wrist_roll"`, `range_maxes[...] = 4095`) — paquet 0.5.1 installe, `robots/so_follower/so_follower.py` l.131-139 ;
> tag GitHub `v0.6.1` (commit `7e241bd6`), meme fichier l.135-143.
>
> **EXPECTED ne veut pas dire sur.** Cela signifie que LeRobot n'impose **aucune
> borne logicielle** a `wrist_roll` : au premier mouvement, surveiller cables et
> butees de cet axe. EXPECTED porte sur la plage seule ; le `homing_offset` de
> `wrist_roll` et le fichier entier restent **TO_REVALIDATE**.
>
> Pour `shoulder_lift` et `elbow_flex`, une course mecanique reelle de bras est
> plus etroite. Trois lectures restent possibles et aucune n'est tranchee :
> 1. la calibration a ete faite bras non assemble ou sans butees ;
> 2. elle a ete interrompue avant d'avoir borne ces axes ;
> 3. ces axes tournent reellement librement sur ce montage.
>
> Il faut **recalibrer sur le robot assemble** avant tout mouvement, et comparer
> les deux fichiers. Ne pas reutiliser celui de 2026-09-11 comme reference.
> *(Precise par la decision HQ du 2026-10-05 : sa reprise pour le meme bras est
> autorisee, mais la copie reste TO_REVALIDATE — elle ne devient pas une
> reference.)*

### Follower — copie stagee pour le Pilote #001 (decision HQ, 2026-10-05)

HQ autorise la reprise de l'artefact historique pour le **meme bras follower
physique** (transfert d'hote du meme bras autorise ; original conserve). La copie
est **stagee seulement** : elle n'est **pas** placee dans le cache LeRobot actif.

| Element | Valeur |
|---|---|
| Source (cache LeRobot, inchangee) | `~/.cache/huggingface/lerobot/calibration/robots/so_follower/follower_nevil.json` |
| SHA256 source | `f48d50d5ba8c220f13575f13c1d6562d9431391fb1e726541abdaf2c4e714a9d` |
| Copie stagee (ignoree par Git) | `calibration/staging/pilot001_follower.from_follower_nevil.json` |
| SHA256 copie | `f48d50d5ba8c220f13575f13c1d6562d9431391fb1e726541abdaf2c4e714a9d` |
| Identite octet a octet (`cmp`) | **OUI** |
| Chemin actif `robots/so_follower/pilot001_follower.json` | **absent** — non active |

`FOLLOWER_CALIBRATION_STATUS = TO_REVALIDATE` : la copie herite de toutes les
reserves ci-dessus (`shoulder_lift` / `elbow_flex` a `[0, 4095]`, version LeRobot
d'origine inconnue). L'activation sous l'id du pilote est une etape distincte,
soumise a decision HQ.

> ⚠️ **Le staging n'est pas une barriere sur le Mac ENYOLAB.** Le meme fichier
> reste actif dans le cache sous l'id `follower_nevil` : une commande LeRobot
> lancee avec `--robot.id=follower_nevil` le chargerait sans invite si les moteurs
> correspondent. Ne pas utiliser cet id. Le retirer du cache actif est une
> decision HQ (question ouverte), pas une action d'agent.

### Leader

**NOT_FOUND.** Aucun fichier de calibration leader n'a ete trouve lors de
l'audit ENYO-14 — ni dans le cache LeRobot, ni ailleurs sur la machine.

Il doit etre **retrouve ou recree avant toute teleoperation.** C'est l'une des
raisons pour lesquelles `scripts/teleop.sh` est bloque.

## Regles

1. **Aucun fichier de calibration machine-specific n'est commite sans revue HQ.**
   `.gitignore` ignore `calibration/*.json` : c'est volontaire, ne pas le lever.
2. Une calibration appartient a **un** bras physique. La copier d'un bras vers un
   autre produit un fichier qui a l'air valide et ne l'est pas. Le transfert
   d'une calibration du **meme** bras vers un autre hote est autorise par HQ
   (2026-10-05), a condition de conserver l'original et de verifier le SHA256.
3. Avant d'ecraser une calibration existante, la **sauvegarder horodatee**. Une
   calibration perdue se repaye en temps de banc.
4. Une calibration n'est reputee bonne qu'apres verification sur le robot :
   course observee coherente avec la course mecanique, aucun forcage en butee.
   Tant que cette verification n'est pas faite, l'etat est TO_REVALIDATE.
