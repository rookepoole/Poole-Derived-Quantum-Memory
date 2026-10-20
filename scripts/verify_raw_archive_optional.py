#!/usr/bin/env python3
"""OPTIONAL: compare an ORIGINAL user-owned IBM SamplerV2 ZIP to the public release.

The private raw provider ZIP is NOT included in this public package because
its metadata can contain account identifiers. Requires NumPy; no Qiskit or API.
"""
import argparse,base64,collections,hashlib,io,json,zipfile,zlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('raw_ibm_zip',type=Path,help='original IBM-exported job-dbaoflpgv2cc73e75v10.zip, not included')
    args=ap.parse_args()
    private=args.raw_ibm_zip
    public=json.loads((ROOT/'data/sanitized_ibm_9bit_counts.json').read_text(encoding='utf-8'))
    prov=json.loads((ROOT/'data/sanitized_provenance.json').read_text(encoding='utf-8'))
    assert hashlib.sha256(private.read_bytes()).hexdigest()==prov['original_provider_zip_sha256'], 'Original provider ZIP hash differs'
    with zipfile.ZipFile(private) as z:
        prefix='job-dbaoflpgv2cc73e75v10'
        raw=json.loads(z.read(prefix+'-result.json'))
        info=json.loads(z.read(prefix+'-info.json'))
        assert info['id']==public['job_id'] and len(info['params']['pubs'])==16
        for i,(rec,pub,program) in enumerate(zip(public['pubs'],raw['__value__']['pub_results'],info['params']['pubs'])):
            c=pub['__value__']['data']['__value__']['fields']['c']['__value__']
            arr=np.load(io.BytesIO(zlib.decompress(base64.b64decode(c['array']['__value__']))),allow_pickle=False)
            assert arr.shape==(1024,2) and arr.dtype==np.uint8
            freq=collections.Counter(format((int(pair[0])<<8)+int(pair[1]),'09b') for pair in arr)
            assert dict(freq)==rec['counts'],i
            qpy=zlib.decompress(base64.b64decode(program[0]['__value__']))
            expected=ROOT/'circuits/original_ibm_qpy'/f'original_ibm_pub{i:02d}.qpy'
            assert qpy==expected.read_bytes(),i
    print('PASS: original private IBM ZIP checksum, all 16 complete 9-bit outcome histograms and original QPY files match the public release')
if __name__=='__main__':main()
