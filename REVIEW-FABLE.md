# REVIEW-FABLE — pre-submission review (2026-07-23)

Three-phase autonomous review ahead of the Discover Computing submission (deadline 2026-10-05):
methods audit, real-data injection prep, literature novelty check. Builds on — does not redo —
REDTEAM.md (2026-07-22) and the real-data readiness audit (2026-07-23).

## Verdict

- **Methods sound? YES.** Zero confirmed defects across all four slices and the evidence runner. The R1 dual-endpoint fix independently re-verified. One skeptic-confirmed *test-coverage* concern (A-1) and eleven observation-grade notes; nothing requires a SPEC or code change before submission.
- **Real-data ready? YES.** All three known gaps closed and landed (SPEC-first): feature-width gate, first-ever `from_raw` end-to-end coverage (+ the API extension it forced), worked example. Suite 64/64 green; adversarial verifier PASS on 26/26 probes.
- **Novelty intact? YES, at medium threat.** No published or preprint work performs risk control or selective prediction with the cluster/site as the unit of independence. Three near-misses require repositioning the contribution as an intersection claim — guidance below, no headline threat.

Evidence discipline: every claim below is tagged with its source from this session — a direct file read, a quoted test/tool output, or a named agent's verified check. Claims resting on a single agent's report without independent re-verification are labeled *(agent-reported)*.

---

## 1. Methods audit

Process: four slice reviewers (high effort) + one synthetic-evidence runner ran in parallel; every defect/concern-grade finding went to a fresh-context skeptic instructed to refute it before acceptance. The original Reviewer B agent died on an output-format failure and was redone standalone; its redo produced the strongest numerical verification of the run.

### 1.1 Synthetic evidence chain (runner)

