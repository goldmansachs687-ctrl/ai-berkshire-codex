"""Read-only AKShare/EdgarTools adapter with provenance and a workspace runtime."""
import argparse
import contextlib
from datetime import date, datetime, timezone
import hashlib
import importlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from uuid import uuid4


BASE_FORMS = ('10-K', '10-Q', '20-F', '6-K', '8-K')
FORMS = BASE_FORMS + tuple(value + '/A' for value in BASE_FORMS)


def iso_date(value):
    return date.fromisoformat(value).isoformat()


def identity_valid(value):
    return bool(isinstance(value, str) and re.search(r'[^\s@]+@[^\s@]+\.[^\s@]+', value)
                and '\n' not in value and '\r' not in value)


def redact(value):
    return re.sub(r'[^\s<>@]+@[^\s<>@]+', '[email redacted]', str(value))[:1200]


def runtime_config(workspace):
    path = Path(workspace).resolve() / '.berkshire/data-runtime.json'
    config = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    python = os.environ.get('BERKSHIRE_DATA_PYTHON') or config.get('python', '.runtime/market-data/bin/python')
    python = Path(python).expanduser()
    if not python.is_absolute():
        python = Path(workspace).resolve() / python
    identity = os.environ.get('EDGAR_IDENTITY') or config.get('edgar_identity', '')
    return python, identity


def validate_query(args):
    if args.command == 'doctor':
        return
    if not 1 <= args.limit <= 10000:
        raise ValueError('limit must be between 1 and 10000')
    if args.command == 'ak-prices':
        size = 5 if args.market == 'hk' else 6
        if not re.fullmatch(r'\d{' + str(size) + '}', args.symbol):
            raise ValueError(f'{args.market} requires an explicit {size}-digit local security code')
        if args.start > args.end:
            raise ValueError('start must not be after end')
        if date.fromisoformat(args.end) > date.today():
            raise ValueError('end must not be in the future')
        if args.source == 'sina' and args.market != 'hk':
            raise ValueError('Sina adapter currently supports HK only')
    elif args.command == 'ak-hk-financials':
        if not re.fullmatch(r'\d{5}', args.symbol):
            raise ValueError('HK financials require a 5-digit local security code')
    else:
        # SEC ticker or CIK, never silently convert HK codes to US tickers.
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9.\-]{0,19}|\d{1,10}', args.symbol):
            raise ValueError('SEC symbol must be a ticker or CIK')
        if args.command == 'edgar-text' and not re.fullmatch(r'\d{10}-\d{2}-\d{6}', args.accession):
            raise ValueError('invalid SEC accession number')


def frame_dataset(name, frame, limit):
    if frame is None:
        return {'name': name, 'row_count': 0, 'exported_rows': 0, 'truncated': False, 'columns': [], 'rows': []}
    if not frame.columns.is_unique:
        raise ValueError('duplicate source columns; cannot export without losing financial context')
    head = frame.head(limit)
    # pandas emits JSON null for missing cells, preserving a real zero as zero.
    rows = json.loads(head.to_json(orient='records', force_ascii=False, date_format='iso'))
    return {'name': name, 'row_count': len(frame), 'exported_rows': len(rows),
            'truncated': len(frame) > limit, 'columns': [str(x) for x in frame.columns],
            'row_index': json.loads(head.index.to_series().to_json(orient='values', date_format='iso')),
            'rows': rows}


def filter_filings(frame, as_of, accession=None, form=None):
    if 'filing_date' not in frame:
        raise ValueError('SEC response lacks filing_date')
    dates = frame['filing_date'].map(lambda x: iso_date(str(x)[:10]))
    result = frame.loc[dates <= as_of].copy()
    if form:
        if 'form' not in result:
            raise ValueError('SEC response lacks form')
        result = result.loc[result['form'] == form]
    if accession:
        column = 'accession_number' if 'accession_number' in result else 'accession_no'
        if column not in result:
            raise ValueError('SEC response lacks accession')
        result = result.loc[result[column] == accession]
    return result.sort_values('filing_date', ascending=False, kind='stable')


def sec_url(cik, accession):
    return f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace("-", "")}/{accession}-index.html'


