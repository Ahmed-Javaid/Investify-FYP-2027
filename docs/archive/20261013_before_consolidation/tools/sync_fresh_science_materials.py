"""Synchronise the completed fresh scientific evidence into current mid drafts."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'code/src'))
RUN = ROOT / 'code/artifacts/scientific_runs/alpaca_revision_conservative_20261012_run01'
SUMMARY = ROOT / 'evidence/fresh_alpaca_science_summary_20261012_run01.json'
SUMMARY_LINK = '../evidence/fresh_alpaca_science_summary_20261012_run01.json'
REPLAY_LINK = '../evidence/fresh_alpaca_science_replay_20261012_run01.json'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_text(path, text):
    raw = path.read_bytes() if path.exists() else b''
    newline = '\r\n' if raw.count(b'\r\n') > raw.count(b'\n') / 2 else '\n'
    path.write_bytes(text.replace('\r\n','\n').replace('\n',newline).encode('utf-8'))


def prepend_after_heading(path, section):
    text = path.read_text(encoding='utf-8')
    if '## Fresh scientific execution - 12 October 2026' in text:
        raise ValueError('Fresh execution is already documented: ' + str(path))
    first, rest = text.split('\n',1)
    write_text(path, first + '\n\n' + section.strip() + '\n\n' + rest.lstrip())


def main():
    if SUMMARY.exists():
        raise ValueError('Preserve the existing scientific summary')
    inputs = read(ROOT / 'evidence/fresh_alpaca_science_inputs_20261012_run01.json')
    execution = read(ROOT / 'evidence/fresh_alpaca_science_execution_20261012_run01.json')
    replay = read(ROOT / 'evidence/fresh_alpaca_science_replay_20261012_run01.json')
    if inputs['status'] != 'prepared_and_validated' or execution['status'] != 'executed_pending_result_review' or not replay['passed']:
        raise ValueError('Scientific execution and replay must pass before document updates')
    from sklearn.metrics import f1_score
    from investify.decision_record import DecisionRecord
    from investify.explain.template import render_guided
    from investify.explain.local_llm import verify_generated
    diagnoses = {}
    for mode, folder in [('frozen_classifier','engine_frozen_alpaca'),('refit_transfer','engine_refit_alpaca')]:
        payload = read(RUN / 'recovery01' / folder / 'decision_records.json')
        trace = read(RUN / 'recovery01' / folder / 'scientific_trace.json')
        classes = trace['classes']
        raw = [classes[max(range(3),key=lambda c: row[c])] for row in trace['evaluation']['raw_probabilities']]
        calibrated = trace['calibrated_evaluation']
        rows = [DecisionRecord.from_dict(value) for value in payload['decision_records']]
        for record in rows:
            if not verify_generated(record, render_guided(record)).passed:
                raise ValueError('Fresh record fails complete explanation verification')
        diagnoses[mode] = {
            'raw_evaluation_decision_counts': dict(Counter(raw)),
            'raw_evaluation_macro_f1': float(f1_score(trace['evaluation']['truth'],raw,labels=classes,average='macro',zero_division=0)),
            'calibrated_evaluation_decision_counts': dict(Counter(record.decision for record in rows)),
            'minimum_buy_probability_advantage': min(row[0]-max(row[1:]) for row in calibrated),
            'calibrated_probability_ranges': {name:[min(row[index] for row in calibrated),max(row[index] for row in calibrated)] for index,name in enumerate(classes)},
            'guided_explanations_verified': len(rows),
            'interpretation': 'Raw decisions vary; the learned isotonic maps make Buy the argmax on every current evaluation row. The frozen mode also collapses, so classifier refitting is not required for this observation. This does not establish the cause of the preserved September outputs.'}
    tests = {}
    for name in ['fresh_science_contract_tests_20261012_run01.xml','fresh_science_admission_tests_20261012_run01.xml']:
        cases = ET.parse(ROOT / 'evidence' / name).findall('.//testcase')
        tests[name] = {'passed':sum(not any(item.find(tag) is not None for tag in ['failure','error','skipped']) for item in cases),
                       'skipped':sum(item.find('skipped') is not None for item in cases),
                       'failed':sum(item.find('failure') is not None or item.find('error') is not None for item in cases)}
    if any(value['failed'] for value in tests.values()):
        raise ValueError('Retained engineering checks contain failures')
    areas = [
        ('Scientific pipeline, baseline and leakage',25,85),
        ('Interface, explanation and transparency',20,95),
        ('Social-sentiment selection',15,50),
        ('Report, requirements and design',20,80),
        ('Committee responses, inventory and metrics',10,85),
        ('Handover, repository and contributions',5,70),
        ('Presentation, demo and defence',5,55)]
    percentage = sum(weight*completion/100 for _,weight,completion in areas)
    summary = {'schema':'investify-fresh-science-review-summary-v1','checked_utc':datetime.now(timezone.utc).isoformat(),
               'inputs':inputs,'execution_receipt':str(ROOT / 'evidence/fresh_alpaca_science_execution_20261012_run01.json'),
               'replay_receipt':str(ROOT / 'evidence/fresh_alpaca_science_replay_20261012_run01.json'),
               'diagnosis':diagnoses,'engineering_tests':tests,'readiness_judgement':{
                   'weighted_percentage':percentage,'previous_weighted_percentage':72.25,
                   'areas':[{'area':name,'weight':weight,'completion':completion} for name,weight,completion in areas],
                   'basis':'Only science increases from 60 to 85 after actual fresh ingestion/scoring, all-arm execution, both fitted calibration modes and model/SHAP replay. Weights and other area estimates remain unchanged. This is a planning judgement, not a grade or automatic acceptance.'},
               'scope':'New Alpaca SIP split-adjusted/revision-conservative experiment. No September-byte reproduction, original lock restoration, social-candidate inference, student training, human validation or institutional submission.',
               'summary_tool_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    with SUMMARY.open('x',encoding='utf-8') as stream:
        json.dump(summary,stream,indent=2,allow_nan=False)
        stream.write('\n')
    common = f"""## Fresh scientific execution - 12 October 2026

