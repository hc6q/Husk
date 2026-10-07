#!/system/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
# Block the unavailable Bluetooth application through Android PackageManager.
# No global dialog dismissal, init/SELinux edit, root, or immutable image change.
set -eu
package=com.android.bluetooth
command -v pidof >/dev/null
if ! pm list packages -d --user 0 "$package" | grep -Fx "package:$package"; then
    pm disable-user --user 0 "$package"
fi
pm list packages -d --user 0 "$package" | grep -Fx "package:$package"
am force-stop --user 0 "$package"
if pidof "$package"; then
    echo '[NoJIT] Bluetooth remains running; startup block not confirmed'
    exit 4
else
    status=$?
    # Only pidof's documented no-match result confirms absence. Tool failures
    # must not be reported as successful process termination.
    [ "$status" -eq 1 ] || exit "$status"
fi
# Persist PackageManager state before any later snapshot/save.
sync
echo '[NoJIT] Bluetooth startup blocked: package disabled, primary process stopped'
