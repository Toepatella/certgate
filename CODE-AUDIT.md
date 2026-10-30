# CertGate correctness audit — verdict

Date: 2026-07-25. Auditor: independent verdict pass over six dimension sweeps and four prosecution passes.
Scope: `certgate/` (package), `tests/`, `experiments/`, `SPEC.md`, `METHODS.md`, `README.md`, `paper/draft.md`.

> Citations re-verified against the working tree 2026-08-25. Line numbers and quoted comment
> text were re-pointed after the 2026-08-24 comment humanization and the 2026-08-25 paper
> de-labelling; findings, verdicts and numbers are the originals and are unchanged. Note that
> all fixes this audit prescribes except recommendation 17 have since landed (see RESOLUTION below),
> so a re-pointed citation usually names the
> *corrected* code rather than the defect the row describes — several quoted strings were deleted
> by the very fix their row prescribes and are annotated as having no current match.
> A later 2026-08-25 simplification pass restructured certgate/pipeline.py, certgate/shift.py, experiments/run_synthetic.py and experiments/run_eicu.py (behavior proven byte-identical) and split tests/test_eicu_path.py into test_eicu_mock.py / test_eicu_etl.py / test_eicu_run.py, so line citations into those files are as of the re-verification date, before the moves.
> The companion working documents this record cites -- CLAUDE.md, REVIEW-FABLE.md, PAPER-OUTLINE.md and the paper/review/ corpus -- were removed from HEAD at submission (2026-08-27); all remain in git history.

---

## Verdict

**The mathematics is right and the English is wrong.** That sentence is the whole finding, and the
distinction matters more than any severity label in this document.

The statistical core is sound. The WSR betting test is a correct finite-sample level-δ procedure; the
atoms are provably in [0,1]; the fixed-sequence walk is a valid gatekeeping procedure that needs no
δ-splitting; the BBSE dual-endpoint reduction genuinely covers the interior of the ρ box; the cluster
mechanics give one atom per site and cannot let a large site dominate; determinism holds byte-for-byte.
Six auditors attacked the core from six directions and none of them broke it. I did not break it either.

What is wrong is what the certificate **says it proves**, and one place where a real input error is
never propagated. Answering the three questions the reader needs separated:

**1. Can the package issue a certificate it should not? Yes, in two distinct ways.**

- *In baseline mode, the certificate is true but the sentence printed on it is false.* The test certifies
  `E[Z] ≤ α`, which is the influence-weighted answered risk **averaged across the site population**.
  `report.py` prints that this bounds the risk **"at this target site."** Those are different quantities.
  Under between-site heterogeneity that exchangeability fully permits, I drove the per-target-site
  hard-violation rate to 0.10 — twice δ — using E1's exact protocol with only the documented generator
  parameter `s_u` changed, while the quantity actually certified stayed at *half* of α on the same
  fresh sites. Nobody's arithmetic is wrong; the claim on the certificate is not the claim that was proved.

- *In BBSE mode, an actual invalid certificate is issued at up to 3× δ.* The target predicted-positive
  rate `q_t` is treated as a known constant and given no share of the confidence budget. It is a noisy
  estimate. I measured the resulting `[ρ_lo, ρ_hi]` missing the true odds ratio in 67% of draws against
  a nominal 2.5%, and 16% of draws certified-and-violating under *pure* label shift with the mode's own
  assumption exactly satisfied. The control settles causality: hand the same code a target pool large
  enough that `q_t` is effectively exact and it issues **zero** certificates in the cell where it
  currently issues 43, 24 of them false.

**2. Are there implementation defects that do not threaten the guarantee?** Yes, about twenty, none of
them severe. The largest cluster is at the input boundary: site identity is unvalidated `str()`, so
cosmetic noise in one column silently multiplies the cluster count, buys a strictness rung the honest
clustering refuses, and defeats the minimum-cluster gate. The rest are diagnostic-tier or edge-case
defects — `-inf` into a JSON field, an all-NaN ranking returning identity order, a dead parameter, a
provenance block that does not bind the labels that determine the certificate.

**3. What is not verified?** More than the green suite suggests, and this is the finding I would put
second on the list. **Fourteen of fourteen load-bearing mutations I ran left the suite at 69/69 passing** —
including deleting the M-influence cap that supplies the [0,1] boundedness Ville's inequality *requires*,
spending δ = 0.5 instead of 0.05, and inverting the concept-shift disclosure to assert its exact opposite.
The suite does protect the betting statistic itself (I confirmed four core mutations are caught). It does
not protect the accounting, the data discipline, the guarantee text, or `harness.py` — the module that
computes every violation number in the paper and has zero tests.

**Bottom line.** I would not describe this codebase as incorrect. I would describe it as a correct
procedure carrying an overclaiming certificate, plus one genuine unpropagated uncertainty in the
label-shift mode. Neither is a rewrite. The first is a wording fix in `report.py`, `SPEC.md`, `METHODS.md`
and the paper, plus an honest experiment; the second is a confidence interval on `q_t` and one more
Bonferroni term. Both must land before this is used on patients, and the first must land before the
paper is submitted, because the overclaimed sentence *is* the paper's contribution.

**On `SPEC.md`.** The brief says the spec is binding but not infallible. Here it is wrong.
`SPEC.md:817-851` mandates the guarantee text as *"per-target-site; all sites from one calibration draw share
the 1-delta event."* Both clauses are false — the first because the estimand is a population aggregate,
the second because the permutation is seeded from the target label. The code faithfully implements a
specification that misstates the mathematics. Fixing the code alone would not fix this; `SPEC.md` must
change first, as its own protocol requires.

## RESOLUTION (applied through 2026-09-04)

Every item below landed before the repository's first commit, the pre-extract freeze `9f25b49`
(2026-07-30), so no later commit can be cited for it; the corrected code is what that commit carries,
and the durable pointer is the regression test named on each line (`tests/<file>::<test>`).

- **Critical 1 (V1) — FIXED.** SPEC.md's mandated guarantee text was changed first (rec. 1), then
  `certgate/report.py` states the estimand the test certifies: the influence-weighted answered-set
  risk "averaged over the population of sites from which the calibration sites were drawn … NOT any
  individual site's answered error rate". Pinned by: `test_report.py::test_guarantee_statement_frozen_baseline`,
  `::test_guarantee_statement_frozen_both_modes`, `::test_guarantee_statement_frozen_bbse_only`
  (exact-string equality against three frozen variants; changing the text is a SPEC change).
  E1 reports aggregate conformance as the metric and the per-site rate as a diagnostic across an
  `s_u` sweep (rec. 3); pinned by `test_experiments.py::test_rm_on_pool_matches_closed_form_and_is_not_the_record_mean`,
  `::test_per_site_exceed_frac_closed_form`.
- **Critical 2 (V2) — FIXED.** `q_t` receives its own confidence share: `BBSE_BONFERRONI = 4`, an
  exact Clopper–Pearson interval for a single-site pool, a cluster bootstrap for pools of at least
  `BBSE_MIN_TARGET_SITES = 10` declared sites, and a `bbse-target-clustering` decline for 2–9; the
  box propagates over 16 corners. Pinned by: `test_shift.py::test_fit_records_q_interval`,
  `::test_q_ci_is_clopper_pearson_at_the_bonferroni_level`, `::test_q_interval_matches_the_scipy_reference_implementation`,
  `::test_multi_site_q_interval_path`, `::test_few_target_sites_decline_bbse_target_clustering`,
  `::test_q_interval_propagation_regression`; constants by `test_constants.py::test_bbse_bonferroni`,
  `::test_bbse_min_target_sites`. The box's realized coverage is measured post-hoc in
  `experiments/out-bbse-probe/` (implied certificate level about 0.93 in the probe's regime) and
  disclosed in METHODS §5 and in every BBSE guarantee string — the residue is recommendation 17.
  *(2026-10-29 correction, 2026-10 PROBE-1 / BBSE-5: "implied certificate level about 0.93" charges every box miss to
  the certificate. The propagated `[rho_lo, rho_hi]` covered the declared site's odds ratio in all 1,163
  certifiable probe fits (exact 95% upper end of the miss 0.0032), so in the probe's regime the union bound gives
  a level of at least 0.97; about 0.93 is the looser box-route bound. See "Mathematical-exactness audit, 2026-10".)*
- **V6 #1 (M-cap deleted) — pinned by** `test_certify.py::test_mcap_supplies_ville_boundedness`.
- **V6 #2 (baseline walk spends δ = 0.5) — pinned by** `test_pipeline.py::test_delta_accounting_spy`.
- **V6 #3 (BBSE bet spends the full δ) — pinned by** `test_pipeline.py::test_delta_accounting_spy`.
- **V6 #4 (box drops the Bonferroni split) — pinned by** `test_constants.py::test_bbse_bonferroni`
  (the constant) and `test_shift.py::test_q_ci_is_clopper_pearson_at_the_bonferroni_level`,
  `::test_q_interval_propagation_regression` (the level actually spent on the q interval); the three
  bootstrap percentiles' level is pinned only through the constant.
- **V6 #5 (walk order derived from S_cal) — pinned by** `test_pipeline.py::test_walk_order_is_aux_derived`.
- **V6 #6 (`wilson_lcb` returns the upper bound) — pinned by** `test_harness.py::test_wilson_lcb_is_a_LOWER_bound_and_monotone`,
  `::test_wilson_lcb_matches_closed_form`, `::test_wilson_lcb_matches_the_scipy_reference_implementation`.
- **V6 #7 (`hard_violation` uses the raw rate) — pinned by** `test_harness.py::test_hard_violation_criterion`.
- **V6 #8 (BBSE walk `break` → `continue`) — pinned by** `test_shift.py::test_bbse_walk_break_not_continue`.
- **V6 #9 (provenance hashes → a literal) — pinned by** `test_pipeline.py::test_provenance_binds_label_content_and_shape`,
  `::test_provenance_binds_run_configuration`.
- **V6 #10 (bootstrap quantiles a reduced count) — pinned by** `test_shift.py::test_bootstrap_shortfall_declines_not_reduced_quantile`.
- **V6 #11 (atoms use `>` while deploy uses `>=`) — pinned by** `test_certify.py::test_threshold_tie_is_answered_in_atoms`.
- **V6 #12 (`certification_rng` ignores `alpha`) — pinned by** `test_certify.py::test_certification_rng_streams`.
- **V6 #13 (out-of-scope clause inverted) — pinned by** the three `test_report.py::test_guarantee_statement_frozen_*`
  exact-string tests.
- **V6 #14 (BBSE asymptotic clause deleted) — pinned by** `test_report.py::test_guarantee_statement_frozen_both_modes`,
  `::test_guarantee_statement_frozen_bbse_only`.
- **Rec. 1 — CLOSED.** SPEC.md guarantee text rewritten first; enforced through the `test_report.py`
  frozen strings above.
- **Rec. 2 — CLOSED.** `report.py` estimand wording; `test_report.py::test_guarantee_statement_frozen_*`.
- **Rec. 3 — CLOSED.** E1 scored on aggregate conformance with the `s_u` sweep reported as a
  dispersion diagnostic; `test_experiments.py::test_per_site_exceed_frac_closed_form`,
  `test_constants.py::test_simconfig_generator_defaults_pinned`.
- **Rec. 4 — CLOSED.** As Critical 2.
- **Rec. 5 — CLOSED.** `target_label` out of the permutation seed; the shared-event clause struck
  for BBSE. `test_certify.py::test_certification_rng_streams`, `test_pipeline.py::test_baseline_reports_are_target_label_invariant`,
  `::test_bbse_fit_is_target_label_free_and_data_seeded`, `test_report.py::test_bbse_rows_never_claim_a_shared_event`.
- **Rec. 6 — CLOSED.** E2/E3 run at the documented separation (`SimConfig()` defaults; the local
  constant is gone). `test_constants.py::test_no_experiment_local_separation_override`,
  `::test_simconfig_generator_defaults_pinned`.
- **Rec. 7 — CLOSED.** The BBSE guarantee string carries the asymptotic clause (frozen by
  `test_report.py`), METHODS §5 reports the measured shortfall, and `experiments/out-bbse-probe/`
  records the box's realized coverage at auxiliary-site counts bracketing the design's (36, 42 and 74).
- **Rec. 8 — CLOSED.** `tests/test_harness.py` exists; the δ-accounting spy is
  `test_pipeline.py::test_delta_accounting_spy`; the exact-string guarantee assertion is the
  `test_report.py` trio.
- **Rec. 9 — CLOSED.** Site identity canonicalized, missing site ids rejected.
  `test_validate.py::test_dirty_site_ids_whitespace_merges_to_one_site`, `::test_dirty_site_ids_case_collision_raises`,
  `::test_dirty_site_ids_string_numeric_spelling_raises`, `::test_numeric_int_float_ids_merge_to_one_site`,
  `::test_invisible_and_nfd_spellings_merge_to_one_site`, `::test_missing_site_ids_rejected`,
  `test_pipeline.py::test_target_gates_use_canonical_normal_form`.
- **Rec. 10 — CLOSED.** `test_validate.py::test_duplicate_site_labels_rejected_by_make_cohort`.
- **Rec. 11 — CLOSED.** Target pool asserted site-disjoint; `target_site_id` added and used by
  `examples/real_data_example.py`. `test_pipeline.py::test_target_overlapping_calibration_raises`,
  `::test_misaligned_target_site_id_raises_on_every_path`.
- **Rec. 12 — CLOSED.** `test_validate.py::test_cohort_post_init_enforces_contract`.
- **Rec. 13 — CLOSED.** `test_validate.py::test_column_shaped_arrays_rejected`.
- **Rec. 14 — CLOSED.** `test_pipeline.py::test_unknown_or_empty_modes_raise`,
  `::test_single_class_fitting_cohort_raises`, `::test_malformed_oracle_labels_raise`.
- **Rec. 15 — CLOSED.** The V6 table above: every one of the fourteen mutations now has a named test.
- **Rec. 16 — CLOSED.** `test_report_estimated.py::test_feasibility_reports_none_not_inf_when_no_coverage`
  (V16), `test_explain.py::test_empty_population_gap_ranking_is_empty` (V22),
  `test_pipeline.py::test_gated_report_has_stable_diagnostic_keys` (V25).
- **Rec. 17 — OPEN.** Replacing the percentile box with a finite-sample cluster bound is deferred
  post-submission; the manuscript names it as future work (§6.1), and the shortfall it would retire
  is measured (`experiments/out-bbse-probe/`) and disclosed wherever the BBSE guarantee is stated.
  *(2026-10-29 pointer, 2026-10 BBSE-2: for a pool declaring ten or more target sites the q interval is a fourth
  percentile bootstrap, unprobed by `experiments/out-bbse-probe/`; retiring the last asymptotic step needs it
  replaced too.)*

*(2026-10-29: resolutions that landed after the freeze, from the mathematical-exactness audit, are recorded in the
last section, "Mathematical-exactness audit, 2026-10".)*

---

## Scope and method

I read `certgate/` in full (certify, shift, pipeline, report, validate, harness, data, explain, model,
constants), the eight test modules, `experiments/run_synthetic.py`, and the estimand/scope sections of
`SPEC.md`, `METHODS.md` and `paper/draft.md`. I did not read `REDTEAM.md`, `REVIEW-FABLE.md` or
`paper/review/`, per the brief.

`python -m pytest tests -q` → **69 passed in 5.47s** on this working tree. I treated that as a starting
point, not as evidence: I copied the tree to a scratch directory and ran eighteen source mutations
against it. Fourteen survived; four were caught. A green suite that cannot go red for the M-cap is
information about the suite, not about the code.

Probes written for this pass (all in the session scratchpad, no repository file modified): `v_cc1.py`
(E1 protocol under varying `s_u`), `v_cc1_rm.py` (R_M vs per-site on the same fresh sites),
`v_bbse2.py` (ρ-interval coverage with the target random effect zeroed so ρ_true is exactly known),
`v_bbse_cert.py` (false certificates + large-pool control), `v_label.py` (relabelling), `v_split.py`
(cluster inflation), `v_mutate.py` (mutation runner). Where I could not construct a counterexample I say
so and mark the finding reasoned-only.

Findings below are consolidated across dimensions: several were discovered independently by two or three
auditors, which I note explicitly because independent rediscovery is the strongest signal in this dataset.

---

## Findings

### CRITICAL

---

#### V1 — The certified inequality bounds a cross-site population average; the certificate states it as a bound at the target site
*(= CC-1 / CG-R1 / CW-1 — found independently by three dimensions)*
**Location:** `certgate/report.py:76-162` (text) vs `certgate/certify.py:29-34` (estimand); `SPEC.md:817-851`;
`METHODS.md:7,19,21-23,25,62-65`; `paper/draft.md:52,101,247`; validated wrongly at `certgate/harness.py:50-61`
(the V1 relabelling is now recorded at `harness.py:6-21`).
**Empirically demonstrated.**

`influence_atoms` builds `Z_c = (g_c/(M·n_c))·Σ_i ans_i(err_i − α) + α`. `wsr_reject` tests `E[Z] ≤ α`
where the expectation is over the **site draw**. That is exactly `R_M = Σ_c g_c a_c e_c / Σ_c g_c a_c`,
which `METHODS.md:19` itself defines as a sum over sites. For a *single* site, `g_c` and `a_c` cancel and
the quantity is just that site's own error rate `e_c`. A population mean does not bound an individual draw,
and the probability in the statement is over the calibration draw only — there is no residual randomness
left for a per-site reading to average over.

The emitted text (generated from the shipped code, verbatim):

> Under the tagged assumption (exchangeability), with probability >= 0.95 over the draw of calibration
> sites, the M=100 influence-weighted answered-set risk **at this target site** is <= 0.1. This guarantee
> is per-target-site; all sites certified from one calibration draw share the same 1-0.05 event.

*[Exhibit of the 2026-07-25 text, kept verbatim. The shipped statement today is
`certgate/report.py:76-162`; the "at this target site" wording was removed by the fix this finding
prescribes and has no current match.]*

**Probe A** — E1's exact protocol (fresh 208-site calibration draw per replicate, one fresh target site,
in-distribution so exchangeability holds exactly), R=200, varying **only** `SimConfig.s_u`, the documented
site-prevalence random effect:

