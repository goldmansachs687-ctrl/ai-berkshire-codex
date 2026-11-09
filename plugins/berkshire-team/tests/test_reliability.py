import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/berkshire-team/scripts'
sys.path.insert(0, str(SCRIPTS))
from report_audit import extract_data_points
from audit_core import evaluate
from evidence_gate import audit
from knowledge import register, search, review
from research_run import initialize, checkpoint, inspect
from financial_rigor import verify_market_cap, cross_validate


def fact(**extra):
    result = dict(id='revenue', reported_value=100, fetched_value=100, fetched_source='filing.pdf p1')
    result.update(extra)
    return result


class AuditTests(unittest.TestCase):
    def test_empty_not_pass(self):
        self.assertEqual(evaluate([])['verdict'], 'INCOMPLETE')

    def test_missing_not_pass(self):
        self.assertEqual(evaluate([fact(fetched_value=None)])['verdict'], 'INCOMPLETE')

    def test_single_source_wrong_fails(self):
        self.assertEqual(evaluate([fact(fetched_value=80)])['verdict'], 'FAIL')

    def test_conflicting_second_fails(self):
        self.assertEqual(evaluate([fact(fetched_value2=80, fetched_source2='other')])['verdict'], 'FAIL')

    def test_unknown_reported_value_incomplete(self):
        self.assertEqual(evaluate([fact(reported_value=None)])['verdict'], 'INCOMPLETE')

    def test_table_empty_cells_preserve_period(self):
        points = extract_data_points('| Metric | FY2023 | FY2024 |\n|---|---|---|\n| Revenue | | 100 |')
        self.assertEqual(len(points), 1)
        self.assertIn('FY2024', points[0]['label'])

    def test_source_missing_not_pass(self):
        self.assertEqual(evaluate([fact(fetched_source='')])['verdict'], 'INCOMPLETE')

    def test_negative_and_zero(self):
        self.assertEqual(evaluate([fact(reported_value=-100, fetched_value=-100)])['verdict'], 'PASS')
        self.assertEqual(evaluate([fact(reported_value=0, fetched_value=0)])['verdict'], 'PASS')
        self.assertEqual(evaluate([fact(reported_value=0, fetched_value=1)])['verdict'], 'FAIL')

    def test_nonfinite_and_boolean_fail(self):
        for value in ['NaN', 'Infinity', True, 'not a number']:
            with self.subTest(value=value):
                self.assertEqual(evaluate([fact(fetched_value=value)])['verdict'], 'FAIL')

    def test_duplicate_id_fails(self):
        self.assertEqual(evaluate([fact(), fact()])['verdict'], 'FAIL')

    def test_missing_required(self):
        self.assertEqual(evaluate([fact()], ['revenue', 'shares'])['verdict'], 'INCOMPLETE')

    def test_assumptions_not_facts(self):
        self.assertEqual(evaluate([fact(kind='assumption', rationale='scenario')])['verdict'], 'INCOMPLETE')
        result = evaluate([fact(), fact(id='pe', kind='assumption', rationale='sensitivity')])
        self.assertEqual(result['pass_count'], 1)
        self.assertEqual(result['excluded_count'], 1)

    def test_required_cannot_be_assumption(self):
        result = evaluate([fact(), fact(id='shares', kind='assumption', rationale='guess')], ['shares'])
        self.assertEqual(result['verdict'], 'INCOMPLETE')

    def test_independence_not_platform_count(self):
        row = fact(require_independent_sources=True, fetched_value2=100, fetched_source2='mirror', origin_group='issuer', origin_group2='issuer')
        self.assertEqual(evaluate([row])['verdict'], 'INCOMPLETE')
        row['origin_group2'] = 'independent-origin'
        self.assertEqual(evaluate([row])['verdict'], 'PASS')

    def test_same_source_url_cannot_count_twice(self):
        row = fact(fetched_source='https://example.org/filing#sales',
                   fetched_value2=100, fetched_source2='https://EXAMPLE.org/filing?utm_source=copy#income',
                   origin_group='issuer', origin_group2='another-label')
        for flag in ('require_independent_sources', 'require_second_source'):
            with self.subTest(flag=flag):
                self.assertEqual(evaluate([dict(row, **{flag: True})])['verdict'], 'INCOMPLETE')

    def test_cli_exit_codes_and_json(self):
        for records, code in [([], 2), ([fact()], 0), ([fact(fetched_value=80)], 1)]:
            result = subprocess.run([sys.executable, str(SCRIPTS/'report_audit.py'), 'verdict', '--results', json.dumps(records), '--output-json'], capture_output=True, text=True)
            self.assertEqual(result.returncode, code, result.stderr)
            self.assertIn('verdict', json.loads(result.stdout))


