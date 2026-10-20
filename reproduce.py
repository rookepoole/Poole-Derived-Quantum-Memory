#!/usr/bin/env python3
"""Reproduce the original IBM v2.4 two-generation results from PUBLIC histograms.

Python 3.10+ standard library ONLY. No Qiskit, account, network, or QPU needed.
Every shot is included. Results are attributed to frozen historical PUB order,
independently cross-checked by preparation-register majorities.
"""
from __future__ import annotations
import collections, csv, json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COUNTS = ROOT / 'data/sanitized_ibm_9bit_counts.json'
PUBS_EXPECTED = [
    ('001','erase'),('111','erase'),('011','erase'),('110','erase'),
    ('010','retain'),('100','retain'),('000','retain'),('011','retain'),
    ('101','erase'),('010','erase'),('000','erase'),('111','retain'),
    ('001','retain'),('100','erase'),('101','retain'),('110','retain'),
]

def source_f1(abc: str) -> tuple[int,int,int,int,int]:
    a,b,c = map(int,abc)
    n = int(not (a or b or c))
    return (b, a & c, n, n, b)

def expected_center(abc: str, arm: str) -> int:
    r=source_f1(abc)
    return int(bool(r[0] or r[2])) if arm=='retain' else 0

def calculate(path: Path=COUNTS):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    assert len(data['pubs'])==16
    rows=[]
    histogram_total=0
    for i,(rec,(abc,arm)) in enumerate(zip(data['pubs'],PUBS_EXPECTED)):
        assert (rec['pub'],rec['abc'],rec['arm'])==(i,abc,arm),i
        counts=rec['counts']
        assert all(isinstance(s,str) and len(s)==9 and set(s)<={'0','1'} for s in counts)
        assert all(type(n) is int and n>0 for n in counts.values())
        n=sum(counts.values())
        assert n==1024==rec['shots'],(i,n)
        histogram_total+=n
        prep=collections.Counter()
        on=0
        env_ones=0
        for string,howmany in counts.items():
            value=int(string,2)
            prep[''.join(str((value>>bit)&1) for bit in (0,1,2))]+=howmany
            on+= ((value>>4)&1)*howmany
            env_ones+=sum((value>>bit)&1 for bit in (3,5,6,7))*howmany
        most_common,prep_n=prep.most_common(1)[0]
        assert most_common==abc,(i,abc,most_common)
        ideal=expected_center(abc,arm)
        rows.append({
            'pub':i,'abc':abc,'arm':arm,'middle_b':int(abc[1]),
            'first_generation':''.join(map(str,source_f1(abc))),
            'ideal_final_center':ideal,'shots':n,'center_on':on,'center_off':n-on,
            'correct_center':on if ideal else n-on,
            'preparation_match':prep_n,
            'environment_bit_mean':env_ones/(4*n)
        })
    assert histogram_total==16384
    agg={}
    for arm in ('retain','erase'):
        for middle in (0,1):
            members=[r for r in rows if r['arm']==arm and r['middle_b']==middle]
            assert len(members)==4
            on=sum(r['center_on'] for r in members)
            n=sum(r['shots'] for r in members)
            agg[f'{arm}_b{middle}']={'on':on,'shots':n,'on_probability':on/n}
    p=lambda arm,b:agg[f'{arm}_b{b}']['on_probability']
    retained=p('retain',1)-p('retain',0)
    erased=p('erase',1)-p('erase',0)
    did=retained-erased
    se=math.sqrt(sum(g['on_probability']*(1-g['on_probability'])/g['shots'] for g in agg.values()))
    out={'source':'sanitized original IBM v2.4 9-bit outcome histograms',
         'job_id':data['job_id'],'backend':data['device'],'n_circuits':len(rows),
         'shots':histogram_total,'correct_final_center':sum(r['correct_center'] for r in rows),
         'center_accuracy':sum(r['correct_center'] for r in rows)/histogram_total,
         'preparation_register_agreement':sum(r['preparation_match'] for r in rows)/histogram_total,
         'group_rates':agg,'retained_contrast':retained,'erased_contrast':erased,
         'difference_in_differences':did,'shot_only_standard_error':se,
         'difference_in_differences_95pct_normal_shot_only':[did-1.96*se,did+1.96*se],
         'ideal_difference_in_differences':0.75,
         'method':'full 9-bit histograms, 1024 shots each, computational-basis central-bit q4, no postselection',
         'uncertainty_caveat':'binomial independent-shot normal approximation only; excludes QPU drift, temporal correlations and SPAM/reset systematics',
         'source_caveat':'two-generation simplified center update is restricted to eight reachable F1 states and all-neighbor-erased control',
         'QPY_gate_by_gate_disassembly_verified':False}
    return out,rows

def check_known_results(result, rows):
    """Golden-value regression on the archived original job (not a fit)."""
    assert result['shots']==16384
    assert result['correct_final_center']==15272
    assert result['preparation_register_agreement']==12896/16384
    assert result['group_rates']['retain_b0']['on']==1143
    assert result['group_rates']['retain_b1']['on']==3846
    assert result['group_rates']['erase_b0']['on']==204
    assert result['group_rates']['erase_b1']['on']==263
    assert abs(result['difference_in_differences']-0.6455078125)<1e-12
    assert len(rows)==16

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('--check-only',action='store_true',help='do not write results')
    args=p.parse_args()
    summary,rows=calculate()
    check_known_results(summary, rows)
    if not args.check_only:
        out=ROOT/'results';out.mkdir(exist_ok=True)
        (out/'verified_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8',newline='\n')
        with (out/'per_pub.csv').open('w',encoding='utf-8',newline='') as f:
            w=csv.DictWriter(f, fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print('IBM job:',summary['job_id'],summary['backend'])
    print('Circuits / shots:',summary['n_circuits'],'/',summary['shots'])
    print(f"Correct center bits: {summary['correct_final_center']}/{summary['shots']} = {summary['center_accuracy']:.6%}")
    print('Center-ON by arm/middle:',{k:(g['on'],g['shots']) for k,g in summary['group_rates'].items()})
    print(f"Retained middle-bit contrast: {summary['retained_contrast']:.4%}")
    print(f"Erased middle-bit contrast: {summary['erased_contrast']:.4%}")
    lo,hi=summary['difference_in_differences_95pct_normal_shot_only']
    print(f"Difference-in-differences: {summary['difference_in_differences']:.4%} (95% shot-only CI {lo:.4%} to {hi:.4%})")
    print('Golden-value checks: PASS')
    if not args.check_only: print('Saved results/verified_summary.json and results/per_pub.csv')

if __name__=='__main__':main()
