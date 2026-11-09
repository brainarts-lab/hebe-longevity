"""Self-contained, offline report. No model, remote assets or scripts."""
from datetime import date
import hashlib
import html
from pathlib import Path

NAMES = {'albumin':('Albumin','Liver and nutrition'),
         'creatinine':('Creatinine','Kidney function'),
         'glucose':('Glucose','Blood sugar'),
         'crp':('C-reactive protein','Inflammation'),
         'lymphocyte_pct':('Lymphocytes','Immune cells'),
         'mcv':('Mean cell volume','Red blood cell size'),
         'rdw':('Cell size variation','Red blood cell spread'),
         'alp':('Alkaline phosphatase','Liver and bone'),
         'wbc':('White blood cells','Immune system')}
UNIT_LABELS = {'umol/L':'µmol/L','10*3/uL':'×10³/µL'}

CSS = '''
:root{color-scheme:light dark;
--bg:#f2f2f7;--surface:#ffffff;--ink:#1d1d1f;--muted:#6e6e73;--faint:#8e8e93;--line:#e5e5ea;
--accent:#0a8f7f;--track:#ececf1;--calendar:#aeaeb2;--demo:#fff4d6;--demo-ink:#7a5600}
@media (prefers-color-scheme:dark){:root{
--bg:#000000;--surface:#1c1c1e;--ink:#f5f5f7;--muted:#a1a1a6;--faint:#8e8e93;--line:#2c2c2e;
--accent:#30d1b8;--track:#2c2c2e;--calendar:#636366;--demo:#3a2e0c;--demo-ink:#ffd66b}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);
font:17px/1.47 -apple-system,BlinkMacSystemFont,"SF Pro Text","Helvetica Neue",Arial,sans-serif;
-webkit-font-smoothing:antialiased;letter-spacing:-.01em}
main{max-width:680px;margin:0 auto;padding:28px 20px 56px}
.top{display:flex;align-items:baseline;justify-content:space-between;margin:0 4px 28px}
.brand{font-size:17px;font-weight:600;letter-spacing:-.02em}
.brand span{color:var(--muted);font-weight:400}
.where{font-size:13px;color:var(--muted)}
.demo{background:var(--demo);color:var(--demo-ink);border-radius:14px;padding:12px 16px;font-size:15px;margin:0 0 20px}
.demo strong{font-weight:600}
.hero{background:var(--surface);border-radius:24px;padding:32px 28px 28px;margin:0 0 36px}
h1{font-size:17px;font-weight:600;margin:0;color:var(--accent);letter-spacing:-.01em}
.age{font-family:ui-rounded,"SF Pro Rounded",-apple-system,BlinkMacSystemFont,sans-serif;
font-size:clamp(84px,22vw,124px);font-weight:700;line-height:1;letter-spacing:-.045em;margin:14px 0 6px;
font-variant-numeric:tabular-nums}
.age small{font-size:28px;font-weight:600;letter-spacing:-.01em;color:var(--muted);margin-left:6px}
.verdict{font-size:22px;line-height:1.3;font-weight:600;letter-spacing:-.02em;margin:0 0 28px}
.compare{display:grid;gap:14px;margin:0}
.bar{display:grid;grid-template-columns:1fr auto;row-gap:6px;align-items:baseline}
.bar .k{font-size:15px;color:var(--muted)}
.bar .v{font-size:15px;font-weight:600;font-variant-numeric:tabular-nums}
.track{grid-column:1/-1;height:12px;border-radius:6px;background:var(--track);overflow:hidden}
.fill{height:100%;border-radius:6px;background:var(--accent)}
.bar.calendar .fill{background:var(--calendar)}
.when{font-size:13px;color:var(--faint);margin:20px 0 0}
section{margin:0 0 36px}
h2{font-size:22px;font-weight:700;letter-spacing:-.025em;margin:0 4px 10px}
.group{background:var(--surface);border-radius:18px;margin:0;padding:0;list-style:none;overflow:hidden}
.points li{position:relative;padding:14px 20px 14px 44px;font-size:16px;line-height:1.42}
.points li+li{border-top:1px solid var(--line);margin-left:44px;padding-left:0}
.points li::before{content:"";position:absolute;left:20px;top:22px;width:8px;height:8px;border-radius:50%;background:var(--accent)}
.points li+li::before{left:-24px}
.points strong{font-weight:600}
.markers li{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:12px 20px;min-height:60px}
.markers li+li{border-top:1px solid var(--line);margin-left:20px;padding-left:0}
.name{display:flex;flex-direction:column;min-width:0}
.name b{font-weight:500;font-size:16px}
.name span{font-size:13px;color:var(--muted)}
.value{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums;font-size:17px;font-weight:600}
.value span{font-size:13px;font-weight:400;color:var(--muted);margin-left:4px}
.note{font-size:13px;color:var(--muted);margin:8px 20px 0}
details{background:var(--surface);border-radius:18px;margin:0 0 12px}
summary{list-style:none;cursor:pointer;padding:16px 20px;font-size:16px;font-weight:500;display:flex;justify-content:space-between;align-items:center;border-radius:18px}
summary::-webkit-details-marker{display:none}
summary::after{content:"";width:8px;height:8px;border-right:2px solid var(--faint);border-bottom:2px solid var(--faint);transform:rotate(45deg) translateY(-3px);transition:transform .2s ease}
details[open] summary::after{transform:rotate(225deg) translate(-2px,-2px)}
summary:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.inner{padding:0 20px 18px;font-size:14px;color:var(--muted)}
.inner p{margin:0 0 12px}
.inner dl{margin:0}
.inner dt{color:var(--ink);font-weight:500;margin-top:12px}
.inner dd{margin:2px 0 0;font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:12px;overflow-wrap:anywhere}
footer{font-size:12px;line-height:1.5;color:var(--faint);margin:28px 4px 0}
footer p{margin:0 0 6px}
@media (max-width:420px){main{padding:20px 16px 40px}.hero{padding:26px 22px 22px;border-radius:22px}.verdict{font-size:20px}}
@media (prefers-reduced-motion:reduce){summary::after{transition:none}}
@media print{:root{--bg:#fff;--surface:#fff}body{background:#fff}.hero,.group,details{border:1px solid #ddd}details .inner{display:block}}
'''

