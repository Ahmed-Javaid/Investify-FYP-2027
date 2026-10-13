# Ahmed Javaid: Mid-1 preparation

22I-2530. Assigned share: **one-third**. Focus: **Temporal integrity, evaluation harness and leakage**.

This is your assigned preparation and defence work. Study the current implementation, practise its boundaries and record what you personally review or change. The packet does not state that you authored all existing code.

## Presentation and live-demo route

Planned speaking time: **five minutes**, including your live-demo actions. Slide numbers refer to the current twelve-slide deck. Follow the deck order and hand over to the next named presenter.

- Slide 1 (30 seconds): introduce the confirmed team and supervisor.
- Slide 3 (60 seconds): bound the recorded prototype and distinguish later milestones.
- Slide 4 (70 seconds): show the Mid-1 evidence and distinguish checks from approval.
- Slide 8 (40 seconds): on Evidence, select one technical feature and one news feature. Identify their recorded value and contribution.
- Slide 10 (100 seconds): explain the chronological experiment, purge boundary, clean result and deliberately leaky canary.

## Code to study

| File | What you should explain |
| --- | --- |
| [code/src/investify/harness/splits.py](../code/src/investify/harness/splits.py) | Chronological split and purge rules |
| [code/src/investify/features/causality_audit.py](../code/src/investify/features/causality_audit.py) | Available-at and future-information checks |
| [code/src/investify/labels.py](../code/src/investify/labels.py) | Five-session targets and label availability |
| [code/src/investify/harness/arms.py](../code/src/investify/harness/arms.py) | Clean arm and deliberately leaky canary |
| [code/app/presenter.py](../code/app/presenter.py) | evidence_view and leakage_view |
| [code/scripts/run_mid1_ci.py](../code/scripts/run_mid1_ci.py) | Shared CI runner, source guards and job receipts |

## Tests and report reading

Read the tests below and explain the failure each one prevents. Existing pass receipts are available; you do not need to rerun paid inference or retrain a model for practice.

- [code/tests/test_splits.py](../code/tests/test_splits.py)
- [code/tests/test_asof_join.py](../code/tests/test_asof_join.py)
- [code/tests/test_purge_label_availability.py](../code/tests/test_purge_label_availability.py)
- [code/tests/test_leak_canary.py](../code/tests/test_leak_canary.py)
- [code/tests/test_ci_runner.py](../code/tests/test_ci_runner.py)

Supporting reading:

- [report/chapters/chapter3_iteration_plan.tex](../report/chapters/chapter3_iteration_plan.tex)
- [report/chapters/chapter6_iteration1.tex](../report/chapters/chapter6_iteration1.tex)
- [report/chapters/chapter8_testing.tex](../report/chapters/chapter8_testing.tex)
- [deliverables/CI_CD_STATUS.md](../deliverables/CI_CD_STATUS.md)

## Facts to keep accurate

- A feature must be available before the decision. A label can depend on later prices but must not enter the feature vector or an earlier fit.
- The clean five-session macro-F1 is 0.2843 versus the training-distribution random comparator at 0.3287.
- The centred canary has lift +0.2104 because it deliberately uses future information. It is a leakage demonstration.
- Local CI replay and ZIP checks are engineering evidence. GitHub/Ubuntu execution and deployment have not occurred.

## Likely defence questions

**Why is a chronological split insufficient by itself?** Labels can cross the fit/evaluation boundary. Explain the purge and when a target becomes available.

**Why keep the leaky result?** It demonstrates detection of a known failure and is explicitly excluded from valid predictive claims.

**What is the difference between session time and availability time?** Session time identifies the market interval. Availability time determines when an input could actually be used.

**What CI/CD exists?** The two shared CI jobs pass locally. Hosted Windows/Ubuntu jobs and artifact retention are configured. A remote run and continuous deployment remain pending.

## Record after practice

- Date and files/functions personally reviewed:
- Demo steps completed and observed results:
- One test boundary explained in your own words:
- Changes personally made, if any:
- Assistance/tools used:
- Questions or failures still needing follow-up:

Also rehearse the entire team route so you can recover if another member needs help. [Shared schedule](MEMBER_PREPARATION_PACK.md).
