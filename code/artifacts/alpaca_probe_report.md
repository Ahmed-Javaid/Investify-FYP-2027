# Alpaca Markets News API probe: does it make E_SAMEBAR_TEXT measurable?

**Status: complete. Recommendation below. Full numbers back up the corpus_manifest.json entry.**

## 0. Why this probe ran

Phase 0 (`artifacts/phase0_report.md` Sec.3/7) found FNSPID's NVDA rows are
99.78% midnight-defaulted: only 26 of 11,708 headlines carry a genuine time
of day, and of those 26, exactly one maps to a different session under the
same-bar-vs-next-session rule (`phase2_report.md` Sec.3) -- and that one case
turned out to be a timestamp-default artifact, not a real after-close item.
The honest finding stood as "this corpus cannot answer the question," not
"the leak is small." This probe tests whether the Alpaca Markets News API
(Benzinga wire) gives real second-resolution timestamps for NVDA 2018-2023,
and if so, pulls it.

## 1. Step 1 -- timestamp granularity probe (small samples, 2018/2020/2023)

Requested `limit=50` for NVDA over a ~3-month window in each year:

| Window | Articles returned | Fraction non-midnight time-of-day | Example `created_at` |
|---|---|---|---|
| 2018-01-01 to 2018-03-31 | 50 | **1.000** (50/50) | `2018-03-28T18:48:16Z` |
| 2020-01-01 to 2020-03-31 | 50 | **1.000** (50/50) | `2020-03-27T15:09:19Z` |
| 2023-01-01 to 2023-03-31 | 50 | **1.000** (50/50) | `2023-03-30T21:14:04Z` |

Every single sampled row across all three windows carries a genuine
second-resolution timestamp. Not midnight-defaulted like FNSPID. Cleared to
proceed.

## 2. Step 2 -- earliest available date probe

Per-year earliest-article probe (`sort=asc, limit=1`) from 2010 through 2018:

| Year queried | Earliest article found |
|---|---|
| 2010 | none |
| 2012 | none |
| 2014 | none |
| 2015 | **2015-01-05T20:14:29Z** |
| 2016 | 2015-12-17T15:44:51Z |
| 2017 | 2017-01-02T15:13:33Z |
| 2018 | 2018-01-02T09:15:41Z |

True earliest NVDA article available to this account: **2015-01-05**. No
free-tier history restriction encountered before 2015 -- well ahead of the
2018 start of the target window. The full 2018-2023 pull is unconstrained by
subscription tier.

## 3. The pull

