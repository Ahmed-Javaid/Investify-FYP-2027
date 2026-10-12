# Current Investify status

## Fresh scientific execution - 12 October 2026

The new **Alpaca revision-conservative experiment has completed and passed actual
model/calibration/native-TreeSHAP replay**. It consumed 1,509 complete NYSE price
sessions and 6,768 news rows, with 5,748 distinct headlines scored offline by the
pinned original ProsusAI/finbert checkpoint. The recovery doctor had zero blockers
and all three scientific commands completed.

Six arms at both horizons ran on shared row sets: 1,309 rows at one day and
1,305 at five days, six folds each. Clean five-day macro-F1 is **0.2843** against
the training-distribution random baseline **0.3287** (lift -0.0444).
The deliberately centred Bollinger canary has five-day lift **+0.2104**,
95% fold-bootstrap CI **[+0.1698, +0.2421]**. E_SAMEBAR_TEXT remains a lag ablation.

Both current calibration modes still emit **186 Buy decisions**. Raw frozen-mode
predictions are Buy 40 / Hold 51 / Sell 95; learned isotonic maps make Buy highest
on every evaluation row. Frozen Brier improves **0.7929 to 0.6105**; refit-transfer
improves **0.7760 to 0.6078**. Better Brier does not resolve decision collapse or
establish useful prediction. Five unavailable calibration labels were excluded;
181 rows calibrate, and evaluation runs 29 March to 21 December 2023.

Actual retained-model inference reproduces margins/probabilities exactly; native
TreeSHAP agrees with every exported contribution/bias, with maximum frozen
additivity residual about 1.02e-6. All 372 **new** guided explanations validate,
separately from the 372 preserved historical records. New engineering checks:
179 passed / six legacy-input skips, plus eight admission-refusal passes.

This is a fresh SIP split-adjusted snapshot using max(created_at, updated_at)
for news availability, not the original September data or exact uv.lock.
Historical vintage is not proven; all original records, freezes and ZIPs remain
separate. No FNSPID was requested.

[Reviewed summary](../evidence/fresh_alpaca_science_summary_20261012_run01.json) and [actual replay](../evidence/fresh_alpaca_science_replay_20261012_run01.json).

Readiness is now **78.5%, approximately 79%**, with unchanged weights and other
areas: science alone rises from 60% to 85%. Remaining substantive gaps are the
social comparison, rendered institutional report/deck, and genuine team review,
contribution/rehearsal and repository evidence. The 90% target is not achieved.

Updated 12 October 2026 after workspace consolidation and folder cleanup. **The active project is `E:\Uni_Stuff\FYP\Investify`.** Use [the document guide](../deliverables/README.md) to choose current drafts and reference versions.

## Alpaca access restored - 12 October, 15:30 UTC

After the user replaced the local key pair, both paper-account and market-news
requests returned **200 OK**. [Authentication receipt](../evidence/market_reacquisition_20261012/paper_auth_20261012T152909983Z/probe.json).
Approved outside-sandbox requests work; default sandbox networking remains
restricted. Credentials and account response bodies were not saved.

A fresh, bounded historical sample retrieved **30 NVDA articles**, five from
each year 2018-2023, with 200 responses for all six requests. All 30 have
non-midnight, timezone-aware `created_at` values and satisfy ticker/year/headline
checks. [Historical sample receipt](../evidence/market_reacquisition_20261012/historical_news_sample_20261012T153005905951Z/probe.json).
Every year has further pages; this is not a complete corpus or scientific run.
Fourteen sampled records were updated after creation, so retain `updated_at`
and assess revised-text availability before claiming point-in-time-safe inputs.
No original/frozen input was replaced. **No FNSPID request or download occurred.**

