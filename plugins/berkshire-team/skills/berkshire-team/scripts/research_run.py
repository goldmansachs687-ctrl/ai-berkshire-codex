"""Create research checkpoints and detect missing or changed role artifacts."""
import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfoNotFoundError

import research_progress as progress

ROLES = (*progress.RESEARCHERS, progress.REVIEWER)
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
    agent_id = agent_id.strip() if agent_id else None
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
    if 'progress' in state:
        progress.validate_role(state, role, status, agent_id, artifacts, directory)
        protocol = state['progress'].get('debate_protocol', 0)
        if protocol >= 4 and role in progress.DEBATERS:
            from research_exchange import checkpoint_exchange
            checkpoint_exchange(directory, state['roles'], role, status, artifacts, agent_id)
        elif protocol >= 2 and role in progress.DEBATERS:
            if status == 'waiting':
                opening = progress.OPENINGS[role]
                if not (directory / opening).read_text(encoding='utf-8').strip():
                    raise ValueError(f'{opening} must be nonempty')
                checksum = next(item['sha256'] for item in artifacts if item['path'] == opening)
                if record.setdefault('opening_sha256', checksum) != checksum:
                    raise ValueError(f'{opening} changed after its first checkpoint')
            if status == 'running' and record['status'] == 'waiting':
                for side, opening in progress.OPENINGS.items():
                    other = state['roles'][side]
                    if other.get('opening_sha256') != digest(directory / opening):
                        raise ValueError('both unchanged openings are required before exchange')

        progress.event(state, progress.STATUS[status], note, role)
    if status == 'running':
        record['attempts'] += 1
    record.update(status=status, note=note)
    if delivery_binding is not None:
        record['delivery_binding'] = delivery_binding
    if agent_id:
        record['agent_id'] = agent_id
    if artifacts:
        record['artifacts'] = artifacts
    save_run(directory, state)
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


def save_run(directory, state):
    save(directory / 'run.json', state)
    if 'progress' in state:
        progress.write_dashboard(directory, state)


def update_progress(directory, action, *, note='', question='', next_action='', stage=None,
                    role=None, display_timezone='UTC'):
    directory = Path(directory).resolve()
    state = json.loads((directory / 'run.json').read_text(encoding='utf-8'))
    if action == 'start':
        progress.start(state, question, next_action, display_timezone)
    elif action == 'stage':
        if stage in {'complete', 'limited'}:
            from delivery_gate import accept
            result = accept(directory)
            if result['status'].lower() != stage:
                raise ValueError('delivery gate returned ' + result['status'])
        if stage == 'debate' and state['progress'].get('debate_protocol', 0) >= 2:
            from delivery_dependencies import read_file
            data, _, _ = read_file(directory, progress.DEBATE_BASIS)
            checksum = hashlib.sha256(data).hexdigest()
            previous = state['progress'].setdefault('debate_basis_sha256', checksum)
            if checksum != previous:
                raise ValueError('debate-basis.md changed after the debate began')
        if stage == 'review':
            from delivery_dependencies import read_file
            for name in progress.REVIEW_OUTPUTS:
                read_file(directory, name)
            if state['progress'].get('debate_protocol', 0) >= 2:
                from research_debate import preflight_debate
                preflight_debate(directory, state)
        progress.set_stage(state, inspect(directory), stage, note, next_action)
    elif action == 'event':
        if state['progress']['stage'] in {'blocked', 'complete', 'limited'}:
            raise ValueError('resume an active stage before recording research events')
        if role and state['roles'][role]['status'] != 'running':
            raise ValueError('role updates require a running checkpoint')
        if role:
            state['roles'][role]['note'] = note.strip()
        progress.event(state, '研究更新', note, role)
        if question.strip():
            state['progress']['question'] = question.strip()
        if next_action.strip():
            state['progress']['next_action'] = next_action.strip()
    elif action == 'render':
        progress.write_dashboard(directory, state)
        return directory / 'progress.html'
    save_run(directory, state)
    return directory / 'progress.html'




