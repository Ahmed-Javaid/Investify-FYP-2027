"""Synchronize current drafts from the actual frozen pilot and test receipt.

Prior working text is retained under planning/history; protected originals are
never edited. This does not compile a report or export a presentation.
"""
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'code/src'))
from investify.sentiment_selection import validate_benchmark, digest

tree = ET.parse(ROOT / 'evidence/current_tests_20261012.xml')
cases = tree.findall('.//testcase')
if not cases or any(tree.findall('.//' + kind) for kind in ('failure', 'error', 'skipped')):
    raise ValueError('A completed, passing current test receipt is required')
count = len(cases)
ui_count = sum('StreamlitMidEvalTests' in case.get('classname', '') for case in cases)
benchmark = json.loads((ROOT / 'code/artifacts/mid_eval/social_benchmark.json').read_text(encoding='utf-8'))
usable = validate_benchmark(benchmark)
plan = json.loads((ROOT / 'code/artifacts/mid_eval/social_selection_plan.json').read_text(encoding='utf-8'))
if digest(benchmark) != plan['benchmark_sha256']:
    raise ValueError('Pilot draft must refer to the actual frozen benchmark')


def write(relative, text):
    path = ROOT / relative
    history = ROOT / 'planning/history/before_ai_pilot' / relative
    if path.exists() and not history.exists():
        history.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, history)
    path.write_text(text, encoding='utf-8')


def update(relative, replacements):
    path = ROOT / relative
    text = path.read_text(encoding='utf-8-sig')
    for old, new in replacements:
        text = text.replace(old, new)
    if text != path.read_text(encoding='utf-8-sig'):
        write(relative, text)


summary = 'The actual AI reference pilot contains 200 real MSFT tweets: 117 usable labels (31 positive, 67 neutral, 19 negative) and 83 explicit exclusions. Its frozen split is 93 development/24 held out, with only two negative held-out references. One session pass is recorded with full prompt/input/raw-output/timing and declared model-identity provenance; agreement/kappa are null and independent human validation is absent. Candidate inference remains blocked with null metrics.'
common = [('124', str(count)), ('135', str(count)), ('twelve actual Streamlit', f'{ui_count} actual Streamlit'),
          ('human-labelled social selection', 'AI-reference social comparison'),
          ('human social annotations', 'actual sentiment-candidate inference'),
          ('human-labelled social-model study', 'AI-reference social-model comparison')]
for relative in ['README.md', 'code/README.md', 'code/docs/mideval_increment.md', 'deliverables/MODELS_AND_EVALUATION.md',
                 'report/chapters/04_abstract.tex', 'report/chapters/06_executive_summary.tex',
                 'report/chapters/chapter3_iteration_plan.tex', 'report/chapters/chapter6_iteration1.tex',
                 'report/chapters/chapter8_testing.tex', 'report/chapters/chapter9_development_evidence.tex',
                 'report/chapters/conclusion.tex', 'report/chapters/appendix_test_cases.tex']:
    update(relative, common)
update('README.md', [('[Human-labelled social-study validation and evaluation tooling](code/docs/social_selection.md), with the actual study still pending.',
                      '[AI/human social-study tooling](code/docs/social_selection.md) and the [actual AI reference pilot](deliverables/AI_SENTIMENT_PILOT.md); candidate inference remains pending.'),
                     ('no actual LLM completion has been obtained', 'no actual explainer completion has been obtained')])
update('code/README.md', [('supplied post/human-label provenance', 'declared post/AI-or-human annotation provenance'),
                         ('The actual social benchmark remains absent; no sentiment-model comparison result is claimed.', summary)])
update('deliverables/MODELS_AND_EVALUATION.md', [('Selection study and hand-labelled benchmark pending;', 'AI references acquired/annotated; candidate inference pending;'),
                                               ('on human-labelled equity social posts', 'against model-generated equity-social reference labels; independent human validation unmeasured')])
update('report/chapters/chapter4_requirements.tex', [('separate initial human labels', 'declared AI or human initial labels and annotation provenance'),
                                                  ('Tool implemented; real labels pending', 'AI reference pilot frozen; candidate inference pending')])
update('report/chapters/04_abstract.tex', [('Real LLM generations and human validation remain unavailable.',
                                        'Real explainer generations and human validation remain unavailable. ' + summary)])
