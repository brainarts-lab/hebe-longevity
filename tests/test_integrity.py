from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_import
import unittest
class Integrity(unittest.TestCase):
    setUp=test_import.ImportTests.setUp
    payload=test_import.ImportTests.payload
    api=test_import.ImportTests.api
    def test_concurrent_confirmations_commit_once(self):
        s=self.api();p=s.preview(self.payload(),1981,'alex-demo')
        with ThreadPoolExecutor(max_workers=4) as pool:
            out=list(pool.map(lambda _:s.commit(p['id'],True),range(4)))
        self.assertEqual(len(s.results()),1);self.assertTrue(all(x==out[0] for x in out))
    def test_expired_tampered_and_cross_home_previews_refused(self):
        s=self.api();p=s.preview(self.payload(),1981,'alex-demo')
        with sqlite3.connect(s.path) as db:db.execute('UPDATE previews SET expires=0')
        with self.assertRaises(ValueError):s.commit(p['id'],True)
        p=s.preview(self.payload(),1981,'alex-demo')
        with sqlite3.connect(s.path) as db:db.execute('UPDATE previews SET body=?',('{}',))
        with self.assertRaises(ValueError):s.commit(p['id'],True)
        from hebe.service import Service
        with self.assertRaises(ValueError):Service(self.home/'second').commit(p['id'],True)
        self.assertEqual(s.results(),[])
    def test_changed_existing_draw_is_not_overwritten(self):
        s=self.api();p=s.preview(self.payload(),1981,'alex-demo');s.commit(p['id'],True)
        self.rows[0]['value']='50';p=s.preview(self.payload(),1981,'alex-demo')
        with self.assertRaises(ValueError):s.commit(p['id'],True)
        self.assertEqual(len(s.results()),1)
    def test_malformed_tool_request_returns_json(self):
        from hebe.commands import prepare
        self.assertFalse(json.loads(prepare(self.home,[]))['ok'])

    def test_repeat_preview_refreshes_deadline(self):
        import time
        s=self.api();p=s.preview(self.payload(),1981,'alex-demo')
        with s.db() as db:db.execute('UPDATE previews SET expires=?',(time.time()+5,))
        s.preview(self.payload(),1981,'alex-demo')
        with s.db() as db:expiry=db.execute('SELECT expires FROM previews').fetchone()[0]
        self.assertGreater(expiry,time.time()+1790)
    def test_uncertain_adulthood_and_ambiguous_numbers_refused(self):
        s=self.api()
        with self.assertRaises(ValueError):s.preview(self.payload(),2008,'alex-demo')
        for value in ('4_4',' 44 ','+44','4.4e1'):
            self.rows[0]['value']=value
            with self.subTest(value=value),self.assertRaises(ValueError):s.preview(self.payload(),1981,'alex-demo')
    def test_birth_year_conflict_refused_before_confirmation(self):
        s=self.api();p=s.preview(self.payload(),1981,'alex-demo');s.commit(p['id'],True)
        with self.assertRaisesRegex(ValueError,'Birth year'):s.preview(self.payload(),1982,'alex-demo')
    def test_private_directory_and_report(self):
        from hebe.commands import handle
        self.home.chmod(0o755)
        class Context:
            def ask_choice(self,*args):return 'save'
        handle(Context(),self.home,'')
        self.assertEqual(self.home.stat().st_mode & 0o777,0o700)
        self.assertEqual(next(self.home.glob('report-*.html')).stat().st_mode & 0o777,0o600)
    def test_cancel_discards_preview_and_explains_cancellation(self):
        from hebe.commands import handle
        class Context:
            def ask_choice(self,*args):return 'cancel'
        result=handle(Context(),self.home,'')
        self.assertIn('Cancelled',result)
        with self.api().db() as db:self.assertEqual(db.execute('SELECT count(*) FROM previews').fetchone()[0],0)
