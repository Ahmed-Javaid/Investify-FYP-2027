# Mid-evaluation explanation increment

## Recorded teacher increment

The Teacher Study tab replays six actual assistant explanations and separate four-training/two-validation exports, with date grouping and no held-out test inputs. No student model is trained or evaluated. Current selected suite: 212 passes, zero skips, including 20 Streamlit cases. The teacher's exact serving identity/revision is unavailable; the factual JSON payload is constructed from original records, while the prose is assistant-generated. See ../../deliverables/ASSISTANT_TEACHER_PILOT.md.

11 October 2026. Baseline: `1dc24e0`; working branch: `gpt/mid-eval`.

The original payload-first verifier could accept an incorrect displayed probability beside correct JSON. The corrected contract checks both representations against the saved decision, scores coverage from visible text, and reports the worse numeric/directional fidelity of text and JSON. Any known contradictory claim fails regardless of aggregate score. Feature values, attribution target class, contributor count, mandatory decision/probabilities/notice, and malformed payloads are checked. The rejected candidate report survives verified fallback.

Strict mode rejects every line outside the supported template grammar. Default mode preserves the existing unverifiable-rate policy, including its documented acceptance of a single vague line. Neither mode is a semantic verifier for arbitrary natural-language market explanations. The current contract is `mideval-complete-evidence-v4`. Top-k recall retains the V2 numeric/target slots; the richer generation gate additionally requires every feature's value, contribution, direction and target, all reviewed definitions, family totals and attribution scope in both prose and JSON.

## Run the live portable demo

From this code directory:

```powershell
python -B scripts/serve_mideval_demo.py
```

Open `http://127.0.0.1:8765`. Select either corpus and a session, inspect technical/news evidence, inject a labelled error, and verify it. Correct JSON cannot hide the wrong display text. The displayed fallback and candidate failure report are separate. This is a local HTTP interface calling the real Python verifier, using historical records; no LLM generation or retraining is simulated.

From another shell, with the server running:

```powershell
python -B scripts/verify_mideval_demo.py --output ../evidence/live_demo_verification.json
```

The check runs clean/corrupt/guided cases on three sessions from each corpus and separate risk-comparator/refusal probes. Source hashes must match the running server; restart it after changing source. Ctrl+C stops the server.

## Run verification

```powershell
python -B -m unittest discover -s tests -p 'test_mideval*.py' -v
python -B scripts/verify_demo_artifacts.py --output ../evidence/demo_artifact_verification.json
```

The selected pytest runtime additionally runs `test_verifier.py`, `test_emit_pipeline.py`, the `test_mideval*` modules, and `test_streamlit_mideval.py`. Current result: **212 passed, zero skipped**. All **372 saved records** retain numeric and complete-guided template acceptance. The live endpoint exercise passes **62 checks**. A separate audit passes **228** arithmetic checks on actual held-out rows and labelled profile scenarios. This is not the full scientific suite or a human validation study.

The default-mode fixture matrix is written to a new evidence file when `INVESTIFY_VERIFIER_REPORT` is set; ordinary tests no longer overwrite the historical artifact. It has 112 cases: 80 corruptions detected, 16 clean accepted, 16 vague corruptions accepted, and zero clean rejected. Strict-mode rejection of unsupported sentences is tested separately.

## Subsequent local LLM increment

The [local pilot](local_llm_pilot.md) now implements local structured-output requests, bounded retries/timeouts, token authentication, raw/failed/truncated attempt retention, complete maintained-definition checking and verified guide fallback. Both interfaces expose the path. Real evaluation requires a previously saved matching data/code plan; zero completions receives no model-quality score.

The complete guided comparator now states every feature contribution and both family totals, preserving missing values and neutral zero attribution. Non-top-k contributors receive descriptive evidence without a headline rank. Known numerical, directional, scope or target contradictions in either representation fail. No real LLM completion has been obtained. Earlier V2 evidence is retained under the parent workspace's `evidence/history/a99de5f`.

## Streamlit and full reproduction

The Streamlit Decision tab shows the failed candidate report and offers a text-only corruption and strict-mode control. Invalid records show an explicit error. The Leakage Lab labels its historical table and disables re-runs for missing, empty, unreadable or structurally invalid data or absent runtime modules. Its preflight does not validate row/schema/cache coverage or the scientific lock. Eighteen actual AppTest cases pass; Windows/Linux CI jobs are configured but unexecuted remotely.

The viewer runtime was restored from a broader existing E: pip cache, with two missing pure-Python dependencies prepared from unchanged vendor source/fallback code and retained licenses. Receipts are under the parent workspace's evidence directory. `requirements-demo-runtime.txt` freezes the tested viewer environment: Streamlit 1.63.0, NumPy 2.4.6 and Pandas 3.0.6. It is separate from the old scientific lock. `pip check`, actual AppTest cases and HTTP health checks pass.

```powershell
& 'E:\AI-Tools\Temp\investify-ui-py311\Scripts\python.exe' -B -m streamlit run app/streamlit_app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

Open `http://127.0.0.1:8501`. On another host, install the viewer runtime file in a separate environment. The full scientific dependency lock and raw/store inputs are not restored. Browser surfaces are unavailable, so browser interaction/visual QA is not claimed. No GitHub job or deployment has been executed.

Keep environments, caches and scratch under `E:\AI-Tools\Temp`, `Cache` and `Work`. Do not install a project environment on C:. Use the existing full lock for scientific reproduction when access is restored; the demo dependency subset is not that environment.

## Demonstration and traceability

[The demo/defence guide](../../deliverables/DEMO_AND_DEFENCE_GUIDE.md) ties the actual controls, rejection/fallback and refusal paths to source functions and scientific limits. [The requirements matrix](../../deliverables/REQUIREMENTS_TRACEABILITY.md) checks 18 engineering IDs against exact functions and named passing tests, and separately records original first-mid gaps. From the workspace root, `python -B GPT_MIDEVAL/tools/verify_requirements_traceability.py --tests GPT_MIDEVAL/evidence/current_tests.xml --output GPT_MIDEVAL/evidence/traceability_NEW.json` requires a new dated receipt. This does not close institutional or scientific acceptance.

## Source handover

The tracked code can be delivered without `.git`. Verification/evaluation tools read a checked source inventory in a bundle, report absent Git state explicitly, and refuse a modified inventory file rather than silently claiming a revision. An ancestor repository never supplies the bundle's identity. Working report/evidence sources are packaged separately from final rendered artifacts; missing models, labels, compiler/runtime and external CI remain disclosed. See the parent workspace's `deliverables/HANDOVER_GUIDE.md`.

## Scope and evidence

Predictions and historical experiment artifacts are unchanged: both saved models predict Buy throughout. The [risk increment](risk_comparator.md) conditions a separate retrospective linear blend on an explicit prototype profile; it does not personalize the saved classifier or establish suitability/predictive performance. Social sentiment, real LLM results and user-study evidence remain pending. The coding assistant performed these changes; student review/authorship must be disclosed accurately.
