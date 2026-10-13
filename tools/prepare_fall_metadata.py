"""Carry team-supplied Fall 2026/report-date metadata into current review documents."""
from datetime import date, datetime, timezone
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / 'evidence/fall_report_metadata_20261013.json'


def main():
    if RECEIPT.exists():
        raise ValueError('Preserve the earlier metadata receipt')
    selected_date = date(2026, 10, 11)
    assert selected_date.strftime('%A') == 'Sunday'
    replacements = {
        'deliverables/MEMBER_PREPARATION_PACK.md': [
            ('Session/cohort, coordinator and assessment date remain to be supplied.',
             'Assessment term: FYP-1 Mid-Evaluation, Fall 2026. Report date: 11 October 2026, selected by the team. The current coordinator and formal committee appointment remain unconfirmed; actual test/revision dates stay in their receipts.')],
        'deliverables/MID1_FUNCTIONAL_STATUS.md': [
            ('Cover fields still needed: programme session/cohort, FYP coordinator and confirmed assessment date.',
             'Assessment term: FYP-1 Mid-Evaluation, Fall 2026. Team-selected report date: 11 October 2026 (Sunday). The FYP coordinator remains to be confirmed. The formal committee appointment is separate from the report date; verification performed on 12-13 October retains its actual dates.')],
        'deliverables/DEMO_AND_DEFENCE_GUIDE.md': [
            ('Investify_FYP1_Mid_Presentation_Team_Allocation_20261013.pdf', 'Investify_FYP1_Mid_Presentation_Fall_2026_20261013.pdf'),
            ('Investify_FYP1_Mid_Report_Team_Allocation_20261013.pdf', 'Investify_FYP1_Mid_Report_Fall_2026_20261013.pdf'),
            ('session/cohort, coordinator and assessment date remain open.',
             'FYP-1 Mid-Evaluation is in Fall 2026. The report date is 11 October 2026, as selected by the team. Coordinator and the formal committee appointment remain unconfirmed; actual execution dates are preserved.')],
        'deliverables/MID1_90_95_ROADMAP.md': [
            ('Confirm programme session, coordinator and assessment date. Team names/roll numbers, supervisor and absence of a co-supervisor are confirmed.',
             'Confirm the current coordinator and applicable submission arrangements. Fall 2026, the team-selected report date of 11 October 2026, team names/roll numbers, supervisor and absence of a co-supervisor are recorded. The report date is separate from a formal committee appointment.')],
        'report/README.md': [
            ('Session/cohort, coordinator, assessment date and actual review/rehearsal remain open.',
             'Fall 2026 and the team-selected report date of 11 October 2026 are recorded. Coordinator and actual review/rehearsal remain open; the formal committee appointment is separate.'),
            ('programme session, coordinator and assessment date need confirmation',
             'coordinator and applicable submission details need confirmation')],
        'presentation/README.md': [
            ('The preparation date is not a confirmed assessment date.',
             'Fall 2026 and the report date of 11 October 2026 are team-supplied metadata. Actual revision/test dates remain in the receipts; the formal committee appointment is separate.')],
        'planning/MID_EVAL_READINESS.md': [
            ('The team confirms names, roll numbers and supervisor, with no co-supervisor.',
             'The team confirms names, roll numbers and supervisor, with no co-supervisor. The assessment term is Fall 2026 and the selected report date is 11 October 2026; actual execution receipts keep their dates.'),
            ('remaining cover fields', 'current coordinator/submission details')],
    }
    for name, pairs in replacements.items():
        path = ROOT / name
        text = path.read_text(encoding='utf-8')
        for old, new in pairs:
            if old not in text:
                raise ValueError(f'Metadata update anchor absent: {name}')
            text = text.replace(old, new)
        path.write_text(text, encoding='utf-8')
    metadata = ROOT / 'deliverables/REPORT_METADATA.md'
    text = metadata.read_text(encoding='utf-8')
    paragraphs = text.split('\n\n')
    paragraphs[1] = ('Assessment: **FYP-1 Mid-Evaluation, Fall 2026**. Team-selected report date: **11 October 2026 (Sunday)**. '
                     'The current revision and execution receipts retain their actual dates, including 12-13 October. '
                     'This report date does not assert a committee appointment or that later tests occurred on Sunday. '
                     'The team confirms Ahmed Javaid (22I-2530), Rafay Ul Haq (22I-2520), Soban Ahmad (22I-2460) and supervisor Mr. Irfan Ullah. '
                     '**There is no co-supervisor.** A degree-batch range is not inferred from the assessment term. '
                     'The current SE FYP coordinator remains unconfirmed.')
    metadata.write_text('\n\n'.join(paragraphs), encoding='utf-8')
    presentation = (ROOT / 'presentation/main.tex').read_text(encoding='utf-8')
    notes = re.findall(r'\\note\{(.*?)\}\s*\\end\{frame\}', presentation, re.S)
    outline_path = ROOT / 'deliverables/presentation_outline.json'
    outline = json.loads(outline_path.read_text())
    assert len(notes) == len(outline['slides']) == 12
    for item, note in zip(outline['slides'], notes):
        item['speaker_notes'] = note
    outline.update(report_date='2026-10-11', assessment_term='Fall 2026',
                   assessment_stage='FYP-1 Mid-Evaluation', assessment_date=None,
                   date_prepared='2026-10-13', compiled_output='deliverables/Investify_FYP1_Mid_Presentation_Fall_2026_20261013.pdf')
    outline_path.write_text(json.dumps(outline, indent=2) + '\n', encoding='utf-8')
    receipt = dict(schema='investify-report-metadata-v1', checked_utc=datetime.now(timezone.utc).isoformat(),
                   assessment_stage='FYP-1 Mid-Evaluation', assessment_term='Fall 2026',
                   report_date=selected_date.isoformat(), report_date_weekday='Sunday',
                   report_date_basis='User-selected last Sunday relative to 13 October 2026.',
                   committee_assessment_date=None, coordinator=None,
                   execution_dates_preserved=True,
                   pending=['current SE FYP coordinator', 'formal committee appointment if needed for submission'],
                   source='Direct team instructions; coordinator not inferred from the dated official portal.')
    RECEIPT.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print('Recorded Fall 2026 and Sunday report date; actual test dates preserved.')


if __name__ == '__main__':
    main()
