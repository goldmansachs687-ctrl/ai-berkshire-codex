"""Replay saved research through a durable LangGraph workflow without model calls."""
import hashlib
import sqlite3
from contextlib import closing
from functools import partial
from operator import add
from pathlib import Path
from typing import Annotated, TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from langsmith import tracing_context

import research_progress as progress
from delivery_dependencies import read_file, strict_json
from delivery_gate import accept
from research_debate import preflight_debate
from research_run import digest, inspect, save


class ReplayState(TypedDict, total=False):
    source: str
    source_fingerprint: str
    pause_before_review: bool
    researchers_checked: bool
    bull_case: bool
    bear_case: bool
    exchange_checked: bool
    comparisons: list[dict]
    delivery: dict
    events: Annotated[list[dict], add]


def source_state(state):
    root = Path(state['source'])
    data = (root / 'run.json').read_bytes()
    if hashlib.sha256(data).hexdigest() != state['source_fingerprint']:
        raise ValueError('source run.json changed; start a new replay')
    return root, strict_json(data.decode('utf-8'))


def milestone(kind, note, role=None):
    return [{'time': progress.timestamp(), 'kind': kind, 'role': role, 'note': note}]


def verify_research(state):
    root, source = source_state(state)
    if source.get('progress', {}).get('debate_protocol', 0) < 2:
        raise ValueError('replay requires recorded independent openings (debate protocol 2 or later)')
    roles = inspect(root)['roles']
    if not all(roles[role]['resumable_complete'] and roles[role].get('agent_id')
               for role in progress.RESEARCHERS):
        raise ValueError('replay requires four intact research checkpoints')
    basis, _, _ = read_file(root, progress.DEBATE_BASIS)
    if hashlib.sha256(basis).hexdigest() != source['progress'].get('debate_basis_sha256'):
        raise ValueError('replay requires the original debate basis')
    return {'researchers_checked': True, 'events': milestone('独立研究', '四份既有取证底稿已校验')}


def verify_opening(state, role):
    root, source = source_state(state)
    name = progress.OPENINGS[role]
    while not (root / name).exists():
        interrupt({'stage': 'debate', 'role': role, 'note': f'等待原始开篇 {name}'})
    content, _, _ = read_file(root, name)
    if hashlib.sha256(content).hexdigest() != source['roles'][role].get('opening_sha256'):
        raise ValueError(f'{name} does not match its original checkpoint')
    return {role: True, 'events': milestone('等候交接', '既有开篇已校验', role)}


def verify_exchange(state):
    root, _ = source_state(state)
    read_file(root, 'cross-examination.md')
    roles = inspect(root)['roles']
    if not all(roles[role]['resumable_complete'] for role in progress.DEBATERS):
        raise ValueError('replay requires both intact debate replies')
    return {'exchange_checked': True, 'events': milestone('多空辩论', '双方开篇齐备，已核对既有质询与答复底稿')}


def recompute_comparisons(state):
    root, source = source_state(state)
    checks = preflight_debate(root, source)
    return {'comparisons': checks, 'events': milestone('估值与报告', f'已复算 {len(checks)} 项单变量比较')}


def verify_delivery(state):
    events = []
    if state['pause_before_review']:
        interrupt({'stage': 'review', 'role': progress.REVIEWER, 'note': '暂停于既有独立复核验证之前'})
        events = milestone('独立复核', '从 SQLite 断点恢复，继续核对既有复核记录')
    root, _ = source_state(state)
    result = accept(root)
    status = result['status']
    delivery = {key: result[key] for key in ('status', 'issues')}
    return {'delivery': delivery, 'events': events + milestone(
        progress.STAGES[status.lower()], f'既有独立复核和交付检查返回 {status}', progress.REVIEWER)}


def build_graph(checkpointer):
    graph = StateGraph(ReplayState)
    graph.add_node('research', verify_research)
    graph.add_node('bull', partial(verify_opening, role='bull_case'))
    graph.add_node('bear', partial(verify_opening, role='bear_case'))
    graph.add_node('exchange', verify_exchange)
    graph.add_node('valuation', recompute_comparisons)
    graph.add_node('review', verify_delivery)
    graph.add_edge(START, 'research')
    graph.add_edge('research', 'bull')
    graph.add_edge('research', 'bear')
    graph.add_edge(['bull', 'bear'], 'exchange')
    graph.add_edge('exchange', 'valuation')
    graph.add_edge('valuation', 'review')
    graph.add_edge('review', END)
    return graph.compile(checkpointer=checkpointer)


