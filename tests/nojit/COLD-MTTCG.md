# Cold boot MTTCG experiment

Uses the original v12 base image, a fresh 4 GiB userdata disk, four vCPUs and
2048 MiB RAM. No snapshot, instruction clock, or Bluetooth package disable.
The TCI mmap/mprotect guard remains mandatory. A slow boot bridge retries
within the existing boot deadline instead of classifying one timeout as boot
failure. No property is changed to simulate Android readiness.

Acceptance still requires boot_completed=1, installation, resumed Activity,
raw framebuffer counter changing from 0 to 1 via USB HID. Actual WAV output is
recorded for the original sound device; iPhone/Metal/AudioUnit remain untested.
This workflow is an experiment and does not alter the published IPA.