def price_result(args, ak):
    function = 'stock_hk_hist' if args.market == 'hk' else 'stock_zh_a_hist'
    parameters = dict(symbol=args.symbol, period='daily', start_date=args.start.replace('-', ''),
                      end_date=args.end.replace('-', ''), adjust=args.adjust)
    date_column = '日期'
    if args.source == 'sina':
        function, date_column = 'stock_hk_daily', 'date'
        frame = getattr(ak, function)(symbol=args.symbol, adjust=args.adjust)
        if len(frame):
            if date_column not in frame:
                raise ValueError('price response lacks date column; schema changed')
            dates = frame[date_column].map(lambda x: iso_date(str(x)[:10]))
            frame = frame.loc[(dates >= args.start) & (dates <= args.end)].copy()
    else:
        frame = getattr(ak, function)(**parameters)
    dataset = frame_dataset('price_history_raw', frame, args.limit)
    # Validate the returned dates as well as the request; upstream filters can drift.
    if len(frame):
        if date_column not in frame:
            raise ValueError('price response lacks date column; schema changed')
        dates = frame[date_column].map(lambda x: iso_date(str(x)[:10]))
        if ((dates < args.start) | (dates > args.end)).any():
            raise ValueError('upstream returned price rows outside requested date range')
    source = ('https://quote.eastmoney.com/hk/' + args.symbol + '.html' if args.market == 'hk'
              else 'https://quote.eastmoney.com/')
    if args.source == 'sina':
        source = f'https://stock.finance.sina.com.cn/hkstock/quotes/{args.symbol}.html'
    return dict(datasets=[dataset], sources=[dict(source=source,
                locator=f'{function}, security={args.symbol}, dates={args.start}:{args.end}, adjust={args.adjust or "none"}',
                origin_group=f'{args.source}:prices:{args.market}:{args.symbol}')],
                dimensions=dict(currency='UNRESOLVED_VERIFY_SECURITY',
                                currency_hint='HKD' if args.market == 'hk' else 'CNY',
                                price_unit='currency_per_share', adjustment=args.adjust or 'none',
                                volume_unit='see upstream definition; not normalized'),
                upstream_api=function, warnings=['Verify trading currency and security type; market alone does not establish currency.',
                'Historical retrieval is not a live quote; use returned trading dates.',
                'Historical adjusted prices may reflect later corporate actions; use unadjusted prices for dated valuation.'])


def hk_financial_result(args, ak):
    function = 'stock_financial_hk_report_em'
    frame = getattr(ak, function)(stock=args.symbol, symbol=args.statement, indicator=args.frequency)
    # Keep original schema: the report can mix currencies, scales and non-additive KPIs.
    return dict(datasets=[frame_dataset('hk_financial_report_raw', frame, args.limit)],
                sources=[dict(source=f'https://emweb.securities.eastmoney.com/PC_HKF10/FinancialAnalysis/index?code={args.symbol}',
                              locator=f'{function}, {args.statement}, {args.frequency}',
                              origin_group=f'issuer-disclosures:HK:{args.symbol}')],
                dimensions=dict(currency='UNRESOLVED_READ_SOURCE', unit='UNRESOLVED_READ_SOURCE',
                                basis='UNRESOLVED_READ_SOURCE'), upstream_api=function,
                warnings=['Not normalized: verify each item currency, scale, period and basis before evidence entry.',
                          'Latest provider history is not a point-in-time archive. Publication dates/restatements require primary filings.'])


