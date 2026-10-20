#!/usr/bin/env python3
"""Qiskit SDK parser smoke test. No IBM service, credentials or submission."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from hardware.replication_core import source_conditions, QASM_DIR
from hardware.ibm_runner import source_circuit_gate_checks

def main():
    try:
        from qiskit import QuantumCircuit
    except ImportError:
        print('Qiskit not installed. Run SETUP_IBM_WINDOWS.bat (Windows) or install requirements-hardware.txt.')
        return 2
    for entry in source_conditions():
        text=(QASM_DIR/entry['filename']).read_text(encoding='utf-8')
        qc=QuantumCircuit.from_qasm_str(text)
        source_circuit_gate_checks(qc,entry)
    print('PASS: all 16 V207 QASM circuits import into Qiskit, have nine measurements and expected resets.')
    print('No IBM service connected; no QPU time used.')
    return 0

if __name__=='__main__': raise SystemExit(main())
