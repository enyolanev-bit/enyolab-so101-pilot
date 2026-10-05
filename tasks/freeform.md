# Tache — Libre

**Etat : NOT_PROVEN.** Documentation d'experience. Rien ici n'a ete execute.

## Intention

Case ouverte : la tache que Boris choisira une fois le systeme en main.
Deplacer un objet d'un point A a un point B, trier, empiler, poser un
couvercle, appuyer sur un bouton.

Ce fichier n'est pas une tache. C'est la **grille a remplir** avant d'en
engager une, pour eviter de decouvrir en cours de route qu'elle n'etait pas
faisable avec ce bras.

## Grille de faisabilite

Repondre aux six lignes avant d'enregistrer le premier episode.

| # | Question | Pourquoi elle est la |
|---|---|---|
| 1 | **Objet rigide ou deformable ?** | Deformable = ordre de grandeur de demonstrations superieur. Voir `folding.md`. |
| 2 | **Tient dans la course du bras ?** | Le SO-101 est petit. Mesurer avant, pas apres. |
| 3 | **Masse dans les limites des servos ?** | Les STS3215 ne sont pas des actionneurs de charge. Un objet trop lourd fait chauffer puis decrocher. |
| 4 | **Prehension possible avec cette pince ?** | Pince simple, deux doigts, pas de retour d'effort. Un objet rond et lisse peut etre hors de portee mecanique. |
| 5 | **L'etat est-il visible par les 2 cameras ?** | Ce que les cameras ne voient pas, la politique ne l'apprend pas. |
| 6 | **Le succes est-il observable sans ambiguite ?** | Si deux personnes ne tombent pas d'accord sur "reussi / rate", la tache n'est pas evaluable. |

Une reponse "non" ou "je ne sais pas" sur une seule ligne suffit a renvoyer la
tache en conception. Ce n'est pas du zele : chacune de ces six lignes correspond
a un echec qui ne devient visible qu'apres des heures d'enregistrement.

## Criteres de succes

A ecrire **avant** l'enregistrement, jamais apres, et jamais ajustes a la
lumiere du resultat. Doivent comprendre :

- un critere binaire de reussite par episode ;
- un nombre d'essais annonce a l'avance ;
- une condition de securite qui invalide l'essai independamment du resultat.

## Prerequis bloquants

Dessin PROVEN d'abord. La tache libre est la troisieme, pas la premiere.
