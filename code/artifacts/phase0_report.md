# Phase 0 report: FNSPID corpus acquisition probe

**Status: STOP AND REPORT, per brief. Both files in the repo are now fully scanned. Timebox was 2 hours; this took roughly 8 hours wall-clock (mostly unattended background transfer, not active work, but still well past the nominal timebox). Waiting for confirmation before Phase 1.**

## 1. Source chosen

`Zihan1004/FNSPID` on Hugging Face Hub (dataset repo). Verified canonical: author matches the paper (Zihan Dong), and the repo's `arxiv:2402.06698` tag matches the brief's own citation exactly. 41 other repos on HF matched a search for "FNSPID" — all forks/derivatives, all far behind on downloads (6,487 vs. next-highest 588) and likes (121 vs. next-highest 9).

License: **CC BY-NC-4.0** — non-commercial only. Fine for this FYP; would block any future commercial framing without contacting the authors.

Repo contains 4 files (listed via HF Hub API, no download needed for this step):

| File | Size |
|---|---|
| `Stock_news/nasdaq_exteral_data.csv` | 23.23 GB |
| `Stock_news/All_external.csv` | 5.73 GB |
| `Stock_price/full_history.zip` | 589.5 MB |
| `README.md` | 2 KB |

Both CSVs carry `Date`, `Article_title`, `Stock_symbol` — the minimum required columns. `All_external.csv` is the smaller file that meets the minimum, so it was processed first, per the brief's instruction to identify "the smallest file that contains, at minimum" those columns. Given that file's coverage gap (§4), `nasdaq_exteral_data.csv` was scanned too.

## 2. Size pulled

**Both files were streamed and filtered in full.**

- `All_external.csv`: 13,057,514 rows scanned, all 5,731,397,037 bytes accounted for (byte count matches upstream `content-length` exactly). 5,494 rows matched AAPL/NVDA/TSLA.
- `nasdaq_exteral_data.csv`: scanned in two legs. First attempt crashed at 73% on a pandas internal bug (see §6); resumed from an estimated byte offset rather than restarting, with a 642-row dedup pass afterward to clean the resume boundary. Final: **31,145 rows** matched AAPL/NVDA/TSLA across the full 23.23GB file.

Neither run ever held more than a small buffer in memory — matched rows were checkpointed to disk incrementally in both cases, which is what made the crash-and-resume on the second file cheap rather than a full restart.

## 3. Timestamp granularity — the single most important fact, confirmed by full scan of both files

| File | Ticker | Rows | Fraction at exactly 00:00:00 UTC |
|---|---|---|---|
| All_external.csv | AAPL | 473 | 97.9% |
| All_external.csv | NVDA | 3,146 | 99.7% |
| All_external.csv | TSLA | 1,875 | 99.5% |
| nasdaq_exteral_data.csv | AAPL | 9,142 | **99.66%** |
| nasdaq_exteral_data.csv | NVDA | 11,709 | **99.78%** |
| nasdaq_exteral_data.csv | TSLA | 10,294 | **99.76%** |

In absolute terms, across all of 2018–2023, the number of rows with a *genuine* intraday timestamp in the larger, better-covered file: **AAPL 31, NVDA 26, TSLA 25.** Total, all three tickers, six years: **82 rows.**

Two files, independently sourced (one Benzinga-only by publisher names, one broader Nasdaq.com-derived source with full article bodies), same pathology for the same 3 tickers. This isn't a quirk of one file or one ticker — it's a property of the corpus.

**Consequence for the spike:** the brief's 16:00 ET session-cutoff rule, and the `E_SAMEBAR_TEXT` leak arm that depends on knowing whether a headline landed before or after the close, need real time-of-day to mean anything. With 82 usable rows spread across 3 tickers and 6 years, there is not enough real signal to run that arm against the committed universe as designed. This is exactly the kind of quiet, structural risk this spike exists to catch — it just showed up one layer earlier than expected, in the corpus itself rather than in the pipeline built on top of it.

## 4. Per-ticker coverage — full scan of both files

**All_external.csv:**

| Ticker | Date range | Rows |
|---|---|---|
| AAPL | 2020-03-09 → 2020-06-10 | 473 |
| NVDA | 2011-03-03 → 2020-06-10 | 3,146 |
| TSLA | 2019-07-01 → 2020-06-10 | 1,875 |

All three stop dead in June 2020. Doesn't reach 2018-2023 beyond a mid-2020 slice for any ticker.

**nasdaq_exteral_data.csv** (much better, but not clean):

| Ticker | Years present | Rows | Gap |
|---|---|---|---|
| AAPL | 2020, 2022, 2023 | 9,142 | **No 2018, 2019, or 2021 at all** |
| NVDA | 2011–2023, continuous | 11,709 | None — full coverage |
| TSLA | 2019, 2020, 2022, 2023 | 10,294 | **No 2018 or 2021 at all** |

