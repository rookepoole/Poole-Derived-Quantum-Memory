# Public data dictionary and chain of custody

`data/sanitized_ibm_9bit_counts.json` is a **lossless per-PUB histogram** derived from original IBM job `dbaoflpgv2cc73e75v10` and retains all 9 measured bits. Keys are nine-character binary strings representing measured classical register `c8...c0`. Values are numbers of shots; each PUB totals 1024. Unlike the raw job archive, the public JSON does not contain IBM account metadata, the provider's serialized result objects, per-shot ordering, or any user token. Histogramming loses shot order but not any register's joint measurement frequency.

`pub` is the historical position within the list submitted to IBM. `abc` is the prepared 3-bit input in `a,b,c` order, and `arm` is `retain` or `erase`. The original IBM export did not include those labels, so their association relies on archived submission order and a majority-input-register consistency check. It should not be treated as provider-authenticated experimental labels.

`data/sanitized_provenance.json` records the job ID, backend, creation time, original ZIP hash, the reason the private raw archive is excluded, and the extracted **original QPY** file lengths and checksums. The QPY files were taken directly from the original provider submission program. They were byte-compared against an independently retained copy from the earlier audit package. QPY format version 17 is recorded; no Qiskit parser inspection was completed here.

`data/verified_off_sector_counterexamples.json` was produced by an earlier independent full-lattice source audit. It is included so researchers can reproduce or challenge the restricted-oracle limitation instead of assuming an arbitrary-input equivalence.

`source/reconstructed_dark_pair_t250.npz` contains two `(250,250,10)` NumPy `uint8` arrays named `A` and `B`. The v2.4 source verification uses **A**. The B array is kept to preserve provenance from the reconstructed dark-pair study and is not substituted silently. The original older snapshot is absent and cannot be byte-compared; full historical regeneration scripts are included separately.

`results/verified_summary.json` and `results/per_pub.csv` are generated artifacts from running `python reproduce.py`. Their content can be recalculated without any scientific software package.

## v1.1 independent hardware exports

The `public_exports/Poole_V207_independent_replication_*.zip` artifact contains:

- `manifest.json`: randomized mapping of each of the 16 QASM conditions to its IBM PUB index; source SHA-256, compiler seed, backend, shots, native compilation counts, and checksummed QPY digest. No API key or instance CRN.
- `sanitized_counts.json`: one 9-bit histogram per submitted PUB, including every returned shot; `c8...c0` classical order.
- `analysis.json`: four groups, retained/erased contrasts, controlled difference-in-differences and shot-only confidence interval.
- `per_condition.csv`: per-PUB center counts and the source-predicted Boolean center bit.
- `compiled_isa.qpy`: frozen native-gate circuits submitted on that particular IBM backend, for independent gate/measurement-map inspection.
- `public_job_reference.json`: backend and job ID (if the researcher elects to share the export).

The tool refuses to infer missing results or to silently replace shuffled PUB order with the original historical ordering. The `private_runs` folder contains the local compiled circuits and job receipt and is ignored by Git. Do not publish an IBM account's provider-native raw ZIP without checking its metadata.
