"""Hebe Longevity native Hermes plugin."""
def register(ctx):
    from .hebe.commands import prepare, handle
    from plugins.plugin_storage import plugin_data_dir
    def home():return plugin_data_dir('hebe-longevity')
    def command(raw_args):return handle(ctx,home(),raw_args)
    def tool(args,**kwargs):return prepare(home(),args)
    ctx.register_command('hebe',command,description='Try Hebe Longevity with fictional labs; review and calculate',args_hint='demo | import | status | report')
    ctx.register_tool(name='hebe_preview',toolset='hebe-longevity',description='Preview fictional demo labs or inspect saved result identifiers; never confirms or saves measurements.',
        schema={'name':'hebe_preview','description':'Prepare the fictional Hebe demo or list saved result identifiers. To approve and calculate, the user opens /hebe and confirms the dialog. Research only.',
                'parameters':{'type':'object','properties':{'action':{'type':'string','enum':['demo','status']}},'required':['action'],'additionalProperties':False}},
        handler=lambda args,**kwargs:tool(args) if isinstance(args,dict) and args.get('action') in ('demo','status') else '{"ok":false,"error":"Unsupported tool action"}')
    ctx.register_system_prompt_section('hebe-help','Hebe Longevity computes blood PhenoAge for research and education. To try fictional labs use hebe_preview, then ask the user to open /hebe for the confirmation dialog. Never use shell/file tools to approve or alter Hebe data. Real-data import currently requires the strict Hebe CSV template. FHIR, PDF, wearables, treatment plans and full network isolation are unsupported. Cloud models may receive tool output.',max_chars=1000)
