// Hebe for Hermes Desktop: the page where people add blood results, see their Blood PhenoAge and start plans.
// Saving a draw and starting a plan always need the user's click here; the agent cannot reach these routes.
import React from 'react'
import {
  host, useValue, writeClipboardText, SandboxedFrame,
  ROUTES_AREA, SIDEBAR_NAV_AREA, PALETTE_AREA, TRANSCRIPT_DIRECTIVE_AREA
} from '@hermes/plugin-sdk'

const h = React.createElement
const PATH = '/hebe'
const ASK = [
  'What could I try to lower my Blood PhenoAge?',
  'Explain my latest result in plain words',
  'Which value moved my result the most?',
  'What does Blood PhenoAge measure, and what does it not?'
]

const CSS = `
.hebe{--hb-accent:var(--ui-accent,#0a84ff);--hb-text:var(--ui-text-primary,inherit);--hb-muted:var(--ui-text-secondary,#6e6e73);
--hb-faint:var(--ui-text-tertiary,#8e8e93);--hb-line:var(--ui-stroke-tertiary,rgba(127,127,127,.18));
--hb-card:var(--ui-bg-elevated,rgba(127,127,127,.05));--hb-soft:var(--ui-bg-tertiary,rgba(127,127,127,.08));
--hb-green:var(--ui-green,#30a46c);--hb-teal:#14a38f;--hb-yellow:var(--ui-yellow,#d4a017);--hb-red:var(--ui-red,#e5484d);
box-sizing:border-box;height:100%;overflow:auto;color:var(--hb-text);
font:15px/1.5 -apple-system,BlinkMacSystemFont,"SF Pro Text",system-ui,sans-serif;-webkit-font-smoothing:antialiased}
.hebe *{box-sizing:border-box}.hebe button,.hebe input,.hebe textarea{font:inherit;color:inherit}
.hb-wrap{max-width:1040px;margin:0 auto;padding:28px clamp(18px,4vw,48px) 56px}
.hb-top{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:28px}
.hb-brand{display:flex;align-items:center;gap:10px;font-weight:600;letter-spacing:-.01em}
.hb-mark{flex:none;display:block;border-radius:8px}
.hb-brand small{display:block;font-size:12px;font-weight:500;color:var(--hb-faint);letter-spacing:0}
.hb-pill{font-size:11px;color:var(--hb-muted);border:1px solid var(--hb-line);border-radius:999px;padding:4px 10px;white-space:nowrap}
.hb-eyebrow{font-size:12px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--hb-accent)}
.hb-herogrid{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(260px,1fr);gap:32px;align-items:center}
.hb-sample{padding:22px;display:grid;gap:10px;box-shadow:0 10px 40px rgba(0,0,0,.06)}
.hb-srow{display:flex;justify-content:space-between;align-items:center;gap:10px;font-size:13px;color:var(--hb-muted)}.hb-srow b{color:var(--hb-text);font-variant-numeric:tabular-nums}
.hb-steal{color:var(--hb-teal);font-weight:600;font-size:14px}
.hb-sbig{font-size:56px;font-weight:700;letter-spacing:-.04em;line-height:1}.hb-sbig span{font-size:18px;font-weight:500;color:var(--hb-muted);letter-spacing:0}
.hb-ssub{font-weight:600;margin-bottom:6px}
.hb-sbar{display:grid;gap:5px}.hb-strack{height:7px;border-radius:99px;background:var(--hb-soft);overflow:hidden}.hb-strack div{height:100%;border-radius:99px}
.hb-smove{border-top:1px solid var(--hb-line);padding-top:10px;margin-top:4px}
.hb-hero h1{text-wrap:balance;font-size:clamp(34px,5vw,52px);line-height:1.05;letter-spacing:-.035em;margin:10px 0 14px;font-weight:700}
.hb-hero p{font-size:17px;color:var(--hb-muted);max-width:620px;margin:0 0 24px}
.hb-row{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.hb-btn{border:1px solid var(--hb-line);background:var(--hb-card);border-radius:10px;padding:10px 16px;min-height:42px;cursor:pointer;font-weight:500;transition:transform .12s,background .12s}
.hb-btn:hover:not(:disabled){background:var(--hb-soft)}.hb-btn:active:not(:disabled){transform:scale(.98)}
.hb-btn:disabled{opacity:.45;cursor:not-allowed}
.hebe .hb-primary{background:var(--hb-accent);border-color:transparent;color:var(--ui-accent-foreground,#fff);font-weight:600}
.hebe .hb-primary:hover:not(:disabled){background:var(--hb-accent);filter:brightness(1.08)}
.hb-link{background:none;border:0;padding:0;color:var(--hb-accent);cursor:pointer;font-weight:500}
.hebe :focus-visible{outline:2px solid var(--hb-accent);outline-offset:2px}
.hb-section{margin-top:44px}.hb-section>h2{font-size:20px;letter-spacing:-.02em;margin:0 0 14px}
.hb-steps{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
.hb-card{background:var(--hb-card);border:1px solid var(--hb-line);border-radius:16px;padding:20px}
.hb-step b{display:block;font-size:16px;margin:8px 0 4px;letter-spacing:-.01em}.hb-step p{margin:0;color:var(--hb-muted);font-size:14px}
.hb-num{width:26px;height:26px;border-radius:50%;display:grid;place-items:center;font-size:13px;font-weight:600;background:var(--hb-soft);color:var(--hb-muted)}
.hb-chips{display:flex;flex-wrap:wrap;gap:8px}
.hb-chip{border:1px solid var(--hb-line);background:transparent;border-radius:999px;padding:8px 14px;cursor:pointer;font-size:14px;text-align:left}
.hb-chip:hover{background:var(--hb-soft)}.hb-chip::before{content:"\\201C"}.hb-chip::after{content:"\\201D"}
.hb-note{font-size:13px;color:var(--hb-muted);margin-top:10px}
.hb-foot{margin-top:48px;padding-top:18px;border-top:1px solid var(--hb-line);font-size:12px;color:var(--hb-faint);display:grid;gap:4px}
.hb-tabs{display:flex;gap:4px;padding:4px;background:var(--hb-soft);border-radius:11px;width:max-content;max-width:100%;overflow:auto}
.hb-tab{border:0;background:transparent;border-radius:8px;padding:7px 14px;cursor:pointer;font-weight:500;color:var(--hb-muted);white-space:nowrap}
.hb-tab[aria-selected=true]{background:var(--ui-bg-editor,var(--hb-card));color:var(--hb-text);box-shadow:0 1px 3px rgba(0,0,0,.12)}
.hb-bar{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:14px;margin-bottom:18px}
.hb-person{font-size:24px;font-weight:700;letter-spacing:-.02em}.hb-person small{display:block;font-size:13px;font-weight:400;color:var(--hb-muted);letter-spacing:0}
.hb-frame{width:100%;border:0;display:block;background:transparent}
.hb-ask{margin-top:22px}.hb-ask h3,.hb-card h3{font-size:15px;margin:0 0 10px}
.hb-table{width:100%;border-collapse:collapse;font-size:14px}.hb-table td{padding:10px 0;border-top:1px solid var(--hb-line);vertical-align:top}
.hb-table td:last-child{text-align:right;font-variant-numeric:tabular-nums}.hb-table small{display:block;color:var(--hb-faint);font-size:12px}
.hb-meta{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:6px 0 16px}
.hb-meta small{display:block;font-size:12px;color:var(--hb-faint)}.hb-meta b{font-weight:600}
.hb-checks{list-style:none;padding:0;margin:14px 0 0;display:grid;gap:6px;font-size:14px}
.hb-checks li::before{content:"\\2713";color:var(--hb-green);font-weight:700;margin-right:8px}
.hb-grid2{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(0,1fr);gap:16px;align-items:start}
.hb-field{display:grid;gap:6px;margin-bottom:14px;font-size:13px;font-weight:600}
.hb-field input,.hb-field textarea{width:100%;border:1px solid var(--hb-line);background:var(--ui-bg-input,transparent);border-radius:10px;padding:10px 12px;font-weight:400}
.hb-field textarea{min-height:150px;font:12px/1.5 ui-monospace,SFMono-Regular,monospace;resize:vertical}
.hb-filebtn{position:relative;overflow:hidden;display:inline-flex;align-items:center}.hb-filebtn input{position:absolute;inset:0;opacity:0;cursor:pointer}
.hb-mgrid{display:grid;gap:8px}.hb-mrow{display:grid;grid-template-columns:minmax(0,1fr) 110px 110px;gap:10px;align-items:center;font-size:14px}
.hb-mrow input,.hb-mrow select{width:100%;border:1px solid var(--hb-line);background:var(--ui-bg-input,transparent);border-radius:9px;padding:8px 10px;font-variant-numeric:tabular-nums}
.hb-mrow em{font-style:normal;color:var(--hb-muted);padding-left:10px}
@media(max-width:560px){.hb-mrow{grid-template-columns:1fr 90px 90px}}
.hb-field span{font-weight:400;color:var(--hb-faint)}
.hb-banner{border-radius:12px;padding:12px 14px;margin-bottom:16px;font-size:14px;display:flex;gap:10px;align-items:flex-start}
.hb-error{background:color-mix(in srgb,var(--hb-red) 12%,transparent);border:1px solid color-mix(in srgb,var(--hb-red) 35%,transparent)}
.hb-ok{background:color-mix(in srgb,var(--hb-green) 12%,transparent);border:1px solid color-mix(in srgb,var(--hb-green) 35%,transparent)}
.hb-busy{display:flex;align-items:center;gap:10px;color:var(--hb-muted);font-size:14px;padding:30px 0}
.hb-spin{width:16px;height:16px;border-radius:50%;border:2px solid var(--hb-line);border-top-color:var(--hb-accent);animation:hb-spin .9s linear infinite}
@keyframes hb-spin{to{transform:rotate(360deg)}}
.hb-badge{display:inline-block;font-size:12px;font-weight:600;border-radius:999px;padding:2px 9px;background:var(--hb-soft);color:var(--hb-muted)}
.hb-badge.clear{background:color-mix(in srgb,var(--hb-green) 15%,transparent);color:var(--hb-green)}
.hb-badge.caution{background:color-mix(in srgb,var(--hb-yellow) 18%,transparent);color:var(--hb-yellow)}
.hb-badge.block,.hb-badge.revise{background:color-mix(in srgb,var(--hb-red) 15%,transparent);color:var(--hb-red)}
.hb-plan{display:grid;gap:14px}.hb-plan h3{font-size:17px;margin:0;letter-spacing:-.01em}
.hb-list{list-style:none;margin:0;padding:0;display:grid;gap:8px;font-size:14px}.hb-list li{display:flex;justify-content:space-between;gap:12px;align-items:baseline}
.hb-list small{color:var(--hb-faint)}
.hb-objections{white-space:pre-wrap;font-size:13px;color:var(--hb-muted);background:var(--hb-soft);border-radius:10px;padding:12px;margin:8px 0 0;max-height:260px;overflow:auto}
.hb-confirm{border-top:1px solid var(--hb-line);padding-top:14px;display:grid;gap:12px}
.hb-check{display:flex;gap:10px;align-items:flex-start;font-size:14px}.hb-check input{margin-top:3px;accent-color:var(--hb-accent)}
.hb-empty{text-align:center;padding:40px 20px}.hb-empty p{color:var(--hb-muted);max-width:460px;margin:6px auto 18px}
.hb-options{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.hb-option{text-align:left;cursor:pointer;display:grid;gap:6px}.hb-option:hover{background:var(--hb-soft)}
.hb-option b{font-size:16px}.hb-option span{color:var(--hb-muted);font-size:14px}
.hb-dcard{display:flex;align-items:center;gap:16px;border:1px solid var(--hb-line);border-radius:14px;padding:14px 16px;max-width:520px;background:var(--hb-card)}
.hb-dcard .hb-big{font-size:30px;font-weight:700;letter-spacing:-.03em;font-variant-numeric:tabular-nums}
@media(max-width:760px){.hb-herogrid,.hb-steps,.hb-options,.hb-grid2,.hb-meta{grid-template-columns:1fr}}
@media(prefers-reduced-motion:reduce){.hb-spin{animation:none}.hb-btn{transition:none}}
`

