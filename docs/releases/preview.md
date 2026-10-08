# Rottweiler No-JIT — Experimental preview

Android APK launcher for iOS arm64, based on Husk and QEMU 10.0.12-utm TCI.
This is an experimental test build, not a validated daily-use release.

## Changes
- Move pending APK file-provider copies off the iOS main actor. Commit complete split sets atomically; failed copies leave no installable partial transaction.
- Block the unavailable Bluetooth package before slow cached-process recovery, with visible startup stages.
- Require a responding PackageManager before releasing queued imports; a restored boot property alone is insufficient. Timed-out mutations are not replayed.
- Reduce No-JIT background health polling from every 5 seconds to every 30 seconds; the original JIT mode is unchanged.
- No-JIT version **0.8.4, build 27**. No measured speedup or successful physical APK interaction is claimed.
- Previous exact-TCI controls recovered **31 frozen processes in single mode and 24 in multi mode**, and installed the offline APK. Both still failed visible UI/USB acceptance and later lost framework services. The remaining SystemUI/Android hang is not resolved.

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
- [x] Repeat static backend/bundle audits and executable-memory guard tests in CI. Runtime iPhone auditing remains pending.
- [ ] Measure JIT versus No-JIT with the same image and workload.

## Validation and credits
Build 37762010302 passed iOS compilation, Swift import staging and bridge tests, target isolation and No-JIT backend/bundle audits. Successful compilation is not physical acceptance. See `docs/nojit.md` in the tagged source for evidence and limitations.

Based on [Husk by Leviidev](https://github.com/Leviidev/Husk). Original credits and GPL-2.0-or-later obligations remain in the source and Settings menu. The original JIT target is preserved; this preview uses `HUSK_NO_JIT`.
