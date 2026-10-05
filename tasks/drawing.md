# Tache — Dessin

**Etat : NOT_PROVEN.** Documentation d'experience. Rien ici n'a ete execute.

## Intention

Le follower tient un feutre et reproduit un trace simple sur une feuille posee
a plat : une ligne, un carre, un cercle. L'operateur montre le geste au leader,
le systeme enregistre, puis rejoue.

## Pourquoi commencer par la

C'est la tache la plus accessible des trois, pour une raison precise : **son
echec est visible**. Une trajectoire approximative laisse une trace tordue sur
le papier. Pas besoin de metrique, pas besoin d'instrument — la feuille est le
rapport d'evaluation.

Les trois autres proprietes qui la rendent commode :

- 2D. La hauteur du feutre est quasi constante ; une dimension de moins a tenir.
- Pas de prehension fine. Le feutre est tenu une fois, pas saisi puis relache.
- Repetable a l'identique. Meme feuille, meme depart, autant d'essais qu'on veut.

## Montage

| Element | Note |
|---|---|
| Feutre | fixe dans la pince, **pas** saisi a chaque episode |
| Feuille | scotchee a plat, repere de depart marque |
| Hauteur | le feutre doit toucher sans que le bras pousse sur la table |
| Camera poignet | voit la pointe et le trace |
| Camera dessus | voit la feuille entiere |

Le point delicat est la pression. Trop haut : rien ne s'ecrit. Trop bas : le
bras force contre la table a chaque point du trace, et ce sont les servos qui
encaissent. Un feutre monte sur une petite reprise elastique absorbe l'erreur
de hauteur — a concevoir si le probleme se presente.

## Criteres de succes, a figer AVANT le premier enregistrement

1. le trace est **continu** — pas d'interruption au milieu d'un segment ;
2. il est **reconnaissable** — un carre se lit comme un carre ;
3. il est **reproductible** — n fois de suite, pas une reussite sur dix ;
4. le bras **ne force jamais** contre la table.

Le critere 4 est un critere de securite, pas de performance : il invalide
l'essai meme si le dessin est beau.

## Prerequis bloquants

- `scripts/teleop.sh` debloque et valide ;
- calibration leader obtenue ;
- calibration follower revalidee ;
- 2 cameras fonctionnelles.

Aucun n'est satisfait au 2026-10-05.
