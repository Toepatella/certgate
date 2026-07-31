# Revision plan — CertGate, *Discover Computing* Collection submission

Working document for the authors. Every one of the 282 surviving findings appears below, by ID.

**How to read this.** Findings are bundled into numbered work-items. A work-item lists the IDs it closes; **an ID inherits its work-item's rank**. Ranks:

- **S1** — would sink the paper or trigger desk rejection at this venue. 79 IDs, 14 work-items.
- **S2** — forces major revision, or threatens the 2026-10-05 deadline. 170 IDs, 44 work-items.
- **S3** — polish. 33 IDs, 8 work-items.

The 15 PLAUSIBLE findings are marked `(PLAUSIBLE — settle by: …)` carrying the single check the office specified. Everything else is CONFIRMED.

Referee key: **DS** desk screen · **R1** statistics · **R2** clinical · **R3** XAI · **R4** reproducibility (repo access) · **R5** forensic.

---

# S1 — must change or the paper does not run

### S1-1 · Restate the certified estimand to match what is proved
**Closes:** `R5-01` (R5) · `R1-01` (R1) · `DS-47` (DS) · `R5-63` (R5) · `R1-03` (R1) · `R5-58` (R5)

**What.** R_M as displayed in §3.3 is a ratio of sums over sites; the betting test in §3.4 tests a statement about the site-population mean. §3.1 and §3.7(1) claim the bound holds "at a new target site". Supply the transport step or narrow the claim. Also state the index set of *c* — A.1(ii)'s "E[R_M] is a ratio of expectations" currently reads as a cross-site population quantity (`DS-47`). `R1-03`: the equivalence "E[Z] ≤ α ⟺ R_M ≤ α" is asserted between an expectation and a realized-site quantity; make the parameter/realization level explicit, since §3.7(3) and §5.1 both turn on it. `R5-63`: E1's targets are drawn *exchangeably* with calibration, so no adversarial per-site case is ever tested — say so. `R5-58`: the only per-site evidence in the paper is three bin means over 40 sites with no dispersion.

**Where.** `paper/draft.md` §3.1, §3.3, §3.7 clause (1), §5.1, Appendix A.1(ii); new per-site distribution panel in §4.2 and §4.7.

**What satisfies.** Either a derivation from the site-population bound to a single new site with its stated assumption, or — expected — §3.7(1) rewritten as "It bounds the influence-weighted answered-set risk averaged over the site population; it is not a per-site guarantee", plus a §5.1 sentence conceding what that costs. Plus, for E1 and E6, the per-site answered-error distribution with minimum coverage, maximum answered error, and the count of sites exceeding α.

---

### S1-2 · State the sampling assumption on calibration sites; repair A.1(iii)
**Closes:** `R5-02` (R5) · `R1-02` (R1) · `R5-55` (R5)

**What.** Under A.1(ii)'s design-conditioning the atoms have site-specific means μ_c, so A.1(iii)'s conditional inequality evaluates to 1 + λ_t(α − μ_t), which exceeds 1 at any site with μ_t < α even when the average satisfies H₀. The supermartingale property fails atom-wise. No i.i.d.-or-exchangeable assumption on calibration sites is stated in §3.1, §3.3, §3.4, §4.1 or A.1 — and §6.1 concedes a temporal dependence that would break it. Use the office's realizable counterexample: λ = (1.0, 0.5) with (α − μ₁, α − μ₂) = (+0.5, −0.5) gives E[K₂] = 1.125 > 1. (The referee's own (1, 0.01) is not producible by your λ schedule; do not respond to that version.)

**Where.** `paper/draft.md` §3.4 (null statement), Appendix A.1(ii)–(iii), §6.1.

**What satisfies.** A numbered assumption block naming the conditioning regime and the exchangeability/i.i.d. condition on calibration sites, an A.1(iii) that derives the supermartingale property *from* it, and either a quantification of level inflation under §6.1's conceded common-shock correlation or an explicit sensitivity note in its place.

---

### S1-3 · Withdraw or condition the exact-Shapley identification
**Closes:** `R3-01` (R3) · `R1-18` (R1) · `R5-12` (R5) · `R4-15` (R4) · `R5-60` (R5)

**What.** φ_j = w_j(x_j − μ_j) is the Shapley value of a linear model under the interventional value function, or under the conditional one *given feature independence*. Neither is stated. §4.1's generator makes features 0–3 marginally correlated (≈0.09 at π = 0.095, sep = 2.2, equal loading); R4 confirmed this from `data.py` (`x|y ~ N(±(sep/2)v, I)` with v on coordinates 0–3). "Exact"/"genuine" appears attached to attributions nine times, all unqualified. Fix honestly: the distortion is real but modest — do not oversell the correction either.

**Where.** `paper/draft.md` §3.8 (both sentences), §4.6 ("genuine Shapley values, not sampled approximations"), Abstract, §1 contribution 3, §2.4, §6.1.

**What satisfies.** One sentence naming the value function invoked; one sentence stating the condition under which the identity holds; the empirical correlation matrix of features 0–3 reported in §4.6 or an appendix; and, if the interventional function is invoked, an explicit statement that the attributions then answer a different question than a conditional reading. Cite Štrumbelj & Kononenko and Kumar et al. (ICML 2020) — see S2-33.

---

