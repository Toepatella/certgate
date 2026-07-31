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

### Results — synthetic run, 2026-07-21 (all criteria met)

Full grid at R=200; artifacts in `experiments/out/` (`summary.md` + `provenance.json` + per-experiment CSVs/PNGs/JSON). Suite 136/136 green (~11s; +1 full-scale fixture arm gated behind `CERTGATE_FIXTURE=1`).

*(Table refreshed 2026-07-25 after the correctness-audit fixes — E1 is rescored to the certified estimand, E2/E3 run at the documented sep=2.2, and BBSE carries the q_t confidence share; see `CODE-AUDIT.md`.)*

| Exp | Result | Criterion |
|---|---|---|
| **E1** validity | α=0.10 certifies 1.0 at 0.982 coverage; **aggregate R_M-exceed rate 0.0 ≤ δ=0.05** on fresh 200-site pools, holding at s_u ∈ {0.5, 1.0, 2.0}; per-site dispersion diagnostic rises 0.02 → 0.10 with heterogeneity (measured, not bounded — the certificate is a site-population average) | ✓ viol ≤ δ on the certified estimand; coverage ≥ 0.75 |
| **E2** label shift (0.095→0.22) | uncorrected baseline hard-violates **0.395**; **BBSE issues zero certificates** (declines 200/200: 194 failsafe / 6 misspecified) — never certifies-and-lies; with the q_t budget a small single-site pool cannot support a certified rung under this shift | ✓ correction removes violations |
| **E3** concept control | tilt verified to push true risk to 0.161 > α, then certificate hard-violates 0.700 | ✓ tag is load-bearing |
| **E4** frontier | α=0.10 certifies from ~150 sites (1.0 at 150/208/300/400, coverage 0.94–0.98); α=0.05 first at 300 (0.285), reliable at 400 (1.0); 60/100 gated by the 50-carrying-cluster floor | ✓ clean frontier; α=0.10 operative at 208 |
| **E5** explain | τ*=0.55, 200 answered / 2 declined, top abstention-driver feature identified | ✓ |
| **E6** fairness | per-site coverage 0.980–0.990 across size bins, answered error 0.052–0.067 (< α); composition predicted 6.3% / BBSE-implied 8.6% / oracle 9.2% positive | ✓ no size-based coverage collapse |

Headline for the paper: the certificate is **valid on the estimand it actually certifies** (0/200 aggregate exceedances under a 5% budget, robust to a 4× increase in between-site heterogeneity), the label-shift correction converts a 39.5%-violation baseline into an honest abstainer that issues no unsupported certificate, and the concept-shift control fails exactly as an honest method must. At the real 208-site scale α=0.10 is the operative rung; α=0.05 needs ~300+ sites.

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
| Frozen-preregistration / amendment-log apparatus | Regulator-grade machinery. The paper states: splits, constants, and thresholds fixed before evaluation — enforced by `constants.py` + `tests/test_constants.py` (audit F13), which is the right-sized version of the same idea. |
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
  requirements.txt     ← exact pins
  certgate/            ← package
    constants.py  validate.py  data.py  model.py
    certify.py    shift.py     explain.py  report.py  pipeline.py
  tests/               ← incl. test_constants.py pinning every frozen scalar
  experiments/
    run_synthetic.py   ← E1–E6 grid (--quick for smoke)
    out/               ← figures + CSVs for the paper
  examples/
    real_data_example.py    ← runnable from_raw → run_certgate walkthrough
    explain_dashboard.py    ← self-contained interactive explanation dashboard
                              (plain-language + advanced modes; open the
                              generated .html in any browser, no install)
```

## Quickstart

```bash
pip install -r requirements.txt
python -m pytest tests -q                      # ~10 s
python -m experiments.run_synthetic --quick    # smoke grid
python -m experiments.run_synthetic            # full paper grid
```

## Real data

When a real multi-site dataset arrives, `certgate/validate.py` is the loader contract to build against: `from_raw(x, y_raw, positive_label, site_ids_raw)` coerces string or int outcome labels to strict bool, densifies raw site ids, and runs the loud input checks before anything is fitted. `examples/real_data_example.py` is a runnable, heavily-commented walkthrough of the whole glue — it writes a realistic 208-site CSV (~35 MB, temp-dir, cleaned up), reads it back with the stdlib `csv` module (no pandas), splits sites into train/aux/cal **by site** (never by record — site-disjointness is asserted at pipeline entry), builds cohorts with `from_raw`, and runs `run_certgate` *without* oracle labels — passing `target_site_id` for a 12-site deployment pool, so the per-site target disjointness gate and BBSE's cluster-bootstrap q interval are both exercised — through to a certificate, an abstention explanation, and an honest decline. A legitimately all-negative deployment batch flows through via `from_raw(..., require_both_classes=False)`.

## Relation to v1

v1 (`../testbed/`, `../PROTOCOL.md`) remains untouched as the archival record. CertGate is a from-scratch rewrite: smaller surface, audit lessons applied at design time rather than patched in, and a paper-shaped deliverable. If the real 208-site dataset arrives before the submission deadline, `validate.py` is the loader contract to build against and the experiments gain a real-data section; the paper stands on the synthetic study either way.
