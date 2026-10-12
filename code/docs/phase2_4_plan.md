# Phase 2–4 module breakdown (draft, for brainstorming validation)

Written at the Phase 1→2 handoff to size the remaining work for parallel
subagent execution without duplicated context-discovery or conflicting
edits. **This is a draft the new session should still run through the
brainstorming skill with the user before executing** — it is a strong
starting point, not a pre-approved plan.

Scope confirmed with the user at handoff time: build **everything
remaining** (Phase 2 → Phase 3 → Phase 4 → `POC_REPORT.md`), not just
Phase 2. The Phase 4 demo is explicitly **not** the first thing to cut
under time pressure — the user wants a real small MVP with a basic UI,
not just a report with charts. If time is short, trim polish inside the
demo before cutting it.

A scope nuance worth getting right early: **risk profiling is not a
model input for this spike.** Brief section 2's in-scope list has no
risk feature feeding the XGBoost model — the model's only inputs are
technical indicators + sentiment features (already built in Phase 1).
The risk quiz appears *only* in Phase 4 (Tab 2 of the demo) for display
alongside a decision. The decision record's `risk_tier` field (brief
§7) should be populated from whatever the demo's quiz produces, not
computed by `engine.py`. Don't build risk-conditioning into the model —
that's full-semester scope, not this spike's.

---

## Phase 2: the leakage harness and five arms

