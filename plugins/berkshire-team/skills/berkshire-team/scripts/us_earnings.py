"""Read-only US earnings/consensus snapshots; not a point-in-time database or audit."""
import argparse
import contextlib
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import importlib.metadata
import io
import json
from pathlib import Path
import re
import subprocess
import sys
from zoneinfo import ZoneInfo

from market_data import frame_dataset, iso_date, persist, runtime_config

US_EXCHANGES = {'NMS', 'NGM', 'NCM', 'NYQ', 'ASE', 'PCX', 'BTS', 'BATS'}
MODES = {
    'estimates': ('earnings_estimate', 'revenue_estimate', 'eps_trend', 'eps_revisions',
                  'growth_estimates', 'earnings_history'),
    'recap': ('earnings_dates', 'earnings_history', 'quarterly_income_stmt',
              'quarterly_cashflow', 'quarterly_balance_sheet'),
}


def local_today():
    return datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()


def number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        n = Decimal(str(value))
        return n if n.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def change(actual, reference):
    """Null and zero references are not zero-percent changes."""
    a, b = number(actual), number(reference)
    if a is None or b is None:
        return {'difference': None, 'percent': None, 'reason': 'MISSING_VALUE'}
    return {'difference': str(a - b), 'percent': str((a - b) / abs(b) * 100) if b else None,
            'reason': None if b else 'ZERO_REFERENCE'}


def estimate_summary(frame):
    result = []
    if frame is None:
        return result
    for period, row in frame.iterrows():
        current = number(row.get('current'))
        revisions = {window: change(current, row.get(window))
                     for window in ('7daysAgo', '30daysAgo', '60daysAgo', '90daysAgo')}
        result.append({'period_label': str(period), 'current': str(current) if current is not None else None,
                       'changes': revisions})
    return result


def earnings_summary(frame):
    """Compare only the provider's paired values; leave accounting basis unresolved."""
    result = []
    if frame is None:
        return result
    for period, row in frame.iterrows():
        actual, estimate = number(row.get('epsActual')), number(row.get('epsEstimate'))
        result.append({'fiscal_period_end': str(period),
                       'actual_eps': str(actual) if actual is not None else None,
                       'estimated_eps': str(estimate) if estimate is not None else None,
                       'comparison': change(actual, estimate),
                       'basis': 'PROVIDER_PAIR_UNVERIFIED; confirm GAAP/adjusted, fiscal period, currency and ADR units'})
    return result


def price_reaction(frame, pre_session, post_session, today_ny=None):
    """Use two explicitly verified sessions, never infer earnings timing from midnight."""
    if not pre_session or not post_session:
        return {'status': 'NOT_COMPUTED', 'reason': 'VERIFIED_SESSIONS_REQUIRED'}
    today_ny = today_ny or datetime.now(ZoneInfo('America/New_York')).date().isoformat()
    # Conservatively exclude the current NY session (daily bar may still be partial).
    if post_session >= today_ny:
        return {'status': 'PENDING', 'reason': 'POST_SESSION_NOT_CONFIRMED_COMPLETE'}
    if frame is None or frame.empty or 'Close' not in frame:
        return {'status': 'PENDING', 'reason': 'MISSING_CLOSES'}
    if frame.index.tz is None:
        return {'status': 'INCOMPLETE', 'reason': 'UNKNOWN_PRICE_TIMEZONE'}
    dates = frame.index.tz_convert('America/New_York').strftime('%Y-%m-%d')
    if sum(dates == pre_session) != 1 or sum(dates == post_session) != 1:
        return {'status': 'PENDING', 'reason': 'EXACT_SESSION_CLOSE_MISSING'}
    in_window = (dates > pre_session) & (dates <= post_session)
    if 'Stock Splits' not in frame:
        return {'status': 'INCOMPLETE', 'reason': 'SPLIT_STATUS_UNKNOWN'}
    splits = [number(x) for x in frame.loc[in_window, 'Stock Splits']]
    if any(x is None or x != 0 for x in splits):
        return {'status': 'INCOMPLETE', 'reason': 'SPLIT_IN_WINDOW_OR_UNKNOWN'}
    pre = number(frame.loc[dates == pre_session, 'Close'].iloc[0])
    post = number(frame.loc[dates == post_session, 'Close'].iloc[0])
    if pre is None or post is None or pre <= 0 or post <= 0:
        return {'status': 'INCOMPLETE', 'reason': 'INVALID_CLOSE'}
    return {'status': 'CALCULATED', 'pre_session': pre_session, 'post_session': post_session,
            'pre_close': str(pre), 'post_close': str(post), 'change_pct': change(post, pre)['percent'],
            'basis': 'unadjusted regular-session close; excludes dividends; not causal attribution'}


