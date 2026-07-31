# CertGate correctness audit — verdict

Date: 2026-07-25. Auditor: independent verdict pass over six dimension sweeps and four prosecution passes.
Scope: `certgate/` (package), `tests/`, `experiments/`, `SPEC.md`, `METHODS.md`, `README.md`, `paper/draft.md`.

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
`SPEC.md:228` mandates the guarantee text as *"per-target-site; all sites from one calibration draw share
the 1-delta event."* Both clauses are false — the first because the estimand is a population aggregate,
the second because the permutation is seeded from the target label. The code faithfully implements a
specification that misstates the mathematics. Fixing the code alone would not fix this; `SPEC.md` must
change first, as its own protocol requires.

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
**Location:** `certgate/report.py:66-69` (text) vs `certgate/certify.py:29-31` (estimand); `SPEC.md:228`;
`METHODS.md:7,17,21,23,58`; `paper/draft.md:60,124,208`; validated wrongly at `certgate/harness.py:40`.
**Empirically demonstrated.**

`influence_atoms` builds `Z_c = (g_c/(M·n_c))·Σ_i ans_i(err_i − α) + α`. `wsr_reject` tests `E[Z] ≤ α`
where the expectation is over the **site draw**. That is exactly `R_M = Σ_c g_c a_c e_c / Σ_c g_c a_c`,
which `METHODS.md:17` itself defines as a sum over sites. For a *single* site, `g_c` and `a_c` cancel and
the quantity is just that site's own error rate `e_c`. A population mean does not bound an individual draw,
and the probability in the statement is over the calibration draw only — there is no residual randomness
left for a per-site reading to average over.

The emitted text (generated from the shipped code, verbatim):

> Under the tagged assumption (exchangeability), with probability >= 0.95 over the draw of calibration
> sites, the M=100 influence-weighted answered-set risk **at this target site** is <= 0.1. This guarantee
> is per-target-site; all sites certified from one calibration draw share the same 1-0.05 event.

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

The "design-conditional estimand" defence (`METHODS.md:23`) does not rescue it: conditioning on the target's
features makes them observed, but does not convert a population-average bound into a per-site bound. Note
also that in baseline mode the target's data never enters the test at all — `pipeline.py:58-70` builds atoms
from `cal` only — so a genuinely site-specific claim is structurally impossible on that path.

**Why the harness cannot catch it:** `experiments/run_synthetic.py:108-125` draws one target site per
calibration draw from `SimConfig` defaults, whose only between-site variation is `u_c ~ N(0, 0.5²)`. Per-site
true risk is nearly uniform there.

**Fix.** Two coupled changes, `SPEC.md:228` first since it is binding and currently mandates the wrong text.
(a) `report.py:65-76`: state the certified estimand — *"the expected M=100 influence-weighted answered-set
risk over sites drawn from the calibration population is ≤ α"* — and add a fourth mandatory clause with the
same force as the binomial one: *"This is a population average across sites. It does not bound any individual
site's answered error rate; under between-site heterogeneity the fraction of target sites exceeding α is
governed by that dispersion, which this certificate does not measure or bound."* (b) Restate `METHODS.md:7,
21, 23, 58` and `paper/draft.md:60, 124, 208` to match, and either rescore E1's conformance metric against
the aggregate estimand or keep the per-site column relabelled honestly as a dispersion diagnostic with no
δ target attached. Report the `s_u` sensitivity in the paper — the published 0.01 is not robust to it.
If a genuine per-site guarantee is wanted, `E[Z]` is the wrong statistic: it must become a tolerance bound
on an upper quantile of the per-site risk distribution, which is a different test and costs more clusters.

---

#### V2 — BBSE treats the target predicted-positive rate `q_t` as known; its sampling error is never propagated, and false certificates result at up to 3× δ
*(= BBSE-1)*
**Location:** `certgate/shift.py:87` (also `42-43, 114, 130, 138`); `certgate/constants.py:17`.
**Empirically demonstrated, with a control isolating causality.**

```python
q_t = float(head.predict(target_x).mean())        # exact on the pool
```

`BBSE_BONFERRONI = 3  # box covers (c0, c1, pi_source)`. `q_t` gets no share of `BBSE_DELTA_CONF` and no
interval anywhere in the chain, yet it enters the inversion at `shift.py:138`
(`pi_t = clip((q_t − c0)/(c1 − c0), …)`) where the `BBSE_GAP_FLOOR = 0.10` gate permits its error to be
amplified up to 10×. The only `q_t` guard (`shift.py:130`) fires only for `q_t` outside `[c0_lo, c1_hi]`.

