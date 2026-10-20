# Public release checklist

This archive is a prepared **downloadable scientific release**. It is **not yet hosted** on GitHub, Zenodo, arXiv, or any external service.

- [ ] Review `README.md` and `METHODS_AND_SCOPE.md`; keep the interpretation limited to the original v2.4 computational-basis experiment.
- [ ] Run `python reproduce.py` and `python -m unittest discover -s tests -v` after extracting the release.
- [ ] In a local Qiskit environment, run `python scripts/verify_qpy_optional.py` and retain its inspection report; update the methods if the actual compiled circuit structure differs from the reconstruction.
- [ ] Review every included binary and manifest for metadata you do not want public. The original private IBM ZIP is deliberately **not** redistributed.
- [x] Include `LICENSE` and `LICENSE_SCOPE.md` using the original Poole Manifold source-available research terms. **This is not open source.** [ ] Author should approve the license and permissions before publication; corporate researchers must request separate written permission.
- [ ] Read `HARDWARE_QUICKSTART.md` and test `RUN_ON_IBM.bat` / Linux CLI on an IBM account before advertising live hardware compatibility. The package has no actual IBM job submission verification in this environment.
- [ ] Confirm the API-key dialog and instance flow function on Windows, and compile-only passes on at least one accessible backend. No source-level v2.4 experiment circuits may be replaced by mock circuits.
- [ ] Upload the release as source plus a tagged ZIP on a repository you control. Add the original source pinned commit link and the SHA256SUMS file.
- [ ] Optionally create a DOI archive and update `CITATION.cff` with the real deposit URL/DOI (do not invent one).
- [ ] If the public manuscript is updated, do not merge v2.4's 93.21% computational-basis accuracy with v2.5's Bell fidelity or later 24-generation coherent test; these are different experiments.

Suggested GitHub release title: **Poole V207 Two-Generation Causal Cone — v1.1 Own-Account IBM Replication Toolkit**.
