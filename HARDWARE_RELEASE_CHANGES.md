# v1.1 release notes

**Added:**

- Own-account IBM Cloud authentication (paste-friendly masked popup on Windows, or existing locally saved account). No key persistence by the replication code.
- Backend discovery for operational 9+-qubit reset-capable QPUs.
- Compiles all 16 frozen logical cases and stores a checksummed native QPY and randomized manifest.
- Requires explicit `SUBMIT 16` confirmation before calling IBM Sampler.
- Protects against accidental duplicate submission by writing intent before issuing request.
- Retrieves jobs by existing ID without resubmitting; safely handles QUEUED status.
- Full-shot 9-bit counts, central-bit analysis, comparison with original DID, sanitized public export.
- Automated Qiskit-free tests for backend compilation, authorization, QPY corruption, result ordering, statistical analysis and privacy.
- One-click Windows setup and workflow, plus Linux/macOS CLI.

**Not changed:** 16 historical original QPY files, 16 source-level reconstructed QASM files, 9-bit original measurement histograms, V207 source verification, ideal hypothesis or statistical formulas.

**Important limitations:** Native IBM transpilation and live hardware submission must be validated by each researcher on their own backend. This release has been tested offline with a mocked IBM service, not on a live QPU. It does not certify the historical QPY gate mapping independently. It does not create quantum coherence from the classical V207 rule.