class EvidenceTests(unittest.TestCase):
    def ledger(self):
        dims = dict(metric='revenue', unit='million', currency='CNY', period='FY2025', basis='IFRS')
        observation = dict(dims, value=100, source='filing.pdf', locator='p1 revenue', accessed_at='2026-10-28', origin_group='issuer2025')
        return dict(required_claims=['revenue'], claims=[dict(dims, id='revenue', reported_value=100, observations=[observation])])

    def test_traceable_match(self):
        self.assertEqual(audit(self.ledger())['verdict'], 'PASS')

    def test_different_period_not_pass(self):
        data = self.ledger(); data['claims'][0]['observations'][0]['period'] = 'FY2024'
        self.assertEqual(audit(data)['verdict'], 'INCOMPLETE')

    def test_missing_locator_not_pass(self):
        data = self.ledger(); del data['claims'][0]['observations'][0]['locator']
        self.assertEqual(audit(data)['verdict'], 'INCOMPLETE')

    def test_fetched_field_cannot_bypass_metadata(self):
        data = self.ledger(); data['claims'][0].update(observations=[], fetched_value=100, fetched_source='fake')
        self.assertEqual(audit(data)['verdict'], 'INCOMPLETE')

    def test_no_declared_coverage_rejected(self):
        with self.assertRaises(ValueError): audit(dict(required_claims=[], claims=[]))

    def test_derived_requires_calculation(self):
        data = self.ledger(); data['claims'][0]['kind'] = 'derived'
        self.assertEqual(audit(data)['verdict'], 'INCOMPLETE')

    def test_document_hash_flags_mirror_with_different_origin_label(self):
        data = self.ledger()
        claim = data['claims'][0]
        claim['require_independent_sources'] = True
        original = claim['observations'][0]
        original['source_sha256'] = 'a' * 64
        mirror = dict(original, source='mirror.pdf', origin_group='another-label')
        claim['observations'].append(mirror)
        self.assertEqual(audit(data)['verdict'], 'INCOMPLETE')
        mirror['source_sha256'] = 'b' * 64
        self.assertEqual(audit(data)['verdict'], 'PASS')


