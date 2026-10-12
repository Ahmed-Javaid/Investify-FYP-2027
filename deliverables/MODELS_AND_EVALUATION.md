# Investify model and evaluation inventory

## Active teacher and student

Current assistant session: actual teacher, six accepted controlled-prose examples with null exact serving identity/revision. Phi-3-mini: planned local student, exact Microsoft checkpoint and training setup pending. Original and QLoRA-adapted student comparison is unexecuted. Four training/two validation examples are a construction pilot, with factual JSON targets assembled from original records and disclosed separately. Earlier Qwen pilot selections below are inactive. See ASSISTANT_TEACHER_PILOT.md.

Local generative-model policy: original publisher models and publisher-issued quantizations only; any later project-trained adapter must be disclosed separately. Earlier Qwen2.5/Qwen3 official replacement experiments are inactive optional configurations, not the selected teacher/student workflow. Their acquisition failed before weights arrived and they have no replacement inference scores. Earlier variant outcomes were removed and withdrawn. See [the official model policy](OFFICIAL_MODEL_POLICY.md).

## Components and status

| Component | Role | Current status |
| --- | --- | --- |
| `ProsusAI/finbert` | English financial-news sentiment classification; cached positive, neutral, and negative probabilities. The code derives polarity as positive minus negative probability. | Implemented in the historical spike. The [provider model card](https://huggingface.co/ProsusAI/finbert) documents its financial sentiment task. |
| CryptoBERT or a social-domain alternative | Candidate equity social-post sentiment model. | AI references acquired/annotated; candidate inference pending; a final checkpoint has not been selected. |
| XGBoost | Team-trained classifier over technical/news features. | Stored predictions exist. The current calibrated evaluation records all predict Buy. |
| Isotonic calibration | Maps scores to estimated class probabilities. | Implemented, with documented classifier collapse. Brier improvement alone is insufficient evidence of usefulness. |
| TreeSHAP | Attributes the raw predicted-class model score to features. | Stored vectors validated for additivity; these do not decompose calibrated probability. |
| Deterministic template and verifier | Produces and checks the baseline explanation; provides fallback. | Implemented. Twenty selected existing tests pass in the current validation runtime. |
| Complete guided template/verifier | Every feature contribution, family totals, meanings and raw-score scope in prose/JSON. | All 372 records pass; unknown, missing, contradictory or unsupported claims fail the constrained generation contract. |
| Prototype risk-dependent linear comparator | Blends technical/news z-scores using an explicit reconciled profile beside fixed R=0.5. | Separately fits 148 earlier saved rows and scores 38 later rows per corpus; arithmetic tested, suitability/predictive performance unvalidated. |
| Prompted LLM | Attempts the same complete-guided contract. | Adapter/evaluation plumbing implemented; actual checkpoint/runtime and real-generation evaluation pending. |
| Current assistant teacher | Supplies recorded explanation examples under the user-directed change from the proposal's open-weight teacher assumption. | Six actual controlled-prose examples accepted; exact serving revision unavailable. Construction/provenance demonstrated; added explanatory content and comprehension benefit unestablished. |
| Phi-3-mini and QLoRA | Planned local explainer, later adapted on verified examples and compared with the original student and teacher. | Exact Microsoft checkpoint, student inference, training and comparison remain pending. |

## Evaluation matrix

| Area | Measurements | Acceptance or reporting rule |
| --- | --- | --- |
| Prediction | Macro-F1 and class precision/recall; compare stratified-random and transparent linear baselines. | Held-out walk-forward protocol; report null and below-chance results honestly. |
| Calibration | Brier score, reliability curves, class distribution. | Report calibration and classification behavior together. |
| Explanation | Numeric fidelity, directional consistency, recall, unverifiable rate; rank/vocabulary errors; fault detection and false positives. | Existing targets: >= 0.98, >= 0.95, >= 0.80, <= 0.15 respectively. Definitions must agree between report and code. |
| Sentiment | Agreement and proposed macro-F1/per-class measures against model-generated equity-social reference labels; independent human validation unmeasured. | Select empirically; use declared news-only fallback if transfer is inadequate. |
| Leakage | Causal join/window/scaling tests, control lift and intervals, deliberate fault detection. | Distinguish leakage, chance-level behavior, and below-chance predictive performance. |
| User understanding | Interpretation of decision, drivers, uncertainty, and limitations; task completion/time/assistance. | Pilot and later participant study, with actual consent and recorded observations. |
| Runtime | Applicable latency, memory, throughput, reproducible setup and deployment checks. | Record measured environment; planned NFR bounds are not completed measurements. |

## Evidence from this increment

The selected suite has 212 passes and no skips, including 20 actual Streamlit widget tests; all 372 records/numeric/complete-guided templates validate. The live endpoint exercise passes 62 checks. Separate comparator evidence records 228 arithmetic probes on actual held-out rows and three labelled profile scenarios. SHA-256 hashes identify source/data. These scenarios are not participant profiles and have no outcome-performance metric.

Contract `mideval-complete-evidence-v4` checks text/JSON independently and rejects known contradictions. Top-k recall retains the V2 visible numeric/target slots; generated output additionally requires all-feature, family, definition and scope coverage in both sources. Metrics are not directly identical to historical payload-first results. Strict mode rejects unparsed sentences; default mode retains vague-sentence acceptance under the rate threshold. No arbitrary-prose semantic verification is claimed.

The full scientific suite, locked training environment, live model inference, student quality and cloud deployment are not validated by those checks. Six recorded assistant-teacher generations exist separately; they do not demonstrate student inference or training. No new predictive-performance figures are claimed.
