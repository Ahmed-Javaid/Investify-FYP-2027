"""Build a standalone evidence preview from committed historical records."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from investify.decision_record import DecisionRecord
from investify.explain.context import build_context
from investify.explain.pipeline import emit

PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Investify evidence explorer</title>
<style>
:root{font-family:system-ui,sans-serif;color:#172b36;background:#f6f7f4}body{margin:0}main{max-width:1100px;margin:auto;padding:35px 25px}header{border-bottom:1px solid #ccd5d6;padding-bottom:20px}h1{font-size:34px;margin:8px 0}h2{font-size:22px;margin-top:28px}.eyebrow{font-size:13px;letter-spacing:2px;color:#35636b}.muted{color:#53656b;font-size:14px}.controls{display:flex;flex-wrap:wrap;gap:22px;margin:22px 0}label{display:grid;gap:7px;font-size:14px}select{font:inherit;background:white;border:1px solid #9eafb3;border-radius:5px;padding:9px;min-width:200px}.notice{background:#fff1d0;padding:16px;border-left:4px solid #b38322;margin:20px 0}.facts{display:flex;gap:35px;flex-wrap:wrap;margin:24px 0}.fact strong{display:block;font-size:27px;margin-top:5px}.fact span{font-size:13px;color:#53656b}table{width:100%;border-collapse:collapse}th{text-align:left;color:#53656b;font-size:13px}th,td{padding:14px 8px;border-bottom:1px solid #d7e0df;vertical-align:top}td:first-child{width:62%}td.number{white-space:nowrap;font-variant-numeric:tabular-nums}.definition{font-size:14px;line-height:1.5;margin-top:6px;color:#425b65}a{color:#156d80}footer{margin-top:30px;padding-top:20px;border-top:1px solid #ccd5d6;font-size:14px}.scroll{overflow:auto}code{font-size:12px}#probabilities{line-height:1.7}@media(max-width:650px){main{padding:22px 15px}h1{font-size:28px}.facts{gap:20px}td:first-child{min-width:250px}}
</style></head><body><main>
<header><div class="eyebrow">F26-003-INVESTIFY · MID EVALUATION WORKING PREVIEW</div><h1>Understand the evidence behind a decision</h1><p class="muted">A historical record explorer using the existing model outputs. This preview uses reviewed definitions and deterministic verification; an LLM has not been connected.</p></header>
<div class="notice"><strong>Current model limitation</strong><br>Both stored evaluation folds predict Buy for every session. Calibration has not produced a useful predictor. A verified explanation establishes consistency with the recorded model output, not predictive skill or a safe trade.</div>
<div class="controls"><label>News corpus<select id="corpus"><option value="alpaca">Alpaca / Benzinga</option><option value="fnspid">FNSPID</option></select></label><label>Recorded session<select id="session"></select></label></div>
<div class="facts"><div class="fact"><span>Recorded model decision</span><strong id="decision"></strong></div><div class="fact"><span>Prediction horizon</span><strong id="horizon"></strong></div><div class="fact"><span>Template verification</span><strong id="verification"></strong></div></div>
<div id="probabilities"></div><p class="muted" id="interpretation"></p>
<section><h2>Technical analysis</h2><div class="scroll"><table><thead><tr><th>Indicator and meaning</th><th>Recorded value</th><th>Raw-score contribution</th><th>Effect on selected class</th></tr></thead><tbody id="technical"></tbody></table></div></section>
<section><h2>News sentiment</h2><div class="scroll"><table><thead><tr><th>Feature and meaning</th><th>Recorded value</th><th>Raw-score contribution</th><th>Effect on selected class</th></tr></thead><tbody id="news"></tbody></table></div></section>
<footer><p id="coverage"></p><p id="data"></p><p id="notice"></p><p class="muted" id="model"></p></footer>
</main><script>
const datasets=__DATA__;
const corpus=document.getElementById('corpus'),session=document.getElementById('session');
const format=x=>x===null?'Missing':Number(x).toLocaleString(undefined,{maximumSignificantDigits:6});
function table(id,features){const body=document.getElementById(id);body.replaceChildren();for(const f of features){const tr=document.createElement('tr'),label=document.createElement('td');const strong=document.createElement('strong');strong.textContent=f.label;label.append(strong);const definition=document.createElement('div');definition.className='definition';definition.textContent=f.meaning;label.append(definition);if(f.reference){const a=document.createElement('a');a.href=f.reference;a.target='_blank';a.rel='noopener';a.textContent='Reference';definition.append(' ',a);}tr.append(label);for(const text of [format(f.value),(f.shap_value>0?'+':'')+format(f.shap_value),f.effect_on_predicted_class]){const td=document.createElement('td');td.className='number';td.textContent=text;tr.append(td);}body.append(tr);}}
function render(){const r=datasets[corpus.value][Number(session.value)];document.getElementById('decision').textContent=r.decision;document.getElementById('horizon').textContent=r.horizon_days+' sessions';document.getElementById('verification').textContent=r.template_verification_passed?'PASS':'FAIL';document.getElementById('probabilities').textContent='Model probabilities: '+Object.entries(r.probabilities).map(([k,v])=>k+' '+(v*100).toFixed(2)+'%').join(' · ');document.getElementById('interpretation').textContent=r.interpretation;table('technical',r.features.filter(f=>f.family==='Technical analysis'));table('news',r.features.filter(f=>f.family==='News sentiment'));document.getElementById('coverage').textContent=r.coverage.social_sentiment+'. '+r.coverage.risk_conditioning+'.';document.getElementById('data').textContent=r.data_status+'. The recorded session is '+r.session_date+'.';document.getElementById('notice').textContent=r.notice;document.getElementById('model').textContent='Model reference: '+r.model_version;}
function selectCorpus(){session.replaceChildren();datasets[corpus.value].forEach((r,i)=>{const option=document.createElement('option');option.value=i;option.textContent=r.session_date;session.append(option);});session.value=Math.floor(datasets[corpus.value].length/2);render();}
corpus.addEventListener('change',selectCorpus);session.addEventListener('change',render);selectCorpus();
</script></body></html>'''


def export_preview(output: Path) -> int:
    datasets = {}
    for corpus, filename in [("fnspid", "decision_records.json"), ("alpaca", "decision_records_alpaca.json")]:
        data = json.loads((ROOT / "artifacts" / filename).read_text())
        rows = []
        for payload in data["decision_records"]:
            record = DecisionRecord.from_dict(payload)
            context = build_context(record, corpus=corpus)
            context["template_verification_passed"] = emit(record).verification.passed
            rows.append(context)
        datasets[corpus] = rows
    encoded = json.dumps(datasets, allow_nan=False).replace("</", "<\\/")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(PAGE.replace("__DATA__", encoded), encoding="utf-8")
    return sum(len(rows) for rows in datasets.values())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    count = export_preview(args.output)
    print(f"Exported {count} real records to {args.output}")
