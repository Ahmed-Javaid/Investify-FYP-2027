"""Review actual paired social outputs and synchronise current mid drafts."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code/src'))
STUDY=ROOT/'code/artifacts/mid_eval'
RUN=STUDY/'social_study_20261013_run02'
SUMMARY=ROOT/'evidence/social_study_review_20261013.json'

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def write(path,text):
    raw=path.read_bytes() if path.exists() else b''
    newline='\r\n' if raw.count(b'\r\n')>raw.count(b'\n')/2 else '\n'
    path.write_bytes(text.replace('\r\n','\n').replace('\n',newline).encode('utf-8'))

def top(path,section):
    text=path.read_text(encoding='utf-8')
    if '## Completed original-classifier study - 13 October 2026' in text:
        raise ValueError('Study update already present')
    first,rest=text.split('\n',1)
    write(path,first+'\n\n'+section.strip()+'\n\n'+rest.lstrip())

def main():
    if SUMMARY.exists():raise ValueError('Preserve earlier social review')
    from investify.sentiment_receipts import compare_bundles
    benchmark=read(STUDY/'social_benchmark.json')
    parent=read(STUDY/'social_selection_plan.json')
    catalog=read(STUDY/'social_study_20261012_run01/publisher_catalog.json')
    plan=read(RUN/'plan.json')
    bundles=[read(RUN/(key+'_run02')/'bundle.json') for key in ('cryptobert','cardiff')]
    result=compare_bundles(benchmark,parent,catalog,plan,bundles)
    if result!=read(RUN/'comparison/comparison.json') or result['status']!='complete':
        raise ValueError('Actual paired comparison cannot be reproduced')
    old=read(STUDY/'social_study_20261012_run01/cryptobert_run01/bundle.json')
    if old['run']['outputs']!=bundles[0]['run']['outputs']:
        raise ValueError('Repeated original CryptoBERT predictions changed; investigate before reporting parity')
    outcomes={}
    for bundle in bundles:
        outputs=bundle['run']['outputs']
        outcomes[bundle['run']['model_id']]={'predicted_labels':dict(Counter(max(row['probabilities'],key=row['probabilities'].get) for row in outputs)),
            'complete_posts':len(outputs),'truncated_posts':sum(row.get('truncated',False) for row in bundle['receipt']['details']),
            'backend':bundle['receipt']['backend']}
    cases=ET.parse(ROOT/'evidence/social_recorded_viewer_tests_20261013_run03.xml').findall('.//testcase')
    if any(case.find('failure') is not None or case.find('error') is not None for case in cases):
        raise ValueError('Current viewer checks contain failures')
    areas=[('Scientific pipeline, baseline and leakage',25,85),('Interface, explanation and transparency',20,95),
           ('Social-sentiment selection',15,85),('Report, requirements and design',20,80),
           ('Committee responses, inventory and metrics',10,85),('Handover, repository and contributions',5,70),
           ('Presentation, demo and defence',5,55)]
    readiness=sum(weight*completion/100 for _,weight,completion in areas)
    summary={'schema':'investify-completed-social-review-v1','checked_utc':datetime.now(timezone.utc).isoformat(),
             'status':'paired_comparison_reproduced','result':result,'outcomes':outcomes,
             'original_cryptobert_repeat_outputs_identical':True,'original_labels_and_v3_plan_modified':False,
             'readiness_judgement':{'weighted_percentage':readiness,'previous':78.5,'areas':areas,
                 'basis':'Social rises from 50 to 85 after exact original acquisition, lossless conversion, complete paired inference, receipt/logit replay and recorded viewer checks. Acceptance criteria, larger independent validation and deployment selection remain open.'},
             'scope':'24 MSFT AI-reference posts; no independently human-validated accuracy, NVDA transfer, return prediction, significance or deployment approval.'}
    with SUMMARY.open('x',encoding='utf-8') as stream:
        json.dump(summary,stream,indent=2,allow_nan=False)
        stream.write('\n')
    section="""## Completed original-classifier study - 13 October 2026

The original CryptoBERT and Cardiff candidates now complete **24/24 held-out
posts each**, without errors or missing predictions. Both publisher snapshots
and every tokenizer/config file are verified. Original Cardiff BIN serialization
preserves all 204 keys/dtypes/shapes/raw bytes; the loader retains its unused
native pooler and proves bitwise classifier-logit parity with/without it.