def edgar_result(args, identity):
    if not identity_valid(identity):
        return dict(status='INCOMPLETE', error_code='MISSING_EDGAR_IDENTITY',
                    error='Configure a real SEC contact identity before querying.', datasets=[], sources=[])
    import edgar
    edgar.set_identity(identity)
    identifier = int(args.symbol) if args.symbol.isdigit() else args.symbol.upper()
    company = edgar.Company(identifier)
    filings = company.get_filings(form=args.form, amendments=False)
    if filings is None:
        return dict(datasets=[], sources=[], warnings=['No matching SEC filings returned.'])
    frame = filings.to_pandas()
    selected = filter_filings(frame, args.as_of, getattr(args, 'accession', None), args.form)
    if args.command == 'edgar-filings':
        dataset = frame_dataset('sec_filings', selected, args.limit)
        sources = []
        for row in dataset['rows']:
            accession = row.get('accession_number') or row.get('accession_no')
            if not accession:
                raise ValueError('SEC filing row lacks accession number')
            row['source_url'] = sec_url(company.cik, accession)
            sources.append(dict(source=row['source_url'], locator=f'SEC accession {accession}',
                                origin_group=f'sec:{company.cik}:{accession}'))
        return dict(company=dict(name=company.name, cik=company.cik), datasets=[dataset], sources=sources,
                    warnings=['Filtered by public filing date, not fiscal period end.'])
    if selected.empty:
        return dict(datasets=[], sources=[], warnings=['No matching SEC filing on or before cutoff.'])
    row = selected.iloc[0]
    accession = row.get('accession_number') or row.get('accession_no')
    if not accession:
        raise ValueError('SEC filing row lacks accession number')
    # Resolve against the same company/form collection; avoid an unrelated global index lookup.
    filing = filings.get(accession)
    if filing is None:
        raise ValueError('selected accession could not be resolved')
    source = dict(source=filing.url, locator=f'SEC accession {accession}',
                  origin_group=f'sec:{company.cik}:{accession}')
    metadata = dict(company=company.name, cik=company.cik, form=filing.form,
                    accession=accession, filing_date=str(filing.filing_date),
                    period_of_report=str(filing.period_of_report), source_url=filing.url)
    if args.command == 'edgar-text':
        content = filing.text()
        if not content or not content.strip():
            return dict(datasets=[], sources=[source], filing=metadata, warnings=['Filing has no extractable text.'])
        return dict(datasets=[], sources=[source], filing=metadata, document_text=content,
                    warnings=['Extracted text requires contextual reading before a fact is cited.'])
    xbrl = filing.xbrl()
    if xbrl is None:
        return dict(status='INCOMPLETE', error_code='NO_XBRL', datasets=[], sources=[source], filing=metadata,
                    warnings=['This filing has no supported XBRL; read its original documents.'])
    datasets, warnings = [], ['Statement columns may mix periods and units; inspect row metadata before normalization.']
    missing = []
    for name in ('income_statement', 'balance_sheet', 'cashflow_statement'):
        statement = getattr(xbrl.statements, name)()
        if statement is None:
            warnings.append('Missing statement: ' + name)
            missing.append(name)
            continue
        dataset = frame_dataset(name, statement.to_dataframe(include_unit=True, include_point_in_time=True), args.limit)
        datasets.append(dataset)
        if not dataset['row_count']:
            missing.append(name)
    result = dict(datasets=datasets, sources=[source], filing=metadata, warnings=warnings,
                  dimensions=dict(currency='READ_XBRL_UNITS', unit='READ_XBRL_SCALE', basis='READ_FILING'))
    if missing:
        result.update(status='INCOMPLETE', missing_statements=missing)
    return result


def worker(args, identity):
    os.environ.setdefault('EDGAR_RATE_LIMIT_PER_SEC', '3')
    os.environ['EDGAR_LOCAL_DATA_DIR'] = str(Path(args.workspace).resolve() / '.runtime/cache/edgar')
    versions = {}
    if args.command == 'doctor':
        packages = {}
        for package, module in [('akshare', 'akshare'), ('edgartools', 'edgar')]:
            try:
                importlib.import_module(module)
                packages[package] = dict(importable=True, version=importlib.metadata.version(package))
            except Exception as exc:
                packages[package] = dict(importable=False, error=redact(exc))
        ready = all(x['importable'] for x in packages.values())
        return dict(status='READY' if ready else 'INCOMPLETE', packages=packages,
                    python=sys.version.split()[0], edgar_identity_configured=identity_valid(identity),
                    network_tested=False)
    provider = 'akshare' if args.command.startswith('ak-') else 'edgartools'
    versions[provider] = importlib.metadata.version(provider)
    if provider == 'akshare':
        ak = importlib.import_module('akshare')
        result = price_result(args, ak) if args.command == 'ak-prices' else hk_financial_result(args, ak)
    else:
        result = edgar_result(args, identity)
        result.setdefault('warnings', []).append('Exact form query; amendments (/A) must be queried and reviewed separately.')
    result.update(provider=provider, package_versions=versions)
    if 'status' not in result:
        datasets = result.get('datasets', [])
        if any(x['truncated'] for x in datasets):
            result['status'] = 'INCOMPLETE'
            result.setdefault('warnings', []).append('Export truncated; raise limit or narrow query.')
        elif any(x['exported_rows'] for x in datasets) or result.get('document_text'):
            result['status'] = 'FETCHED'
        else:
            result['status'] = 'EMPTY'
    return result


