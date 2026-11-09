"""Read-only delivery acceptance. COMPLETE=0, LIMITED=2, BLOCKED=1."""
import argparse
import json
import re
from pathlib import Path
from evidence_gate import audit
from research_run import ROLES, inspect
from delivery_dependencies import binding, read_file, strict_json, strings
from delivery_model import check_model

EXIT_CODES = {'COMPLETE': 0, 'LIMITED': 2, 'BLOCKED': 1}
BOUNDARY = ('Reviewer IDs do not prove independent thinking; files do not prove adequate counterevidence; '
            'valid evidence metadata does not prove source authenticity or correct interpretation. '
            'Scope completeness and economic assumptions require human/AI judgment.')


def accept(directory):
    root = Path(directory).resolve()
    issues, dependencies, model_checks = [], [], []
    gate = None
    def issue(check, artifact, reason, repair, severity='blocking'):
        issues.append(dict(check=check, artifact=artifact, reason=str(reason), repair=repair, severity=severity))
    def load(name):
        return read_file(root, name)[2]
    def finish():
        status = 'BLOCKED' if any(i['severity'] == 'blocking' for i in issues) else 'LIMITED' if issues else 'COMPLETE'
        return dict(schema_version=1, status=status, exit_code=EXIT_CODES[status], issues=issues,
                    evidence_gate=gate, model_checks=model_checks, dependencies=dependencies, boundary=BOUNDARY)
    try:
        state = strict_json((root/'run.json').read_text(encoding='utf-8'))
        if not isinstance(state, dict) or not isinstance(state.get('roles'), dict):
            raise ValueError('run.json requires roles object')
        contract = load('delivery.json')
        if not isinstance(contract, dict) or contract.get('schema_version') != 1:
            raise ValueError('delivery.json requires schema_version=1 object')
    except (OSError, ValueError, TypeError, KeyError) as exc:
        issue('contract', 'run.json / delivery.json', exc, 'Provide valid run state and explicit delivery scope; preserve original evidence requirements.')
        return finish()
    starting_binding = None
    try:
        starting_binding = binding(root, state)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, SyntaxError) as exc:
        issue('dependencies', 'delivery.json', exc, 'Restore nonempty valid files and declared references before independent review.')
    try:
        ledger = load('evidence.json')
        gate = audit(ledger)  # Always audit current bytes; never consume a handwritten passed flag.
    except (OSError, ValueError, TypeError, KeyError) as exc:
        issue('evidence', 'evidence.json', exc, 'Repair the current evidence ledger and source metadata.')
        return finish()
    passed = {item['id'] for item in gate['pass_items']}
    try:
        applicable = strings(contract.get('applicable_roles'), 'applicable_roles')
        if not set(applicable) <= set(ROLES[:-1]):
            raise ValueError('unknown or review role listed as researcher')
        kind = contract.get('research_type')
        if kind not in ('full', 'qualitative_brief'):
            raise ValueError('research_type must be full or qualitative_brief')
        if kind == 'full' and set(applicable) != set(ROLES[:-1]):
            raise ValueError('full research requires all four research roles')
        if kind == 'qualitative_brief' and not contract.get('scope_reason'):
            raise ValueError('brief requires scope_reason explaining applicable roles and conclusion boundaries')
        participants = strings(contract.get('participants'), 'participants')
        inspected = inspect(root)
        for role in applicable:
            record = inspected['roles'].get(role, {})
            if not record.get('resumable_complete'):
                issue('workflow.' + role, 'run.json', record.get('integrity_issues') or 'role incomplete or no actual artifacts', 'Complete the applicable role and checkpoint its current deliverable.')
            if not record.get('agent_id') or record['agent_id'] not in participants:
                issue('workflow.identity', 'run.json', role + ' lacks a participant ID', 'Record actual researcher IDs, including author/coordinator/model author in participants.')
            for artifact in record.get('artifacts', []):
                read_file(root, artifact['path'])
        # Any recorded participant, even a non-applicable role, participates in independence checks.
        for role, record in state['roles'].items():
            if role != 'independent_review' and record.get('agent_id') and record['agent_id'] not in participants:
                raise ValueError('participants omits recorded researcher: ' + role)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, SyntaxError) as exc:
        issue('workflow', 'run.json / delivery.json', exc, 'Repair role scope, IDs, checkpoints and deliverable files.')
        participants = contract.get('participants', [])
    try:
        current_binding = binding(root, state)
        dependencies = current_binding['dependencies']
        recorded = state['roles'].get('independent_review', {})
        if recorded.get('delivery_binding') != current_binding:
            issue('review.binding', 'run.json', 'review missing or stale: content/dependency list/research state changed', 'Obtain a fresh independent review of current artifacts, then explicitly checkpoint it.')
    except (OSError, ValueError, TypeError, KeyError, AttributeError, SyntaxError) as exc:
        issue('dependencies', 'delivery.json', exc, 'Restore valid nonempty required files and recursive references; then obtain fresh review.')
    try:
        challenge_name = contract['challenges']
        challenge = load(challenge_name)
        questions = challenge.get('questions')
        if not isinstance(questions, list) or not questions:
            raise ValueError('question/response records required')
        for question in questions:
            if not question.get('question') or not question.get('response'):
                raise ValueError('each challenge needs question and response')
            for name in strings(question.get('evidence'), 'challenge evidence'):
                read_file(root, name)
                if name not in {d['path'] for d in dependencies}:
                    raise ValueError('challenge evidence must be listed in dependencies: ' + name)
        disputes = challenge.get('disagreements')
        if not isinstance(disputes, list):
            raise ValueError('disagreements must be an explicit list')
        if not disputes and not challenge.get('no_material_disagreements_reason'):
            raise ValueError('record why no material disagreement remains')
        for dispute in disputes:
            if type(dispute.get('material')) is not bool:
                raise ValueError('each disagreement must declare materiality')
            if dispute.get('status') != 'resolved' or not dispute.get('resolution'):
                raise ValueError('unresolved disagreement: ' + str(dispute.get('question', 'unspecified')))
            for name in strings(dispute.get('evidence'), 'resolution evidence'):
                read_file(root, name)
                if name not in {d['path'] for d in dependencies}:
                    raise ValueError('resolution evidence must be listed in dependencies: ' + name)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        issue('challenges', contract.get('challenges', 'delivery.json'), exc, 'Record challenges, answers, material disagreements and supported reconciliation; link evidence in dependencies.')
    try:
        minimum = strings(contract.get('minimum_claims'), 'minimum_claims')
        used = strings(contract.get('conclusion_claims'), 'conclusion_claims', False)
        if not set(minimum) <= passed or not set(used) <= passed:
            raise ValueError('minimum or conclusion facts have not passed the current evidence gate')
        if not set(minimum + used) <= set(ledger['required_claims']):
            raise ValueError('minimum/conclusion facts must remain in required_claims')
        if gate['verdict'] == 'FAIL':
            raise ValueError('evidence FAIL: ' + json.dumps(gate['fail_items'], ensure_ascii=False))
        limitations = contract.get('limitations', [])
        if not isinstance(limitations, list):
            raise ValueError('limitations must be an array')
        claims = {c['id']: c for c in ledger['claims']}
        missing_ids = {i['id'] for i in gate['incomplete_items']}
        gap_ids = [item['claim_id'] for item in limitations]
        if len(gap_ids) != len(set(gap_ids)) or set(gap_ids) != missing_ids:
            raise ValueError('limitations must match exactly the current incomplete claim IDs')
        report = read_file(root, 'report.md')[1]
        for item in gate['incomplete_items']:
            if item['reason'] != 'reported value unknown':
                raise ValueError('blocking INCOMPLETE: ' + str(item))
        for gap in limitations:
            identifier = gap['claim_id']
            if identifier in minimum + used or identifier not in ledger['required_claims']:
                raise ValueError('gap may not support minimum/major conclusions and must remain required')
            claim = claims[identifier]
            if claim.get('kind', 'fact') not in ('fact', 'derived') or claim.get('reported_value') is not None:
                raise ValueError('gap must remain an explicitly unknown fact')
            if gap.get('reason') != 'objective_unavailable':
                raise ValueError('only objective unavailability can permit limited delivery')
            strings(gap.get('attempted_sources'), 'attempted_sources')
            for field in ('impact', 'prohibited_conclusions', 'disclosure'):
                if not isinstance(gap.get(field), str) or not gap[field].strip() or gap[field] not in report:
                    raise ValueError('report must include gap ' + field)
            issue('evidence.limited', 'evidence.json#' + identifier, gap['impact'], gap['prohibited_conclusions'], 'limitation')
        if gate['pass_count'] == 0:
            raise ValueError('at least one audited factual claim is mandatory')
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        issue('evidence', 'evidence.json / delivery.json', exc, 'Resolve discrepancies or unsupported facts; only explicitly unavailable unused values qualify as LIMITED.')
    try:
        valuation = contract['valuation']
        if type(valuation.get('required')) is not bool:
            raise ValueError('explicit valuation.required boolean required')
        if contract.get('research_type') == 'full' and not valuation['required']:
            raise ValueError('full company research requires valuation; use a scoped qualitative_brief for reports without valuation conclusions')
        if valuation['required']:
            manifest = load(valuation['manifest'])
            model_checks = check_model(root, manifest, ledger, passed)
        else:
            if not valuation.get('reason'):
                raise ValueError('explain why this report makes no quantitative valuation conclusion')
            report_text = read_file(root, 'report.md')[1]
            if re.search(r'(?:DCF|SOTP|估值|目标价|内在价值|合理价值|fair value|price target|intrinsic value)[^\n]{0,100}(?:[0-9]|[$￥¥])', report_text, re.I):
                raise ValueError('valuation language with a number requires a model; qualitative scope declaration is insufficient')
            if valuation.get('manifest'):
                raise ValueError('a declared valuation manifest requires valuation.required=true')
    except (OSError, ValueError, TypeError, KeyError, AttributeError, SyntaxError, ArithmeticError, IndexError) as exc:
        issue('model', contract.get('valuation', {}).get('manifest', 'delivery.json'), exc, 'Supply valid model/input/output artifacts, traceable inputs and reproducible arithmetic checks.')
    try:
        record = state['roles'].get('independent_review', {})
        review = load('review.json')
        reviewer = record.get('agent_id', '').strip()
        if record.get('status') != 'complete' or not reviewer or reviewer in participants:
            raise ValueError('independent reviewer must be complete and distinct from every participant')
        if review.get('reviewer_id') != reviewer:
            raise ValueError('review.json reviewer differs from checkpoint ID')
        if not record.get('note', '').strip():
            raise ValueError('review checkpoint needs a substantive note')
        checks = review.get('checks')
        if not isinstance(checks, dict) or any(not isinstance(checks.get(k), str) or not checks[k].strip()
                for k in ('workflow', 'evidence', 'model', 'scope', 'counterevidence')):
            raise ValueError('review lacks workflow/evidence/model/scope/counterevidence records')
        expected = 'LIMITED' if contract.get('limitations') else 'COMPLETE'
        if review.get('decision') != expected:
            raise ValueError('review decision must acknowledge intended delivery scope: ' + expected)
        acknowledged = strings(review.get('acknowledged_limitations', []), 'acknowledged_limitations', False)
        if set(acknowledged) != {g['claim_id'] for g in contract.get('limitations', [])}:
            raise ValueError('review must acknowledge each limitation')
        review_state = inspect(root)['roles']['independent_review']
        if not review_state['resumable_complete']:
            raise ValueError('review artifacts not current: ' + str(review_state['integrity_issues']))
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        issue('review', 'review.json / review.md / run.json', exc, 'Obtain actual independent review with complete records and checkpoint current content.')
    if starting_binding is not None:
        try:
            if binding(root, strict_json((root/'run.json').read_text(encoding='utf-8'))) != starting_binding:
                issue('snapshot', 'run directory', 'inputs changed during acceptance', 'Rerun against stable artifacts; obtain a fresh review if content changed.')
        except (OSError, ValueError, TypeError, KeyError, AttributeError, SyntaxError) as exc:
            issue('snapshot', 'run directory', exc, 'Restore stable valid artifacts and re-review.')
    return finish()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--json', action='store_true', help='machine-readable result only')
    args = parser.parse_args()
    try:
        result = accept(args.run)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, SyntaxError, IndexError, RecursionError) as exc:
        result = dict(status='BLOCKED', exit_code=1, issues=[dict(check='format', artifact=args.run,
                      reason=str(exc), repair='Repair invalid schema or dependencies before review.', severity='blocking')])
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result['status'] + ' (exit ' + str(result['exit_code']) + ')')
        for item in result['issues']:
            print(f"[{item['check']}] {item['artifact']}: {item['reason']}\n  Repair: {item['repair']}")
        print(BOUNDARY)
    return result['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
