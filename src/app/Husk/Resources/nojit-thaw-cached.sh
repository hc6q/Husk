#!/system/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
# AOSP's disabled override stops future freezes but can retain frozen snapshot
# processes. Use ActivityManager's supported thaw path (Binder then cgroup),
# never write cgroups directly or change SELinux/root privileges.
set -eu
dump=$(mktemp /data/local/tmp/rottweiler-freezer.XXXXXX)
trap 'rm -f "$dump"' EXIT
settings put global cached_apps_freezer disabled
[ "$(settings get global cached_apps_freezer)" = disabled ]
# SettingsContentObserver runs asynchronously on the ActivityManager handler.
attempt=0
while :; do
    dumpsys activity cao > "$dump"
    if grep -Eq '^[[:space:]]*use_freezer=false[[:space:]]*$' "$dump"; then
        break
    fi
    attempt=$((attempt + 1))
    [ "$attempt" -lt 12 ] || { echo '[NoJIT] Freezer override not effective'; exit 5; }
    sleep 2
done
# Refuse partial dumps or unexpected formats. Only the frozen process list may
# supply numeric PIDs to am; no package names or arbitrary dump text is executed.
pids=$(awk '
    /^[[:space:]]*Apps frozen: [0-9]+[[:space:]]*$/ {
        if (seen++) exit 6
        expected=$3; listing=1; next
    }
    listing && NF {
        if ($1 !~ /^[0-9]+:$/ || $2 !~ /^[0-9]+$/ || $2+0 <= 1) exit 6
        ids=ids " " $2; count++
    }
    END { if (!seen || count != expected || expected > 512) exit 6; print ids }
' "$dump")
count=0
for pid in $pids; do
    # Each mutation is attempted once. A disappearing cached process is benign
    # only if the final dump confirms it is no longer frozen.
    am unfreeze --sticky "$pid" || echo "[NoJIT] Thaw command failed for pid $pid"
    count=$((count + 1))
done
dumpsys activity cao > "$dump"
grep -Eq '^[[:space:]]*use_freezer=false[[:space:]]*$' "$dump"
grep -Eq '^[[:space:]]*Apps frozen: 0[[:space:]]*$' "$dump"
sync
echo "[NoJIT] Cached freezer disabled; thawed $count snapshot processes; Apps frozen: 0"
