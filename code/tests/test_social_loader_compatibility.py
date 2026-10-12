"""Transformers diagnostic containers must not weaken original-weight gates."""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from investify.sentiment_receipts import normalize_loading_info, validate_class_metadata, LOADING_FIELDS

LABELS = {'0':'negative','1':'neutral','2':'positive'}
CONFIG = SimpleNamespace(num_labels=3,id2label=LABELS,label2id={'negative':0,'neutral':1,'positive':2})


class LoaderDiagnosticCompatibilityTests(unittest.TestCase):
    def validate(self, info):
        validate_class_metadata(CONFIG,normalize_loading_info(info),LABELS,LABELS)

    def test_actual_modern_empty_set_convention_is_accepted(self):
        info = {'missing_keys':set(),'unexpected_keys':set(),'mismatched_keys':set(),'error_msgs':[]}
        self.validate(info)
        self.assertEqual(normalize_loading_info(info),{key:[] for key in LOADING_FIELDS})

    def test_legacy_list_and_tuple_conventions_remain_supported(self):
        for kind in (list,tuple):
            self.validate({key:kind() for key in LOADING_FIELDS})

    def test_every_nonempty_modern_diagnostic_still_refuses_a_checkpoint(self):
        for field in LOADING_FIELDS:
            info = {key:set() for key in LOADING_FIELDS}
            info[field] = {'LABELLED missing/unexpected/mismatch/error fixture'}
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'must be empty'):
                self.validate(info)

    def test_absent_field_is_never_defaulted_to_success(self):
        info = {key:[] for key in LOADING_FIELDS}
        del info['error_msgs']
        with self.assertRaisesRegex(ValueError,'Complete actual'):
            normalize_loading_info(info)

    def test_ambiguous_scalar_and_null_diagnostics_refuse(self):
        for value in (None,'',False,{},0):
            info = {key:[] for key in LOADING_FIELDS}
            info['missing_keys'] = value
            with self.subTest(value=value),self.assertRaisesRegex(ValueError,'explicit collections'):
                normalize_loading_info(info)

    def test_conversion_preserves_all_nonempty_keys_without_mutating_input(self):
        info = {key:set() for key in LOADING_FIELDS}
        info['unexpected_keys'] = {'LABELLED.b','LABELLED.a'}
        normalized = normalize_loading_info(info)
        self.assertEqual(normalized['unexpected_keys'],['LABELLED.a','LABELLED.b'])
        self.assertEqual(info['unexpected_keys'],{'LABELLED.a','LABELLED.b'})


if __name__=='__main__':
    unittest.main()
