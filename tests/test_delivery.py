import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from make_delivery_examples import example, load, save, review, SCRIPTS, ROLES


class DeliveryCLI(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = example(self.temp.name)

    def run_gate(self, status, root=None):
        root = root or self.root
        result = subprocess.run([sys.executable, str(SCRIPTS/'delivery_gate.py'), '--run', str(root), '--json'], capture_output=True, text=True)
        data = json.loads(result.stdout)
        self.assertEqual(data['status'], status, data)
        self.assertEqual(result.returncode, {'COMPLETE':0,'LIMITED':2,'BLOCKED':1}[status], result.stderr)
        return data

    def test_complete_real_cli(self):
        data=self.run_gate('COMPLETE')
        self.assertEqual(data['evidence_gate']['verdict'],'PASS')
        self.assertEqual(data['model_checks'][0]['recomputed'],'1000')
        result=subprocess.run([sys.executable,str(SCRIPTS/'delivery_gate.py'),'--run',str(self.root)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0);self.assertIn('COMPLETE (exit 0)',result.stdout)

    def test_pending_empty_evidence_fake_complete_review_blocked(self):
        data=self.run_gate('BLOCKED',example(self.temp.name,'blocked'))
        self.assertEqual(data['evidence_gate']['verdict'],'INCOMPLETE')
        self.assertTrue(any(i['check']=='workflow.business_analyst' for i in data['issues']))

    def test_objective_gap_limited_real_cli(self):
        data=self.run_gate('LIMITED',example(self.temp.name,'limited'))
        self.assertEqual(data['evidence_gate']['verdict'],'INCOMPLETE')
        self.assertEqual(data['issues'][0]['severity'],'limitation')

    def test_conflicting_sources_cannot_be_limited(self):
        ledger=load(self.root,'evidence.json');obs=dict(ledger['claims'][0]['observations'][0],value=80,source='https://example.org/other')
        ledger['claims'][0]['observations'].append(obs);save(self.root,'evidence.json',ledger);review(self.root)
        data=self.run_gate('BLOCKED');self.assertEqual(data['evidence_gate']['verdict'],'FAIL')

    def test_reconciled_period_currency_basis_can_complete(self):
        ledger=load(self.root,'evidence.json');obs=dict(ledger['claims'][0]['observations'][0],source='https://example.org/other',
            normalization='FY2025 revenue EUR million 80 converted at documented 1.25 USD/EUR; same GAAP basis.',local_file='reconciliation.json')
        ledger['claims'][0]['observations'].append(obs)
        save(self.root,'reconciliation.json',dict(original_value=80,original_currency='EUR',normalized_value=100,rate=1.25,period='FY2025',basis='GAAP'))
        save(self.root,'evidence.json',ledger)
        challenge=load(self.root,'challenges.json');challenge['disagreements']=[dict(material=True,status='resolved',resolution='Period and basis match; currency converted with preserved record.',evidence=['reconciliation.json'])]
        save(self.root,'challenges.json',challenge);review(self.root);self.run_gate('COMPLETE')
        (self.root/'reconciliation.json').unlink();self.run_gate('BLOCKED')

    def test_each_content_change_invalidates_review(self):
        for name in ('report.md','evidence.json','model.py','inputs.json','valuation-result.json','source.md','review.md','review.json','delivery.json','challenges.json'):
            with self.subTest(file=name):
                original=(self.root/name).read_bytes();(self.root/name).write_bytes(original+b'\n')
                data=self.run_gate('BLOCKED');self.assertTrue(any(i['check']=='review.binding' for i in data['issues']))
                (self.root/name).write_bytes(original)
        self.run_gate('COMPLETE')

    def test_missing_empty_corrupt_and_broken_references_block(self):
        for name,content in [('model.py',None),('inputs.json',None),('inputs.json',b''),('inputs.json',b'{bad'),('model.py',b'def broken('),
                             ('review.md',b'   '),('report.md',b'[missing](missing.md)'),('inputs.json',b'{"revenue":100,"revenue":200}')]:
            with self.subTest(file=name,content=content):
                original=(self.root/name).read_bytes()
                if content is None:(self.root/name).unlink()
                else:(self.root/name).write_bytes(content)
                data=self.run_gate('BLOCKED');self.assertTrue(any(name in i['reason'] or i['check'] in ('dependencies','model','review') for i in data['issues']))
                (self.root/name).write_bytes(original)

    def test_reviewer_same_as_participant_or_missing_records(self):
        state=load(self.root,'run.json');state['roles']['independent_review']['agent_id']='fixture-business_analyst';save(self.root,'run.json',state)
        self.run_gate('BLOCKED')
        (self.root/'review.json').unlink();self.run_gate('BLOCKED')

    def test_missing_reviewer_checkpoint_rejected(self):
        result=subprocess.run([sys.executable,str(SCRIPTS/'research_run.py'),'checkpoint','--run',str(self.root),'--role','independent_review','--status','complete','--file','review.md','--note','reviewed'],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0);self.assertIn('reviewer agent ID',result.stderr)

    def test_review_checkpoint_automatically_binds_model_inputs(self):
        state=load(self.root,'run.json');record=state['roles']['independent_review']
        paths={a['path'] for a in record['artifacts']}
        self.assertTrue({'model.py','inputs.json','valuation.json','valuation-result.json','source.md'} <= paths)
        result=subprocess.run([sys.executable,str(SCRIPTS/'research_run.py'),'checkpoint','--run',str(self.root),'--role','independent_review','--status','complete','--file','review.md','--note','Synthetic explicit re-review','--agent-id','fixture-reviewer'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);self.run_gate('COMPLETE')

    def test_stable_read_only_and_output_not_dependency(self):
        before={p.name:p.read_bytes() for p in self.root.iterdir()}
        first=self.run_gate('COMPLETE')
        (self.root/'delivery-result.json').write_text(json.dumps(first))
        self.assertEqual(first,self.run_gate('COMPLETE'))
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.root.iterdir() if p.name!='delivery-result.json'})
        state=load(self.root,'run.json');state['updated_at']='different time';save(self.root,'run.json',state)
        self.assertEqual(first,self.run_gate('COMPLETE'))

    def test_dependency_list_and_role_identity_changes_invalidate_review(self):
        state=load(self.root,'run.json');state['roles']['business_analyst']['agent_id']='other';save(self.root,'run.json',state)
        self.run_gate('BLOCKED')

    def test_research_cutoff_change_invalidates_review(self):
        state=load(self.root,'run.json');state['as_of']='2026-02-01';save(self.root,'run.json',state)
        self.run_gate('BLOCKED')

    def test_qualitative_brief_needs_no_model(self):
        self.run_gate('COMPLETE',example(self.temp.name,'qualitative'))

    def test_unknown_used_number_and_other_incomplete_block(self):
        for mutation in ('locator','unknown','required_absent','reclassified'):
            with self.subTest(mutation=mutation):
                ledger=load(self.root,'evidence.json');original=json.loads(json.dumps(ledger))
                if mutation=='locator':del ledger['claims'][0]['observations'][0]['locator']
                elif mutation=='unknown':ledger['claims'][0]['reported_value']=None
                elif mutation=='required_absent':ledger['required_claims'].append('missing')
                else:ledger['claims'][0].update(kind='assumption',rationale='fake')
                save(self.root,'evidence.json',ledger);review(self.root);self.run_gate('BLOCKED')
                save(self.root,'evidence.json',original);review(self.root)

    def test_model_recomputed_not_handwritten_passed(self):
        save(self.root,'valuation-result.json',dict(value=1200,status='passed'));review(self.root)
        data=self.run_gate('BLOCKED');self.assertTrue(any('recomputation mismatch' in i['reason'] for i in data['issues']))

    def test_major_unresolved_conflict_blocks_even_evidence_pass(self):
        c=load(self.root,'challenges.json');c['disagreements']=[dict(material=True,status='open',resolution='',evidence=['source.md'])]
        save(self.root,'challenges.json',c);review(self.root)
        data=self.run_gate('BLOCKED');self.assertEqual(data['evidence_gate']['verdict'],'PASS')

    def test_limited_missing_disclosure_or_review_ack_blocks(self):
        root=example(self.temp.name,'limited');r=load(root,'review.json');r['acknowledged_limitations']=[];save(root,'review.json',r);review(root)
        self.run_gate('BLOCKED',root)

    def test_full_research_cannot_disable_model(self):
        c=load(self.root,'delivery.json');c['valuation']=dict(required=False,reason='skip');save(self.root,'delivery.json',c);review(self.root)
        self.run_gate('BLOCKED')

    def test_symlink_and_output_dependency_rejected(self):
        (self.root/'inputs.json').rename(self.root/'actual.json');(self.root/'inputs.json').symlink_to('actual.json')
        self.run_gate('BLOCKED')

    def test_qualitative_scope_cannot_hide_numeric_valuation(self):
        root=example(self.temp.name,'qualitative')
        for report in ('Synthetic fair value 100 USD. [Source](source.md)\n',
                       '目标价\n每股 500 美元。\n',
                       '| **目标价** | $500 |\n'):
            with self.subTest(report=report):
                (root/'report.md').write_text(report, encoding='utf-8')
                review(root)
                data = self.run_gate('BLOCKED', root)
                self.assertTrue(any(i['check'] == 'model' for i in data['issues']))

    def test_valuation_disclaimer_with_historical_figures_is_qualitative(self):
        root = example(self.temp.name, 'qualitative')
        (root/'report.md').write_text('本简报不提供估值；2025 年现金收益为 50 百万美元。\n', encoding='utf-8')
        review(root)
        self.run_gate('COMPLETE', root)

    def test_null_claim_with_conflicting_observations_is_not_an_objective_gap(self):
        root = example(self.temp.name, 'limited')
        ledger = load(root, 'evidence.json')
        history = next(c for c in ledger['claims'] if c['id'] == 'history')
        observation = ledger['claims'][0]['observations'][0]
        history['observations'] = [dict(observation, value=80, source='https://example.org/first'),
                                   dict(observation, value=160, source='https://example.org/second')]
        history['reported_value'] = 80
        save(root, 'evidence.json', ledger)
        review(root)
        self.assertEqual(self.run_gate('BLOCKED', root)['evidence_gate']['verdict'], 'FAIL')
        history['reported_value'] = None
        save(root, 'evidence.json', ledger)
        review(root)
        data = self.run_gate('BLOCKED', root)
        self.assertEqual(data['evidence_gate']['verdict'], 'INCOMPLETE')
        self.assertTrue(any('history: source values already exist' in i['reason'] for i in data['issues']))

    def test_blank_and_non_text_challenge_records_block(self):
        challenge = load(self.root, 'challenges.json')
        for record in (dict(question=' \t ', response='\n '), dict(question=True, response=42)):
            with self.subTest(record=record):
                challenge['questions'][0].update(record)
                save(self.root, 'challenges.json', challenge)
                review(self.root)
                data = self.run_gate('BLOCKED')
                self.assertTrue(any(i['check'] == 'challenges' for i in data['issues']))

    def test_html_source_is_bound_and_change_or_deletion_blocks(self):
        source = self.root/'filing.html'
        source.write_text('<html><p>Revenue 100</p></html>', encoding='utf-8')
        ledger = load(self.root, 'evidence.json')
        ledger['claims'][0]['observations'][0]['source'] = source.name
        save(self.root, 'evidence.json', ledger)
        review(self.root)
        data = self.run_gate('COMPLETE')
        self.assertIn(source.name, {dep['path'] for dep in data['dependencies']})
        source.write_text('<html><p>Revenue 50</p></html>', encoding='utf-8')
        self.run_gate('BLOCKED')
        source.unlink()
        self.run_gate('BLOCKED')

    def test_unrecognized_local_source_is_not_silently_ignored(self):
        source = self.root/'filing.unknown'
        source.write_text('Revenue 100', encoding='utf-8')
        ledger = load(self.root, 'evidence.json')
        ledger['claims'][0]['observations'][0]['source'] = source.name
        save(self.root, 'evidence.json', ledger)
        data = self.run_gate('BLOCKED')
        self.assertTrue(any('unsupported dependency format' in i['reason'] for i in data['issues']))

    def test_resolved_challenge_can_link_to_parent_inside_run(self):
        notes = self.root/'notes'
        notes.mkdir()
        reconciliation = notes/'reconciliation.md'
        reconciliation.write_text('Reconciled period and units. [Original](../source.md)\n', encoding='utf-8')
        challenge = load(self.root, 'challenges.json')
        challenge['disagreements'] = [dict(material=True, status='resolved', resolution='Same reporting period.',
                                           evidence=['notes/reconciliation.md'])]
        save(self.root, 'challenges.json', challenge)
        review(self.root)
        data = self.run_gate('COMPLETE')
        paths = {dep['path'] for dep in data['dependencies']}
        self.assertIn('source.md', paths)
        self.assertFalse(any('..' in Path(path).parts for path in paths))
        for target, reason in (('../../source.md', 'path must stay inside run'),
                               ('alias/../../source.md', 'symlink dependency forbidden')):
            with self.subTest(target=target):
                if target.startswith('alias'):
                    (notes/'alias').symlink_to(self.root, target_is_directory=True)
                reconciliation.write_text(f'[Original]({target})\n', encoding='utf-8')
                blocked = self.run_gate('BLOCKED')
                self.assertTrue(any(reason in i['reason'] for i in blocked['issues']))

    def test_missing_key_input_and_invalid_pointer_block(self):
        original=(self.root/'valuation.json').read_bytes()
        manifest=load(self.root,'valuation.json');manifest['key_inputs']=[]
        save(self.root,'valuation.json',manifest);review(self.root);self.run_gate('BLOCKED')
        (self.root/'valuation.json').write_bytes(original)
        manifest=load(self.root,'valuation.json');manifest['key_inputs'][0]['pointer']='/missing'
        save(self.root,'valuation.json',manifest);review(self.root);self.run_gate('BLOCKED')

    def test_recursive_dependency_change_and_removal_block(self):
        manifest=load(self.root,'valuation.json');manifest['dependencies']=['calibration.json']
        save(self.root,'calibration.json',dict(dependencies=['calibration-source.md'],note='Synthetic calibration'))
        (self.root/'calibration-source.md').write_text('Source for calibration.')
        save(self.root,'valuation.json',manifest);review(self.root);self.run_gate('COMPLETE')
        (self.root/'calibration-source.md').write_text('Replaced calibration source.');self.run_gate('BLOCKED')
        (self.root/'calibration-source.md').unlink();self.run_gate('BLOCKED')

    def test_acceptance_output_cannot_be_declared_as_dependency(self):
        save(self.root,'delivery-result.json',dict(status='COMPLETE'))
        c=load(self.root,'delivery.json');c['dependencies']=['delivery-result.json'];save(self.root,'delivery.json',c)
        self.run_gate('BLOCKED')

    def test_invalid_source_reference_and_local_digest_block(self):
        ledger=load(self.root,'evidence.json');original=json.loads(json.dumps(ledger))
        ledger['claims'][0]['observations'][0]['source']='https://'
        save(self.root,'evidence.json',ledger);self.run_gate('BLOCKED')
        original['claims'][0]['observations'][0].update(local_file='source.md',source_sha256='a'*64)
        save(self.root,'evidence.json',original);self.run_gate('BLOCKED')

    def test_malformed_run_and_contract_fail_closed(self):
        for name, value in [('run.json',{'roles':[]}),('delivery.json',{'schema_version':1,'valuation':None})]:
            with self.subTest(file=name):
                old=(self.root/name).read_bytes();save(self.root,name,value);self.run_gate('BLOCKED');(self.root/name).write_bytes(old)


if __name__=='__main__':unittest.main()
