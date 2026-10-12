# Staleness gate — material move since the last complete session

**Status:** identified 2026-09-11, deferred to FYP-2. Not in the proposal yet.

## The gap

The recommendation is computed from the most recent **complete** session. If the
market moves sharply after that close, the system answers from stale data and
believes it is healthy — the feed is up and the row is only one session old, so
neither existing degraded path fires.

Worked case: last complete session is Friday's close. NVDA drops 12% at 09:45
Tuesday on an earnings pre-announcement. A user asks at 10:00. The system quotes
Friday's row, with no indication that anything happened.

The §16 failure table covers *feed unavailable* and *insufficient history*. It
does not cover *the world moved since our data*.

## The fix

A **serving-time gate**, not a feature. At request time, before returning a
recommendation:

```
last_close   = the close the feature row was built from
current      = a live quote (one call, no model, no sentiment)
sessions     = complete sessions elapsed since that close
move_sigma   = (current - last_close) / (vol_20d * sqrt(sessions))
```

Then:

| \|move_sigma\| | Behaviour |
| --- | --- |
| < 2 | Serve normally |
| 2 to 3 | Serve **with a labelled warning** naming the move and the session |
| >= 3 | **Degraded state.** No recommendation. |

Suggested wording at the warning level:

> NVDA has moved −3.4 volatility units since the 4 September close. This
> recommendation is computed from that session and does not reflect the move.

## Why this does not break the leakage discipline

This is the part to get right, and it is the reason the fix is safe.

The live price is used **only as a gate on whether to serve**. It never enters
the feature vector, never reaches XGBoost, never appears in the decision record,
and never influences the explanation. The recommendation itself is still
computed purely from a completed session.

Adding a live price as a *feature* would be a same-session leak of exactly the
kind the harness exists to prevent. Using it as a *serving gate* is not, because
it cannot affect the prediction — only whether the prediction is shown.

State that distinction explicitly wherever this is documented. It is the
difference between a safe addition and a dangerous one.

## Thresholds

2σ and 3σ are starting points, not measured values. Financial returns are
fat-tailed, so 2σ will fire more often than a normal distribution predicts —
likely 5–8% of days rather than 5%. Measure the actual distribution of
overnight moves across the universe and set the cuts from that, the same way
the label thresholds were chosen for class balance rather than assumed.

## What it touches

- **New FR** (FR-16): the system shall report a labelled staleness state when
  price has moved materially since the session its recommendation was computed
  from.
- **New row** in the §16 failure table.
- **New control** in the operator view's suite listing.
- **Fault-injection test**, following the existing FR-12 pattern: pin the clock,
  inject a synthetic move, assert the system degrades rather than answering.

## Related but different

The "speculative-spike caution flag" already in the future-extensions list is a
price *and volume* anomaly corroborated by a surge in mention volume. This is
simpler and narrower: has the price moved since the data we are quoting. Build
this one first — it is a few lines and it closes a real hole.