```
   s_u  certified   hard     rate  mean_ans_err
  0.50        200      2   0.0100        0.0517     <- reproduces the published E1 headline
  1.00        200     11   0.0550        0.0526
  1.50        200     14   0.0700        0.0508
  2.00        200     20   0.1000        0.0515     <- 2x delta;  P(X>=20|n=200,p=.05) = 0.0027
```

That the `s_u = 0.5` row reproduces E1's published 0.01 confirms my harness matches theirs. The published
validity headline is therefore a property of the frozen generator's mild heterogeneity, not of the theorem.

**Probe B** — the decisive separation. Certify once, then apply the *same certified τ* to 400 fresh sites
and measure both quantities on them:

```
  s_u    tau  R_M(400 fresh)   <=a  per-site viol    rate  worst site
 0.50   0.69          0.0409  True        0/400  0.0000      0.1061
 1.00   0.69          0.0466  True       14/400  0.0350      0.2188
 1.50   0.73          0.0481  True       31/400  0.0775      0.2794
 2.00   0.77          0.0472  True       40/400  0.1000      0.2370
```

`R_M` — the quantity the test controls — is comfortably ≤ α in every row, at less than half of α. The
certificate is **correct about what it certifies**. Meanwhile the per-site violation rate reaches 2δ and
the worst individual site runs at 0.28 against α = 0.10. Heterogeneity leaves the population mean untouched
and blows out the tail; that is the aggregate-vs-individual signature and nothing else.

This is not binomial noise. `harness.hard_violation` uses a one-sided 95% Wilson **lower** bound precisely
to discount dispersion, and it still fires — these are parameter-level exceedances. The existing disclaimer
("NOT a bound on this batch's realized error count, which exceeds alpha at binomial-dispersion rates") names
only that mode and does not cover this one.

The "design-conditional estimand" defence (`METHODS.md:25`, the Scope paragraph; the phrase itself no
longer appears in `METHODS.md` and survives only in `paper/review/`, in git history) does not rescue it: conditioning on
the target's features makes them observed, but does not convert a population-average bound into a per-site
bound. Note also that in baseline mode the target's data never enters the test at all —
`pipeline.py:71-89` builds atoms from `cal` only, at `:79-82` — so a genuinely site-specific claim is
structurally impossible on that path.

**Why the harness cannot catch it:** `experiments/run_synthetic.py:244-255` draws one target site per
calibration draw from `SimConfig` defaults, whose only between-site variation is `u_c ~ N(0, 0.5²)`. Per-site
true risk is nearly uniform there.

**Fix.** Two coupled changes, `SPEC.md:817-851` first since it is binding and currently mandates the wrong text.
(a) `report.py:76-162`: state the certified estimand — *"the expected M=100 influence-weighted answered-set
risk over sites drawn from the calibration population is ≤ α"* — and add a fourth mandatory clause with the
same force as the binomial one: *"This is a population average across sites. It does not bound any individual
site's answered error rate; under between-site heterogeneity the fraction of target sites exceeding α is
governed by that dispersion, which this certificate does not measure or bound."* (b) Restate `METHODS.md:7,
21-23, 25, 62-65` and `paper/draft.md:52, 101, 247` to match, and either rescore E1's conformance metric against
the aggregate estimand or keep the per-site column relabelled honestly as a dispersion diagnostic with no
δ target attached. Report the `s_u` sensitivity in the paper — the published 0.01 is not robust to it.
If a genuine per-site guarantee is wanted, `E[Z]` is the wrong statistic: it must become a tolerance bound
on an upper quantile of the per-site risk distribution, which is a different test and costs more clusters.

---

#### V2 — BBSE treats the target predicted-positive rate `q_t` as known; its sampling error is never propagated, and false certificates result at up to 3× δ
*(= BBSE-1)*
**Location:** `certgate/shift.py:258-259` (also `19-22, 59-60, 186, 287-289, 307`); `certgate/constants.py:20`.
**Empirically demonstrated, with a control isolating causality.**

```python
q_t = float(head.predict(target_x).mean())        # exact on the pool
```

*[Exhibit of the 2026-07-25 source, kept verbatim. Today `shift.py:258-259`; the "exact on the pool"
comment was deleted by the fix this finding prescribes and has no current match. `constants.py:20` now
reads `BBSE_BONFERRONI = 4   # box covers (c0, c1, pi_source, q_target) — audit V2`.]*

`BBSE_BONFERRONI = 3  # box covers (c0, c1, pi_source)`. `q_t` gets no share of `BBSE_DELTA_CONF` and no
interval anywhere in the chain, yet it enters the inversion at `shift.py:186`
(`pi_t = clip((q_t − c0)/(c1 − c0), …)`) where the `BBSE_GAP_FLOOR = 0.10` gate permits its error to be
amplified up to 10×. The only `q_t` guard (`shift.py:307`) fires only for `q_t` outside `[c0_lo, c1_hi]`.

The docstring's justification is that `q_target` is *"exact under the design-conditional estimand."*
(That docstring text is gone — no current match; `shift.py:19-22` and `:59-60` now state the opposite.)
This is the false premise. Conditioning on the target features makes `q_t` exactly **observed**, but it simultaneously
destroys the population identity `q = c0(1−π_t) + c1·π_t` that makes `q_t` informative about `π_t` — because
`ŷ(x)` is then a deterministic function of `x`. `q_t` is an unbiased-but-noisy estimate of the population `q`,
carrying entirely unbudgeted error.

**Probe** — head and `S_aux` held fixed (so the box is a *constant*), target site random effect zeroed so the
target prevalence is exactly `π_t` and `ρ_true` is a known constant. The only thing varying is the finite pool:

```
source pooled pi_s = 0.1105 ;  nominal box miscoverage = BBSE_DELTA_CONF = 0.025

--- pi_t=0.22  rho_true=2.2712 ---
 n_pool  miss rho_true  disjoint pairs
     50          0.675           0.582
    100          0.570           0.450
    200          0.455           0.250
    400          0.230           0.100
   1000          0.105           0.000
   5000          0.005           0.000
  20000          0.000           0.000
```

Miscoverage of 67.5% against a nominal 2.5%, decaying monotonically to zero as the pool grows. Nothing else in
the chain depends on target-pool size, so `q_t` is the sole driver. The *disjointness* column needs no external
definition of truth: 58% of independent pairs of intervals, drawn from the identical distribution with an
identical box, are **disjoint from each other**. Two 97.5% intervals for any fixed quantity cannot behave that way.

**False certificates.** Pure label shift, `P(x|y)` exactly invariant — the mode's own assumption fully satisfied.
Certified from a small pool; judged against the true answered risk of the target site measured on a large
held-out sample at the deployed τ:

```
pure label shift, alpha=0.10, delta=0.05, modes=('bbse',), R=150, 400 sites
  pi_t  n_pool  certified  cert&violating    rate
  0.22      50         43              24  0.1600
  0.22     100         23              14  0.0933
  0.22     200          8               4  0.0267
  0.30      50         20              16  0.1067
  0.22   40000          0               0  0.0000  <-- CONTROL (q_t ~exact)
```

**The control is the finding.** With `q_t` effectively exact the method issues *zero* certificates in the cell
where it currently issues 43 — 24 of them false. The false certificates are attributable to `q_t` sampling error
and nothing else.

At the paper's own 208-site anchor the exposure persists: `π_t=0.22, n_pool=50` gives 13/150 = 8.7%
certified-and-violating, and **13 of the 15 certificates issued were false**. `n_pool = 50` is five times
`MIN_ANSWERABLE = 10` and inside the generator's own `size_lo = 20` range; `π_t = 0.22` is E2's own `SHIFT_BASE`.

**Why existing evidence missed it:** `harness.hard_violation`'s Wilson-LCB criterion flags only a fraction of the
true violation rate on these configurations, so E2's reported `bbse hard_violation_rate 0.0` is not evidence of
absence. E2's substantive *conclusion* — BBSE declines rather than certifying-and-violating — survives at the
headline scale, but the **reason** it survives is wrong: it declines from lack of power, not from correct
uncertainty propagation.

**Fix.** `SPEC.md`'s `shift.py` block first: state that `q_t` estimates the target *population* predicted-positive
rate and carries sampling error, and that the box covers four parameters. Then `constants.py:20` →
`BBSE_BONFERRONI = 4`. Then `shift.py` after `:259`: build a finite-sample interval for `q` at
`lvl = BBSE_DELTA_CONF/BBSE_BONFERRONI` — exact Clopper-Pearson on `k = predict(target_x).sum()` for a
single-site pool; a cluster bootstrap over target sites for a multi-site pool, which requires adding a
`target_site_id` parameter (`run_certgate` has it available) and treating unknown clustering as one cluster.
Widen the misspecification gate at `shift.py:307` to `if not (lo[0] <= q_lo and q_hi <= hi[1])`. Make `rho_of`
take `q` as an argument and enumerate **16** corners. Add the regression test the current code fails: with head
and `S_aux` fixed and ≥200 independent target pools of n=100, assert the fraction of intervals missing `ρ_true`
is ≤ `BBSE_DELTA_CONF` + MC tolerance — today it is ~0.57. Expect BBSE to decline more often on small pools;
that is the correct behaviour, as the control shows.

---

### HIGH

---

#### V3 — The WSR permutation is seeded from the caller-supplied target label, so target sites do not share one 1−δ event and the deployed threshold moves with a respelling
*(= CC-2 / CG-R2 / CW-6)*
**Location:** `certgate/certify.py:152-174` (seed rule), `certgate/pipeline.py:83`, `certgate/shift.py:371-374`;
falsifies `certgate/report.py:136-139`, `SPEC.md:817-851`, `METHODS.md:25`, `paper/draft.md:84,101`.
**Empirically demonstrated.**

In baseline mode nothing about the target enters the calibration atoms (`pipeline.py:79-82` uses `cal` only;
walk order from `aux`). The sole target dependence is `certification_rng(alpha, MODE_BASELINE, target_label)`,
and `certify.py:171` is `h = hashlib.sha256(str(target_label).encode()).digest()` (today
`str(stream)` — `target_label` was dropped by the fix this row prescribes). `certify.py:95` permutes `z`
with that stream, and `wsr_reject`'s decision is a sup over prefixes of an **order-dependent** wealth product.
So each target site receives a separately randomized test of identical calibration data.

**Probe A** — identical `train`/`aux`/`cal`, identical target features, only the label varied over 12 spellings
of the same site. 3 of 6 configurations were label-dependent, including at the paper's 208-site anchor:

```
  seed=3 sep=1.6 n_sites=208 (cal=83): {('certified',0.75): 4, ('certified',0.77): 8}
      's-0042' -> 0.75    'S-0042' -> 0.77    'site-42' -> 0.77
      '0042'   -> 0.75    'st marys' -> 0.75  "St Mary's" -> 0.77   ...
```

The deployed operating point, the answered set and the reported coverage all move with the spelling of a
free-text identifier on byte-identical data. `paper/draft.md:84` claims the permutation *"cannot be chosen to
flatter the outcome."* (Current wording there: *"unchoosable to flatter the outcome"*.)

**Probe B** — the shared-event claim, at the exact H0 boundary (`E[Z] = α`), where every certification is false
by construction. `f` = fraction of 400 distinct labels certifying on the *same* atom vector:

```
                construction     n    E[f]  draws split  P(>=1 of 40)
         spike p=0.10 hi=1.0    83  0.0050        0.742        0.1689
         spike p=0.10 hi=1.0   200  0.0184        1.000        0.5050
               beta(0.2,1.8)   200  0.0031        0.691        0.1119
```

The marginal per-target level is intact everywhere (≤ 0.018 ≤ δ) — that is what the seed rule buys, and it means
**no individual certificate is invalid**. But a single shared 1−δ event would force `f ∈ {0, 1}`; instead 100% of
draws split. A 200-site health system certifying 40 sites from one calibration draw faces up to a 50% chance that
at least one certificate is false, while every certificate prints a promise of 95% *jointly*.

**Severity high, not critical:** each certificate remains marginally level-δ. What fails is the joint claim
printed on every certificate and the unchoosability claim in the paper.

**Fix.** Drop `target_label` from the permutation seed: `certification_rng(alpha, mode_idx)` seeded from
`SeedSequence([SEED, ALPHA_LADDER.index(alpha), mode_idx])`. Nothing is lost in baseline mode — the atoms are
already target-independent — and one calibration draw then yields literally the single shared event `report.py:136-139`
promises. BBSE endpoints keep distinct streams via a `'lo'`/`'hi'` discriminator rather than `f"{target_label}|lo"`.
Leave `_bbse_seed_rng` alone; it legitimately depends on the target because `fit_bbse` consumes `target_x`. Add a
test asserting `run_certgate` output is byte-identical across a list of target-label spellings — that test fails today.
*Caveat:* the shared-event clause is **independently** false in BBSE mode because `fit_bbse` depends on the target
pool through `q_t`, so different targets get different ρ boxes regardless of seeding. Restoring the clause fully is
achievable for baseline only; for BBSE the clause must be deleted.

