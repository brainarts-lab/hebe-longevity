"""Plans the PLSI way, run inside Hermes.

The model drafts a PlanInput (PLSI's own contract). Hebe adds one gate in front of PLSI, then runs PLSI's original
`screen` and `plan check`. A separate model call challenges the draft with only the plan, the state and the
screening, never the planner's reasoning. Only the user's /hebe plan start can record and adopt a plan.
"""
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import time

from .plsi_bridge import Plsi, PlsiError, VENDOR
from .service import Service, encode, DEMO_PERSON, DISCLAIMER

PLAN_ID = re.compile(r'[0-9a-f]{64}')
CHALLENGER_SKILL = VENDOR / 'skills' / 'challenger' / 'challenge' / 'SKILL.md'
CHALLENGER_NOTE = '''You run inside Hebe Longevity on Hermes as PLSI Challenger, in Predictions mode and Fit mode.
You have no tools. Everything you may use is in the user message: the plan, the current blood_phenoage state and
PLSI's screening records. Care context, history and other maps are not available here; name that gap instead of
assuming. Reply with one line per objection: [major] or [minor], the action or prediction id, the objection and,
if you cite a source, its PMID or DOI. End with exactly one line: VERDICT: no objections | VERDICT: revise.'''


def hebe_gate(plan):
    """Hebe's consistency checks before PLSI sees the plan. Reproduced PLSI gap: an RxNorm-coded action with a
    category other than drug or supplement skips label screening entirely."""
    problems = []
    if not isinstance(plan, dict) or not isinstance(plan.get('actions'), list):
        return ['The plan must be a PLSI PlanInput object with an actions list.']
    for action in plan['actions']:
        if not isinstance(action, dict):
            problems.append('Every action must be an object.')
            continue
        code = action.get('code') or {}
        if isinstance(code, dict) and code.get('system') == 'rxnorm' and action.get('category') not in ('drug', 'supplement'):
            problems.append(f'Action {action.get("local_id")!r} carries an RxNorm code but category '
                            f'{action.get("category")!r}. Use category drug or supplement so PLSI screens it.')
    return problems


