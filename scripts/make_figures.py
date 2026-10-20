"""Optional regenerable, source-backed charts (matplotlib)."""
from pathlib import Path
import json,sys
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import reproduce
s,rows=reproduce.calculate()
xlabels=['Retain\nb=0','Retain\nb=1','Erase\nb=0','Erase\nb=1']
vals=[s['group_rates'][name]['on_probability']*100 for name in ('retain_b0','retain_b1','erase_b0','erase_b1')]
fig,ax=plt.subplots(figsize=(8.4,4.8))
bar=ax.bar(xlabels,vals,linewidth=0.6,edgecolor='#424242',color=['#36688d','#36688d','#8395a7','#8395a7'])
for b,v in zip(bar,vals):ax.text(b.get_x()+b.get_width()/2,v+1,f'{v:.2f}%',ha='center',va='bottom',fontsize=10)
ax.set_ylim(0,108);ax.set_ylabel('Final center ON, % of shots');ax.set_title('Poole V207 two-generation IBM result · all 16,384 shots')
ax.spines['top'].set_visible(False);ax.spines['right'].set_visible(False)
fig.tight_layout(); fig.savefig(ROOT/'figures/center_on_by_arm.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(figsize=(10,4.8))
histories=[f'{i:03b}' for i in range(8)]
ret={r['abc']:r for r in rows if r['arm']=='retain'}
era={r['abc']:r for r in rows if r['arm']=='erase'}
x=list(range(8));w=.38
ax.bar([i-w/2 for i in x],[100*ret[h]['center_on']/1024 for h in histories],w,label='Neighbors retained',color='#36688d')
ax.bar([i+w/2 for i in x],[100*era[h]['center_on']/1024 for h in histories],w,label='Neighbors erased',color='#8395a7')
ax.set_xticks(x,histories);ax.set_ylim(0,108);ax.set_xlabel('Prepared initial abc');ax.set_ylabel('Final center ON, % of 1,024 shots');ax.set_title('Original IBM v2.4 measurements by initial history');ax.legend(frameon=False)
ax.spines['top'].set_visible(False);ax.spines['right'].set_visible(False)
fig.tight_layout();fig.savefig(ROOT/'figures/by_input_history.png',dpi=180);plt.close(fig)
print('Generated two figures from public counts, no IBM access')
if __name__=='__main__': pass
