import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class ConfigurationCLI(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'repo'
        shutil.copytree(ROOT,self.root,ignore=shutil.ignore_patterns('.git','__pycache__','outputs'))
    def run_check(self,success):
        result=subprocess.run([sys.executable,str(ROOT/'scripts/check_plugins.py'),'--root',str(self.root)],capture_output=True,text=True)
        data=json.loads(result.stdout)
        self.assertEqual(result.returncode,0 if success else 1,data)
        self.assertEqual(data['status'],'PASS' if success else 'FAIL')
        return data
    def mutate(self,name,fn):
        p=self.root/name;d=json.loads(p.read_text());fn(d);p.write_text(json.dumps(d))
    def test_multiple_plugin_versions_are_valid(self):
        data=self.run_check(True);self.assertEqual(data['plugins'],{'berkshire-team':'2.2.9','ai-value-investing-agents':'1.2.1'})
    def test_corrupt_json_fails_real_cli(self):
        (self.root/'plugins/berkshire-team/plugin.json').write_text('{broken');self.run_check(False)
    def test_same_plugin_version_mismatch_fails_real_cli(self):
        self.mutate('plugins/berkshire-team/.codex-plugin/plugin.json',lambda d:d.update(version='9.9.9'));self.run_check(False)
    def test_readme_version_mismatch_fails(self):
        p=self.root/'README.md';p.write_text(p.read_text().replace('Berkshire Team 2.2.9','Berkshire Team 9.9.9'));self.run_check(False)
    def test_missing_required_field_fails(self):
        self.mutate('plugins/berkshire-team/plugin.json',lambda d:d.pop('description'));self.run_check(False)
    def test_marketplace_path_and_entry_fail(self):
        self.mutate('.agents/plugins/marketplace.json',lambda d:d['plugins'][0]['source'].update(path='./plugins/missing'));self.run_check(False)
    def test_skill_entrypoint_missing_fails(self):
        # Fixed skills path still exists; missing named main skill must be detected via references/entrypoint invariant.
        (self.root/'plugins/berkshire-team/skills/berkshire-team/SKILL.md').unlink();self.run_check(False)
    def test_critical_reference_missing_fails(self):
        (self.root/'plugins/berkshire-team/skills/berkshire-team/references/valuation.md').unlink();self.run_check(False)
    def test_manifest_asset_missing_fails(self):
        (self.root/'plugins/berkshire-team/assets/berkshire.svg').unlink();self.run_check(False)
    def test_corrupt_yaml_and_duplicate_keys_fail(self):
        path=self.root/'plugins/berkshire-team/skills/berkshire-team/agents/openai.yaml'
        path.write_text('interface: [broken');self.run_check(False)
        path.write_text('interface: {}\ninterface: {}');self.run_check(False)
    def test_upstream_version_distinct_but_local_version_consistent(self):
        self.mutate('plugins/ai-value-investing-agents/UPSTREAM.json',lambda d:d.update(local_package_version='1.2.0'));self.run_check(False)
    def test_test_runner_rejects_skipped_tests(self):
        p=self.root/'skip_fixture';p.mkdir();(p/'test_skip.py').write_text('import unittest\nclass Skip(unittest.TestCase):\n @unittest.skip("intentional fixture")\n def test_skip(self): pass\n')
        result=subprocess.run([sys.executable,str(self.root/'scripts/run_tests.py'),'--suite','skip_fixture'],capture_output=True,text=True)
        self.assertEqual(result.returncode,1);self.assertIn('"skipped": 1',result.stdout)
    def test_runner_rejects_missing_original_suite(self):
        shutil.rmtree(self.root/'plugins/berkshire-team/tests')
        result = subprocess.run([sys.executable, str(self.root/'scripts/run_tests.py')],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn('Missing required test suites: plugins/berkshire-team/tests', result.stderr)
    def test_workflow_push_pull_request_no_ignored_failure(self):
        # BaseLoader keeps GitHub's YAML 1.2 `on` key as a string.
        import yaml
        data=yaml.load((self.root/'.github/workflows/ci.yml').read_text(),Loader=yaml.BaseLoader)
        self.assertEqual(set(data['on']),{'push','pull_request'})
        steps=data['jobs']['test']['steps'];commands=[s['run'] for s in steps if 'run' in s]
        self.assertIn('python scripts/run_tests.py',commands);self.assertIn('python scripts/check_plugins.py',commands)
        self.assertNotIn('continue-on-error',(self.root/'.github/workflows/ci.yml').read_text())


if __name__=='__main__':unittest.main()
