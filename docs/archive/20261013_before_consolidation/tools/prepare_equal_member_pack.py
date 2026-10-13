"""Write the team's equal preparation assignments and synchronize speaker notes."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'evidence/equal_member_allocation_20261013.json'
MEMBERS = [
    dict(name='Ahmed Javaid', roll='22I-2530', slug='AHMED_JAVAID', slides=[1, 3, 4, 10],
         focus='Temporal integrity, evaluation harness and leakage',
         demo='Evidence step: technical/news values and their available-at boundary (40 seconds).',
         code=[('code/src/investify/harness/splits.py', 'Chronological split and purge rules'),
               ('code/src/investify/features/causality_audit.py', 'Available-at and future-information checks'),
               ('code/src/investify/labels.py', 'Five-session targets and label availability'),
               ('code/src/investify/harness/arms.py', 'Clean arm and deliberately leaky canary'),
               ('code/app/presenter.py', 'evidence_view and leakage_view'),
               ('code/scripts/run_mid1_ci.py', 'Shared CI runner, source guards and job receipts')],
         tests=['code/tests/test_splits.py', 'code/tests/test_asof_join.py',
                'code/tests/test_purge_label_availability.py', 'code/tests/test_leak_canary.py',
                'code/tests/test_ci_runner.py'],
         reading=['report/chapters/chapter3_iteration_plan.tex',
                  'report/chapters/chapter6_iteration1.tex',
                  'report/chapters/chapter8_testing.tex', 'deliverables/CI_CD_STATUS.md'],
         route=['Slide 1 (30 seconds): introduce the confirmed team and supervisor.',
                'Slide 3 (60 seconds): bound the recorded prototype and distinguish later milestones.',
                'Slide 4 (70 seconds): show the Mid-1 evidence and distinguish checks from approval.',
                'Slide 8 (40 seconds): on Evidence, select one technical feature and one news feature. Identify their recorded value and contribution.',
                'Slide 10 (100 seconds): explain the chronological experiment, purge boundary, clean result and deliberately leaky canary.'],
         facts=['A feature must be available before the decision. A label can depend on later prices but must not enter the feature vector or an earlier fit.',
                'The clean five-session macro-F1 is 0.2843 versus the training-distribution random comparator at 0.3287.',
                'The centred canary has lift +0.2104 because it deliberately uses future information. It is a leakage demonstration.',
                'Local CI replay and ZIP checks are engineering evidence. GitHub/Ubuntu execution and deployment have not occurred.'],
         questions=[('Why is a chronological split insufficient by itself?', 'Labels can cross the fit/evaluation boundary. Explain the purge and when a target becomes available.'),
                    ('Why keep the leaky result?', 'It demonstrates detection of a known failure and is explicitly excluded from valid predictive claims.'),
                    ('What is the difference between session time and availability time?', 'Session time identifies the market interval. Availability time determines when an input could actually be used.'),
                    ('What CI/CD exists?', 'The two shared CI jobs pass locally. Hosted Windows/Ubuntu jobs and artifact retention are configured. A remote run and continuous deployment remain pending.')]),
    dict(name='Rafay Ul Haq', roll='22I-2520', slug='RAFAY_UL_HAQ', slides=[2, 6, 8, 11],
         focus='Interface, risk profile, social sentiment and recovery',
         demo='Open the walkthrough (20 seconds), then cautious/higher-tolerance/clear profile (60 seconds).',
         code=[('code/app/presenter.py', 'navigate, profile_example, clear_profile, profile_view and social_view'),
               ('code/app/presenter_data.py', 'load_cases and social_comparison'),
               ('code/src/investify/risk_profile.py', 'score_profile and RiskProfile'),
               ('code/src/investify/risk_comparator.py', 'build_comparator and HistoricalComparator.score'),
               ('code/src/investify/sentiment_receipts.py', 'compare_bundles and frozen candidate identities'),
               ('code/src/investify/explain/teacher_session.py', 'Recorded teacher examples and their bounded scope')],
         tests=['code/tests/test_presenter_ui.py', 'code/tests/test_mideval_risk.py',
                'code/tests/test_recorded_social_study.py', 'code/tests/test_mideval_sentiment_receipts.py',
                'code/tests/test_mideval_teacher_session.py'],
         reading=['report/chapters/chapter4_requirements.tex',
                  'report/chapters/chapter7_ui_manual.tex',
                  'deliverables/MODELS_AND_EVALUATION.md', 'deliverables/DEMO_AND_DEFENCE_GUIDE.md'],
         route=['Slide 2 (60 seconds): explain the problem and evidence-based explanations.',
                'Slide 6 (60 seconds): relate cases, validated records, feature context and file schema.',
                'Slide 8 (20 seconds): open Overview, then Open the decision walkthrough. Keep Fresh Alpaca - frozen classifier and 2023-12-21 selected.',
                'Slide 8 (60 seconds): choose Cautious example, Higher-tolerance example, then Clear profile. Show the separate comparator change while the classifier stays Buy.',
                'Slide 11 (100 seconds): explain the sentiment comparison and recorded teacher pilot with their sample/reference limits.'],
         facts=['The profile examples are fictional inputs. R=0 produces Hold and R=1 Sell in the separate retrospective comparator on the demonstrated case.',
                'Clearing the profile removes its result. The questionnaire does not silently supply personal answers.',
                'Original CryptoBERT/Cardiff macro-F1 is 0.2564/0.6016 on the same 24 held-out AI references, including only two negative examples.',
                'There are six recorded assistant-teacher examples, four training and two validation. The original Phi-3-mini student remains untrained.'],
         questions=[('Does the profile change XGBoost probabilities?', 'No. It changes a separate prototype comparator and leaves the recorded classifier output fixed.'),
                    ('Why is Cardiff not finally selected?', 'This small AI-reference benchmark supports exploratory comparison. Adequacy criteria and appropriate independent or supervisor review remain open.'),
                    ('Are social features used by the core classifier?', 'The social study remains separate from the current news-based core.'),
                    ('What happens if a source is invalid?', 'The interface reports the error and withholds substitute results. Do not silently select a different artifact.')]),
    dict(name='Soban Ahmad', roll='22I-2460', slug='SOBAN_AHMAD', slides=[5, 7, 9, 12],
         focus='Decision engine, calibration, SHAP and verified explanations',
         demo='Decision step (40 seconds), then wrong-confidence rejection, fallback and edit invalidation (80 seconds).',
         code=[('code/src/investify/engine.py', 'Model, calibration and attribution orchestration'),
               ('code/src/investify/decision_record.py', 'DecisionRecord probability, class and attribution invariants'),
               ('code/src/investify/explain/context.py', 'build_context and complete feature evidence'),
               ('code/src/investify/explain/verifier.py', 'verify and independent visible-prose/JSON checks'),
               ('code/src/investify/explain/pipeline.py', 'emit and independently verified fallback'),
               ('code/app/presenter_data.py', 'calibration_diagnosis and source-bound diagnostics'),
               ('code/app/presenter.py', 'decision_view, candidate_identity and explanation_view')],
         tests=['code/tests/test_calibration_availability.py', 'code/tests/test_shap_additivity.py',
                'code/tests/test_mideval_record_validation.py', 'code/tests/test_mideval_verifier.py',
                'code/tests/test_emit_pipeline.py', 'code/tests/test_presenter_ui.py'],
         reading=['report/chapters/chapter5_design.tex',
                  'report/chapters/chapter6_iteration1.tex',
                  'deliverables/CALIBRATION_INVESTIGATION.md', 'deliverables/LLM_DESIGN.md'],
         route=['Slide 5 (50 seconds): trace offline model artifacts into the validated record and presentation layer.',
                'Slide 7 (45 seconds): explain candidate checking, retained rejection and separate fallback.',
                'Slide 8 (40 seconds): show the recorded class/probabilities and SHAP contributions on Decision.',
                'Slide 8 (80 seconds): Inject wrong probability, then Check explanation. Show rejection and verified fallback, then edit the candidate to clear the old verdict.',
                'Slide 9 (55 seconds): explain why the retained fresh calibration maps force Buy and why varied output cannot be claimed.',
                'Slide 12 (30 seconds): state the equal assignments, remaining review and later student/deployment work.'],
         facts=['TreeSHAP explains raw model scores. Its values are not calibrated probabilities, causes or expected returns.',
                'Both fresh calibration modes select Buy on all 186 retained evaluation cases. Global map bounds also force Buy across the raw-probability simplex.',
                'Frozen raw macro-F1 is 0.3182 and calibrated macro-F1 is 0.2238. The negative result stays in the report.',
                'Correct factual JSON does not excuse a conflicting visible sentence. A rejected candidate and verified fallback retain separate verdicts.'],
         questions=[('Why does calibration produce only Buy?', 'The Buy map minimum exceeds the other maps\' maxima. Positive common normalization preserves the ordering.'),
                    ('Does a consistent explanation show investment usefulness?', 'It shows agreement with the recorded inputs. It does not establish causality, predictive skill or user comprehension.'),
                    ('Why check fallback independently?', 'Candidate rejection is retained and the replacement must pass its own checks. A failed template check must also surface.'),
                    ('Is QLoRA complete or required for this Mid-1?', 'No. It remains a later proposal milestone. The current student is untrained and no student efficacy is claimed.')]),
]
OWNERS = {number: row['name'] for row in MEMBERS for number in row['slides']}
TIMES = {1: 30, 2: 60, 3: 60, 4: 70, 5: 50, 6: 60, 7: 45, 8: 240,
         9: 55, 10: 100, 11: 100, 12: 30}


def write(name, text):
    (ROOT / name).write_text(text.rstrip() + '\n', encoding='utf-8')


def main():
    if OUTPUT.exists():
        raise ValueError('Preserve the earlier allocation receipt')
    assert set(OWNERS) == set(range(1, 13)) and sum(TIMES.values()) == 900
    proposal = json.loads((ROOT / 'evidence/proposal_work_division_20261013.json').read_text())
    for member in MEMBERS:
        for path in [p for p, _ in member['code']] + member['tests'] + member['reading']:
            if not (ROOT / path).is_file():
                raise ValueError(f'Unknown preparation reference: {path}')
    work = ['# Equal member work allocation', '',
            'The team assigns each member one-third of preparation, review and defence responsibility. Each has four primary slides and five minutes of planned speaking, including their live-demo part. These allocations describe the next preparation cycle. Existing authorship is preserved; each member records personal review and changes during practice.', '',
            '| Member | Assigned share | Proposal responsibilities | Preparation packet |',
            '| --- | --- | --- | --- |']
    tex = [r'\begin{longtable}{p{0.18\textwidth}p{0.60\textwidth}p{0.12\textwidth}}\toprule',
           r'Member & Proposal-assigned responsibilities & Assigned share\\\midrule']
    allocation = [r'\begin{longtable}{p{0.18\textwidth}p{0.11\textwidth}p{0.61\textwidth}}\toprule',
                  r'Member & Share & Assigned review and demonstration\\\midrule']
    for member, original in zip(MEMBERS, proposal['assignments']):
        assert member['name'] == original['member']
        tasks = '; '.join(original['planned_tasks'])
        packet = f'MEMBER_PREPARATION_{member["slug"]}.md'
        work.append(f'| {member["name"]} | 1/3 | {tasks} | [Individual handout]({packet}) |')
        tex.append(member['name'] + ' & ' + tasks + r' & $1/3$\\')
        allocation.append(member['name'] + r' & $1/3$ & ' + member['focus'] + '. Slides ' +
                          ', '.join(map(str, member['slides'])) + r'; five minutes including demo.\\')
        handout = [f'# {member["name"]}: Mid-1 preparation', '',
                   f'{member["roll"]}. Assigned share: **one-third**. Focus: **{member["focus"]}**.', '',
                   'This is your assigned preparation and defence work. Study the current implementation, practise its boundaries and record what you personally review or change. The packet does not state that you authored all existing code.', '',
                   '## Presentation and live-demo route', '',
                   'Planned speaking time: **five minutes**, including your live-demo actions. Slide numbers refer to the current twelve-slide deck. Follow the deck order and hand over to the next named presenter.', '']
        handout += [f'- {text}' for text in member['route']]
        handout += ['', '## Code to study', '', '| File | What you should explain |', '| --- | --- |']
        handout += [f'| [{path}](../{path}) | {point} |' for path, point in member['code']]
        handout += ['', '## Tests and report reading', '',
                    'Read the tests below and explain the failure each one prevents. Existing pass receipts are available; you do not need to rerun paid inference or retrain a model for practice.', '']
        handout += [f'- [{path}](../{path})' for path in member['tests']]
        handout += ['', 'Supporting reading:', '']
        handout += [f'- [{path}](../{path})' for path in member['reading']]
        handout += ['', '## Facts to keep accurate', '']
        handout += [f'- {text}' for text in member['facts']]
        handout += ['', '## Likely defence questions', '']
        for question, answer in member['questions']:
            handout += [f'**{question}** {answer}', '']
        handout += ['## Record after practice', '',
                    '- Date and files/functions personally reviewed:',
                    '- Demo steps completed and observed results:',
                    '- One test boundary explained in your own words:',
                    '- Changes personally made, if any:',
                    '- Assistance/tools used:',
                    '- Questions or failures still needing follow-up:', '',
                    'Also rehearse the entire team route so you can recover if another member needs help. [Shared schedule](MEMBER_PREPARATION_PACK.md).']
        write('deliverables/' + packet, '\n'.join(handout))
    tex.append(r'\bottomrule\end{longtable}')
    allocation.append(r'\bottomrule\end{longtable}')
    work += ['', 'The proposal lists five duties for each person. Deployment and QLoRA are later work and remain unexecuted. The source slide spells Soban Ahmed; the team confirms Soban Ahmad and the existing roll numbers. The supervisor is Mr. Irfan Ullah and there is no co-supervisor.', '',
             '[Proposal source receipt](../evidence/proposal_work_division_20261013.json). [Shared practice schedule](MEMBER_PREPARATION_PACK.md). [Current functional status](MID1_FUNCTIONAL_STATUS.md).']
    write('deliverables/WORK_DIVISION.md', '\n'.join(work))
    write('report/chapters/proposal_work_division.tex', '\n'.join(tex))
    write('report/chapters/equal_member_allocation.tex', '\n'.join(allocation))
    schedule = ['# Equal Mid-1 preparation and speaking schedule', '',
                'Each member has an equal one-third assigned share, four primary slides and **300 seconds of planned speaking**. Total talk and demo: **15 minutes**, with questions afterward. These are practice targets, not observed timings. If the committee includes questions within fifteen minutes, shorten the talk after a timed rehearsal.', '',
                '| Slide | Presenter | Planned seconds |', '| --- | --- | ---: |']
    schedule += [f'| {number} | {"Shared live demo" if number == 8 else OWNERS[number]} | {TIMES[number]} |' for number in range(1, 13)]
    schedule += ['', 'On slide 8: Rafay opens the walkthrough (20 sec), Soban shows Decision (40 sec), Ahmed shows Evidence (40 sec), Rafay demonstrates Risk profile (60 sec), then Soban demonstrates Explanation check (80 sec).', '',
                 '| Member | Non-demo seconds | Demo seconds | Total | Handout |', '| --- | ---: | ---: | ---: | --- |',
                 '| Ahmed Javaid | 260 | 40 | 300 | [Ahmed](MEMBER_PREPARATION_AHMED_JAVAID.md) |',
                 '| Rafay Ul Haq | 220 | 80 | 300 | [Rafay](MEMBER_PREPARATION_RAFAY_UL_HAQ.md) |',
                 '| Soban Ahmad | 180 | 120 | 300 | [Soban](MEMBER_PREPARATION_SOBAN_AHMAD.md) |', '',
                 'Launch from the project root with `& .\\tools\\start_guided_demo.ps1`. Use the demonstrated source/session and rehearse rejection/recovery as well as the successful path. Do one individual code walkthrough, then one combined timed rehearsal and physical projector check. Each member records actual review and personal changes in their handout.', '',
                 'The team confirms all existing names/roll numbers and supervisor Mr. Irfan Ullah. There is no co-supervisor. Session/cohort, coordinator and assessment date remain to be supplied. [Functional status](MID1_FUNCTIONAL_STATUS.md).']
    write('deliverables/MEMBER_PREPARATION_PACK.md', '\n'.join(schedule))
    functional = '''# Current Mid-1 functionality

The current Mid-1 prototype is ready for team practice. The engineering work supporting the recorded demonstration is implemented and locally checked. This does not mean the whole proposed FYP product is finished.

| Area | Current behaviour | Boundary or later work |
| --- | --- | --- |
| Guided interface | Overview, four-step walkthrough, experiments and design; selected-case/profile state and failure recovery | Projector and actual participant review still pending |
| Decision and evidence | Source-bound recorded outputs, calibrated probabilities and complete technical/news feature evidence | Fresh calibrated paths remain all Buy; useful predictive skill unproved |
| Risk profile | Explicit questionnaire, fictional examples, clear/reset and separate retrospective comparator | Profile assumptions, suitability and performance require review |
| Explanation checks | Independent visible-text and JSON verification, retained rejection, verified fallback and edit invalidation | Human comprehension and live student-model usefulness unmeasured |
| Research evidence | Fresh baseline/leakage execution, original sentiment comparison and six recorded teacher examples | Social reference/selection criteria remain open; student inference and QLoRA later |
| Process and handover | Local CI jobs, source guards, reviewed report/deck and extraction-verified source archive | Actual remote CI and continuous deployment not implemented/executed |

The remaining Mid-1 preparation includes the genuine individual walkthrough, combined rehearsal, physical projector check, cover fields and applicable supervisor/criteria review. Future FYP work includes the student programme, deployment and broader research/product acceptance. The negative predictive and small-reference findings remain visible.

Cover fields still needed: programme session/cohort, FYP coordinator and confirmed assessment date. The team confirms names, roll numbers and supervisor Mr. Irfan Ullah; no co-supervisor applies. Signature/declaration pages remain unsigned until the real team reviews them.
'''
    write('deliverables/MID1_FUNCTIONAL_STATUS.md', functional)
    presentation = ROOT / 'presentation/main.tex'
    source = presentation.read_text(encoding='utf-8')
    blocks = re.findall(r'\\begin\{frame\}.*?\\end\{frame\}', source, re.S)
    assert len(blocks) == 12
    outline = json.loads((ROOT / 'deliverables/presentation_outline.json').read_text())
    for number, block in enumerate(blocks, 1):
        match = re.search(r'\\note\{(.*?)\}\s*\\end\{frame\}', block, re.S)
        if not match:
            raise ValueError('Missing speaker note')
        note = re.sub(r'Timing: [^.]+\.', '', match.group(1)).strip()
        note = note.replace('Browser/projector visual review and genuine rehearsal remain pending.',
                            'The actual browser journey is reviewed; physical projector review and genuine rehearsal remain pending.')
        prefix = (f'Assigned presenter: {OWNERS[number]}. Planned speaking: {TIMES[number]} seconds. '
                  if number != 8 else 'Shared demo: Rafay opens for 20 seconds, Soban Decision 40, Ahmed Evidence 40, Rafay Risk 60, Soban Explanation 80. ')
        updated = block[:match.start(1)] + prefix + note + block[match.end(1):]
        source = source.replace(block, updated, 1)
        item = outline['slides'][number - 1]
        title = re.search(r'\\begin\{frame\}\{([^}]+)\}', updated)
        item.update(title=title.group(1) if title else 'Investify', speaker_notes=prefix + note,
                    primary_presenter=OWNERS[number],
                    assigned_presenter='Shared' if number == 8 else OWNERS[number],
                    planned_seconds=TIMES[number])
    write('presentation/main.tex', source)
    outline.update(compiled_output='deliverables/Investify_FYP1_Mid_Presentation_Team_Allocation_20261013.pdf',
                   status='Equal speaking/preparation allocation assigned; refreshed PDF compilation and layout review pending.',
                   member_share='1/3 each, assigned preparation/review/defence', planned_total_seconds=900)
    write('deliverables/presentation_outline.json', json.dumps(outline, indent=2))
    receipt = dict(schema='investify-equal-member-allocation-v1', checked_utc=datetime.now(timezone.utc).isoformat(),
                   authorization='Team instruction: equal allocation, followed by individual study and practice.',
                   allocation_scope='Assigned preparation, review and defence; no retrospective authorship or completed practice asserted.',
                   assigned_share=dict(numerator=1, denominator=3),
                   members=[dict(name=m['name'], roll=m['roll'], slides=m['slides'], planned_speaking_seconds=300,
                                 handout=f'deliverables/MEMBER_PREPARATION_{m["slug"]}.md') for m in MEMBERS],
                   confirmed_metadata=dict(supervisor='Mr. Irfan Ullah', cosupervisor=None,
                                           team_names_and_roll_numbers=True),
                   pending_metadata=['programme session/cohort', 'FYP coordinator', 'assessment date'],
                   proposal_receipt_sha256=hashlib.sha256((ROOT/'evidence/proposal_work_division_20261013.json').read_bytes()).hexdigest())
    OUTPUT.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print('Assigned three equal preparation packets; twelve slides and fifteen planned minutes synchronized.')


if __name__ == '__main__':
    main()