| Candidate | Macro-F1 agreement | Exact AI-reference agreement | Observed limit |
| --- | ---: | ---: | --- |
| CryptoBERT | 0.256410 | 15/24 (62.5%) | All 24 predictions neutral; positive/negative recall zero |
| Cardiff | 0.601587 | 16/24 (66.7%) | Positive recall 4/7; neutral 11/15; negative 1/2 |

Cardiff is the **exploratory benchmark leader**, not a deployment-approved winner.
The held-out references are AI-generated and contain only two negatives.
No independently human-validated accuracy, significance, NVDA transfer or useful
return prediction follows from these results. Adequacy criteria and genuine
review remain unclosed; deployment_selection stays null.

The Social Study view now recomputes the comparison from the actual raw
output/receipt bundles, with AI-reference/exploratory disclosures. It performs
no model inference. Latest viewer checks: **25 passes, zero skips**, including
21 Streamlit cases and four recorded-selector checks, plus five subtest checks.
Current native-pooler/loader gates have 37 passes plus nine subtests.
The earlier Cardiff refusal and failed viewer receipt remain preserved.
Repeated actual CryptoBERT outputs are identical.

[Current paired review](../evidence/social_study_review_20261013.json) and
[raw comparison](../code/artifacts/mid_eval/social_study_20261013_run02/comparison/comparison.json).

Readiness is now **83.75%, approximately 84%**. Original weights are unchanged;
social alone rises from 50% to 85%, while other areas retain their preceding
estimates. The report/deck still require compilation/export, visual QA and
institutional/team review. No student training or new teacher-model choice
occurred. The current assistant/Phi-3-mini/Mistral roles remain unchanged.

"""
    for relative in ['planning/CURRENT_STATUS.md','planning/HANDOFF_20261012.md','planning/MID_EVAL_PLAN.md',
                     'planning/MID_EVAL_SCOPE.md','deliverables/AI_SENTIMENT_PILOT.md',
                     'deliverables/MODELS_AND_EVALUATION.md','deliverables/ORIGINAL_MID_TRACEABILITY.md']:
        top(ROOT/relative,section)
    table='\n'.join(f'| {name} | {weight}% | {completion}% | {weight*completion/100:.2f}% |' for name,weight,completion in areas)
    top(ROOT/'planning/MID_EVAL_READINESS.md',f"""## Completed original-classifier study - 13 October 2026

Current weighted planning completion is **83.75%, approximately 84%**.
All original weights are unchanged; this supersedes 78.5% below.

| Work area | Weight | Completion judgement | Contribution |
| --- | ---: | ---: | ---: |
{table}

Social moves from 50% to 85% after genuine pinned candidate execution and paired
receipt/logit replay on the unchanged 24 AI references. Cardiff leads the
exploratory benchmark. Predeclared adequacy criteria, larger independent
validation, final selection and genuine review remain open. No report/deck
rendering or human-review credit is added from candidate scores alone.

[Actual paired evidence](../evidence/social_study_review_20261013.json).
The estimate is not an institutional grade. The 90% target remains unmet.
""")
    for relative in ['README.md','deliverables/README.md','code/README.md']:
        top(ROOT/relative,section.replace('../evidence/', 'evidence/') if relative=='README.md' else section)
    path=ROOT/'planning/BACKGROUND_PROGRESS.md'
    write(path,path.read_text(encoding='utf-8')+'\n\n'+section)
    tex=r"""
\section{Executed Original-Publisher Social Comparison}
On 13 October 2026 both pinned original classifiers completed the same 24
chronologically held-out MSFT posts. The frozen reference contains 7 positive,
15 neutral and 2 negative AI labels. Source posts, reference labels, exclusions,
candidate identities, preprocessing and the original V3 split are unchanged.

\begin{table}[htbp]
\centering
\small
\begin{tabular}{lrrrr}
\toprule
Candidate & Macro-F1 & Exact agreement & Positive recall & Negative recall \\
\midrule
CryptoBERT & 0.2564 & 15/24 & 0/7 & 0/2 \\
Cardiff & 0.6016 & 16/24 & 4/7 & 1/2 \\
\bottomrule
\end{tabular}
\caption{Agreement with frozen AI reference labels; not independently human-validated accuracy.}
\end{table}

CryptoBERT predicts neutral on all 24 posts, matching the development-majority
neutral comparator. Cardiff is the exploratory benchmark leader. A single
prediction changes exact agreement by 4.17 percentage points, and negative
recall changes in 50-point steps. Public-post pretraining overlap and shared
events remain unexcluded. These results do not establish NVDA transfer, return
prediction, significance, suitability or deployment readiness.
No predeclared adequacy threshold exists in the retained plan, and the
deployment selection remains unset pending actual criteria and review.

