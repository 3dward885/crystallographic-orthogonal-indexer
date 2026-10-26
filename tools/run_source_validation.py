"""Run source tests with workspace-local temporary files and method-level counts."""
import argparse
from datetime import datetime, timezone
import faulthandler
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest


class RecordedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.successes = []
        self.failed_methods = set()

    def addSuccess(self, test):
        self.successes.append(test.id())
        super().addSuccess(test)

    def addFailure(self, test, error):
        self.failed_methods.add(test.id())
        super().addFailure(test, error)

    def addError(self, test, error):
        self.failed_methods.add(test.id())
        super().addError(test, error)

    def addSubTest(self, test, subtest, error):
        if error is not None:
            self.failed_methods.add(test.id())
        super().addSubTest(test, subtest, error)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('baseline', 'regressions', 'all'), required=True)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    working = Path(__file__).resolve().parents[1]
    output = working / 'validation'
    output.mkdir(exist_ok=True)
    temporary = output / 'temporary'
    temporary.mkdir(exist_ok=True)
    tempfile.tempdir = str(temporary)
    os.environ['COI_VISIBLE_GUI_TESTS'] = '0'
    os.chdir(working)
    sys.path.insert(0, str(working))
    patterns = {'baseline': ('test_app.py', 'test_packaging.py'),
                'regressions': ('test_regressions.py',), 'all': ('test*.py',)}[args.mode]
    suite = unittest.TestSuite(unittest.defaultTestLoader.discover(str(working / 'tests'), pattern=pattern)
                               for pattern in patterns)
    log_path = output / (args.name + '.log')
    receipt_path = output / (args.name + '.json')
    if log_path.exists() or receipt_path.exists():
        raise RuntimeError('Refusing to overwrite existing validation evidence')
    with log_path.open('w', encoding='utf-8') as log:
        faulthandler.dump_traceback_later(45, exit=True, file=log)
        result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=RecordedResult).run(suite)
        faulthandler.cancel_dump_traceback_later()
    receipt = dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(), mode=args.mode,
                   run=result.testsRun, passed=len(result.successes), failed_methods=sorted(result.failed_methods),
                   failure_records=len(result.failures), error_records=len(result.errors),
                   skipped=[(str(test), reason) for test, reason in result.skipped],
                   successful=result.wasSuccessful() and not result.skipped,
                   python=sys.version, temporary_directory=str(temporary),
                   working_directory=str(working), method_count_note='Failure/error records can contain multiple failed subtests of one method.')
    receipt['visible_gui_tests'] = os.environ.get('COI_VISIBLE_GUI_TESTS') == '1'
    receipt['desktop_automation'] = False
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt, indent=2))
    return 0 if receipt['successful'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
