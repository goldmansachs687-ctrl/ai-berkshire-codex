"""Create research checkpoints and detect missing or changed role artifacts."""
import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

ROLES = ('business_analyst', 'financial_analyst', 'industry_researcher', 'risk_assessor', 'independent_review')
REVIEW_ARTIFACTS = ('review.md', 'report.md', 'evidence.json')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, data):
    path = Path(path)
    temporary = path.with_name(path.name + '.' + uuid4().hex + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def initialize(root, company, symbol, date):
    datetime.strptime(date, '%Y-%m-%d')
    slug = ''.join(c for c in company if c.isalnum() or c in '-_')[:60] or 'company'
    directory = Path(root).resolve() / f'{slug}-{date.replace("-", "")}-{uuid4().hex[:6]}'
    directory.mkdir(parents=True, exist_ok=False)
    save(directory / 'run.json', {'schema_version': 1, 'company': company, 'symbol': symbol,
         'as_of': date, 'phase': 'independent_research', 'next_action': 'Gather primary filings, then independent first passes',
         'roles': {role: {'status': 'pending', 'attempts': 0, 'artifacts': [], 'note': ''} for role in ROLES}})
    save(directory / 'evidence.json', {'schema_version': 1, 'required_claims':
         ['price', 'shares', 'fx', 'revenue', 'parent_profit', 'ocf', 'cash_capex', 'sbc', 'net_cash'],
         'scope_notes': 'Adapt required IDs to actual decision; explain any non-applicable fields. Never remove unavailable fields merely to pass.',
         'claims': []})
    return directory


def review_issues(directory, roles, agent_id, artifact_names):
    issues = []
    reviewer = agent_id.strip() if isinstance(agent_id, str) else ''
    if not reviewer:
        issues.append('independent_review requires the actual reviewer agent ID')
    elif any(reviewer == str(record.get('agent_id', '')).strip()
             for role, record in roles.items() if role != 'independent_review'):
        issues.append('independent reviewer must not be one of the recorded research agents')
    for name in REVIEW_ARTIFACTS:
        if name not in artifact_names:
            issues.append('independent_review must record ' + name)
            continue
        if name in ('review.md', 'report.md'):
            path = directory / name
            if not path.resolve().is_relative_to(directory) or not path.is_file():
                issues.append('missing or outside run: ' + name)
            else:
                try:
                    if not path.read_text(encoding='utf-8').strip():
                        issues.append('empty review artifact: ' + name)
                except (OSError, UnicodeError):
                    issues.append('unreadable review artifact: ' + name)
    return issues


def checkpoint(directory, role, status, files, note, agent_id=None):
    directory = Path(directory).resolve()
    state = json.loads((directory / 'run.json').read_text(encoding='utf-8'))
    record = state['roles'][role]
    files = list(files)
    if status == 'complete' and not files:
        raise ValueError('complete requires an explicit deliverable')
    if role == 'independent_review' and status == 'complete':
        if not any((directory / name).resolve() == directory / 'review.md' for name in files):
            raise ValueError('independent_review requires review.md as an explicit deliverable')
        # An audit cannot stay current after its report or evidence changes.
        for name in REVIEW_ARTIFACTS[1:]:
            if name not in files:
                files.append(name)
    delivery_binding = None
    if role == 'independent_review' and status == 'complete' and (directory / 'delivery.json').exists():
        from delivery_dependencies import binding
        delivery_binding = binding(directory, state)
        files.extend(item['path'] for item in delivery_binding['dependencies'] if item['path'] not in files)
    artifacts = []
    for name in files:
        path = (directory / name).resolve()
        if not path.is_relative_to(directory) or not path.is_file():
            raise ValueError('artifact must be an existing file inside run directory')
        artifacts.append({'path': str(path.relative_to(directory)), 'sha256': digest(path)})
    if status == 'complete' and not artifacts:
        raise ValueError('complete requires at least one actual deliverable')
    if role == 'independent_review' and status == 'complete':
        issues = review_issues(directory, state['roles'], agent_id,
                               {artifact['path'] for artifact in artifacts})
        if issues:
            raise ValueError('; '.join(issues))
    if status == 'running':
        record['attempts'] += 1
    record.update(status=status, note=note)
    if delivery_binding is not None:
        record['delivery_binding'] = delivery_binding
    if isinstance(agent_id, str) and agent_id.strip():
        record['agent_id'] = agent_id.strip()
    if artifacts:
        record['artifacts'] = artifacts
    save(directory / 'run.json', state)
    return state


def inspect(directory):
    directory = Path(directory).resolve()
    state = json.loads((directory / 'run.json').read_text(encoding='utf-8'))
    for role, record in state['roles'].items():
        issues = []
        for artifact in record['artifacts']:
            path = (directory / artifact['path']).resolve()
            if not path.is_relative_to(directory) or not path.is_file():
                issues.append('missing or outside run: ' + artifact['path'])
            elif digest(path) != artifact['sha256']:
                issues.append('changed since checkpoint: ' + artifact['path'])
        if role == 'independent_review' and record['status'] == 'complete':
            issues.extend(review_issues(directory, state['roles'], record.get('agent_id'),
                                       {artifact['path'] for artifact in record['artifacts']}))
        if role == 'independent_review' and record['status'] == 'complete' and (directory / 'delivery.json').exists():
            from delivery_dependencies import binding
            try:
                if record.get('delivery_binding') != binding(directory, state):
                    issues.append('delivery review missing or stale: dependency content/list or research state changed')
            except (OSError, ValueError, TypeError, KeyError, AttributeError, SyntaxError) as exc:
                issues.append('invalid delivery dependency: ' + str(exc))
        record['integrity_issues'] = issues
        record['resumable_complete'] = record['status'] == 'complete' and bool(record['artifacts']) and not issues
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    init = commands.add_parser('init')
    for field in ('root', 'company', 'symbol', 'date'):
        init.add_argument('--' + field, required=True)
    update = commands.add_parser('checkpoint')
    update.add_argument('--run', required=True)
    update.add_argument('--role', choices=ROLES, required=True)
    update.add_argument('--status', choices=('pending', 'running', 'complete', 'failed'), required=True)
    update.add_argument('--file', action='append', default=[])
    update.add_argument('--note', required=True)
    update.add_argument('--agent-id')
    resume = commands.add_parser('resume')
    resume.add_argument('--run', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'init':
            print(initialize(args.root, args.company, args.symbol, args.date))
        else:
            result = inspect(args.run) if args.command == 'resume' else checkpoint(args.run, args.role, args.status, args.file, args.note, args.agent_id)
            print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, str(exc) + '\n')


if __name__ == '__main__':
    main()
