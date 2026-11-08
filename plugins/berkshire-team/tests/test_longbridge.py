import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/berkshire-team/scripts'
sys.path.insert(0, str(SCRIPTS))
from longbridge_data import normalize

TIME = '2026-11-07T12:00:00+08:00'


def fixture():
    return {'report': 'af', 'list': {'i_s': {'indicators': [
        {'title': '收入', 'currency': 'USD', 'accounts': [
            {'name': 'Revenue', 'field': 'OperatingRevenue', 'values': [
                {'year': 2025, 'period': 'FY 2025', 'fp_end': '1758945600', 'value': '100.0000'},
                {'year': 2024, 'period': 'FY 2024', 'value': '-2'},
                {'year': 2023, 'period': 'FY 2023', 'value': '0'},
                {'year': 2022, 'period': 'FY 2022', 'value': None}]}]}]}}}


class LongbridgeTests(unittest.TestCase):
    def run_report(self, data):
        return normalize(data, 'financial-report', 'AAPL.US', TIME)

    def test_period_currency_locator_and_no_verification_claim(self):
        out = self.run_report(fixture())
        self.assertEqual(out['status'], 'FETCHED_UNVERIFIED')
        self.assertEqual(out['rows'][0]['currency'], 'USD')
        self.assertEqual(out['rows'][0]['value'], '100.0000')
        self.assertIsNone(out['rows'][0]['unit'])
        self.assertIsNone(out['publication_date'])
        self.assertEqual(len(out['periods_by_statement']['i_s']), 4)
        self.assertIn('values[0]', out['rows'][0]['locator'])

    def test_missing_negative_and_zero_are_distinct(self):
        out = self.run_report(fixture())
        self.assertEqual([r['value'] for r in out['rows']], ['100.0000', '-2', '0', None])

    def test_mcp_wrapper_and_errors(self):
        out = self.run_report({'content': [{'type': 'text', 'text': json.dumps(fixture())}]})
        self.assertEqual(len(out['rows']), 4)
        with self.assertRaises(ValueError):
            self.run_report({'isError': True, 'content': []})

    def test_period_mismatch_is_rejected(self):
        f = fixture(); f['report'] = 'qf'
        with self.assertRaises(ValueError): self.run_report(f)

    def test_empty_is_not_success(self):
        self.assertEqual(self.run_report({'report': 'af', 'list': {}})['status'], 'EMPTY')
        with self.assertRaises(ValueError): self.run_report({'income_statement': {}})

    def test_invalid_values(self):
        for value in ['NaN', 'Infinity', True, '100 billion']:
            f = fixture(); f['list']['i_s']['indicators'][0]['accounts'][0]['values'][0]['value'] = value
            with self.subTest(value=value), self.assertRaises(ValueError): self.run_report(f)

    def test_symbol_and_timezone_required(self):
        with self.assertRaises(ValueError): normalize(fixture(), 'financial-report', 'AAPL', TIME)
        with self.assertRaises(ValueError): normalize(fixture(), 'financial-report', 'AAPL.US', '2026-11-07')

    def test_quote_never_mixes_sessions_or_symbols(self):
        payload = [{'symbol': 'MSFT.US', 'last_done': '1'}, {'symbol': 'AAPL.US', 'last_done': '100',
                    'timestamp': '2026-11-06T16:00:00-05:00', 'post_market': {'last_done': '102'}}]
        out = normalize(payload, 'quote', 'AAPL.US', TIME)
        self.assertEqual(len(out['rows']), 1)
        self.assertEqual(out['rows'][0]['price'], '100')
        self.assertEqual(out['rows'][0]['raw']['post_market']['last_done'], '102')

    def test_cli_preserves_existing_files(self):
        with tempfile.TemporaryDirectory() as d:
            raw = Path(d)/'raw.json'; raw.write_text(json.dumps(fixture()))
            args = [sys.executable, str(SCRIPTS/'longbridge_data.py'), 'normalize', '--kind', 'financial-report',
                    '--symbol', 'AAPL.US', '--retrieved-at', TIME, '--input', str(raw), '--output', str(raw)]
            result = subprocess.run(args, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(json.loads(raw.read_text()), fixture())


if __name__ == '__main__': unittest.main()