---

#### V4 — Site identity is unvalidated `str()`; cosmetic noise in one column fabricates independent clusters, buys a rung the honest clustering refuses, and defeats the minimum-cluster gate
*(= VB1, absorbing VB2)*
**Location:** `certgate/validate.py:253-287` (`densify_sites`); consumed at `pipeline.py:275`, `certify.py:55`.
Canonicalization now lives at `validate.py:161-212` (`_canonical_site_id`). **Empirically demonstrated.**

```python
labels_str = np.array([str(s) for s in raw_site_ids], dtype=object)
uniq = np.unique(labels_str)
```

*[Exhibit of the 2026-07-25 source, kept verbatim; the corresponding lines today are
`validate.py:271-273`, which call `_canonical_site_id` — the fix this finding prescribes.]*

No `.strip()`, no numeric canonicalization, no consistency check. Verified directly:

```
 whitespace  : ('A', 'A ', 'B')                  <- 3 clusters from 2 hospitals
 int vs float: ('0', '0.0', '1', '1.0')          <- 4 clusters from 2
 None / NaN  : ('A', 'None', 'nan')              <- see V11
```

The int-vs-float case is exactly what a pandas site-id column that acquires float dtype from one stray NaN produces.

**Harm 1 — a refused rung becomes certified.** Each calibration site split into `k` sub-clusters; records, labels
and outcomes **identical**, only `site_id` changed:

```
            clustering  n_sites             alpha=0.05             alpha=0.10
  honest (1 atom/site)       83     ('declined', None)    ('certified', 0.55)
      2 atoms per site      166    ('certified', 0.87)    ('certified', 0.55)
      4 atoms per site      332    ('certified', 0.77)    ('certified', 0.55)
      8 atoms per site      664    ('certified', 0.71)    ('certified', 0.55)
```

The honest clustering **refuses** α = 0.05; the inflated one certifies it, at progressively more liberal thresholds.
Mechanism: splitting one site into `k` sub-clusters produces `k` atoms sharing that site's random effect, while
WSR's `λ = √(2 ln(1/δ)/(s²n))` treats them as `n` independent units — evidence grows as ~√k with no new information.

**Harm 2 — the gate is defeated outright:**

```
MIN_CAL_CLUSTERS = 50; honest cal sites = 42
         honest clusters=  42 reason= insufficient-clusters a=0.10 -> None
    2-way split clusters=  84 reason=                  None a=0.10 -> ('certified', 0.55)
```

A cohort the library correctly refuses becomes a certificate under cosmetic noise.

**Absorbed sub-finding (VB2):** `assert_site_disjoint` — the sole enforcement of the site-disjointness invariant
(audit F03) — compares these same strings. I verified that two cohorts over the *same three sites*, one from an int
column and one from a float column, get labels `('0','1','2')` and `('0.0','1.0','2.0')`, and
`assert_site_disjoint` **passes**. If `S_aux` and `S_cal` are literally the same sites, the walk order is computed
on `S_cal` itself, voiding `certify.py:122-128`'s *"The order never looks at S_cal, which is why it costs no
multiplicity budget."*

*Honest mitigation:* the report surfaces `n_cal` and `n_cal_carrying`, so an attentive user could notice 166 where
they expected 83. Nothing forces them to look.

**Fix.** `validate.py:253-287`: canonicalize before `np.unique` — reject None/NaN/empty (V11), strip surrounding
whitespace, map integral floats to their integer string so `0` and `0.0` collide. Then raise `CohortError`, not a
warning, when the raw forms collapse to fewer clusters than they produced — that is the caller's signal that their
site column is dirty, and it must be loud because the count feeds `MIN_CAL_CLUSTERS`. Add a regression test asserting
`from_raw` over an int site column and the same column cast to float produce identical `site_labels`. Surface the
calibration cluster count and min/median/max cluster size in the diagnostic tier so a 2× inflation is visible.

---

#### V5 — `make_cohort` ignores a caller's declaration that two clusters are the same physical site
*(= CW-2)*
**Location:** `certgate/validate.py:340-349`. **Empirically demonstrated.**

The entire `site_labels` contract checks only the **length**:

```python
site_labels = tuple(str(s) for s in site_labels)
if len(site_labels) != n_sites:
    raise CohortError(...)
```

*[Exhibit of the 2026-07-25 source, kept verbatim; those lines are `validate.py:340-343` today, now
followed by the uniqueness check this finding prescribes at `:344-349`.]*

`SPEC.md:68` documents `site_labels` as *"original identifiers, index-aligned to dense ids"* — so a repeated
identifier is the caller explicitly declaring that two dense clusters are one physical site. The library holds
that declaration and discards it. Verified: `make_cohort(x, y, [0,0,1,1,2,2], site_labels=('H-A','H-A','H-B'))`
is accepted, `n_sites = 3`, three atoms from two hospitals.

The end-to-end harm is the V4 table (identical, since the mechanism downstream is the same), with
`len(set(site_labels))` staying at 83 in every row. Distinct from V4 in **trigger** and in **fix**: V4 is the library
manufacturing spurious clusters from unnormalized strings; this is the library ignoring a uniqueness declaration it
was handed. It requires the caller to supply `site_id` and `site_labels` at inconsistent granularity — e.g. `site_id`
from a ward/encounter grouping and labels from the hospital column — which is why it is high rather than critical.
`densify_sites`, `subset_sites` and `draw_cohort` cannot produce duplicates, so the raw loader is safe; `make_cohort`
is equally public and is not.

**Fix.** `validate.py`, immediately after the length check: `if len(set(site_labels)) != n_sites: raise CohortError(...)`
explaining that a repeated label declares one physical site, which cannot span two independent clusters. Safe for
every sanctioned constructor. Mirror in `SPEC.md`'s `make_cohort` contract block.

---

#### V6 — The test suite does not go red when the guarantee is broken: 14 of 14 load-bearing mutations survive
*(consolidates TS-01, TS-03, TS-04, TS-05, TS-07, TS-08, TS-09, TS-10, TS-11, TS-13)*
**Location:** `tests/` as a whole. **Empirically demonstrated.**

I copied the tree and mutated it. Every one of these left the suite at **69 passed**:

| # | Mutation | What it breaks |
|---|---|---|
| 1 | `np.minimum(sizes, M)` → `sizes` (`certify.py:58`) | the [0,1] atom bound **Ville's inequality requires** |
| 2 | baseline walk spends `δ = 0.5` (`pipeline.py:84-85`) | the δ in the paper's title |
| 3 | BBSE bet spends full `DELTA` (`shift.py:378`) | `δ_conf + δ_bet = δ` union bound |
| 4 | box drops Bonferroni-over-3 (`shift.py:287-289`) | ρ-interval width |
| 5 | walk order derived from `S_cal` (`pipeline.py:313`) | selection on the testing data — the reason `S_aux` exists |
| 6 | `wilson_lcb` returns the **upper** bound (`harness.py:46-47`) | every violation number in the paper |
| 7 | `hard_violation` uses the raw rate (`harness.py:61`) | the two-number violation protocol |
| 8 | BBSE walk `break` → `continue` (`shift.py:383`) | fixed-sequence FWER across 23 thresholds |
| 9 | provenance hashes → literal `"deadbeef"` (`report.py:58-62`) | content binding (audit F49) |
| 10 | bootstrap may quantile a reduced count (`shift.py:279`) | audit F40/B-8 hardening |
| 11 | atoms use `>` while deploy uses `>=` (`certify.py:70`) | tie handling between statistic and answered mask |
| 12 | `certification_rng` ignores `alpha` (`certify.py:172-174`) | ladder rungs share a permutation stream |
| 13 | **invert** the out-of-scope clause to "Nothing is OUT OF SCOPE" | the disclosure E3 exists to justify |
| 14 | delete the BBSE asymptotic clause (`report.py:149-161`) | a named `CLAUDE.md` invariant |

**What the suite does protect** — I checked, so the picture is fair. These four were **caught**:
WSR sup-crossing threshold `1/δ → 1/√δ`; removal of the λ cap; dropping the atom recentering offset; and removing
the baseline walk's `break`. The betting statistic itself is genuinely load-bearing and well tested. The frozen
constants are literally pinned. What is unprotected is everything *around* the statistic: the δ accounting at its
point of use, the data discipline, the guarantee text, and `harness.py`.

**Counterexample for #1**, showing the shipped code is right and the suite is blind to the difference:

```
CAPPED (as shipped):
  atom range [0.0000, 0.1400]  in [0,1]? True
  E[Z]=0.1260 vs alpha=0.1 -> must REFUSE
  wsr_reject certifies? False
UNCAPPED (mutation that survives 69/69):
  atom range [-2.9000, 0.1400]  in [0,1]? False
  E[Z]=-0.1640
  wsr_reject certifies? True  <-- FALSE CERTIFICATE
```

**Two assertions are outright vacuous.** `tests/test_shift.py:78-91` asserts
`rb["reason"] is None or rb["reason"] in {"failsafe","bbse-degenerate-bootstrap","bbse-ill-conditioned","bbse-misspecified"}`
under the comment *"never a silent certify-and-violate."* (That comment text was removed by the fix this row
prescribes and has no current match; the comment at `:78-81` now records the vacuity lesson explicitly.) That set
**is** `certify_bbse`'s complete return domain (`shift.py:332-393`), so the predicate is identically true.
`tests/test_pipeline.py:42-45` checks only that three
tokens — `"per-target-site"`, `"NOT a bound"`, `"OUT OF SCOPE"` — appear *somewhere* in the guarantee string, which
is why mutation #13 survives while asserting the exact opposite of the intended clause. (That three-token check no
longer exists; the exact-string freeze this finding prescribes lives at `tests/test_report.py:179-191`.)

`certgate/harness.py` has **zero** tests; no test file imports it. `SPEC.md`'s Tests section lists no `test_harness.py`.
(`tests/test_harness.py` now exists — fix (1) of this row.)
I verified the module is nevertheless *correct* — `wilson_lcb` matches the closed form and `exceedance_reference`
matches brute-force enumeration including the integer-boundary cases — so this is a complete coverage hole over the
paper's measurement instrument with no error behind it today.

**Fix.** Priority order: (1) a `tests/test_harness.py` covering `wilson_lcb`, `exceedance_reference` and
`hard_violation` against closed forms — kills #6, #7. (2) A δ-accounting spy: monkeypatch `wsr_reject` with a
recording wrapper, run `run_certgate` per mode, assert the recorded δ arguments are exactly `{DELTA}` and
`{BBSE_DELTA_BET}` — kills #2, #3. (3) An M-cap test with sizes spanning 20 and 3000 against `M=100`, asserting
`z.min() >= 0 and z.max() <= 1`, plus the counterexample above — kills #1. (4) Freeze the guarantee statement by
exact string comparison for a known `(alpha, modes)` pair — kills #13, #14. (5) Give `_manual_fit`
(`tests/test_shift.py:205-210`) a multi-element walk order; today it supplies `np.array([0])`, under which `break`
and `continue` are provably indistinguishable — kills #8. (6) A walk-order provenance test: permute `cal` labels
within sites and assert the walk order is unchanged — kills #5. (7) Flip one calibration label and assert
`prov["input_hashes"]` differs — kills #9, and is the same assertion V13's fix needs.

---

#### V7 — E2 and E3 run at an undeclared `sep = 1.8` while every document states 2.2
*(= TS-06)*
**Location:** `experiments/run_synthetic.py:40`, used at `:195` (E2) and `:264` (E3) — the constant no longer
exists; those two call sites are `run_synthetic.py:457` and `:574` today.
**Empirically demonstrated (by prior passes; mechanism verified by me).**

```python
SHIFT_SEP = 1.8                             # realistic head so shift bites
```

*[Exhibit of the 2026-07-25 source, kept verbatim. The constant was deleted by the fix this finding
prescribes and has no current match: E2 and E3 now build `SimConfig()` at `run_synthetic.py:457` and `:574`,
each emitting `sep` into its summary block at `:494` and `:623`.]*

Used only by E2 and E3. E1 (`:245`), E4 (`:670`), E5 (`:739`) and E6 (`:911`) all use `SimConfig()` → `sep = 2.2`.
I confirmed by grep that **no document mentions 1.8 anywhere**; the only `sep` hit across `SPEC.md`, `METHODS.md`,
`README.md` and `paper/draft.md` is `SPEC.md:147` (`sep=2.2`). `paper/draft.md:152` — the Experimental setup section
governing all six experiments — states *"the two class means separated by sep = 2.2"* (the setup paragraph is
`paper/draft.md:125` today and no longer states `sep` numerically; the quoted sentence has no current match), and
§4.3/§4.4 (`paper/draft.md:133-135`, `:137-139`) report the E2/E3 numbers without qualification.

Re-run at R=40 under each value (prior passes, consistent across two independent reproductions):

```
E2 uncorrected baseline:  sep=1.8 hard_violation_rate 0.4750  |  sep=2.2 (as documented) 0.3500
E3 concept control:       sep=1.8 0.8750 (risk 0.2069)        |  sep=2.2 0.6500 (risk 0.1567)
```

Two headline paper numbers (0.485 and 0.83) move materially under the setup the paper actually describes. The
qualitative conclusions survive — E3's control is still poisonous at 0.1567 > 0.10 — but a reader reproducing from
the stated setup gets different figures. None of `SHIFT_SEP`, `SHIFT_BASE`, `CONCEPT_INTERCEPT`, `ANCHOR_SITES`,
`QUICK_SWEEP`, `FULL_SWEEP` is pinned by `tests/test_constants.py`, and the E2/E3 summary blocks record
`target_base_rate` and `concept_intercept` but not `sep`.

**Fix.** Preferably run E2 and E3 at the documented `SimConfig()` so all six experiments share one generator.
Otherwise declare `sep = 1.8` in `SPEC.md`'s Experiments block and `paper/draft.md` §4.1, pin it in
`tests/test_constants.py`, and emit `sep` into the E2/E3 summary blocks.

---

### MEDIUM

---

#### V8 — The BBSE bootstrap box under-covers at the design's own cluster scale *(= BBSE-2)*
`certgate/shift.py:271-289`; `constants.py:18,31-32` (the audit's `:29` is under-determined at HEAD; the
bootstrap-box constants now span both lines). **Empirically demonstrated by two independent passes; I did not
re-run it** (each replicate costs 2000 bootstrap fits) and I record it on their consistent numbers.

The Bonferroni arithmetic is correct (3 × 0.008333 = 0.025), so the shortfall is the naive percentile method's
finite-cluster error, not a bookkeeping mistake. With the head held fixed so `(c0*, c1*, π_s*)` are exact population
constants, measured joint coverage against a nominal 0.975:

```
  aux sites= 42  JOINT = 0.942 / 0.945   <-- the 208-site headline scale
  aux sites= 83  JOINT = 0.927
  aux sites=160  JOINT = 0.947 / 0.967   <-- an 800-site cohort; does NOT go away at scale
```

Realized miscoverage ~0.055-0.058 against a budget of 0.025 — larger than the entire `DELTA = 0.05`. Every BBSE
certificate's printed *"probability >= 0.95"* is closer to ~0.92. The weak parameter is `π_s`, whose record-pooled
prevalence is a cluster-level ratio with heavy site-size tails. Held at medium rather than high: the miscoverage is
two-sided so only part is in the certificate-invalidating direction, the step is explicitly disclosed as asymptotic,
and no invalid certificate was isolated to this cause — unlike V2, whose control isolates it cleanly.

