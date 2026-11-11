"""Record team milestones and render a local dashboard from the run state."""
import hashlib
import json
from datetime import datetime, timezone
from html import escape
from os.path import relpath
from pathlib import Path
from string import Template
from urllib.parse import quote
from zoneinfo import ZoneInfo

RESEARCHERS = ('business_analyst', 'financial_analyst', 'industry_researcher', 'risk_assessor')
DEBATERS = ('bull_case', 'bear_case')
REVIEWER = 'independent_review'
TEAM = (*RESEARCHERS, *DEBATERS, REVIEWER)
STAGES = {
    'setup': '立项', 'research': '独立研究', 'debate': '多空辩论',
    'valuation': '估值与报告', 'review': '独立复核', 'complete': '交付完成',
    'limited': '有限交付', 'blocked': '流程受阻',
}
NEXT = {
    'setup': {'research'}, 'research': {'debate'}, 'debate': {'valuation', 'research'},
    'valuation': {'review', 'research', 'debate'},
    'review': {'complete', 'limited', 'research', 'debate', 'valuation'},
    'complete': {'research', 'debate', 'valuation', 'review'},
    'limited': {'research', 'debate', 'valuation', 'review'},
}
ROLE_STAGE = {**dict.fromkeys(RESEARCHERS, 'research'),
              **dict.fromkeys(DEBATERS, 'debate'), REVIEWER: 'review'}
LABELS = dict(zip(TEAM, ('商业模式', '财务与估值', '行业竞争', '管理层与风险',
                        '多方', '空方', '独立复核员')))
STATUS = {'pending': '待开始', 'queued': '待派工', 'running': '运行中',
          'waiting': '等候交接', 'complete': '已完成', 'failed': '受阻'}
DEBATE_OUTPUTS = dict(zip(DEBATERS, ('bull-case.md', 'bear-case.md')))
OPENINGS = dict(zip(DEBATERS, ('bull-opening.md', 'bear-opening.md')))
DEBATE_BASIS = 'debate-basis.md'
REVIEW_OUTPUTS = ('debate-ruling.md', 'leader-feedback.md')


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def event(state, kind, note, role=None):
    note = note.strip()
    if not note or len(note) > 500:
        raise ValueError('progress message must contain 1–500 characters')
    state['progress']['events'].append(
        {'time': timestamp(), 'kind': kind, 'role': role, 'note': note})


def start(state, question, next_action, display_timezone):
    question, next_action = question.strip(), next_action.strip()
    if not question or not next_action:
        raise ValueError('research question and next action are required')
    if 'progress' in state:
        raise ValueError('progress already enabled; use the existing run and timeline')
    ZoneInfo(display_timezone)
    for role in DEBATERS:
        state['roles'][role] = {'status': 'pending', 'attempts': 0, 'artifacts': [], 'note': ''}
    state['progress'] = {'stage': 'setup', 'question': question, 'next_action': next_action,
                         'timezone': display_timezone, 'debate_protocol': 4, 'events': []}
    event(state, '立项', question)


def has_current_roles(state, roles):
    return all(state['roles'][role].get('resumable_complete') and
               state['roles'][role].get('agent_id') for role in roles)


def set_stage(state, inspected, stage, note, next_action):
    progress = state['progress']
    current = progress['stage']
    previous = progress.get('blocked_from', current) if current == 'blocked' else current
    allowed = {previous, 'blocked'} | NEXT.get(previous, set())
    if stage not in allowed or (stage == current and current in {'complete', 'limited'}):
        raise ValueError(f'invalid workflow transition: {current} → {stage}')
    if stage != current and any(record['status'] == 'running' for record in state['roles'].values()):
        raise ValueError('finish or stop running roles before changing stages')
    if not next_action.strip():
        raise ValueError('next action is required')
    if stage in {'debate', 'valuation', 'review', 'complete', 'limited'}:
        if not has_current_roles(inspected, RESEARCHERS):
            raise ValueError('four valid research checkpoints are required')
    if stage in {'valuation', 'review', 'complete', 'limited'}:
        if not has_current_roles(inspected, DEBATERS):
            raise ValueError('two valid debate checkpoints are required')
    if stage in {'complete', 'limited'} and not has_current_roles(inspected, (REVIEWER,)):
        raise ValueError('a current independent review is required for delivery')
    if previous in {'review', 'complete', 'limited'} and stage in {'research', 'debate', 'valuation'}:
        reviewer = state['roles'][REVIEWER]
        reviewer.update(status='pending', artifacts=[], note='等待复核修订后的研究。')
        reviewer.pop('delivery_binding', None)
    if stage == 'blocked':
        progress['blocked_from'] = previous
    progress.update(stage=stage, next_action=next_action.strip())
    event(state, STAGES[stage], note)