**Everything held constant across arms except temporal discipline**
(brief §6): same features (from Phase 1's feature matrix), same XGBoost
config, same seed (42), same folds where applicable.

| Module | What it does | Depends on |
|---|---|---|
| `harness/splits.py` | Expanding purged walk-forward CV (6 folds, 5-day embargo) for the clean/purged arms; shuffled K-fold for `B_SHUFFLED`; no-purge variant for `C_NOPURGE` | Phase 1 feature matrix only |
| `harness/metrics.py` | Macro-F1 per fold (mean+SD), stratified-random baseline from the **training fold's** class distribution, lift = macro-F1 − baseline, bootstrap CI on lift (10,000 resamples) | Independent — no dependency on splits.py |
| Arm feature variants | `D_CENTRED`: one indicator (suggest `dist_sma200` or `bollinger_pos`) recomputed with a centred window instead of trailing — small, isolated change to `features/indicators.py` (new function, don't mutate the backward-only ones Phase 1 already tested). `E_SAMEBAR_TEXT`: alternate session-mapping — text maps to the SAME session it published in rather than next, after-close items join the just-closed bar. Small variant of `ingest/news.py::map_to_sessions` (new function, e.g. `map_to_sessions_samebar`) | Phase 1's calendar/indicators modules |
| `harness/arms.py` | The five arm configurations, wiring splits.py + metrics.py + the feature variants together | splits.py, metrics.py, arm feature variants |
| `harness/run_spike.py` | Orchestrator: runs all 5 arms × 2 horizons, writes `artifacts/results.json` + `results.csv` (one row per arm per horizon: macro-F1, SD, chance, lift, CI bounds, verdict) + a grouped bar chart with the 0.03 threshold line. Records seed, snapshot hashes, corpus manifest hash, package versions, git commit | arms.py |
| `tests/test_leak_canary.py` | **The crux test.** Asserts `A_CLEAN` does NOT breach the 0.03 lift threshold AND `D_CENTRED` DOES. Build fails if the canary goes quiet | arms.py, metrics.py |

**Suggested parallel split:** one subagent on `splits.py` + its tests,
one on `metrics.py` + its tests (fully independent of splits.py), one
on the two arm feature variants (small, isolated). Main agent integrates
into `arms.py` + `run_spike.py` once those land, then runs the leak
canary.

**Do not tune anything to produce a nice-looking result** (brief §6) —
if `A_CLEAN` shows signal, that's a leakage alarm in the harness itself
and must be investigated, not smoothed over.

**Remember Phase 0/1's findings apply here too:** `E_SAMEBAR_TEXT`'s
result should be reported against the ~26-row real-timestamp caveat
from `artifacts/phase0_report.md` §3/§7 — don't let the harness's clean
mechanics imply more statistical confidence than the underlying data
supports.

---

## Phase 3: engine, attribution, verifier

| Module | What it does | Depends on |
|---|---|---|
| `engine.py` — decision record schema | A frozen schema (dataclass or pydantic): ticker, session date, decision, calibrated class probabilities, full feature vector, SHAP vector, base value, top-k contributors, risk tier, model version, data hashes, timestamps | Nothing — define this first, fast, before the two tracks below branch |
| `engine.py` — model | Fixed XGBoost config (`hist` tree method, class weights, macro-F1 reported), isotonic calibration on a held-out fold, Brier score + reliability curve, transparent linear baseline `C = R·S + (1−R)·T` mapped to 3 classes as comparator | Decision record schema, Phase 1 feature matrix |
| `engine.py` — attribution | TreeSHAP, path-dependent, no interaction values | The trained model |
| `tests/test_shap_additivity.py` | Contributions + base value = model output, within tolerance, for every emitted decision | Attribution |
| `explain/template.py` | Deterministic English from a decision record — grounded by construction, no model | Decision record schema only (can start before the model track finishes) |
| `explain/verifier.py` | Six checks: numeric extraction, tolerance matching, sign/direction, rank consistency, closed-vocabulary validation, claim-level scoring. Reports numeric fidelity (≥0.98), directional consistency (≥0.95), claim recall (≥0.80), unverifiable-claim rate (≤0.15) | Decision record schema only |
| `explain/fixtures.py` | Corrupted-explanation generator: one variant per error class (wrong probability, wrong SHAP magnitude, flipped direction, promoted minor feature, invented feature name, vague unverifiable sentence) | template.py, verifier.py |
| `tests/test_verifier.py` | Verifier catches every corruption, passes the clean original; confusion matrix over ~100 generated fixtures | fixtures.py |

**Suggested parallel split:** define the decision record schema first
(quick, main agent). Then two tracks in parallel — Track A: model +
SHAP + `test_shap_additivity.py`. Track B: template + verifier +
fixtures + `test_verifier.py` (Track B can build and test against a
handful of *hand-constructed* decision records while Track A is still
training, then swap in real ones for final integration). Converge at
the end: any explanation failing verification gets replaced by the
deterministic template, never emitted unverified.

---

## Phase 4: the demo (only after Phase 3 is green)

Streamlit, two tabs, running from cached artefacts in under two
minutes (brief §8). **User wants a real working MVP here, not a
placeholder.**

| Module | What it does |
|---|---|
| Tab 1 — Leakage Lab | Arms table, bar chart with the 0.03 threshold line, a button that re-runs one arm live so the panel watches the leak appear. Snapshot hash + seed shown on screen. |
| Tab 2 — Decision | Short risk quiz (a few capacity questions + a Grable-Lytton subset), reconciled by taking the **more restrictive** of capacity/tolerance into a 3-tier profile (display only — see the scope note at the top of this doc). Since the spike is NVDA-only, the "ticker picker" is trivial (one option) — a date picker over the covered range is the real control. Shows: decision, calibrated probability, SHAP contribution bar chart, template explanation, per-claim verifier report as a table. A "corrupt this explanation" control injects an error and shows the verifier rejecting it and the template taking over. |
| Every screen | Non-advice notice + the horizon, always visible. |

**Suggested split:** Tab 1 and Tab 2 are fairly independent Streamlit
components — reasonable to parallelize across two subagents, main agent
integrates into one `app/streamlit_app.py` and does a real click-through
verification before calling it done (per the project's standing rule:
test UI features in a browser, don't just claim success from code review).

---

## POC_REPORT.md (written last, by the main agent — not delegated)

Structured around the five questions the university guide requires
(brief §9, guide §12): what risky assumption was tested, what
input/setup was used, what result was obtained, what was learned or
disproved, what it changes in the design/plan. Must include a "what
this spike does not establish" section — update the brief's own
template here for the NVDA-only scope decision (it was written assuming
3 tickers; say plainly it narrowed to 1, and why). Also produce
`artifacts/slide_content.md` (arms table, chart reference, one sentence
on what was disproved, one sentence on what changed) per brief §9.

This synthesis step needs holistic judgment across everything Phases
0-4 produced — better done by the orchestrating agent directly than
split across subagents.
