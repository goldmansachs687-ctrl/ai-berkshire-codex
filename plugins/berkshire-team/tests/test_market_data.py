"""Adapter invariants, using synthetic rows rather than live financial facts."""
import argparse
from datetime import date
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/berkshire-team/scripts'))
from market_data import (edgar_result, filter_filings, frame_dataset, identity_valid, parser,
                         persist, price_result, redact, runtime_config, sec_url, validate_query, worker)
try:
    import pandas as pd
except ImportError:
    pd = None


class ConfigurationTests(unittest.TestCase):
    def test_missing_and_incomplete_identity_do_not_query_sec(self):
        for value in ('', 'Bruce @outlook.com'):
            self.assertFalse(identity_valid(value))
            result = edgar_result(None, value)
            self.assertEqual(result['status'], 'INCOMPLETE')

    def test_relative_runtime_is_workspace_based(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {}, clear=True):
            base=Path(root); (base/'.berkshire').mkdir()
            (base/'.berkshire/data-runtime.json').write_text(json.dumps({'python':'env/bin/python'}))
            python, identity=runtime_config(base)
            self.assertEqual(python, base.resolve()/'env/bin/python')
            self.assertEqual(identity, '')

    def test_environment_identity_not_printed_and_overrides_file(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {'EDGAR_IDENTITY':'Person contact@example.org'}, clear=True):
            _, identity=runtime_config(root)
            self.assertTrue(identity_valid(identity))
            self.assertNotIn('contact@example.org', redact('Failed: '+identity))

    def test_symbol_and_range_validation(self):
        for options in (
            ['--market','hk','--symbol','AAPL','--start','2024-01-01','--end','2024-01-03'],
            ['--market','cn','--symbol','00700','--start','2024-01-01','--end','2024-01-03'],
            ['--market','hk','--symbol','00700','--start','2024-02-01','--end','2024-01-03'],
            ['--market','cn','--source','sina','--symbol','600519','--start','2024-01-01','--end','2024-01-03']):
            args=parser().parse_args(['ak-prices',*options,'--output','out'])
            with self.assertRaises(ValueError):validate_query(args)

    def test_invalid_accession_rejected(self):
        args=parser().parse_args(['edgar-text','--symbol','AAPL','--accession','wrong','--as-of','2024-01-01','--output','out'])
        with self.assertRaises(ValueError):validate_query(args)

    def test_query_bundles_do_not_overwrite_and_text_is_hashed(self):
        import hashlib
        with tempfile.TemporaryDirectory() as root:
            first=persist({'status':'FETCHED','document_text':'synthetic text'},root)
            second=persist({'status':'ERROR'},root)
            self.assertNotEqual(first,second)
            record=json.loads(first.read_text())['document']
            content=(first.parent/record['path']).read_bytes()
            self.assertEqual(record['sha256'],hashlib.sha256(content).hexdigest())


