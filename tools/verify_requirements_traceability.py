"""Check requirement/source/test anchors against an actual selected-suite receipt."""
import argparse
import ast
import hashlib
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'code/docs/requirements_traceability_v2.json'


def symbols(path):
    result = {}
    def visit(nodes, prefix=''):
        for node in nodes:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                name = prefix + node.name
                result[name] = node.lineno
                if isinstance(node, ast.ClassDef):
                    visit(node.body, name + '.')
    visit(ast.parse(path.read_text(encoding='utf-8-sig')).body)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tests', type=Path, default=ROOT / 'evidence/current_tests.xml')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--markdown', type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / 'evidence') or output.exists():
        raise ValueError('Use a new evidence receipt')
    if args.markdown and args.markdown.resolve() != ROOT / 'docs/technical/REQUIREMENTS.md':
        raise ValueError('Update the consolidated technical requirements document')
    xml = ET.parse(args.tests)
    cases = xml.findall('.//testcase')
    if not cases or any(xml.findall('.//' + tag) for tag in ('failure', 'error', 'skipped')):
        raise ValueError('Require a complete passing selected-suite receipt')
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    hashes = {str(MANIFEST.relative_to(ROOT)): hashlib.sha256(MANIFEST.read_bytes()).hexdigest()}
    ids, rows = set(), []
    for requirement in manifest['requirements']:
        if requirement['id'] in ids:
            raise ValueError('Duplicate requirement ID')
        ids.add(requirement['id'])
        row = dict(requirement, checked_anchors=[])
        for kind in ('implementation', 'tests'):
            for anchor in requirement[kind]:
                path = (ROOT / anchor['path']).resolve()
                if not path.is_relative_to(ROOT / 'code') or not path.is_file():
                    raise ValueError(f'Invalid source anchor: {anchor}')
                line = symbols(path).get(anchor['symbol'])
                if line is None:
                    raise ValueError(f'Missing symbol: {anchor}')
                hashes[anchor['path']] = hashlib.sha256(path.read_bytes()).hexdigest()
                executed = None
                if kind == 'tests':
                    module = path.stem
                    class_name, method = anchor['symbol'].rsplit('.', 1)
                    matches = [case for case in cases if
                               case.get('classname', '').endswith(module + '.' + class_name)
                               and case.get('name') == method]
                    if len(matches) != 1:
                        raise ValueError(f'Test anchor not executed exactly once in receipt: {anchor}')
                    executed = True
                row['checked_anchors'].append(dict(anchor, kind=kind, line=line, executed_pass=executed))
        rows.append(row)
    if ids != {f'MID-FR-{i:02d}' for i in range(1, 24)}:
        raise ValueError('Traceability must cover the declared 23 engineering requirements')
    report = {'schema': 'investify-requirements-traceability-receipt-v1',
              'checked_utc': datetime.now(timezone.utc).isoformat(),
              'requirements_checked': len(rows), 'selected_tests_passed': len(cases),
              'test_receipt': str(args.tests.resolve().relative_to(ROOT)),
              'test_receipt_sha256': hashlib.sha256(args.tests.read_bytes()).hexdigest(),
              'source_sha256': hashes, 'requirements': rows,
              'scope': manifest['scope'], 'institutional_acceptance_claimed': False}
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    if args.markdown:
        path = args.markdown.resolve()
        def link(relative):
            return os.path.relpath(ROOT / relative, path.parent).replace(chr(92), '/')
        lines = [f'Checked {len(rows)} IDs against source symbols and {len(cases)} passing tests in '
                 f'[the dated input receipt]({link(args.tests.resolve().relative_to(ROOT))}). '
                 'This is anchor execution, not coverage or institutional acceptance.', '',
                 f'[Matching checker receipt]({link(output.relative_to(ROOT))}).', '',
                 '| ID / acceptance | Source and named passing regression | Evidence boundary |',
                 '| --- | --- | --- |']
        for row in rows:
            anchors = [f"[{anchor['symbol']}]({link(anchor['path'])}#L{anchor['line']})"
                       for anchor in row['checked_anchors']]
            lines.append(f"| {row['id']}: {row['acceptance']} | " + '<br>'.join(anchors)
                         + f" | {row['evidence_boundary']} |")
        start, end = '<!-- REQUIREMENT_ANCHORS_START -->', '<!-- REQUIREMENT_ANCHORS_END -->'
        content = path.read_text(encoding='utf-8')
        if content.count(start) != 1 or content.count(end) != 1:
            raise ValueError('The consolidated requirements document needs one anchor block')
        first, rest = content.split(start, 1)
        _, last = rest.split(end, 1)
        path.write_text(first + start + '\n\n' + '\n'.join(lines) + '\n\n' + end + last, encoding='utf-8')
    print(f'Traceability: {len(rows)} requirement IDs, {len(cases)} passing selected tests; source/test anchors verified')


if __name__ == '__main__':
    main()
