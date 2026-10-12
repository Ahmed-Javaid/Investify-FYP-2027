"""FinBERT sentiment scoring over headlines only (brief section 5: 128-
token truncation, batched, cached by document hash so a re-run is near-
instant). Reports wall-clock for the scoring pass.

polarity = P(positive) - P(negative), in [-1, 1]. FinBERT's label order
is read from the model config rather than assumed, so a future model
swap can't silently scramble which column is which.
"""
import time
from pathlib import Path

import pandas as pd
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from investify.news_cache import doc_hash

MODEL_NAME = "ProsusAI/finbert"
MAX_TOKENS = 128


def _pick_device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class FinBERTScorer:
    def __init__(self, cache_dir: str, device: str | None = None):
        self.cache_path = Path(cache_dir) / "finbert_scores.parquet"
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.device = device or _pick_device()

        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        self.model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME).to(self.device)
        self.model.eval()

        # read label order from the model config -- never assume it
        id2label = self.model.config.id2label
        self._label_index = {v.lower(): k for k, v in id2label.items()}
        for required in ("positive", "negative", "neutral"):
            if required not in self._label_index:
                raise ValueError(f"FinBERT config missing expected label {required!r}: {id2label}")

        if self.cache_path.exists():
            self._cache = pd.read_parquet(self.cache_path)
        else:
            self._cache = pd.DataFrame(columns=["doc_hash", "positive", "negative", "neutral", "polarity"])

    def _score_batch_uncached(self, texts: list[str]) -> pd.DataFrame:
        with torch.no_grad():
            enc = self.tokenizer(
                texts, truncation=True, max_length=MAX_TOKENS, padding=True, return_tensors="pt"
            ).to(self.device)
            logits = self.model(**enc).logits
            probs = torch.softmax(logits, dim=-1).cpu().numpy()

        pos_i = self._label_index["positive"]
        neg_i = self._label_index["negative"]
        neu_i = self._label_index["neutral"]
        return pd.DataFrame(
            {
                "positive": probs[:, pos_i],
                "negative": probs[:, neg_i],
                "neutral": probs[:, neu_i],
                "polarity": probs[:, pos_i] - probs[:, neg_i],
            }
        )

    def score(self, headlines_df: pd.DataFrame, text_col: str = "headline", batch_size: int = 32) -> pd.DataFrame:
        """Returns headlines_df with positive/negative/neutral/polarity
        columns attached, using the on-disk cache wherever possible."""
        df = headlines_df.copy()
        df["doc_hash"] = df[text_col].apply(doc_hash)

        known_hashes = set(self._cache["doc_hash"])
        to_score = df[~df["doc_hash"].isin(known_hashes)].drop_duplicates(subset="doc_hash")

        t0 = time.time()
        n_scored = 0
        if len(to_score):
            new_rows = []
            texts = to_score[text_col].tolist()
            hashes = to_score["doc_hash"].tolist()
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i : i + batch_size]
                batch_hashes = hashes[i : i + batch_size]
                scored = self._score_batch_uncached(batch_texts)
                scored["doc_hash"] = batch_hashes
                new_rows.append(scored)
            new_scores = pd.concat(new_rows, ignore_index=True)
            self._cache = (
                new_scores
                if self._cache.empty
                else pd.concat([self._cache, new_scores], ignore_index=True).drop_duplicates(subset="doc_hash")
            )
            self._cache.to_parquet(self.cache_path, index=False)
            n_scored = len(to_score)
        elapsed = time.time() - t0

        print(
            f"[FinBERT] {n_scored} newly scored, {len(df) - n_scored} from cache, "
            f"{elapsed:.1f}s wall-clock ({n_scored / elapsed:.1f} docs/sec)"
            if n_scored and elapsed > 0
            else f"[FinBERT] {n_scored} newly scored, {len(df) - n_scored} from cache (cache hit, ~0s)"
        )

        return df.merge(self._cache, on="doc_hash", how="left")
