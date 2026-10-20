"""No account, SDK, or QPU required. Mocks exercise compile, submit, retrieve."""
from __future__ import annotations
import collections, io, json, os, tempfile, types, unittest, zipfile
from pathlib import Path
from unittest.mock import patch

from hardware import replication_core as core
from hardware import ibm_runner as runner
from reproduce import expected_center


class FakeOp:
    def __init__(self, qubits): self.qubits = tuple(range(qubits))


class FakeCircuit:
    def __init__(self, text='', name='unnamed', raw=None):
        self.text = text
        self.name = name
        self.num_qubits = 9
        self.num_clbits = 9
        self.cregs = [types.SimpleNamespace(name='c')]
        self.ops = collections.Counter()
        self.data = []
        if raw is not None:
            self.ops = collections.Counter(raw['ops'])
            self.name = raw['name']
            self.data = [FakeOp(qubits) for qubits in raw['arity']]
        else:
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith(('OPENQASM', 'include', 'qreg', 'creg')):
                    continue
                opname = line.split(' ')[0]
                self.ops[opname] += 9 if opname == 'measure' else 1
                n = {'x':1,'cx':2,'ccx':3,'reset':1,'measure':2}[opname]
                self.data.append(FakeOp(n))
    @classmethod
    def from_qasm_str(cls, text): return cls(text)
    def count_ops(self): return self.ops
    def depth(self): return len(self.data)
    def export(self): return {'name':self.name,'ops':dict(self.ops),
                              'arity':[len(x.qubits) for x in self.data]}


class FakeQPY:
    @staticmethod
    def dump(circuits, file): file.write(core.to_json_bytes([c.export() for c in circuits]))
    @staticmethod
    def load(file): return [FakeCircuit(raw=c) for c in json.loads(file.read().decode())]


class FakePassManager:
    def __init__(self, **kwargs): self.kwargs = kwargs
    def run(self, circuits):
        return circuits


class FakeBackend:
    name = 'ibm_mock_device'
    num_qubits = 127
    target = types.SimpleNamespace(operation_names={'reset','measure','cz','sx','rz','x','cx','ccx'})
    def status(self): return types.SimpleNamespace(operational=True,pending_jobs=0)


