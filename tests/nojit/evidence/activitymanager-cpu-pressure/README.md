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

Both follow-up results are pending. No physical APK/touch/audio acceptance or
new IPA release is claimed. Personal device logs are deliberately excluded.
