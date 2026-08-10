# CertGate — certified selective prediction with explainable abstention for multi-site clinical risk models

**Status:** fresh restart (v2) of the selective-prediction project, 2026-07-21. Deliberately smaller than v1: every cut and every kept component below traces to the v1 readiness audit ([../audit/readiness-report.md](../audit/readiness-report.md), 57 verified findings).

## Target venue

**Discover Computing** (Springer Nature, open access, IF 1.9, median 22 days to first decision) — Collection *"Intelligent Medicine: Machine Learning and Explainable AI for Next-Generation Healthcare"*, **submission deadline 2026-10-05**. The collection explicitly solicits: uncertainty quantification, calibration, out-of-distribution robustness, clinical auditability, and explainability. This project is built to hit those keywords with one coherent artifact.

**Working paper title:** *CertGate: finite-sample certified selective prediction for multi-site clinical risk models, with label-shift robustness and explainable abstention.*

## The pitch (one paragraph)

A clinical risk model should answer only when it can back the answer with a guarantee. CertGate wraps any probabilistic classifier in a selective gate that certifies, with finite-sample confidence 1−δ, that the influence-weighted error rate among *answered* cases — **averaged over the site population** from which calibration was drawn — stays below a stated budget α, treating the **site** (hospital), not the record, as the unit of statistical independence, which is what multi-site clinical data actually requires and what naive record-level guarantees silently get wrong. (A site-population average, not a per-site bound: individual sites can exceed α under between-site heterogeneity, and the certificate says so on its face.) The certificate survives outcome-prevalence (label) shift between calibration sites and a new deployment site via a worst-case correction whose own estimation uncertainty is folded into the guarantee; under relationship (concept) shift — provably undetectable from unlabeled data — the system's failure is demonstrated openly as a negative control rather than hidden. Every answer and every abstention is explained: the risk model is intrinsically interpretable, and the gate reports which features drove each decline.

## Objectives (measurable)

- **O1 — Method.** A certified selective-prediction gate for site-clustered data: influence-capped cluster statistics + a betting-style (WSR) finite-sample test + a fixed-sequence threshold walk; two assumption modes (exchangeable baseline; BBSE label-shift with cluster-robust uncertainty), with the mode tag part of the guarantee.
- **O2 — Explainability.** Global (standardized coefficients), local (exact linear attributions), and **abstention explanations** (which features pushed a declined case below the confidence bar) — no post-hoc approximator needed, because the deployed head is linear by design.
- **O3 — Honest empirical validation.** Across ≥200 replicated calibration draws: empirical hard-violation rate ≤ δ wherever a certificate fires; label-shift experiments where the uncorrected baseline provably fails and the corrected mode certifies or honestly declines; a concept-shift **negative control that is verified capable of failing** (v1 lesson: a control that cannot fail proves nothing).
- **O4 — Reproducibility.** One pinned environment (`requirements.txt`), deterministic seeds derived by a fixed rule, provenance block (versions, seeds, input hashes) embedded in every report artifact, full experiment grid re-runnable with one command.

**Success criteria:** violation rate ≤ δ in E1/E2; α=0.10 certifies with coverage ≥ ~0.75 at the realistic 208-site scale; the site-count sweep (E4) cleanly shows the feasibility frontier (which α each cluster count can support); test suite green in < ~2 min; end-to-end experiment grid < ~30 min.

### Results — synthetic grid, R=200 (all criteria met)

Full grid at R=200; artifacts in `experiments/out/` (`summary.md` + `provenance.json` + per-experiment CSVs/PNGs/JSON). Suite 260 passed / 3 skipped green (~31s; three off-default arms gated behind `CERTGATE_FIXTURE=1` / `CERTGATE_EICU=1` / `CERTGATE_EICU_LARGE=1`).

