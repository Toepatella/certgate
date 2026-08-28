# CLAUDE.md — CertGate project guide

Certified selective prediction with explainable abstention for multi-site clinical risk models. Standalone Python research project targeting a paper. Read this first, then `SPEC.md` before touching any code.

## Simplicity rules — these override any instinct to be thorough

Ship the smallest diff that fully solves the stated problem. Nothing else.

- No features, refactors, cleanup, or abstractions beyond the task. No new classes, layers,
  wrappers, helpers, config options, or files when editing existing code works.
- No error handling or validation for scenarios that cannot happen. Validate only at the
  boundary (`certgate/validate.py`).
- No unneeded tests. Test what changed; don't build suites around it or test inputs
  internal code cannot produce.
- No designing for hypothetical future requirements, no feature flags, no back-compat
  shims — just change the code.
- The paper targets Discover Computing, not a top-tier ML conference: scope experiments,
  analyses, and sections to clear THAT venue's bar comfortably, and no higher.
- Think something more is needed? Propose it in one sentence; don't build it.

This licenses adding nothing new — it never licenses removing existing hardening: the
Design discipline and Invariants sections below stay binding.

## Where numbers live (single-source policy, adopted 2026-08-10)

Result numbers have ONE canonical home: the generated artifacts — `experiments/out/summary.md` (synthetic grid), `experiments/out*/EICU-SUMMARY.md` + the JSON/CSV beside them (real data) — plus `paper/draft.md`, which must be self-contained for submission. This file and `README.md` carry **headlines and claims, not number trains**; when you need a figure, open the artifact or the draft rather than trusting a prose copy. A 2026-08-10 audit found the same fact drifted in up to five hand-maintained copies — do not reintroduce copies here.

## What this is

A selective-prediction gate that certifies, with finite-sample confidence 1−δ, that the error rate among *answered* cases stays ≤ α — treating the **site (cluster), not the record**, as the unit of statistical independence. Two assumption modes (exchangeable baseline; BBSE label-shift with cluster-robust uncertainty), an explainable-abstention layer, and an honest validation harness (verified-falsifiable negative controls; a two-number violation protocol).

**Target venue:** Discover Computing (Springer) — collection *"Intelligent Medicine: ML and Explainable AI for Next-Generation Healthcare"*, **submission deadline 2026-10-05**. See `PAPER-OUTLINE.md` (pre-draft planning record, banner-marked where superseded).

**Design discipline:** every scope cut (covariate-shift mode, kNN screen, temporal machinery, heavyweight preregistration apparatus) and every hardening (loud input validation, sha256-only seeds, record-carrying cluster gate, bootstrap top-up-or-decline, provenance blocks, pinned deps, literal-pinned constants test) is a deliberate, audited design decision traced in SPEC's "Audit-lesson conformance" checklist. These are native to the design — **do not regress them.**

## Real data: certified (2026-07-31)

The eICU-CRD v2.0 extract arrived and the frozen operator checklist ran end to end. **Headline: α=0.10 certified on all 20 by-site re-splits, α=0.05 on none; every pre-declared failure criterion (F-A–F-E) clear; leak_alarm 0/20.** The E-9 leak screen fired INVERTED — APACHE-absent stays have *lower* mortality (early discharge, not early death, dominates absence), so the registered fear was not what governs this extract. Predictions P1/P3/P6/P7 confirmed, P2/P4/P5 falsified — P4's falsification is the *desired* outcome (abstention drivers are physiology, not missingness; under A1 a confirmed P4 would have been the leak's signature). The honest caveat that travels with every number: the gate earns part of its low answered error by abstaining where deaths concentrate (three-way composition disclosure). Full figures: `experiments/out/EICU-SUMMARY.md` and draft §4.10 / Tables 1–2 (current numbering: main Figures 1–5 with 1 = pipeline schematic and 3 = the eICU abstention-driver figure, main Tables 1–2; everything else lives in the SI as Figures S1–S9 / Tables S1–S10 — map in README § Paper).

