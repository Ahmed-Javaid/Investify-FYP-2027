"""Check requirement/source/test anchors against an actual selected-suite receipt."""
import argparse
import ast
import hashlib
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'code/docs/requirements_traceability.json'


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
    if args.markdown and not args.markdown.resolve().is_relative_to(ROOT / 'deliverables'):
        raise ValueError('Traceability Markdown must remain under deliverables')
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
    if ids != {f'MID-FR-{i:02d}' for i in range(1, 19)}:
        raise ValueError('Traceability must cover the declared 18 engineering requirements')
    report = {'schema': 'investify-requirements-traceability-receipt-v1',
              'checked_utc': datetime.now(timezone.utc).isoformat(),
              'requirements_checked': len(rows), 'selected_tests_passed': len(cases),
              'test_receipt': str(args.tests.resolve().relative_to(ROOT)),
              'test_receipt_sha256': hashlib.sha256(args.tests.read_bytes()).hexdigest(),
              'source_sha256': hashes, 'requirements': rows,
              'scope': manifest['scope'], 'institutional_acceptance_claimed': False}
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    if args.markdown:
        lines = ['# Current requirements, source and test traceability', '', manifest['scope'], '',
                 f'The matching receipt checks **{len(rows)} requirement IDs** against source symbols and named passing tests '
                 f'in the **{len(cases)}-test** selected suite. These are existence/execution checks, not a test-coverage '
                 'percentage or supervisor acceptance.', '',
                 f'[Matching dated receipt](../evidence/{output.name}). Re-run the checker after changing anchors or source; '
                 'an older receipt proves its matching hashes only.', '',
                 '| ID / acceptance criterion | Source and actual passing regression | Evidence boundary |',
                 '| --- | --- | --- |']
        for row in rows:
            anchors = [f"[{a['symbol']}](../{a['path']}#L{a['line']})" for a in row['checked_anchors']]
            lines.append(f"| {row['id']}: {row['acceptance']} | " + '<br>'.join(anchors) + f" | {row['evidence_boundary']} |")
        lines += ['', '## Original first-mid commitments', '',
                  '| Proposal commitment | Current source/evidence | Still needed |', '| --- | --- | --- |',
                  '| Ingestion, two calendars, indicators and news sentiment | Historical ingest/features/calendar/store modules and saved results; structural input preflight | Original data/cache and scientific runtime; fresh ingestion-to-feature run and current scientific tests. |',
                  '| Interpretable linear baseline end to end | Separate saved-feature profile comparator is checked | Complete ingestion-to-linear-baseline run; the retrospective comparator does not reproduce it. |',
                  '| Social-model selection | 200 acquired posts, 117 frozen AI references; validated runners/evaluator | Actual paired original candidate inference and scoped selection or declared news-only deviation. |',
                  '| Leakage suite and deliberate mutation | Historical harness results and current UI refusal | Fresh scientific suite and actual canary run; portable explanation checks are a separate suite. |',
                  '| Thin interface slice | Actual Streamlit widgets and portable endpoints, failure/fallback paths | Live supervisor demonstration, browser visual review and genuine student defence. |',
                  '| Baselined requirements/design | Engineering anchors above, report/figure sources | Full-proposal reconciliation, institutional metadata/review, compilation and rendered QA. |', '',
                  'The teacher pilot advances later research and addresses the worked-explanation discussion. '
                  'QLoRA is not a first-mid prerequisite. Team ownership, agreed dates, meeting records and approvals '
                  'are pending genuine inputs; this matrix assigns none.', '']
        args.markdown.write_text('\n'.join(lines), encoding='utf-8')
    print(f'Traceability: {len(rows)} requirement IDs, {len(cases)} passing selected tests; source/test anchors verified')


if __name__ == '__main__':
    main()
