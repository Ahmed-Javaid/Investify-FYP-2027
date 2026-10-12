# Current Investify status

Updated 12 October 2026 after workspace consolidation and folder cleanup. **The active project is `E:\Uni_Stuff\FYP\Investify`.** Use [the document guide](../deliverables/README.md) to choose current drafts and reference versions.

## Implemented and recorded

The integrated code contains the historical-record demo, deterministic explanation/verifier and fallback, evidence coverage, prototype risk profile and separate comparator, leakage/scientific-recovery tooling, and receipt-bound social/teacher workflows.

The latest full engineering snapshot records **212 selected passes including 20 Streamlit cases**, **153 scoped core passes with 3 deselected cases**, and separate JavaScript/backend fixtures. Integration verification records **165 portable passes** and **372 validated historical records**. These scopes overlap and do not establish market performance or scientific reproduction.

Six actual assistant-teacher explanations replay into four training/two validation examples. The social pilot retains 200 source posts and 117 usable model-generated references. Candidate inference, student inference and QLoRA have not run. The assistant is teacher, Phi-3-mini is the planned student, and Mistral is fallback. Use original publisher models; preserve the frozen references and withdrawn-result boundaries.

## Verification after folder cleanup

This continuation reran **165 portable tests with zero skips/failures**, validated all **372 saved records**, replayed all **six teacher examples** and the **200-post/117-reference social pilot**, and passed **62 HTTP checks** against the canonical live demo at `http://127.0.0.1:8768`. All 877 moved files, 224 protected originals and 199 integration code files retain their hashes. [The dated summary](../evidence/folder_cleanup_continuation_summary_20261012.json) links this scope to the retained receipts.

The local `.env` pair is detected and remains Git-ignored. [The new acquisition receipt](../evidence/market_reacquisition_20261012/with_local_env_v1/probe.json) records **WinError 10061 before HTTP for Yahoo, FNSPID and Alpaca**; credentials are no longer the missing prerequisite. No data was received. [The fresh dependency audit](../evidence/folder_cleanup_dependency_audit_20261012.json) still finds missing scientific inputs/packages, original candidate weights and LaTeX compilers.

## Current documents and remaining work

**Original-repository source review:** the original README and Phase 0/1/PoC reports distinguish FNSPID coverage from timestamp granularity. The smaller `All_external.csv` stops in June 2020. The larger file lacks AAPL 2018/2019/2021 and TSLA 2018/2021; NVDA has every year in 2018–2023 but daily coverage is sparse. The historical feature run had 303/1,509 price bars without attached sentiment. Only 26/11,708 usable NVDA headlines had a real time of day (about 99.78% midnight-defaulted). Alpaca/Benzinga was added for the timing experiment, not because FNSPID was inaccessible. FNSPID recovery therefore restores the original NVDA baseline only; it does not close the precise-timestamp study. [The review receipt](../evidence/fnspid_source_review_20261012.json) records original file hashes and source anchors. The new acquisition helper is tested on labelled fixtures/plan-only mode; no actual CSV download has yet occurred in this session.

**Later host-terminal check:** [the user's normal-terminal receipt](../evidence/market_reacquisition_20261012/normal_terminal_20261012T140203797Z/probe.json) has no configured proxy and reaches all three providers: FNSPID metadata 200, Yahoo 429, Alpaca news 401. This establishes provider connectivity in that terminal; the agent session remains restricted. The FNSPID revision/file metadata is retained, not the full corpus. The user confirms the keys came from the paper account's API Keys tab. Use `tools/check_alpaca_auth.ps1` in the normal terminal to compare paper-account and news access with the same pair; both key validity and news access remain unresolved until that check. A 401 alone does not identify the fault. The diagnostic now preserves a redacted provider error body and request ID; audit the request and compare an independent client before changing credentials. For Yahoo 429, delay retries and retain/cache successful fresh price snapshots.

- Report: [../report/main.tex](../report/main.tex), editable institutional draft, not yet compiled or reviewed.
- Slides: [../deliverables/presentation_outline.json](../deliverables/presentation_outline.json), current content and notes, no exported mid PPTX.
- Requirements and demo: [document guide](../deliverables/README.md), current working write-ups.
- Official requirements and proposal: [../sources](../sources/), preserved reference originals.

The last recorded readiness judgement is approximately **72%**, not the requested 90%. The [unchanged readiness ledger](MID_EVAL_READINESS.md) explains the missing actual scientific run, sentiment comparison, institutional report/deck and student/supervisor evidence. Folder organization does not change that estimate.

## Resume work

1. Read `code/.env` locally for the declared Alpaca key pair through the acquisition tool; inherited environment values take precedence. Record new acquisition attempts separately from historical data.
   The recommended connectivity check is `tools/check_market_access.ps1` in your normal PowerShell terminal. It uses the same provider requests and key handling, preserves network settings and saves a new dated result. If that terminal also fails, diagnose its expected proxy/VPN configuration and provider reachability; if Alpaca returns HTTP, use that response to investigate authentication/access separately.
2. Restore genuine market/store/FinBERT inputs and the supported science runtime; run the existing recovery doctor before executing the pipeline.
3. Restore original publisher candidate snapshots and complete the receipt-bound social comparison.
4. Compile and inspect the institutional report, export/check the slides, and obtain genuine team review/contribution/rehearsal evidence.

The latest probe result and this continuation's checks are recorded in [BACKGROUND_PROGRESS.md](BACKGROUND_PROGRESS.md) and dated files under `evidence`. Network failures do not authorize routing/security changes or fabricated inputs.

## Workspace ownership and history

The preceding continuation task was observed `notLoaded`, with its latest turn interrupted; this session owns the current continuation. Earlier native task/parallel-worker descriptions are historical. Do not restart those tasks as writers.

Old workspaces and loose material are under the parent `_archives` folder. All 877 relocated files passed before/after hash checks. The protected-original manifest remains unchanged; the checker uses the explicit relocation receipt. Current model/data freezes and existing review ZIPs retain their paths.

The superseded large README/handoff/next-chat instructions are preserved in [history/before_folder_cleanup_20261012](history/before_folder_cleanup_20261012/). Detailed logs below their new top notices describe earlier snapshots.
