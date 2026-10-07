#!/system/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
# Reversible userspace tuning; never changes the immutable guest image.
set -eu
state=/data/local/tmp/rottweiler-performance-v1
mode=${1:-apply}
keys='global:window_animation_scale global:transition_animation_scale global:animator_duration_scale system:show_touches system:pointer_location'

if [ "$mode" = restore ]; then
    [ -d "$state" ] || exit 0
    for entry in $keys; do
        namespace=${entry%%:*}; key=${entry#*:}
        [ -f "$state/$key" ] || continue
        value=$(cat "$state/$key")
        if [ "$value" = null ]; then settings delete "$namespace" "$key";
        else settings put "$namespace" "$key" "$value"; fi
    done
    if [ -f "$state/size" ]; then wm size "$(cat "$state/size")"; fi
    if [ -f "$state/density" ]; then wm density "$(cat "$state/density")"; fi
    rm -rf "$state"
    echo '[NoJIT] Original rendering settings restored'
    exit 0
fi
[ "$mode" = apply ] || exit 2
[ ! -f "$state/applied" ] || { echo '[NoJIT] Performance profile already applied'; exit 0; }
umask 077
mkdir -p "$state"
for entry in $keys; do
    namespace=${entry%%:*}; key=${entry#*:}
    if [ ! -f "$state/$key" ]; then
        settings get "$namespace" "$key" > "$state/$key.tmp"
        mv "$state/$key.tmp" "$state/$key"
    fi
done
size_info=$(wm size)
density_info=$(wm density)
if [ ! -f "$state/size" ]; then
    original=$(printf '%s\n' "$size_info" | sed -n 's/^Override size: //p')
    printf '%s\n' "${original:-reset}" > "$state/size"
fi
if [ ! -f "$state/density" ]; then
    original=$(printf '%s\n' "$density_info" | sed -n 's/^Override density: //p')
    printf '%s\n' "${original:-reset}" > "$state/density"
fi
physical=$(printf '%s\n' "$size_info" | sed -n 's/^Physical size: //p')
density=$(printf '%s\n' "$density_info" | sed -n 's/^Physical density: //p')
width=${physical%x*}; height=${physical#*x}
case "$width:$height:$density" in *[!0-9:]*|'') echo '[NoJIT] Invalid display geometry'; exit 3;; esac
[ "$width" -gt 0 ] && [ "$height" -gt 0 ] && [ "$density" -gt 0 ]
width=$((width * 3 / 8 * 2)); height=$((height * 3 / 8 * 2)); density=$((density * 3 / 4))
[ "$width" -ge 120 ] && [ "$height" -ge 120 ] && [ "$density" -ge 120 ]
for entry in $keys; do
    namespace=${entry%%:*}; key=${entry#*:}
    settings put "$namespace" "$key" 0
    [ "$(settings get "$namespace" "$key")" = 0 ]
done
wm size "${width}x${height}"
wm density "$density"
wm size | grep -Fx "Override size: ${width}x${height}"
wm density | grep -Fx "Override density: $density"
touch "$state/applied"
echo '[NoJIT] Performance profile verified: 75% linear rendering, animations and touch overlays off'
