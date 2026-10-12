# Investify

## Fresh scientific execution - 12 October 2026

The isolated scientific runtime is
E:\AI-Tools\Temp\investify-science-py311-20261012\Scripts\python.exe.
The completed experiment is under
artifacts/scientific_runs/alpaca_revision_conservative_20261012_run01.
Its fresh_config.yaml, recovery01/recovery_config.yaml, input store, six-arm
results, two sets of decision records/traces and logs are retained. Scores are
under E:\AI-Tools\Cache\finbert_scores\alpaca_revision_conservative_20261012_run01.
The existing default config and historical demo records remain separate.

To prepare another run, use scripts/prepare_fresh_alpaca_science.py --help.
Supply the three acquisition receipts, a **new** run directory, a **new** score
cache on E: and a **new** evidence receipt. It gates source bytes against pinned
publisher hashes and keeps model loading offline. Run the recovery doctor with
the new config before execution. Choose new result/receipt identities.

The independent completed-run checker is scripts/verify_fresh_science_run.py:

~~~powershell
& 'E:\AI-Tools\Temp\investify-science-py311-20261012\Scripts\python.exe' -B scripts/verify_fresh_science_run.py --run-directory artifacts/scientific_runs/alpaca_revision_conservative_20261012_run01/recovery01 --output ../evidence/fresh_science_replay_NEW.json
~~~

The new outcome is documented in ../planning/CURRENT_STATUS.md. The original
September source inputs and exact lock are not reproduced, and the all-Buy
calibration outcome still prevents a predictive-usefulness claim.

Current teacher increment: six actual assistant-written explanations pass the bounded verifier; four training/two validation examples are exported. Teacher Study replays their source/prompt/raw-output/persistence checks. Phi-3-mini remains the student family, with no student baseline inference or QLoRA yet. Qwen is not a required teacher download. Current selected suite: 212 passes, including 20 Streamlit cases. See ../deliverables/ASSISTANT_TEACHER_PILOT.md.

The intended product combines technical, news/social and risk-profile evidence into an educational Buy/Hold/Sell view with verified explanations. The current implementation uses historical, news-only NVDA records; all saved calibrated decisions are Buy. A separate prototype risk-dependent linear comparator is now available. No real explainer completion has been obtained; the separate sentiment pilot now has actual session-generated AI reference labels.

**Current mid-evaluation work:** [live demo and verification](docs/mideval_increment.md), [local LLM adapter/evaluation](docs/local_llm_pilot.md), and [risk profile/comparator](docs/risk_comparator.md). The selected suite has **212 passes with no skips**, including 20 actual Streamlit AppTest cases. All **372** numeric/complete-guided records, **62** live HTTP checks and **228** comparator arithmetic probes validate. Streamlit is running in an isolated viewer environment. Full scientific reproduction, browser visual QA, real generation evaluation and remote CI remain pending. The original documentation below describes the historical spike.

Two contributions carry the project, neither is the model itself:

1. A leakage-audited, point-in-time evaluation harness — text and price data align across incompatible calendars with no look-ahead, and the test suite is proven to detect leakage when it's deliberately introduced.
2. A deterministic verifier for generated explanations — every number, sign, ranking and feature name in an explanation is checked against the decision record that produced it.

The [social-selection tooling](docs/social_selection.md) now validates declared post/AI-or-human annotation provenance, freezes a chronological plan and exact candidate identities, and scores complete paired actual outputs. Its unit fixtures are separate from research evidence. The actual AI reference pilot contains 200 real MSFT tweets: 117 usable labels (31 positive, 67 neutral, 19 negative) and 83 explicit exclusions. Its frozen split is 93 development/24 held out, with only two negative held-out references. One session pass is recorded with full prompt/input/raw-output/timing and declared model-identity provenance; agreement/kappa are null and independent human validation is absent. Candidate inference remains blocked with null metrics.

FAST NUCES Islamabad, Software Engineering, Final Year Project F26-003-Investify (formerly F26-003-QuantamentalAI). Stream A — research-derived.

---

## Proposal-defence spike

The repository currently holds the completed proposal-stage proof of concept. **Read [`POC_REPORT.md`](POC_REPORT.md) first** — it answers the five questions the university guide requires and states plainly what the spike does and does not establish.

**What it found, in three lines:**

- The leakage detector works. A deliberately future-peeking feature is caught at +0.183 (FNSPID) and +0.219 (Alpaca) against a 0.03 threshold, and an oracle-feature positive control registers +0.664.
- The spike's central arm — mapping text to the session it published in rather than the next — produces **no detectable leak** on a corpus that can actually measure it. On FNSPID it could not be measured at all: 26 of 11,708 headlines carry a real time of day.
- The clean pipeline has **no predictive signal**, and sits below chance at the 5-day horizon. Reported, not tuned away.

Scope: NVDA only, 2018-2023, two news corpora, seed 42, one fixed model configuration. 119 tests.

## Running it

```bash
make setup       # pinned environment via uv
make features    # build both feature matrices (offline after the first price fetch)
make spike       # the leakage harness, both corpora -> artifacts/
make engine      # train, calibrate, attribute -> decision records
make test        # full suite, including the leak canary
make app         # the two-tab demo
```

`make data` re-pulls the news corpora and needs the network; the Alpaca pull also needs `ALPACA_API_KEY` and `ALPACA_API_SECRET` in a gitignored `.env`. Everything else runs offline from `data/store/` and `.cache/`. The demo opens in about a second from cached artefacts.

## Layout

| Path | What's in it |
| --- | --- |
| `src/investify/` | calendars, ingest, features, store, labels, scaling |
| `src/investify/harness/` | splits, metrics, the arms, the spike runner |
| `src/investify/explain/` | template, verifier, corrupted fixtures, the emit seam |
| `src/investify/engine.py` | fixed XGBoost, isotonic calibration, TreeSHAP |
| `src/investify/decision_record.py` | the frozen, self-validating schema everything downstream reads |
| `app/` | the two-tab Streamlit demo |
| `artifacts/` | **committed evidence** — results, hashes, figures, phase reports |
| `docs/` | proposal, pitch deck, university FYP guide, the spike brief |

`artifacts/` is evidence, not scratch. `data/raw/`, `data/store/` and `.cache/` are gitignored and reproducible.

See `CLAUDE.md` for active work, hard constraints and repo conventions.
