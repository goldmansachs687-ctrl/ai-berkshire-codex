"""Keep the selected report language through every debate worker turn."""

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/berkshire-team/scripts'
sys.path.insert(0, str(SCRIPTS))

from research_live_debate import Debate, FIELDS


class DebateLanguageTest(unittest.TestCase):
    def test_each_worker_turn_receives_the_selected_language(self):
        for requested, expected in [('English', 'English'), ('简体中文', '简体中文'),
                                    (None, 'Simplified Chinese')]:
            with self.subTest(language=requested), TemporaryDirectory() as temporary:
                root = Path(temporary)
                brief = {
                    'facts': 'Evidence for the test',
                    'issues': [{'dispute_id': 'cash', 'topic': 'Cash conversion'}],
                    'sources': {},
                }
                if requested is not None:
                    brief['output_language'] = requested
                (root / 'debate-brief.json').write_text(json.dumps(brief), encoding='utf-8')

                def worker(instruction, inputs, fields, session, started):
                    self.assertIn(f'Output language: {expected}.', instruction)
                    self.assertIn('Keep verbatim quotes', instruction)
                    row = dict.fromkeys(fields, 'exact quote')
                    row.update(dispute_id='cash')
                    if 'decision' in fields:
                        row.update(decision='accept', target='none', instruction='')
                    return {'rows': [row], 'agent_id': 'test-worker'}

                debate = Debate(root, worker)
                for step in FIELDS:
                    role = 'independent_review' if step == 'review' else 'bull_case'
                    _, rows = debate.turn(step, role, {'opposing_opening': 'An exact quote.'}, ['cash'])
                    self.assertIn('cash', rows)
