"""Explicit V4 file/backend fixtures cannot become research outcomes."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import importlib.util
import os

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tests'))
from test_mideval_sentiment_selection import fixture_benchmark
from investify.sentiment_selection import freeze_plan, digest
from investify.sentiment_receipts import (freeze_receipt_plan, run_bundle, compare_bundles, verify_local_files,
    model_manifest, validate_class_metadata, validate_original_config, validate_backend_metadata, LOADING_FIELDS, read_json)


class ReceiptBackendFixture:
    metadata = {'execution_kind': 'LABELLED UNIT BACKEND, not loaded original weights'}
    def predict(self, text, maximum):
        return {'logits': [0., 1., 2.], 'input_tokens': 12, 'truncated': False}


class SentimentReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='investify-social-v4-fixture-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = fixture_benchmark()
        preprocessing = json.dumps({'text_policy': 'raw', 'max_length': 128,
                                    'label_mapping': {'0': 'negative', '1': 'neutral', '2': 'positive'}})
        self.checkpoints = [{'model_id': f'fixture/candidate-{letter}', 'revision': letter * 40, 'preprocessing': preprocessing}
                            for letter in ('a', 'b')]
        self.parent = freeze_plan(self.data, self.checkpoints, frozen_utc='2026-10-04T12:00:00Z')
        self.catalog = {'purpose': 'unit_test', 'models': []}
        for checkpoint in self.checkpoints:
            folder = self.root / checkpoint['revision']
            folder.mkdir()
            files = []
            for name in ('config.json', 'tokenizer_config.json', 'tokenizer.json', 'model.safetensors'):
                raw = b'LABELLED BOUNDARY FIXTURE, not an actual model or tokenizer'
                (folder / name).write_bytes(raw)
                files.append({'filename': name, 'sha256': hashlib.sha256(raw).hexdigest(), 'expected_bytes': len(raw)})
            self.catalog['models'].append({**checkpoint, 'status': 'complete_original_file_metadata', 'files': files})
        self.plan = freeze_receipt_plan(self.data, self.parent, self.catalog,
                                       frozen_utc='2026-10-05T12:00:00Z', _allow_fixture=True)

    def bundles(self):
        return [run_bundle(self.data, self.parent, self.catalog, self.plan, checkpoint['model_id'],
                           self.root / checkpoint['revision'], _backend=ReceiptBackendFixture(), _allow_fixture=True)
                for checkpoint in self.checkpoints]

    def compare(self, bundles):
        return compare_bundles(self.data, self.parent, self.catalog, self.plan, bundles, _allow_fixture=True)

    def test_fixture_receipt_comparison_is_explicitly_separate_from_research(self):
        bundles = self.bundles()
        result = self.compare(bundles)
        self.assertEqual(result['execution_kind'], 'unit_fixture')
        self.assertTrue(result['comparison_ready'])
        self.assertFalse(result['independently_authenticated_execution'])
        with self.assertRaisesRegex(ValueError, 'Fixture publisher catalogs'):
            compare_bundles(self.data, self.parent, self.catalog, self.plan, bundles)

    def test_parent_split_labels_and_candidate_declarations_are_unchanged(self):
        self.assertEqual(self.plan['heldout_post_ids'], self.parent['heldout_post_ids'])
        self.assertEqual(self.plan['development_post_ids'], self.parent['development_post_ids'])
        self.assertEqual(self.plan['candidate_checkpoints'], self.parent['candidate_checkpoints'])

    def test_directory_revision_name_cannot_hide_substituted_weight_bytes(self):
        manifest = self.catalog['models'][0]
        path = self.root / manifest['revision']
        (path / 'model.safetensors').write_bytes(b'LABELLED substituted fixture')
        with self.assertRaisesRegex(ValueError, 'Local bytes differ'):
            verify_local_files(path, manifest)

    def test_unbound_tokenizer_configuration_cannot_be_loaded(self):
        manifest = self.catalog['models'][0]
        path = self.root / manifest['revision']
        (path / 'added_tokens.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Unbound model/tokenizer'):
            verify_local_files(path, manifest)

    def test_missing_or_swapped_sidecar_cannot_score_a_probability_run(self):
        bundles = self.bundles()
        missing = copy.deepcopy(bundles)
        missing[0]['receipt'] = {}
        with self.assertRaisesRegex(ValueError, 'sidecar receipt'):
            self.compare(missing)
        swapped = copy.deepcopy(bundles)
        swapped[0]['receipt'] = swapped[1]['receipt']
        with self.assertRaisesRegex(ValueError, 'sidecar receipt'):
            self.compare(swapped)

    def test_hash_consistent_probability_edit_still_fails_retained_logit_replay(self):
        bundles = self.bundles()
        bundles[0]['run']['outputs'][0]['probabilities'] = {'negative': 1., 'neutral': 0., 'positive': 0.}
        bundles[0]['receipt']['run_sha256'] = digest(bundles[0]['run'])
        with self.assertRaisesRegex(ValueError, 'retained logits'):
            self.compare(bundles)

    def test_text_and_token_provenance_tampering_fail_closed(self):
        for field, value in (('processed_text_sha256', '0' * 64), ('truncated', True)):
            bundles = self.bundles()
            bundles[0]['receipt']['details'][0][field] = value
            with self.assertRaises(ValueError):
                self.compare(bundles)

    def test_catalog_and_source_plan_drift_prevent_a_run_before_backend_use(self):
        changed = copy.deepcopy(self.catalog)
        changed['models'][0]['files'][0]['expected_bytes'] += 1
        with self.assertRaisesRegex(ValueError, 'drift'):
            run_bundle(self.data, self.parent, changed, self.plan, self.checkpoints[0]['model_id'],
                       self.root / self.checkpoints[0]['revision'], _backend=ReceiptBackendFixture(), _allow_fixture=True)

    def test_incomplete_actual_publisher_metadata_never_freezes_a_research_plan(self):
        catalog = json.loads((ROOT / 'artifacts/mid_eval/social_publisher_catalog_v4.json').read_text(encoding='utf-8'))
        benchmark = json.loads((ROOT / 'artifacts/mid_eval/social_benchmark.json').read_text(encoding='utf-8'))
        parent = json.loads((ROOT / 'artifacts/mid_eval/social_selection_plan.json').read_text(encoding='utf-8'))
        with self.assertRaisesRegex(ValueError, 'catalog remains incomplete'):
            freeze_receipt_plan(benchmark, parent, catalog)

    def test_backend_injection_has_no_production_path(self):
        with self.assertRaisesRegex(ValueError, 'Injected backend'):
            run_bundle(self.data, self.parent, self.catalog, self.plan, self.checkpoints[0]['model_id'],
                       self.root / self.checkpoints[0]['revision'], _backend=ReceiptBackendFixture())

    def test_catalog_cannot_relabel_fixture_weight_bytes_as_the_known_original_cryptobert(self):
        checkpoint = {'model_id': 'ElKulako/cryptobert', 'revision': '9e37c910fe87727cb842a9ac55c6388256fe0f15'}
        manifest = copy.deepcopy(self.catalog['models'][0])
        manifest.update(checkpoint)
        with self.assertRaisesRegex(ValueError, 'inspected original publisher'):
            model_manifest({'models': [manifest]}, checkpoint)

    def test_model_file_resolving_outside_snapshot_is_rejected_before_reading(self):
        manifest = self.catalog['models'][0]
        folder = self.root / manifest['revision']
        weight = folder / 'model.safetensors'
        original_resolve = Path.resolve
        outside = self.root / 'LABELLED_outside_weight'
        outside.write_bytes(weight.read_bytes())
        # No symlink privilege is needed to exercise the resolved escape branch.
        def resolve(path, *args, **kwargs):
            return outside if path == weight else original_resolve(path, *args, **kwargs)
        with patch.object(Path, 'resolve', resolve):
            with self.assertRaisesRegex(ValueError, 'escapes'):
                verify_local_files(folder, manifest)

    def test_loader_affecting_file_with_uppercase_extension_is_not_ignored(self):
        folder = self.root / self.catalog['models'][0]['revision']
        (folder / 'unbound_tokenizer.JSON').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Unbound'):
            verify_local_files(folder, self.catalog['models'][0])

    def test_unknown_inverted_or_incomplete_class_semantics_are_refused(self):
        labels = {'0': 'negative', '1': 'neutral', '2': 'positive'}
        mapping = dict(labels)
        valid = SimpleNamespace(num_labels=3, id2label=labels, label2id={v: int(k) for k, v in labels.items()})
        info = {key: [] for key in LOADING_FIELDS}
        validate_class_metadata(valid, info, labels, mapping)
        for altered in ({}, {0: 'LABEL_0', 1: 'LABEL_1', 2: 'LABEL_2'},
                        {'0': 'positive', '1': 'neutral', '2': 'negative'}):
            config = copy.deepcopy(valid)
            config.id2label = altered
            with self.assertRaises(ValueError):
                validate_class_metadata(config, info, labels, mapping)
        config = copy.deepcopy(valid)
        config.label2id['positive'] = True
        with self.assertRaises(ValueError):
            validate_class_metadata(config, info, labels, mapping)
        for key in LOADING_FIELDS:
            altered = copy.deepcopy(info)
            altered[key] = ['LABELLED incomplete or unexpected weight']
            with self.assertRaisesRegex(ValueError, 'loading keys'):
                validate_class_metadata(valid, altered, labels, mapping)
        with self.assertRaises(ValueError):
            validate_class_metadata(valid, {}, labels, mapping)

    def test_original_config_semantics_are_checked_before_any_model_load(self):
        manifest = self.catalog['models'][0]
        folder = self.root / manifest['revision']
        config = {'architectures': ['RobertaForSequenceClassification'], 'model_type': 'roberta',
                  'id2label': {'0': 'negative', '1': 'neutral', '2': 'positive'},
                  'label2id': {'negative': 0, 'neutral': 1, 'positive': 2}}
        (folder / 'config.json').write_text(json.dumps(config))
        self.assertEqual(validate_original_config(folder, manifest, config['id2label']), config['id2label'])
        config['id2label'] = {'0': 'LABEL_0', '1': 'LABEL_1', '2': 'LABEL_2'}
        (folder / 'config.json').write_text(json.dumps(config))
        with self.assertRaisesRegex(ValueError, 'class semantics'):
            validate_original_config(folder, manifest, {'0': 'negative', '1': 'neutral', '2': 'positive'})

    def test_cardiff_manifest_uses_only_original_tokenizer_files_and_disclosed_conversion(self):
        from investify.model_conversion import ORIGINAL_CARDIFF_BIN_SHA256
        checkpoint = {'model_id': 'cardiffnlp/twitter-roberta-base-sentiment-latest',
                      'revision': '3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7'}
        prefix = f"https://huggingface.co/{checkpoint['model_id']}/blob/{checkpoint['revision']}/"
        manifest = {**checkpoint, 'status': 'complete_original_file_metadata',
                    'serialization': 'verified_lossless_project_conversion',
                    'conversion': {'source_bin_sha256': ORIGINAL_CARDIFF_BIN_SHA256,
                                   'original_bin_path': str(self.root / 'original.bin'),
                                   'receipt_path': str(self.root / 'conversion_receipt.json'), 'receipt_sha256': '0' * 64},
                    'files': [{'filename': name, 'sha256': '0' * 64, 'expected_bytes': None,
                               'source_url': prefix + ('pytorch_model.bin' if name == 'model.safetensors' else name)}
                              for name in ('config.json', 'special_tokens_map.json', 'vocab.json', 'merges.txt', 'model.safetensors')]}
        self.assertIs(model_manifest({'models': [manifest]}, checkpoint), manifest)
        broken = copy.deepcopy(manifest)
        broken['conversion']['source_bin_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'original Cardiff BIN'):
            model_manifest({'models': [broken]}, checkpoint)
        broken = copy.deepcopy(manifest)
        broken['files'] = [row for row in broken['files'] if row['filename'] != 'special_tokens_map.json']
        with self.assertRaisesRegex(ValueError, 'loading-affecting'):
            model_manifest({'models': [broken]}, checkpoint)

    def test_observed_file_sizes_cannot_be_missing_or_modified(self):
        for mutation in ('missing', 'wrong'):
            bundles = self.bundles()
            if mutation == 'missing':
                bundles[0]['publisher_verification'].pop('observed_file_bytes')
            else:
                bundles[0]['publisher_verification']['observed_file_bytes']['config.json'] += 1
            with self.assertRaisesRegex(ValueError, 'sizes'):
                self.compare(bundles)

    def test_runtime_metadata_requires_versions_device_config_and_complete_loading_info(self):
        manifest = self.catalog['models'][0]
        verification = verify_local_files(self.root / manifest['revision'], manifest)
        labels = {'0': 'negative', '1': 'neutral', '2': 'positive'}
        backend = {'backend_kind': 'transformers_local_v4', 'device': 'cpu', 'attn_implementation': 'eager',
                   'input_files_sha256': verification['input_files_sha256'],
                   'observed_file_bytes': verification['observed_file_bytes'],
                   'config_sha256': verification['input_files_sha256']['config.json'],
                   'id2label': labels, 'label2id': {v: int(k) for k, v in labels.items()}, 'num_labels': 3,
                   'loading_info': {key: [] for key in LOADING_FIELDS},
                   **{key: 'LABELLED version fixture' for key in ('python', 'torch', 'transformers', 'tokenizers', 'safetensors')},
                   'local_files_only': True, 'trust_remote_code': False, 'use_safetensors': True,
                   'tokenizer_use_fast': True, 'head_weights_complete': True}
        validate_backend_metadata(backend, manifest, verification, labels)
        for field, value in (('torch', None), ('safetensors', ''), ('device', 'cuda'),
                             ('config_sha256', '0' * 64), ('tokenizer_use_fast', False), ('observed_file_bytes', {})):
            altered = copy.deepcopy(backend)
            altered[field] = value
            with self.assertRaises(ValueError):
                validate_backend_metadata(altered, manifest, verification, labels)

    def test_failure_receipts_cannot_hide_success_fields_or_wrong_error_types(self):
        class FailedFixture(ReceiptBackendFixture):
            def predict(self, text, maximum):
                raise RuntimeError('LABELLED fixture failure')
        bundles = [run_bundle(self.data, self.parent, self.catalog, self.plan, checkpoint['model_id'],
                              self.root / checkpoint['revision'], _backend=FailedFixture(), _allow_fixture=True)
                   for checkpoint in self.checkpoints]
        result = self.compare(bundles)
        self.assertFalse(result['comparison_ready'])
        self.assertTrue(all(row['quality_metrics'] is None for row in result['results']))
        for field, value in (('error_type', None), ('error_type', 'WrongError'), ('logits', [0., 1., 2.])):
            altered = copy.deepcopy(bundles)
            altered[0]['receipt']['details'][0][field] = value
            with self.assertRaisesRegex(ValueError, 'Failure receipt'):
                self.compare(altered)
        successful = self.bundles()
        successful[0]['receipt']['details'][0]['error_type'] = 'RuntimeError'
        with self.assertRaisesRegex(ValueError, 'mixed failure'):
            self.compare(successful)

    def test_nonfinite_probability_cannot_escape_logit_replay(self):
        bundles = self.bundles()
        bundles[0]['run']['outputs'][0]['probabilities']['positive'] = float('nan')
        # digest rejects nonfinite JSON before it can be accepted as a receipt.
        with self.assertRaises(ValueError):
            self.compare(bundles)

    def test_source_plan_drift_during_backend_execution_is_detected_afterward(self):
        owner = self
        class DriftFixture(ReceiptBackendFixture):
            def predict(self, text, maximum):
                owner.plan['source_sha256']['src/investify/sentiment_receipts.py'] = '0' * 64
                return super().predict(text, maximum)
        with self.assertRaisesRegex(ValueError, 'drift'):
            run_bundle(self.data, self.parent, self.catalog, self.plan, self.checkpoints[0]['model_id'],
                       self.root / self.checkpoints[0]['revision'], _backend=DriftFixture(), _allow_fixture=True)

    def test_model_bytes_changed_during_backend_execution_are_refused(self):
        folder = self.root / self.checkpoints[0]['revision']
        class DriftFixture(ReceiptBackendFixture):
            def predict(self, text, maximum):
                (folder / 'model.safetensors').write_bytes(b'LABELLED mutation while running')
                return super().predict(text, maximum)
        with self.assertRaisesRegex(ValueError, 'Local bytes differ'):
            run_bundle(self.data, self.parent, self.catalog, self.plan, self.checkpoints[0]['model_id'],
                       folder, _backend=DriftFixture(), _allow_fixture=True)

    def test_duplicate_json_keys_are_refused(self):
        path = self.root / 'LABELLED_duplicate.json'
        path.write_text('{"purpose":"unit_test","purpose":"research"}')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            read_json(path)


def load_script(name):
    spec = importlib.util.spec_from_file_location('fixture_' + name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SentimentCliAndRuntimeGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='investify-social-cli-fixture-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def arguments(self, output, **overrides):
        values = dict(output_directory=output, benchmark=self.root / 'benchmark.json',
                      parent_plan=self.root / 'parent.json', catalog=self.root / 'catalog.json',
                      plan=None, bundles=None, snapshot=None)
        values.update(overrides)
        return SimpleNamespace(**values)

    def test_existing_output_and_input_aliases_are_refused_without_changes(self):
        module = load_script('social_study_v4')
        module.ROOT = self.root / 'code'
        existing = self.root / 'prior'
        existing.mkdir()
        original = existing / 'bundle.json'
        original.write_bytes(b'LABELLED frozen output')
        with self.assertRaisesRegex(ValueError, 'Preserve prior'):
            module.reserve_output(self.arguments(existing))
        self.assertEqual(original.read_bytes(), b'LABELLED frozen output')
        future = self.root / 'new_output'
        for field in ('benchmark', 'parent_plan', 'catalog', 'plan'):
            with self.assertRaisesRegex(ValueError, 'collide'):
                module.reserve_output(self.arguments(future, **{field: future / 'failure.json'}))
            self.assertFalse(future.exists())
        with self.assertRaises(ValueError):
            module.reserve_output(self.arguments(future, bundles=[future / 'bundle.json']))
        self.assertFalse(future.exists())

    def test_snapshot_overlap_and_parent_traversal_are_refused_before_creation(self):
        module = load_script('social_study_v4')
        module.ROOT = self.root / 'code'
        for output, snapshot in ((self.root / 'snapshot' / 'new', self.root / 'snapshot'),
                                 (self.root / 'parent', self.root / 'parent' / 'snapshot'),
                                 (self.root / '..' / 'LABELLED_escape', None)):
            with self.assertRaises(ValueError):
                module.reserve_output(self.arguments(output, snapshot=snapshot))
            self.assertFalse(output.exists())

    def test_exclusive_new_directory_reservation_cannot_reuse_prior_output(self):
        module = load_script('social_study_v4')
        module.ROOT = self.root / 'code'
        output = self.root / 'new'
        self.assertEqual(module.reserve_output(self.arguments(output)), output.resolve())
        with self.assertRaises(ValueError):
            module.reserve_output(self.arguments(output))

    def test_runtime_audit_refuses_external_metadata_mutations_and_networking(self):
        module = load_script('classifier_runtime_py313')
        allowed = self.root / 'outputs'
        audit = module.make_audit(probe=False, output_root=allowed, temp_root=allowed)
        outside = str(self.root / 'LABELLED_external')
        events = [('os.utime', (outside, None, None, -1)), ('os.chmod', (outside, 0o600, -1)),
                  ('os.truncate', (outside, 0)), ('os.link', (outside, str(allowed / 'link'), -1, -1)),
                  ('os.symlink', (outside, str(allowed / 'link'), -1)),
                  ('os.rename', (outside, str(allowed / 'moved'), -1, -1)),
                  ('os.remove', ('relative', 42)), ('open', (outside, 'w', os.O_WRONLY)),
                  ('open', (42, 'w', os.O_WRONLY)), ('socket.connect', (None, ('example.invalid', 443)))]
        for event, values in events:
            with self.assertRaises(PermissionError, msg=event):
                audit(event, values)
        audit('open', (outside, 'r', os.O_RDONLY))
        audit('os.utime', (str(allowed / 'owned'), None, None, -1))
        with self.assertRaises(PermissionError):
            module.make_audit(probe=True, output_root=allowed, temp_root=allowed)(
                'os.mkdir', (str(allowed / 'owned'), 0o700, -1))