The new **Alpaca revision-conservative experiment has completed and passed actual
model/calibration/native-TreeSHAP replay**. It consumed 1,509 complete NYSE price
sessions and 6,768 news rows, with 5,748 distinct headlines scored offline by the
pinned original ProsusAI/finbert checkpoint. The recovery doctor had zero blockers
and all three scientific commands completed.

Six arms at both horizons ran on shared row sets: 1,309 rows at one day and
1,305 at five days, six folds each. Clean five-day macro-F1 is **0.2843** against
the training-distribution random baseline **0.3287** (lift -0.0444).
The deliberately centred Bollinger canary has five-day lift **+0.2104**,
95% fold-bootstrap CI **[+0.1698, +0.2421]**. E_SAMEBAR_TEXT remains a lag ablation.

Both current calibration modes still emit **186 Buy decisions**. Raw frozen-mode
predictions are Buy 40 / Hold 51 / Sell 95; learned isotonic maps make Buy highest
on every evaluation row. Frozen Brier improves **0.7929 to 0.6105**; refit-transfer
improves **0.7760 to 0.6078**. Better Brier does not resolve decision collapse or
establish useful prediction. Five unavailable calibration labels were excluded;
181 rows calibrate, and evaluation runs 29 March to 21 December 2023.

Actual retained-model inference reproduces margins/probabilities exactly; native
TreeSHAP agrees with every exported contribution/bias, with maximum frozen
additivity residual about 1.02e-6. All 372 **new** guided explanations validate,
separately from the 372 preserved historical records. New engineering checks:
179 passed / six legacy-input skips, plus eight admission-refusal passes.

This is a fresh SIP split-adjusted snapshot using max(created_at, updated_at)
for news availability, not the original September data or exact uv.lock.
Historical vintage is not proven; all original records, freezes and ZIPs remain
separate. No FNSPID was requested.

[Reviewed summary]({SUMMARY_LINK}) and [actual replay]({REPLAY_LINK}).

Readiness is now **78.5%, approximately 79%**, with unchanged weights and other
areas: science alone rises from 60% to 85%. Remaining substantive gaps are the
social comparison, rendered institutional report/deck, and genuine team review,
contribution/rehearsal and repository evidence. The 90% target is not achieved.
"""
    for relative in ['planning/CURRENT_STATUS.md','planning/HANDOFF_20261012.md','planning/MID_EVAL_PLAN.md',
                     'planning/MID_EVAL_SCOPE.md','deliverables/SCIENCE_CORRECTIONS_20261012.md',
                     'deliverables/MODELS_AND_EVALUATION.md','deliverables/CALIBRATION_INVESTIGATION.md']:
        prepend_after_heading(ROOT / relative, common)
    ledger = f"""## Latest readiness - actual scientific execution

