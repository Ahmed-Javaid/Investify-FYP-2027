"""Create a current-role working PDF brief, preserving the earlier snapshot."""
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

VENDOR = Path('E:/AI-Tools/Temp/investify-reportlab-source-20261012-c4c83349/src')
sys.path.insert(0, str(VENDOR))
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, PageBreak, Spacer

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'deliverables/mid_eval_continuation_evidence_20261012.pdf'
styles = getSampleStyleSheet()
ink, teal = colors.HexColor('#173044'), colors.HexColor('#0f766e')
styles.add(ParagraphStyle(name='TitleC', fontName='Helvetica-Bold', fontSize=25, leading=29, textColor=ink, spaceAfter=13))
styles.add(ParagraphStyle(name='HeadC', fontName='Helvetica-Bold', fontSize=13, leading=17, textColor=teal, spaceBefore=13, spaceAfter=7))
styles.add(ParagraphStyle(name='BodyC', fontName='Helvetica', fontSize=10, leading=14, textColor=ink, spaceAfter=9))
styles.add(ParagraphStyle(name='CellC', fontName='Helvetica', fontSize=9, leading=12, textColor=ink))
styles.add(ParagraphStyle(name='HeaderC', fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=colors.white))


def paragraph(text, kind='BodyC'):
    return Paragraph(text, styles[kind])


def grid(rows, widths):
    table = Table([[paragraph(escape(str(cell)), 'HeaderC' if row == 0 else 'CellC') for cell in values]
                   for row, values in enumerate(rows)], colWidths=widths, repeatRows=1, hAlign='LEFT')
    table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), teal),
                               ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#eef6f5'), colors.white]),
                               ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                               ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                               ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 8)]))
    return table


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(teal)
    canvas.line(20 * mm, 18 * mm, 190 * mm, 18 * mm)
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(ink)
    canvas.drawString(20 * mm, 13 * mm, 'Investify | 12 October 2026 | Working evidence, not institutional submission')
    canvas.drawRightString(190 * mm, 13 * mm, str(doc.page))
    canvas.restoreState()


