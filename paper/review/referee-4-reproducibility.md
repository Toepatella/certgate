# Referee 4 — Reproducibility review

**Manuscript:** *CertGate: finite-sample certified selective prediction for multi-site clinical risk models, with label-shift robustness and explainable abstention*
**Venue:** *Discover Computing* (Springer Nature), Collection "Intelligent Medicine: ML and Explainable AI for Next-Generation Healthcare"
**Referee role:** reproducibility / artifact evaluation
**Materials examined:** `paper/draft.md`, `paper/references.bib`, `README.md`, `requirements.txt`, `certgate/`, `tests/`, `experiments/` including `experiments/out/` and all six embedded PNGs.
**Environment used:** Windows 11, Python 3.13.3, numpy 2.5.0, scipy 1.18.0, scikit-learn 1.9.0, joblib 1.5.3, threadpoolctl 3.6.0, matplotlib 3.11.0, pytest 9.1.1 — i.e. exactly the pinned set in `requirements.txt`.

---

## Summary

The paper proposes a selective-prediction gate ("CertGate") that abstains on low-confidence cases and issues a finite-sample certificate that the error rate among *answered* cases is at most α with confidence 1−δ, where the unit of statistical independence is the **site**, not the record. The machinery is: (i) a data-independent influence cap `g_c = min(n_c, M)` with M = 100 defining an influence-weighted answered-set risk `R_M`, linearised into per-site atoms `Z_c ∈ [0,1]`; (ii) a Waudby-Smith–Ramdas betting martingale over calibration sites, with Ville's inequality giving level δ; (iii) a fixed-sequence threshold walk over 23 thresholds ordered on an auxiliary site split; (iv) two assumption modes — an exchangeable baseline and a BBSE label-shift mode whose confusion-matrix uncertainty is carried in a cluster-bootstrap box and tested at both endpoints of the induced weight interval; (v) exact linear attributions on a logistic head, extended to abstentions via a margin-to-answer. Six synthetic experiments (E1–E6) supply validity, label-shift, a concept-shift negative control, a site-count frontier, an explainability case study, and a per-site-coverage/composition study.

**What I verified.** I ran the suite: `python -m pytest tests -q` → **69 passed in 8.65s**, matching the manuscript's "The test suite is 69/69 green" (§A.3) exactly. I re-derived every aggregate in `experiments/out/summary.md` independently from the raw CSVs and they reconcile to the digit. I traced **every** quantitative claim in the abstract, body, all six figure captions and all four tables against `experiments/out/` — **every one of them matches its artifact**, including three-decimal quantities such as 0.9722, 0.0189/0.4820, 0.0551/0.4915, 1.157/1.161/1.178/1.155, −0.854, 0.0956, 0.0223, 23,325, 1,378.9 and ρ̂ = 0.830. The four Clopper–Pearson intervals are arithmetically correct (I recomputed all four; e.g. 2/200 → [0.0012, 0.0357] vs the stated [0.001, 0.036]). Determinism is real and I confirmed it empirically, not by reading: re-running `--only E5,E6` and `--only E1` into a clean directory reproduced `E1_validity.csv`, `E6_fairness.csv`, `E5_explain.json` and `E6_composition.json` **byte-for-byte**, and even the PNGs match by SHA-256. The parenthetical in §4.5 explaining the 0.9715-vs-0.9722 gap by independently derived seeds is correct (`_rng(1, r)` vs `_rng(4, n_sites, r)`).

This is, by the standards I usually apply, an unusually honest artifact. I found no fabricated number and no number that failed to reproduce.

