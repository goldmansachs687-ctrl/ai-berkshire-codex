"""Deterministic synthetic examples. Never label these as real research/review."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT/'plugins/berkshire-team/skills/berkshire-team/scripts'
sys.path.insert(0, str(SCRIPTS))
from research_run import ROLES, initialize, checkpoint


def save(root, name, value):
    (root/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def load(root, name):
    return json.loads((root/name).read_text(encoding='utf-8'))


def review(root):
    checkpoint(root, 'independent_review', 'complete', ['review.md'],
               'Synthetic reviewer checked supplied model, evidence, scope and counterevidence.', 'fixture-reviewer')


def example(parent, mode='complete'):
    root = initialize(parent, mode, 'SYNTHETIC', '2026-01-01')
    (root/'source.md').write_text('Synthetic source: FY2025 revenue USD million 100. Not investment data.\n')
    (root/'report.md').write_text('Synthetic research. Revenue 100; illustrative value 1000. [Source](source.md)\n')
    (root/'review.md').write_text('Synthetic independent review: arithmetic recomputed, sources and counterevidence inspected.\n')
    dims = dict(metric='revenue', unit='million', currency='USD', period='FY2025', basis='GAAP')
    observation = dict(dims, value=100, source='source.md', locator='line 1', accessed_at='2026-01-01', origin_group='synthetic')
    fact = dict(dims, id='revenue', reported_value=100, observations=[observation])
    save(root, 'evidence.json', dict(required_claims=['revenue'], claims=[fact,
         dict(id='multiple', kind='assumption', reported_value=10, rationale='Synthetic scenario assumption, not a historical fact.')]))
    for role in ROLES[:-1]:
        name = role+'.md'
        (root/name).write_text('Synthetic '+role+' findings and counterarguments. [Source](source.md)\n')
        checkpoint(root, role, 'complete', [name], 'Synthetic role work recorded', 'fixture-'+role)
    save(root, 'challenges.json', dict(questions=[dict(question='Is the input comparable?', response='FY2025 USD million GAAP checked.', evidence=['source.md'])],
         disagreements=[], no_material_disagreements_reason='Synthetic normalized source matches; no material divergence found.'))
    (root/'model.py').write_text('import json\nfrom pathlib import Path\np = Path(__file__).parent\nx = json.loads((p / "inputs.json").read_text())\nprint(x["revenue"] * x["multiple"])\n')
    save(root, 'inputs.json', dict(revenue=100, multiple=10))
    save(root, 'valuation-result.json', dict(value=1000))
    save(root, 'valuation.json', dict(models=['model.py'], inputs=['inputs.json'], outputs=['valuation-result.json'],
        reproduce='python3 model.py; compare stdout to valuation-result.json /value',
        key_inputs=[dict(file='inputs.json', pointer='/revenue', claim_id='revenue'),
                    dict(file='inputs.json', pointer='/multiple', claim_id='multiple', rationale='Synthetic illustrative multiple')],
        checks=[dict(name='illustrative value', expression='revenue * multiple', variables={
                    'revenue':dict(file='inputs.json', pointer='/revenue'), 'multiple':dict(file='inputs.json', pointer='/multiple')},
                    expected=dict(file='valuation-result.json', pointer='/value'))]))
    save(root, 'delivery.json', dict(schema_version=1, research_type='full', applicable_roles=list(ROLES[:-1]),
         participants=['fixture-'+r for r in ROLES[:-1]], minimum_claims=['revenue'], conclusion_claims=['revenue'],
         challenges='challenges.json', valuation=dict(required=True, manifest='valuation.json'), limitations=[], dependencies=[]))
    save(root, 'review.json', dict(reviewer_id='fixture-reviewer', decision='COMPLETE', acknowledged_limitations=[],
         checks={k:'Synthetic review of '+k+' and its boundaries.' for k in ('workflow','evidence','model','scope','counterevidence')}))
    if mode == 'limited':
        ledger=load(root,'evidence.json')
        ledger['required_claims'].append('history')
        ledger['claims'].append(dict(dims, id='history', reported_value=None, observations=[]))
        save(root,'evidence.json',ledger)
        contract=load(root,'delivery.json')
        gap=dict(claim_id='history', reason='objective_unavailable', attempted_sources=['Synthetic archived filing search'],
                 impact='Long history comparison unavailable.', prohibited_conclusions='No conclusion about ten-year stability.', disclosure='Historical data objectively unavailable in this fixture.')
        contract['limitations']=[gap];save(root,'delivery.json',contract)
        with (root/'report.md').open('a') as f:f.write('\n'.join(gap[k] for k in ('impact','prohibited_conclusions','disclosure'))+'\n')
        r=load(root,'review.json');r.update(decision='LIMITED',acknowledged_limitations=['history']);save(root,'review.json',r)
    if mode == 'qualitative':
        contract=load(root,'delivery.json');contract.update(research_type='qualitative_brief',scope_reason='Business overview only; no valuation conclusion.',
            applicable_roles=['business_analyst'],valuation=dict(required=False,reason='No quantitative valuation conclusions.'))
        save(root,'delivery.json',contract)
        (root/'report.md').write_text('Synthetic qualitative overview. Revenue 100. [Source](source.md)\n')
        for name in ('model.py','inputs.json','valuation-result.json','valuation.json'): (root/name).unlink()
    if mode == 'blocked':
        state=load(root,'run.json')
        for role in ROLES[:-1]:state['roles'][role].update(status='pending',artifacts=[])
        save(root,'run.json',state)
        save(root,'evidence.json',dict(required_claims=['revenue'],claims=[]))
    review(root)
    return root


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    print(json.dumps({kind:str(example(args.output,kind)) for kind in ('complete','limited','blocked','qualitative')},indent=2))
