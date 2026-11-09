import hashlib
import json
import os
from pathlib import Path
import shlex
import stat
import sqlite3
from .service import Service, DISCLAIMER, DEMO_FILES, DEMO_PERSON, DEMO_BIRTH_YEAR
from .report import describe_delta, marker_name, unit_label, years
from .drivers import explain_change, previous_draw

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

def _day(iso):
    from datetime import date
    d=date.fromisoformat(iso);return f'{d.day} {d.strftime("%B %Y")}'

def confirmation_text(p):
    conv={c['marker']:c for c in p.get('conversions',[])}
    def line(r):
        text=f'{marker_name(r["marker"])}: {r["value"]} {unit_label(r["unit"])}'
        c=conv.get(r['marker'])
        return text+(f' (converted to {c["value"]:g} {unit_label(c["unit"])})' if c else '')
    lines=[line(r) for r in p['markers']]
    units=(f'{len(conv)} units converted with documented factors' if conv else 'matching units')
    return '\n'.join([
        'Check your blood panel before saving','',
        f'Person: {p["person_id"]}, born {p["birth_year"]}',
        f'Blood drawn: {_day(p["measured_at"])} ({p["draw_id"]})','',
        *lines,'',
        f'Checked: all {len(lines)} markers, one person, one blood draw, final values, {units}.',
        'Save this snapshot and calculate your Blood PhenoAge?','',
        DISCLAIMER])

def result_text(r,report,history=(),saved=None):
    trend=[]
    if saved and saved['id']!=r['id']:
        trend.append(f'Added an earlier blood draw from {_day(saved["measured_at"])}: {saved["pheno_age"]:.1f} years')
    if len(history)>1:
        first,last=history[0],history[-1]
        trend+=[f'Across {len(history)} blood draws since {_day(first["measured_at"])}: '
               f'{first["pheno_age"]:.1f} to {last["pheno_age"]:.1f} years']
    previous=previous_draw(list(history),r) if history else None
    if previous:
        top=[x for x in explain_change(previous,r)['effects'] if x['kind']=='marker'][:2]
        if top:trend.append('Biggest movers in the formula: '+', '.join(f'{marker_name(x["marker"])} {years(x["years"])}' for x in top))
    return '\n'.join([
        f'Blood PhenoAge: {r["pheno_age"]:.1f} years',
        f'{describe_delta(r["delta"])} ({r["chrono_age"]:.1f})',*trend,'',
        f'Report: {report.as_uri()}',
        f'Result ID: {r["id"]}','',
        'Next: ask in chat "What could I try to lower my Blood PhenoAge?" to draft a plan. /hebe help shows everything Hebe can do.','',
        DISCLAIMER])

def next_demo(service):
    """Next fictional demo draw that is not saved yet, or None when all are saved."""
    saved={r['source_sha256'] for r in service.history(DEMO_PERSON)}
    for name in DEMO_FILES:
        data=(ROOT/'data'/name).read_bytes()
        if hashlib.sha256(data).hexdigest() not in saved:return data
    return None

USAGE='Usage: /hebe [help | demo | status | import "file.csv" birth-year person-id | report result-id | plan [person-id] | plan start PLAN_ID [YYYY-MM-DD]]'

WELCOME='\n'.join([
    'Hebe Longevity',
    'Longevity Intelligence for Hermes','',
    'What you get',
    '- Your Blood PhenoAge from nine routine blood markers, with the original formula Longevity Grok uses',
    '- Your trend across blood draws and which values moved your result',
    '- A plan to lower it, built the Longevity Grok way: verified evidence, safety screening and an independent challenger','',
    'What you do',
    '1. /hebe  try the fictional demo, or /hebe import "panel.csv" birth-year person-id for your own values',
    '2. Ask in chat: "What could I try to lower my Blood PhenoAge?"',
    '3. /hebe plan start PLAN_ID  only you can start a plan','',
    'More',
    '- /hebe status  saved results',
    '- /hebe report RESULT_ID  open a report',
    '- /hebe plan  your plans and drafts','',
    'Your data stays in your Hermes home. Your configured model sees what appears in chat.',
    DISCLAIMER])

