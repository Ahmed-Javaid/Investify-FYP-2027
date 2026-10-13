# Local explanation pilot

The adapter, both explanation-interface connections, guarded evaluation command and labelled fixture tests are implemented. **No real local completion has been obtained in this session.** Fresh read-only model-list probes on LM Studio's default port 1234 and Ollama's 11434 returned no model identifiers. The inspected model-directory metadata names an old C: target. The E: LM Studio home now contains settings/backends, but the inspected E: AI-Tools weight search found only a bundled embedding GGUF, which cannot serve this chat-explanation task. These observations do not prove every service failure's cause or rule out models elsewhere. No global links/settings were changed.

## Contract and comparators

The generator receives a saved decision, all technical/news evidence, the maintained glossary and a supported reference explanation. It returns JSON with `text` and `payload`. Under contract `mideval-complete-evidence-v4` and prompt `mideval-local-complete-evidence-v2`, the pilot requires every feature's value/contribution/direction/target, family totals, maintained definitions and attribution scope in both prose and JSON. Unknown fields, contradictions, missing disclosures and unsupported sentences fail. Missing feature values remain null/"missing"; zero contributions are neutral.

This constrained contract permits supported factual, all-feature, family-total and maintained-definition sentences. It does not accept arbitrary paraphrases or certify semantic truth. The glossary still needs independent content review. The numeric top-k template and the complete guided template are separate comparators: giving richer evidence only to an LLM would make a claimed benefit ambiguous. Human comprehension and any advantage of a real generator remain unmeasured. The larger dual-representation response has a 4,096-token ceiling; truncated responses are retained and rejected.

The adapter records raw output, including truncated/failed attempts, requested and reported model identifiers, completion finish reason, elapsed time, returned token counts, prompt hash and verification. It makes at most two generation attempts for bad output, fails fast on service unavailability, and then verifies the deterministic guide. Network/model failure is visibly labelled. No fixture generator is available in the evaluation CLI.

## Run when a model is available

Use an already available local model and its exact provider identifier. The local service must support the documented chat-completions and JSON-schema format. The pilot defaults to `http://127.0.0.1:1234/v1` and rejects remote URLs. These instructions do not install/download/load a model.

```powershell
python -B scripts/probe_local_llm.py --output ../evidence/local_llm_probe.json
python -B scripts/evaluate_mideval_llm.py --plan-only --output ../evidence/explainer_evaluation_plan.json
python -B scripts/serve_mideval_demo.py --llm-model "available-model-id"
```

Replace the model placeholder with an actual identifier. For Streamlit, its optional configuration reads `INVESTIFY_LLM_MODEL` and `INVESTIFY_LLM_BASE_URL` from the environment. If local authentication is enabled, all entry points read the optional `INVESTIFY_LLM_API_KEY`; it is never a command-line value or a reported evaluation field. Keep credentials out of source, chat and evidence.

The default, unconfigured demo still provides a verified deterministic explanation and makes no model request. Operator configuration means a model was requested, not that its connection or quality has been established.

## Frozen evaluation

The current artifact selection separates 148 development sessions and 38 held-out sessions per corpus. Six held-out sessions per corpus are selected deterministically. This is a prompt/generation study over saved prediction-evaluation records, not a new train/test split for the predictor.

Use development records for prompt/model investigation. Real evaluation requires the saved plan to match the current data, selection and source hashes before any provider call:

```powershell
python -B scripts/evaluate_mideval_llm.py --model "available-model-id" --plan ../evidence/explainer_evaluation_plan.json --output ../evidence/llm_evaluation.json
```

Code/data changes require a deliberate new declaration and version/evidence review, rather than silently reusing a stale plan. Results retain first-attempt failures, retries, accepted generations and fallback. A partial run is labelled. Zero real completions produces `blocked`, null quality metrics and a nonzero CLI status; successful template checks are not presented as LLM performance.

The current plan-only and unavailable-model reports have zero completions. Tests with provider fixtures validate behaviour and are labelled as such; they do not enter the real evaluation files.

## Source documentation

[LM Studio structured output](https://lmstudio.ai/docs/developer/openai-compat/structured-output), [chat completions](https://lmstudio.ai/docs/developer/openai-compat/chat-completions), and [local authentication](https://lmstudio.ai/docs/developer/core/authentication) were checked on 11 October 2026. JSON schema constrains format; the project verifier separately checks recorded facts. Actual checkpoint identity, access/license conditions and performance remain pending available runtime/model access.