@unittest.skipIf(pd is None, 'Run adapter data tests in installed market-data environment')
class DataTests(unittest.TestCase):
    def test_cutoff_uses_public_filing_date(self):
        frame=pd.DataFrame([
            {'filing_date':date(2024,2,1),'period_of_report':'2023-12-31','accession_number':'later'},
            {'filing_date':date(2024,1,1),'period_of_report':'2023-09-30','accession_number':'available'}])
        filtered=filter_filings(frame,'2024-01-15')
        self.assertEqual(filtered['accession_number'].tolist(),['available'])
        self.assertTrue(filter_filings(frame,'2024-01-15','later').empty)

    def test_original_and_amendment_are_not_interchanged(self):
        frame=pd.DataFrame([
            {'filing_date':date(2024,1,1),'form':'10-K','accession_number':'original'},
            {'filing_date':date(2024,2,1),'form':'10-K/A','accession_number':'amended'}])
        self.assertEqual(filter_filings(frame,'2024-03-01',form='10-K')['accession_number'].tolist(),['original'])
        self.assertEqual(filter_filings(frame,'2024-03-01',form='10-K/A')['accession_number'].tolist(),['amended'])
        self.assertTrue(filter_filings(frame,'2024-03-01',accession='amended',form='10-K').empty)

    def test_unknown_date_does_not_silently_pass_cutoff(self):
        with self.assertRaises(ValueError):filter_filings(pd.DataFrame({'filing_date':[None]}),'2024-01-01')

    def test_missing_dates_rejected(self):
        with self.assertRaises(ValueError):filter_filings(pd.DataFrame({'other':[1]}),'2024-01-01')

    def test_raw_zero_null_negative_and_date_preserved(self):
        data=frame_dataset('sample',pd.DataFrame({'amount':[0,None,-3],'date':[date(2024,1,1)]*3}),10)
        self.assertEqual([r['amount'] for r in data['rows']],[0,None,-3])
        self.assertTrue(data['rows'][0]['date'].startswith('2024-01-01'))

    def test_truncation_is_explicit(self):
        data=frame_dataset('sample',pd.DataFrame({'amount':[1,2,3]}),2)
        self.assertTrue(data['truncated'])
        self.assertEqual((data['row_count'],data['exported_rows']),(3,2))

    def test_source_index_labels_are_preserved(self):
        data=frame_dataset('sample',pd.DataFrame({'FY2024':[1,2]},index=['Revenue','Income']),10)
        self.assertEqual(data['row_index'],['Revenue','Income'])

    def test_missing_requested_statement_is_incomplete(self):
        rows=pd.DataFrame({'filing_date':[date(2024,1,1)],'form':['10-K'],'accession_number':['0000000001-24-000001']})
        statement=SimpleNamespace(to_dataframe=lambda **kw:pd.DataFrame({'amount':[1]}))
        filing=SimpleNamespace(url='https://www.sec.gov/test',form='10-K',filing_date=date(2024,1,1),
                               period_of_report='2023-12-31',
                               xbrl=lambda:SimpleNamespace(statements=SimpleNamespace(income_statement=lambda:statement,
                                   balance_sheet=lambda:None,cashflow_statement=lambda:statement)))
        filings=SimpleNamespace(to_pandas=lambda:rows,get=lambda accession:filing)
        company=SimpleNamespace(cik=1,name='Synthetic',get_filings=lambda **kw:filings)
        module=SimpleNamespace(set_identity=lambda value:None,Company=lambda identifier:company)
        args=parser().parse_args(['edgar-financials','--symbol','1','--as-of','2024-01-01','--output','out'])
        with patch.dict(sys.modules,{'edgar':module}):result=edgar_result(args,'Tester tester@example.org')
        self.assertEqual(result['status'],'INCOMPLETE')
        self.assertEqual(result['missing_statements'],['balance_sheet'])

    def test_duplicate_columns_rejected(self):
        with self.assertRaises(ValueError):frame_dataset('sample',pd.DataFrame([[1,2]],columns=['FY','FY']),10)

    def test_sina_filtered_locally_and_lineage_retained(self):
        args=parser().parse_args(['ak-prices','--market','hk','--source','sina','--symbol','00700',
                                 '--start','2024-01-02','--end','2024-01-03','--output','out'])
        ak=SimpleNamespace(stock_hk_daily=lambda **kw:pd.DataFrame({'date':[date(2024,1,1),date(2024,1,2)],'close':[1,2]}))
        result=price_result(args,ak)
        self.assertEqual(result['datasets'][0]['row_count'],1)
        self.assertEqual(result['sources'][0]['origin_group'],'sina:prices:hk:00700')
        self.assertEqual(result['dimensions']['currency'],'UNRESOLVED_VERIFY_SECURITY')

    def test_upstream_outside_range_is_not_accepted(self):
        args=parser().parse_args(['ak-prices','--market','hk','--symbol','00700',
                                 '--start','2024-01-02','--end','2024-01-03','--output','out'])
        ak=SimpleNamespace(stock_hk_hist=lambda **kw:pd.DataFrame({'日期':[date(2024,1,1)],'收盘':[1]}))
        with self.assertRaises(ValueError):price_result(args,ak)

    def test_empty_query_is_not_fetched_and_truncated_is_incomplete(self):
        args=parser().parse_args(['ak-prices','--market','hk','--symbol','00700',
                                 '--start','2024-01-01','--end','2024-01-03','--limit','1','--output','out'])
        with patch('market_data.importlib.metadata.version',return_value='fixture'):
            for frame, status in [(pd.DataFrame(),'EMPTY'),
                                  (pd.DataFrame({'日期':[date(2024,1,1),date(2024,1,2)],'收盘':[1,2]}),'INCOMPLETE')]:
                ak=SimpleNamespace(stock_hk_hist=lambda **kw:frame)
                with patch('market_data.importlib.import_module',return_value=ak):
                    self.assertEqual(worker(args,'')['status'],status)

    def test_accession_link_uses_filing_entity(self):
        self.assertEqual(sec_url(320193,'0000320193-24-000123'),
                         'https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/0000320193-24-000123-index.html')


if __name__ == '__main__':unittest.main()
