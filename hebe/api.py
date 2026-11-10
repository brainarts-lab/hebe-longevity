"""Routes for the Hebe page in Hermes Desktop (mounted by Hermes under /api/plugins/hebe-longevity/).

Hermes authenticates these routes. Saving a blood draw and starting a plan need a fresh confirmation token
that only the page requests after the user's click; the agent has no tool that reaches these routes.
"""
from datetime import date
import hashlib
import json
import re
import secrets
import sqlite3
import time
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from .commands import next_demo
from .drivers import explain_change, previous_draw
from .plans import Plans
from .plsi_bridge import PlsiError
from .report import marker_name, unit_label
from .service import Service, DEMO_BIRTH_YEAR, DEMO_PERSON, DISCLAIMER, ID

EMBED = ('<script>(function(){function s(){var m=document.querySelector("main");if(!innerWidth)return;'
         'parent.postMessage({type:"hebe-height",h:Math.ceil(m.getBoundingClientRect().bottom)+8},"*")}'
         'addEventListener("load",s);new ResizeObserver(s).observe(document.querySelector("main"));'
         '[100,500,1500].forEach(function(t){setTimeout(s,t)})})()</script>')
# Inside the Hebe page: follow the app's light or dark theme, drop the report's own header and background.
EMBED_THEME = {
    'light': ':root{--bg:transparent;--surface:#ffffff;--ink:#1f1a12;--muted:#6f6553;--faint:#8d846f;--line:#ece4d2;'
             '--accent:#8A6A3F;--fillg:linear-gradient(90deg,#B08A5B,#8A6A3F);--track:#f1ead9;--calendar:#c9bfa9;'
             '--demo:#f3ead8;--demo-ink:#5e4526;color-scheme:light}',
    'dark': ':root{--bg:transparent;--surface:#141210;--ink:#ece3d2;--muted:#a39a88;--faint:#8a8170;--line:#2b261d;'
            '--accent:#DEB88A;--fillg:linear-gradient(90deg,#7C603F,#B08A5B 50%,#DEB88A);--track:#2b261d;--calendar:#5f574a;'
            '--demo:#1d1810;--demo-ink:#DEB88A;color-scheme:dark}'}
EMBED_LAYOUT = 'html,body{background:transparent}.top,main>footer{display:none}main{max-width:none;padding:0 0 8px}'
ORDER = ('albumin', 'creatinine', 'glucose', 'crp', 'lymphocyte_pct', 'mcv', 'rdw', 'alp', 'wbc')


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid')


class PreviewIn(Input):
    source: Literal['demo', 'csv']
    csv: str = Field(default='', max_length=65536)
    birth_year: Optional[int] = None
    person_id: str = Field(default='', max_length=64)
    replaces: str = Field(default='', max_length=64)


class ConfirmIn(Input):
    action: Literal['save', 'start', 'delete', 'delete_person']
    id: str = Field(min_length=1, max_length=64)
    start_on: str = Field(default='', max_length=10)


class SaveIn(Input):
    id: str = Field(min_length=64, max_length=64)
    confirmation: str = Field(min_length=32, max_length=100)


class DeleteIn(Input):
    id: str = Field(min_length=1, max_length=64)
    confirmation: str = Field(min_length=32, max_length=100)


class DiscardIn(Input):
    id: str = Field(min_length=64, max_length=64)


class StartIn(Input):
    id: str = Field(min_length=6, max_length=64)
    start_on: str = Field(min_length=10, max_length=10)
    confirmation: str = Field(min_length=32, max_length=100)


def _summary(r):
    return {'id': r['id'], 'person_id': r['person_id'], 'measured_at': r['measured_at'], 'draw_id': r['draw_id'],
            'pheno_age': r['pheno_age'], 'chrono_age': r['chrono_age'], 'delta': r['delta']}


def _people(service):
    people = {}
    for r in service.results():
        people.setdefault(r['person_id'], None)
    out = []
    for person in sorted(people):
        history = service.history(person)
        latest = history[-1]
        entry = {'person_id': person, 'demo': person == DEMO_PERSON, 'birth_year': latest['birth_year'],
                 'draws': [{**_summary(r), 'corrected': bool(r.get('corrects'))} for r in history],
                 'latest': _summary(latest), 'movers': []}
        before = previous_draw(history, latest)
        if before:
            entry['movers'] = [{'marker': x['marker'], 'name': marker_name(x['marker']), 'years': x['years']}
                               for x in explain_change(before, latest)['effects'] if x['kind'] == 'marker'][:3]
        out.append(entry)
    return out