**Where it fails.** The problems are not in the numbers; they are in the *distance between what the manuscript says the code does and what the code does*, and in what the artifact declines to record. Specifically: two of the six experiments silently change a generator parameter the manuscript presents as frozen (§4.1 states `sep = 2.2`; E2 and E3 run at 1.8, and these are the two experiments producing the paper's most dramatic numbers); the constants that define the experiments are *not* covered by the "pinned by a unit test" pre-registration claim; §6.1 describes a missingness encoder that does not exist anywhere in the package; the provenance block that §A.3 says is embedded in "each report artifact" is written to no file; the decline-reason attribution that §4.3 and §4.5 both lean on is computed and then discarded before any CSV is written; and `certgate/harness.py` — the module computing the hard-violation rate that every validity claim in §4 rests on — has **zero** unit tests. Together these mean a reader can reproduce the paper's numbers exactly and still be unable to check the paper's *explanations* of those numbers.

**Overall assessment.** The artifact is real, deterministic and reproduces the manuscript; the manuscript is not yet an accurate description of the artifact. Every defect below is fixable by disclosure, by serialising diagnostics the code already computes, and by adding tests to an untested module — no new science is required. I recommend major revision, in the specific sense that the revision is mechanical but extensive and must be verified against a re-run.

---

## Major points

### R4-01 — Two experiments silently change the generator; §4.1 presents one frozen specification

> §4.1, Generator: "The cohort follows the specification frozen in `data.py`: 208 collection sites … with the two class means separated by $\mathrm{sep} = 2.2$ along that direction"

`certgate/data.py` `SimConfig` does default to `sep: float = 2.2`, and E1, E4, E5, E6 use `SimConfig()`. But `experiments/run_synthetic.py` line 40 declares `SHIFT_SEP = 1.8  # realistic head so shift bites`, and both `run_E2` (line 195) and `run_E3` (line 264) instantiate `cfg = SimConfig(sep=SHIFT_SEP)`. The class separation — the single parameter that sets how discriminative the head is, and therefore how far a shift can push the answered-set error — is reduced by 18% for exactly the two experiments that produce the manuscript's headline failure numbers (48.5% baseline hard-violation, 83% concept-shift hard-violation).

Neither §4.3 nor §4.4 mentions this. §4.1 asserts a single frozen cohort spec and the reader is entitled to assume E1–E6 share it. The code comment ("realistic head so shift bites") is candid about the motivation, which makes the manuscript's silence worse rather than better: an experimenter chose a generator setting because it made the effect appear, and the paper does not say so.

*Fix:* state `sep = 1.8` for E2/E3 in §4.3/§4.4 and in §4.1's setup paragraph, give the rationale that appears in the code comment, and — because this is the obvious reviewer question — report the E2/E3 rates at `sep = 2.2` as a sensitivity check.

### R4-02 — The pre-registration claim does not cover the constants that define the experiments

> §3.2: "All constants that govern the procedure — split fractions, budget ladder, influence cap, threshold grid, betting-test parameters, and decline thresholds — are fixed a priori and pinned to their literal values by a unit test, so any drift fails continuous integration. This is a lightweight, machine-verifiable substitute for pre-registration"
> §A.3 repeats: "The frozen design constants … are pinned to their literal values by a unit test, so any drift fails continuous integration."

`tests/test_constants.py` imports only `certgate.constants` and pins exactly the 19 scalars in that module. It pins nothing else. Outside its reach and unpinned by any test:

- `experiments/run_synthetic.py`: `ANCHOR_SITES = 208`, `SHIFT_SEP = 1.8`, `SHIFT_BASE = 0.22`, `CONCEPT_INTERCEPT = 2.0`, `QUICK_SWEEP`, `FULL_SWEEP = (60, 100, 150, 208, 300, 400)`, and the replication count `R = 10 if quick else 200` (inline in each runner).
- `certgate/data.py` `SimConfig` defaults: `d=8, sep=2.2, base_rate=0.095, s_u=0.5, size_mu=6.0, size_sigma=1.1, size_lo=20, size_hi=5000`. §4.1 calls these "the specification frozen in `data.py`" — nothing freezes them. I grepped `tests/`: no test asserts any `SimConfig` default value. `SimConfig()` is merely *constructed* in five tests.
- `certgate/report.py` `_bootstrap_estimate(..., n_boot=500)`.

So the pre-registration substitute pins the estimator's internals and leaves the experimental design — cohort, shift magnitude, tilt magnitude, sweep points, replication count — free to move without a red test. This is precisely the degrees of freedom §3.2 claims to have removed. Given R4-01 shows one of these unpinned values *was* set to make an effect appear, this is not hypothetical.

*Fix:* move the experiment constants into `certgate/constants.py` (or a sibling frozen module) and extend `test_constants.py` to pin them literally, including `SimConfig`'s defaults; then §3.2's claim becomes true.

### R4-03 — §6.1 describes a missingness encoder that does not exist in the artifact

> §6.1: "*Missingness is handled without a positivity diagnostic.* Missing values pass through the frozen encoder's imputation-and-indicator scheme; we do not add a dedicated positivity (overlap) diagnostic"

There is no encoder, no imputation, and no missingness indicator anywhere in the package. I grepped `certgate/`, `examples/`, `experiments/`, `tests/` for `imput|indicator|encoder|missing`: the only hits are docstring prose and error messages. The actual behaviour is the opposite of what the sentence describes — `certgate/validate.py:139` raises `CohortError("make_cohort: x contains non-finite values (NaN/inf)")` and `certgate/pipeline.py:110` raises `ValueError(... reason=nonfinite-features)`. Missing values do not "pass through"; they abort the run.

This is the one place in the manuscript where a described component is entirely absent from the code. It is in the limitations section, which makes it a gratuitous liability: the honest limitation is stronger than the fictional one.

*Fix:* replace with the truth — CertGate accepts only complete feature matrices and rejects non-finite values loudly at the boundary; handling missingness (and the positivity diagnostic that would accompany it) is future work.

### R4-04 — "Every experiment … replicates over R = 200" is false for E5 and E6

> §4.1, Replication design: "Every experiment runs in mode FULL under protocol seed 20260721, over the $\alpha \in \{0.05, 0.10\}$ ladder at confidence $1-\delta$ with $\delta = 0.05$, and replicates over $R = 200$ independent calibration draws."

`run_E5` (`experiments/run_synthetic.py:398`) and `run_E6` (line 461) take a single `rng = _rng(5)` / `_rng(6)`, draw one cohort, and produce one deployment. Neither takes the `R` loop that E1–E4 take, and neither accepts `quick` as anything but an ignored argument. Every number in §4.6 and §4.7 — the global importances, the three case studies, the abstention profile, Tables 2 and 3, Figures 5 and 6 — comes from **one** draw with **no** replication and therefore has no sampling uncertainty attached, in a paper whose §4.1 explicitly promises Clopper–Pearson intervals on its rates.

*Fix:* scope the sentence ("E1–E4 replicate over R = 200; E5 and E6 are single-draw case studies"), and either replicate E5/E6 or label their tables as illustrative.

### R4-05 — The provenance block is never written to any released artifact

> §A.3: "each report artifact embeds a provenance block recording package versions, seeds, and input hashes."
> §3.10: "Package versions, the seeding rule, and the provenance block are detailed in Appendix A.3."

`certgate/report.provenance()` does construct exactly such a block, and `run_certgate` attaches it to the returned report dict (`pipeline.py:130, 191`). But `experiments/run_synthetic.py` never reads `rep["provenance"]`. `_cert_eval` ignores it; `_write_csv` writes fixed field lists that exclude it; `E5_explain.json` and `E6_composition.json` are assembled from explicit payload dicts that exclude it; `summary.md` excludes it. I confirmed by inspection of all eight files in `experiments/out/`: not one contains a package version, an input hash, or a Python version.

So the reproducibility claim reduces to "the code can compute provenance", not "the released artifacts carry it". For a reader trying to establish that `experiments/out/summary.md` was produced by the code as released and the environment as pinned, there is nothing in the artifact to check.

*Fix:* serialise `rep["provenance"]` (or a run-level equivalent) into `summary.md` and/or a `provenance.json` beside the CSVs, and re-run before submission.

### R4-06 — The decline-reason attribution the manuscript leans on is computed and then discarded

> §4.5: "The 60- and 100-site points are declined, and the reason is specific: the minimum-cluster gate counts only record-carrying sites and requires 50 of them, so any run with fewer than roughly 125 sites yields a ~40% calibration share below 50 clusters and is refused by that gate — **not by the betting test's information floor**. We say so explicitly because the two failure modes have different remedies."

The arithmetic is right (`MIN_CAL_CLUSTERS/SPLIT_FRACTIONS[2] = 50/0.40 = 125`; at 100 sites `n_cal = 40 < 50`). But the *observation* is nowhere in the artifact. `_cert_eval` computes `out["decline_reason"]` (`run_synthetic.py:82–86`), including the structural gate reason for fully-gated reports — and then every `_write_csv` field list drops it. I checked the headers directly:

```
E4_site_sweep.csv:      n_sites,draw,alpha,certified,tau,coverage,n_answered,answered_err_rate,hard
E1_validity.csv:        draw,n_sites,alpha,certified,tau,coverage,n_answered,answered_err_rate,hard,exceed,deploy_mode
E3_concept_shift.csv:   draw,alpha,certified,tau,coverage,n_answered,answered_err_rate,hard,exceed,deploy_mode
```

The string `insufficient-clusters` occurs **zero times** across all five CSVs. `summary.md`'s `gate_note` is not an observation either — `run_synthetic.py:370–375` derives it from `n_sites < 125` by arithmetic, not from any recorded reason. A reader cannot distinguish "refused by the cluster gate" from "refused by the betting test" anywhere in `experiments/out/`, which is exactly the distinction §4.5 says it is making explicitly.

*Fix:* add `decline_reason` to the E1/E3/E4 CSV field lists — the value is already in the row dict — and re-run.

### R4-07 — E2's headline "honest decline" is 191/191 generic walk failure; the three named BBSE declines never fire

> §3.6 devotes a paragraph to three declines: "(i) the worst-case confusion gap $(c_1 - c_0) < 0.10$ … (ii) fewer than 2,000 valid resamples within 4,000 attempts … (iii) $q$ outside the box's $[c_{0,\text{lo}}, c_{1,\text{hi}}]$ range"
> §4.3: "BBSE declines the remaining 95.5% of draws (decline rate 0.955) rather than issue an unsupported certificate"

`E2_label_shift.csv` carries a `bbse_reason` column. I tabulated it at α = 0.10: **191 × `failsafe`, 9 × certified.** Zero `bbse-ill-conditioned`, zero `bbse-degenerate-bootstrap`, zero `bbse-misspecified`. `failsafe` is set in `shift.certify_bbse:216` when the walk certifies no threshold — the same generic outcome the exchangeable baseline would report. The three-decline machinery described at length in §3.6 and Appendix A.2 is exercised only in unit tests and fires zero times in every reported experiment.

That matters because it changes what E2 demonstrates. §4.3's framing ("rather than issue an unsupported certificate") reads as principled refusal by the label-shift diagnostics. What the artifact shows is that the BBSE walk simply lost the bet — unsurprising, since it must reject at *both* endpoints of `[ρ_lo, ρ_hi]` at `δ_bet = 0.025`, i.e. two tests at half the baseline's budget on positive-upweighted atoms. An equally consistent reading of "0 certify-and-violate in 200" is that the mode is underpowered rather than correct, and the artifact cannot arbitrate: `fit_bbse` computes `rho_lo`, `rho_hi`, `rho_point`, `gap_lo`, `c0_ci`, `c1_ci`, `pi_s_ci`, `n_boot`, `n_attempts` into `BBSEFit.diagnostics` (`shift.py:118–124, 148`) and `run_synthetic.py` writes **none** of them.

*Fix:* write the BBSE diagnostics into `E2_label_shift.csv` (at minimum ρ̂, ρ_lo, ρ_hi, gap_lo, and which endpoint failed), report the interval widths in §4.3, and soften the causal language to what the artifact supports.

### R4-08 — Clopper–Pearson intervals exist nowhere in the artifact, and the paper's central safety number gets none

> §4.1: "Because every rate below is a proportion over $R = 200$ independent draws, we accompany the primary rates with exact (Clopper–Pearson) 95% confidence intervals."

Two problems.

*(a) Provenance.* No Clopper–Pearson computation exists anywhere in the released code. `run_synthetic.py` imports nothing from `scipy.stats`; `summary.md` contains no interval. The four intervals in §4.2–§4.4 were computed off-artifact. I recomputed all four and they are **correct** — 2/200 → [0.0012, 0.0357] vs "[0.001, 0.036]"; 97/200 → [0.4139, 0.5565] vs "[0.414, 0.557]"; 0/200 → [0, 0.0183] vs "[0, 0.018]"; 166/200 → [0.7706, 0.8793] vs "[0.771, 0.879]" — but they are numbers a reader following §A.3's "one command" cannot regenerate.

*(b) Selective application.* The one rate the paper's safety argument actually turns on gets no interval:

> §4.3: "conditioning on the 9 draws that did certify ($n_{\text{certified}} = 9$), the hard-violation rate among them is 0.0."

0 of 9 has an exact 95% upper bound of **0.336** — 6.7× the δ = 0.05 budget. The manuscript supplies the flattering interval for the joint event over 200 and omits the unflattering one for the conditional over 9, in the same paragraph, under a protocol sentence promising intervals on primary rates. Table 4's certify rates (all proportions over R = 200) likewise carry no intervals.

*Fix:* compute the intervals inside `run_synthetic.py` so they land in `summary.md`, and report [0, 0.336] beside the conditional 0.0 in §4.3.

### R4-09 — "S_cal is touched exactly once" is false; the code touches it four times

> §3.2: "$S_{\text{cal}}$ (40%, used for certification only and touched exactly once, by the certification test)"
> §4.1 repeats: "$S_{\text{cal}}$ is touched exactly once, by the certification test."

In `run_certgate`, `cal` is consumed by: (1) the baseline walk `_baseline_walk` and/or `certify_bbse`; (2) `report._bootstrap_estimate(head, cal, tau, ...)` — a 500-draw cluster bootstrap over `cal` sites; (3) `report._rm_vs_unweighted(head, cal, tau, ...)`; (4) `report._capped_influence_share(cal)`. Plus `n_carrying = int((cal.site_sizes > 0).sum())` at `pipeline.py:134` and again at `report.py:185`.

Uses (2)–(4) feed the *estimated* and *diagnostic* tiers only and do not flow back into the certificate, so I do not allege a validity leak. But the manuscript makes a flat factual claim about the code and the code contradicts it, in two places, and the claim is load-bearing for the data-discipline argument.

*Fix:* "S_cal enters the certified path exactly once, by the certification test; the estimated and diagnostic tiers also read S_cal, downstream of and without feedback into the certificate."

### R4-10 — The E5 "cohort-level" abstention driver rests on n = 2 declined cases

> §4.6: "At the cohort level, feature 0 is the dominant abstention driver: its mean absolute attribution is 0.868 on answered cases but 1.722 on declined cases, the largest answered-to-declined gap of any feature (gap $-0.854$…). Declines are **systematically** the cases where feature 0's pull leaves the decision contested"
> Figure 5 caption: "feature 0 shows the largest gap ($-0.854$; 0.868 answered vs 1.722 declined), identifying it as the dominant systematic abstention driver."

Every one of those numbers matches `E5_explain.json` to the digit. The denominator is the problem: `"n_declined": 2`. `1.722` is the mean of two numbers, quoted to three decimal places, and the word "systematically" is doing work no sample of size two can support. The same paragraph does say "answering 200 cases and declining 2" — but the cohort-level sentence and the Figure 5 caption, which is where a reader skimming will land, both omit it.

Compounding this: `tau_star` in E5 is **0.55 = `TAU_GRID[0]`**, the minimum of the threshold grid. The walk certified the entire grid, so the operating point was set by the grid's lower boundary, not by the certificate. The two declines are a grid-boundary artifact, and §4.6 presents the deployment as if 0.55 were a certified operating choice.

*Fix:* state n = 2 in the cohort-level sentence and the caption, drop "systematically", disclose that τ* = 0.55 is the grid floor, and — if a cohort-level abstention profile is wanted — run E5 at a threshold that produces a usable declined population.

### R4-11 — `certgate/harness.py` has zero tests: the instrumentation behind every validity number is unverified

> §3.9: "A certificate counts as violated only when the one-sided 95% Wilson lower confidence bound on the target pool's answered error exceeds $\alpha$ [@wilson1927]."

Every hard-violation number in the paper — 0.01, 0.485, 0.0, 0.83 — is produced by `harness.hard_violation`, which calls `harness.wilson_lcb`. Every binomial reference in Table 1 and Figure 1 is produced by `harness.exceedance_reference`. I grepped `tests/`: **no test file imports `certgate.harness`**, and neither `wilson_lcb`, `hard_violation`, nor `exceedance_reference` is asserted on anywhere. `SIZE_BINS` is likewise unpinned despite defining Table 1's and Table 2's rows.

There are obvious, cheap tests that are missing: `wilson_lcb(k, n)` against a textbook value; monotonicity in `k`; the `n <= 0 → 0.0` branch; `exceedance_reference` against `1 - binom.cdf(floor(αn), n, α)` for small n; the `k_thresh` off-by-one guarded by the `+1e-9` fudge at `harness.py:57`. A sign error in `wilson_lcb` would silently move every validity number in §4 and no test would fire.

This is my single largest credibility concern about the suite. The statistical *core* is well tested (see below); the statistical *scoring* is not tested at all.

*Fix:* add unit tests for all three functions plus `SIZE_BINS`.

### R4-12 — A test whose assertion cannot fail

> `tests/test_shift.py:72–76`, in `test_pure_label_shift_falsifiability_and_bbse`:
> ```python
> # 3. BBSE certifies-or-declines (never a silent certify-and-violate).
> rb = certify_bbse(head, fit, cal, alpha, "tgt")
> assert (rb["reason"] is None) or (rb["reason"] in {
>     "failsafe", "bbse-degenerate-bootstrap", "bbse-ill-conditioned",
>     "bbse-misspecified"})
> ```

`certify_bbse` can only ever return `reason ∈ {None, "failsafe", fit.reason}`, and step 1 of the same test has already asserted `not fit.declined`. The assertion enumerates the complete range of the function. It is a tautology and cannot fail under any code change short of inventing a fifth reason string.

The docstring above it claims it checks "never a silent certify-and-violate" — but the test never evaluates the target-pool risk under the BBSE-certified threshold, which is what that claim would require. Steps 1 and 2 of the same test are genuinely good (the ρ interval must cover the true odds ratio; the baseline must be shown to certify *and* violate before BBSE is judged). Step 3 is decoration.

*Fix:* if `rb["reason"] is None`, compute the target answered-set risk at `TAU_GRID[rb["tau_idx"]]` and assert it does not exceed α — that is the assertion the docstring promises.

### R4-13 — E3's "the harness first verifies the poison" is not the order the code runs in, and "true risk" is a realized rate

> §4.4: "the harness first *verifies the poison*: it confirms that the tilt pushes the true mean answered risk to 0.2022, above the $\alpha = 0.10$ budget"
> §5.1: "E3's verified tilt (true answered risk 0.2022, above $\alpha$)"

`run_E3` (`run_synthetic.py:267–293`) runs the full 200-draw loop, collects `ev["answered_err_rate"]` **only for draws that certified at α = 0.10**, means them, and only then tests `poisonous = verified > 0.10`. The check is post hoc on the same draws that produce the 83% figure, conditioned on certification, and evaluated at the certified τ. The manuscript's claim that the abort happens "before any output is written" is true (the `raise RuntimeError` precedes `_write_csv`); the claim that the harness verifies the poison *first* is not.

Second: 0.2022 is the mean of 200 *realized* answered error rates, not a risk parameter. The paper elsewhere insists on exactly this distinction — §3.9 and §5.1 both hammer that the certificate bounds "the answered-set error parameter, not any single batch's realized error count". Calling this quantity "true risk" and "the true mean answered risk" contradicts the paper's own vocabulary, in the one experiment whose entire point is definitional rigour.

Third: the abort path itself (`reason=e3-control-not-poisonous`) is untested. `run_synthetic.py` is imported by no test file; nothing verifies that a de-poisoned tilt actually raises. §4.4 calls the check "enforced, not decorative" — that is an assertion about code with no test behind it.

*Fix:* describe the check as what it is (a post-hoc gate on the run's own output that aborts before writing); rename 0.2022 to "mean realized answered error"; add a test that drives `run_E3`'s verification branch with a null tilt.

### R4-14 — Only three of the guarantee's five clauses are pinned by a test

> §3.7: "The guarantee the certificate makes carries five clauses, all of which survive into the deployed guarantee text." (per-target-site scope; shared 1−δ event; parameter-not-realized-count; concept shift out of scope; BBSE bootstrap asymptotic)

`report._statement` does emit all five (`report.py:65–82`). But `tests/test_pipeline.py:42–45` checks only three substrings:

```python
assert "per-target-site" in stmt
assert "NOT a bound" in stmt
assert "OUT OF SCOPE" in stmt
```

Unpinned: clause (2), "all sites certified from one calibration draw share the same 1-0.05 event", and clause (5), the BBSE asymptotic-bootstrap disclosure — which is only emitted when `"bbse" in modes`, and the only end-to-end test that inspects `statement` runs an in-distribution fixture. A regression that dropped the shared-δ clause, or that dropped the asymptotic caveat from BBSE-deployed rows, passes green. Given that §3.7 and §6.1 both make the asymptotic disclosure a centrepiece of the paper's honesty posture, this is the clause most in need of a test.

*Fix:* assert all five substrings, and add a case where the deployed mode is BBSE.

### R4-15 — "exact Shapley values" is stronger than the cited source supports for this generator

> §3.8: "For a linear model these attributions are exact Shapley values, with no approximation or sampling [@lundberg2017shap]."
> §4.6 repeats: "genuine Shapley values, not sampled approximations [@lundberg2017shap]".

Lundberg & Lee's linear-model result (their "Linear SHAP") gives `φ_j = w_j(x_j − E[x_j])` **under an assumption of feature independence**. The manuscript's `φ_j(x) = w_j(x_j − μ_j)` is exactly that expression, and the code (`explain.py:48`, `phi = head.coef * z`) implements it. But §4.1's generator makes the features marginally *dependent*: `x | y ~ N(μ_y, I)` with `μ_1 = −μ_0 = (sep/2)·v` supported on coordinates 0–3, so marginally `Cov(x_i, x_j) = μ_i μ_j·Var(1{y=1}) ≠ 0` for every pair among features 0–3. Under dependence the Shapley value with the conditional-expectation value function is not `w_j(x_j − μ_j)`, and the cited paper says so.

The additive decomposition *is* exact (`sum(φ) + base == logit` to machine precision, correctly pinned by `test_explain.py::test_additive_attribution_is_exact`). "Exact Shapley values" is the overreach, and it is a citation that does not support the sentence hanging on it — in a collection whose central emphasis is explainability, where this claim will be read closely.

*Fix:* say the attributions are the exact additive decomposition of the logit, and that they coincide with Shapley values under the interventional/independent-feature value function, citing Lundberg & Lee for that qualified statement.

### R4-16 — E6's certified deployment fires the label-shift correction on an unshifted cohort, with ρ̂ = 0.830

> §4.7, Table 3: "BBSE-implied true-class | 0.0591 | 1,378.9 expected ($\hat{\rho} = 0.830$) | estimated, label-shift assumption"

`run_E6` builds its cohort with `SimConfig()` and `draw_cohort(cfg, 40, rng, site_label_prefix="e6t")` — no `label_base_rate`, no tilt. Source and target share the generative prevalence, so the true odds ratio is ρ = 1. The BBSE point estimate is 0.8297. `composition()` is called with `rho_point` only when `op["deploy_mode"] == "bbse"` (`run_synthetic.py:502–503`), so the presence of the BBSE row in Table 3 tells us the operative deployment at τ* = 0.77 was tagged **label shift**, not exchangeability — on data with no shift.

The manuscript reads the resulting 0.0591-vs-0.0630 gap as "the visible cost of the label-shift correction's estimation step", which is fair as far as it goes. What it does not report is that the correction estimated a 17% prevalence movement where the truth is none, and that the E6 deployment therefore carries the label-shift assumption tag and its asymptotic-bootstrap caveat. Both facts are directly relevant to §3.6's "the mode is part of the guarantee text" argument, and both are recoverable from the artifact but absent from the paper.

*Fix:* state E6's deploy mode and τ* provenance, report ρ̂ = 0.830 against the true ρ = 1, and say what that implies about the correction's behaviour in the null case.

### R4-17 — Data and code availability: nothing named, nothing licensed, nothing packaged

> Data availability: "All data used in this study are synthetic and generated deterministically by the included code, publicly available at **[CODE REPOSITORY URL — to be added]**."

This is not an author-placeholder exemption; it is the availability statement itself. Against repository reality:

- No repository URL, no DOI, no archival deposit (Zenodo/Software Heritage) named anywhere in the manuscript.
- **No licence file.** I checked: no `LICENSE`, no `COPYING`, no licence header in any source file. Absent a licence, a reader who obtains the code has no right to run, modify or redistribute it, which makes "publicly available" hollow even once a URL is added. Springer Nature's research-data policy will ask for this.
- No `pyproject.toml`, `setup.py` or `setup.cfg`. The package is importable only because a deliberately empty root `conftest.py` puts the project root on `sys.path` for pytest; `python -m experiments.run_synthetic` works only from the repository root. §A.3's "The full grid runs from a single command" is true only with that unstated precondition.
- The working tree is **not** under version control (no `.git`), so there is no commit hash to cite and no way to bind the manuscript to a code state.
- `README.md` — the reader-facing instruction set — points repeatedly outside the repository: `../audit/readiness-report.md` (line 3), `../testbed/` and `../PROTOCOL.md` (line 105), `../testbed/` again in the repository map narrative. None of these paths exists. Source docstrings do the same: `certify.py:4` ("ported verbatim from the audited v1 reference (`../testbed/certify.py`)"), `shift.py:8` ("`../testbed/modes.py`"), `report.py:87` ("v1 report.py:14-35"), `data.py:3` ("`../testbed/generator.py`"). A reader who clones the release inherits a provenance chain to a codebase that is not in the release.
- `README.md` further points readers at `SPEC.md`, `METHODS.md` and `PAPER-OUTLINE.md` as if they were part of the deliverable; whether those ship is an editorial decision, but the README currently presumes they do.

*Fix:* deposit the code with a DOI, add an OSI licence, add a minimal `pyproject.toml`, cite the archived version and commit hash in the availability statement, and strip or resolve the `../testbed`, `../audit`, `../PROTOCOL.md` references in README and docstrings.

### R4-18 — Three of the six figures render annotations outside the plot area; Figure 3's title is clipped

I opened all six PNGs.

- **Figure 3 (`E3_concept_shift.png`) is broken.** The axes occupy only the right half of the canvas, the left half is blank, the "no certificates" annotation for the α = 0.05 rung sits far outside the axes in that blank margin, and the title is **truncated mid-word**: it renders as "E3 concept-shift negative control (certificate shou". This is the figure the manuscript uses to carry its negative-control argument.
- **Figure 1 left panel** shows a single x-tick ("0.1"); the α = 0.05 category has no tick and its "no certificates" annotation is rendered outside the axes at the far left. The caption claims the panel shows "the $\alpha = 0.05$ rung issues no certificates at 208 sites" — visually it does not.
- **Figure 2** renders two "no certificates" annotations for α = 0.05, one inside the axes and one clipped outside at the far left. Separately, the caption states "The BBSE bar (blue) is at zero" — a zero-height bar is visually identical to *absent*, and absence is the encoding this same figure uses for "no certificates". A reader cannot distinguish "BBSE certified 9 draws with 0 violations" from "BBSE issued nothing".

The cause is visible in the code: `ax.text(i, ...)` / `ax.text(xpos[i] + dx, ...)` places the annotation in data coordinates at a category whose bar is `np.nan`, so it falls outside the axes limits matplotlib computes, and `tight_layout` then reflows around it (`run_synthetic.py:170–173, 246–250, 316–319`).

*Fix:* annotate in axes coordinates (`transform=ax.transAxes`) or draw a zero-height bar with a hatch/label; and for Figure 2 mark the BBSE zero explicitly (e.g. an annotated "0.000 (9 certified)" label).

---

## Minor points

### R4-19 — §3.6 "each at full δ" contradicts §3.5 and the code

> §3.6, Combination: "The modes run as alternatives, each at full $\delta$, and we deploy the most conservative certified threshold."

§3.5 says the opposite two paragraphs earlier — "each is tested at the mode's full betting budget ($\delta$ for the baseline, $\delta_{\text{bet}}$ in the label-shift mode)" — and the code agrees with §3.5: `_baseline_walk` passes `DELTA` (0.05), `certify_bbse` passes `BBSE_DELTA_BET` (0.025). Reword §3.6.

### R4-20 — An undocumented decline gate: `MIN_ANSWERABLE = 10`

`pipeline.py:149` refuses any target pool with fewer than 10 records and returns an all-declined report with `reason="pool-too-small"`. The manuscript documents the minimum-cluster gate (§3.3, §4.5) and BBSE's three declines (§3.6) but never mentions this fourth gate, which is the one a real deployment with small daily batches would hit first.

### R4-21 — Constants that govern the procedure but appear nowhere in §3.2's enumeration

§3.2 enumerates "split fractions, budget ladder, influence cap, threshold grid, betting-test parameters, and decline thresholds". Pinned in `constants.py` but absent from the manuscript: `PI_CLIP = 1e-4` (the prevalence clip inside `rho_of`, alluded to obliquely in A.2's "the clipped $\rho$" but never valued), `SD_REL_TOL = 1e-9`, `HEAD_MAX_ITER = 2000`, `MIN_ANSWERABLE = 10`, `BBSE_BONFERRONI = 3` (implied by "$\delta_{\text{conf}}/3$" but not named). Also undocumented: `report._bootstrap_estimate(n_boot=500)`.

### R4-22 — "byte-identical certificates" versus the timestamp in the provenance block

> §3.10 / §4.1 / §A.3: "identical inputs yielding byte-identical certificates" / "Identical inputs produce byte-identical certificates."

`report.provenance` emits `timestamp_utc`, and its own docstring says "The timestamp is intentionally the only non-deterministic field, so callers comparing runs for determinism must exclude it." The pinning test `test_pipeline.py::test_two_runs_byte_identical_certified_tiers` compares only `r["certified"]`, not the report. The claim is true of the certified tier and false of the report object; say which. (Empirically the *experiment outputs* are byte-identical — I verified this — because they never serialise the provenance block, which is R4-05.)

### R4-23 — Size-bin notation is off by one endpoint

§3.9 writes the bins as "$\{<30,\ 30\text{–}100,\ 100\text{–}300,\ >300\}$". `harness.SIZE_BINS` is `((0,30),(30,100),(100,300),(300,inf))` and Tables 1–2 render the last as `[300, ∞)`, i.e. **≥** 300. Use `≥300` in §3.9.

### R4-24 — "$\sim\!10^5$ record-level" overstates the calibration pool by roughly 2×

> §3.1: "resting on roughly eighty site-level observations, not the $\sim\!10^5$ record-level ones a naive analysis would claim"; §5.2 repeats "not from the $\sim\!10^5$ records they contain".

I instantiated the E1 draw-0 cohort: 208 sites, 137,533 records total, split 83/42/83 sites and 55,538 / 30,581 / 51,414 records. The calibration pool — the one the sentence is contrasting against its 83 clusters — holds ~5.1 × 10⁴. The whole cohort is ~1.4 × 10⁵. As written the sentence attaches 10⁵ to the calibration records. Either say "the ~5 × 10⁴ calibration records" or make the contrast explicitly against the full cohort.

### R4-25 — Figure 4's right panel plots 0.0 where Table 4 prints "—"

Table 4's caption says "'—' where nothing certifies", and the table correctly shows "—" at the four non-certifying grid points. `E4_site_sweep.png`'s right panel plots those same points at coverage **0.0** (`run_synthetic.py:362–364` rounds `0.0` when `certs` is empty), so the figure shows a measured-looking zero-coverage regime that the table declares undefined. Mask the non-certifying points.

### R4-26 — The E1–E4 CSVs emit literal `nan` tokens

I counted bare `nan` tokens: `E1_validity.csv` 200, `E2_label_shift.csv` 591, `E3_concept_shift.csv` 200, `E4_site_sweep.csv` 1,340 — 2,331 in total, produced by `answered_err_rate=float("nan")` in `_cert_eval:78`. This is inconsistent with the artifact's own stated convention: `run_synthetic.py:151–152` and `:488–490` go out of their way to emit `None`/`null` rather than NaN in the JSON/rollup paths, explicitly "never NaN: NaN is an invalid JSON token that breaks downstream parsers and reads as an error in a paper table". The CSV path was not brought into line. Any reader loading these with a strict parser gets a token the authors themselves have flagged as hostile.

### R4-27 — Bibliography key/year mismatches

Not fatal, but a referee checking citations trips on all three: `ifac2025abstainexplain` is keyed 2025 and the entry is `year = {2024}`, ECML PKDD 2024 (nothing IFAC about it); `l2lore2025` is keyed 2025 with `year = {2024}`; `angelopoulos2021ltt` is keyed 2021 with `year = {2025}` (Annals of Applied Statistics). Since the manuscript cites by key and the rendered bibliography will show the year, in-text/reference-list year mismatches will surface at proof.

### R4-28 — The permutation is described in the singular; the code draws one per threshold, with a short-circuit

> §3.4: "The processing order is a deterministic, SHA-256-seeded permutation of the calibration sites, data-independent so it preserves predictability and cannot be chosen to flatter the outcome."

`fixed_sequence_walk` passes one `rng` object to every `wsr_reject` call, and `wsr_reject` calls `rng.permutation(z)`, so the walk consumes a fresh permutation per threshold from an advancing stream — the *number* of permutations drawn is data-dependent (the walk breaks at first failure). Separately, `certify_bbse:207` uses `all(...)` over a generator, which short-circuits: when the `ρ_lo` endpoint fails, the `ρ_hi` stream never advances. Neither affects validity (each test is independently level-δ, and the walk breaks anyway), and `shift.py:180–183`'s docstring claims the per-endpoint streams make the result "order-independent" — but §3.4's singular "a permutation" is not what happens.

### R4-29 — `README.md` is stale as an instruction set

The README states "Suite 53/53 green (~4s)" (line 26) and "`python -m pytest tests -q`  # ~2 min" (line 94). The actual suite is 69 tests in 8.65 s. The manuscript's §A.3 correctly says 69/69. A reader following the README will believe they are running a different suite than the paper describes. (I flag this as evidence about the artifact's documentation, not as a claim about the work.)

### R4-30 — Target-pool structure is undisclosed for E1, E3, E5

E1, E3 and E5 each certify against a target pool consisting of **one** freshly drawn site (`draw_cohort(cfg, 1, rng, ...)` at `run_synthetic.py:117, 270, 402`); E5's pool holds 202 records. E6 discloses its 40 target sites; the others say nothing. Since §3.7's clause (1) scopes the guarantee per target site, the reader should be told that E1's 200 "pools" are 200 single-site pools, and that E5's case study is one site.

### R4-31 — `experiments/run_synthetic.py` has no test coverage whatsoever

No test file imports `experiments`. Untested: `_rate` (the `None`-for-zero-denominator convention that produces the `null`s in `summary.md`), `_cert_eval`, the E3 poison-verification abort (§4.4 calls it "enforced"), `_existing_summary_blocks` (the regex-based merge that preserves un-recomputed sections of `summary.md` — a silent-corruption risk on partial re-runs), and every figure/CSV writer. The 632-line file that produces every number in §4 is entirely outside the 69-test suite.

### R4-32 — The type-I boundary test's tolerance is 60% above nominal

> `tests/test_certify.py:70–76`: `"""Boundary null Bernoulli(alpha) at n=80, 800 reps, fixed seed. Level 5%; empirical rate must stay <= 0.08 (documented tolerance)."""` … `assert rej / 800 <= 0.08`

This is a real statistical test of a real property (`Z ~ Bernoulli(0.05)` sits exactly at the null boundary) and I credit it — but the assertion admits a true level of ~0.065 with ~97% probability. §A.1(iv) says "The test's boundary behaviour (type-I error at $\mathbb{E}[Z] = \alpha$) is additionally pinned by the unit test suite"; what is pinned is "not grossly anti-conservative at one seed", not level 0.05. Either tighten (more reps, or several seeds) or scope the manuscript sentence to what is actually pinned.

### R4-33 — Repetition of the three headline numbers

0.9722 / 0.01 (2 of 200), 48.5% / 95.5%, and 83% each appear five times: abstract, §1, §4, §5.1, and a figure caption. 0.0551-vs-0.4915 appears three times. Nothing is *wrong* — I checked each instance against the artifact and all match — but the captions restate body numbers verbatim rather than describing what the panel shows, which is both padding and the mechanism by which caption/body drift usually enters at revision. Trim the captions to figure-specific content.

### R4-34 — Several load-bearing citations are unrefereed 2026 preprints, one carrying a specific number I cannot check

> §2.4: "certified record-level selective-risk rules overrun their budget by **9–30%** under grouped deployment [@zhou2026falsesense]"

`zhou2026falsesense` (arXiv 2606.15153) is an unrefereed preprint, as are `triage2026audit` (2605.20956), `yu2026joint` (2606.08517), `score2026` (2603.24704), `fedcrc2026` (2606.20115), `scrc2025` (2512.12844) and `thermal2026audit` (2607.13221). The 9–30% figure is quoted as established fact, is used again in §1 and §4 to motivate the whole design, and I cannot verify it from anything in the artifact. Consider attributing it explicitly as a preprint result ("a recent preprint reports…") and, where the argument can stand on the refereed literature (Bates et al.; Dunn et al.; Lee et al.), leaning on that instead.

### R4-35 — Missing prior art on exactly the axis the paper's motivation turns on

§2.2 builds the paper's central motivation — that exchangeability fails under multi-site clustering — without citing the canonical treatment of that failure: **Barber, Candès, Ramdas & Tibshirani, "Conformal prediction beyond exchangeability" (Annals of Statistics 51(2):816–845, 2023)**, which gives coverage guarantees with an explicit penalty for departures from exchangeability. That is the nearest work to §2.2's argument and its absence will be noticed. Two further gaps: **Gibbs, Cherian & Candès, "Conformal prediction with conditional guarantees"** (group/covariate-conditional validity — directly adjacent to the cluster-as-unit claim, and to §4.7's per-site-uniformity question), and **Tibshirani, Barber, Candès & Ramdas, "Conformal prediction under covariate shift" (NeurIPS 2019)**, which §6.1 should cite when it excludes covariate-shift importance weighting. The positioning survives all three — none of them certifies a selective-risk budget with the cluster as the unit — but the paper should say so rather than omit them.

---

## Questions to authors

### R4-36
Why does `sep` drop from 2.2 to 1.8 for E2 and E3 only (`SHIFT_SEP`, `run_synthetic.py:40`)? What are the E2 baseline hard-violation rate and the E3 hard-violation rate at `sep = 2.2` — i.e. at the generator §4.1 actually describes? Was 1.8 chosen before or after seeing the results at 2.2?

### R4-37
For the 191 BBSE declines in E2, what are the distributions of ρ̂, `rho_lo`, `rho_hi` and `gap_lo`, and which endpoint failed? Concretely: if BBSE were run as a *single*-endpoint test at ρ̂ and at full δ = 0.05 rather than dual-endpoint at δ_bet = 0.025, what would the certify rate and the certify-and-violate rate be? Without that comparison I cannot tell whether E2 shows the correction working or the correction lacking power.

### R4-38
In E6 — a cohort generated with no label shift, so ρ = 1 — the BBSE mode estimates ρ̂ = 0.830 and wins the deployment (τ* = 0.77 under the label-shift tag). Is a 17% spurious prevalence correction on unshifted data within expected estimator noise at 42 auxiliary sites? What is the distribution of ρ̂ across E1's 200 in-distribution draws, and how often does the BBSE tag win deployment there?

### R4-39
Both α rungs are tested at full δ = 0.05 (`pipeline.py:176–185`) and `build_report` then selects the "operative" rung as the strictest α that certified (`report.py:212`). That is a data-dependent selection across two families, each tested at δ. Is the intended reading that the guarantee is per-rung (each α statement holds at 1−δ separately), or that the deployed operative rung holds at 1−δ? The manuscript describes the within-mode fixed-sequence argument (§3.5) and the across-mode OR-rule (§3.6) but not the across-rung selection.

### R4-40
Will the code be deposited with a DOI and an OSI licence before submission, and will the manuscript cite an archived version and commit hash? Relatedly, will `SPEC.md`, `METHODS.md` and `PAPER-OUTLINE.md` — which `README.md` presents as part of the deliverable — ship with the release, and if not, will the README be rewritten so its repository map matches what a reader receives?

### R4-41
`_existing_summary_blocks` merges a partial `--only` run into an existing `summary.md` by regex. Was `experiments/out/summary.md` as submitted produced by a single full `python -m experiments.run_synthetic`, or assembled across partial runs? Since no provenance block is written (R4-05), I cannot tell from the artifact, and the E1/E4 208-site distinction in §4.5 makes the answer material.

---

## Confidential comments to the editor

### R4-42
I want to be unambiguous about the positive finding, because it is unusual and it should count. I traced every number in this manuscript to an artifact and **all of them matched**, including three-decimal quantities. I re-ran the experiments and got byte-identical CSVs, JSON and even PNGs. The 69-test suite passes in 8.65 s exactly as claimed. The four Clopper–Pearson intervals are arithmetically correct. I could not find a single fabricated or drifted number. Most submissions I review fail this bar. Whatever else is decided, the authors are not misreporting their results.

### R4-43
My sharpest concern is R4-01 combined with R4-02. Somebody reduced the class separation from 2.2 to 1.8 for precisely the two experiments that generate the paper's dramatic numbers, wrote a code comment saying it was so the shift would "bite", left that parameter outside the set pinned by the pre-registration-substitute test, and did not mention it in a manuscript that claims a frozen generator and a machine-verifiable pre-registration substitute. I am not alleging misconduct — 1.8 is a defensible choice and the code comment is candid — but this is the exact shape of a researcher-degree-of-freedom, and the paper's central methodological boast is that it has closed those. I would make disclosure of `sep = 1.8` plus a sensitivity table at 2.2 a condition of acceptance. If the E2 baseline violation rate at 2.2 is materially lower than 48.5%, the abstract needs rewriting.

### R4-44
The second thing I would not let through is R4-07. As written, §4.3 invites the reader to conclude that BBSE's 95.5% decline rate is the label-shift diagnostics working. The artifact says all 191 declines are the generic betting-walk `failsafe` and the three named BBSE declines fire zero times in every reported experiment. Since BBSE must clear two endpoints at half the baseline's δ, "the mode is underpowered" and "the mode is correctly refusing" predict the same observable, and the authors discarded the diagnostics (ρ interval width, gap, failing endpoint) that would separate them — they compute all of it in `BBSEFit.diagnostics` and write none of it. This is the paper's flagship robustness result and it is currently unfalsifiable from the released artifact. R4-37 asks for the specific comparison that would settle it.

### R4-45
Third: R4-11. `certgate/harness.py` computes every validity number in Section 4 and has no tests at all. The statistical *core* is genuinely well tested — `test_mcap_counterexample_regression` is a real adversarial regression, `test_wsr_boundary_type_I_at_n80` is a real level check at the null boundary, and `test_dual_endpoint_soundness_straddling_rho_one` plus `test_dual_endpoint_loop_requires_both_endpoints` pin a subtle non-obvious property (the atom mean is *not* affine across ρ=1; the sign-carrier is) with an assertion that would catch a regression to the wrong justification. Those are the tests of somebody who has been burned before. Which makes the harness gap conspicuous rather than careless: the module that decides whether a certificate "violated" is the one nobody tested. Add five tests and this concern disappears.

### R4-46
Two smaller things I would weight lightly but not drop. (a) R4-03: a limitations paragraph describes an imputation-and-indicator encoder that does not exist and whose actual behaviour is the opposite (hard rejection of non-finite values). It reads to me like a paragraph carried over from an earlier, larger version of this system, and it is the only place in the paper where a described component is wholly absent from the code — an alert reviewer who greps for it will lose trust in the rest, which would be unfair given R4-42. (b) R4-10: the "systematic abstention driver" in §4.6 and Figure 5 is a mean over **two** declined cases quoted to three decimals, at a threshold (0.55) that is the grid's floor. In a collection whose central emphasis is explainability, the explainability case study is the weakest evidence in the paper, and it is the section the collection editors will read most closely. I would ask for E5 to be re-run at a threshold producing a real declined population before this goes out.

### R4-47
On venue fit, for whatever it is worth from a reproducibility referee: the work is squarely inside the collection's scope (uncertainty quantification, calibration, OOD robustness, clinical auditability, explainability) and the abstention-explanation layer speaks directly to the collection's framing of explainability as both transparency requirement and clinician-facing aid. My reservations are about disclosure and artifact hygiene, not fit, and none of them requires new experiments beyond a sensitivity re-run.

---

## Recommendation

**Major revision.**

Nothing here impugns the results. The artifact is deterministic, the numbers reproduce byte-for-byte, the suite passes at the stated count, and the statistical core carries genuinely adversarial tests. What the manuscript does not yet do is describe that artifact accurately: two experiments run a generator parameter the paper says is frozen (R4-01) and that parameter sits outside the pre-registration-substitute test the paper advertises (R4-02); a limitations paragraph describes a component that does not exist (R4-03); the provenance block the paper says is embedded in every artifact is written to no file (R4-05); the decline attributions §4.3 and §4.5 argue from are computed and discarded (R4-06, R4-07); the module that produces every validity number is untested (R4-11); and the availability statement names no repository, no DOI and no licence (R4-17). For a paper whose contribution is *disclosure discipline* — tagged assumptions, parameter-versus-realized-count, verified-falsifiable negative controls — these are not cosmetic; the paper is asking the reader to trust a methodology of honest reporting while under-reporting its own experimental setup.

All of it is fixable without new science: disclose `sep = 1.8` with a sensitivity table, pin the experiment constants, rewrite the missingness limitation, serialise the provenance block and the BBSE/decline diagnostics into `experiments/out/`, add unit tests for `harness.py` and the two unpinned guarantee clauses, replace the vacuous assertion in `test_shift.py`, fix the three annotation-clipped figures, and deposit the code under a licence with a DOI. Given *Discover Computing*'s open-access posture and the collection's emphasis on clinical auditability, an artifact a reader can actually obtain, license, and audit is not optional — and this artifact is close enough to that standard that a single careful revision cycle should reach it.