def export_frame(name, frame, limit):
    dataset = frame_dataset(name, frame, limit)
    if frame is not None:
        dataset['row_labels'] = [str(x) for x in frame.head(limit).index]
        dataset['index_timezone'] = str(getattr(frame.index, 'tz', None))
    dataset['status'] = ('INCOMPLETE' if dataset['truncated'] else
                         'FETCHED' if dataset['exported_rows'] else 'EMPTY')
    return dataset


def validate(args):
    if args.command == 'doctor':
        return
    if not re.fullmatch(r'[A-Z][A-Z0-9.\-]{0,14}', args.symbol):
        raise ValueError('Use an explicit US ticker, not a local numeric code.')
    if args.as_of != local_today():
        raise ValueError('Yahoo live snapshots cannot satisfy a historical/future as-of query. Use saved bundles.')
    if not 1 <= args.limit <= 2000:
        raise ValueError('limit must be in 1..2000')
    sessions = [args.pre_session, args.post_session, args.timing_source]
    if any(sessions) and not all(sessions):
        raise ValueError('Reaction requires pre-session, post-session and a verified timing-source URL together.')
    if all(sessions):
        if args.command != 'recap' or not args.pre_session < args.post_session <= local_today():
            raise ValueError('Invalid recap session range')
        if not args.timing_source.startswith('https://'):
            raise ValueError('Use the verified issuer/exchange earnings schedule HTTPS URL.')


def fetch(args, yf):
    ticker = yf.Ticker(args.symbol)
    info = ticker.get_info()
    security = {key: info.get(key) for key in ('symbol', 'longName', 'exchange', 'fullExchangeName',
                                              'quoteType', 'currency', 'financialCurrency', 'exchangeTimezoneName')}
    if (str(info.get('symbol', '')).upper() != args.symbol or info.get('exchange') not in US_EXCHANGES
            or info.get('quoteType') != 'EQUITY'):
        return {'status': 'INCOMPLETE', 'error_code': 'US_EQUITY_NOT_VERIFIED', 'security': security,
                'datasets': [], 'warnings': ['No implicit conversion of foreign shares or ADRs.']}
    frames, datasets = {}, []
    for name in MODES[args.command]:
        try:
            frame = ticker.get_earnings_dates(limit=12) if name == 'earnings_dates' else getattr(ticker, name)
            frames[name] = frame
            dataset = export_frame(name, frame, args.limit)
            dataset['provider_method'] = 'yfinance.Ticker.' + name
            datasets.append(dataset)
        except Exception as exc:
            datasets.append({'name': name, 'status': 'ERROR', 'exported_rows': 0,
                             'error_type': type(exc).__name__})
    summary = {}
    if args.command == 'estimates':
        summary['eps_revisions'] = estimate_summary(frames.get('eps_trend'))
    else:
        summary['provider_eps_comparisons'] = earnings_summary(frames.get('earnings_history'))
        prices = None
        if args.pre_session:
            try:
                prices = ticker.history(start=args.pre_session,
                                        end=(date.fromisoformat(args.post_session) + timedelta(days=1)).isoformat(),
                                        auto_adjust=False, actions=True)
                datasets.append(export_frame('reaction_prices', prices, args.limit))
            except Exception as exc:
                datasets.append({'name': 'reaction_prices', 'status': 'ERROR', 'exported_rows': 0,
                                 'error_type': type(exc).__name__})
        summary['price_reaction'] = price_reaction(prices, args.pre_session, args.post_session)
        summary['timing_source'] = args.timing_source
    complete = all(d['status'] == 'FETCHED' for d in datasets)
    if args.pre_session and summary.get('price_reaction', {}).get('status') != 'CALCULATED':
        complete = False
    return {'status': 'FETCHED' if complete else 'INCOMPLETE', 'security': security,
            'datasets': datasets, 'summary': summary,
            'sources': [{'source': f'https://finance.yahoo.com/quote/{args.symbol}/{page}/',
                         'locator': ', '.join(MODES[args.command]),
                         'origin_group': f'yahoo-finance:{args.symbol}'}
                        for page in (('analysis',) if args.command == 'estimates' else ('analysis', 'financials', 'history'))],
            'warnings': [
                'Retrieved current snapshot, not an evidence PASS or a point-in-time archive.',
                'All Yahoo endpoints share one source family; do not count them as independent sources.',
                'Verify fiscal period, trading/financial currency, adjusted EPS and ADR share basis against issuer/SEC.',
                '0q/+1q/0y/+1y are provider-relative labels; retain actual fiscal period before comparing snapshots.',
                'Consensus estimates are market expectations, not company guidance or the analyst model.',
                'Do not infer revenue surprise without same-period, same-basis pre-release consensus.',
                'Historical statement rows may be restated; current consensus cannot support historical backtests.',
            ]}


