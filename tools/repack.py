#!/usr/bin/env python3
"""Rebuild the VoltSet APK with the patched backend script and the vsetns helper.

Why not unzip/zip: the APK declares extractNativeLibs=false, so every
lib/**/*.so entry MUST stay ZIP_STORED (uncompressed) or the installer fails
with INSTALL_FAILED_INVALID_APK / "Failed to extract native libraries, res=-2".
This script copies the original entries one by one, preserving compression
type, and only replaces/ adds the two files we care about.

Usage:
    python3 repack.py <original.apk> <patched-voltset.sh> <vsetns> <out-unsigned.apk>

Then:
    zipalign -f -p 4 out-unsigned.apk out-aligned.apk
    apksigner sign --ks vset.jks --out voltset-mod.apk out-aligned.apk
"""
import sys
import zipfile

HELPER_NAME = "assets/backend/bin/vsetns"
SCRIPT_NAME = "assets/backend/voltset.sh"


def is_signature_entry(name: str) -> bool:
    if not name.startswith("META-INF/"):
        return False
    if name == "META-INF/MANIFEST.MF":
        return True
    return name.rsplit(".", 1)[-1] in {"SF", "RSA", "DSA", "EC"}


def main(orig: str, patched_script: str, vsetns: str, out: str) -> None:
    with open(patched_script, "rb") as f:
        script_bytes = f.read()
    with open(vsetns, "rb") as f:
        helper_bytes = f.read()

    src = zipfile.ZipFile(orig)
    names = set(src.namelist())
    if SCRIPT_NAME not in names:
        raise SystemExit(f"{SCRIPT_NAME} not found in {orig}")

    replaced = 0
    with zipfile.ZipFile(out, "w") as dst:
        for item in src.infolist():
            name = item.filename
            if is_signature_entry(name):
                continue
            data = script_bytes if name == SCRIPT_NAME else src.read(name)
            if name == SCRIPT_NAME:
                replaced += 1
            stored = name.startswith("lib/") and name.endswith(".so")
            info = zipfile.ZipInfo(name, date_time=item.date_time)
            info.compress_type = zipfile.ZIP_STORED if stored else item.compress_type
            info.external_attr = item.external_attr
            dst.writestr(info, data)

        helper = zipfile.ZipInfo(HELPER_NAME, date_time=(2020, 1, 1, 0, 0, 0))
        helper.compress_type = zipfile.ZIP_DEFLATED
        helper.external_attr = 0o100755 << 16
        dst.writestr(helper, helper_bytes)

    print(f"rebuilt -> {out} (script replaced: {replaced})")


if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit(__doc__)
    main(*sys.argv[1:5])