class Plans:
    def __init__(self, home):
        self.home = Path(home)
        self.service = Service(home)
        self.plsi = Plsi(home)
        with self.service.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS plan_drafts (id TEXT PRIMARY KEY, person TEXT NOT NULL, body TEXT NOT NULL, '
                       'created REAL NOT NULL, objections TEXT, recorded_plan TEXT)')

    def _sync(self, person):
        history = self.service.history(person)
        with self.service.db() as db:
            started = db.execute('SELECT 1 FROM plan_drafts WHERE person=? AND recorded_plan IS NOT NULL', (person,)).fetchone()
        return self.plsi.sync(history, demo=person == DEMO_PERSON, has_plans=bool(started))

    def state(self, person):
        state = self._sync(person)
        coords = {k: {'value': v.get('value'), 'unit': v.get('unit'), 'status': v.get('status'),
                      'observed_at': v.get('observed_at')} for k, v in state['coordinates'].items()}
        return {'instance': person, 'map_id': 'blood_phenoage', 'state_hash': state.get('state_hash'),
                'coordinates': coords}

    def check(self, person, plan, findings=None):
        problems = hebe_gate(plan)
        if problems:
            return {'ok': False, 'stage': 'hebe_gate', 'violations': problems,
                    'next': 'Fix the actions and run hebe_plan_check again. Nothing was screened or saved.'}
        self._sync(person)
        plan_id = hashlib.sha256(encode({'person': person, 'plan': plan, 'findings': findings or {}}).encode()).hexdigest()
        plan_path = self.plsi.write(f'{plan_id}.plan.json', plan)
        args = ['screen', '--instance', person, '--file', plan_path]
        if findings:
            args += ['--findings', self.plsi.write(f'{plan_id}.findings.json', findings)]
        screened = self.plsi.run(*args)
        outcomes = screened.get('outcomes', {})
        try:
            checked = self.plsi.run('plan', 'check', '--instance', person, '--file', plan_path)
        except PlsiError as error:
            if not error.violations:
                raise
            # PLSI rule G3: a caution needs the user's acknowledgement. In Hebe that is the start dialog,
            # so it is pending here, not a fault in the draft. Every other violation stays a violation.
            ids = [a.get('local_id') for a in plan['actions']]
            def awaiting(v):
                path = str(v.get('path', ''))
                index = int(path.split('.')[1]) if path.startswith('actions.') and path.split('.')[1].isdigit() else -1
                return v.get('rule') == 'G3' and 0 <= index < len(ids) and outcomes.get(ids[index]) == 'caution'
            checked = {'ok': not [v for v in error.violations if not awaiting(v)],
                       'violations': [f'{v.get("path")}: {v.get("message")} ({v.get("hint")})' for v in error.violations if not awaiting(v)],
                       'awaiting_acknowledgement': [ids[int(str(v['path']).split('.')[1])] for v in error.violations if awaiting(v)]}
        body = {'person': person, 'plan': plan, 'findings': findings or {}, 'screen': screened, 'check': checked}
        with self.service.db() as db:
            db.execute('INSERT INTO plan_drafts (id, person, body, created) VALUES (?,?,?,?) '
                       'ON CONFLICT(id) DO UPDATE SET body=excluded.body, created=excluded.created',
                       (plan_id, person, encode(body), time.time()))
        return {'ok': checked.get('ok', False), 'stage': 'plsi', 'plan_id': plan_id, 'screening': outcomes,
                'awaiting_user_acknowledgement': checked.get('awaiting_acknowledgement', []),
                'blocked': sorted(a for a, o in outcomes.items() if o == 'block'),
                'cautions': sorted(a for a, o in outcomes.items() if o == 'caution'),
                'violations': checked.get('violations', []),
                'next': ('Fix these PLSI violations and run hebe_plan_check again.' if not checked.get('ok', False) else
                         'Run hebe_challenge with this plan_id and answer the objections. Then ask the user to start it on the '
                         f'Plans tab of the Hebe page or with /hebe plan start {plan_id[:12]}. Cautions are acknowledged by the user '
                         'when they start. You cannot start plans.')}

    def draft(self, plan_id):
        if not isinstance(plan_id, str) or not re.fullmatch(r'[0-9a-f]{6,64}', plan_id):
            raise ValueError('Unknown plan.')
        with self.service.db() as db:
            rows = db.execute('SELECT id, body, objections, recorded_plan FROM plan_drafts WHERE id LIKE ?',
                              (plan_id + '%',)).fetchall()
        if len(rows) != 1:
            raise ValueError('Unknown or ambiguous plan id.')
        key, body, objections, recorded = rows[0]
        return key, json.loads(body), objections, recorded

    def challenge(self, plan_id, llm):
        key, body, _, _ = self.draft(plan_id)
        state = self.state(body['person'])
        material = {'plan': body['plan'], 'state': state, 'screening': body['screen'].get('records', []),
                    'plan_check': body['check']}
        messages = [{'role': 'system', 'content': CHALLENGER_SKILL.read_text() + '\n\n' + CHALLENGER_NOTE},
                    {'role': 'user', 'content': json.dumps(material, sort_keys=True)}]
        text = (llm(messages) or '').strip()
        if not text:
            raise ValueError('The challenger returned nothing; the plan is unchanged.')
        with self.service.db() as db:
            db.execute('UPDATE plan_drafts SET objections=? WHERE id=?', (text, key))
        return {'plan_id': key, 'objections': text,
                'next': 'Revise the plan with hebe_plan_check or rebut each objection with a source, then ask the '
                        f'user to enter /hebe plan start {key[:12]}.'}

    def summary(self, plan_id):
        key, body, objections, recorded = self.draft(plan_id)
        plan = body['plan']; outcomes = body['screen'].get('outcomes', {})
        lines = [f'Plan {key[:12]} for {body["person"]}', '', f'Goal: {plan.get("objective", "not stated")}', '', 'Actions']
        for a in plan.get('actions', []):
            extra = ', '.join(x for x in (a.get('dose'), a.get('schedule')) if x)
            flag = {'caution': ' (caution from screening)', 'block': ' (blocked by screening)'}.get(outcomes.get(a.get('local_id')), '')
            lines.append(f'- {a.get("description")}{" (" + extra + ")" if extra else ""}{flag}')
        lines += ['', 'Predictions']
        for p in plan.get('predictions', []):
            label = 'No-action control' if not p.get('driven_by') else f'With {", ".join(p["driven_by"])}'
            lines.append(f'- {label}: {p.get("coordinate")} {p.get("expected")} '
                         f'({p.get("low")} to {p.get("high")}) after {p.get("horizon_days")} days')
        rule = plan.get('revision_rule') or {}
        if rule.get('review_after_days'):
            lines.append(f'Review after {rule["review_after_days"]} days')
        lines += ['', 'Challenger', objections or 'Not challenged yet.']
        return key, body, recorded, '\n'.join(lines)

    def start(self, plan_id, start_on):
        key, body, objections, recorded = self.draft(plan_id)
        if recorded:
            return {'plan_id': recorded, 'already_started': True}
        if not objections:
            raise ValueError('Run the challenger first; Hebe starts only challenged plans.')
        date.fromisoformat(start_on)
        person, plan = body['person'], json.loads(json.dumps(body['plan']))
        if hebe_gate(plan):
            raise ValueError('The plan no longer passes the Hebe gate.')
        self._sync(person)
        args = ['screen', '--instance', person, '--file', self.plsi.write(f'{key}.start.json', plan)]
        if body.get('findings'):  # the planner's findings can only raise the outcome; keep them for the start
            args += ['--findings', self.plsi.write(f'{key}.start-findings.json', body['findings'])]
        screened = self.plsi.run(*args)
        outcomes = screened.get('outcomes', {})
        if any(o == 'block' for o in outcomes.values()):
            raise ValueError('PLSI screening blocks an action; the plan cannot start.')
        for action in plan['actions']:
            if outcomes.get(action.get('local_id')) == 'caution':
                action['acknowledged'] = True
                action['acknowledgement_note'] = f'Started by the user with /hebe plan start on {date.today().isoformat()}'
        path = self.plsi.write(f'{key}.start.json', plan)
        rec = self.plsi.run('plan', 'record', '--instance', person, '--file', path)
        plan_ref = rec.get('plan_id') or rec.get('plan', {}).get('plan_id')
        if not plan_ref:
            raise PlsiError('PLSI did not return a plan id.')
        self.plsi.run('plan', 'adopt', '--instance', person, '--plan', plan_ref, '--start-on', start_on)
        with self.service.db() as db:
            db.execute('UPDATE plan_drafts SET recorded_plan=? WHERE id=?', (plan_ref, key))
        return {'plan_id': plan_ref, 'already_started': False}

    def overview(self, person):
        self._sync(person)
        listed = self.plsi.run('plan', 'list', '--instance', person)
        due = self.plsi.run('due', '--instance', person)
        with self.service.db() as db:
            drafts = [{'id': k, 'created': c, 'challenged': bool(o), 'started_as': r} for k, c, o, r in
                      db.execute('SELECT id, created, objections, recorded_plan FROM plan_drafts WHERE person=? ORDER BY created',
                                 (person,))]
        return {'plans': listed, 'due': due, 'drafts': drafts, 'disclaimer': DISCLAIMER}