*[Note, 2026-10-29, text above kept verbatim: the "~0.92" charges every box miss to the certificate. The
dual-endpoint reduction consumes only coverage of the true odds ratio, which box coverage implies but does not
require; at 36, 42 and 74 auxiliary sites the post-hoc probe (`experiments/out-bbse-probe/`) measured it at 1,163
of 1,163 certifiable fits, so there the union bound gives a level of at least 0.97 and the box miss bounds the
level from below rather than setting it. The 83- and 160-site cells above were not re-probed.]*

**Fix.** Replace the naive percentile box with a studentized/BCa bootstrap over the existing site resamples, or
better, a finite-sample cluster bound: `c0`, `c1`, `π_s` are all ratios of bounded per-site quantities, so the WSR
machinery already in `certify.py` can be inverted to give finite-sample intervals at `BBSE_DELTA_CONF/BBSE_BONFERRONI`
— which also retires the asymptotic caveat entirely. Add a coverage regression test at `n_aux = 42`. Until then,
`METHODS.md:43` and `paper/draft.md:94` (restated at `:237`) must report the measured realized coverage, not only
the nominal `δ_conf`.

---

#### V9 — The target pool is never checked for site-overlap with `S_cal` / `S_aux` / `S_train` *(= CW-3)*
`certgate/pipeline.py:184`. **Empirically demonstrated.**

The whole data-discipline gate is `assert_site_disjoint(train=train, aux=aux, cal=cal)`. The target enters as a bare
`target_x` plus a free-text `target_label` and is never compared to anything, even though `METHODS.md:7,25` scope the
guarantee to *"a NEW target site"* and `pipeline.py:271` already passes `str(target_label)` into provenance:

```
  target = calibration site 's-0000' (its own records), label = the same string
  reason=None  operative={'alpha': 0.1, 'tau': 0.55, 'deploy_mode': 'baseline', ...}
  target = the ENTIRE calibration cohort -> reason=None, operative alpha/tau = 0.1/0.55
```

The certificate is issued with the full per-target-site guarantee text for a site whose own records are among the
calibration atoms that produced it. No warning; nothing distinguishes it from an honest fresh-site run. Medium rather
than high: the guarantee is not mathematically invalidated for the site population, but the walk stops at a τ chosen
partly on this site's own atom, so the reported coverage and estimated-tier risk are selected on the target itself —
the exact leak the F03 assertion exists to prevent, on the one split it does not cover. `examples/real_data_example.py:122-126`
tells practitioners that `run_certgate` asserts site-disjointness at entry without qualifying that the target is excluded.

**Fix.** After `pipeline.py:184`, raise if `str(target_label)` is in the union of the three cohorts' `site_labels`.
Add an optional `target_site_labels=None` keyword and assert full disjointness when supplied — `target_label` alone
cannot catch a target pool whose records come from a cal site under a different label. Update `SPEC.md`'s gate list
and the example's comment.

---

#### V10 — Missing site ids are coerced into a bona fide pseudo-site *(= VB4)*
`certgate/validate.py:183-190`. **Empirically demonstrated:** `densify_sites(['A', None, float('nan')])` →
`('A', 'None', 'nan')` — three legitimate clusters, two fabricated from missing data.

The damage is two-sided: records with no known cluster are welded into one fake independent unit, while every affected
real hospital simultaneously has its records split between its own cluster and the `'None'` cluster — the
anti-conservative direction demonstrated under V4. The contract violation is sharp and internal to the same file:
`coerce_labels` (`validate.py:103-158`) explicitly rejects NaN and None in the **label** column, with a comment that the
code never guesses at a caller's intent (`validate.py:5`, still verbatim; `coerce_labels`' own echo is
*"It never guesses."* at `validate.py:108`), while the **site** column — which the whole method designates as the unit of
statistical independence — gets no such check thirty lines earlier. `CLAUDE.md` lists loud boundary validation as a
non-regressable invariant.

**Fix.** In `densify_sites`, before building `labels_str`, raise `CohortError` on None, float NaN, and empty/whitespace-only
strings, mirroring `coerce_labels`' wording. Add the rule to `SPEC.md`'s `densify_sites` contract line.

---

#### V11 — The provenance block does not bind the calibration labels or the site partition *(= CG-R4)*
`certgate/report.py:35-73`, `certgate/pipeline.py:252-273`, pinned incomplete at `tests/test_pipeline.py:98-107`.
**Empirically demonstrated:**

```
  run1 certified: [(0.05, 'declined', None), (0.1, 'certified', 0.55)]
  run2 certified (35% of cal LABELS flipped): [(0.05, 'declined', None), (0.1, 'declined', None)]
  input_hashes IDENTICAL? True
  keys hashed: ['aux_x', 'cal_x', 'target_x', 'train_x']
```

One run certifies, the other refuses, and the reproducibility record cannot tell them apart. Only the four feature
matrices are hashed — no `y`, no `site_id` — and `tests/test_pipeline.py:103-106` pins exactly that key set, freezing the
omission into the suite. Separately, `report.py:57-62` hashes raw bytes with no shape or dtype in the digest, so a
reshaped or transposed matrix is provenance-indistinguishable from the original. This cannot produce a wrong
certificate, but it defeats the stated purpose of the block (audit F49) and it is the one artifact a reviewer or
regulator would rely on to reproduce a certificate.

**Fix.** Pass the label and partition arrays to `provenance()` too. Bind shape and dtype into the digest. Update the
test to the new key set **and** add a content-binding assertion: flip one calibration label, re-run, assert the hashes differ.

---

### LOW

Fifteen defects that change no certificate the package can issue today. Compressed, with location, one-line
statement, and fix. All empirically demonstrated except where noted.

