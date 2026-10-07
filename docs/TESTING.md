# Testing Rottweiler

Rottweiler's acceptance target is **a small Android APK visibly running and responding to touch on a physical iPhone without JIT**. This has not yet been confirmed. This checklist is designed to distinguish partial progress from a successful end-to-end run.

## Prepare a reproducible test

1. Record your iPhone model, iOS version, Rottweiler commit / workflow run and installation method.
2. Install the signed `Rottweiler.ipa` built by the [No-JIT workflow](https://github.com/hc6q/Rottweiler/actions/workflows/nojit.yml?query=branch%3Amain).
3. Record which Android guest image / saved snapshot you use.
4. Start with the **CPU** renderer, snapshot enabled and sound off if using the published software snapshot.
5. Use the small offline `NoJITSmoke.apk` produced by the fixture job; do not upload third-party commercial APKs with your report.

## Acceptance checklist

- [ ] Rottweiler installs and opens on the iPhone.
- [ ] The Android guest restores or boots, without a fatal iOS crash.
- [ ] The guest reports readiness and the interface remains responsive.
- [ ] Importing the APK visibly progresses and installation succeeds.
- [ ] The test app launches and is clearly visible — not just listed as a resumed Activity.
- [ ] Pressing **Count touch** changes the displayed counter from **0** to **1**.
- [ ] The application remains usable after that first interaction.

Treat any incomplete step as **not confirmed**. A process listed in logs, an unchanged screenshot or `sys.boot_completed=1` alone is not proof of full compatibility.

## Record failures

For a useful [bug report](https://github.com/hc6q/Rottweiler/issues/new?template=bug_report.yml), attach:

| Field | Example of what to record |
| --- | --- |
| App build | Git commit, workflow run, artifact |
| iPhone | Model and exact iOS version |
| Guest configuration | Image, CPU/GPU, snapshot, sound, RAM |
| Test app | APK name, package name, version |
| Last successful step | Snapshot, installation, Activity resume, etc. |
| Failure | Error text, log excerpt, brief description or redacted screenshot |

**Privacy:** remove Apple IDs, device UUIDs, signing identities, tokens, paths containing personal names, network credentials and private APK contents before sharing.

## Where to look

- [Historical No-JIT evidence](nojit.md)
- [GitHub Actions builds](https://github.com/hc6q/Rottweiler/actions/workflows/nojit.yml)
- [Contributing guidance](../CONTRIBUTING.md)

Audio, cold-boot speed and GPU renderer behavior are separate tests. Do not merge their outcomes into the core APK-and-touch acceptance result.
