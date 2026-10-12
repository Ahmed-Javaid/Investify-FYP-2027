# Receipt-bound original-publisher social study

V4 wraps the preserved V3 source/plan; original texts, AI labels, candidates/preprocessing and 93-development/24-held-out identities remain unchanged. Hash/receipt binding establishes reproducible self-consistency and original bytes, **not independent execution attestation**. There is no real candidate output or score yet.

## Current prerequisites

The CPU classifier imports are verified in [the guarded Python 3.13 receipt](../evidence/background_classifier_py313_runtime_20261012.json): Torch 2.12.0+cpu, Transformers 5.12.1, Safetensors 0.8.0 and Tokenizers 0.22.2 read from an unchanged E: environment. Its old launcher is broken; use the existing base interpreter and process-local wrapper, without repair/copy/install. This does not restore the Python 3.11 scientific lock, CUDA training or a student model.

Original snapshots and exact config/tokenizer byte provenance are still missing. The [catalog](../code/artifacts/mid_eval/social_publisher_catalog_v4.json) is explicitly `metadata_incomplete`; a [new declaration attempt](../evidence/background_social_v4_declaration_20261012/failure.json) correctly remains blocked. Normal pinned metadata fetches on the recovered interpreter still fail with connection refused; proxies/settings were not changed.

The pinned [CryptoBERT publisher pointer](https://huggingface.co/ElKulako/cryptobert/blob/9e37c910fe87727cb842a9ac55c6388256fe0f15/model.safetensors) provides SHA256 `fe34ba09b3d701ff2b4ee69205e42c8143fcee1f89fe3a0cf10444988634a3c9`. The read-only review reported original Cardiff BIN SHA256 `4d24a3e32a88ed1c4e5b789fc6644e2e767500554e954b27dccf52a8e762cbae` at [the pinned original file](https://huggingface.co/cardiffnlp/twitter-roberta-base-sentiment-latest/blob/3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7/pytorch_model.bin); this task's direct fetch was unavailable. Exact sizes stay null until actually measured/obtained. Rendered config/tokenizer page text was not converted into invented byte hashes.

## Gates and commands when genuine files exist

`sentiment_receipts.py` checks pinned original model identity, used config/tokenizer/weight closure, local bytes before/after inference, current V4/V3/benchmark hashes and exact held-out receipt details. Comparison recomputes preprocessing/text hashes and softmax probabilities from retained logits, checks token/truncation/timing, and refuses missing/swapped/stale or test-purpose receipts. The production CLI has no fixture backend option. Failures remain failures with null partial metrics; complete pairing is required.

From `code`, reserve a new directory for every operation:

```powershell
python -B scripts/social_study_v4.py --freeze --catalog artifacts/mid_eval/social_publisher_catalog_v4_COMPLETE.json --output-directory ../evidence/social_v4_freeze_NEW
```

Use the original revision-named local snapshot and the newly frozen plan for `--run`; then `--compare --bundles <bundle paths>` on both actual outputs. The same predeclared 128-token ceiling, raw CryptoBERT text and Cardiff tweet-placeholder mapping remain. New files/code/catalog metadata require an explicit new declaration and preservation of previous outcomes; they do not silently replace V3 evidence.

For the verified separate runtime:

```powershell
& 'C:\Users\Habibi\AppData\Local\Programs\Python\Python313\python.exe' -I -B scripts/classifier_runtime_py313.py --probe
& 'C:\Users\Habibi\AppData\Local\Programs\Python\Python313\python.exe' -I -B scripts/classifier_runtime_py313.py --study-args --run --plan ../evidence/social_v4_freeze_NEW/plan.json --catalog artifacts/mid_eval/social_publisher_catalog_v4_COMPLETE.json --model-id ElKulako/cryptobert --snapshot E:/AI-Tools/Temp/investify-social-models/9e37c910fe87727cb842a9ac55c6388256fe0f15 --output-directory ../evidence/social_v4_cryptobert_NEW
```

The wrapper refuses network/socket operations and external-runtime mutations, and routes cache/temp to E:. No original snapshot is modified and outputs cannot overwrite prior directories.

## Cardiff serialization

The pinned original Cardiff snapshot lacks the runner's required original Safetensors file. The separate converter verifies the known original BIN SHA **before** `torch.load(weights_only=True, map_location='cpu')`, never falls back to unsafe loading, and requires a dense tensor state dict. It clones every key without casts/alias-key loss, writes `format=pt`, reloads and compares exact key/dtype/shape/raw bytes. Preserve the original BIN and a new conversion receipt; use explicit `verified_lossless_project_conversion` metadata in the new catalog. The loader re-verifies original/converted bytes and tensor equality. Config/tokenizer originals still need their own complete provenance.

[The actual small CPU tensor fixture](../evidence/background_lossless_conversion_fixture_20261012.json) retains all three keys and equal raw bytes/dtypes/shapes, including alias and special floating-point values. **It is not an original Cardiff conversion or model inference.** One initial Python 3.13 scratch-directory operation was denied; the successful fixture used a normal task-owned E: directory without changing ACLs or the unrelated runtime.

No converted original weights, new completed research freeze, paired candidate scores, model selection, independent human validation, NVDA transfer or stock-return usefulness is claimed. Teacher/student roles remain separate: this assistant is teacher, original Phi-3-mini is planned student, Mistral is fallback and QLoRA is later.
