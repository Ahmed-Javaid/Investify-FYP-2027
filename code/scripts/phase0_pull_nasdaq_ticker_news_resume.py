"""Resume the nasdaq_exteral_data.csv scan that crashed at row 2,400,000
(~73% through the file) on a pandas internal bug: combining `usecols` with
chunked low-memory dtype-consistency checking hits an IndexError inside
pandas' own _concatenate_chunks warning path. Fixed here with dtype=str
(no type inference, no mismatch warnings possible) and low_memory=False.

Resumes via an estimated byte offset (interpolated from the last known
row-count/byte-count checkpoint, minus a 1GB safety margin -- we'd rather
re-scan ~140k rows than silently skip real ones). Appends to the existing
partial output; duplicate rows near the resume boundary are removed by a
final dedup pass.
"""
import io
import os
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

# estimated from the crash log: 2,000,000 rows confirmed at 14,104.7MB (60.7%),
# crash occurred after 2,400,000 rows -- interpolate the extra 400k rows at the
# same observed ~7052 bytes/row, then back off 1GB as a safety margin.
RESUME_FROM_BYTE = 14_104_700_000 + int(400_000 * 7052) - 1_000_000_000

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


t0 = time.time()
rows_scanned = 0
matched_total = 0
crashed = False

try:
    with httpx.stream(
        "GET", url, follow_redirects=True, timeout=httpx.Timeout(30.0, read=180.0),
        headers={"Range": f"bytes={RESUME_FROM_BYTE}-"},
    ) as r:
        r.raise_for_status()
        # for a 206 Partial Content response, content-length is the REMAINDER size
        remainder_size = int(r.headers.get("content-length", 0))
        print(f"resuming from byte {RESUME_FROM_BYTE:,} -- {remainder_size/1e9:.2f} GB remaining, status={r.status_code}", flush=True)

        raw_iter = r.iter_bytes(chunk_size=262_144)

        # discard the first partial line (we started mid-row at an arbitrary offset)
        first_chunk = next(raw_iter)
        nl = first_chunk.find(b"\n")
        while nl == -1:
            first_chunk += next(raw_iter)
            nl = first_chunk.find(b"\n")
        remainder_first_chunk = first_chunk[nl + 1:]
        print(f"discarded {nl+1} bytes of partial first line", flush=True)

        def chained():
            if remainder_first_chunk:
                yield remainder_first_chunk
            yield from raw_iter

        stream = HttpxStream(chained())
        buffered = io.BufferedReader(stream, buffer_size=1_000_000)

        reader = pd.read_csv(
            buffered,
            chunksize=CHUNK_ROWS,
            names=COLS,
            header=None,  # no header line -- we're resuming mid-file
            usecols=["Date", "Article_title", "Stock_symbol", "Publisher"],
            on_bad_lines="skip",
            engine="c",
            dtype=str,
            low_memory=False,
        )

        chunk_idx = 0
        for chunk in reader:
            chunk_idx += 1
            rows_scanned += len(chunk)
            m = chunk[chunk["Stock_symbol"].isin(TICKERS)][KEEP_COLS]
            if len(m):
                m.to_csv(OUT_CSV, mode="a", header=False, index=False)
                matched_total += len(m)

            if chunk_idx % PROGRESS_EVERY_N_CHUNKS == 0:
                elapsed = time.time() - t0
                bytes_seen = stream.total_read
                rate = bytes_seen / elapsed / 1e6 if elapsed > 0 else 0
                pct = 100 * bytes_seen / remainder_size if remainder_size else 0
                eta = (remainder_size - bytes_seen) / (rate * 1e6) if rate > 0 else float("inf")
                print(
                    f"[{elapsed:7.1f}s] {bytes_seen/1e6:8.1f}/{remainder_size/1e6:.0f} MB ({pct:5.1f}%) | "
                    f"{rate:5.2f} MB/s | ETA {eta:6.0f}s | rows_scanned={rows_scanned:>10,} | matched={matched_total:>6,}",
                    flush=True,
                )
except Exception as e:
    crashed = True
    elapsed = time.time() - t0
    print(f"\nCRASHED after {elapsed:.1f}s: {type(e).__name__}: {e}", flush=True)
    print(f"PARTIAL RESULTS: rows_scanned={rows_scanned:,} matched_total={matched_total:,} (checkpointed rows safe in {OUT_CSV})", flush=True)
    raise
finally:
    elapsed = time.time() - t0
    if not crashed:
        print(f"\nDONE (resume leg). rows_scanned={rows_scanned:,} bytes={stream.total_read:,} in {elapsed:.1f}s", flush=True)
        print(f"matched_total this leg={matched_total:,}, appended to {OUT_CSV}", flush=True)

        # dedup the full file now that both legs are combined
        full = pd.read_csv(OUT_CSV)
        before = len(full)
        full = full.drop_duplicates(subset=["Date", "Article_title", "Stock_symbol", "Publisher"])
        after = len(full)
        full.to_csv(OUT_CSV, index=False)
        print(f"dedup: {before:,} -> {after:,} rows ({before - after:,} duplicates removed, expected near the resume boundary)", flush=True)
    print(f"TOTAL WALL TIME: {elapsed:.1f}s", flush=True)
