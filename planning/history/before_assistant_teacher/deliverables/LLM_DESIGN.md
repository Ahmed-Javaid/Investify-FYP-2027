# Investify LLM explanation design

The LLM's task is to make recorded technical and sentiment evidence understandable to a retail user. The prediction engine produces the class probabilities and decision; the LLM communicates the result, the evidence, conflicts, and limitations.

## Input and user benefit

`build_context` supplies the company, recorded session, horizon, class probabilities, feature values, complete SHAP vector, reviewed feature meanings, model reference, source/register coverage, and limitations. Unlike the old top-k template, the input covers all technical and news features. It contains no invented social observations or claimed risk conditioning.

The desired explanation answers: what the important technical signals measure; what the news evidence says; which recorded features support or oppose the selected class; what evidence conflicts; and how much the prediction and data support the conclusion. Less influential features can be available as detail rather than promoted to decisive causes.

## Implemented constrained output contract

The supported-claim verifier now checks the actual displayed text independently of its JSON, includes feature-value/attribution-target checks, requires essential displayed claims, and rejects known contradictions. Strict mode rejects sentences outside the supported template grammar. This is the checked baseline for a future generator, not evidence that arbitrary LLM prose is already supported. A broader educational-language contract still needs design and held-out generation evaluation.

The generator should return user-readable sections plus atomic claims linked to record fields. Verification must check the actual prose as well as the structured claims. A correct payload alongside contradictory prose is a failure. Reviewed background definitions need a separate content policy; a numeric matcher cannot certify arbitrary market explanations.

Failure behavior is bounded retry followed by verified deterministic fallback. Model unavailability/timeout also displays that state. An LLM must not change a recorded decision, promise returns, conceal missing inputs, equate SHAP with a market cause, or describe the separate prototype risk comparator as personalization of the saved classifier.

## Evaluation and schedule

Compare the existing template with a prompted model on the same held-out records. Evaluate raw generations for numeric, directional, rank, feature-vocabulary, coverage/recall, and unverifiable-claim errors; also test emitted outputs after gating. Add user tasks checking interpretation of drivers, uncertainty, and limitations. Preserve the constant-Buy model caveat in both configurations.

The proposal names Phi-3-mini for later QLoRA adaptation and an unspecified open-weight teacher. The current pilot now selects Qwen's original Qwen2.5-7B-Instruct-GGUF at a pinned publisher revision with Q5_K_M quantization. Both original shards must match the publisher SHA-256/size pointers before inference. Official weights remain unavailable locally; no replacement generation-quality result is claimed. The adapter, interface connections, bounded retries/timeouts, failed/truncated output retention and complete maintained-definition gates are implemented. QLoRA and teacher/student comparison remain later proposal work; the user instruction excludes third-party fine-tunes and behaviour-modified variants from current workings. See [the official model policy](OFFICIAL_MODEL_POLICY.md).

The current V4 contract additionally requires every feature's value/contribution/direction/target, family totals, all reviewed definitions and attribution scope in prose and JSON. Missing values remain missing and zero contributions neutral. Non-top-k features carry descriptive evidence without a headline rank. This is a constrained compatibility pilot, not unrestricted semantic faithfulness. The fair comparators are the numeric top-k template and the complete guided template with identical richer evidence. Matching frozen selection/data/code hashes are mandatory before real evaluation; zero completions receive no fabricated quality score. See `code/docs/local_llm_pilot.md`.
