#!/usr/bin/env python3
"""Run every packaged unittest suite in isolated processes; skips are failures in CI."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
REQUIRED_SUITES = ('tests', 'plugins/berkshire-team/tests')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--suite');args=parser.parse_args()
    if args.suite:
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT/args.suite)))
        summary=dict(suite=args.suite,total=result.testsRun,passed=result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped)-len(result.expectedFailures)-len(result.unexpectedSuccesses),
                     failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),expected_failures=len(result.expectedFailures),unexpected_successes=len(result.unexpectedSuccesses))
        print('TEST_SUMMARY '+json.dumps(summary),flush=True)
        return 0 if result.wasSuccessful() and result.testsRun and not (result.skipped or result.expectedFailures) else 1
    required = [ROOT / name for name in REQUIRED_SUITES]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_dir()]
    if missing:
        print('Missing required test suites: ' + ', '.join(missing), file=sys.stderr)
        return 1
    extra = sorted(path for path in (ROOT / 'plugins').glob('*/tests') if path not in required)
    suites = required + extra
    codes=[]
    for suite in suites:
        codes.append(subprocess.run([sys.executable,str(Path(__file__).resolve()),'--suite',str(suite.relative_to(ROOT))],cwd=ROOT).returncode)
    return int(any(codes))


if __name__=='__main__':raise SystemExit(main())
