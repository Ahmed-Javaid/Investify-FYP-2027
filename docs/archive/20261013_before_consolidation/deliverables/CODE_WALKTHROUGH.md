# Mid-1 code walkthrough and ownership evidence

This prepares the handbook-required walkthrough; it does not establish that a student has completed it. Actual ownership remains for the team to record.

| Module | Explain at file/function level | Demonstrate a change or boundary |
| --- | --- | --- |
| app/streamlit_app.py, presenter.py | Why one page/step executes; how callbacks keep a case/profile across navigation | Move Decision to Evidence; change source/session and show candidate reset |
| app/presenter_data.py:load_cases | Fixed source registry, duplicate-session refusal, schema validation, artifact-byte identity | Invalid input shows an error and no substitute class |
| decision_record.py:DecisionRecord | Probability sum/argmax and attribution/value invariants; nested mappings are read-only by convention | Explain why a contradictory top contributor cannot enter the UI |
| explain/context.py:build_context | Feature meanings, missing status and raw-score units; no fabricated economic cause | Compare a technical and news row; locate all eleven fields |
| explain/verifier.py:verify | Independent prose and JSON checks, hard contradictions, coverage and strict unsupported prose | Correct JSON beside 1.00% visible confidence still fails |
| explain/pipeline.py:emit | Candidate rejection, retained report and independently checked fallback | Show candidate rejected and verified replacement; explain a template-check failure |
| risk_profile.py:score_profile | Five capacity factors, caps, three tolerance answers, smaller-axis reconciliation | Clear questions; show no assumed profile; identify prototype assumptions |
| risk_comparator.py:build_comparator/score | Earlier scaling split, held-out-only arithmetic, fixed/profile blend | R=0 gives Hold and R=1 Sell on the current example, while XGBoost remains Buy |
| sentiment_receipts.py:compare_bundles | Frozen identities, paired coverage and receipt/logit recomputation | Explain AI-label agreement, two negative references and pending selection |
| teacher_session.py / teacher viewer | Genuine recorded prose versus assembled JSON and deterministic reference | Four/two exports do not establish student training or comprehension benefit |

Questions for each person: what did you personally implement/review; which tools generated parts; what did you change; which tests would fail if your function were removed; what limitation did the evaluation reveal; what would you implement next? Record actual answers and dates in the team/supervisor meeting log. Commit counts and this assistant-written worksheet are not student contribution evidence.