def add_learning_parser(commands):
    learn = commands.add_parser('graph-learn', help='checkpoint a local learning exercise through LangGraph')
    learn.add_argument('action', choices=('init', 'start', 'submit', 'resume'))
    learn.add_argument('--run', required=True)
    learn.add_argument('--stage')
    learn.add_argument('--role')
    learn.add_argument('--agent')
    learn.add_argument('--note')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    init = commands.add_parser('init')
    for field in ('root', 'company', 'symbol', 'date'):
        init.add_argument('--' + field, required=True)
    update = commands.add_parser('checkpoint')
    update.add_argument('--run', required=True)
    update.add_argument('--role', choices=progress.TEAM, required=True)
    update.add_argument('--status', choices=tuple(key for key in progress.STATUS if key != 'queued'), required=True)
    update.add_argument('--file', action='append', default=[])
    update.add_argument('--note', required=True)
    update.add_argument('--agent-id')
    resume = commands.add_parser('resume')
    resume.add_argument('--run', required=True)
    handoff = commands.add_parser('debate-ready', help='check what can be shared before contacting a debater')
    handoff.add_argument('--run', required=True)
    handoff.add_argument('--role', choices=progress.DEBATERS, required=True)
    replay = commands.add_parser('graph-replay', help='replay saved research with LangGraph')
    replay.add_argument('--output', required=True)
    source = replay.add_mutually_exclusive_group(required=True)
    source.add_argument('--source')
    source.add_argument('--resume', action='store_true')
    replay.add_argument('--pause-before-review', action='store_true')
    live = commands.add_parser('graph-debate', help='dispatch the live debate through LangGraph')
    live.add_argument('--run', required=True)
    live.add_argument('--resume', action='store_true')
    for action in ('start', 'stage', 'event', 'render'):
        view = commands.add_parser('progress-' + action)
        view.add_argument('--run', required=True)
        if action in {'start', 'event'}:
            view.add_argument('--question', required=action == 'start', default='')
        if action in {'start', 'stage', 'event'}:
            view.add_argument('--next', required=action != 'event', default='')
        if action in {'stage', 'event'}:
            view.add_argument('--note', required=True)
        if action == 'start':
            view.add_argument('--timezone', default='UTC')
        if action == 'stage':
            view.add_argument('--stage', choices=tuple(progress.STAGES), required=True)
        if action == 'event':
            view.add_argument('--role', choices=progress.TEAM)
    add_learning_parser(commands)
    args = parser.parse_args()
    try:
        if args.command == 'init':
            print(initialize(args.root, args.company, args.symbol, args.date))
        elif args.command == 'debate-ready':
            from research_exchange import ready
            directory = Path(args.run).resolve()
            state = json.loads((directory / 'run.json').read_text(encoding='utf-8'))
            if state['progress']['stage'] != 'debate' or state['progress'].get('debate_protocol', 0) < 4:
                raise ValueError('debate-ready requires an active debate with protocol 4 or later')
            print(ready(directory, state['roles'], args.role))
        elif args.command == 'graph-learn':
            try:
                from research_learning import run_learning
            except ModuleNotFoundError as exc:
                if exc.name not in {'langgraph', 'langgraph.checkpoint.sqlite'}:
                    raise
                raise ValueError('Install dependencies from references/langgraph-requirements.txt') from exc
            result = run_learning(args.run, args.action, stage=args.stage, role=args.role,
                                  agent=args.agent, note=args.note)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command == 'graph-replay':
            try:
                from research_graph import replay_run
            except ModuleNotFoundError as exc:
                if exc.name not in {'langgraph', 'langgraph.checkpoint.sqlite'}:
                    raise
                raise ValueError('Install the optional dependencies from references/langgraph-requirements.txt') from exc
            if args.resume and args.pause_before_review:
                raise ValueError('--pause-before-review is set when starting a replay')
            result = replay_run(args.output, args.source, args.pause_before_review)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if result['status'] == 'BLOCKED':
                raise SystemExit(1)
        elif args.command == 'graph-debate':
            try:
                from research_live_debate import run_live_debate
            except ModuleNotFoundError as exc:
                if exc.name not in {'langgraph', 'langgraph.checkpoint.sqlite'}:
                    raise
                raise ValueError('Install dependencies from references/langgraph-requirements.txt') from exc
            result = run_live_debate(args.run, resume=args.resume)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if result['status'] == 'BLOCKED':
                raise SystemExit(1)
        elif args.command.startswith('progress-'):
            print(update_progress(
                args.run, args.command.removeprefix('progress-'), note=getattr(args, 'note', ''),
                question=getattr(args, 'question', ''), next_action=getattr(args, 'next', ''),
                stage=getattr(args, 'stage', None), role=getattr(args, 'role', None),
                display_timezone=getattr(args, 'timezone', 'UTC'),
            ))
        else:
            result = inspect(args.run) if args.command == 'resume' else checkpoint(args.run, args.role, args.status, args.file, args.note, args.agent_id)
            print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError, TypeError, SyntaxError, ArithmeticError, ZoneInfoNotFoundError) as exc:
        parser.exit(2, str(exc) + '\n')


if __name__ == '__main__':
    main()
