"""Runs the unchanged, pinned PLSI toolbelt (vendor/plsi) as a child process.

Arguments are always passed as an argument list, never through a shell. Only an allowlist of PLSI commands can be
reached. PLSI keeps its own append-only log under <plugin-data>/plsi; Hebe feeds it only confirmed snapshots.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

VENDOR = Path(__file__).resolve().parents[1] / 'vendor' / 'plsi'
BOOT = ('import os, sys; sys.path.insert(0, os.environ["HEBE_PLSI_SRC"]); '
        'sys.path.extend(p for p in os.environ["HEBE_PLSI_DEPS"].split(os.pathsep) if p); '
        'from plsi.cli import main; sys.exit(main(sys.argv[1:]))')


def dependency_paths():
    """Where this process loads PLSI's two dependencies from. Hermes adds its packages to sys.path at runtime,
    so a child interpreter has to be told the same locations."""
    try:
        import pydantic, yaml
    except ImportError:
        raise PlsiError('PLSI needs pydantic and PyYAML, which Hermes normally provides.') from None
    paths = []
    for module in (pydantic, yaml):
        root = str(Path(module.__file__).resolve().parents[1])
        if root not in paths:
            paths.append(root)
    return os.pathsep.join(paths)
ALLOWED = {('init',), ('ingest',), ('project',), ('state', 'show'), ('calc', 'derive'), ('evidence', 'search'),
           ('evidence', 'verify'), ('screen',), ('plan', 'check'), ('plan', 'record'), ('plan', 'adopt'),
           ('plan', 'list'), ('due',)}
# LOINC codes accepted by the pinned blood_phenoage map for each canonical unit
LOINC = {'albumin': '1751-7', 'creatinine': '14682-9', 'glucose': '14749-6', 'crp': '1988-5',
         'lymphocyte_pct': '736-9', 'mcv': '787-2', 'rdw': '788-0', 'alp': '6768-6', 'wbc': '6690-2'}


class PlsiError(ValueError):
    """PLSI refused a request or could not run."""


class Plsi:
    def __init__(self, home, timeout=120):
        self.home = Path(home)
        self.data = self.home / 'plsi'
        self.data.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.timeout = timeout

    def run(self, *args):
        args = [str(a) for a in args]
        key = tuple(args[:2]) if tuple(args[:2]) in ALLOWED else tuple(args[:1])
        if key not in ALLOWED:
            raise PlsiError(f'PLSI command not allowed: {" ".join(args[:2])}')
        env = {'HOME': str(self.home), 'PATH': os.environ.get('PATH', '/usr/bin:/bin'),
               'PLSI_HOME': str(self.data), 'PLSI_ENV_FILE': str(self.home / 'plsi.env.absent'),
               'HEBE_PLSI_SRC': str(VENDOR / 'src'), 'HEBE_PLSI_DEPS': dependency_paths(),
               'PYTHONDONTWRITEBYTECODE': '1'}
        for name in ('PLSI_NOW', 'PLSI_TEST_MODE', 'LANG', 'TMPDIR', 'SSL_CERT_FILE'):
            if name in os.environ:
                env[name] = os.environ[name]
        try:
            proc = subprocess.run([sys.executable, '-I', '-c', BOOT, *args], env=env, cwd=self.home,
                                  capture_output=True, text=True, timeout=self.timeout)
        except subprocess.TimeoutExpired:
            raise PlsiError('PLSI did not answer in time.') from None
        try:
            out = json.loads(proc.stdout)
        except ValueError:
            raise PlsiError('PLSI returned no result.') from None
        if not out.get('ok'):
            error = out.get('error') or {}
            raise PlsiError(f'PLSI refused: {error.get("message") or error or "unknown error"}')
        return out['data']

    def write(self, name, payload):
        work = self.home / 'plsi-work'
        work.mkdir(exist_ok=True, mode=0o700)
        path = work / name
        path.write_text(json.dumps(payload, sort_keys=True))
        return path

    def sync(self, results, demo=False):
        """Feed confirmed Hebe snapshots of one person into PLSI and project blood_phenoage. Idempotent:
        PLSI reports repeated observations as duplicates."""
        from .service import UNITS
        if not results:
            raise PlsiError('No confirmed blood draws for this person.')
        person = results[0]['person_id']
        self.run('init', '--instance', person, '--birth-year', results[0]['birth_year'],
                 '--relation', 'sample' if demo else 'self')
        lines = ['effective_at,text,value,unit,code_system,code']
        for r in results:
            for marker, code in LOINC.items():
                lines.append(f'{r["measured_at"]}T12:00:00Z,{marker},{r["values"][marker]!r},{UNITS[marker]},loinc,{code}')
        path = self.write(f'{person}-draws.csv', None)
        path.write_text('\n'.join(lines) + '\n')
        ingest = self.run('ingest', '--instance', person, '--csv', path)
        if ingest['counts'].get('rejected'):
            raise PlsiError('PLSI rejected confirmed values; nothing was planned.')
        state = self.run('project', '--instance', person, '--map', 'blood_phenoage')['state']
        return state