| ID | Statement | Location | Fix |
|---|---|---|---|
| **V12** *(CC-4)* | The record-carrying cluster gate can never differ from `n_sites` on any sanctioned input path — `make_cohort` rejects gappy `site_id`, so `(site_sizes > 0).sum() == n_sites` always. A guard that cannot fire, credited by `SPEC.md`/`CLAUDE.md` as load-bearing audit-B-5 hardening. The `np.where(sizes > 0, …)` at `certify.py:57-59` is likewise unreachable arithmetic (the divisor is already `np.maximum(sizes, 1.0)`). | `validate.py:332-334` (`make_cohort`'s density check; the deliberate allowance is documented at `validate.py:42-45` and `site_sizes` at `:97-100`) vs `pipeline.py:275,286` | Either make the guard real (an explicit `n_sites` parameter threaded through `subset_sites`) or delete the dead distinction and amend the conformance checklist. Do not leave it as false assurance. |
| **V13** *(BBSE-3)* | The certified guarantee text asserts the bootstrap box is *"the single non-finite-sample step in the chain."* False given V2: the `q_t` plug-in is a second unmodelled step which, unlike the bootstrap, receives no confidence allowance at all. The sentence structure claims completeness — it enumerates its randomness sources, and the target-pool draw appears in neither. | `report.py:149-161`; `METHODS.md:43,84`; `paper/draft.md:94,101,237`; `shift.py:19-22,59-60,258-259` | Amend `SPEC.md:844-851` first, then the text. Delete the "exact on the pool" comment and the "exact under the design-conditional estimand" clause — they are the false premise (both were deleted by this fix; neither has a current match). Restate after V2 lands. |
| **V14** *(BBSE-4)* | Both `fit_bbse` decline gates are NaN-blind: an empty `target_x` gives `q_t = NaN`, both comparisons evaluate False, and the call dies later inside `influence_atoms` with an error naming *weights* rather than the empty pool. `max(1.0, nan)` silently returns 1.0. | `shift.py:258-259,303,307` | Return a new `bbse-empty-target` decline after line 87 (now `shift.py:236-239`); invert the gate to `if not (lo[0] <= q_t <= hi[1])` so NaN declines. Reachable only via the public `fit_bbse`; `run_certgate` catches it at `MIN_ANSWERABLE`. |
| **V15** *(CW-4)* | `Cohort` is a plain frozen dataclass exported in `__all__` with no `__post_init__`, and `run_certgate` re-checks only feature width — so cohorts `make_cohort` explicitly refuses (non-dense `site_id`, float `y`, non-finite `x`) flow straight through to a certificate. The repo's own tests rely on this bypass. Direction happens to be conservative in every case I tried; nothing in the design makes that general. | `validate.py:30-100` (`__post_init__` now at `:55-83`) | Give `Cohort` a `__post_init__` running the same checks; move the five contract-violating test fixtures to a named test helper. |
| **V16** *(CW-7)* | `_feasibility` initialises `best = -np.inf` and never restores a finite value when no τ achieves coverage, emitting `margin=-inf, ratio=-inf` into the report diagnostic — not strict-JSON serialisable. Verified: `json.dumps(..., allow_nan=False)` raises. The certified path is safe (it declines to failsafe). | `pipeline.py:36-68` (`best = None` at `:54`) | Track feasibility explicitly with `None` rather than a sentinel; `None` serialises as JSON `null` and cannot be mistaken for a very bad but real margin. Same latent issue in the `floor` branch. |
| **V17** *(VB3)* | `make_cohort` checks `y.dtype.kind == "b"` but never `y.ndim == 1`, so an `(n,1)` bool column is accepted and broadcasts `predict(x) != y` into an `(n,n)` matrix — a 30+ GiB `MemoryError` deep in the pipeline instead of a typed `CohortError` at the boundary. Same omission for `site_id`. | `validate.py:315-334` | Add `ndim != 1` checks before the dtype checks, so `np.bincount` is never reached with a 2-D array. |
| **V18** *(VB5)* | `require_both_classes=False`, which `SPEC.md:123-127` restricts to target pools, is an unrestricted public keyword; nothing tags a Cohort's role and `run_certgate` never re-checks. An all-negative **calibration** cohort is admitted and certifies, with BBSE's reweighting silently inert (`w = where(cal.y, rho, 1.0)` is constant) yet still listed as a covering mode. Direction is conservative. | `validate.py:357-358`; no counterpart in `pipeline.py` | Enforce at the boundary where roles are known: in `run_certgate`, require both classes in each of train/aux/cal. Suppress `bbse` from the covering-modes list when the fitted weight vector is constant. |
| **V19** *(VB6)* | `oracle_target_y` is the only `run_certgate` input with no validation anywhere and is coerced with `np.asarray(…, dtype=bool)`. A length-1 array broadcasts to a fabricated all-negative composition; a float probability array coerces to all-positive. Both produce plausible-looking but fabricated `oracle_true_class` figures — the field reported as E6's composition row. Never touches the certificate. | `pipeline.py:172-181`; `explain.py:342-344` | Validate at the boundary in `run_certgate`: 1-D bool of length `target_x.shape[0]`. |
| **V20** *(CG-R3)* | "Exact Shapley values" is unqualified but exact only for the **interventional** value function with the training-mean background — an unnamed choice. The shipped generator's features are correlated by construction (max off-diagonal correlation ~0.10-0.13), so conditional Shapley values differ. The stated justification (`sum(phi) + intercept == logit`) is a non-sequitur: efficiency is one axiom, and both decompositions satisfy it identically, which is why `tests/test_explain.py:28-34` does not test the claim at all. Magnitude disputed between passes (median 3.1%-14%); the *kind* is not. | `explain.py:3-10`; `METHODS.md:54`; `SPEC.md:303-306`; `paper/draft.md:107,199` | Name the value function and background in all four places; cite the Linear SHAP interventional result instead of the efficiency identity. Claim-precision only — no computed number is wrong. |
| **V21** *(CG-R5)* | `_bootstrap_estimate` discards every resample whose answered mass is zero and quantiles over the survivors — the exact pattern `SPEC.md:241` forbids for the BBSE box ("never quantile over a reduced count — audit F40/B-8"), with no top-up and no decline. The dropped resamples are precisely the low-mass ones, so the surviving quantiles are biased. Also returns `point=0.0` (not NaN) when nothing is answered. **Latent:** I could not reach either regime through `run_certgate`, and believe it unreachable — at a τ answering nothing, every atom equals α exactly and the wealth process cannot move. | `report.py:195,200-209` | Return NaN for an empty answered set; adopt `shift.py:271-284`'s top-up-or-decline discipline; surface `n_boot` in `render_text`. |
| **V22** *(CG-R6)* | When every target case is answered (or every one declined), `cohort_abstention_profile` produces an all-NaN gap whose `np.argsort` returns the **identity** permutation, and E5 then reports feature 0 as the top abstention driver with no basis in the data. Also writes bare NaN into `E5_explain.json`, which the harness elsewhere explicitly forbids. Latent: the shipped run has `n_declined = 2`. | `explain.py:218-250` (ranking guard now `:239-242`); `run_synthetic.py:800-802,899-900` | Return an empty ranking rather than `argsort` of NaN; guard both consumers to emit `None`. |
| **V23** *(CG-R7)* | `run_certgate` validates `alphas` loudly against the frozen ladder but performs **no** validation of `modes`, so a misspelled mode yields a full all-declined report with `reasons={}` — indistinguishable from a genuine statistical decline. An empty `modes` tuple behaves identically. Fail-safe in direction. | `pipeline.py:137-141` vs `:329-338` (the modes gate this row prescribes is now `pipeline.py:143-149`) | Mirror the `alphas` gate: raise on any mode outside `('baseline','bbse')` or an empty tuple. |
| **V24** *(CG-R8)* | `_statement`'s `deploy_mode` parameter is never read in the body. Verified: output is identical for `'baseline'`, `'bbse'` and a garbage value. The emitted statement never names which assumption mode backs the deployed threshold. | `report.py:76` (signature now `_statement(alpha, modes)` — `deploy_mode` deleted), called at `report.py:330` | Delete the parameter, or make it load-bearing by naming the deployed mode in the text. Deleting is smaller and removes the silent-garbage-accepted behaviour. |
| **V25** *(CG-R10)* | The gated-exit path returns a diagnostic dict missing five keys `SPEC.md` lists unconditionally (`composition`, `abstention_profile`, `capped_influence_share`, `rm_vs_unweighted`, `bbse`), so a consumer indexing them raises `KeyError` on any gated report. Mitigating: the gated path has `head=None`, so three are genuinely uncomputable. *(The sub-claim that declined rows carry `tier="certified"` is cosmetic — `status` disambiguates — and I would not have filed it alone.)* | `report.py:306-312` vs `:376-391` | Emit a stable key set with explicit `None` values; `capped_influence_share` can actually be computed there. |
| **V26** *(TS-12)* | `_write_summary` carries forward blocks for experiments not recomputed, but the header records only the current invocation's mode and no marker distinguishes recomputed from preserved sections — so `summary.md` can read `mode: FULL` while its E1 block is an R=10 QUICK result. E5/E6 emit neither `R` nor mode, so a preserved block from an earlier code revision is indistinguishable from a fresh one. Related: `run_E3` raises its poison-verification error before `_write_summary`, so an aborted full run leaves fresh CSVs beside a stale summary. | `run_synthetic.py:1803-1837` (`_existing_summary_blocks` at `:1784-1800`; the `finally` this row prescribes is now `:1866-1869`) | Stamp mode and timestamp per block; prefix preserved sections with a visible marker; write the summary in a `finally` block. |

> *Note (2026-10-29), V21's rationale.* The fix this row prescribes stands; the reason it gives does not. The
> drop-only loop and top-up-or-decline discard exactly the same resamples, those with zero answered mass, where
> the ratio is undefined; attempts are i.i.d., so the retained draws follow the same law in both — the resampling
> law conditional on positive answered mass — and the survivors' quantiles were not biased relative to a topped-up
> count. Top-up-or-decline holds the Monte-Carlo count at `n_boot` and adds the shortfall rule: fewer than `n_boot`
> valid draws within the attempt budget (by default `2 * n_boot`, so more than half the attempts had zero answered
> mass) yields NaN. The `point = 0.0` half of the row is unaffected. The `_bootstrap_estimate` docstring and the
> `site_bootstrap_ci` shortfall comment, which repeated the reason, are corrected (CORE-10, reliability-7).

---

### PLAUSIBLE

#### V27 — The operative rung is a post-hoc selection across the α ladder, but its statement still claims 1−δ
*(= CG-R9)* · `report.py:322-336`; `constants.py:16`. **Reasoned only — no counterexample constructed.**

`build_report` designates the strictest **certified** α as operative and derives the deployed answered mask,
estimated tier and diagnostics from it. Each rung is walked at full `DELTA` with no ladder-level correction.
Let `F_a` = {rung `a` certifies while the truth exceeds `a`}; `P(F_a) ≤ δ` per rung. The operative claim is false
iff `(op=0.05 ∧ F_0.05) ∨ (op=0.10 ∧ F_0.10)` — disjoint events summing to at most `2δ = 0.10`. The user is told
`risk ≤ α_op` where `α_op` is itself random.

Three things hold the severity down: every individual row remains marginally valid at 1−δ and `build_report` emits
**all** rows; `SPEC.md` pipeline step 7 explicitly documents "operative rung = strictest certified alpha", so this
is a design choice under the binding contract rather than a contract violation; and with a 2-rung ladder where
α=0.05 never certifies at 208 sites in any shipped experiment, the selection is degenerate in practice.

**The single check that settles it:** build a fixture where both rungs certify simultaneously and the 0.05 rung is
falsely certified, then measure `P(risk > α_op)`. E4 reaches α=0.05 only at 300-400 sites, where 0.10 also
certifies — a construction is possible there. Cheapest honest fix: add a clause noting the rung was data-selected
and the selected claim holds at 1−2δ across the ladder.

---

## Refuted

These were investigated and found sound. This list is a deliverable: it records what was checked and survived.

- **CC-3 — "the OR-rule spends δ twice on the same calibration split."** *Refuted.* The union bound is not needed
  because the two modes do not make claims about the same estimand: baseline certifies the unweighted `R_M`, BBSE
  the ρ-reweighted one (`shift.py:366-370`). There is no single event whose probability needs splitting. The emitted
  claim is a *per-assumption conditional* ("Under the tagged assumption (exchangeability **or** label shift)"), and
  `_combine_alpha` lists a mode only if that mode's own certified set contains the deployed index — so for each
  assumption named, the mode carrying it ran its own level-δ procedure and certified that exact index. Fixed-sequence
  gives FWER at δ over the whole certified set, so the argmax across modes introduces no selection inflation. Baseline
  spends `DELTA = 0.05`; BBSE spends `0.025 + 0.025 = 0.05`. Each conditional claim is at 0.95 as printed. The auditor
  states outright that they could not construct a configuration exceeding δ — consistent with the math being correct.

- **CW-5 — "the record-carrying cluster gate is hollow because it equals `n_sites` everywhere."** *Refuted, and it
  refutes itself.* The arithmetic half is true and is recorded as **V12**. But the conclusion does not follow: the
  hand-built `Cohort` path (documented reachable under V15) does produce the distinction — a probe produced
  `n_cal = 165` against `n_cal_carrying = 83`, with both surfaced in the diagnostic tier. The guard fires and is
  visible. What remains is redundancy on the constructors that validate upstream, which is defence-in-depth, not a
  defect. Note also that the real cluster-inflation attacks (V4, V5) both produce record-**carrying** clusters, so
  counting only record-carrying sites would not have blocked either — the gate is not the wrong guard, it is simply
  not the guard that matters here.

- **VB2 — "`assert_site_disjoint` compares `str()` labels, so `S_aux == S_cal` certifies."** *Confirmed but merged
  into V4.* The behaviour reproduces exactly and I verified it independently. It is not a separate defect:
  `assert_site_disjoint` comparing `site_labels` is correct by design; it is `densify_sites`' unnormalized `str()`
  that manufactures `'0'` and `'0.0'` as distinct identities for one hospital. Same root cause, same fix. The
  multiplicity-budget consequence is preserved in V4 so it is not lost in the merge.

- **VB7 — "`Cohort` is exported with no `__post_init__`."** *Duplicate of V15*, same location and same fix. V15 is
  the survivor because it additionally documents that `run_certgate` re-validates only feature width and alpha
  membership, which is the second half of the same hole.

Also refuted in passing, recorded because a reader may wonder: the auditor's PROBE B under CC-2 asserted that a
calibration draw whose *realized* atom mean exceeds α admits no valid certificate, so a label certifying it must be
false. That is wrong — validity is a statement about `E[Z]`, not the realized sample mean, and a sup-crossing on
such a sample is inside Ville's budget. I did not rely on it; V3 demonstrates the real version at a true boundary null.

---

## What is verified vs. what is assumed

**Verified — a test would go red if it broke.** I confirmed the first four by mutation.

- The WSR level itself: lowering the sup-crossing threshold `1/δ → 1/√δ`, removing the λ cap, and dropping the atom
  recentering offset are all **caught** (`test_wsr_boundary_type_I_at_n80`, observed 0.0213 against a 0.08 tolerance).
  *(2026-10-29 note, NUM-2; the bullet above is kept as filed. It overstates what this check resolves. On {0,1}
  atoms at n = 80 the test hangs on one integer, the step at which an all-zero run first crosses `1/δ`: at
  α = 0.05 it rejects exactly when the first 66 atoms are all 0, so the shipped level at this null is
  0.95^66 = 0.0339, and the 0.08 tolerance has no power against moderate inflation — a `1/(2δ)` bar (exact level
  0.0756 > δ) scores 42/800 and passes, and a λ computed from the current atom scores the identical 17/800. Of the
  three mutations named, `1/√δ` (127/800) and the uncapped λ (111/800) are caught here. Dropping the recentering
  offset is not: read as `α − Z → −Z` it never lets the wealth rise (0/800) and is caught by
  `test_wsr_power_under_clear_margin`; read as the `+ α` of `influence_atoms` it is caught by
  `test_atom_range_and_empty_site_neutral`. The same test now also pins the crossing steps exactly (`rng=None`): 66
  and 33 for an all-zero run at α = 0.05 and 0.10, no recovery from one loss among the first 66 atoms at
  α = 0.05, and recovery at step 58 from a loss at step 20 at α = 0.10. Those pins go red under the `1/(2δ)` bar
  and the current-atom λ.)*
- The baseline walk's `break` — fixed-sequence FWER on that path — is **caught**.
- The frozen constants, literally pinned by `tests/test_constants.py` including the full `TAU_GRID` array.
- Determinism: byte-identical reports in one process, across processes, under different `PYTHONHASHSEED`, and after
  corrupting the global `np.random` state. Every stochastic source is seeded from `constants.SEED`.
- The four decline paths, the ρ-box width, the BBSE re-weighting, the site influence weight, the OR-rule, the 40/20/40 split.
- The `_combine_alpha` OR-combination logic, which is well unit-tested.
- The input boundary for every input class it was designed against: non-finite features, non-bool labels, >2 distinct
  labels, gappy/negative/out-of-range site ids, length mismatch, empty arrays, single-class fitting cohorts, wrong-width
  target. Six auditors tried and failed to break these.

**Assumed — reading the code and believing it.** Each of these is a mutation that survives 69/69:

- The M-influence cap, i.e. the [0,1] boundedness Ville's inequality **requires** — the project's headline
  cluster-as-unit idea.
- The δ accounting at its point of use: the baseline walk's `DELTA`, BBSE's `BBSE_DELTA_BET`, and the box's
  Bonferroni-over-3. Only the *arithmetic on the constants* is pinned; the three call sites are not.
- That the fixed-sequence walk order comes from `S_aux` rather than `S_cal`.
- `certgate/harness.py` in its entirety — `wilson_lcb`, `hard_violation`, `exceedance_reference` — which produces
  every violation number in `summary.md` and the paper. (Verified correct by hand in this pass; verified by no test.)
- The content of the guarantee text. Four of the five clauses `CLAUDE.md` names as a hard invariant can be silently
  weakened, including inverting the concept-shift disclosure to its exact opposite.
- BBSE's fixed-sequence `break` — untested because the only fixture reaching it supplies a one-element walk order.
- Provenance content binding; the bootstrap top-up-or-decline partial-validity branch; tie handling between the
  certified statistic and the deployed answered mask; the estimated tier; the F26/F51 diagnostics.

**Assumed and outside anything a test could currently rule out:**

- That the declared clustering is the honest one. Nothing at pipeline entry re-checks it (V4, V5).
- That the target pool is genuinely a new site (V9).
- The behaviour of the whole method under between-site risk heterogeneity beyond `s_u = 0.5`. The frozen generator
  does not explore it, and V1 shows the headline validity claim is not robust to it.
- Anything on real data. Every empirical claim in this repository rests on one synthetic generator.

---

## Recommended actions

### Before the paper is submitted

1. **`SPEC.md:817-851` — change the mandated guarantee text first.** It is the binding contract and it currently mandates
   two false clauses. Nothing else in this list can be done correctly before it. *(V1, V3)*
2. **`certgate/report.py:76-162` — state the estimand the test certifies.** Replace "at this target site" with the
   population-average wording and add the between-site-dispersion clause. Then `METHODS.md:7,21-23,25,62-65` and
   `paper/draft.md:52,101,247`. *(V1)*
3. **`experiments/run_synthetic.py` — rescore or relabel E1's conformance metric, and report the `s_u` sensitivity.**
   The published 0.01 is a property of `s_u = 0.5`; at `s_u = 2.0` it is 0.10. A reviewer who varies one documented
   generator parameter will find this. *(V1)*
4. **`certgate/shift.py:258-259` — give `q_t` a confidence share** (`BBSE_BONFERRONI = 4`, Clopper-Pearson or cluster
   bootstrap, 16 corners). Then re-run E2. Expect more declines; that is the correct behaviour. *(V2)*
5. **`certgate/certify.py:152-174` — drop `target_label` from the permutation seed**, and strike the "cannot be chosen
   to flatter the outcome" claim at `paper/draft.md:84`. Delete the shared-event clause for BBSE, which cannot be
   restored. *(V3)*
6. **`experiments/run_synthetic.py:40` — resolve the `sep = 1.8` discrepancy**, preferably by running E2/E3 at the
   documented 2.2 (the constant is gone; E2/E3 now build `SimConfig()` at `run_synthetic.py:457,574`). Two headline
   numbers in the manuscript come from a generator the manuscript does not describe. *(V7)*
7. **`report.py:149-161`, `METHODS.md:43` — stop claiming a single non-finite-sample step**, and report the box's
   measured realized coverage at the deployed cluster count. *(V8, V13)*
8. **`tests/` — close the three test gaps that guard paper claims:** `test_harness.py`; the δ-accounting spy; the
   exact-string guarantee-text assertion. *(V6)*

### Before anyone runs this on real patient data

Everything above, plus:

9. **`certgate/validate.py:253-287` (canonicalization now at `:161-212`) — canonicalize site identity and reject missing site ids loudly.** This is the
   single highest-risk item for real data: a routine data-quality defect in one column silently redefines the unit of
   statistical independence and buys a strictness rung the honest clustering refuses. A real extract will have dirty
   site ids. *(V4, V10)*
10. **`certgate/validate.py` — reject duplicate `site_labels` in `make_cohort`.** *(V5)*
11. **`certgate/pipeline.py:184` — assert the target pool is site-disjoint from train/aux/cal**, and add
    `target_site_labels`. Correct `examples/real_data_example.py:122-126`. *(V9)*
12. **`certgate/validate.py:31` — give `Cohort` a `__post_init__`** (now at `:55`) so the documented input contract is not optional
    through the public API. *(V15)*
13. **`certgate/validate.py:315-334` — enforce 1-D `y` and `site_id`**; a column-shaped label array from a loader
    currently detonates as a 30 GiB allocation rather than a typed error. *(V17)*
14. **`certgate/pipeline.py` — validate `modes`, `oracle_target_y`, and single-class fitting cohorts at the
    boundary.** *(V18, V19, V23)*
15. **Complete the mutation-hardening pass in `tests/`** for the remaining items in V6's table — walk-order provenance,
    the M-cap, the BBSE `break`, provenance content binding, tie handling.
16. **Fix the diagnostic-tier emission defects** before any output is machine-parsed: `-inf` into feasibility (V16),
    all-NaN gap ranking (V22), the gated-report key set (V25).
17. **Replace the percentile box with a finite-sample cluster bound** (V8), which also retires the last asymptotic
    step in the chain.
    *(2026-10-29 pointer: for a pool declaring ten or more target sites the q interval is a fourth percentile
    bootstrap, unprobed by `experiments/out-bbse-probe/`; it needs the same replacement.)*

---

## One-line summary

The procedure is correct and the certificate overclaims: `certgate` proves a bound on the influence-weighted answered
risk **averaged across sites** and prints it as a bound **at the target site**, which fails at twice δ under
heterogeneity the design explicitly anticipates; separately, the BBSE mode omits the target pool's sampling error and
issues genuinely invalid certificates at up to three times δ. Both are fixable without touching the betting core.

---

## Mathematical-exactness audit, 2026-10

Date: 2026-10-29; recorded in `SPEC.md` as PIN AMENDMENT 2026-10-29. A mathematical audit checked every formula,
constant, quoted number and stated property in `certgate/`, `experiments/`, `tests/`, `examples/` and the documents
against the code and the released artifacts. About 150 precision defects were confirmed, each by independent skeptic
verification. None invalidates a released certificate. Unlike the RESOLUTION list above, everything here landed after
the freeze and after submission; a change that can alter what is certified is labelled post-hoc.

No file under `experiments/out*/` was regenerated. A released artifact that keeps a wrong number or note is listed
under *Errata* at the end of this section, and corrected values go to new post-hoc sidecar directories:
`experiments/out-e6-composition/` (E6 BBSE-implied composition), `experiments/out-e8a-rescore/` (E8 comparators
scored against the exact population `R_M`), `experiments/out-e9-exact/` (closed-form estimands behind the paper's
§4.14), `experiments/out-derived-r2/` (corrected re-derivation; `out-derived/` stays as released) and
`experiments/out-eicu-composition/` (eICU composition and the exact `S_aux` margin, from the restricted extract).
The corrections to the paper, METHODS, SPEC and README for the same ids are made in those documents in the same
pass; this section records code, tests and artifacts. Ids are the audit's own (`CORE-`, `BBSE-`, `NUM-`, `FNR-`, `PROBE-`, `EICU-`,
`DOCS-`, `PAPER1-`/`PAPER2-`, `explain-`, `reliability-`, `synthetic-`, and `GAP-` for the coverage-gap round);
ids that name one defect share a line. These are the 2026-10 audit's ids; its BBSE-1 to BBSE-4 are unrelated to the
earlier aliases V2 = BBSE-1, V8 = BBSE-2, V13 = BBSE-3 and V14 = BBSE-4 above, and the dated notes above cite them as
'2026-10 BBSE-n'. Test citations are `tests/<file>::<test>`.

