# Risk cross-check — the authors' anticipation against what six referees found

Handling editor, *Discover Computing* · Collection "Intelligent Medicine: ML and Explainable AI for Next-Generation Healthcare"

Source for the authors' anticipation: the reviewer-risk table in `PAPER-OUTLINE.md` (six rows, "Likely objection" / "Pre-emption"). Referred to below as Rows A–F:

| Row | Anticipated objection | Their stated pre-emption |
|---|---|---|
| **A** | "Only synthetic data" | Generator mirrors a documented real multi-site cohort; every mechanism exact so ground truth exists, which real data cannot supply; real data named as ongoing work |
| **B** | "Why not conformal prediction?" | Related-work paragraph: record-level exchangeability false under clustering; cluster-conformal gives the wrong estimand |
| **C** | "Isn't α=0.10 a weak guarantee?" | The information floor makes it a property of ~80-cluster data, not of the method; E4 prices stricter budgets |
| **D** | "Logistic regression is too simple" | Gate is model-agnostic; logistic chosen *for* the XAI requirement; appendix can swap a GBM head |
| **E** | "The bootstrap step isn't finite-sample" | Disclosed in the guarantee text; single asymptotic link; finite-sample replacement as future work |
| **F** | "Negative control seems to show the method failing" | Framed as contribution C4: a control that cannot fail proves nothing |

**Headline: 74 of 282 surviving findings (26%) fall inside a row the authors anticipated. 208 (74%) do not.** Of the six pre-emptions, exactly one reached the page as evidence; four reached it as prose; one (the GBM appendix) never reached it at all. Two of the six rows were transcribed into the manuscript almost verbatim as anticipatory rhetoric — and the rhetoric itself became a finding.

---

## Part 1 — Independently rediscovered (74 IDs)

### Row A — "Only synthetic data" · 16 findings

**A1 — the pre-emption's central sentence is the thing referees attacked.** `DS-53`, `DS-22`, `R1-16`, `R2-26`, `R5-10`, `R5-44`, `R5-64`.

The table's third clause — "every mechanism is exact by construction so ground truth is available for validation — which real data cannot provide" — appears in the draft as §5.5's "Real data cannot supply that ground truth, which is what makes it unable to validate a validity claim." Four referees independently refuted it *from the paper's own §3.9*: the hard-violation criterion consumes only realized answered errors and a Wilson bound, both computable from any labelled retrospective multi-site cohort. `R5-64` then shows the four legs compose into a standing rationale for never testing on real data at all.

**The gap between anticipated and addressed:** the mitigation was not merely unimplemented — it was implemented as an argument the manuscript's own methods section falsifies. This is the worst possible outcome for an anticipated risk: the pre-emption became the attack surface. `DS-22` and `R5-44` add the venue consequence (a title claiming "clinical risk models" over a synthetic-only evidence base); `DS-53` notes the manuscript never says whether a cohort was sought, obtained, or blocked — the one fact that would let a reader price "ongoing work".

**A2 — the realism claim has no source.** `R1-19`, `R2-11` (PLAUSIBLE), `R5-13`, `DS-42`, `R5-47`.

The table's first clause — "generator parameters mirror a documented real multi-site cohort" — is carried in §4.1 by two citations, and three referees checked them: `tripodcluster2023` is a *reporting checklist*, `internalexternal2021` a *methodological* IECV study. Neither can supply log-mean 6.0, log-sigma 1.1, prevalence 0.095 or a site random-effect SD of 0.5. §1 makes the same realism claim with no citation at all. `DS-42` closes the loop: §3.1's "problem setting" agrees with §4.1's generator to the digit, so without the realism support §3.1 describes `data.py`, not clinical data. `R5-47` adds that §4.1 never states the signal direction loads coordinates 0–3 equally, so §4.6's "recovers the generator" check has nothing to check against.

**A3 — the generator is convenient in ways the mitigation never considered.** `R2-08`, `R2-09`, `R2-29`, `R3-19`.

