# Setup — macOS

Poste de développement et de téléopération manuelle.

## État

**Rien n'est installé par ce dépôt.** Aucun venv n'est créé, aucune dépendance n'est posée. Cette page documente ce qui est constaté et ce qui reste à décider.

## Version LeRobot — `LEROBOT_VERSION_STATUS = UNDETERMINED`

**Aucune version n'est retenue à ce stade, et ce n'est pas un oubli.**

Le choix doit résulter d'une comparaison entre trois cibles, pas d'une préférence :

| Cible | Version constatée | Statut |
|---|---|---|
| **Mac** | **0.5.1** (wheel) | PROVEN — relevé lors de l'audit ENYO-14 |
| **Jetson** | 0.6.1 *annoncé* | **ASSUMED** — non vérifié, machine hors ligne lors de l'audit |
| **Raspberry Pi 4** | — | **UNKNOWN** — aucune installation constatée |

Choisir une version avant d'avoir vérifié les trois reviendrait à épingler un chiffre sur une hypothèse. Un leader et un follower qui ne parlent pas la même version de la couche moteur, c'est une incompatibilité qu'on découvre le bras sous tension.

**Critère de sortie** : les trois lignes du tableau sont en PROVEN, et la version retenue est écrite ici avec la date et la raison du choix.

## Constaté sur le Mac lors d'ENYO-14

- Python 3.12
- gestionnaire de paquets `uv` (ni conda, ni poetry, ni pyenv)
- LeRobot 0.5.1 installé en wheel, dans un environnement **non rattaché au SO-101**
- support SO-101 présent sous les modules génériques `robots/so_follower` et `teleoperators/so_leader` — aucun chemin littéral « so101 »
- points d'entrée disponibles : `lerobot-find-port`, `lerobot-setup-motors`, `lerobot-calibrate`, `lerobot-teleoperate`, `lerobot-record`, `lerobot-train`

## Premier contact, sans risque

```bash
./scripts/check_system.sh
./scripts/find_ports.sh
./scripts/test_cameras.sh
```

Ces scripts sont en lecture seule. Ils n'ouvrent aucun port série.

## Points d'attention macOS

- Un câble USB-C de **charge** ne transporte pas les données. Si aucun port série n'apparaît après branchement de l'adaptateur, suspecter le câble avant la carte.
- macOS peut demander une autorisation d'accès à la caméra au premier usage. L'accorder depuis Réglages Système, pas depuis un script.