**Amendment A6 is the ONE post-hoc amendment** (logged data-seen=YES, the only one that relaxes rather than tightens): one negative-not-`-1` cell in ~4.1M led `unexpected-negative-sentinel` to abort only above the already-frozen `EICU_MAX_UNPARSEABLE_SHARE = 0.01`. No new constant, no computed number changed — but **every figure from this extract must carry the post-hoc label**. Details: `EICU-PROTOCOL.md` amendment log.

## Status (2026-08-27)

Suite **276 passed / 3 skipped green** (~1 min on the project machine; three off-default arms gated behind `CERTGATE_FIXTURE=1` / `CERTGATE_EICU=1` / `CERTGATE_EICU_LARGE=1`). The synthetic grid (E1–E9, R=200) and the real-data run are both published; every result number lives in `experiments/out*/` and the draft. One line per experiment — claims only:

- **E1** validity: α=0.10 certifies every draw; aggregate R_M conformance holds at all heterogeneity settings while the per-site dispersion diagnostic (no δ target) detaches — the aggregate-vs-individual signature, measured and labeled. α=0.05 unreachable at 208 sites.
- **E2** label shift: the uncorrected baseline certifies-and-violates heavily and dose-responsively; BBSE with the honest q_t budget declines rather than repeat the overclaim, and certifies at null shift (a correction, not a reflexive decliner).
- **E3** concept control: verified-poisonous tilt → the certificate fails as its exclusion predicts; the assumption tag is load-bearing.
- **E4** frontier: α=0.10 certifiable from ~150 sites; α=0.05 needs ~300–400. At 208 sites α=0.10 is the operative rung.
- **E5** explainability: exact linear attributions; the R=200 replication arm returns the honest NULL — no stable abstention driver on the symmetric generator (the old n=2 "feature 0 driver" reading is retired).
- **E6** per-site coverage flat across size bins, answered error under α, three-way answered-set composition; plus the post-hoc reliability panel.
- **E7** record-as-unit comparator: the record-level certifier grants rungs the site-unit walk refuses, then violates its aggregate budget at ~2δ under heterogeneity — the motivating failure demonstrated in-harness, not cited.
- **E8** comparator + stress suite: among valid bounds on identical atoms the betting test dominates; the asymptotic defaults grant every rung at nominal exceedance with no margin; under an aleatoric floor the certifier declines before it violates; swapping the head costs coverage, never validity.
- **E9** power frontiers: BBSE certifies under genuine shift only at ~900–1,200 source sites with a multi-site declared target (single-site declaration is the study's one budget exceedance); no FNR budget below ~0.55 is issuable at realistic site counts.

Audit history (all fixed, SPEC first, then code, then tests; full records in the named files): internal red-team 2026-07-22 (`REDTEAM.md`); correctness audit V1–V27 2026-07-25 (`CODE-AUDIT.md` — betting core sound; the two criticals were the per-target-site estimand wording and the missing q_t budget, both now frozen into the guarantee text and constants); editorial panel on the manuscript 2026-07-25 (`paper/review/`, major revision — closures tracked in `revision-plan.md`); three-verifier ingest audit + arrival-day attack-corpus audit 2026-07-31 (protocol amendments A1–A5, threats T-20–T-27, E-9…E-22 in SPEC); panel-landing audit 2026-08-01 (RP-1–RP-9 in SPEC); citation spot-check + full-repo coherence audit 2026-08-10 (commit messages `ed7f1c5..b340e48` are the change log); repo-wide comment/docstring humanization 2026-08-24 (prose only, zero code changed, proved by an AST + code-line verifier); paper de-labelling + staleness sweep 2026-08-25; code simplification pass 2026-08-27 (dedup + structure only: run_certgate split at its gate seams, the runner scaffolding deduplicated, test_eicu_path.py split into test_eicu_mock/etl/run.py -- behavior proven byte-identical: 42/42 grid artifacts, the real-extract certificate, and the 194/194 panel replay all reproduce exactly).

**Post-hoc reliability panel (2026-08-01).** The verified `selective-reliability-panel` sandbox is ported **byte-exactly** into `certgate/reliability.py` — numpy + stdlib, a DAG leaf, no certgate dependency. (Byte-exact refers to the **code**. Comments and docstrings were rewritten for readability 2026-08-24 and no longer match the sandbox text; a re-pipe-back from the sandbox would overwrite that prose.) DESCRIPTIVE under A6 discipline: alters no certified quantity, settles none of P1–P7 / F-A–F-E, every real-extract number carries `POST_HOC_LABEL`. Wired into `run_E6` (no new `_rng` stream — every published E1–E7 number stayed byte-identical) and `run_eicu`'s pooled arm. Measured on the real extract at `experiments/out-panel/` (replicates=1, never `out/`): replicate 0 reproduced the published certificate exactly, the answered set is well-calibrated, the head edges APACHE-IVa on the matched denominator, and the answered−all skill contrast is negative — the quantitative form of the composition disclosure. Numbers: `out-panel/EICU_reliability_panel.json`, draft §4.7 (synthetic) and Supplementary Information A.4 (real).

**Manuscript.** De-labelled 2026-08-25: all 31 `E1`–`E9` codenames removed from the SI (caption prefixes, Table S5 row labels, and the `*Experiment labels.*` paragraph in A.3), replaced by one `E1_`–`E9_` artifact-prefix sentence in Code availability; the 20 plot titles in `run_synthetic.py` were de-labelled and the figures regenerated, since the codes were baked into the images. `P1`–`P7` are deliberately KEPT (11 hits, main-text Results) as pre-registration reporting. Two stale cross-refs from the 2026-08-21 renumber fixed (§4.11→§4.12, §4.13→§4.14) and a `$10 	imes 10$` literal-tab corruption in the Table S10 legend repaired. `paper/draft.md` is complete through §4.14 and was trimmed 2026-08-21 to the Discover Computing bar (the venue sets no page limit; abstract 248 words), then rebalanced the same day for the collection's explainability emphasis (venue-fit pass: §4.11 "Explainable abstention on real clinical data" promoted out of §4.10 with Figure 3 and SI Table S10, the subgroup table named as the fairness reading, plain-language leads on §3.6/§3.7, an explanation-facing limitation in §6.1): main Figures 1–5 and Tables 1–2, SI Figures S1–S9 and Tables S1–S10 (all called out in-text; Figure 1 is the pipeline schematic), Assumption 1 + the SI A.1(iii) derivation, and a PhysioNet-compliant citation set — the TODO §6 spot-check ran 2026-08-10 and all entries are VERIFIED (record + caveats in `paper/TODO.md` §6; submission blockers in §6a). Working state lives in `paper/TODO.md`; review closures in `paper/review/revision-plan.md`.

## How to run

```bash
pip install -r requirements.txt
python -m pytest tests -q                       # ~1 min, must stay green
python -m experiments.run_synthetic --quick     # smoke grid (R=10)
python -m experiments.run_synthetic             # full paper grid (R=200); E4 is the long pole
```
Experiments write CSVs, PNGs, and `summary.md` to `experiments/out/`.

The eICU real-data path (the mock corpus is the suite's stand-in; the real extract ran the certified path 2026-07-31):

```bash
python -m experiments.eicu_mock --out ./eicu-mock                      # 9k stays / 180 hospitals
python -m experiments.run_eicu --data ./eicu-mock --preflight --no-reference-check
python -m experiments.run_eicu --data ./eicu-mock --replicates 2
```

Off-default arms: `CERTGATE_EICU=1` (208-hospital / 200,859-stay mock, ~2 min) and
`CERTGATE_EICU_LARGE=1` (900 hospitals — the only arm that reaches the CERTIFIED branch;
`margin_floor` scales as `1/n_carrying`, so the mock's decline is a property of the frozen
corpus sizes, **not** of "any corpus size" — the crossing point is `n_carrying = 77`).
`--preflight` profiles and writes the a-priori predictions but certifies nothing; drop
`--no-reference-check` for the real extract so a wrong download raises. Outputs are
`EICU_*` + `EICU-SUMMARY.md` in `experiments/out/` and are **aggregate-only by
construction** (`run_eicu.assert_aggregate_only` gates every write).

The two explain dashboards are rendered artifacts, rebuilt separately from the runs above:

```bash
python -m examples.explain_dashboard                                # committed synthetic demo
python -m examples.explain_dashboard_eicu --data ./eicu-extract     # local only, gitignored
```

The eICU driver walks the same replicate-0 pipeline `run_eicu` does (`site_split` →
S_train-only `impute` → `_build_cohorts` → `fit_head` → `run_certgate`) and then
**cross-checks the rung it is about to display against the released
`experiments/out/EICU_certificate.json`** — alpha, tau, tau_idx, mode, coverage and
calibration-site count — aborting on any disagreement (a missing field also fails: a
comparison that cannot be made is a failed cross-check, not a passed one), because a page
showing a certificate the published run did not issue is worse than no page. **The OUTCOME of
that check rides onto the page** as the certificate banner's `verification` field, so a page
that skipped it (`--no-cross-check`, a missing released certificate, or an `--alpha` rung
the released certificate does not record — it stores the operative rung only) is never
byte-identical to one that passed it; the banner's risk figure is likewise keyed
`answered_risk_on_calibration_sites`, because `report["estimated"]` is bootstrapped over
S_cal and not over the held-out pool the rest of the page is about. It writes ONE html
file, never into an experiment output directory (`out/`, `out-sens/`, `out-panel/`), and
**refuses any `--out` whose basename escapes the gitignored
`explain_dashboard_eicu*.html` pattern**: that page embeds record-level data by design,
and a gitignore miss is unrecoverable once pushed.

## Invariants — do not break these

- **`SPEC.md` is the binding contract.** Change it *first*, then the code. Its "Audit-lesson conformance" checklist must stay satisfied.
- **Frozen constants are pinned literally** by `tests/test_constants.py`. Any drift must fail CI. This is the lightweight pre-registration substitute — treat a red constants test as a design change, not a nuisance.
- **All third-party imports at module top level** (never inside functions) — enclave/reproducibility requirement.
- **Input validation is loud and at the boundary** (`certgate/validate.py`): strict bool labels, finite features/weights/scores, dense site IDs, site-disjointness assertion. `require_both_classes=False` is the *only* sanctioned relaxation, and only for target pools (an all-negative deployment batch is legitimate at ~9.5% prevalence).
- **The certified path validates its guarantee text** — the guarantee statement in `report.py` must keep the site-population-average estimand / between-site-dispersion / not-a-realized-count / baseline-only-shared-event / operative-rung-selection / concept-out-of-scope / BBSE-four-parameter-box clauses (2026-07-25 audit V1/V3/V13/V27 wording — the old "per-target-site" claim was FALSE and must never return). The exact string is frozen by `tests/test_report.py`; changing it is a SPEC change.
- **Determinism:** every experiment seeds from `constants.SEED`; identical inputs → byte-identical certificates. Preserve this. **The one sanctioned second root seed is `reliability.PANEL_SEED = 20260731`**, the ported sandbox's own: the panel self-seeds from `sha256` of its own input bytes rooted there, consumes no `_rng` draw, and no certified quantity descends from it. It is **renamed, never re-pointed** — pointing it at `constants.SEED` would move every panel interval and silently destroy the byte-exact equivalence with the `selective-reliability-panel` sandbox that `tests/test_reliability_panel.py::PANEL_DICT_SHA256` exists to carry. A red `PANEL_DICT_SHA256` is a design change, not a nuisance.
- **The panel bins `predict_proba`, never `score`.** Both drivers go through `reliability.panel_from_head`, which computes `p = head.predict_proba(x)` (the binned quantity) and `answered = head.score(x) >= tau_star` (the gate) itself; a caller never supplies `p`. Feeding `score` passes `validate_inputs` silently and produces a fully populated, meaningless panel, so the guard is structural, not documentary — which is also why `certgate/reliability.py` must stay a **numpy-only DAG leaf with no `from certgate ...` import of any kind** (it reaches `Head` only by duck typing; an AST test enforces both). Its bootstrap resamples **SITES** (`rng.integers(0, n_sites, n_sites)`), never records — a record bootstrap here would reintroduce inside the diagnostic layer the exact failure E7 exists to demonstrate.
- **The eICU extract is never committed and never redistributed.** PhysioNet DUA 1.5.0 forbids sharing access to the data, and our release policy under its disclosure-avoidance clauses extends that to *derived record-level* artifacts (correction of record 2026-08-10: the agreement's ten clauses carry no explicit derived-artifact term — the record-level rule is ours, and stated as such in the paper), so `.gitignore` denies `*.csv.gz` and the `eicu-*/` corpus directories by default, and every `run_eicu` write passes `assert_aggregate_only` (`EICU_FORBIDDEN_OUT_KEYS`, arrays capped at 512). `eicu_etl.py` is **stdlib + numpy only** and `eicu_mock.py` is **stdlib only** — no pandas, no pyarrow (audit F16); a source grep enforces it.
- **House helpers are bound by identity, never re-implemented** — `run_eicu` imports `_rm_on_pool`/`_per_site_exceed_frac`/`_rate`/`_write_csv` from `run_synthetic` and binds `_auc = eicu_etl._rank_auc`; `test_rm_helpers_are_the_synthetic_ones` pins every identity so a clone cannot drift silently.
- **The explain dashboard's design is documented, not incidental** (2026-07-31 redesign): `examples/DASHBOARD-DESIGN.md` records the bench-instrument system it was rebuilt into and its "do not regress" list (two registers in one file via `body.simple`/`body.adv` + `.simponly`/`.advonly`; the WCAG 2.1 AA floor; all five degraded builds laying out from one template), and `DASHBOARD-PRODUCT.md` the truth constraints (every number is real payload arithmetic; the caveats are product truth, not copy to tighten). The design lives in `_HTML_TEMPLATE` and is edited in the `certgate-dashboard-design/` sandbox — same template over a synthetic non-clinical fixture, spliced back by its `pipe_back.py` — so no design pass has to touch the restricted extract. **Both pages are rendered artifacts: a template edit reaches neither until it is re-run** (`python -m examples.explain_dashboard` for the committed demo, `python -m examples.explain_dashboard_eicu --data ./eicu-extract` for the local one).

## Gotchas

- `experiments/run_synthetic.py --only <E>` merges: the summary writer preserves existing `summary.md` sections for experiments it did not recompute (parsed from the `## E<n>` + fenced-json block format — see `_existing_summary_blocks`). Hand-edits to `summary.md` outside that exact format will not survive a partial rerun.
- E4 (site sweep to 400 sites × 200 draws) is by far the heaviest experiment; run it in the background and confirm the process is alive rather than trusting a run started across a session boundary.
- `run_eicu.py` owns `EICU-SUMMARY.md` and must **never** write `summary.md`: `run_synthetic._existing_summary_blocks`' regex is `^## (E\d)` — a *single* digit — so an `## EICU-…` section placed there is unparseable and gets silently clobbered on the next partial `--only` rerun.
- `EICU_SUMMARY_SECTIONS` is a frozen tuple and `_write_summary` emits **only** the names in it (`else: continue`): a block added to `_certification_blocks` without the tuple edit is silently dropped with no error. Appending (never inserting) is what keeps every pre-2026-08-01 `EICU-SUMMARY.md` parseable.
- **The panel rounds ONCE, at emit time (6 dp).** Never re-round its values into a summary block — E6's own keys carry 4 dp and the panel's carry 6 in the same JSON, and that asymmetry is the round-once invariant, not an inconsistency.
- `experiments/out/provenance.json` describes the **most recent run only**, including a partial `--only` rerun (`meta.selected` then names just the recomputed experiments). The authoritative per-experiment provenance is the `_run` stamp inside each `summary.md` block; do not read provenance.json as a whole-grid record.
- **The mock corpus cannot certify at its frozen default sizes.** At the frozen `EICU_MOCK_SIGNAL_B = 0.85` the outcome's Bayes-optimal AUC is 0.73, the fitted head reaches 0.60 out of sample, and the best margin an oracle ranking achieves is 0.0354 at α=0.10 against a `margin_floor(63, δ, 0.10)` of 0.0428 — `run_certgate` declines every rung on the default and `CERTGATE_EICU` arms, so those exercise the **decline branch only**. The decline is a property of the frozen corpus sizes, **not** of "any corpus size": `margin_floor` scales as `1/n_carrying`, the crossing point is `n_carrying = 77`, and the 900-hospital `CERTGATE_EICU_LARGE=1` arm reaches the CERTIFIED branch (pinned by E-20, `test_large_mock_reaches_the_certified_branch`). The real extract has also run the certified path end to end since 2026-07-31. Raising `EICU_MOCK_SIGNAL_B` toward `synth_fixture.SIGNAL_B = 2.0` remains a SPEC + `test_constants` decision, not a generator tweak.

## Files

**The frozen real-data protocol** is `EICU-PROTOCOL.md` — cohort predicates, the 161-feature deny-by-default allowlist, the 36-entry leak denylist, predictions P1–P7, failure criteria F-A–F-E, threats T-1–T-27, and the amendment log A1–A6. It was frozen *before* the extract was read; that ordering is the whole of its pre-registration value, so the protocol and the `test_constants.py` eICU pins must not be edited to match whatever the data says. The ingest hardening that protocol went through (the outcome-informative-missingness critical, the unlinked-APACHE aborts, the null-token gates, and the rest of E-9…E-22) is recorded in the protocol's amendment log and SPEC's conformance list — not restated here.

**The pre-extract freeze commit** is **`9f25b491b2554d0a4bd7aaaf44081c185d01715f`** ("freeze: eICU-CRD v2.0 protocol + constant pins, pre-extract", 2026-07-30 22:59 EDT), pushed to `git@github.com:Toepatella/certgate.git` on `main` — the pre-registration reference the paper cites, staging verified corpus-clean at commit time. The extract itself must still **never** be committed.

**Still not wired:** `experiments/panel_s2_tables.py` (read-only source of SI Tables S4–S5 — its stdout keys are still named `table6`/`table7` from the pre-renumber era — hard-asserts its replay against the released `E1_validity.csv`) and `experiments/panel_confusion_tables.py` (read-only source of SI Table S7) are not part of `run_synthetic.py`, so §3.10/SI A.3 scope the one-command claim to Figures 4–5, SI Figures S3–S9 and SI Tables S2–S3, S6 and S9. Two more read-only/side-car sources joined them 2026-08-21: `experiments/fig_eicu_abstention_drivers.py` renders main Figure 3 from the released `EICU_diagnostics.json` (no extract needed; prints the 20/13/10 driver counts the text quotes), and SI Table S10 comes from `run_eicu`'s POST-HOC `EICU-FAITHFULNESS` block run into `experiments/out-faithfulness/` (replicates=1, never `out/`; certificate byte-identical to the released one up to the timestamp).

Map: `README.md` scope & objectives · `METHODS.md` paper-ready methods · `SPEC.md` engineering contract · `EICU-PROTOCOL.md` frozen protocol · `PAPER-OUTLINE.md` venue fit (banner-marked) · `REDTEAM.md` / `CODE-AUDIT.md` / `REVIEW-FABLE.md` / `paper/review/` audit corpus · `certgate/` package (incl. `reliability.py`, the POST-HOC panel — descriptive, certifies nothing, a numpy-only DAG leaf) · `tests/` (incl. `test_reliability_panel.py`, whose `PANEL_DICT_SHA256` is the sole carrier of byte-exact sandbox equivalence) · `experiments/` (`eicu_mock.py` · `eicu_etl.py` · `run_eicu.py` · `comparators.py` · `panel_s2_tables.py` · `panel_confusion_tables.py` · `out*/` artifacts) · `examples/` (`explain_dashboard.py` committed synthetic demo · `explain_dashboard_eicu.py` the same page over the real extract, certificate cross-checked, output gitignored · `real_data_example.py` from_raw walkthrough · `DASHBOARD-DESIGN.md` + `DASHBOARD-PRODUCT.md`).
