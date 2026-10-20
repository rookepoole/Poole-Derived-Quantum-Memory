"""Reconstructed ORIGINAL 9-qubit v2.4 source logic (not extracted QPY)."""
from __future__ import annotations
from pathlib import Path
F1=[('cx',1,3),('cx',1,7),('ccx',0,2,4),('x',0),('x',1),('x',2),
 ('ccx',0,1,8),('ccx',8,2,5),('cx',5,6),('ccx',0,1,8),('x',0),('x',1),('x',2)]
F2=[('cx',3,4),('cx',5,4),('ccx',3,5,4)]
ENV=(3,5,6,7)
def ops(abc,erase):
 assert len(abc)==3 and set(abc)<=set('01')
 out=[('x',i) for i,v in enumerate(abc) if v=='1']+F1+[('reset',4)]
 if erase:out += [('reset',q) for q in ENV]
 return out+F2

def qasm(abc,erase):
 lines=['OPENQASM 2.0;','include "qelib1.inc";','qreg q[9];','creg c[9];']
 for name,*args in ops(abc,erase):
  if len(args)==1:lines.append(f'{name} q[{args[0]}];')
  else:lines.append(name+' '+','.join(f'q[{q}]' for q in args)+';')
 lines.append('measure q -> c;')
 return '\n'.join(lines)+'\n'

def emit(out):
 root=Path(out);root.mkdir(exist_ok=True,parents=True)
 for abc in (f'{i:03b}' for i in range(8)):
  for erase in (False,True):
   (root/f'v24_{abc}_{"erased" if erase else "retained"}.qasm').write_bytes(qasm(abc,erase).encode('utf-8'))

if __name__=='__main__':emit(Path(__file__).parent/'v24_reconstruction')
