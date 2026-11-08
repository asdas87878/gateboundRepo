#!/usr/bin/env bash
# Full-quality hero views of the Vale (no --quick: map.json Beauty.Render resolution and samples), posted, plus a sheet.
#   bash tools/blender/vale_final.sh [<out dir>] [<view,view,...>]
set -e
cd "$(dirname "$0")/../.."
OUT=${1:-art/lands/land1/beauty/final}
MAP=art/lands/land1/map.json
VIEWS=${2:-$(python -c "import json; print(','.join(v['Name'] for v in json.load(open('$MAP', encoding='utf-8'))['Beauty']['Views']))")}
mkdir -p "$OUT"
"/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" --background --python tools/blender/vale_beauty.py -- "$MAP" "$OUT" --views "$VIEWS" > "$OUT/blender_out.txt" 2>&1
args=()
for v in ${VIEWS//,/ }; do
	python tools/art/look_post.py "$OUT/$v" "$MAP" --key Beauty
	args+=("$OUT/$v/final.png=$v")
done
python tools/art/contact_sheet.py "$OUT/sheet.jpg" 2 "Verdant Vale" "${args[@]}" --width 960
echo "done: $OUT/sheet.jpg"
