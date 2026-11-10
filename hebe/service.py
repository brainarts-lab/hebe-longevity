"""Strict import and version-bound confirmation. No network or model calls."""
import csv
from datetime import date, datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import re
import sqlite3
import time
from types import SimpleNamespace
from .plsi_kernel import chronological_age, phenoage
from .plsi_units import to_canonical

PIN = '17c433c4a9ecb54279ab02ba1d7d63ee8e8a2e81'
UNITS = {'albumin':'g/L','creatinine':'umol/L','glucose':'mmol/L','crp':'mg/dL',
         'lymphocyte_pct':'%','mcv':'fL','rdw':'%','alp':'U/L','wbc':'10*3/uL'}
# Unit handling follows PLSI exactly: the map's sourced conversions first, then PLSI's generic UCUM
# prefix/volume scale (hebe/plsi_units.py, unchanged). Anything else is refused, never guessed.
YOUNG_1987 = 'PLSI blood_phenoage map, Young DS 1987, doi:10.7326/0003-4819-106-1-114'
MAP_CONVERSIONS = {'creatinine':[SimpleNamespace(from_unit='mg/dL',factor=88.42)],
                   'glucose':[SimpleNamespace(from_unit='mg/dL',factor=0.0555062167)]}
def coordinate(marker):
    return SimpleNamespace(unit=UNITS[marker],conversions=MAP_CONVERSIONS.get(marker,[]))
FIELDS = ['person_id','draw_id','collected_at','observation_id','status','marker','value','unit']
ID = re.compile(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}')
DEMO_FILES = ('demo.csv','demo-earlier.csv')
DEMO_PERSON = 'alex-demo'
DEMO_BIRTH_YEAR = 1981
DISCLAIMER = 'Research and education only. Not a diagnosis or treatment recommendation. Cloud models can receive tool outputs. This is not a network isolation boundary.'

def parse(data, birth_year, person):
    if not isinstance(data, bytes) or len(data) > 65536:
        raise ValueError('CSV must be UTF-8 and at most 64 KiB.')
    if not isinstance(person,str) or not ID.fullmatch(person):
        raise ValueError('Use a local person ID, not a name or contact detail.')
    if type(birth_year) is not int or not 1900 <= birth_year <= date.today().year:
        raise ValueError('Invalid birth year.')
    try:
        reader=csv.DictReader(io.StringIO(data.decode('utf-8-sig')),strict=True)
        if reader.fieldnames != FIELDS:
            raise ValueError('Unsupported CSV header; use the supplied template.')
        rows=list(reader)
    except (UnicodeError,csv.Error):
        raise ValueError('Malformed UTF-8 CSV.') from None
    if len(rows)!=9:
        raise ValueError('Exactly nine distinct markers are required for one draw.')
    values={}; conversions=[]; observation_ids=set(); draws=set(); dates=set()
    for row in rows:
        if set(row)!=set(FIELDS) or any(v is None or not v for v in row.values()):
            raise ValueError('Missing or extra CSV fields.')
        if row['person_id']!=person or row['status']!='final':
            raise ValueError('Person mismatch or non-final result; nothing imported.')
        if not ID.fullmatch(row['draw_id']) or not ID.fullmatch(row['observation_id']):
            raise ValueError('Invalid draw or observation ID.')
        if row['observation_id'] in observation_ids:
            raise ValueError('Duplicate observation ID.')
        observation_ids.add(row['observation_id']);draws.add(row['draw_id'])
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',row['collected_at']):
            raise ValueError('Use an explicit ISO date (YYYY-MM-DD).')
        try: measured=date.fromisoformat(row['collected_at'])
        except ValueError: raise ValueError('Invalid collection date.') from None
        if measured>date.today() or measured.year-birth_year<19:
            raise ValueError('Future measurements are unsupported. With birth year only, collection year must be at least birth year + 19 to establish adulthood.')
        dates.add(measured.isoformat());marker=row['marker']
        if marker not in UNITS or marker in values:
            raise ValueError('Unknown or duplicate marker.')
        if UNITS[marker]=='%' and row['unit']!='%':
            raise ValueError(f'Unsupported unit {row["unit"]!r} for {marker}; PLSI has no conversion, nothing guessed.')
        if not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?',row['value']):
            raise ValueError('Values must be unsigned decimal numbers with a point; no spaces or exponent notation.')
        try: value=float(row['value'])
        except ValueError: raise ValueError('Values must be decimal numbers with a point.') from None
        if not math.isfinite(value) or value<0 or (marker=='crp' and value<=0) or (UNITS[marker]=='%' and value>100):
            raise ValueError('Physically invalid value or unsupported CRP bound.')
        try: converted,conversion=to_canonical(value,row['unit'],coordinate(marker))
        except ValueError: raise ValueError(f'Unsupported unit {row["unit"]!r} for {marker}; PLSI has no conversion, nothing guessed.') from None
        if conversion:
            sourced=any(c.from_unit==row['unit'] for c in coordinate(marker).conversions)
            conversions.append({'marker':marker,'from_value':value,'from_unit':row['unit'],'factor':conversion['factor'],
                                'value':converted,'unit':UNITS[marker],
                                'source':YOUNG_1987 if sourced else 'PLSI generic UCUM prefix scale (map/units.py)'})
            value=converted
        if marker=='crp' and value<=0:
            raise ValueError('CRP is too small to calculate after unit conversion.')
        values[marker]=value
    if len(draws)!=1 or len(dates)!=1:
        raise ValueError('Mixed blood draws are not supported.')
    return {'person_id':person,'birth_year':birth_year,'draw_id':next(iter(draws)),
            'measured_at':next(iter(dates)),'values':values,'rows':rows,'conversions':conversions,'source_sha256':hashlib.sha256(data).hexdigest()}

