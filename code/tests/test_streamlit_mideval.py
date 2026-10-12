"""Real Streamlit AppTest checks. Require the separate demo dependency set."""
import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
HAS_STREAMLIT = importlib.util.find_spec("streamlit") is not None
if HAS_STREAMLIT:
    from streamlit.testing.v1 import AppTest


@unittest.skipUnless(HAS_STREAMLIT, "Streamlit runtime absent; install requirements-demo-runtime.txt")
class StreamlitMidEvalTests(unittest.TestCase):
    def app(self):
        app = AppTest.from_file(str(ROOT / "app/streamlit_app.py"), default_timeout=30).run()
        self.assertFalse(app.exception)
        return app

    def test_live_ui_renders_evidence_for_each_corpus(self):
        app = self.app()
        for corpus in ('alpaca', 'fnspid'):
            app.radio(key='decision_corpus').set_value(corpus).run()
            self.assertFalse(app.exception)
            self.assertTrue(any('Understand the technical and sentiment evidence' in x.value
                                for x in app.markdown))
            self.assertTrue(any('does not condition' in x.value for x in app.caption))

    def test_wrong_displayed_probability_triggers_real_ui_fallback(self):
        app = self.app()
        app.toggle(key='corrupt_explanation').set_value(True).run()
        app.selectbox(key='corruption_kind').set_value('text_only_probability').run()
        self.assertFalse(app.exception)
        self.assertTrue(any('Rejected.' in x.value for x in app.markdown))
        self.assertTrue(any('scores describe the rejected candidate' in x.value for x in app.caption))

    def test_missing_harness_inputs_disable_the_rerun(self):
        with patch('app.tabs.leakage_lab.harness_missing_inputs', return_value=['missing fixture input']):
            app = self.app()
            app.radio(key='leakage_corpus').set_value('results_alpaca').run()
            buttons = [b for b in app.button if b.label == 'Re-run D_CENTRED now']
            self.assertEqual(len(buttons), 1)
            self.assertTrue(buttons[0].disabled)
            self.assertTrue(any('live experiment is unavailable' in x.value for x in app.warning))

    def test_leakage_view_labels_saved_results_and_limits_preflight_claims(self):
        app = self.app()
        for corpus in ('results', 'results_alpaca'):
            app.radio(key='leakage_corpus').set_value(corpus).run()
            self.assertFalse(app.exception)
            self.assertTrue(any('Saved historical experiment results' in x.value for x in app.info))
            self.assertTrue(any('does not validate dataset rows' in x.value for x in app.caption))
            self.assertTrue(any(b.label == 'Re-run D_CENTRED now' and b.disabled for b in app.button))

    def test_actual_fixture_causality_button_detects_centred_mutations_without_claiming_a_market_run(self):
        app = self.app()
        app.radio(key='leakage_corpus').set_value('results_alpaca').run()
        app.button(key='run_fixture_causality').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any('9/9 passed; 4 deliberately centred' in x.value for x in app.success))
        self.assertTrue(any('Labelled synthetic fixtures only' in x.value for x in app.info))
        self.assertTrue(any(b.label == 'Re-run D_CENTRED now' and b.disabled for b in app.button))

    def test_failed_scientific_import_after_preflight_has_a_visible_failure_without_a_fake_result(self):
        with patch('app.tabs.leakage_lab.harness_missing_inputs', return_value=[]):
            app = self.app()
            app.radio(key='leakage_corpus').set_value('results_alpaca').run()
            button = next(b for b in app.button if b.label == 'Re-run D_CENTRED now')
            button.click().run()
            self.assertFalse(app.exception)
            self.assertTrue(any('Scientific re-run failed. No new experiment result' in x.value for x in app.error))
            self.assertFalse(any('Live result' in x.value for x in app.markdown))

    def test_invalid_historical_records_show_an_error_instead_of_a_decision(self):
        with patch('app.tabs.decision.load_records', side_effect=ValueError('labelled invalid fixture')):
            app = self.app()
            self.assertTrue(any('unavailable or invalid' in x.value for x in app.error))
            self.assertFalse(any('day view' in m.label for m in app.metric))

    def test_unconfigured_generator_displays_the_real_verified_comparator(self):
        with patch.dict(os.environ, {'INVESTIFY_LLM_MODEL': '',
                                     'INVESTIFY_LLM_BASE_URL': 'http://127.0.0.1:1234/v1',
                                     'INVESTIFY_LLM_API_KEY': ''}):
            app = self.app()
            app.button(key='generate_explanation').click().run()
            self.assertFalse(app.exception)
            self.assertTrue(any('Verified deterministic explanation' in x.value for x in app.info))
            self.assertTrue(any('Feature definition for mean_polarity:' in x.value for x in app.code))
            self.assertTrue(any('Recorded feature mention_volume' in x.value for x in app.code))

    def complete_profile(self, app, tolerance_index=2):
        capacity = {'horizon': '5+ years', 'buffer': '6+ months', 'stability': 'Salaried and stable',
                    'dependants': '0', 'age': '18-30'}
        for name, answer in capacity.items():
            app.selectbox(key=f'profile_{name}').set_value(answer)
        for index in range(3):
            radio = app.radio(key=f'profile_tolerance_{index}')
            radio.set_value(radio.options[tolerance_index])
        app.run()
        self.assertFalse(app.exception)
        return app

    def test_risk_profile_does_not_assume_answers_or_emit_a_comparator_decision(self):
        app = self.app()
        self.assertTrue(all(app.selectbox(key=f'profile_{name}').value is None
                            for name in ('horizon', 'buffer', 'stability', 'dependants', 'age')))
        self.assertTrue(any('Complete all eight answers' in x.value for x in app.info))
        self.assertFalse(any('Profile blend comparator' in m.label for m in app.metric))

    def test_profile_actually_changes_the_separate_comparator_in_both_corpora(self):
        app = self.complete_profile(self.app())
        for corpus in ('alpaca', 'fnspid'):
            app.radio(key='decision_corpus').set_value(corpus).run()
            self.assertFalse(app.exception)
            self.assertTrue(any('Profile blend comparator (R = 1.000)' == m.label for m in app.metric))
            fixed = next(m.value for m in app.metric if m.label.startswith('Fixed blend comparator'))
            saved = next(m.value for m in app.metric if 'day view' in m.label)
            self.complete_profile(app, tolerance_index=0)
            self.assertTrue(any('Profile blend comparator (R = 0.000)' == m.label for m in app.metric))
            self.assertEqual(fixed, next(m.value for m in app.metric if m.label.startswith('Fixed blend comparator')))
            self.assertEqual(saved, next(m.value for m in app.metric if 'day view' in m.label))
            self.complete_profile(app)

    def test_development_session_refuses_a_comparator_and_cannot_leave_a_stale_result(self):
        app = self.complete_profile(self.app())
        date_widget = app.select_slider(key='decision_session')
        date_widget.set_value(date_widget.options[0]).run()
        self.assertFalse(app.exception)
        self.assertTrue(any('scaling-development block' in x.value for x in app.info))
        self.assertFalse(any('Profile blend comparator' in m.label for m in app.metric))

    def test_recorded_original_candidate_scores_show_reference_limits_and_download(self):
        app = self.app()
        self.assertTrue(any('recorded metrics' in x.value.lower() or 'recorded original-publisher inference' in x.value.lower() for x in app.caption))
        self.assertTrue(any('independent human validation is unmeasured' in x.value for x in app.warning))
        tables = [x.value for x in app.dataframe if 'model' in x.value.columns and 'macro_F1' in x.value.columns]
        self.assertEqual(len(tables), 1)
        rows = tables[0].set_index('model')
        self.assertAlmostEqual(rows.loc['ElKulako/cryptobert', 'macro_F1'], 0.25641025641025644)
        self.assertAlmostEqual(rows.loc['cardiffnlp/twitter-roberta-base-sentiment-latest', 'macro_F1'], 0.6015873015873016)
        self.assertTrue(all(rows['coverage'] == 1.0))
        self.assertTrue(any(button.key == 'download_social_study' for button in app.get('download_button')))

    def test_social_study_discloses_missing_real_benchmark_without_quality_scores(self):
        with patch('app.tabs.social_study.read_json', side_effect=FileNotFoundError('labelled missing benchmark')):
            app = self.app()
            self.assertTrue(any('Social benchmark pending.' in x.value for x in app.info))
            self.assertFalse(any('macro' in m.label.lower() for m in app.metric))

    def test_invalid_social_benchmark_is_refused_in_the_actual_ui(self):
        with patch('app.tabs.social_study.read_json', return_value=[]):
            app = self.app()
            self.assertTrue(any('Social benchmark invalid.' in x.value for x in app.error))
            self.assertFalse(any('macro' in m.label.lower() for m in app.metric))

    def fixture_social_inputs(self):
        # Labelled unit fixtures only; never written as research input files.
        sys.path.insert(0, str(ROOT / 'tests'))
        from test_mideval_sentiment_selection import fixture_benchmark, CHECKPOINTS
        from investify.sentiment_selection import LABELS, digest, freeze_plan, validate_benchmark
        benchmark = fixture_benchmark()
        benchmark['selection']['study_purpose'] = 'unit_test'
        plan = freeze_plan(benchmark, CHECKPOINTS, frozen_utc='2026-10-04T12:00:00Z')
        gold = {post['post_id']: post['gold_label'] for post in validate_benchmark(benchmark)}
        runs = [{**checkpoint, 'plan_sha256': digest(plan), 'benchmark_sha256': plan['benchmark_sha256'],
                 'run_started_utc': '2026-10-05T12:00:00Z', 'run_completed_utc': '2026-10-05T12:01:00Z',
                 'outputs': [{'post_id': key, 'probabilities': {label: float(label == gold[key]) for label in LABELS}}
                             for key in plan['heldout_post_ids']]} for checkpoint in CHECKPOINTS]
        return benchmark, plan, runs

    def test_valid_fixture_study_renders_metrics_and_download_without_inference(self):
        benchmark, plan, runs = self.fixture_social_inputs()
        def read(path):
            return {'social_benchmark.json': benchmark, 'social_selection_plan.json': plan,
                    'social_model_runs.json': runs}[path.name]
        with patch('app.tabs.social_study.read_json', side_effect=read):
            app = self.app()
            self.assertTrue(any('Benchmark leaders:' in x.value for x in app.markdown))
            self.assertTrue(any(m.label == 'Supplied acquired posts' and m.value == '200' for m in app.metric))
            self.assertTrue(any(button.key == 'download_social_study' for button in app.get('download_button')))

    def test_partial_fixture_study_retains_errors_and_refuses_paired_comparison(self):
        benchmark, plan, runs = self.fixture_social_inputs()
        runs[0]['outputs'][0] = {'post_id': runs[0]['outputs'][0]['post_id'], 'error': 'Labelled fixture failure'}
        def read(path):
            return {'social_benchmark.json': benchmark, 'social_selection_plan.json': plan,
                    'social_model_runs.json': runs}[path.name]
        with patch('app.tabs.social_study.read_json', side_effect=read):
            app = self.app()
            self.assertTrue(any('Paired comparison unavailable.' in x.value for x in app.warning))
            self.assertFalse(any('Benchmark leaders:' in x.value for x in app.markdown))

    def test_ai_fixture_reference_discloses_single_pass_and_does_not_claim_human_validation(self):
        sys.path.insert(0, str(ROOT / 'tests'))
        from test_mideval_ai_annotation import fixture_ai_benchmark
        from test_mideval_sentiment_selection import CHECKPOINTS
        from investify.sentiment_selection import freeze_plan
        benchmark = fixture_ai_benchmark()
        plan = freeze_plan(benchmark, CHECKPOINTS, frozen_utc='2026-10-04T12:00:00Z')
        def read(path):
            return {'social_benchmark.json': benchmark, 'social_selection_plan.json': plan,
                    'social_model_runs.json': []}[path.name]
        with patch('app.tabs.social_study.read_json', side_effect=read):
            app = self.app()
            self.assertTrue(any('Model-generated reference labels.' in x.value for x in app.warning))
            self.assertTrue(any(m.label == 'Initial exact agreement' and m.value == 'Not measured' for m in app.metric))
            self.assertTrue(any('fixture/annotator' in x.value for x in app.markdown))
            self.assertFalse(any('Benchmark leaders:' in x.value for x in app.markdown))

    def test_supplementary_fixture_scores_preserve_the_pending_original_classifier_study(self):
        sys.path.insert(0, str(ROOT / 'tests'))
        from test_mideval_generative_sentiment import GenerativeSentimentTests
        fixture = GenerativeSentimentTests()
        fixture.setUp()
        benchmark, parent, plan = fixture.benchmark, fixture.parent, fixture.plan
        runs = [fixture.run_fixture(index)[0] for index in (0, 1)]
        def read(path):
            files = {'social_benchmark.json': benchmark, 'social_selection_plan.json': parent,
                     'social_model_runs.json': [], 'generative_sentiment_plan.json': plan,
                     'generative_sentiment_runs.json': runs}
            if path.name not in files:
                raise FileNotFoundError('LABELLED absent optional V4 fixture file')
            return files[path.name]
        with patch('app.tabs.social_study.read_json', side_effect=read):
            app = self.app()
            self.assertTrue(any('Local generative sentiment agreement' in x.value for x in app.markdown))
            self.assertTrue(any('CryptoBERT/Cardiff classifier study remains pending' in x.value for x in app.caption))
            self.assertFalse(any('Benchmark leaders:' in x.value for x in app.markdown))
            self.assertTrue(any(button.key == 'download_social_study' for button in app.get('download_button')))
            self.assertTrue(any(button.key == 'download_generative_study' for button in app.get('download_button')))

    def test_guided_navigation_keeps_the_selected_case_and_profile(self):
        app = self.app()
        self.assertEqual(app.session_state['demo_section'], 'Start here')
        self.assertEqual(app.radio(key='decision_corpus').value, 'fresh_frozen')
        self.assertEqual(app.radio(key='leakage_corpus').value, 'fresh_alpaca')
        app.button(key='start_walkthrough').click().run()
        self.assertEqual(app.session_state['demo_section'], 'Decision')
        app.button(key='profile_example_cautious').click().run()
        self.assertTrue(any(m.label == 'Profile blend comparator (R = 0.000)' and m.value == 'Hold' for m in app.metric))
        session = app.select_slider(key='decision_session').value
        app.button(key='demo_next').click().run()
        self.assertEqual(app.session_state['demo_section'], 'Leakage Lab')
        app.button(key='demo_previous').click().run()
        self.assertEqual(app.session_state['demo_section'], 'Decision')
        self.assertEqual(app.select_slider(key='decision_session').value, session)
        self.assertEqual(app.selectbox(key='profile_horizon').value, '5+ years')
        self.assertFalse(app.exception)

    def test_fictional_examples_change_comparator_then_clear_all_answers(self):
        app = self.app()
        app.button(key='profile_example_cautious').click().run()
        saved = next(m.value for m in app.metric if 'day view' in m.label)
        app.button(key='profile_example_tolerant').click().run()
        self.assertTrue(any(m.label == 'Profile blend comparator (R = 1.000)' and m.value == 'Sell' for m in app.metric))
        self.assertEqual(saved, next(m.value for m in app.metric if 'day view' in m.label))
        self.assertTrue(any('Fictional demonstration answers' in c.value for c in app.caption))
        app.button(key='clear_profile').click().run()
        self.assertTrue(all(app.selectbox(key=f'profile_{name}').value is None for name in ('horizon','buffer','stability','dependants','age')))
        self.assertFalse(any('Profile blend comparator' in m.label for m in app.metric))
        self.assertFalse(app.exception)

    def test_both_fresh_calibration_modes_show_current_identity(self):
        app = self.app()
        for corpus in ('fresh_frozen', 'fresh_refit'):
            app.radio(key='decision_corpus').set_value(corpus).run()
            self.assertFalse(app.exception)
            self.assertTrue(any('availability-safe calibration' in v.value for v in app.info))
            self.assertTrue(any('learned isotonic maps' in v.value for v in app.markdown))
            self.assertTrue(any(m.value == 'Buy' for m in app.metric if 'day view' in m.label))
        self.assertTrue(any('actual trading-session label endpoints' in v.value for v in app.info))
        self.assertFalse(any(b.label == 'Re-run D_CENTRED now' for b in app.button))

    def test_invalid_response_timeout_refuses_generator_configuration_before_a_request(self):
        with patch.dict(os.environ, {'INVESTIFY_LLM_TIMEOUT': 'invalid fixture value'}):
            app = self.app()
            self.assertTrue(any('generator configuration is invalid' in x.value for x in app.warning))
            self.assertFalse(any(button.key == 'generate_explanation' for button in app.button))

    def test_actual_teacher_view_replays_examples_and_preserves_student_pending_state(self):
        app = self.app()
        self.assertTrue(any(metric.label == 'Accepted teacher examples' and metric.value == '6' for metric in app.metric))
        self.assertTrue(any(metric.label == 'Training examples' and metric.value == '4' for metric in app.metric))
        self.assertTrue(any(metric.label == 'Validation examples' and metric.value == '2' for metric in app.metric))
        self.assertTrue(any('No student has been trained or evaluated' in caption.value for caption in app.caption))
        app.selectbox(key='teacher_record').set_value('fnspid:NVDA:2023-10-09:5d').run()
        self.assertFalse(app.exception)
        self.assertIn('Calibrated confidence in this decision: 52.27%', app.text_area(key='teacher_prose').value)
        self.assertTrue(any(button.key == 'download_teacher_train' for button in app.get('download_button')))

    def test_missing_or_invalid_teacher_evidence_cannot_offer_training_downloads(self):
        for error, message, collection in ((FileNotFoundError('LABELLED missing fixture'), 'Teacher pilot pending', 'info'),
                                           (ValueError('LABELLED invalid fixture'), 'Teacher evidence invalid', 'error')):
            with patch('app.tabs.teacher_study.load_study', side_effect=error):
                app = self.app()
                self.assertTrue(any(message in item.value for item in getattr(app, collection)))
                self.assertFalse(any(button.key in {'download_teacher_train', 'download_teacher_validation'} for button in app.get('download_button')))


if __name__ == '__main__':
    unittest.main()