update('report/chapters/chapter9_development_evidence.tex', [
    ('with separate declared human labels', 'with declared AI or human labels and model/prompt/input/run provenance'),
    ('Acquisition, genuine human annotations, candidate inference, adequacy criteria and actual model-selection evidence remain required.', summary),
    ('social annotation, personalized classifier modelling', 'sentiment-candidate comparison, personalized classifier modelling'),
    ('No fabricated annotation or external LLM generation is included.', 'The retained social labels were generated by the assistant in one actual session pass and disclosed as AI references. No external explainer completion or human annotation is claimed.')])
testing_path = ROOT / 'report/chapters/chapter8_testing.tex'
testing = testing_path.read_text(encoding='utf-8')
testing = testing.replace('On 11 October 2026, the selected suite', 'On 12 October 2026, the selected suite')
testing = testing.replace('The actual benchmark file is absent; readiness is blocked with no acquired posts, created human labels or inference calls.', summary)
testing += '\n\\section{AI Reference Pilot and Saved Calibration Audit}\n' + summary + '\nNine additional annotation/import unit tests use labelled fixtures to check raw packet coverage, input/prompt tampering, single-pass null agreement, optional cross-checks and explicit exclusions. The actual raw-label batches are separate research artifacts. The Social Study widget also checks the AI-reference disclosure and missing-inference state.\n\nThe saved-artifact audit independently summarizes all 372 records: each corpus has 186 Buy decisions and only ten distinct calibrated probability vectors, while recorded raw predicted-class margins vary. The inspected engine transfers isotonic mappings from an earlier classifier to a separately refitted classifier. This is an unchecked mapping-transfer assumption, not an established cause or proof of forward leakage. Full raw scores/labels/models and the scientific runtime remain unavailable, so causal reproduction and new performance metrics are not claimed.\n'
if '\\section{AI Reference Pilot and Saved Calibration Audit}' not in testing_path.read_text(encoding='utf-8'):
    write('report/chapters/chapter8_testing.tex', testing)
research = ROOT / 'report/chapters/chapter2_research.tex'
if '\\section{Actual AI Reference Pilot}' not in research.read_text(encoding='utf-8'):
    write('report/chapters/chapter2_research.tex', research.read_text(encoding='utf-8') + '\n\\section{Actual AI Reference Pilot}\nThe author-released StockNet corpus provides original social-post content/identifiers/timestamps \\cite{stocknet_paper,stocknet_repository}. The first NVDA sampling declaration could not execute because that ticker is absent from the released directory list. MSFT was declared before content acquisition. ' + summary + '\nPublic historical posts may occur in annotation or candidate pretraining. Exact deduplication leaves near-duplicates and retweets. Whole-post sentiment candidates and target-equity references differ in scope. These limits prevent an independently human-validated accuracy or NVDA transfer claim. The retained MIT repository notice does not authenticate third-party tweet rights; this workspace has not publicly redistributed the corpus.\n')
bib = ROOT / 'report/references/references.bib'
if 'stocknet_paper' not in bib.read_text(encoding='utf-8'):
    write('report/references/references.bib', bib.read_text(encoding='utf-8') + '\n@inproceedings{stocknet_paper,\n  author={Xu, Yumo and Cohen, Shay B.},\n  title={Stock Movement Prediction from Tweets and Historical Prices},\n  booktitle={Proceedings of the 56th Annual Meeting of the Association for Computational Linguistics},\n  year={2018},\n  url={https://aclanthology.org/P18-1183/}\n}\n@misc{stocknet_repository,\n  author={Xu, Yumo},\n  title={StockNet Dataset: Author-Released Tweets and Historical Stock Prices},\n  year={2018},\n  url={https://github.com/yumoxu/stocknet-dataset}\n}\n')
protocol = json.loads((ROOT / 'deliverables/social_annotation_protocol.json').read_text(encoding='utf-8'))
protocol['status'] = summary
protocol['annotation'] = {'method': 'model_generated', 'human_method_supported': 'two_independent_humans',
                         'procedure': ['Declare source/window/sampling before acquisition', 'Annotate target/original text only without candidate outputs',
                                       'Preserve actual model identity evidence, prompt, hashes, raw labels/reasons and run timing',
                                       'Optional separate pass retains initial disagreements and adjudication', 'Freeze labels before candidate inference'],
                         'boundary': 'AI reference agreement is not independently human-validated accuracy. Single-pass reliability statistics are null.'}
