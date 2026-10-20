#!/usr/bin/env python3
"""Verify the release's non-mutating artifact checksums (stdlib only)."""
import hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    lines=(ROOT/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines()
    for line in lines:
        if not line.strip():continue
        digest,rel=line.split('  ',1)
        f=ROOT/rel
        if not f.is_file():raise RuntimeError('Missing release file '+rel)
        if hashlib.sha256(f.read_bytes()).hexdigest()!=digest:raise RuntimeError('SHA mismatch for '+rel)
    print(f'PASS: {len(lines)} frozen release-file hashes')
if __name__=='__main__':main()
