"""Offline-only classifier inference for a frozen declared-reference social study.

No model download, remote model code, annotation, training or deployment
selection. A test backend can be injected only through the Python API; the CLI
always requires actual local Transformers/PyTorch classification weights.
"""
import hashlib
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

from investify.sentiment_selection import LABELS, digest, freeze_plan, validate_benchmark


class LocalModelUnavailable(RuntimeError):
    pass


def preprocessing_spec(value: str) -> dict:
    try:
        spec = json.loads(value)
    except (TypeError, ValueError):
        raise ValueError('Inference preprocessing must be a declared JSON specification') from None
    if (not isinstance(spec, dict) or set(spec) != {'text_policy', 'max_length', 'label_mapping'}
            or spec['text_policy'] not in ('raw', 'tweet_mentions_urls')
            or type(spec['max_length']) is not int or not 8 <= spec['max_length'] <= 512
            or not isinstance(spec['label_mapping'], dict) or set(spec['label_mapping']) != {'0', '1', '2'}
            or not all(isinstance(label, str) for label in spec['label_mapping'].values())
            or set(spec['label_mapping'].values()) != set(LABELS)):
        raise ValueError('Predeclare the text policy, token ceiling and exact three-class index mapping')
    return spec


def preprocess(text: str, policy: str) -> str:
    if policy == 'raw':
        return text
    if policy != 'tweet_mentions_urls':
        raise ValueError('unsupported text preprocessing')
    # Provider-documented whole space-delimited username/link placeholders.
    return ' '.join('@user' if token.startswith('@') and len(token) > 1 else
                    'http' if token.startswith('http') else token for token in text.split(' '))


def mapped_probabilities(logits, mapping):
    if (not isinstance(logits, (list, tuple)) or len(logits) != 3
            or any(type(value) not in (int, float) or not math.isfinite(value) for value in logits)):
        raise ValueError('classifier logits must be exactly three finite numbers')
    peak = max(logits)
    exponential = [math.exp(value - peak) for value in logits]
    total = math.fsum(exponential)
    return {mapping[str(index)]: value / total for index, value in enumerate(exponential)}


def validate_loaded_head(config, loading_info, mapping):
    if getattr(config, 'num_labels', None) != 3:
        raise LocalModelUnavailable('The local checkpoint is not a three-class sentiment classifier')
    if not isinstance(loading_info, dict):
        raise LocalModelUnavailable('Checkpoint loading provenance is unavailable')
    if any(loading_info.get(key) for key in ('missing_keys', 'mismatched_keys', 'error_msgs')):
        raise LocalModelUnavailable('Checkpoint weights are incomplete/mismatched; no randomly initialized head is permitted')
    aliases = {'positive': 'positive', 'bullish': 'positive', 'negative': 'negative',
               'bearish': 'negative', 'neutral': 'neutral'}
    if not isinstance(getattr(config, 'id2label', None), dict):
        raise LocalModelUnavailable('Checkpoint label metadata is missing')
    for index in range(3):
        name = config.id2label.get(index, config.id2label.get(str(index), ''))
        known = aliases.get(str(name).casefold())
        if known is not None and known != mapping[str(index)]:
            raise LocalModelUnavailable('Declared class mapping contradicts checkpoint label semantics')


