"""Pull NVDA news from the Alpaca Markets News API (Benzinga wire) for
2018-01-01 through 2023-12-31.

Why this exists: Phase 0 found the FNSPID corpus is 99.78% midnight-defaulted
for NVDA (26 genuine timestamps out of 11,708 rows) -- too thin to measure
the E_SAMEBAR_TEXT leak arm (see artifacts/phase0_report.md Sec.3/7). A probe
of the Alpaca News API (artifacts/alpaca_probe_report.md Sec.1) confirmed
100% of returned NVDA rows across sampled 2018/2020/2023 windows carry a
genuine second-resolution created_at. This script pulls the full window.

Usage:
    uv run python scripts/pull_alpaca_nvda_news.py

Credentials are read from .env (ALPACA_API_KEY, ALPACA_API_SECRET) via a
minimal hand-rolled parser -- no python-dotenv dependency added. Keys are
never printed, logged, or written anywhere.

Checkpointing: progress (next_page_token, rows written so far) is saved to
data/raw/.alpaca_pull_checkpoint.json after every page so a crash or a
Ctrl-C does not lose completed work -- re-running this script resumes from
the checkpoint rather than restarting. Rows are appended to the output CSV
incrementally, not buffered until the end.

Rate limit: Alpaca's free tier allows 200 req/min. We sleep at least 0.35s
between requests (< 172 req/min), comfortably under the limit, rather than
retrying after a 429.

Fail-loud: any non-200 response raises immediately with the status code and
response body. No silent excepts.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".env"
OUT_CSV = REPO_ROOT / "data" / "raw" / "alpaca_nvda_news.csv"
CHECKPOINT_PATH = REPO_ROOT / "data" / "raw" / ".alpaca_pull_checkpoint.json"

NEWS_URL = "https://data.alpaca.markets/v1beta1/news"
TICKER = "NVDA"
START = "2018-01-01T00:00:00Z"
END = "2023-12-31T23:59:59Z"
PAGE_LIMIT = 50
MIN_REQUEST_INTERVAL_SEC = 0.35  # ~171 req/min, under the 200 req/min free-tier cap

CSV_COLUMNS = [
    "id",
    "ticker",
    "headline",
    "event_ts",
    "publisher",
    "author",
    "url",
    "n_symbols_tagged",
]


def load_env(path: Path) -> dict[str, str]:
    if not path.exists():
        raise RuntimeError(f".env not found at {path}")
    env: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    for required in ("ALPACA_API_KEY", "ALPACA_API_SECRET"):
        if required not in env or not env[required]:
            raise RuntimeError(f"{required} missing or empty in {path}")
    return env


def make_headers(env: dict[str, str]) -> dict[str, str]:
    return {
        "APCA-API-KEY-ID": env["ALPACA_API_KEY"],
        "APCA-API-SECRET-KEY": env["ALPACA_API_SECRET"],
    }


def fetch_page(client: httpx.Client, headers: dict[str, str], page_token: str | None) -> dict:
    params = {
        "symbols": TICKER,
        "start": START,
        "end": END,
        "limit": PAGE_LIMIT,
        "sort": "asc",
        "include_content": "false",
        # exclude_contentless intentionally NOT set -- headline-only items are wanted.
    }
    if page_token:
        params["page_token"] = page_token
    r = client.get(NEWS_URL, headers=headers, params=params, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(
            f"Alpaca News API returned HTTP {r.status_code} for page_token={page_token!r}: {r.text}"
        )
    return r.json()


def load_checkpoint() -> dict:
    if CHECKPOINT_PATH.exists():
        return json.loads(CHECKPOINT_PATH.read_text())
    return {"next_page_token": None, "rows_written": 0, "done": False, "seen_ids": []}


def save_checkpoint(state: dict) -> None:
    CHECKPOINT_PATH.write_text(json.dumps(state))


def article_to_row(article: dict) -> dict:
    return {
        "id": article["id"],
        "ticker": TICKER,
        "headline": article["headline"],
        "event_ts": article["created_at"],  # preserved verbatim, full precision + tz
        "publisher": article.get("source", ""),
        "author": article.get("author", ""),
        "url": article.get("url", ""),
        "n_symbols_tagged": len(article.get("symbols", [])),
    }


def main() -> None:
    env = load_env(ENV_PATH)
    headers = make_headers(env)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    state = load_checkpoint()

    if state.get("done"):
        print(f"Checkpoint marks pull already complete: {state['rows_written']} rows. Nothing to do.")
        return

    write_header = not OUT_CSV.exists() or state["rows_written"] == 0
    seen_ids = set(state.get("seen_ids_sample", []))  # not used for full dedup; final pass dedups by id

    import csv

    mode = "a" if OUT_CSV.exists() and not write_header else "w"
    f = open(OUT_CSV, mode, newline="")
    writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
    if write_header:
        writer.writeheader()

    page_token = state["next_page_token"]
    rows_written = state["rows_written"]
    pages_fetched = 0
    t_start = time.monotonic()

    with httpx.Client() as client:
        while True:
            t0 = time.monotonic()
            data = fetch_page(client, headers, page_token)
            news = data.get("news", [])
            for article in news:
                writer.writerow(article_to_row(article))
                rows_written += 1
            f.flush()
            pages_fetched += 1

            page_token = data.get("next_page_token")
            state = {
                "next_page_token": page_token,
                "rows_written": rows_written,
                "done": page_token is None,
            }
            save_checkpoint(state)

            elapsed_total = time.monotonic() - t_start
            if pages_fetched % 20 == 0 or page_token is None:
                print(
                    f"[{elapsed_total:6.1f}s] pages={pages_fetched} rows={rows_written} "
                    f"next_page_token={'yes' if page_token else 'none (done)'}"
                )

            if page_token is None:
                break

            # Time-box guard: report projected completion if this is running long.
            if elapsed_total > 25 * 60 and pages_fetched % 50 == 0:
                rate = pages_fetched / elapsed_total
                print(
                    f"WARNING: {elapsed_total/60:.1f} min elapsed, {pages_fetched} pages, "
                    f"~{rate*60:.1f} pages/min. Still paginating; checkpoint is current."
                )

            # Rate limiting: ensure >= MIN_REQUEST_INTERVAL_SEC between requests.
            dt = time.monotonic() - t0
            if dt < MIN_REQUEST_INTERVAL_SEC:
                time.sleep(MIN_REQUEST_INTERVAL_SEC - dt)

    f.close()
    print(f"DONE. {rows_written} rows written to {OUT_CSV} across {pages_fetched} pages this run.")


if __name__ == "__main__":
    main()