Next: acquire paginated Alpaca news under a fresh snapshot identity, retaining
created/updated timestamps and raw provenance; validate coverage, duplicates and
revision timing before scientific ingestion. The legacy pull script uses a fixed
historical output path and drops `updated_at`, so it must not be run unchanged
against the frozen research inputs. Run the recovery doctor before the pipeline.
Earlier 401 diagnoses below concern the replaced pair and are now historical.

## Implemented and recorded

The integrated code contains the historical-record demo, deterministic explanation/verifier and fallback, evidence coverage, prototype risk profile and separate comparator, leakage/scientific-recovery tooling, and receipt-bound social/teacher workflows.

The latest full engineering snapshot records **212 selected passes including 20 Streamlit cases**, **153 scoped core passes with 3 deselected cases**, and separate JavaScript/backend fixtures. Integration verification records **165 portable passes** and **372 validated historical records**. These scopes overlap and do not establish market performance or scientific reproduction.

Six actual assistant-teacher explanations replay into four training/two validation examples. The social pilot retains 200 source posts and 117 usable model-generated references. Candidate inference, student inference and QLoRA have not run. The assistant is teacher, Phi-3-mini is the planned student, and Mistral is fallback. Use original publisher models; preserve the frozen references and withdrawn-result boundaries.

## Verification after folder cleanup

This continuation reran **165 portable tests with zero skips/failures**, validated all **372 saved records**, replayed all **six teacher examples** and the **200-post/117-reference social pilot**, and passed **62 HTTP checks** against the canonical live demo at `http://127.0.0.1:8768`. All 877 moved files, 224 protected originals and 199 integration code files retain their hashes. [The dated summary](../evidence/folder_cleanup_continuation_summary_20261012.json) links this scope to the retained receipts.

The local `.env` pair is detected and remains Git-ignored. [The new acquisition receipt](../evidence/market_reacquisition_20261012/with_local_env_v1/probe.json) records **WinError 10061 before HTTP for Yahoo, FNSPID and Alpaca**; credentials are no longer the missing prerequisite. No data was received. [The fresh dependency audit](../evidence/folder_cleanup_dependency_audit_20261012.json) still finds missing scientific inputs/packages, original candidate weights and LaTeX compilers.

## Earlier Alpaca diagnosis - 12 October, 15:19 UTC

The fresh sandbox network check still failed before HTTP with WinError 10061.
Explicitly approved execution outside the sandbox reached both Alpaca hosts:
[urllib receipt](../evidence/market_reacquisition_20261012/paper_auth_20261012T151704775Z/probe.json)
and [independent requests receipt](../evidence/market_reacquisition_20261012/independent_auth_20261012T151921041173Z/probe.json).
Both clients returned paper-account **401 / `unauthorized.`** and news **401 /
nginx `401 Authorization Required` HTML**. Neither supplied a more specific
provider code. Request IDs are retained; successful account bodies and all
credential values are absent from the receipts.

