"""Synthetic boundary cases; no external financial facts or network calls."""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/berkshire-team/scripts'))
from us_earnings import change, earnings_summary, estimate_summary, export_frame, fetch, parser, price_reaction, validate
try:
    import pandas as pd
except ImportError:
    pd = None


class Inputs(unittest.TestCase):
    def test_zero_estimate_is_not_zero_surprise(self):
        self.assertIsNone(change(1, 0)['percent'])
        self.assertEqual(change(1, 0)['difference'], '1')

    def test_missing_is_not_zero(self):
        for x in (None, float('nan'), float('inf'), True):
            self.assertIsNone(change(x, 1)['difference'])

    def test_negative_eps_reference_uses_absolute_denominator(self):
        self.assertEqual(change(-1, -2)['percent'], '50.0')

    def test_reject_historical_live_snapshot(self):
        args = parser().parse_args(['estimates', '--symbol', 'AAPL', '--as-of', '2024-01-01', '--output', 'unused'])
        with patch('us_earnings.local_today', return_value='2026-11-05'), self.assertRaises(ValueError):
            validate(args)

    def test_reaction_requires_all_verified_inputs(self):
        args = parser().parse_args(['recap', '--symbol', 'AAPL', '--pre-session', '2026-10-29', '--output', 'unused'])
        with self.assertRaises(ValueError):
            validate(args)

    def test_reject_numeric_local_security(self):
        args = parser().parse_args(['recap', '--symbol', '00700', '--output', 'unused'])
        with self.assertRaises(ValueError):
            validate(args)


@unittest.skipIf(pd is None, 'Requires the installed isolated data runtime')
class Data(unittest.TestCase):
    def prices(self):
        return pd.DataFrame({'Close': [100.0, 110.0], 'Stock Splits': [0.0, 0.0]},
                            index=pd.DatetimeIndex(['2026-10-29', '2026-10-30'], tz='America/New_York'))

    def test_raw_missing_and_zero_preserved_with_timezone(self):
        frame = self.prices()
        frame['EPS'] = [None, 0]
        d = export_frame('sample', frame, 200)
        self.assertEqual([r['EPS'] for r in d['rows']], [None, 0])
        self.assertEqual(d['index_timezone'], 'America/New_York')
        self.assertIn('-04:00', d['row_labels'][0])

    def test_export_truncation_is_incomplete(self):
        self.assertEqual(export_frame('sample', self.prices(), 1)['status'], 'INCOMPLETE')

    def test_duplicate_columns_fail_instead_of_losing_context(self):
        frame = pd.DataFrame([[1, 2]], columns=['EPS', 'EPS'])
        with self.assertRaises(ValueError):
            export_frame('sample', frame, 20)

    def test_no_timestamp_inference_without_verified_sessions(self):
        self.assertEqual(price_reaction(self.prices(), None, None)['status'], 'NOT_COMPUTED')

    def test_current_session_cannot_be_treated_as_complete(self):
        result = price_reaction(self.prices(), '2026-10-29', '2026-10-30', '2026-10-30')
        self.assertEqual(result['status'], 'PENDING')

    def test_exact_verified_sessions_produce_price_return(self):
        result = price_reaction(self.prices(), '2026-10-29', '2026-10-30', '2026-11-01')
        self.assertEqual(result['status'], 'CALCULATED')
        self.assertEqual(result['change_pct'], '10.0')

    def test_no_nearest_session_substitution(self):
        result = price_reaction(self.prices(), '2026-10-28', '2026-10-30', '2026-11-01')
        self.assertEqual(result['reason'], 'EXACT_SESSION_CLOSE_MISSING')

    def test_split_blocks_misleading_return(self):
        frame = self.prices()
        frame.loc[frame.index[-1], 'Stock Splits'] = 2
        result = price_reaction(frame, '2026-10-29', '2026-10-30', '2026-11-01')
        self.assertEqual(result['reason'], 'SPLIT_IN_WINDOW_OR_UNKNOWN')

    def test_naive_price_index_is_incomplete(self):
        frame = self.prices()
        frame.index = frame.index.tz_localize(None)
        self.assertEqual(price_reaction(frame, '2026-10-29', '2026-10-30', '2026-11-01')['status'], 'INCOMPLETE')

    def test_estimates_keep_relative_period_and_signed_values(self):
        frame = pd.DataFrame({'current': [-1, 0], '30daysAgo': [-2, 0]}, index=['0y', '+1y'])
        rows = estimate_summary(frame)
        self.assertEqual(rows[0]['period_label'], '0y')
        self.assertEqual(rows[0]['changes']['30daysAgo']['percent'], '50.0')
        self.assertIsNone(rows[1]['changes']['30daysAgo']['percent'])

    def test_eps_summary_keeps_fiscal_period_separate_from_event_date(self):
        frame = pd.DataFrame({'epsActual': [-1, 2], 'epsEstimate': [-2, 0]},
                             index=['2026-06-30', '2026-09-30'])
        rows = earnings_summary(frame)
        self.assertEqual(rows[0]['fiscal_period_end'], '2026-06-30')
        self.assertEqual(rows[0]['comparison']['percent'], '50.0')
        self.assertIn('UNVERIFIED', rows[0]['basis'])
        self.assertIsNone(rows[1]['comparison']['percent'])

    def test_partial_endpoint_failure_retains_other_tables_and_hides_error_text(self):
        class Ticker:
            def get_info(self):
                return {'symbol': 'AAPL', 'exchange': 'NMS', 'quoteType': 'EQUITY'}
            def __getattr__(self, name):
                if name == 'eps_revisions':
                    raise RuntimeError('credential=DO_NOT_EXPORT')
                return pd.DataFrame({'current': [2], '30daysAgo': [1]}, index=['0y'])
        args = parser().parse_args(['estimates', '--symbol', 'AAPL', '--output', 'unused'])
        result = fetch(args, SimpleNamespace(Ticker=lambda _: Ticker()))
        self.assertEqual(result['status'], 'INCOMPLETE')
        self.assertEqual(sum(d['status'] == 'FETCHED' for d in result['datasets']), 5)
        self.assertNotIn('DO_NOT_EXPORT', str(result))
        self.assertEqual(len({s['origin_group'] for s in result['sources']}), 1)

    def test_foreign_listing_is_not_silently_remapped(self):
        t = SimpleNamespace(get_info=lambda: {'symbol': '0700.HK', 'exchange': 'HKG', 'quoteType': 'EQUITY'})
        args = parser().parse_args(['recap', '--symbol', 'AAPL', '--output', 'unused'])
        result = fetch(args, SimpleNamespace(Ticker=lambda _: t))
        self.assertEqual(result['error_code'], 'US_EQUITY_NOT_VERIFIED')
        self.assertEqual(result['datasets'], [])


if __name__ == '__main__':
    unittest.main()
