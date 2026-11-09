import csv
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

class ImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.rows = [dict(person_id='alex-demo',draw_id='draw-1',collected_at='2026-10-20',observation_id=str(i),status='final',marker=m,value=str(v),unit=u) for i,(m,v,u) in enumerate([
            ('albumin',44,'g/L'),('creatinine',80,'umol/L'),('glucose',5,'mmol/L'),('crp',.1,'mg/dL'),('lymphocyte_pct',30,'%'),('mcv',90,'fL'),('rdw',13,'%'),('alp',60,'U/L'),('wbc',5,'10*3/uL')])]
    def payload(self):
        b=io.StringIO(); w=csv.DictWriter(b,fieldnames=list(self.rows[0])); w.writeheader();w.writerows(self.rows);return b.getvalue().encode()
    def api(self):
        try: from hebe.service import Service
        except ImportError: self.fail('Hebe import service not implemented')
        return Service(self.home)
    def test_approval_required_and_idempotent(self):
        s=self.api();p=s.preview(self.payload(),1981,'alex-demo');self.assertEqual(s.results(),[])
        with self.assertRaises(ValueError):s.commit(p['id'],False)
        r=s.commit(p['id'],True);self.assertAlmostEqual(r['pheno_age'],37.2478,places=3)
        self.assertEqual(s.commit(p['id'],True),r);self.assertEqual(len(s.results()),1)
    def test_invalid_input_never_persists(self):
        s=self.api()
        for field,value in [('person_id','other'),('draw_id','draw-2'),('status','entered-in-error'),('value','-44'),('unit','mg/dL'),('value','NaN'),('collected_at','2026-10-21')]:
            original=self.rows[0][field];self.rows[0][field]=value
            with self.subTest(field=field,value=value):
                with self.assertRaises(ValueError):s.preview(self.payload(),1981,'alex-demo')
                self.assertEqual(s.results(),[])
            self.rows[0][field]=original
    def test_missing_duplicate_and_wrong_person(self):
        s=self.api()
        with self.assertRaises(ValueError):s.preview(self.payload(),1981,'someone-else')
        row=self.rows.pop()
        with self.assertRaises(ValueError):s.preview(self.payload(),1981,'alex-demo')
        self.rows.append(row);self.rows.append(row)
        with self.assertRaises(ValueError):s.preview(self.payload(),1981,'alex-demo')
    def test_snapshot_not_replaced_by_file_changes(self):
        s=self.api();p=s.preview(self.payload(),1981,'alex-demo');self.rows[0]['value']='50'
        r=s.commit(p['id'],True);self.assertAlmostEqual(r['pheno_age'],37.2478,places=3)
    def test_report_and_unknown_approval(self):
        s=self.api()
        with self.assertRaises(ValueError):s.commit('../bad',True)
        p=s.preview(self.payload(),1981,'alex-demo');r=s.commit(p['id'],True)
        report=s.report(r['id']);self.assertIn('Hebe Longevity',report);self.assertIn('Research',report)
if __name__=='__main__':unittest.main()
