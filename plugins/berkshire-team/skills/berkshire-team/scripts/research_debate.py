"""Check that disputes, cross-examination and controlled model impacts are traceable."""
import ast
import hashlib
from decimal import Decimal

from delivery_dependencies import read_file
from delivery_model import pointer
from research_progress import DEBATE_BASIS, DEBATE_OUTPUTS, OPENINGS


def require_text(record, fields):
    for name in fields:
        if not isinstance(record.get(name), str) or not record[name].strip():
            raise ValueError(f'debate requires nonempty {name}')


def check_debate(root, state, challenge, manifest, model_checks):
    basis, _, _ = read_file(root, DEBATE_BASIS)
    if hashlib.sha256(basis).hexdigest() != state['progress'].get('debate_basis_sha256'):
        raise ValueError('debate basis changed after openings')
    for role, opening in OPENINGS.items():
        artifacts = {item['path']: item['sha256'] for item in state['roles'][role]['artifacts']}
        if not artifacts.get(opening) or artifacts[opening] != state['roles'][role].get('opening_sha256'):
            raise ValueError(f'unchanged {opening} must be bound to its original checkpoint')

    disputes = [item for item in challenge['disagreements'] if item.get('material') is True]
    if len(disputes) < 2:
        raise ValueError('debate requires at least two material disputes')
    for item in disputes:
        require_text(item, ('id', 'metric', 'bull', 'bear', 'test', 'verdict', 'driver',
                            'base_check', 'counter_check'))
        if (state['progress'].get('debate_protocol', 0) >= 3
                and item.get('impact_unit') not in {'cash', 'per_share'}):
            raise ValueError('debate impact must be stated as cash or per-share value')
    issue_ids = {item['id'] for item in disputes}
    if len(issue_ids) != len(disputes):
        raise ValueError('debate dispute IDs must be distinct')

    questions = set()
    roles = {'bull': 'bull_case', 'bear': 'bear_case'}
    for question in challenge['questions']:
        require_text(question, ('dispute_id', 'from', 'to', 'concession'))
        sender, receiver = question['from'], question['to']
        if sender not in roles or receiver not in roles or sender == receiver:
            raise ValueError('debate question must be exchanged between bull and bear')
        required = {OPENINGS[roles[sender]], DEBATE_OUTPUTS[roles[receiver]]}
        if not required <= set(question['evidence']):
            raise ValueError('debate question must cite the challenger opening and respondent reply')
        questions.add((question['dispute_id'], sender))
    if questions != {(issue, side) for issue in issue_ids for side in roles}:
        raise ValueError('each material dispute needs questions and replies in both directions')

    definitions = {item['name']: item for item in manifest['checks']}
    checked = {item['name']: Decimal(item['recomputed']) for item in model_checks}
    if len(definitions) != len(manifest['checks']):
        raise ValueError('model check names must be unique for debate')
    pairs, results = set(), []
    for item in disputes:
        if item['bull'].strip() == item['bear'].strip() or item['verdict'] not in {'update', 'retain', 'unresolved'}:
            raise ValueError('debate requires distinct claims and an explicit ruling')
        names = (item['base_check'], item['counter_check'])
        if not set(names) <= checked.keys() or len(set(names)) != 2 or frozenset(names) in pairs:
            raise ValueError('each dispute needs its own two distinct recomputed checks')
        pairs.add(frozenset(names))
        before, after = (definitions[name] for name in names)
        a, b = before['variables'], after['variables']
        driver = item['driver']
        if (before['expression'] != after['expression'] or a.keys() != b.keys()
                or driver not in a or before['expected'] == after['expected']):
            raise ValueError('controlled comparison must use the same expression and distinct outputs')
        used_names = {node.id for node in ast.walk(ast.parse(before['expression'], mode='eval'))
                      if isinstance(node, ast.Name)}
        if driver not in used_names:
            raise ValueError('controlled comparison must use its driver in the expression')
        changed = {name for name in a if pointer(root, a[name]) != pointer(root, b[name])}
        if changed != {driver}:
            raise ValueError('controlled comparison must change only the stated driver')
        results.append(dict(id=item['id'], metric=item['metric'], verdict=item['verdict'], driver=driver,
                            impact_unit=item.get('impact_unit'),
                            base_input=str(pointer(root, a[driver])), counter_input=str(pointer(root, b[driver])),
                            base_output=str(checked[names[0]]), counter_output=str(checked[names[1]]),
                            delta=str(checked[names[1]] - checked[names[0]])))
    return results
