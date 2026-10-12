"""A separately declared chronological comparator using SAVED raw feature rows.

Fit population z-score statistics on the first floor(0.8*N) rows of each
corpus. Only the later rows may be scored. This does not recover the old
engine's scaler, replicate its CV baseline, personalize XGBoost, or measure
profitability. R is the reconciled prototype profile score; that mapping is a
project assumption, not evidence that a blend is suitable for an investor.
"""
import hashlib
import json
from dataclasses import dataclass
from datetime import date
from math import fsum, isfinite, sqrt
from pathlib import Path

from investify.decision_record import DecisionRecord
from investify.risk_profile import RiskProfile

COMPARATOR_VERSION = "mideval-retrospective-linear-v1"
TECHNICAL = ('rsi_14', 'macd_hist', 'dist_sma200', 'bollinger_pos', 'obv_slope')
INPUTS = (*TECHNICAL, 'mean_polarity')


def _finite(value):
    return type(value) in (int, float) and isfinite(value)


def linear_score(technical: float, sentiment: float, weight: float) -> dict:
    """Same fixed trend signs and right-closed thresholds as the old baseline."""
    if not all(_finite(x) for x in (technical, sentiment, weight)) or not 0 <= weight <= 1:
        raise ValueError("comparator inputs must be finite and R in [0, 1]")
    score = weight * sentiment + (1 - weight) * technical
    if not isfinite(score):
        raise ValueError("comparator score is non-finite")
    decision = 'Sell' if score <= -.5 else 'Hold' if score <= .5 else 'Buy'
    return {'score': score, 'decision': decision, 'sentiment_weight': weight,
            'sentiment_term': weight * sentiment, 'technical_term': (1 - weight) * technical}


@dataclass(frozen=True)
class HistoricalComparator:
    manifest: dict
    records: dict[str, DecisionRecord]

    def score(self, session: str, profile: RiskProfile) -> dict:
        if session not in self.manifest['heldout_sessions']:
            raise ValueError("The selected session is in the scaling-development block; choose a held-out session")
        record = self.records[session]
        scaled = {}
        for name in INPUTS:
            value = record.feature_vector[name]
            if name in TECHNICAL and not _finite(value):
                raise ValueError(f"Missing technical input {name}; no comparator decision is emitted")
            stats = self.manifest['scaling'][name]
            scaled[name] = ((value - stats['mean']) / stats['scale']) if _finite(value) else None
        technical = fsum(scaled[name] for name in TECHNICAL) / len(TECHNICAL)
        missing_sentiment = scaled['mean_polarity'] is None
        sentiment = 0.0 if missing_sentiment else scaled['mean_polarity']
        reference = linear_score(technical, sentiment, .5)
        conditioned = linear_score(technical, sentiment, profile.score)
        return {'version': COMPARATOR_VERSION, 'ticker': record.ticker, 'session': session,
                'corpus': self.manifest['corpus'], 'artifact_sha256': self.manifest['artifact_sha256'],
                'scaling_fit_end': self.manifest['fit_end'], 'scaling_rows': self.manifest['fit_rows'],
                'scaled_inputs': scaled, 'technical_signal': technical, 'sentiment_signal': sentiment,
                'missing_sentiment': missing_sentiment, 'reference': reference, 'profile_conditioned': conditioned,
                'profile': profile.to_dict(), 'saved_classifier_decision': record.decision,
                'saved_classifier_probabilities': dict(record.probabilities),
                'interpretation': 'Comparator scores are weighted z-scores, not calibrated probabilities or expected returns.',
                'missing_policy': 'Missing news contributes zero after scaling; this is an absent signal, not measured neutral sentiment.',
                'limitation': 'Prototype weighting is not validated for suitability or predictive performance. Outcome labels are absent.'}


def build_comparator(path: Path, *, corpus: str) -> HistoricalComparator:
    """Recompute statistics from declared development rows, never a supplied scaler."""
    raw = path.read_bytes()
    data = json.loads(raw)
    records = sorted((DecisionRecord.from_dict(row) for row in data['decision_records']), key=lambda r: r.session_date)
    if len(records) < 10 or len({r.session_date for r in records}) != len(records):
        raise ValueError("comparator requires at least ten unique historical sessions")
    if len({(r.ticker, r.horizon_days, r.model_version) for r in records}) != 1:
        raise ValueError("comparator requires one ticker, horizon and saved model per corpus")
    for record in records:
        date.fromisoformat(record.session_date)
        if any(name not in record.feature_vector for name in INPUTS):
            raise ValueError("required comparator feature absent from the saved records")
    split = 4 * len(records) // 5
    development, heldout = records[:split], records[split:]
    stats = {}
    for name in INPUTS:
        values = [r.feature_vector[name] for r in development if _finite(r.feature_vector[name])]
        if not values or name in TECHNICAL and len(values) != len(development):
            raise ValueError(f"insufficient development observations for {name}")
        mean = fsum(values) / len(values)
        variance = fsum((x - mean) ** 2 for x in values) / len(values)
        scale = sqrt(variance) if variance > 0 else 1.0
        if not _finite(mean) or not _finite(scale) or scale <= 0:
            raise ValueError("non-finite scaling statistics")
        stats[name] = {'mean': mean, 'scale': scale, 'observed_rows': len(values)}
    manifest = {'version': COMPARATOR_VERSION, 'corpus': corpus, 'ticker': records[0].ticker,
                'horizon_days': records[0].horizon_days, 'saved_model_version': records[0].model_version,
                'artifact_sha256': hashlib.sha256(raw).hexdigest(),
                'split_rule': 'Chronological first floor(4*N/5) development; remainder held out',
                'fit_start': development[0].session_date, 'fit_end': development[-1].session_date,
                'fit_rows': len(development), 'development_sessions': [r.session_date for r in development],
                'heldout_sessions': [r.session_date for r in heldout], 'scaling': stats,
                'scaling_convention': 'Population standard deviation (ddof=0), constant feature scale=1',
                'technical_convention': 'Mean of five technical z-scores; larger values are trend-positive',
                'sentiment_convention': 'Z-score of mean_polarity; missing held-out news -> zero signal',
                'formula': 'C = R*S + (1-R)*T; R = reconciled prototype profile score',
                'thresholds': {'Sell': 'C <= -0.5', 'Hold': '-0.5 < C <= 0.5', 'Buy': 'C > 0.5'},
                'reference_weight': .5, 'predictive_performance': None,
                'limitation': 'New retrospective comparator; not a reconstruction of historical CV or personalized XGBoost.'}
    return HistoricalComparator(manifest, {r.session_date: r for r in records})
