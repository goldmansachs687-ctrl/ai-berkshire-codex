"""Checkpoint a local learning exercise with independently authored submissions."""
import json
import sqlite3
from contextlib import closing
from datetime import datetime
from hashlib import sha256
from html import escape
from pathlib import Path
from string import Template
from typing import TypedDict
from urllib.parse import quote
from zoneinfo import ZoneInfo

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from langsmith import tracing_context

from knowledge import integrity, read_library
from research_progress import write_in_place
from research_run import digest, save

TZ = ZoneInfo('Asia/Hong_Kong')
STUDENTS = ('A', 'B')
STAGES = {
    'before': ('学习前答题', STUDENTS),
    'materials': ('原文与录音就绪', ('coordinator',)),
    'draft': ('独立提炼', STUDENTS),
    'critique': ('老师回原文批改', ('teacher',)),
    'revision': ('学员修订', STUDENTS),
    'approval': ('老师复核规则', ('teacher',)),
    'after': ('同题学习后作答', STUDENTS),
    'grading': ('独立案例验收', ('grader',)),
}
ARTIFACTS = {
    'before': ('submissions/{role}-before.md',),
    'materials': ('materials/sources.json',),
    'draft': ('submissions/{role}-draft.md',),
    'critique': ('submissions/teacher-critique.md',),
    'revision': ('submissions/{role}-revision.md',),
    'approval': ('submissions/teacher-approval.md', 'submissions/principle.md'),
    'after': ('submissions/{role}-after.md',),
    'grading': ('grading/independent-grading.md',),
}
SEALED = {'case/question.md', 'case/evidence.md', 'grading/rubric.md'}
ROLES = {'A': '学员 A', 'B': '学员 B', 'teacher': '老师',
         'grader': '案例评分员', 'coordinator': '材料整理'}


class LearningState(TypedDict):
    run: str
    seal_sha256: str
    completed: list[str]


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def now():
    return datetime.now(TZ).isoformat(timespec='seconds')


def verify_files(root, files):
    for name, sha256 in files.items():
        path = root / name
        if not path.resolve().is_relative_to(root) or not path.is_file() or digest(path) != sha256:
            raise ValueError(f'已封存文件缺失或被修改：{name}')


def verify_seal(root, expected=None):
    seal_path = root / 'seal.json'
    if expected and digest(seal_path) != expected:
        raise ValueError('封存记录已修改')
    seal = read_json(seal_path)
    if set(seal['files']) != SEALED:
        raise ValueError('封存须包含题目、证据和评分标准')
    if datetime.fromisoformat(seal['sealed_at']).utcoffset() is None:
        raise ValueError('封存时间须带时区')
    verify_files(root, seal['files'])
    return seal


def journal(root):
    path = root / 'learning-events.json'
    return read_json(path) if path.exists() else []


def receipts(events):
    return {(item['stage'], item['role']): item for item in events if item['status'] == 'submitted'}


def verify_materials(root):
    data = read_json(root / 'materials/sources.json')
    library = Path(data['library'])
    if not library.is_absolute():
        library = root / library
    rows = {row['id']: row for row in read_library(library)['materials']}
    sources = data['sources']
    if (len(sources) < 2 or not {'page', 'time'} <= {source['locator_kind'] for source in sources}
            or len({source['id'] for source in sources}) != len(sources)):
        raise ValueError('材料须包含不同的有页码原文和有时间戳录音')
    for source in sources:
        row = rows[source['id']]
        locator_kind = source['locator_kind']
        if locator_kind == 'time' and row['kind'] not in {'audio', 'video'}:
            raise ValueError('时间定位须对应已登记的原声文件')
        if locator_kind == 'page' and Path(row['source_path']).suffix.casefold() != '.pdf':
            raise ValueError('页码定位须对应已登记的 PDF 原件')
        if not integrity(row) or not row.get('text_path') or not any(
                item['locator'] == source['locator'] for item in row['reviewed_sections']):
            raise ValueError(f'材料未登记阅读位置、索引缺失或文件已变：{source["id"]}')
    if not data['files']:
        raise ValueError('缺少可复查的原文定位或转写记录')
    verify_files(root, data['files'])


def stage_node(stage):
    def check(state):
        root = Path(state['run']).resolve()
        verify_seal(root, state['seal_sha256'])
        submitted = receipts(journal(root))
        for role in STAGES[stage][1]:
            if (stage, role) not in submitted:
                interrupt({'stage': stage, 'note': STAGES[stage][0]})
                break
        submitted = receipts(journal(root))
        for role in STAGES[stage][1]:
            verify_files(root, submitted[stage, role]['files'])
        if stage == 'materials':
            verify_materials(root)
        return {'completed': state['completed'] + [stage]}
    return check


def graph_with(saver):
    graph = StateGraph(LearningState)
    previous = START
    for stage in STAGES:
        graph.add_node(stage, stage_node(stage))
        graph.add_edge(previous, stage)
        previous = stage
    graph.add_edge(previous, END)
    return graph.compile(checkpointer=saver)