The docstring's justification is that `q_target` is *"exact under the design-conditional estimand."* This is
the false premise. Conditioning on the target features makes `q_t` exactly **observed**, but it simultaneously
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
rate and carries sampling error, and that the box covers four parameters. Then `constants.py:17` →
`BBSE_BONFERRONI = 4`. Then `shift.py` after line 87: build a finite-sample interval for `q` at
`lvl = BBSE_DELTA_CONF/BBSE_BONFERRONI` — exact Clopper-Pearson on `k = predict(target_x).sum()` for a
single-site pool; a cluster bootstrap over target sites for a multi-site pool, which requires adding a
`target_site_id` parameter (`run_certgate` has it available) and treating unknown clustering as one cluster.
Widen the misspecification gate at `shift.py:130` to `if not (lo[0] <= q_lo and q_hi <= hi[1])`. Make `rho_of`
take `q` as an argument and enumerate **16** corners. Add the regression test the current code fails: with head
and `S_aux` fixed and ≥200 independent target pools of n=100, assert the fraction of intervals missing `ρ_true`
is ≤ `BBSE_DELTA_CONF` + MC tolerance — today it is ~0.57. Expect BBSE to decline more often on small pools;
that is the correct behaviour, as the control shows.

---

### HIGH

---

#### V3 — The WSR permutation is seeded from the caller-supplied target label, so target sites do not share one 1−δ event and the deployed threshold moves with a respelling
*(= CC-2 / CG-R2 / CW-6)*
**Location:** `certgate/certify.py:130-141` (seed rule), `certgate/pipeline.py:64`, `certgate/shift.py:200-203`;
falsifies `certgate/report.py:70-71`, `SPEC.md:228`, `METHODS.md:23`, `paper/draft.md:94,124`.
**Empirically demonstrated.**

In baseline mode nothing about the target enters the calibration atoms (`pipeline.py:62-63` uses `cal` only;
walk order from `aux`). The sole target dependence is `certification_rng(alpha, MODE_BASELINE, target_label)`,
and `certify.py:138` is `h = hashlib.sha256(str(target_label).encode()).digest()`. `certify.py:81` permutes `z`
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
free-text identifier on byte-identical data. `paper/draft.md:94` claims the permutation *"cannot be chosen to
flatter the outcome."*

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
already target-independent — and one calibration draw then yields literally the single shared event `report.py:70-71`
promises. BBSE endpoints keep distinct streams via a `'lo'`/`'hi'` discriminator rather than `f"{target_label}|lo"`.
Leave `_bbse_seed_rng` alone; it legitimately depends on the target because `fit_bbse` consumes `target_x`. Add a
test asserting `run_certgate` output is byte-identical across a list of target-label spellings — that test fails today.
*Caveat:* the shared-event clause is **independently** false in BBSE mode because `fit_bbse` depends on the target
pool through `q_t`, so different targets get different ρ boxes regardless of seeding. Restoring the clause fully is
achievable for baseline only; for BBSE the clause must be deleted.

---

#### V4 — Site identity is unvalidated `str()`; cosmetic noise in one column fabricates independent clusters, buys a rung the honest clustering refuses, and defeats the minimum-cluster gate
*(= VB1, absorbing VB2)*
**Location:** `certgate/validate.py:109-119` (`densify_sites`); consumed at `pipeline.py:134`, `certify.py:48`.
**Empirically demonstrated.**

```python
labels_str = np.array([str(s) for s in raw_site_ids], dtype=object)
uniq = np.unique(labels_str)
```

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
on `S_cal` itself, voiding `certify.py:108-110`'s *"Data-independent of S_cal, so it spends no multiplicity budget."*