protocol['record_fields'] = ['post_id', 'source', 'source_kind', 'source_url', 'published_at_utc', 'ticker', 'text',
                            'model_annotations', 'adjudicated_label', 'adjudication_note', 'adjudicator_id',
                            'adjudicated_at_utc', 'exclusion_reason']
protocol['implemented_tooling'].update(protocol_version='mideval-equity-social-selection-v3',
    session_import_entrypoint='code/scripts/import_session_annotations.py',
    actual_study_status='Actual 200-post AI reference pilot frozen; candidate inference blocked',
    boundary='Schemas cannot authenticate source rights/model identities/blindness. Candidate outputs and independent human validation remain absent.')
protocol['pending_inputs'] = ['Genuine candidate weights/runtime and supported Cardiff format', 'Actual explainer endpoint/model',
                              'Original scientific inputs/runtime', 'Review/adequacy decisions, institutional facts and deadline']
write('deliverables/social_annotation_protocol.json', json.dumps(protocol, indent=2))
outline = json.loads((ROOT / 'deliverables/presentation_outline.json').read_text(encoding='utf-8'))
for slide in outline['slides']:
    if slide['title'] == 'Validation evidence':
        for row in slide['table']['rows']:
            if row[0] == 'Selected Python suite': row[1] = f'{count} passed, no skips'
            if row[0] == 'Streamlit AppTest': row[1] = f'{ui_count} actual cases passed'
    if slide['title'] == 'Remaining work':
        slide['body'][2] = 'Run candidate inference against the frozen AI references and review profile/blend semantics.'
    if slide['title'] == 'Proposal feedback status':
        slide.clear()
        slide.update(title='AI sentiment reference pilot', table={'columns': ['Reference', 'Usable posts', 'Held out'],
                    'rows': [['Positive', '31', '7'], ['Neutral', '67', '15'], ['Negative', '19', '2'], ['Total', '117', '24']]},
                    body=['200 real MSFT tweets; 83 explicit exclusions.', 'One AI pass; independent human validation unmeasured.', 'Candidate inference pending; no model-quality score.'],
                    speaker_notes='Sampling was amended from unavailable NVDA to MSFT before acquiring tweet contents. StockNet source revision and original Git blobs are retained. Exact session model identity is configuration-declared, not provider-authenticated. The 24 held-out references include only two negatives and may overlap public pretraining. These labels cannot establish NVDA transfer or return prediction. Candidate weights/runtime are unavailable. The proposal action register still has open items.',
                    sources=['deliverables/AI_SENTIMENT_PILOT.md', 'evidence/social_pilot/annotation_freeze_receipt.json',
                             'https://github.com/yumoxu/stocknet-dataset', 'https://aclanthology.org/P18-1183/'])
write('deliverables/presentation_outline.json', json.dumps(outline, ensure_ascii=False, indent=2))
update('deliverables/HANDOVER_GUIDE.md', [('No real chat-model completion, acquired social benchmark or human study result is included.',
                                        'The actual 200-post AI reference pilot is included. No actual explainer completion, candidate-model score or human study result is included.')])
update('report/chapters/chapter8_testing.tex', [('Nine additional annotation/import unit tests', 'Ten additional annotation/import unit tests')])
outline['date_prepared'] = '2026-10-12'
write('deliverables/presentation_outline.json', json.dumps(outline, ensure_ascii=False, indent=2))
update('deliverables/SOCIAL_CORPUS_ACCESS.md', [('11 October 2026. This review identifies sources and access gaps; **no real corpus has been acquired, annotated or evaluated**.',
                                              '12 October 2026 update: a real StockNet MSFT corpus has been acquired and annotated with AI reference labels; see [the pilot report](AI_SENTIMENT_PILOT.md). Candidate evaluation remains pending. The earlier source alternatives and access gaps below are retained.'),
                                             ('Genuine human annotation, exact local classifier snapshots and adequacy criteria remain required.',
                                              'AI references are now frozen; exact local classifier snapshots, runtime and adequacy criteria remain required. Independent human validation is unmeasured.')])
print(f'Synchronized working report/12-slide outline/protocol from {count} passing tests and actual frozen references; no render/export claim')
