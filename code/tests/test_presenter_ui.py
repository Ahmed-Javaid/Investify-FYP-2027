"""Current rebuilt UI checks using real Streamlit and retained experiment records."""
import sys
from pathlib import Path
from unittest.mock import patch
import unittest
from streamlit.testing.v1 import AppTest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'src'))
from app import presenter_data as data  # noqa: E402 - local source paths must be installed first.

class PresenterUiTests(unittest.TestCase):
    def app(self):
        app = AppTest.from_file(str(ROOT/'app/streamlit_app.py'),default_timeout=30).run()
        self.assertFalse(app.exception)
        return app

    def walkthrough(self,step='Decision'):
        app = self.app()
        app.button(key='ui_begin').click().run()
        if any(r.key == 'ui_step' for r in app.radio):
            app.radio(key='ui_step').set_value(step).run()
        self.assertFalse(app.exception)
        return app

    def test_overview_has_one_primary_route_and_no_hidden_research_widgets(self):
        app = self.app()
        self.assertEqual(app.session_state['ui_page'],'Overview')
        self.assertFalse(app.selectbox)
        self.assertFalse(app.metric)
        self.assertTrue(any('Five trading-session' in m.value for m in app.markdown))

    def test_walkthrough_renders_only_the_selected_step(self):
        app = self.walkthrough()
        self.assertTrue(any(m.label=='Policy outcome' and m.value=='No recommendation (Observe)' for m in app.metric))
        self.assertTrue(any(c.value=='Diagnostic class: Buy' for c in app.caption))
        self.assertFalse(any(b.key=='ui_verify' for b in app.button))
        app.button(key='ui_next').click().run()
        self.assertEqual(app.radio(key='ui_step').value,'Evidence')
        self.assertFalse(any(m.label=='Policy outcome' for m in app.metric))
        self.assertEqual(len(app.selectbox(key='ui_feature').options),5)
        app.button(key='ui_previous').click().run()
        self.assertEqual(app.radio(key='ui_step').value,'Decision')
        self.assertFalse(app.exception)

    def test_both_fresh_and_preserved_experiments_are_selectable(self):
        app = self.walkthrough()
        for source in data.SOURCES:
            app.selectbox(key='ui_source').set_value(source).run()
            self.assertFalse(app.exception)
            expected = data.load_cases(source).records[app.selectbox(key='ui_session').value]
            self.assertTrue(any(m.label=='Calibrated probability' and m.value==f'{expected.confidence:.1%}' for m in app.metric))

    def test_all_feature_families_remain_inspectable(self):
        app = self.walkthrough('Evidence')
        app.radio(key='ui_family').set_value('News sentiment').run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.selectbox(key='ui_feature').options),6)
        self.assertTrue(any('separate social study' in c.value for c in app.caption))
        app.radio(key='ui_family').set_value('Technical analysis').run()
        self.assertFalse(app.exception)

    def test_profiles_are_explicit_unanswered_and_can_be_cleared(self):
        app = self.walkthrough('Risk profile')
        self.assertTrue(all(app.selectbox(key='ui_profile_'+k).value is None for k in ('horizon','buffer','stability','dependants','age')))
        self.assertFalse(any('Profile comparison' in m.label for m in app.metric))
        app.button(key='ui_cautious').click().run()
        self.assertTrue(any(m.label=='Risk allowance R' and m.value=='0.000' for m in app.metric))
        self.assertTrue(any(m.label=='Profile outcome' and m.value=='Observe' for m in app.metric))
        app.button(key='ui_tolerant').click().run()
        self.assertTrue(any(m.label=='Risk allowance R' and m.value=='1.000' for m in app.metric))
        self.assertTrue(any('Required confidence 50.0%' in c.value for c in app.caption))
        self.assertTrue(any('model class Buy' in c.value for c in app.caption))
        app.button(key='ui_clear_profile').click().run()
        self.assertFalse(any('Profile comparison' in m.label for m in app.metric))
        self.assertFalse(app.exception)

    def test_profile_change_invalidates_verified_explanation_context(self):
        app = self.walkthrough('Risk profile')
        app.button(key='ui_cautious').click().run()
        app.radio(key='ui_step').set_value('Explanation check').run()
        app.button(key='ui_verify').click().run()
        self.assertTrue(any(item.value == 'Candidate accepted' for item in app.success))
        app.radio(key='ui_step').set_value('Risk profile').run()
        app.button(key='ui_tolerant').click().run()
        app.radio(key='ui_step').set_value('Explanation check').run()
        self.assertFalse(any(item.value == 'Candidate accepted' for item in app.success))
        self.assertFalse(app.exception)

    def test_profile_policy_is_available_without_fitting_a_new_comparator(self):
        app = self.walkthrough('Risk profile')
        app.button(key='ui_tolerant').click().run()
        widget = app.selectbox(key='ui_session')
        widget.set_value(widget.options[0]).run()
        self.assertFalse(app.exception)
        self.assertTrue(any(m.label == 'Risk allowance R' and m.value == '1.000' for m in app.metric))
        self.assertTrue(any(m.label == 'Profile outcome' for m in app.metric))

    def test_wrong_visible_probability_is_rejected_with_verified_fallback(self):
        app = self.walkthrough('Explanation check')
        app.button(key='ui_inject').click().run()
        self.assertIn('1.00%',app.text_area(key='ui_candidate_text').value)
        app.button(key='ui_verify').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any(m.value=='Candidate rejected' for m in app.error))
        self.assertTrue(any(m.value=='Verified fallback emitted' for m in app.success))
        self.assertFalse(any('1.00%' in m.value for m in app.text))

    def test_candidate_edits_invalidate_the_visible_verification(self):
        app = self.walkthrough('Explanation check')
        app.button(key='ui_verify').click().run()
        self.assertTrue(any(m.value=='Candidate accepted' for m in app.success))
        app.text_area(key='ui_candidate_text').set_value('Unverified edited text.').run()
        self.assertFalse(any(m.value=='Candidate accepted' for m in app.success))
        self.assertTrue(any('Previous results do not apply' in m.value for m in app.info))

    def test_case_change_resets_candidate_and_cannot_publish_stale_output(self):
        app = self.walkthrough('Explanation check')
        app.button(key='ui_verify').click().run()
        widget=app.selectbox(key='ui_session')
        widget.set_value(widget.options[-2]).run()
        self.assertFalse(app.exception)
        self.assertFalse(any(m.value=='Candidate accepted' for m in app.success))
        self.assertIn(widget.options[-2],app.text_area(key='ui_candidate_text').value)

    def test_invalid_records_are_visible_without_a_fake_decision(self):
        with patch('app.presenter_data.load_cases',side_effect=ValueError('Labelled invalid input')):
            app = self.walkthrough()
            self.assertTrue(any('Recorded evidence unavailable' in m.value for m in app.error))
            self.assertFalse(any(m.label=='Policy outcome' for m in app.metric))

    def test_recorded_experiments_render_scores_without_model_inference(self):
        app = self.app()
        app.button(key='ui_open_experiments').click().run()
        self.assertTrue(any(m.label=='Clean macro-F1' and m.value=='0.2843' for m in app.metric))
        app.radio(key='ui_study').set_value('Sentiment comparison').run()
        self.assertFalse(app.exception)
        self.assertTrue(any('Independent validation is unmeasured' in m.value for m in app.warning))
        table=next(t.value for t in app.dataframe if 'Macro-F1 agreement' in t.value.columns)
        self.assertAlmostEqual(table.iloc[0]['Macro-F1 agreement'],0.25641025641025644)
        self.assertAlmostEqual(table.iloc[1]['Macro-F1 agreement'],0.6015873015873016)
        app.radio(key='ui_study').set_value('Teacher pilot').run()
        self.assertFalse(app.exception)
        self.assertTrue(any('Phi-3-mini remains untrained' in m.value for m in app.markdown))

    def test_failed_study_load_withholds_comparison_scores(self):
        app = self.app();app.button(key='ui_open_experiments').click().run()
        with patch('app.presenter_data.social_comparison',side_effect=ValueError('Labelled invalid bundle')):
            app.radio(key='ui_study').set_value('Sentiment comparison').run()
            self.assertTrue(any('No substitute score' in m.value for m in app.error))
            self.assertFalse(app.dataframe)

    def test_fresh_calibration_diagnosis_has_the_actual_map_bounds(self):
        app = self.walkthrough()
        app.selectbox(key='ui_source').set_value('fresh_frozen').run()
        self.assertTrue(any('0.5345' in m.value and '0.3140' in m.value for m in app.markdown))
        collection = data.load_cases('fresh_refit')
        result = data.calibration_diagnosis(collection)
        self.assertEqual(result['unconditionally_dominant_class'], 'Buy')
        self.assertEqual(result['calibrated_evaluation_rows'], 186)
        with self.assertRaises(ValueError):
            data.calibration_diagnosis(data.load_cases('alpaca'))

    def test_stale_calibration_diagnosis_is_withheld(self):
        import copy
        collection = data.load_cases('fresh_frozen')
        receipt = data.read_json(ROOT.parent / 'evidence/calibration_global_bounds_20261013.json')
        altered = copy.deepcopy(receipt)
        altered['results']['engine_frozen_alpaca']['trace_sha256'] = '0' * 64
        with patch('app.presenter_data.read_json', return_value=altered):
            with self.assertRaisesRegex(ValueError, 'does not match'):
                data.calibration_diagnosis(collection)
        with patch('app.presenter_data.calibration_diagnosis', side_effect=ValueError('Labelled stale trace')):
            app = self.walkthrough()
            app.selectbox(key='ui_source').set_value('fresh_frozen').run()
            self.assertTrue(any('diagnosis unavailable' in m.value for m in app.info))
            self.assertTrue(any(c.value == 'Diagnostic class: Buy' for c in app.caption))

    def test_onboarding_precedes_the_decision_and_discloses_purpose_risks_and_status(self):
        app = self.app()
        app.button(key='ui_begin').click().run()
        self.assertEqual(app.radio(key='ui_step').value, 'Onboarding')
        self.assertTrue(any('does not execute trades' in m.value for m in app.markdown))
        self.assertTrue(any('lose money' in w.value for w in app.warning))
        app.button(key='ui_next').click().run()
        self.assertEqual(app.radio(key='ui_step').value, 'Decision')

    def test_each_walkthrough_step_has_advisory_date_horizon_and_limits(self):
        app = self.walkthrough()
        for step in ('Decision', 'Evidence', 'Risk profile', 'Explanation check'):
            app.radio(key='ui_step').set_value(step).run()
            self.assertFalse(app.exception)
            captions = '\n'.join(c.value for c in app.caption)
            self.assertIn('What this means / limits:', captions)
            self.assertIn('Historical data date:', captions)
            self.assertIn('trading sessions; calibrated confidence:', captions)
            self.assertIn('advisory status: educational research; no trades.', captions)

    def test_abstaining_explanation_and_fallback_keep_policy_outcome(self):
        app = self.walkthrough('Explanation check')
        self.assertIn('Policy outcome: Observe.', app.text_area(key='ui_candidate_text').value)
        self.assertIn('diagnostic class for session', app.text_area(key='ui_candidate_text').value)
        app.button(key='ui_inject').click().run()
        app.button(key='ui_verify').click().run()
        self.assertTrue(any('Policy outcome: Observe.' in t.value for t in app.text))
        self.assertFalse(app.exception)

    def test_design_names_current_profile_file_and_explainer_schedule(self):
        app = self.app()
        app.button(key='ui_open_design').click().run()
        text = '\n'.join(m.value for m in app.markdown)
        self.assertIn('risk_profile_gl.py', text)
        self.assertNotIn('risk_comparator.py', text)
        self.assertFalse(any('student ownership' in c.value for c in app.caption))

if __name__=='__main__':unittest.main()
