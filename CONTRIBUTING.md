# Contributing to Rottweiler

Thanks for helping with Rottweiler. This is an **experimental No-JIT fork** of [Husk](https://github.com/Leviidev/Husk), not a finished Android compatibility layer.

## Before opening a change

- Read the [README](README.md) for scope and current limitations and [docs/nojit.md](docs/nojit.md) for test evidence.
- Search existing [issues](https://github.com/hc6q/Rottweiler/issues) and [pull requests](https://github.com/hc6q/Rottweiler/pulls) for related work.
- Prefer one focused change per PR. Describe the failure it addresses and the exact reproduction steps.
- If you are investigating a guest crash, share **redacted logs** rather than APKs, entire device dumps, signing files or private user data.

## What to include in a bug report

- Exact commit or workflow run and IPA artifact name
- Device model, iOS version and installation/signing method
- Renderer, snapshot, sound and any custom resolution settings
- Android image or snapshot version and the APK's package name
- Expected result, observed result and whether the screen actually changed
- Relevant, short logs with sensitive information removed

Use the [bug report form](https://github.com/hc6q/Rottweiler/issues/new?template=bug_report.yml) or follow [the test checklist](docs/TESTING.md).

## Development

The No-JIT build is selected with `HUSK_NO_JIT=1`. The original JIT build must remain intact.

To build on macOS arm64:

```sh
brew install meson ninja pkg-config xcodegen qemu autoconf automake libtool
python3 -m venv build/ci-python
. build/ci-python/bin/activate
pip install PyYAML
HUSK_NO_JIT=1 ./scripts/ci_build.sh "$PWD/build/Rottweiler.ipa"
```

Useful repository checks:

```sh
python3 tests/nojit/test_build_contract.py
python3 tests/nojit/test_memory_guard.py
```

The first check generates the No-JIT Xcode project and requires PyYAML. CI also compiles `GuestShellFrame.swift` with its test harness, builds the IPA and builds the offline APK fixture. **Passing CI is not evidence of a usable Android app on a physical iPhone.**

## No-JIT invariants

Changes to the interpreter target must not silently introduce:

- native JIT code generation, runtime W+X mappings or executable translation buffers;
- JIT debugger attachment, StikJIT/StikDebug activation or JIT pairing requirements;
- changes that break the original Husk/JIT build configuration.

Document the exact test backend (TCI or otherwise), not just the name of the IPA.

## Pull request checklist

- Explain the change and why it is needed.
- Link the relevant issue and provide before/after evidence when possible.
- List commands and environments you actually tested. Mark everything else **not tested**.
- Keep third-party credits and license notices intact; do not commit generated IPAs or guest images.
- Avoid unrelated formatting or broad renames of compatibility-sensitive `husk.*` keys.

For project status and supported claims, the [validation record](docs/nojit.md) takes precedence over impressions from a splash screen or an emulator log.
