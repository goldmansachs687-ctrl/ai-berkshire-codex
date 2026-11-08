"""Fail-closed numeric checks. This verifies supplied evidence, not its authenticity."""
from decimal import Decimal, InvalidOperation


def number(value):
    if value is None or isinstance(value, bool):
        raise ValueError('missing or boolean numeric value')
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError('invalid numeric value') from exc
    if not result.is_finite():
        raise ValueError('non-finite numeric value')
    return result


def evaluate(results, required_ids=None):
    if not isinstance(results, list):
        raise ValueError('results must be an array')
    passed, failed, missing, excluded = [], [], [], []
    seen = set()
    for row in results:
        if not isinstance(row, dict):
            failed.append({'reason': 'item must be an object'})
            continue
        item = {k: row.get(k) for k in ('id', 'label', 'line_number')}
        identifier = row.get('id')
        if not isinstance(identifier, (int, str)) or isinstance(identifier, bool) or identifier == '' or identifier in seen:
            failed.append(dict(item, reason='missing, invalid or duplicate id'))
            continue
        seen.add(identifier)
        kind = row.get('kind', 'fact')
        if kind in ('assumption', 'judgment'):
            if row.get('rationale'):
                excluded.append(dict(item, reason='not an externally verifiable historical fact'))
            else:
                missing.append(dict(item, reason='assumption requires rationale'))
            continue
        if kind not in ('fact', 'derived'):
            failed.append(dict(item, reason='unknown claim kind'))
            continue
        if row.get('reported_value') is None:
            missing.append(dict(item, reason='reported value unknown'))
            continue
        try:
            reported = number(row.get('reported_value'))
            tolerance = number(row.get('tolerance_pct', 1)) / 100
            if tolerance < 0 or tolerance > Decimal('.05'):
                raise ValueError('tolerance must be between 0 and 5 percent; larger differences need reconciliation')
        except ValueError as exc:
            failed.append(dict(item, reason=str(exc)))
            continue
        evidence = []
        invalid = None
        for suffix in ('', '2'):
            value = row.get('fetched_value' + suffix)
            if value is None:
                continue
            try:
                fetched = number(value)
            except ValueError as exc:
                invalid = str(exc)
                break
            source = row.get('fetched_source' + suffix)
            if not isinstance(source, str) or not source.strip():
                missing.append(dict(item, reason='numeric evidence has no source'))
                invalid = 'incomplete'
                break
            difference = abs(reported - fetched)
            # Zero is a real observation. No relative-error division by zero.
            matches = difference == 0 if reported == 0 else difference / abs(reported) <= tolerance
            evidence.append({'source': source, 'value': str(fetched), 'matches': matches})
        if invalid:
            if invalid != 'incomplete':
                failed.append(dict(item, reason=invalid))
        elif not evidence:
            missing.append(dict(item, reason='no fetched value'))
        elif not all(e['matches'] for e in evidence):
            failed.append(dict(item, reason='source discrepancy requires reconciliation', evidence=evidence))
        elif row.get('require_second_source') and len(evidence) < 2:
            missing.append(dict(item, reason='required second source unavailable'))
        elif row.get('require_independent_sources') and (
            len(evidence) < 2 or not row.get('origin_group') or not row.get('origin_group2')
            or row['origin_group'] == row['origin_group2']
        ):
            missing.append(dict(item, reason='independent source lineage not established'))
        else:
            passed.append(dict(item, evidence=evidence))
    # Required claims cannot be silently dropped or reclassified as assumptions.
    fact_ids = {r.get('id') for r in results if isinstance(r, dict)
                and isinstance(r.get('id'), (str, int)) and r.get('kind', 'fact') in ('fact', 'derived')}
    for identifier in required_ids or []:
        if identifier not in fact_ids:
            missing.append({'id': identifier, 'reason': 'required factual claim absent'})
    verdict = 'FAIL' if failed else 'INCOMPLETE' if missing or not passed else 'PASS'
    return {'verdict': verdict, 'scope': 'supplied numeric evidence only; not publication approval',
            'pass_count': len(passed), 'fail_count': len(failed), 'incomplete_count': len(missing),
            'excluded_count': len(excluded), 'warn_count': 0,
            'total': len(results), 'pass_items': passed, 'fail_items': failed,
            'incomplete_items': missing, 'excluded_items': excluded, 'warn_items': []}