def _date(iso):
    try:
        d=date.fromisoformat(iso)
        return f'{d.day} {d.strftime("%B %Y")}'
    except (TypeError,ValueError):
        return str(iso)

def render(result, units):
    e=lambda value:html.escape(str(value),quote=True)
    demo_path=Path(__file__).resolve().parents[1]/'data/demo.csv'
    demo=(result['person_id']=='alex-demo' and result['birth_year']==1981 and
          result['source_sha256']==hashlib.sha256(demo_path.read_bytes()).hexdigest())
    banner=('<p class="demo"><strong>Sample report.</strong> These values belong to the fictional Alex Demo, not to you.</p>'
            if demo else '')
    pheno=result['pheno_age']; chrono=result['chrono_age']; delta=result['delta']
    if abs(delta)<0.05:verdict='The same as your calendar age'
    elif delta<0:verdict=f'{abs(delta):.1f} years below your calendar age'
    else:verdict=f'{delta:.1f} years above your calendar age'
    scale=max(pheno,chrono)*1.12 or 1
    width=lambda v:f'{max(4,min(100,v/scale*100)):.1f}%'
    rows=''.join(
        f'<li><div class="name"><b>{e(NAMES.get(m,(m,""))[0])}</b><span>{e(NAMES.get(m,(m,""))[1])}</span></div>'
        f'<div class="value">{e(format(result["values"][m],"g"))}<span>{e(UNIT_LABELS.get(units[m],units[m]))}</span></div></li>'
        for m in units)
    who='' if demo else f' for {e(result["person_id"])}'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="light dark"><title>Hebe Longevity Report</title><style>{CSS}</style></head><body><main>
<div class="top"><div class="brand">Hebe <span>Longevity</span></div><div class="where">Stored on this device</div></div>
{banner}
<section class="hero" aria-labelledby="result">
<h1 id="result">Blood PhenoAge</h1>
<div class="age">{pheno:.1f}<small>years</small></div>
<p class="verdict">{e(verdict)}</p>
<div class="compare">
<div class="bar"><span class="k">Blood PhenoAge</span><span class="v">{pheno:.1f}</span><div class="track" aria-hidden="true"><div class="fill" style="width:{width(pheno)}"></div></div></div>
<div class="bar calendar"><span class="k">Calendar age at collection</span><span class="v">{chrono:.1f}</span><div class="track" aria-hidden="true"><div class="fill" style="width:{width(chrono)}"></div></div></div>
</div>
<p class="when">Blood drawn {e(_date(result['measured_at']))}{who}</p>
</section>

<section aria-labelledby="meaning"><h2 id="meaning">What this means</h2>
<ul class="group points">
<li><strong>An estimate from nine blood markers</strong> and your age, not a diagnosis.</li>
<li><strong>One blood draw</strong> shows a snapshot, not a trend.</li>
<li><strong>A lower number</strong> does not predict how long you will live.</li>
</ul></section>

<section aria-labelledby="markers"><h2 id="markers">Your blood markers</h2>
<ul class="group markers">{rows}</ul>
<p class="note">The values you confirmed before the calculation.</p></section>

<section aria-labelledby="next"><h2 id="next">What comes next</h2>
<ul class="group points">
<li><strong>Add another blood draw</strong> later to see how your result changes over time.</li>
<li><strong>Talk to your doctor</strong> about any value that worries you.</li>
<li><strong>Coming later:</strong> which markers move your result most.</li>
</ul></section>

<details><summary>How it was calculated</summary><div class="inner">
<p>Hebe uses the published PhenoAge formula from the open-source PLSI project. The calculation runs locally and is fully traceable to these inputs.</p>
<dl><dt>Input file fingerprint</dt><dd>{e(result['source_sha256'])}</dd>
<dt>Formula source version</dt><dd>{e(result['plsi_commit'])}</dd>
<dt>Result ID</dt><dd>{e(result['id'])}</dd>
<dt>Blood draw</dt><dd>{e(result['draw_id'])}</dd></dl></div></details>
<details><summary>Privacy</summary><div class="inner">
<p>This page loads no scripts, fonts or other files from the internet.</p>
<p>Hermes may still send chat messages and tool results to the cloud model you have configured.</p></div></details>

<footer><p>Research and education only. Hebe does not diagnose or recommend treatment, and it is not clinically validated.</p>
<p>Built on PLSI by Insilico Medicine (MIT). Not affiliated with or endorsed by Insilico Medicine or xAI.</p></footer>
</main></body></html>'''