def _preview_view(p):
    conv = {c['marker']: c for c in p.get('conversions', [])}
    rows = sorted(p['markers'], key=lambda r: ORDER.index(r['marker']) if r['marker'] in ORDER else 99)
    return {'id': p['id'], 'person_id': p['person_id'], 'draw_id': p['draw_id'], 'measured_at': p['measured_at'],
            'birth_year': p['birth_year'], 'demo': p['person_id'] == DEMO_PERSON, 'replaces': p.get('replaces'),
            'markers': [{'marker': r['marker'], 'name': marker_name(r['marker']), 'value': r['value'],
                         'unit': unit_label(r['unit']),
                         'converted': ({'value': conv[r['marker']]['value'], 'unit': unit_label(conv[r['marker']]['unit'])}
                                       if r['marker'] in conv else None)} for r in rows],
            'conversions': len(conv), 'disclaimer': DISCLAIMER}


def _draft_view(plans, draft):
    key, body, objections, recorded = plans.draft(draft['id'])
    plan, outcomes = body['plan'], body['screen'].get('outcomes', {})
    verdict = None
    if objections:
        m = re.search(r'VERDICT:\s*(no objections|revise)', objections, re.I)
        verdict = m.group(1).lower() if m else None
    return {'id': key, 'short_id': key[:12], 'created': draft['created'], 'objective': plan.get('objective', ''),
            'actions': [{'id': a.get('local_id'), 'description': a.get('description', ''), 'category': a.get('category', ''),
                         'dose': a.get('dose'), 'schedule': a.get('schedule'),
                         'screening': outcomes.get(a.get('local_id'), 'clear')} for a in plan.get('actions', [])],
            'predictions': [{'coordinate': p.get('coordinate'), 'expected': p.get('expected'), 'low': p.get('low'),
                             'high': p.get('high'), 'horizon_days': p.get('horizon_days'),
                             'control': not p.get('driven_by')} for p in plan.get('predictions', [])],
            'review_after_days': (plan.get('revision_rule') or {}).get('review_after_days'),
            'violations': body['check'].get('violations', []), 'challenged': bool(objections),
            'objections': objections or '', 'verdict': verdict, 'started_as': recorded}