Current planning completion is **78.5%, approximately 79%**. It supersedes the
72.25% checkpoint below. All original weights are unchanged.

| Work area | Weight | Completion judgement | Weighted contribution |
| --- | ---: | ---: | ---: |
""" + '\n'.join(f'| {name} | {weight}% | {completion}% | {weight*completion/100:.2f}% |' for name,weight,completion in areas) + f"""

The six-arm/two-horizon real Alpaca experiment, both fitted calibration modes,
native model/SHAP replay and 372 new verified guided explanations justify raising
science from 60% to 85%. September raw/cache bytes and exact lock are not restored;
cross-corpus/historical reproduction and review remain. The predictor is still
weak and calibrated decisions remain all Buy. No social/report/deck/team credit
is added merely because these runs passed.

[Current evidence summary]({SUMMARY_LINK}). This estimate is neither the
university's marking rubric nor a measured grade. The 90% goal remains unmet.

One illustrative 90.00% route, retaining the other area estimates, is science
90%, social 90%, report 95% and presentation 80%. Those judgements require actual
study/selection, compiled and inspected documents, review and rehearsal.
No threshold or readiness weight should be changed to manufacture completion.

"""
    prepend_after_heading(ROOT / 'planning/MID_EVAL_READINESS.md', ledger)
    path = ROOT / 'planning/BACKGROUND_PROGRESS.md'
    write_text(path, path.read_text(encoding='utf-8') + '\n\n' + common)
    path = ROOT / 'README.md'
    prepend_after_heading(path, """## Fresh scientific execution - 12 October 2026

The fresh Alpaca baseline/leakage and both calibration runs are now executed and
replayed. Read [current status](planning/CURRENT_STATUS.md) and the
[reviewed scientific summary](evidence/fresh_alpaca_science_summary_20261012_run01.json).
The five-day clean model remains weak and both calibrated modes remain all Buy.
Mid readiness is approximately 79%; institutional rendering, social comparison
and genuine team review remain open. Original September records are preserved.
""")
    path = ROOT / 'deliverables/README.md'
    prepend_after_heading(path, """## Fresh scientific execution - 12 October 2026

The [reviewed scientific summary](../evidence/fresh_alpaca_science_summary_20261012_run01.json)
links the completed new experiment, both calibration modes, actual retained-model
and native-TreeSHAP replay, input identities and current readiness judgement.
Current report and slide sources now include its findings; neither has been
compiled/exported as an institutional submission. Older evidence briefs and ZIPs
retain their original snapshots.
""")
    path = ROOT / 'code/README.md'
    prepend_after_heading(path, """## Fresh scientific execution - 12 October 2026

The isolated scientific runtime is
E:\\AI-Tools\\Temp\\investify-science-py311-20261012\\Scripts\\python.exe.
The completed experiment is under
artifacts/scientific_runs/alpaca_revision_conservative_20261012_run01.
Its fresh_config.yaml, recovery01/recovery_config.yaml, input store, six-arm
results, two sets of decision records/traces and logs are retained. Scores are
under E:\\AI-Tools\\Cache\\finbert_scores\\alpaca_revision_conservative_20261012_run01.
The existing default config and historical demo records remain separate.

To prepare another run, use scripts/prepare_fresh_alpaca_science.py --help.
Supply the three acquisition receipts, a **new** run directory, a **new** score
cache on E: and a **new** evidence receipt. It gates source bytes against pinned
publisher hashes and keeps model loading offline. Run the recovery doctor with
the new config before execution. Choose new result/receipt identities.

The independent completed-run checker is scripts/verify_fresh_science_run.py:

~~~powershell
& 'E:\\AI-Tools\\Temp\\investify-science-py311-20261012\\Scripts\\python.exe' -B scripts/verify_fresh_science_run.py --run-directory artifacts/scientific_runs/alpaca_revision_conservative_20261012_run01/recovery01 --output ../evidence/fresh_science_replay_NEW.json
~~~

The new outcome is documented in ../planning/CURRENT_STATUS.md. The original
September source inputs and exact lock are not reproduced, and the all-Buy
calibration outcome still prevents a predictive-usefulness claim.
""")
    report_section = r"""