*Honest mitigation:* the report surfaces `n_cal` and `n_cal_carrying`, so an attentive user could notice 166 where
they expected 83. Nothing forces them to look.

**Fix.** `validate.py:109-119`: canonicalize before `np.unique` — reject None/NaN/empty (V11), strip surrounding
whitespace, map integral floats to their integer string so `0` and `0.0` collide. Then raise `CohortError`, not a
warning, when the raw forms collapse to fewer clusters than they produced — that is the caller's signal that their
site column is dirty, and it must be loud because the count feeds `MIN_CAL_CLUSTERS`. Add a regression test asserting
`from_raw` over an int site column and the same column cast to float produce identical `site_labels`. Surface the
calibration cluster count and min/median/max cluster size in the diagnostic tier so a 2× inflation is visible.

---

#### V5 — `make_cohort` ignores a caller's declaration that two clusters are the same physical site
*(= CW-2)*
**Location:** `certgate/validate.py:158-164`. **Empirically demonstrated.**

The entire `site_labels` contract checks only the **length**:

```python
site_labels = tuple(str(s) for s in site_labels)
if len(site_labels) != n_sites:
    raise CohortError(...)
```

`SPEC.md:57` documents `site_labels` as *"original identifiers, index-aligned to dense ids"* — so a repeated
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
| 1 | `np.minimum(sizes, M)` → `sizes` (`certify.py:50`) | the [0,1] atom bound **Ville's inequality requires** |
| 2 | baseline walk spends `δ = 0.5` (`pipeline.py:65`) | the δ in the paper's title |
| 3 | BBSE bet spends full `DELTA` (`shift.py:207`) | `δ_conf + δ_bet = δ` union bound |
| 4 | box drops Bonferroni-over-3 (`shift.py:114`) | ρ-interval width |
| 5 | walk order derived from `S_cal` (`pipeline.py:165`) | selection on the testing data — the reason `S_aux` exists |
| 6 | `wilson_lcb` returns the **upper** bound (`harness.py:36`) | every violation number in the paper |
| 7 | `hard_violation` uses the raw rate (`harness.py:47`) | the two-number violation protocol |
| 8 | BBSE walk `break` → `continue` (`shift.py:211`) | fixed-sequence FWER across 23 thresholds |
| 9 | provenance hashes → literal `"deadbeef"` (`report.py:47`) | content binding (audit F49) |
| 10 | bootstrap may quantile a reduced count (`shift.py:107`) | audit F40/B-8 hardening |
| 11 | atoms use `>` while deploy uses `>=` (`certify.py:63`) | tie handling between statistic and answered mask |
| 12 | `certification_rng` ignores `alpha` (`certify.py:140`) | ladder rungs share a permutation stream |
| 13 | **invert** the out-of-scope clause to "Nothing is OUT OF SCOPE" | the disclosure E3 exists to justify |
| 14 | delete the BBSE asymptotic clause (`report.py:77`) | a named `CLAUDE.md` invariant |

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

**Two assertions are outright vacuous.** `tests/test_shift.py:74-76` asserts
`rb["reason"] is None or rb["reason"] in {"failsafe","bbse-degenerate-bootstrap","bbse-ill-conditioned","bbse-misspecified"}`
under the comment *"never a silent certify-and-violate."* That set **is** `certify_bbse`'s complete return domain
(`shift.py:188-222`), so the predicate is identically true. `tests/test_pipeline.py:42-45` checks only that three
tokens — `"per-target-site"`, `"NOT a bound"`, `"OUT OF SCOPE"` — appear *somewhere* in the guarantee string, which
is why mutation #13 survives while asserting the exact opposite of the intended clause.

`certgate/harness.py` has **zero** tests; no test file imports it. `SPEC.md`'s Tests section lists no `test_harness.py`.
I verified the module is nevertheless *correct* — `wilson_lcb` matches the closed form and `exceedance_reference`
matches brute-force enumeration including the integer-boundary cases — so this is a complete coverage hole over the
paper's measurement instrument with no error behind it today.

