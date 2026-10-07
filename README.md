# Rottweiler

Rottweiler is the No-JIT variant of [Husk by Leviidev](https://github.com/Leviidev/Husk): an Android APK launcher for iOS using QEMU TCI interpretation.

The repository remains `hc6q/Husk`. Rottweiler is the app name displayed on iOS, onboarding and settings. Original source identifiers and `com.husk.nojit` remain stable so existing installs retain their Android image, settings and imported APKs.

## Status

**Experimental: a usable APK on iPhone is not yet confirmed.** The iOS IPA compiles and has opened the LineageOS setup screen on a physical iPhone using the shipped software snapshot. Bluetooth/System UI failures still block acceptance. Installation and Activity resume have been confirmed in host experiments; touch and audio remain unconfirmed.

## Build and install

`HUSK_NO_JIT=1` selects QEMU TCI, without debugger, StikJIT or pairing. The existing Android VM and ANGLE/Metal integration are retained. The [No-JIT workflow](.github/workflows/nojit.yml) publishes `Rottweiler.ipa` and an offline test APK.

See [docs/nojit.md](docs/nojit.md) for installation, exact build configuration, test evidence and limitations. The unsigned IPA requires ordinary sideload signing. For the shipped snapshot select **CPU** renderer, snapshot enabled and Sound disabled; GPU mode uses a different machine configuration and falls back to cold boot.

## Original Husk mode and attribution

The original JIT target remains available with `HUSK_NO_JIT=0`. Its original debugger/Stik requirements apply only to that target. Rottweiler preserves Husk's architecture and upstream credits; it does not claim authorship of Husk, QEMU or Android.

## Licence

GPL-2.0-or-later, inherited from Husk. QEMU and other bundled components retain their original licences. See [licensing documentation](docs/01-licensing.md). Full source for this derivative is public here.
