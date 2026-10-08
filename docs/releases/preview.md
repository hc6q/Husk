# Rottweiler No-JIT — Experimental preview

Android APK launcher for iOS arm64, based on Husk and QEMU 10.0.12-utm TCI.
This is an experimental test build, not a validated daily-use release.

## Changes
- Recover cached processes retained in a frozen state after snapshot restoration. Disabling the cached-app freezer alone did not thaw them in the Android 16 guest.
- Recovery uses Android's supported `am unfreeze --sticky` command, then requires `use_freezer=false` and `Apps frozen: 0` before logging success. It runs once per readiness cycle and does not replay timed-out mutations.
- Early Bluetooth package blocking and the reversible rendering profile remain included.
- Independent No-JIT app version **0.8.3, build 26**. The original JIT app version is unchanged.
- Successful physical iPhone APK interaction and a performance improvement remain unverified.
- Real ARM64 parallel-TCI test (run 37722375200): recovery changed **24 frozen processes to 0**, independently verified by ActivityManager. The offline Java APK installed and resumed, but its visible counter and USB touch acceptance **failed**. The Bluetooth error dialog remained over the app and later the framework restarted. Single-TCI results are still pending; this does not certify that the SystemUI hang is resolved.

## Installation
Download `Rottweiler.ipa`, sign it with your normal sideload tool and install it on an iOS arm64 device. The IPA is unsigned. No JIT helper, debugger, pairing, TrollStore or jailbreak is required by the No-JIT target.
For initial testing, select CPU renderer, enable the official snapshot and disable Sound. Import the included `NoJITSmoke.apk` (not a ZIP or IPA).
Keep your existing Android data when upgrading; the bundle identifier remains `com.husk.nojit`.

## Known bugs and limitations
- The Android Bluetooth crash dialog has appeared on a physical iPhone; the mitigation is not physically verified.
- APK selection/import previously appeared unresponsive. The main-actor blocking fix is included, but successful physical import/install/launch remains unverified.
- Touch has not been certified: displaying LineageOS or resuming an Activity does not prove interaction works.
- Interpreter performance is low; boot, installation and UI actions can take several minutes.
- Audio and GPU rendering are not physically validated. Sound changes require a cold boot and prevent snapshots.
- Cold-boot low-performance experiments caused SystemUI/freeform crashes and RescueParty. That option is deliberately excluded from this IPA.
- Linux tests installed a small offline Java APK, but did not pass the visible app + USB touch counter 0→1 acceptance test. They do not certify iPhone behavior.

## To-do list
- [ ] Confirm that the iOS file picker dismisses and imports a selected APK.
- [ ] Verify complete `pm install` success and launch the offline Java test app on an iPhone.
- [ ] Display the test app and increment its counter from 0 to 1 through USB touch input.
- [ ] Confirm the Bluetooth crash dialog no longer blocks the Android UI.
- [ ] Diagnose remaining Android service and SystemUI failures without changing the base image unnecessarily.
- [ ] Validate GPU/Metal rendering, touch coordinates and audio on physical hardware.
- [ ] Repeat backend and executable-memory audits on the release binary.
- [ ] Measure JIT versus No-JIT with the same image and workload.

## Validation and credits
CI compilation and static target checks are required before publishing these assets. Successful compilation is not physical acceptance. See `docs/nojit.md` in the tagged source for evidence and limitations.

Based on [Husk by Leviidev](https://github.com/Leviidev/Husk). Original credits and GPL-2.0-or-later obligations remain in the source and Settings menu. The original JIT target is preserved; this preview uses `HUSK_NO_JIT`.
