#!/usr/bin/env bash
# find_ports.sh — liste les ports serie CANDIDATS.
# N'OUVRE AUCUN PORT. N'ENVOIE AUCUNE COMMANDE.
# Ouvrir un port peut reinitialiser une carte ou reveiller un bus servo :
# ce script se contente d'enumerer des entrees du systeme de fichiers.
set -uo pipefail

UNAME=$(uname -s)
echo "=== PORTS SERIE CANDIDATS ==="
FOUND=0

if [ "$UNAME" = "Darwin" ]; then
  for p in /dev/cu.*; do
    [ -e "$p" ] || continue
    case "$p" in
      *Bluetooth*|*debug-console*) TAG="(systeme / Bluetooth — ignorer)" ;;
      *usbmodem*|*usbserial*|*wchusbserial*|*SLAB*) TAG="<== CANDIDAT adaptateur servo" ;;
      *) TAG="(a identifier)" ;;
    esac
    printf "  %-40s %s\n" "$p" "$TAG"
    FOUND=1
  done
else
  for p in /dev/ttyUSB* /dev/ttyACM* /dev/serial/by-id/*; do
    [ -e "$p" ] || continue
    printf "  %-48s %s\n" "$p" "<== CANDIDAT"
    FOUND=1
  done
fi

[ "$FOUND" -eq 0 ] && echo "  aucun port serie trouve"

echo
echo "=== LECTURE ==="
echo "  Un adaptateur bus servo apparait typiquement en usbmodem / usbserial"
echo "  (macOS) ou ttyUSB / ttyACM (Linux)."
echo
echo "  Si rien n'apparait apres branchement :"
echo "    1. le cable USB-C est peut-etre un cable de CHARGE, sans lignes de donnees ;"
echo "    2. la carte n'est pas alimentee ;"
echo "    3. le pilote serie n'est pas installe (CH340 / CP210x selon la carte)."
echo
echo "  Deux adaptateurs identiques branches ensemble = AMBIGUITE."
echo "  Dans ce cas, s'arreter et les identifier un par un, en les branchant"
echo "  separement. Attribuer le mauvais port au mauvais bras est une erreur"
echo "  couteuse. Voir AGENTS.md, regle 9."
echo
echo "Termine. Aucun port ouvert."
