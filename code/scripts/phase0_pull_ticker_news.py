"""Phase 0: stream FNSPID's All_external.csv through pandas' own C tokenizer
(fed by an httpx byte stream via a file-like adapter) so quote/newline
handling is correct across network chunk boundaries -- v2's manual
buffer-splitting corrupted a row whose quoted field happened to contain a
literal newline right at a flush boundary.

Matched rows are appended to a local CSV incrementally, so a crash partway
through does not lose progress (v2's failure mode).
"""
import csv
import io
import os
import sys
import time

import httpx
import pandas as pd
from huggingface_hub import hf_hub_url

TICKERS = {"AAPL", "NVDA", "TSLA"}
COLS = [
    "Date", "Article_title", "Stock_symbol", "Url", "Publisher",
    "Author", "Article", "Lsa_summary", "Luhn_summary",
    "Textrank_summary", "Lexrank_summary",
]
KEEP_COLS = ["Date", "Article_title", "Stock_symbol", "Publisher"]
CHUNK_ROWS = 200_000
OUT_CSV = "data/raw/fnspid_all_external_aapl_nvda_tsla.csv"

url = hf_hub_url("Zihan1004/FNSPID", "Stock_news/All_external.csv", repo_type="dataset")


class HttpxStream(io.RawIOBase):
    """Adapts an httpx streaming response into a file-like object pandas can
    read incrementally, tracking bytes consumed for progress reporting."""

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

with httpx.stream("GET", url, follow_redirects=True, timeout=httpx.Timeout(30.0, read=120.0)) as r:
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
        on_bad_lines="skip",
        engine="c",
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

        if chunk_idx % 5 == 0:
            elapsed = time.time() - t0
            bytes_seen = stream.total_read
            rate = bytes_seen / elapsed / 1e6 if elapsed > 0 else 0
            pct = 100 * bytes_seen / total_size if total_size else 0
            eta = (total_size - bytes_seen) / (rate * 1e6) if rate > 0 else float("inf")
            print(
                f"[{elapsed:7.1f}s] {bytes_seen/1e6:8.1f}/{total_size/1e6:.0f} MB ({pct:5.1f}%) | "
                f"{rate:5.2f} MB/s | ETA {eta:5.0f}s | rows_scanned={rows_scanned:>9,} | matched={matched_total:>6,}",
                flush=True,
            )

elapsed = time.time() - t0
print(f"\nDONE. rows_scanned={rows_scanned:,} bytes={stream.total_read:,} in {elapsed:.1f}s ({stream.total_read/elapsed/1e6:.2f} MB/s avg)", flush=True)
print(f"matched_total={matched_total:,} written to {OUT_CSV}", flush=True)
print(f"TOTAL WALL TIME: {elapsed:.1f}s", flush=True)