The anticipation defended *synthetic-ness*. Three referees attacked *this particular* synthetic design: only π_c is site-indexed, so BBSE's invariance assumption holds by construction in E2 (`R2-09`); logistic regression is the correctly specified posterior for the generator, so the model class contains the truth (`R2-29`); and no outcome definition, index event, prediction time, observation window or censoring appears anywhere (`R2-08` — one grep hit across the whole manuscript, and it is "censors the error"). `R3-19` targets the mitigation's own oracle argument as an admission with no real-deployment substitute proposed.

### Row B — "Why not conformal prediction?" · 11 findings

**B1 — the answer was written, but not run.** `DS-01`, `R1-12`.

§2.2 carries the argument in full. What the pre-emption did not anticipate is that referees would accept the argument and then ask for the *experiment*: no record-as-unit certificate is run anywhere in E1–E6. The motivating record-level failure enters only by citation to `@zhou2026falsesense`. `R1-12` corrects the referee's own overreach — §4.3 does run an "uncorrected baseline" — but it is an internal ablation of CertGate's exchangeable mode, still site-as-unit.

**B2 — the exchangeability argument's scholarship.** `DS-14`, `R1-17`, `R4-35`, `R5-19`, `R5-45`, `R1-44` (PLAUSIBLE), `R5-20` (PLAUSIBLE).

Four referees independently found that Barber, Candès, Ramdas & Tibshirani (2023) — the canonical treatment of exactly the failure §2.2 builds its motivation on — is absent from all 31 entries, as are Tibshirani et al. (2019) on covariate shift and Gibbs/Cherian/Candès. `R5-45` shows the argument is stated unconditionally when it depends on positive intraclass correlation; the paper's own motivating figure is a *range* (9–30%), which is itself evidence the failure is conditional. `R5-20` (PLAUSIBLE) questions whether "the cluster-as-unit machinery CertGate reuses" names anything actually imported from either hierarchical-conformal paper.

**B3 — the pre-emption's own distinction is then dissolved.** `DS-08`, `R2-31`.

The row's whole force is that conformal gives *coverage* and CertGate gives *selective risk*. The manuscript then uses "coverage" in three incompatible senses across 27 occurrences — conformal set coverage, answered fraction, and confidence-interval coverage — none defined. The pre-emption's key distinction is undermined by the draft's own vocabulary.

### Row C — "Isn't α=0.10 a weak guarantee?" · 22 findings

This is the row with the widest gap between anticipation and delivery, and the one where the pre-emption was transcribed into the manuscript as rhetoric.

**C1 — the pre-emption is on the page, word for word, and it is a finding.** `DS-38`, `DS-37`, `R1-10`, `R1-41`, `R2-47`, `R5-11`.

§5.2 reads: *"For any reader tempted to call α=0.10 a weak guarantee: the operative rung is a property of the available cluster count, not of the method."* That is Row C's pre-emption pasted into the Discussion. Four referees flagged it as anticipatory argument with an imagined critic (`DS-38`, `R1-41`, `R2-47`, part of `DS-37`'s twelve-instance motif), and two attacked its *substance*: "not of the method" is a claim about all procedures, and the information floor is a linearized zero-variance bound for *this* construction, with no minimax lower bound proved or claimed (`R1-10`), and no comparator anywhere against which "not of the method" could be tested (`R5-11`).

**The gap:** the pre-emption's substance ("the information floor makes this a property of the data") is a real technical argument that would need a minimax statement or a comparator to land. The draft ships the conclusion without either, in a sentence that reads as defensiveness. Both halves of the row failed simultaneously.

**C2 — E4 cannot carry the weight the row assigns it.** `R1-31`, `R1-34`, `R5-22` (PLAUSIBLE), `DS-31`, `R1-29`, `R2-36`, `R5-57`, `R4-25`, `R5-31`.

