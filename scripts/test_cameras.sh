#!/usr/bin/env bash
# test_cameras.sh — DETECTE et LISTE les cameras. Premiere version : aucune
# capture, aucun flux ouvert, aucun enregistrement, aucun dataset.
set -uo pipefail

UNAME=$(uname -s)
echo "=== CAMERAS DETECTEES ==="

if [ "$UNAME" = "Darwin" ]; then
  OUT=$(system_profiler SPCameraDataType 2>/dev/null | grep -E '^ {4,8}[^ ].*:$' | sed 's/:$//' | sed 's/^ */  - /')
  [ -n "$OUT" ] && echo "$OUT" || echo "  aucune camera rapportee par le systeme"
  echo
  echo "=== INDEX AVFOUNDATION (liste seule, aucun flux ouvert) ==="
  if command -v ffmpeg >/dev/null 2>&1; then
    ffmpeg -hide_banner -f avfoundation -list_devices true -i "" 2>&1 \
      | sed -n '/AVFoundation video devices/,/AVFoundation audio devices/p' \
      | grep -E '\[[0-9]+\]' | sed -E 's/.*\] (\[[0-9]+\])/  \1/'
    echo "  Index AVFoundation (FFmpeg). Correspondance avec l'index OpenCV NON"
    echo "  prouvee, ordre NON stable d'une enumeration a l'autre. Confirmer"
    echo "  l'identite par une capture avant tout usage ; propre a cette machine."
  else
    echo "  ffmpeg absent : index non listes (voir setup/mac.md)"
  fi
else
  FOUND=0
  for d in /dev/video*; do
    [ -e "$d" ] || continue
    if command -v v4l2-ctl >/dev/null 2>&1; then
      NAME=$(v4l2-ctl -d "$d" --info 2>/dev/null | grep -m1 'Card type' | cut -d: -f2- | sed 's/^ *//')
      printf "  - %-16s %s\n" "$d" "${NAME:-}"
    else
      echo "  - $d"
    fi
    FOUND=1
  done
  [ "$FOUND" -eq 0 ] && echo "  aucun /dev/video* trouve"
fi

echo
echo "=== ATTENDU POUR LE PILOTE ==="
echo "  PILOT_REQUIREMENT: wrist + overhead"
echo "  Deux vues retenues pour ce pilote : poignet (pince et objet) + dessus"
echo "  (scene et position du bras). Choix du projet, pas une regle generale."
echo
echo "  Cameras prevues : InnoMaker U20CAM-1080P (poignet, UVC, 32x32 mm)"
echo "                    InnoMaker U20CAM-720P  (dessus,  UVC, 32x32 mm)"
echo
echo "  La camera integree d'un portable n'est PAS une des vues retenues."
echo "  La mise au point de ces modules est MANUELLE : image floue au premier"
echo "  branchement est normal, il faut tourner l'objectif."
echo
echo "Termine. Aucun flux ouvert, aucune image enregistree."
