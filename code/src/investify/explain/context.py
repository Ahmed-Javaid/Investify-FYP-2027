"""User-readable evidence and the input contract for a future LLM explainer.

Every value and attribution comes from the frozen decision record. Reviewed
indicator definitions explain what a feature measures; they never infer a
market cause or a trading rule from a feature's sign. This module has no model,
network, or training dependency and does not modify the recorded prediction.
"""
from __future__ import annotations

from datetime import date
from math import fsum, isfinite

from investify.decision_record import DecisionRecord

GUIDE = "https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/"
ATTRIBUTION_SCOPE = (
    "Attributions explain the raw model score for the selected class. "
    "They do not sum to its calibrated probability and do not establish what caused a market price move."
)


def attribution_direction(value: float) -> str:
    return "supports" if value > 0 else "opposes" if value < 0 else "neutral"

# Definitions of derived features follow features/indicators.py and assembly.py.
# External references describe the underlying indicator, not this model's skill.
FEATURES = {
    "rsi_14": ("Technical analysis", "Relative strength index", "Recent price momentum on a zero-to-one-hundred scale, calculated here over fourteen sessions.", GUIDE + "rsi"),
    "macd_hist": ("Technical analysis", "MACD histogram", "The difference between the MACD line and its signal line; it describes a change in price momentum.", GUIDE + "macd"),
    "dist_sma200": ("Technical analysis", "Distance from the long-term average", "The closing price's relative distance from its trailing two-hundred-session average.", GUIDE + "sma"),
    "bollinger_pos": ("Technical analysis", "Position within the Bollinger bands", "The closing price's position between trailing volatility bands. Values can move outside the usual band interval.", GUIDE + "bollinger-bands"),
    "obv_slope": ("Technical analysis", "Volume trend", "The average change in on-balance volume over fourteen sessions; volume is added on rising closes and subtracted on falling closes.", GUIDE + "obv"),
    "mean_polarity": ("News sentiment", "Average headline sentiment", "Average headline polarity, calculated as the positive-class probability minus the negative-class probability.", "https://huggingface.co/ProsusAI/finbert"),
    "mention_volume": ("News sentiment", "Headline count", "The number of scored headlines assigned to the contributing news session.", ""),
    "mom_3d": ("News sentiment", "Short sentiment momentum", "The trailing three-session average headline polarity minus polarity three sessions earlier.", ""),
    "mom_7d": ("News sentiment", "Longer sentiment momentum", "The trailing seven-session average headline polarity minus polarity seven sessions earlier.", ""),
    "volume_z": ("News sentiment", "Unusual news attention", "Headline count relative to its trailing twenty-session mean and standard deviation; it is news attention, not traded share volume.", ""),
    "dispersion": ("News sentiment", "Variation in recent sentiment", "The trailing five-session standard deviation of average polarity; it is variation across sessions, not disagreement among individual headlines.", ""),
}


def build_context(record: DecisionRecord, *, corpus: str) -> dict:
    """Return a JSON-safe account of all features, including missing values.

Unknown features remain visible without fabricated definitions. Missing feature
values stay missing; a recorded attribution does not authorize inventing a value.
Family contributions use the same raw-score units as the original SHAP vector.
"""
    date.fromisoformat(record.session_date)
    if record.horizon_days <= 0:
        raise ValueError("The explanation requires a positive prediction horizon")
    if not all(isfinite(float(p)) and 0 <= p <= 1 for p in record.probabilities.values()):
        raise ValueError("The explanation requires finite probabilities in the unit interval")
    rows = []
    for name, value in record.feature_vector.items():
        shap = float(record.shap_values[name])
        if not isfinite(shap):
            raise ValueError(f"Non-finite attribution for {name}")
        family, label, meaning, source = FEATURES.get(
            name,
            ("Unclassified", name, "A definition has not been reviewed for this feature.", ""),
        )
        number = float(value) if value is not None else None
        available = number is not None and isfinite(number)
        effect = attribution_direction(shap)
        rows.append({
            "feature": name, "label": label, "family": family,
            "value": number if available else None, "value_available": available,
            "shap_value": shap, "effect_on_predicted_class": effect,
            "meaning": meaning, "reference": source,
        })
    families = sorted({r["family"] for r in rows})
    totals = {family: fsum(r["shap_value"] for r in rows if r["family"] == family) for family in families}
    return {
        "schema_version": "mideval-evidence-v1",
        "ticker": record.ticker, "session_date": record.session_date,
        "horizon_days": record.horizon_days, "decision": record.decision,
        "probabilities": dict(record.probabilities), "corpus": corpus,
        "model_version": record.model_version, "features": rows,
        "family_contributions": totals,
        "base_value": record.base_value, "raw_model_output": record.raw_model_output,
        "coverage": {
            "technical_features": sum(r["family"] == "Technical analysis" for r in rows),
            "news_features": sum(r["family"] == "News sentiment" for r in rows),
            "social_sentiment": "Not present in this news-only spike",
            "risk_conditioning": "The risk profile does not condition the saved classifier; the live demo offers a separate prototype comparator",
        },
        "interpretation": ATTRIBUTION_SCOPE,
        "data_status": "Historical experiment record; no live market freshness is established",
        "notice": record.non_advice_notice,
    }
