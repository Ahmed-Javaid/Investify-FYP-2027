"""V4 receipt/publisher-byte gate around preserved V3 social-study code.

Hash binding is reproducible provenance, not independent execution attestation.
Original references, V3 source/plan and candidate/split identities stay intact.
"""
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import re
import platform

from investify.sentiment_inference import LocalClassifier, run_inference, preprocessing_spec, preprocess, mapped_probabilities
from investify.sentiment_selection import digest, freeze_plan, validate_benchmark, evaluate_predictions

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'mideval-social-receipt-gate-v4'
ORIGINAL_CANDIDATES = {'ElKulako/cryptobert': '9e37c910fe87727cb842a9ac55c6388256fe0f15',
                       'cardiffnlp/twitter-roberta-base-sentiment-latest': '3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7'}
CRYPTOBERT_ORIGINAL_SHA256 = 'fe34ba09b3d701ff2b4ee69205e42c8143fcee1f89fe3a0cf10444988634a3c9'
SOURCE_CLOSURE = ('src/investify/sentiment_receipts.py', 'src/investify/sentiment_inference.py',
                  'src/investify/sentiment_selection.py', 'scripts/social_study_v4.py',
                  'scripts/classifier_runtime_py313.py', 'src/investify/model_conversion.py',
                  'scripts/convert_original_cardiff.py')
ORIGINAL_LABELS = {
    'ElKulako/cryptobert': {'0': 'Bearish', '1': 'Neutral', '2': 'Bullish'},
    'cardiffnlp/twitter-roberta-base-sentiment-latest': {'0': 'negative', '1': 'neutral', '2': 'positive'},
}
LOADING_FIELDS = ('missing_keys', 'unexpected_keys', 'mismatched_keys', 'error_msgs')


