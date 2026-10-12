# Actual AI sentiment reference pilot — 12 October 2026

The assistant annotated **200 real MSFT tweets in one session pass: 117 usable references and 83 explicit exclusions**. No candidate classifier ran; quality metrics/model selection remain absent.

## Reference evaluability

The [unchanged-reference audit](../evidence/reference_evaluability_20261012.json) examines the frozen 93-development/24-held-out set without candidate inference. Selecting the majority label from development gives a neutral comparator with 15/24 exact AI-reference agreement and macro-F1 0.256410; positive/negative recall are zero. High raw agreement can therefore conceal failure on directional classes. This is a deterministic reference comparator, not candidate inference or independent human accuracy.

One held-out prediction changes exact agreement by 4.17 percentage points; negative recall has 50-point increments because only two negative references exist. No pair meets token-set Jaccard 0.8 with at least five distinct tokens after the disclosed normalization. This heuristic does not establish independence, rule out shared news events or exclude pretraining overlap. Texts, labels and split bytes are unchanged. Official replacement studies remain pending under [the model policy](OFFICIAL_MODEL_POLICY.md).

| Reference | Acquired posts | Development | Held out |
| --- | ---: | ---: | ---: |
| Positive | 31 | 24 | 7 |
| Neutral | 67 | 52 | 15 |
| Negative | 19 | 17 | 2 |
| Exclude | 83 | — | — |
| Usable total | 117 | 93 | 24 |

The author-released [StockNet corpus](https://github.com/yumoxu/stocknet-dataset), associated with [Xu and Cohen (ACL 2018)](https://aclanthology.org/P18-1183/), supplies original Twitter IDs/text/timestamps. Source revision: 330708b5ddc359961078bef469f43f48992fd6e4. NVDA was absent from its directories; stocknet_source_access_v2.json amended the target to MSFT **before tweet-content acquisition**. No contents were acquired under the original NVDA declaration.

The rule selected the first 200 unique IDs/normalized target-text pairs chronologically in 2015. Fifty-one daily files cover 1 January to 24 February, and their preserved bytes pass original Git blob checks. Metadata-ordered fetching prefetched 90 files/350 rows; only the earliest qualifying daily prefix was retained. Preparation logs keep exact duplicates and last-day rows beyond the first-200 cutoff. No candidate, sentiment-tag or later-return filtering chose the sample.

Original text remains exact, including retweets, truncation, HTML entities, URLs and ambiguity. Many posts are promotions, stock lists or about another company. The assistant saw only target/text pairs and did not expand links. Exclusions retain their texts/reasons. These are one model's judgements, without independent verification.

The run declares OpenAI/Codex and GPT-6.1 Sol from the handoff's session configuration. The assistant system describes an agent based on GPT-6; no provider identity endpoint or exact serving revision is exposed. Identity provenance is session_configuration, revision null, and that limitation is recorded. The full prompt/version/hash, corpus/packet/per-post input hashes, run timing and four raw response batches are retained. Per-post timestamps record batch-file persistence time; model latency is unmeasured. Human identities/labels/reliability were not invented. Single-pass agreement/kappa are null.

The label freeze precedes the candidate plan. Candidates are CryptoBERT revision 9e37c910fe87727cb842a9ac55c6388256fe0f15 and Cardiff latest revision 3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7, with declared preprocessing/mappings and 128-token ceilings. These are inspected published identities, not executed local checkpoints. CryptoBERT weights and PyTorch/Transformers are absent. Cardiff's inspected snapshot lacks the Safetensors format required by this runner. Shell external downloads are restricted. A real CryptoBERT runner attempt retained a blocked receipt and created no run output.

The 24 held-out references, especially only two negatives, support exploratory comparison. A majority-neutral comparator has calculated macro-F1 0.25641025641025644 under the evaluator's convention; this is **reference-distribution arithmetic, not a candidate-model score**. Near-duplicate promotions/retweets, one ticker/short historical interval, subjective exclusions, unverified pretraining overlap and whole-post candidates versus target-specific references limit interpretation. A model-name mismatch does not authenticate independence. These references cannot establish human-validated accuracy, NVDA transfer or equity-return prediction.

Artifacts:

- code/artifacts/mid_eval/social_benchmark.json: all 200 original selected posts, initial raw AI labels and exclusions.
- evidence/social_pilot/msft_stocknet_unannotated.json and preparation_receipt.json: source inputs, exact byte checks and preparation exclusions.
- evidence/social_pilot/blinded_packet_01..04.json and raw_labels_batch_01..04.json: actual blinded inputs and assistant-generated responses.
- evidence/social_pilot/annotation_run_started.json, annotation_run_completed.json and annotation_freeze_receipt.json: prompt, identity/timing and label freeze.
- code/artifacts/mid_eval/social_candidates.json, social_selection_plan.json and social_model_runs.json: candidate identities, frozen split and empty actual-output array.
- evidence/social_pilot/candidate_comparison_pending.json and cryptobert_inference_blocked.json: null candidate metrics and actual blocker.
- sources/stocknet: author README/MIT notice, original retained daily files and acquisition manifest. Repository licensing does not authenticate third-party tweet rights. No public redistribution or platform rehydration is performed.

Next: restore genuine weights/runtime and a verified compatible Cardiff conversion/snapshot; refreeze if its identity changes, then execute both declared candidates and retain all outcomes. Optional independent AI cross-check/human review can strengthen references; 200 human labels are not assumed. A larger sample needs a new declaration and separate benchmark. Do not change this pilot after seeing candidate outcomes.

## Continuation runtime and receipt gate

The separate CPU classifier import runtime is now verified through the existing Python 3.13 base and unchanged E: packages: Torch 2.12.0+cpu, Transformers 5.12.1, Safetensors 0.8.0 and Tokenizers 0.22.2. The viewer still lacks these libraries and the Python 3.11 scientific lock is not restored. No model loading/inference occurred. Original weights and complete config/tokenizer byte provenance remain missing, and normal pinned metadata requests still returned connection refused.

[SOCIAL_V4_RUNBOOK.md](SOCIAL_V4_RUNBOOK.md) documents a separately versioned receipt/publisher-byte wrapper around unchanged V3 source/plan and reference identities. The actual catalog is metadata_incomplete, so its new freeze attempt is blocked with no output/model score. Standalone probabilities cannot enter a research comparison without a matching actual-purpose bundle and per-post logit/token/text provenance. Hash binding is self-consistency, not execution attestation. A small actual CPU tensor fixture verifies lossless serialization code; no original Cardiff weights were converted. All earlier raw/source/label/freeze evidence is preserved.
