# Investify engineering reference

Technical setup, implementation, testing, CI/CD and PDF builds belong here.
Preparation and speaking allocations live in the [team guide](../team/MID1_TEAM_GUIDE.md);
continuation instructions live in the [agent handoff](../handoffs/AGENT_HANDOFF.md).

## Setup and implementation

Follow the [Windows setup](../team/MID1_TEAM_GUIDE.md#demo-setup). The recorded
Streamlit viewer needs Git, Python 3.11 and pinned demo dependencies. Fresh science
needs separate raw inputs, runtime and publisher weights. Credentials remain in
ignored `code/.env`; caches/scratch stay on E:\AI-Tools.

The portable interface runs from `code` with
`python -B scripts/serve_mideval_demo.py --port 8768`. It calls the real saved-record
checking/comparator path and has a separate layout from Streamlit.

| Component | Source | Contract |
| --- | --- | --- |
| UI and recorded cases | [presenter.py](../../code/app/presenter.py), [presenter_data.py](../../code/app/presenter_data.py) | One page/step; source-bound cases; invalidation on changes. |
| Authoritative record | [decision_record.py](../../code/src/investify/decision_record.py) | Probability, class, feature and attribution invariants. |
| Evidence context | [context.py](../../code/src/investify/explain/context.py) | Values/missing status, maintained meanings and raw-score scope. |
| Verification/recovery | [verifier.py](../../code/src/investify/explain/verifier.py), [pipeline.py](../../code/src/investify/explain/pipeline.py) | Check text/JSON independently; retain rejection; check fallback separately. |
| Profile/policy | [risk_profile_gl.py](../../code/src/investify/risk_profile_gl.py), [risk_comparator.py](../../code/src/investify/risk_comparator.py) | Eighteen explicit answers, restrictive allowance, confidence gate and fixed classifier; earlier scaling belongs to the historical comparator. |
| Scientific engine | [engine.py](../../code/src/investify/engine.py), [splits.py](../../code/src/investify/harness/splits.py) | Training/calibration/TreeSHAP, causal inputs and available-label purging. |
| Social replay | [recorded_social_replay.py](../../code/src/investify/recorded_social_replay.py) | Portable opaque provenance paths without changing frozen module/source bytes. |
| Teacher evidence | [teacher_session.py](../../code/src/investify/explain/teacher_session.py) | Genuine prose, deterministic JSON targets and grouped exports remain distinct. |

The profile implements five capacity factors and thirteen Grable-Lytton scoring items, using concise paraphrases; local suitability is unvalidated. Comparator
scaling fits the first 148 records and scores only the later 38. Missing technical
inputs refuse scoring; absent sentiment is disclosed. Neither branch personalizes
XGBoost or establishes suitability/performance. See [research](RESEARCH.md).

## CI/CD and tests

[Workflow](../../.github/workflows/mideval-evidence.yml): push main/gpt/**, pull
request and manual dispatch run Python 3.11 portable/UI jobs on Windows and
Ubuntu. Delivery depends on all four. Permissions are read-only; timeouts,
duplicate-run cancellation and fourteen-day retention are configured.

| Stage | Scope |
| --- | --- |
| Portable, both platforms | 183 portable tests, seven metadata/source guards, 372 archived records, 228 comparator probes, preview/plan-only and 62 real HTTP checks. |
| UI, both platforms | Ruff plus 24 legacy, 19 presenter and four selector tests: 47 UI tests. |
| Delivery | Nine guards; four same-commit passing receipts; source/log identities; reviewed PDF packaging and isolated extraction verification. |

Retained [hosted success](https://github.com/Ahmed-Javaid/Investify-FYP-2027/actions/runs/38426650755)
and [download verification](../../evidence/remote_ci_delivery_download_check_20261013.json)
prove their dated source snapshots. The previously checked main run is
https://github.com/Ahmed-Javaid/Investify-FYP-2027/actions/runs/38428835203.
The [revised-source run](https://github.com/Ahmed-Javaid/Investify-FYP-2027/actions/runs/38469231692) passed all five jobs for commit 5089998. Its delivered bundle was downloaded and its server digest, nested file manifest and current reviewed PDFs were independently checked; [download receipt](../../evidence/remote_ci_revision_download_20261014.json).

CD delivers source/PDF artifacts; production hosting is later work. CI does not
acquire current data, train/infer large models, rerun the full scientific study,
measure participant benefit or automatically render PDFs. Corpus/label/plan
checks disclose when original acquisition is not reconstructed. Overlapping
suite counts must not be added into a synthetic total.

Tests cover contradictions, omissions, malformed/nonfinite claims, strict-mode
rejection, fallback, 32,400 questionnaire combinations, scaling isolation,
thresholds, missing inputs, source/session changes, stale verdicts and incomplete
studies. Separate scientific tests cover calendars, joins, label availability,
purging, calibration endpoints, cache/store integrity and leakage canaries.
Software correctness is distinct from prediction quality.

From `code`, use new run directories:

```powershell
python -B scripts/run_mid1_ci.py --job evidence --output artifacts/ci_evidence/NEW_evidence
python -B scripts/run_mid1_ci.py --job streamlit-ui --output artifacts/ci_evidence/NEW_ui
```

Prepared dependencies and the owned Git checkout are required. Dirty receipts
cannot satisfy hosted clean-source delivery. CI temporarily declares source
identity and restores the original tracked `code/source_revision.json` bytes.

## Report and slide builds

Entries: [report/main.tex](../../report/main.tex) and
[presentation/main.tex](../../presentation/main.tex). Reviewed PDF/source hashes:
[current_delivery.json](../../deliverables/current_delivery.json). Current PDFs
are selected by the delivery configuration; this revision has 14 slides. Read the matching new review receipt for the report page count.

Use prepared Tectonic with TEMP/TMP and compiler cache under E:\AI-Tools. From
each source folder: `tectonic --outdir <new-directory> --keep-logs --keep-intermediates main.tex`.
Render with [render_pdf_windows.ps1](../../tools/render_pdf_windows.ps1), inspect
changed pages and publish a new dated receipt with
[review_mid1_artifacts.py](../../tools/review_mid1_artifacts.py). Preserve old outputs.

## Packaging and maintenance

[Groupmate packaging](../../tools/package_groupmate_handover.py) selects the
reviewed report/slides, original rubric, team guide and brief demonstration handout. The source delivery
uses [package_source_handover.py](../../tools/package_source_handover.py) and
[verify_source_handover.py](../../tools/verify_source_handover.py); hosted delivery
uses [run_mid1_delivery.py](../../tools/run_mid1_delivery.py).

Maintain these consolidated guides. Superseded generators, exports and planning
pages were removed with user approval after checkpoint `5f6b6ff`; tracked earlier
versions remain in Git history. The [cleanup audit](../../evidence/workspace_cleanup_20261014.json)
records removal and protected current-file identities.

## Audit revision environments and checks

`code/pyproject.toml` and `uv.lock` describe scientific training (NumPy 1/pandas 2).
`code/requirements-demo-runtime.txt` is the separate recorded viewer (NumPy 2/pandas 3).
Do not combine them. The proposed NFR-5 uses a 16 GB-class GPU; the recorded local
10,240 MiB device is a different environment. No QLoRA timing or memory target
is claimed as met.

The institutional class/logo are unchanged. This workstation has prepared
Tectonic 0.17.0 (XeTeX and bibliography processing); standalone xelatex/bibtex
executables are unavailable. Build with `python -B tools/build_mid1_pdfs.py --run-id NEW`
from the repository root, then render and inspect before publishing new PDFs.
Use `--expected-slides 14` with the publication reviewer. Original evidence JSON
and scientific run files must remain unchanged; new receipts get fresh identities.