def read_json(path):
    """Reject ambiguous duplicate keys as well as nonfinite JSON numbers."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate study/config JSON key')
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('Nonfinite study/config JSON number')
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), object_pairs_hook=unique,
                      parse_constant=invalid)


def expected_labels(model_id):
    return ORIGINAL_LABELS.get(model_id, {'0': 'negative', '1': 'neutral', '2': 'positive'})


def validate_class_metadata(config, loading_info, labels, mapping):
    """Stricter V4-only semantics; the source-bound V3 validator stays intact."""
    id2label = getattr(config, 'id2label', None)
    label2id = getattr(config, 'label2id', None)
    if not isinstance(id2label, dict) or len(id2label) != 3 or {str(key): value for key, value in id2label.items()} != labels:
        raise ValueError('Complete original index-to-class semantics are required')
    inverse = {value: int(key) for key, value in labels.items()}
    if label2id != inverse or any(type(value) is not int for value in label2id.values()):
        raise ValueError('Original class labels require a consistent integer inverse mapping')
    aliases = {'Bearish': 'negative', 'Bullish': 'positive', 'Neutral': 'neutral',
               'negative': 'negative', 'neutral': 'neutral', 'positive': 'positive'}
    if getattr(config, 'num_labels', None) != 3 or {key: aliases[value] for key, value in labels.items()} != mapping:
        raise ValueError('Declared class mapping contradicts original classifier semantics')
    if (not isinstance(loading_info, dict) or any(key not in loading_info or
            not isinstance(loading_info[key], (list, tuple)) or loading_info[key] for key in LOADING_FIELDS)):
        raise ValueError('All missing/unexpected/mismatched/error loading keys must be empty')


def validate_original_config(snapshot, manifest, mapping):
    from types import SimpleNamespace
    config = read_json(Path(snapshot) / 'config.json')
    labels = expected_labels(manifest['model_id'])
    if config.get('architectures') != ['RobertaForSequenceClassification'] or config.get('model_type') != 'roberta':
        raise ValueError('The pinned original RoBERTa classification architecture is required')
    validate_class_metadata(SimpleNamespace(num_labels=config.get('num_labels', len(config.get('id2label', {}))),
                           id2label=config.get('id2label'), label2id=config.get('label2id')),
                            {key: [] for key in LOADING_FIELDS}, labels, mapping)
    return labels


class ReceiptClassifier(LocalClassifier):
    """Actual V4 loader retaining complete semantics/runtime/loading metadata."""
    def __init__(self, snapshot, manifest, spec, verification):
        labels = validate_original_config(snapshot, manifest, spec['label_mapping'])
        import torch
        import transformers
        import tokenizers
        import safetensors
        common = {'local_files_only': True, 'trust_remote_code': False, 'token': False,
                  'cache_dir': 'E:/AI-Tools/Temp/investify-hf-runtime'}
        self.tokenizer = transformers.AutoTokenizer.from_pretrained(str(snapshot), **common, use_fast=True)
        if getattr(self.tokenizer, 'is_fast', False) is not True:
            raise ValueError('The declared fast original tokenizer policy was not loaded')
        self.model, info = transformers.AutoModelForSequenceClassification.from_pretrained(
            str(snapshot), **common, use_safetensors=True, output_loading_info=True,
            ignore_mismatched_sizes=False, attn_implementation='eager')
        validate_class_metadata(self.model.config, info, labels, spec['label_mapping'])
        self.model.to('cpu')
        self.model.eval()
        self.torch = torch
        self.metadata = {'backend_kind': 'transformers_local_v4', 'python': platform.python_version(),
                         'torch': torch.__version__, 'transformers': transformers.__version__,
                         'tokenizers': tokenizers.__version__, 'safetensors': safetensors.__version__,
                         'config_sha256': verification['input_files_sha256']['config.json'],
                         'input_files_sha256': verification['input_files_sha256'],
                         'observed_file_bytes': verification['observed_file_bytes'],
                         'id2label': labels, 'label2id': {value: int(key) for key, value in labels.items()},
                         'num_labels': 3, 'loading_info': {key: list(info[key]) for key in LOADING_FIELDS},
                         'local_files_only': True, 'trust_remote_code': False, 'use_safetensors': True,
                         'tokenizer_use_fast': True, 'attn_implementation': 'eager',
                         'device': 'cpu', 'head_weights_complete': True}


def validate_backend_metadata(backend, manifest, verification, mapping):
    from types import SimpleNamespace
    if (not isinstance(backend, dict) or backend.get('backend_kind') != 'transformers_local_v4'
            or backend.get('device') != 'cpu' or backend.get('attn_implementation') != 'eager'
            or backend.get('input_files_sha256') != verification['input_files_sha256']
            or backend.get('observed_file_bytes') != verification['observed_file_bytes']
            or backend.get('config_sha256') != verification['input_files_sha256']['config.json']
            or any(not isinstance(backend.get(key), str) or not backend[key].strip()
                   for key in ('python', 'torch', 'transformers', 'tokenizers', 'safetensors'))
            or any(backend.get(key) is not value for key, value in
                   (('local_files_only', True), ('trust_remote_code', False), ('use_safetensors', True),
                    ('tokenizer_use_fast', True), ('head_weights_complete', True)))):
        raise ValueError('Complete actual local loader/runtime and publisher-file provenance are required')
    validate_class_metadata(SimpleNamespace(num_labels=backend.get('num_labels'), id2label=backend.get('id2label'),
                           label2id=backend.get('label2id')), backend.get('loading_info'),
                            expected_labels(manifest['model_id']), mapping)


def utc(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError('Use explicit UTC study timestamps')
    return parsed


def model_manifest(catalog, checkpoint, *, _allow_fixture=False):
    if catalog.get('purpose') == 'unit_test' and not _allow_fixture:
        raise ValueError('Fixture publisher catalogs cannot authorize research inference')
    if not _allow_fixture and ORIGINAL_CANDIDATES.get(checkpoint['model_id']) != checkpoint['revision']:
        raise ValueError('Only the unchanged original publisher candidate identities are eligible')
    matches = [item for item in catalog.get('models', []) if item.get('model_id') == checkpoint['model_id']
               and item.get('revision') == checkpoint['revision']]
    if len(matches) != 1 or matches[0].get('status') != 'complete_original_file_metadata':
        raise ValueError('Complete pinned original config/tokenizer/weight metadata is required; catalog remains incomplete')
    manifest = matches[0]
    files = manifest.get('files', [])
    if not isinstance(files, list) or not files or any(not isinstance(item, dict) for item in files):
        raise ValueError('Publisher manifest requires a nonempty file list')
    names = [item.get('filename') for item in files]
    if (any(not isinstance(name, str) for name in names) or len(names) != len(set(names))
            or 'config.json' not in names):
        raise ValueError('Publisher manifest must uniquely bind config and tokenizer files')
    if not ('tokenizer.json' in names or {'vocab.json', 'merges.txt'}.issubset(names)):
        raise ValueError('Publisher manifest must bind the actual tokenizer vocabulary/files')
    if not any(isinstance(name, str) and name.endswith('.safetensors') for name in names):
        raise ValueError('Verified original Safetensors or a separately disclosed verified conversion is required')
    conversion = manifest.get('serialization') == 'verified_lossless_project_conversion'
    if not _allow_fixture and checkpoint['model_id'] == 'cardiffnlp/twitter-roberta-base-sentiment-latest' and not conversion:
        raise ValueError('The pinned original Cardiff snapshot requires a disclosed verified lossless serialization conversion')
    if not _allow_fixture and checkpoint['model_id'] == 'ElKulako/cryptobert':
        original = next((item for item in files if item['filename'] == 'model.safetensors'), {})
        if original.get('sha256') != CRYPTOBERT_ORIGINAL_SHA256 or conversion:
            raise ValueError('CryptoBERT must use the inspected original publisher Safetensors bytes')
    if not _allow_fixture:
        required = {'config.json', 'special_tokens_map.json', 'vocab.json', 'merges.txt', 'model.safetensors'}
        if checkpoint['model_id'] == 'ElKulako/cryptobert':
            required.update({'tokenizer.json', 'tokenizer_config.json'})
        if set(names) != required:
            raise ValueError('Bind exactly all loading-affecting files from the pinned original snapshot')
        if conversion:
            from investify.model_conversion import ORIGINAL_CARDIFF_BIN_SHA256
            info = manifest.get('conversion', {})
            if (not isinstance(info, dict) or info.get('source_bin_sha256') != ORIGINAL_CARDIFF_BIN_SHA256
                    or not isinstance(info.get('original_bin_path'), str)
                    or not isinstance(info.get('receipt_path'), str)
                    or not Path(info['original_bin_path']).is_absolute() or not Path(info['receipt_path']).is_absolute()
                    or not re.fullmatch('[0-9a-f]{64}', info.get('receipt_sha256', ''))):
                raise ValueError('Bind the original Cardiff BIN and retained lossless conversion receipt')
    if conversion and checkpoint['model_id'] != 'cardiffnlp/twitter-roberta-base-sentiment-latest':
        raise ValueError('Only the explicitly versioned original Cardiff serialization conversion is supported')
    for item in files:
        if (not isinstance(item['filename'], str) or Path(item['filename']).name != item['filename']
                or not re.fullmatch('[0-9a-f]{64}', item.get('sha256', ''))
                or (item.get('expected_bytes') is not None and (type(item['expected_bytes']) is not int or item['expected_bytes'] <= 0))):
            raise ValueError('Publisher file names/hashes/sizes are invalid; unknown sizes remain null')
        if not _allow_fixture:
            prefix = f"https://huggingface.co/{checkpoint['model_id']}/blob/{checkpoint['revision']}/"
            source_name = 'pytorch_model.bin' if conversion and item['filename'].endswith('.safetensors') else item['filename']
            if item.get('source_url') != prefix + source_name:
                raise ValueError('Each original file must name its pinned canonical publisher source')
    return manifest


def verify_local_files(snapshot, manifest):
    snapshot = Path(snapshot).resolve(strict=True)
    if not snapshot.is_dir() or snapshot.name != manifest['revision']:
        raise ValueError('Use a local directory named by the exact declared revision')
    expected = {item['filename'] for item in manifest['files']}
    used_extensions = {'.json', '.safetensors', '.txt', '.model', '.bin', '.py'}
    conversion = manifest.get('serialization') == 'verified_lossless_project_conversion'
    receipt_path = Path(manifest['conversion']['receipt_path']).resolve(strict=True) if conversion else None
    extras = {file.name for file in snapshot.iterdir() if file.suffix.lower() in used_extensions
              and (not conversion or file.resolve() != receipt_path)} - expected
    if extras:
        raise ValueError(f'Unbound model/tokenizer files could change inference: {sorted(extras)}')
    hashes, sizes = {}, {}
    for item in manifest['files']:
        path = (snapshot / item['filename']).resolve(strict=True)
        if not path.is_relative_to(snapshot) or not path.is_file():
            raise ValueError('Declared model file escapes the exact snapshot directory')
        checksum = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
                checksum.update(chunk)
        sizes[item['filename']] = path.stat().st_size
        hashes[item['filename']] = checksum.hexdigest()
        if hashes[item['filename']] != item['sha256'] or (item.get('expected_bytes') is not None and sizes[item['filename']] != item['expected_bytes']):
            raise ValueError('Local bytes differ from pinned publisher file metadata')
    result = {'manifest_sha256': digest(manifest), 'input_files_sha256': hashes, 'observed_file_bytes': sizes,
              'scope': 'Matches declared trusted publisher bytes; no independent execution attestation'}
    if conversion:
        from investify.model_conversion import verify_conversion, file_hash
        info = manifest['conversion']
        if file_hash(receipt_path) != info['receipt_sha256']:
            raise ValueError('Retained conversion receipt bytes differ from the declared manifest')
        weight = next(item for item in manifest['files'] if item['filename'].endswith('.safetensors'))
        summary = verify_conversion(Path(info['original_bin_path']), snapshot / weight['filename'],
                                    expected_converted_sha256=weight['sha256'], receipt=read_json(receipt_path))
        result.update(conversion_receipt_sha256=info['receipt_sha256'], conversion_verification=summary)
    return result


def freeze_receipt_plan(data, parent, catalog, *, frozen_utc=None, _allow_fixture=False):
    if freeze_plan(data, parent['candidate_checkpoints'], frozen_utc=parent['frozen_utc']) != parent:
        raise ValueError('Original V3 benchmark/source/candidate plan changed; preserve and replay it first')
    for checkpoint in parent['candidate_checkpoints']:
        model_manifest(catalog, checkpoint, _allow_fixture=_allow_fixture)
    timestamp = frozen_utc or datetime.now(timezone.utc).isoformat()
    if utc(timestamp) < utc(parent['frozen_utc']):
        raise ValueError('New gate declaration must follow the original freeze')
    return {'protocol': PROTOCOL, 'frozen_utc': timestamp, 'parent_plan_sha256': digest(parent),
            'benchmark_sha256': parent['benchmark_sha256'], 'catalog_sha256': digest(catalog),
            'development_post_ids': parent['development_post_ids'], 'heldout_post_ids': parent['heldout_post_ids'],
            'candidate_checkpoints': parent['candidate_checkpoints'],
            'source_sha256': {relative: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() for relative in SOURCE_CLOSURE},
            'purpose': 'unit_test' if _allow_fixture else 'research',
            'scope': 'Receipt-bound original-byte study over unchanged V3 references/splits; no execution attestation or human accuracy'}


def check_plan(data, parent, catalog, plan, *, _allow_fixture=False):
    expected = freeze_receipt_plan(data, parent, catalog, frozen_utc=plan['frozen_utc'], _allow_fixture=_allow_fixture)
    if expected != plan:
        raise ValueError('V4 gate/source/catalog/parent/split drift; no inference or comparison')


def run_bundle(data, parent, catalog, plan, model_id, snapshot, *, _backend=None, _allow_fixture=False):
    if _backend is not None and not _allow_fixture:
        raise ValueError('Injected backend is allowed only for explicitly labelled unit fixtures')
    check_plan(data, parent, catalog, plan, _allow_fixture=_allow_fixture)
    checkpoint = next((item for item in parent['candidate_checkpoints'] if item['model_id'] == model_id), None)
    if checkpoint is None:
        raise ValueError('Unknown original candidate')
    manifest = model_manifest(catalog, checkpoint, _allow_fixture=_allow_fixture)
    verification = verify_local_files(snapshot, manifest)
    spec = preprocessing_spec(checkpoint['preprocessing'])
    backend = _backend if _backend is not None else ReceiptClassifier(Path(snapshot).resolve(strict=True), manifest, spec, verification)
    if not _allow_fixture:
        validate_backend_metadata(backend.metadata, manifest, verification, spec['label_mapping'])
    run, receipt = run_inference(data, parent, model_id, Path(snapshot), _backend=backend)
    if utc(run['run_started_utc']) < utc(plan['frozen_utc']):
        raise ValueError('Run predates the new receipt/source declaration')
    if verify_local_files(snapshot, manifest) != verification:
        raise ValueError('Local model/tokenizer bytes changed during inference')
    check_plan(data, parent, catalog, plan, _allow_fixture=_allow_fixture)
    return {'protocol': PROTOCOL, 'purpose': 'unit_test' if _allow_fixture else 'research',
            'execution_kind': 'unit_fixture' if _allow_fixture else 'local_original_classifier',
            'plan_sha256': digest(plan), 'publisher_verification': verification, 'run': run, 'receipt': receipt}


def compare_bundles(data, parent, catalog, plan, bundles, *, _allow_fixture=False):
    check_plan(data, parent, catalog, plan, _allow_fixture=_allow_fixture)
    posts = {post['post_id']: post for post in validate_benchmark(data)}
    if not isinstance(bundles, list):
        raise ValueError('Research bundles must be an explicit list')
    runs = []
    for bundle in bundles:
        if (bundle.get('protocol') != PROTOCOL or bundle.get('plan_sha256') != digest(plan)
                or bundle.get('purpose') != ('unit_test' if _allow_fixture else 'research')
                or bundle.get('execution_kind') != ('unit_fixture' if _allow_fixture else 'local_original_classifier')):
            raise ValueError('Research comparisons require matching real-purpose run/receipt bundles; fixtures cannot enter')
        run, receipt = bundle['run'], bundle['receipt']
        checkpoint = next((item for item in parent['candidate_checkpoints'] if item['model_id'] == run['model_id']), None)
        if checkpoint is None:
            raise ValueError('Undeclared candidate bundle')
        manifest = model_manifest(catalog, checkpoint, _allow_fixture=_allow_fixture)
        verification = bundle['publisher_verification']
        expected_hashes = {item['filename']: item['sha256'] for item in manifest['files']}
        if verification.get('manifest_sha256') != digest(manifest) or verification.get('input_files_sha256') != expected_hashes:
            raise ValueError('Publisher byte/manifest verification differs from the frozen declaration')
        sizes = verification.get('observed_file_bytes')
        if (not isinstance(sizes, dict) or set(sizes) != set(expected_hashes)
                or any(type(sizes[item['filename']]) is not int or sizes[item['filename']] <= 0
                       or (item.get('expected_bytes') is not None and sizes[item['filename']] != item['expected_bytes'])
                       for item in manifest['files'])):
            raise ValueError('Observed publisher file sizes are incomplete or inconsistent')
        if manifest.get('serialization') == 'verified_lossless_project_conversion':
            from investify.model_conversion import validate_conversion_receipt
            if verification.get('conversion_receipt_sha256') != manifest['conversion']['receipt_sha256']:
                raise ValueError('Conversion receipt is not bound to the publisher verification')
            validate_conversion_receipt(verification.get('conversion_verification'),
                                        expected_converted_sha256=expected_hashes['model.safetensors'])
        if (receipt.get('run_sha256') != digest(run) or receipt.get('model_id') != run['model_id']
                or receipt.get('revision') != run['revision'] or receipt.get('plan_sha256') != digest(parent)):
            raise ValueError('Missing, swapped, stale or modified sidecar receipt')
        spec = preprocessing_spec(checkpoint['preprocessing'])
        if receipt.get('preprocessing') != spec:
            raise ValueError('Receipt preprocessing differs from the frozen text/token/class mapping')
        backend = receipt.get('backend', {})
        if not _allow_fixture:
            validate_backend_metadata(backend, manifest, verification, spec['label_mapping'])
        details = receipt.get('details', [])
        if len(details) != len(parent['heldout_post_ids']) or {item['post_id'] for item in details} != set(parent['heldout_post_ids']):
            raise ValueError('Receipt must retain exactly all held-out detail identities')
        by_id = {item['post_id']: item for item in details}
        for detail in details:
            elapsed = detail.get('elapsed_seconds')
            if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0:
                raise ValueError('Receipt durations must be measured finite nonnegative values')
        for output in run['outputs']:
            detail = by_id[output['post_id']]
            if 'error' in output:
                if (set(detail) != {'post_id', 'error_type', 'elapsed_seconds'}
                        or not isinstance(detail.get('error_type'), str)
                        or not re.fullmatch('[A-Za-z_][A-Za-z0-9_]*', detail['error_type'])
                        or output['error'] != f"Classification failed ({detail['error_type']})"):
                    raise ValueError('Failure receipt cannot become a probability prediction')
                continue
            if set(detail) != {'post_id', 'processed_text_sha256', 'logits', 'input_tokens', 'truncated', 'elapsed_seconds'}:
                raise ValueError('Successful receipts cannot contain missing/mixed failure fields')
            text = preprocess(posts[output['post_id']]['text'], spec['text_policy'])
            if detail.get('processed_text_sha256') != hashlib.sha256(text.encode()).hexdigest():
                raise ValueError('Receipt text differs from held-out original text/preprocessing')
            if (type(detail.get('input_tokens')) is not int or detail['input_tokens'] < 1
                    or type(detail.get('truncated')) is not bool
                    or detail['truncated'] != (detail['input_tokens'] > spec['max_length'])):
                raise ValueError('Invalid token/truncation provenance')
            probabilities = mapped_probabilities(detail.get('logits'), spec['label_mapping'])
            if (not isinstance(output['probabilities'], dict) or set(output['probabilities']) != set(probabilities)
                    or any(type(output['probabilities'][key]) not in (int, float)
                           or not math.isfinite(output['probabilities'][key])
                           or abs(output['probabilities'][key] - value) > 1e-12 for key, value in probabilities.items())):
                raise ValueError('Scored probabilities differ from retained logits')
        if utc(run['run_started_utc']) < utc(plan['frozen_utc']):
            raise ValueError('Bundle inference predates the new declaration')
        runs.append(run)
    result = evaluate_predictions(data, parent, runs)
    result.update(receipt_protocol=PROTOCOL, receipt_plan_sha256=digest(plan),
                  execution_kind='unit_fixture' if _allow_fixture else 'receipt_bound_local_study',
                  independently_authenticated_execution=False)
    return result
