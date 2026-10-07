# Android radio and input diagnostics — 2026-10-07

Source: [run 37567494260](https://github.com/hc6q/Husk/actions/runs/37567494260), commit `093ea7aa3bcff22fc7219e966d283ed33f731218`. Both runs use the exact UTM 10.0.12 TCI backend, original v12 Android disk and official software snapshot, four vCPUs and 4096 MiB file-backed RAM. The mmap/mprotect guard remains active throughout QEMU execution. Original artifacts contain maps after boot and APK resume, serial, actual framebuffer captures, OCR, crash and input diagnostics.

| Threads | Boot property confirmed | Installed | Resumed | USB counter 0→1 | Acceptance |
|---|---:|---:|---:|---:|---|
| single | 33.9 s | yes | yes | no | failed |
| multi | 18.2 s | yes | yes | no | failed |

These boot times measure snapshot restoration, not cold boot or iPhone speed. The APK SHA-256 is `9343927b9eecc7072c834bbffe7fed535741d26e9748d5830ce8d6812b97765b`. It is the Java offline software-rendered fixture. `bluetooth_on=0` and `svc bluetooth disable` were confirmed before installation; neither removed the platform dialogs sufficiently to pass the visible-app and USB counter test.

The input excerpt establishes that USB events reached the guest at the captured coordinates. Android's InputDispatcher timed out delivering to the application-error window owned by system_server. This does not prove that the fixture received input, and does not identify every reason for system_server starvation. Bluetooth crash backtraces include HCI initialization through Binder; no missing-HAL or QEMU correctness conclusion is asserted from those frames alone. Older crash-buffer entries predate snapshot restoration and must not be counted as new failures.

Original artifacts:
- [single](https://github.com/hc6q/Husk/actions/runs/37567494260/artifacts/11460136072), ZIP SHA-256 `02951313e36e0cb058653fee61d248e4d1f547dcb10e770adcb28071513cdf73`.
- [multi](https://github.com/hc6q/Husk/actions/runs/37567494260/artifacts/11459607164), ZIP SHA-256 `96f95b008320e1eededab777d46f0efe4528c64e2ec08a91152bdb6ed0b5929c`.

No iOS signing, iPhone touch or audio certification follows from these Linux tests.