def worker(args):
    if args.command == 'doctor':
        packages = {}
        for name in ('yfinance', 'pandas', 'numpy'):
            try:
                packages[name] = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                packages[name] = None
        return {'status': 'READY' if all(packages.values()) else 'INCOMPLETE',
                'packages': packages, 'network_tested': False}
    import yfinance as yf
    cache = Path(args.workspace).resolve() / '.runtime/cache/yfinance'
    cache.mkdir(parents=True, exist_ok=True)
    yf.set_tz_cache_location(str(cache))
    result = fetch(args, yf)
    result['package_versions'] = {name: importlib.metadata.version(name) for name in ('yfinance', 'pandas')}
    return result


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace', default='.')
    p.add_argument('--_worker', action='store_true', help=argparse.SUPPRESS)
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor')
    for command in MODES:
        s = sub.add_parser(command)
        s.add_argument('--symbol', required=True, type=str.upper)
        s.add_argument('--as-of', type=iso_date, default=local_today())
        s.add_argument('--output', required=True)
        s.add_argument('--limit', type=int, default=200)
        s.add_argument('--pre-session', type=iso_date)
        s.add_argument('--post-session', type=iso_date)
        s.add_argument('--timing-source')
    return p


def main():
    args = parser().parse_args()
    try:
        validate(args)
        if args._worker:
            # Never expose provider logs (cookies, headers or URLs) in protocol output.
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                result = worker(args)
            print(json.dumps(result, ensure_ascii=False, allow_nan=False))
            return 0
        python, _ = runtime_config(args.workspace)
        if not python.is_file():
            raise ValueError('Missing workspace data runtime; use BERKSHIRE_DATA_PYTHON or data-runtime.json.')
        try:
            child = subprocess.run([str(python), '-B', str(Path(__file__).resolve()), '--_worker', *sys.argv[1:]],
                                   capture_output=True, text=True, timeout=180)
            result = json.loads(child.stdout)
        except subprocess.TimeoutExpired:
            result = {'status': 'ERROR', 'error_code': 'TIMEOUT'}
        except json.JSONDecodeError:
            result = {'status': 'ERROR', 'error_code': 'PROVIDER_WORKER_FAILED'}
        result.update(schema_version=1, accessed_at=datetime.now(timezone.utc).isoformat(),
                      query={k: v for k, v in vars(args).items() if k not in ('workspace', '_worker', 'output')},
                      scope='US earnings/consensus supplement only; primary filings and evidence audit remain required.')
        if args.command == 'doctor':
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            path = persist(result, args.output)
            print(json.dumps({'status': result['status'], 'bundle': str(path),
                              'datasets': [{'name': x['name'], 'status': x['status']} for x in result.get('datasets', [])],
                              'error_code': result.get('error_code')}, ensure_ascii=False, indent=2))
        return 0 if result['status'] in ('READY', 'FETCHED') else 2
    except Exception as exc:
        # Internal errors are classified without printing credentials/provider diagnostics.
        detail = str(exc) if isinstance(exc, ValueError) and not args._worker else None
        print(json.dumps({'status': 'ERROR', 'error_code': type(exc).__name__, 'detail': detail}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
