"""Public IBM Quantum reproduction workflow: compile -> explicit submit -> retrieve.

Hardware use is NEVER automatic. Credentials remain in memory and are never saved
by this program. A per-run QPY is frozen before anyone can submit a job.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import io
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import re
import secrets
import sys
import zipfile

from hardware.replication_core import (
    ROOT, QASM_DIR, create_manifest, digest, normalize_counts, render_result,
    save_json, source_conditions, validate_manifest, validate_data, write_analysis,
)

PRIVATE = ROOT / 'private_runs'
EXPORTS = ROOT / 'public_exports'
QPY_FILE = 'compiled_isa.qpy'
PLAN_FILE = 'compile_plan.json'
RECEIPT_FILE = 'job_receipt.json'
RESULT_FILE = 'sanitized_counts.json'


def timestamp_id() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + secrets.token_hex(3)


def public_error(exc: BaseException) -> str:
    """Never print arbitrary credentialed provider errors or stack frames."""
    # Explicitly avoid echoing IBM client exceptions, which may contain request data.
    if isinstance(exc, (ValueError, FileNotFoundError, AssertionError)):
        message = str(exc)[:300]
        message = re.sub(r'(?i)(api[ _-]?key|token|authorization)\s*[:=]\s*\S+', r'\1=[REDACTED]', message)
        message = re.sub(r'crn:v1:[^\s]+', '[INSTANCE REDACTED]', message, flags=re.I)
        message = re.sub(r'(?<![A-Za-z0-9])[A-Za-z0-9_-]{40,}(?![A-Za-z0-9])', '[LONG IDENTIFIER REDACTED]', message)
        return f'{type(exc).__name__}: {message}'
    return f'{type(exc).__name__}: hardware SDK/backend operation failed. Inspect setup and retry; do not publish your credentials.'


def load_sdk():
    """Qiskit is imported lazily; standard-library offline tasks remain free."""
    try:
        from qiskit import QuantumCircuit, qpy
        from qiskit.transpiler import generate_preset_pass_manager
    except ImportError as exc:
        raise RuntimeError('Qiskit SDK not installed. Run SETUP_IBM_WINDOWS.bat or pip install -r requirements-hardware.txt') from exc
    return QuantumCircuit, qpy, generate_preset_pass_manager


def backend_label(backend) -> str:
    name = getattr(backend, 'name', '')
    return name() if callable(name) else str(name)


def source_circuit_gate_checks(qc, condition):
    ops = qc.count_ops()
    expected_resets = 5 if condition['arm'] == 'erased' else 1
    if qc.num_qubits != 9 or qc.num_clbits != 9:
        raise ValueError('Incorrect 9-qubit / 9-bit register count at ' + condition['filename'])
    if len(qc.cregs) != 1 or qc.cregs[0].name != 'c':
        raise ValueError('Expected classical register c[9] at ' + condition['filename'])
    if ops.get('measure', 0) != 9 or ops.get('reset', 0) != expected_resets:
        raise ValueError('Missing source measurements or midpoint resets at ' + condition['filename'])
    unexpected = set(ops) - {'x', 'cx', 'ccx', 'reset', 'measure'}
    if unexpected:
        raise ValueError('Unexpected source operation ' + ','.join(sorted(unexpected)))


def backend_gate_checks(backend):
    if getattr(backend, 'num_qubits', 0) < 9:
        raise ValueError('Backend requires at least nine physical qubits')
    target = getattr(backend, 'target', None)
    if target is not None:
        ops = getattr(target, 'operation_names', None)
        if ops is not None and not {'reset', 'measure'}.issubset(set(ops)):
            raise ValueError('Chosen backend does not advertise reset and measure support')


def compile_preflight(backend, *, run_dir: Path | None = None, shots: int = 1024,
                      seed: int = 20261020, optimization: int = 1,
                      sdk=None) -> Path:
    """Compile all 16 on selected backend; NO Runtime sampler.run()."""
    if sdk is None:
        sdk = load_sdk()
    QuantumCircuit, qpy, pass_manager_factory = sdk
    backend_gate_checks(backend)
    manifest = create_manifest(backend_label(backend), shots, seed, optimization)
    validate_manifest(manifest)
    versions = {}
    for name in ('qiskit', 'qiskit-ibm-runtime'):
        try: versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: versions[name] = 'mocked or unavailable'
    manifest['sdk_versions'] = versions
    manifest['python_version'] = sys.version.split()[0]
    manifest['backend_num_qubits'] = backend.num_qubits
    input_circuits = []
    for item in manifest['assignments']:
        text = (QASM_DIR / item['filename']).read_text(encoding='utf-8')
        qc = QuantumCircuit.from_qasm_str(text)
        qc.name = item['condition']
        source_circuit_gate_checks(qc, item)
        input_circuits.append(qc)
    pm = pass_manager_factory(backend=backend, optimization_level=optimization,
                              seed_transpiler=seed, approximation_degree=1.0)
    physical = pm.run(input_circuits)
    if not isinstance(physical, (list, tuple)) or len(physical) != 16:
        raise ValueError('Transpiler did not return all 16 compiled circuits')
    records = []
    for item, circuit in zip(manifest['assignments'], physical):
        ops = dict(circuit.count_ops())
        min_reset = 5 if item['arm'] == 'erased' else 1
        if circuit.num_clbits != 9 or ops.get('measure', 0) != 9:
            raise ValueError('Mapped circuit lost output bits: ' + item['condition'])
        if ops.get('reset', 0) < min_reset:
            raise ValueError('Mapped circuit lost mandatory mid-circuit resets: ' + item['condition'])
        advertised_ops = getattr(getattr(backend, 'target', None), 'operation_names', None)
        if advertised_ops is not None:
            non_native = set(ops) - set(advertised_ops) - {'barrier'}
            if non_native:
                raise ValueError('Compiler left non-native gates in ' + item['condition'] + ': ' + ','.join(sorted(non_native)))
        # Backend may use any native 2q instruction set, not just CX/CZ.
        num2 = sum(1 for instruction in circuit.data if len(instruction.qubits) == 2)
        try:
            physical_layout = circuit.layout.final_index_layout() if circuit.layout is not None else None
        except (AttributeError, TypeError, ValueError):
            physical_layout = None
        records.append({'pub': item['pub'], 'condition': item['condition'],
                        'final_layout': physical_layout,
                        'physical_qubits': circuit.num_qubits,
                        'compiled_depth': circuit.depth(), 'native_two_qubit_gates': num2,
                        'resets': ops.get('reset', 0), 'measurements': ops.get('measure', 0),
                        'native_ops': ops})
    if run_dir is None:
        run_dir = PRIVATE / f'v24_{timestamp_id()}'
    run_dir = Path(run_dir).resolve()
    if run_dir.exists() and any(run_dir.iterdir()):
        raise ValueError('Select a new empty run directory to avoid overwriting a prior experiment')
    run_dir.mkdir(parents=True, exist_ok=True)
    try:
        binary = io.BytesIO()
        qpy.dump(physical, binary)
        raw = binary.getvalue()
        # QPY should round-trip; no circuit recompilation after this point.
        recovered = qpy.load(io.BytesIO(raw))
        if len(recovered) != 16:
            raise ValueError('QPY roundtrip did not preserve all 16 circuits')
        for prior, replay in zip(physical, recovered):
            if prior.num_clbits != replay.num_clbits or dict(prior.count_ops()) != dict(replay.count_ops()):
                raise ValueError('QPY roundtrip changed circuit operations')
        manifest['qpy_sha256'] = digest(raw)
        manifest['native_compilation'] = records
        manifest['compiled_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
        manifest['compile_only'] = True
        (run_dir / QPY_FILE).write_bytes(raw)
        save_json(run_dir / PLAN_FILE, manifest)
    except Exception:
        # Incomplete compile must never create an apparently ready plan.
        (run_dir / PLAN_FILE).unlink(missing_ok=True)
        raise
    return run_dir


def inspect_plan(run_dir: Path, *, qpy=None) -> tuple[dict, list]:
    path = Path(run_dir)
    manifest = json.loads((path / PLAN_FILE).read_text(encoding='utf-8'))
    validate_manifest(manifest)
    qpy_raw = (path / QPY_FILE).read_bytes()
    if manifest.get('qpy_sha256') != digest(qpy_raw):
        raise ValueError('Compiled-QPY checksum mismatch; refusing hardware submission')
    if qpy is None: qpy = load_sdk()[1]
    compiled = qpy.load(io.BytesIO(qpy_raw))
    if len(compiled) != 16 or len(manifest.get('native_compilation', [])) != 16:
        raise ValueError('Compiled QPY has incorrect circuit count')
    for item, qc, rec in zip(manifest['assignments'], compiled, manifest['native_compilation']):
        if rec['pub'] != item['pub'] or rec['condition'] != item['condition']:
            raise ValueError('Compilation provenance mismatch')
        ops = qc.count_ops()
        expected_reset = 5 if item['arm'] == 'erased' else 1
        if qc.num_clbits != 9 or ops.get('measure', 0) != 9 or ops.get('reset', 0) < expected_reset:
            raise ValueError('Compiled QPY failed final validation at ' + item['condition'])
    return manifest, compiled


def configure_sampler(sampler):
    """Fail closed if requested no-mitigation settings cannot be applied."""
    sampler.options.twirling.enable_gates = False
    sampler.options.twirling.enable_measure = False
    sampler.options.dynamical_decoupling.enable = False
    sampler.options.execution.init_qubits = True
    if sampler.options.twirling.enable_gates or sampler.options.twirling.enable_measure:
        raise ValueError('Sampler twirling unexpectedly enabled')
    if sampler.options.dynamical_decoupling.enable:
        raise ValueError('Sampler dynamical decoupling unexpectedly enabled')


def submit_precompiled(service, run_dir: Path, *, confirmation: str,
                        sampler_cls=None, qpy=None) -> str:
    """Only entry point for QPU execution; requires explicit consent."""
    if confirmation != 'SUBMIT 16':
        raise ValueError('No job submitted: authorization phrase must be SUBMIT 16')
    run_dir = Path(run_dir)
    manifest, circuits = inspect_plan(run_dir, qpy=qpy)
    if (run_dir / RECEIPT_FILE).exists() or (run_dir / 'submission_intent.json').exists():
        raise ValueError('Run already submitted or previously attempted; do not risk duplicate QPU charges')
    backend = service.backend(manifest['backend'])
    backend_gate_checks(backend)
    if sampler_cls is None:
        try:
            from qiskit_ibm_runtime.executor_sampler import Sampler as sampler_cls
        except ImportError:
            from qiskit_ibm_runtime import SamplerV2 as sampler_cls
    sampler = sampler_cls(mode=backend)
    configure_sampler(sampler)
    # Intent is written before submitting; if the network times out, do not blindly resend.
    save_json(run_dir / 'submission_intent.json', {
        'status': 'attempted', 'qpy_sha256': manifest['qpy_sha256'],
        'backend': manifest['backend'],
        'utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'warning': 'If a timeout occurs, check IBM Workloads before attempting any new submission.'
    })
    job = sampler.run(circuits, shots=manifest['shots_per_circuit'])
    job_id = job.job_id()
    if not isinstance(job_id, str) or not job_id:
        raise RuntimeError('IBM returned no job ID. Inspect your account; DO NOT retry blindly.')
    save_json(run_dir / RECEIPT_FILE, {
        'schema': 'poole-v207-v24-private-job-receipt-1',
        'job_id': job_id, 'backend': manifest['backend'],
        'qpy_sha256': manifest['qpy_sha256'],
        'shots_per_circuit': manifest['shots_per_circuit'],
        'expected_total_shots': manifest['expected_total_shots'],
        'pub_order': [a['condition'] for a in manifest['assignments']],
        'source': 'IBM submitted reconstructed QASM compiled specifically for this backend',
        'original_job': manifest['original_ibm_job'],
        'date_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'no_mitigation': True
    })
    return job_id


def _get_status_name(job):
    status = job.status()
    return str(getattr(status, 'name', status)).split('.')[-1].upper()


def retrieve_job(service, run_dir: Path) -> dict | None:
    """Never rerun circuits. Get original job by immutable receipt ID."""
    run_dir = Path(run_dir)
    manifest, _ = inspect_plan(run_dir)
    receipt = json.loads((run_dir / RECEIPT_FILE).read_text(encoding='utf-8'))
    if receipt['qpy_sha256'] != manifest['qpy_sha256'] or receipt['backend'] != manifest['backend']:
        raise ValueError('Job receipt does not match compiled manifest')
    if (run_dir / RESULT_FILE).exists():
        raise ValueError('Counts already downloaded; use analyze. Never overwrite experiment data.')
    job = service.job(receipt['job_id'])
    status = _get_status_name(job)
    if status not in {'DONE', 'COMPLETED'}:
        print('IBM job status:', status, '(nothing submitted, no additional shots used)')
        return None
    results = job.result()
    if len(results) != 16:
        raise ValueError('IBM did not return 16 circuit results; save nothing')
    records = []
    for pub, (assignment, result) in enumerate(zip(manifest['assignments'], results)):
        # The OpenQASM uses `creg c[9]`, not Qiskit measure_all register `meas`.
        data = result.data
        c_register = getattr(data, 'c', None)
        if c_register is None:
            raise ValueError('Missing IBM Sampler classical register c in PUB ' + str(pub))
        counts = normalize_counts(c_register.get_counts(), 9)
        if sum(counts.values()) != manifest['shots_per_circuit']:
            raise ValueError('IBM shot count mismatch in PUB ' + str(pub))
        records.append({'pub': pub, 'condition': assignment['condition'],
                        'abc': assignment['abc'], 'arm': assignment['arm'],
                        'shots': sum(counts.values()), 'counts': counts})
    validate_data(manifest, records)
    data = {'schema': 'poole-v207-v24-sanitized-independent-job-1',
            'job_id': receipt['job_id'], 'backend': manifest['backend'],
            'raw_provider_metadata_included': False,
            'bitstring_order': 'c8..c0',
            'pubs': records}
    save_json(run_dir / RESULT_FILE, data)
    summary = write_analysis(run_dir, manifest, records)
    print(render_result(summary))
    return summary


def analyze_existing(run_dir: Path) -> dict:
    path = Path(run_dir)
    manifest = json.loads((path / PLAN_FILE).read_text(encoding='utf-8'))
    data = json.loads((path / RESULT_FILE).read_text(encoding='utf-8'))
    summary = write_analysis(path, manifest, data['pubs'])
    print(render_result(summary))
    return summary


def export_public(run_dir: Path) -> Path:
    """Create a minimal shareable bundle with no account CRN or API token."""
    path = Path(run_dir)
    summary = analyze_existing(path)
    manifest = json.loads((path / PLAN_FILE).read_text(encoding='utf-8'))
    data = json.loads((path / RESULT_FILE).read_text(encoding='utf-8'))
    receipt = json.loads((path / RECEIPT_FILE).read_text(encoding='utf-8'))
    safe_manifest = {key: manifest[key] for key in (
        'schema', 'experiment', 'original_ibm_job', 'circuit_provenance',
        'backend', 'randomization_seed', 'optimization_level',
        'shots_per_circuit', 'expected_total_shots', 'bitstring_order',
        'mitigation', 'assignments', 'qpy_sha256', 'native_compilation',
        'sdk_versions', 'python_version', 'backend_num_qubits')}
    safe_receipt = {'job_id': receipt['job_id'], 'backend': receipt['backend'],
                    'no_mitigation': True}
    EXPORTS.mkdir(exist_ok=True, parents=True)
    outfile = EXPORTS / ('Poole_V207_independent_replication_' + timestamp_id() + '.zip')
    with zipfile.ZipFile(outfile, 'w', compression=zipfile.ZIP_DEFLATED) as arc:
        for name, content in {
            'manifest.json': safe_manifest,
            'sanitized_counts.json': data,
            'analysis.json': summary,
            'public_job_reference.json': safe_receipt,
        }.items():
            arc.writestr(name, json.dumps(content, indent=2, sort_keys=True) + '\n')
        arc.write(path / 'replication_per_condition.csv', 'per_condition.csv')
        arc.write(path / QPY_FILE, 'compiled_isa.qpy')
    return outfile


def get_token_gui_or_terminal() -> str:
    """Paste-friendly Windows entry that never echoes or persists an API token."""
    if os.name == 'nt':
        try:
            import tkinter as tk
            value = {'token': ''}
            root = tk.Tk()
            root.title('IBM Quantum API key - Poole replication')
            root.geometry('590x145')
            root.resizable(False, False)
            tk.Label(root, text='Paste your own API key. It will NOT be saved to this folder.').pack(pady=8)
            entry = tk.Entry(root, width=74, show='*')
            entry.pack(padx=12)
            entry.focus_set()
            def accept(event=None):
                value['token'] = entry.get().strip()
                root.destroy()
            bar = tk.Frame(root); bar.pack(pady=10)
            tk.Button(bar, text='Paste from clipboard', command=lambda: entry.event_generate('<<Paste>>')).pack(side='left', padx=5)
            tk.Button(bar, text='Continue', command=accept).pack(side='left', padx=5)
            root.bind('<Return>', accept)
            root.mainloop()
            if value['token']:
                return value['token']
            raise ValueError('No API key entered')
        except Exception as exc:
            if not isinstance(exc, (ImportError, RuntimeError, OSError)) and exc.__class__.__name__ != 'TclError':
                raise
            pass  # headless Windows, use hidden terminal prompt below
    import getpass
    token = getpass.getpass('IBM Quantum API key (hidden; not saved): ').strip()
    if not token: raise ValueError('No API key entered')
    return token


def connect(auth: str = 'prompt', *, service_cls=None):
    if service_cls is None:
        try:
            from qiskit_ibm_runtime import QiskitRuntimeService as service_cls
        except ImportError as exc:
            raise RuntimeError('Install Qiskit hardware dependencies first') from exc
    logging.getLogger('qiskit_ibm_runtime').setLevel(logging.ERROR)
    if auth == 'saved':
        return service_cls()
    if auth != 'prompt':
        raise ValueError('Authentication is either saved or prompt')
    token = get_token_gui_or_terminal()
    # Optional CRN, not recorded in any run manifest or export.
    crn = os.environ.get('IBM_QUANTUM_INSTANCE', '').strip()
    if not crn:
        crn = input('IBM Quantum instance CRN (optional; Enter for automatic selection): ').strip()
    params = {'channel': 'ibm_quantum_platform', 'token': token}
    if crn: params['instance'] = crn
    try:
        return service_cls(**params)
    finally:
        del token, params


def list_backends(service) -> list:
    results = service.backends(min_num_qubits=9, simulator=False, operational=True)
    candidates = []
    for b in results:
        if getattr(b, 'num_qubits', 0) < 9: continue
        names = getattr(getattr(b, 'target', None), 'operation_names', None)
        if names is not None and not {'reset','measure'}.issubset(set(names)):
            continue
        candidates.append(b)
    candidates.sort(key=backend_label)
    return candidates


def select_backend(service, name: str | None = None):
    choices = list_backends(service)
    if not choices:
        raise ValueError('No operational accessible IBM backend with 9 qubits and reset support')
    print('Available IBM processors (operational, >=9 qubits, reset capable):')
    for i, b in enumerate(choices, 1):
        try:
            pending = getattr(b.status(), 'pending_jobs', '?')
        except Exception:
            pending = '?'
        print(f"  [{i}] {backend_label(b)} | {b.num_qubits} qubits | pending jobs: {pending}")
    if name:
        for b in choices:
            if backend_label(b) == name: return b
        raise ValueError('Backend not accessible/operational: ' + name)
    choice = input('Choose a backend number: ').strip()
    if not choice.isdecimal() or not 1 <= int(choice) <= len(choices):
        raise ValueError('Invalid backend number')
    return choices[int(choice) - 1]


def prompt_auth_method() -> str:
    value = input('Authentication: [1] paste own API key (default)  [2] saved Qiskit account: ').strip()
    if value in ('', '1'): return 'prompt'
    if value == '2': return 'saved'
    raise ValueError('Invalid authentication option')


def interactive_menu():
    print('\nPOOLE V207 TWO-GENERATION | Public IBM Hardware Replication v1.1')
    print('No hardware job is ever submitted without explicit SUBMIT 16 approval.')
    service = None
    while True:
        print('\n[1] Reproduce original published counts offline (no account)')
        print('[2] List accessible IBM processors (connect account)')
        print('[3] Compile 16 circuits only (NO hardware execution)')
        print('[4] Submit an EXISTING frozen compile plan (16 circuits, uses allocation)')
        print('[5] Retrieve an existing IBM job (no resubmission)')
        print('[6] Analyze downloaded counts offline')
        print('[7] Export a sanitized shareable result ZIP')
        print('[0] Exit')
        choice = input('Choice: ').strip()
        if choice == '0': return 0
        try:
            if choice == '1':
                from reproduce import calculate, check_known_results
                summ, rows = calculate(); check_known_results(summ, rows)
                print('PASS: original job difference-in-differences', f"{summ['difference_in_differences']:.2%}")
            elif choice in ('2', '3', '4', '5'):
                if service is None: service = connect(prompt_auth_method())
                if choice == '2':
                    list_and_print(service)
                elif choice == '3':
                    backend = select_backend(service)
                    shots_s = input('Shots per condition [1024]: ').strip()
                    shots = int(shots_s) if shots_s else 1024
                    path = compile_preflight(backend, shots=shots)
                    print('COMPILE-ONLY PASSED; NO QPU job. Frozen plan:', path)
                    print('Review compile_plan.json and compiled_isa.qpy before submission.')
                elif choice == '4':
                    path = Path(input('Paste the compiled run folder path: ').strip().strip('"'))
                    plan, _ = inspect_plan(path)
                    print(f"\nBackend: {plan['backend']}; conditions: 16; shots: {plan['expected_total_shots']}")
                    print('THIS WILL CONSUME IBM QPU ALLOCATION; costs depend on your plan. No cost estimate is implied.')
                    confirmation = input('To authorize precisely this job, type SUBMIT 16: ').strip()
                    job_id = submit_precompiled(service, path, confirmation=confirmation)
                    print('SUBMITTED! IBM job ID:', job_id)
                    print('Job ID saved in:', path / RECEIPT_FILE)
                else:
                    path = Path(input('Paste the compiled run folder path: ').strip().strip('"'))
                    result = retrieve_job(service, path)
                    if result is not None: print('Counts and analysis saved to:', path)
            elif choice in ('6', '7'):
                path = Path(input('Paste the run folder path: ').strip().strip('"'))
                if choice == '6': analyze_existing(path)
                else: print('Shareable sanitized ZIP:', export_public(path))
            else: print('Unknown option.')
        except (KeyboardInterrupt, EOFError):
            print('\nOperation canceled.'); continue
        except Exception as exc:
            print('ERROR:', public_error(exc))


def list_and_print(service):
    bs = list_backends(service)
    if not bs: print('No operational 9-qubit reset-capable IBM backend accessible.')
    for b in bs:
        print(f"{backend_label(b)} ({b.num_qubits} qubits)")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', choices=['menu', 'list', 'compile', 'submit', 'retrieve', 'analyze', 'export'], default='menu')
    parser.add_argument('--auth', choices=['prompt', 'saved'], default='prompt')
    parser.add_argument('--backend', help='IBM backend for compile (if not specified, choose interactively)')
    parser.add_argument('--run-dir', help='Frozen compile plan directory for submit/retrieve/analyze')
    parser.add_argument('--shots', type=int, default=1024)
    parser.add_argument('--seed', type=int, default=20261020)
    parser.add_argument('--optimization', type=int, choices=[0,1,2,3], default=1)
    args = parser.parse_args(argv)
    if args.action == 'menu': return interactive_menu()
    try:
        if args.action in ('analyze', 'export'):
            if not args.run_dir: raise ValueError('--run-dir is required')
            if args.action == 'analyze': analyze_existing(Path(args.run_dir))
            else: print('Public export:', export_public(Path(args.run_dir)))
            return 0
        service = connect(args.auth)
        if args.action == 'list': list_and_print(service)
        elif args.action == 'compile':
            backend = select_backend(service, name=args.backend)
            run_dir = compile_preflight(backend, shots=args.shots, seed=args.seed,
                                        optimization=args.optimization)
            print('COMPILE ONLY - NO QPU SUBMISSION. Run folder:', run_dir)
        elif args.action == 'submit':
            if not args.run_dir: raise ValueError('--run-dir required')
            plan, _ = inspect_plan(Path(args.run_dir))
            print(f"Submitting 16 circuits to {plan['backend']}, {plan['expected_total_shots']} shots total.")
            print('This may consume QPU time or paid allocation. Verify plan before authorizing.')
            confirmation = input('Type SUBMIT 16 to authorize: ').strip()
            print('IBM Job ID:', submit_precompiled(service, Path(args.run_dir), confirmation=confirmation))
        elif args.action == 'retrieve':
            if not args.run_dir: raise ValueError('--run-dir required')
            retrieve_job(service, Path(args.run_dir))
        return 0
    except (KeyboardInterrupt, EOFError):
        print('Canceled; no new QPU job requested.'); return 2
    except Exception as exc:
        print('ERROR:', public_error(exc)); return 1


if __name__ == '__main__':
    raise SystemExit(main())
