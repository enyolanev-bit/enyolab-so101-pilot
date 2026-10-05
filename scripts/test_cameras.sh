#!/usr/bin/env bash
# test_cameras.sh — DETECTE et LISTE les cameras. Premiere version : aucune
# capture, aucun flux ouvert, aucun enregistrement, aucun dataset.
set -uo pipefail

UNAME=$(uname -s)
echo "=== CAMERAS DETECTEES ==="

if [ "$UNAME" = "Darwin" ]; then
  OUT=$(system_profiler SPCameraDataType 2>/dev/null | grep -E '^ {4,8}[^ ].*:$' | sed 's/:$//' | sed 's/^ */  - /')
  [ -n "$OUT" ] && echo "$OUT" || echo "  aucune camera rapportee par le systeme"
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
echo "  2 vues sont necessaires a l'entrainement : poignet + vue de dessus."
echo "  Une seule vue ne suffit pas."
echo
echo "  Cameras prevues : InnoMaker U20CAM-1080P (poignet, UVC, 32x32 mm)"
echo "                    InnoMaker U20CAM-720P  (dessus,  UVC, 32x32 mm)"
echo
echo "  La camera integree d'un portable n'est PAS une des deux vues."
echo "  La mise au point de ces modules est MANUELLE : image floue au premier"
echo "  branchement est normal, il faut tourner l'objectif."
echo
echo "Termine. Aucun flux ouvert, aucune image enregistree."
