"""Refresh local syntax/test/runtime receipts without claiming rendered QA."""
import ast
import argparse
import hashlib
import importlib.metadata
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'
EVIDENCE = ROOT / 'evidence'
checked = datetime.now(timezone.utc).isoformat()
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--previous-count', type=int, help='Replace this obsolete selected-suite count in current status documents')
args = parser.parse_args()
xml = ET.parse(EVIDENCE / 'current_tests.xml')
cases = xml.findall('.//testcase')
if not cases or xml.findall('.//failure') or xml.findall('.//error') or xml.findall('.//skipped'):
    raise ValueError('Current selected test receipt is empty, failing or skipped')
ui_cases = [case for case in cases if 'StreamlitMidEvalTests' in case.get('classname', '')]
if args.previous_count is not None:
    current_docs = ['README.md', 'planning/CHECKPOINT.md', 'planning/MID_EVAL_PLAN.md',
                    'deliverables/MODELS_AND_EVALUATION.md', 'deliverables/presentation_outline.json',
                    'deliverables/HANDOVER_GUIDE.md', 'planning/NEXT_CHAT.md',
                    'code/README.md', 'code/docs/mideval_increment.md',
                    'report/chapters/04_abstract.tex', 'report/chapters/06_executive_summary.tex',
                    'report/chapters/conclusion.tex', 'report/chapters/chapter3_iteration_plan.tex', 'report/chapters/chapter6_iteration1.tex',
                    'report/chapters/chapter8_testing.tex', 'report/chapters/chapter9_development_evidence.tex',
                    'report/chapters/appendix_test_cases.tex']
    for relative in current_docs:
        path = ROOT / relative
        original = path.read_text(encoding='utf-8-sig')
        text = re.sub(r'\b' + str(args.previous_count) + r'\b', str(len(cases)), original)
        count_word = {8: 'eight', 10: 'ten', 12: 'twelve'}.get(len(ui_cases), str(len(ui_cases)))
        text = re.sub(r'\b(eight|ten|twelve|Eight|Ten|Twelve) actual (Streamlit|AppTest)',
                      lambda match: (count_word.capitalize() if match.group(1)[0].isupper() else count_word)
                      + ' actual ' + match.group(2), text)
        text = re.sub(r'\b(?:8|10|12|13|15) actual (cases|Streamlit)', lambda match: str(len(ui_cases)) + ' actual ' + match.group(1), text)
        text = re.sub(r'(Streamlit AppTest & )\d+( tests)', lambda match: match.group(1) + str(len(ui_cases)) + match.group(2), text)
        if text != original:
            path.write_text(text, encoding='utf-8')
python_files = sorted([*CODE.rglob('*.py'), *(ROOT / 'tools').rglob('*.py')])
for path in python_files:
    ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))

report = ROOT / 'report'
tex_files = sorted(report.rglob('*.tex'))
keys = set(re.findall(r'@\w+\s*\{\s*([^,]+),', (report / 'references/references.bib').read_text()))
main_source = (report / 'main.tex').read_text(encoding='utf-8-sig')
for command in ('projecttitle', 'studentone', 'studenttwo', 'studentthree'):
    if not re.search(r'\\newcommand\{\\' + command + r'\}', main_source):
        raise ValueError(f'Undefined custom front-matter macro: {command}')
for path in tex_files:
    text = re.sub(r'(?<!\\)%[^\n]*', '', path.read_text(encoding='utf-8-sig'))
    for target in re.findall(r'\\(?:input|include)\{([^}]+)\}', text):
        target_path = report / target
        if not target_path.suffix:
            target_path = target_path.with_suffix('.tex')
        if not target_path.exists():
            raise ValueError(f'Missing TeX input {target!r} in {path.name}')
    for citation in re.findall(r'\\cite(?:p|t)?(?:\[[^]]*\])*\{([^}]+)\}', text):
        if set(citation.split(',')) - keys:
            raise ValueError(f'Undefined citation in {path.name}: {citation}')
    environments = []
    for action, name in re.findall(r'\\(begin|end)\{([^}]+)\}', text):
        if action == 'begin':
            environments.append(name)
        elif not environments or environments.pop() != name:
            raise ValueError(f'Unbalanced environment in {path.name}')
    if environments:
        raise ValueError(f'Unclosed environment in {path.name}')
    braces = re.sub(r'\\[{}]', '', text)
    balance = 0
    for character in braces:
        balance += (1 if character == '{' else -1 if character == '}' else 0)
        if balance < 0:
            raise ValueError(f'Unbalanced braces in {path.name}')
    if balance:
        raise ValueError(f'Unclosed brace in {path.name}')

sources = [*python_files, *tex_files, report / 'references/references.bib', CODE / 'app/mideval_demo.html']
syntax = {'checked_utc': checked, 'python_files_parsed': len(python_files), 'tex_sources_checked': len(tex_files),
          'checks': ['Python AST', 'TeX input existence', 'Citation-key existence', 'TeX environment/brace balance', 'Custom front-matter macro definitions'],
          'latex_compiled': False, 'rendered_visual_qa': False,
          'source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}}
(EVIDENCE / 'source_syntax_verification.json').write_text(json.dumps(syntax, indent=2), encoding='utf-8')

xml = ET.parse(EVIDENCE / 'current_tests.xml')
cases = xml.findall('.//testcase')
if not cases or xml.findall('.//failure') or xml.findall('.//error') or xml.findall('.//skipped'):
    raise ValueError('Current selected test receipt is empty, failing or skipped')
ui_cases = [case for case in cases if 'StreamlitMidEvalTests' in case.get('classname', '')]
opener = build_opener(ProxyHandler({}))
with opener.open('http://127.0.0.1:8501/_stcore/health', timeout=3) as response:
    health_status, health = response.status, response.read().decode()
with opener.open('http://127.0.0.1:8501', timeout=3) as response:
    page_status = response.status
runtime = {'checked_utc': checked, 'python': sys.version.split()[0], 'executable': sys.executable,
           'environment': 'Isolated E: viewer/test runtime; separate from original scientific lock',
           'health_status': health_status, 'health_body': health, 'page_status': page_status,
           'url': 'http://127.0.0.1:8501', 'browser_visual_qa': False,
           'app_test_cases_passed': len(ui_cases), 'full_selected_tests_passed': len(cases), 'skipped_tests': 0,
           'test_receipt_sha256': hashlib.sha256((EVIDENCE / 'current_tests.xml').read_bytes()).hexdigest(),
           'packages': {distribution.metadata['Name']: distribution.version for distribution in
                        importlib.metadata.distributions() if distribution.metadata['Name'].lower() not in ('pip', 'setuptools')}}
(EVIDENCE / 'streamlit_runtime_verification.json').write_text(json.dumps(runtime, indent=2), encoding='utf-8')
print(f'Syntax: {len(python_files)} Python files; {len(tex_files)} TeX sources checked; no compilation/render claim')
print(f'Selected tests: {len(cases)} passed, zero skipped; Streamlit cases: {len(ui_cases)}; health/page: {health_status}/{page_status}')
