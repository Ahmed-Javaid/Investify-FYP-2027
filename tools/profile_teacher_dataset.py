"""Record actual teacher export size and local training readiness without training."""
import hashlib
import importlib.util
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / 'evidence/teacher_pilot/assistant_20261012'
sys.path.insert(0, str(ROOT / 'code/src'))
from investify.explain.teacher_session import _records
from investify.explain.template import render_guided


def main():
    verification = json.loads((PILOT / 'verified/verification.json').read_text(encoding='utf-8'))
    if verification['execution_kind'] != 'actual_assistant_session': raise ValueError('Actual teacher evidence is required')
    exports = {}
    records, _ = _records(ROOT / 'code/artifacts')
    for split in ('train', 'validation'):
        path = PILOT / 'verified' / (split + '.jsonl')
        rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
        examples = []
        for row in rows:
            data = json.loads(row['messages'][1]['content'])['evidence']
            target = json.loads(row['messages'][2]['content'])
            guide = render_guided(records[data['corpus']][data['session_date']]).text
            examples.append({'session_date': data['session_date'], 'corpus': data['corpus'], 'decision': data['decision'],
                             'input_characters': len(row['messages'][1]['content']),
                             'target_characters': len(row['messages'][2]['content']),
                             'teacher_prose_characters': len(target['text']), 'teacher_prose_lines': len(target['text'].splitlines()),
                             'actual_student_token_count': None,
                             'exactly_same_text_as_deterministic_guide': target['text'] == guide,
                             'same_sentence_line_multiset_as_guide': Counter(target['text'].splitlines()) == Counter(guide.splitlines())})
        exports[split] = {'rows': len(rows), 'file_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                          'decision_counts': dict(Counter(item['decision'] for item in examples)), 'examples': examples}
    modules = {name: importlib.util.find_spec(name) is not None for name in
               ('torch', 'transformers', 'peft', 'bitsandbytes', 'datasets', 'accelerate')}
    try:
        gpu = subprocess.check_output(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader,nounits'], text=True, timeout=10).strip()
    except (OSError, subprocess.SubprocessError): gpu = None
    result = {'schema': 'investify-teacher-export-readiness-v1', 'checked_utc': datetime.now(timezone.utc).isoformat(),
              'teacher_examples': verification['accepted'], 'exports': exports, 'python': sys.version.split()[0],
              'inspected_runtime': sys.executable, 'training_modules_available': modules,
              'gpu_probe_name_and_total_mib': gpu, 'student_checkpoint_declared': False,
              'student_tokenizer_loaded': False, 'student_token_counts_measured': False,
              'student_load_smoke_test_completed': False, 'student_training_executed': False,
              'training_ready': False,
              'template_comparison_scope': 'Literal text/line-multiset comparison only. The teacher can reorder checked sentences, but this does not establish new supported content, readability gains or human comprehension.',
              'blockers': ['Only four accepted real training examples and two validation examples are present.',
                           'All actual source decisions are Buy; Hold/Sell generation generalization is untested.',
                           'Exact original Phi-3-mini checkpoint, tokenizer and supported training runtime are not configured.',
                           'Combined input/target token lengths and peak training VRAM require measurement; character counts are not token counts.'],
              'scope': 'Actual export character/line counts, hashes and local runtime/device probes. No tokens, training feasibility, model performance or student outcomes are invented.'}
    output = ROOT / 'evidence/teacher_dataset_readiness_20261012.json'
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(f"Profiled {verification['accepted']} actual teacher examples; training ready: False; no student training")


if __name__ == '__main__': main()
