# Framed bridge + Bluetooth package isolation

[Run 37568981358](https://github.com/hc6q/Husk/actions/runs/37568981358), commit `2316cd9659ef165cf5b283408d055adf13c442ea`.

The multi-thread TCI trial confirmed radio settings, `pm disable-user --user 0 com.android.bluetooth`, and `am force-stop`. It still displayed the Bluetooth crash dialog. Boot property was confirmed at 18.4 s, APK installed and Activity resumed, USB counter not confirmed. The mmap guard remained active; maps after boot and APK resume contain no W+X or anonymous executable regions. The trial failed at 315.1 s (340.8s including diagnostics).

The single-thread trial installed the APK, then the settings service returned `Broken pipe (32)` while finishing guest provisioning. Activity resume and touch were not confirmed. Its original artifact is 11460696020. No package-isolation change was adopted in the IPA.

[Original multi artifact](https://github.com/hc6q/Husk/actions/runs/37568981358/artifacts/11459589041), ZIP SHA-256 `da3b61c945b6f023c32bbf60aa2ff52582a1c7b6b4e5ee14500a0bd3c9e6596b`.
[Original single artifact](https://github.com/hc6q/Husk/actions/runs/37568981358/artifacts/11460696020), ZIP SHA-256 `4f626e187382a66cf935eb455f7d128e8096746959bc874cac0ec9dbb5b29932`.

The framebuffer experiment initially exhausted its recovery-click budget before its 300 s observation deadline. Commit `5347afe` corrects that: no more than three recovery clicks, but continued observation of fresh frames until deadline. A visible fixture caption and counter 0→1 remain mandatory. [Follow-up 37569832046](https://github.com/hc6q/Husk/actions/runs/37569832046) is a separate test, not a retroactive pass of this failure.
