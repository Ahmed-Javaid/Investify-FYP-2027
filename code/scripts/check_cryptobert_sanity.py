"""Offline original-model diagnostic; authored probes are separate from study labels."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

CODE = Path(__file__).resolve().parents[1]
PROJECT = CODE.parent
TEMP = Path('E:/AI-Tools/Temp')
sys.dont_write_bytecode = True
sys.path.insert(0, str(CODE / 'src'))
sys.path.insert(0, str(CODE / 'scripts'))
from classifier_runtime_py313 import EXISTING_PACKAGES, make_audit
os.environ.update(TEMP=str(TEMP), TMP=str(TEMP), HF_HOME=str(TEMP / 'investify-classifier-hf'),
                  HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', TOKENIZERS_PARALLELISM='false',
                  XDG_CACHE_HOME='E:/AI-Tools/Cache', PYTHONDONTWRITEBYTECODE='1')
sys.path.insert(0, str(EXISTING_PACKAGES))
sys.addaudithook(make_audit(probe=False))
from investify.sentiment_inference import LocalClassifier, mapped_probabilities


def main():
    import torch
    torch.set_num_threads(4)
    output = PROJECT / 'evidence/cryptobert_sanity_20261014.json'
    if output.exists():
        raise ValueError('Preserve earlier diagnostics')
    catalog_path = CODE / 'artifacts/mid_eval/social_study_20261012_run01/publisher_catalog.json'
    catalog = json.loads(catalog_path.read_text())
    model = next(row for row in catalog['models'] if row['model_id'] == 'ElKulako/cryptobert')
    snapshot = Path(model['snapshot_directory'])
    for row in model['files']:
        path = snapshot / row['filename']
        if path.stat().st_size != row['expected_bytes'] or hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Original CryptoBERT bytes changed')
    mapping = {'0': 'negative', '1': 'neutral', '2': 'positive'}
    backend = LocalClassifier(snapshot, model['revision'], mapping)
    probes = [
        ('positive', "Bitcoin is breaking out. I'm buying more BTC and holding for the next rally. Huge upside ahead!"),
        ('negative', 'Bitcoin is collapsing. I sold all my BTC. This market is a disaster and prices will fall further.'),
        ('neutral', 'Bitcoin currently trades around 40000 dollars. The daily trading volume was reported.'),
        ('positive', 'ETH to the moon! Bullish on Ethereum. I bought the dip, staking ETH and never selling.'),
        ('negative', 'Bearish on Ethereum. Dumping my ETH now. The crash is getting worse and this token is heading down.'),
    ]
    results = []
    for intended, text in probes:
        prediction = backend.predict(text, 128)
        probabilities = mapped_probabilities(prediction['logits'], mapping)
        results.append({'text': text, 'intended_sentiment': intended,
                        'predicted_sentiment': max(probabilities, key=probabilities.get),
                        'probabilities': probabilities, **prediction})
    value = {'schema': 'investify-cryptobert-diagnostic-v1', 'checked_utc': datetime.now(timezone.utc).isoformat(),
             'model_id': model['model_id'], 'revision': model['revision'], 'backend': backend.metadata,
             'catalog_sha256': hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
             'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'probes': results, 'classes_observed': sorted({row['predicted_sentiment'] for row in results}),
             'frozen_benchmark_or_labels_modified': False, 'network_requests': 0,
             'scope': 'Authored sanity probes, not held-out benchmark accuracy or independent human labels.'}
    with output.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'classes_observed': value['classes_observed'],
                      'probes': [{'intended': row['intended_sentiment'], 'predicted': row['predicted_sentiment']}
                                 for row in results]}, indent=2))


if __name__ == '__main__':
    main()
