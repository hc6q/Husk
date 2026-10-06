#!/bin/bash
# Build a small Java APK without Gradle, native libraries or Google services.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:?Set ANDROID_HOME to an Android SDK}}"
TOOLS="$SDK/build-tools/35.0.0"
ANDROID="$SDK/platforms/android-35/android.jar"
WORK="$ROOT/build/nojit-apk"
mkdir -p "$WORK/classes" "$WORK/dex"
MANIFEST="$ROOT/tests/nojit/fixture/AndroidManifest.xml"
OUTPUT="$ROOT/build/NoJITSmoke.apk"
if [ "${HUSK_SMOKE_SOFTWARE_UI:-0}" = 1 ]; then
    mkdir -p "$WORK/software"
    MANIFEST="$WORK/software/AndroidManifest.xml"
    OUTPUT="$ROOT/build/NoJITSmoke-Software.apk"
    python3 - "$ROOT/tests/nojit/fixture/AndroidManifest.xml" "$MANIFEST" <<'PY'
import sys
from pathlib import Path
source = Path(sys.argv[1]).read_text()
source = source.replace('package="org.husk.nojitsmoke"', 'package="org.husk.nojitsmoke.software"')
source = source.replace('android:label="NoJIT Smoke"', 'android:label="NoJIT Smoke Software" android:hardwareAccelerated="false"')
source = source.replace('android:name=".MainActivity"', 'android:name="org.husk.nojitsmoke.MainActivity"')
Path(sys.argv[2]).write_text(source)
PY
fi
javac -source 8 -target 8 -classpath "$ANDROID" -d "$WORK/classes" \
    "$ROOT/tests/nojit/fixture/MainActivity.java"
"$TOOLS/d8" --lib "$ANDROID" --min-api 23 --output "$WORK/dex" \
    "$WORK/classes/org/husk/nojitsmoke/MainActivity.class"
"$TOOLS/aapt" package -f -M "$MANIFEST" \
    -I "$ANDROID" -F "$WORK/unsigned.apk"
(cd "$WORK/dex" && zip -q "$WORK/unsigned.apk" classes.dex)
"$TOOLS/zipalign" -f 4 "$WORK/unsigned.apk" "$WORK/aligned.apk"
if [ ! -f "$WORK/test.keystore" ]; then
    keytool -genkeypair -keystore "$WORK/test.keystore" -alias smoke \
        -storepass android -keypass android -dname 'CN=Husk No-JIT Test' \
        -keyalg RSA -validity 3650
fi
"$TOOLS/apksigner" sign --ks "$WORK/test.keystore" --ks-key-alias smoke \
    --ks-pass pass:android --out "$OUTPUT" "$WORK/aligned.apk"
"$TOOLS/apksigner" verify "$OUTPUT"
echo "$OUTPUT"
