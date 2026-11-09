"""Content binding shared by explicit review checkpoints and read-only delivery checks."""
import ast
import csv
import hashlib
import io
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

RESERVED = {'run.json', 'delivery-result.json'}


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key: ' + key)
            result[key] = value
        return result
    def constant(value):
        raise ValueError('non-finite JSON number: ' + value)
    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def read_file(root, name):
    if not isinstance(name, str) or not name.strip():
        raise ValueError('file path must be a nonempty string')
    path = root / name
    if Path(name).is_absolute() or '..' in Path(name).parts:
        raise ValueError('path must stay inside run: ' + name)
    if any(p.is_symlink() for p in [path, *path.parents] if p != root.parent):
        raise ValueError('symlink dependency forbidden: ' + name)
    if not path.resolve().is_relative_to(root) or not path.is_file():
        raise ValueError('missing or outside run: ' + name)
    data = path.read_bytes()
    if not data.strip():
        raise ValueError('empty file: ' + name)
    suffix = path.suffix.lower()
    if suffix not in {'.json', '.md', '.txt', '.py', '.csv'}:
        raise ValueError('unsupported dependency format (export a reviewable text artifact): ' + name)
    try:
        text = data.decode('utf-8')
    except UnicodeError as exc:
        raise ValueError('unreadable UTF-8 file: ' + name) from exc
    parsed = None
    if suffix == '.json':
        try:
            parsed = strict_json(text)
        except ValueError as exc:
            raise ValueError('invalid JSON ' + name + ': ' + str(exc)) from exc
        if not isinstance(parsed, (dict, list)) or not parsed:
            raise ValueError('empty or non-container JSON: ' + name)
    elif suffix == '.py':
        ast.parse(text, filename=name)
    elif suffix == '.csv':
        rows = list(csv.reader(io.StringIO(text), strict=True))
        if len(rows) < 2 or not rows[0] or any(len(r) != len(rows[0]) for r in rows):
            raise ValueError('invalid CSV table: ' + name)
    return data, text, parsed


def strings(value, label, nonempty=True):
    if not isinstance(value, list) or (nonempty and not value) or any(
            not isinstance(x, str) or not x.strip() or x != x.strip() for x in value) or len(set(value)) != len(value):
        raise ValueError(label + ' must be a list of unique nonempty strings')
    return value


def json_refs(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ('file', 'local_file'):
                if not isinstance(item, str):
                    raise ValueError(key + ' must be a file path')
                yield item
            elif key == 'dependencies' or (key == 'evidence' and isinstance(item, list) and all(isinstance(x, str) for x in item)):
                yield from strings(item, key, False)
            else:
                yield from json_refs(item)
    elif isinstance(value, list):
        for item in value:
            yield from json_refs(item)


def binding(root, state):
    """Derive required closure; no timestamps, acceptance outputs or review state writes."""
    root = Path(root).resolve()
    _, _, contract = read_file(root, 'delivery.json')
    if not isinstance(contract, dict):
        raise ValueError('delivery.json must be an object')
    names = {'delivery.json', 'report.md', 'evidence.json', 'review.md', 'review.json'}
    names.add(contract['challenges'])
    names.update(strings(contract.get('dependencies', []), 'dependencies', False))
    for role, record in state['roles'].items():
        if role != 'independent_review':
            names.update(a['path'] for a in record.get('artifacts', []))
    valuation = contract['valuation']
    if not isinstance(valuation, dict) or type(valuation.get('required')) is not bool:
        raise ValueError('valuation.required must be explicitly boolean')
    if valuation['required']:
        name = valuation['manifest']
        names.add(name)
        _, _, manifest = read_file(root, name)
        for key in ('models', 'inputs', 'outputs'):
            names.update(strings(manifest.get(key), 'valuation.' + key))
    result = {}
    while names:
        name = names.pop()
        name = Path(name).as_posix()
        if name in RESERVED:
            raise ValueError('mutable state/output cannot be a dependency: ' + name)
        if name in result:
            continue
        data, text, parsed = read_file(root, name)
        result[name] = hashlib.sha256(data).hexdigest()
        names.update(json_refs(parsed))
        if Path(name).suffix.lower() == '.md':
            # Inline Markdown links; reference-style definitions are also dependencies.
            links = re.findall(r'\]\(([^)]+)\)', text)
            links += re.findall(r'^\s*\[[^\]]+\]:\s*(\S+)', text, re.M)
            for link in links:
                link = link.strip().strip('<>')
                parts = urlsplit(link)
                if parts.scheme in ('http', 'https'):
                    if not parts.netloc:
                        raise ValueError('invalid remote link: ' + link)
                elif parts.scheme:
                    raise ValueError('unsupported link scheme: ' + link)
                elif parts.path:
                    names.add(str(Path(name).parent / unquote(parts.path)))
        if name == 'evidence.json':
            for claim in parsed['claims']:
                for observation in claim.get('observations', []):
                    source = observation.get('source', '')
                    if not isinstance(source, str):
                        raise ValueError('evidence source must be a string')
                    source_url = urlsplit(source)
                    if source_url.scheme in ('http', 'https') and (not source_url.netloc or any(c.isspace() for c in source)):
                        raise ValueError('invalid source URL: ' + source)
                    if source and not source_url.scheme and Path(source).suffix.lower() in {'.json', '.md', '.txt', '.csv', '.py', '.pdf', '.xlsx', '.xls', '.docx'}:
                        names.add(source)
                    local_source = observation.get('local_file')
                    if local_source and observation.get('source_sha256'):
                        local_bytes = read_file(root, local_source)[0]
                        if hashlib.sha256(local_bytes).hexdigest() != observation['source_sha256'].lower():
                            raise ValueError('source_sha256 does not match local evidence: ' + local_source)
    research = {role: {key: record.get(key) for key in ('status', 'agent_id', 'artifacts', 'note')}
                for role, record in state['roles'].items() if role != 'independent_review'}
    return {'schema_version': 1, 'dependencies': [dict(path=k, sha256=v) for k, v in sorted(result.items())],
            'research_state_sha256': fingerprint({'roles': research, 'context': {key: state.get(key) for key in ('schema_version', 'company', 'symbol', 'as_of')}})}
