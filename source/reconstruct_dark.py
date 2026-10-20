from reconstruct import np,shape,step,ROOT
import time
field=np.zeros(shape,dtype=np.uint8);t0=time.time()
for t in range(1200):
 if 50<=t<100:field[20:23,97:100,3:8]=1
 if 600<=t<650:field[197:200,95:102,3:8]=1
 field=step(field)
 if t in (99,599,649,1199):print('source t',t+1,'active',int(field.sum()),'sec',round(time.time()-t0,1),flush=True)
field[120:200,108:111,3:8]=0
for i in range(90): field=step(field)
A=field.copy();B=field.copy()
A[178,109,5]^=1;B[178,109,5]^=1;B[178,109,4]^=1
for i in range(2):A=step(A);B=step(B)
print('t92 diff',int((A!=B).sum()),flush=True)
for c in [(179,108,5),(179,110,5)]:B[c]=A[c]
for i in range(158):A=step(A);B=step(B)
print('t250 diff',int((A!=B).sum()),'sec',round(time.time()-t0,1),flush=True)
coords=((172,108,3),(173,108,3),(174,108,3));s1=((172,108,3),(173,108,3),(173,108,4),(173,109,3),(174,108,3))
for name,base in [('A',A),('B',B)]:
 print('BASE',name,'readcount',int(base[180:190,108:111,3:8].sum()),flush=True)
 for val in range(8):
  x=base.copy()
  for i,c in enumerate(coords):x[c]=(val>>(2-i))&1
  y=step(x); v=tuple(int(y[c]) for c in s1)
  print(f'{val:03b}',v,flush=True)
np.savez_compressed(ROOT/'reconstructed_dark_pair_t250.npz',A=A,B=B)
