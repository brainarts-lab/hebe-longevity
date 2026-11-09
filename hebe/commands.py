import json
import os
from pathlib import Path
import shlex
import stat
import sqlite3
from .service import Service, DISCLAIMER

ROOT=Path(__file__).resolve().parents[1]

def read_csv(path):
    path=Path(path).expanduser()
    if path.suffix.lower()!='.csv':raise ValueError('Only the Hebe CSV template is supported.')
    fd=os.open(path,os.O_RDONLY|os.O_NONBLOCK|getattr(os,'O_NOFOLLOW',0))
    with os.fdopen(fd,'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):raise ValueError('A regular CSV file is required.')
        return stream.read(65537)

def write_report(path,content):
    fd=os.open(path,os.O_CREAT|os.O_WRONLY|os.O_TRUNC|getattr(os,'O_NOFOLLOW',0),0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as stream:
        os.fchmod(stream.fileno(),0o600)
        stream.write(content)

def prepare(home,args):
    try:
        if not isinstance(args,dict):raise ValueError('Expected structured arguments.')
        s=Service(home);action=args.get('action','demo')
        if action=='status':return json.dumps({'ok':True,'results':[{'id':r['id'],'person_id':r['person_id'],'measured_at':r['measured_at']} for r in s.results()],'disclaimer':DISCLAIMER})
        if action=='demo':data=(ROOT/'data/demo.csv').read_bytes();year=1981;person='alex-demo'
        elif action=='preview':data=read_csv(args['file_path']);year=args['birth_year'];person=args['person_id']
        else:raise ValueError('Unsupported action.')
        p=s.preview(data,year,person)
        return json.dumps({'ok':True,'preview':p,'next':'Open /hebe to try the demo, or /hebe import <file.csv> <birth-year> <person-id>. Saving requires the user confirmation dialog.'})
    except ValueError as error:
        return json.dumps({'ok':False,'error':str(error)})
    except (KeyError,TypeError,OSError,sqlite3.Error):
        return json.dumps({'ok':False,'error':'Input refused. Use a regular Hebe CSV with nine final markers, one person and draw, canonical units and valid nonnegative values. No measurements saved.'})

def handle(ctx,home,raw):
    try:
        words=shlex.split(raw)
        if not words or words==['demo']:
            args={'action':'demo'}
        elif len(words)==4 and words[0]=='import':
            args={'action':'preview','file_path':words[1],'birth_year':int(words[2]),'person_id':words[3]}
        elif words==['status']:return prepare(home,{'action':'status'})
        elif len(words)==2 and words[0]=='report':
            s=Service(home);html=s.report(words[1]);path=Path(home)/f'report-{words[1]}.html'
            write_report(path,html)
            return f'Hebe Longevity report: {path.as_uri()}'
        else:return 'Usage: /hebe [demo | status | import "file.csv" birth-year person-id | report result-id]'
        out=json.loads(prepare(home,args))
        if not out['ok']:return out['error']
        p=out['preview']
        summary='\n'.join(f'{r["marker"]}: {r["value"]} {r["unit"]}' for r in p['markers'])
        answer=ctx.ask_choice(f'Hebe Longevity — review before saving\n{DISCLAIMER}\nPerson: {p["person_id"]}; birth year: {p["birth_year"]}; draw: {p["draw_id"]}; date: {p["measured_at"]}\n{summary}\nSource preview: {p["id"]}\nSave this exact snapshot and calculate?',
                              [{'value':'save','label':'Save and calculate'},{'value':'cancel','label':'Cancel'}])
        if answer!='save':
            Service(home).discard(p['id'])
            if answer=='cancel':return 'Cancelled. Preview discarded; no new measurements saved.'
            return 'No measurements saved. Preview discarded. Run /hebe again on a surface with a confirmation dialog.'
        s=Service(home);r=s.commit(p['id'],True)
        report=Path(home)/f'report-{r["id"]}.html';write_report(report,s.report(r['id']))
        return (f'Hebe Longevity · Blood PhenoAge: {r["pheno_age"]:.1f} years. '
                f'Approximate chronological age: {r["chrono_age"]:.1f}.\n{DISCLAIMER}\n'
                f'Report: {report.as_uri()}\nResult: {r["id"]}')
    except (ValueError,KeyError,TypeError,OSError,sqlite3.Error):return 'Hebe could not complete this request. Check /hebe status before retrying; a result may already be saved. No automatic fallback is used.'