The pre-emption says "E4 shows exactly what stricter budgets cost in sites." `R1-31` shows E4 cannot separate the statistical frontier from the frozen 50-cluster gate below ~125 sites, and the grid {60,100,150,208,300,400} has no point in (100,150), (208,300) or (300,400), so every "first appears at" statement is grid-limited. Four referees found the coverage sequence non-monotone (0.9304 → 0.9715 → 0.9601 → 0.9621) with no Monte-Carlo error at R=200. `R4-25` found Table 4 declares non-certifying cells undefined while the figure plots them as a measured 0.0. `R5-31` finds a second unsupported frontier claim ("roughly 400 clusters") used to justify excluding the covariate-shift mode entirely.

**C3 — the objection was rediscovered in a form the pre-emption does not reach.** `R2-07`, `R2-05`, `R2-13`, `R2-44`.

No referee said "α=0.10 is weak because the method is weak." The clinical referee said something sharper: at 9.5% prevalence an always-negative classifier errs at 9.5%, so **α=0.10 sits above the no-skill rate**, and the reconstructed answered-set sensitivity is ≈0.53 (`R2-07`, arithmetic independently verified by the office). `R2-05` adds that ~40% of all cohort positives land in the declined set. `R2-13` and `R2-44` note the estimand is a symmetric 0-1 loss with no net-benefit, decision-curve or FN/FP asymmetry anywhere, and no clinical decision threshold is stated.

**This is the single most important entry in this file.** The authors anticipated a *statistical* objection to α=0.10 and prepared a *statistical* defence (the information floor). The objection actually arrived from the *clinical* side, where the information floor is irrelevant. A reviewer-risk table written by the methods author cannot anticipate the clinical referee.

**C4 — supporting arithmetic.** `R2-35`, `R5-52`, `R4-24`. Three spellings of the cluster count (≈80 / 83 / "eighty"), and — materially — §3.1's "~10⁵ record-level ones" overstates the 51,414 calibration records by 1.95×, in the sentence that carries the site-count-is-the-constraint claim.

### Row D — "Logistic regression is too simple" · 4 findings

`R5-09`, `R5-32`, `R2-12`, `R3-11`.

**Nobody made the anticipated objection.** What referees attacked was the pre-emption itself. §3.8's "the validity of the certificate never depends on the quality or calibration of the model producing that score" is contradicted by §3.6, where the BBSE mode inverts the *classifier's own* confusion rates and refuses to run when the head's confusion gap is too small (`R5-09`). §3.8's "A stronger black-box head can be substituted at a visible cost in coverage" has the direction backwards — a stronger head ranks better, so coverage should rise — and §5.3 states it correctly, so the two sentences describe the same substitution in opposite directions (`R5-32`). No calibration assessment of any kind exists in the manuscript (`R2-12`, 27 occurrences of "calibrat*" read). And `R3-11` finds §5.3 silent on the explanation cost of the swap: under a black-box head Contribution 3 does not survive, and no section says so.

**The gap:** the outline promised "E-appendix can swap a GBM head and show the coverage/interpretability trade." That appendix does not exist. The pre-emption is the only one of the six that was never even attempted.

### Row E — "The bootstrap step isn't finite-sample" · 14 findings

**E1 — the disclosure does not travel to the two lines that get read.** `R1-45`, `R5-03`, `R5-04`.

§3.6 claims "every guarantee statement carries that caveat." §3.7(5), §6.1 and §1 ¶4 do. The **title** and the **abstract** do not — the title conjoins "finite-sample" with "label-shift robustness", and the abstract's guarantee sentence carries none of the five §3.7 clauses. The manuscript's own universal quantifier is falsified by its two most-read lines. `R5-04` is explicit that this is the one place in the paper where *more* hedging is the correct revision.

**E2 — the anticipated objection was purity; the actual objection was soundness.** `R1-22`, `R1-07`, `R1-08`, `R1-15`, `R5-28`, `R5-29`, `R5-61`, `R5-38` (PLAUSIBLE).

