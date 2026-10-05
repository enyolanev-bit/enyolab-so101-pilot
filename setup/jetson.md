# Setup — Jetson Orin Nano

**Statut : plateforme ENYOLAB historique et actuelle. Hors du périmètre de livraison Boris.**

## Position

La Jetson est la plateforme de calcul du laboratoire ENYOLAB. Elle a servi aux travaux de perception et d'inférence.

**Boris ne dépendra pas de la Jetson dans l'architecture cible.** Elle est documentée ici pour deux raisons seulement :

1. elle porte peut-être une installation LeRobot plus récente que celle du Mac, et ce point conditionne le choix de version (voir [`mac.md`](mac.md)) ;
2. elle a pu produire des artefacts historiques utiles.

## État constaté lors d'ENYO-14

- Jetson **hors ligne** au moment de l'audit.
- Une entrée `192.168.1.155` figure dans `known_hosts`, mais l'adresse était **absente de la table ARP** — la machine n'était pas sur le réseau.
- LeRobot **0.6.1** y est annoncé. **ASSUMED, non vérifié.**

## À faire, en lecture seule, quand la machine sera accessible

- relever la version exacte de LeRobot et, si installée depuis les sources, le commit ;
- relever la version de Python et l'environnement utilisé ;
- inventorier les fichiers de calibration présents ;
- inventorier les datasets éventuels.

Aucun lancement, aucun mouvement, aucune installation côté Jetson depuis ce dépôt.