### Behaviour changes

- **NUM-1 — FIXED, post-hoc (certified path).** `fit_bbse` had no cluster floor on `S_aux`. With one site carrying a
  class, every valid resample reproduces that rate's point estimate, so the (c0, c1, π_s) box had zero width, passed
  the degenerate-bootstrap check, and `run_certgate` could certify on it. `fit_bbse` now declines
  `bbse-aux-clustering` when fewer than `BBSE_MIN_AUX_SITES = 10` `S_aux` sites carry a positive record, or fewer
  than 10 carry a negative one. The count is per class because `c1` resamples only across positive-carrying sites
  and `c0` only across negative-carrying ones; a count of record-carrying sites would admit ten sites with positives
  in one, or one site padded with empty labels. The check sits after `bbse-target-clustering` and before any
  resampling, draws no random number and keeps the 17-key diagnostics, so every fit above the floor is
  byte-identical. The constant is module-local to `certgate/shift.py`, because `constants.py` is the a-priori
  pre-extract surface (the `reliability.MIN_SITES_FOR_CI` precedent), and it takes `BBSE_MIN_TARGET_SITES`' value
  rather than a tuned one. No released fit moves, and this is evidenced: a replay of every synthetic label-shift
  stream found at least 28 `S_aux` sites carrying each class, and a 20-re-split eICU re-run on the restricted extract
  (36 auxiliary hospitals), made with the floor in place, reproduced every released eICU table and JSON exactly
  except the sanctioned composition fields, all 20 released BBSE fits included. The eICU per-class count itself is
  in no released aggregate; the re-run is the evidence that the floor did not fire. The floor removes the
  degenerate regime only; the box's finite-cluster under-coverage above it is V8 / Rec. 17 and is unchanged. With
  the floor in place `bbse-degenerate-bootstrap` is practically unreachable and stays as defence in depth. Pinned by
  `test_shift.py::test_few_aux_sites_decline_bbse_aux_clustering` (1, 3 and 9 sites, a one-site split padded with
  empty labels, twelve record-carrying sites with positives in one, and twelve with negatives in one all decline;
  ten sites fit), `test_pipeline.py::test_one_site_aux_declines_bbse_not_the_run` and
  `test_constants.py::test_bbse_min_aux_sites`. `test_shift.py::test_degenerate_ten_site_pool` (formerly `test_degenerate_three_site_pool`) and
  `::test_bootstrap_shortfall_declines_not_reduced_quantile` (V6 #10's pin, name kept) moved to ten-site pools and
  lower the floor by monkeypatch, so the bootstrap guard behind it stays exercised.
- **BBSE-1 — FIXED (diagnostic, not the certificate).** `explain.composition`'s BBSE-implied true-class view
  multiplied each answered record's head odds by `rho_point`, whose denominator is the `S_aux` prevalence, while the
  logistic head's odds carry the `S_train` prevalence. The multiplier is now
  `rho_point · odds(pi_source) / odds(pi_train)` = odds(π̂_t)/odds(π_train), with `pi_source` clipped to
  [`PI_CLIP`, 1 − `PI_CLIP`] as `rho_box_interval` clips it. `rho_point` without both priors raises `ValueError`
  (`reason=missing-prior`), a `pi_train` outside (0, 1) raises (`reason=bad-prior`), and `bbse_true_class` gains
  `odds_multiplier`, `pi_source` and `pi_train`. `build_report` takes `pi_train`, which `run_certgate` passes as
  `mean(train.y)`; `run_synthetic.run_E6` passes both priors. The certification weights, the walk orders and the
  estimated tier keep `rho_point` unchanged. Pinned by `test_explain.py::test_composition_bbse_divides_out_the_train_prior`,
  `::test_composition_bbse_view_requires_both_priors`, `::test_composition_three_tagged_objects` and
  `test_pipeline.py::test_composition_three_way_whenever_bbse_fit_holds`. Released values: *Errata* 1–2.
- **reliability-11 — FIXED (post-hoc panel; the one sanctioned code divergence from the srp port).**
  `calibration_pair` topped up `separable` and `single-class` resample refits, which deletes the infinite tail that
  `truncated-resamples` exists to protect, and still reported `ok`. Those refits now count toward
  `truncated-resamples`, as `coef-out-of-range` refits already did. `PANEL_DICT_SHA256` is unchanged, every released
  calibration block (126 of them) is `ok` with no top-up, so no released panel can move, and the certified path does
  not import the module. Pinned by `test_reliability_panel.py::test_separable_and_single_class_refits_truncate_rather_than_top_up`
  and `::test_panel_dict_digest_pinned`.
- **CORE-9, BBSE-6 — FIXED (diagnostic).** Under BBSE deployment `rm_vs_unweighted` compared a ρ-weighted `R_M`
  with an unweighted record error, so the gap mixed class reweighting with the influence cap. `unweighted_risk` is
  now Σ w·ans·err / Σ w·ans under the same deploy-mode weights, so the gap isolates the M-cap; under baseline
  (w = 1) it is bit-identical. Pinned by `test_report_estimated.py::test_rm_gap_isolates_the_influence_cap_under_bbse_weights`.
- **NUM-13 — FIXED.** `model._sigmoid` warned, or raised under strict floating-point settings, at extreme logits.
  Its `errstate` now silences overflow, underflow and invalid; the output is bit-identical. `reliability._sigmoid`'s
  docstring no longer claims a naive form would abort. Pinned by `test_explain.py::test_sigmoid_is_silent_and_exact_at_extreme_logits`.
- **explain-13, EICU-11 — FIXED (code only).** `run_eicu` re-scored the fresh-pool `R_M`, the per-site exceedance
  fraction and the abstention ranking at `round(tau, 6)`, one ulp from the deployed grid value at six grid points.
  `_eval_rung` now carries `tau_raw`, the deployed float64 τ, for all re-scoring; the tables still print the rounded
  τ. `rescore_e9a` snaps the CSV's 2-dp τ to the `TAU_GRID` double; a scratch re-run matched the released
  `E9a_rescore.csv` byte for byte on the scoring columns. No released number moves. Pinned by
  `test_eicu_run.py::test_pooled_rescoring_uses_the_raw_deployed_tau`.
- **GAP-unreviewed-tests-5 — FIXED.** No test pinned the registered failure criteria F-A to F-E, and F-B and F-D
  leg 3 compared rounded values with their thresholds. `_failure_criteria` now compares exact values: F-A on
  n_exceed/n_cert, F-B on the mean of n_answered/n_target, and F-D on unrounded row flags (`rm_fd_alarm`,
  `leak_auc_alarm`, `leak_ablation_alarm`), which are not CSV columns. The displayed coverage is byte-identical on
  every released `EICU_pooled.csv`. Pinned by `test_eicu_run.py::test_failure_criteria_thresholds_strictness_and_operative_row`.
- **EICU-12 — FIXED (settlement and derivation code).** `settle_predictions` and `derive_fixpass_numbers`
  departed from the registered P3, P4 and P6 rules in ways the released data never exercised. P3's falsification
  rule is now checked on every pool at both rungs (BBSE covering without baseline, or `bbse:certified-not-covering`);
  P4 counts one ranking per re-split, at the operative rung, with the registered matcher (`aps_present`,
  `apv_present`, or an `aps_*` / `apv_*` `__missing` sibling); P6 scores the mean coverage at each re-split's
  operative rung; P2 tolerates an uncertified re-split. `fig_eicu_abstention_drivers.load_rankings` keeps one
  ranking per replicate. No released verdict changes. Pinned by `test_sidecars.py::test_settle_p3_rule_reads_per_site_pools_and_both_rungs`,
  `::test_p4_matcher_is_the_registered_set`, `::test_p4_counts_one_ranking_per_replicate`,
  `::test_settle_p6_scores_the_registered_mean`, `::test_settle_p2_tolerates_an_uncertified_resplit`,
  `::test_derive_sens_decline_reasons_are_counts` and `test_eicu_run.py::test_abstention_figure_reads_one_ranking_per_replicate`.
- **EICU-2, EICU-13 — FIXED.** `derive_fixpass_numbers` looked for the seven columns appended on 2026-09-04 in
  `out-rev2/EICU_pooled.csv`, which never carried them, and took three ratios from intermediates already rounded for
  display. It now reads `out-rev2/EICU_comparator.csv` (`rev2.comparator_new_columns`, refusing a comparator file
  without them with `reason=rev2-columns-missing`) and rounds only its outputs; its docstring counts seven pinned
  values, not six. Its default output is `experiments/out-derived-r2/`, and `out-derived` joined `FROZEN_DIRS`.
  Pinned by `test_sidecars.py::test_derive_reads_rev2_comparator_columns`,
  `::test_rev2_sections_refuses_comparator_without_appended_columns`, `::test_derive_rounds_only_outputs` and
  `::test_derive_refuses_frozen_targets`. Released values: *Errata* 3.
- **reliability-1 — FIXED.** `panel_confusion_tables._agg` took medians of 4-dp per-replicate rates and rounded
  again; it now summarises the exact count ratios, rounded once, with a ratio self-check. No released artifact stores
  these medians. Pinned by `test_sidecars.py::test_confusion_table_summary_rounds_exact_ratios_once`.
- **PROBE-3 — FIXED (probe script).** `probe_bbse_coverage` labelled a fit clip-bound when `rho_hi > 100`, but five
  of the eleven fits so labelled never touch the π_t clip. `CLIP_BOUND_RHO` is gone; `_rho_hi_clip_bound` flags a fit
  when a (q, c0, c1) box corner implies π_t above 1 − `PI_CLIP`, with `rho_box_interval`'s arithmetic. A re-run
  would emit a `rho_hi_clip_bound` column and a `clip_bound_rule` key; the module docstring records the released
  run's figures. `out-bbse-probe/` is now in `FROZEN_DIRS`, so the probe refuses its released directory and a re-run
  needs `--out` pointing elsewhere. Pinned by
  `test_sidecars.py::test_probe_clip_bound_reads_the_box_not_a_rho_hi_threshold`. Released values: *Errata* 4.
- **explain-5 — FIXED (dashboards).** The threshold explorer and the histogram used 4-dp-rounded scores and
  floating-point bin edges, so they could disagree with the deployed rule. `build_dashboard` now emits integer
  histogram counts split by the deployed float64 mask and `explore_answered` counts, and the payload no longer
  carries `all_scores`. Both committed pages were re-rendered. Pinned by
  `test_explain.py::test_dashboard_histogram_and_explorer_follow_the_deployed_rule`.
- **explain-6 — FIXED (dashboards).** The abstention-profile panel ranked by the signed gap, not |gap|, and printed
  the synthetic "no stable driver" caution on eICU builds. The payload carries the library's `gap_ranking` and the
  panel takes its top 14; the caution names the synthetic null as synthetic. Pinned by
  `test_reliability_panel.py::test_dashboard_profile_ranks_by_abs_gap`.
- **GAP-example-builders-1, -2, -3, -4; GAP-estimand-wording-all-surfaces-3, -6 — FIXED (dashboards).** The
  committed mock page deployed `round(tau, 6) = 0.83` rather than the certified grid value `TAU_GRID[14]`; it now
  deploys the double and rounds for display only. The eICU page always cross-checked against the replicate-0
  primary-arm certificate; off replicate 0 or off the primary arm it now says the check is unavailable. Under BBSE
  deployment the eICU banner's answered risk names its reweighting. Both certificate banners describe `R_M` as
  M = 100 influence-weighted, state the per-rung 1 − δ and the joint level over the ladder
  (`joint_confidence_over_ladder = 0.9`), and carry `deploy_mode` and `tagged_assumption` in place of `mode`.
  Pinned by `test_eicu_mock.py::test_mock_page_deploys_the_unrounded_certified_tau`,
  `::test_mock_page_banner_carries_selected_claim_joint_level`, `::test_committed_mock_dashboard_certificate_states_joint_level`,
  `test_eicu_run.py::test_dashboard_skips_cross_check_off_replicate0_or_off_primary` and
  `::test_dashboard_answered_risk_names_bbse_weighting`.
- **synthetic-10 — FIXED (stdout only).** `panel_s2_tables.cap_facts` reported only a Monte Carlo share of sites
  above M; it now also emits the closed form `share_sites_above_M_exact` (0.896). `data.py` states the size draw as
  floor(clip(exp(N(size_mu, size_sigma²)), size_lo, size_hi)). Pinned by `test_experiments.py::test_cap_share_closed_form`.

### Guarantee text (exact-string pins changed under the SPEC amendment)

- **BBSE-2, DOCS-10 (audit unit multisite-q) — FIXED.** For a pool declaring ten or more target sites the q
  interval is a fourth percentile bootstrap, and the documents counted three asymptotic intervals. The BBSE box clause now ends "…the q_target
  interval is finite-sample Clopper-Pearson for single-site pools and an asymptotic percentile cluster bootstrap for
  multi-site pools." The `BBSEFit`, `_q_interval` and `fit_bbse` docstrings state which rate q names: the declared
  site's own rate for a single-site pool, the record-pooled rate of the target-site population for ten or more
  declared sites. Audit Monte Carlo (SimConfig defaults, base rate 0.22, the probe's fixed head; not a released
  artifact): Clopper–Pearson on the pooled count misses the site-population rate at 0.42–0.61 for K = 10–40 against a
  nominal 0.00625, and the declared sites' own rate at ≤ 0.0058; the bootstrap misses the site-population rate at
  0.015–0.06 (largest at K = 10) and the own rate at ≤ 0.001; inside `fit_bbse` (n_aux ∈ {36, 74, 240},
  K ∈ {10, 24, 40}, 200–300 fits per cell) the four-parameter box misses at 0.045–0.11 against 0.025, while
  [ρ_lo, ρ_hi] covered the population odds ratio in 2,398 of 2,400 fits and the declared pool's in all. These
  ranges carry Monte Carlo error of about ±0.01. A multi-site probe sidecar is deferred. Pinned by
  `test_report.py::test_guarantee_statement_frozen_both_modes`, `::test_guarantee_statement_frozen_bbse_only` and
  `test_shift.py::test_multi_site_q_interval_targets_the_site_population`.
- **BBSE-3 — FIXED.** The BBSE rows said the risk is reweighted to the target class prevalence, but ρ takes its
  source odds from the record-pooled prevalence while `R_M` weights sites by influence. BBSE rows now close: "Under
  label shift the odds ratio rho takes its source odds from pi_source, the record-pooled source prevalence, while
  the estimand weights sites by influence, so the reweighted risk is at the target class prevalence exactly where
  the record-pooled and influence-weighted source prevalences coincide, and otherwise at the prevalence whose odds
  are rho times those of the influence-weighted source prevalence." Pinned by the two frozen BBSE strings,
  `test_report.py::test_bbse_rows_never_claim_a_shared_event`, and, for the identity, by
  `test_shift.py::test_bbse_reweighted_class_mix_is_influence_weighted`.

### Docstrings and comments in `certgate/` (no behaviour change)

- **CORE-1, PAPER1-9, PAPER2-11.** The walk order is by the coverage- and influence-weighted atom margin
  α − mean_c Z_c = mean_c (g_c/M) a_c (α − e_c), largest first; it need not be monotone in τ or open at the highest
  threshold. `certify.py` module index and `walk_order`. Pinned by `test_certify.py::test_walk_order_key_is_atom_margin`.
- **CORE-2, NUM-3, PAPER1-1, DOCS-2.** The information floor ln(1/δ)(1−α)/n was described as an impossibility. At
  atom-unit margin m every valid level-δ test certifies with probability at most δ(1+m/(1−α))^n ≤ δ·exp(nm/(1−α));
  certainty needs m ≥ (1−α)(δ^(−1/n) − 1), of which the floor is the first-order term. `margin_floor`'s formula is
  unchanged: switching to the exact value would move released `feasibility` fields and two constant pins. Pinned
  by `test_certify.py::test_margin_floor_is_a_first_order_lower_bound`. Registered protocol wording: dated erratum
  in EICU-PROTOCOL.md §0.
- **CORE-3, NUM-6.** `_feasibility`'s margin is max_τ cov·(α − risk)·E[g/M] with cov and risk pooled over `S_aux`
  records — a record-pooled proxy for the atom-unit margin, which it equals only when the record-weighted and
  g-weighted site averages coincide. Pinned by `test_pipeline.py::test_feasibility_margin_is_the_record_pooled_proxy`.
- **CORE-4.** A neutral atom (value α) leaves the wealth unchanged but counts toward n and enters the running
  (μ, s²), so it can move the outcome either way, never the validity; dropping neutral atoms would leave `R_M`
  unchanged but make the atom count depend on τ. Pinned by `test_certify.py::test_neutral_atom_moves_bets_both_ways`.
- **CORE-16.** E[Z] ≤ α ⟺ `R_M` ≤ α needs E[g_c a_c] > 0; when nothing answers, `R_M` is 0/0, every atom is α and
  the test cannot certify. `influence_atoms` docstring and the `run_e9b_positives` analogue ("whenever some site
  answers a positive"). Pinned by `test_certify.py::test_atom_range_and_empty_site_neutral`.
- **CORE-13.** The bet's variance term is WSR's predictable plug-in s²_{t−1} = (WSR_S2_0 + Σ_{i<t}(z_i − μ_i)²)/t,
  μ_i = (WSR_MU0 + Σ_{j≤i} z_j)/(i+1), in processing order — not "the running variance of the atoms processed so
  far". Pinned by `test_certify.py::test_wsr_variance_is_predictable_plugin`.
- **CORE-15, DOCS-13.** The permutation-stream construction (`SeedSequence([SEED, alpha index, mode, w1, w2])`,
  w1 and w2 from a sha256 of the stream label, one permutation per test) is pinned by
  `test_certify.py::test_certification_rng_matches_documented_construction`.
- **CORE-5, PAPER1-10, BBSE-6.** The estimated tier estimates the record-pooled answered-set risk on `S_cal`, not
  `R_M`. `_bootstrap_estimate` docstring; console label "[estimated] record-pooled answered-set risk on S_cal
  (<mode>-weighted)"; the eICU dashboard helper and the derivation comment say the same. No τ-selection caveat was
  added (adjudicated: it is disclosed and measured negligible). Pinned by
  `test_report_estimated.py::test_estimated_point_is_record_pooled_not_rm`.
- **CORE-10, reliability-7.** The rationale for top-up-or-decline: a resample with zero answered mass has no ratio,
  and dropping it without a redraw quantiles the same conditional law from fewer draws; top-up restores the
  Monte-Carlo count, and the shortfall rule (more than half of the default 2·n_boot attempts invalid) declines.
  `_bootstrap_estimate` docstring and the `site_bootstrap_ci` comment; V21's rationale is annotated beside the LOW
  table. Behaviour pinned as before by `test_report_estimated.py::test_bootstrap_estimate_tops_up_to_full_count`,
  `::test_bootstrap_estimate_declines_on_topup_shortfall` and `test_reliability_panel.py::test_top_up_or_decline_attempt_arithmetic`.
- **CORE-8, NUM-8, DOCS-17.** `_capped_influence_share` computes the record mass beyond the cap. Pinned by
  `test_report.py::test_capped_influence_share_is_record_mass_beyond_cap`.
- **CORE-12.** Across modes the report deploys the maximum over certifying modes of each mode's own deployed (lowest
  certified) τ. Pinned by `test_report.py::test_deploys_max_of_mode_choices_not_union_max`.
- **GAP-estimand-wording-all-surfaces-8.** `_baseline_walk`: "one set of certified thresholds shared by every target
  pool", not "one certificate".
- **NUM-5, BBSE-4, CORE-14, PAPER2-3, PAPER2-4.** `rho_box_interval` said a clipped endpoint "fails to certify"; a
  clip-bound endpoint is tested like any other and can certify. The clip moves corner prevalences outside
  [1e-4, 1 − 1e-4] to the nearer bound, so it can exclude odds ratios implied by box points whose target or source
  prevalence lies outside that range; the interval covers the true ρ whenever the box covers the true parameters
  and both true prevalences lie in that range. Pinned by `test_shift.py::test_rho_box_interval_clip_semantics`
  (300 random gated boxes, and a box where the clip excludes the true ρ) and `::test_clip_bound_endpoint_can_certify`.
  REDTEAM R4's "only widens" is annotated there.
- **BBSE-8.** `shift.py` module docstring: the misspecification gate declines unless the q_t interval lies wholly
  inside the box's [c0_lo, c1_hi]; the gap gate is worst-case (lo_c1 − hi_c0). Pinned by
  `test_shift.py::test_gap_gate_is_worst_case_not_point` and `::test_q_interval_partial_overlap_misspecified`.
- **DOCS-15.** `test_shift.py`'s module docstring counts six BBSE declines, `bbse-aux-clustering` included.
- **explain-9, explain-10, explain-11.** `delta_*_min_l2` and `single_feature_delta_*` both carry the headroom; the
  pinv rationale holds "up to float rounding" (under mean imputation a feature and its own `__missing` sibling are
  uncorrelated on `S_train`); `declined` is the logit-space test and can disagree with the deployed float64 rule
  within rounding of the bar. Pinned by `test_explain.py::test_declined_flag_is_the_logit_test_at_the_float64_bar`,
  `::test_value_and_missing_sibling_are_uncorrelated_on_s_train` and the strengthened single-feature and dead-head
  tests.
- **explain-1, PAPER1-14, NUM-7, DOCS-5.** No code change: the counterfactual formulas use the head's coefficient on
  standardized features, as the code always did; the documents now define it. Pinned by
  `test_explain.py::test_cohort_gap_factorises_as_abs_standardized_coef` and
  `::test_counterfactual_formulas_use_standardized_coef_under_nonunit_sd`.
- **synthetic-4.** `model.py`: the score is thresholded on the fixed `TAU_GRID`, so a temperature change keeps ŷ and
  the score order but moves the candidate answered sets; only validity is calibration-free. Pinned by
  `test_certify.py::test_temperature_rescaling_keeps_labels_but_moves_grid_answered_sets`. Released note: *Errata* 7.
- **synthetic-2, PAPER1-2, DOCS-1.** Conformance is the share of certified draws whose fresh-pool `R_M` exceeds α:
  a conditional rate, scored on a finite-pool estimate of the population `R_M`; the betting test bounds the joint
  probability of certifying while the population `R_M` is at or above α. `harness.py`, `_rm_on_pool` and `run_E1`
  docstrings; the emitted `conformance_metric` string is unchanged. Pinned by
  `test_experiments.py::test_rm_exceed_rate_is_conditional_on_certified_draws`.
- **synthetic-3, PAPER1-16.** `exceedance_reference` is a homogeneous-batch yardstick that oscillates at small n and
  tends to 1/2, not a bound under heterogeneity. Pinned by `test_harness.py::test_exceedance_reference_small_n_lattice`
  and `::test_exceedance_reference_is_a_homogeneous_yardstick`.
- **PROBE-6, synthetic-12.** `data.py`: "posterior log-odds", and `logit P(y=1 | x, c) = …`.
- **reliability-6.** `_is_separated`: the pre-check is the only source of `separable`; data near the cut gives
  `coef-out-of-range` and a wide gap crawls to `not-converged`. Pinned by
  `test_reliability_panel.py::test_separation_precheck_names_the_defect_the_loop_cannot`.
- **reliability-3.** Differencing two marginal interval endpoints ignores their dependence, is typically far wider
  and has no coverage claim; it is not "strictly wider". Pinned by `::test_brier_difference_can_equal_endpoint_difference`.
- **reliability-4, NUM-9.** `skill_contrast`: answered_minus_all = w_d · answered_minus_declined − G with G ≥ 0;
  the inference that the least skill came from the gate's selection is removed. Pinned by `::test_skill_contrast_mixing_identity`.
- **reliability-12, NUM-14, DOCS-16.** `clipped_logit` saturates at about ±13.8155096, inside
  |logit| ≤ log(1/ε); five bins, not four, lie wholly below 0.5 for a probability-fed panel. Pinned by
  `::test_clipped_logit_saturation_value` and `::test_the_binned_quantity_is_predict_proba_not_score`.
- **reliability-2, reliability-10.** The ECE's plug-in bias is an absolute-value term ≥ 0 plus −Cov(ece, N)/E[N],
  of either sign; dated comments say how `notes[0]`, `notes[2]` and `WEIGHTING` should be read. Emitted strings are
  unchanged. Pinned by `::test_ece_plugin_bias_sign_depends_on_site_size_gap_covariance`. Released notes: *Errata* 9.
- **reliability-8, PAPER2-9.** The IRLS weight floor is a clamp and emits no status. Pinned by
  `::test_irls_weight_floor_emits_no_status`.
- **CORE-6, BBSE-7, PAPER2-2.** `N_BOOT` comment: at `CI_LEVEL = 0.95` each endpoint rests on about 50 tail draws.

### Experiment scripts and tests (comments, docstrings, non-emitted strings, new pins)

- **FNR-2, DOCS-3, FNR-8.** The shipped FNR atom's sign identity at FNR_M = E[g·fn/n] / E[g·ap/n] (SPEC's formula
  had dropped the 1/n_c) is pinned on unequal site sizes either side of the cap by
  `test_e9b_positives.py::test_shipped_fnr_atom_sign_identity`; the capped positive-count weight by the strengthened
  `::test_positives_atoms_bounded_in_both_regimes`. `run_e9b_positives` says "i.i.d. draws", not "exchangeable
  draws". Released README: *Errata* 6.