Disclosure answers "is this finite-sample?" It does not answer: what is a "valid" resample and why is conditioning on validity ignorable (`R1-22`); why the box carries no target-batch term when §3.1 admits sites of 20 records (`R1-07`); what the empirical coverage of [ρ_lo, ρ_hi] actually is — never measured in any of the six experiments (`R1-08`); what A and B are, since they appear once and are never defined (`R1-15`); what the "clipped ρ" is, since the clipping is load-bearing for A.2's corner argument and is defined nowhere (`R5-28`, `R5-61`); and why gate (iii)'s necessary condition is presented as sufficient (`R5-29`).

**E3 — the δ the disclosure is about is not accounted for.** `DS-49`, `R1-04`, `R4-39`, `R4-19`.

Three referees found that no combined error probability is stated across the two modes, and a fourth found the same gap across the two α rungs. `R4-19` adds a flat contradiction the manuscript cannot absorb: §3.6 says "each at full δ", §3.5 says "δ for the baseline, δ_bet in the label-shift mode", and the code agrees with §3.5.

### Row F — "Negative control seems to show the method failing" · 7 findings

**F1 — this pre-emption worked, and the office record says so.** `R2-70`, `DS-60`, `R5-68`.

No referee accused the negative control of showing the method failing. §4.4's "A negative control that cannot fail proves nothing" is Row F's pre-emption transcribed, and it landed: `R2-70` explicitly credits the disclosure apparatus (five guarantee clauses, the two-number protocol, the enforced poison check, the six-item limitations list) and identifies the paper as fixable by addition. `DS-60` verified independently that a novelty-inflation scan returns zero hits and every "first" in the manuscript is ordinal. `R5-68` reproduced the full arithmetic audit and found it clean, plus a voluntarily disclosed cross-run difference no referee would have caught.

**F2 — but the control's specification was attacked instead.** `DS-21`, `R1-11`, `R4-13`, `R1-40`.

No generative equation for the concept tilt appears anywhere; §4.4 names no assumption mode; and under §4.1's class-conditional Gaussian generator, adding 2.0 to the posterior logit is a prior-odds multiplication by e² ≈ 7.4 — which makes E3 a possible *relabelled prior shift*, in which case the 83% is evidence against the BBSE mode rather than for the honesty contribution (`R1-11`; the confidential form goes further). `R4-13` found that the 0.2022 the paper calls "true mean answered risk" is a mean of *realized* rates, contradicting §3.7 clause (3) — in the one experiment whose subject is definitional rigour. `R1-40` notes the contribution is demoted inside its own sentence and again in §5.1.

---

## Part 2 — Genuinely new (208 IDs)

The authors did not anticipate any of the following. I group by what a real referee would call the finding.

**N1 — The certified parameter is not the certified claim (13).** `R5-01`, `R1-01`, `DS-47`, `R5-63`, `R1-03`, `R5-58`, `R1-05`, `R2-34`, `R5-62`, `R4-30`, `R2-18`, `R5-48`, `R2-21`.
R_M sums over sites; §3.1 and §3.7(1) claim it holds "at a new target site". No transport step exists in §3, A.1 or A.2. Two referees working from different materials reached this independently; a third supplied the remedy question. This is the paper's headline claim, and the risk table does not mention it.

**N2 — The supermartingale does not follow from the stated null (8).** `R5-02`, `R1-02`, `R5-55`, `R1-24`, `R5-24`, `R1-25`, `R1-06`, `R4-32`.
Under A.1(ii)'s design-conditioning the atoms have site-specific means, and A.1(iii)'s per-step inequality fails at any site with μ_t < α even when the average satisfies H₀. The office supplied a realizable counterexample (λ = (1.0, 0.5), E[K₂] = 1.125 > 1). No i.i.d.-or-exchangeable assumption on calibration sites is stated anywhere, and §6.1 then concedes a dependence structure that would break it.

**N3 — The influence weighting is unjustified and unexplored (8).** `R1-14`, `R2-04`, `R5-26`, `DS-40`, `R1-50`, `R2-27`, `DS-45` (PLAUSIBLE), `R1-13` (PLAUSIBLE).
M = 100 pins ~90% of sites at the cap, so R_M is close to an unweighted per-site average; a 5,000-record hospital and a 100-record one carry identical influence; the abstract omits "influence-weighted" entirely. R2's worked counterexample (0.0563 certified vs 0.1790 record-weighted) reproduces exactly.