NVDA is genuinely continuous across the target window. AAPL and TSLA both have an unexplained hole — no 2021 coverage whatsoever, and AAPL additionally has nothing in 2018–2019. Not investigated further (could be a real crawl gap in the source, or something about how this file was assembled) — flagging it as-is rather than guessing.

## 5. What this changes

Two separate problems:

1. **Granularity** (the bigger one): confirmed by full scan of both files, not just samples. 82 usable rows across 3 tickers × 6 years is not enough to test the same-bar leak arm as the brief specifies it.
2. **Coverage**: `nasdaq_exteral_data.csv` is much better than `All_external.csv`, but AAPL and TSLA both have real gaps (missing 2021 entirely; AAPL also missing 2018-2019). NVDA alone is clean.

The honest read: **the corpus does not support the same-bar-vs-next-bar leak arm across the full 3-ticker, 2018-2023 universe as committed.** This is the disproving-result kind of finding the brief says is worth more than a clean confirmation — but it means a real scope decision before Phase 1, not a data-engineering workaround.

Options worth considering (not a recommendation, just what the data supports):
- Narrow the same-bar arm to NVDA only, where coverage is genuinely continuous — though the 26-row real-timestamp count is still very thin for a leak-detection test needing statistical power.
- Redefine what "same-bar" means using only the ~0.2-0.3% of rows with real timestamps as the whole population for that specific arm, clearly labeled as a small-sample illustration rather than a corpus-wide result.
- Treat this as the disproved-assumption finding for the proposal defence itself: the risky assumption was "text can be aligned to price bars with no look-ahead, and leakage is detectable" — Phase 0 didn't get to test detection at all, because the precondition (real timestamps) mostly doesn't hold in the chosen corpus. That's a legitimate, defensible finding on its own for Friday.

## 6. Process notes (why this took ~8 hours, not 2)

- HF's backing storage for this dataset throttled to ~1–2.4 MB/s regardless of method: single connection, 8-way parallel range requests (worse than single — 0.9 MB/s aggregate, likely per-client throttling), and `pandas.read_csv(url, ...)` via its own urllib-based streaming (which stalled almost completely for reasons not fully diagnosed — abandoned rather than debugged further under time pressure).
- `All_external.csv`'s first working attempt crashed at 75% (~37 min in) on a CSV parsing bug: manually splitting the byte buffer on the last newline occasionally cut a quoted multi-line field in half. Fixed by routing the network stream through a file-like adapter directly into pandas' own C tokenizer (verified against a synthetic adversarial test before the real rerun).
- `nasdaq_exteral_data.csv`'s first attempt crashed at 73% (~130 min in) on a *different* bug: a pandas-internal `IndexError` in `_concatenate_chunks`, triggered by combining `usecols` with chunked `low_memory` dtype-consistency checks. Fixed with `dtype=str` + `low_memory=False`. Recovered via a resumed run from an estimated byte offset (1GB safety margin) rather than a full ~3hr restart — resume took ~50 min instead.
- Both crashes were survivable without losing completed work because matched rows were checkpointed to disk per-chunk from the start, not held in memory until a final write.

## 7. Scope decision (recorded 2026-09-10)

**Decision: proceed NVDA-only**, not AAPL/NVDA/TSLA, for the corpus-dependent work (sentiment features, session alignment, the `E_SAMEBAR_TEXT` arm).

**Why:** of the coverage gaps in §4, only NVDA is continuous across 2018-2023 in `nasdaq_exteral_data.csv`. AAPL and TSLA both have a real hole — zero 2021 rows for either, AAPL additionally missing 2018-2019.

**What this does and doesn't fix:** this is a coverage decision, not a granularity one. NVDA actually has the *worst* midnight-only fraction of the three tickers (99.78% vs AAPL's 99.66%), so the underlying granularity problem from §3 is unchanged — `E_SAMEBAR_TEXT` still runs on roughly 26 genuinely-timestamped NVDA rows across all six years. Explicitly confirmed with the user (2026-09-10) to proceed anyway, on the basis that the arm's result will be reported honestly as a small-N illustration rather than a corpus-wide claim.

**What it changes going forward:** Phase 1's ticker universe narrows from the brief's stated AAPL/NVDA/TSLA to NVDA only. `config/spike.yaml` (Phase 1) should reflect this. The proposal's contribution claims (leakage-audited harness, deterministic verifier) are unaffected — only the demonstration universe shrinks.

## What Phase 0 did not do

- Evaluate non-FNSPID alternatives (GDELT, live yfinance/RSS headlines), per the brief's instructions for an unworkable source. Not started — FNSPID isn't unworkable in the "can't obtain it" sense (both files were fully retrieved and analyzed), the problem is specifically that its timestamps don't carry what the same-bar arm needs. Worth doing if the scope decision above lands on "need a better-timestamped source" rather than "adapt the arm to what we have."
