#!/bin/bash
# Build a patched VoltSet APK.
#   bash build.sh /path/to/voltset-0.2.0-original.apk /path/to/your.jks
set -euo pipefail
ORIG=${1:?usage: bash build.sh <original.apk> <keystore.jks>}
KS=${2:?usage: bash build.sh <original.apk> <keystore.jks>}
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
mkdir -p build

gcc -O2 -static -s -o build/vsetns src/vsetns.c
python3 tools/repack.py "$ORIG" assets/backend/voltset.sh build/vsetns build/unsigned.apk
zipalign -f -p 4 build/unsigned.apk build/aligned.apk
apksigner sign --ks "$KS" --out build/VoltSet-patched.apk build/aligned.apk
apksigner verify build/VoltSet-patched.apk
echo "OK -> build/VoltSet-patched.apk"