- **Suite green before any Phase 2 change:** `python -m pytest tests -q` → `53 passed in 22.96s` (quoted runner output; the ~23s vs. CLAUDE.md's ~4s reflects four concurrent reviewer processes — the post-change clean run in §2.2 took 3.85s).
- **All five CLAUDE.md headline claims match the recorded R=200 `experiments/out/summary.md`** (checked *before* the quick grid could overwrite it; directory backed up and byte-restored afterward, `out_dir_restored=true`):
  - E1: α=0.10 certify_rate 1.0 (200/200), mean coverage 0.9722, hard-violation rate 0.01 ≤ δ=0.05; α=0.05 certify_rate 0.0 at 208 sites.
  - E2: target prevalence 0.22; baseline α=0.10 hard-violates 0.485; BBSE hard-violation rate 0.0 with certify_rate 0.045 (9/200) — certifies *and* never violates, i.e. non-vacuous at R=200.
  - E3: verified mean answered risk 0.2022 > α, tilt-pushes flag true; hard-violation rate 0.83.
  - E4: α=0.10 certify rates [0, 0, 1.0, 1.0, 1.0, 1.0] over {60,100,150,208,300,400}; α=0.05 [0, 0, 0, 0, 0.3, 1.0].
  - E5/E6: per-site mean coverage 0.9191/0.8966/0.9063 by size bin, answered error 0.0294–0.0406 (all < 0.10); composition 3.9% / 5.9% / 6.3% (predicted / BBSE / oracle).
- **Quick grid (R=10) invariants all hold**, including the exact invariant *BBSE certify-and-violate = 0*. Caveat (runner observation): at R=10 the E2 BBSE arm declines every draw, so that invariant is satisfied vacuously at smoke scale — the demonstrative version (certifies 9/200 and still never violates) needs the full grid.

### 1.2 Slice verdicts

**A — core certificate (certify.py, pipeline.py, constants.py, report.py): sound.** 18 checks, 16 pass. Key verifications (Reviewer A, with numerics run this session): WSR bets on (α − Z) against H0: E[Z] ≥ α — the correct direction — with empirical boundary type-I 0.047 ≤ δ=0.05 at n=83, 4000 reps; λ predictable and capped so wealth stays positive (certify.py:86-91); atoms algebraically in [0,1] with E[Z] ≤ α ⟺ R_M ≤ α; empty-site neutral atoms Z=α are strictly power-diluting, never type-I-inflating; the Hole-1 regression (truncation certifies, influence-weighting refuses) passes; the fixed-sequence walk needs no multiplicity correction because the order is S_aux-only and stops at first failure. **The critical check — OR across baseline+BBSE — does not double-spend δ:** `_combine_alpha` lists a mode only if its own FWER-controlled certified prefix contains the deployed τ index, so each listed conditional guarantee holds separately (report.py:150-168, agent-reported logic trace; and see A-1 below for the test gap on exactly this code).

**B — BBSE label-shift path (shift.py, test_shift.py): sound; R1 fix independently confirmed.** 16 checks, all pass (Reviewer B redo, all numerics run this session):
- Inversion π_t = (q_t − c0)/(c1 − c0), ρ = odds(π_t)/odds(π_s) re-derived and matches shift.py:138-140.
- ρ-interval coverage: corner min/max over the box covered the true interior ρ in 20k boxes × 30 points — **0 violations** — because clipped ρ is coordinate-wise monotone in (c0, c1, π_s), so extrema sit at vertices. PI_CLIP preserves coverage (0 violations, 600k+ randomized trials).
- Percentile box: two-sided lvl/2 tails at lvl = δ_conf/3 (shift.py:114-116) → joint coverage ≥ 1 − δ_conf by Bonferroni×3. Correct.
- **R1:** on the production wmax=max(1,ρ) path, the sign-carrier (mean − α)·max(1,ρ) = A + ρB is affine to residual ~3.6e-17 with (A, B) ρ-free — verified *through* the M_INFLUENCE cap and empty-site neutral atoms, with the raw atom mean visibly kinked at ρ=1 (2nd-diff 3.7e-3). So the certifiable set is convex, dual-endpoint certification covers the interior, and each endpoint at full δ_bet is an intersection-union test (correctly not split). δ_conf + δ_bet = δ.
- Declines honest at every layer: fit → `certify_bbse` passthrough (shift.py:187-190) → `_combine_alpha` excludes any mode with tau_idx=None (report.py:158-160). Endpoint RNGs distinct/deterministic/order-independent. Walk order is aux+target-features only — no S_cal or target-label leakage; ρ_point in the *order* affects power, not validity.

**C — validation boundary and data path (validate.py, data.py, model.py): clean.** 10 checks, all pass. Highlights (Reviewer C, numerics run this session): loud checks fire in the SPEC order; `coerce_labels` never guesses; `site_sizes` always derived; `require_both_classes=False` exempts only the both-classes check and (by grep) is used only on target pools; the generator's label-shift path changes only the label marginal with p(x|y) exactly invariant (empirically confirmed), and the concept path genuinely tilts p(y|x) — E2/E3 are valid experiments. **Oracle non-leakage verified the strong way:** certified and estimated tiers are byte-identical across real / flipped / absent `oracle_target_y`; oracle labels reach only the diagnostic composition.

**D — explainability, reporting, harness (explain.py, report.py, harness.py): sound.** 14 checks, all pass. Highlights (Reviewer D, numerics run this session): φ_j = coef_j·z_j sums with the intercept to the logit at machine zero; the abstention equivalence (score ≥ τ ⟺ |logit| ≥ log(τ/(1−τ))) holds exactly for τ ∈ (0.5, 1) — 0 mismatches over 60k draws × 3 thresholds; composition's BBSE view uses the correct label-shift posterior multiplier odds_t = ρ·odds_s; `wilson_lcb` is the standard one-sided bound and `hard_violation` demands the 95% LCB exceed α (evidence-requiring, conservative); `exceedance_reference` computes strict P(K/n > α) with the integer-boundary guard verified; the guarantee statement carries every mandated clause (per-site / shared-δ / not-a-realized-count / concept-out-of-scope / BBSE-asymptotic).

### 1.3 Confirmed findings (skeptic-verified)

**No defects.** Two findings survived at concern grade or were downgraded:

- **A-1 [concern, skeptic CONFIRMED] — the OR-rule has no dedicated unit test.** `_combine_alpha` (report.py:150-168) — deploy = max-τ certifying mode, list only modes whose certified prefix contains the deployed index — is the single most important δ-accounting step, and it is exercised only via the in-distribution end-to-end test (tests/test_pipeline.py:32-45) where baseline and BBSE agree. The skeptic independently confirmed: no test imports `certgate.report`, no test constructs divergent certified prefixes; test_shift.py bypasses the OR entirely. A regression that listed a mode unconditionally would silently mis-attach an assumption tag and no current test would fail. *Recommended: one divergent-prefix unit test before submission.*
- **D3 [downgraded to observation by skeptic] — E3's poison verification is reported, not enforced.** `verified_mean_answered_risk` and the tilt-pushes flag are computed post-hoc (experiments/run_synthetic.py:284-297) and written to summary.md, but nothing asserts them before violation counting. The skeptic confirmed every factual claim (no assert, no pinned tilt constant, no E3 test) but judged severity overstated: the flag is published in summary.md and matches METHODS §8's "verified (by construction check)" wording, and current parameters verifiably poison (0.2022 > 0.10 at R=200). *Cheap hardening: gate the E3 violation count on the flag.*

### 1.4 Observations (no action required; none skeptic-escalated)

| ID | Note | Evidence |
|---|---|---|
| A-2 | BBSE guarantee's headline clause attributes the full 1−δ to "the draw of calibration sites" while δ_conf is over S_aux; the appended BBSE sentence corrects it — mild internal tension, already logged as N2-fixed | report.py:66-69 vs 79-82 *(agent-reported)* |
| A-3 | `margin_floor` docstring's "no valid level-δ test certifies below this" is a linearized zero-variance ideal — a loose (conservative-direction) floor, not tight; diagnostic-only, never a gate | certify.py:99-103; pipeline.py:51-54 |
| B-1 | The straddling-ρ test pins the *math* of the R1 fix but never calls `certify_bbse`; a regression to a single-endpoint loop would pass all of test_shift.py | test_shift.py:155-158 (calls `influence_atoms` directly) vs :72-75 *(agent-reported)* |
| B-2 | SPEC.md:155 percentile-level wording ambiguous between per-tail and total; code implements the sound (total, lvl/2-per-tail) reading — an anti-conservative reimplementation would also "satisfy" the sentence | shift.py:114-116 |
| B-3 | "Clip only WIDENS" (SPEC 158-162) is informal; the property that actually holds — and was verified 0/600k+ — is corner-interval *coverage* via coordinate-wise monotonicity | shift.py:135-137 |
| C-O1 | `densify_sites` orders by lexicographic str(), so numeric IDs get non-numeric dense numbering ('10' < '3'); cosmetic — labels carry originals | validate.py:94-98 |
| C-O2 | Missing-label sentinels (−1, "NA") are not auto-detected — only NaN/None raise; real-data users must clean sentinels first (now warned in the worked example, §2) | validate.py:68-85 |
| C-O3 | E6 draws its target pool with strict `require_both_classes=True`, inconsistent with E1–E5's target-pool convention; harmless at 40 sites | run_synthetic.py:453 vs :118,201,271,327,391 *(agent-reported)* |
| D1 | METHODS §6 writes φ_j = w_j(x_j − μ_j); correct only if w_j is the *raw-space* coefficient (= coef_j/sd_j). A reader using the standardized coef literally gets non-additive attributions — one clarifying clause recommended | METHODS.md:50 vs explain.py:48 *(agent-reported)* |
| D2 | SPEC.md:191 says composition does a "(c0,c1,q) inversion"; the code reweights by ρ_point (the inversion happened upstream in fit_bbse) — result correct, wording overstates | explain.py:132-136 *(agent-reported)* |
| D4 | `provenance()` hashes raw bytes only (no dtype/shape); negligible risk given the pipeline fixes both | report.py:46-48 *(agent-reported)* |
| R-1 | E2's "BBSE never certifies-and-violates" is vacuous at R=10 (all declines); demonstrative only at R=200 (9 certifications, 0 violations) | quick-run vs R=200 summary.md, quoted in §1.1 |

---

## 2. Real-data injection prep (landed in repo)

All three gaps closed, SPEC updated **before** code in each case. Implemented by one agent, then independently attacked by a fresh-context verifier that had not seen the implementation. **Verifier verdict: PASS — 26/26 probes, zero SPEC-code mismatches, zero invariant violations.**

### 2.1 What changed

| File | Change |
|---|---|
| SPEC.md | Gate **2b** (feature-column alignment) added to the pipeline gate list; `coerce_labels` / `from_raw` signatures re-pinned with rationale; new Tests bullet |
| certgate/pipeline.py | Loud gate after finiteness: `target_x` must be 2-D with `train.d` columns, and `aux.d`/`cal.d` must equal `train.d`; `ValueError … (reason=feature-width-mismatch)`; docstring gate list updated (verified at pipeline.py:119-128, docstring :8-14, SPEC.md:243-251) |
| certgate/validate.py | `coerce_labels(…, allow_absent_positive=False)`: opt-in all-False when the positive label is absent and exactly one other value observed; NaN/None/>1-distinct rejections still fire; strict default byte-identical. `from_raw(…, *, require_both_classes=True)` (keyword-only), wired to both `make_cohort` and `coerce_labels` (validate.py:188-192) |
| tests/test_realdata_path.py | **New — the first test ever to invoke `from_raw`.** 11 tests: raw string-label and {1,2}-int round-trips through `from_raw` → `run_certgate` (certifies α=0.10, partition sums to n_target), wrong-width gate, all-negative target-pool path, `coerce_labels` opt-in contract |
| examples/real_data_example.py | Runnable CSV → certificate walkthrough: stdlib `csv` (no new deps), split-by-site with the why stated loudly, certification without oracle labels, abstention explanation, honest-decline demo, sentinel warning |
| README.md | Short "Real data" subsection pointing at the example |

Design note surfaced by the work: **deployment target pools never need `from_raw`** — `run_certgate` consumes only `target_x`; the all-negative relaxation exists specifically for attaching *oracle* labels in the harness path. The example is built around that distinction.

### 2.2 Verification evidence

- `python -m pytest tests -q` → **`64 passed in 3.85s`** (up from 53; quoted verifier output). `tests/test_constants.py` run alone: 17 passed, still pins every frozen constant literally — untouched, no weakening.
- Adversarial probes (all quoted from the verifier's table): 1-D / 3-D / ±1-column / **0-column** / list-of-lists `target_x` all raise the reason-tagged error — no probe produced a raw numpy broadcast error; cross-cohort aux/cal width checks fire; gate order verified as SPEC 2 → 2b → 4 (non-finite beats width; width beats pool-too-small); `require_both_classes` positional attempt → TypeError; strict paths byte-equivalent to old behavior; all-negative oracle path flows to a report with the partition summing to n; two identical runs → equal certified tiers (determinism invariant held).
- Invariants: no function-local third-party imports in any changed file; example imports only stdlib + numpy + certgate; example exits 0 with a certified α=0.10 rung (τ=0.750, coverage 0.944) and cleans up its temp dir.

---

## 3. Literature novelty check

Process: four searchers over adjacent literatures + adversarial synthesizer. The first-pass conformal/risk-control searcher returned a degenerate placeholder and was **fully redone** (12 queries + abstract fetches); the redo also independently verified the two top-threat 2026 preprints exist as described (arXiv abstract pages fetched: 2606.08517, Yu & Liu; 2606.15153, Zhou & Wang — both record-level).

### 3.1 Verdict

**Novelty intact; threat level medium.** No single paper anticipates the combination, and — the decisive check — **no work was found performing risk control or selective prediction with the cluster/site as the exchangeable unit** (S2 redo, 12 queries across the RCPS/LTT/CRC, hierarchical-conformal, and selective-risk-control lineages). The two capabilities exist only in separate silos: cluster-as-unit inference for *prediction-set coverage* (Dunn–Wasserman–Ramdas JASA 2023; Lee–Barber–Willett 2025), and finite-sample *selective risk control with honest decline* only at the record level (SCRC 2512.12844; the Joint Certificate 2606.08517; LTT; RCPS).

Headline threats (all manageable, none a stop-condition):
1. **Assembly-foreseeability:** DWR 2023 + any 2025-26 selective-risk-control paper together span the two halves. The paper must show the assembly is non-trivial — data-dependent selection at cluster counts, the influence-weighted estimand, decline behavior at realistic site scales. The E4 frontier (α=0.05 simply unreachable at 208 sites, and the method says so) is the evidence.
2. **arXiv 2606.15153** independently publishes the *diagnosis* (record-level selective certificates overrun 9–30% under grouped deployment) and the negative-control validation philosophy. Cite it as the published problem CertGate constructively answers; stop claiming the validation philosophy itself as novel.
3. **arXiv 2606.08517** is the structural twin on certificate shape (selected-risk bound + acceptance floor + honest decline), i.i.d. records. Cite prominently, not defensively; monitor for a hierarchical follow-up before the October deadline.

### 3.2 Related-work delta table (synthesizer output, verified entries marked)

| Closest work (venue+year) | What they guarantee | What CertGate does differently | Threat |
|---|---|---|---|
| Joint Finite-Sample Certificate for Adaptive Selective Conformal Risk Control (arXiv 2026, 2606.08517) ✔fetched | Finite-sample certificate bounding selected-case risk + acceptance floor + honest decline, i.i.d. records | Cluster as the independence unit; BBSE mode with cluster-robust uncertainty; explainable abstention; falsifiable controls | High |
| Dunn, Wasserman & Ramdas, Distribution-Free Prediction Sets for Two-Layer Hierarchical Models (JASA 2023) ✔fetched | Distribution-free prediction-set coverage with the group as the exchangeable unit | The cluster-as-unit backbone — but sets, not a selective-risk gate; must be cited as the ancestor of the core move | High |
| False Sense of Safety in Selective Signal Classification (arXiv 2026, 2606.15153) ✔fetched | Audit: certified record-level selective-risk rules hold under exchangeable splits, overrun 9–30% under grouped deployment; negative-control protocol | Diagnoses the exact failure; CertGate constructs the cluster-level certified gate that resolves it | High |
| Lee, Barber & Willett, Distribution-free inference with hierarchical data (ACM JDS 2025, arXiv 2306.06342) ✔fetched | Hierarchical exchangeability for conformal prediction and jackknife+; coverage only | The direct DWR follow-up — still never crosses into risk control or selection | High (must-cite) |
| Si et al., PAC Prediction Sets Under Label Shift (ICLR 2024) | Finite-sample 1−δ coverage under label shift via confusion-matrix weight-uncertainty propagation | Same machinery pattern for prediction sets under i.i.d. records; CertGate targets answered-set error with cluster-robust weight uncertainty | Medium |
| Federated Conformal Risk Control via Risk-Curve Shrinkage (arXiv 2026, 2606.20115) ✔fetched | Per-site shrinkage-regularized CRC (in-expectation), clinical | Sites first-class but heuristic shrinkage, no finite-sample cluster-unit certificate, no selection/shift/explanations | Medium |
| Deployment Audit of Release-Side Risk in Conformal Triage under Prevalence Shift (arXiv 2026, 2605.20956) | Audit concluding marginal coverage cannot certify release-side risk under prevalence shift | Asks CertGate's exact question and concludes it cannot certify; record-level | Medium |
| Conformal selective prediction with cost-aware deferral for clinical triage under shift (Sci. Reports 2026) *(agent-reported; auth-walled, characterized from indexed abstract)* | Finite-sample set coverage with cost-aware deferral; importance-weighted shift variant | Coverage per record vs. cluster-certified answered-error; demographic (not site) strata | Medium |
| SCoRE: Conformal Selective Prediction with General Risk Control (arXiv 2026, 2603.24704) | Finite-sample selective deployment risk via e-values, record-exchangeable | No cluster unit, label-shift mode, explanations, or controls | Medium |
| Selective Conformal Risk Control (arXiv 2025/26, 2512.12844) ✔fetched | Risk control on the selected subset, record exchangeability | Same answered-subset target, none of the cluster/shift/explanation components | Low |
| Geifman & El-Yaniv, Selection with Guaranteed Risk (NeurIPS 2017) | Selective risk ≤ target w.p. 1−δ, i.i.d. sample | The lineage anchor for the guarantee phrasing | Low |
| Audited Selective Verification for N-1 Thermal Contingency Screening (arXiv 2026, 2607.13221) ✔fetched | (α,δ) finite-sample cert on violation rate among trusted/skipped set under deployment shift — power systems | Structural twin in another domain; per-window unit, online auditing, not cluster exchangeability | Low (cite as parallel) |
| TRIPOD-Cluster (BMJ 2023) + internal–external CV (J Clin Epi 2021) | Cluster-as-unit reporting/validation guidance for clinical models | The clinical culture of site-as-unit — point estimates, no certificate | Low |
| Podkopaev & Ramdas, Distribution-free UQ under label shift (UAI 2021) | Coverage/calibration under label shift, record level | Foundational; no answered-error certificate or cluster unit | Low |
| Artelt & Hammer (2022) + IFAC (arXiv 2025) + L2loRe (2025) | Explanations of reject/abstain decisions, no statistical guarantee | CertGate's delta is exact attributions *attached to a certified gate* | Low |

### 3.3 Repositioning (recommended, none fatal)

1. **Lead with the intersection, not the ingredients.** State that certified selective risk (Geifman–El-Yaniv → SCoRE/2606.08517), cluster-as-unit distribution-free inference (DWR 2023; Lee et al. 2025), and label-shift guarantees with propagated weight uncertainty (Si et al. 2024) each exist — and that CertGate is the first working certificate at their intersection, plus the specific obstacles the intersection creates (influence-weighted estimand at cluster counts, cluster-robust BBSE box, honest-decline behavior at realistic site scales; E4 is the exhibit).
2. **Demote "verified-falsifiable negative controls" from headline contribution to validation-rigor practice**, citing 2606.15153 as independent convergent methodology and as the published diagnosis this paper answers — it converts a novelty overlap into the motivation section.
3. **Scope the explainability claim precisely:** "exact linear attributions for answer/abstain decisions attached to a certified gate" (citing Artelt & Hammer, IFAC) — the attachment is the claim, not explainable rejection per se.

### 3.4 Evidence caveats

- ✔fetched = abstract page independently fetched this session. Unmarked entries rest on search-result snippets plus one agent's characterization — **spot-check titles/authors/venues against the actual papers while writing the related-work section** (the synthesizer flagged incomplete author metadata on several 2026 arXiv entries; the two top threats were the ones explicitly re-verified).
- The S1/S3/S4 searchers each ran ≥6 queries; S2's first pass was degenerate and fully redone with 12. Residual risk: a cluster-unit risk-control paper invisible to all 30+ queries across four agents — low, and worth one final search the week before submission given threat #3.

---

## 4. Recommended follow-ups

1. **[DONE 2026-07-24] Two regression tests** (the only concern-grade item): divergent-prefix unit tests for `_combine_alpha` (A-1, tests/test_report.py) and a `certify_bbse`-level dual-endpoint test (B-1, tests/test_shift.py) so the R1 code path — not just its math — is pinned. Both mutation-verified: the tests fail under list-all-modes, lo-only, and hi-only regressions. Suite 69/69.
2. **[DONE 2026-07-24] E3 enforcement** (D3): a de-poisoned tilt now aborts E3 loudly (`reason=e3-control-not-poisonous`) before any output is written; SPEC.md E3 bullet updated first. Verified both ways (intercept-0 tilt aborts with no CSV; real tilt unchanged).
3. **Wording batch** (30 minutes, all observation-grade): SPEC.md:155 percentile phrasing (B-2); "clip only widens" → corner-coverage phrasing in SPEC/shift.py (B-3); METHODS.md:50 clarify w_j is the raw-space coefficient (D1); soften `margin_floor` docstring (A-3); SPEC.md:191 composition wording (D2); E6 target-draw consistency (C-O3).
4. **Novelty hygiene:** re-run one cluster-unit-risk-control search in late September; verify unfetched citations while drafting related work.

## Appendix — process notes

~16 agents total: Phase 3 = 4 searchers + synthesizer + 1 S2 redo; Phase 1 = 4 reviewers + runner + 2 skeptics (A-1 CONFIRMED, D3 DOWNGRADED) + 1 Reviewer-B redo after a structured-output failure; Phase 2 = 1 implementer + 1 fresh-context verifier. Reviewer B's observation-grade findings did not trigger skeptics per protocol (skeptics reserved for defect/concern). `experiments/out/` was backed up before the quick grid and byte-restored (sha256-checked). Full agent transcripts live under the session's workflow/task directories.
