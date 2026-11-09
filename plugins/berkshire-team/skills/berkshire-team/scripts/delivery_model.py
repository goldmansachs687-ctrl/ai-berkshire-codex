"""Recompute declared arithmetic without executing untrusted model programs."""
import ast
from decimal import Decimal, localcontext
from audit_core import number
from delivery_dependencies import read_file, strings


def pointer(root, ref):
    _, _, value = read_file(root, ref['file'])
    path = ref['pointer']
    if not isinstance(path, str) or not path.startswith('/'):
        raise ValueError('input/output pointer must be a nonempty JSON pointer')
    try:
        for token in path[1:].split('/'):
            token = token.replace('~1', '/').replace('~0', '~')
            value = value[int(token)] if isinstance(value, list) else value[token]
        return number(value)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ValueError('missing or invalid numeric input/output: ' + ref['file'] + '#' + path) from exc


def calculate(expression, variables):
    if not isinstance(expression, str) or len(expression) > 2000:
        raise ValueError('invalid or oversized calculation expression')
    tree = ast.parse(expression, mode='eval')
    used = set()
    def visit(node):
        if isinstance(node, ast.Name):
            used.add(node.id)
            return variables[node.id]
        if isinstance(node, ast.Constant):
            return number(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            return visit(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1)
        if isinstance(node, ast.BinOp):
            a, b = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add): return a + b
            if isinstance(node.op, ast.Sub): return a - b
            if isinstance(node.op, ast.Mult): return a * b
            if isinstance(node.op, ast.Div): return a / b
            if isinstance(node.op, ast.Pow) and b == b.to_integral_value() and abs(b) <= 100:
                return a ** int(b)
        raise ValueError('only numeric + - * / and bounded integer powers are supported')
    with localcontext() as context:
        context.prec = 40
        result = visit(tree.body)
    return number(result), used


def check_model(root, manifest, ledger, passed_ids):
    for key in ('models', 'inputs', 'outputs'):
        strings(manifest.get(key), key)
    if not isinstance(manifest.get('reproduce'), str) or not manifest['reproduce'].strip():
        raise ValueError('valuation manifest needs reproduction instructions')
    keys = manifest.get('key_inputs')
    checks = manifest.get('checks')
    if not isinstance(keys, list) or not keys or not isinstance(checks, list) or not checks:
        raise ValueError('valuation needs key_inputs and recomputation checks')
    claims = {c['id']: c for c in ledger['claims']}
    required, used_inputs, used_outputs = set(), set(), set()
    for item in keys:
        if item['file'] not in manifest['inputs']:
            raise ValueError('key input not declared in inputs: ' + item['file'])
        value = pointer(root, item)
        if item.get('claim_id') not in claims:
            raise ValueError('key input ' + item['file'] + '#' + item['pointer'] + ' references missing evidence claim: ' + str(item.get('claim_id')))
        claim = claims[item['claim_id']]
        if claim.get('kind', 'fact') == 'assumption':
            if not item.get('rationale') or not claim.get('rationale'):
                raise ValueError('assumed model input needs rationale')
            if value != number(claim['reported_value']):
                raise ValueError('model assumption differs from ledger: ' + claim['id'])
        elif claim['id'] not in passed_ids or claim['id'] not in ledger['required_claims'] or value != number(claim['reported_value']):
            raise ValueError('model input lacks matching audited fact: ' + claim['id'])
        required.add((item['file'], item['pointer']))
    results = []
    for check in checks:
        if not isinstance(check.get('name'), str) or not check['name'].strip():
            raise ValueError('model check needs a name')
        variables = check['variables']
        if not isinstance(variables, dict) or not variables:
            raise ValueError('model check needs input references')
        values = {}
        for name, ref in variables.items():
            if ref['file'] not in manifest['inputs']:
                raise ValueError('calculation variable not an input: ' + ref['file'])
            values[name] = pointer(root, ref)
        result, used = calculate(check['expression'], values)
        for name in used:
            ref = variables[name]
            used_inputs.add((ref['file'], ref['pointer']))
        expected = check['expected']
        if expected['file'] not in manifest['outputs']:
            raise ValueError('expected result not declared in outputs')
        used_outputs.add(expected['file'])
        actual = pointer(root, expected)
        tolerance = number(check.get('absolute_tolerance', '0.000001'))
        if tolerance < 0 or tolerance > Decimal('0.000001'):
            raise ValueError('invalid arithmetic tolerance')
        if abs(result - actual) > tolerance:
            raise ValueError('recomputation mismatch: ' + check['name'])
        results.append({'name': check['name'], 'recomputed': str(result), 'recorded': str(actual)})
    if required != used_inputs:
        raise ValueError('every used input must be a declared key input and every key input must be recomputed')
    if used_outputs != set(manifest['outputs']):
        raise ValueError('every declared output needs a recomputation check')
    return results
