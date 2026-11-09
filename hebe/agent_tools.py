"""Model-facing tools for planning. None of them can record or start a plan; that is /hebe plan start."""
import json
import re
import sqlite3

from .plans import Plans
from .plsi_bridge import Plsi, PlsiError
from .service import ID, DISCLAIMER

EVIDENCE_SOURCES = ('pubmed', 'europepmc', 'ctgov', 'openfda', 'evipedia')
EVIDENCE_KINDS = ('pmid', 'doi', 'nct')
MARKERS = ('albumin', 'creatinine', 'glucose', 'crp', 'lymphocyte_pct', 'mcv', 'rdw', 'alp', 'wbc')


def _ok(**data):
    return json.dumps({'ok': True, **data, 'disclaimer': DISCLAIMER})


def _person(args):
    person = args.get('person_id')
    if not isinstance(person, str) or not ID.fullmatch(person):
        raise ValueError('person_id must be a saved Hebe person id.')
    return person


def run_tool(name, home, args, llm=None):
    try:
        if not isinstance(args, dict):
            raise ValueError('Expected structured arguments.')
        if name == 'hebe_state':
            return _ok(state=Plans(home).state(_person(args)))
        if name == 'hebe_evidence':
            plsi = Plsi(home)
            if args.get('action') == 'search':
                if args.get('source') not in EVIDENCE_SOURCES or not isinstance(args.get('query'), str):
                    raise ValueError(f'search needs source in {EVIDENCE_SOURCES} and a query.')
                limit = min(max(int(args.get('limit', 10)), 1), 20)
                return _ok(result=plsi.run('evidence', 'search', '--source', args['source'], '--query',
                                           args['query'][:300], '--limit', limit))
            if args.get('action') == 'verify':
                if args.get('kind') not in EVIDENCE_KINDS or not isinstance(args.get('id'), str) \
                        or not re.fullmatch(r'[A-Za-z0-9./_:()-]{1,200}', args['id']):
                    raise ValueError(f'verify needs kind in {EVIDENCE_KINDS} and an identifier.')
                return _ok(result=plsi.run('evidence', 'verify', '--kind', args['kind'], '--id', args['id']))
            raise ValueError('action must be search or verify.')
        if name == 'hebe_calc':
            person = _person(args)
            Plans(home)._sync(person)
            values = args.get('set') or {}
            if not isinstance(values, dict) or any(k not in MARKERS for k in values):
                raise ValueError(f'set maps markers in canonical units: {MARKERS}.')
            coordinate = args.get('coordinate', 'phenoage')
            if coordinate not in ('phenoage', 'phenoage_acceleration'):
                raise ValueError('coordinate must be phenoage or phenoage_acceleration.')
            cmd = ['calc', 'derive', '--instance', person, '--map', 'blood_phenoage', '--coordinate', coordinate]
            for k, v in values.items():
                cmd += ['--set', f'{k}={float(v)!r}']
            if args.get('at'):
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(args['at'])):
                    raise ValueError('at must be YYYY-MM-DD.')
                cmd += ['--at', f'{args["at"]}T12:00:00Z']
            return _ok(result=Plsi(home).run(*cmd))
        if name == 'hebe_plan_check':
            plan, findings = args.get('plan'), args.get('findings')
            if findings is not None and not isinstance(findings, dict):
                raise ValueError('findings must be an object keyed by action id.')
            return json.dumps(Plans(home).check(_person(args), plan, findings))
        if name == 'hebe_challenge':
            if llm is None:
                raise ValueError('No challenger model is configured.')
            return _ok(**Plans(home).challenge(args.get('plan_id'), llm))
        if name == 'hebe_plans':
            return _ok(**Plans(home).overview(_person(args)))
        raise ValueError('Unknown Hebe tool.')
    except (ValueError, PlsiError) as error:
        return json.dumps({'ok': False, 'error': str(error)})
    except (KeyError, TypeError, OSError, sqlite3.Error):
        return json.dumps({'ok': False, 'error': 'Hebe could not complete this request. Nothing was started.'})


def obj(properties, required):
    return {'type': 'object', 'properties': properties, 'required': required, 'additionalProperties': False}


PERSON = {'type': 'string', 'description': 'Saved Hebe person id, for example alex-demo'}
SCHEMAS = {
    'hebe_state': ('Current PLSI blood_phenoage state of a person, built from confirmed Hebe draws.',
                   obj({'person_id': PERSON}, ['person_id'])),
    'hebe_evidence': ('PLSI evidence search or identifier verification (PubMed, Europe PMC, ClinicalTrials.gov, '
                      'openFDA, Evipedia). Topic only: never put personal data in a query.',
                      obj({'action': {'type': 'string', 'enum': ['search', 'verify']},
                           'source': {'type': 'string', 'enum': list(EVIDENCE_SOURCES)},
                           'query': {'type': 'string'}, 'limit': {'type': 'integer'},
                           'kind': {'type': 'string', 'enum': list(EVIDENCE_KINDS)}, 'id': {'type': 'string'}},
                          ['action'])),
    'hebe_calc': ('PLSI calc derive: PhenoAge or acceleration with what-if values in canonical units. Use it for '
                  'expected values of predictions; never compute by hand.',
                  obj({'person_id': PERSON, 'coordinate': {'type': 'string', 'enum': ['phenoage', 'phenoage_acceleration']},
                       'set': {'type': 'object', 'additionalProperties': {'type': 'number'}},
                       'at': {'type': 'string', 'description': 'YYYY-MM-DD, for a prediction horizon'}},
                      ['person_id'])),
    'hebe_plan_check': ('Check a PLSI PlanInput: Hebe gate, then PLSI screen and plan check. Saves a draft and returns '
                        'its plan_id. Never records or starts a plan.',
                        obj({'person_id': PERSON, 'plan': {'type': 'object'}, 'findings': {'type': 'object'}},
                            ['person_id', 'plan'])),
    'hebe_challenge': ('PLSI Challenger in a separate model call. It sees only the plan, the state and the screening, '
                       'not your reasoning.', obj({'plan_id': {'type': 'string'}}, ['plan_id'])),
    'hebe_plans': ('Recorded PLSI plans, predictions due for measurement and Hebe drafts of a person.',
                   obj({'person_id': PERSON}, ['person_id'])),
}
