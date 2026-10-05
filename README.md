# enyolab-so101-pilot

Couche de livraison et d'expérimentation du système **SO-101 leader / follower** pour le pilote **Boris × Astra Paint**.

Ce dépôt est volontairement **propre, indépendant et partageable**. Il ne remplace pas `lab-hardware`.

| Dépôt | Rôle |
|---|---|
| `lab-hardware` | historique, R&D, traces, preuves d'audit — **reste privé** |
| `enyolab-so101-pilot` | environnement de livraison du pilote — **destiné à être partagé** |

---

## État du système — au 2026-10-05

Cet état provient de l'audit lecture seule **ENYO-14**. Rien n'y est affirmé sans artefact.

### PROVEN

- Un **artefact de calibration follower** existe, contient les entrées de **6 moteurs**, et a été préservé hors machine.
- La source mécanique amont est identifiée et épinglée : `TheRobotStudio/SO-ARM100` @ `fda892cba81032c46c40976a48c9ceadbf40a9ca`.
- Le matériel du second bras est commandé et payé (voir ENYO-13).

### TO_REVALIDATE

- **Validité physique de la calibration follower sur le robot actuellement assemblé.**
  L'artefact existe ; rien ne démontre qu'il corresponde encore à l'état mécanique présent du bras.

### NOT_PROVEN

- calibration **leader** — aucun artefact retrouvé ;
- **téléopération physique** ;
- **dataset physique** enregistré ;
- **policy physique** ;
- **rollout physique**.

### UNKNOWN

- version de LeRobot à retenir — voir [`setup/mac.md`](setup/mac.md) ;
- architecture Raspberry Pi — voir [`docs/architecture.md`](docs/architecture.md) ;
- état physique réel du bras leader, dont la pièce `Trigger_SO101` est en cours de réimpression (ENYO-6).

> Aucune ligne de ce dépôt n'affirme que le leader est calibré, ni que la téléopération fonctionne.

---

## Expérience cible

### Disponible aujourd'hui — lecture seule, sans risque

```bash
git clone <url>
cd enyolab-so101-pilot
./scripts/check_system.sh     # OS, CPU, Python, LeRobot, périphériques USB
./scripts/find_ports.sh       # liste les ports série candidats, sans les ouvrir
./scripts/test_cameras.sh     # liste les caméras détectées, sans capture
```

Ces trois scripts n'ouvrent aucun port, n'envoient aucune commande et ne font bouger aucun moteur.

### Bloqué aujourd'hui — à débloquer après validation

```bash
./scripts/teleop.sh                      # BLOCKED
./scripts/record_demo.sh --task drawing  # BLOCKED
```

Ces deux scripts **se terminent immédiatement avec un code de sortie non nul**. C'est voulu : ils resteront bloqués tant que la téléopération et l'enregistrement n'auront pas été validés avec artefacts à l'appui.

---

## Tâches

`tasks/drawing.md`, `tasks/folding.md`, `tasks/freeform.md` décrivent **l'expérience visée**, pas des capacités démontrées. Aucune de ces tâches n'a été exécutée sur le robot physique.

---

## Avant toute mise sous tension

Lire [`docs/safety.md`](docs/safety.md). Sans exception.

---

## Contenu du dépôt

| Chemin | Contenu |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | architecture cible candidate, `RASPBERRY_PI_ARCHITECTURE = TO_BE_VALIDATED`, place de la Jetson |
| [`docs/hardware.md`](docs/hardware.md) | bras, servos, carte, alimentation, caméras, pièces imprimées — avec le niveau de preuve par ligne |
| [`docs/safety.md`](docs/safety.md) | à lire avant toute mise sous tension |
| [`docs/recovery.md`](docs/recovery.md) | que faire quand quelque chose ne va pas |
| [`setup/mac.md`](setup/mac.md) | `LEROBOT_VERSION_STATUS = UNDETERMINED` et le tableau des trois cibles |
| [`setup/raspberry-pi.md`](setup/raspberry-pi.md) | `PLANNED` — rien n'a été installé ni mesuré |
| [`setup/jetson.md`](setup/jetson.md) | plateforme historique ENYOLAB ; le pilote n'en dépendra pas |
| [`config/robot.example.yaml`](config/robot.example.yaml) | gabarit, valeurs `CHANGEME` |
| [`config/cameras.example.yaml`](config/cameras.example.yaml) | gabarit, valeurs `CHANGEME` |
| [`calibration/README.md`](calibration/README.md) | rôle des fichiers de calibration, état constaté, règles |
| [`tasks/`](tasks/README.md) | dessin / pliage / libre — expérience visée, **NOT_PROVEN** |
| `evidence/` | vide — destiné aux artefacts de preuve (logs, mesures, photos) |

Aucun fichier de calibration n'est versionné ici. `.gitignore` ignore `calibration/*.json` : c'est volontaire.

---

## Pour les agents

Tout agent travaillant dans ce dépôt lit d'abord [`AGENTS.md`](AGENTS.md).
