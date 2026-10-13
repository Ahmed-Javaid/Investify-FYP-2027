# Investify: five-minute demonstration

Open **http://127.0.0.1:8507**. If it is not running, use the
[team guide's setup commands](MID1_TEAM_GUIDE.md#demo-setup). Keep the server
terminal open. This demonstration inspects a historical decision, applies a
risk profile, and catches a false explanation.

## 1. Choose the case and explain the decision

On **Overview**, click **Open the decision walkthrough**. Expand **Case
selection**, choose **Alpaca, multiclass calibration (frozen)** and session
**2023-12-21**. Then collapse the selector. On **Onboarding**, state the educational purpose, loss risk and that no trades are executed. Click **Next** to open **Decision**.

Say: **“A session is a stock-market trading day. We are loading NVDA's saved
decision for this date, predicting its next five trading sessions.”** Weekends
and holidays do not count. The study ends in December 2023 because this is the
recorded evaluation dataset; it is not today's market feed.

On **Decision**, show the three probabilities. Buy is about **33.34%**, Hold
**33.32%**, and Sell **33.33%**. Say: **“Buy is the largest raw class, but the
probabilities are almost equal. The application withholds a directional
recommendation.”** Calibration converts model scores into probability estimates;
these estimates do not establish accuracy or expected profit.

## 2. Show what entered the model

Open **Evidence → Technical analysis → MACD histogram**. Show the value
**0.0963** and contribution **+0.1874**.

Say: **“Technical analysis supplies numerical price and volume inputs. MACD
histogram measures momentum: the difference between the MACD line and its signal
line. SHAP explains how this fitted model used an input for this decision.”**
A positive contribution supports the raw Buy score; a negative one opposes it.
**+0.1874 is a model-score contribution, not 18.74% confidence or profit.**

The other technical inputs are RSI (recent price momentum), distance from the
200-session average, position within volatility bands, and volume trend.

Switch to **News sentiment → Headline count**: show **10** and contribution
**−0.1312**. Then select **Average headline sentiment**: **−0.1419**, contribution
**+0.0759**.

Say: **“FinBERT scores financial headline tone. Polarity is positive probability
minus negative probability. These aggregated inputs come from the most recent
prior completed news session. SHAP shows the model's response to them.”**
The slightly negative tone and positive contribution describe different things:
the text's tone and this model's learned response. This panel traces inputs;
it does not display a live news feed. Expand **All eleven feature values and
definitions** briefly if asked about coverage.

## 3. Demonstrate the risk profile

Open **Risk profile**. Click **Cautious example**, then **Higher-tolerance example**.
Show **R = 0 / required confidence 80%** versus **R = 1 / required confidence 50%**.

Say: **“Five capacity answers assess ability to bear loss; thirteen tolerance
answers assess willingness. The lower score, with additional restrictions,
determines R and the confidence requirement.”** These are fictional examples.
Both return **Observe**, because **33.34% is below both thresholds**. That is
expected. The profile changes the requirement; it does not alter probabilities
or reverse Buy into Sell.

## 4. Catch an incorrect explanation — the main demonstration

Open **Explanation check**:

1. Click **Check explanation**. The unchanged candidate should be accepted.
2. Click **Inject wrong probability**, then **Check explanation** again.
3. Show **Candidate rejected** and **Verified fallback emitted**. The replacement retains **Policy outcome: Observe**. The candidate
   falsely says **1.00%**; the independently checked replacement restores **33.34%**.
4. Edit the text: the old verdict becomes invalid. Finish with **Restore record
   facts → Check explanation**, leaving a clean accepted result.

Say: **“The checker compares the explanation the user sees with the recorded
facts. Correct structured data cannot hide a false number in its text. We reject
the contradiction and separately check the replacement.”** Changing the case,
profile or text invalidates its previous verification.

## What the six case choices mean

All six contain **the same 186 NVDA evaluation dates**, not six stocks.
Alpaca supplies market/news data; FNSPID is an alternative historical news corpus.

| Choice | Why it exists |
| --- | --- |
| **Alpaca, multiclass calibration (frozen)** | Main demo: corrected calibration preserves raw classes and exposes low confidence. “Frozen” means the fitted classifier/scaler stayed fixed through calibration and evaluation. |
| **Alpaca, multiclass calibration (refit)** | Comparison: classifier trained again offline on a later available training block, with earlier calibration transferred. Selecting it does not retrain. |
| **Fresh Alpaca, frozen classifier** | October rerun preserving the original calibration failure: every output became Buy. |
| **Fresh Alpaca, refit classifier** | The original refit comparison had the same all-Buy failure. “Fresh” means rerun recently on historical data. |
| **Archived Alpaca** | September Alpaca baseline, retained for comparison. |
| **Archived FNSPID** | Original corpus baseline; timestamp precision and ticker coverage motivated the source change. |

Stay on the first case during the main demonstration. The four older cases are
ineligible for directional suggestions. The temperature diagnostic preserves class order;
it does not establish useful predictive performance.

## If asked what runs live

**Profile scoring, confidence gating, explanation checks, rejection and fallback
run live.** Model fitting, headline scoring and predictions were recorded offline;
opening this demo does not call a language model or fetch current prices.

The optional **Experiments** screens show separate leakage, social-model and
teacher/student studies. FinBERT remains in the news core. CryptoBERT/Cardiff are
social-text comparisons; student adaptation and whole-FYP integration remain
later work. Use the [team guide](MID1_TEAM_GUIDE.md) for deeper questions and
member speaking assignments.
