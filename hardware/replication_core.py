"""Credential-free helpers: immutable source provenance and full-shot IBM comparisons.

There is intentionally no dependency on Qiskit/NumPy, IBM account, or network.
"""
from __future__ import annotations
import csv
import hashlib
import json
import math
import random
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / 'hardware' / 'source_hashes.json'
QASM_DIR = ROOT / 'circuits' / 'reconstructed_qasm'
HISTORICAL_JOB = 'dbaoflpgv2cc73e75v10'
HISTORICAL_DID = 0.6455078125


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def to_json_bytes(data: Any) -> bytes:
    return (json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True) + '\n').encode('utf-8')


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(to_json_bytes(data))  # canonical LF independent of OS


def source_conditions():
    """Return immutable, independently checked 8 x 2 historical test inputs."""
    expected = json.loads(REFERENCE.read_text(encoding='utf-8'))
    conditions = []
    for i in range(8):
        abc = f'{i:03b}'
        for arm in ('retained', 'erased'):
            filename = f'v24_{abc}_{arm}.qasm'
            raw = (QASM_DIR / filename).read_bytes()
            if digest(raw) != expected.get(filename):
                raise ValueError('QASM integrity failure: ' + filename)
            if b'\r' in raw:
                raise ValueError('QASM has unexpected Windows carriage return: ' + filename)
            conditions.append({'condition': filename.removesuffix('.qasm'),
                               'filename': filename, 'abc': abc, 'arm': arm,
                               'qasm_sha256': digest(raw)})
    if len(conditions) != 16 or len(expected) != 16:
        raise ValueError('Unexpected source inventory')
    return conditions


def create_manifest(backend_name: str, shots: int = 1024, seed: int = 20261020,
                    optimization: int = 1) -> dict:
    if not backend_name or not isinstance(backend_name, str):
        raise ValueError('Backend name is required')
    if not 128 <= shots <= 100000:
        raise ValueError('Shots must be between 128 and 100,000')
    if optimization not in (0, 1, 2, 3):
        raise ValueError('Optimization must be 0, 1, 2, or 3')
    conditions = source_conditions()
    random.Random(seed).shuffle(conditions)
    manifest = {
        'schema': 'poole-v207-v24-ibm-replication-manifest-1',
        'experiment': 'Reconstructed two-generation V207 computational-basis causal cone',
        'original_ibm_job': HISTORICAL_JOB,
        'circuit_provenance': 'v1.0 reconstructed source-level QASM, NOT original Kingston QPY',
        'backend': backend_name,
        'randomization_seed': seed,
        'optimization_level': optimization,
        'shots_per_circuit': shots,
        'expected_total_shots': 16 * shots,
        'bitstring_order': 'c8..c0; q4/c4 final center; q0..q2/c0..c2 unconditioned inputs',
        'mitigation': {'dynamical_decoupling': False,
                       'gate_twirling': False, 'measurement_twirling': False},
        'assignments': [{'pub': i, **desc} for i, desc in enumerate(conditions)],
    }
    return manifest


def validate_manifest(manifest: dict) -> None:
    if manifest.get('schema') != 'poole-v207-v24-ibm-replication-manifest-1':
        raise ValueError('Manifest schema mismatch')
    if len(manifest.get('assignments', [])) != 16:
        raise ValueError('Manifest must have all 16 circuits')
    if manifest.get('expected_total_shots') != 16 * manifest['shots_per_circuit']:
        raise ValueError('Shot totals do not reconcile')
    by_name = {x['condition']: x for x in source_conditions()}
    seen = set()
    for pub, entry in enumerate(manifest['assignments']):
        key = entry['condition']
        if entry['pub'] != pub or key not in by_name or key in seen:
            raise ValueError('Manifest order or condition mismatch')
        seen.add(key)
        for k in ('abc', 'arm', 'filename', 'qasm_sha256'):
            if entry[k] != by_name[key][k]:
                raise ValueError('Manifest source mismatch at ' + key)
    # Prevent relaxing experimental options after compilation.
    if manifest.get('mitigation') != {'dynamical_decoupling': False,
                                    'gate_twirling': False,
                                    'measurement_twirling': False}:
        raise ValueError('Unexpected mitigation setting')


def normalize_counts(raw_counts: dict, nbits: int = 9) -> dict[str, int]:
    if not isinstance(raw_counts, dict) or not raw_counts:
        raise ValueError('Counts must be a nonempty mapping')
    clean = {}
    for key, count in raw_counts.items():
        if not isinstance(key, str):
            raise ValueError('Non-string bitstring')
        bits = key.replace(' ', '')
        if not bits or len(bits) > nbits or any(x not in '01' for x in bits):
            raise ValueError('Invalid bitstring ' + repr(key))
        if type(count) is not int or count <= 0:
            raise ValueError('Invalid shot count')
        bits = bits.zfill(nbits)
        clean[bits] = clean.get(bits, 0) + count
    return dict(sorted(clean.items()))


