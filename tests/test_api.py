"""Hebe page backend: the page can preview, but saving and starting need a fresh, matching confirmation."""
import sys
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
except ImportError:  # the plain test venv has no FastAPI; Hermes' Python does
    FastAPI = None
from hebe.service import Service


@unittest.skipIf(FastAPI is None, 'FastAPI not installed')
class Page(unittest.TestCase):
    def setUp(self):
        from hebe.api import create_router
        self.tmp = tempfile.TemporaryDirectory()
        app = FastAPI(); app.include_router(create_router(lambda: self.tmp.name), prefix='/api')
        self.c = TestClient(app)

    def tearDown(self): self.tmp.cleanup()

    def post(self, path, body, **kw): return self.c.post('/api' + path, json=body, **kw)

    def test_demo_preview_then_confirmed_save_then_report(self):
        boot = self.c.get('/api/bootstrap').json()
        self.assertEqual(boot['people'], []); self.assertTrue(boot['demo_available'])
        p = self.post('/preview', {'source': 'demo'}).json()
        self.assertEqual(len(p['markers']), 9); self.assertTrue(p['demo'])
        self.assertEqual(Service(self.tmp.name).results(), [])
        token = self.post('/confirm', {'action': 'save', 'id': p['id']}).json()['confirmation']
        saved = self.post('/save', {'id': p['id'], 'confirmation': token}).json()
        self.assertAlmostEqual(saved['saved']['pheno_age'], 37.2478, places=3)
        html = self.c.get(f"/api/report/{saved['saved']['id']}").json()['html']
        self.assertIn('Blood PhenoAge', html)
        # a used token cannot save again
        p2 = self.post('/preview', {'source': 'demo'}).json()
        self.assertEqual(self.post('/save', {'id': p2['id'], 'confirmation': token}).status_code, 400)

    def test_save_without_or_with_mismatched_confirmation_saves_nothing(self):
        p = self.post('/preview', {'source': 'demo'}).json()
        self.assertEqual(self.post('/save', {'id': p['id']}).status_code, 422)
        other = self.post('/confirm', {'action': 'save', 'id': 'f' * 64}).json()['confirmation']
        self.assertEqual(self.post('/save', {'id': p['id'], 'confirmation': other}).status_code, 400)
        self.assertEqual(Service(self.tmp.name).results(), [])

    def test_cross_origin_and_non_json_writes_are_refused(self):
        self.assertEqual(self.post('/preview', {'source': 'demo'}, headers={'origin': 'https://evil.example'}).status_code, 403)
        self.assertEqual(self.c.post('/api/preview', content='source=demo',
                                     headers={'content-type': 'application/x-www-form-urlencoded'}).status_code, 415)

    def test_csv_import_needs_person_and_birth_year(self):
        csv = (ROOT / 'data' / 'demo.csv').read_text()
        self.assertEqual(self.post('/preview', {'source': 'csv', 'csv': csv, 'person_id': 'me'}).status_code, 400)
        self.assertEqual(self.post('/preview', {'source': 'csv', 'csv': csv, 'birth_year': 1981, 'person_id': '../x'}).status_code, 400)

    def test_typed_values_in_lab_units_preview_with_conversions(self):
        rows = [('albumin', '4.4', 'g/dL'), ('creatinine', '0.9', 'mg/dL'), ('glucose', '90', 'mg/dL'), ('crp', '1', 'mg/L'),
                ('lymphocyte_pct', '30', '%'), ('mcv', '90', 'fL'), ('rdw', '13', '%'), ('alp', '60', 'U/L'), ('wbc', '5', '10*9/L')]
        csv = 'person_id,draw_id,collected_at,observation_id,status,marker,value,unit\n' + ''.join(
            f'me,draw-2026-10-01,2026-10-01,m{i},final,{m},{v},{u}\n' for i, (m, v, u) in enumerate(rows))
        p = self.post('/preview', {'source': 'csv', 'csv': csv, 'birth_year': 1980, 'person_id': 'me'}).json()
        self.assertEqual(len(p['markers']), 9); self.assertGreaterEqual(p['conversions'], 4)
        self.assertEqual(self.c.get('/api/template').json()['csv'].splitlines()[1].split(',')[0], 'me')

    def demo(self):
        p = self.post('/preview', {'source': 'demo'}).json()
        token = self.post('/confirm', {'action': 'save', 'id': p['id']}).json()['confirmation']
        return self.post('/save', {'id': p['id'], 'confirmation': token}).json()['saved']

    def test_delete_needs_a_confirmation_for_exactly_that_draw(self):
        first = self.demo(); second = self.demo()
        self.assertEqual(self.post('/delete', {'id': first['id']}).status_code, 422)
        wrong = self.post('/confirm', {'action': 'delete', 'id': second['id']}).json()['confirmation']
        self.assertEqual(self.post('/delete', {'id': first['id'], 'confirmation': wrong}).status_code, 400)
        save_token = self.post('/confirm', {'action': 'save', 'id': first['id']}).json()['confirmation']
        self.assertEqual(self.post('/delete', {'id': first['id'], 'confirmation': save_token}).status_code, 400)
        self.assertEqual(len(Service(self.tmp.name).results()), 2)
        token = self.post('/confirm', {'action': 'delete', 'id': first['id']}).json()['confirmation']
        out = self.post('/delete', {'id': first['id'], 'confirmation': token}).json()
        self.assertEqual(len(out['people'][0]['draws']), 1); self.assertTrue(out['demo_available'])

    def test_delete_person_brings_back_the_start_page(self):
        self.demo()
        self.assertEqual(self.post('/confirm', {'action': 'delete_person', 'id': 'nobody'}).status_code, 400)
        token = self.post('/confirm', {'action': 'delete_person', 'id': 'alex-demo'}).json()['confirmation']
        out = self.post('/delete-person', {'id': 'alex-demo', 'confirmation': token}).json()
        self.assertEqual(out['people'], []); self.assertEqual(out['draws'], 1)
        self.assertEqual(self.c.get('/api/bootstrap').json()['people'], [])

    def test_draw_prefills_a_correction_that_replaces_it(self):
        rows = [('albumin', '4.4', 'g/dL'), ('creatinine', '0.9', 'mg/dL'), ('glucose', '90', 'mg/dL'), ('crp', '1', 'mg/L'),
                ('lymphocyte_pct', '30', '%'), ('mcv', '90', 'fL'), ('rdw', '13', '%'), ('alp', '60', 'U/L'), ('wbc', '5', '10*9/L')]
        def csv(crp):
            return 'person_id,draw_id,collected_at,observation_id,status,marker,value,unit\n' + ''.join(
                f'me,draw-2026-10-01,2026-10-01,m{i},final,{m},{crp if m == "crp" else v},{u}\n' for i, (m, v, u) in enumerate(rows))
        def save(body):
            p = self.post('/preview', body).json()
            token = self.post('/confirm', {'action': 'save', 'id': p['id']}).json()['confirmation']
            return p, self.post('/save', {'id': p['id'], 'confirmation': token}).json()
        _, out = save({'source': 'csv', 'csv': csv('1'), 'birth_year': 1980, 'person_id': 'me'})
        old = out['saved']['id']
        draw = self.c.get(f'/api/draw/{old}').json()
        self.assertIn({'marker': 'albumin', 'value': '4.4', 'unit': 'g/dL'}, draw['rows'])
        self.assertEqual(draw['birth_year'], 1980)
        p, out = save({'source': 'csv', 'csv': csv('2'), 'birth_year': 1980, 'person_id': 'me', 'replaces': old})
        self.assertEqual(p['replaces'], old)
        draws = out['people'][0]['draws']
        self.assertEqual(len(draws), 1); self.assertTrue(draws[0]['corrected']); self.assertNotEqual(draws[0]['id'], old)
        self.assertEqual(self.c.get(f'/api/draw/{old}').status_code, 400)


if __name__ == '__main__': unittest.main()
