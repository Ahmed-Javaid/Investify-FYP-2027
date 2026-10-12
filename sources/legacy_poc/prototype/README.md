# Investify — proposal-stage proof of concept

F26-003-QuantamentalAI · Ahmed Javaid · Rafay Ul Haq · Soban Ahmad

## Run it

```bash
cd poc/prototype
streamlit run app.py
```

Opens on <http://localhost:8501>. Needs `streamlit`, `numpy`, `matplotlib`.
No network, no GPU, no trained model, no API key.

The parts that run real code have tests. No pytest needed:

```bash
cd poc/prototype
python test_prototype.py     # 59 checks, exit 0 on success
```

The two technical spikes run separately and take about two seconds each:

```bash
cd poc && python poc_leakage_spike.py && python poc_risk_profile_spike.py
```

## Why there are two different things here

The committee defines the PoC as *"a high-fidelity functional prototype … a
skeleton of the finished product without actual implementation of the
functionality behind the interface."*

The Selection Guide §12 asks for something different — a focused technical
spike on the riskiest assumption — and says plainly that *"a polished interface
that does not test a technical or workflow risk is not sufficient by itself."*

Those pull in opposite directions, so we satisfy both rather than choosing:

| | What it is | Where |
| --- | --- | --- |
| The prototype | Ten screens, fully navigable, real layout and states | `prototype/app.py` |
| The live path | The verifier, running real code, corruptible on stage | `prototype/verifier.py` |
| Spike 1 | Does a negative control detect leakage when leakage is present? | `../poc_leakage_spike.py` |
| Spike 2 | Do our capacity weights decide the tier, or does the user? | `../poc_risk_profile_spike.py` |

## What is real and what is mocked

The sidebar states this on every screen, because the examiner is entitled to
know. The user journey itself does not announce it.

| Screen | Behind it |
| --- | --- |
| 1. Sign in | Mocked. No credentials stored. |
| 2. Risk capacity | **Real** — `profile_scoring.py` |
| 3. Risk tolerance | **Real** instrument, real scoring |
| 4. Profile summary | **Real** — the binding constraint, FR-7 |
| 5. Choose a company | Mocked list with coverage density |
| 6. Recommendation | Fixture decision record (§10.8, number for number) |
| 7. Verifier report | **REAL — this is the live path** |
| 8. Follow-up questions | Scripted responses |
| 9. Degraded state | **Real** state machine, FR-12 |
| 10. Operator view | Reads the real spike result files |

Deliberately not real at this stage: the trained engine, the sentiment
pipeline, the point-in-time store and the live feeds. Building them properly is
the work of two semesters, and a rushed version would prove nothing about
whether the finished one is correct.

## The demonstration (screen 7, ~30 seconds)

1. Open **7. Verifier report**. All four measures pass; verdict **PASS**.
2. Drag *Stored P(Hold)* from **0.58** to **0.72**.
3. Numeric fidelity drops to **0.75**, below the 0.98 threshold. Verdict flips
   to **FAIL**. The explanation is regenerated once, fails again, and is
   replaced by the deterministic template — which is shown on screen.
4. Press **Reset record**.

Also try dragging *Stored SHAP contribution of `rsi_14`* from −0.06 to
positive: directional consistency drops to 0.67 and the sign check names the
offending sentence.

**Why this is worth more than a passing test:** anyone can show a system
producing correct output. The claim that is hard to believe is that we would
notice if it were wrong.

**Why it can be real this early:** groundedness here is decidable by symbolic
checking, not judged by another model. The verifier needs only a decision
record — a fixture record works exactly as well as a real one.

## The five questions §12 requires

**Spike 1 — leakage detection**

1. *Assumption:* that a negative control detects leakage when leakage is present.
2. *Setup:* 8,856 real daily bars, four arms differing only in temporal
   discipline, identical model and seed, snapshot hashed.
3. *Result:* `poc_results.json`. A deliberately future-peeking feature lifts
   macro-F1 by +0.19 at 1 day and +0.34 at 5 days.
4. *Disproved:* the 1-day control does **not** catch fold-overlap leakage —
   1-day labels do not overlap, so there is nothing for purging to protect.
   Purge/embargo also measured as nearly inert under expanding walk-forward.
5. *Changed:* controls must run at the label geometry of the primary horizon.
   Gate A amended. Purging retained but no longer presented as the primary
   defence. `D_LOOKAHEAD` becomes a permanent CI leak canary.

**Spike 2 — risk-profile weight sensitivity**

1. *Assumption:* that the tier is a property of the user, not of the five
   weights we chose.
2. *Setup:* all 1,200 personas in the input space, 1,000 perturbed weight
   vectors (each weight × U(0.5, 1.5), renormalised), seed 42.
3. *Result:* `poc_risk_results.json`. FR-7 passes over 42,000 pairs with zero
   violations. Tier matches baseline in 94.7% of cells; 65.8% of personas never
   flip under a ±50% perturbation. Equal weights agree 89.9% (κ = 0.829).
4. *Learned:* the weights are inert for most users and decisive for a named
   minority. The hard caps contribute more stability (+37 points) than the
   weights do — and a cap has a citation behind it where a weight does not.
5. *Changed:* caps restated as tier ceilings rather than decimals, which fixed
   an off-by-one that put one cap exactly on a tier cut. Boundary personas are
   published rather than left to be found. §10.8's tolerance figure of 0.68 is
   not attainable under the published Grable–Lytton bands; nearest is 0.67.

## Two deviations from the proposal, both deliberate

**Claim recall is measured against the record, not against the claim list.**
Section 13 defines it as verifiable claims over total claims, which makes it
exactly `1 - unverifiable_rate` — so reporting both measures one thing twice,
and neither catches the failure recall exists to catch ("an explanation that
stays safe by saying almost nothing"). Here it asks: of the top-5 SHAP drivers,
how many did the explanation actually name. The section 10.8 example scores
0.80 on that — exactly the floor.

**Risk capacity carries hard caps as well as weights.** A cap is stated as a
tier ceiling ("this profile cannot be rated above conservative"), not a
decimal. Writing them as decimals put one exactly on a tier cut, so capping a
profile "to conservative" landed it in moderate instead. The caps are anchored
in Carroll (1997); the weights are ours and are not anchored in anything, which
is why spike 2 measures how much they matter.

## Known limitations, stated before being asked

- The Grable–Lytton items here are structurally faithful stand-ins — same
  response formats, same 13–47 raw range. The licensed instrument is
  substituted before any real participant sees it.
- The λ → action-band figures in spike 2 use a synthetic return distribution.
  The real label distribution replaces it at Iteration 2.
- Spike 2 tests whether the tier is *stable*, not whether it is *correct*.
  There is no ground truth for a correct capacity tier — which is the same
  reason the weights cannot be fitted.
- The recommendation on screen 6 comes from a fixture record. No model has
  been trained. NVDA is section 10.8 verbatim; the other seven tickers are
  deterministic jitters of it, bounded so that signs and the driver ranking
  are preserved.
- The claim payload the verifier checks is authored by us, not emitted by a
  language model. This demonstrates that the *checker* is correct — not yet
  that it catches a real model. That is the right scope for proposal stage:
  the verifier is built first, and the explainer is measured against it after.
- The free-prose number sweep accepts a figure that matches *any* value in the
  record, not the specific value the sentence is about. The structured payload
  is the primary path; the sweep is a backstop.
- The Grable-Lytton **scoring key** is a stand-in as well as the item wording.
  The band cut-points are the published ones; the per-item point values are
  not.
