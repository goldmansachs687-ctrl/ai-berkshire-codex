"""Dispatch and resume real Codex debaters with LangGraph."""
import sqlite3
from contextlib import closing
from functools import partial
from pathlib import Path
from threading import Lock
from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langsmith import tracing_context

import research_progress as progress
from debate_codex import codex_turn
from delivery_dependencies import read_file
from research_exchange import QUESTIONS, REPLIES, by_dispute, check_transcript, opposing_role, ready, replies
from research_run import checkpoint, digest, inspect, save, update_progress

BRIEF = 'debate-brief.json'
SIDES = dict(zip(progress.DEBATERS, ('bull', 'bear')))
FIELDS = {
    'opening': ('position', 'source_locator', 'counterevidence', 'change_trigger'),
    'questions': ('target', 'question'),
    'replies': ('response', 'concession', 'position_before', 'position_after',
                'change_trigger', 'source_locator', 'evidence_id', 'request_reason'),
    'review': ('strongest_evidence', 'directness', 'independent_judgment', 'assumption_impact',
               'decision', 'target', 'instruction'),
    'revision': ('response', 'position_after', 'source_locator'),
}
INSTRUCTIONS = {
    'opening': '独立给出同口径预测或区间，指出最强反证及改判条件。把事实、假设和压力情景分开。'
               '只从给定的中性事实和争点出发。每栏最多两句。',
    'questions': '每个争点提出一条最可能改变判断的质询。target 必须逐字引用对手开篇中的连续原文，'
                 '包括必要的标点。追问能区分两种解释的披露或数量级。',
    'replies': '逐项直接回答对手的原始问题，说明让步、预测前后和改判条件。'
               '如果某个已列来源能补一个具体缺口，填写 evidence_id 和 request_reason。否则两栏留空。每栏最多两句。',
    'review': '独立复核双方原始问答与补证，指出证据能支持的判断和对估值输入的影响。'
              '每项 decision 只能是 accept 或 revise。若需要明确的补答，填 revise，target 填 bull 或 bear，'
              'instruction 写可执行的补答要求。若证据确实不可得，允许保留未决，指出条件。'
              '通过时 target 填 none，instruction 留空。每栏最多两句。',
    'revision': '只处理复核员退回的争点。引用原始定位，说明答复后的预测和理由。每栏最多两句。',
}


class DebateState(TypedDict, total=False):
    brief_hash: str
    cycle: int
    decision: str


