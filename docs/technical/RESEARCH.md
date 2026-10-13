# Investify research reference

Consolidated model inventory, datasets, results, explanation design and domain
limits. Implementation/setup: [engineering](ENGINEERING.md). Acceptance and
proposal responses: [requirements](REQUIREMENTS.md).

## Contribution and models

The project builds temporal evaluation controls and explanations checked against
recorded evidence. Pretrained sentiment, XGBoost and TreeSHAP provide components;
using them alone is not a novelty claim. The intended LLM communicates the
decision/evidence rather than determining the class or certifying an outcome.

| Component | Role and state |
| --- | --- |
| ProsusAI/FinBERT | Financial-news sentiment; polarity is positive minus negative probability. Genuine fresh headline inference completed with the original pinned checkpoint. |
| CryptoBERT/Cardiff | Social candidates, both executed on the same frozen MSFT references. Deployment selection remains open. |
| XGBoost | Project-trained classifier over eleven technical/news features; raw predictions vary; original isotonic decisions are all Buy. New temperature records preserve classes but confidence is near one-third. |
| Isotonic calibration | Held-out probability mapping improves Brier while collapsing the emitted class. |
| TreeSHAP | Attribution of raw predicted-class score, not probabilities, causes or expected returns. |
| Template/verifier | Deterministic explanation, independent prose/JSON checks and checked fallback. |
| OpenAI GPT-6 assistant teacher | Six actual controlled-prose examples; deterministic factual JSON is disclosed hybrid supervision. |
| Original Phi-3-mini | Planned student; exact checkpoint/runtime, baseline inference and QLoRA remain unfinished. |
| Mistral | Fallback option, not a completed substitute study. |

Use original publisher models and publisher-issued quantizations for baselines.
Later project adapters are versioned/disclosed separately. Earlier third-party
variant scores are withdrawn; Qwen entries are inactive history, not required
teacher downloads. Exact assistant serving revision, token use and example
latency are unavailable.

## Data and experiment versions

NVDA decision window: 2018-2023. Each selection contains 186 final evaluation
decisions from 29 March-21 December 2023 at a five-session horizon. Prices reach
29 December; outcome-label availability determines the earlier final decision
date. Earlier periods train/calibrate. No continuously updating 2026 feed exists.

| Selection | Meaning |
| --- | --- |
| Fresh Alpaca, frozen classifier | New October-2026 historical acquisition/execution; the same classifier/scaler serves calibration and evaluation. |
| Fresh Alpaca, refit classifier | Same fresh data; later retrained classifier receives earlier fitted calibration mappings. |
| Archived Alpaca | Preserved earlier Alpaca-news experiment. |
| Archived FNSPID | Preserved earlier financial-news corpus experiment. |

Fresh means newly executed historical work. The new run consumed 1,509 complete
NYSE price sessions and 6,768 news rows containing 5,748 distinct headlines,
scored with original FinBERT revision `0bc2ac10dda6929bcb1f77ccc43c7ec5c424f031`.
Price basis is current-vintage SIP split adjustment without cash-dividend
adjustment. News availability uses `max(created_at, updated_at)`. Neither policy
proves historical vendor availability or reproduces original September bytes.
No new FNSPID download occurred in the continuation.

The earlier corpus audit found extensive midnight-only timestamps and gaps for
other tickers. NVDA-only was a bounded spike decision. MSFT social posts are a
separate benchmark; they are not integrated NVDA model features.

## Executed prediction and calibration

Six arms at one/five sessions used shared rows, six folds, fixed seed and model
settings. Clean five-session macro-F1 is **0.2843** against stratified-random
**0.3287**, lift **-0.0444**. The deliberately centred Bollinger canary gives
lift **+0.2104**, fold-bootstrap interval **[+0.1698,+0.2421]**. This is a labelled
leakage failure, not useful prediction. Same-bar text remains a lag ablation.

| Mode | Rows | Raw macro-F1 | Calibrated macro-F1 | Brier before/after |
| --- | ---: | ---: | ---: | --- |
| Frozen | 186 | 0.3182 | 0.2238 | 0.7929 / 0.6105 |
| Refit transfer | 186 | 0.3116 | 0.2238 | 0.7760 / 0.6078 |

Five unavailable calibration outcomes were excluded, leaving 181 rows. Both
modes emit 186 Buy decisions. Buy mapping minimum 0.5344828 exceeds Hold maximum
0.2500000 and Sell maximum 0.3139535; common positive normalization preserves
ordering. These maps force Buy. Retraining is unnecessary for this fresh
collapse, which does not establish the earlier September cause.

Retained-model replay reproduces scores/probabilities. Native TreeSHAP matches
exported contributions, with maximum frozen residual about 1.02e-6 against the
unchanged 1e-4 tolerance. All 372 new guided records verify separately from the
372 archived records in portable CI. The recovered runtime meets declared
ranges; exact original raw-input/uv.lock restoration remains separate.

[Execution/replay summary](../../evidence/fresh_alpaca_science_summary_20261012_run01.json) ·
[Calibration bounds](../../evidence/calibration_global_bounds_20261013.json).

## Social comparison

Two hundred real MSFT posts produced 117 usable references and 83 exclusions.
Labels: 31 positive, 67 neutral, 19 negative. Chronological split: 93 development,
24 held out; held-out labels: 7 positive, 15 neutral, 2 negative. Single reference-construction pass, disclosed in report Chapter 7; independent
validation and reliability are unmeasured.

| Candidate | Macro-F1 agreement | Exact agreement | Limit |
| --- | ---: | ---: | --- |
| CryptoBERT | 0.256410 | 15/24 | All neutral; positive/negative recall zero. |
| Cardiff | 0.601587 | 16/24 | Positive recall 4/7; negative 1/2. |

