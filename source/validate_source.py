#!/usr/bin/env python3
"""Exact 625,000-cell V207 source-sector verification using archived t250 A snapshot.

Requires NumPy+SciPy locally; does not regenerate 1200 historical steps unless
`python reconstruct_dark.py` is separately invoked. No QPU/network use.
"""
from __future__ import annotations
import hashlib,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
try:
 import numpy as np
 from scipy.ndimage import correlate
except ImportError:
 raise SystemExit('Optional dependencies: python -m pip install numpy scipy\nOffline data/statistics checks do not require these.')
from reconstruct import inh,amp,thr,kernel,shape
SEED=((172,108,3),(173,108,3),(174,108,3))
SITES=((172,108,3),(173,108,3),(173,108,4),(173,109,3),(174,108,3))
CENTER=SITES[1]; ENV=(SITES[0],SITES[2],SITES[3],SITES[4])

def step(field):
 n=correlate(field,kernel,mode='wrap',output=np.int16)
 effective=n-15*inh.astype(np.int16)-2*thr.astype(np.int16)+amp.astype(np.int16)
 return np.where(field==0,(effective>=5)&(effective<=6),(effective>=5)&(effective<=9)).astype(np.uint8)

def main():
 primes=(2,3,5,7,11,13,17,19,23)
 for n in range(-20,30):
  phi=n+sum(.35*math.exp(-((n-p)**2)/.01) for p in primes)
  assert (5<=phi<=7)==(5<=n<=6)
  assert (5<=phi<=9)==(5<=n<=9)
 z=np.load(ROOT/'reconstructed_dark_pair_t250.npz',allow_pickle=False)
 A,B=z['A'],z['B']
 assert A.shape==B.shape==shape
 assert hashlib.sha256(A.tobytes()).hexdigest()=='9d0a837e136e4c13c2b6968521de20dd0bc82725e01c63beca89f76b93c4fbf7'
 assert hashlib.sha256(B.tobytes()).hexdigest()=='0fd8d9b54c98bc2b4863387a42cfd0dd538acf1d3d8fabcc48b98f6e8b9f926e'
 sys.path.insert(0,str(ROOT.parent))
 from reproduce import source_f1,expected_center
 for i in range(8):
  abc=f'{i:03b}'; s=A.copy()
  for site,bit in zip(SEED,map(int,abc)):s[site]=bit
  t1=step(s)
  r=tuple(int(t1[site]) for site in SITES)
  assert r==source_f1(abc),(abc,'F1',r)
  t1[CENTER]=0
  c=int(step(t1)[CENTER]);assert c==expected_center(abc,'retain'),(abc,'retain',c)
  for site in ENV:t1[site]=0
  c=int(step(t1)[CENTER]);assert c==0,(abc,'erase',c)
 print('PASS: reconstructed source A and B state hashes, 50 prime-threshold checks, 8/8 F1 and 16/16 F2 source interventions.')
 print('LIMITATION: source state is a reproducible reconstruction; missing original historical snapshot prevents bytewise historical comparison.')
if __name__=='__main__':main()
