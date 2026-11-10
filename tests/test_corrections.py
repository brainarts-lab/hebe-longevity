"""Correcting and deleting saved blood draws, in Hebe and in the person's PLSI record."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hebe.plans import Plans
from hebe.plsi_bridge import Plsi, PlsiError
from hebe.service import Service

DEMO = (ROOT / 'data' / 'demo.csv').read_text()


def draw(person='me', date='2026-10-20', crp=None):
    lines = DEMO.replace('alex-demo', person).replace('2026-10-20', date).replace('draw-1', 'draw-' + date).splitlines()
    if crp is not None:
        lines = [(l.rsplit(',', 2)[0] + f',{crp},' + l.rsplit(',', 1)[1]) if ',crp,' in l else l for l in lines]
    return ('\n'.join(lines) + '\n').encode()


class Corrections(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.s = Service(self.home)

    def tearDown(self):
        self.tmp.cleanup()

    def save(self, data, replaces=None):
        return self.s.commit(self.s.preview(data, 1981, 'me', replaces)['id'], True)

    def crp(self):
        return Plans(self.home).state('me')['coordinates']

    def test_correction_replaces_the_draw_and_recalculates(self):
        first = self.save(draw(crp='0.5'))
        (self.home / f'report-{first["id"]}.html').write_text('old')
        fixed = self.save(draw(crp='0.2'), replaces=first['id'])
        history = self.s.history('me')
        self.assertEqual([r['id'] for r in history], [fixed['id']])
        self.assertEqual(fixed['corrects'], first['id'])
        self.assertNotAlmostEqual(fixed['pheno_age'], first['pheno_age'])
        self.assertFalse((self.home / f'report-{first["id"]}.html').exists())

    def test_correction_cannot_land_on_another_saved_date_or_another_person(self):
        first = self.save(draw(date='2026-10-20'))
        self.save(draw(date='2025-10-14'))
        moved = self.s.preview(draw(date='2025-10-14', crp='0.3'), 1981, 'me', first['id'])
        with self.assertRaises(ValueError):
            self.s.commit(moved['id'], True)
        with self.assertRaises(ValueError):
            self.s.preview(draw(person='someone'), 1981, 'someone', first['id'])
        self.assertEqual(len(self.s.history('me')), 2)

    def test_correction_of_a_draw_deleted_meanwhile_saves_nothing(self):
        a = self.save(draw(date='2026-10-20')); self.save(draw(date='2025-10-14'))
        p = self.s.preview(draw(crp='0.3'), 1981, 'me', a['id'])
        self.s.delete_draw(a['id'])
        with self.assertRaises(ValueError):
            self.s.commit(p['id'], True)
        self.assertEqual(len(self.s.history('me')), 1)

    def test_plsi_retracts_corrected_and_deleted_values(self):
        early = self.save(draw(date='2025-10-14', crp='0.4'))
        late = self.save(draw(date='2026-10-20', crp='0.5'))
        self.assertEqual(self.crp()['crp']['value'], 0.5)
        fixed = self.save(draw(date='2026-10-20', crp='0.2'), replaces=late['id'])
        self.assertEqual(self.crp()['crp']['value'], 0.2)
        self.s.delete_draw(fixed['id'])
        state = self.crp()
        self.assertEqual(state['crp']['value'], 0.4)
        self.assertTrue(str(state['crp']['observed_at']).startswith('2025-10-14'))
        log = (self.home / 'plsi' / 'me' / 'events.jsonl').read_text().splitlines()
        self.assertTrue(any(json.loads(l)['type'] == 'retraction' for l in log))
        self.assertEqual([r['id'] for r in self.s.history('me')], [early['id']])

    def test_deleting_the_last_draw_removes_the_person_everywhere(self):
        only = self.save(draw())
        Plans(self.home).state('me')
        self.assertTrue((self.home / 'plsi' / 'me').is_dir())
        with self.s.db() as db:
            db.execute("INSERT INTO plan_drafts (id, person, body, created) VALUES ('x', 'me', '{}', 0)")
        self.s.delete_draw(only['id'])
        self.assertEqual(self.s.results(), [])
        self.assertFalse((self.home / 'plsi' / 'me').exists())
        with self.s.db() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM plan_drafts').fetchone()[0], 0)

    def test_delete_person_leaves_other_people_alone(self):
        self.save(draw())
        other = self.s.commit(self.s.preview(draw(person='partner'), 1980, 'partner')['id'], True)
        out = self.s.delete_person('me')
        self.assertEqual(out['draws'], 1)
        self.assertEqual([r['id'] for r in self.s.results()], [other['id']])
        for bad in ('../plsi', 'nobody', ''):
            with self.assertRaises(ValueError):
                self.s.delete_person(bad)

    def test_demo_values_cannot_be_corrected(self):
        demo = self.s.commit(self.s.preview(DEMO.encode(), 1981, 'alex-demo')['id'], True)
        with self.assertRaises(ValueError):
            self.s.preview(draw(person='alex-demo', crp='0.2'), 1981, 'alex-demo', demo['id'])

    def test_record_from_an_older_hebe_is_rebuilt_unless_it_holds_started_plans(self):
        self.save(draw())
        plsi = Plsi(self.home)
        plsi.run('init', '--instance', 'me', '--birth-year', 1981, '--relation', 'self')
        csv = self.home / 'legacy.csv'
        csv.write_text('effective_at,text,value,unit,code_system,code\n2026-10-20T12:00:00Z,crp,0.9,mg/dL,loinc,1988-5\n')
        plsi.run('ingest', '--instance', 'me', '--csv', csv)
        with self.assertRaises(PlsiError):
            plsi.sync(self.s.history('me'), has_plans=True)
        plsi.sync(self.s.history('me'))
        self.assertEqual(self.crp()['crp']['value'], 0.1)


if __name__ == '__main__':
    unittest.main()
