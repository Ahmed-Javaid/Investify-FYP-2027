# Investify — CLAUDE.md

FAST NUCES FYP (F26-003-QuantamentalAI). A leakage-audited, point-in-time advisory pipeline with a deterministic explanation verifier. Full context: `docs/Investify_Concept.docx` (the proposal), `docs/Investify Updated.pdf` (defence deck), `docs/FAST_FYP_Student_Idea_Selection_Guide_School_of_Computing.pdf` (university requirements this project is judged against).

## Active work right now

`docs/investify_poc_claude_code_brief.md` — the proposal-defence POC spike, due **Friday**. Read it before touching anything under `src/`. It is phased and self-gating:

- **Phase 0 is a hard stop.** Probe FNSPID on Hugging Face (list files, don't download the corpus), report findings, wait for confirmation before writing any pipeline code.
- Every phase boundary after that also stops for a report before continuing.
- If Phase 0 shows FNSPID unworkable, that is a finding to report, not a gap to paper over — do not silently swap in a different corpus or synthetic headlines.

Do not skip ahead to Phase 1+ code because it seems obvious what's next. The brief's sequencing exists because the team is time-boxed to Friday.

**Phase 0 is done and confirmed (2026-09-10).** Scope decision recorded, see `artifacts/phase0_report.md` §5/§7:

- **The spike is now NVDA-only**, not AAPL/NVDA/TSLA. Coverage check on both FNSPID files found AAPL and TSLA both have a real gap — zero 2021 rows for either, AAPL also missing 2018-2019 — while NVDA is the only ticker with continuous 2018-2023 coverage.
- This fixes coverage, **not** granularity: NVDA actually has the worst midnight-only-timestamp fraction of the three (99.78%). The `E_SAMEBAR_TEXT` leak arm runs on roughly 26 genuinely-timestamped rows across all of 2018-2023 — user confirmed proceeding anyway, reported honestly as a small-N illustration, not a corpus-wide result. Don't quietly inflate confidence in that arm's result.
- Corpus source: `Stock_news/nasdaq_exteral_data.csv` from `Zihan1004/FNSPID` (not `All_external.csv`, which stops mid-2020 for all three tickers). Extraction script: `scripts/phase0_pull_nasdaq_ticker_news.py` (fixed version — see its docstring for the pandas bug it works around). Extracted subset lives at `data/raw/fnspid_nasdaq_external_aapl_nvda_tsla.csv` (gitignored, reproducible via the script + the sha256 in `artifacts/corpus_manifest.json`).

**Phase 1 is done (2026-09-10).** `artifacts/phase1_report.md` has the full detail. Store, calendar, as-of join, indicators, FinBERT sentiment, labels, fold-local scaling all built and unit-tested (29/29 passing), then run end-to-end on real NVDA data via `scripts/build_phase1_feature_matrix.py`: 1,509 price bars (zero orphans), 11,708 headlines scored, feature matrix at `data/store/feature_matrix.parquet` (gitignored, reproducible). The 303 bars with no sentiment attached cluster in March 2021 — the same sparse patch Phase 0 already found, confirming it downstream rather than surfacing a new bug.

**Next: Phase 2 onward (harness, engine, verifier, demo, POC_REPORT.md).** See `docs/phase2_4_plan.md` for the module breakdown — written so the work can be split across parallel subagents without them stepping on each other or re-deriving decisions already made. Two things the user has emphasized beyond what the original brief says:
- **The Phase 4 demo is not optional filler and should not be the first thing cut under time pressure.** The user wants a real small MVP with a basic UI, not just a written report with charts. If time is genuinely short, cut scope *inside* the demo (fewer polish touches) before cutting the demo itself.
- **Working convention for this stretch of the project:** the orchestrating session runs on Opus 5 and dispatches Sonnet subagents for parallelizable work *within* a phase (e.g. the 5 arms, or engine+verifier as separate tracks) — but still stops and reports to the user at each phase boundary before continuing, per the brief's own gating. Don't let subagent parallelism inside a phase turn into skipping the report-and-wait step between phases.

## Hard constraints

- macOS, Apple M1 Pro, 16GB, **no CUDA**. CPU, or `torch` MPS where it helps.
- Python 3.11, managed via `uv` — the system `python3` is 3.14, don't build the venv against it. Pin every dependency in a lock file.
- The panel demo must run on this machine in under two minutes from cached artefacts.
- Never fabricate a result — every number in `POC_REPORT.md` comes from a run that actually happened.
- Never substitute synthetic text for real dated headlines in the real experiment. Synthetic fixtures are fine for unit tests only, and must be labelled as fixtures.
- Fail loudly. No silent `except: pass`, no default fallback that hides a missing input.
- A leaking result and a clean result are both findings. Don't tune anything to make `A_CLEAN` or any control look better than it is.

## Repo layout

Once Phase 1 starts, code lives at repo root per the brief's layout: `src/investify/`, `tests/`, `config/`, `artifacts/` (committed — results, hashes, figures), `app/streamlit_app.py`. `artifacts/` is evidence, not scratch — don't gitignore it. Raw corpus pulls and model caches go under `data/raw/` / `.cache/`, which are gitignored.

## Team ownership (full two-semester project)

From the concept doc's work division — relevant once the project moves past the Friday spike:

- **Soban Ahmad** (you) — **point-in-time harness, leakage tests, dual-timestamp schema, parity test**, decision engine, calibration, SHAP, verifier, QLoRA distillation.
- **Ahmed Javaid** — deployment.
- **Rafay Ul Haq** — risk profiling, sentiment pipeline, degraded operation, acceptance testing, frontend.

**Ownership change (2026-09-10):** the harness and leakage work moved from Ahmed to Soban. It was originally Ahmed's declared area and Soban built the proposal-defence spike solo because it was the highest-risk assumption the team needed proven; the ownership now matches who actually built and understands it. Soban therefore owns both of the project's declared contributions — the leakage-audited harness and the deterministic verifier. Ahmed retains deployment. This supersedes the concept doc's original work division, and the concept doc should be updated to match at the next revision.

## Explicitly out of scope for the spike (do not build)

No LLM (local or hosted) — explanation layer is a deterministic template only. No Optuna/hyperparameter search — one fixed XGBoost config everywhere. No Docker, cloud deployment, FastAPI, schedulers. No live news feeds — historical only. No social/crypto sentiment, CryptoBERT, divergence features. No 1-month horizon, portfolio logic, position sizing, Sharpe/drawdown. These all belong to the full-semester build, not this spike.

## Change control

Once a scope decision is made (committed core, evaluation metrics, architecture), changing it gets recorded — what changed, why, what evidence prompted it — not silently altered. This mirrors the university's own requirement (guide §5.3) and the concept doc's change-control section.
