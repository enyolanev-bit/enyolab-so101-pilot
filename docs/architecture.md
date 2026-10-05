# Architecture

> `RASPBERRY_PI_ARCHITECTURE = TO_BE_VALIDATED`
> `PI4_READY_STATE = UNKNOWN`
>
> Le schema ci-dessous est l'architecture **cible candidate**. Elle n'a pas ete
> montee ni mesuree. Aucune ligne de ce document ne decrit un systeme en
> fonctionnement.

## 1. Architecture cible candidate

```
   ┌──────────────┐
   │ Bras LEADER  │──── USB ────┐
   │  6x STS3215  │             │
   └──────────────┘             │
          ▲                     │
          │ 5 V / 4 A           │
                                │
   ┌──────────────┐             │        ┌─────────────────────┐
   │ Bras FOLLOWER│──── USB ────┼───────▶│  RASPBERRY PI 4     │
   │  6x STS3215  │             │        │                     │
   └──────────────┘             │        │  LeRobot            │
          ▲                     │        │  teleop / record    │
          │ 5 V / 4 A           │        │  TO_BE_VALIDATED    │
                                │        └─────────┬───────────┘
   ┌──────────────┐             │                  │
   │ Camera       │──── USB ────┤                  │ reseau
   │ poignet      │             │                  │ SSH (candidat)
   │ U20CAM-1080P │             │                  ▼
   └──────────────┘             │        ┌─────────────────────┐
                                │        │  Poste operateur    │
   ┌──────────────┐             │        │  (Mac / portable)   │
   │ Camera       │──── USB ────┘        └─────────────────────┘
   │ dessus       │
   │ U20CAM-720P  │
   └──────────────┘
```

4 peripheriques USB sur le Pi : 2 adaptateurs bus servo + 2 cameras.
2 alimentations 5 V / 4 A dediees, une par bras — **separees** de l'alimentation
du Pi.

## 2. Pourquoi un Pi, et ce que ca n'est pas

| Rend | Ne rend pas |
|---|---|
| Machine dediee, qui ne sert qu'au robot | Machine d'entrainement |
| Toujours branchee, toujours au meme endroit | Remplacement de GPU |
| Accessible a distance en SSH | Garantie de debit USB |
| Sans dependance au portable de l'operateur | Etat valide — voir le bandeau |

L'**entrainement** d'une politique ne se fait pas sur le Pi. Le Pi fait de la
teleoperation et de l'enregistrement ; l'entrainement se fait sur une machine
avec un GPU et le checkpoint revient vers le Pi pour l'inference.

## 3. Points non valides — a mesurer avant de s'engager

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
| Mac | 0.5.1 | PROVEN — presente et importable |
| Jetson | 0.6.1 | ASSUMED — non verifie, machine hors ligne |
| Raspberry Pi | — | UNKNOWN |

> Aucune version n'est retenue pour ce projet. Les trois cibles doivent finir sur
> **la meme** : un dataset enregistre avec une version et rejoue avec une autre
> est une source de panne qui ne se voit pas tout de suite. Le choix se fait
> quand le Pi aura ete teste, pas avant. Voir `../setup/`.

## 5. La Jetson

La Jetson Orin Nano est la plateforme **historique et actuelle** d'ENYOLAB pour
les charges GPU. Elle reste en service pour ce qu'elle fait bien.

> **Boris ne dependra pas de la Jetson dans l'architecture cible.**
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
