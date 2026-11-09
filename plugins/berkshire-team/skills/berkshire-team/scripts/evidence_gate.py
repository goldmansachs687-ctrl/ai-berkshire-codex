"""Validate an explicit evidence ledger; never infer full coverage from Markdown."""
import argparse
import json
import re
from audit_core import evaluate


def audit(ledger):
    if not isinstance(ledger, dict):
        raise ValueError('ledger must be an object')
    required = ledger.get('required_claims')
    claims = ledger.get('claims')
    if not isinstance(required, list) or not required or not all(isinstance(x, str) and x for x in required):
        raise ValueError('required_claims must be a nonempty list of claim IDs')
    if not isinstance(claims, list):
        raise ValueError('claims must be an array')
    missing = []
    rows = []
    for claim in claims:
        if not isinstance(claim, dict):
            raise ValueError('claim must be an object')
        row = dict(claim)
        if claim.get('kind', 'fact') in ('fact', 'derived'):
            for key in ('metric', 'unit', 'currency', 'period', 'basis'):
                if not isinstance(claim.get(key), str) or not claim[key].strip():
                    missing.append({'id': claim.get('id'), 'reason': f'missing {key}'})
            observations = claim.get('observations', [])
            if not isinstance(observations, list) or len(observations) > 2:
                raise ValueError('observations must be an array with at most two normalized records')
            # Do not accept legacy fetched_* fields as a bypass of source metadata.
            for key in ('fetched_value', 'fetched_value2', 'fetched_source', 'fetched_source2',
                        'origin_group', 'origin_group2', 'fetched_source_sha256', 'fetched_source_sha2562'):
                row.pop(key, None)
            for index, obs in enumerate(observations):
                if not isinstance(obs, dict):
                    raise ValueError('observation must be an object')
                suffix = '' if index == 0 else '2'
                for key in ('source', 'locator', 'accessed_at', 'origin_group'):
                    if not isinstance(obs.get(key), str) or not obs[key].strip():
                        missing.append({'id': claim.get('id'), 'reason': f'observation lacks {key}'})
                for key in ('metric', 'unit', 'currency', 'period', 'basis'):
                    if obs.get(key) != claim.get(key):
                        missing.append({'id': claim.get('id'), 'reason': f'observation {key} not normalized to claim'})
                if claim.get('kind') == 'derived' and not obs.get('calculation'):
                    missing.append({'id': claim.get('id'), 'reason': 'derived claim lacks source-to-result calculation'})
                row['fetched_value' + suffix] = obs.get('value')
                row['fetched_source' + suffix] = obs.get('source')
                row['origin_group' + suffix] = obs.get('origin_group')
                if 'source_sha256' in obs:
                    digest = obs['source_sha256']
                    if not isinstance(digest, str) or not re.fullmatch('[0-9a-fA-F]{64}', digest):
                        missing.append({'id': claim.get('id'), 'reason': 'invalid source_sha256'})
                    else:
                        row['fetched_source_sha256' + suffix] = digest
        rows.append(row)
    result = evaluate(rows, required)
    result['incomplete_items'].extend(missing)
    result['incomplete_count'] += len(missing)
    if missing and result['verdict'] == 'PASS':
        result['verdict'] = 'INCOMPLETE'
    result['scope'] = 'declared critical claims and supplied provenance; not source authenticity or full-report approval'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', required=True)
    parser.add_argument('--output')
    args = parser.parse_args()
    try:
        with open(args.ledger, encoding='utf-8') as handle:
            result = audit(json.load(handle))
        output = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as handle:
                handle.write(output + '\n')
        print(output)
        return {'PASS': 0, 'FAIL': 1, 'INCOMPLETE': 2}[result['verdict']]
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({'verdict': 'INCOMPLETE', 'error': str(exc)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
