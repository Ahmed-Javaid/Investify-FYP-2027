"""Render an evidence-bound working brief, separate from the institutional report."""
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

# Unmodified vendor source, verified in evidence/reportlab_source_runtime_20261012.json.
VENDOR = Path('E:/AI-Tools/Temp/investify-reportlab-source-20261012-c4c83349/src')
sys.path.insert(0, str(VENDOR))
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.graphics.shapes import Drawing, Rect, String

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'deliverables/mid_eval_evidence_brief_20261012.pdf'
INK = colors.HexColor('#152c3d')
TEAL = colors.HexColor('#087f8c')
GRAY = colors.HexColor('#526373')
PALE = colors.HexColor('#edf5f7')
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='BriefTitle', fontName='Helvetica-Bold', fontSize=25, leading=29, textColor=INK, spaceAfter=10))
styles.add(ParagraphStyle(name='BriefH', fontName='Helvetica-Bold', fontSize=13, leading=17, textColor=TEAL, spaceBefore=12, spaceAfter=6))
styles.add(ParagraphStyle(name='BriefBody', fontName='Helvetica', fontSize=10, leading=14, textColor=INK, spaceAfter=8))
styles.add(ParagraphStyle(name='BriefSmall', fontName='Helvetica', fontSize=8, leading=11, textColor=GRAY, spaceAfter=5))
styles.add(ParagraphStyle(name='BriefCell', fontName='Helvetica', fontSize=9, leading=12, textColor=INK))
styles.add(ParagraphStyle(name='BriefHeader', fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=colors.white))


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8-sig'))


def p(text, style='BriefBody'):
    return Paragraph(text, styles[style])


def table(rows, widths):
    cells = [[p(escape(str(value)), 'BriefHeader' if index == 0 else 'BriefCell') for value in row]
             for index, row in enumerate(rows)]
    item = Table(cells, colWidths=widths, hAlign='LEFT', repeatRows=1)
    item.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), TEAL), ('ROWBACKGROUNDS', (0, 1), (-1, -1), [PALE, colors.white]),
                             ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 9),
                             ('RIGHTPADDING', (0, 0), (-1, -1), 9), ('TOPPADDING', (0, 0), (-1, -1), 8),
                             ('BOTTOMPADDING', (0, 0), (-1, -1), 8)]))
    return item


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(TEAL)
    canvas.line(20 * mm, 18 * mm, 190 * mm, 18 * mm)
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(GRAY)
    canvas.drawString(20 * mm, 13 * mm, 'Investify | Working evidence brief | 12 October 2026')
    canvas.drawRightString(190 * mm, 13 * mm, f'{doc.page}')
    canvas.restoreState()