**N4 — "Provably anti-conservative" with no proof (2).** `R1-33`, `R5-27`. The pointer runs §3.3 → A.3 → "a regression test", and Appendix A is titled *Deferred proofs* while A.3 is *Software and reproducibility details*.

**N5 — Threshold selection and data discipline (15).** `DS-18`, `R1-53`, `R1-59`, `R1-21`, `R2-32`, `R4-09`, `R4-19`, `R1-23`, `R5-17`, `DS-46`, `R1-32`, `R2-33`, `R5-41`, `R5-59`, `R3-12`.
Two "we deploy the … threshold" sentences with opposite selection rules; "S_cal touched exactly once" against a 23-point walk × 2 modes × 2 rungs (and, from the artifact, four further reads); no τ* reported for E1–E4 at all; the E5 case study run at the grid minimum where declines barely occur. Note that `R1-23`/`R5-17` attack the outline's own "lightweight pre-registration substitute" framing — the authors treated the constants test as a strength and never anticipated it being read as an unearned claim.

**N6 — Whether the label-shift mode works at all (18).** `DS-19`, `DS-54`, `DS-57`, `R4-07`, `R4-37`, `R4-44`, `R1-09`, `R2-03`, `R5-06`, `R4-08`, `R5-49`, `R5-50`, `R2-02`, `R2-28`, `DS-48`, `R4-16`, `R4-38`, `R2-10`.
Four referees found the 0/9 conditional rate reported without its interval (exact upper bound 0.3363 = 6.7× δ) in the same paragraph as four correctly computed intervals over 200. Three concluded independently that at 83 clusters, δ halved, a Bonferroni-widened ρ interval and both endpoints required, "correctly calibrated refusal" and "underpowered mode" predict the same 95.5%. R4, with artifact access, showed the discriminating diagnostics *are computed and then discarded* and that all 191 declines are the generic `failsafe` — so E2 is currently unfalsifiable from the release.

**N7 — The exact-Shapley claim is wrong as stated (14).** `R3-01`, `R1-18`, `R5-12`, `R4-15`, `R5-60`, `R1-43`, `R3-22`, `DS-25`, `R3-21`, `R3-04`, `R3-20`, `R3-09`, `R3-06`, `R3-23`.
**All six referees found this.** Linear SHAP requires feature independence or the interventional value function; the manuscript names neither, states exactness nine times, and runs on a generator that induces marginal correlation ≈0.09 among exactly the features being explained. Adjacent: μ_j and "base" undefined in the identity that defines the attributions; "gap ranking" undefined; a magnitude statistic used to license the causal word "driver".

**N8 — The explainability evidence is two cases (12).** `DS-11`, `DS-50` (PLAUSIBLE), `R1-30`, `R2-19`, `R3-25`, `R4-10`, `R3-05`, `R3-26`, `R3-08`, `R4-04`, `R3-32`, `R3-03`.
**Ten independent flags — the most-replicated finding in the pool.** A three-decimal cohort statistic, an eight-feature gap ranking and the adverb "systematically" over n_declined = 2, with features 0–3 reported at 1.157/1.161/1.178/1.155 so no mechanism exists by which feature 0 should separate. §4.6 exhibits no per-case φ_j at all, and neither E5 nor E6 is replicated despite §4.1's blanket "Every experiment … replicates over R = 200".

**N9 — Venue fit: the collection's central emphasis is demoted in the paper's own voice (21).** `DS-09`, `DS-58`, `DS-22`→see A1, `R1-69`, `R2-68`, `R3-13`, `R5-67`, `R5-33`, `R1-39`, `R3-02`, `R3-17`, `R3-10`, `R3-18`, `R2-46`, `R4-47` (PLAUSIBLE), `R3-16` (PLAUSIBLE), `R3-27` (PLAUSIBLE), `R2-20`, `R1-47`, `R5-37`, `DS-41`, `R3-33`.