### S1-4 · Replace the n=2 abstention-driver result
**Closes:** `DS-11` (DS) · `DS-50` (DS, **PLAUSIBLE — settle by:** decide whether §4.6 ¶1's "declining 2" satisfies the disclosure; if yes, the count limb dies and only the "systematically"/caption limbs survive) · `R1-30` (R1) · `R2-19` (R2) · `R3-25` (R3) · `R4-10` (R4) · `R3-06` (R3) · `R4-46` (R4)

**What.** §4.6's cohort statistic (mean |φ₀| 0.868 answered vs 1.722 declined, gap −0.854, gap ranking [0,3,2,1,…], "systematically", "dominant systematic abstention driver") is computed over **two** declined cases, at τ* = 0.55 — the exact minimum of the 23-point grid, where coverage is 200/202 = 0.990 and declines barely occur. `R3-06` adds the inferential objection that survives any amount of disclosure: a case is declined when signed contributions cancel, so a large mean |φ_j| on declined cases identifies a feature that had to be *offset*, not one that caused the abstention. `R3-25`: the Figure 5 caption carries the claim with no denominator and travels alone.

**Where.** `paper/draft.md` §4.6, Figure 5 caption; `experiments/run_synthetic.py::run_E5`.

**What satisfies.** E5 re-run at a certified operating point with a material decline rate, replicated (R ≥ 200), reporting the answered-vs-declined attribution gap with an interval; the denominator stated in both §4.6 and the Figure 5 caption; "driver" replaced with a claim the statistic licenses, or a signed/decomposition statistic that does license it. A null result is acceptable and should be reported as one.

---

### S1-5 · Disclose `sep = 1.8` and report E2/E3 at 2.2
**Closes:** `R4-01` (R4) · `R4-36` (R4) · `R4-43` (R4) · `R4-02` (R4)

**What.** `experiments/run_synthetic.py:40` sets `SHIFT_SEP = 1.8` (comment: *"realistic head so shift bites"*), consumed at `:195` (run_E2) and `:264` (run_E3). §4.1 states `sep = 2.2` once, for the whole Results section; E1/E4/E5/E6 use it. The two experiments running the undisclosed value produce the 48.5% and 83% headlines. `R4-02`: `tests/test_constants.py` pins `certgate.constants` only — `ANCHOR_SITES`, `SHIFT_SEP`, `SHIFT_BASE`, `CONCEPT_INTERCEPT`, `FULL_SWEEP`, `QUICK_SWEEP`, the inline `R = 10 if quick else 200` and every `SimConfig` default are unpinned, so the parameter sits outside the mechanism §3.2 offers as protection against tunable pipelines.

**Where.** `paper/draft.md` §4.1 and §4.3/§4.4 (per-experiment generator statement), §3.2; `tests/test_constants.py`; `experiments/run_synthetic.py`.

**What satisfies.** Per-experiment disclosure of every generator parameter that differs from §4.1's baseline; a sensitivity table reporting E2's and E3's certify, decline, hard-violation and exceedance rates at sep = 2.2 alongside 1.8; a stated answer to when 1.8 was chosen relative to seeing results at 2.2; and `test_constants.py` extended to pin the experiment-defining constants.

---

### S1-6 · Supply the figures — embedded, called out, and repaired
**Closes:** `DS-05` (DS) · `R1-42` (R1) · `R3-24` (R3) · `R5-15` (R5) · `R4-18` (R4)

**What.** The manuscript contains six figure captions (lines 298–310) and no images: zero `![`, `.png`, `.pdf`, `.svg` or `includegraphics` matches, and the string "Figure N" occurs nowhere outside the Figures section, so no figure is called out in §1–§6 or the appendices. Separately, R4 opened the PNGs in the repository and found three defective: `E3_concept_shift.png` title truncated mid-word ("…negative control (certificate shou") with axes on half the canvas and the "no certificates" annotation in the blank margin; `E1_validity.png` with a single x-tick and the α = 0.05 annotation rendered outside the axes, so the caption's claim that α = 0.05 issues no certificates is not visually shown; `E2_label_shift.png` with a zero-height BBSE bar visually identical to absence, which is that same figure's encoding for "no certificates". Cause: `ax.text(...)` in data coordinates at categories whose bar is `np.nan` (`:170-173`, `:246-250`, `:316-319`).

**Where.** `paper/draft.md` §4.2–§4.7 (in-text callouts) and the `# Figures` section; `experiments/run_synthetic.py` plotting blocks.

**What satisfies.** Six figures embedded in the submitted package, each called out at first use in the body; the three rendering defects fixed (annotations in axes coordinates, full titles, explicit zero-vs-absent encoding); captions that describe panel content and stand alone with their denominators.

---

### S1-7 · Deposit code and data; add a Code availability section
**Closes:** `DS-07` (DS, narrowed) · `DS-27` (DS) · `R1-36` (R1) · `R2-40` (R2) · `R4-17` (R4) · `R4-40` (R4) · `R5-40` (R5)

**What.** Data availability reads "publicly available at [CODE REPOSITORY URL — to be added]", and there is no Code availability section at all (back matter runs Acknowledgements → Data availability → Funding → Author contributions → Ethics → Consent → Competing interests). Eleven checkable claims terminate at that placeholder: §3.10's determinism, A.3's pinned environment and one-command grid, §4.1's `data.py` and byte-identical certificates, §5.5's `from_raw` loader and worked example, §4.4's two code identifiers. R4 verified the repository root has **no LICENSE, no COPYING, no pyproject.toml, no setup.py, no setup.cfg, no `.git`**, and six dangling paths (`README.md:3` → `../audit/readiness-report.md`; README → `../testbed/`, `../PROTOCOL.md`; `certify.py:4`, `shift.py:8`, `data.py:3`, `report.py:87`). The office ruled the placeholder is *not* a criterion-4 identity field; and the substance survives even if the URL is treated as one.

**Where.** `paper/draft.md` back matter; repository root.

**What satisfies.** A DOI-minted deposit (Zenodo or equivalent) with an OSI licence, packaging metadata, version control, and the dangling `../testbed`/`../audit` references removed or vendored; the URL and DOI in both a Data availability and a new Code availability statement.

---

### S1-8 · Delete the missingness-encoder limitation
**Closes:** `R5-30` (R5) · `R4-03` (R4)

**What.** §6.1 line 242 describes "the frozen encoder's imputation-and-indicator scheme". R5 found from the manuscript that `encoder`, `imput*`, `indicator` and `missing` match that line and nothing else — no encoder in §3, none in §4.1's model description, and §3.2's inventory of fitted objects is "the head, the walk order, the confusion-matrix statistics". R4 found from the code that no such component exists and the actual behaviour is the *inverse*: `validate.py:139` raises on non-finite features, `pipeline.py:109-112` raises `reason=nonfinite-features`. Two referees from opposite directions on a fictional component, in the section the paper most relies on for credibility.

**Where.** `paper/draft.md` §6.1.

**What satisfies.** The sentence deleted, and replaced — if a missingness limitation is wanted — with the true one: the pipeline rejects non-finite features outright, so real-data application requires an imputation step the paper does not specify.

---

### S1-9 · Retract "published"; attribute the preprint base in text
**Closes:** `R5-18` (R5) · `DS-59` (DS) · `R1-20` (R1) · `R2-23` (R2) · `R2-69` (R2) · `R4-34` (R4)

**What.** `zhou2026falsesense` is `@misc`, arXiv:2606.15153, no venue — and is called "a **published** diagnosis" (§1 contribution 4) and "the **published** warning" (§4.4). Seven of thirty-one entries are unrefereed 2025–26 arXiv `@misc`: `yu2026joint`, `zhou2026falsesense`, `triage2026audit`, `fedcrc2026`, `score2026`, `scrc2025`, `thermal2026audit`. Two carry "submitted to" notes. Between them they carry the motivating 9–30% figure (§2.4), the closest-competitor identity on which contribution 1's novelty delta rests (§2.1), and §5.4's federated positioning. Nowhere is any of them attributed as a preprint. (Note: the correct denominator is **31**, not 30; several reports say 30/6 and the office corrected them.)

**Where.** `paper/draft.md` §1 contribution 4, §2.1, §2.4, §4.4, §5.4; `paper/references.bib`.

**What satisfies.** "Published" removed; each of the seven flagged in text as a preprint at first use; the 9–30% figure attributed as a preprint claim rather than stated as established fact; the office to spot-check arXiv 2606.15153, 2605.20956 and 2606.08517 before acceptance.

---

### S1-10 · Repair the real-data justification
**Closes:** `R1-16` (R1) · `R2-26` (R2) · `R5-10` (R5) · `R5-64` (R5) · `DS-53` (DS)

**What.** §5.5's "Real data cannot supply that ground truth, which is what makes it unable to validate a validity claim" is refuted by §3.9: the hard-violation criterion — the number required to stay ≤ δ, the number reported for E1, E2 and E3 — consumes only realized answered errors and a Wilson lower bound, both computable from a labelled retrospective multi-site cohort. The oracle is used in the paper for one thing only: verifying E3's poison. `R5-64` shows the four legs (this overreach; the only comparator being CertGate's own mode; realism resting on a reporting checklist; §4's "cannot be falsified" sentence) compose into a rationale for never testing on real data at all. `DS-53`: §5.5 calls the route "concrete" and application "ongoing work" without saying whether a cohort was sought, obtained or blocked.

**Where.** `paper/draft.md` §4 opening, §5.5.

**What satisfies.** The claim narrowed to what §4's opening actually supports (real data cannot supply the true *parameter*), an explicit statement that the §3.9 violation protocol *is* runnable on a labelled retrospective cohort, and one sentence on the concrete status of real-data access.

---

### S1-11 · Report the 0/9 interval and write out the BBSE diagnostics
**Closes:** `R1-09` (R1) · `R2-03` (R2) · `R5-06` (R5) · `R4-08` (R4) · `DS-57` (DS) · `R4-07` (R4) · `R4-37` (R4) · `R4-44` (R4)

**What.** §4.3's "conditioning on the 9 draws that did certify, the hard-violation rate among them is 0.0" carries no interval, in the same paragraph as four correctly computed ones, against §4.1's promise. The exact Clopper–Pearson upper bound on 0/9 is **0.3363** — 6.7× δ. R4 additionally found no Clopper–Pearson code anywhere in the release (`grep scipy|clopper|beta.ppf` → zero), so all four published intervals were computed off-artifact. And the mode cannot be diagnosed: `E2_label_shift.csv` shows 191 declines at α = 0.10, **all** `failsafe`, with zero `bbse-ill-conditioned`, zero `bbse-degenerate-bootstrap` and zero `bbse-misspecified` — the three declines §3.6 devotes a paragraph to never fire in any reported experiment. `fit_bbse` computes `c0_ci`, `c1_ci`, `pi_s_ci`, `gap_lo`, `rho_lo/hi/point`, `n_boot`, `n_attempts` into `BBSEFit.diagnostics` and `run_synthetic.py` writes none of them. Structurally, `certify_bbse` must reject at both endpoints at `BBSE_DELTA_BET = 0.025` — two tests at half the baseline's budget on 83 clusters with a Bonferroni-widened ρ interval — so "correctly calibrated refusal" and "underpowered mode" predict the same 95.5%, and the artifact as released cannot arbitrate.

**Where.** `paper/draft.md` §4.3, Abstract, §1 ¶5; `experiments/run_synthetic.py` CSV field lists; new appendix table.

**What satisfies.** The [0, 0.3363] interval printed beside the 0/9 rate; the BBSE diagnostics serialized into `E2_label_shift.csv` (ρ̂, ρ interval, `gap_lo`, failing endpoint, decline reason); the single-endpoint-at-full-δ comparison run and reported, which is the one measurement separating correct refusal from underpowering.

---

### S1-12 · Earn the explainability contribution (Collection-fit condition)
**Closes:** `DS-09` (DS) · `DS-58` (DS) · `DS-22` (DS) · `R1-69` (R1) · `R2-68` (R2) · `R3-13` (R3) · `R5-67` (R5) · `R5-33` (R5) · `R1-39` (R1) · `R4-47` (R4, **PLAUSIBLE — settle by:** weigh R4-47 against R3's explainability findings rather than treating it as an independent fit clearance; its anchors do not address the demotion passages)

**What.** The Collection's central emphasis is explainability. The paper demotes it in its own voice — §3.8 "a supporting capability the linear head makes nearly free", §1 contribution 3 "supports the certificate above rather than standing as an independent method" — and delivers it as one methods subsection, one experiment on two declined cases, and one exactness claim that is wrong as stated. `R5-33`/`R1-39`: explainable abstention is one of §2's four literatures and is dropped from both the §1 three-count and the §6 three-count. `DS-09`: no faithfulness metric, no comparator explanation method, no clinician assessment anywhere; §6.1's six limitations are all statistical. `R2-68`: fairness → one sentence; calibration → no assessment of any kind; human-centered design → zero occurrences; auditability → no certificate exhibit. `DS-58`/`DS-22`: §2.4 volunteers that the certificate shape "is not specific to medicine", and §Ethics states the work involves no patient data.

**Where.** `paper/draft.md` §1 (contribution 3 and the three-count), §2.4, §3.8, §4.6, §5.3, §6, §6.1, Keywords.

**What satisfies.** (a) A faithfulness/fidelity assessment of the attributions against at least one comparator explanation method; (b) one worked vignette with plausibly named clinical features and an EHR-facing abstention message a clinician would receive; (c) at least one explanation-facing item in §6.1; (d) explainable abstention restored to §1's and §6's own literature counts; (e) engagement with the *fairness* content of `ifac2025abstainexplain` (see S2-36); (f) the two demotion sentences defended or removed. If (a)–(f) are not attempted, the honest alternative is retitling and resubmitting outside this Collection.

---

### S1-13 · Add a comparator
**Closes:** `DS-01` (DS) · `R1-12` (R1) · `R5-11` (R5)

**What.** No record-as-unit certificate and no external method appears in any of E1–E6. E2's "uncorrected baseline" is CertGate's own exchangeable assumption mode — still site-as-unit — so the motivating record-level failure enters only by citation (§1 ¶4, §2.4, §4 opening). `R5-11`: §5.2's "a property of the available cluster count, not of the method" and §6's "obstacles that appear only in combination" are comparative claims with no comparator; E4 sweeps CertGate's own cluster count and cannot separate a property of the data from a property of this linearized betting construction. (Do not respond to "no baseline of any kind" — that clause was corrected.)

**Where.** New subsection in §4 (or extension of §4.2/§4.3); §1 contribution 1; §5.2; §6.

**What satisfies.** A record-as-unit selective-risk certificate run on the same E1 draws under the same §3.9 screen, with its hard-violation rate reported beside CertGate's — this is the single cheapest high-value experiment in the plan. Optionally one external comparator from the named list (hierarchical conformal, RCPS/LTT, BBSE without the uncertainty box). Comparative language in §5.2 and §6 narrowed to what the comparator supports.

---

### S1-14 · Rewrite the abstract and title claims
**Closes:** `DS-56` (DS) · `R5-04` (R5) · `R5-03` (R5) · `R1-45` (R1) · `R5-44` (R5) · `DS-23` (DS) · `R2-04` (R2)

**What.** `DS-56`: the abstract's two strongest sentences rest on its two thinnest bases — the record-level premise is carried entirely by a preprint and never reproduced in your own oracle-equipped harness, and "the corrected mode never does" is 0/9 with an omitted upper bound of 0.3363. `R5-04`: the abstract's guarantee sentence carries none of §3.7's five clauses. `R5-03`/`R1-45`: §3.6 claims "every guarantee statement carries that caveat"; the title and the abstract do not, and the title conjoins "finite-sample" with label-shift robustness. `R5-44`: the title says "clinical risk models"; the abstract discloses "synthetic" 190 words in. `DS-23`: "hard-violation", "mean coverage" (ambiguous across three senses — see S2-32) and "budget" (used for both α and δ in one paragraph — see S3-6) are undefined; the abstract is 240 tokens, at a typical Springer cap, so the fix is **substitution, not addition**. `R2-04`: the abstract omits "influence-weighted" from the estimand; §1 contribution 1, §3.1, §3.3 and §5.1 all carry it, so the omission is confined to the abstract and §1's framing sentence.

**Where.** `paper/draft.md` line 1 (title), line 11 (Abstract), §1 ¶5.

**What satisfies.** An abstract that (i) names the estimand as influence-weighted, (ii) carries the per-site-scope and asymptotic-step clauses in plain wording, (iii) reports the BBSE result as "certified 9 of 200 draws with no violation among them (exact 95% upper bound 0.34) and declined the remainder", (iv) substitutes plain wording for the three undefined terms, and (v) keeps within the word cap. Title: either qualify "finite-sample" or drop it from the conjunction with label-shift robustness.

---

# S2 — forces major revision, or threatens the deadline

### S2-1 · Account for δ across modes and rungs
**Closes:** `DS-49` (DS) · `R1-04` (R1) · `R4-39` (R4) · `R4-19` (R4)
**What/where.** §3.6's OR-guarantee ("if *either* tagged assumption holds") prices no union over the two independently-budgeted modes; §3.5's "Both budgets α ∈ {0.05, 0.10} … certified by separate walks" prices no union across rungs, and `report.py:205-217` selects the first certified rung strictest-first. Separately §3.6 says "each at full δ" while §3.5 says "δ for the baseline, δ_bet in the label-shift mode" — the code (`pipeline.py:65-66`, `shift.py:207`) agrees with §3.5, so §3.6 is wrong. **Satisfies:** a stated error probability for the *deployed* decision across modes and rungs, and §3.6's "each at full δ" corrected. `paper/draft.md` §3.5, §3.6, §3.7.

### S2-2 · Reconcile the two threshold-selection rules
**Closes:** `DS-18` (DS) · `R1-53` (R1) · `R1-59` (R1)
**What/where.** §3.5 "We deploy the maximum-coverage threshold in the certified prefix" vs §3.6 "we deploy the most conservative certified threshold" — identical construction, opposite rules; three referees tripped on it. The reconciliation (within-mode, then across-mode) is never stated, and §3.6's next sentence presupposes a threshold already chosen. `R1-59` asks the further unanswered question: on which pool is the coverage that decides the deployed threshold measured? (§3.5 states only that ordering is by margin on S_aux.) **Satisfies:** one sentence stating the two levels explicitly, plus the pool on which deployment coverage is evaluated. `paper/draft.md` §3.5, §3.6.

### S2-3 · Report certified thresholds; re-run E5 at a defensible operating point
**Closes:** `DS-46` (DS) · `R1-32` (R1) · `R2-33` (R2) · `R5-41` (R5) · `R5-59` (R5) · `R3-12` (R3)
**What/where.** No numeric τ* appears in §4.2–§4.5 at all; the only two in the paper are E5's 0.55 (the grid minimum, coverage 0.990) and E6's 0.77, neither derived, neither stated as certified, in which mode, or at which α. §3.5's whole apparatus exists to select a threshold. **Satisfies:** τ* reported for E1–E4 with its variation across draws; E5 and E6 stating their mode, α and certification status; E5 re-run away from the grid floor (bundled with S1-4). `paper/draft.md` §4.2–§4.7.

### S2-4 · Fix "touched exactly once"
**Closes:** `R1-21` (R1) · `R2-32` (R2) · `R4-09` (R4)
**What/where.** §3.2 and §4.1 both say S_cal is "touched exactly once, by the certification test". Up to 23 grid points × 2 modes × 2 rungs = 92 tests run against it, and R4 found four further reads from the code (`_bootstrap_estimate` 500-draw cluster bootstrap over `cal`, `_rm_vs_unweighted`, `_capped_influence_share`, `n_carrying`). No validity leak is alleged; the sentence is simply false as written and is the one a reader leans on. **Satisfies:** the sentence replaced with an accurate description of what touches S_cal, and the fixed-sequence FWER argument stated where it belongs. `paper/draft.md` §3.2, §4.1.

### S2-5 · Drop or qualify the pre-registration claim
**Closes:** `R1-23` (R1) · `R5-17` (R5)
**What/where.** §3.2 and §3.10 call the constants test "a lightweight, machine-verifiable substitute for pre-registration" that "**removes** the degrees of freedom that would otherwise let a tunable pipeline flatter itself". A self-authored unit test carries no timestamp and no third party. (The phrase appears twice, not three times; A.3 restates the pinning without it.) Read alongside S1-5, which shows the claim is additionally false for the experiment-defining constants. **Satisfies:** "removes" → "pins against drift", and an explicit statement that this is not pre-registration. `paper/draft.md` §3.2, §3.10.

### S2-6 · Sweep the shift magnitude
**Closes:** `DS-19` (DS) · `DS-54` (DS) · `R2-02` (R2) · `R5-49` (R5) · `R5-50` (R5)
**What/where.** One shift, 0.095 → 0.22, is the only label-shift condition in the paper; a single magnitude cannot distinguish a working correction from a shift detector. (Do not respond to "no evidence that the mode ever functions as a correction" — struck; 9 certified draws with 0 violations is weak but non-zero evidence.) Availability appears nowhere as a cost: §6.1's six limitations contain nothing about decline rate. `R5-50`: "certifies or declines" in contribution 2 conveys a balanced disjunction where the realized split is 4.5%/95.5%. `R5-49`: §1 ¶5's "declining instead" presents declining as the sole alternative when 9 draws certified safely. **Satisfies:** certify rate, decline rate and conditional hard-violation rate across a magnitude sweep; the realized split stated in contribution 2; a decline-rate/availability item in §6.1. `paper/draft.md` §1, §4.3, §6.1; `experiments/run_synthetic.py::run_E2`.

### S2-7 · Report BBSE under no shift; explain ρ̂ = 0.830
**Closes:** `DS-48` (DS) · `R4-16` (R4) · `R4-38` (R4) · `R1-08` (R1)
**What/where.** §3.6 defines ρ as the target-to-source odds ratio, so no shift implies ρ = 1; Table 3 reports ρ̂ = 0.830, a 17% departure. R4 established from `run_E6` (`SimConfig()`, no `label_base_rate`, no `concept_intercept`) that true ρ = 1, and — from the fact that `run_synthetic.py:501-504` populates `rho` only when `deploy_mode == "bbse"` — that **E6's operative deployment at τ* = 0.77 carries the label-shift tag on unshifted data**, which §4.7 and Table 3 never state. R4 further found that across E1's 200 in-distribution draws at α = 0.10 the deployed mode is baseline 147 / bbse 53, i.e. the BBSE tag wins deployment on 26.5% of in-distribution draws (E3: 34/200) — recoverable from `E1_validity.csv` and absent from the manuscript. `R1-08`: no coverage of [ρ_lo, ρ_hi] for the true ρ is reported in any of the six experiments. **Satisfies:** E6's shift status and deploy mode stated; true ρ = 1 stated against ρ̂ = 0.830; the in-distribution deploy-mode split reported; empirical coverage of the ρ interval measured across E1/E2/E6 including whether it covers ρ = 1; the same question answered for E2 with its direction relative to safety. `paper/draft.md` §4.2, §4.7, Table 3.

### S2-8 · Define a "valid" bootstrap resample and justify conditioning on validity
**Closes:** `R1-22` (R1)
**What/where.** §3.6 and A.2 require "2,000 valid resamples within 4,000 attempts" and "valid" is never defined. Quantiling over the retained set is the bootstrap distribution *conditional on validity*; the stated rationale addresses Monte-Carlo error, not selection, and δ_conf's coverage claim is stated as if the selection were not there. **Satisfies:** a definition of "valid", plus either an argument that the selection is ignorable or a measurement showing coverage is intact. `paper/draft.md` §3.6, A.2.

### S2-9 · Define the ρ clipping; repair gate (iii)
**Closes:** `R5-28` (R5) · `R5-29` (R5) · `R5-61` (R5) · `R2-28` (R2)
**What/where.** A.2's "the clipped ρ(c₀, c₁, π_s)" is the only occurrence of a clipping of ρ in the manuscript and it is undefined, while carrying the corner-interval argument. §3.6's gate (iii) tests q against the *widest* box interval [c₀,lo, c₁,hi], which is necessary but not sufficient — at the corner (c₀,hi, c₁,lo) the implied prevalence can be negative. And gate (iii) declines only when π_t leaves (0,1); no clinical plausibility band on π_t exists anywhere. **Satisfies:** the clip defined with its value; a statement of whether the clipped function's monotonicity survives saturation (which is what makes the corner argument sound); gate (iii) restated as the correct per-corner condition; a plausibility band on π_t or an explicit statement that none is imposed. `paper/draft.md` §3.6, A.2.

### S2-10 · Carry a target-batch term into the box
**Closes:** `R1-07` (R1)
**What/where.** §3.6's parenthetical "(which is exact under the design-conditional estimand)" conflates q's exactly-observed *value* with the population identity. Substituting a realized q from a finite target batch leaves an O(n_target^−1/2) error in π̂_t and hence ρ̂. The box is stated over (c₀, c₁, π_source) only; §3.1 admits sites as small as 20 records. **Satisfies:** a target-size term in the box or a stated bound on the omitted error, plus a note in §6.1. `paper/draft.md` §3.6, A.2, §6.1.

### S2-11 · Write out A and B
**Closes:** `R1-15` (R1)
**What/where.** A.2's "sign(E[Z(ρ)] − α) = sign(A + ρB) with (A, B) free of ρ" — A and B appear exactly once and are never defined in terms of atoms, weights or w_max = max(1, ρ). There is no theorem environment, no numbered assumption list, and no proposition covering the composed deployed procedure (walk × two modes × two rungs × endpoint pair). A passing test is not a substitute for a stated derivation. **Satisfies:** A and B written out explicitly in both branches of w_max, and a proposition covering the composed procedure. `paper/draft.md` A.2.

### S2-12 · Exhibit the truncation counterexample
**Closes:** `R1-33` (R1) · `R5-27` (R5)
**What/where.** §3.3's "provably anti-conservative: a construction with 17.5% true risk certifies at α = 5% under naive truncation" forwards to A.3, which restates the numbers and forwards to a regression test. No site configuration, no error rates, no argument is on the page — and Appendix A is titled *Deferred proofs* while A.3 is *Software and reproducibility details*. This construction is the sole justification for the influence-weighting estimand; the office rates it major. **Satisfies:** the construction exhibited in A.1 or a new A.4 with its site configuration and error rates, or "provably" removed. `paper/draft.md` §3.3, A.3.

### S2-13 · Justify the frozen constants and show sensitivity
**Closes:** `DS-40` (DS) · `R1-50` (R1) · `R1-14` (R1) · `R5-26` (R5) · `R2-27` (R2) · `DS-45` (DS, **PLAUSIBLE — settle by:** state whether "change the estimand" means R_M's numeric value — in which case the sentence is wrong, since with a_c = 0 both terms vanish — or its reference population, in which case say so and give the λ_t reason instead) · `R1-13` (R1, **PLAUSIBLE — settle by:** report the minimum certified coverage across E1's 200 draws; if no low-coverage certificate exists, drop the "trivially satisfiable by abstaining" clause and forward only the no-coverage-floor half, which is confirmed outright)
**What/where.** M = 100, the 0.10 confusion gap and the 2,000/4,000 resample thresholds carry no justification and no sensitivity analysis. §3.2's pre-registration argument defends *fixing* constants, not the values chosen. Consequences the paper never states: with log n ~ N(6.0, 1.1²), **89.8% of sites exceed 100 records**, so g_c is pinned at M for nine sites in ten and R_M is close to an unweighted per-site average; a 5,000-record hospital and a 100-record one carry identical influence (`R1-14`); at the clipped maximum g_c/n_c = 1/50, so §3.3's "still enters at full adverse **weight**" is literally false for a defined symbol — the intended word is "error" (`R5-26`). `R2-27`: a site with 500 records where the gate answers none is record-carrying, so it counts toward the 50-cluster gate *and* enters as a neutral atom; the count is never reported and Table 2's empty [0,30) bin shows the case is never exercised. `R1-50`: none of the six frozen constants is varied in any experiment. **Satisfies:** a sensitivity table over M (and ideally the two decline thresholds); the record-level answered error reported beside R_M in E1 and E6; the cap-hit fraction stated; the one-word fix in §3.3; the count of zero-coverage sites in E1 and E6. `paper/draft.md` §3.3, §3.6, §4.2, §4.7, A.3.

### S2-14 · Define the target pool
**Closes:** `R2-34` (R2) · `R5-62` (R5) · `R4-30` (R4) · `DS-52` (DS)
**What/where.** "target pool" occurs exactly once in the manuscript (§3.9, line 138), load-bearingly, and is never defined as a site or an aggregate. Table 1's counts 2+18+53+127 = 200 = R let a reader infer one pool per draw but not what a pool contains. R4 supplies the answer the others could not reach: `run_E1:117`, `run_E3:270` and `run_E5:402` each call `draw_cohort(cfg, 1, rng, …)` — a target pool of **one** freshly drawn site; E6 draws 40 and discloses it, E1/E3/E5 disclose nothing. Since §3.7(1) scopes the guarantee per target site, this is material. `DS-52`: E1's 0.9722 mean coverage has no stated weighting, while Table 2 labels its column "Mean per-site coverage" — so you label weighting when you choose to. **Satisfies:** a definition of "target pool" at first use; per-experiment disclosure of pool composition; the weighting stated for every reported mean. `paper/draft.md` §3.9, §4.1–§4.7.

### S2-15 · Repair the Wilson screen
**Closes:** `R1-05` (R1) · `R1-06` (R1)
**What/where.** The certified object is influence-weighted and cross-site; the screened object is the *unweighted* answered error of a target pool. §3.9 nowhere relates the two or bounds the gap, and its closing disclaimer addresses a different point. (The secondary claim about the binomial device inflating E2/E3 rates depends on S2-14: if a pool is one site, §4.1's generator does make records conditionally independent and the device is defensible — settle S2-14 first.) `R1-06`: a one-sided 95% lower bound exceeds the true parameter with probability ≈ 0.05 by construction, so a system sitting exactly at R_M = α trips the screen at ≈ 0.05 = δ; the screen's error rate and the confidence budget share the numeral, and §3.9 does not say so. **Satisfies:** the functional relationship between the certified and screened quantities stated, or a bound on the gap; and one sentence separating the screen's 0.05 from δ's 0.05. `paper/draft.md` §3.9.

### S2-16 · Deliver the promised intervals and make Table 1 reproducible
**Closes:** `DS-20` (DS) · `R1-28` (R1) · `R5-07` (R5) · `R5-46` (R5) · `DS-30` (DS) · `R1-27` (R1)
**What/where.** §4.1 promises exact Clopper–Pearson intervals "because every rate below is a proportion over R = 200 independent draws". Intervals appear on exactly four numbers; omitted from the 0/9 rate, both decline rates, all four Table 1 exceedances, both overall exceedance rates, all twelve Table 4 certify rates and every coverage mean. The promise's hedge is the undefined word "primary". The sharp instance to fix first is **Table 4's certify rates**, which are primary: E4's 0.3 at 300 sites fixes the α = 0.05 frontier and the abstract's "300+" claim, and its exact interval is [0.237, 0.369]. `R5-07`: the promise's *premise* is false — Table 1's bins are proportions over 2, 18, 53 and 127. `R5-46`: "Across every size bin the observed exceedance sits far below the reference" is asserted over a bin holding two pools at 0/2. `DS-30`/`R1-27`: the binomial reference column's n and p are stated nowhere and the column cannot be regenerated — Bin(25, 0.1) gives 0.463 against the tabled 0.4063, so an unstated within-bin averaging rule is in play. **Satisfies:** intervals on every primary rate including all twelve Table 4 cells; "primary" defined or dropped; §4.1's causal premise corrected; per-bin denominators and intervals in Table 1; the reference column's n, p and averaging rule stated in the caption; "every" removed from §4.2. `paper/draft.md` §4.1, §4.2, Tables 1 and 4.

### S2-17 · Report E1's realized answered error and the coverage-versus-α curve
**Closes:** `R5-16` (R5) · `R1-49` (R1) · `R5-56` (R5)
**What/where.** §3.5 promises the budgets are "reported as a coverage-versus-α curve"; no such curve appears in Figures 1–6 or Tables 1–4 (Table 4 is coverage vs *site count*, and the α = 0.05 cell at 208 sites is "—"). And §4 states "because we control the data-generating process, we can compute the true answered-set risk at each target site" — then §4.2 reports certify rate, coverage, hard-violation, exceedance and Table 1, and **never the realized answered-set error**, the quantity the certificate bounds. The tightness argument in §4.2 therefore rests entirely on 2 draws. **Satisfies:** the coverage-vs-α curve, or the sentence removed; E1's realized answered-error distribution and its achieved certification margin against the information floor. `paper/draft.md` §3.5, §4.2.

### S2-18 · Per-site dispersion in Table 2
**Closes:** `R2-21` (R2)
**What/where.** Table 2 reports three bin means over 40 sites (counts 0+4+15+21) with no dispersion, no minimum coverage, no maximum answered error and no count of sites exceeding α, while §4.7 concludes "Small sites are neither over-answered nor starved." **Satisfies:** dispersion columns plus the count of sites exceeding α. `paper/draft.md` §4.7, Table 2.

### S2-19 · Explain the non-monotone coverage; add Monte-Carlo error
**Closes:** `DS-31` (DS) · `R1-29` (R1) · `R2-36` (R2) · `R5-57` (R5)
**What/where.** §4.5 reports 0.9304 at 150, 0.9715 at 208, 0.9601 at 300, 0.9621 at 400 to four significant figures — rises, dips, rises — while the surrounding argument is that more clusters buy a better certificate. No Monte-Carlo error anywhere at R = 200. §4.5 already explains the 0.9715-vs-0.9722 cross-run difference by independent seeding, which shows the vocabulary is available. Additionally, Table 4's α = 0.05/300-site coverage of 0.7376 averages over only the 30% of draws that certified, which the caption does not disclose. **Satisfies:** a Monte-Carlo standard error on every coverage mean; one sentence on the 208→300 drop; the conditional-on-certification averaging disclosed in the Table 4 caption. `paper/draft.md` §4.5, Table 4.

### S2-20 · Narrow the frontier claims to what E4 supports
**Closes:** `R1-31` (R1) · `R1-34` (R1) · `R5-22` (R5, **PLAUSIBLE — settle by:** decide whether the abstract is held to §1's precision; if yes the fix is "roughly 300–400 sites, reliably at 400" and the finding stands, if "300+" is accepted as a lower bound it dies) · `R4-25` (R4) · `R1-10` (R1) · `R5-31` (R5)
**What/where.** Below ~125 sites the 50-cluster gate refuses regardless of the test (`MIN_CAL_CLUSTERS/SPLIT_FRACTIONS[2] = 50/0.40 = 125`), so E4 cannot separate the statistical frontier from a frozen constant — yet §1 and §5.2 present 150 as a capacity result. The grid {60,100,150,208,300,400} has no point in (100,150), (208,300) or (300,400), so every "first appears at" statement is grid-limited. §4.5 itself distinguishes gate from floor explicitly, which is to the paper's credit; the residual defect is §1's and §5.2's framing plus the grid. The abstract's "roughly 300+ sites" is looser than §1's own "first appears near 300 and stabilizes only at 400", and a 30% certify rate is not a budget met at 300. `R4-25`: Table 4's caption says "—" where nothing certifies, while `run_synthetic.py:362-364` writes 0.0 and plots it unmasked, so `E4_site_sweep.png` shows a measured-looking zero-coverage regime the table declares undefined. `R1-10`: §5.2's and §1's "not of the method" is a statement about all procedures; the information floor is a linearized zero-variance bound for this construction, and §3.4's "feasibility diagnostic, never a gate" governs its use, not its generality. `R5-31`: §6.1's "structurally prevents certification below roughly 400 clusters" is a specific quantitative frontier claim with no derivation, no clip-cap value and no experiment, offered as the reason a third assumption mode is excluded. **Satisfies:** grid points added in the three gaps or the "first appears" language replaced with interval statements; the gate/floor distinction carried into §1 and §5.2; "not of the method" removed or supported (bundled with S1-13); Table 4's zeros masked in the figure; §6.1's 400-cluster claim derived, measured, or softened. `paper/draft.md` §1, §4.5, §5.2, §6.1, Table 4; `experiments/run_synthetic.py:362-383`.

### S2-21 · Repair guarantee clause (3)
**Closes:** `R5-48` (R5) · `R2-18` (R2)
**What/where.** §3.7 clause (3) states unconditionally that the realized error count "exceeds α at binomial-dispersion rates even under a valid certificate", dropping the "at the boundary" qualifier §3.9 supplies — and your own E1 refutes the unconditional version (realized exceedance 0.05 overall, 0.0000/0.1111/0.0189/0.0551 by bin, against references of 0.4063–0.4915). §4.2 says so itself. Because clause (3) is one of five clauses that "survive into the deployed guarantee text", the overstatement ships to deployers. `R2-18`: §3.9's Wilson criterion is defined only as a harness device and is never promoted to an operational monitoring rule with a sample size and an escalation threshold. **Satisfies:** "at the boundary" restored to clause (3); §3.9's criterion either promoted to a monitoring rule with n and a threshold, or explicitly declared not one. `paper/draft.md` §3.7, §3.9.

### S2-22 · Specify E3
**Closes:** `DS-21` (DS) · `R1-11` (R1) · `R4-13` (R4, limbs b and c only — limb (a) is partially killed: §4.4's next clause discloses the true ordering) · `R1-40` (R1)
**What/where.** §4.4 gives no generative equation for the concept tilt and names no assumption mode, while §4.3 names its modes explicitly. Under §4.1's class-conditional Gaussian generator the posterior logit is linear in x plus a prior-odds intercept, so adding 2.0 multiplies the prior odds by e² ≈ 7.4 — whether that is concept shift or label shift depends on whether x is redrawn from the retilted mixture, which the manuscript does not say. If E3 is a relabelled prior shift, contribution 4 is not what it claims and the 83% is evidence *against* the BBSE mode. `R4-13(b)`: `run_E3:278` collects `answered_err_rate`, a **realized** rate, and `summary.md` stores it as `verified_mean_answered_risk_alpha0.10` — the honest name — while §4.4 calls it "the true mean answered risk" and §5.1 "true answered risk", contradicting §3.7 clause (3) in the one experiment about definitional rigour. `R4-13(c)`: the `e3-control-not-poisonous` abort path §4.4 calls "enforced, not decorative" has no test behind it. `R1-40`: contribution 4 is demoted inside its own sentence and again in §5.1 while being listed among the primary contributions. **Satisfies:** the tilt's generative equation; whether P(x|y) changes; which modes were run and which produced the 83%; "true risk" renamed to match what is computed; a test on the abort path; contribution 4 either promoted or moved out of the contributions list. `paper/draft.md` §4.4, §5.1, §1; `experiments/run_synthetic.py:267-293`; `tests/`.

### S2-23 · Test the harness and the guarantee text
**Closes:** `R4-11` (R4) · `R4-45` (R4) · `R4-12` (R4) · `R4-14` (R4) · `R4-31` (R4) · `R4-32` (R4)
**What/where.** `certgate/harness.py` — which decides whether a certificate counts as violated, and produces 0.01, 0.485, 0.0, 0.83 and every Table 1 binomial reference — has **zero test imports**; no assertion touches `wilson_lcb`, `hard_violation`, `exceedance_reference` or `SIZE_BINS`. `tests/test_shift.py:72-76` asserts a set that is the *complete* range of `certify_bbse`'s `reason`, narrowed by the preceding step to {None, "failsafe"}: it cannot fail, and the comment above it claims a certify-and-violate check the test never computes. `report._statement` emits five clauses; `test_pipeline.py:42-45` pins three — clause (2) and clause (5), the asymptotic disclosure, are unpinned, and no test inspects a BBSE-deployed statement, so a regression dropping clause (5) passes green. The 632-line `experiments/run_synthetic.py` producing every number in §4 is outside the suite entirely (`grep tests/ for experiments` → zero). `R4-32`: A.1(iv) says the boundary type-I behaviour is "pinned" by a test that asserts ≤ 0.08 against a 0.05 nominal at one seed. `R4-45` is the counterweight and should be preserved: `test_mcap_counterexample_regression` and the two dual-endpoint soundness tests are genuine adversarial regressions — the contrast with `harness.py` is the finding. **Satisfies:** tests importing `certgate.harness` with assertions on all four objects; the vacuous BBSE assertion replaced with the certify-and-violate check its comment claims; all five guarantee clauses pinned including a BBSE-deployed statement; at least smoke coverage of `run_synthetic.py`'s `_rate`, `_cert_eval`, the E3 abort and `_existing_summary_blocks`; A.1(iv)'s "pinned" softened to match the 0.08 tolerance. `tests/`, `paper/draft.md` A.1(iv), A.3.

### S2-24 · Serialize provenance and decline reasons into the released artifacts
**Closes:** `R4-05` (R4) · `R4-41` (R4) · `R4-06` (R4) · `R4-26` (R4) · `R4-28` (R4)
**What/where.** A.3 says "each report artifact embeds a provenance block recording package versions, seeds, and input hashes." `report.provenance()` builds it and `pipeline.py:130` attaches it, but grepping all of `experiments/out/` for `provenance|input_hash|timestamp_utc|python.*3\.13` returns **zero files**. §4.5 says it distinguishes the cluster gate from the information floor "explicitly … because the two failure modes have different remedies", yet `decline_reason` is populated by `_cert_eval` and omitted from all three `_write_csv` field lists; `insufficient-clusters` occurs zero times in every released artifact, and `summary.md`'s `gate_note` is derived arithmetically from `n_sites < 125`, not recorded. `R4-41`: `_existing_summary_blocks` lets a `--only` run assemble `summary.md` across partial runs, and with no provenance block nothing lets a reader tell which happened — material, given §4.5's explicit E1-vs-E4 distinction. `R4-26`: 2,331 bare `nan` tokens in the released CSVs (E1 200, E2 591, E3 200, E4 1,340) against the artifact's own documented JSON convention. `R4-28`: §3.4 describes "a deterministic, SHA-256-seeded permutation" (singular); `fixed_sequence_walk` consumes a fresh permutation per threshold from one advancing stream, a data-dependent number of them, and `shift.py:207`'s `all(...)` short-circuits so the ρ_hi stream never advances when ρ_lo fails — despite the docstring claiming per-endpoint streams make the result order-independent. Validity is unaffected; the description is not what runs. **Satisfies:** provenance written into every released artifact; `decline_reason` in every CSV; NaN replaced with the JSON-path convention; §3.4's permutation description corrected; a run-identity stamp distinguishing full-grid from merged summaries. `experiments/run_synthetic.py`, `certgate/report.py`, `paper/draft.md` §3.4, §4.5, A.3.

### S2-25 · Document the undocumented constants and the fourth decline gate
**Closes:** `R4-20` (R4) · `R4-21` (R4)
**What/where.** `pipeline.py:149-155` returns an all-declined report with `gate_reason="pool-too-small"` when the target has fewer than `MIN_ANSWERABLE = 10` records. `MIN_ANSWERABLE`, `pool-too-small` and "10 records" each return **zero hits** in the draft — this is the gate a real deployment with small daily batches hits first, and it appears nowhere. §3.2's constants enumeration also omits `n_boot = 500`, `PI_CLIP = 1e-4` (alluded to obliquely in A.2 as "the clipped ρ" but never valued — see S2-9), `SD_REL_TOL = 1e-9` and `HEAD_MAX_ITER = 2000`, all of which govern the procedure. **Satisfies:** the fourth gate documented in §3.3 or §3.6 alongside the cluster gate and the three BBSE declines; §3.2's enumeration completed with values. `paper/draft.md` §3.2, §3.3, §3.6.

### S2-26 · Fix the model-agnosticism claims
**Closes:** `R5-09` (R5) · `R5-32` (R5) · `R2-12` (R2) · `R3-11` (R3)
**What/where.** §3.8's "the validity of the certificate never depends on the quality or calibration of the model producing that score" is unqualified, while §3.6's BBSE mode inverts the classifier's own confusion rates and refuses when the confusion gap is < 0.10. A defensible reconciliation exists (quality governs *availability*, not validity) and the manuscript never draws it. §3.8's "A stronger black-box head can be substituted at a visible cost in coverage" has the direction backwards — a stronger head ranks better, so coverage should rise — and §5.3's neutral "a change in certified coverage" is correct; both sentences are untested since no experiment swaps the head. `R3-11`: §5.3 discusses only coverage and is silent on the explanation cost — under a black-box head, Contribution 3 does not survive. `R2-12`: no calibration plot, slope, intercept, Brier score, ECE or per-site calibration exists anywhere (27 occurrences of "calibrat*" read; every one is the pool, the fitting sense, or this dismissal), in a Collection that names calibration explicitly. **Satisfies:** the availability/validity distinction stated in §3.8; the "cost in coverage" direction corrected; §5.3 extended to state what explanation survives a black-box head and whether Contribution 3 does; at least one calibration diagnostic reported, or an explicit statement in §6.1 that calibration is out of scope and why. `paper/draft.md` §3.8, §5.3, §6.1.

### S2-27 · Run a degraded or misspecified head
**Closes:** `R2-29` (R2)
**What/where.** L2-regularized logistic regression is the correctly specified posterior form for the generator's equal-covariance class-conditional distributions, so the model class contains the truth; no degraded or misspecified head is run anywhere, and §3.8's untested "stronger black-box head" concerns the opposite direction. **Satisfies:** one experiment with a misspecified or miscalibrated head, reporting certify rate, coverage and hard-violation rate — this is the missing evidence for the model-agnosticism claim and closes the Row-D risk the panel did not raise. `experiments/`, `paper/draft.md` §4, §5.3.

### S2-28 · Define the clinical target, the loss, and the operating point
**Closes:** `R2-08` (R2) · `R2-06` (R2) · `R2-13` (R2) · `R2-44` (R2) · `R2-07` (R2) · `R2-05` (R2) · `R2-10` (R2)
**What/where.** Grepping for outcome definition / index event / prediction time / observation window / follow-up / censor / competing risk / calendar / time horizon returns **one** hit across the whole manuscript, and it is "never censors the error itself". `err_i` occurs once, undefined; `ŷ` occurs once, undefined; sensitivity, specificity, PPV, NPV, AUROC, AUPRC and confusion matrix return zero true hits. A.1(i)'s bound confirms err_i ∈ {0,1}, i.e. symmetric 0-1 loss; net benefit, decision curve and Brier return zero; "cost" occurs three times and never about FN/FP asymmetry. The score is max-softmax on [0.5, 1] and §3.8's answer rule is symmetric about p̂ = 0.5, so no clinical decision threshold is stated. The consequences the office verified: reconstructed answered-set **sensitivity ≈ 0.53**, and at 9.5% prevalence an always-negative classifier errs at 9.5%, so **α = 0.10 sits above the no-skill rate**; and ~40% of all cohort positives are declined (the declined-set prevalence estimate 38% is less robust and should be hedged). `R2-10`: §1's motivating community-hospital scenario is never connected to either assumption mode, and §6.1's exclusion of a covariate-shift mode does not discharge that. **Satisfies:** an outcome definition, index event, prediction time and horizon in §3.1 or §4.1; err_i and ŷ defined with the threshold at which ŷ is formed; a confusion matrix and sensitivity/specificity for the answered set; the declined-set positive fraction reported directly for E1 and E6; an explicit statement of whether FP and FN weigh equally and what that means clinically; and §5.1 or §5.4 connecting the motivating scenario to the assumption tags. `paper/draft.md` §3.1, §3.3, §4.2, §4.7, §5.1, §5.4.

### S2-29 · Governance, workload, and the certificate as an artifact
**Closes:** `R2-16` (R2) · `R2-17` (R2) · `R2-54` (R2) · `R2-01` (R2) · `R2-15` (R2)
**What/where.** `recertif|re-certif|expir|monitor|cadence|governance|oversight` → **zero matches**. `regulat|medical device|AI Act|accountab|automation bias|IRB` → **zero matches**. `per day|per year` → zero. So: no review interval, no monitored quantity, no expiry, no re-certification trigger, no regulatory framing, no abstention workload figure and no statement of who reviews declined cases. `R2-01`: "decline" carries two senses — per-case abstention (§3.8, §4.6) and whole-certificate refusal (§3.6, §4.2, §4.3) — with nothing distinguishing them and no operational consequence stated for the second. (§3.1 does say the per-case decline is deferred to human judgment; that half of the finding is corrected.) `R2-15`: §3.7 paraphrases five clauses but never quotes the deployed text, and nothing anywhere exhibits a certificate with its α, δ, τ*, mode tag, calibration site count or decline reasons; the provenance block is the only artifact given concrete content. **Satisfies:** distinct terms for the two declines; a §5 paragraph on recertification cadence, monitored quantity and expiry, or an explicit out-of-scope statement; a sized abstention workload (per site, per day) and the receiving role; and **one full certificate exhibited verbatim** — the single cheapest item in this bundle and the one that most directly serves this Collection's auditability emphasis. `paper/draft.md` §3.1, §3.6, §3.7, §5.

### S2-30 · Clinical citations, guideline conformance, keywords
**Closes:** `R2-14` (R2) · `R2-22` (R2) · `R2-46` (R2)
**What/where.** Exactly **2 of 31** references are peer-reviewed clinical works (`tripodcluster2023`, `internalexternal2021`), and neither TRIPOD+AI (Collins et al.) nor DECIDE-AI (Vasey et al.) appears; nor do Wong, Finlayson, Dvijotham, Mozannar & Sontag, Madras, Sendak, Obermeyer, Van Calster, Vickers & Elkin or Feng. §2.4's citation set is 2 clinical + 3 preprints + 3 reject-option. No guideline conformance is claimed and no checklist supplied. (Correction to carry: TRIPOD-Cluster is cited not only for site-as-unit practice but also at §1 and §4.1 for the distributional-profile claim — see S2-31.) `R2-46`: three of the Collection's named topics — fairness, calibration, clinical auditability — are absent from the keyword list. ("Clinical decision support" is *not* on the Collection's list; drop that item.) **Satisfies:** TRIPOD+AI and DECIDE-AI cited with a conformance statement or an explicit non-conformance note; a broader clinical-ML citation base in §1 and §2.4; keywords amended. `paper/draft.md` line 13, §1, §2.4; `paper/references.bib`.

### S2-31 · Support the generator's realism or label it illustrative
**Closes:** `R1-19` (R1) · `R2-11` (R2, **PLAUSIBLE — settle by:** read Takada et al., *J Clin Epidemiol* 2021;137:83–91 and determine whether it reports cluster-size distributions and between-cluster outcome heterogeneity; if it does even partially, narrow the finding to the three specific parameters rather than claiming neither source supplies anything) · `R5-13` (R5) · `DS-42` (DS) · `R5-47` (R5) · `R2-09` (R2) · `R3-19` (R3)
**What/where.** §4.1 attaches `tripodcluster2023` and `internalexternal2021` to a paragraph whose subject is the generator's numbers; the first is a *reporting checklist* by its own title and cannot supply log-mean 6.0, log-sigma 1.1, prevalence 0.095 or a site random-effect SD of 0.5. §1 makes the same realism claim with **no citation at all**. `DS-42`: §3.1's problem setting and §4.1's generator agree to the digit on all three parameters, so without realism support §3.1 describes `data.py`. `R5-47`: §4.1 states which coordinates carry signal but never that the direction loads them equally, so §4.6's "recovers the generator" check has no target — and if the loading is equal, features 0–3 are interchangeable by construction, which is the mechanism argument against S1-4. `R2-09`: the only site-indexed quantity in the generator is π_c, so P(x|y) is site-invariant by construction, "case mix" is being used to mean class mix, and BBSE's invariance assumption holds by construction in E2. `R3-19`: §3.8's and §4.7's oracle-only quantities are admitted without a real-deployment substitute. **Satisfies:** each of the four parameters sourced to a study that reports it, or a plain "these values are illustrative" disclaimer in §1 and §4.1; the signal direction's loading stated; §4.6's recovery claim narrowed to support recovery; a stated acknowledgement that E2 satisfies BBSE's invariance assumption by construction; and a proposed real-deployment substitute for the oracle columns. `paper/draft.md` §1, §3.1, §4.1, §4.6, §4.7, §5.5.

### S2-32 · Conformal citations, the exchangeability wording, and the three senses of "coverage"
**Closes:** `DS-14` (DS) · `R1-17` (R1) · `R4-35` (R4) · `R5-19` (R5) · `R1-44` (R1, **PLAUSIBLE — settle by:** state which reading of "not exchangeable with" is intended; under the joint-law reading the sentence is already correct and this is a wording preference, not an error) · `R5-20` (R5, **PLAUSIBLE — settle by:** state whether "machinery" in §2.2 names a construction actually imported from Dunn et al. or Lee et al.; if not, the fix is "machinery" → "unit") · `R5-45` (R5) · `DS-08` (DS) · `R2-31` (R2)
**What/where.** Absent from all 31 entries and directly on point: Barber, Candès, Ramdas & Tibshirani (2023) — the canonical treatment of the exchangeability failure §2.2 builds on, and additionally *adverse* to §3.7(1) as the impossibility result for non-trivial distribution-free conditional inference; Tibshirani et al. (2019), which §6.1 needs where it excludes covariate-shift weighting; Gibbs/Cherian/Candès; Jones et al. (ICLR 2021), whose result that selective classification magnifies group disparities is the adverse prior art for §4.7's own equity analysis; plus Jung, Bastani, Snell, Lu, Cortes–DeSalvo–Mohri, Field–Welsh, Aas. `R5-45`: the abstract's "silently overconfident once deployment spans institutions" and §1 ¶3's "overruns its stated confidence once deployment is grouped by site" are unconditional and depend on positive intraclass correlation — your own motivating figure is a *range*. (Do not respond to §1 ¶1's "often false"; that instance was struck as properly hedged.) `DS-08`/`R2-31`: "coverage" carries three incompatible senses across 27 occurrences — conformal set coverage, answered fraction, and confidence-interval coverage ("a coverage statement over the S_aux bootstrap box", "corner-interval coverage") — none defined. **Satisfies:** the named works cited where their claims bear, with BCRT-2021's adverse implication for §3.7(1) engaged rather than omitted; the unconditional generalizations conditioned on intraclass correlation; and either three distinct terms for the three senses of coverage, or explicit definitions at each first use. `paper/draft.md` §1, §2.2, §2.4, §3.6, §3.7, §4.7, §5.1, §6.1, A.2; `paper/references.bib`.

### S2-33 · XAI literature and positioning
**Closes:** `R3-14` (R3) · `R3-15` (R3) · `R3-29` (R3) · `R3-30` (R3) · `R3-31` (R3) · `R3-16` (R3, **PLAUSIBLE — settle by:** confirm from Artelt, Visser & Hammer, "Model Agnostic Local Explanations of Reject" (ESANN 2022, arXiv:2205.07623) whether their reject explanations are contrastive/counterfactual in form; if they are, the finding stands as filed) · `R3-27` (R3, **PLAUSIBLE — settle by:** read Lenders et al., ECML PKDD 2024, doi 10.1007/978-3-031-70368-3_25 and confirm whether it attaches formal fairness constraints or guarantees to the reject decision; if it does, §2.4's "attach no statistical guarantee" mischaracterises a cited work)
**What/where.** The manuscript's entire explanation citation set is four entries: `lundberg2017shap`, `artelt2022reject`, `ifac2025abstainexplain`, `l2lore2025`. Absent: Ghassemi/Oakden-Rayner/Beam, Tonekaboni et al. and Rudin (2019) — Rudin would convert the transparent-head choice from an unanchored decision into a positioned one; Antorán et al. (CLUE), whose subject *is* the declined-case problem, and Wachter et al.; Cortes–DeSalvo–Mohri (ALT 2016) and Hendrickx et al. (*Machine Learning*, 2024), the survey omission being the more consequential for a paper with "abstention" in its title; Shapley (1953), Štrumbelj & Kononenko (2014) and Kumar et al. (ICML 2020) — Kumar is the standing critique of exactly the magnitude-as-importance move §4.6 makes; Madras et al. (2018) and Mozannar & Sontag (2020), against which the expert-agnostic abstention is never scoped. **Satisfies:** the named works cited where their claims bear; §2.4's one-sided guarantee-axis argument extended to concede the axes on which reject-option prior art is ahead (explanation form, actionability); the learning-to-defer literature scoped against. `paper/draft.md` §1, §2.1, §2.4, §3.1, §3.8, §4.6; `paper/references.bib`.

### S2-34 · Attribution notation and semantics
**Closes:** `R1-43` (R1) · `R3-22` (R3) · `DS-25` (DS) · `R3-21` (R3) · `R3-04` (R3) · `R3-20` (R3) · `R3-09` (R3) · `R3-23` (R3)
**What/where.** In §3.8's identity φ_j(x) = w_j(x_j − μ_j) with logit(p̂(x)) = base + Σφ_j, **μ_j and "base" are defined nowhere** while sd_j and coef_j are defined with care in the same sentence; μ_j fixes the attribution baseline and base is the intercept the exactness claim depends on. Four referees flagged μ_j. `R3-21`: §3.8 glosses standardized coefficients as "the direction and strength of each feature" — a standardized coefficient is a *conditional* effect given the other model features, not a marginal importance, and under the generator's ≈0.09 correlation the two readings diverge; §4.6 then uses them as ground-truth-recovery evidence. `R3-04`: "signed feature attributions of the confidence deficit" occurs once with no formula, value function or exactness argument. The office correction makes this cheap: for a given x the sign of logit p̂(x) is fixed, so m(x) is *affine* in the φ_j and the deficit's attributions on that branch are simply ∓φ_j; non-additivity bites only across the sign branch. `R3-20`: "exact" attaches to attributions **nine** times (Abstract, §1 ×2, contribution 3 heading and body, §2.4, §3.8 ×3, §4.6), plus "genuine Shapley values". `R3-09`: the global-importance "recovery" check is vacuous — φ_j is a deterministic function of the fitted coefficients, so if the fit recovers the signal the attributions recover it necessarily; it tests model fit, not explanation fidelity, and `faithful|plausib|user study|human evaluation` returns zero. `R3-23`: "gap ranking" is undefined and its ellipsis hides features 4–7, which is exactly the check that would test the driver claim. **Satisfies:** μ_j and base defined, with a stated reason why the training-split mean is the right reference population; the standardized-coefficient gloss corrected to a conditional reading; the deficit decomposition written out in one line using the affine identity; the nine "exact" claims conditioned per S1-3; the recovery check reframed as a fit check and a faithfulness measure added per S1-12; "gap ranking" defined and all eight features shown. `paper/draft.md` §3.8, §4.6.

### S2-35 · Per-case attribution exhibit, site structure, and the R=1 disclosure
**Closes:** `R3-05` (R3) · `R3-26` (R3) · `R3-08` (R3) · `R4-04` (R4) · `R3-32` (R3) · `R3-03` (R3)
**What/where.** §3.8 promises an abstention reading of the form "declined because feature A pulls toward positive while features B and C pull toward negative"; §4.6 delivers "declined because the informative features leave confidence below the certified bar" — naming no feature and no direction — and reports for declined cases only scores (0.5262, 0.5445) and margins (0.0956, 0.0223), **without exhibiting a single φ_j value**. §4.6 also never states how many sites its 202 records come from or how many draws they represent, in a paper whose central claim is that the site is the unit of independence. `R3-08`/`R4-04`: §4.1 says "Every experiment … replicates over R = 200 independent calibration draws"; `run_E5` (`:398-401`) and `run_E6` (`:461-465`) each take one `rng`, one cohort, one deployment, no R loop, and accept `quick` and ignore it — neither §4.6 nor §4.7 states R = 1 or that no sampling uncertainty attaches. `R3-03`: §3.7 establishes that no individual record carries a certified property, so "explanation attached to a *certified decision*" at the record level is unsupported by the paper's own guarantee text; §2.4's "exact attributions on a certified **gate**" is the accurate phrasing and both are in play. `R3-32`: §3.8's "Three artifacts make the gate explainable" then introduces a fourth one paragraph later, with its results in §4.7. **Satisfies:** at least one declined case with its full signed φ vector and a delivered sentence naming features and directions; the site count and draw count for §4.6's records; R = 1 stated in §4.6 and §4.7 with §4.1's blanket claim corrected; "certified decision" reconciled with "certified gate" throughout; §3.8's artifact count fixed. `paper/draft.md` §3.7, §3.8, §4.1, §4.6, §4.7, §2.4.

### S2-36 · Explanation limitations, the human-facing artifact, and fairness
**Closes:** `R3-17` (R3) · `R3-02` (R3) · `R3-10` (R3) · `R3-18` (R3) · `R2-20` (R2)
**What/where.** §6.1's six italicized limitations are all statistical; not one concerns explanation, against §6's own "Its posture throughout is disclosure". `R3-02`: no explanation method is contributed and the manuscript concedes it — though the abstract is not silent on the mechanism ("*Because the deployed risk model is linear*…"), so what it omits is the explicit disclaimer that this is a read-out rather than a method. `R3-10`: every feature is an integer index, no clinical name anywhere, no human evaluation, and the absence is never stated. Merged into it, R2-25's two concrete asks: one worked vignette with plausibly named clinical features and an EHR-facing abstention message, and one sentence conceding the layer's clinical utility is untested. `R3-18`: `education|human-cent|human cent|workflow` returns **zero matches** — the Collection frames explainability as an educational aid for clinicians, and the manuscript has three human-facing sentences in total. `R2-20`: `fairness|equity|protected|demograph|subgroup` matches **only line 200**; `ifac2025abstainexplain` ("Interpretable and **Fair** Mechanisms for Abstaining Classifiers") is cited **five** times and never for its fairness content. **Satisfies:** at least one explanation-facing item in §6.1; an explicit read-out-not-a-method sentence in the abstract or §1; the vignette and the untested-utility concession; the fairness content of the cited work engaged, or an explicit statement of why the paper does not; a sentence on the educational/human-centered dimension the Collection names. `paper/draft.md` Abstract, §1, §3.8, §4.7, §5, §6.1. (Feeds S1-12 — do these together.)

### S2-37 · Substantiate the novelty delta against the closest prior work
**Closes:** `R5-53` (R5)
**What/where.** §2.1's "Yu and Liu are closest: the same certificate shape … but over i.i.d. records" is where contribution 1's entire novelty delta lives, and `yu2026joint` is `@misc`, arXiv:2606.08517, no venue. **Satisfies:** direct quotation of that work's stated assumptions in §2.1, so the delta is checkable rather than asserted. `paper/draft.md` §2.1.

### S2-38 · Citation-support mismatches
**Closes:** `R1-46` (R1) · `R2-37` (R2) · `R5-36` (R5) · `R5-38` (R5, **PLAUSIBLE — settle by:** read Bates et al. 2021 (JACM 68(6):43) and determine whether it contains any multiplicity-control argument bearing on selecting one threshold from an ordered grid; if it is purely UCB-over-nested-sets the citation is misapplied)
**What/where.** §4.2's "non-zero — consistent with a tight rather than a vacuous certificate [@geifman2017selective]": the interval [0.0012, 0.0357] is equally consistent with a distinctly slack certificate, so 2/200 does not license "tight"; and a 2017 selective-classification method paper offers no tightness criterion and cannot speak to CertGate's cohort. (Note the same citation is used *correctly* at §3.1 for the (α, δ) phrasing convention.) `R5-36`: §2.1 attributes the finite-sample certificate to Geifman and El-Yaniv and explicitly *not* to Chow, and §6 then groups both under "certified selective risk" — an internal inconsistency settled from the manuscript alone. `R5-38`: §3.5 cites `bates2021rcps` alongside fixed-sequence testing and LTT for "no δ-splitting across the grid"; RCPS controls risk over a nested family by a UCB, not by a fixed-sequence argument. **Satisfies:** the tightness claim removed or supported by the achieved margin against the information floor (see S2-17); §6's grouping corrected; the RCPS citation moved or its relevance stated. `paper/draft.md` §2.1, §3.5, §4.2, §6.

### S2-39 · Delete the power-grid sentence
**Closes:** `R1-47` (R1) · `R5-37` (R5)
**What/where.** §2.4 closes with "The same certificate shape appears in power-grid contingency screening [@thermal2026audit], so it is not specific to medicine." The citation is an unrefereed `@misc` noted "submitted to IEEE Transactions on Power Systems" and is used nowhere else. Shape resemblance in one unrefereed cross-domain preprint does not establish generality; the sentence also breaks §2's announced structure (each section closes with nearest-work-and-gap, and §2.4's gap statement comes *before* it); and in a Collection scoped to clinical ML it spends credibility for nothing. **Satisfies:** deleted, and §2.4 closed on its gap statement. `paper/draft.md` §2.4.

### S2-40 · Cite or drop the clinician/auditor claims
**Closes:** `DS-41` (DS) · `R3-33` (R3)
**What/where.** §1 ¶1's "what a clinician weighs before trusting an automated triage, and what an auditor asks to see documented" is two empirical claims about human behaviour with no citation on the sentence — the preceding `[@chow1970reject; @elyaniv2010selective]` sits on the prior clause — and no evidence anywhere in the paper bears on clinician or auditor behaviour. In a general ML venue this is ordinary framing; in a Collection whose stated emphasis is explainability as a transparency requirement *and an educational aid for clinicians*, it is squarely in scope. **Satisfies:** cited to clinical-ML trust or governance literature, or rewritten as a design premise rather than an empirical claim. `paper/draft.md` §1.

### S2-41 · Trim the register, without weakening the disclosures
**Closes:** `DS-37` (DS) · `DS-38` (DS) · `R1-41` (R1) · `R2-47` (R2)
**What/where.** `DS-37` counts **at least twelve** instances of the self-attestation motif, not eight: "We do not paper over this" (§3.6), "We disclose plainly" (§3.6), "Demonstrating the failure openly is validation rigor" (§4.4), "This check is enforced, not decorative" (§4.4), "the reading is honest" (§4.7), "a deliberate validation choice, not a deferral" (§5.5), "Its posture throughout is disclosure" (§6), "We state the boundaries … plainly" and "none is patched over in the results" (§6.1), "the rigor that constructively answers" (§1), and "disclosed wherever the guarantee is stated" (×3). `DS-38` is distinct — anticipatory argument with an imagined critic: "For any reader tempted to call α=0.10 a weak guarantee" (§5.2, doubly exposed since S2-20 shows its substance is unproved), "That is not a defect; it is what a selective gate on a low-prevalence task should do" (§4.7), "A negative control that cannot fail proves nothing" (§4.4). Four referees flagged the register while explicitly crediting the draft's restraint elsewhere. **This must be read with S3-8: cut the claims of honesty, keep every disclosure.** **Satisfies:** the motif reduced to two or three instances; §5.2's imagined-critic sentence cut (it fails on substance as well as register); the §3.7/§3.9/§6.1 scoping clauses untouched. `paper/draft.md` §1, §3.6, §4.4, §4.7, §5.2, §5.5, §6, §6.1.

### S2-42 · Fix the §5.1-versus-§4.2 contradiction
**Closes:** `R1-26` (R1) · `R5-05` (R5)
**What/where.** §5.1 says "E1 shows realized exceedance rising toward its binomial reference (0.0551 against 0.4915 in the largest size bin)"; §4.2 says the observed exceedance "sits far below the reference" using the same two numbers, which are 8.9× apart, and Table 1's observed column (0.0000/0.1111/0.0189/0.0551) is not monotone rising. §4.2 is right on both counts. The consequence is not cosmetic: §5.1 uses the sentence to support clause (3), and E1's data do not illustrate that point — see S2-21. **Satisfies:** §5.1 corrected, and clause (3)'s supporting evidence replaced with something that actually shows it. `paper/draft.md` §4.2, §5.1.

### S2-43 · Numerical descriptors that propagate to the abstract
**Closes:** `DS-29` (DS) · `DS-36` (DS) · `R1-51` (R1) · `R1-52` (R1)
**What/where.** `DS-29`: 0.22 / 0.095 = **2.3158**, so "a near-tripling of outcome frequency" is wrong — it is closer to a doubling — and the phrase is quoted in the Abstract and the Figure 2 caption, so the correction propagates. `DS-36`/`R1-51`: 0.0630 − 0.0591 = 0.0039 = **0.39 percentage points**, and both operands are given as fractions on [0,1] in the preceding sentence and in Table 3, so "the ~0.4-point gap" invites a hundredfold misreading; the fix is one word. `R1-52`: §4.3 pairs "exact 95% CI [0, 0.018]" with "consistent with the rule-of-three bound 3/200 = 0.015" — 3/200 is an accurate approximation to the *one-sided* 95% bound (0.014867) while the interval quoted is two-sided Clopper–Pearson; the mismatch is one-sided-versus-two-sided, not anti-conservatism. **Satisfies:** "2.32-fold" substituted throughout; "percentage points" added; the rule-of-three sentence corrected to name the one-sided bound. `paper/draft.md` Abstract, §4.3, §4.7, Figure 2 caption.

### S2-44 · Correct the record-count claim
**Closes:** `R4-24` (R4)
**What/where.** §3.1 and §5.2 both say "roughly eighty site-level observations, not the ~10⁵ record-level ones a naive analysis would claim". The parallel term is the calibration records, which R4 measured at **51,414** under the E1 draw-0 seed — the stated figure overstates by 1.95×, and even the whole cohort (137,533) overstates by 2.67×. This sits in the sentence carrying the site-count-is-the-constraint argument. **Satisfies:** the true figure substituted, with the pool it refers to named. `paper/draft.md` §3.1, §5.2.

---

# S3 — polish

### S3-1 · Bibliography hygiene
**Closes:** `DS-32` (DS) · `R1-37` (R1) · `R2-38` (R2) · `R4-27` (R4) · `DS-33` (DS) · `R1-38` (R1) · `R2-39` (R2) · `DS-34` (DS, **PLAUSIBLE — settle by:** render `references.bib` through the Springer Nature CSL style and see whether the `note` field is emitted; if dropped this is package hygiene, if emitted it is a substantive correction) · `DS-35` (DS, **PLAUSIBLE — settle by:** check DOI registration for JMLR 11(53) and PMLR 161, and the current ACM J. Data Science record for 10.1145/3786352; if no DOI exists and no volume is assigned, the finding dies)
Three citekeys mismatch their year field (`ifac2025abstainexplain` → 2024 ECML PKDD, and the `ifac` prefix names a federation the entry has nothing to do with; `l2lore2025` → 2024; `angelopoulos2021ltt` → 2025 AoAS). The `.bib` header (lines 1–3) dates an internal verification pass, points at `paper/TODO.md`, and names a deliberately excluded citation candidate — strip it. Two entries record another author's unpublished submission status in `note`. Missing DOIs/volumes in three entries (see DS-35's check). Fix in `paper/references.bib`; nothing here renders as an in-text error, so this is production hygiene.

### S3-2 · Stop letting code identifiers stand in for exposition
**Closes:** `DS-26` (DS) · `DS-28` (DS) · `R1-35` (R1) · `R2-42` (R2) · `R5-39` (R5)
"mode FULL" (§4.1) occurs once, is never expanded, and no alternative mode is named — the reader cannot tell whether it is an assumption mode, a fidelity setting or a run profile, and it is why S2-22 cannot be resolved from the text. "The test suite is 69/69 green" (A.3) is a pass count presented as a result; replace it with a sentence naming what is verified, on the model of A.3's own truncation-regression description. "The cohort follows the specification frozen in `data.py`" locates authority in a file rather than the paper — the specification *is* given in the same sentence, so the fix is the attribution phrasing only. Same for §4.4's `tilt_pushes_risk_above_alpha` and `e3-control-not-poisonous`. `paper/draft.md` §4.1, §4.4, A.3.

### S3-3 · Bin notation
**Closes:** `R5-43` (R5) · `R4-23` (R4)
§3.9 writes the size bins as {<30, 30–100, 100–300, >300}; `harness.py:20` uses `((0,30),(30,100),(100,300),(300,inf))` filtered `lo <= x < hi`, and Tables 1 and 2 render `[300, ∞)`. ">300" excludes 300; "30–100" is ambiguous at both endpoints. §3.9 is the one place out of step. `paper/draft.md` §3.9.

### S3-4 · Over-precision and unit hygiene in tables
**Closes:** `R2-43` (R2) · `R5-42` (R5)
Four-decimal reporting on quantities derived from single-draw deployments (the E5 importances 1.157/1.161/1.178/1.155; Table 3's 1,378.9) alongside means over 200 draws (0.9722), with no uncertainty attached to either class. Table 3's "Count" column holds two exact integers and one non-integer expected value carrying an embedded parameter estimate — and 1,378.9 patients reads oddly in a clinical framing. The Tag column's three-way distinction is good and should be kept. `paper/draft.md` §4.6, §4.7, Table 3.

### S3-5 · Captions should describe panels, not restate the body
**Closes:** `R4-33` (R4)
Figure 1's caption reproduces "0.01 (2 of 200 calibration draws)" and "0.0189 vs 0.4820 for [100,300)" verbatim from §4.2; Figure 2's reproduces "48.5%"; Figure 3's reproduces "83%". Counts verified: 0.9722 ×4, the 0.01 hard-violation ×5, 48.5% ×5, 83% ×4, 95.5% ×3. Rewrite captions to describe what each panel shows, with denominators (see S1-6). `paper/draft.md` Figure captions.

### S3-6 · Notation and symbol hygiene
**Closes:** `R1-24` (R1) · `R1-25` (R1) · `R5-24` (R5) · `R5-23` (R5) · `R2-35` (R2) · `R5-52` (R5)
In §3.4's λ_t display: bare `n` is used before it is introduced (its only gloss arrives two paragraphs later) and collides with n_c, n_cal and n_answered; σ̂²_{t−1} is never given as an estimator; μ̂ is initialized at 0.5 and then appears in no displayed formula. (One sub-claim is already answered: §3.5 states which betting budget each mode spends.) Carry the reason it matters: §3.3 puts two site counts in play and λ_t ∝ n^{−1/2}, so the ambiguity changes the bet schedule and hence power. `R1-25`: WSR's predictable-mixture bet scales as (σ̂²_{t−1} t log(1+t))^{−1/2} and the displayed schedule substitutes a fixed n — validity is preserved by data-independence, but the deviation from the cited construction is not stated. `R5-23`: across 14 occurrences, "budget" denotes α in seven places and δ in five, and the collision is worst **inside the abstract**, where "under a 0.05 budget" means δ and "the stricter α=0.05 budget" means α, two sentences apart. `R2-35`/`R5-52`: the calibration cluster count appears as "roughly eighty site-level observations" (§3.1), "about 83 calibration clusters" (§3.5) and "roughly 80 of them" (§5.2) — 0.40 × 208 = 83.2, so all three renderings are *correct*; this is one quantity with two values and three spellings, including "eighty" and "80" in the same document. House style, not an error. `paper/draft.md` §3.1, §3.4, §3.5, §5.2, Abstract.

### S3-7 · Back-matter and reader-facing repo hygiene
**Closes:** `DS-43` (DS, **PLAUSIBLE — settle by:** read Discover Computing's Submission guidelines → Manuscript structure for the required back-matter order; if the journal places tables and figure legends after the references the finding stands, otherwise it dies) · `R4-29` (R4) · `R4-22` (R4, **PLAUSIBLE — settle by:** determine whether "certificate" anywhere in the manuscript denotes the full report object including the provenance block; the office searched and found no such usage, in which case §4.1's byte-identity sentence is already correct and this reduces to an optional one-clause disambiguation)
Document order runs Competing interests → Figures → Tables → References; check against the journal's template. `README.md` says "Suite 53/53 green (~4s)" against an actual 69 passing in ~3.6s, and its Quickstart says "~2 min" — three mutually inconsistent reader-facing numbers, and §A.3's "69/69" is the correct one. `README.md`, `paper/draft.md` back matter.

### S3-8 · Editorial record — no author action
**Closes:** `DS-55` (DS) · `DS-60` (DS) · `R5-68` (R5) · `R2-70` (R2) · `R4-42` (R4)
`DS-55` recommended seating a distribution-free-inference referee; satisfied — Referee 1 reached the A.1(iii) conditioning gap independently, which is the evidence the recommendation was necessary rather than precautionary. `DS-60`, `R5-68`, `R2-70` and `R4-42` are the counterweights and are recorded here so they are not lost when the register is trimmed: zero hits on a novelty-inflation scan and every "first" ordinal; a clean arithmetic audit (Table 1's bins recover 0.05 exactly, all four Clopper–Pearson intervals correct, all three Table 3 fractions recompute, zero dangling citekeys, zero orphaned entries, §4.5's volunteered cross-run difference); the disclosure apparatus Referee 2 credits by name; and Referee 4's independent re-verification of 69/69 tests, byte-identical E5/E6 regeneration including PNG SHA-256, and every quantitative claim it could trace. **Authors: do not respond to these. Do not delete what they credit.** A revision that replaces hedges with confidence will not be accepted.

---

# Coverage check

**282 of 282 survivor IDs appear above.** By referee: DS 46/46 · R1 54/54 · R2 46/46 · R3 31/31 · R4 47/47 · R5 58/58.

By rank: **S1 = 79** (14 work-items) · **S2 = 170** (44 work-items) · **S3 = 33** (8 work-items).

All 15 PLAUSIBLE findings are marked with their settling check: `DS-34`, `DS-35` (S3-1) · `DS-43`, `R4-22` (S3-7) · `DS-45`, `R1-13` (S2-13) · `DS-50` (S1-4) · `R1-44`, `R5-20` (S2-32) · `R2-11` (S2-31) · `R3-16`, `R3-27` (S2-33) · `R4-47` (S1-12) · `R5-22` (S2-20) · `R5-38` (S2-38).

**Deliberately bundled** — the large multi-ID work-items, where one fix closes many findings and the plan would be unusable if split:

| Work-item | IDs | Why bundled |
|---|---|---|
| S1-12 venue fit | 10 | Five referees reached one judgment from four angles; one programme of work answers all of them |
| S1-11 BBSE reporting | 8 | The interval, the diagnostics and the underpowering question are one CSV change plus one experiment |
| S1-4 n=2 | 8 | Ten flags, one re-run |
| S2-13 constants | 7 | One sensitivity table plus two one-line fixes |
| S2-28 clinical target | 7 | One §3.1/§4.1 specification block plus one confusion-matrix table |
| S2-31 generator realism | 7 | One decision — cite or label illustrative — settles all seven |
| S2-32 conformal/coverage | 9 | One citation pass plus one terminology pass |
| S2-33 XAI literature | 7 | One citation pass |
| S2-34 attribution notation | 8 | One rewrite of §3.8's two paragraphs |
| S2-24 artifact provenance | 5 | One serialization change to `run_synthetic.py` |
| S2-23 test coverage | 6 | One test-suite session |
| S3-1 bibliography | 9 | One `.bib` pass |
| S3-6 notation | 4 | One symbol-table pass |

Near-identical S3 items (bibliography years, notation collisions, caption wording, bin notation, over-precision) are bundled aggressively by design; each is one line of work.

---

# Critical path

**Must happen first, and blocks nearly everything downstream.**

1. **S1-1 and S1-2** (the estimand and the sampling assumption). Every claim in §3.7, §5.1, the abstract and the title inherits from these. Do not write the abstract (S1-14) or the venue-fit programme (S1-12) until you know whether §3.7(1) says "per target site" or "over the site population" — S1-1's outcome changes the paper's headline sentence, and `R1-01`'s confidential form warns that the contribution shrinks if the claim is honestly restated. Budget the honest restatement, not the derivation; BCRT-2021 (see S2-32) is the impossibility result standing in the way of the derivation, and finding it in your own reference list would have saved you this.
2. **S1-5** (`sep = 1.8`). Re-running E2 and E3 at 2.2 changes 48.5% and 83%, which appear in the abstract, §1, contribution 2, §4.3, §4.4, §5.1 and three figure captions. Every downstream number depends on it. Start this on day one; it is compute, not thought.
3. **S1-6 and S1-7** (figures, deposit). Independent of everything, and the paper cannot be re-refereed without them. Do them in week one and stop worrying about them.

**Can run fully in parallel.**

- The artifact track — S1-7, S2-23, S2-24, S2-25, S3-7 — touches no manuscript claim and can proceed alongside the statistical work by a different person.
- The citation track — S2-30, S2-32, S2-33, S2-37, S2-38, S2-39, S2-40, S3-1 — is a bounded reading-and-writing task, roughly 25 works, entirely independent.
- The notation and presentation track — S2-34, S2-43, S2-44, S3-2 through S3-6 — is independent once S1-1 fixes the estimand's name.
- **S1-13** (the record-as-unit comparator) is the cheapest high-value experiment in the plan: same E1 draws, same §3.9 screen, one extra certification path. Start it early; it feeds S1-14's abstract, §1 contribution 1, §5.2 and S2-20's frontier language.

**Sequenced, and the real long poles.**

- **S1-4** (re-run E5) depends on **S2-3** (choosing a defensible certified operating point), which depends on **S2-2** (which threshold rule actually governs). Three steps, and the last one is a 200-draw replication.
- **S1-11 → S2-6 → S2-7** is one chain: serialize the BBSE diagnostics, then sweep the shift magnitude, then report BBSE under no shift. The sweep is the heaviest new compute in the plan after E4.
- **S1-12** is not a writing task. A faithfulness assessment against a comparator explanation method, a clinically named vignette, and the fairness engagement are new work with a literature to read first.

**Is S1+S2 achievable before 2026-10-05? No.**

You have roughly ten weeks. The S1 set alone contains four new or re-run experiments (comparator, E5 re-run, shift-magnitude sweep, E2/E3 at sep = 2.2), a faithfulness study against a comparator explanation method, an archival deposit with packaging and licensing, six figures to produce, and two structural rewrites of the guarantee. The S2 set adds a misspecified-head experiment, a per-site distribution analysis, a confusion-matrix and clinical-target specification, roughly 25 works to read and cite, a test-suite programme, a serialization change to the experiment driver, and a Monte-Carlo error pass over every reported mean. On the evidence of the original timeline — which allotted two weeks to the full grid and figures and slipped to the point that the GBM appendix and the real-data section were never written at all — 249 findings across 58 work-items in ten weeks is not a plan, it is a hope.

**A realistic scope cut.** Deliver **all of S1 plus the S2 items that S1 depends on or that a referee will read as part of the same defect** — concretely S2-1 through S2-7, S2-12 through S2-17, S2-19 through S2-24, S2-26, S2-28 (partial: the target definition, err_i, and the confusion matrix), S2-29 (partial: the certificate exhibit and the two decline senses), S2-31 through S2-36, S2-39, S2-41, S2-42, S2-43 — and the whole of S3, which is cheap. Defer the rest to a stated future-work paragraph, and say in your response letter which items you deferred and why. Referees tolerate an explicit deferral; they do not tolerate silence.

**Three cuts that buy the most time, if you need them.**

- **Drop the α = 0.05 rung and E4's upper sweep points.** E4 is your heaviest experiment and it currently cannot separate the statistical frontier from a frozen constant below 125 sites (S2-20). Reporting α = 0.10 at the 208-site scale, with the frontier as a stated limitation, costs one contribution sentence and buys back the sweep.
- **Cut §5.4's federated paragraph and §2.4's power-grid sentence.** Both rest on unrefereed preprints, neither is evidenced, and one actively undercuts your venue fit (S2-39).
- **Do not attempt the per-target-site derivation.** Restate the estimand (S1-1) and take the smaller contribution. It is the honest move and it is also the fast one.

**And one thing you should not cut.** If the S1-12 explainability programme will not fit before 2026-10-05, do not submit a thinner version of it to this Collection. Retitle, drop the explainability claims to what the evidence supports, and submit to *Discover Computing* outside the Collection — the statistical contribution stands on its own and the journal's scope covers it. A paper that promises explainability in its title and evidences it on two cases will draw the same six reports again, and the second time there will be no revision offered.