def main():
    if OUTPUT.exists(): raise ValueError('Preserve the prior brief; choose a new output version')
    xml = ET.parse(ROOT / 'evidence/current_tests_official_policy_20261012.xml')
    if any(xml.findall('.//' + kind) for kind in ('failure', 'error', 'skipped')):
        raise ValueError('Use an actual passing selected-suite receipt')
    tests = len(xml.findall('.//testcase'))
    ui = sum('StreamlitMidEvalTests' in case.get('classname', '') for case in xml.findall('.//testcase'))
    benchmark = read('code/artifacts/mid_eval/social_benchmark.json')
    plan = read('code/artifacts/mid_eval/social_selection_plan.json')
    catalog = read('code/artifacts/mid_eval/official_model_catalog.json')
    acquisition = read('evidence/official_qwen25_acquisition_20261012.json')
    originals = read('evidence/originals_preservation_check.json')
    if not originals['passed'] or len(benchmark['posts']) != 200 or len(plan['heldout_post_ids']) != 24:
        raise ValueError('Evidence changed; revise the brief before rendering')
    if acquisition['status'] != 'blocked' or acquisition['runtime'] is not None:
        raise ValueError('Acquisition status changed; revise the pending-run narrative')
    story = [p('Investify<br/>Mid-evaluation evidence', 'BriefTitle'),
             p('F26-003-Investify | Source and engineering review | 12 October 2026', 'BriefSmall'),
             p('The AI reference pilot and local explanation checks are implemented. Official-publisher model runs, scientific reproduction and institutional submission rendering remain open.'),
             table([['Measured evidence', 'Current result', 'What it establishes'],
                    ['Selected local tests', f'{tests} passed; zero skipped', 'Engineering behaviour, including publisher-weight gates'],
                    ['Actual Streamlit tests', f'{ui} cases passed', 'Widget behaviour; browser visual QA remains open'],
                    ['Historical records', '372 records checked', 'Schema/context/template consistency'],
                    ['Live HTTP checks', '62 passed', 'Local endpoint integration'],
                    ['AI references', '117 usable; 83 exclusions', 'One documented AI annotation pass'],
                    ['Protected originals', f"{originals['files_checked']} unchanged", 'Preservation against original SHA-256 manifest']], [125, 130, 226]),
             p('Official model replacement', 'BriefH'),
             p('Use original Qwen publisher weights and publisher-issued Q5_K_M quantizations. Removed variant results are withdrawn. The acquisition attempt failed with a refused network connection before any official weights arrived; replacement completions and agreement scores are pending.'),
             p('Bounded explanation architecture', 'BriefH'),
             p('Saved decision and attributions -> complete evidence context -> candidate explanation -> independent prose/JSON checks -> accepted text or verified template fallback.'),
             p('The model receives a complete supported guide. Successful reproduction would demonstrate compatibility with the checking contract; it would not alone demonstrate better comprehension.'),
             p('This brief is a rendered working artifact, separate from the uncompiled institutional LaTeX report and the presentation content draft. It contains no participant evidence, signatures or assigned student contributions.', 'BriefSmall'), PageBreak()]
    story += [p('AI sentiment reference pilot', 'BriefTitle'),
              p('Real posts, recorded provenance, frozen references', 'BriefSmall'),
              p('The source is the author-released StockNet repository, pinned to revision 330708b5ddc359961078bef469f43f48992fd6e4. NVDA was absent. MSFT was declared before tweet-content acquisition. The selection retains the first 200 unique identifiers/normalized target-text pairs chronologically in 2015.'),
              p('Fifty-one original daily files from 1 January to 24 February retain their Git blob identities. Batch prefetch and exclusions are documented. The annotator saw target ticker and original text, without candidate predictions or later returns.'),
              p('Reference disposition among 200 selected posts', 'BriefH')]
    chart = Drawing(481, 130)
    for index, (label, count, color) in enumerate([('Positive', 31, TEAL), ('Neutral', 67, colors.HexColor('#537ca8')),
                                                  ('Negative', 19, colors.HexColor('#cb7656')), ('Excluded', 83, colors.HexColor('#9ca7b1'))]):
        y = 103 - index * 29
        chart.add(String(0, y + 4, label, fontName='Helvetica', fontSize=10, fillColor=INK))
        chart.add(Rect(82, y, count * 3.8, 16, strokeColor=None, fillColor=color))
        chart.add(String(90 + count * 3.8, y + 4, str(count), fontName='Helvetica-Bold', fontSize=10, fillColor=INK))
    story += [chart,
              table([['Frozen subset', 'Posts', 'Positive / neutral / negative'],
                     ['Development', '93', '24 / 52 / 17'], ['Held out', '24', '7 / 15 / 2']], [140, 90, 251]),
              p('Annotation identity and reliability', 'BriefH'),
              p('One actual OpenAI/Codex assistant session pass is retained with prompt/version/input hashes, raw labels/reasons and hash-bound persistence times. The handoff declares GPT-6.1 Sol; exact provider serving revision is unavailable. That configuration declaration is not authenticated serving identity.'),
              p('No second pass or independent human validation exists. Agreement and kappa are null. Exclusions, subjective ambiguity, near-duplicates, potential pretraining overlap and the small held-out negative class limit inference.'),
              p('Candidate scores must be reported as agreement with these AI references. They cannot establish independently human-validated accuracy, NVDA transfer, return prediction or investor suitability. Frozen labels are not edited after candidate outcomes.'),
              p('Source: <link href="https://github.com/yumoxu/stocknet-dataset">StockNet author repository</link>. Exact sources, raw packets, label receipts and freeze replay are included in the local source package.', 'BriefSmall'), PageBreak()]
    story += [p('Models and calibration', 'BriefTitle'),
              p('Official publisher identities precede any replacement inference', 'BriefSmall'),
              table([['Model', 'Declared weight format', 'Actual replacement status'],
                     ['Qwen2.5-7B-Instruct', 'Official Q5_K_M; two shards', 'Acquisition blocked; primary explainer pending'],
                     ['Qwen3-8B', 'Official Q5_K_M; one file', 'Not acquired; sentiment comparator pending'],
                     ['CryptoBERT / Cardiff', 'Pinned classifier candidates', 'Separate original classifier study pending']], [150, 160, 171]),
              p('Identity gate', 'BriefH'),
              p('The catalog records canonical publisher repositories, full revisions, SHA-256 pointers and byte sizes. Every shard must match before inference. Runtime receipts are checked against actual local files; filenames and serving aliases alone do not establish origin. Unit fixtures cannot enter the research comparison.'),
              p('Publisher pointer pages at main and repository revision pages were readable. Full-revision blob/raw URLs were unavailable through the web tool, and the actual shell acquisition connection was refused. The acquisition tool must recheck all pointers at the pinned revision before downloading.'),
              p('The same existing sentiment prompt and 24 held-out identities are retained. Qwen3 is declared in non-thinking mode with shared temperature-zero hard-label decoding; this differs from its publisher general sampling recommendation. Two Qwen models are not an independent-provider reference cross-check.'),
              p('Saved calibration investigation', 'BriefH'),
              p('Each of the two historical 186-row corpora contains only Buy decisions and ten distinct calibrated probability vectors, while recorded raw Buy margins vary. Source inspection shows isotonic mappings fitted to an earlier classifier and applied to a separately refitted evaluation classifier.'),
              p('This is an unchecked mapping-transfer assumption, not an established cause or proof of leakage. The historical baseline is preserved. A future comparison should use one frozen classifier with disjoint chronological calibration/evaluation blocks and the same purge, embargo and label-availability rules.'),
              p('Retain full truth/raw/calibrated arrays, calibration class counts, fitted knots and model/scaler hashes. Report class distributions, macro-F1, multiclass Brier and a class-prior comparator together. Do not tune held-out thresholds to create varied decisions.'),
              p('Original raw/store price/news inputs, FinBERT cache, fitted objects and scientific dependencies remain missing. No scientific rerun or new prediction-quality result is claimed.', 'BriefSmall'), PageBreak()]
    story += [p('Risk meaning and open work', 'BriefTitle'),
              p('Actual historical arithmetic; unvalidated suitability', 'BriefSmall'),
              p('The separate prototype comparator uses C(R) = T + R(S - T), with technical score T and news score S. Its derivative is S - T. Increasing R changes the news weight; it does not impose a conservative-to-aggressive action ordering.'),
              table([['Historical corpus', 'Held-out sessions', 'Actions changed: R=0 versus R=1'],
                     ['Alpaca', '38', '25'], ['FNSPID', '38', '29']], [150, 115, 216]),
              p('The audit preserves source hashes and scenario arithmetic. Profiles are labelled parameter scenarios, not people. Comparator scores are not probabilities or expected returns; the saved classifier remains unchanged. Profile scoring and investment suitability are unvalidated.'),
              p('Closest research and the scope of this implementation', 'BriefH'),
              p('<b>FActScore</b> assesses support for atomic generated facts against a knowledge source. This project checks a bounded numerical record and required visible coverage; it does not demonstrate a new general factuality method.'),
              p('<b>RARR</b> researches attribution and revises unsupported generation. This project instead rejects/retries under its contract and emits a verified deterministic guide. A useful educational benefit still needs separate evaluation.'),
              p('<b>Gilardi et al.</b> investigate ChatGPT annotation for relevance, topic, stance and framing. That motivates AI annotation research; it does not independently validate this financial reference set.'),
              p('Remaining execution', 'BriefH'),
              p('1. Acquire exact official weights through available authorized access and run the frozen explainer/sentiment studies with retained failures.<br/>2. Restore original scientific inputs and reproduce the calibration comparison.<br/>3. Compile and visually review the institutional report and presentation when their required tooling is available.<br/>4. Reconcile upstream, execute remote CI and confirm institutional metadata and actual team contributions.'),
              p('No specific task currently needs Astra. The outstanding execution limits concern data, runtime and external access. Current source changes are uncommitted; the review archive identifies its base HEAD and checked working-tree inventory.', 'BriefSmall'),
              p('Primary references: <link href="https://aclanthology.org/2023.emnlp-main.741/">FActScore</link>; <link href="https://aclanthology.org/2023.acl-long.910/">RARR</link>; <link href="https://doi.org/10.1073/pnas.2305016120">Gilardi et al.</link>; <link href="https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF">official Qwen2.5 GGUF</link>; <link href="https://huggingface.co/Qwen/Qwen3-8B-GGUF">official Qwen3 GGUF</link>.', 'BriefSmall')]
    doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=20 * mm, leftMargin=20 * mm,
                            topMargin=19 * mm, bottomMargin=23 * mm, title='Investify mid-evaluation evidence brief',
                            author='Codex, tool-assisted development')
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print('Rendered evidence brief:', OUTPUT)


if __name__ == '__main__': main()