def validate_data(manifest: dict, pubs: list) -> None:
    validate_manifest(manifest)
    if len(pubs) != 16:
        raise ValueError('Results must have exactly 16 PUBs')
    for i, (assignment, record) in enumerate(zip(manifest['assignments'], pubs)):
        if record.get('pub') != i or record.get('condition') != assignment['condition']:
            raise ValueError('Result order mismatch; refusing to guess')
        counts = normalize_counts(record['counts'])
        if sum(counts.values()) != manifest['shots_per_circuit']:
            raise ValueError('Invalid number of shots in PUB ' + str(i))


def analyze(manifest: dict, pubs: list) -> tuple[dict, list[dict]]:
    """Analyze ALL sampled shots; never postselect by measured prepared bits."""
    validate_data(manifest, pubs)
    from reproduce import expected_center
    rows = []
    for assignment, record in zip(manifest['assignments'], pubs):
        counts = normalize_counts(record['counts'])
        shots = sum(counts.values())
        on = sum(n for bitstring, n in counts.items() if (int(bitstring, 2) >> 4) & 1)
        abc, arm = assignment['abc'], assignment['arm']
        ideal = expected_center(abc, 'retain' if arm == 'retained' else 'erase')
        rows.append({'pub': assignment['pub'], 'condition': assignment['condition'],
                     'abc': abc, 'arm': arm, 'middle_b': int(abc[1]),
                     'shots': shots, 'center_on': on, 'center_off': shots - on,
                     'p_on': on / shots, 'ideal_center': ideal,
                     'correct_center': on if ideal else shots - on})
    groups = {}
    for arm in ('retained', 'erased'):
        for middle in (0, 1):
            subset = [r for r in rows if r['arm'] == arm and r['middle_b'] == middle]
            if len(subset) != 4: raise ValueError('Invalid group composition')
            n = sum(r['shots'] for r in subset)
            on = sum(r['center_on'] for r in subset)
            groups[f'{arm}_b{middle}'] = {'on': on, 'shots': n, 'p_on': on/n}
    p = lambda arm,b: groups[f'{arm}_b{b}']['p_on']
    retained = p('retained', 1) - p('retained', 0)
    erased = p('erased', 1) - p('erased', 0)
    did = retained - erased
    se = math.sqrt(sum(g['p_on'] * (1-g['p_on']) / g['shots'] for g in groups.values()))
    lower, upper = did - 1.96 * se, did + 1.96 * se
    result = {'schema': 'poole-v207-v24-ibm-replication-result-1',
              'backend': manifest['backend'],
              'experiment': manifest['experiment'],
              'shots': sum(r['shots'] for r in rows), 'conditions': 16,
              'groups': groups,
              'retained_contrast': retained,
              'erased_contrast': erased,
              'difference_in_differences': did,
              'shot_only_95pct_normal_ci': [lower, upper],
              'standard_error': se,
              'center_accuracy': sum(r['correct_center'] for r in rows) / sum(r['shots'] for r in rows),
              'historical_difference_in_differences': HISTORICAL_DID,
              'positive_history_effect_shot_only': lower > 0,
              'historical_point_in_new_ci': lower <= HISTORICAL_DID <= upper,
              'shot_only_qualifier': 'Normal independent-shot approximation, not a hardware systematics uncertainty interval; no error mitigation or postselection.',
              'science_qualifier': 'Engineered computational-basis history dependence in a restricted V207-derived logic circuit; not intrinsic quantum non-Markovianity or quantum-coherent memory.',
              'interpretation': 'positive_history_effect tests a directional witness, NOT device parity or an equivalence/noninferiority test.'}
    return result, rows


def write_analysis(run_dir: Path, manifest: dict, pubs: list) -> dict:
    summary, rows = analyze(manifest, pubs)
    save_json(run_dir / 'replication_summary.json', summary)
    with (run_dir / 'replication_per_condition.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return summary


def render_result(summary: dict) -> str:
    group = summary['groups']
    lo, hi = summary['shot_only_95pct_normal_ci']
    return '\n'.join([
        f"Backend: {summary['backend']}",
        f"Shots: {summary['shots']} across {summary['conditions']} circuits (no postselection)",
        *(f"  {key}: {v['on']}/{v['shots']} = {v['p_on']:.2%} center-ON"
          for key,v in group.items()),
        f"Retained middle-bit contrast: {summary['retained_contrast']:.2%}",
        f"Erased middle-bit contrast:   {summary['erased_contrast']:.2%}",
        f"Controlled contrast (difference-in-differences): {summary['difference_in_differences']:.2%}",
        f"95% shot-only normal CI: [{lo:.2%}, {hi:.2%}]",
        f"Positive history-effect witness: {'YES' if summary['positive_history_effect_shot_only'] else 'NO'}",
        f"Original Kingston reference effect: {summary['historical_difference_in_differences']:.2%}",
        'Note: a positive witness is not evidence of intrinsic quantum non-Markovianity.'
    ])