def plan_command(ctx,home,words):
    from datetime import date
    from .plans import Plans
    from .plsi_bridge import PlsiError
    plans=Plans(home)
    try:
        if len(words)<=1:
            people=[words[0]] if words else sorted({r['person_id'] for r in Service(home).results()})
            if not people:return 'No saved results yet. Enter /hebe to try the demo.'
            lines=[]
            for person in people:
                o=plans.overview(person);entries=[]
                listed=o['plans'] if isinstance(o['plans'],list) else o['plans'].get('plans',[])
                for p in listed:
                    entries.append(f'- {p["plan_id"]}: {p["state"]}, starts {p.get("start") or "not set"}, review {p.get("review_at") or "not set"}')
                for d in o['drafts']:
                    if not d['started_as']:
                        entries.append(f'- Draft {d["id"][:12]}: {"challenged" if d["challenged"] else "not challenged yet"}. Start it with /hebe plan start {d["id"][:12]}')
                lines+=[person,*(entries or ['- No plans yet. Ask Hebe in chat to draft one.']),'']
            return '\n'.join(lines)
        if words[0]!='start' or len(words) not in (2,3):return USAGE
        start_on=words[2] if len(words)==3 else date.today().isoformat()
        date.fromisoformat(start_on)
        key,body,recorded,text=plans.summary(words[1])
        if recorded:return f'This plan already started as {recorded}.'
        answer=ctx.ask_choice(f'Start this plan on {start_on}?\n\n{text}\n\nStarting records the plan and its predictions in PLSI. '
                              f'Cautions from screening are accepted by starting. Talk to your clinician before changing medication, supplements or routines.\n\n{DISCLAIMER}',
                              [{'value':'start','label':'Start plan'},{'value':'cancel','label':'Not yet'}])
        if answer!='start':return 'Not started. The draft is kept; nothing was recorded.'
        out=plans.start(key,start_on)
        return f'Plan started as {out["plan_id"]} on {start_on}. See the review date with /hebe plan. Scoring predictions against your next blood draw is not available in Hebe yet.'
    except (ValueError,PlsiError) as error:return f'Not started: {error}'

def prepare(home,args):
    try:
        if not isinstance(args,dict):raise ValueError('Expected structured arguments.')
        s=Service(home);action=args.get('action','demo')
        if action=='status':return json.dumps({'ok':True,'results':[{'id':r['id'],'person_id':r['person_id'],'measured_at':r['measured_at']} for r in s.results()],'disclaimer':DISCLAIMER})
        if action=='demo':
            data=next_demo(s);year=DEMO_BIRTH_YEAR;person=DEMO_PERSON
            if data is None:return json.dumps({'ok':False,'error':'All demo blood draws are already saved. Use /hebe status to list them or /hebe report RESULT_ID to open a report.'})
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
        elif words==['status']:
            rows=Service(home).results()
            if not rows:return 'No saved results yet. Enter /hebe to try the demo.'
            return '\n'.join(['Saved Hebe results',''] +
                [f'{r["person_id"]}, {_day(r["measured_at"])}: {r["pheno_age"]:.1f} years. Result ID {r["id"]}' for r in rows] +
                ['','Open a report with /hebe report RESULT_ID'])
        elif len(words)==2 and words[0]=='report':
            s=Service(home);html=s.report(words[1]);path=Path(home)/f'report-{words[1]}.html'
            write_report(path,html)
            return f'Hebe Longevity report: {path.as_uri()}'
        elif words and words[0]=='plan':return plan_command(ctx,home,words[1:])
        elif words==['help']:return WELCOME
        else:return USAGE+'\n/hebe help explains what Hebe does.'
        out=json.loads(prepare(home,args))
        if not out['ok']:return out['error']
        p=out['preview']
        answer=ctx.ask_choice(confirmation_text(p),
                              [{'value':'save','label':'Save and calculate'},{'value':'cancel','label':'Cancel'}])
        if answer!='save':
            Service(home).discard(p['id'])
            if answer=='cancel':return 'Cancelled. Preview discarded; no new measurements saved.'
            return 'No measurements saved. Preview discarded. Run /hebe again on a surface with a confirmation dialog.'
        s=Service(home);saved=s.commit(p['id'],True)
        history=s.history(saved['person_id']);latest=history[-1]
        report=Path(home)/f'report-{latest["id"]}.html';write_report(report,s.report(latest['id']))
        return result_text(latest,report,history,saved)
    except (ValueError,KeyError,TypeError,OSError,sqlite3.Error):return 'Hebe could not complete this request. Check /hebe status before retrying; a result may already be saved. No automatic fallback is used.'
