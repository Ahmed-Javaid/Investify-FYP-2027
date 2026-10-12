# Investify domain research and design notes

The initial review connects definitions to the actual feature code. It supplies the educational glossary for the first explanation increment. The broader stock-market research requested by the panel remains a planned deliverable.

## Technical features

RSI summarizes recent price momentum; it is not a rule that guarantees a reversal. The implementation uses fourteen-session rolling average gains/losses. [Fidelity RSI guide](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/rsi)

The MACD histogram is the MACD line minus its signal line. A recorded positive indicator and a positive SHAP contribution are different quantities: the former describes the input, while the latter describes how the model used it for the selected class. [Fidelity MACD guide](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/macd)

The code's SMA feature is relative distance from a trailing two-hundred-session mean. Bollinger position locates the close within trailing bands based on a mean and standard deviation. Neither feature independently establishes why a stock price moved. [SMA guide](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/sma), [Bollinger Bands guide](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/bollinger-bands)

OBV adds volume on rising closes and subtracts it on falling closes. The feature here is its average change over fourteen sessions. It is different from headline count and the news-attention z-score. [Fidelity OBV guide](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/obv)

## Sentiment and transparency

FinBERT classifies financial text; the pipeline transforms its class probabilities into headline polarity. This measures the text's sentiment, not the truth of the news, future returns, or the user's suitability for a trade. [Provider model card](https://huggingface.co/ProsusAI/finbert)

The feature named `dispersion` is a trailing standard deviation of session-average polarity. Calling it disagreement among individual headlines would misdescribe this implementation. The first explanation increment uses the code's actual definition. Its news aggregates are backward as-of joined; the decision record does not store the exact contributing news-session timestamp, so the explanation must not invent that date.

Investor.gov cautions against relying on AI-generated information to predict securities prices and describes how false online promotions can influence investment behavior. The design implication is explicit uncertainty, coverage, and source disclosure, without guaranteed-return language. [SEC/NASAA/FINRA investor alert](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-alerts/artificial-intelligence-fraud)

## Market mechanics added to the working review

Stocks are ownership interests, with potential capital appreciation and dividends. Company-specific and broader market events can affect price. The design implication is to describe what the actual technical/news inputs contain rather than present them as a complete valuation or a proven cause of a move. Corporate actions, macroeconomic variables and regimes still need dedicated review. [SEC stock overview](https://www.investor.gov/introduction-investing/investing-basics/investment-products/stocks)

NYSE documentation distinguishes regular sessions from early closes and holidays. Calendar-date matching is insufficient for the project's decision-time contract. The actual calendar/cutoff implementation and proposal wording still need reconciliation before a broad correctness claim. [NYSE holidays and trading hours](https://www.nyse.com/trade/hours-calendars)

The research chapter now compares financial sentiment, integrated news/price data, TreeSHAP, and explanation consistency using primary abstracts and the provider model card. It distinguishes record-consistency checking from universal semantic or causal faithfulness. This is a preliminary review, not a systematic novelty finding or a closed PF-09 action.

## Research still to complete

Corporate-action review now includes a concrete design implication. [NVIDIA's official 2021 split FAQ](https://investor.nvidia.com/files/doc_downloads/doc_faq/06/21/NVIDIA-2021-Stock-Split-FAQ.pdf) describes its four-for-one split and trading on that basis from 20 July 2021. In an arithmetic illustration, one share at 100 units becoming four at 25 preserves 100 units of value; the apparent −75% per-share price change is not itself a −75% investment loss. These illustrative numbers are not measured NVDA prices.

[Yahoo's adjusted-close help](https://in.help.yahoo.com/kb/adjusted-close-sln28256.html) describes adjustment for splits/distributions; [yfinance's download documentation](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html) distinguishes client adjustment and action retrieval. The actual project calls `auto_adjust=False, actions=False` and uses provider `Close`/`Volume`. This is not sufficient evidence that the provider's historical fields are unadjusted as-traded prices. The earlier ingest docstring overstated that assumption and has been corrected without changing processing. Retain/audit raw snapshots, corporate actions, adjusted/unadjusted field definitions, volume basis and acquisition/version metadata before reproducing labels/indicators. The missing raw price snapshot prevents that audit here; no correction or causal explanation of classifier collapse is claimed.

The actual calendar module deliberately applies a fixed 16:00 New York cutoff even on half-days and timestamps price bars at 16:00. This is an explicit baseline simplification, not a verified actual-close policy. The decision time, price availability/entry convention and after-early-close news treatment must be reconciled with the proposal and evaluated together before changing scientific results. Existing artifacts remain unchanged.

Still open: a raw-data corporate-action audit and agreed calendar/entry policy; earnings/fundamentals; interest-rate/macroeconomic factors; liquidity/volume; source reliability/manipulation; regimes; prediction horizons; and deeper attribution/association/causation comparisons. Each needs referenced findings, a worked example and a design/evaluation implication. This preliminary review does not close PF-09.
