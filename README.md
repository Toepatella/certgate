# CertGate — certified selective prediction with explainable abstention for multi-site clinical risk models

**Status:** code and aggregate artifacts accompanying the manuscript *"CertGate: finite-sample certified selective prediction for multi-site clinical risk models, with label-shift robustness and explainable abstention"* (prepared for the Springer Nature collection named below). The synthetic experiment grid (E1–E9) and a certified run on real multi-site clinical data (eICU-CRD v2.0, 20 by-site re-splits) are both published in `experiments/out*/`; the test suite is green (304 passed, 3 skipped); the code is archived at Zenodo (concept DOI 10.5281/zenodo.22148739).

## Venue

**Discover Computing** (Springer Nature, open access), topical collection *"Intelligent Medicine: Machine Learning and Explainable AI for Next-Generation Healthcare"*; article type Research; collection deadline 2026-10-05. The collection lists uncertainty quantification, calibration, out-of-distribution robustness, clinical auditability and explainability among its topics.

**Manuscript title:** *CertGate: finite-sample certified selective prediction for multi-site clinical risk models, with label-shift robustness and explainable abstention.*

## The pitch (one paragraph)

A clinical risk model should answer only when it can back the answer with a guarantee. CertGate wraps any probabilistic classifier in a selective gate that certifies, with finite-sample confidence 1−δ, that the influence-weighted error rate among *answered* cases — **averaged over the site population** from which calibration was drawn — stays below a stated budget α, treating the **site** (hospital), not the record, as the unit of statistical independence, which is what multi-site clinical data actually requires and what naive record-level guarantees silently get wrong. (A site-population average, not a per-site bound: individual sites can exceed α under between-site heterogeneity, and the certificate says so on its face.) Under outcome-prevalence (label) shift between calibration sites and a new deployment site the certificate is re-derived through a worst-case correction whose own estimation uncertainty is folded into the guarantee; when the data cannot support the correction the mode declines rather than certify — which is what it did on eICU. Under relationship (concept) shift — undetectable from unlabeled data at prediction time, detectable retrospectively once discharge labels accrue — the system's failure is demonstrated openly as a negative control rather than hidden. Every answer and every abstention is explained: the risk model is linear by design, and the gate reports which features drove each decline.

## Objectives (measurable)

- **O1 — Method.** A certified selective-prediction gate for site-clustered data: influence-capped cluster statistics + a betting-style (WSR) finite-sample test + a fixed-sequence threshold walk; two assumption modes (exchangeable baseline; BBSE label-shift with cluster-robust uncertainty), with the mode tag part of the guarantee.
- **O2 — Explainability.** Global (standardized coefficients), local (exact linear attributions), and **abstention explanations** (which features pushed a declined case below the confidence bar) — no post-hoc approximator needed, because the deployed head is linear by design.
- **O3 — Honest empirical validation.** Across replicated calibration draws (R = 200 per point unless stated): aggregate conformance — the certified site-population risk on fresh pools exceeds α in at most a δ share of the replications in which a certificate fires — with the per-site hard-violation rate reported as a diagnostic that carries no δ target; label-shift experiments where the uncorrected baseline demonstrably fails and the corrected mode certifies or declines; a concept-shift **negative control that is verified capable of failing** — a control that cannot fail proves nothing.
- **O4 — Reproducibility.** One pinned environment (`requirements.txt`), deterministic seeds derived by a fixed rule, provenance block (versions, seeds, and for the eICU runs a name-and-size fingerprint of the extract) embedded in every report artifact, full experiment grid re-runnable with one command.

**Design targets (checked against the released artifacts):** aggregate exceedance rate ≤ δ in E1/E2; α=0.10 certifies with coverage ≥ ~0.75 at the realistic 208-site scale; the site-count sweep (E4) shows the feasibility frontier (which α each cluster count can support). **Measured runtimes** (Intel Core Ultra 7 165U, 14 logical cores, 31.5 GB RAM, CPU only, Windows 11, Python 3.13.3): test suite about a minute wall-clock (47–83 s over seven runs; 307 tests: 304 pass, 3 full-scale arms skipped by default); full synthetic grid 42 min (2,514 s); the `panel_s2_tables` replay 135 s; the eICU 20-replicate run 29.5 min (1,768 s) plus a 49 s preflight, given the credentialed extract.

