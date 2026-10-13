"""Review the localhost presenter with an isolated headless Edge browser on E:."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import time
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = Path("E:/AI-Tools/Temp").resolve()
MODULES = Path("E:/AI-Tools/Work/investify-browser-tools").resolve()
for key in ("TEMP", "TMP"):
    os.environ[key] = str(SCRATCH)
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "E:/AI-Tools/Cache/playwright"
sys.path.insert(0, str(MODULES))


def snapshot(page, directory, name):
    page.locator('[data-testid="stMainBlockContainer"]').wait_for(state="visible")
    # Streamlit rerenders after widget events; wait for layout and fonts before capture.
    page.wait_for_timeout(600)
    page.wait_for_function("() => !document.querySelector('[data-stale=true]')")
    page.evaluate("() => document.fonts.ready")
    # Streamlit scrolls inside stMain. A taller real viewport exposes all content.
    page.evaluate("() => { const main=document.querySelector('[data-testid=stMain]'); if(main) main.scrollTop=0; }")
    viewport = dict(page.viewport_size)
    height = math.ceil(page.locator('[data-testid="stMainBlockContainer"]').bounding_box()['height']) + 10
    capture_viewport = dict(width=viewport['width'], height=max(viewport['height'], height))
    page.set_viewport_size(capture_viewport)
    page.wait_for_timeout(300)
    page.locator('[data-testid="stMainBlockContainer"]').screenshot(path=str(directory / (name + ".png")))
    page.set_viewport_size(viewport)
    page.wait_for_timeout(300)
    page.evaluate("() => { const main=document.querySelector('[data-testid=stMain]'); if(main) main.scrollTop=0; }")
    return {"name": name, "capture_viewport":capture_viewport, "aria": page.locator("body").aria_snapshot(),
            "geometry": page.evaluate("""() => {
              const header=document.querySelector('[data-testid="stHeader"]');
              const main=document.querySelector('[data-testid="stMainBlockContainer"]');
              const box=el=>{if(!el)return null;let r=el.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height};};
              return {viewport:{width:innerWidth,height:innerHeight},header:box(header),main:box(main),
                documentWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth,
                brand:box(document.querySelector('.brand')),
                mainStyle:main?{paddingTop:getComputedStyle(main).paddingTop,paddingBottom:getComputedStyle(main).paddingBottom,classes:main.className}:null,
                customStyles:Array.from(document.querySelectorAll('style')).map(e=>e.textContent).filter(t=>t.includes('block-container')).map(t=>t.slice(0,1400)),
                buttons:Array.from(document.querySelectorAll('button')).filter(el=>el.getBoundingClientRect().height>0).map(el=>({text:el.innerText,box:box(el)}))};
            }""")}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run",required=True)
    parser.add_argument("--mode",choices=("inspect","journey"),default="inspect")
    args=parser.parse_args()
    if not re.fullmatch(r"presenter_browser_[a-zA-Z0-9_-]+",args.run):
        raise ValueError("Use a plain, unique presenter_browser run name")
    directory=(SCRATCH / args.run).resolve()
    output=(ROOT / "evidence" / (args.run+".json")).resolve()
    if not directory.is_relative_to(SCRATCH) or directory.exists() or output.exists():
        raise ValueError("Preserve prior browser runs and keep scratch on E:")
    directory.mkdir()
    from playwright.sync_api import sync_playwright
    result={"schema":"investify-actual-presenter-browser-v1","checked_utc":datetime.now(timezone.utc).isoformat(),
            "url":"http://127.0.0.1:8507","method":"Playwright with installed headless Microsoft Edge and a fresh temporary profile",
            "mode":args.mode,"script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"snapshots":[],"page_errors":[]}
    result['ui_source_sha256'] = {str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in sorted((ROOT/'code/app').glob('presenter*.py'))}
    entry = ROOT/'code/app/streamlit_app.py'
    result['ui_source_sha256']['code/app/streamlit_app.py'] = hashlib.sha256(entry.read_bytes()).hexdigest()
    try:
        opener=build_opener(ProxyHandler({}))
        ready=False
        for _ in range(80):
            try:
                with opener.open(result["url"]+"/_stcore/health",timeout=1) as response:
                    ready=response.status==200
            except OSError:
                pass
            if ready:break
            time.sleep(.25)
        if not ready:raise RuntimeError("Task demo server did not become healthy")
        with sync_playwright() as pw:
            browser=pw.chromium.launch(channel="msedge",headless=True,chromium_sandbox=True)
            result["browser_version"]=browser.version
            page=browser.new_page(viewport={"width":1672,"height":860},device_scale_factor=1)
            page.set_default_timeout(30000)
            page.on("pageerror",lambda error: result["page_errors"].append(str(error)))
            page.goto(result["url"],wait_until="domcontentloaded")
            page.get_by_role("button",name="Open the decision walkthrough",exact=True).wait_for(state="visible")
            result["snapshots"].append(snapshot(page,directory,"overview-1672"))
            page.get_by_role("button",name="Open the decision walkthrough",exact=True).click()
            page.get_by_role("heading",name="Recorded decision",exact=True).wait_for(state="visible")
            page.get_by_role("button",name="Next",exact=True).wait_for(state="visible")
            page.get_by_text("Step 1 of 4",exact=True).wait_for(state="visible")
            result["snapshots"].append(snapshot(page,directory,"decision-1672"))
            if args.mode == "journey":
                page.get_by_text('Why the fresh calibration always chooses Buy', exact=True).click()
                page.get_by_text('The saved Buy map never outputs below', exact=False).wait_for()
                result['snapshots'].append(snapshot(page,directory,'calibration-1672'))
                page.get_by_role('button',name='Next',exact=True).click()
                page.get_by_role('heading',name='Evidence behind the decision',exact=True).wait_for()
                result['snapshots'].append(snapshot(page,directory,'evidence-1672'))
                page.get_by_role('button',name='Next',exact=True).click()
                page.get_by_role('heading',name='A profile changes the comparison',exact=True).wait_for()
                page.get_by_role('button',name='Cautious example',exact=True).click()
                page.get_by_text('Fictional example: cautious.',exact=False).wait_for()
                result['snapshots'].append(snapshot(page,directory,'profile-cautious-1672'))
                page.get_by_role('button',name='Higher-tolerance example',exact=True).click()
                page.get_by_text('Fictional example: higher tolerance.',exact=False).wait_for()
                result['snapshots'].append(snapshot(page,directory,'profile-tolerant-1672'))
                page.get_by_role('button',name='Next',exact=True).click()
                page.get_by_role('heading',name='An explanation must match its evidence',exact=True).wait_for()
                page.get_by_role('button',name='Inject wrong probability',exact=True).click()
                page.get_by_role('textbox',name='Explanation to check',exact=True).wait_for(state='visible')
                page.wait_for_function("() => document.querySelector('textarea')?.value.includes('1.00%')")
                page.get_by_role('button',name='Check explanation',exact=True).click()
                page.get_by_text('Candidate rejected',exact=True).wait_for()
                page.get_by_text('Verified fallback emitted',exact=True).wait_for()
                result['snapshots'].append(snapshot(page,directory,'explanation-rejected-1672'))
                page.get_by_role('button',name='Restore record facts',exact=True).click()
                page.wait_for_function("() => { const text=document.querySelector('textarea')?.value; return text && !text.includes('1.00%'); }")
                page.get_by_text('Check the current text to produce a verified output.',exact=False).wait_for()
                page.get_by_role('button',name='Check explanation',exact=True).click()
                page.get_by_text('Candidate accepted',exact=True).wait_for()
                result['snapshots'].append(snapshot(page,directory,'explanation-accepted-1672'))
                page.get_by_role('button',name='Recorded experiments',exact=True).click()
                page.get_by_role('heading',name='The deliberate leak fires',exact=True).wait_for()
                result['snapshots'].append(snapshot(page,directory,'leakage-1672'))
                page.get_by_role('radiogroup',name='Research study',exact=True).get_by_text('Sentiment comparison',exact=True).click()
                page.get_by_role('heading',name='Original sentiment models on the same posts',exact=True).wait_for()
                page.get_by_text('Original identities, receipts and limits',exact=True).wait_for()
                result['snapshots'].append(snapshot(page,directory,'social-1672'))
                page.get_by_role('radiogroup',name='Research study',exact=True).get_by_text('Teacher pilot',exact=True).click()
                page.get_by_role('heading',name='Teacher construction pilot',exact=True).wait_for()
                page.get_by_text('All source decisions are Buy.',exact=False).wait_for()
                result['snapshots'].append(snapshot(page,directory,'teacher-1672'))
                page.get_by_role('radiogroup',name='Workspace',exact=True).get_by_text('Design',exact=True).click()
                page.get_by_role('heading',name='Design connected to the code',exact=True).wait_for()
                result['snapshots'].append(snapshot(page,directory,'design-1672'))
                page.set_viewport_size({'width':1366,'height':768})
                result['snapshots'].append(snapshot(page,directory,'design-1366'))
                page.get_by_role('radiogroup',name='Workspace',exact=True).get_by_text('Overview',exact=True).click()
                page.get_by_role('button',name='Open the decision walkthrough',exact=True).wait_for()
                result['snapshots'].append(snapshot(page,directory,'overview-1366'))
            browser.close()
        result["status"]="captured_for_visual_review"
        result['layout_checks'] = {
            'no_horizontal_document_overflow': all(s['geometry']['documentWidth'] == s['geometry']['clientWidth'] for s in result['snapshots']),
            'brand_clears_fixed_header': all(s['geometry']['brand']['y'] >= s['geometry']['header']['height'] for s in result['snapshots'])}
        if not all(result['layout_checks'].values()) or result['page_errors']:
            raise RuntimeError('Captured journey has a browser error or layout regression')
    except Exception as error:
        result["status"]="failed"
        result["error"]=str(error)
    result["screenshots"]={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(directory.glob("*.png"))}
    result["scratch_directory"]=str(directory)
    output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print('Captured views:', ', '.join(item['name'] for item in result['snapshots']))
    print("Browser status:",result["status"],"receipt:",output)
    if result["status"]=="failed":raise RuntimeError(result["error"])


if __name__=="__main__":
    main()
