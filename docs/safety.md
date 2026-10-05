# Securite

A lire **avant** la premiere mise sous tension, et avant chaque session ou le
robot peut bouger. Ce document ne contient pas de procedure de teleoperation :
la teleoperation est bloquee (`scripts/teleop.sh`).

## 1. Risques connus

Le SO-101 est un bras de table a 6 servos. Ce document ne garantit aucune
gravite maximale de blessure et aucun ordre de rupture des pieces : ni l'un ni
l'autre n'a ete mesure dans ce projet. Risques identifies :

- **pincement** d'un doigt dans la pince ou dans une articulation ;
- **collision** : le bras peut balayer la table, heurter une personne ou
  projeter ce qui s'y trouve ;
- **blocage et surchauffe servo** : un servo qui force contre une butee ou
  contre la table chauffe ;
- **casse mecanique** : une piece imprimee, un servo ou les deux peuvent ceder
  sous un forcage prolonge.

Un risque identifie est le **geste reflexe** : rattraper un bras qui part, et se
faire pincer en le faisant. Couper l'alimentation, ne pas retenir le bras.

## 2. Avant de mettre sous tension

1. **Zone degagee** — rayon d'un bras tendu, libre d'objets, de cables, de
   tasses et de mains.
2. **Base fixee** — serre-joint ou fixation. Un bras non fixe se deplace en
   bougeant et finit par tomber de la table.
3. **Coupure a portee de main** — l'interrupteur de la multiprise ou le barillet
   DC, atteignable **sans se pencher au-dessus du bras**. C'est le point le plus
   souvent neglige : une coupure placee derriere le robot est une coupure
   inutilisable.
4. **Polarite verifiee** — voir `hardware.md` §2. Le barillet 5.5 x 2.1 mm doit
   etre centre positif.
5. **Cameras et cables ranges** — un cable dans la course du bras sera tendu
   puis arrache.
6. **Tension du bloc lue sur l'etiquette** — 5 V pour un bras Standard, jamais
   12 V. Voir `hardware.md` §2.
7. **Hote Mac pret** — sur secteur, mise en veille et mises a jour
   automatiques suspendues pour la session, hub et cables USB fixes. Le Mac
   pilote directement les bras (Pilote #001). Ne pas supposer qu'une veille ou
   une perte USB arrete le bras : en cas de doute, couper l'alimentation du
   bras.

## 3. Pendant

- **Une main sur la coupure** au premier mouvement d'une session.
- **Ne jamais retenir le bras a la main** pour l'empecher d'aller quelque part.
  Couper l'alimentation. Un servo en butee pousse en continu.
- **Un bras qui vibre, chauffe ou siffle** : couper. Un servo chaud est un
  servo qui force contre quelque chose.
- **Mouvement inattendu** = coupure immediate, diagnostic ensuite. Pas l'inverse.
- Personne d'autre dans la zone, en particulier pas d'enfant et pas d'animal.

## 4. Les deux dangers specifiques a ce projet

### 4.1 Une calibration fausse est plus dangereuse qu'une calibration absente

Sans calibration, LeRobot refuse de piloter. Avec une calibration **fausse**, il
pilote avec assurance vers des positions qui n'existent pas mecaniquement, et le
bras force en butee jusqu'a ce que quelque chose cede.

C'est l'etat actuel du dossier : la calibration follower conservee porte une
course `[0, 4095]` sur `shoulder_lift` et `elbow_flex`, ce qui n'est pas une
course attendue de bras assemble. `wrist_roll` a `[0, 4095]` est attendu (LeRobot
fixe cette plage), mais cela signifie **aucune borne logicielle** sur cet axe :
surveiller cables et butees au premier mouvement. Le fichier entier est
**TO_REVALIDATE**. Voir `../calibration/README.md`.

### 4.2 Le premier mouvement apres une calibration

Toujours : amplitude reduite, vitesse reduite, main sur la coupure, une
articulation a la fois. La calibration n'est consideree bonne qu'apres ce test,
pas a la fin du script de calibration.

## 5. Regle d'autorisation

> **Aucun mouvement moteur sans autorisation humaine explicite, donnee pour
> cette session et pour cette action.**
>
> Une autorisation donnee hier ne vaut pas pour aujourd'hui. Une autorisation
> pour "tester le servo 1" ne vaut pas pour "lancer la teleoperation".
> Un agent ne s'auto-autorise jamais. Voir `../AGENTS.md`, regle 3.

## 6. En cas de probleme

Voir `recovery.md`. L'ordre y est toujours le meme : **couper d'abord,
comprendre ensuite.**
