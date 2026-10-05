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
produit, en presence de qui, et si un transfert du meme bras vers le Mac de
Boris est admis : **UNKNOWN — a decider par HQ**.

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
   d'une calibration du **meme** bras vers un autre hote n'est pas regle :
   decision HQ requise, voir ci-dessus.
3. Avant d'ecraser une calibration existante, la **sauvegarder horodatee**. Une
   calibration perdue se repaye en temps de banc.
4. Une calibration n'est reputee bonne qu'apres verification sur le robot :
   course observee coherente avec la course mecanique, aucun forcage en butee.
   Tant que cette verification n'est pas faite, l'etat est TO_REVALIDATE.
