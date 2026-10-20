# Independent hardware reproduction (v1.1)

This document is retained for compatibility with the v1.0 reproducibility release.

**v1.1 now includes an automated, nontechnical hardware runner.** Start with [HARDWARE_QUICKSTART.md](HARDWARE_QUICKSTART.md) and the `RUN_ON_IBM.bat` menu on Windows. Linux and macOS users can run `python -m hardware.ibm_runner`.

The original 16 compiled Kingston QPY files are archival **evidence of the historical job**, not portable to another backend. Fresh QPU runs are compiled from the 16 independently reconstructed QASM programs. These represent the source-derived basis-history logic and midpoint reset, but are not asserted to match the historical *physical* native-gate sequence.

Before authorizing the first job, review the generated compile report and ensure the account's quotas or costs are acceptable. The launcher never uses its own credentials or those of the original researcher. Your key is never sent to the package maintainer. IBM Quantum service receives credentials directly through the SDK.

After retrieving a completed job, publish the sanitized export and the backend/compiler versions rather than a raw provider account archive. Do not claim that a statistically positive classical history effect demonstrates quantum coherence.
