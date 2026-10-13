"""Capture actual focused browser panels for the revised report, retaining raw views."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = Path('E:/AI-Tools/Temp/presenter_browser_20261014_revision05')
OUTPUT = ROOT / 'evidence/presenter_browser_20261014_revision05.json'
os.environ.update(TEMP='E:/AI-Tools/Temp', TMP='E:/AI-Tools/Temp',
                  PLAYWRIGHT_BROWSERS_PATH='E:/AI-Tools/Cache/playwright')
sys.path.insert(0, 'E:/AI-Tools/Work/investify-browser-tools')


def main():
    from playwright.sync_api import sync_playwright
    if SCRATCH.exists() or OUTPUT.exists():
        raise ValueError('Preserve previous captures')
    SCRATCH.mkdir()
    result = {'schema': 'investify-revised-panel-capture-v1', 'checked_utc': datetime.now(timezone.utc).isoformat(),
              'scratch_directory': str(SCRATCH), 'page_errors': [], 'panels': {},
              'method': 'Actual headless Edge screenshots; focused panels use native browser clip, not image alteration.'}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width': 880, 'height': 1000}, device_scale_factor=1)
        page.on('pageerror', lambda error: result['page_errors'].append(str(error)))
        page.goto('http://127.0.0.1:8507', wait_until='domcontentloaded')
        page.get_by_role('button', name='Open the decision walkthrough', exact=True).wait_for()
        page.get_by_role('button', name='Open the decision walkthrough', exact=True).click()

        def capture(name, heading, step):
            page.get_by_role('heading', name=heading, exact=True).wait_for()
            page.wait_for_timeout(650)
            page.wait_for_function("() => !document.querySelector('[data-stale=true]')")
            page.evaluate("() => { const el=document.querySelector('[data-testid=stMain]'); if(el) el.scrollTop=0; }")
            height = int(page.locator('[data-testid=stMainBlockContainer]').bounding_box()['height']) + 150
            page.set_viewport_size({'width': 880, 'height': max(1000, height)})
            page.wait_for_timeout(250)
            page.screenshot(path=str(SCRATCH / (name + '-raw.png')))
            top = page.get_by_role('heading', name=heading, exact=True).bounding_box()
            bottom = page.get_by_text('Step ' + str(step) + ' of 4', exact=True).bounding_box()
            panel = {'x': max(0, top['x'] - 8), 'y': max(0, top['y'] - 8),
                     'width': min(864, top['width'] + 16), 'height': bottom['y'] - top['y'] - 10}
            if name == 'decision':
                edge = page.get_by_role('heading', name='Largest recorded contributions', exact=True).bounding_box()
                panel['height'] = edge['y'] - panel['y'] - 8
            elif name == 'explanation':
                panel['height'] = min(panel['height'], 590)
            page.screenshot(path=str(SCRATCH / (name + '.png')), clip=panel)
            result['panels'][name] = {'clip': panel, 'visible_text': page.locator('body').inner_text()}

        capture('decision', 'Recorded decision', 1)
        page.get_by_text('Risk profile', exact=True).click()
        page.get_by_role('button', name='Cautious example', exact=True).click()
        capture('profile', 'Risk capacity and tolerance', 3)
        page.get_by_text('Explanation check', exact=True).click()
        page.get_by_role('heading', name='An explanation must match its evidence', exact=True).wait_for()
        page.wait_for_timeout(800)
        page.get_by_role('button', name='Inject wrong probability', exact=True).click()
        page.wait_for_function("() => document.querySelector('textarea')?.value.includes('1.00%')")
        page.wait_for_timeout(800)
        page.get_by_role('button', name='Check explanation', exact=True).click()
        page.get_by_text('Candidate rejected', exact=True).wait_for()
        capture('explanation', 'An explanation must match its evidence', 4)
        browser.close()
    result['status'] = 'captured_for_visual_review'
    result['screenshots'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in SCRATCH.glob('*.png')}
    result['ui_source_sha256'] = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in (ROOT / 'code/app').glob('presenter*.py')}
    with OUTPUT.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print('Captured three focused panels plus their unmodified raw browser views.')


if __name__ == '__main__':
    main()