def main():
    if OUTPUT.exists():
        raise ValueError('Preserve prior PDFs; use a new dated/versioned filename')
    cases = ET.parse(ROOT / 'evidence/current_tests.xml').findall('.//testcase')
    count, ui = len(cases), sum('StreamlitMidEvalTests' in item.get('classname', '') for item in cases)
    story = [paragraph('Investify continuation evidence', 'TitleC'),
             paragraph('12 October 2026. Current teacher: the OpenAI assistant session. Planned original student: Microsoft Phi-3-mini. Mistral remains a fallback; QLoRA belongs to a later milestone.'),
             paragraph('What exists now', 'HeadC'),
             grid([['Evidence', 'Actual scope'],
                   [f'{count} selected tests; {ui} Streamlit cases', 'Engineering paths and widgets. No prediction, student quality or sentiment accuracy claim.'],
                   ['108 scoped core contracts', 'Feature/label/join/purge/calendar/ingestion/store and mock orchestration; three shuffled tests excluded.'],
                   ['372 saved historical NVDA decisions', 'Both corpora remain all-Buy. Templates/context/verifier replay their recorded facts.'],
                   ['200 MSFT posts; 117 AI references', 'One actual annotation pass, 83 disclosed exclusions, frozen 93/24 split. No candidate output.'],
                   ['Six actual teacher explanations', 'Six accepted; four training/two validation. Factual JSON assembled as hybrid supervision.'],
                   ['Originals and source history', '224 protected originals unchanged; earlier receipts/bundles and historical science source preserved.']], [57 * mm, 113 * mm]),
             paragraph('The meaningful live module', 'HeadC'),
             paragraph('Both local interfaces inspect technical/news evidence and check visible prose separately from JSON. A wrong displayed probability is rejected even beside correct JSON; a verified fallback is shown with the candidate failure report retained. Prototype risk answers control a separate retrospective blend, with no change to saved classifier probabilities.'),
             paragraph('Historical records and teacher examples do not establish predictive skill, investor suitability, added explanatory content or user understanding. The institutional report and deck remain uncompiled/unrendered.'), PageBreak()]
    story += [paragraph('Temporal and input repairs', 'TitleC'),
              paragraph('The source corrections are verified on labelled fixtures. Historical market/model metrics have not been rerun.'),
              grid([['Correction', 'Observed implementation evidence'],
                    ['Label endpoints', 'The historical five-calendar-day purge retains 18 overlapping training endpoints on a business-day fixture. Full-price endpoint purging retains zero on the same test blocks.'],
                    ['Calibration targets', 'Five of twenty fixture targets end on/after evaluation start and are excluded. A future price shock cannot alter retained calibration inputs.'],
                    ['Frozen classifier/scaler', 'Explicit frozen mode reuses the same model/scaler. Refit-transfer is a separate corrected-boundary comparator. Mocked orchestration proves flow, not model fitting.'],
                    ['Feature/cache contracts', 'Rising/falling RSI gives 100/0; flat completed windows use project midpoint 50. Cache key/probability/polarity and many-to-one checks prevent row expansion.'],
                    ['Ingestion/store identity', 'Explicit timestamps/ranges/tickers; ambiguous revisions and orphan/missing sessions refused. Batch deduplication and declared V2 hashes preserve prior Parquet bytes.']], [52 * mm, 118 * mm]),
              paragraph('Trace and provenance', 'HeadC'),
              paragraph('New runs retain source/config/runtime/input hashes before and after execution, full class probability/margin/truth arrays, calibration knots, scaler parameters and model JSON bytes/hashes. Numeric replay checks normalization and Brier. These are prepared retention/replay mechanisms; no genuine trained-model trace has yet been produced.'),
              paragraph('The live labelled feature audit calculates nine checks and detects four deliberately centred-window mutations without classifier fitting. E_SAMEBAR_TEXT is accurately a lag-rule ablation under the strict-prior join, not a proved pre-publication-text leak.'), PageBreak()]
    story += [paragraph('Social and teacher research', 'TitleC'),
              paragraph('Frozen references', 'HeadC'),
              paragraph('StockNet source selection retains 200 original MSFT posts, 117 usable AI labels and 83 reasoned exclusions. The held-out block has seven positive, fifteen neutral and two negative references. Independent human validation, a second annotation pass and kappa are unmeasured.'),
              paragraph('A development-majority neutral comparator matches 15/24 AI references with macro-F1 0.256410. This is distribution arithmetic, not candidate inference. Two negative held-out references make recall coarse; pretraining overlap and near-event dependence remain unresolved.'),
              paragraph('Original publisher execution', 'HeadC'),
              paragraph('A separate read-only Python 3.13 CPU loader imports existing Torch, Transformers, Safetensors and Tokenizers. Original weights and exact config/tokenizer byte metadata are still missing. Normal pinned metadata requests fail with connection refused. The V4 original-byte/receipt catalog remains incomplete and cannot authorize a research run.'),
              paragraph('The lossless serializer verifies original BIN bytes before safe loading, preserves every key/dtype/shape/raw tensor byte, and has passed an actual three-key CPU fixture. No original Cardiff conversion occurred. Receipt binding is reproducible self-consistency, not independent execution attestation.'),
              paragraph('Teacher benefit remains unproven', 'HeadC'),
              paragraph('All six actual teacher outputs have the same sentence-line multiset as the complete deterministic guide, reordered. Exact serving ID/revision, decoding, tokens and per-example inference latency are unavailable. All are Buy. Student inference, sufficient adaptation data, Hold/Sell generalization and user comprehension still need measurement.'), PageBreak()]
    story += [paragraph('What closes the first mid', 'TitleC'),
              grid([['Required evidence', 'Current dependency'],
                    ['Fresh ingestion-to-baseline and leakage/mutation run', 'Original raw/store/score cache and supported scientific environment. Current contract tests do not replace the trained experiment.'],
                    ['Actual paired social-model comparison', 'Complete original snapshots/config/tokenizer provenance, receipt-bound outputs and scoped AI-reference metrics.'],
                    ['Institutional report and presentation', 'LaTeX/compiler and required artifact-tool presentation runtime; final render/layout QA and institutional completion.'],
                    ['Live review and ownership', 'Supervisor/browser demonstration, genuine member review/rehearsal, contribution/meeting records, repository/CI evidence.']], [68 * mm, 102 * mm]),
              paragraph('Scope and target', 'HeadC'),
              paragraph('The user requested continued autonomous development toward at least 90% first-mid readiness. No grade, automated acceptance percentage, guaranteed uptime or completed 90% result is claimed. The rubric sets no fixed whole-project completion percentage. QLoRA and the full teacher/original-student/adapted-student comparison are later proposal milestones.'),
              paragraph('Original quantitative NFR-1..8 remain preserved and unmeasured. Socket timeouts/retries do not establish the five-second explanation deadline; the proposal\'s 16 GB envelope is not assumed satisfied by the inspected 10 GiB GPU or recovered CPU-only classifier runtime.'),
              paragraph('Source trail', 'HeadC'),
              paragraph('Planning: BACKGROUND_PROGRESS.md, CHECKPOINT.md and HANDOFF_20261012.md. Review: DEMO_AND_DEFENCE_GUIDE.md, REQUIREMENTS_TRACEABILITY.md, ORIGINAL_MID_TRACEABILITY.md, SCIENCE_CORRECTIONS_20261012.md and SOCIAL_V4_RUNBOOK.md. Exact source/evidence/archive hashes belong in matching dated receipts; older bundles prove only their snapshots.'),
              paragraph('Native browser work was stopped by policy before navigation because the current URL could not be established. No browser visual QA/download completed and no alternate UI retry was used. No specific reasoning task requires Astra; current blockers concern genuine inputs, execution access, rendering and human review.')]
    doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=19 * mm, bottomMargin=25 * mm, title='Investify continuation evidence',
                            author='Tool-assisted working evidence')
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f'Working continuation PDF generated: {OUTPUT}; visual QA pending; institutional report/deck not compiled')


if __name__ == '__main__':
    main()