class Debate:
    def __init__(self, root, worker):
        self.root = root
        self.worker = worker
        self.lock = Lock()
        self.brief = read_file(root, BRIEF)[2]
        language = self.brief.get('output_language', 'Simplified Chinese')
        if not isinstance(language, str) or not language.strip():
            raise ValueError('output_language must be a nonempty language name')
        self.output_language = language.strip()
        self.issues = by_dispute(self.brief['issues'], ('topic',))
        if not isinstance(self.brief['facts'], str) or not self.brief['facts'].strip():
            raise ValueError('debate brief requires neutral facts')
        self.sources = self.brief['sources']
        if not isinstance(self.sources, dict):
            raise ValueError('debate brief sources must be an object')
        for item in self.sources.values():
            if not all(isinstance(item[key], str) and item[key].strip()
                       for key in ('path', 'description')):
                raise ValueError('each source needs a local file and description')
            first, last = item['first_line'], item['last_line']
            if type(first) is not int or type(last) is not int or not 1 <= first <= last <= first + 60:
                raise ValueError('source line ranges must be positive and at most 61 lines')
        self.receipts = root / '.debate-graph'
        self.receipts.mkdir(exist_ok=True)

    def read(self, name):
        _, text, parsed = read_file(self.root, name)
        return parsed if parsed is not None else text

    def event(self, note, next_action='', role=None):
        with self.lock:
            update_progress(self.root, 'event', note=note[:500], next_action=next_action, role=role)

    def note_role(self, role, status, files, note, agent_id):
        with self.lock:
            checkpoint(self.root, role, status, files, note, agent_id)

    def turn(self, step, role, inputs, issues, session=None, receipt_id=None):
        receipt = self.receipts / ((receipt_id or f'{step}-{role}') + '.json')
        session_file = receipt.with_suffix('.session.json')
        if receipt.exists():
            result = self.read(str(receipt.relative_to(self.root)))
        else:
            if session_file.exists():
                session = self.read(str(session_file.relative_to(self.root)))['agent_id']

            def started(agent_id):
                save(session_file, {'agent_id': agent_id})
                if role in SIDES:
                    self.note_role(role, 'running', [], {
                        'opening': '根据中性底稿独立预测，提交后再看对手意见',
                        'questions': '已收到对手原始开篇，准备质询',
                        'replies': '已收到对手原始问题，逐条答复',
                        'revision': '复核退回，按具体要求补答',
                    }[step], agent_id)
                else:
                    self.event('已启动独立复核智能体')

            label = {'bull_case': '多方', 'bear_case': '空方'}.get(role, '独立复核员')
            try:
                instruction = (
                    f'你是伯克希尔的{label}。{INSTRUCTIONS[step]}\n'
                    f'Output language: {self.output_language}. Write all original prose in this language. '
                    'Keep verbatim quotes, source locators, IDs, and schema values unchanged.'
                )
                result = self.worker(instruction, inputs, ('dispute_id', *FIELDS[step]), session, started)
                self.validate(step, inputs, result, issues)
            except (ValueError, OSError) as exc:
                if role in SIDES and session_file.exists():
                    agent = self.read(str(session_file.relative_to(self.root)))['agent_id']
                    self.note_role(role, 'failed', [], f'{step} 执行中断，等待恢复', agent)
                raise ValueError(f'{label}的{step}未完成：{exc}') from exc
        save(receipt, result)
        return result, {row['dispute_id']: row for row in result['rows']}

    def validate(self, step, inputs, result, issues):
        optional = {'evidence_id', 'request_reason', 'instruction'}
        rows = by_dispute(result['rows'], tuple(key for key in FIELDS[step] if key not in optional))
        if rows.keys() != set(issues):
            raise ValueError(f'{step} must respond once to each assigned dispute')
        for row in rows.values():
            if step == 'questions' and row['target'].strip() not in inputs['opposing_opening']:
                raise ValueError('question must quote the opposing opening verbatim')
            if step == 'review':
                if (row['decision'], row['target']) not in {('accept', 'none'), ('revise', 'bull'), ('revise', 'bear')}:
                    raise ValueError('review decision and target are inconsistent')
                if row['decision'] == 'revise' and not row['instruction'].strip():
                    raise ValueError('review revision needs a concrete instruction')

    def open(self, state, role):
        result, rows = self.turn('opening', role, {'facts': self.brief['facts'], 'issues': list(self.issues.values())},
                                 self.issues)
        name = progress.OPENINGS[role]
        opening = '\n\n'.join(
            f'## {issue}\n\n{row["position"]}\n\n依据 {row["source_locator"]}'
            f'\n\n反证 {row["counterevidence"]}\n\n改判条件 {row["change_trigger"]}'
            for issue, row in rows.items())
        self.publish(role, 'waiting', [name], '独立预测已封存', result, text=(name, opening))
        return {}

    def publish(self, role, status, names, note, result, *, text=None, data=None):
        with self.lock:
            record = inspect(self.root)['roles'][role]
            if record['status'] == status and set(names) <= {item['path'] for item in record['artifacts']}:
                if record['integrity_issues']:
                    raise ValueError('recorded debate submission changed: ' + role)
                return
            if record['status'] != 'running':
                checkpoint(self.root, role, 'running', [], '恢复已收到的提交', result['agent_id'])
            if text:
                name, content = text
                (self.root / name).write_text(content + '\n', encoding='utf-8')
            if data:
                name, content = data
                save(self.root / name, content)
            checkpoint(self.root, role, status, names, note, result['agent_id'])

    def question(self, state, role):
        roles = inspect(self.root)['roles']
        if ready(self.root, roles, role) not in {'questions', 'replies'}:
            raise ValueError('opposing opening is not ready')
        result, _ = self.turn('questions', role,
                              {'issues': list(self.issues.values()), 'opposing_opening': self.read(progress.OPENINGS[opposing_role(role)])},
                              self.issues, roles[role]['agent_id'])
        self.publish(role, 'waiting', [progress.OPENINGS[role], QUESTIONS[role]], '已提交引用对手原话的质询',
                     result, data=(QUESTIONS[role], result['rows']))
        return {}

    def reply(self, state, role):
        roles = inspect(self.root)['roles']
        if ready(self.root, roles, role) != 'replies':
            raise ValueError('opposing questions are not ready')
        sources = {key: value['description'] for key, value in self.sources.items()}
        result, rows = self.turn('replies', role, {'questions': self.read(QUESTIONS[opposing_role(role)]),
                                                  'available_sources': sources},
                                 self.issues, roles[role]['agent_id'])
        name = progress.DEBATE_OUTPUTS[role]
        text = '\n\n'.join(f'## {issue}\n\n{row["response"]}\n\n{row["position_after"]}'
                            for issue, row in rows.items())
        self.publish(role, 'complete', [progress.OPENINGS[role], QUESTIONS[role], REPLIES[role], name],
                     '已直接回复对手并登记改判条件', result, text=(name, text), data=(REPLIES[role], result['rows']))
        return {}

    def collect(self, state):
        if (self.root / 'debate-evidence.json').exists():
            return {}
        requests = []
        for role in SIDES:
            for issue, row in replies(self.root, role).items():
                if not row['evidence_id'] and not row['request_reason']:
                    continue
                key = row['evidence_id']
                item = self.sources.get(key)
                response = {'dispute_id': issue, 'role': role, 'source': key,
                            'request': row['request_reason'], 'status': 'unavailable'}
                if item:
                    try:
                        lines = read_file(self.root, item['path'])[1].splitlines()
                    except (OSError, ValueError):
                        lines = []
                    first, last = item['first_line'], item['last_line']
                    if last <= len(lines):
                        response.update(status='retrieved', file=item['path'], first_line=first, last_line=last,
                                        excerpt='\n'.join(lines[first - 1:last])[:12000])
                requests.append(response)
                self.event(f'{progress.LABELS[role]}请求补证：{row["request_reason"]}。'
                           + ('已定位到指定材料。' if response['status'] == 'retrieved' else '可用资料中未找到。'))
        save(self.root / 'debate-evidence.json', {'requests': requests})
        return {}

    def review(self, state):
        cycle = state['cycle']
        session = None
        if cycle:
            session = self.read('debate-review-pass-0.json')['agent_id']
            inputs = {'prior_review': self.read('debate-review-pass-0.json')['rows'],
                      'revisions': [self.read(name) for side in SIDES.values()
                                    if (self.root / (name := f'{side}-revision.json')).exists()]}
        else:
            inputs = {'facts': self.brief['facts'], 'issues': list(self.issues.values()),
                      'submissions': {name: self.read(name) for role in SIDES
                                      for name in (progress.OPENINGS[role], QUESTIONS[role], REPLIES[role])},
                      'retrieved': self.read('debate-evidence.json')}
        result, rows = self.turn('review', 'reviewer', inputs, self.issues, session, f'review-{cycle}')
        if result['agent_id'] in {record.get('agent_id') for record in inspect(self.root)['roles'].values()}:
            raise ValueError('debate reviewer must be independent of every research role')
        save(self.root / f'debate-review-pass-{cycle}.json', result)
        decision = 'revise' if any(row['decision'] == 'revise' for row in rows.values()) else 'accept'
        self.event(f'独立复核第 {cycle + 1} 次判定：' + ('退回指定争点。' if decision == 'revise' else '通过本轮辩论。'))
        return {'decision': decision}

    def revise(self, state):
        prior = self.read('debate-review-pass-0.json')['rows']
        evidence = self.read('debate-evidence.json')
        for role, side in SIDES.items():
            assigned = [row for row in prior if row['target'] == side]
            if not assigned:
                continue
            name = f'{side}-revision.json'
            self.event(f'自动转交给{progress.LABELS[role]}：{assigned[0]["instruction"]}', '等待被退回的争点补答')
            record = inspect(self.root)['roles'][role]
            result, _ = self.turn('revision', role, {'review': assigned, 'retrieved': evidence},
                                  {row['dispute_id'] for row in assigned}, record['agent_id'])
            names = [item['path'] for item in record['artifacts'] if item['path'] != name] + [name]
            self.publish(role, 'complete', names, '已提交独立复核要求的补答', result,
                         data=(name, result['rows']))
        return {'cycle': 1}

    def finish(self, state):
        records, lines = [], ['# 多空交锋', '']
        for issue in self.issues:
            lines += [f'## {self.issues[issue]["topic"]}', '']
            for role, side in SIDES.items():
                opponent = opposing_role(role)
                question = next(row['question'] for row in self.read(QUESTIONS[role]) if row['dispute_id'] == issue)
                reply = replies(self.root, opponent)[issue]
                records.append(dict(dispute_id=issue, **{'from': side}, to=SIDES[opponent],
                                    question=question, response=reply['response'], concession=reply['concession'],
                                    evidence=[progress.OPENINGS[role], progress.DEBATE_OUTPUTS[opponent]]))
                lines += [f'**{progress.LABELS[role]}质询**　{question}', '', f'**答复**　{reply["response"]}', '',
                          f'**承认的限制**　{reply["concession"]}', '', f'**改判条件**　{reply["change_trigger"]}', '']
        check_transcript(self.root, inspect(self.root)['roles'], set(self.issues), records)
        save(self.root / 'debate-transcript.json', records)
        links = [BRIEF, 'debate-evidence.json', 'debate-review-pass-0.json']
        if state['cycle']:
            links += ['debate-review-pass-1.json', *(name for side in SIDES.values()
                                                     if (self.root / (name := f'{side}-revision.json')).exists())]
        lines += [' · '.join(f'[{name}]({name})' for name in links)]
        (self.root / 'cross-examination.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
        if inspect(self.root)['progress']['stage'] == 'debate':
            if state['decision'] == 'accept':
                update_progress(self.root, 'stage', stage='valuation', note='多空交锋经独立复核通过',
                                next_action='财务角色复算受影响的假设，Leader 整理正式报告')
            else:
                update_progress(self.root, 'stage', stage='blocked', note='补答后的辩论仍被独立复核退回',
                                next_action='查看复核意见，补充新证据后再安排修订')
        return {}

    def graph(self, saver):
        graph = StateGraph(DebateState)
        graph.add_node('collect_evidence', self.collect)
        graph.add_node('independent_review', self.review)
        graph.add_node('targeted_revision', self.revise)
        graph.add_node('finish', self.finish)
        previous = START
        for step, action in (('opening', self.open), ('questions', self.question), ('replies', self.reply)):
            nodes = []
            for role, side in SIDES.items():
                name = f'{side}_{step}'
                graph.add_node(name, partial(action, role=role))
                graph.add_edge(previous, name)
                nodes.append(name)
            join = f'{step}_complete'
            graph.add_node(join, lambda state: {})
            graph.add_edge(nodes, join)
            previous = join
        graph.add_edge(previous, 'collect_evidence')
        graph.add_edge('collect_evidence', 'independent_review')
        graph.add_conditional_edges('independent_review',
                                    lambda s: 'targeted_revision' if s['decision'] == 'revise' and not s['cycle'] else 'finish',
                                    ['targeted_revision', 'finish'])
        graph.add_edge('targeted_revision', 'independent_review')
        graph.add_edge('finish', END)
        return graph.compile(checkpointer=saver)


def run_live_debate(directory, *, resume=False, worker=codex_turn):
    root = Path(directory).resolve()
    if not (root / 'run.json').is_file():
        raise ValueError('initialize a research run before dispatching the debate')
    with closing(sqlite3.connect(root / '.debate-graph.lock', timeout=0)) as lock:
        try:
            lock.execute('BEGIN IMMEDIATE')
        except sqlite3.OperationalError as exc:
            raise ValueError('another process owns the live debate') from exc
        debate = Debate(root, worker)
        manifest_hash = digest(root / BRIEF)
        config = {'configurable': {'thread_id': 'berkshire-live-debate'}, 'max_concurrency': 2}
        with tracing_context(enabled=False), SqliteSaver.from_conn_string(str(root / '.debate-graph' / 'state.sqlite3')) as saver:
            graph = debate.graph(saver)
            snapshot = graph.get_state(config)
            if resume:
                if not snapshot.values or snapshot.values['brief_hash'] != manifest_hash:
                    raise ValueError('the debate checkpoint is missing or the brief changed')
                initial = None
            else:
                if snapshot.values:
                    raise ValueError('the debate already has a checkpoint; use --resume')
                state = inspect(root)
                if state['progress'].get('debate_protocol', 0) < 4 or state['progress']['stage'] not in {'research', 'debate'}:
                    raise ValueError('live debate requires a protocol 4 research run ready for debate')
                if any(state['roles'][role]['status'] != 'pending' for role in SIDES):
                    raise ValueError('start LangGraph before the manual debate has dispatched workers')
                if state['progress']['stage'] == 'research':
                    update_progress(root, 'stage', stage='debate', note='LangGraph 接管多空调度',
                                    next_action='并行派出两位辩手，封存独立预测')
                initial = {'brief_hash': manifest_hash, 'cycle': 0}
            result = graph.invoke(initial, config, durability='sync') if initial is not None or snapshot.next else snapshot.values
        output = {'scope': 'debate', 'status': 'COMPLETE' if result['decision'] == 'accept' else 'BLOCKED',
                  'revision_rounds': result['cycle'], 'stage': inspect(root)['progress']['stage'],
                  'dashboard': str(root / 'progress.html'), 'transcript': str(root / 'cross-examination.md'),
                  'review': str(root / f'debate-review-pass-{result["cycle"]}.json')}
        save(root / 'debate-graph-result.json', output)
        return output