- **FNR-4.** The positives arm's weight rationale: validity needs i.i.d. atoms in [0, 1] whose mean crosses b
  exactly when the named estimand does; the requirement on the weight guards against a site factor that depends on
  the site's own errors, like the truncation of SI A.3. `run_e9b_positives` docstring; `ESTIMAND_NOTE` unchanged.
- **FNR-5.** On this generator FNR_M = FNR_M^+ at every τ, so the frontier gap is power, not estimand. Pinned by
  `test_e9b_positives.py::test_fnr_estimands_coincide_on_generator`.
- **FNR-1, DOCS-9, PAPER1-7.** b = 0.4 is not a negative control: FNR_M(τ) falls below 0.4 at high τ in most draws,
  and all six positives-atom certificates at 0.4 hold against the closed-form estimand. `E9_FNR_LADDER` comment,
  an erratum comment above the frozen E9 note, and the `run_e9b_positives` docstring. Pinned by
  `test_e9b_positives.py::test_b04_certificates_hold_against_closed_form_estimand`. Released note: *Errata* 7.
- **FNR-6, NUM-4.** The E9a rescore reweights the fresh pool to the declared pool's realised prevalence, a proxy for
  the estimand the certificate names; `population_odds_ratio` is the nominal per-site multiplier
  odds(0.22)/odds(0.095), not the record-pooled population ratio. Comments in `rescore_e9a` and
  `derive_fixpass_numbers` (keys and emitted strings unchanged). `test_shift.py`'s pure-label-shift test now scores
  the declared site's own odds ratio (1.886) rather than 2.687. Pinned by
  `test_shift.py::test_rho_truth_is_the_declared_sites_own`, `::test_pure_label_shift_falsifiability_and_bbse` and
  `test_sidecars.py::test_e9a_rescore_is_a_proxy_for_the_latent_prevalence_estimand`. Released files: *Errata* 5.
- **synthetic-5, PAPER1-4, PAPER2-1.** Table S4 replays all 200 validity-grid draws; the six BBSE-deploying draws
  enter at their baseline-walk threshold and only the self-check is restricted to the other 194. The e1 note string
  in `derive_fixpass_numbers` is corrected. Pinned by `test_experiments.py::test_table_s4_rows_count_bbse_deploying_draws`
  and `test_sidecars.py::test_e1_note_says_table_s4_replays_every_draw`. Released note: *Errata* 3.
- **synthetic-6.** On the generator `R_M` has one population value at every M, so the M-sweep compares procedures on
  one quantity. Pinned by `test_experiments.py::test_rm_population_value_is_m_invariant_on_generator`.
- **synthetic-9, PAPER1-17.** The chance reference for E5's modal top-feature share over 186 draws and four
  features is E[max share] = 0.288, not 0.25. Pinned by
  `test_sidecars.py::test_e5_modal_share_chance_reference` and `::test_e5_chance_reference_in_paper_text` (which
  checks that paper/draft.md quotes 0.288 at both places and no longer quotes the 0.25 chance level).
- **synthetic-11, PAPER1-19.** 0.095 is the base rate of a site with zero random effect, not the prevalence; the
  population prevalences are pinned by `test_sidecars.py::test_probe_truths_closed_form`.
- **PROBE-1, BBSE-5.** `probe_bbse_coverage` docstring: the union bound needs only coverage of the declared site's
  odds ratio, which box coverage implies; `implied_certificate_level` is the plug-in of the looser box-route bound,
  not the level. Pinned by `test_sidecars.py::test_probe_release_level_reads_from_rho_coverage`. Released reading:
  *Errata* 4.
- **PROBE-2.** Each bootstrap interval misses at 1.2–4× its nominal rate and the joint miss is exactly the sum of
  the parameter misses. Pinned by `test_sidecars.py::test_probe_joint_miss_is_sum_of_parameter_misses`.
- **PROBE-4, PROBE-5.** Probe denominators (1,163 certifiable fits of 1,200; 384–391 of 400 per cell) and the
  190-site arm's 33 `S_aux` sites, in docstrings and comments.
- **PAPER2-15; GAP-seed-stream-aliasing-1, -2, -3.** The E6 reliability panel self-seeds from `PANEL_SEED`, not
  `SEED`; E5's replication stream `_rng(5, 0)` is the case-study stream `_rng(5)`; draw 0 of E2 sweep arm m is
  anchor draw 100 + m; the probe's head stream `_rng(9, 2)` shares its entropy with `eicu_etl.site_split(replicate=2)`.
  Comments and docstrings. Pinned by `test_experiments.py::test_seed_streams_alias_at_trailing_zero`; the panel seed
  by the existing `test_constants.py::test_panel_schema_and_seed`.
- **EICU-3, DOCS-6, PAPER2-7.** A dated comment above the P2 note in `settle_predictions` (string unchanged). Pinned
  by `test_sidecars.py::test_p2_registered_basis_vs_settling_statistic`. Protocol: dated erratum to P2. Released
  note: *Errata* 8.
- **EICU-1.** A non-emitted comment in `exact_cis_section`: the `eicu_*` intervals are nominal over dependent units.
  Released intervals: *Errata* 3.
- **EICU-8.** `outcome_screen` decides the nine timing-unverified flags under the registered 0.75 rule; it bounds
  their univariate AUC but cannot establish their timing. Comments in `eicu_etl` and `run_eicu`; protocol erratum
  at §5.4a.
