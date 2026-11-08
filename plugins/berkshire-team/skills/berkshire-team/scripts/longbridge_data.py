"""Normalize saved public Longbridge MCP responses; never connects or trades."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re


def unwrap(data):
    if not isinstance(data, dict) or 'content' not in data:
        return data
    if data.get('isError'):
        raise ValueError('Longbridge returned an error')
    if data.get('structuredContent') is not None:
        return data['structuredContent']
    blocks = [x['text'] for x in data['content'] if x.get('type') == 'text']
    if len(blocks) != 1:
        raise ValueError('expected exactly one JSON text block')
    return json.loads(blocks[0])


def numeric(value):
    if value is None or value == '':
        return None
    if isinstance(value, bool):
        raise ValueError('boolean is not financial data')
    try:
        d = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError('non-numeric financial value') from exc
    if not d.is_finite():
        raise ValueError('non-finite financial value')
    return str(value)


def normalize(data, kind, symbol, retrieved_at, report_type='af'):
    if not re.fullmatch(r'[A-Z0-9][A-Z0-9.\-]*\.(US|HK|SH|SZ|SG)', symbol):
        raise ValueError('expected a canonical security symbol, e.g. AAPL.US')
    timestamp = datetime.fromisoformat(retrieved_at.replace('Z', '+00:00'))
    if timestamp.tzinfo is None:
        raise ValueError('retrieved_at requires a timezone')
    payload = unwrap(data)
    out = dict(provider='Longbridge', symbol=symbol, retrieved_at=retrieved_at,
               status='FETCHED_UNVERIFIED', origin_group='longbridge',
               publication_date=None, rows=[], warnings=[])
    if kind == 'quote':
        if not isinstance(payload, list):
            raise ValueError('expected quote array')
        for index, entry in enumerate(payload):
            if entry.get('symbol') != symbol:
                continue
            out['rows'].append(dict(symbol=symbol, price=numeric(entry.get('last_done')),
                                    timestamp=entry.get('timestamp'),
                                    locator=f'$[{index}]', raw=entry))
    elif kind == 'financial-report':
        if not isinstance(payload, dict) or not isinstance(payload.get('list'), dict):
            raise ValueError('expected financial_report indicator envelope; preserve alternate raw shape')
        if payload.get('report') != report_type:
            raise ValueError('returned report type differs from request')
        out['report_type'] = report_type
        out['warnings'].append('Amounts retain upstream units; ratios and yoy need field-level interpretation.')
        for statement, body in payload['list'].items():
            if statement not in ('i_s', 'b_s', 'c_f') or not isinstance(body, dict):
                continue
            for i, indicator in enumerate(body.get('indicators', [])):
                for j, account in enumerate(indicator.get('accounts', [])):
                    for k, value in enumerate(account.get('values', [])):
                        row = dict(statement=statement, field=account.get('field'),
                                   name=account.get('name'), indicator=indicator.get('title'),
                                   currency=indicator.get('currency'), year=value.get('year'),
                                   period=value.get('period'), period_end_raw=value.get('fp_end'),
                                   value=numeric(value.get('value')), unit=None,
                                   locator=f'$.list.{statement}.indicators[{i}].accounts[{j}].values[{k}]',
                                   raw=value)
                        out['rows'].append(row)
        out['periods_by_statement'] = {
            s: sorted({str(r['period']) for r in out['rows'] if r['statement'] == s and r['period'] is not None})
            for s in ('i_s', 'b_s', 'c_f')
        }
    else:
        raise ValueError('unsupported normalization kind')
    if not out['rows'] or not any(r.get('value', r.get('price')) is not None for r in out['rows']):
        out['status'] = 'EMPTY'
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    n = sub.add_parser('normalize')
    n.add_argument('--kind', choices=['financial-report', 'quote'], required=True)
    n.add_argument('--symbol', required=True)
    n.add_argument('--report-type', default='af', choices=['af', 'saf', 'q1', 'q2', 'q3', 'qf'])
    n.add_argument('--retrieved-at', required=True)
    n.add_argument('--input', type=Path, required=True)
    n.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.input.resolve() == a.output.resolve() or a.output.exists():
        p.error('output must be a new file distinct from raw input')
    try:
        out = normalize(json.loads(a.input.read_text(encoding='utf-8')), a.kind,
                        a.symbol, a.retrieved_at, a.report_type)
    except (ValueError, TypeError, KeyError) as exc:
        p.error(str(exc))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(status=out['status'], rows=len(out['rows']), output=str(a.output)), ensure_ascii=False))
    return 2 if out['status'] == 'EMPTY' else 0


if __name__ == '__main__':
    raise SystemExit(main())