class LocalClassifier:
    def __init__(self, snapshot: Path, revision: str, mapping: dict):
        snapshot = snapshot.resolve()
        if not snapshot.is_dir() or snapshot.name != revision:
            raise LocalModelUnavailable('Provide the exact local snapshot directory named by the declared revision')
        if not list(snapshot.glob('*.safetensors')):
            raise LocalModelUnavailable('An actual local Safetensors classification checkpoint is required')
        try:
            import torch
            import transformers
        except ImportError:
            raise LocalModelUnavailable('The offline inference environment requires PyTorch and Transformers') from None
        common = {'local_files_only': True, 'trust_remote_code': False, 'token': False,
                  'cache_dir': 'E:/AI-Tools/Temp/investify-hf-runtime'}
        try:
            self.tokenizer = transformers.AutoTokenizer.from_pretrained(str(snapshot), **common)
            self.model, info = transformers.AutoModelForSequenceClassification.from_pretrained(
                str(snapshot), **common, use_safetensors=True, output_loading_info=True,
                ignore_mismatched_sizes=False, attn_implementation='eager')
            validate_loaded_head(self.model.config, info, mapping)
            self.model.to('cpu')
            self.model.eval()
        except (OSError, ValueError, RuntimeError) as error:
            if isinstance(error, LocalModelUnavailable):
                raise
            raise LocalModelUnavailable(f'Local classifier could not load ({type(error).__name__})') from None
        self.torch = torch
        files = sorted(path for path in snapshot.iterdir() if path.is_file() and
                       (path.suffix == '.safetensors' or path.name in {
                           'config.json', 'tokenizer.json', 'tokenizer_config.json', 'special_tokens_map.json',
                           'vocab.json', 'vocab.txt', 'merges.txt', 'model.safetensors.index.json'}))
        hashes = {}
        for path in files:
            checksum = hashlib.sha256()
            with path.open('rb') as stream:
                for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
                    checksum.update(chunk)
            hashes[path.name] = checksum.hexdigest()
        self.metadata = {'torch': torch.__version__, 'transformers': transformers.__version__,
                         'config_sha256': hashlib.sha256((snapshot / 'config.json').read_bytes()).hexdigest(),
                         'input_files_sha256': hashes,
                         'local_files_only': True, 'trust_remote_code': False, 'use_safetensors': True,
                         'device': 'cpu', 'head_weights_complete': True}

    def predict(self, text: str, max_length: int) -> dict:
        full = self.tokenizer(text, truncation=False, add_special_tokens=True)['input_ids']
        encoded = self.tokenizer(text, return_tensors='pt', truncation=True, max_length=max_length)
        with self.torch.inference_mode():
            output = self.model(**encoded)
        return {'logits': output.logits[0].detach().cpu().tolist(), 'input_tokens': len(full),
                'truncated': len(full) > max_length}


def run_inference(data: dict, plan: dict, model_id: str, snapshot: Path, *, _backend=None) -> tuple[dict, dict]:
    if freeze_plan(data, plan['candidate_checkpoints'], frozen_utc=plan['frozen_utc']) != plan:
        raise ValueError('Study data/code/selection changed after freezing; no inference performed')
    matches = [item for item in plan['candidate_checkpoints'] if item['model_id'] == model_id]
    if len(matches) != 1:
        raise ValueError('Select one uniquely declared model/revision in the frozen plan')
    checkpoint = matches[0]
    spec = preprocessing_spec(checkpoint['preprocessing'])
    started = datetime.now(timezone.utc).isoformat()
    if datetime.fromisoformat(started) < datetime.fromisoformat(plan['frozen_utc'].replace('Z', '+00:00')):
        raise ValueError('Inference cannot start before the declared freeze time')
    backend = _backend if _backend is not None else LocalClassifier(snapshot, checkpoint['revision'], spec['label_mapping'])
    posts = {post['post_id']: post for post in validate_benchmark(data)}
    outputs, details = [], []
    for identifier in plan['heldout_post_ids']:
        text = preprocess(posts[identifier]['text'], spec['text_policy'])
        before = time.perf_counter()
        try:
            prediction = backend.predict(text, spec['max_length'])
            if (not isinstance(prediction, dict) or set(prediction) != {'logits', 'input_tokens', 'truncated'}
                    or type(prediction['input_tokens']) is not int or prediction['input_tokens'] < 1
                    or type(prediction['truncated']) is not bool
                    or prediction['truncated'] != (prediction['input_tokens'] > spec['max_length'])):
                raise ValueError('classifier returned invalid token/length provenance')
            outputs.append({'post_id': identifier, 'probabilities': mapped_probabilities(prediction['logits'], spec['label_mapping'])})
            details.append({'post_id': identifier, 'processed_text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                            **prediction, 'elapsed_seconds': time.perf_counter() - before})
        except (OSError, ValueError, RuntimeError, TypeError, KeyError, IndexError) as error:
            outputs.append({'post_id': identifier, 'error': f'Classification failed ({type(error).__name__})'})
            details.append({'post_id': identifier, 'error_type': type(error).__name__,
                            'elapsed_seconds': time.perf_counter() - before})
    run = {**checkpoint, 'plan_sha256': digest(plan), 'benchmark_sha256': plan['benchmark_sha256'],
           'run_started_utc': started, 'run_completed_utc': datetime.now(timezone.utc).isoformat(), 'outputs': outputs}
    receipt = {'model_id': model_id, 'revision': checkpoint['revision'], 'plan_sha256': digest(plan),
               'run_sha256': digest(run), 'backend': getattr(backend, 'metadata', {}),
               'preprocessing': spec, 'details': details, 'model_downloads': 0,
               'scope': 'Whole-post sentiment baseline scored against the declared reference method; target-specific and human-validated performance are separate questions.'}
    return run, receipt