class FakeJob:
    def __init__(self, circuits, assignments, shots):
        self.assignments, self.shots = assignments, shots
    def job_id(self): return 'fake-job-public-test-only'
    def status(self): return 'DONE'
    def result(self):
        items = []
        for item in self.assignments:
            abc, arm = item['abc'], item['arm']
            b = int(abc[1])
            ones = (3*self.shots//4 if b else self.shots//4) if arm=='retained' else self.shots//16
            prep = int(abc[0]) + 2*int(abc[1]) + 4*int(abc[2])
            counts = {f'{prep:09b}':self.shots - ones,
                      f'{prep|16:09b}':ones}
            items.append(types.SimpleNamespace(data=types.SimpleNamespace(
                c=types.SimpleNamespace(get_counts=lambda cc=counts: cc))))
        return items


class FakeSampler:
    ran = 0
    assignments = []
    def __init__(self, *, mode):
        self.options = types.SimpleNamespace(
            twirling=types.SimpleNamespace(enable_gates=None, enable_measure=None),
            dynamical_decoupling=types.SimpleNamespace(enable=None),
            execution=types.SimpleNamespace(init_qubits=None))
    def run(self, circuits, *, shots):
        self.__class__.ran += 1
        assert self.options.twirling.enable_gates is False
        assert self.options.twirling.enable_measure is False
        assert self.options.dynamical_decoupling.enable is False
        assert self.options.execution.init_qubits is True
        return FakeJob(circuits, self.__class__.assignments, shots)


class FakeService:
    def __init__(self, job=None): self.job_value = job
    def backend(self,name):
        if name != FakeBackend.name: raise ValueError('wrong backend')
        return FakeBackend()
    def job(self, job_id):
        assert job_id == 'fake-job-public-test-only'
        return self.job_value
    def backends(self,**kwargs): return [FakeBackend()]


class TestHardwareRelease(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'run'
        self.sdk = (FakeCircuit, FakeQPY, FakePassManager)
        FakeSampler.ran = 0

    def compile_plan(self):
        run = runner.compile_preflight(FakeBackend(),run_dir=self.path,sdk=self.sdk)
        manifest = json.loads((run / runner.PLAN_FILE).read_text())
        FakeSampler.assignments = manifest['assignments']
        return run, manifest

    def test_source_all_16_frozen_bytes_and_no_credentials(self):
        items = core.source_conditions()
        self.assertEqual(len(items),16)
        self.assertEqual(len({x['filename'] for x in items}),16)
        self.assertFalse(any(b'\r\n' in (core.QASM_DIR/x['filename']).read_bytes() for x in items))

    def test_manifest_reordered_and_strict_mapping(self):
        m = core.create_manifest('ibm_mock_device')
        core.validate_manifest(m)
        self.assertNotEqual([x['condition'] for x in m['assignments']],
                            [x['condition'] for x in core.source_conditions()])
        m['assignments'][0],m['assignments'][1] = m['assignments'][1],m['assignments'][0]
        with self.assertRaises(ValueError): core.validate_manifest(m)

    def test_compilation_freezes_all_16_and_never_submits(self):
        run,manifest = self.compile_plan()
        self.assertEqual(manifest['expected_total_shots'],16384)
        self.assertEqual(len(manifest['native_compilation']),16)
        self.assertEqual(FakeSampler.ran,0)
        self.assertEqual(core.digest((run/runner.QPY_FILE).read_bytes()),manifest['qpy_sha256'])
        check, circuits = runner.inspect_plan(run,qpy=FakeQPY)
        self.assertEqual(len(circuits),16)
        self.assertEqual([c.name for c in circuits],[x['condition'] for x in check['assignments']])

    def test_confirmation_refuses_any_unauthorized_job(self):
        run,m = self.compile_plan()
        for phrase in ('', 'yes', 'SUBMIT', 'SUBMIT 15', 'submit 16'):
            with self.assertRaises(ValueError):
                runner.submit_precompiled(FakeService(),run,confirmation=phrase,
                                          sampler_cls=FakeSampler,qpy=FakeQPY)
        self.assertEqual(FakeSampler.ran,0)
        self.assertFalse((run/'submission_intent.json').exists())

    def test_modified_qpy_refused_even_with_authorization(self):
        run,m = self.compile_plan()
        with (run/runner.QPY_FILE).open('ab') as out: out.write(b'evil')
        with self.assertRaises(ValueError):
            runner.submit_precompiled(FakeService(),run,confirmation='SUBMIT 16',
                                      sampler_cls=FakeSampler,qpy=FakeQPY)
        self.assertEqual(FakeSampler.ran,0)

    def test_automatic_full_shot_analysis_and_shareable_export(self):
        run,m = self.compile_plan()
        job_id=runner.submit_precompiled(FakeService(),run,confirmation='SUBMIT 16',
                                         sampler_cls=FakeSampler,qpy=FakeQPY)
        self.assertEqual(job_id,'fake-job-public-test-only')
        self.assertEqual(FakeSampler.ran,1)
        with self.assertRaises(ValueError):
            runner.submit_precompiled(FakeService(),run,confirmation='SUBMIT 16',
                                      sampler_cls=FakeSampler,qpy=FakeQPY)
        self.assertEqual(FakeSampler.ran,1)
        original_inspect = runner.inspect_plan
        with patch.object(runner,'inspect_plan',side_effect=lambda path:original_inspect(path,qpy=FakeQPY)):
            fake_job=FakeJob([],m['assignments'],m['shots_per_circuit'])
            summary=runner.retrieve_job(FakeService(fake_job),run)
            self.assertEqual(summary['shots'],16384)
            self.assertAlmostEqual(summary['difference_in_differences'],0.5)
            self.assertTrue(summary['positive_history_effect_shot_only'])
            self.assertTrue((run/'replication_per_condition.csv').exists())
            with self.assertRaises(ValueError): runner.retrieve_job(FakeService(fake_job),run)
            with patch.object(runner,'EXPORTS',Path(self.temp.name)/'exports'):
                bundle=runner.export_public(run)
                with zipfile.ZipFile(bundle) as z:
                    names=z.namelist()
                    self.assertEqual(set(names),{'manifest.json','sanitized_counts.json',
                                                  'analysis.json','public_job_reference.json','per_condition.csv','compiled_isa.qpy'})
                    txt=''.join(z.read(n).decode() for n in names if not n.endswith('.qpy'))
                    self.assertNotIn('instance',txt.lower())
                    self.assertNotIn('token',txt.lower())
                    self.assertNotIn('account_id',txt.lower())

    def test_non_complete_job_never_calls_results(self):
        run,m = self.compile_plan()
        runner.submit_precompiled(FakeService(),run,confirmation='SUBMIT 16',
                                  sampler_cls=FakeSampler,qpy=FakeQPY)
        job=types.SimpleNamespace(status=lambda:'QUEUED',result=lambda: (_ for _ in ()).throw(AssertionError('should not call result')))
        original_inspect = runner.inspect_plan
        with patch.object(runner,'inspect_plan',side_effect=lambda path:original_inspect(path,qpy=FakeQPY)):
            self.assertIsNone(runner.retrieve_job(FakeService(job),run))
        self.assertFalse((run/runner.RESULT_FILE).exists())

    def test_analyzer_rejects_missing_shots_or_shuffled_data(self):
        m=core.create_manifest('ibm_mock_device')
        items=[]
        for entry in m['assignments']:
            items.append({'pub':entry['pub'],'condition':entry['condition'],
                          'counts':{'000000000':1024}})
        core.validate_data(m,items)
        items[0]['counts']={'000000000':1023}
        with self.assertRaises(ValueError):core.analyze(m,items)
        items[0]['counts']={'000000000':1024}
        items[0]['condition']='wrong name'
        with self.assertRaises(ValueError):core.analyze(m,items)

    def test_invalid_measured_bitstrings_or_noninteger_shots_rejected(self):
        for bad in [{'xx':4},{'1111111111':4},{'000':-1},{'0':3.3},{'010110001':'9'}]:
            with self.assertRaises(ValueError):core.normalize_counts(bad)

    def test_original_reference_still_reproduces(self):
        from reproduce import calculate, check_known_results
        summary,rows=calculate()
        check_known_results(summary,rows)
        self.assertAlmostEqual(summary['difference_in_differences'],core.HISTORICAL_DID)

    def test_credentials_not_written_in_public_manifest(self):
        run,m = self.compile_plan()
        txt=(run/runner.PLAN_FILE).read_text()
        self.assertNotIn('account',txt.lower())
        self.assertNotIn('password',txt.lower())
        self.assertNotIn('token',txt.lower())
        self.assertNotIn('crn',txt.lower())

    def test_cannot_overwrite_existing_plan(self):
        run,m = self.compile_plan()
        with self.assertRaises(ValueError):runner.compile_preflight(FakeBackend(),run_dir=run,sdk=self.sdk)


if __name__ == '__main__':unittest.main()