**Fix.** Priority order: (1) a `tests/test_harness.py` covering `wilson_lcb`, `exceedance_reference` and
`hard_violation` against closed forms — kills #6, #7. (2) A δ-accounting spy: monkeypatch `wsr_reject` with a
recording wrapper, run `run_certgate` per mode, assert the recorded δ arguments are exactly `{DELTA}` and
`{BBSE_DELTA_BET}` — kills #2, #3. (3) An M-cap test with sizes spanning 20 and 3000 against `M=100`, asserting
`z.min() >= 0 and z.max() <= 1`, plus the counterexample above — kills #1. (4) Freeze the guarantee statement by
exact string comparison for a known `(alpha, modes)` pair — kills #13, #14. (5) Give `_manual_fit`
(`tests/test_shift.py:183-187`) a multi-element walk order; today it supplies `np.array([0])`, under which `break`
and `continue` are provably indistinguishable — kills #8. (6) A walk-order provenance test: permute `cal` labels
within sites and assert the walk order is unchanged — kills #5. (7) Flip one calibration label and assert
`prov["input_hashes"]` differs — kills #9, and is the same assertion V13's fix needs.

---

#### V7 — E2 and E3 run at an undeclared `sep = 1.8` while every document states 2.2
*(= TS-06)*
**Location:** `experiments/run_synthetic.py:40`, used at `:195` (E2) and `:264` (E3).
**Empirically demonstrated (by prior passes; mechanism verified by me).**

```python
SHIFT_SEP = 1.8                             # realistic head so shift bites
```

Used only by E2 and E3. E1 (`:112`), E4 (`:333`), E5 (`:399`) and E6 (`:462`) all use `SimConfig()` → `sep = 2.2`.
I confirmed by grep that **no document mentions 1.8 anywhere**; the only `sep` hit across `SPEC.md`, `METHODS.md`,
`README.md` and `paper/draft.md` is `SPEC.md:100` (`sep=2.2`). `paper/draft.md:152` — the Experimental setup section
governing all six experiments — states *"the two class means separated by sep = 2.2"*, and §4.3/§4.4 report the
E2/E3 numbers without qualification.

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
`certgate/shift.py:113-124`; `constants.py:15,29`. **Empirically demonstrated by two independent passes; I did not
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

**Fix.** Replace the naive percentile box with a studentized/BCa bootstrap over the existing site resamples, or
better, a finite-sample cluster bound: `c0`, `c1`, `π_s` are all ratios of bounded per-site quantities, so the WSR
machinery already in `certify.py` can be inverted to give finite-sample intervals at `BBSE_DELTA_CONF/BBSE_BONFERRONI`
— which also retires the asymptotic caveat entirely. Add a coverage regression test at `n_aux = 42`. Until then,
`METHODS.md:39` and `paper/draft.md:114` must report the measured realized coverage, not only the nominal `δ_conf`.

---

#### V9 — The target pool is never checked for site-overlap with `S_cal` / `S_aux` / `S_train` *(= CW-3)*
`certgate/pipeline.py:106`. **Empirically demonstrated.**

The whole data-discipline gate is `assert_site_disjoint(train=train, aux=aux, cal=cal)`. The target enters as a bare
`target_x` plus a free-text `target_label` and is never compared to anything, even though `METHODS.md:7,23` scope the
guarantee to *"a NEW target site"* and `pipeline.py:132` already passes `str(target_label)` into provenance:

```
  target = calibration site 's-0000' (its own records), label = the same string
  reason=None  operative={'alpha': 0.1, 'tau': 0.55, 'deploy_mode': 'baseline', ...}
  target = the ENTIRE calibration cohort -> reason=None, operative alpha/tau = 0.1/0.55
```

