"""Execute the named requirement regressions and retain real JUnit XML results."""
from datetime import datetime, timezone
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys
import time
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'code'))
sys.path.insert(0, str(ROOT / 'code/src'))
sys.path.insert(0, str(ROOT / 'code/tests'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.parent != ROOT / 'evidence' or output.suffix != '.xml':
        raise ValueError('Use a new XML test receipt directly under project evidence')
    if output.exists():
        raise ValueError('Preserve existing test evidence')
    manifest = json.loads((ROOT / 'code/docs/requirements_traceability_v2.json').read_text())
    anchors = {(row['path'], row['symbol']) for item in manifest['requirements'] for row in item['tests']}
    suite = unittest.TestSuite()
    for path, symbol in sorted(anchors):
        module = importlib.import_module(Path(path).stem)
        class_name, method = symbol.rsplit('.', 1)
        suite.addTest(getattr(module, class_name)(method))
    xml = ET.Element('testsuite', name='Executed requirement anchors', tests=str(len(anchors)))

    class Result(unittest.TextTestResult):
        def startTest(self, test):
            super().startTest(test)
            self.started = time.monotonic()

        def row(self, test):
            return ET.SubElement(xml, 'testcase', classname=test.id().rsplit('.', 1)[0],
                                 name=test.id().rsplit('.', 1)[1], time=str(time.monotonic() - self.started))

        def addSuccess(self, test):
            super().addSuccess(test)
            self.row(test)

        def addFailure(self, test, error):
            super().addFailure(test, error)
            ET.SubElement(self.row(test), 'failure').text = self._exc_info_to_string(error, test)

        def addError(self, test, error):
            super().addError(test, error)
            ET.SubElement(self.row(test), 'error').text = self._exc_info_to_string(error, test)

        def addSkip(self, test, reason):
            super().addSkip(test, reason)
            ET.SubElement(self.row(test), 'skipped').text = reason

    result = unittest.TextTestRunner(verbosity=0, resultclass=Result).run(suite)
    ET.ElementTree(xml).write(output, encoding='utf-8', xml_declaration=True)
    receipt = {'checked_utc': datetime.now(timezone.utc).isoformat(), 'tests_executed': result.testsRun,
               'passed': result.wasSuccessful() and not result.skipped, 'xml_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
               'scope': 'Named requirement regressions; overlaps broader CI suites and is not added to their totals.'}
    with output.with_suffix('.json').open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, indent=2)
    print(json.dumps(receipt))
    if not receipt['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
