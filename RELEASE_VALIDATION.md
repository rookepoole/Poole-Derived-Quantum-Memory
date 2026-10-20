# Poole V207 public reproduction v1.1 — release validation

**Release date:** 20 October 2026  
**Source:** original v1.0 public release and historical IBM v2.4 experiment

## Offline validation

- Historical IBM sanitized histograms (16 x 1024 shots) reproduce **15,272/16,384** correct center bits and **64.55078125 percentage points** in retained-minus-erased DID, with shot-only normal 95% CI **62.6983–66.4033** percentage points.
- All original 16 QASM source hashes and 16 authentic original provider QPY hashes are retained and validated; all original reconstructed QASM programs are byte-for-byte unchanged.
- Credential-free gate interpreter checks all 16 reconstructed Boolean circuits, including the intermediate center reset and erasure controls.
- Hardware release unit tests use a simulated IBM service and QPY round-trip to verify compile-only, backend selection, shot count, randomized order, explicit confirmation, QPY hash tampering rejection, duplicate-job protection, nonblocking queued-job retrieval, no-postselection decoding, statistical analysis and sanitized exports.
- Tests exercise a full 16-circuit fake IBM job through compile, submit, retrieval and result export. **These are MOCKED tests, not live quantum hardware results.**
- All public zip contents exclude API keys, Qiskit saved account files, instance CRNs and the private historical provider ZIP. `private_runs/`, `.venv/` and `public_exports/` are ignored by Git.

## Required live verification by independent users

The release environment has **no connected IBM Quantum service or installed Qiskit Runtime SDK**. Independent researchers must run `RUN_LOCAL_QISKIT_CHECK.bat`, then compile-only against a backend they can access and explicitly authorize their own hardware job. This release is designed for the IBM v0.50 client-side Sampler; provider API compatibility on a specific processor is a testable preflight, not a guarantee.

## Scientific scope

Positive reported contrast is an **engineered two-generation computational-basis memory effect** in a V207-derived causal-cone circuit, not proof of spontaneously generated quantum coherence, a universal simulation of the V207 automaton, or intrinsic non-Markovian hardware noise. The v2.4 reconstructed QASM files are not asserted to be byte-for-byte the hardware-executed QPY circuits. The second-generation Boolean shortcut is valid only for the selected reachable states.

## Source-available licensing edition (v1.1.1)

- Adopted the original Poole Manifold `LICENSE` text; included `LICENSE_SCOPE.md` and updated publication guidance.
- All 16 reconstructed source QASM files, 16 historical original QPY records, sanitized counts, source snapshots and executable reproduction/IBM runner scripts are **byte-for-byte unchanged** from v1.1.0.
- Release checksum manifest was regenerated, including the new license materials.
- This release does **not** change the IBM benchmark methods or independently validate live IBM availability.
