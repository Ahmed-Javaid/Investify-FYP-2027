"""Validate/join original cached news scores without importing a model."""
import hashlib

import numpy as np
import pandas as pd


def doc_hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def attach_cached_scores(news, cache):
    required = {'doc_hash', 'positive', 'negative', 'neutral', 'polarity'}
    if not required.issubset(cache.columns):
        raise ValueError(f'FinBERT cache missing required fields: {sorted(required - set(cache.columns))}')
    if cache['doc_hash'].isna().any() or cache['doc_hash'].duplicated().any():
        raise ValueError('FinBERT cache must have unique nonmissing document hashes')
    if not cache['doc_hash'].map(lambda value: isinstance(value, str) and len(value) == 64
                                 and all(character in '0123456789abcdef' for character in value)).all():
        raise ValueError('FinBERT cache document hashes must be canonical SHA256 values')
    if any(pd.api.types.is_bool_dtype(cache[name]) for name in ('positive', 'negative', 'neutral', 'polarity')):
        raise ValueError('FinBERT cache probabilities/polarity must be numeric, not booleans')
    probabilities = cache[['positive', 'negative', 'neutral']].to_numpy(dtype=float)
    polarity = cache['polarity'].to_numpy(dtype=float)
    if (not np.isfinite(probabilities).all() or not np.isfinite(polarity).all()
            or (probabilities < 0).any() or (probabilities > 1).any()
            or not np.allclose(probabilities.sum(axis=1), 1, atol=1e-6, rtol=0)
            or not np.allclose(polarity, probabilities[:, 0] - probabilities[:, 1], atol=1e-6, rtol=0)):
        raise ValueError('FinBERT cache probabilities/polarity are nonfinite, unnormalised or inconsistent')
    if 'polarity' in news.columns:
        raise ValueError('Cached-score attachment requires raw headlines without an existing polarity column')
    frame = news.copy()
    frame['doc_hash'] = frame['headline'].map(doc_hash)
    merged = frame.merge(cache[['doc_hash', 'polarity']], on='doc_hash', how='left', validate='many_to_one')
    missing = int(merged['polarity'].isna().sum())
    if missing:
        raise ValueError(f'{missing} headlines have no cached FinBERT score; no unscored text is dropped or replaced')
    if len(merged) != len(news):
        raise ValueError('Cached-score attachment changed headline cardinality')
    merged.attrs.update(news.attrs)
    return merged
