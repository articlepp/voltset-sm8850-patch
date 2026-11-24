#!/bin/bash
# Verify that a built APK actually contains all seven layers.
#   bash tools/verify.sh build/VoltSet-patched.apk
set -euo pipefail
APK=${1:?usage: bash tools/verify.sh <apk>}
python3 - "$APK" <<'PY'
import sys, zipfile
apk = zipfile.ZipFile(sys.argv[1])
names = apk.namelist()
script = apk.read('assets/backend/voltset.sh').decode()
checks = {
    'L1 private-ns mount':        'VOLTSET_PRIVATE_NS' in script,
    'L2 record on apply':         '$target_global" > "$persistent/last-set"' in script,
    'L3 self-heal target':        'heal_cpuss' in script,
    'L4 drift repair (user only)':'last-set.from-user' in script and 'layer 2: repair' in script,
    'L5 boot hook':               '99-voltset-bootapply.sh' in script,
    'L6 write retries':           'BOOTAPPLY=FAILED' in script,
    'L7 diagnostics':             'voltset-diag.txt' in script,
    'vsetns asset':               'assets/backend/bin/vsetns' in names,
}
for k, v in checks.items():
    print(('OK   ' if v else 'FAIL ') + k)
if not all(checks.values()):
    sys.exit(1)
print('all layers present')
PY
