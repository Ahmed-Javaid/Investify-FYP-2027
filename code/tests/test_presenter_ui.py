"""Current rebuilt UI checks using real Streamlit and retained experiment records."""
import sys
from pathlib import Path
from unittest.mock import patch
import unittest
from streamlit.testing.v1 import AppTest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'src'))
from app import presenter_data as data

class PresenterUiTests(unittest.TestCase):
    def app(self):
        app = AppTest.from_file(str(ROOT/'app/streamlit_app.py'),default_timeout=30).run()
        self.assertFalse(app.exception)
        return app

    def walkthrough(self,step='Decision'):
        app = self.app()
        app.button(key='ui_begin').click().run()
        if step != 'Decision':app.radio(key='ui_step').set_value(step).run()
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
        self.assertTrue(any(m.label=='Model class' and m.value=='Buy' for m in app.metric))
        self.assertFalse(any(b.key=='ui_verify' for b in app.button))
        app.button(key='ui_next').click().run()
        self.assertEqual(app.radio(key='ui_step').value,'Evidence')
        self.assertFalse(any(m.label=='Model class' for m in app.metric))
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
        self.assertTrue(any(m.label=='Profile comparison, R = 0.000' and m.value=='Hold' for m in app.metric))
        app.button(key='ui_tolerant').click().run()
        self.assertTrue(any(m.label=='Profile comparison, R = 1.000' and m.value=='Sell' for m in app.metric))
        self.assertTrue(any('Recorded classifier: Buy' in c.value for c in app.caption))
        app.button(key='ui_clear_profile').click().run()
        self.assertFalse(any('Profile comparison' in m.label for m in app.metric))
        self.assertFalse(app.exception)

    def test_development_case_refuses_profile_scoring(self):
        app = self.walkthrough('Risk profile')
        app.button(key='ui_cautious').click().run()
        widget=app.selectbox(key='ui_session')
        widget.set_value(widget.options[0]).run()
        self.assertFalse(app.exception)
        self.assertTrue(any('scaling-development' in m.value for m in app.info))
        self.assertFalse(any('Profile comparison' in m.label for m in app.metric))

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
            self.assertFalse(any(m.label=='Model class' for m in app.metric))

    def test_recorded_experiments_render_scores_without_model_inference(self):
        app = self.app()
        app.button(key='ui_open_experiments').click().run()
        self.assertTrue(any(m.label=='Clean macro-F1' and m.value=='0.2843' for m in app.metric))
        app.radio(key='ui_study').set_value('Sentiment comparison').run()
        self.assertFalse(app.exception)
        self.assertTrue(any('Independent human validation is unmeasured' in m.value for m in app.warning))
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

if __name__=='__main__':unittest.main()
