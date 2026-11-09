import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hebe.commands import handle,prepare
from hebe.service import Service
class Commands(unittest.TestCase):
    def test_missing_or_declined_confirmation_never_saves(self):
        for answer in (None,'cancel','true'):
            with tempfile.TemporaryDirectory() as home:
                class Context:
                    def ask_choice(self,*args):return answer
                handle(Context(),home,'')
                self.assertEqual(Service(home).results(),[])
    def test_demo_one_confirmation_and_report(self):
        with tempfile.TemporaryDirectory() as home:
            class Context:
                count=0
                def ask_choice(self,question,choices):
                    self.count+=1
                    self.seen=question
                    return 'save'
            ctx=Context();result=handle(ctx,home,'')
            self.assertEqual(ctx.count,1);self.assertIn('albumin: 44',ctx.seen)
            self.assertIn('37.2',result);self.assertEqual(len(list(Path(home).glob('report-*.html'))),1)
    def test_tool_errors_are_json_and_do_not_execute_shell(self):
        with tempfile.TemporaryDirectory() as home:
            result=prepare(home,{'action':'preview','file_path':'$(touch bad).csv','birth_year':1981,'person_id':'demo'})
            self.assertFalse(json.loads(result)['ok']);self.assertFalse(Path('bad').exists())
