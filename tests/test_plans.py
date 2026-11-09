"""Plans run against the vendored, unchanged PLSI toolbelt (child process, no network)."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hebe.agent_tools import run_tool
from hebe.commands import handle
from hebe.plans import Plans
from hebe.plsi_bridge import Plsi, PlsiError

PLAN = {"objective": "lower phenoage_acceleration over 90 days",
        "actions": [{"local_id": "a1", "description": "Brisk walking 30 minutes", "category": "exercise",
                     "dose": "30 min", "schedule": "5 days a week"}],
        "claims": [{"local_id": "c1", "statement": "Regular aerobic exercise may lower CRP",
                    "evidence_class": "hypothesis_only", "supports": ["a1"]}],
        "predictions": [
            {"local_id": "p1", "map_id": "blood_phenoage", "coordinate": "phenoage_acceleration",
             "target": "change_from_baseline", "horizon_days": 90, "expected": -0.5, "low": -2, "high": 1,
             "interval_level": 0.8, "method": "assumption", "evidence_class": "hypothesis_only",
             "basis": [{"kind": "rule", "id": "plsi.derive.phenoage"}], "driven_by": ["a1"]},
            {"local_id": "p0", "map_id": "blood_phenoage", "coordinate": "phenoage_acceleration",
             "target": "change_from_baseline", "horizon_days": 90, "expected": 0, "low": -1.5, "high": 1.5,
             "method": "no-action control", "evidence_class": "rule_derived",
             "basis": [{"kind": "rule", "id": "plsi.derive.phenoage"}], "driven_by": []}],
        "revision_rule": {"review_after_days": 90, "continue_if": "p1 within interval", "modify_if": "no change",
                          "stop_if": "adverse effect"}}


class Answer:
    def __init__(self, value): self.value = value; self.asked = []
    def ask_choice(self, question, choices): self.asked.append(question); return self.value


class Planning(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.home = cls.tmp.name
        handle(Answer('save'), cls.home, '')

    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()

    def plans(self): return Plans(self.home)

    def recorded(self):
        return self.plans().overview('alex-demo')['plans']

    def test_state_comes_from_original_plsi_and_matches_hebe(self):
        state = self.plans().state('alex-demo')
        self.assertAlmostEqual(state['coordinates']['phenoage']['value'], 37.24779932614395, places=9)

    def test_rxnorm_code_outside_drug_category_is_refused_before_plsi(self):
        bad = json.loads(json.dumps(PLAN))
        bad['actions'].append({"local_id": "a2", "description": "Take test-drug-a", "category": "other",
                               "code": {"system": "rxnorm", "code": "12345"}})
        out = json.loads(run_tool('hebe_plan_check', self.home, {'person_id': 'alex-demo', 'plan': bad}))
        self.assertFalse(out['ok']); self.assertEqual(out['stage'], 'hebe_gate'); self.assertNotIn('plan_id', out)

    def test_challenger_sees_only_plan_state_and_screening(self):
        checked = self.plans().check('alex-demo', PLAN)
        self.assertTrue(checked['ok'], checked)
        seen = []
        out = self.plans().challenge(checked['plan_id'], lambda m: seen.append(m) or 'VERDICT: no objections')
        self.assertEqual(out['objections'], 'VERDICT: no objections')
        system, user = seen[0]
        self.assertIn('PLSI Challenger', system['content'])
        self.assertEqual(set(json.loads(user['content'])), {'plan', 'state', 'screening', 'plan_check'})

    def test_only_the_user_dialog_starts_a_challenged_plan_once(self):
        plan = json.loads(json.dumps(PLAN)); plan['objective'] = 'lower phenoage_acceleration, start test'
        checked = self.plans().check('alex-demo', plan)
        pid = checked['plan_id'][:12]
        before = len(self.recorded())
        # Tools cannot start plans
        for name in ('hebe_plan_start', 'hebe_plan_record'):
            self.assertFalse(json.loads(run_tool(name, self.home, {'plan_id': pid}))['ok'])
        self.assertIn('Run the challenger first', handle(Answer('start'), self.home, f'plan start {pid} 2026-11-10'))
        self.plans().challenge(pid, lambda m: '[minor] p1 interval is wide\nVERDICT: no objections')
        declined = Answer('cancel')
        self.assertIn('Not started', handle(declined, self.home, f'plan start {pid} 2026-11-10'))
        self.assertIn('Brisk walking', declined.asked[0]); self.assertIn('p1 interval is wide', declined.asked[0])
        self.assertEqual(len(self.recorded()), before)
        out = handle(Answer('start'), self.home, f'plan start {pid} 2026-11-10')
        self.assertIn('Plan started as plan_', out)
        adopted = [p for p in self.recorded() if p['objective'] == plan['objective']]
        self.assertEqual([p['state'] for p in adopted], ['adopted'])
        self.assertIn('already started', handle(Answer('start'), self.home, f'plan start {pid} 2026-11-10'))
        self.assertEqual(len(self.recorded()), before + 1)

    def test_caution_waits_for_the_user_and_is_acknowledged_at_start(self):
        plan = json.loads(json.dumps(PLAN)); plan['objective'] = 'lower phenoage_acceleration, caution test'
        findings = {'a1': [{'severity': 'caution', 'source': {'kind': 'pmid', 'id': '16818923'}, 'summary': 'Older study population.'}]}
        checked = self.plans().check('alex-demo', plan, findings)
        self.assertTrue(checked['ok'], checked)
        self.assertEqual(checked['awaiting_user_acknowledgement'], ['a1']); self.assertEqual(checked['violations'], [])
        self.plans().challenge(checked['plan_id'], lambda m: 'VERDICT: no objections')
        out = self.plans().start(checked['plan_id'], '2026-11-10')
        self.assertFalse(out['already_started'])

    def test_unverified_source_violation_is_named_for_the_model(self):
        plan = json.loads(json.dumps(PLAN)); plan['objective'] = 'lower phenoage_acceleration, unverified source'
        plan['claims'][0]['sources'] = [{'kind': 'pmid', 'id': '99999999'}]  # never verified: PLSI rule G5
        checked = self.plans().check('alex-demo', plan)
        self.assertFalse(checked['ok']); self.assertTrue(checked['violations'])
        self.assertTrue(all(':' in v for v in checked['violations']))

    def test_bridge_allowlist_blocks_other_plsi_commands(self):
        for args in (('mothership', 'join'), ('plan', 'review'), ('retract',), ('feedback', 'send')):
            with self.subTest(args=args), self.assertRaises(PlsiError):
                Plsi(self.home).run(*args)


class Vendor(unittest.TestCase):
    def test_vendored_plsi_is_unchanged_and_complete(self):
        manifest = json.loads((ROOT / 'vendor' / 'plsi.manifest.json').read_text())
        self.assertEqual(manifest['commit'], '17c433c4a9ecb54279ab02ba1d7d63ee8e8a2e81')
        base = ROOT / 'vendor' / 'plsi'
        present = {str(p.relative_to(base)) for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        self.assertEqual(present, set(manifest['files']))
        for name, digest in manifest['files'].items():
            self.assertEqual(hashlib.sha256((base / name).read_bytes()).hexdigest(), digest, name)


if __name__ == '__main__': unittest.main()
