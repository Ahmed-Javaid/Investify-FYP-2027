# Official publisher models

The user's 12 October instruction requires original publisher models. Use publisher-issued instruction models and publisher-issued quantizations; exclude third-party fine-tunes and behaviour-modified variants. Previous variant experiments, comparison outputs and derived PDF have been removed from the working package. Their scores are withdrawn and must not be attributed to a replacement model. Original external model files and the 224 protected project files are preserved.

The replacement primary explainer is [Qwen's Qwen2.5-7B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF), with [official Qwen3-8B-GGUF](https://huggingface.co/Qwen/Qwen3-8B-GGUF) as a supplementary sentiment comparator. Both use publisher Q5_K_M quantizations under Apache 2.0. These are two models from the same publisher, not an independent-provider annotation check. The frozen OpenAI/Codex AI reference labels are preserved separately.

The checked [catalog](../code/artifacts/mid_eval/official_model_catalog.json) records canonical publisher repositories, full revisions, file SHA-256 pointers and sizes. Qwen2.5 requires both original split shards (5,444,831,360 bytes total); Qwen3 requires its single 5,851,112,224-byte file. A reviewed repository name or serving alias alone is insufficient. Acquisition must first recheck **every pointer at the pinned revision**, then downloaded bytes must match every SHA-256 and size. The web tool read pointer metadata at `main` and repository revision pages; it could not retrieve the full-revision raw/blob URLs. No pinned-revision acquisition or official local inference is claimed yet.

Actual inference runners now require an official runtime receipt and recheck all local bytes before making requests. Unit fixtures are explicitly marked and cannot enter the command-line research comparison. Changing weights, prompt, code, held-out selection or publisher identity requires a new study plan. The 117 usable AI references and 24 held-out post identities stay frozen. CryptoBERT/Cardiff classifier inference remains a separate pending study.

From `code`, acquire through an ordinarily available network without changing restrictions:

```powershell
python -B scripts/acquire_official_model.py --model-key qwen25 --download --directory E:/AI-Tools/Temp/investify-official-models/qwen25 --output ../evidence/official_qwen25_acquisition_NEW.json
python -B scripts/verify_official_model.py --model-key qwen25 --directory E:/AI-Tools/Temp/investify-official-models/qwen25 --output ../evidence/official_qwen25_runtime_NEW.json
```

Run `qwen3` separately with its corresponding directory/receipt. Keep download/cache files on E:. Failures are retained without fabricated completions or scores. The local generation study tests record compatibility and AI-reference agreement; it does not establish comprehension benefit, independent human accuracy, investor suitability or prediction quality.

The actual Qwen2.5 acquisition attempt is [retained](../evidence/official_qwen25_acquisition_20261012.json): connection refused (WinError 10061), zero pointer checks completed, no weight files downloaded. No altered proxy configuration or alternative model identity was used. The replacement model choice follows the user instruction after earlier exploratory outcomes had been seen; it is not a first-ever preregistration. The original reference freeze is unchanged, and the prompt/held-out set must not be tuned using replacement outcomes.

Launch verified local files with the declared installed backend:

```powershell
powershell -File ../tools/start_official_model.ps1 -ModelKey qwen25 -Directory E:/AI-Tools/Temp/investify-official-models/qwen25 -Receipt E:/Uni_Stuff/FYP/GPT_MIDEVAL/evidence/official_qwen25_runtime_NEW.json
python -B scripts/evaluate_mideval_llm.py --model investify-official-qwen25-q5km --base-url http://127.0.0.1:1235/v1 --timeout 45 --plan-only --output ../evidence/explainer_evaluation_plan_official_NEW.json
```

Use that exact model identity and frozen plan for the actual explanation command in `code/docs/local_llm_pilot.md`. Run only one model server at a time on the current 10 GiB GPU. The supplement uses the existing hard-label prompt and shared temperature-zero decoding; Qwen3 is explicitly launched in non-thinking mode. This differs from its publisher's general non-thinking sampling recommendation and must be reported, not presented as optimal Qwen3 performance.