Both original publisher revisions, weight hashes and all loading-affecting
tokenizer/config files are verified. Original Cardiff BIN weights were
losslessly serialized: all 204 tensor keys, dtypes, shapes and raw bytes match.
Its two unused native pooler parameters are retained during modern loading,
with exact classifier-logit parity verified. No classifier head is missing,
mismatched, substituted or randomly initialized. Modern set-valued loader
diagnostics are normalized for recording; nonempty diagnostics still refuse
inference.

The first Cardiff loading refusal is retained. Both models reran under a new
source-bound plan, retaining per-post raw logits, processed-text hashes,
token counts, truncation, runtime identity and probability outputs.
Independent receipt/logit comparison reproduces the reported table; repeated
CryptoBERT outputs are identical. The Social Study view displays recomputed
recorded scores with AI-reference limitations and download evidence.
Twenty-five current viewer/selector checks pass, including 21 Streamlit cases;
37 current loader/pooler checks and nine subtests pass on their declared scopes.
These scopes overlap earlier evidence and are not summed as a full-suite total.
"""
    path=ROOT/'report/chapters/chapter8_testing.tex'
    text=path.read_text(encoding='utf-8')
    text=text.replace('no original model conversion or inference occurred.','those earlier fixture receipts did not execute original weights; the genuine comparison below is separate.')
    text=text.replace('Candidate inference remains blocked with null metrics.','The later original-publisher paired comparison is recorded below.')
    text=text.replace('The real Transformers/PyTorch loading branch remains unexecuted; its input-file hashes and loading flags are prepared, not measured real-model results.',
                      'Those early fixtures did not execute original weights; actual publisher-byte-bound Torch/Transformers inference now completes both candidates, as recorded below.')
    text=text.replace('Scientific raw/store inputs are absent.','The original September raw/store inputs remain absent; a separately identified fresh Alpaca experiment now executes on restored genuine inputs.')
    text=text.replace('no LLM or scientific retraining is claimed.','no LLM generation is claimed by those probes. The separate fresh science and original social-classifier runs retain actual execution evidence.')
    write(path,text+'\n'+tex)
    path=ROOT/'report/chapters/chapter6_iteration1.tex'
    text=path.read_text(encoding='utf-8').replace('Live LLM inference, candidate social-model comparison, social features, personalized classifier predictions and remote GitHub execution remain pending.',
        'Original social-candidate comparison now executes with recorded results in Chapter 8. Live LLM inference, social features in the saved predictor, personalized classifier predictions and remote GitHub execution remain pending.')
    write(path,text)
    deck_path=ROOT/'deliverables/presentation_outline.json'
    deck=read(deck_path)
    deck['date_prepared']='2026-10-13'
    for slide in deck['slides']:
        if slide['title']=='Social study and remaining actions':
            slide['body']=['200 acquired MSFT posts; 117 usable AI references; 24 frozen held out.',
                           'Original CryptoBERT and Cardiff each complete 24/24 posts with no errors.',
                           'Macro-F1 agreement: CryptoBERT 0.2564; Cardiff 0.6016.',
                           'Cardiff leads this exploratory benchmark. Deployment selection and independent human validation remain open.']
            slide['speaker_notes']='CryptoBERT predicts only neutral, matching the majority comparator. Cardiff agrees exactly on 16/24 versus 15/24 for CryptoBERT. The held-out labels include only two negatives. Original bytes and lossless Cardiff serialization are verified; the unused original pooler is retained with exact logit parity. Whole-post candidate scores against target-equity AI references do not establish independent accuracy, NVDA transfer or investment returns. Adequacy criteria were not predeclared, so deployment selection stays unset.'
            slide['sources']=['evidence/social_study_review_20261013.json','code/artifacts/mid_eval/social_study_20261013_run02/comparison/comparison.json']
        elif slide['title']=='Remaining work':
            slide['body'][0]='Agree social-model acceptance criteria, review the exploratory comparison and preserve the news-only core until integration is justified.'
        elif slide['title']=='Live demonstration':
            slide['body'].append('Open Social Study and inspect actual paired scores with the AI-reference disclosure.')
    deck['status']='Completed fresh science and original-classifier comparison incorporated; institutional PPTX export/render and genuine team review remain pending.'
    write(deck_path,json.dumps(deck,indent=2,ensure_ascii=False)+'\n')
    print(f'Original classifier review synchronised; planning readiness {readiness:.2f}%.')

if __name__=='__main__':
    main()
