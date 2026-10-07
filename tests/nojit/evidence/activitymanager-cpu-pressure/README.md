# ActivityManager / compositor pressure — 7 October 2026

This evidence is from disposable Linux ARM64 guests, not the user's iPhone.
Both jobs in [run 37641950749](https://github.com/hc6q/Rottweiler/actions/runs/37641950749)
used exact QEMU 10.0.12-utm standard TCI, four guest vCPUs on one TCI CPU thread,
4096 MiB, the original v12 image and official software snapshot. Both disabled
Bluetooth without broadcasting CLOSE_SYSTEM_DIALOGS. The memory guard remained
loaded. Neither report passes visible offline APK and USB counter acceptance.

| Observation | Baseline | Rendering profile |
|---|---|---|
| Snapshot boot property | Confirmed, 33.7 seconds | Confirmed, 33.6 seconds |
| Software APK installed / resumed | Both confirmed | Both confirmed |
| Visible USB counter 0 to 1 | Failed; SystemUI ANR covers fixture | Failed; SystemUI ANR covers fixture |
| Guest CPU total in ANR sample | 99% | 99% |
| Largest process at that sample | SurfaceFlinger, 116% of one guest CPU | SurfaceFlinger, 173% of one guest CPU |
| Memory PSI some/full averages | Zero | Zero |
| Profile applied and verified | Not requested | Confirmed; profile command took 461 seconds |
| Watchdog finding | ActivityManager handler blocked 67 seconds | Main/UI handlers blocked 150 seconds |

Guest process percentages may exceed 100% across virtual CPUs. They do not
measure iPhone host CPU or establish a speedup between samples. The profile
run also later records launcher and dex2oat CPU load during repeated launcher
restarts. The logs support severe CPU contention and delayed composition /
framework dispatch. They do not establish a unique deadlock owner.

Baseline logcat records PointerEventDispatcher motion delivery timing out after
54939 ms and launcher TouchInteractionService execution after 65107 ms.
SurfaceFlinger / drmhwc report composition not presented / NOT_VALIDATED.
Java/native thread dump attempts exceed their deadlines. Read-only input/window
dumps themselves expire after 10000 ms; they are not evidence of a missing
input device. Activity state reports the fixture resumed in fullscreen while
the current focus belongs to the SystemUI ANR dialog.

Original artifacts:
- Baseline 11494490578, ZIP SHA-256 d0a10d236727bd6ddb2a67dc17bfe29ae703c66f26055eb5072d4ee1821977b4.
- Optimized 11493906933, ZIP SHA-256 02b3e4d3d701fa988d40e1bb70915503cc2af49d552cf4e27edac77328754d49.

Follow-up:
- [37678737174](https://github.com/hc6q/Rottweiler/actions/runs/37678737174)
  retains baseline and collects DropBox watchdog/ANR records plus activity
  lastanr under the existing shell UID.
- [37680023103](https://github.com/hc6q/Rottweiler/actions/runs/37680023103)
  changes only single to multi CPU threads in the same standard TCI backend.
  Guest vCPU count, RAM, image, snapshot, software APK, display, memory guard and
  counter acceptance remain the same. This is not the UTM threaded interpreter
  backend and does not introduce a JIT.

Both follow-ups are now completed and failed acceptance; detailed findings follow.
Personal device logs are deliberately excluded.


## Completed watchdog / throughput controls

Both follow-ups failed the unchanged visible APK and USB counter requirement.
The serial run restored boot in 36.0 seconds, installed/resumed the fixture, but
retained SystemUI ANR. Before framework death its logcat recorded CPU saturation
(99%, then 97%), CPU PSI some avg10 88.26% and zero memory pressure averages.
A later sample was dominated by system_server (260% of one guest CPU, 176%
kernel), so composition is not the sole observed CPU consumer.

The logcat preserved the decisive end of this failure: Watchdog reports
PowerManagerService monitor overdue 65 seconds and main handler overdue
64 seconds, then explicitly kills system_server with SIGKILL. The annotated
monitor/main stacks captured at kill time are in MessageQueue.nativePollOnce.
They do not expose a permanent Java monitor owner; the overdue condition may
have cleared during slow stack collection. DropBox dumping returned DEAD_OBJECT
and activity disappeared, so the full historical Java trace was not recovered.

InputDispatcher records DOWN delivery timing out and cancels events for the
unresponsive SystemUI ANR window. This explains why an Android touch marker can
appear while the button action does not complete in this host reproduction.
It does not certify the offline APK's counter or every physical iPhone tap.

The parallel run restored boot in 17.8 seconds and installed/resumed the same
fixture source. QMP confirms four distinct CPU thread IDs. It still retained a
Bluetooth dialog, exhausted three captured USB close attempts, then lost the
bridge during diagnostic collection. The disabled-package state is confirmed;
the retained dialog is not evidence that a new Bluetooth process restarted.
No visible fixture counter 0 to 1 or audio was observed. Parallel TCI alone is
not an accepted correction and remains outside the IPA.

APK archive hashes differ between builds; classes.dex and AndroidManifest.xml
hashes are identical in both artifacts:
- classes.dex: b9d63a5e095f349421fb81078602bd47f481ef3f98dd5a445ca6e532e92736c3
- AndroidManifest.xml: 57c6426482b7178572f1747df931bcac37d85aa71a9e9a335a840506a58be9d0

The parallel sysrq blocked-state sample shows CachedAppOptimizer in state D
waiting in synchronize_rcu / locks_start / seq_read_iter, plus a launcher
queued-work thread in state D. This points to a concrete next isolation target:
the Android cached-app freezer and its file-lock checks. One sample does not
prove a persistent RCU deadlock or that disabling this feature fixes the VM.
[AOSP Android 16 CachedAppOptimizer source](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/android16-release/services/core/java/com/android/server/am/CachedAppOptimizer.java)
provides an existing disabled setting for the freezer. It has not been changed
in the IPA or tested in these runs.

Exact QEMU's [EDID generator](https://github.com/utmapp/qemu/blob/v10.0.12-utm/hw/display/edid-generate.c)
defaults to 75000 mHz when no refresh preference is supplied; logcat frame
intervals correspond to 75 Hz. Lowering compositor demand is another candidate,
but a requested mode must actually be accepted after snapshot restoration.
No display-frequency patch or claimed FPS improvement is included.

Verified follow-up artifact SHA-256:
- Serial 11510406720: 4ed8fb876a15aa0155ee464e47f929acfef1a728d884bf6c8348a4f77e7bf911.
- Parallel 11510286583: 3d5f6db9bd7c593b5754a130b0e1618e675d5627c7bf57e6d597f4d957a875b6.

Selected reports are stored beside this file. All evidence here is from
disposable hosts; no personal device logs are included. Released IPA remains
0.8.2 build 25. No new runtime fix, physical acceptance, or release is claimed.
