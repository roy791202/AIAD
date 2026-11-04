"""Closed document-packet validator; no arbitrary command execution or semantic proof."""
import argparse, importlib.util, json, pathlib, shlex, sys
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent
BASE=HERE.parent/'remaining-action-correction-20261103'
spec=importlib.util.spec_from_file_location('prior_document_checker',BASE/'check.py')
prior=importlib.util.module_from_spec(spec); spec.loader.exec_module(prior)
read=prior.read
PACKETS=read(BASE/'task-packets.json')
APPROVED={p['primary_module']:p for p in PACKETS}
AUTHORITY='Original planning scope only; no implementation authorization or decision adoption.'
STATE='BOUNDED_PLANNING_PACKET_ONLY'
CHECKER='docs/requirements-confirmation/phase1-spec/tasks/M01/planning/remaining-action-correction-20261103/check.py'

def validate(p):
    if not isinstance(p,dict): raise ValueError('packet must be object')
    m=p.get('primary_module')
    if not isinstance(m,str) or m not in APPROVED: raise ValueError('unknown module')
    if p.get('authority')!=AUTHORITY or p.get('state')!=STATE: raise ValueError('document-only authority/state required')
    # These are the two already approved invocation shapes, with packet/module binding.
    expected=[['python',CHECKER,flag,m] for flag in ('--packet','--deliverables')]
    commands=p.get('commands')
    if not isinstance(commands,list) or len(commands)!=2: raise ValueError('two document checks required')
    parsed=[]
    for command in commands:
        if not isinstance(command,str) or any(c in command for c in '\r\n\x00;&|`$<>'):
            raise ValueError('unsafe or malformed command')
        try: tokens=shlex.split(command,posix=True)
        except ValueError as error: raise ValueError('malformed command') from error
        parsed.append(tokens)
    if parsed!=expected: raise ValueError('invocation not in approved module-bound whitelist')
    if p.get('allowed_files')!=APPROVED[m]['allowed_files']: raise ValueError('exact approved output paths required')
    prior.validate(p)

def io_validate(row): prior.io_validate(row)
def deliverables(p):
    validate(p)
    prior.deliverables(p)

def check_cards(cards):
    io_validate(cards['cards'][0])
    assert len(cards['cards'])==31
    original=read(HERE.parent/'remaining-action-dispatch-20261103/31-card-actions.json')
    import copy
    for i,(before,after) in enumerate(zip(original['cards'],cards['cards'])):
        expected=copy.deepcopy(before)
        if i==0: expected['provider']=after['provider']
        assert expected==after, 'unexpected per-card drift'

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--packet',choices=['M02','M03'])
    group.add_argument('--deliverables',choices=['M02','M03'])
    args=parser.parse_args()
    for packet in PACKETS:
        if not args.packet and not args.deliverables or packet['primary_module']==(args.packet or args.deliverables):
            validate(packet)
            if args.deliverables: deliverables(packet)
    check_cards(read(BASE/'31-card-actions.json'))
    print(json.dumps({'status':'PASS','layer':'AUTHOR_CLOSED_DOCUMENT_PACKET_CHECK_ONLY','product':'NOT RUN','valid_red':'N/A'}))