function message(e) {
  const text = String((e && e.message) || e || '')
  try { const d = JSON.parse(text.slice(text.indexOf('{'))).detail; if (typeof d === 'string') return d } catch {}
  return text.length > 300 || !text ? 'Hebe could not reach Hermes. Check that the gateway is running, then try again.' : text
}
const one = n => (Math.round(n * 10) / 10).toFixed(1)
const day = iso => { try { return new Date(iso + 'T12:00:00Z').toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' }) } catch { return iso } }
const today = () => new Date().toISOString().slice(0, 10)
const cap = t => t ? t[0].toUpperCase() + t.slice(1) : t
const plain = t => String(t || '').replace(/phenoage_acceleration/g, 'PhenoAge gap').replace(/blood_phenoage/g, 'Blood PhenoAge').replace(/phenoage/g, 'PhenoAge').replace(/_/g, ' ')
const signed = n => (n > 0 ? '+' : n < 0 ? '−' : '') + Math.abs(n)
const SCREEN = { block: ['block', 'Blocked by screening'], caution: ['caution', 'Caution'] }
const pretty = id => id === 'alex-demo' ? 'Alex Demo' : id
const versus = d => Math.abs(d) < 0.05 ? 'the same as your calendar age' : `${one(Math.abs(d))} years ${d < 0 ? 'younger' : 'older'} than your calendar age`

function askHebe(ctx, text) {
  const opened = ctx.runAction('session.new')
  const fallback = () => {
    writeClipboardText(text)
    host.notify({ kind: 'info', message: 'Question copied. Paste it into a chat with Hebe.' })
  }
  if (!opened || !opened.ok) return fallback()
  ctx.setTimeout(() => {
    Promise.resolve(host.composer.setDraft('new', text)).then(ok => ok ? host.composer.focus('new') : fallback(), fallback)
  }, 250)
}

function Busy({ label }) { return h('div', { className: 'hb-busy', role: 'status' }, h('span', { className: 'hb-spin' }), label) }

function Ask({ ctx, title }) {
  return h('div', { className: 'hb-ask' },
    h('h3', null, title || 'Ask Hebe'),
    h('div', { className: 'hb-chips' }, ASK.map(q => h('button', { key: q, type: 'button', className: 'hb-chip', onClick: () => askHebe(ctx, q) }, q))),
    h('div', { className: 'hb-note' }, 'Opens a new chat with your question ready to send. Hebe answers with your saved results and the original Longevity Grok tools.'))
}

function Footer({ disclaimer }) {
  return h('div', { className: 'hb-foot' },
    h('div', null, 'Your blood results stay in this Hermes. Your chat model sees what appears in chat.'),
    h('div', null, disclaimer || 'Research and education only. Not a diagnosis or treatment recommendation.'),
    h('div', null, 'Built on PLSI by Insilico Medicine (MIT), the open toolbelt behind Longevity Grok. Not affiliated with Insilico Medicine or xAI.'))
}

// Hebe's mark: a blood drop holding Hebe's cup, the Greek goddess of youth.
function Mark({ size = 28 }) {
  return h('svg', { width: size, height: size, viewBox: '0 0 64 64', 'aria-hidden': true, className: 'hb-mark' },
    h('defs', null, h('linearGradient', { id: 'hebe-mark-g', x1: 0, y1: 0, x2: 1, y2: 1 },
      h('stop', { offset: 0, stopColor: '#19b39c' }), h('stop', { offset: 1, stopColor: '#0a6e63' }))),
    h('rect', { width: 64, height: 64, rx: 15, fill: 'url(#hebe-mark-g)' }),
    h('path', { d: 'M32 9c0 0-15 16.5-15 27a15 15 0 0 0 30 0C47 25.5 32 9 32 9z', fill: '#fff' }),
    h('path', { d: 'M23.5 34.5c3 4 5.5 5.5 8.5 5.5s5.5-1.5 8.5-5.5', fill: 'none', stroke: '#0d8576', strokeWidth: 3, strokeLinecap: 'round' }),
    h('path', { d: 'M32 40v6M27.5 46h9', stroke: '#0d8576', strokeWidth: 3, strokeLinecap: 'round' }))
}

// What a result looks like, before the user has one. Values are the fictional demo person's.
function Sample() {
  const bar = (label, value, pct, accent) => h('div', { className: 'hb-sbar' },
    h('div', { className: 'hb-srow' }, h('span', null, label), h('b', null, value)),
    h('div', { className: 'hb-strack' }, h('div', { style: { width: pct + '%', background: accent ? 'var(--hb-teal)' : 'var(--hb-faint)' } })))
  return h('div', { className: 'hb-card hb-sample', 'aria-label': 'Example result' },
    h('div', { className: 'hb-srow' }, h('span', { className: 'hb-steal' }, 'Blood PhenoAge'), h('span', { className: 'hb-pill' }, 'Example')),
    h('div', { className: 'hb-sbig' }, '37.2', h('span', null, ' years')),
    h('div', { className: 'hb-ssub' }, '8.1 years younger than calendar age'),
    bar('Blood PhenoAge', '37.2', 62, true), bar('Calendar age', '45.3', 76),
    h('div', { className: 'hb-srow hb-smove' }, h('span', null, 'Biggest mover since last draw'), h('b', null, 'Cell size variation −1.5 y')))
}

function Welcome({ ctx, start, importOwn, demo }) {
  const steps = [
    ['Add a blood panel', 'Nine routine markers from a standard lab test. Try the demo or bring your own values. You check every value before anything is saved.'],
    ['See your Blood PhenoAge', 'Your biological age from the same original formula Longevity Grok uses, your trend across draws and which values moved it.'],
    ['Plan with Hebe', 'Hebe drafts a plan with verified studies and safety screening. An independent second model challenges it. Only you can start it.']
  ]
  return h(React.Fragment, null,
    h('div', { className: 'hb-herogrid' }, h('div', { className: 'hb-hero' },
      h('div', { className: 'hb-eyebrow' }, 'Blood PhenoAge for Hermes'),
      h('h1', null, 'Know your biological age'),
      h('p', null, 'Hebe reads nine values from a routine blood test, calculates your Blood PhenoAge, shows what moved it and helps you plan what to try next. It runs inside your Hermes, with the open toolbelt behind Longevity Grok.'),
      h('div', { className: 'hb-row' },
        demo && h('button', { type: 'button', className: 'hb-btn hb-primary', onClick: start }, 'Try it with demo data'),
        h('button', { type: 'button', className: 'hb-btn', onClick: importOwn }, 'Use my blood results'))),
      h(Sample)),
    h('div', { className: 'hb-section' },
      h('h2', null, 'How Hebe works'),
      h('div', { className: 'hb-steps' }, steps.map(([t, p], i) => h('div', { key: t, className: 'hb-card hb-step' },
        h('span', { className: 'hb-num' }, i + 1), h('b', null, t), h('p', null, p))))),
    h('div', { className: 'hb-section' },
      h('h2', null, 'What you can ask Hebe'),
      h(Ask, { ctx, title: ' ' })))
}

function Review({ preview, busy, save, cancel }) {
  const conv = preview.conversions
  return h('div', { className: 'hb-card' },
    h('div', { className: 'hb-eyebrow' }, preview.demo ? 'Demo data, fictional person' : 'Your blood panel'),
    h('h2', { style: { fontSize: 26, letterSpacing: '-.02em', margin: '6px 0 4px' } }, 'Check your values before saving'),
    h('p', { style: { color: 'var(--hb-muted)', margin: '0 0 14px' } }, 'Hebe calculates only after you confirm. Saved values cannot be changed later.'),
    h('div', { className: 'hb-meta' },
      h('div', null, h('small', null, 'Person'), h('b', null, pretty(preview.person_id))),
      h('div', null, h('small', null, 'Born'), h('b', null, preview.birth_year)),
      h('div', null, h('small', null, 'Blood drawn'), h('b', null, day(preview.measured_at)))),
    h('table', { className: 'hb-table' }, h('tbody', null, preview.markers.map(m => h('tr', { key: m.marker },
      h('td', null, m.name),
      h('td', null, `${m.value} ${m.unit}`, m.converted && h('small', null, `= ${m.converted.value} ${m.converted.unit}`)))))),
    h('ul', { className: 'hb-checks' },
      h('li', null, `All ${preview.markers.length} markers present`),
      h('li', null, 'One person, one blood draw, final lab values'),
      h('li', null, conv ? `${conv} ${conv === 1 ? 'unit' : 'units'} converted with documented factors` : 'All units already match the formula')),
    h('div', { className: 'hb-row', style: { marginTop: 20 } },
      h('button', { type: 'button', className: 'hb-btn hb-primary', disabled: busy, onClick: save }, 'Save and calculate'),
      h('button', { type: 'button', className: 'hb-btn', disabled: busy, onClick: cancel }, 'Cancel')))
}

// The nine markers in lab-report order, with the units Hebe converts exactly (PLSI rules).
const MARKERS = [
  ['albumin', 'Albumin', [['g/L', 'g/L'], ['g/dL', 'g/dL']]],
  ['creatinine', 'Creatinine', [['umol/L', 'µmol/L'], ['mg/dL', 'mg/dL']]],
  ['glucose', 'Glucose (fasting)', [['mmol/L', 'mmol/L'], ['mg/dL', 'mg/dL']]],
  ['crp', 'C-reactive protein (CRP)', [['mg/L', 'mg/L'], ['mg/dL', 'mg/dL']]],
  ['lymphocyte_pct', 'Lymphocytes', [['%', '%']]],
  ['mcv', 'Mean cell volume (MCV)', [['fL', 'fL']]],
  ['rdw', 'Red cell distribution width (RDW)', [['%', '%']]],
  ['alp', 'Alkaline phosphatase (ALP)', [['U/L', 'U/L']]],
  ['wbc', 'White blood cells', [['10*9/L', '×10⁹/L'], ['10*3/uL', '×10³/µL']]]
]

function ManualForm({ busy, submit, back, ctx }) {
  const [vals, setVals] = React.useState({}), [units, setUnits] = React.useState({})
  const [date, setDate] = React.useState(''), [year, setYear] = React.useState(''), [person, setPerson] = React.useState('me')
  const num = v => String(v || '').trim().replace(',', '.')
  const ok = MARKERS.every(([k]) => /^\d+(\.\d+)?$/.test(num(vals[k])))
  const ready = ok && /^\d{4}-\d{2}-\d{2}$/.test(date) && /^\d{4}$/.test(year) && /^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$/.test(person)
  const csv = () => ['person_id,draw_id,collected_at,observation_id,status,marker,value,unit',
    ...MARKERS.map(([k, , us], i) => [person, 'draw-' + date, date, 'm' + i, 'final', k, num(vals[k]), units[k] || us[0][0]].join(','))].join('\n') + '\n'
  return h('div', { className: 'hb-grid2' },
    h('div', { className: 'hb-card' },
      h('h3', null, 'Values from your lab report'),
      h('div', { className: 'hb-mgrid' }, MARKERS.map(([k, label, us]) => h('label', { key: k, className: 'hb-mrow' },
        h('span', null, label),
        h('input', { inputMode: 'decimal', value: vals[k] || '', 'aria-label': label + ' value', onChange: e => setVals(v => ({ ...v, [k]: e.target.value })) }),
        us.length > 1
          ? h('select', { value: units[k] || us[0][0], 'aria-label': label + ' unit', onChange: e => setUnits(u => ({ ...u, [k]: e.target.value })) }, us.map(([v, l]) => h('option', { key: v, value: v }, l)))
          : h('em', null, us[0][1])))),
      h('div', { className: 'hb-meta', style: { marginTop: 16 } },
        h('label', { className: 'hb-field' }, 'Blood drawn on', h('input', { type: 'date', value: date, onChange: e => setDate(e.target.value) })),
        h('label', { className: 'hb-field' }, 'Birth year', h('input', { inputMode: 'numeric', value: year, placeholder: '1981', onChange: e => setYear(e.target.value.trim()) })),
        h('label', { className: 'hb-field' }, 'Name', h('input', { value: person, onChange: e => setPerson(e.target.value.trim()) }))),
      h('div', { className: 'hb-row' },
        h('button', { type: 'button', className: 'hb-btn hb-primary', disabled: busy || !ready, onClick: () => submit(csv(), Number(year), person) }, 'Check values'),
        h('button', { type: 'button', className: 'hb-btn', disabled: busy, onClick: back }, 'Back'))),
    h('div', { className: 'hb-card' },
      h('h3', null, 'Where to find these'),
      h('ul', { className: 'hb-checks' },
        h('li', null, 'A complete blood count, a comprehensive metabolic panel and a CRP test cover all nine'),
        h('li', null, 'Pick the unit printed on your lab report. Hebe converts it with documented factors'),
        h('li', null, 'Use one blood draw. Fasting glucose gives the most comparable result'),
        h('li', null, 'You see every value again before anything is saved')),
      h('p', { className: 'hb-note' }, 'Your values stay in this Hermes. Name can be a nickname; use the same one for later draws to see your trend.')))
}

function ImportForm({ ctx, busy, submit, back }) {
  const [csv, setCsv] = React.useState(''), [year, setYear] = React.useState(''), [person, setPerson] = React.useState('')
  const file = e => {
    const f = e.target.files && e.target.files[0]
    if (!f) return
    if (f.size > 65536) { host.notify({ kind: 'warning', message: 'That file is larger than 64 KB. Use the Hebe CSV template.' }); return }
    f.text().then(setCsv)
  }
  const template = () => ctx.rest('/template').then(t => { setCsv(t.csv); setPerson(p => p || 'me') }, () => {})
  const ready = csv.trim() && /^\d{4}$/.test(year) && /^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$/.test(person)
  return h('div', { className: 'hb-grid2' },
    h('div', { className: 'hb-card' },
      h('h3', null, 'Your blood results'),
      h('div', { className: 'hb-row', style: { marginBottom: 14 } },
        h('label', { className: 'hb-btn hb-filebtn' }, 'Choose CSV file', h('input', { type: 'file', accept: '.csv,text/csv', onChange: file })),
        h('button', { type: 'button', className: 'hb-btn', onClick: template }, 'Start from the template')),
      h('label', { className: 'hb-field' }, 'Or paste the CSV', h('textarea', { value: csv, onChange: e => setCsv(e.target.value), spellCheck: false, placeholder: 'person_id,draw_id,collected_at,observation_id,status,marker,value,unit' })),
      h('label', { className: 'hb-field' }, 'Birth year', h('input', { inputMode: 'numeric', value: year, onChange: e => setYear(e.target.value.trim()), placeholder: '1981' })),
      h('label', { className: 'hb-field' }, 'Name for this person', h('span', null, 'A short nickname. It must match person_id in the file.'),
        h('input', { value: person, onChange: e => setPerson(e.target.value.trim()), placeholder: 'me' })),
      h('div', { className: 'hb-row' },
        h('button', { type: 'button', className: 'hb-btn hb-primary', disabled: busy || !ready, onClick: () => submit(csv, Number(year), person) }, 'Check values'),
        h('button', { type: 'button', className: 'hb-btn', disabled: busy, onClick: back }, 'Back'))),
    h('div', { className: 'hb-card' },
      h('h3', null, 'What Hebe needs'),
      h('ul', { className: 'hb-checks' },
        h('li', null, 'Albumin, creatinine, glucose and C-reactive protein'),
        h('li', null, 'Lymphocytes in %, MCV, RDW, alkaline phosphatase and white blood cells'),
        h('li', null, 'Common lab units such as mg/dL or g/dL are converted for you'),
        h('li', null, 'One blood draw per file, final lab values')),
      h('p', { className: 'hb-note' }, 'Start from the template, replace the values with the ones from your lab report and set person_id to the name on the left. Hebe shows every conversion before saving.')))
}

// Light or dark, read from the app's own text color so the report matches the theme.
function appTheme(el) {
  const c = el ? getComputedStyle(el).color : ''
  const m = c.match(/\d+(\.\d+)?/g)
  if (!m || m.length < 3) return 'light'
  // rgb() uses 0 to 255, color(srgb ...) uses 0 to 1
  const scale = c.startsWith('color(') ? 1 : 255
  const [r, g, b] = m.slice(0, 3).map(n => Number(n) / scale)
  return 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.5 ? 'dark' : 'light'
}

function Report({ ctx, id }) {
  const [html, setHtml] = React.useState(null), [error, setError] = React.useState(''), [height, setHeight] = React.useState(900)
  const frame = React.useRef(null), box = React.useRef(null)
  React.useEffect(() => {
    let live = true; setHtml(null); setError('')
    ctx.rest('/report/' + id + '?embed=1&theme=' + appTheme(box.current)).then(r => live && setHtml(r.html), e => live && setError(message(e)))
    return () => { live = false }
  }, [id])
  React.useEffect(() => ctx.addEventListener(window, 'message', e => {
    const d = e.data
    if (frame.current && e.source === frame.current.contentWindow && d && d.type === 'hebe-height' && Number.isFinite(d.h))
      setHeight(Math.min(Math.max(d.h + 4, 400), 8000))
  }), [])
  return h('div', { ref: box },
    error ? h('div', { className: 'hb-banner hb-error' }, error)
      : html == null ? h(Busy, { label: 'Preparing your report…' })
      : h(SandboxedFrame, { ref: frame, title: 'Hebe report', className: 'hb-frame', style: { height },
          src: 'data:text/html;charset=utf-8,' + encodeURIComponent(html) }))
}

function Plans({ ctx, person, refreshKey }) {
  const [data, setData] = React.useState(null), [error, setError] = React.useState(''), [open, setOpen] = React.useState('')
  const [date, setDate] = React.useState(today()), [ack, setAck] = React.useState(false), [busy, setBusy] = React.useState(false), [done, setDone] = React.useState('')
  const load = () => { setError(''); return ctx.rest('/plans/' + encodeURIComponent(person)).then(setData, e => setError(message(e))) }
  React.useEffect(() => { setData(null); load() }, [person, refreshKey])
  const start = async d => {
    setBusy(true); setError('')
    try {
      const { confirmation } = await ctx.rest('/confirm', { method: 'POST', body: { action: 'start', id: d.id, start_on: date } })
      const out = await ctx.rest('/plans/start', { method: 'POST', body: { id: d.id, start_on: date, confirmation }, timeoutMs: 120000 })
      setDone(`Plan started on ${day(date)}. Hebe tracks its predictions until your next blood draw.`); setOpen(''); setAck(false)
      host.notify({ kind: 'success', message: 'Plan started' }); await load()
    } catch (e) { setError(message(e)) } finally { setBusy(false) }
  }
  if (error && !data) return h('div', { className: 'hb-banner hb-error' }, error)
  if (!data) return h(Busy, { label: 'Loading plans…' })
  const draft = 'What could I try to lower my Blood PhenoAge? Please draft a plan for ' + person + '.'
  if (!data.drafts.length && !data.plans.length) return h('div', { className: 'hb-card hb-empty' },
    h('h3', { style: { fontSize: 20 } }, 'No plans yet'),
    h('p', null, 'Hebe drafts a plan in chat: options backed by studies, safety screening and an independent challenger. You decide here whether to start it.'),
    h('button', { type: 'button', className: 'hb-btn hb-primary', onClick: () => askHebe(ctx, draft) }, 'Draft a plan with Hebe'))
  return h('div', { className: 'hb-plan' },
    done && h('div', { className: 'hb-banner hb-ok' }, done),
    error && h('div', { className: 'hb-banner hb-error' }, error),
    data.plans.length > 0 && h('div', { className: 'hb-card' },
      h('h3', null, 'Started plans'),
      h('ul', { className: 'hb-list' }, data.plans.map(p => h('li', { key: p.id },
        h('span', null, cap(plain(p.objective)) || p.id), h('small', null, [p.state, p.start && `since ${day(p.start)}`, p.review_at && `review ${day(p.review_at)}`].filter(Boolean).join(' · ')))))),
    data.drafts.filter(d => !d.started_as).map(d => {
      const blocked = d.actions.some(a => a.screening === 'block'), cautions = d.actions.filter(a => a.screening === 'caution')
      const canStart = d.challenged && !blocked && !d.violations.length
      return h('div', { key: d.id, className: 'hb-card hb-plan' },
        h('div', { className: 'hb-bar', style: { marginBottom: 0 } },
          h('h3', null, cap(plain(d.objective)) || 'Draft plan'),
          h('span', { className: 'hb-badge ' + (d.verdict === 'revise' ? 'revise' : d.challenged ? 'clear' : '') },
            !d.challenged ? 'Not challenged yet' : d.verdict === 'revise' ? 'Challenger: revise' : 'Challenger: no objections')),
        h('div', null, h('h3', { style: { fontSize: 14, color: 'var(--hb-muted)', marginBottom: 6 } }, 'What you would do'),
          h('ul', { className: 'hb-list' }, d.actions.map(a => h('li', { key: a.id },
            h('span', null, a.description, (a.dose || a.schedule) && h('small', null, ' · ' + [a.dose, a.schedule].filter(Boolean).join(', '))),
            SCREEN[a.screening] ? h('span', { className: 'hb-badge ' + SCREEN[a.screening][0] }, SCREEN[a.screening][1]) : h('small', null, 'Safety screened'))))),
        h('div', null, h('h3', { style: { fontSize: 14, color: 'var(--hb-muted)', marginBottom: 6 } }, 'What Hebe predicts'),
          h('ul', { className: 'hb-list' }, d.predictions.map((p, i) => h('li', { key: i },
            h('span', null, p.control ? 'If you change nothing' : 'With this plan'),
            h('small', null, `${plain(p.coordinate)} ${signed(p.expected)} years (range ${signed(p.low)} to ${signed(p.high)}) after ${p.horizon_days} days`)))),
          h('div', { className: 'hb-note' }, 'PhenoAge gap is your Blood PhenoAge minus your calendar age. Your next blood draw shows how close the prediction was.')),
        d.objections && h('details', null, h('summary', { style: { cursor: 'pointer', fontSize: 14 } }, 'What the challenger said'), h('div', { className: 'hb-objections' }, d.objections)),
        d.violations.length > 0 && h('div', { className: 'hb-banner hb-error' }, 'PLSI found problems. Ask Hebe to fix them: ' + d.violations.join('; ')),
        open === d.id
          ? h('div', { className: 'hb-confirm' },
              cautions.length > 0 && h('div', { className: 'hb-banner', style: { background: 'var(--hb-soft)' } },
                'Safety screening flagged: ' + cautions.map(a => a.description).join(', ') + '. Starting accepts these cautions.'),
              h('label', { className: 'hb-field', style: { maxWidth: 220 } }, 'Start on', h('input', { type: 'date', value: date, onChange: e => setDate(e.target.value) })),
              h('label', { className: 'hb-check' }, h('input', { type: 'checkbox', checked: ack, onChange: e => setAck(e.target.checked) }),
                'I read the plan, the screening and the challenger. I will talk to my clinician before changing medication, supplements or routines.'),
              h('div', { className: 'hb-row' },
                h('button', { type: 'button', className: 'hb-btn hb-primary', disabled: busy || !ack || !date, onClick: () => start(d) }, busy ? 'Starting…' : 'Start plan'),
                h('button', { type: 'button', className: 'hb-btn', disabled: busy, onClick: () => { setOpen(''); setAck(false) } }, 'Not yet')))
          : h('div', { className: 'hb-row' },
              h('button', { type: 'button', className: 'hb-btn hb-primary', disabled: !canStart, onClick: () => { setOpen(d.id); setAck(false); setDone('') } }, 'Review and start'),
              !d.challenged && h('button', { type: 'button', className: 'hb-link', onClick: () => askHebe(ctx, `Run the challenger on plan ${d.short_id} and answer its objections.`) }, 'Ask Hebe to run the challenger'),
              blocked && h('span', { className: 'hb-note' }, 'A screened action is blocked. Ask Hebe for a safer alternative.')))
    }),
    h('button', { type: 'button', className: 'hb-btn', style: { justifySelf: 'start' }, onClick: () => askHebe(ctx, draft) }, 'Draft another plan with Hebe'))
}

function App({ ctx }) {
  const [boot, setBoot] = React.useState(null), [error, setError] = React.useState(''), [busy, setBusy] = React.useState('')
  const [view, setView] = React.useState('main'), [tab, setTab] = React.useState('report'), [preview, setPreview] = React.useState(null)
  const [person, setPerson] = React.useState(''), [flash, setFlash] = React.useState(''), [planKey, setPlanKey] = React.useState(0), [importMode, setImportMode] = React.useState('manual')
  const load = () => ctx.rest('/bootstrap').then(b => {
    setBoot(b)
    setPerson(p => b.people.some(x => x.person_id === p) ? p : (b.people[b.people.length - 1] || {}).person_id || '')
  }, e => setError(message(e)))
  React.useEffect(() => { load() }, [])
  const run = async (label, fn) => { setBusy(label); setError(''); try { await fn() } catch (e) { setError(message(e)) } finally { setBusy('') } }
  const previewDemo = () => run('Preparing the demo blood panel…', async () => {
    setPreview(await ctx.rest('/preview', { method: 'POST', body: { source: 'demo' } })); setView('review'); setFlash('')
  })
  const previewCsv = (csv, birth_year, person_id) => run('Checking your values…', async () => {
    setPreview(await ctx.rest('/preview', { method: 'POST', body: { source: 'csv', csv, birth_year, person_id } })); setView('review'); setFlash('')
  })
  const save = () => run('Calculating your Blood PhenoAge…', async () => {
    const { confirmation } = await ctx.rest('/confirm', { method: 'POST', body: { action: 'save', id: preview.id } })
    const out = await ctx.rest('/save', { method: 'POST', body: { id: preview.id, confirmation } })
    const s = out.saved
    setBoot(b => ({ ...b, people: out.people, demo_available: b.demo_available })); setPerson(s.person_id)
    setFlash(`Saved. Blood PhenoAge for ${day(s.measured_at)}: ${one(s.pheno_age)} years, ${versus(s.delta)}.`)
    setPreview(null); setView('main'); setTab('report'); load()
  })
  const cancel = () => { if (preview) ctx.rest('/discard', { method: 'POST', body: { id: preview.id } }).catch(() => {}); setPreview(null); setView('main') }

  let body
  if (!boot) body = error ? h('div', { className: 'hb-banner hb-error' }, error) : h(Busy, { label: 'Opening Hebe…' })
  else if (busy) body = h(Busy, { label: busy })
  else if (view === 'review' && preview) body = h(Review, { preview, busy: !!busy, save, cancel })
  else if (view === 'import') body = h(React.Fragment, null,
    h('div', { className: 'hb-bar' }, h('div', { className: 'hb-person' }, 'Add your blood results', h('small', null, 'Nine values from one routine blood test')),
      h('div', { className: 'hb-tabs', role: 'tablist' }, [['manual', 'Type them in'], ['csv', 'Upload a CSV']].map(([k, l]) =>
        h('button', { key: k, type: 'button', role: 'tab', className: 'hb-tab', 'aria-selected': importMode === k, onClick: () => setImportMode(k) }, l)))),
    importMode === 'manual' ? h(ManualForm, { ctx, busy: !!busy, submit: previewCsv, back: () => setView('main') })
      : h(ImportForm, { ctx, busy: !!busy, submit: previewCsv, back: () => setView('main') }))
  else if (!boot.people.length) body = h(Welcome, { ctx, start: previewDemo, importOwn: () => setView('import'), demo: boot.demo_available })
  else {
    const p = boot.people.find(x => x.person_id === person) || boot.people[0], latest = p.latest
    body = h(React.Fragment, null,
      h('div', { className: 'hb-bar' },
        h('div', { className: 'hb-person' }, pretty(p.person_id),
          h('small', null, `${p.draws.length} blood ${p.draws.length === 1 ? 'draw' : 'draws'} · latest ${day(latest.measured_at)}${p.demo ? ' · fictional demo person' : ''}`)),
        h('div', { className: 'hb-tabs', role: 'tablist' }, [['report', 'Your result'], ['plans', 'Plans'], ['add', 'Add blood draw']].map(([k, l]) =>
          h('button', { key: k, type: 'button', role: 'tab', className: 'hb-tab', 'aria-selected': tab === k, onClick: () => setTab(k) }, l)))),
      boot.people.length > 1 && h('div', { className: 'hb-row', style: { marginBottom: 14 } }, boot.people.map(x =>
        h('button', { key: x.person_id, type: 'button', className: 'hb-chip', style: { fontWeight: x.person_id === p.person_id ? 600 : 400 }, onClick: () => setPerson(x.person_id) }, pretty(x.person_id)))),
      tab === 'report' && h(React.Fragment, null, h(Report, { ctx, id: latest.id }), h(Ask, { ctx })),
      tab === 'plans' && h(Plans, { ctx, person: p.person_id, refreshKey: planKey }),
      tab === 'add' && h('div', { className: 'hb-options' },
        boot.demo_available && p.demo && h('button', { type: 'button', className: 'hb-card hb-option', onClick: previewDemo },
          h('b', null, 'Add the earlier demo draw'), h('span', null, 'A second fictional draw from October 2025 in typical lab units. Your result then shows a trend and what moved it.')),
        h('button', { type: 'button', className: 'hb-card hb-option', onClick: () => setView('import') },
          h('b', null, 'Add my blood results'), h('span', null, 'Type in nine values from one lab report, or upload a CSV. You check every value before saving.'))))
  }
  return h('div', { className: 'hebe' }, h('style', null, CSS),
    h('div', { className: 'hb-wrap' },
      h('div', { className: 'hb-top' },
        h('div', { className: 'hb-brand' }, h(Mark, { size: 30 }),
          h('div', null, 'Hebe', h('small', null, 'Personal Longevity Intelligence'))),
        h('span', { className: 'hb-pill' }, 'Research prototype')),
      flash && view === 'main' && h('div', { className: 'hb-banner hb-ok', role: 'status' }, flash),
      error && boot && h('div', { className: 'hb-banner hb-error', role: 'alert' }, error),
      body,
      h(Footer, { disclaimer: boot && boot.disclaimer })))
}

// Inline card the agent can show in chat with a paragraph `::hebe{view="result"}`.
function ChatCard({ ctx, view }) {
  const [boot, setBoot] = React.useState(null)
  React.useEffect(() => { let live = true; ctx.rest('/bootstrap').then(b => live && setBoot(b), () => live && setBoot({ people: [] })); return () => { live = false } }, [])
  const p = boot && boot.people[boot.people.length - 1]
  const open = () => host.navigate(PATH)
  return h('div', { className: 'hebe', style: { height: 'auto', overflow: 'visible' } }, h('style', null, CSS),
    h('div', { className: 'hb-dcard' }, h(Mark, { size: 36 }),
      p ? h('div', null, h('div', { className: 'hb-big' }, one(p.latest.pheno_age), h('span', { style: { fontSize: 15, fontWeight: 500 } }, ' years')),
            h('div', { className: 'hb-note', style: { marginTop: 0 } }, `Blood PhenoAge, ${pretty(p.person_id)}, ${day(p.latest.measured_at)}`))
        : h('div', null, h('b', null, 'Hebe'), h('div', { className: 'hb-note', style: { marginTop: 0 } }, boot ? 'No blood results yet' : 'Loading…')),
      h('button', { type: 'button', className: 'hb-btn hb-primary', style: { marginLeft: 'auto' }, onClick: open },
        view === 'plans' ? 'Open plans' : p ? 'Open report' : 'Open Hebe')))
}

export default {
  id: 'hebe-longevity',
  name: 'Hebe',
  register(ctx) {
    function Page() {
      const profile = useValue(host.state.profile)
      return h(App, { key: String(profile), ctx })
    }
    ctx.registerMany([
      { id: 'page', area: ROUTES_AREA, data: { path: PATH }, render: () => h(Page) },
      { id: 'nav', area: SIDEBAR_NAV_AREA, data: { path: PATH, label: 'Hebe', codicon: 'pulse' } },
      { id: 'open', area: PALETTE_AREA, data: { id: 'hebe-open', label: 'Hebe: Open Personal Longevity Intelligence', run: () => host.navigate(PATH) } },
      { id: 'card', area: TRANSCRIPT_DIRECTIVE_AREA, data: { name: 'hebe', render: ({ attrs }) => h(ChatCard, { ctx, view: attrs && attrs.view === 'plans' ? 'plans' : 'result' }) } }
    ])
  }
}
