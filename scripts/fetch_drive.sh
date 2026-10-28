#!/usr/bin/env bash
# Download a Google Drive file by id (file must be shared "Anyone with the link").
# The Drive connector can't move large videos, so use it to look up ids and this to download.
# usage: fetch_drive.sh FILE_ID OUT_PATH
set -euo pipefail
curl -fsSL -o "$2" "https://drive.usercontent.google.com/download?id=$1&export=download&confirm=t"
size=$(stat -c %s "$2")
if [ "$size" -lt 100000 ] && grep -qi "<html" "$2"; then
  echo "ERROR: got a web page instead of the file. Is it shared as 'Anyone with the link can view'?" >&2
  exit 1
fi
echo "$2: $size bytes"