Two local parsers agreed on the values. Both credentials have one declaration,
ASCII content, no whitespace or literal quotes, and the independently prepared
request contains the matching documented APCA headers with no extra Authorization
header. This reduces the likelihood of parsing/client errors but does not prove
the pair is valid. Generic rejection does not identify a news subscription fault
or distinguish invalid/revoked/mismatched credentials from an account-side issue.
The hosts and header names match
[Alpaca's documentation](https://docs.alpaca.markets/us/docs/authentication).

Recommended next step: locally compare `code/.env` with the current matching
paper-account key pair. If correct, ask Alpaca support to trace the request IDs
in the receipts; account credentials need not be shared in chat. Account resets
can require regenerated credentials according to
[Alpaca's FAQ](https://docs.alpaca.markets/us/docs/market-data-faq).
After correction/provider resolution, rerun `tools/check_alpaca_auth.ps1` in a
network-enabled terminal. No account/key settings were changed here.

**The user explicitly prohibits downloading FNSPID.** This continuation made
zero FNSPID requests and downloaded no corpus. No scientific/readiness claim
changes. Earlier status-only/proxy-only descriptions below are historical and
superseded by these actual responses.

## Current documents and remaining work

**Original-repository source review:** the original README and Phase 0/1/PoC reports distinguish FNSPID coverage from timestamp granularity. The smaller `All_external.csv` stops in June 2020. The larger file lacks AAPL 2018/2019/2021 and TSLA 2018/2021; NVDA has every year in 2018–2023 but daily coverage is sparse. The historical feature run had 303/1,509 price bars without attached sentiment. Only 26/11,708 usable NVDA headlines had a real time of day (about 99.78% midnight-defaulted). Alpaca/Benzinga was added for the timing experiment, not because FNSPID was inaccessible. FNSPID recovery therefore restores the original NVDA baseline only; it does not close the precise-timestamp study. [The review receipt](../evidence/fnspid_source_review_20261012.json) records original file hashes and source anchors. The new acquisition helper is tested on labelled fixtures/plan-only mode; no actual CSV download has yet occurred in this session.

**Later host-terminal check:** [the user's normal-terminal receipt](../evidence/market_reacquisition_20261012/normal_terminal_20261012T140203797Z/probe.json) has no configured proxy and reaches all three providers: FNSPID metadata 200, Yahoo 429, Alpaca news 401. This establishes provider connectivity in that terminal; the agent session remains restricted. The FNSPID revision/file metadata is retained, not the full corpus. The user confirms the keys came from the paper account's API Keys tab. Use `tools/check_alpaca_auth.ps1` in the normal terminal to compare paper-account and news access with the same pair; both key validity and news access remain unresolved until that check. A 401 alone does not identify the fault. The diagnostic now preserves a redacted provider error body and request ID; audit the request and compare an independent client before changing credentials. For Yahoo 429, delay retries and retain/cache successful fresh price snapshots.

- Report: [../report/main.tex](../report/main.tex), editable institutional draft, not yet compiled or reviewed.
- Slides: [../deliverables/presentation_outline.json](../deliverables/presentation_outline.json), current content and notes, no exported mid PPTX.
- Requirements and demo: [document guide](../deliverables/README.md), current working write-ups.
- Official requirements and proposal: [../sources](../sources/), preserved reference originals.

The last recorded readiness judgement is approximately **72%**, not the requested 90%. The [unchanged readiness ledger](MID_EVAL_READINESS.md) explains the missing actual scientific run, sentiment comparison, institutional report/deck and student/supervisor evidence. Folder organization does not change that estimate.

## Resume work

1. Complete original-publisher social candidate metadata/weights and the frozen-reference paired comparison. The scientific Python 3.11 runtime now imports Torch/Transformers; candidate snapshots remain missing.
2. Review the completed fresh Alpaca experiment and its calibration collapse. Any new calibration/model comparison must use a new identity and development-only selection; do not tune thresholds on the retained evaluation fold. September bytes and the exact lock remain unreproduced.
3. Compile and inspect the updated institutional report, export/check the slide deck, and resolve required institutional facts.
4. Obtain genuine student review, contributions and demo rehearsal, plus current repository/CI evidence where applicable.

The fresh science summary links current execution and actual inference replay.
Do not download FNSPID or overwrite historical records, labels, teacher examples,
models, receipts or ZIPs. Earlier network/access sections above retain their
dated historical scope.

## Workspace ownership and history

The preceding continuation task was observed `notLoaded`, with its latest turn interrupted; this session owns the current continuation. Earlier native task/parallel-worker descriptions are historical. Do not restart those tasks as writers.

Old workspaces and loose material are under the parent `_archives` folder. All 877 relocated files passed before/after hash checks. The protected-original manifest remains unchanged; the checker uses the explicit relocation receipt. Current model/data freezes and existing review ZIPs retain their paths.

The superseded large README/handoff/next-chat instructions are preserved in [history/before_folder_cleanup_20261012](history/before_folder_cleanup_20261012/). Detailed logs below their new top notices describe earlier snapshots.
