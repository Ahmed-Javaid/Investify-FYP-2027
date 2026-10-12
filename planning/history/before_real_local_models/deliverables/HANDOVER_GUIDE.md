# Investify mid-evaluation working source handover

This package contains the implemented demo, original tracked code/history references, current working report sources and validation receipts. **It is a working source handover, not a submission-ready report/deck or a completed scientific/human evaluation.** The report is uncompiled; the presentation is content/notes only. Institutional fields/signatures and team review remain pending.

## Portable demonstration

Use Python 3.11 or later. From the extracted `code` directory:

```powershell
python -B scripts/serve_mideval_demo.py
```

Open `http://127.0.0.1:8765`. The portable path uses only the Python standard library. It reads 372 saved NVDA decisions, checks edited explanations, emits verified guided fallback, and supports an explicit prototype profile/separate retrospective linear comparator. It does not acquire prices, retrain or simulate an LLM. Stop with Ctrl+C.

```powershell
python -B -m unittest discover -s tests -p 'test_mideval*.py' -v
python -B scripts/verify_demo_artifacts.py --output ../evidence/your_artifact_check.json
python -B scripts/verify_mideval_demo.py --output ../evidence/your_live_check.json
python -B scripts/evaluate_mideval_llm.py --plan-only --output ../evidence/your_explainer_plan.json
```

These portable tests are a subset of the selected suite; existing NumPy-based tests and actual Streamlit tests require the viewer environment. Verification scripts work without `.git`, check the declared source inventory, and explicitly report Git state as unavailable rather than borrowing an ancestor repository's revision. Inventory hashes verify included contents, not origin/authorship authenticity.

Current AI review delivery checks: 103 portable tests, 62 live endpoint checks and all 372 saved records pass after ZIP extraction in a separate environment without NumPy/Streamlit/Torch/pytest. The original-source/AI-label/freeze audit also passes from the extracted bundle. The selected viewer suite has 136 passes and no skips, including 13 actual Streamlit widget tests. Exact archive hashes and clean-host receipts identify each dated bundle.

The current review bundle contains uncommitted source changes and the actual AI reference pilot. Its manifest records base HEAD 0a27ed1 and working-tree status explicitly; it does not claim the included changes belong to that commit. The earlier clean-commit source ZIP and its 92-test receipt remain preserved. Third-party tweet data has not been approved for public redistribution. This local handover does not publish the corpus.

## Streamlit viewer and studies

Install `code/requirements-demo-runtime.txt` in a separate viewer environment, then run `python -B -m streamlit run app/streamlit_app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false`. Cache/temp/venv work on this Windows machine belongs under `E:\AI-Tools\Cache`, `Temp` or `Work`. This viewer environment is separate from the scientific lock.

The Decision tab provides checked evidence/explanations and the profile comparator. Social Study reads actual supplied post/annotation/plan/model files and reports missing, invalid or partial data honestly. The offline sentiment runner requires genuine local classifier weights and a matched frozen plan. See `code/docs/local_llm_pilot.md`, `risk_comparator.md` and `social_selection.md` for contracts and real-study commands. Corpus/source access and report metadata checks are in the deliverables folder.

The actual 200-post AI reference pilot is included. No actual explainer completion, candidate-model score or human study result is included. Exact model access/identities and genuine labels are required. Both saved classifiers remain constant-Buy. The separate profile blend is unvalidated for investor suitability/predictive performance and does not modify those classifier outputs.

## Report and evidence

`report/main.tex` is the official-template working source; compile/review it only after confirming institutional fields, declarations and team contributions. `deliverables/presentation_outline.json` is a twelve-slide content draft; no PPTX has been authored/rendered because the required presentation runtime is unavailable. The bundle manifest records every included file hash; current engineering receipts are in `evidence`.

Scientific raw/store inputs, actual LLM/social evaluations, browser visual QA, remote GitHub CI and deployment are incomplete. Nothing has been pushed or published. Tool-assisted changes are attributed as such; historical student authorship is preserved and new student contributions are not inferred.