The certificate is issued with the full per-target-site guarantee text for a site whose own records are among the
calibration atoms that produced it. No warning; nothing distinguishes it from an honest fresh-site run. Medium rather
than high: the guarantee is not mathematically invalidated for the site population, but the walk stops at a τ chosen
partly on this site's own atom, so the reported coverage and estimated-tier risk are selected on the target itself —
the exact leak the F03 assertion exists to prevent, on the one split it does not cover. `examples/real_data_example.py:116`
tells practitioners that `run_certgate` asserts site-disjointness at entry without qualifying that the target is excluded.

**Fix.** After `pipeline.py:106`, raise if `str(target_label)` is in the union of the three cohorts' `site_labels`.
Add an optional `target_site_labels=None` keyword and assert full disjointness when supplied — `target_label` alone
cannot catch a target pool whose records come from a cal site under a different label. Update `SPEC.md`'s gate list
and the example's comment.

---

#### V10 — Missing site ids are coerced into a bona fide pseudo-site *(= VB4)*
`certgate/validate.py:115`. **Empirically demonstrated:** `densify_sites(['A', None, float('nan')])` →
`('A', 'None', 'nan')` — three legitimate clusters, two fabricated from missing data.

The damage is two-sided: records with no known cluster are welded into one fake independent unit, while every affected
real hospital simultaneously has its records split between its own cluster and the `'None'` cluster — the
anti-conservative direction demonstrated under V4. The contract violation is sharp and internal to the same file:
`coerce_labels` (`validate.py:76-84`) explicitly rejects NaN and None in the **label** column, with a comment that the
code never guesses at a caller's intent, while the **site** column — which the whole method designates as the unit of
statistical independence — gets no such check thirty lines earlier. `CLAUDE.md` lists loud boundary validation as a
non-regressable invariant.

**Fix.** In `densify_sites`, before building `labels_str`, raise `CohortError` on None, float NaN, and empty/whitespace-only
strings, mirroring `coerce_labels`' wording. Add the rule to `SPEC.md`'s `densify_sites` contract line.

---

#### V11 — The provenance block does not bind the calibration labels or the site partition *(= CG-R4)*
`certgate/report.py:29-59`, `certgate/pipeline.py:130-132`, pinned incomplete at `tests/test_pipeline.py:97-98`.
**Empirically demonstrated:**

```
  run1 certified: [(0.05, 'declined', None), (0.1, 'certified', 0.55)]
  run2 certified (35% of cal LABELS flipped): [(0.05, 'declined', None), (0.1, 'declined', None)]
  input_hashes IDENTICAL? True
  keys hashed: ['aux_x', 'cal_x', 'target_x', 'train_x']
```