**This is the largest inversion between the outline and the reports.** `PAPER-OUTLINE.md`'s fit table lists explainable abstention as the paper's "novel angle" for this collection. The draft calls it "a supporting capability the linear head makes nearly free" (§3.8) and "supports the certificate above rather than standing as an independent method" (§1). Two referees found independently that explainable abstention is one of §2's four literatures and is dropped from both the §1 and §6 three-counts. §6.1's six limitations are all statistical; not one concerns explanation. Zero occurrences of "faithful", "plausib", "user study", "human evaluation", "education", "human-cent", "workflow". Fairness appears in one sentence; `ifac2025abstainexplain` ("Interpretable and **Fair** Mechanisms for Abstaining Classifiers") is cited five times and never for its fairness content. And §2.4 closes by volunteering that the certificate shape "is not specific to medicine" (`R1-47`, `R5-37`).

**N10 — The clinical deployment questions (8).** `R2-01`, `R2-54`, `R2-06`, `R2-14`, `R2-15`, `R2-16`, `R2-17`, `R2-22`.
"Decline" means two different things (per-case abstention, whole-certificate refusal) with no stated operational consequence for the second; no abstention workload figure; `err_i` never defined and no discrimination metric anywhere; no certificate exhibit despite §3.7 enumerating five clauses; zero hits for recertif/expir/monitor/cadence/governance/oversight and for regulat/medical device/AI Act/IRB; 2 of 31 references are peer-reviewed clinical works, and neither TRIPOD+AI nor DECIDE-AI appears.

**N11 — The evidence base and citation integrity (24).** `R2-23`, `R2-69`, `R5-18`, `DS-59`, `R1-20`, `R4-34`, `R5-53`, `R1-46`, `R2-37`, `R5-36`, `R3-29`, `R3-30`, `R3-14`, `R3-15`, `R3-31`, `DS-32`, `R1-37`, `R2-38`, `R4-27`, `DS-33`, `R1-38`, `R2-39`, `DS-34` (PLAUSIBLE), `DS-35` (PLAUSIBLE).
Seven of thirty-one entries are unrefereed 2025–26 arXiv `@misc`; they carry the motivating 9–30% figure, the closest-competitor identity on which contribution 1's novelty entirely rests, and the federated positioning. The manuscript twice calls one of them "published". Three citekeys mismatch their year field, and the `.bib` header points at an internal to-do file and names a rejected citation candidate.

**N12 — The artifact (30).** `R4-01`, `R4-36`, `R4-43`, `R4-02`, `R4-03`, `R5-30`, `R4-46`, `R4-05`, `R4-41`, `R4-06`, `R4-11`, `R4-45`, `R4-12`, `R4-14`, `R4-17`, `R4-40`, `DS-07`, `R1-36`, `R2-40`, `R5-40`, `DS-27`, `R4-20`, `R4-21`, `R4-22` (PLAUSIBLE), `R4-26`, `R4-28`, `R4-29`, `R4-31`, `R4-42`, `R4-18`.
The outline's §7 says the reproducibility statement "is cheap for us because it is already true." A referee with repo access disagreed on 43 of 47 counts. The sharpest: `SHIFT_SEP = 1.8` (code comment: *"realistic head so shift bites"*) is used in E2 and E3 — the two experiments producing 48.5% and 83% — against §4.1's single stated `sep = 2.2`, and that parameter sits outside the "pre-registered" pinned set. A described missingness encoder does not exist and the code does the inverse. `harness.py`, which decides whether a certificate counts as violated, has zero test imports. No LICENSE, no packaging, no version control, six dangling `../testbed` paths. Counterweight, and it must be read: `R4-42` independently re-verified 69/69 tests, all four Clopper–Pearson intervals, byte-identical E5/E6 regeneration including PNG SHA-256, and every quantitative claim it could trace — all matched.

