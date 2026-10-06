#!/bin/bash
# Build a small Java APK without Gradle, native libraries or Google services.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:?Set ANDROID_HOME to an Android SDK}}"
TOOLS="$SDK/build-tools/35.0.0"
ANDROID="$SDK/platforms/android-35/android.jar"
WORK="$ROOT/build/nojit-apk"
mkdir -p "$WORK/classes" "$WORK/dex"
javac -source 8 -target 8 -bootclasspath "$ANDROID" -d "$WORK/classes" \
    "$ROOT/tests/nojit/fixture/MainActivity.java"
"$TOOLS/d8" --lib "$ANDROID" --min-api 23 --output "$WORK/dex" \
    "$WORK/classes/org/husk/nojitsmoke/MainActivity.class"
"$TOOLS/aapt" package -f -M "$ROOT/tests/nojit/fixture/AndroidManifest.xml" \
    -I "$ANDROID" -F "$WORK/unsigned.apk"
(cd "$WORK/dex" && zip -q "$WORK/unsigned.apk" classes.dex)
"$TOOLS/zipalign" -f 4 "$WORK/unsigned.apk" "$WORK/aligned.apk"
if [ ! -f "$WORK/test.keystore" ]; then
    keytool -genkeypair -keystore "$WORK/test.keystore" -alias smoke \
        -storepass android -keypass android -dname 'CN=Husk No-JIT Test' \
        -keyalg RSA -validity 3650
fi
"$TOOLS/apksigner" sign --ks "$WORK/test.keystore" --ks-key-alias smoke \
    --ks-pass pass:android --out "$ROOT/build/NoJITSmoke.apk" "$WORK/aligned.apk"
"$TOOLS/apksigner" verify "$ROOT/build/NoJITSmoke.apk"
echo "$ROOT/build/NoJITSmoke.apk"
