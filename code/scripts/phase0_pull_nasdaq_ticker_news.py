"""Phase 0 follow-up: full scan of FNSPID's nasdaq_exteral_data.csv (23GB,
full article bodies) for AAPL/NVDA/TSLA, to get the per-ticker
granularity+coverage numbers All_external.csv couldn't provide (it stops
mid-2020; this file's samples reached 2023-12).

Same httpx-stream -> file-like adapter -> pandas C tokenizer approach as
phase0_pull_ticker_news.py (verified correct against embedded-newline
quoted fields via a synthetic adversarial test). Checkpoints matched rows
to disk per chunk, so a crash mid-scan leaves labeled partial results
rather than losing everything -- this file's full article-body text is
messier scraped content than the headline-only file and more likely to
hit a genuinely malformed row.
"""
import io
import os
import sys
import time

import httpx
import pandas as pd
from huggingface_hub import hf_hub_url

TICKERS = {"AAPL", "NVDA", "TSLA"}
COLS = [
    "row_idx", "Date", "Article_title", "Stock_symbol", "Url", "Publisher",
    "Author", "Article", "Lsa_summary", "Luhn_summary",
    "Textrank_summary", "Lexrank_summary",
]
KEEP_COLS = ["Date", "Article_title", "Stock_symbol", "Publisher"]
CHUNK_ROWS = 100_000
OUT_CSV = "data/raw/fnspid_nasdaq_external_aapl_nvda_tsla.csv"
PROGRESS_EVERY_N_CHUNKS = 5

url = hf_hub_url("Zihan1004/FNSPID", "Stock_news/nasdaq_exteral_data.csv", repo_type="dataset")


class HttpxStream(io.RawIOBase):
    def __init__(self, byte_iter):
        self._iter = byte_iter
        self._leftover = b""
        self.total_read = 0

    def readable(self):
        return True

    def readinto(self, b):
        if not self._leftover:
            try:
                self._leftover = next(self._iter)
            except StopIteration:
                return 0
        n = len(b)
        output, self._leftover = self._leftover[:n], self._leftover[n:]
        b[: len(output)] = output
        self.total_read += len(output)
        return len(output)


os.makedirs("data/raw", exist_ok=True)
if os.path.exists(OUT_CSV):
    os.remove(OUT_CSV)
wrote_header = False

t0 = time.time()
rows_scanned = 0
matched_total = 0
crashed = False

try:
    with httpx.stream("GET", url, follow_redirects=True, timeout=httpx.Timeout(30.0, read=180.0)) as r:
        r.raise_for_status()
        total_size = int(r.headers.get("content-length", 0))
        print(f"streaming {total_size/1e9:.2f} GB from {url}", flush=True)

        stream = HttpxStream(r.iter_bytes(chunk_size=262_144))
        buffered = io.BufferedReader(stream, buffer_size=1_000_000)

        reader = pd.read_csv(
            buffered,
            chunksize=CHUNK_ROWS,
            names=COLS,
            header=0,
            usecols=["Date", "Article_title", "Stock_symbol", "Publisher"],
            on_bad_lines="skip",
            engine="c",
            # dtype=str + low_memory=False: usecols + chunked low_memory dtype
            # consistency checks hit a pandas internal IndexError in
            # _concatenate_chunks on this file (hit at ~73% through a real
            # run). No type inference needed here anyway -- see
            # phase0_pull_nasdaq_ticker_news_resume.py.
            dtype=str,
            low_memory=False,
        )

        chunk_idx = 0
        for chunk in reader:
            chunk_idx += 1
            rows_scanned += len(chunk)
            m = chunk[chunk["Stock_symbol"].isin(TICKERS)][KEEP_COLS]
            if len(m):
                m.to_csv(OUT_CSV, mode="a", header=not wrote_header, index=False)
                wrote_header = True
                matched_total += len(m)

            if chunk_idx % PROGRESS_EVERY_N_CHUNKS == 0:
                elapsed = time.time() - t0
                bytes_seen = stream.total_read
                rate = bytes_seen / elapsed / 1e6 if elapsed > 0 else 0
                pct = 100 * bytes_seen / total_size if total_size else 0
                eta = (total_size - bytes_seen) / (rate * 1e6) if rate > 0 else float("inf")
                print(
                    f"[{elapsed:7.1f}s] {bytes_seen/1e6:8.1f}/{total_size/1e6:.0f} MB ({pct:5.1f}%) | "
                    f"{rate:5.2f} MB/s | ETA {eta:6.0f}s | rows_scanned={rows_scanned:>10,} | matched={matched_total:>6,}",
                    flush=True,
                )
except Exception as e:
    crashed = True
    elapsed = time.time() - t0
    print(f"\nCRASHED after {elapsed:.1f}s: {type(e).__name__}: {e}", flush=True)
    print(f"PARTIAL RESULTS: rows_scanned={rows_scanned:,} matched_total={matched_total:,} (checkpointed rows up to the crash are safe in {OUT_CSV})", flush=True)
    raise
finally:
    elapsed = time.time() - t0
    if not crashed:
        print(f"\nDONE. rows_scanned={rows_scanned:,} bytes={stream.total_read:,} in {elapsed:.1f}s ({stream.total_read/elapsed/1e6:.2f} MB/s avg)", flush=True)
        print(f"matched_total={matched_total:,} written to {OUT_CSV}", flush=True)
    print(f"TOTAL WALL TIME: {elapsed:.1f}s", flush=True)