def render_replay(output, state, waiting=(), error=None):
    root, source = source_state(state)
    original_roles = source['roles']
    roles = {role: {'status': 'pending', 'note': '', 'artifacts': []} for role in progress.TEAM}
    if state.get('researchers_checked'):
        for role in progress.RESEARCHERS:
            roles[role].update(status='complete', note='已核对既有底稿',
                               artifacts=original_roles[role]['artifacts'])
    for role in progress.DEBATERS:
        if state.get(role):
            roles[role].update(status='waiting', note='已核对独立开篇',
                               artifacts=[{'path': progress.OPENINGS[role]}])
        if state.get('exchange_checked'):
            roles[role].update(status='complete', note='已核对既有开篇与答复',
                               artifacts=original_roles[role]['artifacts'])
    delivery = state.get('delivery')
    stage, next_action, status = 'research', '核对既有研究底稿', 'RUNNING'
    if state.get('researchers_checked'):
        stage, next_action = 'debate', '核对双方独立开篇和质询答复'
    if state.get('exchange_checked'):
        stage, next_action = 'valuation', '复算已登记的单变量估值比较'
    if 'comparisons' in state:
        stage, next_action = 'review', '验证既有独立复核和交付结论'
    events = list(state['events'])
    if waiting:
        status = 'PAUSED'
        stage = waiting[0]['stage']
        next_action = ' · '.join(item['note'] for item in waiting)
        for item in waiting:
            roles[item['role']].update(status='waiting', note=item['note'])
        events += milestone('回放暂停', next_action)
    if delivery:
        status = delivery['status']
        stage, next_action = status.lower(), '查看回放结果与原研究的复核范围'
        if status in ('COMPLETE', 'LIMITED'):
            roles[progress.REVIEWER].update(status='complete', note='已核对既有独立复核记录',
                                           artifacts=original_roles[progress.REVIEWER]['artifacts'])
    if error:
        stage, next_action, status = 'blocked', error, 'BLOCKED'
        events += milestone('回放受阻', error[:500])
    source.update(roles=roles, progress={
        'stage': stage, 'question': 'LangGraph 离线回放 · 核验已有研究产物',
        'next_action': next_action, 'timezone': source['progress']['timezone'], 'events': events,
    })
    progress.write_dashboard(output, source, artifact_directory=root)
    result = {'status': status, 'stage': stage, 'waiting': list(waiting),
              'comparisons': state.get('comparisons', []), 'delivery': delivery,
              'error': error, 'events': events, 'dashboard': str(output / 'progress.html')}
    save(output / 'replay-result.json', result)
    return result


def replay_run(output, source=None, pause_before_review=False):
    output = Path(output).resolve()
    database = output / 'langgraph.sqlite3'
    config = {'configurable': {'thread_id': 'berkshire-replay'}}
    if source is not None:
        source = Path(source).resolve()
        if output.is_relative_to(source):
            raise ValueError('replay output must be outside the original research directory')
        initial = {'source': str(source), 'source_fingerprint': digest(source / 'run.json'),
                   'pause_before_review': pause_before_review,
                   'events': milestone('立项', '开始离线回放，沿用已保存的研究产物')}
        output.mkdir(parents=True, exist_ok=False)
    elif not database.is_file():
        raise ValueError('no replay checkpoint in the output directory')
    else:
        initial = None
    with closing(sqlite3.connect(output / '.runner.sqlite3', timeout=0)) as lock:
        try:
            lock.execute('BEGIN IMMEDIATE')
        except sqlite3.OperationalError as exc:
            raise ValueError('this replay is already running or its lock is unavailable') from exc
        with tracing_context(enabled=False), SqliteSaver.from_conn_string(str(database)) as saver:
            graph = build_graph(saver)
            if initial is None:
                snapshot = graph.get_state(config)
                if not snapshot.values:
                    raise ValueError('no replay state in the checkpoint database')
                source_state(snapshot.values)
                if not snapshot.next:
                    return render_replay(output, snapshot.values)
                if snapshot.interrupts:
                    initial = Command(resume={item.id: True for item in snapshot.interrupts})
            else:
                render_replay(output, initial)
            try:
                for state in graph.stream(initial, config, stream_mode='values', durability='sync'):
                    render_replay(output, state)
            except (ValueError, OSError, TypeError, KeyError, ArithmeticError, SyntaxError) as exc:
                snapshot = graph.get_state(config)
                return render_replay(output, snapshot.values, error=str(exc))
            snapshot = graph.get_state(config)
            return render_replay(output, snapshot.values, tuple(item.value for item in snapshot.interrupts))
