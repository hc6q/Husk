#!/bin/bash
# Build Husk and package an unsigned IPA, validating the bundle before shipping it.
#
# Unsigned is deliberate: AltStore / SideStore / TrollStore re-sign at install, so
# a signing team is not needed and the same artifact works for anyone.
#
# The validation step exists because a bundle missing CFBundleIdentifier or
# CFBundleExecutable builds and zips perfectly happily, and then fails to install
# with no useful message. Xcode does not inject those keys when a custom
# INFOPLIST_FILE is supplied without GENERATE_INFOPLIST_FILE, which is exactly how
# this project is set up.
set -euo pipefail

HUSK_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DD="${DD:-/tmp/husk_ipa}"
OUT="${1:-$HOME/Desktop/Husk.ipa}"
HUSK_NO_JIT="${HUSK_NO_JIT:-0}"
QEMU_BUILD=_husk_build
STAGE_LIB=lib
PROJECT=Husk.xcodeproj
SCHEME=Husk
if [ "$HUSK_NO_JIT" = 1 ]; then
    QEMU_BUILD=_husk_build_nojit
    STAGE_LIB=nojit/lib
    PROJECT=Husk-NoJIT.xcodeproj
    SCHEME=Husk-NoJIT
    DD="${DD}-nojit"
    python3 "$HUSK_ROOT/scripts/generate_nojit_project.py"
fi
mkdir -p "$DD"

# The .app is not the only thing that can be stale. The Xcode target links the
# dylib staged in build/ios-arm64/lib, which is filled in by build_ios.sh's qemu
# stage -- so rebuilding QEMU with plain ninja produces a new dylib that never
# reaches the app, and the IPA ships the previous one with no warning at all.
# That happened once and looked exactly like a fix that did not work.
BUILT="$HUSK_ROOT/third_party/build/qemu-10.0.12-utm/$QEMU_BUILD/libqemu-aarch64-softmmu.dylib"
STAGED="$HUSK_ROOT/build/ios-arm64/$STAGE_LIB/libqemu-aarch64-softmmu.dylib"
if [ -f "$BUILT" ] && [ "$BUILT" -nt "$STAGED" ]; then
    echo "==> staged dylib is older than the built one; restaging"
    cp "$BUILT" "$STAGED"
fi

# Regenerate the project first.
#
# project.yml globs src/app/Husk, so adding a source file there is meant to be
# all it takes -- but the checked-in .pbxproj is a build artefact of that glob,
# and nothing was regenerating it. A new file was therefore silently absent from
# the target, and the only symptom was "cannot find X in scope" for a type that
# is plainly right there on disk.
if command -v xcodegen >/dev/null 2>&1; then
    echo "==> regenerating the project from project.yml"
    (cd "$HUSK_ROOT/src/app" && if [ "$HUSK_NO_JIT" = 1 ]; then xcodegen generate --spec project-nojit.yml --quiet; else xcodegen generate --quiet; fi)
else
    [ "$HUSK_NO_JIT" != 1 ] || { echo "No-JIT requires xcodegen" >&2; exit 1; }
    echo "==> xcodegen not installed; using the checked-in project as-is" >&2
fi

echo "==> building"
xcodebuild -project "$HUSK_ROOT/src/app/$PROJECT" -scheme "$SCHEME" \
    -sdk iphoneos -configuration Release -derivedDataPath "$DD" \
    CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO CODE_SIGN_IDENTITY="" \
    build 2>&1 | tee "$DD/build.log" | grep -E "error:|BUILD (SUCCEEDED|FAILED)" || true

# A failed build used to sail straight past this: the previous .app is still in
# DerivedData, so validation and packaging both succeed and produce an IPA of
# the LAST build. Shipping a stale binary silently is the worst outcome here --
# it looks exactly like a fix that did not work.
if ! grep -q "BUILD SUCCEEDED" "$DD/build.log"; then
    echo "build failed; refusing to package a stale app" >&2
    grep -E "error:" "$DD/build.log" | head -10 >&2
    exit 1
fi

APP="$DD/Build/Products/Release-iphoneos/$SCHEME.app"
[ -d "$APP" ] || { echo "no app bundle at $APP" >&2; exit 1; }