\section{Fresh Alpaca Scientific Execution}
On 12 October 2026 a separately identified, genuine Alpaca experiment executed
the corrected pipeline. All 1,509 requested NYSE price sessions were present.
The 6,768 revision-conservative news rows contain 5,748 distinct headlines,
scored offline with original ProsusAI/finbert revision
\texttt{0bc2ac10dda6929bcb1f77ccc43c7ec5c424f031}.
The selected price basis is current-vintage SIP split adjustment, without cash
dividend adjustment. News availability uses the later creation/update timestamp.
Neither policy proves historical vendor availability. No FNSPID was downloaded;
this run does not replace the preserved September results or reproduce their bytes.

Six arms at two horizons ran on shared row sets (1,309 one-day and 1,305
five-day rows), with six folds, fixed seed and unchanged model settings.
The clean five-day macro-F1 is 0.2843 versus the training-distribution
stratified-random baseline 0.3287, giving lift -0.0444
(95\% fold-bootstrap interval [-0.0855,-0.0121]).
The centred-Bollinger mutation gives five-day macro-F1 0.5390 and lift +0.2104
(interval [+0.1698,+0.2421]), demonstrating the deliberate canary.
The one-day clean arm passes the configured control rule; the five-day
clean arm remains below chance. E\_SAMEBAR\_TEXT remains a lag ablation.

\begin{table}[htbp]
\centering
\small
\begin{tabular}{lrrrr}
\toprule
Calibration mode & Eval. rows & Macro-F1 & Brier before & Brier after \\
\midrule
Frozen classifier & 186 & 0.2238 & 0.7929 & 0.6105 \\
Refit transfer & 186 & 0.2238 & 0.7760 & 0.6078 \\
\bottomrule
\end{tabular}
\caption{Fresh revision-conservative Alpaca experiment, five-day held-out evaluation.}
\end{table}

Five of 186 candidate calibration labels ended on or after evaluation start and
were excluded. The 181 retained rows fit isotonic mappings; 186 evaluation
sessions span 29 March--21 December 2023. Both current modes produce 186 Buy
decisions. Before calibration, the frozen model predicts Buy 40, Hold 51 and
Sell 95. Its fitted isotonic mappings make Buy largest on every evaluation row.
Thus classifier refitting is not necessary for the observed fresh-run collapse.
This is an observation about the current experiment, not proof of the historical
cause. Lower Brier and all-Buy classifications must be reported together.

Actual inference from retained model bytes/scalers exactly reproduces the stored
raw scores. Independent native XGBoost TreeSHAP matches every exported
contribution and bias; the maximum frozen additivity residual is about
$1.02\times10^{-6}$ against the unchanged $10^{-4}$ tolerance.
Calibration, labels/endpoints and metric replay pass. Complete guided
explanations verify on all 372 new records, separately from the historical 372.

The current source/input/runtime identities and execution logs are retained in
\texttt{code/artifacts/scientific\_runs/} and dated evidence receipts.
The restored Python 3.11 runtime satisfies declared dependency ranges; it is
not exact restoration of \texttt{uv.lock}. Engineering contracts record
179 passes and six legacy-input skips, with eight separate admission-refusal
passes. No independently validated social accuracy, trading return, human
benefit, student training or institutional approval is established.

\begin{figure}[htbp]
\centering
\includegraphics[width=\textwidth]{../code/artifacts/scientific_runs/alpaca_revision_conservative_20261012_run01/recovery01/harness_alpaca/arms_lift_alpaca.png}
\caption{Actual fresh Alpaca leakage harness: lift relative to a training-distribution random baseline.}
\end{figure}
"""
    path = ROOT / 'report/chapters/chapter6_iteration1.tex'
    text = path.read_text(encoding='utf-8')
    text = text.replace('The independent code copy is on branch \\texttt{gpt/mid-eval}.',
                        'The active consolidated repository is on \\texttt{main}; the earlier isolated branch is preserved in history.')
    text = text.replace('Live model inference, candidate social-model comparison','Live LLM inference, candidate social-model comparison')
    text = text.replace('but actual model fitting/results require restored inputs/runtime.',
                        'with a genuine fresh Alpaca fitted comparison now recorded below.')
    text = text.replace('None of these source/fixture repairs establishes changed historical performance or explains the all-Buy result.',
                        'These earlier source/fixture repairs alone do not establish changed historical performance; the fresh-run findings below are separate.')
    write_text(path,text + '\n' + report_section)
    path = ROOT / 'report/chapters/chapter8_testing.tex'
    text = path.read_text(encoding='utf-8')
    start = text.index('The saved-artifact audit independently summarizes')
    end = text.index('The frozen-reference evaluability audit',start)
    text = text[:start] + r"""The saved-artifact audit independently summarizes the preserved 372 historical
