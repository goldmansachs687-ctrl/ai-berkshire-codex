#!/usr/bin/env python3
"""Run every packaged unittest suite in isolated processes; skips are failures in CI."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--suite');args=parser.parse_args()
    if args.suite:
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT/args.suite)))
        summary=dict(suite=args.suite,total=result.testsRun,passed=result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped)-len(result.expectedFailures)-len(result.unexpectedSuccesses),
                     failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),expected_failures=len(result.expectedFailures),unexpected_successes=len(result.unexpectedSuccesses))
        print('TEST_SUMMARY '+json.dumps(summary),flush=True)
        return 0 if result.wasSuccessful() and result.testsRun and not (result.skipped or result.expectedFailures) else 1
    suites=[ROOT/'tests',*sorted((ROOT/'plugins').glob('*/tests'))]
    codes=[]
    for suite in suites:
        codes.append(subprocess.run([sys.executable,str(Path(__file__).resolve()),'--suite',str(suite.relative_to(ROOT))],cwd=ROOT).returncode)
    return int(any(codes))


if __name__=='__main__':raise SystemExit(main())
