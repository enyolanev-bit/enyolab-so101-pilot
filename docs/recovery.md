# Recuperation

Que faire quand quelque chose ne va pas. **Couper d'abord, comprendre ensuite.**

## 0. Reflexe

| Situation | Action immediate |
|---|---|
| Mouvement inattendu | couper l'alimentation du bras |
| Bras en butee, servo qui pousse | couper — ne pas retenir a la main |
| Odeur, chaleur anormale, fumee | couper, debrancher le secteur, ne pas rebrancher |
| Doute quelconque | couper. Une coupure ne coute rien. |

Ne jamais diagnostiquer un bras sous tension qui bouge.

## 1. Aucun port serie detecte

`scripts/find_ports.sh` ne liste rien de plausible.

Par ordre de probabilite :

1. **Cable USB-C de charge** — le plus frequent. Pas de lignes de donnees, donc
   aucun port. Essayer un autre cable, connu comme cable data.
2. **Carte non alimentee** — le bloc 5 V n'est pas branche ou le barillet est mal
   insere.
3. **Pilote serie absent** — selon la carte : CH340 ou CP210x.
4. **Port USB du cote machine** — tester un autre port, puis un autre hub. Un hub
   passif peut ne pas suffire.

## 2. Deux ports apparaissent, on ne sait pas lequel est quel bras

C'est une **ambiguite, pas un detail**. Attribuer le mauvais port au mauvais bras
envoie des commandes leader a un follower.

Procedure : debrancher les deux, brancher **un seul**, relever le port, le noter,
debrancher, brancher l'autre, relever. Ne pas deviner a partir de l'ordre
d'apparition ou d'un numero de port — il change d'un branchement a l'autre.

## 3. Un servo ne repond pas

1. Couper.
2. Verifier le cable 3 fils aux deux extremites — c'est la cause la plus
   frequente et la moins couteuse.
3. Verifier que l'**ID** attendu est bien celui configure. Deux servos au meme ID
   sur un bus produisent un comportement incoherent, pas une erreur franche.
4. Verifier la tension d'alimentation sous charge, pas a vide.
5. Si le servo chauffe sans bouger : il force contre une butee mecanique. Coupe,
   puis desassembler pour comprendre — ne pas reessayer.

## 4. Un servo chauffe

Couper immediatement. Un STS3215 chaud force contre quelque chose : butee
mecanique, piece imprimee mal ajustee, ou position commandee hors course.
Reprendre apres refroidissement complet, et apres avoir trouve la cause. Une
reprise sans diagnostic repete exactement le meme forcage.

## 5. La calibration est perdue ou douteuse

1. **Ne pas** recopier une calibration d'un autre bras : le fichier aura l'air
   valide et sera faux. Transfert d'une calibration du meme bras vers un autre
   hote : non autorise tant que HQ n'a pas decide, voir `../calibration/README.md`.
2. Sauvegarder horodate ce qui existe encore, avant toute nouvelle calibration.
3. Recalibrer sur le robot assemble.
4. Comparer l'ancien et le nouveau fichier. Un ecart important sur `range_min` /
   `range_max` est une information, pas un bruit.
5. Premier mouvement apres recalibration : amplitude et vitesse reduites, une
   articulation a la fois, main sur la coupure.

Voir `../calibration/README.md`.

## 6. Une piece imprimee a cede

1. Couper.
2. **Photographier avant de demonter.** La facon dont une piece casse dit ou
   etait la contrainte.
3. Ne pas recoller pour continuer la session. Une piece recollee se recasse au
   meme endroit, generalement en emportant autre chose.
4. Reimprimer. Consigner quelle piece, a quel endroit, sous quel geste.

## 7. Cameras absentes ou image floue

- Absente : UVC ne demande aucun pilote, donc c'est le cable, le hub, ou le port.
  Deux cameras sur un hub passif peuvent depasser le budget de bande passante
  USB — les repartir sur deux ports.
- Floue : **la mise au point de ces modules est manuelle.** Tourner l'objectif.
  Ce n'est pas un defaut.

## 8. Regle generale

> Un seul fait inexplique suffit a arreter la session.
>
> Continuer en esperant que ca passe transforme un probleme identifiable en
> trois problemes superposes. Noter le fait, couper, reprendre une fois qu'il est
> explique.