def create_router(home_provider):
    def boundary(request: Request):
        # Hermes owns authentication and profile/plugin authorization. This supplements its gate.
        if request.method != 'GET':
            origin = request.headers.get('origin')
            if origin and origin.rstrip('/') != str(request.base_url).rstrip('/'):
                raise HTTPException(403, 'Cross-origin writes are not allowed.')
            if request.headers.get('content-type', '').split(';')[0] != 'application/json':
                raise HTTPException(415, 'JSON is required.')

    router = APIRouter(dependencies=[Depends(boundary)])

    def service():
        s = Service(home_provider())
        with s.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS confirmations (hash TEXT PRIMARY KEY, intent TEXT NOT NULL, expires REAL NOT NULL)')
        return s

    def call(fn):
        try:
            return fn()
        except (ValueError, PlsiError) as exc:
            raise HTTPException(400, str(exc)) from None
        except (KeyError, TypeError, OSError, sqlite3.Error):
            raise HTTPException(400, 'Hebe could not complete this. Nothing was saved or started.') from None

    def consume(s, token, intent):
        digest = hashlib.sha256(token.encode()).hexdigest()
        with s.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT intent, expires FROM confirmations WHERE hash=?', (digest,)).fetchone()
            db.execute('DELETE FROM confirmations WHERE hash=? OR expires<?', (digest, time.time()))
        if not row or row[1] < time.time() or json.loads(row[0]) != intent:
            raise ValueError('This confirmation expired or does not match. Review and confirm again.')

    @router.get('/bootstrap')
    def bootstrap():
        def read():
            s = service()
            return {'people': _people(s), 'demo_available': next_demo(s) is not None, 'disclaimer': DISCLAIMER}
        return call(read)

    @router.get('/template')
    def template():
        def read():
            from .commands import ROOT
            rows = (ROOT / 'data' / 'demo.csv').read_text().splitlines()
            # Same columns and markers as the demo, with the person renamed so the user only edits values and dates.
            return {'csv': '\n'.join([rows[0]] + [r.replace(DEMO_PERSON, 'me', 1) for r in rows[1:]]) + '\n'}
        return call(read)

    @router.post('/preview')
    def preview(body: PreviewIn):
        def run():
            s = service()
            if body.source == 'demo':
                data = next_demo(s)
                if data is None:
                    raise ValueError('Both demo blood draws are already saved.')
                return _preview_view(s.preview(data, DEMO_BIRTH_YEAR, DEMO_PERSON))
            if not body.person_id or not ID.fullmatch(body.person_id):
                raise ValueError('Choose a short name for this person, using letters, numbers and dashes.')
            if body.birth_year is None or not 1900 <= body.birth_year <= date.today().year:
                raise ValueError('Enter a birth year such as 1981.')
            if body.replaces and not re.fullmatch('[0-9a-f]{64}', body.replaces):
                raise ValueError('Unknown blood draw.')
            return _preview_view(s.preview(body.csv.encode('utf-8'), body.birth_year, body.person_id, body.replaces or None))
        return call(run)

    @router.post('/confirm')
    def confirm(body: ConfirmIn):
        def prepare():
            s = service()
            if body.action == 'start':
                date.fromisoformat(body.start_on)
                key = Plans(s.home).draft(body.id)[0]
                intent = {'action': 'start', 'id': key, 'start_on': body.start_on}
            elif body.action == 'delete':
                intent = {'action': 'delete', 'id': s.result(body.id)['id']}
            elif body.action == 'delete_person':
                if not ID.fullmatch(body.id) or not s.history(body.id):
                    raise ValueError('Unknown person.')
                intent = {'action': 'delete_person', 'id': body.id}
            else:
                intent = {'action': 'save', 'id': body.id}
            token = secrets.token_urlsafe(32)
            with s.db() as db:
                db.execute('DELETE FROM confirmations WHERE expires<?', (time.time(),))
                if db.execute('SELECT COUNT(*) FROM confirmations').fetchone()[0] >= 30:
                    raise ValueError('Too many pending confirmations. Try again in a few minutes.')
                db.execute('INSERT INTO confirmations VALUES (?,?,?)',
                           (hashlib.sha256(token.encode()).hexdigest(), json.dumps(intent, sort_keys=True), time.time() + 300))
            return {'confirmation': token, 'expires_in': 300}
        return call(prepare)

    @router.post('/save')
    def save(body: SaveIn):
        def run():
            s = service()
            consume(s, body.confirmation, {'action': 'save', 'id': body.id})
            saved = s.commit(body.id, True)
            return {'saved': _summary(saved), 'people': _people(s)}
        return call(run)

    @router.get('/draw/{result_id}')
    def draw(result_id: str):
        def read():
            r = service().result(result_id)
            return {'id': r['id'], 'person_id': r['person_id'], 'birth_year': r['birth_year'], 'measured_at': r['measured_at'],
                    'demo': r['person_id'] == DEMO_PERSON,
                    'rows': [{'marker': x['marker'], 'value': x['value'], 'unit': x['unit']} for x in r['rows']]}
        return call(read)

    @router.post('/delete')
    def delete(body: DeleteIn):
        def run():
            s = service()
            consume(s, body.confirmation, {'action': 'delete', 'id': body.id})
            person = s.delete_draw(body.id)
            return {'deleted': body.id, 'person_id': person, 'people': _people(s), 'demo_available': next_demo(s) is not None}
        return call(run)

    @router.post('/delete-person')
    def delete_person(body: DeleteIn):
        def run():
            s = service()
            consume(s, body.confirmation, {'action': 'delete_person', 'id': body.id})
            out = s.delete_person(body.id)
            return {**out, 'people': _people(s), 'demo_available': next_demo(s) is not None}
        return call(run)

    @router.post('/discard')
    def discard(body: DiscardIn):
        return call(lambda: (service().discard(body.id), {'ok': True})[1])

    @router.get('/report/{result_id}')
    def report(result_id: str, embed: int = 0, theme: str = 'light'):
        def run():
            if not re.fullmatch('[0-9a-f]{64}', result_id):
                raise ValueError('Unknown result.')
            html = service().report(result_id)
            if embed:  # inside the Hebe page the report reports its height, so the page scrolls once
                css = EMBED_THEME.get(theme, EMBED_THEME['light']) + EMBED_LAYOUT
                html = html.replace('</head>', '<style>' + css + '</style></head>', 1).replace('</body>', EMBED + '</body>', 1)
            return {'html': html}
        return call(run)

    @router.get('/plans/{person}')
    def plans(person: str):
        def run():
            if not ID.fullmatch(person):
                raise ValueError('Unknown person.')
            p = Plans(home_provider())
            o = p.overview(person)
            listed = o['plans'] if isinstance(o['plans'], list) else o['plans'].get('plans', [])
            return {'drafts': [_draft_view(p, d) for d in reversed(o['drafts'])],
                    'plans': [{'id': x.get('plan_id'), 'state': x.get('state'), 'objective': x.get('objective', ''),
                               'start': x.get('start'), 'review_at': x.get('review_at')} for x in listed]}
        return call(run)

    @router.post('/plans/start')
    def start(body: StartIn):
        def run():
            s = service()
            p = Plans(s.home)
            key = p.draft(body.id)[0]
            consume(s, body.confirmation, {'action': 'start', 'id': key, 'start_on': body.start_on})
            return p.start(key, body.start_on)
        return call(run)

    return router
