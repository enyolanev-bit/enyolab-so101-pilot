#!/usr/bin/env bash
# record_demo.sh — VOLONTAIREMENT BLOQUE.
#
# N'enregistre aucun dataset. Les arguments sont acceptes puis ignores.
set -uo pipefail

echo "BLOCKED: physical dataset recording has not been validated yet" >&2
echo >&2
[ "$#" -gt 0 ] && echo "Arguments recus et ignores : $*" >&2 && echo >&2
echo "Raisons, au 2026-10-05 (audit ENYO-14) :" >&2
echo "  - dataset physique : NOT_PROVEN (aucun episode enregistre a ce jour)" >&2
echo "  - la teleoperation, prerequis de l'enregistrement, est elle-meme BLOCKED" >&2
echo >&2
echo "Enregistrer avant d'avoir une teleoperation stable produirait un jeu de" >&2
echo "donnees inexploitable : trajectoires incoherentes, episodes tronques," >&2
echo "calibration douteuse. Le cout n'est pas le temps d'enregistrement, c'est" >&2
echo "l'entrainement mene ensuite sur des donnees fausses." >&2
echo >&2
echo "Prerequis : scripts/teleop.sh doit d'abord etre debloque et valide." >&2
echo "Les taches drawing / folding / freeform sont de la documentation" >&2
echo "d'experience, pas des capacites demontrees. Voir tasks/." >&2
exit 1