One run certifies, the other refuses, and the reproducibility record cannot tell them apart. Only the four feature
matrices are hashed — no `y`, no `site_id` — and `tests/test_pipeline.py:97` pins exactly that key set, freezing the
omission into the suite. Separately, `report.py:47-48` hashes raw bytes with no shape or dtype in the digest, so a
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
| **V12** *(CC-4)* | The record-carrying cluster gate can never differ from `n_sites` on any sanctioned input path — `make_cohort` rejects gappy `site_id`, so `(site_sizes > 0).sum() == n_sites` always. A guard that cannot fire, credited by `SPEC.md`/`CLAUDE.md` as load-bearing audit-B-5 hardening. The `np.where(sizes > 0, …)` at `certify.py:50-52` is likewise unreachable arithmetic (the divisor is already `np.maximum(sizes, 1.0)`). | `validate.py:153-156` vs `pipeline.py:134,140` | Either make the guard real (an explicit `n_sites` parameter threaded through `subset_sites`) or delete the dead distinction and amend the conformance checklist. Do not leave it as false assurance. |
| **V13** *(BBSE-3)* | The certified guarantee text asserts the bootstrap box is *"the single non-finite-sample step in the chain."* False given V2: the `q_t` plug-in is a second unmodelled step which, unlike the bootstrap, receives no confidence allowance at all. The sentence structure claims completeness — it enumerates its randomness sources, and the target-pool draw appears in neither. | `report.py:78-82`; `METHODS.md:39,74`; `paper/draft.md:108,114,124,244`; `shift.py:42-43,87` | Amend `SPEC.md:233-235` first, then the text. Delete the "exact on the pool" comment and the "exact under the design-conditional estimand" clause — they are the false premise. Restate after V2 lands. |
| **V14** *(BBSE-4)* | Both `fit_bbse` decline gates are NaN-blind: an empty `target_x` gives `q_t = NaN`, both comparisons evaluate False, and the call dies later inside `influence_atoms` with an error naming *weights* rather than the empty pool. `max(1.0, nan)` silently returns 1.0. | `shift.py:87,126,130` | Return a new `bbse-empty-target` decline after line 87; invert the gate to `if not (lo[0] <= q_t <= hi[1])` so NaN declines. Reachable only via the public `fit_bbse`; `run_certgate` catches it at `MIN_ANSWERABLE`. |
| **V15** *(CW-4)* | `Cohort` is a plain frozen dataclass exported in `__all__` with no `__post_init__`, and `run_certgate` re-checks only feature width — so cohorts `make_cohort` explicitly refuses (non-dense `site_id`, float `y`, non-finite `x`) flow straight through to a certificate. The repo's own tests rely on this bypass. Direction happens to be conservative in every case I tried; nothing in the design makes that general. | `validate.py:24-53` | Give `Cohort` a `__post_init__` running the same checks; move the five contract-violating test fixtures to a named test helper. |
| **V16** *(CW-7)* | `_feasibility` initialises `best = -np.inf` and never restores a finite value when no τ achieves coverage, emitting `margin=-inf, ratio=-inf` into the report diagnostic — not strict-JSON serialisable. Verified: `json.dumps(..., allow_nan=False)` raises. The certified path is safe (it declines to failsafe). | `pipeline.py:44-55` | Track feasibility explicitly with `None` rather than a sentinel; `None` serialises as JSON `null` and cannot be mistaken for a very bad but real margin. Same latent issue in the `floor` branch. |
| **V17** *(VB3)* | `make_cohort` checks `y.dtype.kind == "b"` but never `y.ndim == 1`, so an `(n,1)` bool column is accepted and broadcasts `predict(x) != y` into an `(n,n)` matrix — a 30+ GiB `MemoryError` deep in the pipeline instead of a typed `CohortError` at the boundary. Same omission for `site_id`. | `validate.py:142-149` | Add `ndim != 1` checks before the dtype checks, so `np.bincount` is never reached with a 2-D array. |
| **V18** *(VB5)* | `require_both_classes=False`, which `SPEC.md:79-83` restricts to target pools, is an unrestricted public keyword; nothing tags a Cohort's role and `run_certgate` never re-checks. An all-negative **calibration** cohort is admitted and certifies, with BBSE's reweighting silently inert (`w = where(cal.y, rho, 1.0)` is constant) yet still listed as a covering mode. Direction is conservative. | `validate.py:171-172`; no counterpart in `pipeline.py` | Enforce at the boundary where roles are known: in `run_certgate`, require both classes in each of train/aux/cal. Suppress `bbse` from the covering-modes list when the fitted weight vector is constant. |
| **V19** *(VB6)* | `oracle_target_y` is the only `run_certgate` input with no validation anywhere and is coerced with `np.asarray(…, dtype=bool)`. A length-1 array broadcasts to a fabricated all-negative composition; a float probability array coerces to all-positive. Both produce plausible-looking but fabricated `oracle_true_class` figures — the field reported as E6's composition row. Never touches the certificate. | `pipeline.py:87`; `explain.py:145-147` | Validate at the boundary in `run_certgate`: 1-D bool of length `target_x.shape[0]`. |
| **V20** *(CG-R3)* | "Exact Shapley values" is unqualified but exact only for the **interventional** value function with the training-mean background — an unnamed choice. The shipped generator's features are correlated by construction (max off-diagonal correlation ~0.10-0.13), so conditional Shapley values differ. The stated justification (`sum(phi) + intercept == logit`) is a non-sequitur: efficiency is one axiom, and both decompositions satisfy it identically, which is why `tests/test_explain.py:25-31` does not test the claim at all. Magnitude disputed between passes (median 3.1%-14%); the *kind* is not. | `explain.py:3-6`; `METHODS.md:50`; `SPEC.md:195`; `paper/draft.md:130,192` | Name the value function and background in all four places; cite the Linear SHAP interventional result instead of the efficiency identity. Claim-precision only — no computed number is wrong. |
| **V21** *(CG-R5)* | `_bootstrap_estimate` discards every resample whose answered mass is zero and quantiles over the survivors — the exact pattern `SPEC.md:164` forbids for the BBSE box ("never quantile over a reduced count — audit F40/B-8"), with no top-up and no decline. The dropped resamples are precisely the low-mass ones, so the surviving quantiles are biased. Also returns `point=0.0` (not NaN) when nothing is answered. **Latent:** I could not reach either regime through `run_certgate`, and believe it unreachable — at a τ answering nothing, every atom equals α exactly and the wealth process cannot move. | `report.py:103,105-113` | Return NaN for an empty answered set; adopt `shift.py:102-112`'s top-up-or-decline discipline; surface `n_boot` in `render_text`. |
| **V22** *(CG-R6)* | When every target case is answered (or every one declined), `cohort_abstention_profile` produces an all-NaN gap whose `np.argsort` returns the **identity** permutation, and E5 then reports feature 0 as the top abstention driver with no basis in the data. Also writes bare NaN into `E5_explain.json`, which the harness elsewhere explicitly forbids. Latent: the shipped run has `n_declined = 2`. | `explain.py:92-100`; `run_synthetic.py:437,456` | Return an empty ranking rather than `argsort` of NaN; guard both consumers to emit `None`. |
| **V23** *(CG-R7)* | `run_certgate` validates `alphas` loudly against the frozen ladder but performs **no** validation of `modes`, so a misspelled mode yields a full all-declined report with `reasons={}` — indistinguishable from a genuine statistical decline. An empty `modes` tuple behaves identically. Fail-safe in direction. | `pipeline.py:96-102` vs `:168-185` | Mirror the `alphas` gate: raise on any mode outside `('baseline','bbse')` or an empty tuple. |
| **V24** *(CG-R8)* | `_statement`'s `deploy_mode` parameter is never read in the body. Verified: output is identical for `'baseline'`, `'bbse'` and a garbage value. The emitted statement never names which assumption mode backs the deployed threshold. | `report.py:62`, called at `:210-211` | Delete the parameter, or make it load-bearing by naming the deployed mode in the text. Deleting is smaller and removes the silent-garbage-accepted behaviour. |
| **V25** *(CG-R10)* | The gated-exit path returns a diagnostic dict missing five keys `SPEC.md` lists unconditionally (`composition`, `abstention_profile`, `capped_influence_share`, `rm_vs_unweighted`, `bbse`), so a consumer indexing them raises `KeyError` on any gated report. Mitigating: the gated path has `head=None`, so three are genuinely uncomputable. *(The sub-claim that declined rows carry `tier="certified"` is cosmetic — `status` disambiguates — and I would not have filed it alone.)* | `report.py:189-197` vs `:254-266` | Emit a stable key set with explicit `None` values; `capped_influence_share` can actually be computed there. |
| **V26** *(TS-12)* | `_write_summary` carries forward blocks for experiments not recomputed, but the header records only the current invocation's mode and no marker distinguishes recomputed from preserved sections — so `summary.md` can read `mode: FULL` while its E1 block is an R=10 QUICK result. E5/E6 emit neither `R` nor mode, so a preserved block from an earlier code revision is indistinguishable from a fresh one. Related: `run_E3` raises its poison-verification error before `_write_summary`, so an aborted full run leaves fresh CSVs beside a stale summary. | `run_synthetic.py:536-570` | Stamp mode and timestamp per block; prefix preserved sections with a visible marker; write the summary in a `finally` block. |

