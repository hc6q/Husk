# Original low-performance option: first ARM64 result

Diagnostic commit b67f262c21e0869dba64e832cfe4a32c2ba20dee, [Actions 37571498826](https://github.com/hc6q/Husk/actions/runs/37571498826).

The multi-thread TCI trial rebooted the official snapshot machine to use the original image's low-performance boot option. Overlay preparation verified the pinned v12 SHA-256 and changed one allocated grubenv byte. The serial contains androidboot.low_perf=1 and its early-init action. It then records system_server requesting reboot,RescueParty, followed by termination of husk_agent. The test stopped at899.0s on bridge EOF; boot_completed, installation, Activity resume and touch were all false. Its final framebuffer was black. Continuous mmap/mprotect guard remained active; no post-boot maps can be claimed because boot was not reached.

The serial establishes a guest-triggered reboot, not its unique cause. The guest crash buffer was unavailable after shutdown. Timeout multiplier50 was not read back in this trial; running an init action alone does not prove the property value. The first single-thread trial was still running when these files were recorded.

[Original artifact11461652779](https://github.com/hc6q/Husk/actions/runs/37571498826/artifacts/11461652779), ZIP SHA-256 b3af48e3460ebe2ae3facd6a863a55d4c44e5b1cfdd4b2da3470217d32bf632a.

Follow-up [37577435425](https://github.com/hc6q/Husk/actions/runs/37577435425), commit d8ceb3637d37851fd1cfc15aa379754fbc93cdea, reconnects only read-only boot queries within the original deadline and captures crashes before boot. It retains genuine TCI, continuous guard and visible caption/counter0→1 requirements. It is pending, not a pass of this failure. No change from this experiment has entered the published iOS IPA.
