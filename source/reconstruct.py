import numpy as np
from scipy.ndimage import correlate
from pathlib import Path
import json,time
ROOT=Path(__file__).resolve().parent
shape=(250,250,10)
inh=np.ones(shape,dtype=bool);amp=np.zeros(shape,dtype=bool);thr=np.zeros(shape,dtype=bool)
z=slice(3,8)
inh[100:120,100:120,z]=False; amp[100:120,100:120,z]=True
inh[105:115,105:115,z]=True; amp[105:115,105:115,z]=False
inh[20:105,97:100,z]=False; amp[20:105,97:100,z]=True
inh[120:200,108:111,z]=False; amp[120:200,108:111,z]=True
inh[120:200,95:102,z]=False; amp[120:200,95:102,z]=True
inh[117:119,95:102,z]=False; amp[117:119,95:102,z]=True
kernel=np.ones((3,3,3),dtype=np.int8);kernel[1,1,1]=0
# actual V207 source computes sum and real-valued 0.35 resonance; for integer sums
# this amounts to inclusion of only potential 5,6 births and potential 5..9 survival.
def step(field):
 n=correlate(field,kernel,mode='wrap',output=np.int16)
 n-=inh.astype(np.int16)*15
 n-=thr.astype(np.int16)*2
 n+=amp.astype(np.int16)
 return np.where(field==0,(n>=5)&(n<=6),(n>=5)&(n<=9)).astype(np.uint8)

if __name__=='__main__':
 field=np.zeros(shape,dtype=np.uint8);t0=time.time()
 for t in range(250):
  if 50<=t<100:field[20:23,97:100,3:8]=1
  field=step(field)
  if t in (0,49,99,199,249):print('step',t+1,'active',int(field.sum()),'elapsed',round(time.time()-t0,2),flush=True)
 np.savez_compressed(ROOT/'snapshot_after_250_steps.npz',state=field)
 print('snapshot done',field.shape, int(field.sum()))
 coords=((172,108,3),(173,108,3),(174,108,3));s1=((172,108,3),(173,108,3),(173,108,4),(173,109,3),(174,108,3))
 for val in range(8):
  x=field.copy()
  for i,c in enumerate(coords):x[c]=(val>>(2-i))&1
  y=step(x); v=tuple(int(y[c]) for c in s1)
  print(f'{val:03b}',v,flush=True)