# Stamp the build's identity into the bundle so its logs can name themselves.
# A log from a stale install is otherwise indistinguishable from a log proving a
# fix did not work.
APP_PLIST="$DD/Build/Products/Release-iphoneos/$SCHEME.app/Info.plist"
if [ -f "$APP_PLIST" ]; then
    COMMIT="$(git -C "$HUSK_ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)"
    git -C "$HUSK_ROOT" diff --quiet 2>/dev/null || COMMIT="$COMMIT-dirty"
    plutil -replace HuskBuildCommit -string "$COMMIT" "$APP_PLIST"
    plutil -replace HuskBuildDate -string "$(date -u '+%Y-%m-%d %H:%M UTC')" "$APP_PLIST"
    echo "==> stamped build $COMMIT"
fi

echo "==> validating bundle"
PLIST="$APP/Info.plist"
rc=0
for key in CFBundleIdentifier CFBundleExecutable CFBundleName \
           CFBundlePackageType CFBundleVersion CFBundleShortVersionString \
           MinimumOSVersion UIDeviceFamily; do
    val="$(/usr/libexec/PlistBuddy -c "Print :$key" "$PLIST" 2>/dev/null || true)"
    if [ -z "$val" ]; then
        echo "  MISSING  $key   <-- the app will not install" >&2
        rc=1
    else
        printf "  ok       %-28s %s\n" "$key" "$(echo "$val" | head -1)"
    fi
done

# The executable named in the plist must actually exist.
EXE="$(/usr/libexec/PlistBuddy -c "Print :CFBundleExecutable" "$PLIST" 2>/dev/null || true)"
if [ -n "$EXE" ] && [ ! -f "$APP/$EXE" ]; then
    echo "  MISSING  executable '$EXE' named by CFBundleExecutable" >&2
    rc=1
elif [ -n "$EXE" ]; then
    printf "  ok       %-28s %s\n" "executable present" "$EXE"
fi

# Both dylibs must be embedded, or the app dies at launch with a dyld error.
#
# ANGLE is checked here because it was not, and an IPA shipped without it: the
# app reached qemu_egl_init_dpy_cocoa and aborted with "Couldn't open
# @rpath/libANGLE-shared.dylib". Everything else in this validation passed. A
# check that covers one of two required libraries is a check that reports
# success on a bundle that cannot launch.
for lib in libqemu-aarch64-softmmu.dylib libANGLE-shared.dylib; do
    if [ ! -f "$APP/Frameworks/$lib" ]; then
        echo "  MISSING  Frameworks/$lib" >&2
        rc=1
    else
        printf "  ok       %-28s %s\n" "${lib%%-*} dylib embedded" \
            "$(du -h "$APP/Frameworks/$lib" | cut -f1)"
    fi
done

# Guest images, firmware, and blank disk seeds required by first launch.
for f in vmlinuz-virt initramfs-virt \
         edk2-aarch64-code.fd lineage-efi-vars-seed.fd lineage-vdb-seed.qcow2; do
    if [ ! -f "$APP/$f" ]; then
        echo "  MISSING  $f" >&2
        rc=1
    else
        printf "  ok       %-28s %s\n" "$f" "$(du -h "$APP/$f" | cut -f1)"
    fi
done

# Built-in StikJIT's helper. Without it the app still installs and runs with
# StikDebug, but its JIT setup would offer a method that can only fail.
if [ "$HUSK_NO_JIT" != 1 ]; then
for f in "$APP/husk-jit.js" "$APP/PlugIns/HuskJITHelper.appex/HuskJITHelper" \
         "$APP/Frameworks/StikJIT.framework/StikJIT" \
         "$APP/Frameworks/StikJIT.framework/Info.plist"; do
    if [ ! -f "$f" ]; then
        echo "  MISSING  ${f#$APP/}" >&2
        rc=1
    else
        printf "  ok       %-28s %s\n" "$(basename "$f")" "${f#$APP/}"
    fi
done

else
    python3 "$HUSK_ROOT/scripts/verify_nojit.py" --build "$HUSK_ROOT/third_party/build/qemu-10.0.12-utm/$QEMU_BUILD" --app "$APP" || rc=1
fi

[ $rc -eq 0 ] || { echo "==> bundle is not installable; refusing to package" >&2; exit 1; }

echo "==> packaging"
STAGE="$(mktemp -d)"
mkdir -p "$STAGE/Payload"
cp -R "$APP" "$STAGE/Payload/"
TMP_IPA="$STAGE/Husk.ipa"
( cd "$STAGE" && zip -qry "$TMP_IPA" Payload )

# Atomic replace so a half-written IPA never sits where the good one was.
mv -f "$TMP_IPA" "$OUT"
rm -rf "$STAGE"
echo "==> $OUT  ($(du -h "$OUT" | cut -f1))"