- **explain-2.** `run_eicu`, above `EICU_FAITHFULNESS_LABEL`: the Gaussian conditional is exact only for jointly
  Gaussian drivers. The label is unchanged.
- **GAP-unreviewed-tests-3, GAP-eicu-mock-math-8.** `site_split`'s refusal messages describe a sufficient floor, not
  an impossibility (148 sites yield 51 calibration clusters; the largest failing total is 145, which yields 49);
  reason tags unchanged. Pinned by `test_eicu_etl.py::test_site_split_refuses_below_the_sufficient_site_floor`
  (formerly `test_site_split_refuses_a_population_it_cannot_calibrate`).
- **GAP-unreviewed-tests-6, -7.** `EICU_MAX_OUTPUT_LEN`: the length cap does not catch short per-hospital record
  arrays; only the forbidden-key leg does, and only under a listed key; `eicu_etl.site_split` describes
  `fixture_etl`'s three pairwise asserts. Protocol errata at §15 and §7.
- **GAP-unreviewed-tests-4.** The end-to-end honesty assertion is a Wilson gross-violation screen of the
  record-pooled error, not a validity check (`_eicu_helpers`, `test_eicu_run`, `test_fixture_integration`).
- **GAP-unreviewed-tests-1, -2.** `test_comparators.py::test_t_and_bootstrap_pinned_and_every_ucb_above_the_mean`
  tests `t_ucb` and `site_bootstrap_ucb` on non-degenerate input, and a single atom's `hoeffding_ucb` is pinned as
  inf; three `test_experiments` helper tests gained the cases that separate them from plausible wrong versions
  (denominator, tie strictness, deploy rule, g/n weighting).
- **EICU-10, DOCS-12, GAP-unreviewed-tests-8.** Attrition: 1,751 blank-outcome stays and 618 adult-step stays;
  137,773 patients remain, 1.14% below the reference count.
  `test_eicu_etl.py::test_reference_check_passes_when_the_constants_match_the_corpus` docstring, checked against the released `EICU_attrition.csv` and `EICU_preflight.json`.
- **DOCS-7, DOCS-2; GAP-eicu-mock-math-1 to -7, -9; GAP-example-builders-7.** Mock-corpus wording in `eicu_mock`,
  `explain_dashboard_mock`, the tests and `test_constants` comments: the exact population AUC is 0.748 for the
  Bayes-optimal score and 0.715 for a score recovering z alone (Φ(B/√2) = 0.726 is the rare-event approximation);
  the superpopulation prevalence is 9.25%; the head reaches 0.60 at the small arm and 0.68–0.69 at full scale; the
  declines at the frozen sizes are measured, not implied by the floor, which is in atom units; n_carrying = 77 is the
  crossing only when every calibration site has at least 100 stays, and `site_split` first reaches it at 213
  hospitals (214 gives 76; every size from 215 up at least 77); at 900 hospitals / 90,000 stays the crossing is about
  134, while a 1,500-hospital, 30,000-stay mock declines. Constants and literals are unchanged. Pinned by
  `test_eicu_etl.py::test_leak_auc_ceiling_sits_just_above_the_mocks_bayes_optimal_auc` (exact quadrature 0.7476)
  and `test_constants.py::test_eicu_mock_constants_pinned` (the split arithmetic behind the `site_split`
  breakpoints). Protocol: erratum to §14.1 step 4.
- **GAP-example-builders-5, -6, -8.** The worked example's comments (the certified quantity is `R_M`; the temp CSVs
  total about 14 MB) and `test_realdata_path`'s docstring (the pruned int-label variant is no longer claimed).
- **explain-3, explain-12, NUM-10, synthetic-8.** New or strengthened pins:
  `test_eicu_etl.py::test_imputed_rows_standardize_to_zero`; `test_explain.py::test_counterfactual_flips_at_float_hostile_thresholds`
  now derives the float-hostile set from `TAU_GRID`; `::test_single_feature_ranking_is_abs_coef_order_and_off_top_equal_budget_never_flips`.
- **NUM-2.** `test_certify.py::test_wsr_boundary_type_I_at_n80` keeps its 800-rep loop and now also pins the exact
  crossing steps; see the note under *What is verified*.
- **NUM-11, NUM-12, PAPER1-13, PAPER2-16, NUM-15.** Test docstrings: the uncapped atom in
  `test_mcap_supplies_ville_boundedness` reaches 4.55, not ~3.05 (now asserted); `wilson_lcb(3, 20)` is 0.0616, not
  ~0.056 (asserted); the Clopper–Pearson exact miss in `test_q_interval_propagation_regression` is 0.0044; the
  truncation counterexample's 17.5% is the record-weighted risk and `R_M` = 200/3800 (both asserted).
- **PAPER2-10.** `test_constants.py::test_report_bootstrap_resamples_pinned` pins the report bootstrap's 500
  resamples and its call site.
- **DOCS-11.** `test_certify.py::test_weight_cap_divides_atom_margin` pins the mechanism behind the covariate-shift
  scope cut: weights clipped at C enter the atoms as w/C, which divides the atom margin by C. Protocol: erratum to
  §12.2 ("provably").
- **synthetic-1.** E8's comparators are re-scored post hoc against the exact population `R_M` by the new
  `experiments/rescore_e8a.py` into `experiments/out-e8a-rescore/`; the frozen E8 artifacts are unchanged. Pinned by
  `tests/test_sidecar_e8a.py` (`::test_replays_frozen_draw_exactly`, `::test_closed_form_matches_record_monte_carlo`,
  `::test_released_sidecar_carries_pinned_counts`, `::test_refuses_released_output_directories`).
- **BBSE-1 (E6 sidecar).** `experiments/rescore_e6_composition.py` writes the corrected E6 composition view into
  `experiments/out-e6-composition/` (*Errata* 1). Pinned by `tests/test_sidecar_e6_composition.py`.
- **FNR-1, FNR-5, FNR-6 (E9 sidecar).** `experiments/rescore_e9_exact.py` writes the closed-form named estimands
  behind the E9 certificates into `experiments/out-e9-exact/` (*Errata* 5). Pinned by
  `tests/test_sidecar_e9_exact.py`.
- **BBSE-1, CORE-3 (eICU sidecar).** `experiments/eicu_composition_margin.py` replays the released primary arm on
  the restricted extract, refuses to write unless the replay matches the release, and writes the corrected
  BBSE-implied composition (published split 0.0307 released, 0.0323 corrected, oracle 0.0458) and the exact
  `S_aux` atom-unit margin into `experiments/out-eicu-composition/` (*Errata* 2). Pinned by
  `tests/test_sidecar_eicu_composition.py`.

### Ledger annotations made in this pass

Dated notes, with the annotated text kept as filed: the Critical 2 line of RESOLUTION (the probe's level), the
Rec. 17 line and recommended action 17 (the multi-site q bootstrap), V8 ("closer to ~0.92"), V21's rationale
(after the LOW table), and the WSR bullet of *What is verified* (NUM-2). REDTEAM.md carries dated notes on R4
(both entries), the refuted R3 entry, N1 and the estimand-atoms lens.

### Errata — released artifacts that keep a wrong number or note

The files below are byte-frozen and stay as released. A corrected value is given only where it is read from
released data or a post-hoc sidecar.

1. **`experiments/out/E6_composition.json`**, `composition.bbse_true_class` (BBSE-1). `positive_fraction` 0.0858
   (0.0857576903) and `expected_n_positive` 2,170.87 were computed with the `S_aux` prior. With the training
   split's prior divided out they are 0.0913 (0.0913101048) and 2,311.42, odds multiplier 0.948; the corrected
   view is in `experiments/out-e6-composition/`.
2. **eICU BBSE-implied composition** (BBSE-1): `diagnostic.composition.bbse_true_class` in `EICU_certificate.json`
   (0.0307 on the published split) and `composition_three_way[*].bbse_implied_positive_fraction` in
   `EICU_diagnostics.json`, in `experiments/out/`, `out-panel/`, `out-sens/`, `out-subgroups/`, `out-faithfulness/`
   and `out-rev2/`; and `three_way_composition` (`bbse_implied`, `expected_n_positive_bbse`,
   `bbse_transfer.understatement_of_answered_positive_load`, `per_replicate`) in
   `experiments/out-derived/fixpass_numbers.json`. All carry the same prior error. The training split's prevalence
   is in no released artifact, so the corrected value cannot be recovered from them; it is in
   `experiments/out-eicu-composition/`, from the restricted extract. Certified fields are unaffected.
3. **`experiments/out-derived/fixpass_numbers.json`**, superseded by `experiments/out-derived-r2/fixpass_numbers.json`:
   - `rev2.pooled_new_columns` = "no new columns found" read the wrong file (EICU-2). The seven columns are in
     `out-rev2/EICU_comparator.csv`: head AUC 0.8593 on the pool and 0.8098 on the answered set, APACHE-IVa AUC
     0.8601 on the pool. `_run.inputs` hashes `out-rev2/EICU_pooled.csv` in place of the comparator file.
   - Double rounding (EICU-2): `three_way_composition.bbse_transfer.true_odds_ratio_vs_pi_s` is 0.984, not 0.983;
     `fairness.age_gradients.answered_err_ratio` is 3.88, not 3.89; `rev2.faithfulness_spearman.mean` is 0.4848,
     not 0.4849.
   - `e1.note` says the six BBSE-deploying draws are excluded from Table S4. They are not: Table S4 replays all 200
     draws, the six at their baseline-walk threshold; the counts (194 of 200) stand (synthetic-5).
   - `e9a_frozen.population_odds_ratio` 2.687 is the nominal per-site multiplier odds(0.22)/odds(0.095), not
     the record-pooled population odds ratio, which is 2.6013 (`out-bbse-probe/BBSE_probe.json`) (NUM-4, FNR-6).
   - `p4_signed.rule` names "an *__missing sibling"; the registered matcher, and the corrected code, take
     `aps_*` / `apv_*` `__missing` siblings only. The verdict is unchanged (EICU-12).
   - `exact_cis` `eicu_*` entries and `fairness_cells_8_of_570` are Clopper–Pearson intervals over dependent units
     (pools and cells of one re-split share its head and threshold, hospitals recur across re-splits, the re-splits
     partition one hospital list): nominal only (EICU-1).
   - The probe headline copied into the derivation reads the box-route plug-in as an "implied level" (*Errata* 4).
   - `_run.inputs` records sha256 `059e8e…` for `out-settled/EICU-PREDICTIONS-SETTLED.json`, and
     `sidecars.settled.run` an earlier stamp: the settlement file was re-emitted after the derivation was written
     (2026-09-07T01:29:12+00:00), with the same headline, so the recorded hash does not match the committed file.
4. **`experiments/out-bbse-probe/`** (PROBE-1, BBSE-5, PROBE-3).
   - The `implied_certificate_level` blocks of `BBSE_probe.json`, its headline, and `README.md`'s "The implied
     certificate level is 1 − (measured box miss + δ_bet)" read a looser bound as the level. The union bound needs
     only coverage of the declared site's odds ratio, which held in all 1,163 certifiable fits (exact 95% upper end
     of the miss 0.0032, pooled; every per-cell bound at least 0.965), so in the probe's regime the level is at least
     1 − (0.0032 + 0.025) = 0.9718; the box-route 0.928 (0.914 at the upper end of the pooled interval) charges every
     box miss to the certificate. Outside that regime — multi-site pools, other heads, other auxiliary-site counts —
     no released artifact measures the odds-ratio coverage (for multi-site pools, BBSE-2 above records an unreleased
     audit Monte Carlo).
   - `box_width_rho.n_clip_bound` 4, 3 and 4 (11 pooled) and `mean_excluding_clip_bound` 7.5922, 7.2638 and 6.4655
     (7.106) counted `rho_hi > 100` as clip-bound. Against the clip flag the released CSV holds 2, 2 and 2 (6) and
     mean widths 8.2248, 7.538 and 8.5153 (8.0908). The clip block's `rho_hi_clip_bound_above` key names the
     superseded threshold.
5. **`experiments/out-e9a-rescore/`** (`README.md`; `E9a_rescore.json` `estimand`) (FNR-6). `pi_target` is the
   declared pool's realised prevalence, so `rm_rescored` and `rho_site` are proxies. The single-site
   Clopper–Pearson box targets the site's latent prevalence: the exact named estimand of the three frozen-exceeding
   rows is 0.0163, 0.0398 and 0.0792 against proxies 0.0175, 0.0408 and 0.0586, and it is within budget in all 44
   single-site certificates; the k40 bootstrap targets the target-site population. `population_odds_ratio`
   (2.6869) is the per-site multiplier odds(0.22)/odds(0.095); the pooled ratio is 2.6013
   (`out-bbse-probe/BBSE_probe.json`), covered by the 1,200-site α = 0.10 single-site boxes in 16 of 20 (15 against
   the fresh pools' realised ratio; the k40 boxes cover it in 47 of 47). The closed-form estimands are in
   `experiments/out-e9-exact/`.
6. **`experiments/out-e9b-positives/README.md`** (FNR-4, FNR-8). The weight rationale ("one fixed functional … the
   estimand is fixed", lines 39–44) is superseded by the validity wording in `run_e9b_positives`, and "exchangeable
   draws" (line 46) should read "i.i.d. draws". The E9b JSON's `ESTIMAND_NOTE` is consistent and stands.
7. **`experiments/out/summary.md`**. The E8 block's `notes` (arm C: "temperature miscalibration is analytically a
   no-op for the gate") is wrong: on the fixed `TAU_GRID` a temperature change moves the answered sets, the deployed
   τ and coverage, and only validity is calibration-free (synthetic-4). The E9 block's `notes` ("0.4 is the built-in
   always-refuses negative control") is wrong: 0.4 is not a negative control, and the shipped atom's 0 of 600 there
   is a power limit (FNR-1, DOCS-9). Erratum comments sit above both strings in `run_synthetic.py`.
8. **`experiments/out-settled/EICU-PREDICTIONS-SETTLED.md` and `.json`** (EICU-3, DOCS-6, EICU-12). P2's note "the
   synthetic s_u = 0.5 arm gave 0.02" quotes E1's hard-violation rate; on `per_site_exceed_frac`, the statistic P2
   settles on, that arm gave 0.055. The P4 clause label describes the broader matcher. No verdict changes; the
   registered copies of the P2 text in `out/EICU-SUMMARY.md`, `out/EICU_preflight.json` and their `out-timing/`
   twins are covered by the dated erratum to P2 in EICU-PROTOCOL.md §9.
9. **Released reliability panels** (`experiments/out/E6_reliability.json` and every `EICU_reliability_panel.json`)
   (reliability-2, reliability-10). `notes[2]`'s "positively biased" names only the absolute-value term of the
   ECE's plug-in bias, whose net sign is not fixed; `notes[0]` and `WEIGHTING`'s "ratio of sums" holds for rates,
   fractions, Brier scores and reliability points, while the ECE, the skill margin and the calibration fit are
   functions of such ratios or pooled score equations, all record-weighted. The strings are hashed into
   `PANEL_DICT_SHA256` and stay as emitted.

The registered protocol text keeps its own errata, as dated blockquotes in EICU-PROTOCOL.md indexed in its §0.

### Still open

- Rec. 17: the percentile box, and for multi-site pools the q bootstrap, remain asymptotic. The NUM-1 floor admits
  `S_aux` splits from ten sites per class, but the box's coverage has a released measurement only at 36, 42 and 74
  auxiliary sites and a single declared target site; a post-hoc probe sidecar, written to a new directory, is needed
  before any figure for fewer sites or for multi-site pools is quoted.
