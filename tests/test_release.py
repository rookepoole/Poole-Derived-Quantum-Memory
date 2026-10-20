"""Credential-free regression tests for the complete public v2.4 release."""
from __future__ import annotations
import hashlib,io,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import reproduce
from verify_reconstructed_circuits import simulate

class TestRelease(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary,cls.rows=reproduce.calculate()
    def test_original_job_identity_and_all_shots(self):
        self.assertEqual(self.summary['job_id'],'dbaoflpgv2cc73e75v10')
        self.assertEqual(self.summary['backend'],'ibm_kingston')
        self.assertEqual(self.summary['n_circuits'],16)
        self.assertEqual(self.summary['shots'],16384)
        self.assertEqual(sum(r['shots'] for r in self.rows),16384)
    def test_all_16_per_pub_expected_predictions(self):
        for r in self.rows:
            self.assertEqual(r['ideal_final_center'],reproduce.expected_center(r['abc'],r['arm']))
            self.assertEqual(len(r['first_generation']),5)
            self.assertTrue(r['preparation_match']>512)
    def test_reproduces_gold_counts(self):
        reproduce.check_known_results(self.summary,self.rows)
        self.assertEqual(self.summary['correct_final_center'],15272)
        self.assertEqual(sum(r['preparation_match'] for r in self.rows),12896)
    def test_correct_ci(self):
        self.assertAlmostEqual(self.summary['difference_in_differences'],.6455078125)
        lo,hi=self.summary['difference_in_differences_95pct_normal_shot_only']
        self.assertAlmostEqual(lo,.6269827871341045,places=13)
        self.assertAlmostEqual(hi,.6640328378658955,places=13)
    def test_sanitized_no_account_metadata(self):
        a=json.loads((ROOT/'data/sanitized_ibm_9bit_counts.json').read_text())
        b=json.loads((ROOT/'data/sanitized_provenance.json').read_text())
        for x in (a,b):
            self.assertNotIn('user_id',x)
            self.assertNotIn('params',x)
            self.assertNotIn('api_token',x)
        self.assertNotIn('pub_results',a)
        self.assertFalse(b['raw_provider_zip_included'])
    def test_actual_qpy_binary_hashes(self):
        b=json.loads((ROOT/'data/sanitized_provenance.json').read_text())
        self.assertEqual(len(b['original_compiled_qpy']),16)
        for q in b['original_compiled_qpy']:
            f=ROOT/'circuits/original_ibm_qpy'/q['filename']
            raw=f.read_bytes()
            self.assertTrue(raw.startswith(b'QISKIT'))
            self.assertEqual(q['qpy_version'],17)
            self.assertEqual(hashlib.sha256(raw).hexdigest(),q['sha256'])
    def test_all_reconstructed_qasm_behavior(self):
        for i in range(8):
            abc=f'{i:03b}'
            for arm in ('retained','erased'):
                f=ROOT/'circuits/reconstructed_qasm'/f'v24_{abc}_{arm}.qasm'
                mid,fin=simulate(f.read_text())
                self.assertEqual(mid[3:8],reproduce.source_f1(abc))
                self.assertEqual(fin[4],reproduce.expected_center(abc, 'retain' if arm=='retained' else 'erase'))
                self.assertEqual(fin[8],0)
                self.assertEqual(fin[:3],tuple(map(int,abc)))
    def test_windows_newlines_do_not_mutate_qasm(self):
        from circuits.generate_reconstructed_qasm import emit
        with tempfile.TemporaryDirectory() as temp:
            emit(temp)
            for original in sorted((ROOT/'circuits/reconstructed_qasm').glob('*.qasm')):
                generated=(Path(temp)/original.name).read_bytes()
                self.assertEqual(generated,original.read_bytes(),original.name)
                self.assertNotIn(b'\r\n',generated)
    def test_f2_off_sector_explicitly_disclosed(self):
        d=json.loads((ROOT/'data/verified_off_sector_counterexamples.json').read_text())
        self.assertEqual(d['variations_per_background'],16)
        self.assertEqual(d['mismatches_per_background'],{'000':4,'011':4,'111':4})
        self.assertEqual(len(d['examples']),12)
    def test_no_original_private_zip_in_public(self):
        self.assertEqual(list(ROOT.rglob('job-dbaoflpgv2cc73e75v10.zip')),[])

if __name__=='__main__':unittest.main()
