"""Prepare visual QA sheets and publish source-bound, dated Mid-1 PDFs."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil

from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = Path('E:/AI-Tools/Temp').resolve()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(folder):
    suffixes = {'.tex', '.cls', '.sty', '.bib', '.png', '.jpg', '.jpeg', '.svg'}
    return {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(folder.rglob('*'))
            if p.is_file() and p.suffix.lower() in suffixes}


def new_json(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def montage(source, destination):
    source, destination = source.resolve(), destination.resolve()
    if not destination.is_relative_to(SCRATCH) or destination.exists():
        raise ValueError('Use a new QA directory beneath E:/AI-Tools/Temp')
    destination.mkdir()
    files = sorted(source.glob('*.png'), key=lambda p: [int(part) if part.isdigit() else part
                   for part in re.split(r'(\d+)', p.name)])
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 20)
    for start in range(0, len(files), 4):
        sheet = Image.new('RGB', (1400, 1860), '#cfd5dc')
        draw = ImageDraw.Draw(sheet)
        for offset, path in enumerate(files[start:start + 4]):
            x, y = (offset % 2) * 700, (offset // 2) * 930
            picture = Image.open(path).convert('RGB')
            picture.thumbnail((680, 884))
            sheet.paste(picture, (x + (700 - picture.width) // 2, y + 36))
            draw.text((x + 12, y + 8), path.name, font=font, fill='#152b3b')
        sheet.save(destination / f'sheet-{start // 4 + 1:02}.png')
    print(f'{len(files)} images in {(len(files) + 3) // 4} QA sheets: {destination}')


def prepare_browser(receipt_path):
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    if receipt['status'] != 'captured_for_visual_review' or receipt['page_errors']:
        raise ValueError('Require a completed, error-free capture run')
    source = Path(receipt['scratch_directory']).resolve()
    if not source.is_relative_to(SCRATCH):
        raise ValueError('Browser scratch must remain on E:')
    destination = ROOT / 'report/figures' / receipt_path.stem
    if destination.exists():
        raise ValueError('Preserve previous capture directories')
    destination.mkdir()
    for name, expected in receipt['screenshots'].items():
        image = source / name
        if image.parent != source or digest(image) != expected:
            raise ValueError('Screenshot failed its capture hash')
        shutil.copyfile(image, destination / name)
    print(f'Preserved {len(receipt["screenshots"])} original browser captures in {destination}')


def publish(args):
    if not args.visually_reviewed:
        raise ValueError('Inspect every rendered page before setting --visually-reviewed')
    inputs = json.loads(args.inputs.read_text(encoding='utf-8'))
    visual_receipt = (json.loads(args.visual_review_receipt.read_text(encoding='utf-8'))
                      if args.visual_review_receipt else None)
    for kind, build, rendered, output in (
            ('report', args.report_build, args.report_render, args.report_output),
            ('presentation', args.deck_build, args.deck_render, args.deck_output)):
        build, rendered, output = build.resolve(), rendered.resolve(), output.resolve()
        if (not build.is_relative_to(SCRATCH) or not rendered.is_relative_to(SCRATCH)
                or not output.is_relative_to(ROOT / 'deliverables') or output.exists()):
            raise ValueError('Keep scratch on E: and preserve prior deliverables')
        source = inventory(ROOT / kind)
        if source != inputs[kind]:
            raise ValueError(f'{kind} sources changed since build input inventory')
        pdf = build / 'main.pdf'
        reader = PdfReader(pdf)
        pages = len(reader.pages)
        empty = [i + 1 for i, page in enumerate(reader.pages) if not page.extract_text().strip()]
        outside = []
        for i, page in enumerate(reader.pages):
            box = page.mediabox
            for ref in page.get('/Annots', []):
                rect = ref.get_object().get('/Rect')
                if rect and (float(rect[0]) < float(box.left) - 1
                             or float(rect[1]) < float(box.bottom) - 1
                             or float(rect[2]) > float(box.right) + 1
                             or float(rect[3]) > float(box.top) + 1):
                    outside.append(i + 1)
        images = sorted(rendered.glob('page-*.png'))
        if visual_receipt:
            reviewed = visual_receipt[kind]
            if (not reviewed['all_pages_reviewed'] or reviewed['rendered_pages'] !=
                    {p.name: digest(p) for p in images}):
                raise ValueError('Visual review receipt does not match current rendered pages')
        log = (build / 'main.log').read_text(encoding='utf-8', errors='replace')
        overfull = len(re.findall(r'Overfull \\[hv]box', log))
        unresolved = len(re.findall(r'(?:Citation|Reference) .+ undefined|There were undefined', log))
        if empty or outside or overfull or unresolved or len(images) != pages:
            raise ValueError(f'{kind} QA failed: pages={pages}, renders={len(images)}, empty={empty}, annotations={outside}, overfull={overfull}, unresolved={unresolved}')
        if kind == 'presentation' and pages != 12:
            raise ValueError('Preserve the twelve-slide presentation')
        shutil.copyfile(pdf, output)
        receipt = {
            'schema': 'investify-document-delivery-v3',
            'checked_utc': datetime.now(timezone.utc).isoformat(),
            'status': 'compiled_and_layout_reviewed_unsigned_working_draft',
            'output': output.relative_to(ROOT).as_posix(), 'pdf_sha256': digest(output),
            'pages': pages, 'empty_text_pages': empty, 'outside_page_annotations': outside,
            'source_entry': f'{kind}/main.tex', 'compiled_source_files': source,
            'source_inventory_scope': 'Conservative inventory of authored source/assets, including auxiliary figures',
            'compiler': {'path': 'E:/AI-Tools/Cache/tectonic-0.17.0/tectonic.exe',
                         'sha256': digest(Path('E:/AI-Tools/Cache/tectonic-0.17.0/tectonic.exe')),
                         'version': '0.17.0', 'engine': 'Tectonic XeTeX'},
            'build_directory': str(build), 'compile_log_sha256': digest(build / 'main.log'),
            'render_directory': str(rendered), 'rendered_pages': {p.name: digest(p) for p in images},
            'all_pages_visually_checked': True,
            'visual_review_method': 'Assistant inspected all numbered four-page QA sheets and inspected new screenshot/calibration pages at full size',
            'overfull_boxes': overfull, 'unresolved_citations': unresolved,
            'human_review_or_institutional_approval': False,
            'browser_ui_screenshots_included': kind == 'report',
            'pending': ['physical projector review', 'genuine rehearsal',
                        'actual student code defence/contributions', 'metadata and applicable approvals'],
            'previous_outputs_preserved': True,
        }
        if kind == 'presentation':
            receipt.update(slides=pages, format_requested='LaTeX/Beamer',
                           editable_diagrams_and_charts=True, notes_embedded_in_tex=True)
        if visual_receipt:
            receipt['visual_review_method'] = reviewed['method']
            receipt['visual_review_receipt'] = args.visual_review_receipt.resolve().relative_to(ROOT).as_posix()
            receipt['visual_review_receipt_sha256'] = digest(args.visual_review_receipt)
        path = ROOT / 'evidence' / f'handbook_{kind}_delivery_{args.run_id}.json'
        new_json(path, receipt)
        print(f'{kind}: {pages} pages, {output.name}, receipt {path.name}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    m = sub.add_parser('montage')
    m.add_argument('--source', type=Path, required=True)
    m.add_argument('--output', type=Path, required=True)
    b = sub.add_parser('prepare-browser')
    b.add_argument('--receipt', type=Path, required=True)
    i = sub.add_parser('inputs')
    i.add_argument('--output', type=Path, required=True)
    p = sub.add_parser('publish')
    for name in ('inputs', 'report-build', 'report-render', 'report-output',
                 'deck-build', 'deck-render', 'deck-output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--run-id', required=True)
    p.add_argument('--visually-reviewed', action='store_true')
    p.add_argument('--visual-review-receipt', type=Path)
    args = parser.parse_args()
    if args.command == 'montage':
        montage(args.source, args.output)
    elif args.command == 'prepare-browser':
        prepare_browser(args.receipt)
    elif args.command == 'inputs':
        if not args.output.resolve().is_relative_to(SCRATCH):
            raise ValueError('Build inventory is scratch on E:')
        new_json(args.output, {kind: inventory(ROOT / kind) for kind in ('report', 'presentation')})
    else:
        if not re.fullmatch(r'[a-zA-Z0-9_-]+', args.run_id):
            raise ValueError('Use a plain dated run ID')
        publish(args)


if __name__ == '__main__':
    main()
