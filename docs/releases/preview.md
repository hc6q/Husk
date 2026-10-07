# Rottweiler No-JIT — Experimental preview

Android APK launcher for iOS arm64, based on Husk and QEMU 10.0.12-utm TCI.
This is an experimental test build, not a validated daily-use release.

## Changes
- Reversible Android performance profile: 75% linear render size, animations and touch overlays disabled, original settings saved for restoration.
- Bluetooth startup blocking now runs on the first responding guest shell, before waiting for boot completion. It verifies disabled-user state and checks that the primary Bluetooth process has stopped; snapshot restoration reapplies the block.
- Settings → Performance allows restoring the previous Android rendering settings on the next guest start.
- Independent No-JIT app version 0.8.2, build 25. The original JIT app version is unchanged.
- Runtime performance and successful iPhone APK interaction remain unverified; this is a test profile, not a measured speedup.

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
