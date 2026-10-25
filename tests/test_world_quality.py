"""Review feedback cannot bypass rendering checks or publish a worse candidate."""
from pathlib import Path
import copy
import importlib
import json
import hashlib
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/interactive'))


def review(score,parameters=None,passed=False,issues=None):
    return {'overallScore':score,'dimensions':{key:score for key in (
        'fidelity','layering','occlusion','motion','interaction')},'passed':passed,
        'issues':issues or [],'suggestedParameters':parameters or {},'summary':'真实单元测试边界，不作为模型实测。'}


class WorldQualityTests(unittest.TestCase):
    def test_portable_evidence_checks_hash_and_confines_paths_to_project(self):
        module=self.module()
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as folder:
            path=Path(folder)/'frame.jpg';path.write_bytes(b'real saved test file')
            frame={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
            portable=module.portable_record(frame)
            self.assertFalse(Path(portable['path']).is_absolute())
            self.assertTrue(module.evidence_intact(portable))
            path.write_bytes(b'tampered')
            self.assertFalse(module.evidence_intact(portable))
            self.assertFalse(module.evidence_intact({'path':'../outside','sha256':'a'*64}))

    def module(self):
        try:return importlib.import_module('world_quality')
        except ModuleNotFoundError:self.fail('world_quality implementation is missing')

    def test_unknown_parameters_and_nonfinite_values_cannot_change_assets(self):
        module=self.module()
        for bad in ({'source':'other.png'},{'haze':True},{'depth_amplitude':float('nan')},
                    {'yaw_limit_deg':90},{'subject_relief':-1}):
            with self.subTest(bad=bad),self.assertRaises(ValueError):module.validate_parameters(bad)
        self.assertEqual(module.validate_parameters({'haze':.04}),{'haze':.04})

    def test_approved_label_does_not_override_browser_failure(self):
        module=self.module()
        self.assertFalse(module.review_passes(review(99,passed=True),{'passed':False}))
        self.assertFalse(module.review_passes(review(99,passed=True,issues=[
            {'severity':'blocker','code':'shape','description':'轮廓破损'}]),{'passed':True}))
        self.assertTrue(module.review_passes(review(92,passed=True),{'passed':True}))

    def test_stale_same_slug_render_is_rejected_by_manifest_hash(self):
        module=self.module()
        manifest={'slug':'own-case','camera':{'depth_amplitude':.24}}
        stale={'manifest_sha256':module.manifest_fingerprint({'slug':'own-case','camera':{'depth_amplitude':.4}}),
               'checks':{'passed':True}}
        self.assertFalse(module.verify_capture(manifest,stale)['checks']['passed'])
        current={'manifest_sha256':module.manifest_fingerprint(manifest),'checks':{'passed':True}}
        self.assertTrue(module.verify_capture(manifest,current)['checks']['passed'])

    def test_high_scoring_blocker_cannot_replace_clean_best(self):
        module=self.module()
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as folder:
            world=Path(folder);original={'slug':'own-case','camera':{'depth_amplitude':.24},'provenance':{}}
            (world/'world.json').write_text(json.dumps(original))
            scores=iter([review(70,{'depth_amplitude':.35}),review(99,issues=[
                {'severity':'blocker','code':'tear','description':'侧视轮廓撕裂'}])])
            result=module.optimize_candidates(world,lambda i,m:{'checks':{'passed':True},'frames':[]},
                lambda e,h:next(scores),max_rounds=2)
            self.assertEqual(result['selectedRound'],0)
            self.assertEqual(json.loads((world/'world.json').read_text())['camera']['depth_amplitude'],.24)

    def test_failed_capture_spends_no_cloud_request_and_keeps_original(self):
        module=self.module()
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as folder:
            world=Path(folder);original={'slug':'own-case','camera':{'depth_amplitude':.24},'provenance':{}}
            (world/'world.json').write_text(json.dumps(original))
            calls=[]
            def paid_review(*_):calls.append(True);return review(90,passed=True)
            result=module.optimize_candidates(world,lambda i,m:{'checks':{'passed':False},'frames':[]},paid_review)
            self.assertEqual(result['status'],'unverified')
            self.assertEqual(result['rounds'],0)
            self.assertEqual(calls,[])

    def test_interruption_restores_original_before_propagating(self):
        module=self.module()
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as folder:
            world=Path(folder);original={'slug':'own-case','camera':{'depth_amplitude':.24},'provenance':{}}
            (world/'world.json').write_text(json.dumps(original))
            def capture(index,manifest):
                if index:raise KeyboardInterrupt()
                return {'checks':{'passed':True},'frames':[]}
            with self.assertRaises(KeyboardInterrupt):
                module.optimize_candidates(world,capture,lambda e,h:review(70,{'depth_amplitude':.4}))
            self.assertEqual(json.loads((world/'world.json').read_text())['camera']['depth_amplitude'],.24)

    def test_case_files_restore_from_same_snapshot_as_selected_world(self):
        module=self.module()
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as folder:
            root=Path(folder);case=root/'case';case.mkdir();output=root/'output';world=root/'world';world.mkdir()
            selected={'slug':'own-case','title':'新标题','camera':{'depth_amplitude':.3}}
            for index,title in ((0,'旧标题'),(1,'新标题')):
                snapshot=output/f'round-{index}'/'case-snapshot';snapshot.mkdir(parents=True)
                module.write_json(snapshot/'world.json',{**selected,'title':title})
                for name in ('metadata.json','experience.json','interaction-analysis.json'):
                    module.write_json(snapshot/name,{'title':title})
            module.write_json(world/'world.json',selected)
            module.restore_case_snapshot(case,output,world)
            self.assertEqual(json.loads((case/'experience.json').read_text(encoding='utf-8'))['title'],'新标题')

    def test_three_round_limit_and_best_candidate_restoration(self):
        module=self.module()
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as folder:
            world=Path(folder)/'world';world.mkdir()
            initial={'slug':'own-case','art':{'file':'art.webp'},'camera':{'depth_amplitude':.24},
                     'provenance':{'source_image_sha256':'a'*64,'asset_revision':'old'}}
            (world/'world.json').write_text(json.dumps(initial),encoding='utf-8')
            scores=iter([review(65,{'depth_amplitude':.35}),review(88,{'depth_amplitude':.45}),
                         review(70,{'depth_amplitude':.4})])
            captures=[]
            def capture(round_index,manifest):
                captures.append(copy.deepcopy(manifest))
                return {'checks':{'passed':True},'frames':[],'snapshots':{}}
            result=module.optimize_candidates(world,capture,lambda evidence,history:next(scores),max_rounds=99)
            self.assertEqual(result['rounds'],3)
            self.assertEqual(result['selectedRound'],1)
            self.assertEqual(result['status'],'needs_review')
            self.assertEqual(json.loads((world/'world.json').read_text())['camera']['depth_amplitude'],.35)
            self.assertEqual(result['finalScore'],88)
            self.assertTrue(result['improved'])
            self.assertEqual(len(captures),3)
            self.assertEqual(captures[2]['provenance']['source_image_sha256'],'a'*64)

    def test_unsupported_or_worse_suggestions_leave_original_usable(self):
        module=self.module()
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as folder:
            world=Path(folder);manifest={'slug':'own-case','camera':{'depth_amplitude':.24},'provenance':{}}
            (world/'world.json').write_text(json.dumps(manifest))
            result=module.optimize_candidates(world,lambda i,m:{'checks':{'passed':True},'frames':[]},
                lambda e,h:review(64,{'execute':'rm -rf'}))
            self.assertEqual(result['selectedRound'],0)
            self.assertEqual(result['status'],'needs_review')
            self.assertFalse(result['improved'])
            self.assertEqual(json.loads((world/'world.json').read_text())['camera']['depth_amplitude'],.24)

    def test_service_failure_restores_highest_valid_state_and_reports_unverified(self):
        module=self.module()
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as folder:
            world=Path(folder);manifest={'slug':'own-case','camera':{'depth_amplitude':.24},'provenance':{}}
            (world/'world.json').write_text(json.dumps(manifest))
            def failed(*_):raise RuntimeError('synthetic failure includes sk-DO-NOT-PRINT')
            result=module.optimize_candidates(world,lambda i,m:{'checks':{'passed':True},'frames':[]},failed)
            self.assertEqual(result['status'],'unverified')
            self.assertNotIn('sk-',json.dumps(result))
            self.assertEqual(json.loads((world/'world.json').read_text())['camera']['depth_amplitude'],.24)


if __name__=='__main__':unittest.main(verbosity=2)
