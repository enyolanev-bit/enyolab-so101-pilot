# Architecture

> **Pilote #001 Boris = Mac direct.** Les bras et les cameras se branchent en
> USB sur le Mac de Boris, qui execute LeRobot. Aucun Pi, aucune Jetson dans le
> chemin d'execution du pilote.
>
> `RASPBERRY_PI_ARCHITECTURE = TO_BE_VALIDATED` — le Pi 4 est un **candidat de
> productisation future**, pas l'architecture du pilote.
>
> Aucune ligne de ce document ne decrit un systeme en fonctionnement : la
> teleoperation est `BLOCKED` (`../scripts/teleop.sh`).

## 1. Architecture du Pilote #001 — Mac direct (decision HQ)

```
Leader USB ─────┐
Follower USB ───┼── Mac de Boris ── LeRobot
Camera poignet ─┤
Camera dessus ──┘
```

- 4 peripheriques USB sur le Mac : 2 adaptateurs bus servo + 2 cameras.
- 2 alimentations 5 V / 4 A dediees, une par bras, independantes du Mac.
- **Pourquoi le Mac** : c'est la topologie qui reduit le nombre de
  dependances — une seule machine, pas de reseau, pas de SSH, pas de seconde
  installation LeRobot a maintenir pour la teleoperation. Les pannes propres a
  l'hote restent ouvertes, voir le tableau ci-dessous.
- **La Jetson reste une infrastructure ENYOLAB.** Elle n'est pas pretee a
  Boris et n'est pas dans le chemin d'execution du pilote.

Statut : **PLANNED**. Rien de cette chaine n'a ete branche ni execute chez Boris.

Points non valides pour le Mac direct :

| Point | Statut |
|---|---|
| Ports USB disponibles sur le Mac de Boris, besoin d'un hub | UNKNOWN |
| Debit USB pour 2 cameras + 2 bus servo simultanes | NON MESURE |
| Version LeRobot sur le Mac de Boris | UNKNOWN — voir `../setup/mac.md` |
| Calibrations presentes sur le Mac de Boris | UNKNOWN — voir `../calibration/README.md` |
| Pannes propres a l'hote : veille, mise a jour OS, cable ou hub debranche | a couvrir par la checklist `safety.md` §2 |
| Hote d'entrainement du Pilote #001 | UNKNOWN — non decide |

## 1 bis. Architecture de productisation future — candidate Raspberry Pi 4

`RASPBERRY_PI_ARCHITECTURE = TO_BE_VALIDATED` · `PI4_READY_STATE = UNKNOWN`

```
SO-101 + cameras
      │
      ▼
Raspberry Pi 4
      │ SSH / reseau
      ▼
Mac de Boris
```

Aucun fonctionnement sur Pi n'a ete demontre dans ce projet. Ce schema est une
piste pour une version produit ulterieure ; il ne conditionne pas le Pilote #001.
Les sections 2 et 3 ne concernent que cette piste.

## 2. Piste Pi — ce qu'elle apporterait, et ce qu'elle n'est pas

| Rend | Ne rend pas |
|---|---|
| Machine dediee, qui ne sert qu'au robot | Machine d'entrainement |
| Toujours branchee, toujours au meme endroit | Remplacement de GPU |
| Accessible a distance en SSH | Garantie de debit USB |
| Sans dependance au portable de l'operateur | Etat valide — voir le bandeau |

L'**entrainement** d'une politique ne se fait pas sur le Pi. Le Pi fait de la
teleoperation et de l'enregistrement ; l'entrainement se fait sur une machine
avec un GPU et le checkpoint revient vers le Pi pour l'inference.

## 3. Piste Pi — points non valides, a mesurer avant de s'engager

| # | Point | Statut |
|---|---|---|
| 1 | LeRobot installable et fonctionnel sur Pi OS **arm64** | UNKNOWN — aucune version de LeRobot n'a tourne sur Pi dans ce projet |
| 2 | Debit USB suffisant pour **2 cameras + 2 bus servo** simultanes | NON MESURE — le facteur limitant probable |
| 3 | Frequence de boucle de teleoperation tenable | NON MESURE |
| 4 | Budget d'alimentation du Pi sous 4 peripheriques USB | NON MESURE |
| 5 | Comportement thermique en session longue | NON MESURE |
| 6 | Etat du Pi 4 physiquement disponible | UNKNOWN |

Le point **2** est celui qui decide. Deux flux video UVC non compresses sur un
controleur USB partage saturent avant la resolution visee. Si ce point tombe, il
y a trois sorties : compression MJPEG, resolution reduite, ou repartition sur
deux controleurs — et c'est un choix a faire avec une mesure en main, pas avant.

## 4. Version LeRobot

`LEROBOT_VERSION_STATUS = UNDETERMINED`

| Cible | Version | Preuve |
|---|---|---|
| Mac ENYOLAB (audit ENYO-14) | 0.5.1 | PROVEN — presente et importable |
| **Mac de Boris** (cible Pilote #001) | — | UNKNOWN — non installe, non releve |
| Jetson | 0.6.1 | ASSUMED — non verifie, machine hors ligne |
| Raspberry Pi | — | UNKNOWN |

> Aucune version n'est retenue pour ce projet. La regle : la version LeRobot est
> **explicitement epinglee et validee sur la cible de deploiement reellement
> utilisee** pour une session. Pour le Pilote #001, cette cible est le **Mac de
> Boris** ; la Jetson et le Pi ne sont pas requis. Si une autre cible entre plus
> tard dans la chaine (rejeu, entrainement, Pi), elle doit etre alignee sur la
> version avec laquelle le dataset a ete enregistre. Voir `../setup/mac.md`.

## 5. La Jetson

La Jetson Orin Nano est la plateforme **historique et actuelle** d'ENYOLAB pour
les charges GPU. Elle reste en service pour ce qu'elle fait bien.

> **La Jetson n'est pas pretee a Boris et n'est pas dans le chemin
> d'execution du Pilote #001.**
>
> Raison : une plateforme dont la mise en route a demande une intervention de
> recuperation bas niveau n'est pas une plateforme qu'on livre. Le pilote doit
> pouvoir fonctionner sans elle. Si l'entrainement passe par la Jetson, c'est un
> detail d'infrastructure ENYOLAB, pas une dependance du livrable.

Voir `../setup/jetson.md`.

## 6. Flux de donnees vise

```
  teleoperation          enregistrement           entrainement         inference
  leader ──▶ follower ──▶ dataset (episodes) ──▶ politique ──▶ follower
     │                        │                      │              │
   BLOCKED                 BLOCKED               NOT_PROVEN     NOT_PROVEN
```

Les quatre etapes sont a l'arret. La premiere bloque les trois suivantes : il n'y
a pas de raccourci qui permette d'enregistrer avant de teleoperer, ni d'entrainer
avant d'enregistrer.

Etat detaille : `../README.md`.
