"""As-of join: attach the most recently COMPLETED session's aggregated
sentiment features to each price bar, via a backward as-of join with an
explicit maximum look-back. Never a nearest-in-time join (which could
silently reach into the future), and never the price bar's own session
(allow_exact_matches=False) -- a session's own text is not known until
that session has already closed, so it cannot feed that session's own
feature row.
"""
import pandas as pd


def aggregate_session_sentiment(scored_news_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per (ticker, session): mean polarity, mention volume,
    and the latest contributing event_ts (kept for the as-of join's own
    correctness test, not used as a model feature)."""
    grouped = (
        scored_news_df.groupby(["ticker", "session"])
        .agg(
            mean_polarity=("polarity", "mean"),
            mention_volume=("polarity", "size"),
            latest_event_ts=("event_ts", "max"),
        )
        .reset_index()
    )
    return grouped.sort_values(["ticker", "session"]).reset_index(drop=True)


def add_backward_only_momentum(session_features_df: pd.DataFrame) -> pd.DataFrame:
    """3-day and 7-day polarity momentum, mention-volume z-score and
    dispersion, computed backward-only per ticker (no centre=True, no
    negative shifts)."""
    df = session_features_df.sort_values(["ticker", "session"]).copy()
    g = df.groupby("ticker")["mean_polarity"]
    df["mom_3d"] = g.transform(lambda s: s.rolling(3, min_periods=1).mean() - s.shift(3))
    df["mom_7d"] = g.transform(lambda s: s.rolling(7, min_periods=1).mean() - s.shift(7))

    vol = df.groupby("ticker")["mention_volume"]
    roll_mean = vol.transform(lambda s: s.rolling(20, min_periods=5).mean())
    roll_std = vol.transform(lambda s: s.rolling(20, min_periods=5).std())
    df["volume_z"] = (df["mention_volume"] - roll_mean) / roll_std.replace(0, pd.NA)

    disp = df.groupby("ticker")["mean_polarity"]
    df["dispersion"] = disp.transform(lambda s: s.rolling(5, min_periods=2).std())
    return df


def asof_join_features(
    price_df: pd.DataFrame,
    session_features_df: pd.DataFrame,
    max_lookback_days: int,
    date_col: str = "date",
    session_col: str = "session",
) -> pd.DataFrame:
    """Backward as-of join, per ticker: for each price bar (session S),
    attach the most recent PRIOR session's sentiment features, within
    max_lookback_days. allow_exact_matches=False forbids using session
    S's own text for session S's own row."""
    left = price_df.copy()
    left["_asof_key"] = pd.to_datetime(left[date_col])
    right = session_features_df.copy()
    right["_asof_key"] = pd.to_datetime(right[session_col])

    merged_parts = []
    for ticker, left_g in left.groupby("ticker"):
        right_g = right[right["ticker"] == ticker]
        m = pd.merge_asof(
            left_g.sort_values("_asof_key"),
            right_g.sort_values("_asof_key"),
            on="_asof_key",
            direction="backward",
            allow_exact_matches=False,
            tolerance=pd.Timedelta(days=max_lookback_days),
            suffixes=("", "_sentiment"),
        )
        merged_parts.append(m)

    result = pd.concat(merged_parts, ignore_index=True)
    return result.drop(columns=["_asof_key", "ticker_sentiment"], errors="ignore")