CryptoBERT's crypto-social domain does not automatically transfer to equity
tweets; Cardiff is a Twitter alternative. Both original classifiers completed
the same frozen sample. Cardiff leads this exploratory comparison. One prediction
changes exact agreement by 4.17 points; negative recall moves in fifty-point
steps. This is reference-label agreement, not deployment accuracy, significance,
NVDA transfer or return prediction. Raw logits, preprocessing/class mappings,
checkpoint/tokenizer identities and failed attempts are retained.

[Paired study](../../evidence/social_study_review_20261013.json) ·
[CryptoBERT publisher](https://huggingface.co/ElKulako/cryptobert) ·
[Cardiff publisher](https://huggingface.co/cardiffnlp/twitter-roberta-base-sentiment-latest) ·
[FinBERT publisher](https://huggingface.co/ProsusAI/finbert).

## Explanation design and teacher pilot

Context supplies identity, horizon, probabilities, all eleven features, SHAP,
maintained definitions, coverage and limits. It invents no social observations
or classifier personalization. The guard checks supported claims/definitions,
not unrestricted semantic/causal validity. Strict mode refuses unparsed
sentences; default mode retains a disclosed vague-sentence rate limitation.

Six actual assistant explanations pass strict checking: four train, two
validation. JSON is deterministically assembled, not a teacher completion.
Grouped dates retain 118 training, 30 validation and 38 test dates; actual pilot
examples exclude test dates. Controlled wording and all-Buy sources do not
establish class generalization, adequate QLoRA data, added explanatory content
or participant benefit. Phi-3-mini remains untrained.

Later comparison scores raw prompted/student/teacher output before gating and
emitted output separately. Measure numeric/directional/rank/vocabulary errors,
recall, unverifiable rate, retries/fallback and user interpretation. Preserve
evaluation freezes; do not tune on held-out results.

## Domain interpretation and remaining work

Indicator meanings and model effects differ. RSI describes momentum; MACD
histogram momentum components; SMA200 distance/Bollinger position price relative
to trailing statistics; OBV slope price-associated volume. SHAP describes use
by this fitted model, not a market cause. News dispersion is trailing variation
of session-average polarity, not disagreement among individual headlines.

The baseline uses fixed 16:00 New York cutoff even on half-days. Actual-close,
entry/availability and after-early-close policies need reconciliation. Audit
corporate actions, dividends, vendor revisions, source reliability/manipulation,
macro/company factors and regimes before broad timing/prediction claims.
Closest-work/novelty review, population-specific profile validation, social divergence,
multi-company evaluation, performance/serving parity, student adaptation,
production hosting and participant acceptance remain whole-FYP work.

## Multiclass and profile revision, 14 October 2026

The new temperature experiment retains the original model/trace bytes, fits one positive parameter on 181 earlier outcomes and preserves raw classes. Its upper-bound fit approaches uniform confidence (Brier about 0.6667), so it is a no-signal diagnosis: temperature reaches T = 1000 and Brier rounds to 0.6667, the constant one-third forecast. Frozen class counts are 40/51/95; refit 37/50/99. The primary UI abstains on insufficient confidence and rejects directional use of archived failed calibration. Complete tolerance scoring now has thirteen items plus five capacity questions; allowance controls confidence requirements without changing direction. CryptoBERT sanity probes produce positive/negative outputs; the neutral probe is negative. Reference labels remain unchanged and their single-pass construction is disclosed in the report methods.

## Audit revision: baselines, gates and explanation schedule

Saved `provenance.metrics` in both recovery01 engine modes gives XGBoost CV
macro-F1 **0.2843234954**, fold SD **0.0536851075**, and linear **0.2796068787**,
SD **0.0559261189**. The modes share this training CV result. On the final 186
cases, isotonic XGBoost is **0.2238095238** in both; linear frozen is
**0.1800094720**, refit **0.1896191338**. The **0.3182123510** frozen raw result
is a separate final-case score, not the six-fold **0.2843** CV mean.

Gate A remains partial: causal/unit controls and the centred canary are supported;
the one-session clean arm is PASS, but the five-session arm is BELOW_CHANCE,
not literal chance-level closure of the entire proposal gate. Gate B is not
passed: a small CV lift over linear and final-case isotonic improvement do not
establish the combined out-of-sample prediction/calibration conditions.

Real temperature records all remain Observe even at maximum allowance (50%
threshold versus about 33% confidence). Controlled 0.70-confidence fixtures
exercise the policy separately. The implemented explainer is a deterministic
template plus grammar-based verifier. Prompted LLM prose with constrained claims
is scheduled for Mid-2 / Iteration 3; QLoRA is Iteration 4.

C1 is the timing harness/permanent canary, C2 the deterministic verifier with
retained rejection and checked fallback, and C3 the planned preregistered
news/social divergence ablation. Novelty in imported sentiment/XGBoost/SHAP/QLoRA
and profit are not claimed. See report Chapters 2 and 5 for the primary-source
comparison, market formulas, LLM design and illustrative example.

Executed revisions: FinBERT `0bc2ac10dda6929bcb1f77ccc43c7ec5c424f031`,
CryptoBERT `9e37c910fe87727cb842a9ac55c6388256fe0f15`,
Cardiff `3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7`. Current publisher cards
state FinBERT weights CC BY-NC-SA 4.0, CryptoBERT MIT and Cardiff CC BY 4.0.
The recorded teacher family is OpenAI GPT-6, with no exact serving revision.
Phi-3-mini checkpoint and Mistral fallback are unselected; their candidate
publisher licenses do not imply a completed project run.
