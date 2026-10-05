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
~/.cache/huggingface/lerobot/calibration/robots/<type>/<nom>.json        # follower
~/.cache/huggingface/lerobot/calibration/teleoperators/<type>/<nom>.json # leader
```

Le `<nom>` est celui passe a `--robot.id` / `--teleop.id`.

Ce cache est **local a l'hote qui execute LeRobot**. Pour le Pilote #001 (Mac
direct), les calibrations utilisees doivent donc exister sur le **Mac de
Boris**. Une calibration est liee au **bras physique** (et a la version LeRobot
qui l'a produite), pas a l'hote. Qui la produit, sur quelle machine, en
presence de qui, et si un transfert du meme bras vers le Mac de Boris est
admis : **UNKNOWN — a decider par HQ**.

## Etat constate — audit ENYO-14, 2026-10-05

### Follower

Un artefact de calibration follower **existe** et a ete conserve :
6 moteurs renseignes, ecrit le **2026-09-11**.

> **Sa validite physique est TO_REVALIDATE.**
> Trois axes y portent une course `[0, 4095]`, soit la plage entiere du codeur
> 12 bits. Une course mecanique reelle de bras est toujours plus etroite. Trois
> lectures restent possibles et aucune n'est tranchee :
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
