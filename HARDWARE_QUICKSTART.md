# Independent IBM Quantum hardware replication — easy path

**Poole V207 two-generation public release v1.1.1** · Windows 11, Linux, macOS · Python 3.10 or newer

This is **the original 16-condition, computational-basis two-generation causal-cone experiment**, not the later 16/24-generation *coherent Bell* benchmark. A fresh run uses the 16 readable **reconstructed** QASM circuits and compiles them for the researcher's own accessible IBM Quantum processor. The 16 original Kingston QPY binaries remain archival reference material; they are **not** blindly reused on other processors.

**License:** This package is **source-available, not open-source**. Running the experiments for personal or academic research is permitted under [`LICENSE`](LICENSE); a commercial-lab replication or redistributed software requires written permission. See [`LICENSE_SCOPE.md`](LICENSE_SCOPE.md).

## Windows (no code edits required)

1. Unzip into a new folder. Install Python 3.10+ if necessary, with the Windows Python launcher (`py`) available.
2. Double-click **`RUN_OFFLINE_REPRODUCTION.bat`** to verify the published counts; this uses no account or hardware time. `RUN_HARDWARE_FREE_TESTS.bat` checks the new launcher logic without any IBM access.
3. Double-click **`SETUP_IBM_WINDOWS.bat`** once. This installs Qiskit into a local `.venv` folder, not the global Python environment. Network access is needed for the one-time installation.
4. Optionally run `RUN_LOCAL_QISKIT_CHECK.bat` to confirm the 16 readable QASM circuits parse with Qiskit. Then double-click **`RUN_ON_IBM.bat`**. Choose **paste your own IBM Quantum API key** (secure masked popup) or **saved Qiskit account**. An optional IBM instance CRN can be supplied; leave blank for automatic instance selection. The launcher **never saves API keys**.
5. Choose **List backends** and then **Compile 16 circuits only**. Pick an accessible processor, with at least nine qubits and mid-circuit resets. Compile-only does not request QPU execution. Inspect the saved `private_runs/v24_.../compile_plan.json` and SHA-256 checked `compiled_isa.qpy`.
6. Select **Submit existing frozen compile plan**. Review backend, shot count (default 16 x 1024 = 16,384), and any cost/allocation. Only typing **`SUBMIT 16`** requests a new IBM job.
7. If queued, leave the job alone. Later choose **Retrieve existing IBM job** for the same run folder. Retrieval never resubmits. When complete, a statistical report and full sanitized 9-bit counts are generated automatically.
8. Choose **Export a sanitized shareable result ZIP**. Share *that* ZIP with the research community, rather than credentials, raw IBM account exports or your entire `private_runs` folder. The export includes the submitted compiled QPY circuit file, its hash, and the complete result mapping.

If a submission request throws a timeout, check your IBM Quantum Workloads page for a queued job ID before retrying. The launcher writes `submission_intent.json` before requesting the job to prevent accidental double charges.

## Linux / macOS (or manual Windows command line)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-hardware.txt
python -m unittest discover -s tests -v
python -m hardware.ibm_runner list
python -m hardware.ibm_runner compile --backend YOUR_ACCESSIBLE_BACKEND
# Review the run directory printed by compile.
python -m hardware.ibm_runner submit --run-dir private_runs/v24_YOUR_RUN_FOLDER
# Type exactly SUBMIT 16 to authorize IBM QPU allocation.
python -m hardware.ibm_runner retrieve --run-dir private_runs/v24_YOUR_RUN_FOLDER
python -m hardware.ibm_runner analyze --run-dir private_runs/v24_YOUR_RUN_FOLDER
python -m hardware.ibm_runner export --run-dir private_runs/v24_YOUR_RUN_FOLDER
```

You can add `--auth saved` to `list`, `compile`, `submit`, or `retrieve` if you have previously configured credentials with Qiskit. Interactive prompt mode never calls `QiskitRuntimeService.save_account()`. For accounts with several IBM service instances, set `IBM_QUANTUM_INSTANCE` to your chosen IBM Cloud instance CRN, or supply it to the prompt at login. Choose `instance` that you are authorized to use; costs and quotas are account-specific.

## Critical reproducibility checks

- **16 distinct input/arm conditions:** eight `abc` histories, each with neighboring memory retained or erased. No control can be omitted from a replication.
- **Exact source:** SHA-256 checks against the v1.0 reconstructed QASM; a changed source file aborts preflight. Compilation targets the selected backend and uses a fixed random seed, explicitly saved PUB ordering, and no approximate synthesis.
- **Intermediate state:** the system/center qubit is reset after generation one. The erased arm additionally resets four neighboring-memory qubits. A backend must support mid-circuit reset; compile verifies all required resets and all 9 final classical measurements remain.
- **ISA/QPY:** the compiled circuits are saved as a frozen QPY with checksum *before submission*. Submission reads that file; no silent recompilation or change to circuit order is allowed.
- **Shots:** default 1,024 per circuit, 16,384 overall. The analyzer rejects missing PUBs, unexpected order, and shot-count mismatches. **Every measured shot is counted**; no conditioning on input-register correctness.
- **Metric:** center `c4=1` by arm and middle input `b`, with `DID=(retain b1−retain b0)−(erase b1−erase b0)` and independent-shot normal 95% confidence interval. Original `ibm_kingston` result DID **64.55 percentage points**, 95% shot-only CI **62.70–66.40**.
- **Interpreting results:** a positive replicated DID is programmed **classical/computational-basis history dependence**, not spontaneous coherence, intrinsic quantum non-Markovianity, or Poole-specific quantum advantage.

## What software is installed?

`requirements-hardware.txt` requests Qiskit 2.5+ and IBM Runtime 0.50.x (current at release). On v0.50+ the new client-side `Sampler` is preferred; the legacy `SamplerV2` import is supported as a fallback. Installation and live IBM service access have **not** been tested in the packaging environment. If IBM changes its API, raise a GitHub issue describing versions and error text **without any API key, CRN, or account ID**.

## No automatic hardware spend

`RUN_OFFLINE_REPRODUCTION.bat`, `RUN_HARDWARE_FREE_TESTS.bat`, and `RUN_COMPILE_ONLY_IBM.bat` never submit jobs. Only the explicit submit path can invoke Sampler `run()`. Job retrieval reuses the stored job ID and **cannot schedule new circuits**.

### IBM documentation

- [Initialize IBM account and API key](https://quantum.cloud.ibm.com/docs/en/guides/initialize-account)
- [Sampler quickstart](https://quantum.cloud.ibm.com/docs/en/guides/get-started-with-sampler)
- [Compile with preset pass managers](https://quantum.cloud.ibm.com/docs/en/guides/transpile-with-pass-managers)
- [Sampler input/output](https://quantum.cloud.ibm.com/docs/en/guides/sampler-input-output)