### Results (headlines; full numbers live in `experiments/out*/` and `paper/draft.md` §4)

On the paper's metric — aggregate conformance, with the per-site rate a diagnostic — every design target above is met. Every figure below is stated once, canonically, in the generated artifacts — `experiments/out/summary.md` (synthetic grid, per-block `_run` stamps authoritative) and `experiments/out/EICU-SUMMARY.md` (real data) — and in the paper draft; this section deliberately carries claims, not number trains.

**Synthetic grid (E1–E9; R = 200 per point unless stated — the E9 label-shift arm runs 50, the E2 sweep 100, the E8 noise arm 300):** the certificate is valid on the estimand it actually certifies — 0 of 200 replications exceed the budget on fresh pools, robust to a 4× increase in between-site heterogeneity, while the per-site dispersion diagnostic (which carries no δ target) visibly detaches (E1). Under a prevalence shift the uncorrected gate exceeds its budget on fresh pools in 97.5% of replications (hard-violating 39.5%), while the corrected mode certifies or declines — it declines under that shift rather than repeat the overclaim, and certifies at null shift (E2). The concept-shift negative control is verified poisonous first and then fails the certificate, as an honest method must (E3). The site-count frontier makes α=0.10 the operative rung at the realistic 208-site scale, with α=0.05 a property of ~300–400-site data (E4). The explainability arm reports its cohort-level null as a null (E5), per-site coverage is flat across size bins with the three-way composition disclosed (E6), and the record-as-unit comparator demonstrates in-harness the overconfidence the design premise cites — granting rungs the site-unit walk refuses, then violating its budget at ~2δ under heterogeneity (E7). The comparator, stress, and power-frontier families bound what the certificate can deliver: every valid alternative bound confirms the site-count frontier and the asymptotic defaults run at their nominal level with no margin (E8), the certifier declines before it violates under an aleatoric floor (E8), and the label-shift mode certifies under genuine shift only once source capacity reaches the high hundreds of sites with a multi-site declared target (E9).

**eICU-CRD v2.0 (real data, 2026-07-31):** the credentialed extract ran end to end against a protocol frozen *before* any eICU byte was read (`EICU-PROTOCOL.md`; freeze commit `9f25b49`). **α=0.10 certified on all 20 by-site re-splits and α=0.05 on none**, with every pre-declared failure criterion clear; three pre-declared leak screens clear and a fourth returns a caution the ablation screen bounds — one screen inverted (APACHE absence tracks early *discharge*, not early death, on this extract). Of the seven predictions registered in the protocol, 3 are confirmed, 1 partly, and 3 falsified (clause-by-clause settlement: `experiments/out-settled/EICU-PREDICTIONS-SETTLED.md`, post-hoc). The caveat that travels with every number: the gate earns part of its low answered error by abstaining where deaths concentrate, which the three-way composition instrument exists to surface. Artifacts are aggregate-only by construction; the extract is gitignored and was never committed. Full record: `experiments/out/EICU-SUMMARY.md`, draft §4.10 and Tables 1–2.

## Scope — what is IN