def render(root, snapshot, events, error=None):
    active = snapshot.next[0] if snapshot.next else None
    title = STAGES[active][0] if active else '各阶段产物已核对'
    status = 'BLOCKED' if error else 'WAITING' if active else 'COMPLETE'
    cards = []
    for role, label in ROLES.items():
        own = [item for item in events if item['role'] == role]
        latest = own[-1] if own else None
        badge, note = ('待开始', '') if latest is None else (
            '进行中' if latest['status'] == 'started' else '已提交', latest['note'])
        names = [name for item in own for name in item.get('files', {})]
        links = ' '.join(f'<a href="./{quote(name)}">{escape(Path(name).name)}</a>' for name in names)
        cards.append(f'<article><div class="role"><h3>{label}</h3><span class="badge">{badge}</span>'
                     f'</div><p>{escape(note)}</p><div class="files">{links}</div></article>')
    timeline = ''.join(
        f'<li><time>{escape(item["time"])}</time><strong>{STAGES[item["stage"]][0]} · '
        f'{ROLES[item["role"]]}</strong><p>{escape(item["note"])}</p></li>'
        for item in reversed(events))
    steps = ''.join('<li aria-current="step">' + label + '</li>' if stage == active else '<li>' + label + '</li>'
                    for stage, (label, _) in STAGES.items())
    template = Template(Path(__file__).with_name('research_progress.html').read_text(encoding='utf-8'))
    page = template.substitute(latest=escape(events[-1]['time'] if events else now()), company='AI 伯克希尔',
                               symbol='本地资料库', cutoff='香港时间', stage=title, question='读书与演讲 → 新案例验收',
                               counts=f'<span>{len(snapshot.values["completed"])} / {len(STAGES)} 阶段已检查</span>',
                               steps=steps, cards=''.join(cards), next_action=escape(error or title),
                               timeline=timeline, deliverables='')
    content = page.split('<main>', 1)[1].split('</main>', 1)[0]
    payload = {'revision': sha256(content.encode('utf-8')).hexdigest(),
               'terminal': status == 'COMPLETE', 'content': content}
    write_in_place(root / 'progress-state.js', 'window.berkshireProgress(' + json.dumps(payload) + ');')
    write_in_place(root / 'progress.html', page)
    result = {'status': status, 'waiting': active, 'completed': snapshot.values['completed'],
              'seal_sha256': snapshot.values['seal_sha256'], 'error': error, 'events': events}
    save(root / 'learning-result.json', result)
    return result


def run_learning(root, action, *, stage=None, role=None, agent=None, note=None):
    root = Path(root).resolve(strict=True)
    database = root / 'langgraph.sqlite3'
    with closing(sqlite3.connect(root / '.learning-lock.sqlite3', timeout=0)) as lock:
        try:
            lock.execute('BEGIN IMMEDIATE')
        except sqlite3.OperationalError as exc:
            raise ValueError('另一进程正在更新这轮学习断点') from exc
        if action != 'init' and not database.is_file():
            raise ValueError('先用 graph-learn init 建立断点')
        with tracing_context(enabled=False), SqliteSaver.from_conn_string(str(database)) as saver:
            graph = graph_with(saver)
            config = {'configurable': {'thread_id': 'berkshire-learning'}}
            snapshot = graph.get_state(config)
            events = journal(root)
            if action == 'init':
                if snapshot.values or events:
                    raise ValueError('学习轮次已存在')
                verify_seal(root)
                initial = {'run': str(root), 'seal_sha256': digest(root / 'seal.json'), 'completed': []}
                graph.invoke(initial, config, durability='sync')
            else:
                if not snapshot.values:
                    raise ValueError('未找到已初始化的学习断点')
                try:
                    verify_seal(root, snapshot.values['seal_sha256'])
                    submitted = receipts(events)
                    for item in submitted.values():
                        verify_files(root, item['files'])
                    if 'materials' in snapshot.values['completed']:
                        verify_materials(root)
                except (OSError, ValueError, KeyError) as exc:
                    render(root, snapshot, events, error=str(exc))
                    raise
                if action in {'start', 'submit'}:
                    if stage not in STAGES or snapshot.next != (stage,) or role not in STAGES[stage][1]:
                        raise ValueError('阶段或角色与当前断点不符')
                    if not agent or not note or not note.strip() or len(note) > 500:
                        raise ValueError('登记实际参与者 ID 和 1–500 字进展')
                    for item in events:
                        if (item['role'] == role) != (item['agent'] == agent):
                            raise ValueError('同一角色必须使用同一 ID，独立角色必须使用不同 ID')
                    prior = [item for item in events if (item['stage'], item['role']) == (stage, role)]
                    required = [] if action == 'start' else ['started']
                    if [item['status'] for item in prior] != required:
                        raise ValueError('须先记录派工，且只能提交一次')
                    if datetime.fromisoformat(verify_seal(root)['sealed_at']) > datetime.now(TZ):
                        raise ValueError('封存时间晚于当前派工时间')
                    item = dict(stage=stage, role=role, agent=agent, note=note,
                                time=now(), status='started' if action == 'start' else 'submitted')
                    if action == 'submit':
                        names = [name.format(role=role) for name in ARTIFACTS[stage]]
                        for name in names:
                            path = root / name
                            if not path.resolve().is_relative_to(root) or not path.is_file() or not path.read_text(encoding='utf-8').strip():
                                raise ValueError(f'缺少交付文件：{name}')
                        if stage == 'materials':
                            verify_materials(root)
                        item['files'] = {name: digest(root / name) for name in names}
                    events.append(item)
                    save(root / 'learning-events.json', events)
                if snapshot.next:
                    waiting = snapshot.next[0]
                    submitted = receipts(events)
                    if all((waiting, name) in submitted for name in STAGES[waiting][1]):
                        command = Command(resume=True) if snapshot.interrupts else None
                        graph.invoke(command, config, durability='sync')
            return render(root, graph.get_state(config), events)
