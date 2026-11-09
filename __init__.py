"""Hebe Longevity native Hermes plugin."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLANNING = ('hebe_state', 'hebe_evidence', 'hebe_calc', 'hebe_plan_check', 'hebe_challenge', 'hebe_plans')


def register(ctx):
    from .hebe.commands import prepare, handle
    from .hebe.agent_tools import SCHEMAS, run_tool
    from plugins.plugin_storage import plugin_data_dir
    def home():return plugin_data_dir('hebe-longevity')
    def command(raw_args):return handle(ctx,home(),raw_args)
    def tool(args,**kwargs):return prepare(home(),args)
    ctx.register_command('hebe',command,description='Hebe Longevity: Longevity Intelligence for Hermes',args_hint='help | demo | import | status | report | plan')
    ctx.register_tool(name='hebe_preview',toolset='hebe-longevity',description='Preview fictional demo labs or inspect saved result identifiers; never confirms or saves measurements.',
        schema={'name':'hebe_preview','description':'Prepare the fictional Hebe demo or list saved result identifiers. To approve and calculate, the user opens /hebe and confirms the dialog. Research only.',
                'parameters':{'type':'object','properties':{'action':{'type':'string','enum':['demo','status']}},'required':['action'],'additionalProperties':False}},
        handler=lambda args,**kwargs:tool(args) if isinstance(args,dict) and args.get('action') in ('demo','status') else '{"ok":false,"error":"Unsupported tool action"}')
    def challenger_llm(messages):
        # PLSI Challenger as its own host-owned completion: fresh context, own model via auxiliary.hebe_challenger
        return ctx.llm.complete(messages, task='hebe_challenger', temperature=0.2, purpose='Hebe plan challenger').text
    for name in PLANNING:
        description, parameters = SCHEMAS[name]
        def handler(args, _name=name, **kwargs):
            return run_tool(_name, home(), args, llm=challenger_llm if _name == 'hebe_challenge' else None)
        ctx.register_tool(name=name, toolset='hebe-longevity', description=description,
                          schema={'name': name, 'description': description, 'parameters': parameters}, handler=handler)
    ctx.register_auxiliary_task('hebe_challenger', display_name='Hebe plan challenger',
                                description='PLSI Challenger for Hebe plans: a separate model call that sees only the plan, state and screening')
    vendor = ROOT / 'vendor' / 'plsi'
    ctx.register_skill('plan', ROOT / 'skills' / 'plan' / 'SKILL.md', description='Draft a PLSI plan to lower Blood PhenoAge with screening, an independent challenger and a user-only start')
    ctx.register_skill('nostradamus-plan', vendor / 'skills' / 'nostradamus' / 'plan' / 'SKILL.md', description='Original PLSI Nostradamus planning skill (unchanged)')
    ctx.register_skill('challenge', vendor / 'skills' / 'challenger' / 'challenge' / 'SKILL.md', description='Original PLSI Challenger skill (unchanged)')
    ctx.register_skill('persona', vendor / 'persona.md', description='Original PLSI persona and safety norms (unchanged)')
    ctx.register_system_prompt_section('hebe-help','Hebe Longevity (Longevity Intelligence for Hermes) runs Longevity Grok\'s open PLSI toolbelt inside Hermes for research and education. If asked what Hebe can do, point to /hebe help. Blood PhenoAge: use hebe_preview for the fictional demo, then ask the user to open /hebe to confirm. Plans: load skill hebe-longevity:plan and use the hebe_* tools; only the user can start a plan with /hebe plan start. Never use shell or file tools to approve, alter or start Hebe data. No outside reference ranges. FHIR, PDF and wearables are unsupported. Cloud models may receive tool output.',max_chars=1000)