def validate_role(state, role, status, agent_id, artifacts, directory):
    if status not in {'running', 'waiting', 'complete'}:
        return
    record = state['roles'][role]
    stage = state['progress']['stage']
    if ROLE_STAGE[role] != stage and not (role == 'financial_analyst' and stage == 'valuation'):
        raise ValueError(f'{role} cannot be {status} during {stage}')
    if not agent_id:
        raise ValueError('running and complete require the actual agent ID')
    if status in {'waiting', 'complete'} and (record['status'] != 'running' or record.get('agent_id') != agent_id):
        raise ValueError(f'{status} requires a running checkpoint from the same agent')
    if state['progress'].get('debate_protocol', 0) >= 2 and role in DEBATERS:
        opening = OPENINGS[role]
        received = next((item['sha256'] for item in artifacts if item['path'] == opening), None)
        if status == 'waiting' and not received:
            raise ValueError(f'{role} must file {opening} before exchanging questions')
        if status == 'complete' and (not received or received != record.get('opening_sha256')):
            raise ValueError(f'{role} must include its unchanged, checkpointed {opening}')
    if status == 'complete' and role in DEBATERS:
        expected = DEBATE_OUTPUTS[role]
        if not any(item['path'] == expected for item in artifacts) or not (directory / expected).read_text(encoding='utf-8').strip():
            raise ValueError(f'{role} requires a nonempty {expected}')
    for other, other_record in state['roles'].items():
        if other == role or other_record.get('agent_id') != agent_id:
            continue
        if (other_record['status'] in {'running', 'waiting'} or
                role in (*DEBATERS, REVIEWER) or other in (*DEBATERS, REVIEWER)):
            raise ValueError('agent ID conflicts with an active or independent role')


def write_dashboard(directory, state, *, artifact_directory=None):
    progress = state['progress']
    replay = artifact_directory is not None
    artifact_directory = artifact_directory if replay else directory
    status_labels = {**STATUS, 'queued': '待核对', 'complete': '已核对'} if replay else STATUS

    def artifact_link(path, label):
        resolved = (artifact_directory / path).resolve()
        if not resolved.is_relative_to(artifact_directory) or not resolved.is_file():
            return ''
        return f'<a href="./{quote(relpath(resolved, directory))}">{escape(label)}</a>'

    stage = progress['stage']
    records = state['roles']
    active = {r['agent_id'] for r in records.values() if r['status'] == 'running' and r.get('agent_id')}
    queued = [role for role in TEAM if ROLE_STAGE[role] == stage and records[role]['status'] == 'pending']
    done = sum(records[role]['status'] == 'complete' for role in TEAM)
    shown_stage = 'complete' if stage == 'limited' else stage
    steps = ''.join(f'<li aria-current="step">{STAGES[key]}</li>' if key == shown_stage else f'<li>{STAGES[key]}</li>'
                    for key in ('setup', 'research', 'debate', 'valuation', 'review', 'complete'))
    cards = []
    for role in TEAM:
        record = records[role]
        status = 'queued' if role in queued else record['status']
        links = []
        for artifact in record['artifacts']:
            path = artifact['path']
            if role == REVIEWER and path not in ('review.md', 'review.json'):
                continue
            link = artifact_link(path, Path(path).name)
            if link:
                links.append(link)
        cards.append(f'<article><div class="role"><h3>{LABELS[role]}</h3>'
                     f'<span class="badge {status}">{status_labels[status]}</span></div>'
                     f'<p>{escape(record["note"] or "等待进入对应阶段。")}</p>'
                     f'<div class="files">{" ".join(links)}</div></article>')
    timeline = []
    display_timezone = ZoneInfo(progress['timezone'])
    for item in reversed(progress['events']):
        time = datetime.fromisoformat(item['time']).astimezone(display_timezone).strftime('%m-%d %H:%M %Z')
        role = ' · ' + LABELS[item['role']] if item['role'] else ''
        timeline.append(f'<li><time datetime="{escape(item["time"])}">{escape(time)}</time>'
                        f'<strong>{escape(item["kind"] + role)}</strong>'
                        f'<p>{escape(item["note"])}</p></li>')
    debate_link = ''
    if stage in {'valuation', 'review', 'complete', 'limited'} or (stage == 'debate' and not replay):
        debate_link = artifact_link('cross-examination.md', '查看多空交锋')
    deliverables = debate_link
    if stage in {'complete', 'limited'}:
        links = (('report.md', '正式报告'), ('leader-feedback.md', 'Leader 反馈'),
                 ('debate-ruling.md', '多空裁决'))
        deliverables = ' '.join((debate_link, *(artifact_link(path, label) for path, label in links)))
    if deliverables.strip():
        deliverables = f'<p class="files">{deliverables}</p>'
    counts = (f'<span><b>{done}</b> / {len(TEAM)} 项角色产物已核对</span>' if replay else
              f'<span><b>{len(active)}</b> 个子智能体运行中</span>'
              f'<span><b>{len(queued)}</b> 项待派工</span><span><b>{done}</b> 项已完成</span>')
    template = Template(Path(__file__).with_name('research_progress.html').read_text(encoding='utf-8'))
    events = progress['events']
    latest = datetime.fromisoformat(events[-1]['time']).astimezone(display_timezone)
    page = template.substitute(
        latest=escape(latest.strftime('%m-%d %H:%M:%S %Z')),
        company=escape(state['company']), symbol=escape(state['symbol']),
        cutoff=escape(state['as_of']), stage=STAGES[stage], question=escape(progress['question']),
        counts=counts, steps=steps, cards=''.join(cards),
        next_action=escape(progress['next_action']), timeline=''.join(timeline), deliverables=deliverables,
    )
    content = page.split('<main>', 1)[1].split('</main>', 1)[0]
    revision = hashlib.sha256(content.encode('utf-8')).hexdigest() if replay else len(events)
    payload = {'revision': revision, 'terminal': stage in {'complete', 'limited'}, 'content': content}
    write_in_place(directory / 'progress-state.js', 'window.berkshireProgress(' + json.dumps(payload) + ');')
    write_in_place(directory / 'progress.html', page)


def write_in_place(path, content):
    # Preserve the inode Chrome was granted access to for each local file.
    if path.is_symlink():
        raise ValueError(f'{path.name} must be a regular local file')
    with path.open('r+b' if path.exists() else 'wb') as handle:
        handle.write(content.encode('utf-8'))
        handle.truncate()