records, all Buy; their historical cause remains unproven. The later genuine
revision-conservative Alpaca experiment executes both corrected calibration
modes on matching evaluation dates. Each still produces 186 Buy decisions.
Actual retained-model, isotonic, label-endpoint, metric and native-TreeSHAP
replay passes, and every new guided explanation verifies. The raw frozen
classifier's diverse decisions collapse after its fitted isotonic mappings;
refit transfer is therefore not required for the fresh observation.
Five unavailable calibration targets are excluded. The new experiment's clean
five-day score is below its random baseline, while the deliberate centred
feature canary fires. Chapter 6 records exact metrics, input/runtime limits and
the distinction from September results.

""" + text[end:]
    write_text(path,text)
    deck_path = ROOT / 'deliverables/presentation_outline.json'
    deck = read(deck_path)
    deck['status'] = 'Fresh real Alpaca science and calibration findings incorporated; institutional PPTX export/render and genuine team review remain pending.'
    for slide in deck['slides']:
        if slide['title'] == 'Implemented scope':
            slide['speaker_notes'] += ' A separate fresh Alpaca input-to-model experiment now completes all six leakage arms and both calibration modes; September inputs and the exact lock are not reproduced.'
        elif slide['title'] == 'Prediction limitation':
            slide['title'] = 'Fresh experiment: calibration limitation'
            slide['table'] = {'columns':['Mode','Raw held-out decisions','Calibrated decisions','Brier before / after'],
                'rows':[['Frozen classifier','40 Buy / 51 Hold / 95 Sell','186 Buy','0.7929 / 0.6105'],
                        ['Refit transfer','37 Buy / 50 Hold / 99 Sell','186 Buy','0.7760 / 0.6078']]}
            slide['body'] = ['Actual retained-model, calibration and native-TreeSHAP replay passes.',
                             'Lower Brier does not resolve all-Buy classifications or establish useful prediction.']
            slide['speaker_notes'] = ('These are new real Alpaca revision-conservative results, not overwritten September metrics. '
                '181 calibration rows remain after excluding five unavailable labels; evaluation has 186 sessions from 29 March to 21 December 2023. '
                'Frozen raw predictions vary, but fitted isotonic maps make Buy largest on every evaluation row. Refitting is not required for this fresh collapse. '
                'The preserved historical cause is still unproven. Do not tune thresholds on this evaluation fold to manufacture varied decisions.')
            slide['sources'] = ['evidence/fresh_alpaca_science_replay_20261012_run01.json','evidence/fresh_alpaca_science_summary_20261012_run01.json']
        elif slide['title'] == 'Remaining work':
            slide['body'][0] = 'Complete original-publisher social candidate acquisition/comparison and configured LLM evaluation.'
            slide['body'].insert(1,'Review the completed fresh science; preserve weak prediction/all-Buy findings and study calibration using development data only.')
        elif slide['title'] == 'Live demonstration':
            slide['speaker_notes'] = slide['speaker_notes'].replace('The saved market canary is not a fresh run.',
                'Show the separate completed fresh experiment and its actual canary chart alongside the historical-record UI; this does not turn its fixture button into a model run.')
        elif 'table' in slide and any(row[0] == 'Selected Python suite' for row in slide['table'].get('rows',[])):
            slide['body'] = ['Fresh science: six arms, two horizons, six folds; clean five-day F1 0.2843 versus random baseline 0.3287.',
                             'Deliberate centred canary: five-day lift +0.2104, 95% fold-bootstrap CI [+0.1698,+0.2421].',
                             '179 scientific contracts pass; six legacy-input skips; eight separate admission gate passes.']
            slide['table']['rows'].append(['Fresh actual model/SHAP replay','Both calibration modes pass','New snapshot; exact historical bytes/lock not reproduced'])
            slide['sources'].append('evidence/fresh_alpaca_science_replay_20261012_run01.json')
            slide['speaker_notes'] += ' Current fitted-model evidence is now available under a separate fresh identity; earlier fixture and test counts retain their original scopes.'
    write_text(deck_path,json.dumps(deck,indent=2,ensure_ascii=False)+'\n')
    print(f'Fresh scientific evidence synchronised. Readiness judgement: {percentage:.2f}%.')
    print(json.dumps(diagnoses,indent=2))


if __name__ == '__main__':
    main()