| Component | Design rationale |
|---|---|
| Site-disjoint splits, site = cluster | The core statistical contribution; record-level bounds are wrong for this data |
| Influence-capped atoms (cap on weights, never realized contributions) | A naive-truncation counterexample (17.5% true risk certified at 5%) is kept as a permanent regression test; the cap is applied where it cannot recreate it |
| WSR betting test | Finite-sample, and measurably tighter than the empirical-Bernstein alternative at these cluster counts (quantified in the paper's comparator suite) |
| Fixed-sequence threshold walk | Multiplicity-free threshold selection; order fixed on the aux split |
| BBSE label-shift mode, worst-case over a four-parameter confidence box | The flagship robustness result; the asymptotic steps (the S_aux percentile box, and the q cluster bootstrap for multi-site pools) are **disclosed in the guarantee text itself**, with measured realized coverage in METHODS |
| α ladder {0.05, 0.10} | At ~83 calibration clusters only 0.10 is realistically certifiable; 0.05 is the stretch rung, and the E4 sweep quantifies exactly what more sites buy |
| Concept-shift negative control | Certificates fail there *and must* — assumption tags are load-bearing, and the control is verified capable of failing before it is trusted |
| Explainable abstention layer | The collection's headline theme; exact attributions come nearly free on a linear head |
| Input-contract validation (loud, at the boundary) | Silent input failure modes are designed out rather than patched: strict labels, finite features, dense site ids, disjointness asserted at pipeline entry |

## Scope — what is OUT (each cut is deliberate)

| Cut | Justification |
|---|---|
| Covariate-shift importance weighting | A design-time estimate puts certification out of reach at any α rung below ~400 clusters (the clip cap divides the margin under the information floor). Shipping a never-firing mode adds pages, not value. Stated in limitations. |
| kNN out-of-support screen | An entire subsystem whose failure modes outweigh its contribution at this scale; the confidence gate + BBSE carry the robustness story. Limitations + future work. |
| Temporal / calendar machinery | The datasets carry no usable calendar dimension; one limitations paragraph covers it. |
| External-score wrapping, eligibility protocol | Outside the certified path by design; the gate certifies its own head's answered set. |
| Missingness three-part veto | Belonged to the covariate-shift mode (cut) and to a deployment-grade claim this paper doesn't make. One limitations paragraph. |
| Heavyweight preregistration / amendment-log apparatus | The right-sized version ships instead: splits, constants, and thresholds fixed before evaluation, enforced by `constants.py` + `tests/test_constants.py` — and, for the real-data path, `EICU-PROTOCOL.md` frozen at commit `9f25b49` before any eICU byte was read, with its A1–A6 amendment log. |
| Multi-class outcome, per-class certification | Infeasible at these cluster counts; per-class rates are reported as estimates only. |

## Design constants (see SPEC.md for the full frozen table)

- Splits **40% train / 20% aux / 40% calibration** (site-disjoint). The aux split serves only the walk order and the BBSE confusion matrix, so calibration gets an equal 40% share with training (83 calibration clusters at 208 sites, beside 83 train / 42 aux); a design-time estimate places the α=0.10 rung within reach at that cluster count, and the E4 sweep measures where it is.
- δ = 0.05; BBSE split δ_conf = δ_bet = 0.025, Bonferroni over the 4 box parameters (c0, c1, π_source, q_target).
- Influence cap M = 100 (swept in SI Table S4; larger caps certify no more); threshold grid 23 points in [0.55, 0.99].
- Hardening is native, not bolted on: loud input validation, disjointness assertions, finite-weight checks, record-carrying cluster gate, degenerate-bootstrap decline, BBSE misspecification decline, sha256-only seed rule, provenance block in every artifact, pinned dependencies, literal-pinned constants test.

## Repository map

```
certgate/
  README.md            ← this file (scope & objectives)
  METHODS.md           ← paper-ready methods section
  SPEC.md              ← engineering contract: interfaces, frozen constants, audit-lesson checklist
  EICU-PROTOCOL.md     ← frozen real-data protocol (cohort, allowlist, denylist, P1–P7, F-A–F-E)
  CODE-AUDIT.md        ← adversarial correctness audit of the method (LLM-simulated auditors,
                          2026-07-25) + RESOLUTION ledger naming the test that pins each fix
  REDTEAM.md           ← adversarial red-team pass on the statistical core (LLM-simulated
                          lenses, 2026-07-21/22) + resolution ledger
  requirements.txt     ← exact pins
  certgate/            ← package
    constants.py  validate.py  data.py  model.py
    certify.py    shift.py     explain.py  report.py  pipeline.py
    harness.py    ← the violation instruments (wilson_lcb, hard_violation,
                     exceedance_reference — every violation number in the paper)
    reliability.py ← POST-HOC selective reliability panel (descriptive; a numpy-only DAG leaf)
  conftest.py          ← two-line sys.path shim (examples/ and the root have no __init__.py)
  tests/               ← incl. test_constants.py pinning every frozen scalar
  experiments/
    run_synthetic.py   ← E1–E9 grid (--quick for smoke)
    synth_fixture.py   ← hostile multi-table fixture corpus
    fixture_etl.py     ← fixture → cohorts
    eicu_mock.py       ← schema-faithful eICU mock corpus (stdlib only)
    eicu_etl.py        ← eICU extract → cohorts (stdlib + numpy only)
    run_eicu.py        ← eICU preflight + certification runner
    comparators.py     ← E8 alternative cluster-aware bounds (pure arithmetic)
    panel_s2_tables.py ← read-only analysis behind SI Tables S4–S5
    panel_confusion_tables.py ← read-only derived confusion tables (SI Table S7)
    fig_eicu_abstention_drivers.py ← read-only renderer of main Figure 3 from the released eICU diagnostics
    out/               ← figures + CSVs for the paper (20-replicate eICU aggregates included)
    out-sens/          ← eICU apache-complete sensitivity arm (aggregate-only sidecar)
    out-panel/         ← eICU replicate-0 panel measurement (aggregate-only sidecar, POST-HOC)
    out-subgroups/     ← eICU subgroup aggregates (aggregate-only sidecar)
    out-faithfulness/  ← eICU replicate-0 attribution value-function contrast (aggregate-only sidecar, POST-HOC; SI Table S10)
    out-e9a-rescore/   ← replay + rescoring of the E9 label-shift power frontier (POST-HOC, 2026-09-04)
    out-e9b-positives/ ← second arm of the E9 false-negative frontier, positives-normalised atom (POST-HOC, 2026-09-04)
    out-bbse-probe/    ← coverage probe of the BBSE uncertainty box, head held fixed (POST-HOC, 2026-09-04)
    out-settled/       ← clause-by-clause settlement of the seven registered eICU predictions (POST-HOC, 2026-09-04)
    out-derived/       ← read-only numbers derived from the released aggregates (POST-HOC, 2026-09-04)
    out-timing/        ← eICU preflight re-run for runtime and LOS-window facts (aggregate-only sidecar, POST-HOC, 2026-09-05)
    out-rev2/          ← eICU 20-replicate re-run with appended diagnostics; the released run stays canonical (aggregate-only sidecar, POST-HOC, 2026-09-05)
  examples/
    real_data_example.py    ← runnable from_raw → run_certgate walkthrough
    explain_dashboard.py    ← self-contained interactive explanation dashboard
                              (plain-language + advanced modes; open the
                              generated .html in any browser, no install)
    explain_dashboard.html  ← the committed synthetic demo page it renders
    explain_dashboard_mock.py   ← the same page over a MOCK eICU-shaped corpus (900
                              generated hospitals carrying the real column names;
                              no eICU record); banner "MOCK CORPUS" on the page
    explain_dashboard_mock.html ← its committed output (cited in draft §4.11)
    explain_dashboard_eicu.py ← the same page over one replicate of the real
                              extract; cross-checks its rung against the
                              released certificate and carries the OUTCOME of
                              that check on the page. Output is record-level and
                              gitignored — never commit it (DUA 1.5.0)
    DASHBOARD-DESIGN.md     ← the dashboard's design system + do-not-regress list
    DASHBOARD-PRODUCT.md    ← its audiences and truth constraints
  paper/               ← manuscript draft, references, build script
```

## Quickstart

```bash
pip install -r requirements.txt
python -m pytest tests -q                      # ~1 min
python -m experiments.run_synthetic --quick    # smoke grid
python -m experiments.run_synthetic            # full paper grid
```

## Real data

**This path has been exercised on the real thing** (eICU-CRD v2.0, 2026-07-31 — see the results section above and `EICU-PROTOCOL.md`). `experiments/eicu_etl.py` + `run_eicu.py` are the worked real-extract implementation; the extract itself is gitignored, never committed, and never redistributable.

## How this repository was built

Large language models (Anthropic Claude) were used throughout as coding, drafting and review-simulation assistants. All methods, analyses, results and text were specified, verified and are the sole responsibility of the author; no language model is an author. The repository's commit trailers record this assistance.

Concretely: a commit carries a `Co-Authored-By: Claude …` trailer whenever a model drafted part of the change (82 of the 83 commits at the time of writing), and the history is kept as written rather than rewritten, because the pre-extract freeze commit `9f25b49` is cited in the manuscript. Two adversarial passes were run on the statistical core with simulated reviewers and resolved in the open: `REDTEAM.md` (2026-07-21/22; six reviewer lenses with independent skeptic verification of every actionable finding; resolution ledger at its head) and `CODE-AUDIT.md` (2026-07-25; six dimension sweeps and four prosecution passes; RESOLUTION ledger after the verdict, naming the test that now pins each fix). The repository history also contains the author's internal pre-submission audits and simulated reviews, removed from HEAD at submission and kept for provenance; they are not part of the submission.

## Paper

The manuscript master is `paper/draft.md` (pandoc markdown; citations are `[@key]` groups against `paper/references.bib`) — the canonical, self-contained home of every result number alongside the generated artifacts in `experiments/out*/`. `python paper/make_submission.py` builds the whole submission package for Discover Computing (Springer Nature `sn-jnl`, pdflatex): `CertGate_DiscoverComputing.pdf` (the submission typescript), `CertGate_SI.pdf` (Supplementary Information A — deferred proofs, reproducibility details, the frozen-constants register as Table S1, and Figures S1–S10), `CertGate_compact.pdf` (a 10pt reading copy, not the typescript), and the Snapp figures zip (`Fig1.pdf`, `Fig2.png`, …). All author blanks are filled; the code is archived at Zenodo (concept DOI 10.5281/zenodo.22148739).

Figure → source map (as called out in the draft; the current build keeps five figures and two tables in the main text and moves the rest to the peer-reviewed SI):

| Figure | Source |
|---|---|
| 1 | `paper/figures-src/pipeline.tex` (schematic, compiled at build time) |
| 2 | `experiments/out/EICU_pooled.png` |
| 3 | `experiments/out/EICU_abstention_drivers.png` (rendered read-only from the released `EICU_diagnostics.json` by `experiments/fig_eicu_abstention_drivers.py`) |
| 4 | `experiments/out/E8_suite.png` |
| 5 | `experiments/out/E9_frontiers.png` |
| S1 | `experiments/out/EICU_reliability_panel.png` (SI) |
| S2 | `experiments/out/EICU_per_site.png` (SI) |
| S3 | `experiments/out/E1_validity.png` (SI) |
| S4 | `experiments/out/E3_concept_shift.png` (SI) |
| S5 | `experiments/out/E5_explain.png` (SI) |
| S6 | `experiments/out/E7_comparator.png` (SI) |
| S7 | `experiments/out/E4_site_sweep.png` (SI) |
| S8 | `experiments/out/E6_fairness.png` (SI) |
| S9 | `experiments/out/E2_label_shift.png` (SI) |
| S10 | `experiments/out-e9b-positives/E9b_fnr_positives.png` (SI, POST-HOC) |

Main-text tables: 1 = eICU attrition ledger, 2 = eICU per-replicate certificates. SI tables: S1 = frozen-constants register, S2 = realized exceedance strata (E1 artifacts), S3 = per-site coverage bins (E6 artifacts), S4 = influence-cap sweep, S5 = operating characteristics, S6 = cluster-count sweep grid (E4 artifacts), S7 = derived answered/declined confusion, S8 = eICU subgroup coverage, S9 = three-way answered-set composition (E6 artifacts), S10 = eICU attribution value-function contrast (POST-HOC; `experiments/out-faithfulness/EICU_faithfulness.csv`), S11 = the head's discrimination and calibration over the 20 re-splits (POST-HOC; `experiments/out-rev2/EICU_comparator.csv` + `experiments/out/EICU_pooled.csv`). One artifact PNG deliberately carries no figure number: `E6_reliability.png` (its results appear as prose in §4.7). And `experiments/out-sens/` is the frozen 2026-07-31 sensitivity-arm record: it predates the reliability panel, so it legitimately lacks the three `EICU_reliability*` files a current-code rerun would add.

Cloning without SSH keys: `git clone https://github.com/Toepatella/certgate.git`

## Adapting to a different dataset

For a *different* dataset, `certgate/validate.py` is the loader contract to build against: `from_raw(x, y_raw, positive_label, site_ids_raw)` coerces string or int outcome labels to strict bool, densifies raw site ids, and runs the loud input checks before anything is fitted. `examples/real_data_example.py` is a runnable, heavily-commented walkthrough of the whole glue — it writes a realistic 208-site CSV (~35 MB, temp-dir, cleaned up), reads it back with the stdlib `csv` module (no pandas), splits sites into train/aux/cal **by site** (never by record — site-disjointness is asserted at pipeline entry), builds cohorts with `from_raw`, and runs `run_certgate` *without* oracle labels — passing `target_site_id` for a 12-site deployment pool, so the per-site target disjointness gate and BBSE's cluster-bootstrap q interval are both exercised — through to a certificate, an abstention explanation, and an honest decline. A legitimately all-negative deployment batch flows through via `from_raw(..., require_both_classes=False)`.

