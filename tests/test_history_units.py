import csv
import io
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hebe.commands import handle
from hebe.service import Service

CANONICAL = [('albumin','44','g/L'),('creatinine','80','umol/L'),('glucose','5','mmol/L'),('crp','0.1','mg/dL'),
             ('lymphocyte_pct','30','%'),('mcv','90','fL'),('rdw','13','%'),('alp','60','U/L'),('wbc','5','10*3/uL')]

def panel(markers, person='p1', draw='draw-1', day='2026-10-20'):
    b=io.StringIO()
    w=csv.writer(b);w.writerow(['person_id','draw_id','collected_at','observation_id','status','marker','value','unit'])
    for i,(m,v,u) in enumerate(markers):w.writerow([person,draw,day,f'{draw}-{i}','final',m,v,u])
    return b.getvalue().encode()

def replace(marker, value, unit):
    return [(m,value,unit) if m==marker else (m,v,u) for m,v,u in CANONICAL]

class Confirm:
    def __init__(self):self.asked=0
    def ask_choice(self,question,choices):
        self.asked+=1;self.question=question;return 'save'

class Units(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.s=Service(self.tmp.name)

    def save(self,markers,**kw):
        p=self.s.preview(panel(markers,**kw),1981,kw.get('person','p1'));return p,self.s.commit(p['id'],True)

    def test_lab_units_give_the_same_result_as_canonical_units(self):
        _,base=self.save(CANONICAL,draw='a')
        lab=[('albumin','4.4','g/dL'),('creatinine','0.904772','mg/dL'),('glucose','90.0799','mg/dL'),('crp','1','mg/L'),
             ('lymphocyte_pct','30','%'),('mcv','90','fL'),('rdw','13','%'),('alp','60','U/L'),('wbc','5','10*9/L')]
        p,r=self.save(lab,draw='b',day='2026-10-21')
        self.assertAlmostEqual(r['pheno_age'],base['pheno_age'],places=2)
        converted={c['marker']:c for c in r['conversions']}
        self.assertEqual(set(converted),{'albumin','creatinine','glucose','crp','wbc'})
        self.assertIn('10.7326/0003-4819-106-1-114',converted['creatinine']['source'])
        report=self.s.report(r['id']);self.assertIn('from 4.4 g/dL',report);self.assertIn('5 units converted',report)
        # The confirmed snapshot keeps the lab's original value and unit
        self.assertIn({'marker':'glucose','value':'90.0799','unit':'mg/dL'},
                      [{k:row[k] for k in ('marker','value','unit')} for row in r['rows']])

    def test_unknown_units_are_refused_and_nothing_is_stored(self):
        for marker,value,unit in [('creatinine','9','mg/L'),('glucose','5','mmol/mol'),('crp','1','mg/l'),
                                  ('albumin','44','g/l'),('wbc','5','/uL'),('rdw','13','fL'),('wbc','5','G/L'),('wbc','5','/nL'),
                                  ('lymphocyte_pct','0.3','1'),('glucose','0.9','g/L')]:
            with self.subTest(unit=unit),self.assertRaises(ValueError):
                self.s.preview(panel(replace(marker,value,unit)),1981,'p1')
        self.assertEqual(self.s.results(),[])

    def test_generic_scale_matches_plsi_and_never_crosses_quantity_kinds(self):
        # PLSI's generic UCUM scale: same base, different prefix (mg/dL albumin -> g/L)
        p=self.s.preview(panel(replace('albumin','4400','mg/dL')),1981,'p1')
        self.assertEqual(p['conversions'][0]['value'],44.0)
        # Mass to molar is a different quantity: refused like PLSI's NO_CONVERSION
        with self.assertRaises(ValueError):self.s.preview(panel(replace('albumin','0.6','mmol/L')),1981,'p1')

    def test_history_is_per_person_and_sorted_by_collection_date(self):
        self.save(CANONICAL,draw='late',day='2026-10-20')
        self.save(CANONICAL,draw='early',day='2025-03-01')
        self.save(CANONICAL,person='p2',draw='other',day='2026-01-01')
        self.assertEqual([r['draw_id'] for r in self.s.history('p1')],['early','late'])
        late=next(r for r in self.s.history('p1') if r['draw_id']=='late')
        report=self.s.report(late['id'])
        self.assertIn('Your trend',report);self.assertIn('1 March 2025',report)
        self.assertNotIn('1 January 2026',report)

    def test_single_draw_report_has_no_trend(self):
        _,r=self.save(CANONICAL)
        self.assertNotIn('Your trend',self.s.report(r['id']))

class DemoFlow(unittest.TestCase):
    def test_demo_saves_each_fictional_draw_once_then_stops_asking(self):
        with tempfile.TemporaryDirectory() as home:
            first=Confirm();out1=handle(first,home,'')
            self.assertIn('37.2',out1);self.assertNotIn('Across',out1)
            second=Confirm();out2=handle(second,home,'')
            self.assertIn('converted to',second.question)
            self.assertIn('Across 2 blood draws since 14 October 2025',out2)
            # The headline stays on the latest draw even when an earlier one is added
            self.assertTrue(out2.startswith('Blood PhenoAge: 37.2 years'),out2)
            self.assertIn('Added an earlier blood draw from 14 October 2025: 41.0',out2)
            third=Confirm();out3=handle(third,home,'')
            self.assertEqual(third.asked,0);self.assertIn('already saved',out3)
            self.assertEqual(len(Service(home).results()),2)
            report=Path(out2.split('Report: file://')[1].split('\n')[0]).read_text()
            self.assertIn('<div class="age">37.2',report)
            self.assertIn('Sample report',report);self.assertIn('Your trend',report);self.assertNotIn('from 0.92 mg/dL',report)

    def test_status_is_readable_text(self):
        with tempfile.TemporaryDirectory() as home:
            self.assertIn('No saved results',handle(None,home,'status'))
            handle(Confirm(),home,'')
            self.assertIn('alex-demo, 20 October 2026: 37.2 years',handle(None,home,'status'))

if __name__=='__main__':unittest.main()

class Drivers(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.s=Service(self.tmp.name)
    def save(self,markers,draw,day):
        p=self.s.preview(panel(markers,draw=draw,day=day),1981,'p1');return self.s.commit(p['id'],True)

    def test_effects_add_up_to_the_real_change_and_skip_unchanged_markers(self):
        from hebe.drivers import explain_change
        a=self.save(CANONICAL,'a','2025-10-14')
        b=self.save(replace('crp','0.4','mg/dL')[:7]+[('alp','90','U/L'),('wbc','5','10*3/uL')],'b','2026-10-20')
        change=explain_change(a,b)
        self.assertAlmostEqual(change['total'],b['pheno_age']-a['pheno_age'],places=9)
        self.assertAlmostEqual(sum(x['years'] for x in change['effects']),change['total'],places=9)
        markers={x['marker']:x for x in change['effects'] if x['kind']=='marker'}
        self.assertEqual(set(markers),{'crp','alp'})
        # Original formula: higher CRP and ALP raise PhenoAge; a year of calendar age raises it too
        self.assertGreater(markers['crp']['years'],0);self.assertGreater(markers['alp']['years'],0)
        self.assertGreater(next(x for x in change['effects'] if x['kind']=='age')['years'],0)

    def test_drivers_only_appear_with_an_earlier_draw(self):
        a=self.save(CANONICAL,'a','2025-10-14')
        self.assertNotIn('What moved your result',self.s.report(a['id']))
        b=self.save(replace('crp','0.4','mg/dL'),'b','2026-10-20')
        self.assertIn('What moved your result',self.s.report(b['id']))
        self.assertNotIn('What moved your result',self.s.report(a['id']))

    def test_demo_result_names_biggest_movers(self):
        with tempfile.TemporaryDirectory() as home:
            handle(Confirm(),home,'');out=handle(Confirm(),home,'')
            self.assertIn('Biggest movers in the formula: ',out)