def encode(data):
    return json.dumps(data,sort_keys=True,separators=(',',':'),allow_nan=False)

class Service:
    def __init__(self, home):
        self.home=Path(home);self.home.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.home.chmod(0o700)
        self.path=self.home/'hebe.sqlite3'
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS previews (id TEXT PRIMARY KEY, body TEXT NOT NULL, expires REAL NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS results (id TEXT PRIMARY KEY, person TEXT NOT NULL, draw TEXT NOT NULL, body TEXT NOT NULL, UNIQUE(person,draw))')
        self.path.chmod(0o600)
    def db(self):
        from contextlib import contextmanager
        @contextmanager
        def connection():
            db=sqlite3.connect(self.path,timeout=10)
            try:
                with db: yield db
            finally: db.close()
        return connection()
    def preview(self,data,birth_year,person,replaces=None):
        body=parse(data,birth_year,person)
        if replaces:
            old=self.result(replaces)
            if old['person_id']!=person:raise ValueError('A correction must keep the same person.')
            if person==DEMO_PERSON:raise ValueError('Demo values are fixed. Delete the demo person to start over.')
            body['replaces']=replaces
        # Check arithmetic before any durable measurement write.
        self.calculate(body)
        serial=encode(body);key=hashlib.sha256(serial.encode()).hexdigest()
        with self.db() as db:
            db.execute('DELETE FROM previews WHERE expires < ?', (time.time(),))
            existing=db.execute('SELECT body FROM results WHERE person=?',(person,)).fetchall()
            if any(json.loads(x[0])['birth_year']!=birth_year for x in existing):
                raise ValueError('Birth year conflicts with the existing person.')
            db.execute('INSERT INTO previews VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET expires=excluded.expires',(key,serial,time.time()+1800))
        return {'id':key,'person_id':person,'draw_id':body['draw_id'],'measured_at':body['measured_at'],'replaces':replaces or None,
                'birth_year':birth_year,'markers':body['rows'],'conversions':body['conversions'],'disclaimer':DISCLAIMER,'expires_in_seconds':1800}
    @staticmethod
    def calculate(body):
        at=datetime.fromisoformat(body['measured_at']).replace(tzinfo=timezone.utc)
        age=chronological_age(body['birth_year'],at)
        try: biological=phenoage(body['values'],age)
        except (ArithmeticError,ValueError): raise ValueError('Values are outside the supported calculation domain.') from None
        if not math.isfinite(biological): raise ValueError('No finite PhenoAge result.')
        return {'chrono_age':age,'pheno_age':biological,'delta':biological-age}
    def commit(self,key,approved):
        if approved is not True: raise ValueError('Explicit user confirmation is required.')
        if not isinstance(key,str) or not re.fullmatch('[0-9a-f]{64}',key): raise ValueError('Unknown preview.')
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT body FROM results WHERE id=?',(key,)).fetchone()
            if old:return json.loads(old[0])
            row=db.execute('SELECT body,expires FROM previews WHERE id=?',(key,)).fetchone()
            if not row or row[1]<time.time():raise ValueError('Preview missing or expired; preview again.')
            if hashlib.sha256(row[0].encode()).hexdigest()!=key:raise ValueError('Preview integrity check failed.')
            body=json.loads(row[0])
            replaces=body.pop('replaces',None)
            if replaces and not db.execute('SELECT 1 FROM results WHERE id=? AND person=?',(replaces,body['person_id'])).fetchone():
                raise ValueError('The blood draw you are correcting no longer exists.')
            if db.execute('SELECT 1 FROM results WHERE person=? AND draw=? AND id IS NOT ?',(body['person_id'],body['draw_id'],replaces)).fetchone():
                raise ValueError('A blood draw from this date is already saved for this person. Correct or delete it under Blood draws.')
            existing=db.execute('SELECT body FROM results WHERE person=?',(body['person_id'],)).fetchall()
            if any(json.loads(x[0])['birth_year']!=body['birth_year'] for x in existing):
                raise ValueError('Birth year conflicts with the existing person.')
            result={**body,**self.calculate(body),'id':key,'plsi_commit':PIN,'disclaimer':DISCLAIMER}
            if replaces:
                result['corrects']=replaces
                db.execute('DELETE FROM results WHERE id=?',(replaces,))
            db.execute('INSERT INTO results VALUES (?,?,?,?)',(key,body['person_id'],body['draw_id'],encode(result)))
            db.execute('DELETE FROM previews WHERE id=?',(key,))
        if replaces:self._forget_reports([replaces])
        return result
    def result(self,key):
        if not isinstance(key,str) or not re.fullmatch('[0-9a-f]{64}',key):raise ValueError('Unknown blood draw.')
        with self.db() as db:row=db.execute('SELECT body FROM results WHERE id=?',(key,)).fetchone()
        if not row:raise ValueError('Unknown blood draw.')
        return json.loads(row[0])
    def _forget_reports(self,keys):
        for key in keys:(self.home/f'report-{key}.html').unlink(missing_ok=True)
    def delete_draw(self,key):
        """Remove one confirmed blood draw. PLSI retracts its values on the next sync (plsi revise)."""
        person=self.result(key)['person_id']
        if len(self.history(person))==1:  # the last draw: nothing is left to plan on, so the person goes too
            self.delete_person(person);return person
        with self.db() as db:db.execute('DELETE FROM results WHERE id=?',(key,))
        self._forget_reports([key])
        return person
    def delete_person(self,person):
        """Remove everything Hebe and PLSI hold for one person: draws, previews, plan drafts, reports and the
        person's PLSI record, including started plans."""
        if not isinstance(person,str) or not ID.fullmatch(person):raise ValueError('Unknown person.')
        import shutil
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            keys=[k for (k,) in db.execute('SELECT id FROM results WHERE person=?',(person,))]
            if not keys:raise ValueError('Unknown person.')
            db.execute('DELETE FROM results WHERE person=?',(person,))
            for key,body in db.execute('SELECT id,body FROM previews').fetchall():
                if json.loads(body).get('person_id')==person:db.execute('DELETE FROM previews WHERE id=?',(key,))
            plans=[]
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='plan_drafts'").fetchone():
                plans=[k for (k,) in db.execute('SELECT id FROM plan_drafts WHERE person=?',(person,))]
                db.execute('DELETE FROM plan_drafts WHERE person=?',(person,))
        self._forget_reports(keys)
        work=self.home/'plsi-work'
        for name in [f'{person}-draws.csv']+[f'{k}.{x}' for k in plans for x in ('plan.json','findings.json','start.json','start-findings.json')]:
            (work/name).unlink(missing_ok=True)
        record=self.home/'plsi'/person
        if record.is_dir() and record.parent==self.home/'plsi':shutil.rmtree(record)
        return {'person_id':person,'draws':len(keys),'plans':len(plans)}
    def discard(self,key):
        with self.db() as db:db.execute('DELETE FROM previews WHERE id=?',(key,))
    def results(self):
        with self.db() as db:return [json.loads(x[0]) for x in db.execute('SELECT body FROM results ORDER BY rowid')]
    def history(self,person):
        with self.db() as db:
            rows=[json.loads(x[0]) for x in db.execute('SELECT body FROM results WHERE person=?',(person,))]
        return sorted(rows,key=lambda r:(r['measured_at'],r['draw_id']))
    def report(self,key):
        result=next((r for r in self.results() if r['id']==key),None)
        if result is None:raise ValueError('Unknown result.')
        from .report import render
        return render(result, UNITS, self.history(result['person_id']))
