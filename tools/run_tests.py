"""Machine-readable test receipt; Windows release builds may not skip native QA."""
from pathlib import Path
import argparse
import json
import sys
import unittest

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
parser = argparse.ArgumentParser()
parser.add_argument('--out', required=True)
parser.add_argument('--require-native', action='store_true')
args = parser.parse_args()
suite = unittest.defaultTestLoader.discover(str(root/'tests'))
result = unittest.TextTestRunner(verbosity=2).run(suite)
receipt = {'run':result.testsRun, 'failures':len(result.failures), 'errors':len(result.errors),
           'skipped':[(str(test),reason) for test,reason in result.skipped],
           'passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
           'native_required':args.require_native}
Path(args.out).write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
sys.exit(0 if result.wasSuccessful() and (not args.require_native or not result.skipped) else 1)
