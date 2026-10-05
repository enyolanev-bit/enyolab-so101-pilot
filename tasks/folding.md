# Tache — Pliage

**Etat : NOT_PROVEN.** Documentation d'experience. Rien ici n'a ete execute.

## Intention

Le follower plie un petit carre de tissu — lingette, mouchoir, chiffon — en
deux, puis eventuellement en quatre.

## Pourquoi c'est nettement plus dur que le dessin

Le tissu est **deformable**. Cette seule propriete casse plusieurs hypotheses
commodes :

- **L'etat initial n'est jamais le meme.** Un feutre repose a la meme place a
  chaque episode ; un tissu non. La politique doit generaliser sur une
  configuration de depart qui varie a chaque fois.
- **L'etat n'est pas entierement visible.** Un pli cache une partie du tissu.
  Deux configurations physiquement differentes peuvent donner la meme image.
- **Le contact est l'essentiel de la tache.** Saisir, glisser, lisser : ce sont
  des gestes ou la force compte autant que la position. Un bras a 6 servos sans
  retour d'effort n'a qu'une information indirecte sur ce qu'il touche.
- **Le succes est graduel.** Un pli "presque bon" existe, alors qu'un carre
  "presque dessine" se voit tout de suite.

Consequence pratique : **le nombre de demonstrations necessaires est d'un autre
ordre de grandeur** que pour le dessin. Ne pas planifier cette tache comme une
variante de la precedente.

## Montage

| Element | Note |
|---|---|
| Tissu | petit, leger, uni ; un motif aide la camera mais complique la lecture |
| Surface | contrastee avec le tissu, mate, non glissante |
| Position de depart | a plat, orientation libre — c'est le point de la tache |
| Camera poignet | voit la pince et le bord saisi |
| Camera dessus | voit le carre entier et l'etat du pli |

## Criteres de succes, a figer AVANT le premier enregistrement

1. le tissu est **saisi** sans etre pousse hors de la zone ;
2. le pli est **effectue**, pas seulement amorce ;
3. le resultat tient apres relachement de la pince ;
4. le taux de reussite est mesure sur **n essais annonces a l'avance**, en
   partant d'orientations differentes.

Le critere 4 est le seul qui distingue une politique d'une coincidence.

## Prerequis bloquants

Les memes que pour le dessin, plus : le dessin devrait etre PROVEN avant
d'engager du temps de banc ici. Enchainer sur le pliage sans avoir valide une
tache simple revient a debugger deux problemes a la fois.