class WorkflowTests(unittest.TestCase):
    def test_run_no_overwrite_and_artifact_integrity(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = initialize(temporary, '腾讯', '0700.HK', '2026-10-28')
            other = initialize(temporary, '腾讯', '0700.HK', '2026-10-28')
            self.assertNotEqual(run, other)
            with self.assertRaises(ValueError): checkpoint(run, 'business_analyst', 'complete', [], 'not done')
            (run/'business.md').write_text('first', encoding='utf-8')
            checkpoint(run, 'business_analyst', 'complete', ['business.md'], 'done')
            self.assertTrue(inspect(run)['roles']['business_analyst']['resumable_complete'])
            (run/'business.md').write_text('changed', encoding='utf-8')
            self.assertFalse(inspect(run)['roles']['business_analyst']['resumable_complete'])
            (run/'business.md').unlink()
            self.assertFalse(inspect(run)['roles']['business_analyst']['resumable_complete'])

    def test_review_invalidated_when_evidence_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = initialize(temporary, 'A', 'A', '2026-10-28')
            (run/'report.md').write_text('report')
            with self.assertRaises(ValueError): checkpoint(run, 'independent_review', 'complete', [], 'not done')
            with self.assertRaises(ValueError): checkpoint(run, 'independent_review', 'complete', ['report.md'], 'not done')
            (run/'review.md').write_text('review')
            checkpoint(run, 'independent_review', 'complete', ['review.md'], 'done', 'reviewer-agent')
            self.assertTrue(inspect(run)['roles']['independent_review']['resumable_complete'])
            (run/'evidence.json').write_text('{}')
            self.assertFalse(inspect(run)['roles']['independent_review']['resumable_complete'])

    def test_review_rejects_empty_missing_id_and_reused_researcher(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = initialize(temporary, 'A', 'A', '2026-10-28')
            (run/'report.md').write_text('report')
            (run/'review.md').write_text('   \n')
            with self.assertRaisesRegex(ValueError, 'empty review artifact'):
                checkpoint(run, 'independent_review', 'complete', ['review.md'], 'done', 'reviewer-agent')
            (run/'review.md').write_text('review')
            with self.assertRaisesRegex(ValueError, 'reviewer agent ID'):
                checkpoint(run, 'independent_review', 'complete', ['review.md'], 'done')
            (run/'business.md').write_text('business research')
            checkpoint(run, 'business_analyst', 'complete', ['business.md'], 'done', 'researcher-agent')
            with self.assertRaisesRegex(ValueError, 'must not be one of'):
                checkpoint(run, 'independent_review', 'complete', ['review.md'], 'done', 'researcher-agent')
            self.assertEqual(inspect(run)['roles']['independent_review']['status'], 'pending')

    def test_legacy_review_without_reviewer_is_not_resumable(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = initialize(temporary, 'A', 'A', '2026-10-28')
            (run/'report.md').write_text('report')
            (run/'review.md').write_text('review')
            checkpoint(run, 'independent_review', 'complete', ['review.md'], 'done', 'reviewer-agent')
            state = json.loads((run/'run.json').read_text())
            del state['roles']['independent_review']['agent_id']
            (run/'run.json').write_text(json.dumps(state))
            self.assertFalse(inspect(run)['roles']['independent_review']['resumable_complete'])

    def test_outside_artifact_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = initialize(temporary, 'A', 'A', '2026-10-28')
            (Path(temporary)/'outside.md').write_text('x')
            with self.assertRaises(ValueError): checkpoint(run, 'business_analyst', 'complete', ['../outside.md'], 'invalid')

    def test_registry_and_changed_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); library = root/'library'
            file = root/'notes.md'; file.write_text('第3页\n维护性资本开支影响所有者收益\n', encoding='utf-8')
            row = register(library, file, 'My notes', 'note')
            self.assertEqual(row['reviewed_sections'], [])
            self.assertEqual(len(search(library, '资本开支')['matches']), 1)
            review(library, row['id'], 'p3', 'read context')
            file.write_text('new content', encoding='utf-8')
            self.assertEqual(search(library, 'new')['matches'], [])
            updated = register(library, file, 'My notes', 'note')
            self.assertEqual(updated['reviewed_sections'], [])

    def test_pdf_registration_does_not_claim_read(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); file = root/'book.pdf'; file.write_bytes(b'%PDF test fixture')
            row = register(root/'library', file, 'Book', 'book')
            self.assertEqual(row['state'], 'registered')
            result = search(root/'library', 'Book')
            self.assertFalse(result['matches'])
            self.assertTrue(result['unavailable'])

    def test_non_utf8_rejected_before_registry_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); file = root/'bad.md'; file.write_bytes(b'\xff')
            with self.assertRaises(UnicodeDecodeError): register(root/'library', file, 'Bad', 'note')
            self.assertFalse((root/'library/manifest.json').exists())


class RigorTests(unittest.TestCase):
    def quiet(self, fn, *args):
        with contextlib.redirect_stdout(io.StringIO()): return fn(*args)

    def test_marketcap_discrepancy_and_zero(self):
        self.assertFalse(self.quiet(verify_market_cap, 10, 100, 980))
        self.assertFalse(self.quiet(verify_market_cap, 10, 100, 0))
        self.assertTrue(self.quiet(verify_market_cap, 10, 100, 1000))

    def test_negative_median_and_zero_cannot_pass(self):
        self.assertFalse(self.quiet(cross_validate, 'loss', {'a': -100, 'b': -120})['all_consistent'])
        self.assertFalse(self.quiet(cross_validate, 'loss', {'a': -1, 'b': 1})['all_consistent'])
        with self.assertRaises(ValueError): self.quiet(cross_validate, 'revenue', {'one': 100})


if __name__ == '__main__': unittest.main()