**N13 — The validity harness's own reporting (11).** `DS-20`, `R1-28`, `R5-07`, `R5-46`, `DS-30`, `R1-27`, `R5-16`, `R1-49`, `R5-56`, `R1-52`, `R4-33`.
§4.1's promise of exact intervals is delivered on four numbers out of dozens; its stated justification ("because every rate below is a proportion over R = 200") is false for the stratified rates the paper then reports bare; Table 1's binomial reference column cannot be regenerated from anything stated; and E1 — the validity experiment, on an oracle-equipped harness — never reports the realized answered-set error, the quantity the certificate bounds.

**N14 — Presentation and internal contradiction (16).** `DS-05`, `R1-42`, `R3-24`, `R5-15`, `R1-26`, `R5-05`, `DS-23`, `DS-56`, `DS-29`, `DS-36`, `R1-51`, `R2-43`, `R5-42`, `R5-23`, `DS-43` (PLAUSIBLE), `DS-52`.
Five referees found the submission contains six figure captions and no figures. `R1-26`/`R5-05` found §5.1 describing E1's data as "rising toward its binomial reference" when §4.2 correctly says the opposite about the same two numbers. `DS-56` is the framing the decision letter needs: the abstract's two strongest sentences are its two thinnest.

**N15 — Code identifiers substituting for exposition (5).** `DS-26`, `DS-28`, `R1-35`, `R2-42`, `R5-39`. "mode FULL" never expanded; "The test suite is 69/69 green" as a result; `data.py`, `from_raw`, `tilt_pushes_risk_above_alpha`, `e3-control-not-poisonous` as authorities, against an absent repository URL.

**N16 — Bin notation (2).** `R5-43`, `R4-23`. §3.9 writes ">300" where the code and both tables use [300, ∞).

**N17 — Editorial (1).** `DS-55` — the recommendation to seat a distribution-free-inference referee. Satisfied: Referee 1 reached the A.1(iii) conditioning gap independently, which is the evidence the recommendation was necessary rather than precautionary.

---

## Part 3 — Table risks the panel did not raise

Three of the six anticipated objections were never actually made by any referee. Two were genuinely neutralized on the page; one was not, and remains live.

### Row B — "Why not conformal prediction?" · **Neutralized.**

No referee asked it. The pre-emption reached the page as written, in §2.2:

> "Conformal prediction [@vovk2005algorithmic] gives distribution-free coverage under exchangeability of the calibration and test points — false under multi-site clustering, where records within a hospital are not exchangeable with those from an unseen site. Applied at the record level it certifies the wrong estimand (per-record coverage, counting correlated records as fresh evidence); lifted to the cluster level it fixes the unit but still yields coverage, not a risk budget on the answered subset."

That is a complete answer and every referee accepted it. **But it is not safe.** Four referees found the canonical citation for the argument (Barber, Candès, Ramdas & Tibshirani 2023) absent, and BCRT-2021 is additionally *adverse* to §3.7(1) — it is the impossibility result for non-trivial distribution-free conditional inference, which is exactly the claim `R1-01`/`R5-01` challenge. A conformal specialist on a second round would open §2.2 not to ask "why not conformal" but to ask why the impossibility result that governs the paper's per-site claim is uncited. The row is neutralized as an objection and live as a liability.

### Row F — "Negative control seems to show the method failing" · **Neutralized.**

No referee made the objection, and the pre-emption is on the page:

> "A negative control that cannot fail proves nothing." (§4.4)
> "Demonstrating the failure openly is validation rigor" (§4.4)

`R2-70` credits the enforced poison check by name ("a tilt that failed to raise true risk above α aborts the run before any output is written"). This is the one row where the mitigation was implemented as *machinery* rather than prose, and it is the one row that worked. The lesson is not subtle.

**Residual risk:** `R1-11` and its confidential form raise a different and worse attack the framing does not cover — if the concept tilt is a relabelled prior shift, E3 is not a concept-shift control at all, and the 83% becomes evidence against the BBSE mode. A referee who reconstructs the tilt from §4.1's generator will get there. The framing is safe; the specification is not.

