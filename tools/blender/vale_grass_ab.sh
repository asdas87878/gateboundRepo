#!/usr/bin/env bash
# Grass A/B on the Vale (docs/style/grass.md): the same view rendered once per grass style, posted, then a labelled sheet.
#   bash tools/blender/vale_grass_ab.sh <out dir> <view> <style> [<style> ...]
# Styles live in art/lands/land1/map.json "Beauty.GrassStyles". Writes <out>/<style>/<view>/final.png and <out>/sheet.jpg.
set -e
cd "$(dirname "$0")/../.."
OUT=$1
VIEW=$2
shift 2
BL="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
MAP=art/lands/land1/map.json
args=()
for st in "$@"; do
	mkdir -p "$OUT/$st"
	"$BL" --background --python tools/blender/vale_beauty.py -- "$MAP" "$OUT/$st" --views "$VIEW" --grass "$st" --quick > "$OUT/$st/blender_out.txt" 2>&1
	python tools/art/look_post.py "$OUT/$st/$VIEW" "$MAP" --key Beauty
	args+=("$OUT/$st/$VIEW/final.png=$st")
	echo "rendered $st"
done
python tools/art/contact_sheet.py "$OUT/sheet.jpg" "$#" "Grass styles: $VIEW" "${args[@]}" --width 960
echo "sheet $OUT/sheet.jpg"
