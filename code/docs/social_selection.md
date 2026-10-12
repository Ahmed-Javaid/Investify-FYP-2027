# Equity-social study with declared AI or human references

The actual pilot contains **200 real MSFT tweets**, one AI annotation pass, **117 usable references** (31 positive, 67 neutral, 19 negative), and 83 explicit exclusions. Candidate classifiers have not run; quality metrics remain null. See [the pilot report](../../deliverables/AI_SENTIMENT_PILOT.md) for acquisition, actual raw labels and limitations. Unit fixtures remain separate.

## Current receipt-bound execution

Use [the V4 runbook](../../deliverables/SOCIAL_V4_RUNBOOK.md) for actual research inference/comparison. V3 source modules and their original plan stay byte-preserved as the reference parent. Production CLI calls now require publisher-byte and receipt gates; standalone probabilities or test-purpose bundles cannot be scored as actual candidate outcomes. The V4 catalog remains incomplete and its declaration is blocked. A separate Python 3.13 CPU runtime imports original existing packages read-only; genuine weights/config/tokenizer metadata remain missing. Older V3 commands below document the preserved protocol and no longer bypass the current research gate.

## Protocol and provenance

The evaluator expects protocol: mideval-equity-social-selection-v3, selection, and posts. V2 frozen plans are historical and cannot be reused under changed source hashes. Both two_independent_humans and model_generated are supported.

Selection retains sampling_rule, access_conditions_reference, annotation_method, target_tickers, and explicit UTC window_start_utc/window_end_utc/declared_at_utc/acquired_at_utc. Declare sampling before acquisition. Retain at least 200 acquired selected posts including exclusions. Each post keeps post_id, source, source_kind (reddit/stocktwits/x/other_social), source_url, published_at_utc, ticker and exact text. Target/window, duplicate IDs/normalized target-text pairs, chronology and social source kind are checked. Exact deduplication leaves some near-duplicates and retweets; news headlines cannot substitute for social posts.

The human method retains different annotator_a_id/annotator_b_id, separate annotator_a_label/annotator_b_label, and UTC annotated_a_at_utc/annotated_b_at_utc. Identity checks do not authenticate real/independent people.

The AI method requires selection.annotation_runs: one initial run and at most one optional cross-check. Each retains run_id, provider, model_id, explicit model_revision (null when unavailable), identity_source (provider_reported/session_configuration/operator_declared), identity_evidence, prompt_version, full prompt, matching UTF-8 prompt_sha256, raw_output_reference, UTC run_started_utc/run_completed_utc, input_contract: ticker_and_original_text_v1, and candidate_predictions_visible: false.

Each post's model_annotations retains one entry per run: run_id, label, reason, raw_response, input_sha256 and annotated_at_utc. Input hashes cover canonical ticker plus original text. Raw structured label/reason must match the annotation; timestamps fall inside the run. Human-style fields cannot disguise AI labels. Identities/blindness are declared, not authenticated. Same-model repeated passes do not imply independence.

Labels are positive/neutral/negative/exclude. Disagreements require adjudicated_label, adjudication_note and adjudicated_at_utc after initial labels; AI disagreements also declare adjudicator_id. Raw initial labels stay unchanged. Unanimous labels cannot be silently overridden. Exclusions require exclusion_reason; usable posts cannot carry it. Single-pass agreement/kappa are null; two-pass agreement explicitly measures AI-pass agreement.

## Blinded session import

investify.sentiment_annotation.packets emits only post ID, ticker and original text, binding each packet to the unannotated corpus hash. The full versioned prompt defines sentiment/ambiguity and treats posts as untrusted data. prepare_stocknet_pilot.py verifies original Git blobs and prepares the declared chronological first-200 sample without labels or prices.

import_session_annotations.py imports actual retained batches, checks exact packet/post coverage, preserves responses/hashes, validates the reference and refuses to overwrite research outputs. The importer makes no API calls or labels. The assistant generated the current four raw batches in this session. Per-post timestamps mean batch-file persistence times; model latency is unmeasured. Copied/archive-extracted batches replay original hash-bound persistence receipts rather than treating their new filesystem times as annotation times. The handoff's declared GPT-6.1 Sol configuration is recorded with exact serving identity/revision unavailable.

## Freeze and evaluation

Freeze with evaluate_social_study.py --freeze --benchmark artifacts/mid_eval/social_benchmark.json --checkpoints artifacts/mid_eval/social_candidates.json --output artifacts/mid_eval/social_selection_plan.json. Candidates require model_id, exact 40-character hexadecimal revision and preprocessing.

The plan hashes benchmark, evaluator/inference source and candidates. It sorts usable posts by publication timestamp/post ID, then assigns the first floor(4N/5) to development and the rest held out. Current split: **93 / 24**, with 7 positive, 15 neutral and only 2 negative held-out references. This is exploratory. The plan preserves annotation/candidate identities separately and discloses exact-name overlap; no match proves independent training or absence of aliases/shared models. Public historical posts may occur in pretraining. MSFT references cannot establish NVDA-specific transfer.

Each actual run names checkpoint/preprocessing, matching plan/benchmark hashes, UTC start/completion after freezing, and probabilities or explicit per-post failures. Failed/missing outputs never become neutral. Changed data/code/candidates invalidate the plan. Partial runs have null metrics; paired comparison requires every declared candidate on exactly the held-out IDs. Complete runs report macro-F1, per-class precision/recall/support and confusion matrices against the declared reference. Macro averages all three classes, zero denominators contribute zero, and probability ties use positive/neutral/negative order. Raw outputs and ties remain visible.

The current social_model_runs.json array is empty. Scores against these references would measure **agreement with AI labels**, not independently human-validated accuracy, return prediction or suitability. Benchmark leaders are not a deployment choice; adequacy/fallback criteria and review remain pending.

## Offline inference

run_social_inference.py requires an existing snapshot named by the exact revision, complete Safetensors classification-head weights, and PyTorch/Transformers. Downloads, remote code and stored-token use are disabled. It retains versions, file hashes, logits, processed-text hashes, token/truncation counts and timings, and rejects missing/randomly initialized heads. Preprocessing is a JSON string with text_policy (raw/tweet_mentions_urls), max_length (8..512), and explicit three-class label_mapping for indices 0/1/2. Whole-post sentiment remains a baseline for the target-specific task.

[CryptoBERT's pinned revision](https://huggingface.co/ElKulako/cryptobert/commit/9e37c910fe87727cb842a9ac55c6388256fe0f15) has a published Safetensors variant, absent locally. The [Cardiff snapshot](https://huggingface.co/cardiffnlp/twitter-roberta-base-sentiment-latest/tree/3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7) lists pickle/TensorFlow weights without Safetensors. A verified compatible conversion needs its own identity and a refrozen plan. The runner's restriction has not been weakened. Shell downloads are restricted and active environments lack PyTorch/Transformers.

The Streamlit Social Study tab shows actual reference counts/method, single-pass agreement status, model-identity caveats and pending/partial inference. Social sentiment remains absent from the saved stock classifier.
