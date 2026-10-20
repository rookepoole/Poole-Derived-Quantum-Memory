#!/usr/bin/env python3
"""Independently interpret supplied reconstructed QASM circuits on all 16 basis states.

Strictly a computational-basis check for the X/CX/CCX/reset gate set.
No Qiskit required. Original IBM QPY must be checked separately.
"""
from __future__ import annotations
import re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from reproduce import expected_center, source_f1

def simulate(text):
    bits=[0]*9
    pre_mid=None
    for raw in text.splitlines():
        line=raw.strip()
        if not line or line.startswith('//'): continue
        if line.startswith(('OPENQASM','include','qreg','creg','measure')):continue
        parts=line.split(' ',1)
        name=parts[0]
        qs=[int(x) for x in re.findall(r'q\[(\d+)\]',parts[1])] if len(parts)>1 else []
        if name=='x': assert len(qs)==1;bits[qs[0]]^=1
        elif name=='cx': assert len(qs)==2;bits[qs[1]]^=bits[qs[0]]
        elif name=='ccx': assert len(qs)==3;bits[qs[2]]^=bits[qs[0]]&bits[qs[1]]
        elif name=='reset':
            if pre_mid is None:
                assert qs==[4]
                pre_mid=tuple(bits)
            bits[qs[0]]=0
        else:raise ValueError(f'Unsupported gate in reconstructed QASM: {line}')
    assert pre_mid is not None
    return pre_mid,tuple(bits)

def check():
    for num in range(8):
        abc=f'{num:03b}'
        for arm in ('retained','erased'):
            f=ROOT/'circuits/reconstructed_qasm'/f'v24_{abc}_{arm}.qasm'
            mid,final=simulate(f.read_text(encoding='utf-8'))
            assert mid[3:8]==source_f1(abc),(abc,arm,mid)
            assert final[4]==expected_center(abc,'retain' if arm=='retained' else 'erase'),(abc,arm)
            assert final[8]==0 and final[:3]==tuple(map(int,abc))
    print('PASS: 16 reconstructed 9-qubit QASM circuits; F1, F2, central reset, erasure, clean scratch, preserved input registers')
if __name__=='__main__':check()
