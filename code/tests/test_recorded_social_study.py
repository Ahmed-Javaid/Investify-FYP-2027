"""Recorded study selectors cannot escape project evidence or bypass receipts."""
import importlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'src'))
from app.tabs.social_study import recorded_receipt_comparison, STUDY

class RecordedSocialStudyTests(unittest.TestCase):
    def setUp(self):
        self.benchmark=json.loads((STUDY/'social_benchmark.json').read_text(encoding='utf-8'))
        self.parent=json.loads((STUDY/'social_selection_plan.json').read_text(encoding='utf-8'))
        self.pointer=json.loads((STUDY/'social_latest_study.json').read_text(encoding='utf-8'))

    def test_actual_two_candidate_bundles_recompute_the_retained_comparison(self):
        result=recorded_receipt_comparison(self.benchmark,self.parent,self.pointer)
        expected=json.loads((STUDY/'social_study_20261013_run02/comparison/comparison.json').read_text(encoding='utf-8'))
        self.assertEqual(result,expected)
        self.assertEqual(result['status'],'complete')
        self.assertEqual(result['heldout_posts'],24)
        self.assertIsNone(result['deployment_selection'])

    def test_absolute_and_escaping_references_fail_before_reading_external_files(self):
        for value in ('../../../../.env',str(ROOT/'config/spike.yaml')):
            pointer=dict(self.pointer,catalog=value)
            with self.subTest(value=value),self.assertRaises(ValueError):
                recorded_receipt_comparison(self.benchmark,self.parent,pointer)

    def test_missing_or_unpaired_bundle_list_is_refused(self):
        for value in ([],self.pointer['bundles'][:1],None):
            pointer=dict(self.pointer,bundles=value)
            with self.subTest(value=value),self.assertRaisesRegex(ValueError,'complete recorded'):
                recorded_receipt_comparison(self.benchmark,self.parent,pointer)

    def test_a_retained_bundle_cannot_silently_rebind_to_a_changed_plan(self):
        module=importlib.import_module('app.tabs.social_study')
        original=module.read_json
        def changed(path):
            data=original(path)
            if path.name=='plan.json':
                data['heldout_post_ids']=list(reversed(data['heldout_post_ids']))
            return data
        with patch.object(module,'read_json',side_effect=changed),self.assertRaisesRegex(ValueError,'drift'):
            recorded_receipt_comparison(self.benchmark,self.parent,self.pointer)


if __name__=='__main__':
    unittest.main()