### Row D — "Logistic regression is too simple" · **Not neutralized. Live.**

No referee made the objection — but the pre-emption is the *weakest* of the six on the page, and the promised evidence does not exist. §3.8 offers:

> "The gate itself is model-agnostic: the score only *ranks* cases, and the validity of the certificate never depends on the quality or calibration of the model producing that score."

`R5-09` shows that "never" is false: the BBSE mode inverts the head's own confusion rates and declines when the head's confusion gap is too small. So the standing defence against Row D is a sentence the office has confirmed overreaches. The outline's promised GBM appendix was never written, no experiment anywhere swaps the head, no calibration assessment of any kind exists, and `R2-29` establishes that the logistic head is the correctly specified posterior for the generator — so the paper has never once run its gate on a model that could be wrong.

**A real referee may still hit this, and would land hard.** The obvious next question — "your gate is model-agnostic; show me it on a head that is miscalibrated or misspecified" — has no answer in the manuscript, no answer in the artifact, and a defence sentence that is false as written. Of the three rows the panel missed, this is the one I would fix before resubmission even though nobody asked.

---

## Part 4 — Assessment

**The table anticipated the right *kinds* of objection and the wrong *severity*.** All six rows name objections a reviewer would plausibly make, and five of the six drew referee fire. But 74 of 282 findings fall inside them, and not one of the top-tier defects appears anywhere in the table: the estimand/guarantee mismatch, the supermartingale conditioning gap, the exact-Shapley overclaim, the n=2 explainability evidence, the undisclosed generator parameter, the missing figures, the demotion of the collection's central emphasis. The table is a list of things a *sympathetic* reader might grumble about. The reports are a list of things that are wrong.

**Four of the six mitigations reached the page as prose, and the prose became findings.** Rows C and F were transcribed into the draft nearly verbatim (§5.2's "For any reader tempted to call α=0.10 a weak guarantee"; §4.4's "A negative control that cannot fail proves nothing"). Row F's transcription worked because it sat beside real machinery. Row C's did not, because it sat beside nothing — and four referees flagged it as defensive register while two attacked its substance. `DS-37` counts at least twelve instances of the disclosure motif and `DS-38` three instances of anticipatory pre-emption. **A reviewer-risk table written into the Discussion is a liability; written into the Experiments it is a contribution.**

**Two mitigations were never implemented at all** — the GBM appendix (Row D) and the real-data section (Row A's escape hatch, "if real-data access lands by ~week 5"). Both were conditional in the outline and both conditions failed, but the *claims* they were meant to support stayed in the paper. §3.8 still asserts model-agnosticism; §5.5 still asserts the route to real data is "concrete". That is the recurring shape of this failure: the mitigation was planned, the plan slipped, and the assertion shipped without it.

**Independent rediscovery is strongest exactly where the mitigation was rhetorical.** Row A drew seven findings across four referees; Row C drew twenty-two across five; Row E fourteen across four. In each case the authors knew the objection was coming and answered it with a sentence. Six independent referees found the sentence.

**The single largest miss is structural, not technical.** `PAPER-OUTLINE.md`'s fit table lists explainable abstention as this collection's hook — "novel angle: explaining why the system says 'I don't know'." The reviewer-risk table has no row for it, because the authors treated it as an asset. Five of six referees read the same passages and concluded the paper demotes it in its own voice, evidences it on two cases, drops it from both of its literature counts, and lists six statistical limitations and none about explanation. **The risk the authors most needed to anticipate was the one they thought was their advantage.**

**One thing the table got exactly right, and it should not be lost.** Row F's pre-emption is the only one backed by a mechanism (the enforced abort). It is also the only one no referee attacked, and the office's counterweight findings (`DS-60`, `R5-68`, `R2-70`, `R4-42`) all point at the same disclosure apparatus. The authors' instinct — that honest disclosure is a contribution — was correct. Their execution error was believing it could be delivered in prose.