*(Rescored 2026-07-25 after the correctness-audit fixes — E1 against the certified estimand, E2/E3 at the documented sep=2.2, BBSE carrying the q_t confidence share; see `CODE-AUDIT.md`. E2/E3 aggregate-estimand columns, E5's replication arm and E7 landed 2026-07-30; per-block `_run` stamps in `summary.md` are authoritative.)*

| Exp | Result | Criterion |
|---|---|---|
| **E1** validity | α=0.10 certifies 1.0 at 0.982 coverage; **aggregate R_M-exceed rate 0.0 ≤ δ=0.05** on fresh 200-site pools, holding at s_u ∈ {0.5, 1.0, 2.0}; per-site dispersion diagnostic rises 0.02 → 0.10 with heterogeneity (measured, not bounded — the certificate is a site-population average) | ✓ viol ≤ δ on the certified estimand; coverage ≥ 0.75 |
| **E2** label shift (0.095→0.22) | uncorrected baseline hard-violates **0.395**; **BBSE issues zero certificates** (declines 200/200: 194 failsafe / 6 misspecified) — never certifies-and-lies; with the q_t budget a small single-site pool cannot support a certified rung under this shift | ✓ correction removes violations |
| **E3** concept control | tilt verified to push true risk to 0.161 > α, then certificate hard-violates 0.700 | ✓ tag is load-bearing |
| **E4** frontier | α=0.10 certifies from ~150 sites (1.0 at 150/208/300/400, coverage 0.94–0.98); α=0.05 first at 300 (0.285), reliable at 400 (1.0); 60/100 gated by the 50-carrying-cluster floor | ✓ clean frontier; α=0.10 operative at 208 |
| **E5** explain | τ*=0.55, 200 answered / 2 declined; exact attributions + abstention explanations. The R=200 replication arm returns the honest **NULL** — no stable single abstention driver (top-feature share 0.274 ≈ 0.25 chance over 2,644 pooled declines), retiring the old single-draw "feature 0" reading | ✓ instrument works; reports a null as a null |
| **E6** fairness | per-site coverage 0.980–0.990 across size bins, answered error 0.052–0.067 (< α); composition predicted 6.3% / BBSE-implied 8.6% / oracle 9.2% positive | ✓ no size-based coverage collapse |
| **E7** record-as-unit comparator | the record-level certifier grants α=0.05 in 99–100% of the draws the site-unit walk refuses in 100%, then violates its aggregate budget in 3.5% (s_u=0.5) / **9.6%** (s_u=2.0, ≈2δ) of them | ✓ the motivating failure is demonstrated, not cited |

Headline for the paper: the certificate is **valid on the estimand it actually certifies** (0/200 aggregate exceedances under a 5% budget, robust to a 4× increase in between-site heterogeneity), the label-shift correction converts a 39.5%-violation baseline into an honest abstainer that issues no unsupported certificate, and the concept-shift control fails exactly as an honest method must. At the real 208-site scale α=0.10 is the operative rung; α=0.05 needs ~300+ sites.

### Results — eICU-CRD v2.0, real data, 2026-07-31

The credentialed extract was run end to end against a protocol frozen *before* any eICU byte was read (`EICU-PROTOCOL.md`; freeze commit `9f25b49`, 2026-07-30). Cohort 164,322 first ICU stays over 207 hospitals at 8.89% prevalence; 161 features from a deny-by-default allowlist. **α=0.10 certified on all 20 replicates and α=0.05 on none**, mean coverage 0.890 at mean τ 0.793, with the fresh-pool `rm_exceed` firing 0/20 and all five pre-declared failure criteria (F-A–F-E) clear. APACHE-IVa on the same answered set: AUC 0.820. Predictions P1/P3/P6/P7 confirmed, P2/P4/P5 falsified — and P4's falsification is the *desired* outcome, since under amendment A1 a confirmed P4 would have been the leak's signature. Artifacts are aggregate-only by construction (`EICU-SUMMARY.md`, `EICU_*.csv/json`); the extract itself is gitignored and was never committed.

One caveat travels with every one of those numbers: among answered cases the oracle positive rate is 4.6% against 8.9% cohort-wide, so the gate earns part of its low error by abstaining where deaths concentrate. That is what the three-way composition instrument exists to surface.

## Scope — what is IN

| Component | Why it survives |
|---|---|
| Site-disjoint splits, site = cluster | The core statistical contribution; record-level bounds are wrong for this data |
| Influence-capped atoms (cap on weights, never realized contributions) | v1's Hole-1 counterexample (17.5% true risk certified at 5% under naive truncation) — kept as a regression test |
| WSR betting test, audited constants | Finite-sample, ~10× tighter than empirical-Bernstein at these cluster counts (v1 Stage-0) |
| Fixed-sequence threshold walk | Multiplicity-free threshold selection; order fixed on the aux split |
| BBSE label-shift mode, worst-case over a four-parameter confidence box | The flagship robustness result; the asymptotic steps (the S_aux percentile box, and the q cluster bootstrap for multi-site pools) **disclosed in the guarantee text from day one** (audit F01/V13), with measured realized coverage in METHODS |
| α ladder {0.05, 0.10} | Audit F15: at ~80 calibration clusters only 0.10 is realistically certifiable; 0.05 is the stretch rung; the E4 sweep quantifies exactly what more sites buy |
| Concept-shift negative control | The honesty story: certificates fail there *and must* — assumption tags are load-bearing |
| Explainable abstention layer | The collection's headline theme; nearly free on a linear head |
| Input-contract validation (loud, at the boundary) | Audit Part 2: a dozen silent failure modes existed in v1 because nothing validated inputs |

## Scope — what is OUT (each cut is audit-justified)

| Cut | Justification |
|---|---|
| A1 covariate-shift importance weighting | Audit F34: structurally cannot certify at any α rung below ~400 clusters (clip cap divides the margin under the floor). Shipping a never-firing mode adds pages, not value. Mentioned in limitations. |
| kNN out-of-support screen | Removes an entire subsystem (and v1's screen-kill failure mode F06, per-target runtime F50). Confidence gate + BBSE carry the robustness story. Limitations + future work. |
| Temporal / calendar machinery (Hole 6) | No calendar dimension existed anywhere in v1 (F21); for the paper it is one limitations paragraph. |
| External-score wrapping, eligibility protocol | v1 Decision 2 already kept it out of the certified path; drop the harness roles too. |
| Missingness three-part veto | Belonged to A1 (cut) and to a deployment-grade claim this paper doesn't make. One limitations paragraph. |
| Frozen-preregistration / amendment-log apparatus (v1's regulator-grade machinery) | The right-sized version of the same idea ships instead: splits, constants, and thresholds fixed before evaluation, enforced by `constants.py` + `tests/test_constants.py` (audit F13) — and, for the real-data path, `EICU-PROTOCOL.md` frozen at commit `9f25b49` before any eICU byte was read, with its A1–A6 amendment log. |
| 4-way outcome, per-class certification | v1 Decision 1: infeasible at these cluster counts; per-class rates reported as estimates only. |

## Design constants (chosen fresh, informed by the audit — see SPEC.md for the full frozen table)

- Splits **40% train / 20% aux / 40% calibration** (site-disjoint). v1's 40/30/30 starved calibration (63 clusters — audit F15); with A1 and the screen gone, the aux split only serves the walk order + BBSE confusion matrix, so calibration gets 40% (~83 clusters at 208 sites), moving the α=0.10 rung from marginal to comfortable.
- δ = 0.05; BBSE split δ_conf = δ_bet = 0.025, Bonferroni over 4 box parameters (c0, c1, π_source, q_target — audit V2).
- Influence cap M = 100; threshold grid 23 points in [0.55, 0.99]; WSR constants exactly as audited in v1.
- Every hardening the audit recommended is native here: loud input validation, disjointness assertions, finite-weight checks, record-carrying cluster gate, degenerate-bootstrap decline, BBSE misspecification decline, sha256-only seed rule, provenance block, pinned dependencies, literal-pinned constants test.

## Repository map

```
certgate/
  README.md            ← this file (scope & objectives)
  METHODS.md           ← paper-ready methods section
  PAPER-OUTLINE.md     ← section plan mapped to the collection's topics + reviewer risks
  SPEC.md              ← engineering contract: interfaces, frozen constants, audit-lesson checklist
  EICU-PROTOCOL.md     ← frozen real-data protocol (cohort, allowlist, denylist, P1–P7, F-A–F-E)
  CODE-AUDIT.md        ← 2026-07-25 correctness audit (V1–V27) + resolution
  REDTEAM.md           ← internal red-team pass + resolution
  requirements.txt     ← exact pins
  certgate/            ← package
    constants.py  validate.py  data.py  model.py
    certify.py    shift.py     explain.py  report.py  pipeline.py
    reliability.py ← POST-HOC selective reliability panel (descriptive; a numpy-only DAG leaf)
  tests/               ← incl. test_constants.py pinning every frozen scalar
  experiments/
    run_synthetic.py   ← E1–E7 grid (--quick for smoke)
    synth_fixture.py   ← hostile multi-table fixture corpus
    fixture_etl.py     ← fixture → cohorts
    eicu_mock.py       ← schema-faithful eICU mock corpus (stdlib only)
    eicu_etl.py        ← eICU extract → cohorts (stdlib + numpy only)
    run_eicu.py        ← eICU preflight + certification runner
    panel_s2_tables.py ← read-only analysis behind paper Tables 6 and 7
    out/               ← figures + CSVs for the paper
  examples/
    real_data_example.py    ← runnable from_raw → run_certgate walkthrough
    explain_dashboard.py    ← self-contained interactive explanation dashboard
                              (plain-language + advanced modes; open the
                              generated .html in any browser, no install)
    explain_dashboard_eicu.py ← the same page over one replicate of the real
                              extract; cross-checks its rung against the
                              released certificate and carries the OUTCOME of
                              that check on the page. Output is record-level and
                              gitignored — never commit it (DUA 1.5.0)
    DASHBOARD-DESIGN.md     ← the dashboard's design system + do-not-regress list
    DASHBOARD-PRODUCT.md    ← its audiences and truth constraints
  paper/               ← manuscript draft, references, editorial-panel review
```

## Quickstart

```bash
pip install -r requirements.txt
python -m pytest tests -q                      # ~28 s
python -m experiments.run_synthetic --quick    # smoke grid
python -m experiments.run_synthetic            # full paper grid
```

## Real data

**This path has been exercised on the real thing** (eICU-CRD v2.0, 2026-07-31 — see the results section above and `EICU-PROTOCOL.md`). `experiments/eicu_etl.py` + `run_eicu.py` are the worked real-extract implementation; the extract itself is gitignored, never committed, and never redistributable.

For a *different* dataset, `certgate/validate.py` is the loader contract to build against: `from_raw(x, y_raw, positive_label, site_ids_raw)` coerces string or int outcome labels to strict bool, densifies raw site ids, and runs the loud input checks before anything is fitted. `examples/real_data_example.py` is a runnable, heavily-commented walkthrough of the whole glue — it writes a realistic 208-site CSV (~35 MB, temp-dir, cleaned up), reads it back with the stdlib `csv` module (no pandas), splits sites into train/aux/cal **by site** (never by record — site-disjointness is asserted at pipeline entry), builds cohorts with `from_raw`, and runs `run_certgate` *without* oracle labels — passing `target_site_id` for a 12-site deployment pool, so the per-site target disjointness gate and BBSE's cluster-bootstrap q interval are both exercised — through to a certificate, an abstention explanation, and an honest decline. A legitimately all-negative deployment batch flows through via `from_raw(..., require_both_classes=False)`.

## Relation to v1

v1 (`../testbed/`, `../PROTOCOL.md`) remains untouched as the archival record. CertGate is a from-scratch rewrite: smaller surface, audit lessons applied at design time rather than patched in, and a paper-shaped deliverable. The real 208-hospital dataset did arrive before the deadline and has run end to end (2026-07-31), so the study now rests on both arms: the synthetic grid, where oracle access makes the validity claim falsifiable, and eICU-CRD v2.0, where the certificate meets a cohort nobody constructed.