---

### PLAUSIBLE

#### V27 — The operative rung is a post-hoc selection across the α ladder, but its statement still claims 1−δ
*(= CG-R9)* · `report.py:205-217`; `constants.py:13`. **Reasoned only — no counterexample constructed.**

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
  the ρ-reweighted one (`shift.py:194-199`). There is no single event whose probability needs splitting. The emitted
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

1. **`SPEC.md:228` — change the mandated guarantee text first.** It is the binding contract and it currently mandates
   two false clauses. Nothing else in this list can be done correctly before it. *(V1, V3)*
2. **`certgate/report.py:65-83` — state the estimand the test certifies.** Replace "at this target site" with the
   population-average wording and add the between-site-dispersion clause. Then `METHODS.md:7,21,23,58` and
   `paper/draft.md:60,124,208`. *(V1)*
3. **`experiments/run_synthetic.py` — rescore or relabel E1's conformance metric, and report the `s_u` sensitivity.**
   The published 0.01 is a property of `s_u = 0.5`; at `s_u = 2.0` it is 0.10. A reviewer who varies one documented
   generator parameter will find this. *(V1)*
4. **`certgate/shift.py:87` — give `q_t` a confidence share** (`BBSE_BONFERRONI = 4`, Clopper-Pearson or cluster
   bootstrap, 16 corners). Then re-run E2. Expect more declines; that is the correct behaviour. *(V2)*