`scripts/pull_alpaca_nvda_news.py` paginated `symbols=NVDA`,
`start=2018-01-01T00:00:00Z`, `end=2023-12-31T23:59:59Z`, `limit=50`,
`sort=asc`, `include_content=false` (headline-only; `exclude_contentless` was
**not** set, per instructions). Checkpointed to
`data/raw/.alpaca_pull_checkpoint.json` after every page (rows already
written are never re-fetched on resume). Rate-limited to ~171 req/min
(comfortably under the free tier's 200/min) by sleeping between requests.

**Result: 6,769 rows in 136 pages, 49 seconds wall clock.** Far under the
30-minute timebox -- the query is narrow enough (single ticker, symbol-tagged
articles only) that no extended run or partial-progress report was needed.

- 0 duplicate `id`s.
- True date range: `2017-07-31T21:10:51Z` to `2023-12-30T09:16:38Z`.
- One row (id `9851408`, 2017-07-31, "NVIDIA Shares Down 1% After Hours...")
  fell outside the requested `start=2018-01-01` boundary, and was **not**
  chronologically first in the asc-sorted pagination sequence -- it appeared
  mid-stream at row 2,313 of 6,769. This looks like a minor API/pagination
  boundary quirk (possibly the `start` filter and the pagination ordering key
  disagree at the margin). Not investigated further: it is 1 row out of
  6,769 (0.015%), and it was **kept in the output file** rather than quietly
  dropped, consistent with "never hide a result." 6,768 of 6,769 rows fall
  within the committed 2018-2023 window.

### Rows per year (NY-local)

| Year | Rows |
|---|---|
| 2017 | 1 (the stray row above) |
| 2018 | 493 |
| 2019 | 375 |
| 2020 | 515 |
| 2021 | 1,035 |
| 2022 | 1,632 |
| 2023 | 2,718 |
| **Total** | **6,769** |

Volume rises sharply toward 2023 -- consistent with NVDA's growing news
coverage, not an artifact of the pull (pagination was uniform `limit=50`
throughout).

## 4. The numbers that decide whether this replaces FNSPID for E_SAMEBAR_TEXT

**Fraction of rows with a genuine (non-midnight UTC) time of day: 6,769 / 6,769 = 100%.**
Contrast: FNSPID NVDA was 26 / 11,708 = 0.22%.

**Rows with NY-local time at or after 16:00 (what the cutoff rule acts on): 810 (11.97%).**

**Rows on a non-trading day (weekend or NYSE holiday): 232** -- 210 weekend, 22 weekday holidays.

**Rows where the same-bar rule maps to a DIFFERENT session than the correct
next-session rule: 749 of 6,769 (11.07%) overall; 748 within the committed
2018-2023 window.** Computed with `investify.calendars.NYSECalendar` and
`investify.ingest.news.map_to_sessions` / `map_to_sessions_samebar`, imported
read-only -- neither module was modified.

Contrast: FNSPID's usable population for this arm was 26 rows total, with
exactly 1 differing -- and that 1 was diagnosed as a timestamp-default
artifact rather than a genuine after-close case (`phase2_report.md` Sec.3).
Alpaca gives **~750 genuinely differing rows**, driven by real after-close
publication times and weekend/holiday items -- a population large enough to
measure a leak's magnitude, not just gesture at whether one could exist in
principle.

### SHA-256 / provenance (also recorded in `artifacts/corpus_manifest.json` -> `alpaca_news_supplemental_source`)

- File: `data/raw/alpaca_nvda_news.csv` (gitignored, reproducible via the script)
- SHA-256: `7c72ad6d621bcb7a6680eed69fcd13db0d240afd3189eeb583734d3d52b2feb7`
- Row count: 6,769
- Retrieval timestamp: 2026-09-10T14:26:00-05:00

## 5. Shape vs. `load_ticker_news`

`src/investify/ingest/news.py::load_ticker_news` (not modified) takes FNSPID's
**raw** columns (`Date`, `Article_title`, `Stock_symbol`, `Publisher`),
filters to one ticker, parses `Date` with the FNSPID-specific format string
`"%Y-%m-%d %H:%M:%S UTC"`, and renames to `ticker`, `headline`, `event_ts`,
`publisher` -- that renamed shape is its **output**.

`data/raw/alpaca_nvda_news.csv` is written columns:
`id, ticker, headline, event_ts, publisher, author, url, n_symbols_tagged`.

This already matches `load_ticker_news`'s **output** column names
(`ticker`, `headline`, `event_ts`, `publisher`) plus extra provenance columns
(`id`, `url`, `author`, `n_symbols_tagged`). It does **not** match
`load_ticker_news`'s expected **input** shape -- `load_ticker_news` cannot be
pointed at this file directly, because it looks for `Date`/`Article_title`/
`Stock_symbol` and applies FNSPID's specific datetime format string, neither
of which this file has. `event_ts` here is ISO8601 with a `Z` suffix (e.g.
`2020-01-09T20:15:55Z`), which `pd.to_datetime(..., utc=True)` parses
directly with no format string needed -- if anything this is a simpler load
than FNSPID's, but it is a different (smaller) loader than the one that
exists today. Building that loader is out of this script's scope (`news.py`
was intentionally left untouched).

One data caveat worth flagging for whoever writes that loader: Alpaca's
`source` field (mapped here to `publisher`) was empty string for every row
sampled -- the whole feed is the Benzinga wire, so this column carries no
discriminating signal, similar to FNSPID's own frequently-empty `Publisher`
column. `author` (the Benzinga writer/analyst, e.g. "Lisa Levin", or
"Benzinga" for wire-desk items) is populated and was kept.

One further quality caveat for the eventual sentiment-scoring step: several
sampled Alpaca articles (e.g. "Stocks That Hit 52-Week Highs On Thursday")
tag NVDA alongside 200+ other symbols in a single market-roundup piece --
this is expected behavior for `symbols=NVDA` filtering on a wire feed, not a
bug, but it means "headline mentions NVDA's ticker" is a broader net than
"headline is about NVDA," which the FNSPID extract (Nasdaq.com-sourced,
per-company pages) did not have to contend with in the same way.

## 6. Recommendation

**Yes -- this corpus makes `E_SAMEBAR_TEXT` measurable.** 100% real
timestamps (vs. FNSPID's 0.22%), and ~750 rows (11% of the corpus) map to a
different trading session under the same-bar rule than under the correct
next-session rule -- enough rows, spanning weekends, holidays, and real
after-close publication times, to measure a leak's magnitude rather than
merely note that the corpus can't answer the question.

This is a recommendation, not a decision -- per `CLAUDE.md`'s change-control
section, swapping (or supplementing) the corpus for this arm is a scope
change that should be recorded with what changed and why once made, and it
affects only the news-timestamp side of the pipeline; NVDA-only scope, the
16:00 ET cutoff rule, and price/label construction from Phase 1 are
unaffected either way.