def persist(result, root):
    directory = Path(root).resolve() / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid4().hex[:8])
    directory.mkdir(parents=True, exist_ok=False)
    content = result.pop('document_text', None)
    if content is not None:
        path = directory / 'filing.txt'
        path.write_text(content, encoding='utf-8')
        result['document'] = dict(path=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                  characters=len(content))
    path = directory / 'bundle.json'
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    return path


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace', default='.')
    p.add_argument('--_worker', action='store_true', help=argparse.SUPPRESS)
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor')
    for command in ('ak-prices', 'ak-hk-financials', 'edgar-filings', 'edgar-financials', 'edgar-text'):
        s = sub.add_parser(command)
        s.add_argument('--symbol', required=True)
        s.add_argument('--output', required=True, help='Directory for a new immutable query bundle')
        s.add_argument('--limit', type=int, default=2000)
        if command == 'ak-prices':
            s.add_argument('--market', choices=('hk', 'cn'), required=True)
            s.add_argument('--start', type=iso_date, required=True)
            s.add_argument('--end', type=iso_date, required=True)
            s.add_argument('--adjust', choices=('', 'qfq', 'hfq'), default='')
            s.add_argument('--source', choices=('eastmoney', 'sina'), default='eastmoney')
        elif command == 'ak-hk-financials':
            s.add_argument('--statement', choices=('利润表', '资产负债表', '现金流量表'), default='利润表')
            s.add_argument('--frequency', choices=('年度', '报告期'), default='年度')
        else:
            s.add_argument('--as-of', type=iso_date, required=True)
            s.add_argument('--form', choices=FORMS, default='10-K')
            if command == 'edgar-text':
                s.add_argument('--accession', required=True)
    return p


def main():
    args = parser().parse_args()
    try:
        validate_query(args)
        python, identity = runtime_config(args.workspace)
        if args._worker:
            # Third-party progress/log output must not corrupt the JSON protocol.
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                result = worker(args, identity)
            print(json.dumps(result, ensure_ascii=False, allow_nan=False))
            return 0
        if not python.is_file():
            raise ValueError('Data runtime missing; configure .berkshire/data-runtime.json or BERKSHIRE_DATA_PYTHON')
        try:
            child = subprocess.run([str(python), '-B', str(Path(__file__).resolve()), '--_worker', *sys.argv[1:]],
                                   capture_output=True, text=True, timeout=120, check=False)
            result = json.loads(child.stdout)
        except subprocess.TimeoutExpired:
            result = dict(status='ERROR', error_code='TIMEOUT', error='Provider exceeded the 120 second query deadline.')
        except json.JSONDecodeError:
            result = dict(status='ERROR', error_code='WORKER_FAILED', error=redact(child.stderr or child.stdout))
        result.update(schema_version=1, accessed_at=datetime.now(timezone.utc).isoformat(),
                      query={k: v for k, v in vars(args).items() if k not in ('_worker', 'workspace', 'output')},
                      scope='Data retrieval only; not an evidence audit or investment conclusion.')
        if args.command == 'doctor':
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            path = persist(result, args.output)
            print(json.dumps(dict(status=result['status'], bundle=str(path),
                                  datasets=[dict(name=x['name'], exported_rows=x['exported_rows']) for x in result.get('datasets', [])],
                                  error_code=result.get('error_code')), ensure_ascii=False, indent=2))
        return 0 if result['status'] in ('FETCHED', 'READY') else 2
    except Exception as exc:
        result = dict(status='ERROR', error_code=type(exc).__name__, error=redact(exc))
        print(json.dumps(result, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