5. **`certgate/certify.py:130-141` — drop `target_label` from the permutation seed**, and strike the "cannot be chosen
   to flatter the outcome" claim at `paper/draft.md:94`. Delete the shared-event clause for BBSE, which cannot be
   restored. *(V3)*
6. **`experiments/run_synthetic.py:40` — resolve the `sep = 1.8` discrepancy**, preferably by running E2/E3 at the
   documented 2.2. Two headline numbers in the manuscript come from a generator the manuscript does not describe. *(V7)*
7. **`report.py:78-82`, `METHODS.md:39` — stop claiming a single non-finite-sample step**, and report the box's
   measured realized coverage at the deployed cluster count. *(V8, V13)*
8. **`tests/` — close the three test gaps that guard paper claims:** `test_harness.py`; the δ-accounting spy; the
   exact-string guarantee-text assertion. *(V6)*

### Before anyone runs this on real patient data

Everything above, plus:

9. **`certgate/validate.py:109-119` — canonicalize site identity and reject missing site ids loudly.** This is the
   single highest-risk item for real data: a routine data-quality defect in one column silently redefines the unit of
   statistical independence and buys a strictness rung the honest clustering refuses. A real extract will have dirty
   site ids. *(V4, V10)*
10. **`certgate/validate.py` — reject duplicate `site_labels` in `make_cohort`.** *(V5)*
11. **`certgate/pipeline.py:106` — assert the target pool is site-disjoint from train/aux/cal**, and add
    `target_site_labels`. Correct `examples/real_data_example.py:116`. *(V9)*
12. **`certgate/validate.py:24` — give `Cohort` a `__post_init__`** so the documented input contract is not optional
    through the public API. *(V15)*
13. **`certgate/validate.py:142-149` — enforce 1-D `y` and `site_id`**; a column-shaped label array from a loader
    currently detonates as a 30 GiB allocation rather than a typed error. *(V17)*
14. **`certgate/pipeline.py` — validate `modes`, `oracle_target_y`, and single-class fitting cohorts at the
    boundary.** *(V18, V19, V23)*
15. **Complete the mutation-hardening pass in `tests/`** for the remaining items in V6's table — walk-order provenance,
    the M-cap, the BBSE `break`, provenance content binding, tie handling.
16. **Fix the diagnostic-tier emission defects** before any output is machine-parsed: `-inf` into feasibility (V16),
    all-NaN gap ranking (V22), the gated-report key set (V25).
17. **Replace the percentile box with a finite-sample cluster bound** (V8), which also retires the last asymptotic
    step in the chain.

---

## One-line summary

The procedure is correct and the certificate overclaims: `certgate` proves a bound on the influence-weighted answered
risk **averaged across sites** and prints it as a bound **at the target site**, which fails at twice δ under
heterogeneity the design explicitly anticipates; separately, the BBSE mode omits the target pool's sampling error and
issues genuinely invalid certificates at up to three times δ. Both are fixable without touching the betting core.
