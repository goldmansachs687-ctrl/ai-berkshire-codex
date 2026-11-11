"""Regression tests for learning role isolation and durable artifact checks."""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/berkshire-team/scripts'))

import knowledge
from learning_media import srt_timestamp
from research_run import digest, save

if importlib.util.find_spec('langgraph'):
    from research_learning import now, run_learning
else:
    run_learning = None


class MediaTests(unittest.TestCase):
    def test_source_timestamp_carries_across_hour(self):
        self.assertEqual(srt_timestamp('00:59:59,900', 250), '01:00:00,150')
        self.assertEqual(srt_timestamp('00:00:10,900', 250, 10800), '00:00:10,800')

    def test_recording_registry_checks_original_and_transcript(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, index = root / 'clip.wav', root / 'index.txt'
            source.write_bytes(b'recording fixture')
            index.write_text('00:00:00,000 test')
            row = knowledge.register(root, source, 'Test', 'audio', index)
            self.assertTrue(knowledge.integrity(row))
            index.write_text('changed')
            self.assertFalse(knowledge.integrity(row))


@unittest.skipIf(run_learning is None, 'optional LangGraph runtime')
class GraphLearningTests(unittest.TestCase):
    def test_checkpoint_gates_and_seal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = ('case/question.md', 'case/evidence.md', 'grading/rubric.md')
            for name in (*files, 'submissions/A-before.md', 'submissions/B-before.md'):
                path = root / name
                path.parent.mkdir(exist_ok=True)
                path.write_text(name)
            seal = {name: digest(root / name) for name in files}
            save(root / 'seal.json', {'sealed_at': now(), 'files': seal})
            self.assertEqual(run_learning(root, 'init')['waiting'], 'before')
            self.assertEqual(run_learning(root, 'resume')['waiting'], 'before')

            def update(action, role, agent):
                return run_learning(root, action, stage='before', role=role, agent=agent, note='fixture')

            with self.assertRaisesRegex(ValueError, '先记录派工'):
                update('submit', 'A', 'agent-one')
            update('start', 'A', 'agent-one')
            with self.assertRaisesRegex(ValueError, '独立角色'):
                update('start', 'B', 'agent-one')
            self.assertEqual(update('submit', 'A', 'agent-one')['waiting'], 'before')
            update('start', 'B', 'agent-two')
            self.assertEqual(update('submit', 'B', 'agent-two')['waiting'], 'materials')
            (root / 'case/evidence.md').write_text('tampered')
            with self.assertRaisesRegex(ValueError, 'case/evidence.md'):
                run_learning(root, 'resume')
            (root / 'case/evidence.md').write_text('case/evidence.md')
            (root / 'submissions/A-before.md').write_text('tampered')
            with self.assertRaisesRegex(ValueError, 'A-before.md'):
                run_learning(root, 'resume')
