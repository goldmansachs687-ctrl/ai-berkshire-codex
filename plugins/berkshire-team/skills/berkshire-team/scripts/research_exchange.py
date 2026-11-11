"""Validate the handoff between actual debaters and bind their direct exchanges."""
import hashlib

from delivery_dependencies import read_file
from research_progress import DEBATERS, OPENINGS

QUESTIONS = dict(zip(DEBATERS, ('bull-questions.json', 'bear-questions.json')))
REPLIES = dict(zip(DEBATERS, ('bull-replies.json', 'bear-replies.json')))


def text_fields(record, fields):
    if not isinstance(record, dict) or any(
            not isinstance(record.get(key), str) or not record[key].strip() for key in fields):
        raise ValueError('debate record requires ' + ', '.join(fields))


def by_dispute(rows, fields):
    if not isinstance(rows, list) or not rows:
        raise ValueError('debate records must be a nonempty list')
    indexed = {}
    for row in rows:
        text_fields(row, ('dispute_id', *fields))
        issue = row['dispute_id']
        if issue in indexed:
            raise ValueError('duplicate debate record: ' + issue)
        indexed[issue] = row
    return indexed


def opposing_role(role):
    return next(other for other in DEBATERS if other != role)


def questions(root, role):
    name = QUESTIONS[role]
    rows = by_dispute(read_file(root, name)[2], ('target', 'question'))
    opponent_opening = read_file(root, OPENINGS[opposing_role(role)])[1]
    if any(row['target'].strip() not in opponent_opening for row in rows.values()):
        raise ValueError(name + ' must quote the opposing opening verbatim')
    return rows


def replies(root, role):
    rows = by_dispute(read_file(root, REPLIES[role])[2], (
        'response', 'concession', 'position_before', 'position_after', 'change_trigger', 'source_locator'))
    if rows.keys() != questions(root, opposing_role(role)).keys():
        raise ValueError(REPLIES[role] + ' must answer every received question')
    return rows


def file_hash(root, name):
    return hashlib.sha256(read_file(root, name)[0]).hexdigest()


def require_round(root, roles, names, field):
    for role, name in names.items():
        if not roles[role].get(field) or roles[role][field] != file_hash(root, name):
            raise ValueError('waiting for both unchanged debate submissions: ' + name)


def ready(root, roles, role):
    """Return the next handoff for a recorded debater before the Leader sends it."""
    record = roles[role]
    round_name = record.get('debate_round', 'opening')
    if record['status'] == 'waiting':
        round_name = 'replies' if record.get('questions_sha256') else 'questions'
    if round_name in {'questions', 'replies'}:
        require_round(root, roles, OPENINGS, 'opening_sha256')
    if round_name == 'replies':
        require_round(root, roles, QUESTIONS, 'questions_sha256')
    return round_name


def checkpoint_exchange(root, roles, role, status, artifacts, agent_id):
    record = roles[role]
    if status == 'running':
        if record.get('opening_sha256') and record.get('agent_id') != agent_id:
            raise ValueError('continue this debate with the agent that wrote the opening')
        record['debate_round'] = ready(root, roles, role)
        return
    if status not in {'waiting', 'complete'}:
        return
    round_name = record.get('debate_round')
    if status == 'complete' and round_name != 'replies':
        raise ValueError('both recorded question sets must be exchanged before completing debate')
    if status == 'waiting' and round_name not in {'opening', 'questions'}:
        raise ValueError('waiting requires an opening or a question submission')
    registered = {item['path']: item['sha256'] for item in artifacts}
    opening = OPENINGS[role]
    if registered.get(opening) != file_hash(root, opening):
        raise ValueError('checkpoint must include the unchanged ' + opening)
    if record.setdefault('opening_sha256', registered[opening]) != registered[opening]:
        raise ValueError(opening + ' changed after its first checkpoint')
    if round_name in {'questions', 'replies'}:
        require_round(root, roles, OPENINGS, 'opening_sha256')
        name = QUESTIONS[role]
        if registered.get(name) != file_hash(root, name):
            raise ValueError('checkpoint must include ' + name)
        questions(root, role)
        if record.setdefault('questions_sha256', registered[name]) != registered[name]:
            raise ValueError(name + ' changed after its first checkpoint')
    if status == 'complete':
        require_round(root, roles, QUESTIONS, 'questions_sha256')
        name = REPLIES[role]
        checksum = file_hash(root, name)
        if registered.get(name) != checksum:
            raise ValueError('checkpoint must include ' + name)
        if any(item['path'] == name and item['sha256'] != checksum for item in record['artifacts']):
            raise ValueError('preserve the first replies and record follow-up separately: ' + name)
        replies(root, role)


def check_transcript(root, roles, disputes, transcript):
    require_round(root, roles, OPENINGS, 'opening_sha256')
    require_round(root, roles, QUESTIONS, 'questions_sha256')
    for role, name in REPLIES.items():
        if {'path': name, 'sha256': file_hash(root, name)} not in roles[role]['artifacts']:
            raise ValueError('debate replies must match their recorded submission: ' + name)
    for side, role in zip(('bull', 'bear'), DEBATERS):
        asked = questions(root, role)
        answered = replies(root, opposing_role(role))
        recorded = by_dispute([row for row in transcript if row['from'] == side],
                              ('question', 'response', 'concession'))
        if recorded.keys() != disputes or asked.keys() != disputes:
            raise ValueError('each material dispute needs an original exchange in both directions')
        for issue, row in recorded.items():
            if (row['question'] != asked[issue]['question'] or
                    any(row[key] != answered[issue][key] for key in ('response', 'concession'))):
                raise ValueError('transcript differs from the original agent submissions: ' + issue)


def check_review_judgments(review, dispute_ids):
    judgments = by_dispute(review.get('debate_judgments'), (
        'strongest_evidence', 'directness', 'independent_judgment', 'assumption_impact', 'decision'))
    if judgments.keys() != dispute_ids:
        raise ValueError('review must assess every material debate dispute')
    for issue, judgment in judgments.items():
        if judgment['decision'] != 'accept':
            raise ValueError('independent reviewer requires debate revision: ' + issue)
