#!/usr/bin/env python3
"""Read ORIGINAL provider QPY circuits, requiring local Qiskit but no IBM API.

This is a structural inspection; it is NOT an equivalence proof against all
source-lattice configurations or a claim about unobserved hardware dynamics.
"""
from __future__ import annotations
import collections,hashlib,io,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from reproduce import PUBS_EXPECTED

def main():
    try:from qiskit import qpy
    except ImportError:raise SystemExit('Install Qiskit in your environment: python -m pip install qiskit\nThis optional check never calls IBM.')
    prov=json.loads((ROOT/'data/sanitized_provenance.json').read_text(encoding='utf-8'))
    rows=[]
    for row in prov['original_compiled_qpy']:
        i=row['pub']
        f=ROOT/'circuits/original_ibm_qpy'/row['filename']
        raw=f.read_bytes()
        assert hashlib.sha256(raw).hexdigest()==row['sha256'],f
        circuits=qpy.load(io.BytesIO(raw))
        assert len(circuits)==1
        qc=circuits[0]
        assert qc.num_qubits==9 and qc.num_clbits==9
        ops=collections.Counter(entry.operation.name for entry in qc.data)
        measurements={}
        for index,entry in enumerate(qc.data):
            if entry.operation.name=='measure':
                for qb,clb in zip(entry.qubits,entry.clbits):
                    measurements[qc.find_bit(clb).index]=qc.find_bit(qb).index
        center_wire=measurements.get(4)
        resets=[]
        for index,entry in enumerate(qc.data):
            if entry.operation.name=='reset':
                resets.append({'instruction_index':index,'wires':[qc.find_bit(q).index for q in entry.qubits]})
        observed_center_resets=[r for r in resets if center_wire in r['wires']]
        abc,arm=PUBS_EXPECTED[i]
        rows.append({'pub':i,'abc':abc,'arm':arm,'n_qubits':qc.num_qubits,'n_clbits':qc.num_clbits,
           'op_counts':dict(ops),'terminal_measurement_to_wire':measurements,
           'center_wire':center_wire,'center_resets':observed_center_resets,'all_resets':resets})
        assert center_wire is not None
        assert observed_center_resets
        assert len(resets)>= (1 if arm=='retain' else 5),(i,arm,len(resets))
    f=ROOT/'results/original_qpy_inspection.json'
    f.write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('PASS: all 16 actual IBM QPY programs parsed with Qiskit; structure saved to',f)
    print('WARNING: native-QPY structural inspection is not a general source-to-circuit equivalence proof.')
if __name__=='__main__':main()
