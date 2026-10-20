# Methods, causal interpretation and reporting limits

## Source automaton

The source is a **classical**, noninvertible, masked 3D cellular automaton (Poole V207), with a 26-cell Moore neighborhood on a periodic `250×250×10` lattice. An inhibitor shifts effective neighbor potential by `−15`, threshold geometry by `−2`, and amplifier geometry by `+1`; the specific mask placement is reproduced in `source/reconstruct.py`.

The V207 update applies a prime-selective term:

```
N_eff = N_neighbors + spatial_mask_adjustment
Phi   = N_eff + 0.35 * sum(exp(-(N_eff - p)^2/0.01) for p in [2,3,5,7,11,13,17,19,23])
birth if 5 <= Phi <= 7; survive if 5 <= Phi <= 9
```

For the integer effective potentials in this reproduced source sector, the rule is exactly **B5–6 / S5–9**. This equivalence has been checked for integer effective counts from −20 through 29. It is not a claim about arbitrary noninteger potentials.

Source anchor: initial three variable cells `(172,108,3)`, `(173,108,3)`, `(174,108,3)`, in `(y,x,z)` order, on the *A* state in `source/reconstructed_dark_pair_t250.npz`. Their prepared values are the eight binary triples `abc`. The five first-generation varying sites are:

```
r0 -> (172,108,3)
r1 -> (173,108,3)    <- intermediate central system bit
r2 -> (173,108,4)
r3 -> (173,109,3)
r4 -> (174,108,3)
```

## Nine-qubit circuit

The independent source check gives the restricted first step:

```
F1(a,b,c) = (b, a AND c, NOR(a,b,c), NOR(a,b,c), b)
            (r0, r1,     r2,             r3,          r4)
```

Logical reconstruction register mapping:

| Qubit | Role |
|---|---|
| q0, q1, q2 | Prepared input bits a, b, c; preserved but not read for later logic |
| q3 | First-generation r0 = b |
| q4 | First-generation r1 = a∧c; physically reset at midpoint and subsequently used as final observed center |
| q5 | First-generation r2 = NOR(a,b,c) |
| q6 | First-generation r3 = NOR(a,b,c) |
| q7 | First-generation r4 = b |
| q8 | Scratch for reversible NOR construction, uncomputed to 0 |

The **midpoint system break** is a `reset q[4]`. The retained arm leaves q3, q5, q6, q7 intact. The erased arm additionally resets those four neighbor registers. The second restricted center update is implemented with `cx q3,q4; cx q5,q4; ccx q3,q5,q4`, because `x XOR y XOR (x AND y) = x OR y` when the target starts at 0.

The final center bit is `r0 OR r2` for the eight reachable intermediate patterns. **This optimized expression is not the general V207 neighborhood update.** Tests on 16 unrestricted four-neighbor assignments found four discrepancies per tested surrounding context (backgrounds `000`, `011`, `111`). The off-sector counterexamples are in the JSON release data. Importantly, the *complete erasure of all four specified neighbors* is one of the explicitly validated controls and produces center OFF under the full V207 update.

| Initial abc | F1 r0…r4 | Ideal retained center | Ideal erased center |
|:--:|:--:|--:|--:|
| 000 | 00110 | 1 | 0 |
| 001 | 00000 | 0 | 0 |
| 010 | 10001 | 1 | 0 |
| 011 | 10001 | 1 | 0 |
| 100 | 00000 | 0 | 0 |
| 101 | 01000 | 0 | 0 |
| 110 | 10001 | 1 | 0 |
| 111 | 11001 | 1 | 0 |

Only `101` and `111` have first-generation center q4 initially ON before the nontrivial reset. The remaining histories still test the complete retained-vs-erased comparison.

## IBM experiment and decoding

Original completed job: `dbaoflpgv2cc73e75v10`, IBM `ibm_kingston`, UTC 19 Oct 2026 03:00:39, 16 SamplerV2 circuits × 1024 shots. The IBM export includes all nine classical readout bits in the register `c` for each circuit, in standard `c8...c0` bitstring convention. The last five bits are `c4c3c2c1c0`; the central output is `c4` and the preparation is measured as `c0`, `c1`, `c2` in `a,b,c` order.

The original PUB order was randomized and is recorded as independent historical metadata in `reproduce.py`. The raw provider archive did not embed descriptive circuit labels, so assignment to `abc` and retained/erased arm relies on the archived submission order. Each assigned input also matches the most-frequent measured `c0:c2` preparation triple (16/16); this is a consistency check, not cryptographic proof of arm identity. The exact original compiled circuit QPY binaries are bundled for independent inspection.

For each group (`retain/erase` × `b=0/1`), sum center ON over four 1024-shot circuits. Define:

```
Delta_retain = p(center=1 | retain, b=1) - p(center=1 | retain, b=0)
Delta_erase  = p(center=1 | erase, b=1)  - p(center=1 | erase, b=0)
DID = Delta_retain - Delta_erase
```

Observed four groups:

| Group | Center ON / 4096 | ON proportion |
|---|---:|---:|
| Retain, b=0 | 1143 | 0.279053 |
| Retain, b=1 | 3846 | 0.938965 |
| Erase, b=0 | 204 | 0.049805 |
| Erase, b=1 | 263 | 0.064209 |

Thus `DID = 0.6455078125` versus ideal `0.75`. Final-bit correctness is `15,272/16,384` (93.21%). Measured preparation-register agreement is `12,896/16,384` (78.71%). A small history contrast persists after erasure (1.44 percentage points), consistent with residual physical imperfections; its precise cause was not determined in this experiment.

For the quoted normal-approximation 95% **shot-only** CI, independently treat all four group rates as binomial proportions, with

```
SE(DID) = sqrt( sum_over_four_groups( p*(1-p)/N ) )
CI      = DID +/- 1.96*SE
```

This gives `[0.6269827871, 0.6640328379]`. It is **not** a drift-robust interval and does not account for correlated readout, reset errors, SPAM, job-to-job variability, or full quantum process uncertainty.

## Evidence status (do not conflate)

| Statement | Evidence |
|---|---|
| Full V207 lattice yields stated Boolean F1 and restricted center F2 for 8 histories in reconstructed A | Direct 625,000-cell classical computation (optional source test) |
| Human-readable 9-qubit QASM achieves those 16 retained/erased ideal predictions | Pure Python interpreter test in this package |
| Original IBM hardware produces the reported 16,384-shot effect | Sanitized complete 9-bit IBM measurement histograms and independent decoder |
| Exact compiled circuits from original IBM submission are preserved | All 16 provider QPY binaries and their SHA-256 fingerprints |
| Original compiled QPY gate ordering was fully disassembled in this packaging session | **No**; local Qiskit optional check supplied |
| The compact F2 function correctly implements V207 for arbitrary intermediate patterns | **No**; counterexamples provided |
| This demonstrates native quantum coherence storage or device-intrinsic non-Markovianity | **No**; this experiment is a programmed classical-basis memory witness |
| This is the full 625,000-site automaton executing on IBM | **No**; the QPU executes a reduced 9-qubit circuit |

For phase-coherent **quantum** information transfer, see the *separate* v2.5 experiment. Its Bell-fidelity observable and circuit are not included or silently merged into this v2.4 release.
