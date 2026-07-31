# Verification record — editorial office audit of the six referee reports

Four examiners prosecuted the pooled Stage-1 findings against the manuscript (Examiner D additionally against the repository artifacts Referee 4 cited). Findings below are reproduced verbatim from the examiners' parts; this file reorders them by ID and groups them by disposition. No content has been paraphrased or dropped.

| Examiner | Findings prosecuted | Source reports |
| --- | --- | --- |
| A | 104 surviving | desk-screen (DS) and Referee 5 (R5) |
| B | 54 surviving | Referee 1 (R1) |
| C | 77 surviving | Referee 2 (R2) and Referee 3 (R3) |
| D | 47 surviving | Referee 4 (R4) |

| Disposition | Count |
| --- | --- |
| Raised at Stage 1 | 361 |
| CONFIRMED | 267 |
| PLAUSIBLE | 15 |
| MERGED / co-discovered into a survivor | 77 |
| KILLED outright | 2 (DS-06, R2-41) |
| Partially killed (survives narrowed) | 1 (DS-07) |

Kill rate is low because Stage 1 ran six referees over one manuscript: the dominant Stage-2 outcome was merging co-discovered findings, not refuting them.

---

## Verified findings — CONFIRMED

### DS-01 — CONFIRMED

> "**A site-as-unit certified selective-prediction gate.** … This is the central contribution; the site-count frontier is direct evidence that the combination is not free, since certification is feasible only above a data-dependent cluster count (E1, E4)." (§1, contribution 1)

I read all six experiments. E2's "uncorrected baseline" is CertGate's own *exchangeable assumption mode* — still site-as-unit — not a record-as-unit certificate. The record-level failure enters only by citation (§1 ¶4, §2.4, §4 opening, all to `@zhou2026falsesense`). No scoping passage anywhere defends the omission. The site-count frontier prices the *cost* of the design, which is not the same evidence as the *necessity* of it. Co-discovered by R1-12 and R1-62.

*(Examiner A)*

### DS-05 — CONFIRMED

> "# Figures" (line 298) … "**Figure 1. E1 in-distribution validity.**" (line 300) … "**Figure 6. E6 per-site coverage and answered error.**" (line 310)

Verified mechanically: the string `Figure N` occurs at lines 300, 302, 304, 306, 308, 310 **and nowhere else**; a search for `![`, `.png`, `.pdf`, `.svg`, `.jpg`, `includegraphics` returns zero matches. Six captions, no images, no in-text callout. Co-discovered by R5-15 (kept separate, see Merged note), R1-42, R2-30, R3-24/R3-46.

*(Examiner A)*

### DS-07 — CONFIRMED (narrowed)

> "All data used in this study are synthetic and generated deterministically by the included code, publicly available at [CODE REPOSITORY URL — to be added]." (§ Data availability)

The surviving limb is verified: the Data availability statement's operative content is a placeholder URL, and the manuscript carries **no Code availability section** (back matter runs Acknowledgements → Data availability → Funding → Author contributions → Ethics → Consent → Competing interests). The Funding / Author contributions / Competing interests `[TO BE COMPLETED]` limbs are killed under criterion 4 — see Kill log. Forward the narrowed finding only.

*(Examiner A)*

### DS-08 — CONFIRMED (and understated)

> "hierarchical conformal methods deliver coverage whose unit of independence is the group" (§1) · "the first two guarantee coverage, not selective risk" (§2.2) · "mean answered-set coverage 0.9722" (§4.2)

I enumerated all 27 occurrences of "coverage". There are not two senses but **three**: (a) conformal set coverage — §1, §2.2 ×4, §2.3, §2.4, §5.1 "per-record coverage statement"; (b) answered fraction — Abstract, §1, §3.5, §4.2, §4.5, §4.7, §5.3, Table 4; (c) **confidence-interval coverage** — §3.6 "δ_conf is a coverage statement over the S_aux bootstrap box", §3.7, §6.1, and A.2 "*corner-interval coverage*". None is defined. The nearest gesture is §2.1's "risk–coverage tradeoff", which the editor should note as a partial mitigation. Co-discovered by R2-31.

*(Examiner A)*

### DS-09 — CONFIRMED

> "This supports the certificate above rather than standing as an independent method (E5)." (§1, contribution 3) · "a supporting capability the linear head makes nearly free" (§3.8)

All limbs verified: features are indices 0–7 with no semantics (§4.1 "features 0–3 are informative and features 4–7 are noise"); §4.6 reports standardized importances, three case margins and one gap ranking — no faithfulness metric, no comparator explanation method, no clinician assessment anywhere; §6.1's six limitations are all statistical and none concerns explanation. Given the venue card names explainability as the *central* emphasis, this is a fit finding, not merely a coverage gap. Cross-noted with R5-67 (confidential) and R3-13/R3-41.

*(Examiner A)*

### DS-11 — CONFIRMED

> "This case study uses a deployment with threshold $\tau^* = 0.55$, answering 200 cases and declining 2." … "its mean absolute attribution is 0.868 on answered cases but 1.722 on declined cases, the largest answered-to-declined gap of any feature (gap $-0.854$; gap ranking $[0, 3, 2, 1, \dots]$; top gap feature 0). Declines are systematically the cases where feature 0's pull leaves the decision contested" (§4.6)

Both quotes sit in the same subsection, three paragraphs apart. An eight-feature gap ranking, a three-decimal cohort statistic, the adverb "systematically" and the Figure 5 caption's "dominant systematic abstention driver" all rest on n_declined = 2. Sharpened by R5-47 (verified separately): §4.6 reports features 0–3 at 1.157/1.161/1.178/1.155 — near-identical — so there is no stated mechanism by which feature 0 should separate, which is what makes the n=2 basis load-bearing rather than incidental. Five-way co-discovery (R5-14 merged; R1-30, R2-19, R3-07, R4-10).

*(Examiner A)*

### DS-14 — CONFIRMED

> "A safer design wraps the model in a *selective gate* … routing the hard ones to a clinician [@chow1970reject; @elyaniv2010selective]." (§1) · "Conformal prediction [@vovk2005algorithmic] gives distribution-free coverage under exchangeability of the calibration and test points — false under multi-site clustering" (§2.2)

I read all 31 bibliography entries. Confirmed absent: Dvijotham et al.; Barber, Candès, Ramdas & Tibshirani (`lee2025hierarchical` is Lee/Barber/Willett, a different paper); Tibshirani et al. on covariate shift; Ghassemi et al.; Rudin. Each is directly on-point for a passage the manuscript actually writes — most sharply Barber et al. against §2.2's exchangeability-failure argument, and Tibshirani et al. against §6.1's covariate-shift exclusion. §6.1's exclusion of a covariate-shift *mode* does not scope out *citing* the covariate-shift literature, so criterion 5 does not apply. Kept separate from R5-19, which names a disjoint set (Jones et al. ICLR 2021, Gibbs/Cherian/Candès) — the editor needs the union.

*(Examiner A)*

### DS-18 — CONFIRMED (survivor; R5-08 merged)

> "We deploy the maximum-coverage threshold in the certified prefix." (§3.5) · "The modes run as alternatives, each at full $\delta$, and we deploy the most conservative certified threshold." (§3.6, Combination)

Both sentences use the identical construction "we deploy the … threshold" with opposite selection rules. A reconciliation exists — §3.5 selects *within* a mode's certified prefix, §3.6 selects *across* the two modes — but the manuscript never states that the two operate at different levels, and §3.6's next sentence ("A mode is listed in the combined guarantee only if its own certified prefix contains the deployed threshold") presupposes a deployed threshold already chosen. Downgraded on that basis but real. Co-discovered by R1-53.

*(Examiner A)*

### DS-19 — CONFIRMED (one clause corrected)

> "We shift site-level prevalence from the source value of 0.095 up to a target base rate of 0.22" … "BBSE declines the remaining 95.5% of draws (decline rate 0.955)" (§4.3)

Single-magnitude limb verified: one shift, 0.095 → 0.22, is the only label-shift condition in the paper; there is no sweep. **Correction the editor must make:** the finding's clause "provides no evidence that the BBSE mode ever functions as a correction" overstates — 9 draws certified with 0 hard-violations is weak but non-zero evidence. Forward the finding as "the single-magnitude design cannot distinguish a working correction from a shift detector," which is what DS-57 and R4-44 independently reach.

*(Examiner A)*

### DS-20 — CONFIRMED (hedge noted)

> "Because every rate below is a proportion over $R = 200$ independent draws, we accompany the primary rates with exact (Clopper–Pearson) 95% confidence intervals." (§4.1)

I located every interval in the Results: exactly four (§4.2 [0.001, 0.036]; §4.3 [0.414, 0.557]; §4.3 [0, 0.018]; §4.4 [0.771, 0.879]). Omitted from: the 0/9 conditional rate, both decline rates, all four Table 1 exceedances, both overall exceedance rates, all twelve Table 4 certify rates, and every coverage mean. All four present intervals recompute correctly. The manuscript's hedge is the word "**primary**" — undefined, and the editor should note it gives the authors a defence for the certify/decline rates but not for the 0/9 headline.

*(Examiner A)*

### DS-21 — CONFIRMED

> "Given a genuinely poisonous shift, the $\alpha = 0.10$ certificate certifies all 200 draws and hard-violates 83% of them (hard-violation rate 0.83, exact 95% CI $[0.771, 0.879]$; exceedance 0.935)." (§4.4)

§4.3 names its modes explicitly ("the exchangeable baseline", "the BBSE label-shift mode"); §4.4 names none. Nothing elsewhere supplies it — §4.1's "mode FULL" is an implementation flag, not an assumption mode (DS-26). Since the whole point of E3 is that the assumption tag is load-bearing, not saying which tag was carried leaves the negative control's scope undetermined. Co-discovered by R1-56 (question form) and R1-11.

*(Examiner A)*

### DS-22 — CONFIRMED (facts; fit conclusion is the editor's)

> "The same certificate shape appears in power-grid contingency screening [@thermal2026audit], so it is not specific to medicine." (§2.4) · "so features 0–3 are informative and features 4–7 are noise" (§4.1) · "Applying CertGate to a real multi-site cohort is ongoing work." (§5.5)

Every factual limb verified, and the manuscript confirms one itself: "the study involves no human subjects and no patient data; all data are synthetic" (§ Ethics approval). §5.5 does offer a *defence* of the synthetic-only posture, which under criterion 5 would downgrade a demand for real data — but that defence ("Real data cannot supply that ground truth, which is what makes it unable to validate a validity claim") is the exact sentence R5-10 refutes from the paper's own §3.9, so the defence does not hold. The venue card's encouraged list (uncertainty quantification, calibration, OOD robustness, clinical auditability) does cover much of this work; whether the balance places it inside or outside the collection is the editor's call, not mine. I confirm the facts and flag the judgment.

*(Examiner A)*

### DS-23 — CONFIRMED (rationale corrected)

> "at $\alpha=0.10$ the gate certifies all 200 calibration draws at 0.9722 mean coverage with a hard-violation rate of 0.01 under a 0.05 budget" (Abstract)

All three terms verified undefined in the abstract, and "mean coverage" is additionally ambiguous across the three senses documented under DS-08. **Correction:** the abstract is **240** tokens by my count — at or against a typical 250-word Springer cap — so the finding's rationale "having room to define them" is unsupported. Forward the defect, drop the rationale; the fix is substitution of plain wording, not addition.

*(Examiner A)*

### DS-25 — CONFIRMED

> "we report exact additive attributions $\phi_j(x) = w_j(x_j - \mu_j)$ with $\text{logit}(\hat{p}(x)) = \text{base} + \sum_j \phi_j$. Here $w_j$ is the raw-feature-space coefficient, $w_j = \text{coef}_j / \text{sd}_j$, where $\text{coef}_j$ is the coefficient learned on standardized inputs and $\text{sd}_j$ the training-split standard deviation of feature $j$" (§3.8)

"base" is never defined anywhere in the manuscript. The sentence is conspicuous because it defines `w_j`, `coef_j` and `sd_j` with care in the same breath and leaves `base` — and `μ_j`, which DS-25 does not flag but R1-43, R2-45 and R3-22 do — undefined. Since exactness of the decomposition is the claim, the undefined intercept term is not cosmetic.

*(Examiner A)*

### DS-26 — CONFIRMED

> "Every experiment runs in mode FULL under protocol seed 20260721" (§4.1, Replication design)

"mode FULL" occurs once, is never expanded, and no alternative mode is named — so the reader cannot tell whether it is an assumption mode (which would answer DS-21), a fidelity setting, or a run profile. Co-discovered by R5-39, R1-35, R2-42.

*(Examiner A)*

### DS-27 — CONFIRMED

> "The cohort follows the specification frozen in `data.py`" (§4.1) · "the implementation includes a `from_raw` loader and a worked example" (§5.5) · "under a pinned environment (`requirements.txt`)" and "(`python -m experiments.run_synthetic`)" (A.3)

Four code artefacts referenced as resolvable, against "[CODE REPOSITORY URL — to be added]" (§ Data availability). Not a criterion-4 placeholder: the exempt class is author/affiliation/ORCID/corresponding-author identity fields, and a repository URL is a substantive availability claim. Five-way co-discovery (R5-40, R1-36, R2-40, R4-17).

*(Examiner A)*

### DS-28 — CONFIRMED

> "The test suite is 69/69 green." (Appendix A.3)

Verified verbatim. Properly framed as a reader-facing point ("unverifiable at review"), so it does not trip criterion 6 — the finding makes no claim about what the suite contains. A bare pass count with no statement of what is tested conveys nothing assessable; A.3 does describe one specific regression test (truncation anti-conservativity), which is the model the rest of the count should follow.

*(Examiner A)*

### DS-29 — CONFIRMED (survivor; R5-21 merged)

> "from the source value of 0.095 up to a target base rate of 0.22 — a near-tripling of outcome frequency" (§4.3)

Recomputed: 0.22 / 0.095 = **2.3158**. A 2.32-fold change is not a near-tripling; it is closer to a doubling. The same number is quoted in the Abstract and Figure 2 caption, so the correction propagates. DS-29's "2.32-fold" is exact; R5-21's "2.3-fold" is the same finding rounded.

*(Examiner A)*

### DS-30 — CONFIRMED

> "**Table 1. E1 realized exceedance by answered-set size bin ($\alpha = 0.10$), observed versus binomial reference.**" with reference column 0.4063 / 0.4689 / 0.4820 / 0.4915

Neither the caption nor §4.2 nor §3.9 states the n or p behind the reference column. The success probability is *inferable* (§4.2 calls it "the exceedance a perfectly valid boundary-case certificate would show", and §3.9 says "at the boundary the exceedance rate approaches 50% as batches grow", so p = α) — the editor should note that mitigation. The per-bin batch size is not recoverable at all, so the column cannot be regenerated, and Springer requires captions to stand alone. Co-discovered by R1-27.

*(Examiner A)*

### DS-31 — CONFIRMED (survivor; R5-25 merged)

> "with mean coverage 0.9304 at 150, 0.9715 at the realistic 208-site scale, 0.9601 at 300, and 0.9621 at 400" (§4.5)

Verified against Table 4. The sequence rises, dips, then rises — non-monotone — while §4.5's surrounding argument is that more clusters buy a better certificate. §4.5 *does* explain the E1-vs-E4 208-site difference ("a separate run from E1, with independently derived seeds — hence 0.9715 here against E1's 0.9722"), which shows the authors were alert to cross-run variation; it makes the silence on the within-sweep dip more, not less, conspicuous. No Monte-Carlo error is given at R = 200. Four-way co-discovery (R5-25 merged; R1-29, R2-36).

*(Examiner A)*

### DS-32 — CONFIRMED (survivor; R5-34 merged)

> `@inproceedings{ifac2025abstainexplain, … booktitle = {… (ECML PKDD 2024)}, … year = {2024}` (lines 249–260) · `@inproceedings{l2lore2025, … (DS-LB 2024)}, … year = {2024}` (lines 262–271) · `@article{angelopoulos2021ltt, … year = {2025}` (lines 169–181)

I checked the year field of all 31 entries: exactly **three** mismatch their key, and DS-32's count is right. The `ifac` prefix on an ECML PKDD paper (IFAC is the International Federation of Automatic Control) is the one that could mislead a copy-editor. Note for the editor: pandoc renders the *year field*, not the key, so this will not surface as an in-text year error — it is bibliography hygiene, correctly rated minor by DS. Five-way co-discovery (R5-34 merged; R1-37, R2-38, R3-28, R4-27).

*(Examiner A)*

### DS-33 — CONFIRMED (survivor; R5-35 merged)

> "% CertGate manuscript references — every entry verified against its primary source on 2026-07-24
> % (arXiv abstract page, DOI/Crossref record, or publisher/proceedings page; see paper/TODO.md for
> % the one unverified candidate, scireports2026deferral, which is deliberately NOT in this file)." (references.bib lines 1–3)

Verbatim, lines 1–3. The comment points at an internal to-do file and names a rejected citation candidate. It will not render, but the `.bib` is part of the submitted package and is read by editors and production. Four-way co-discovery (R5-35 merged; R1-38, R2-39).

*(Examiner A)*

### DS-36 — CONFIRMED

> "the ~0.4-point gap between the BBSE-implied and oracle fractions is the visible cost of the label-shift correction's estimation step" (§4.7)

Recomputed: 0.0630 − 0.0591 = **0.0039**, i.e. 0.39 **percentage points**. The two operands are given as fractions on [0,1] in the immediately preceding sentence and in Table 3, so "0.4-point" invites reading as 0.4 on that same scale — a hundredfold error. The fix is one word ("percentage points"). Co-discovered by R1-51.

*(Examiner A)*

### DS-37 — CONFIRMED (survivor; R5-51 merged; count is an undercount)

> "We do not paper over this." (§3.6) · "Demonstrating the failure openly is validation rigor" (§4.4) · "the reading is honest" (§4.7) · "Its posture throughout is disclosure" (§6)

I enumerated the motif and found **at least twelve** instances, not eight — additionally §1 "the rigor that constructively answers"; §3.6 "We disclose plainly"; §3.7 and §6.1 "disclosed wherever the guarantee is stated" (×3 with §1); §4.4 "This check is enforced, not decorative"; §5.5 "a deliberate validation choice, not a deferral"; §6.1 "We state the boundaries … plainly" and "none is patched over in the results". The finding's count is conservative. **The editor must read this together with DS-60**, which is the same referee warning that the underlying disclosures are the manuscript's strongest feature and must not be sanded down when the register is trimmed.

*(Examiner A)*

### DS-38 — CONFIRMED

> "For any reader tempted to call $\alpha=0.10$ a weak guarantee: the operative rung is a property of the available cluster count, not of the method" (§5.2) · "That is not a defect; it is what a selective gate on a low-prevalence task should do." (§4.7) · "A negative control that cannot fail proves nothing." (§4.4)

All three verified verbatim. Distinct from DS-37: this is anticipatory argument with an imagined critic, not self-attestation. Note the §5.2 instance is doubly exposed — R5-11 independently attacks its *substance* ("not of the method" is unsupported without any comparator), so the sentence should be cut on both grounds. Co-discovered by R1-41.

*(Examiner A)*

### DS-40 — CONFIRMED

> "each site receives a *data-independent* influence weight $g_c = \min(n_c, M)$ with $M = 100$" (§3.3) · "(i) the worst-case confusion gap $(c_1 - c_0) < 0.10$ … (ii) fewer than 2,000 valid resamples within 4,000 attempts" (§3.6)

No justification is offered for any of the three values, and no sensitivity analysis appears anywhere. §3.2's pre-registration argument defends *fixing* the constants a priori — "it removes the degrees of freedom that would otherwise let a tunable pipeline flatter itself" — which is an argument for immutability, not for the values chosen; it therefore does not scope the objection out under criterion 5. M = 100 is the most consequential: at the generator's clipped-lognormal maximum of 5,000 records, it caps a site's weight at 1/50 of its record count (see R5-26). Co-discovered by R1-50.

*(Examiner A)*

### DS-41 — CONFIRMED

> "what a clinician weighs before trusting an automated triage, and what an auditor asks to see documented" (§1, ¶1)

Verified: no citation on the sentence, and no evidence anywhere in the paper bears on clinician or auditor behaviour (no human evaluation, no survey, no governance reference). In a general ML venue this would be ordinary motivational framing; in a collection whose stated emphasis is explainability as a transparency requirement *and an educational aid for clinicians*, an uncited empirical claim about what clinicians weigh is squarely in scope. Co-discovered by R3-33.

*(Examiner A)*

### DS-42 — CONFIRMED

> "We consider multi-site clinical data in which on the order of two hundred collection sites each contribute between 20 and 5,000 records, the outcome prevalence is roughly 9–10%" (§3.1) against "208 collection sites … clipped to $[20, 5000]$ … The base outcome prevalence is 0.095." (§4.1)

The general problem setting and the specific generator agree to the digit on all three parameters. That is only circular if the generator's realism is unsupported — and it is precisely R5-13 that shows the realism claim rests on a reporting checklist and a cross-validation methods paper. The two findings interlock: fix R5-13 and DS-42 dissolves; leave R5-13 and §3.1 is a description of `data.py`, not of clinical data.

*(Examiner A)*

### DS-46 — CONFIRMED

> "This case study uses a deployment with threshold $\tau^* = 0.55$, answering 200 cases and declining 2." (§4.6) against "a grid of 23 values evenly spaced in $[0.55, 0.99]$" (§3.5) and "threshold $\tau^* = 0.77$" (§4.7)

τ* = 0.55 is the exact minimum of the frozen grid, and since the score is bounded below at 0.5 (§3.1, "$s(x) \in [0.5, 1]$"), it is the operating point at which abstention is rarest — 2 declines in 202 cases, ~0.99 coverage. The subsection whose entire subject is *declined* cases is run where declines barely occur, with no rationale given and no statement that this deployment was certified. Distinct from R5-41 (which is about certified thresholds never being reported at all); the two should travel together. Co-discovered by R3-12, R3-36, R4-10.

*(Examiner A)*

### DS-47 — CONFIRMED (question stands)

> "$$R_M = \frac{\sum_c g_c\, a_c\, e_c}{\sum_c g_c\, a_c},$$" (§3.3) against "the influence-weighted answered-set risk … at a new target site is at most $\alpha$" (§3.1)

The manuscript never states the index set of $c$. A.1(ii) makes it worse rather than better: "the denominator $\sum_c g_c a_c$ of $R_M$ is non-random and $\mathbb{E}[R_M]$ is a ratio of expectations" reads as a cross-site population quantity. The question is unanswered anywhere and is the remedy half of R5-01; both must go forward.

*(Examiner A)*

### DS-48 — CONFIRMED (survivor; R5-54 merged)

> "the BBSE-implied true-class fraction is 0.0591 (expected 1,378.9 positives, $\hat{\rho} = 0.830$, tagged estimated under the label-shift assumption)" (§4.7, Table 3)

§3.6 defines ρ as "the target-to-source odds ratio of the positive class", so no shift implies ρ = 1; 0.830 is a 17% departure. That E6 is unshifted is not stated outright but is available from §4.7's own "the ~9.5% cohort prevalence" — the editor should note this, because the manuscript never states E6's shift status *at all*, which is itself part of the answer required. DS-48's second limb (does the same departure operate in E2, and in which direction relative to safety) is the one that matters, since R5-06 shows the E2 safety headline rests on 9 draws. Co-discovered by R1-58, R1-08, R4-38.

*(Examiner A)*

### DS-49 — CONFIRMED (question stands)

> "The modes run as alternatives, each at full $\delta$, and we deploy the most conservative certified threshold. … so the OR-guarantee reads \"if *either* tagged assumption holds…\"" (§3.6, Combination)

No combined error probability is stated anywhere. The manuscript's per-mode conditional statements are individually 1−δ, but a deployer who does not know which assumption holds and takes whichever mode certifies faces a union that the "if either" wording does not price. Note a second, separate discrepancy inside the same anchor: §3.6 says "each at full δ" while §3.5 says "$\delta$ for the baseline, $\delta_{\text{bet}}$ in the label-shift mode" — δ_bet = 0.025, i.e. half. Independently reached as a major by R1-04; R4-19 flags the δ discrepancy.

*(Examiner A)*

### DS-52 — CONFIRMED (question stands)

> "the $\alpha = 0.10$ rung certifies every one of the 200 draws (certify rate 1.0) at mean answered-set coverage 0.9722" (§4.2)

The weighting is stated nowhere for E1. The contrast is telling: Table 2's column is explicitly labelled "**Mean per-site** coverage", so the authors label weighting when they choose to. The question is compounded by R5-62 — "target pool" occurs exactly **once** in the whole manuscript (§3.9, line 138) and is never defined — so the reader cannot even determine what population the 0.9722 averages over.

*(Examiner A)*

### DS-53 — CONFIRMED (question stands)

> "The route to real data is concrete: the implementation includes a `from_raw` loader and a worked example that carries a cohort through the same site-disjoint pipeline. Applying CertGate to a real multi-site cohort is ongoing work." (§5.5)

Properly framed as what the manuscript describes, so criterion 6 does not apply. The manuscript asserts the route is "concrete" and simultaneously that application is "ongoing work," without saying whether a cohort was sought, obtained, or attempted, or what blocked it — the one fact that would let a reader price "ongoing".

*(Examiner A)*

### DS-54 — CONFIRMED (question stands)

> "BBSE declines the remaining 95.5% of draws (decline rate 0.955) rather than issue an unsupported certificate, and both modes decline entirely at $\alpha = 0.05$." (§4.3)

Unanswered anywhere; the paper reports one shift magnitude. This is the constructive remedy for DS-19 and DS-57 and should be forwarded with them as a single revision request: sweep the shift magnitude and report certify rate, decline rate and conditional hard-violation rate across it. Co-discovered by R1-57.

*(Examiner A)*

### DS-55 — CONFIRMED (confidential; editorial recommendation)

> "*(iii) Supermartingale.* The bet $\lambda_t$ is predictable — a function only of atoms already processed — and its cap at $0.9/(1-\alpha)$ keeps every factor $1 + \lambda_t(\alpha - Z_t) \ge 0.1 > 0$" (A.1) · "the sign that decides certification factors as $\operatorname{sign}(\mathbb{E}[Z(\rho)] - \alpha) = \operatorname{sign}(A + \rho B)$" (A.2)

Both anchors verified. The recommendation is well grounded: per the venue card, neither collection editor's stated expertise (Barbierato — performance evaluation, Green AI, philosophy of AI; Striani — AI in healthcare, process mining, medical informatics, XAI education) reaches betting supermartingales or affine-endpoint soundness, and my own prosecution of R5-02 shows the A.1(ii)/A.1(iii) conditioning gap is exactly the kind of defect only a distribution-free-inference referee will catch. R1's independent arrival at the same objection (R1-02, R1-55) is evidence the recommendation is necessary rather than precautionary.

*(Examiner A)*

### DS-56 — CONFIRMED (confidential; survivor, R5-65 merged)

> "Under a prevalence shift from 0.095 to 0.22, the uncorrected baseline certifies and violates in 48.5% of draws, while the corrected mode never does, declining in 95.5% instead." (Abstract)

Both limbs verified independently: the record-level premise is carried entirely by `@zhou2026falsesense` and is never reproduced in the paper's own oracle-equipped harness (DS-01), and "the corrected mode never does" is 0/9 with an exact upper bound of 0.3363 that the manuscript omits (R5-06). The observation that the abstract's two strongest sentences are its two thinnest is the correct editorial framing and should shape the decision letter's ordering. R5-65 states the same for the second limb alone.

*(Examiner A)*

### DS-57 — CONFIRMED (confidential)

> "The two confidence budgets combine as $\delta_{\text{conf}} + \delta_{\text{bet}} = \delta$ with $\delta_{\text{conf}} = \delta_{\text{bet}} = 0.025$" (§3.6) · "decline rate 0.955" (§4.3) · "about 83 calibration clusters" (§3.5)

All three verified, as is the Bonferroni mechanism ("a Bonferroni percentile box on $(c_0, c_1, \pi_{\text{source}})$ at level $\delta_{\text{conf}}/3$, propagated to a weight interval"). The referee's honesty about what could not be determined is correct and important: at 83 clusters, δ halved, a Bonferroni-widened ρ interval, and both endpoints required to reject, "correctly calibrated refusal" and "underpowered mode" predict the same 95.5%. Independently reached by R1-67 and — with artifact access — by R4-44, which reports the discriminating diagnostics are computed and then discarded.

*(Examiner A)*

### DS-58 — CONFIRMED (confidential)

> "The same certificate shape appears in power-grid contingency screening [@thermal2026audit], so it is not specific to medicine." (§2.4) · "a supporting capability the linear head makes nearly free" (§3.8)

Both verified verbatim. The observation is sharp because the two sentences are the paper's own: the manuscript volunteers that its contribution is domain-general and that the collection's central emphasis is a by-product of a design choice made for other reasons. R5-33 adds the structural corroboration — explainable abstention is one of the four literatures in §2 but is dropped from both the §1 and §6 three-counts. Cross-noted with DS-09, DS-22, R5-67, R3-41/R3-45.

*(Examiner A)*

### DS-59 — CONFIRMED (confidential; survivor, R5-66 merged)

> `@misc{zhou2026falsesense, … eprint = {2606.15153}` · `@misc{triage2026audit, … eprint = {2605.20956}` · `@misc{yu2026joint, … eprint = {2606.08517}`

I counted the bibliography: **exactly 7 of 31** entries are `@misc` arXiv preprints dated 2025–26 (zhou2026falsesense, triage2026audit, yu2026joint, score2026, scrc2025, fedcrc2026, thermal2026audit). The three named carry, respectively, the motivating 9–30% figure (§2.4), the prevalence-shift gap claim (§2.4), and the closest-work characterization on which contribution 1's novelty entirely rests (§2.1). The spot-check instruction is correct and actionable. R5-66 reaches the same conclusion by a different route and adds the "published" mislabel, which R5-18 carries as a major.

*(Examiner A)*

### DS-60 — CONFIRMED (confidential; **counterweight — must travel with DS-23, DS-37, DS-38, R5-45, R5-51**)

> "Meeting the $\le \delta$ target therefore evidences the *absence of gross violations at the tested power*, rather than confirming validity against arbitrarily small excesses." (§3.9) · the five-clause guarantee (§3.7)

I ran the referee's search myself. Scanning for `novel`, `unprecedented`, `state-of-the-art`, `for the first time`, `we are the first`, `paradigm`, `breakthrough` returns **zero hits**; every occurrence of "first" in the manuscript is ordinal or sequential ("first appears at 300", "the first two guarantee coverage", "stops at the first failure", "the first number", "the first four coordinates"). The scoping clauses in §3.7 and §3.9 are genuinely stronger than typical. The warning is therefore load-bearing, not decorative: my own register findings (DS-23, DS-37, DS-38, R5-45, R5-51) all ask for *less* prose, and the editor must ensure the decision letter does not read as an invitation to replace hedges with confidence. A revision that adds assertion instead of experiments would be a worse paper.

---

*(Examiner A)*

### R1-01 — **CONFIRMED**

> §3.1: "the influence-weighted answered-set risk — the parameter $R_M$ defined in Section 3.3 — at a new target site is at most $\alpha$" · §3.7: "(1) It is scoped per target site." · §3.3: "$R_M = \frac{\sum_c g_c\, a_c\, e_c}{\sum_c g_c\, a_c}$"

$R_M$ as displayed sums over sites; A.1(ii) establishes only that the atom mean "sits on the same side of
$\alpha$ as $R_M$" — an aggregate statement. I searched §3, A.1 and A.2 for a transport step to a single
new site and there is none. The nearest thing to a defence is §3.3's "Three scope facts follow directly —
per-target-site scope…", which asserts the conclusion without deriving it; and under exchangeability the
most one recovers is the *expected* risk of a randomly drawn target site, which is the marginal claim
again. Co-discovered by DS-02 and R5-01 — three independent referees on the same gap.

*(Examiner B)*

### R1-02 — **CONFIRMED** (with a sharpened counterexample)

> A.1(ii): "Because the estimand is design-conditional, the answered fractions $a_c$ and weights $g_c$ are fixed functions of observed features" · A.1(iii): "under $H_0$, $\mathbb{E}[\,1 + \lambda_t(\alpha - Z_t) \mid \mathcal{F}_{t-1}\,] \le 1$, so $K_t$ is a nonnegative supermartingale"

Both quotes verbatim. Under design-conditioning the atoms are independent with *site-specific* means
$\mu_c$, so A.1(iii)'s conditional inequality evaluates to $1 + \lambda_t(\alpha-\mu_t)$, which exceeds 1
for any site with $\mu_t < \alpha$ — the supermartingale property fails atom-wise, before any product is
formed. The manuscript states no i.i.d.-over-sites assumption anywhere (§3.6's "exchangeable" tag concerns
target-vs-calibration, not calibration sites among themselves).

*Correction to the referee, which strengthens rather than weakens him:* his illustrative bets
$(\lambda_1,\lambda_2)=(1,0.01)$ are **not producible by the manuscript's own schedule** — with
$\hat\sigma^2 \le 0.25$ and $n\approx 83$, $\lambda_t$ is confined to roughly $[0.54, 1.0]$. The objection
does not need them: a realizable pair $(\lambda_1,\lambda_2)=(1.0,\,0.5)$ with
$(\alpha-\mu_1,\alpha-\mu_2)=(+0.5,-0.5)$ — average atom mean exactly $\alpha$, so $H_0$ holds — gives
$\mathbb{E}[K_2] = 1.5\times0.75 = 1.125 > 1$. Forward the realizable version.

*(Examiner B)*

### R1-03 — **CONFIRMED** (second clause corrected)

> §3.3: "constructed so that $\mathbb{E}[Z] \le \alpha \iff R_M \le \alpha$" · A.1(ii): "$\mathbb{E}[R_M]$ is a ratio of expectations with no approximation"

The primary defect is real: §3.3 defines $R_M$ over realized sites with realized $e_c$ and states the
bridging identity at the realized level ("the inner sum collapses to $n_c a_c(e_c-\alpha)$"), then asserts
an equivalence between $\mathbb{E}[Z]$ (a number) and $R_M$. §3.7(3) and §5.1 both turn on the
parameter/realization distinction that this definition leaves ambiguous. **But the referee's second clause
misfires:** A.1(ii) does not bare-assert that $\mathbb{E}$ of a ratio is a ratio of $\mathbb{E}$s — it
derives it from a stated premise ("the denominator … is non-random and"), and given that premise the
implication is valid. That clause is therefore parasitic on R1-02 and should not be forwarded as an
independent error.

*(Examiner B)*

### R1-04 — **CONFIRMED**

> §3.6: "The modes run as alternatives, each at full $\delta$, and we deploy the most conservative certified threshold. … so the OR-guarantee reads 'if *either* tagged assumption holds…'"

Verbatim. The only union bound in the manuscript is the intra-mode
$\delta_{\text{conf}}+\delta_{\text{bet}}=\delta$; nothing anywhere states the exposure of the *deployed*
decision across two independently-budgeted modes, nor across §3.5's "Both budgets $\alpha \in \{0.05,
0.10\}$ … certified by separate walks." The clause "A mode is listed … only if its own certified prefix
contains the deployed threshold" restricts *listing*, not the union over false-certification events.
Co-discovered by DS-49 and R4-39.

*(Examiner B)*

### R1-05 — **CONFIRMED** (primary claim; secondary claim needs one datum)

> §3.9: "A certificate counts as violated only when the one-sided 95% Wilson lower confidence bound on the target pool's answered error exceeds $\alpha$ [@wilson1927]."

The functional mismatch is confirmed outright: the certified object is influence-weighted
($g_c=\min(n_c,100)$) and cross-site; the screened object is the unweighted answered error of a target
pool, and the manuscript nowhere relates the two or bounds the gap. §3.9's closing paragraph disclaims
that the guarantee rests on the harness, but never addresses the functional mismatch.

The secondary claim — that the record-level i.i.d. binomial device inflates E2's 48.5% and E3's 83% —
turns on whether a "target pool" spans sites, which the manuscript never defines (independently flagged by
R2-34 and R5-62). My Table 1 arithmetic above shows E1 uses one pool per draw; if that pool is one site,
then *conditional on the site*, §4.1's generator does make records independent and the Wilson device is
defensible. **The single check:** state the composition of a target pool. If it is one site, only the
functional-mismatch half of R1-05 should be forwarded.

*(Examiner B)*

### R1-06 — **CONFIRMED**

> §3.9: "We require this to hold for at most $\delta$ of certificates" · §4.2: "The hard-violation rate is 0.01 (2 of 200 …), at or below $\delta = 0.05$"

Arithmetically unavoidable: a one-sided 95% lower confidence bound exceeds the true parameter with
probability ≈ 0.05 by construction, so a system sitting exactly at $R_M=\alpha$ — the tightest *valid*
system — trips the screen at ≈ 0.05 = $\delta$, and "hard-violation rate $\le\delta$" is satisfied at the
margin by construction. In the manuscript's favour, §3.9 already concedes the adjacent point ("Meeting the
$\le \delta$ target therefore evidences the *absence of gross violations at the tested power*") — the
editor should note that concession. What §3.9 does **not** say is that the screen's own error rate and the
confidence budget share the numeral 0.05, which is the confusability R1-06 identifies.

*(Examiner B)*

### R1-07 — **CONFIRMED**

> §3.6: "observe the target predicted-positive rate $q$ (which is exact under the design-conditional estimand), and invert the black-box shift equation $q = c_0(1-\pi_t) + c_1\pi_t$"

The parenthetical conflates two things: $q$'s *value* is indeed exactly observed (given fixed features,
$\hat y_i$ is deterministic), but the shift equation is a population identity, and substituting a realized
$q$ from a finite target batch for its population counterpart leaves an $O(n_{\text{target}}^{-1/2})$ error
in $\hat\pi_t$ and hence $\hat\rho$. The box is stated over $(c_0,c_1,\pi_{\text{source}})$ only; nothing
in §3.6, A.2 or §6.1 carries a target-size term, and §3.1 admits sites as small as 20 records.

*(Examiner B)*

### R1-08 — **CONFIRMED**

> §3.6: "We disclose plainly that this percentile bootstrap box is the single asymptotic step in an otherwise finite-sample chain" · Table 3: "1,378.9 expected ($\hat{\rho} = 0.830$)"

I searched all six experiments: no reported coverage of $[\rho_{\text{lo}},\rho_{\text{hi}}]$ for the true
$\rho$, anywhere. The step carrying $\delta_{\text{conf}}=0.025$ is disclosed and unmeasured. The
$\hat\rho=0.830$ observation is properly hedged as "apparently unshifted" — and the manuscript's silence on
whether E6 involves a shift is itself the reason the referee has to hedge (§4.7 gives only "a separate
deployment (threshold $\tau^*=0.77$; 40 target sites)"). Co-discovered by DS-48 and R5-54; R4-16/R4-38
reach the same place from the artifact side.

*(Examiner B)*

### R1-09 — **CONFIRMED**

> §4.3: "conditioning on the 9 draws that did certify ($n_{\text{certified}} = 9$), the hard-violation rate among them is 0.0" · Abstract: "the corrected mode never does, declining in 95.5% instead"

Verified: the 0/9 rate is the one rate in §4.2–§4.7 carrying no interval, against §4.1's promise to
"accompany the primary rates with exact (Clopper–Pearson) 95% confidence intervals." Its exact upper bound
is 0.336 — I recomputed it. And no experiment reports BBSE's behaviour under no shift: §4.2 breaks E1 out
by $\alpha$ rung only, never by mode. Co-discovered by DS-03, R2-03 and R5-06 — four independent referees,
which is as strong a signal as this pool produces.

*(Examiner B)*

### R1-10 — **CONFIRMED**

> §3.4: "an *information floor* $\ln(1/\delta)(1-\alpha)/n$ — a linearized, zero-variance lower bound" · §5.2: "the operative rung is a property of the available cluster count, not of the method" · §1: "a property of how many hospitals contribute, not of the method"

The floor is derived from this construction's linearization and $\lambda$ cap; no minimax lower bound over
procedures is proved or claimed anywhere. §3.4's qualifier ("used strictly as a feasibility diagnostic,
never a gate") governs its *use*, not its generality, so it does not license the twice-repeated "not of the
method," which is a statement about all procedures. The same overreach sits in contribution 1
("the site-count frontier is direct evidence that the combination is not free").

*(Examiner B)*

### R1-11 — **CONFIRMED**

> §4.4: "We inject a posterior tilt (concept intercept 2.0) and the harness first *verifies the poison*"

Both halves check out. No generative equation for the tilt appears in §4.4, §4.1 or anywhere else; §4.1
gives only $\pi_c = \sigma(\mathrm{logit}(0.095)+u_c)$. And neither §4.4 nor Figure 3's caption names the
assumption mode that produced the 83%. The arithmetic worry is well founded: under §4.1's class-conditional
Gaussian generator the posterior logit is linear in $x$ plus a prior-odds intercept, so adding 2.0 is a
prior-odds multiplication by $e^2\approx7.4$ — whether that is concept shift or label shift depends on
whether $x$ is redrawn from the retilted mixture, which the manuscript does not say. Properly framed as
"the manuscript does not tell the reader," so it clears the access rule.

*(Examiner B)*

### R1-12 — **CONFIRMED** (headline overstated; substance intact)

> §1: "a failure recently documented for record-level selective-risk rules under grouped deployment [@zhou2026falsesense]"

I read §4.2–§4.7 for comparators. Neither a record-as-unit certificate nor any external method appears in
any experiment. **Correction:** the headline "no baseline of any kind" is too strong — §4.3 does run an
"uncorrected baseline," and the manuscript calls it that. What is true, and is what the referee's own body
text says, is that E2's baseline is an *internal ablation of the same system*, so the motivating
record-as-unit failure is imported from a preprint rather than demonstrated in an oracle-equipped harness
built for exactly that job. Forward the corrected wording. Co-discovered by DS-01 and DS-15.

*(Examiner B)*

### R1-14 — **CONFIRMED**

> §3.3: "$g_c = \min(n_c, M)$ with $M = 100$" · §4.1: "clipped lognormal (log-mean 6.0, log-sigma 1.1, clipped to $[20, 5000]$)"

I computed the implication myself: median site size $e^{6.0}=403$, and **89.8% of sites exceed 100
records**, so $g_c$ is pinned at $M$ for roughly nine sites in ten and $R_M$ is close to an unweighted
per-site average. A 5,000-record hospital and a 100-record one carry identical influence. Neither
consequence is stated; no experiment reports the record-level answered error alongside $R_M$; $M$ is never
varied. Co-discovered by R2-04/R2-63 from the clinical side.

*(Examiner B)*

### R1-15 — **CONFIRMED**

> A.2: "$\operatorname{sign}(\mathbb{E}[Z(\rho)] - \alpha) = \operatorname{sign}(A + \rho B)$ with $(A, B)$ free of $\rho$" · "The argument is pinned numerically in the test suite"

$A$ and $B$ appear exactly once in the manuscript and are never defined in terms of atoms, weights or
$w_{\max}=\max(1,\rho)$. There is no theorem environment, no numbered assumption list, and no proposition
covering the composed deployed procedure (walk × two modes × two rungs × endpoint pair) — A.1 covers one
test, A.2 one endpoint pair. The referee is not asserting a fact about the test suite; he is saying a
mathematical claim cannot be verified by report of a passing test, which is within his access.

*(Examiner B)*

### R1-16 — **CONFIRMED**

> §5.5: "Real data cannot supply that ground truth, which is what makes it unable to validate a validity claim."

The manuscript's own §3.9 violation protocol consumes only realized answered errors and a Wilson bound —
both computable from observed outcomes in a retrospective multi-site cohort. So the epistemic claim as
written is too strong, and it is the load-bearing justification for a synthetic-only evidence base in a
clinical collection. This is not a defended scope boundary under my criterion 5: the accompanying
statement ("Applying CertGate to a real multi-site cohort is ongoing work") is an admission, and the
defence offered rests on the premise being challenged. Co-discovered by DS-10, R2-26 and R5-10.

*(Examiner B)*

### R1-17 — **CONFIRMED**

> §3.1: "Cluster-as-unit distribution-free inference has precedent in the conformal literature [@dunn2023hierarchical; @lee2025hierarchical]; we adopt it as the foundation of the certificate."

I checked all 31 bibliography entries: none of the nine named works is present — Barber–Candès–Ramdas–
Tibshirani (2021), Jung et al., Bastani et al., Snell et al., Lu et al., Cortes–DeSalvo–Mohri, Tibshirani
et al. (2019), Barber et al. (2023), Jones et al., Field–Welsh, Aas et al. The characterization of
BCRT-2021 as adverse to §3.7(1) is correct: it is the impossibility result for non-trivial distribution-free
conditional inference, which is precisely the claim R1-01 challenges. *Minor location slip:* the anchored
sentence is in §3.1 (line 62), not §3.2 as the index states. Quote is verbatim; the slip is not a defect
in the finding.

*(Examiner B)*

### R1-18 — **CONFIRMED**

> §3.8: "For a linear model these attributions are exact Shapley values, with no approximation or sampling [@lundberg2017shap]." · §4.6: "genuine Shapley values, not sampled approximations"

$\phi_j = w_j(x_j-\mu_j)$ is the Shapley value of a linear model under the interventional value function,
or under the conditional one *given feature independence* — the assumption behind Lundberg & Lee's
LinearSHAP. §4.1's generator ("the class signal lives on a single normalized direction supported on the
first four coordinates") makes features 0–3 marginally correlated through the class label, since the
mixture covariance is $I + \pi(1-\pi)\,\mathrm{sep}^2 vv^\top$. No caveat appears at either site; exactness
is stated twice, unqualified. Independently found by DS-16, R2-24, R3-01, R4-15 and R5-12 — the most
heavily co-discovered finding in the pool, and the one that lands in the collection's central emphasis.

*(Examiner B)*

### R1-19 — **CONFIRMED**

> §4.1: "This follows the distributional profile reported across multi-site clinical studies … [@tripodcluster2023; @internalexternal2021]" · §1: "whose lognormal sizes, ~9.5% prevalence, and site random effects follow the distributional profile reported for large multi-site clinical cohorts"

From the bib entries themselves: `tripodcluster2023` is the TRIPOD-Cluster *reporting checklist* (BMJ
2023); `internalexternal2021` is Takada et al.'s *methodological* IECV study (J Clin Epidemiol 2021).
Neither is a source for log-mean 6.0, log-sigma 1.1, prevalence 0.095, or a site random-effect SD of 0.5.
The §4.1 sentence attaches the citation to a paragraph whose subject is the generator's numbers, and §1
makes the same realism claim with no citation at all. No "these values are illustrative" disclaimer exists
anywhere. Co-discovered by DS-04, R2-11 and R5-13.

*(Examiner B)*

### R1-20 — **CONFIRMED**

> §2.4: "certified record-level selective-risk rules overrun their budget by 9–30% under grouped deployment [@zhou2026falsesense]" · §2.1: "Yu and Liu [@yu2026joint] are closest"

Verified against the bib: `zhou2026falsesense`, `triage2026audit`, `yu2026joint`, `score2026`, `scrc2025`,
`fedcrc2026`, `thermal2026audit` are all `@misc` arXiv entries, 2025–26, none with a refereed venue. Two
carry only "submitted to" notes. Between them they carry the motivating quantitative claim, the closest-
competitor identity (and hence the novelty delta), and §5.4's federated positioning. Nowhere in the text is
any of them attributed as a preprint; §1 contribution 4 goes the other way and calls `zhou2026falsesense`
"a **published** diagnosis."

*(Examiner B)*

### R1-21 — **CONFIRMED**

> §3.2 and §4.1: "$S_{\text{cal}}$ … touched exactly once, by the certification test" · §3.5: "we walk the grid in a fixed sequence … the walk stops at the first failure"

23 grid points × 2 modes × 2 rungs = up to 92 tests against the same pool. The fixed-sequence construction
may control FWER within one walk, but "touched exactly once" is not a description of what happens, and it
is the sentence a reader leans on to believe the calibration pool is uncontaminated. Co-discovered by
R2-32; R4-09 finds additional reads of the same pool from the artifact side.

*(Examiner B)*

### R1-22 — **CONFIRMED**

> §3.6: "fewer than 2,000 valid resamples within 4,000 attempts, a degenerate bootstrap pool for which we refuse to take quantiles over a silently reduced draw count" · A.2: "requires 2,000 valid resamples within at most 4,000 attempts"

"Valid" is never defined anywhere in the manuscript. Quantiling over the retained set is the bootstrap
distribution *conditional on validity*, and the manuscript's stated rationale (protecting against a reduced
draw count) addresses Monte-Carlo error, not selection. Nothing in §3.6 or A.2 argues the selection is
ignorable, and $\delta_{\text{conf}}$'s coverage claim is stated as if it were not there.

*(Examiner B)*

### R1-23 — **CONFIRMED** (count corrected)

> §3.2: "This is a lightweight, machine-verifiable substitute for pre-registration: it removes the degrees of freedom that would otherwise let a tunable pipeline flatter itself." · §3.10: "(a lightweight, machine-verifiable substitute for pre-registration)"

The substance is right: a unit test asserts that constants presently equal certain literals; it carries no
timestamped commitment that they were fixed before results were seen, which is the entire content of
pre-registration. **Correction:** the pre-registration *phrase* appears **twice** (§3.2, §3.10), not three
times; A.3 restates the pinning without the pre-registration claim. Co-discovered by R5-17; R4-02/R4-43
show from the artifact that the claim is additionally false for the experiment-defining constants, which
the editor should read alongside this.

*(Examiner B)*

### R1-24 — **CONFIRMED** (one clause partly answered)

> §3.4: "$\lambda_t = \min(\sqrt{2\ln(1/\delta)/(\hat{\sigma}^2_{t-1} n)},\ 0.9/(1-\alpha))$, with a variance floor of $10^{-8}$ and the running mean and variance $(\hat{\mu}, \hat{\sigma}^2)$ initialized at $(0.5, 0.25)$"

Three of four sub-claims hold cleanly: bare $n$ is defined nowhere (the manuscript elsewhere uses $n_c$,
$n_{\text{cal}}$, and $n$ for pool counts in Table 1); $\hat\sigma^2_{t-1}$ is never given as an estimator;
$\hat\mu$ is initialized and appears in no displayed formula. **The fourth is partly answered:** §3.5 says
"each is tested at the mode's full betting budget ($\delta$ for the baseline, $\delta_{\text{bet}}$ in the
label-shift mode)," which settles which budget the BBSE test spends even if not the $\ln(1/\delta)$ inside
$\lambda_t$. Absorbs R1-48 and R1-60.

*(Examiner B)*

### R1-25 — **CONFIRMED**

> §3.4: "We test the null … with the Waudby-Smith–Ramdas betting martingale for means of bounded random variables [@waudbysmith2024betting]."

WSR's predictable-mixture bet scales as $(\hat\sigma^2_{t-1}\,t\log(1+t))^{-1/2}$; the displayed schedule
substitutes a fixed $n$. The referee grants that a data-independent $n$ preserves predictability and hence
validity — his claim is only that the deviation from the cited construction is not stated, and it is not.
This is a characterization of a cited published work, which is within a manuscript-only referee's remit.

*(Examiner B)*

### R1-26 — **CONFIRMED**

> §5.1: "E1 shows realized exceedance rising toward its binomial reference (0.0551 against 0.4915 in the largest size bin)" · §4.2: "the observed exceedance sits far below the reference (… 0.0551 against 0.4915 in the largest bin)"

Same two numbers, opposite descriptions, nine-fold apart. §5.1 misdescribes its own data and undercuts
§4.2's correct reading. Co-discovered by R5-05.

*(Examiner B)*

### R1-27 — **CONFIRMED**

> Table 1 header "Binomial reference"; rows "| [0, 30) | 2 | 0.0000 | 0.4063 |" and "| [30, 100) | 18 | 0.1111 | 0.4689 |"

Neither caption nor body gives the reference's $n$ or $p$. §4.2's gloss ("the exceedance a perfectly valid
boundary-case certificate would show purely from label dispersion") implies $p=\alpha$ and the pool's own
$n$, but I could not reproduce the column from that: $\mathrm{Bin}(25,0.1)$ gives 0.463 against the tabled
0.4063 for the smallest bin, so some within-bin averaging rule is in play that the manuscript does not
state. No interval on any row, including the $n=2$ and $n=18$ rows §4.2 asserts comparisons across (2/18
→ [0.014, 0.347]). Co-discovered by DS-30.

*(Examiner B)*

### R1-28 — **CONFIRMED** (scope of the promise noted)

> §4.1: "we accompany the primary rates with exact (Clopper–Pearson) 95% confidence intervals" · Tables 1–4

Verified: no interval appears in any of the four tables. **Fair to the authors:** the promise says "the
*primary* rates," and the body does supply correct intervals for four of them; §3.9 calls exceedance a
diagnostic, so Table 1's columns arguably sit outside the promise. The sharp instance is Table 4's certify
rates, which are primary — E4's 0.3 at 300 sites fixes the $\alpha=0.05$ frontier and the abstract's
"300+" claim, and its exact interval is [0.237, 0.369], unshown. Forward the sharp instance.

*(Examiner B)*

### R1-29 — **CONFIRMED**

> §4.5: "mean coverage 0.9304 at 150, 0.9715 at the realistic 208-site scale, 0.9601 at 300, and 0.9621 at 400"

Four significant figures, no Monte-Carlo error anywhere in the manuscript; the sequence dips at 300 with no
comment. On the selection point: Table 4's caption reads "Certify rate and mean answered-set coverage at
certifying points," where "points" most naturally denotes sweep grid rows — so the fact that the
$\alpha=0.05$/300-site coverage of 0.7376 is an average over only the 30% of draws that certified is not
disclosed. I credit §4.5's own noise disclosure ("The 208-site sweep point is a separate run from E1 …
hence 0.9715 here against E1's 0.9722"), which does not amount to an MC error but is an honest gesture the
editor should see. Co-discovered by DS-31, R2-36 and R5-25.

*(Examiner B)*

### R1-30 — **CONFIRMED** (sub-clause corrected)

> §4.6: "This case study uses a deployment with threshold $\tau^* = 0.55$, answering 200 cases and declining 2." then "its mean absolute attribution is 0.868 on answered cases but 1.722 on declined cases … Declines are systematically the cases where feature 0's pull leaves the decision contested"

The primary claim is confirmed on the natural reading: "at the cohort level" sits three sentences after the
deployment description, so 1.722, the $-0.854$ gap, the ranking $[0,3,2,1,\dots]$ and "systematically" are
all means over $n=2$. **Correction:** the sub-clause "the declined-case count … is never stated" is
defeated by the finding's own anchor — the count *is* stated ("declining 2") in the same subsection. The
residual, and correct, form of that complaint is that the manuscript never says whether the cohort
statistic is drawn from that deployment or a larger one. Co-discovered by eleven findings across five
referees (DS-11, DS-50, R2-19, R2-66, R3-07, R3-25, R3-35, R3-42, R4-10, R4-46, R5-14); R4, with artifact
access, confirms `n_declined: 2`.

*(Examiner B)*

### R1-31 — **CONFIRMED**

> §4.5: "the minimum-cluster gate … requires 50 of them, so any run with fewer than roughly 125 sites … is refused by that gate — not by the betting test's information floor"

Both clauses true. Below ~125 sites the gate refuses regardless of the test, so E4 cannot separate the
statistical frontier from the frozen constant 50 — yet §1 ("reliably certifiable from about 150 sites") and
§5.2 ("becomes reachable around 150 sites") present 150 as a capacity result. The grid $\{60,100,150,208,
300,400\}$ has no point in (100,150), (208,300) or (300,400), so every "first appears at" statement is
grid-limited. In the manuscript's favour: §4.5 is unusually forthright about the gate/floor distinction and
says so explicitly — the residual defect lives in §1 and §5.2's framing and in the grid.

*(Examiner B)*

### R1-32 — **CONFIRMED**

> §4.6: "a deployment with threshold $\tau^* = 0.55$" · §4.7: "E6 uses a separate deployment (threshold $\tau^* = 0.77$; 40 target sites)" · §4.2: "mean answered-set coverage 0.9722"

Three operating points, no derivation for any, and no $\tau^*$ reported for E1–E4 at all despite §3.5
describing an elaborate selection procedure. Co-discovered by R2-33, R3-12, R5-41.

*(Examiner B)*

### R1-33 — **CONFIRMED**

> §3.3: "provably anti-conservative: a construction with 17.5% true risk certifies at $\alpha = 5\%$ under naive truncation (Appendix A.3; retained as a regression test)"

A.3 restates the same two numbers and says a regression test pins them; it exhibits no site configuration,
no error rates, no argument. "Provably" promises a proof and none is on the page. Co-discovered by DS-17
and R5-27.

*(Examiner B)*

### R1-34 — **CONFIRMED**

> Abstract: "a site-count frontier shows the stricter $\alpha=0.05$ budget needs roughly 300+ sites" · §4.5: "first appears at 300 (certify rate 0.3, coverage 0.7376), and becomes reliable only at 400"

A 30% certify rate is not a budget that is met at 300. I note in fairness that "300+" is literally a lower
bound and so is not false; but §1's own phrasing ("first appears near 300 and stabilizes only at 400") is
the accurate compression, and the abstract's is looser than the paper's own body. Independently found by
R5-22.

*(Examiner B)*

### R1-35 — **CONFIRMED** (one item weaker than stated)

> §4.1: "The cohort follows the specification frozen in `data.py`" and "Every experiment runs in mode FULL" · A.3: "The test suite is 69/69 green." · §5.5: "the implementation includes a `from_raw` loader"

All four verbatim; "mode FULL" is defined nowhere; a test count is not a reviewable result, and with no
repository URL none of the identifiers resolves. **Weakest item:** `data.py` does not quite "stand in for a
specification" — the sentence continues with a colon and then gives the specification ("208 collection
sites, each contributing…"), so the file name is a redundant attribution rather than a substitute.

*(Examiner B)*

### R1-36 — **CONFIRMED** (borderline against the placeholder rule — flagged for the editor)

> Data availability: "publicly available at [CODE REPOSITORY URL — to be added]"

This survives because my kill rule enumerates author/affiliation/ORCID/corresponding-author placeholders,
and this is none of those: it is a Data-availability field on which §3.10, A.3 and §5.5 stake specific
checkable claims (determinism, byte-identical certificates, a `from_raw` loader, a one-command grid),
none of which a referee can assess. **If the office's convention treats every bracketed "to be added" field
as deliberate front-matter, this dies with the author-name findings.** I flag rather than decide, because
the answer is editorial policy, not manuscript fact. Co-discovered by DS-07, R2-40, R4-17/R4-40, R5-40.

*(Examiner B)*

### R1-37 — **CONFIRMED**

> `ifac2025abstainexplain`: `booktitle = {… (ECML PKDD 2024)}`, `year = {2024}` · `l2lore2025`: `year = {2024}` (DS-LB 2024) · `angelopoulos2021ltt`: `year = {2025}` (AoAS)

All three verified in `references.bib`, and at the exact line ranges the finding gives (169–181, 249–260,
262–271). The `ifac` prefix additionally implies IFAC, which the entry is not — it is Lenders et al., ECML
PKDD 2024. Co-discovered by DS-32, R2-38, R3-28, R4-27, R5-34.

*(Examiner B)*

### R1-38 — **CONFIRMED**

> `references.bib` lines 1–3: "% … see paper/TODO.md for % the one unverified candidate, scireports2026deferral, which is deliberately NOT in this file)."

Verbatim at lines 1–3. A submitted artifact naming an internal TODO file and advertising a rejected
citation candidate. Co-discovered by DS-33, R2-39, R5-35.

*(Examiner B)*

### R1-39 — **CONFIRMED**

> §1: "Three questions in reliable machine learning have mature but separate answers." · §2: "CertGate draws on four literatures" · §6: "CertGate occupies the intersection of three separately developed lines"

Verified; §1's closing paragraph also lists three. Explainable abstention is the literature that drops out
of both three-counts — which, given the collection's central emphasis, is worth the editor's attention
beyond the bookkeeping. Co-discovered by R5-33.

*(Examiner B)*

### R1-40 — **CONFIRMED**

> §1: "**A validation design that can fail.** … rather than a new validation philosophy (E3)." · §5.1: "The negative control is validation design, not a headline contribution."

Both verbatim. The item is demoted inside its own sentence and again in the discussion, while being listed
among the primary contributions.

*(Examiner B)*

### R1-41 — **CONFIRMED**

> §5.2: "For any reader tempted to call $\alpha=0.10$ a weak guarantee" · §3.6: "We do not paper over this." · §4.4: "A negative control that cannot fail proves nothing." · §6: "Its posture throughout is disclosure"

All four verbatim. The referee's framing is worth preserving for the editor: he explicitly credits the
draft's restraint elsewhere ("no 'first ever', no repeated 'novel'"), so this is a narrow register point,
not a general charge of overclaiming — and §5.2's instance additionally carries the unproved claim of
R1-10. Co-discovered by DS-37/DS-38, R2-47, R5-51.

*(Examiner B)*

### R1-42 — **CONFIRMED**

> "# Figures" (line 298) through Figure 6 (line 310), caption text only

I read the whole file: no image markup, no `.png`/`.pdf`/`.svg` reference, and no in-text callout to any
figure anywhere in §1–§6 or the appendices. Caption claims such as Figure 4's shaded gate region cannot be
checked. Co-discovered by DS-05, R2-30, R3-24/R3-46, R5-15. (R4, with artifact access, reports the PNGs
exist in the repository — which does not disturb the finding, since the *manuscript* embeds none.)

*(Examiner B)*

### R1-43 — **CONFIRMED**

> §3.8: "$\phi_j(x) = w_j(x_j - \mu_j)$ … where $\text{coef}_j$ is the coefficient learned on standardized inputs and $\text{sd}_j$ the training-split standard deviation of feature $j$"

$\mu_j$ appears once and is defined nowhere; $\mathrm{sd}_j$ is defined with care in the same sentence.
$\mu_j$ fixes the attribution baseline, so it is not cosmetic. Co-discovered by R2-45 and R3-22; DS-25
makes the same point about the undefined "base" in the adjacent identity.

*(Examiner B)*

### R1-45 — **CONFIRMED**

> Title (line 1): "CertGate: finite-sample certified selective prediction … with label-shift robustness and explainable abstention"

The title conjoins "finite-sample" with label-shift robustness while §3.6, §3.7(5) and §6.1 all disclose
that the label-shift mode contains an asymptotic step. The body's disclosure is thorough and does not
repair a title. Note the sharper adjacent instance, which is R5-03's not mine: §3.6 claims "every guarantee
statement carries that caveat," and the abstract's guarantee sentence does not.

*(Examiner B)*

### R1-46 — **CONFIRMED**

> §4.2: "0.01 (2 of 200; exact 95% CI $[0.001, 0.036]$) … and non-zero — consistent with a tight rather than a vacuous certificate [@geifman2017selective]"

I recomputed the interval: [0.0012, 0.0357] — the manuscript's arithmetic is right. But an interval reaching
down to 0.001 is equally consistent with a distinctly slack certificate, so "tight" is not what 2/200
licenses. And `geifman2017selective` ("Selective classification for deep neural networks") is a method
paper offering no tightness criterion. Co-discovered by R2-37 and R5-36.

*(Examiner B)*

### R1-47 — **CONFIRMED**

> §2.4: "The same certificate shape appears in power-grid contingency screening [@thermal2026audit], so it is not specific to medicine."

Verbatim, and `thermal2026audit` is an unrefereed `@misc` arXiv entry noted "submitted to IEEE Transactions
on Power Systems." Shape resemblance in one unrefereed cross-domain preprint does not establish generality,
and against the venue card — a collection scoped to clinical, epidemiological and public-health ML — a
sentence disclaiming medical specificity spends credibility for nothing. Co-discovered by R5-37; DS-22
builds a venue-fit case partly on the same sentence.

*(Examiner B)*

### R1-49 — **CONFIRMED**

> §4: "because we control the data-generating process, we can compute the true answered-set risk at each target site" · §4.2

§4.2 reports certify rate, coverage, hard-violation rate, exceedance and Table 1 — and no true answered
risk. The quantity that oracle access exists to supply, and that would show how much slack the certificate
operates on, is reported in E3 (0.2022) but not in the validity experiment. Co-discovered by R5-16/R5-56.

*(Examiner B)*

### R1-50 — **CONFIRMED**

> A.3: "The frozen design constants — split fractions, budget ladder, influence cap $M$, threshold grid, betting-test parameters, and decline thresholds — are pinned to their literal values by a unit test"

None of the six is varied in any experiment: E1–E3 vary the environment, E4 varies site count (not a design
constant), E5–E6 vary the deployment. Freezing is good practice and orthogonal to the reader's need to know
sensitivity. Overlaps R1-14 on $M$ specifically; kept separate because R1-14's charge is that the estimand
is not what the abstract advertises, while this one is the absence of ablations. Co-discovered by DS-40.

*(Examiner B)*

### R1-51 — **CONFIRMED**

> §4.7: "the ~0.4-point gap between the BBSE-implied and oracle fractions"

Table 3 gives 0.0591 and 0.0630; the difference is 0.0039, i.e. 0.39 **percentage** points on a [0,1]
fraction. Recomputed. Co-discovered by DS-36.

*(Examiner B)*

### R1-52 — **CONFIRMED** (diagnosis sharpened)

> §4.3: "exact 95% CI $[0, 0.018]$, consistent with the rule-of-three bound $3/200 = 0.015$; both below $\delta$"

The manuscript's exact bound is right (0.01828) and 3/200 = 0.015 is smaller, so "consistent with" is doing
loose work as the finding says. **Sharper diagnosis for the editor:** 3/200 is an accurate approximation to
the *one-sided* 95% bound (I compute 0.014867), and the manuscript pairs it with a *two-sided* Clopper–
Pearson interval. The mismatch is one-sided-versus-two-sided, not a plain anti-conservatism, and that is
the correction to request.

*(Examiner B)*

### R1-53 — **CONFIRMED**

> §3.5: "We deploy the maximum-coverage threshold in the certified prefix." · §3.6: "we deploy the most conservative certified threshold"

Both verbatim, both using "deploy," pointing in opposite directions. A coherent reconciliation exists
(max-coverage within a mode's walk, then most-conservative across modes, which §3.6's "**Combination.**"
heading hints at) but the manuscript never states it, and the two sentences read as contradictory
instructions. Three independent referees tripped on it (DS-18, R5-08, R1-53), which is itself evidence the
hazard is real. Co-discovered.

*(Examiner B)*

### R1-59 — **CONFIRMED**

> §3.5: "We deploy the maximum-coverage threshold in the certified prefix."

Kept separate from R1-53 and R1-21: this asks something neither does — on which pool coverage is measured.
§3.5 says only that the *ordering* is by "estimated certification margin on $S_{\text{aux}}$"; where the
coverage that decides the deployed threshold is evaluated is stated nowhere. **In the authors' favour on
the second half:** the fixed-sequence rejection principle the manuscript cites does license selecting any
element of the certified prefix, so that part of the question is answerable from the cited theory even
though the manuscript does not spell it out. The "which pool" half stands unanswered.

*(Examiner B)*

### R1-69 — **CONFIRMED**

> §1 contribution 3: "This supports the certificate above rather than standing as an independent method (E5)." · §3.8: "a supporting capability the linear head makes nearly free"

Both verbatim — the explanation layer is characterized as subordinate twice, in the paper's own voice.
Against the venue card, where "Explainability is the central emphasis," the whole layer is one methods
subsection (§3.8), one experiment (§4.6) resting on two declined cases, and one exactness claim that R1-18
confirms is wrong as stated. This is an editorial judgment, but it is anchored in verified text and in the
collection's stated framing rather than in taste. Co-discovery outside my assignment is heavy: R3-41,
R3-45, R2-68, DS-58, R5-67 all reach the same conclusion from four different referees.

---

*(Examiner B)*

### R2-01 — CONFIRMED (with one overreach corrected)

> "otherwise it abstains and defers the case to human judgment" (§3.1, line 60)
> "BBSE declines the remaining 95.5% of draws (decline rate 0.955)" (§4.3, line 174)
> "the system declines rather than issue a certificate it cannot support at this cluster count" (§4.2, line 166)

The conflation is real: "declined case" is used for per-case abstention throughout §3.8 and §4.6 ("A declined case (index 38…)", "answering 200 cases and declining 2"), while "declines" carries the whole-certificate sense in §4.2, §4.3 and §3.6. Nothing in the manuscript distinguishes the terms, and nothing states the operational consequence of a whole-certificate decline. **Correction:** the finding's clause "never … says what happens after either" is too strong on the per-case side — §3.1 does say the case is deferred to human judgment. It holds for the certificate-level decline.

*(Examiner C)*

### R2-02 — CONFIRMED

> "BBSE declines the remaining 95.5% of draws (decline rate 0.955) rather than issue an unsupported certificate, and both modes decline entirely at $\alpha = 0.05$." (§4.3, line 174)

The shift is characterised by the paper itself as ordinary — "a near-tripling of outcome frequency of the kind that a change in referral pattern or case mix produces" (§4.3, line 170) — and the decline is framed as correct behaviour in §4.2 ("That decline, not a violation, is the correct behavior") and in Contribution 2. Availability appears nowhere as a requirement or a cost: the §6.1 limitations list contains six items, none about decline rate.

*(Examiner C)*

### R2-03 — CONFIRMED

> "occurs 0 times in 200 draws (exact 95% CI $[0, 0.018]$ …); conditioning on the 9 draws that did certify ($n_{\text{certified}} = 9$), the hard-violation rate among them is 0.0." (§4.3, line 174)

Arithmetic verified: certify rate $9/200 = 0.045$; rule of three on the conditional denominator $3/9 = 0.333$; the exact one-sided 95% Clopper–Pearson upper bound on 0/9 is $1 - 0.025^{1/9} = 0.336$. The abstract ("the corrected mode never does, declining in 95.5% instead") and §1 line 27 ("the joint event is 0 of 200 draws") report the joint event only; neither carries the conditional denominator. **Co-discovery:** DS-03, R1-09/R1-67, R5-06/R5-65.

*(Examiner C)*

### R2-04 — CONFIRMED

> Abstract: "certifies … that the error rate among answered cases stays at or below $\alpha$" (line 11)
> §3.3: "each site receives a *data-independent* influence weight $g_c = \min(n_c, M)$ with $M = 100$" and "a site that answers many cases badly still enters at full adverse weight" (line 72, 76)

Cap-hit fraction verified: with $\log n \sim N(6.0, 1.1^2)$, $P(n > 100) = \Phi((6.0-4.605)/1.1) = \Phi(1.268) = 0.90$ — about 90% of sites sit at the cap, so $R_M$ is close to an $a_c$-weighted per-site average. R2's worked counterexample reproduces exactly: $(42{\times}100{\times}0.20 + 166{\times}100{\times}0.02)/(208{\times}100) = 0.0563$ certified, against record-weighted $25{,}532/142{,}600 = 0.1790$. **Correction:** the abstract does omit the qualifier, but §1's Contribution 1 carries it ("bounds the influence-weighted error rate among answered cases"), as do §3.1, §3.3 and §5.1 — so the omission is confined to the abstract and to §1's generic framing sentence, not to the introduction as a whole. No record-weighted answered error is reported anywhere (`grep "record-weighted"` → zero).

*(Examiner C)*

### R2-05 — CONFIRMED

> "the gate earns its low error by answering predominantly easy negatives and abstaining where positives concentrate. That is not a defect; it is what a selective gate on a low-prevalence task should do." (§4.7, line 202)

Reconstruction reproduces: 23,325 answered at mean per-site coverage ≈ 0.90 → ≈ 25,900 records; at 9.5% base prevalence ≈ 2,460 positives; oracle answered positives 1,470 (Table 3) → ≈ 990 declined positives in ≈ 2,590 declined records = 38% declined prevalence, 40% of all positives. **Sensitivity check I ran:** across record-weighted coverage 0.85–0.93 the *fraction of cohort positives that is declined* stays 38–44% (robust), while the *declined-set prevalence* moves 28–52% (less robust). Forward the 40% figure; hedge the 38%. The manuscript computes neither; §4.7's equity scoping covers only demographic subgroups, not outcome-class concentration, so kill criterion 5 does not reach this.

*(Examiner C)*

### R2-06 — CONFIRMED

> "$$Z_c = \frac{g_c}{M\, n_c}\sum_{i \in c} \text{ans}_i\,(\text{err}_i - \alpha) + \alpha$$" (§3.3, line 80)

`grep` confirms `\text{err}` occurs exactly once in the manuscript, at line 80, with no definition. `\hat y` appears only at line 108 inside the BBSE confusion rates, itself undefined. And `grep -i "sensitivit|specificit|PPV|NPV|AUROC|AUPRC|confusion matrix"` returns zero true hits across the whole file — no discrimination metric is reported anywhere, for the answered set or otherwise.

*(Examiner C)*

### R2-07 — CONFIRMED

> "the mean answered error stays well below $\alpha = 0.10$ in every bin (0.0294, 0.0406, 0.0348)" (§4.7, line 200); Table 3.

Arithmetic verified independently. With $TP+FP = 917$, $TP+FN = 1470$, $FP+FN = 0.035 \times 23{,}325 = 816$: $2TP = 917+1470-816 = 1571 \Rightarrow TP = 786$, $FP = 131$, $FN = 684$, sensitivity $= 786/1470 = 0.535$. Re-running with the largest-bin error 0.0348 (which dominates a record-weighted average) gives $TP = 788$, sensitivity 0.536 — the estimate is stable. At 9.5% prevalence an always-negative classifier errs at 9.5%, so $\alpha = 0.10$ does sit above the no-skill rate. §5.1's list of what the certificate is not ("not a bound on a batch's realized error count … not a per-record coverage statement … not protection against concept shift") does not mention sensitivity or asymmetric costs, so there is no scoping passage to invoke.

*(Examiner C)*

### R2-08 — CONFIRMED

> §1: "A deterioration or readmission score calibrated on patients from a handful of academic centers…" versus §3.1: "on the order of two hundred collection sites each contribute between 20 and 5,000 records"

`grep -i "outcome definition|index event|prediction time|observation window|follow-up|censor|competing risk|calendar|time horizon"` returns exactly one hit across the entire manuscript — "censors" at line 76, in "never censors the error itself", which is the influence-cap discussion, not survival censoring. Every element the finding lists is genuinely absent.

*(Examiner C)*

### R2-09 — CONFIRMED

> §3.1: "sites differ in both prevalence and case mix"; §4.1: "Site heterogeneity enters through a site random effect $u_c \sim \mathcal{N}(0, 0.5^2)$ that shifts each site's outcome log-odds, $\pi_c = \sigma(\mathrm{logit}(0.095) + u_c)$ … no two sites share an identical case mix"; §3.6: "the class-conditional feature distribution $P(x \mid y)$ is held invariant"

As described in §4.1, the only site-indexed quantity in the generator is $\pi_c$; the feature description ("the class signal lives on a single normalized direction … the two class means separated by $\mathrm{sep} = 2.2$") carries no site index. So on the manuscript's own account $P(x\mid y)$ is site-invariant by construction, "case mix" is being used to mean class mix, and BBSE's invariance assumption holds by construction in E2. Properly framed as a manuscript-level inference, so kill criterion 6 does not apply.

*(Examiner C)*

### R2-10 — CONFIRMED

> §1: "A deterioration or readmission score calibrated on patients from a handful of academic centers is deployed at a community hospital that contributed no training records"
> §6.1: "A third assumption mode that reweights by feature-density ratios is not offered" and "*There is no out-of-support screen.*"

§6.1 does defend excluding covariate-shift weighting (the effective-sample-size argument), but the finding does not demand that mode — it demands that the manuscript disclose the mismatch between its motivating scenario and its assumption modes. I checked §5.1, §5.4 and §5.5: none connects the community-hospital scenario to the exchangeable or BBSE tag. Kill criterion 5 does not reach this.

*(Examiner C)*

### R2-12 — CONFIRMED

> "The gate itself is model-agnostic: the score only *ranks* cases, and the validity of the certificate never depends on the quality or calibration of the model producing that score." (§3.8, line 128)

I read all 27 occurrences of "calibrat*": every one refers to the calibration pool/sites/draws, to the model being "calibrated on patients" (fitting sense), or to this §3.8 dismissal. No calibration plot, slope, intercept, Brier score, ECE, or per-site calibration exists. The §3.8 sentence is a claim about validity, not a defended scope boundary.

*(Examiner C)*

### R2-13 — CONFIRMED

> "$$R_M = \frac{\sum_c g_c\, a_c\, e_c}{\sum_c g_c\, a_c},$$ where $a_c$ is the answered fraction and $e_c$ the answered-set error rate" (§3.3, line 74)

`grep -i "net benefit|decision curve|Brier"` → zero. "cost" occurs three times (lines 128, 202, 212), all about coverage or estimation cost, never about FN/FP asymmetry. A.1(i)'s bound (inner terms in $[-\alpha, 1-\alpha]$) confirms $\text{err}_i \in \{0,1\}$, i.e. symmetric 0-1.

*(Examiner C)*

### R2-14 — CONFIRMED (with one correction)

> "Clinical practice already treats the site as the unit — TRIPOD-Cluster [@tripodcluster2023] and internal–external cross-validation [@internalexternal2021] — but reports point estimates, not certificates." (§2.4, line 54)

No guideline conformance is claimed, no checklist is supplied, and neither TRIPOD+AI (Collins et al.) nor DECIDE-AI (Vasey et al.) appears among the 31 bibliography entries. **Correction:** "cites TRIPOD-Cluster only as evidence that other authors treat the site as the unit" is inaccurate — it is also cited at §1 line 23 and §4.1 line 152 for the distributional-profile claim.

*(Examiner C)*

### R2-15 — CONFIRMED

> §3.7: "The guarantee the certificate makes carries five clauses, all of which survive into the deployed guarantee text." (line 124)
> §A.3: "each report artifact embeds a provenance block recording package versions, seeds, and input hashes." (line 268)

§3.7 paraphrases the five clauses in the authors' prose but never quotes the deployed text, and nothing anywhere exhibits a certificate with its $\alpha$, $\delta$, $\tau^*$, mode tag, calibration site count or decline reasons. The provenance block is the only artifact given any concrete content.

*(Examiner C)*

### R2-16 — CONFIRMED

> "*Temporal common-shock correlation is not modeled.*" (§6.1, line 240)

`grep -i "recertif|re-certif|expir|monitor|cadence|governance|oversight"` returns **zero matches** across the whole manuscript. No review interval, no monitored quantity, no expiry, no re-certification trigger.

*(Examiner C)*

### R2-17 — CONFIRMED

> "Not applicable: the study involves no human subjects and no patient data; all data are synthetic." (Ethics approval, line 288)

`grep -i "regulat|medical device|AI Act|accountab|automation bias|IRB|oversight|governance"` returns **zero matches**. The §5.4 mention of "privacy" concerns federation mechanics, not oversight.

*(Examiner C)*

### R2-18 — CONFIRMED

> "(3) It bounds the answered-set error parameter, not any single batch's realized error *count*…" (§3.7, line 124)

Arithmetic verified: §4.2 reports realized exceedance 0.05 overall against hard-violation 0.01 — a factor of five. §3.9 does define the Wilson criterion, but explicitly as a harness device: "The guarantee itself rests on the finite-sample level of the betting test (Section 3.4), not on this harness." It is never promoted to an operational monitoring rule with a sample size or an escalation threshold.

*(Examiner C)*

### R2-19 — CONFIRMED *(survivor of the n=2 abstention-driver cluster)*


**Anchor, located and verified:**
> "This case study uses a deployment with threshold $\tau^* = 0.55$, answering 200 cases and declining 2." (§4.6, line 192)
> "At the cohort level, feature 0 is the dominant abstention driver: its mean absolute attribution is 0.868 on answered cases but 1.722 on declined cases, the largest answered-to-declined gap of any feature (gap $-0.854$; gap ranking $[0, 3, 2, 1, \dots]$; top gap feature 0). Declines are systematically the cases where feature 0's pull leaves the decision contested" (§4.6, line 196)

The declined-side mean is a mean over two cases, both individually enumerated four lines earlier (indices 38 and 102). No interval, variance or replication accompanies it. **Correction to the finding as filed:** it calls this "the sole empirical evidence for the paper's third contribution" — §4.6 also carries the global-importance recovery check and three case studies, so the accurate scope is *the sole evidence for §3.8's cohort-level promise* ("the attribution profiles of the answered and declined populations identify systematic abstention drivers"), which is how R2's own report words it.

**Mechanism argument preserved from the merged R3-42, and it is the strongest reason to expect noise:** §4.6 reports features 0–3 at 1.157, 1.161, 1.178, 1.155 — a spread of 0.023 across four coefficients on a single shared signal direction. There is no stated mechanism by which feature 0 should differ from 1–3 in abstention behaviour.

**Co-discovery:** DS-11/DS-50, R1-30, R2-19/R2-66, R3-07/R3-25/R3-35/R3-42, R4-10, R5-14. Five of six referees.

---

*(Examiner C)*

### R2-20 — CONFIRMED (with count correction)

> "The equity question here is scoped narrowly to site size … demographic and protected-attribute subgroup analysis is beyond this synthetic harness." (§4.7, line 200)

`grep -i "fairness|equity|protected|demograph|subgroup"` matches **only line 200** in the entire manuscript. `ifac2025abstainexplain` (title: "Interpretable and **Fair** Mechanisms for Abstaining Classifiers") is cited **five** times, not four (lines 25, 33, 54, 130, 192); I checked each — all five are for reject-option explanation, none engages the fairness content. On kill criterion 5: "beyond this synthetic harness" is an admission whose stated reason is a property of the authors' own design choice, not an external constraint — an admission, not a defence, so it downgrades rather than kills.

*(Examiner C)*

### R2-21 — CONFIRMED

> "Coverage is essentially flat across bins — 0.9191, 0.8966, and 0.9063 … the smallest populated bin holds 4 sites … Small sites are neither over-answered nor starved." (§4.7, line 200)

Table 2 verified: site counts 0 + 4 + 15 + 21 = 40; columns are exactly "Sites | Mean per-site coverage | Mean answered error". No dispersion, no minimum coverage, no maximum answered error, no count of sites exceeding $\alpha$.

*(Examiner C)*

### R2-22 — CONFIRMED (with count correction)

I read all 31 bibliography entries. Exactly two are peer-reviewed clinical works (`tripodcluster2023`, `internalexternal2021`) — **out of 31, not 30**. None of Wong, Finlayson, Dvijotham, Mozannar & Sontag, Madras, Sendak, Obermeyer, Van Calster, Vickers & Elkin, Collins (TRIPOD+AI), Vasey (DECIDE-AI) or Feng appears. §2.4's citation set is exactly as described: 2 clinical + 3 preprints (`zhou`, `triage`, `thermal`) + 3 reject-option (`artelt`, `ifac`, `l2lore`).

*(Examiner C)*

### R2-23 — CONFIRMED (with count correction)

> "certified record-level selective-risk rules overrun their budget by 9–30% under grouped deployment [@zhou2026falsesense]" (§2.4, line 54)

The entry is `@misc{zhou2026falsesense}`, year 2026, no venue, title "False Sense of Safety in Selective **Signal** Classification: Auditing Bound Tightness and Exchangeability for Risk Control" — verified verbatim. Two entries carry submission-status notes: `fedcrc2026` ("submitted to DeCaF Workshop, MICCAI 2026") and `thermal2026audit` ("submitted to IEEE Transactions on Power Systems"). **Correction: seven of thirty-one preprints, not six of thirty** — `scrc2025` is omitted from the finding's list. **Supporting fact the finding does not use:** the manuscript twice calls this preprint "published" — §1 contribution 4 ("a published diagnosis") and §4.4 ("the published warning") — which strengthens the point. The 9–30% figure appears only in §2.4, not §1.

*(Examiner C)*

### R2-26 — CONFIRMED

> "Real data cannot supply that ground truth, which is what makes it unable to validate a validity claim." and "The route to real data is concrete: the implementation includes a `from_raw` loader…" (§5.5, line 224)

The manuscript's own hard-violation criterion (§3.9) consumes only realized answered errors and a Wilson lower bound — both computable from labelled real cohorts. So the §5.5 sentence overreaches beyond the narrower and defensible claim §4's opening actually makes (real data cannot supply the true *parameter*). **Co-discovery:** DS-10, R1-16, R5-10/R5-64.

*(Examiner C)*

### R2-27 — CONFIRMED

> "Sites with no answered-eligible records enter as *neutral* atoms $Z_c = \alpha$ rather than being dropped…" (§3.3, line 82)

Important distinction the manuscript blurs and the finding gets right: §3.3's reassurance that "an empty site never pads the effective sample size" covers only *record-carrying* status. A site with 500 records where the gate answers none **is** record-carrying, so it counts toward the 50-cluster gate *and* enters as a neutral atom. The finding's "partly earned" is loose — a neutral atom yields wealth factor exactly 1 — but the substance (zero-coverage sites scored at budget and counted toward feasibility, count never reported) holds. Table 2's [0,30) bin holding 0 sites confirms the case is never exercised in the reported results.

*(Examiner C)*

### R2-28 — CONFIRMED

> "(iii) $q$ outside the box's $[c_{0,\text{lo}}, c_{1,\text{hi}}]$ range, meaning the implied prevalence leaves $(0,1)$ and BBSE is misspecified." (§3.6, line 116)

As written, gate (iii) declines only when the implied $\pi_t$ leaves $(0,1)$; any value inside passes. No clinical plausibility band on $\pi_t$ exists anywhere in the manuscript.

*(Examiner C)*

### R2-29 — CONFIRMED

> "The risk head is an L2-regularized logistic regression ($C = 1.0$) fit on $S_{\text{train}}$" (§4.1, line 154), on a generator whose classes differ only in mean along one direction (§4.1, line 152)

Logistic regression is the correctly specified posterior form for equal-covariance class-conditional distributions differing in mean, so the model class contains the truth. No degraded or misspecified head is run anywhere; §3.8's "A stronger black-box head can be substituted at a visible cost in coverage" is untested and concerns a *stronger* head, not a degraded one — not a scoping passage.

*(Examiner C)*

### R2-31 — CONFIRMED (and strengthened)

> §2.2: "the first two guarantee coverage, not selective risk" (line 46) versus §4.2: "mean answered-set coverage 0.9722" (line 162)

Confirmed, and the manuscript is worse than the finding says: a **third internal sense** appears in §3.6 and A.2 — "a coverage statement over the $S_{\text{aux}}$ bootstrap box" (line 114), "the coverage of the $S_{\text{aux}}$ bootstrap box" (line 124), "corner-interval coverage" (line 262). Three incompatible senses, none disambiguated.

*(Examiner C)*

### R2-32 — CONFIRMED

> §3.2: "$S_{\text{cal}}$ (40%, used for certification only and touched exactly once, by the certification test)" (line 66) versus §3.5: "we walk the grid in a fixed sequence … the walk stops at the first failure" and "risk is controlled on $S_{\text{cal}}$" (line 100)

Up to 23 candidates are tested sequentially against $S_{\text{cal}}$, twice over (two $\alpha$ rungs), in two modes. A charitable reading of "touched exactly once" is "only one procedure touches it"; the phrase as written reads as a single access and will be taken as a stronger hygiene claim than is true. **Co-discovery:** R1-21.

*(Examiner C)*

### R2-33 — CONFIRMED

> §4.6: "$\tau^* = 0.55$"; §4.7: "$\tau^* = 0.77$"

Verified by reading §4.2–§4.5 in full: no numeric $\tau^*$ appears in E1, E2, E3 or E4. The only numeric thresholds in the manuscript are 0.55 (E5), 0.77 (E6), and the grid endpoints [0.55, 0.99] (§3.5). No sentence reconciles 0.55 against 0.77. **Co-discovery:** R1-32, R5-41/R5-59.

*(Examiner C)*

### R2-34 — CONFIRMED

> "the one-sided 95% Wilson lower confidence bound on the target pool's answered error exceeds $\alpha$ [@wilson1927]." (§3.9, line 138)

`grep "target pool"` returns **exactly one match**, at line 138. The term is used once, load-bearingly, and never defined as a site or an aggregate.

*(Examiner C)*

### R2-35 — CONFIRMED

> §3.1 line 62: "roughly eighty site-level observations"; §3.5 line 102: "about 83 calibration clusters"; §5.2 line 212: "roughly 80 of them at the 208-site scale"

All three verified verbatim; $208 \times 0.4 = 83.2$. **Co-discovery:** R5-52.

*(Examiner C)*

### R2-36 — CONFIRMED

> "with mean coverage 0.9304 at 150, 0.9715 at the realistic 208-site scale, 0.9601 at 300, and 0.9621 at 400" (§4.5, line 186)

Table 4 confirms the sequence; it rises, falls, rises. The manuscript's only nearby explanation covers a different discrepancy — "(The 208-site sweep point is a separate run from E1 … hence 0.9715 here against E1's 0.9722.)" — and says nothing about the 208→300 drop. No error bars on any coverage column. **Co-discovery:** DS-31, R1-29, R5-25/R5-57.

*(Examiner C)*

### R2-37 — CONFIRMED

> "non-zero — consistent with a tight rather than a vacuous certificate [@geifman2017selective]." (§4.2, line 162)

The citation is attached to a claim about the tightness of CertGate's certificate on CertGate's cohort, which a 2017 selective-classification method paper cannot speak to. Note the manuscript already uses this citation correctly at §3.1 line 60 for the $(\alpha,\delta)$ phrasing convention, so the §4.2 use is a second and different one. **Co-discovery:** R1-46, R5-36.

*(Examiner C)*

### R2-38 — CONFIRMED

All three verified against the bibliography verbatim:
- `ifac2025abstainexplain`: `booktitle = {… (ECML PKDD 2024)}`, `year = {2024}` — key says 2025, and the "ifac" prefix names a venue the entry is not.
- `l2lore2025`: `year = {2024}` (DS-LB 2024).
- `angelopoulos2021ltt`: `year = {2025}` (*Ann Appl Stat*).
**Co-discovery:** DS-32, R1-37, R3-28, R4-27, R5-34 — five referees.

*(Examiner C)*

### R2-39 — CONFIRMED

> "% CertGate manuscript references — every entry verified against its primary source on 2026-07-24 / % (arXiv abstract page, DOI/Crossref record, or publisher/proceedings page; see paper/TODO.md for / % the one unverified candidate, scireports2026deferral, which is deliberately NOT in this file)." (references.bib lines 1–3)

Verified verbatim. The header dates an internal verification pass, points at an internal to-do file, and names a deliberately excluded candidate. **Co-discovery:** DS-33, R1-38, R5-35.

*(Examiner C)*

### R2-40 — CONFIRMED, with a criterion-4 boundary flagged for the editor

> "publicly available at [CODE REPOSITORY URL — to be added]." (Data availability, line 276)

**I ruled kill criterion 4 does not reach this**, because the criterion enumerates a closed class — "author/affiliation/ORCID/corresponding-author placeholders" — i.e. the identity fields blinded for review. The repository URL is a substantive content gap on which §3.10 and A.3 depend, and it is marked "to be added" rather than redacted. The finding's second limb (no archived or DOI-minted identifier) is a Springer requirement that survives regardless. **If the editor reads criterion 4 broadly to cover every bracketed to-be-completed field, this finding dies with it** — I flag rather than decide that.

*(Examiner C)*

### R2-42 — CONFIRMED

> "The cohort follows the specification frozen in `data.py`: 208 collection sites…" (§4.1, line 152)

The sentence does attribute the specification to a source file. The parameters follow in the same sentence, so nothing is missing — the finding is a register point about where authority is located, and as such it is accurately anchored. **Co-discovery:** DS-27, R1-35, R5-39.

*(Examiner C)*

### R2-43 — CONFIRMED

> "mean answered-set coverage 0.9722" (§4.2); "1,378.9 expected" (Table 3); "1.157, 1.161, 1.178, and 1.155" (§4.6)

All three verified verbatim. Note the anchors mix sources: 0.9722 is a mean over 200 draws, while 1,378.9 and the four importances come from single-draw deployments (E6, E5). The over-precision claim holds for both classes; the "derived from 200 replicates" framing applies only to the first.

*(Examiner C)*

### R2-44 — CONFIRMED

> "A deployed risk model produces a bounded score $s(x) \in [0.5, 1]$ — the max-softmax of a probabilistic classifier over the binary outcome $y \in \{0,1\}$" (§3.1, line 60)

For a binary outcome this is $\max(\hat p, 1-\hat p)$. §3.8's answer rule $|\text{logit}\,\hat p(x)| \ge \text{logit}\,\tau^*$ confirms the abstention band is symmetric about $\hat p = 0.5$, and no clinical decision threshold is stated anywhere.

*(Examiner C)*

### R2-46 — CONFIRMED (with one item corrected)

> "**Keywords** Selective prediction · Distribution-free uncertainty quantification · Cluster-robust inference · Label shift · Explainable abstention · Clinical risk prediction" (line 13)

Fairness, calibration and clinical auditability are all named explicitly on the venue card and all absent from the keyword list. **Correction:** "clinical decision support" is *not* on the collection's stated list — the card names fairness, uncertainty quantification, calibration, OOD robustness, clinical auditability, human-centered design, federated/privacy-preserving learning, and multimodal EHR. Three of the finding's four items hold.

*(Examiner C)*

### R2-47 — CONFIRMED

All three verified verbatim: "the rigor that constructively answers a published diagnosis of overconfident selective certificates" (§1 contribution 4, line 34); "the reading is honest" (§4.7, line 202); "Its posture throughout is disclosure" (§6, line 228). **Co-discovery:** DS-37, R1-41, R5-51.

*(Examiner C)*

### R2-54 — CONFIRMED

> "otherwise it abstains and defers the case to human judgment" (§3.1, line 60)

`grep -i "per day|per year"` → zero matches. No abstention workload figure, per-site or per-day, and no statement of who reviews declined cases, exists anywhere. Overlaps R2-01 and R2-02 in motivation but asks for a distinct artefact (a sized workload), so I kept it separate.

*(Examiner C)*

### R2-68 — CONFIRMED

> §4.7: "demographic and protected-attribute subgroup analysis is beyond this synthetic harness"; §3.8: "the validity of the certificate never depends on the quality or calibration of the model producing that score"; §3.7 enumerates clauses without showing the text

Each axis of the fit judgment rests on an absence I verified independently: fairness → one sentence, no analysis (grep); calibration → no assessment of any kind (27 occurrences read); human-centered design → zero occurrences; auditability-as-artifact → no certificate exhibit (R2-15); explainability-as-evidenced → the n=2 result (R2-19). The judgment is grounded, not asserted.

*(Examiner C)*

### R2-69 — CONFIRMED (with count correction)

> §2.1: "Yu and Liu [@yu2026joint] are closest: the same certificate shape — a selected-risk bound with an acceptance floor and a decline option — but over i.i.d. records" (line 42)

`yu2026joint` is verified as `@misc`, `year = {2026}`, `note = {arXiv:2606.08517}`, no venue. The novelty delta in Contribution 1 does rest entirely on the "but over i.i.d. records" clause being an accurate reading of that preprint. **Correction: seven of thirty-one preprints, not six of thirty.** Kept separate from R2-23 because the ask is different — office verification of three specific entries before decision, versus in-text attribution. **Co-discovery:** DS-59, R1-68, R5-66.

*(Examiner C)*

### R2-70 — CONFIRMED

All four anchors verified verbatim: the five guarantee clauses (§3.7, line 124); "two numbers that must never be conflated" (§3.9, line 136); "a tilt that failed to raise true risk above $\alpha$ aborts the run before any output is written (reason `e3-control-not-poisonous`)" (§4.4, line 178); the six-item §6.1 limitations list (lines 234–244). This is a favourable finding and it survives on anchoring: the disclosure apparatus the referee credits is exactly where he says it is. Worth forwarding — several of my other confirmations are requests for *addition*, and this finding correctly identifies that the paper is fixable that way.

---

*(Examiner C)*

### R3-01 — CONFIRMED *(survivor of the Shapley-independence cluster)*


**Anchor, located and verified:**
> "For a linear model these attributions are exact Shapley values, with no approximation or sampling [@lundberg2017shap]." (§3.8, line 130)
> "the class signal lives on a single normalized direction supported on the first four coordinates, with the two class means separated by $\mathrm{sep} = 2.2$ along that direction" (§4.1, line 152)

Lundberg & Lee derive Linear SHAP, $\phi_j = w_j(x_j - E[x_j])$, under feature independence (equivalently the interventional/marginal value function); the manuscript states neither the assumption nor the value function anywhere. The generator violates it: a two-component mixture with class-dependent means along a shared direction over coordinates 0–3 has marginal covariance $I + \pi(1-\pi)\,\mathrm{sep}^2\,vv^{\!\top}$. At $\pi = 0.095$, $\mathrm{sep} = 2.2$ and equal loading on four coordinates this gives marginal correlation $\approx 0.09$ among features 0–3 — non-zero, though modest, so the finding is right in kind and should not be sold as a large numerical distortion.

**Co-discovery:** all six referees (DS-16, R1-18, R2-24, R3-01/R3-37/R3-44, R4-15, R5-12/R5-60). This is the most heavily corroborated finding in the pool.

*(Examiner C)*

### R3-02 — CONFIRMED (with a qualification)

> "The deployed head is L2-regularized logistic regression with $C = 1.0$, chosen so that the answer/abstain decision is intrinsically interpretable." and "a supporting capability the linear head makes nearly free" (§3.8, lines 128, 130); "This supports the certificate above rather than standing as an independent method (E5)." (Contribution 3, line 33)

The substantive claim — no explanation method is contributed, and the manuscript concedes it — is confirmed from the manuscript's own words. **Qualification:** the abstract is not silent on the mechanism. It says "*Because the deployed risk model is linear*, every answer and every abstention additionally carries an exact feature attribution", which already attributes the property to the model class. The finding's prescription ("the abstract should say so") is therefore half-anticipated; what the abstract omits is the explicit disclaimer that this is a read-out rather than a method.

*(Examiner C)*

### R3-03 — CONFIRMED

> Contribution 3: "the contribution is the attachment of explanation to a *certified* decision"; §3.7: "(3) It bounds the answered-set error parameter, not any single batch's realized error count" and "(2) All sites certified from one calibration draw share a single $1-\delta$ event, not an independent guarantee each."

The tension is exactly as described: on the manuscript's own guarantee text, no individual record carries a certified property, so "certified decision" at the record level is unsupported by §3.7. **Note both ways:** §2.4 uses the accurate phrasing — "exact attributions on a certified **gate**" — which is simultaneously a partial answer and evidence the authors have both formulations in play without reconciling them.

*(Examiner C)*

### R3-04 — CONFIRMED on the core, with a mathematical correction

> "we report the margin-to-answer $m(x) = \text{logit}\,\tau^* - |\text{logit}\,\hat{p}(x)| > 0$ together with the signed feature attributions of the confidence deficit" (§3.8, line 130)

**Core confirmed:** the phrase "signed feature attributions of the confidence deficit" occurs once, at line 130, and no formula, value function, or exactness argument for it appears anywhere in the manuscript.
**Correction the editor should carry:** the finding's stronger claim — that the deficit "is not additively decomposable" — is over-stated. For a given $x$ the sign of $\text{logit}\,\hat p(x)$ is fixed, so $m(x) = \text{logit}\,\tau^* \mp (\text{base} + \sum_j \phi_j)$ is *affine* in the $\phi_j$, and by linearity of Shapley values the deficit's attributions on that branch are simply $\mp\phi_j$. Non-additivity bites only across the sign branch. This makes the requested fix cheap rather than impossible — useful for the editor to know, since it converts R3-34's demand from a research question into a one-line addition.

*(Examiner C)*

### R3-05 — CONFIRMED

> Methods (§3.8): "declined because feature A pulls toward positive while features B and C pull toward negative, leaving confidence below the certified bar."
> Results (§4.6): "so the abstention reads as 'declined because the informative features leave confidence below the certified bar' rather than an opaque refusal."

Verified verbatim. The delivered sentence names no feature and no direction. §4.6 reports for declined cases only scores (0.5262, 0.5445) and margins (0.0956, 0.0223); the claim "In each declined case the signed attributions localize the confidence deficit to specific features" is made without exhibiting a single $\phi_j$ value. The nearest thing in the manuscript is the cohort mean $|\phi_0| = 1.722$ on declined cases — which is unsigned and aggregated over the two cases, not a per-case attribution.

*(Examiner C)*

### R3-06 — CONFIRMED

> "At the cohort level, feature 0 is the dominant abstention driver: its mean absolute attribution is 0.868 on answered cases but 1.722 on declined cases" (§4.6); "identifying it as the dominant systematic abstention driver" (Figure 5 caption)

The reasoning holds. A case is declined precisely when $|\text{base} + \sum_j \phi_j|$ is small — i.e. when signed contributions cancel — so a large mean $|\phi_j|$ on declined cases identifies a feature that *had to be offset*, not one that caused the abstention. A per-feature magnitude statistic cannot separate that from a variance/scale effect. The causal word "driver" is not licensed by the statistic reported.

*(Examiner C)*

### R3-08 — CONFIRMED

> "**Replication design.** Every experiment runs in mode FULL … and replicates over $R = 200$ independent calibration draws." (§4.1, line 156) versus "This case study uses a deployment with threshold $\tau^* = 0.55$" (§4.6) and "E6 uses a separate deployment (threshold $\tau^* = 0.77$; 40 target sites)" (§4.7)

Both §4.6 and §4.7 describe a singular "deployment", report point values with no $R$ and no intervals, and neither flags a departure from §4.1's blanket statement. The finding is properly framed as a manuscript-internal contradiction, so criterion 6 does not reach it. **Co-discovery:** R4-04 reaches the same conclusion from the artifact.

*(Examiner C)*

### R3-09 — CONFIRMED

> "The global standardized importances recover the generator: features 0–3 dominate at 1.157, 1.161, 1.178, and 1.155, while features 4–7 are negligible ($|\cdot| \le 0.036$)." (§4.6, line 192)

I ran the search myself: `grep -i "faithful|plausib|user study|human evaluation"` returns **zero matches** across the manuscript. The vacuity argument is sound: $\phi_j = w_j(x_j-\mu_j)$ is a deterministic function of the fitted coefficients, so if the fit recovers the signal the attributions recover it necessarily — the check tests model fit, not explanation fidelity.

*(Examiner C)*

### R3-10 — CONFIRMED

> §1: "what a clinician weighs before trusting an automated triage, and what an auditor asks to see documented"; §4.1: "Each record carries $d = 8$ features … features 0–3 are informative and features 4–7 are noise"

Verified: every feature in the manuscript is an integer index; no feature carries a clinical name anywhere. No human evaluation is reported, and — checked against §5, §6 and §6.1 — the absence is never stated. Merged into this: R2-25, which independently reaches the same conclusion from the clinical side and adds two concrete asks worth preserving (one worked vignette with plausibly named clinical features and an EHR-facing abstention message; one sentence in §5 conceding the layer's clinical utility is untested).

*(Examiner C)*

### R3-11 — CONFIRMED

> §3.8: "A stronger black-box head can be substituted at a visible cost in coverage; we use logistic regression here because the explainability requirement, not the certificate, calls for a transparent head."
> §5.3: "A black-box head can be swapped in; the gate would then price its selective quality visibly, as a change in certified coverage"

I read §5.3 in full (line 216): it discusses only coverage. The specific claim — §5.3 is silent on the explanation cost of the swap — is exactly true. §3.8's clause partially anticipates it by naming the explainability requirement as the reason for the linear head, but neither section states what explanation the system would produce under a black-box head, nor that Contribution 3 would not survive.

*(Examiner C)*

### R3-12 — CONFIRMED

> "This case study uses a deployment with threshold $\tau^* = 0.55$, answering 200 cases and declining 2." (§4.6) against "a grid of 23 values evenly spaced in $[0.55, 0.99]$" (§3.5)

0.55 is the grid minimum. Coverage $200/202 = 0.990$, verified — an operating point that appears nowhere else (E1: 0.9722; E6: $\tau^*=0.77$ at ~0.90). I read §4.6 in full: it never states whether the deployment was certified, under which mode, or at which $\alpha$. Given that "attachment to a *certified* decision" is the claimed novelty (R3-03), the demonstration does not establish the claim.

*(Examiner C)*

### R3-13 — CONFIRMED (with the deletion test qualified)

> Title: "…with label-shift robustness and explainable abstention"; Abstract: "so the gate can explain what it refuses as well as what it predicts"; Keyword: "Explainable abstention" — against "a supporting capability the linear head makes nearly free" (§3.8) and "This is the central contribution" applied to Contribution 1 (line 31)

All four quotations verified verbatim. I checked the deletion claim directly: the estimand (§3.3), betting test (§3.4), threshold walk (§3.5), assumption modes (§3.6), guarantee (§3.7), validation protocol (§3.9), E1–E4 and Appendix A all run without consuming an attribution. **Qualification:** deleting *all* of §3.8 would also remove the model-agnosticism statement §5.3 builds on and the composition artifact whose results occupy §4.7 and Table 3 — R3's own report accounts for the latter, but the finding as filed does not.

*(Examiner C)*

### R3-14 — CONFIRMED

> "what a clinician weighs before trusting an automated triage, and what an auditor asks to see documented" (§1)

Verified against all 31 bibliography entries: Ghassemi/Oakden-Rayner/Beam, Tonekaboni et al., and Rudin are all absent. The manuscript's explanation citations are exactly the four named — `lundberg2017shap`, `artelt2022reject`, `ifac2025abstainexplain`, `l2lore2025`. The Rudin observation is worth forwarding as constructive: it would convert the transparent-head choice from an unanchored decision into a positioned one.

*(Examiner C)*

### R3-15 — CONFIRMED

> "what the gate adds is that the same exact attributions accompany a certified decision" (§3.8)

Neither Antorán et al. (CLUE) nor Wachter et al. appears in the bibliography, and the explanation citation set contains no uncertainty-explanation or counterfactual-explanation entry. CLUE's subject — explaining why a model is uncertain about a given input — is the paper's declined-case problem, so the omission is on point rather than incidental.

*(Examiner C)*

### R3-17 — CONFIRMED

> §6.1 lists exactly six italicized limitations (lines 234–244): concept shift, excluded covariate-shift mode, no out-of-support screen, unmodelled temporal correlation, missingness without a positivity diagnostic, and the BBSE bootstrap's asymptotic step.

I read all six. Every one is statistical; not one concerns explanation. Against §6's own "Its posture throughout is disclosure", the asymmetry is exactly as the finding describes.

*(Examiner C)*

### R3-18 — CONFIRMED (with a small undercount)

> "routing the hard ones to a clinician [@chow1970reject; @elyaniv2010selective]" (§1) and "otherwise it abstains and defers the case to human judgment" (§3.1)

I ran the search: `grep -i "education|human-cent|human cent|workflow"` returns **zero matches**; "training" occurs twice, both as "training records" (§1) and "training-split" (§3.8). The venue card does frame explainability as "an educational aid for clinicians", so the premise is correct. **Small correction:** §1 also contains "what a clinician weighs before trusting an automated triage", a third human-facing sentence, so "only two" undercounts by one.

*(Examiner C)*

### R3-19 — CONFIRMED

> "the oracle true-class fraction (available in the synthetic harness only)" (§3.8, line 132); "But without the oracle column one could not confirm the certificate was not being earned by hiding a large positive load" (§4.7, line 202)

Both verified verbatim. On kill criterion 5: these are admissions, not defended scope boundaries — no defence is offered and no real-deployment substitute is proposed — so the criterion downgrades rather than kills. The finding itself credits the honesty, which is the right register.

*(Examiner C)*

### R3-20 — CONFIRMED (undercount corrected upward)

I enumerated the attribution-attached uses of "exact": Abstract ("an exact feature attribution"); §1 line 25 ("exact linear attributions"); Contribution 3 heading ("Exact explanations attached to every certified decision") and its body ("exact additive attributions"); §2.4 ("exact attributions on a certified gate"); §3.8 ("exact additive attributions", "exact Shapley values", "the same exact attributions"); §4.6 ("exact additive attributions"). That is **nine**, not seven, plus "genuine Shapley values, not sampled approximations". The finding undercounts, which strengthens rather than weakens it.

*(Examiner C)*

### R3-21 — CONFIRMED

> "*Globally*, the standardized coefficients — the coefficients learned on standardized inputs — give the direction and strength of each feature." (§3.8, line 130)

A standardized coefficient is a conditional effect given the other model features, not a marginal importance. Under the ~0.09 marginal correlation among features 0–3 that the generator induces (computed under R3-01), the two readings diverge — and §4.6 then uses these same coefficients as ground-truth-recovery evidence.

*(Examiner C)*

### R3-22 — CONFIRMED

> "$\phi_j(x) = w_j(x_j - \mu_j)$ with $\text{logit}(\hat{p}(x)) = \text{base} + \sum_j \phi_j$" (§3.8, line 130)

`grep` confirms `\mu` occurs at exactly two lines: line 92 (the betting test's running mean $\hat\mu$, a different object) and line 130. `\text{base}` occurs at line 130 only. Neither $\mu_j$ nor "base" is defined anywhere, while $\text{sd}_j$ is defined in the same sentence — which is what makes the omission conspicuous. **Co-discovery:** DS-25, R1-43, R2-45 (four referees on $\mu_j$).

*(Examiner C)*

### R3-23 — CONFIRMED

> "(gap $-0.854$; gap ranking $[0, 3, 2, 1, \dots]$; top gap feature 0)" (§4.6); "(`tilt_pushes_risk_above_alpha` true)" and "reason `e3-control-not-poisonous`" (§4.4)

Verified verbatim. "gap ranking" is never defined, and the ellipsis does hide features 4–7 — the reader cannot see whether the noise features rank above or below the informative ones, which is exactly the check that would test the driver claim.

*(Examiner C)*

### R3-24 — CONFIRMED *(survivor of the figures cluster)*

> The "# Figures" section (lines 298–310) runs from "**Figure 1. E1 in-distribution validity.**" to "**Figure 6. E6 per-site coverage and answered error.**"

I verified independently: `grep -i "!\[|\.png|\.pdf|\.svg"` returns **zero image references**, and `ls paper/` shows only `TODO.md`, `draft.md`, `references.bib` and `review/` — no image files accompany the manuscript. I also confirmed the stronger fact DS-05 reports: the string "Figure" appears **only** at lines 298–310, so no figure is called out anywhere in §1–§6 or the appendices. Figure 5 — the only figure in R3's remit — is unreviewable.
**Co-discovery:** DS-05, R1-42, R2-30, R3-24/R3-46, R5-15 — five of six referees.

*(Examiner C)*

### R3-25 — CONFIRMED

> "Right: the answered-minus-declined gap in mean absolute attribution per feature; feature 0 shows the largest gap ($-0.854$; 0.868 answered vs 1.722 declined), identifying it as the dominant systematic abstention driver." (Figure 5 caption, line 308)

Verified verbatim: the caption carries no $n$. Kept separate from R2-19 because the defect is in a different passage — a caption that must stand alone for a reader who does not read §4.6.

*(Examiner C)*

### R3-26 — CONFIRMED

> "At the cohort level, feature 0 is the dominant abstention driver" (§4.6, line 196)

I read §4.6 in full: it states neither how many sites the 202 records come from nor how many draws they represent. In a manuscript whose central claim is that the site is the unit of independence, an aggregate statistic with unspecified site structure is a real gap, not a stylistic one.

*(Examiner C)*

### R3-29 — CONFIRMED

> "The reject option dates to Chow [@chow1970reject]; El-Yaniv and Wiener [@elyaniv2010selective] formalized the risk–coverage tradeoff, and Geifman and El-Yaniv [@geifman2017selective] turned it into a finite-sample selective-risk certificate on i.i.d. records." (§2.1, line 42)

Verified against all 31 entries: neither Cortes, DeSalvo & Mohri (ALT 2016) nor Hendrickx et al. (*Machine Learning*, 2024) appears. The survey omission is the more consequential of the two for a paper whose title contains "abstention".

*(Examiner C)*

### R3-30 — CONFIRMED

> "For a linear model these attributions are exact Shapley values, with no approximation or sampling [@lundberg2017shap]." (§3.8)

Verified: `lundberg2017shap` is the sole Shapley citation in the bibliography. Shapley (1953), Štrumbelj & Kononenko (2014) and Kumar et al. (ICML 2020) are all absent. The Kumar omission connects directly to R3-06 — it is the standing critique of exactly the magnitude-as-importance move §4.6 makes.

*(Examiner C)*

### R3-31 — CONFIRMED

> "routing the hard ones to a clinician [@chow1970reject; @elyaniv2010selective]" (§1); "otherwise it abstains and defers the case to human judgment" (§3.1)

Verified: neither Madras et al. (NeurIPS 2018) nor Mozannar & Sontag (ICML 2020) is in the bibliography, and the manuscript nowhere scopes its expert-agnostic abstention against that literature. **Co-discovery:** DS-14, R1-17, R2-22.

*(Examiner C)*

### R3-32 — CONFIRMED (with a trivial correction)

> "Three artifacts make the gate explainable." (§3.8, line 130) followed by "A fourth artifact guards against a subtler failure." (line 132), with results at "The composition analysis (Table 3)" (§4.7, line 202)

Verified verbatim. **Correction:** the fourth artifact is introduced one paragraph later, not two.

*(Examiner C)*

### R3-33 — CONFIRMED

> "what a clinician weighs before trusting an automated triage, and what an auditor asks to see documented" (§1, line 19)

Verified: two empirical claims about human behaviour with no citation attached. The preceding citation pair `[@chow1970reject; @elyaniv2010selective]` sits on the prior clause about routing hard cases to a clinician, not on these claims. **Co-discovery:** DS-41.

---

*(Examiner C)*

### R4-01 — **CONFIRMED**

Anchor located, §4.1 line 152: *"The cohort follows the specification frozen in `data.py`: 208 collection sites … with the two class means separated by $\mathrm{sep} = 2.2$ along that direction."* Against `experiments/run_synthetic.py:40` `SHIFT_SEP = 1.8  # realistic head so shift bites`, consumed at `:195` (`run_E2`) and `:264` (`run_E3`) as `SimConfig(sep=SHIFT_SEP)`. `certgate/data.py:50` does default `sep: float = 2.2`, and E1/E4/E5/E6 use bare `SimConfig()` — so the split is exactly as alleged.

I grepped the whole draft for `sep`: **it occurs once, at line 152.** §4.3 and §4.4 say nothing about the generator. There is no scoping passage anywhere that could invoke kill criterion 5. The two experiments running the undisclosed value are precisely the two producing 48.5% and 83%.

*(Examiner D)*

### R4-02 — **CONFIRMED**

Anchor located, §3.2 line 68, verbatim as quoted, including *"a lightweight, machine-verifiable substitute for pre-registration"*. `tests/test_constants.py` imports `certgate.constants` only and pins its scalars literally — I read all 86 lines. Verified unpinned by any test: `ANCHOR_SITES=208`, `SHIFT_SEP=1.8`, `SHIFT_BASE=0.22`, `CONCEPT_INTERCEPT=2.0`, `FULL_SWEEP`, `QUICK_SWEEP`, the inline `R = 10 if quick else 200`, and every `SimConfig` default. I grepped `tests/` for any assertion on `.sep`, `base_rate`, `size_mu`, `size_sigma`, `s_u`, `== 2.2`, `== 0.095` — **zero hits**; `SimConfig` is only ever *constructed* (test_explain:16, test_pipeline:20/65, test_realdata_path:47, test_shift:30, test_validate:118). `report._bootstrap_estimate(..., n_boot=500)` likewise unpinned. The finding's scope claim is exactly right.

*(Examiner D)*

### R4-03 — **CONFIRMED**

Anchor located, §6.1 line 242: *"Missing values pass through the frozen encoder's imputation-and-indicator scheme; we do not add a dedicated positivity (overlap) diagnostic."* I grepped `certgate/`, `examples/`, `experiments/`, `tests/` for `imput|indicator|encoder|missing`: the only hits are `data.py:4` (a docstring saying missingness machinery was *dropped*), `validate.py:60/82/155` and `examples/real_data_example.py:156` (error-message prose), and `test_validate.py:53` (a comment). No encoder, no imputation, no indicator exists. `certgate/validate.py:139` raises `CohortError("make_cohort: x contains non-finite values (NaN/inf)")`; `certgate/pipeline.py:109-112` raises `ValueError(... reason=nonfinite-features)`. The described behaviour is the inverse of the implemented behaviour. Co-discovered independently by **R5-30** from the manuscript alone ("a component described nowhere in the Methods or Results and inapplicable to a generator that produces complete features") — two referees reaching the same defect from opposite directions is strong evidence.

*(Examiner D)*

### R4-04 — **CONFIRMED**

Anchor located, §4.1 line 156: *"Every experiment runs in mode FULL under protocol seed 20260721 … and replicates over $R = 200$ independent calibration draws."* `run_E5` (`:398-401`) takes `rng = _rng(5)`, one cohort, one deployment; `run_E6` (`:461-465`) takes `rng = _rng(6)`, one cohort, one deployment. Neither has an `R` loop; both accept `quick` and ignore it. §4.6/§4.7 call them "case study" and "a separate deployment" but nowhere state R=1 or that no sampling uncertainty attaches — insufficient to invoke kill criterion 2 against a blanket "Every experiment". Co-discovered by **R3-08** and **R3-43** from the manuscript alone.

*(Examiner D)*

### R4-05 — **CONFIRMED**

Anchor located, §A.3 line 268: *"each report artifact embeds a provenance block recording package versions, seeds, and input hashes."* `report.provenance()` (`report.py:29-59`) does construct the block and `pipeline.py:130` attaches it — so the sentence is true of the in-memory report object, and `test_pipeline.py:90-99` confirms it. But I grepped all of `experiments/out/` for `provenance|input_hash|timestamp_utc|python.*3\.13`: **zero files match.** `_write_csv` field lists exclude it; `E5_explain.json` and `E6_composition.json` are built from explicit payload dicts; `summary.md` carries only mode/seed/ladder. The finding's factual assertion — no released artifact carries a package version, input hash, or Python version — is verified exactly. The defect is that a reader auditing the *release* cannot check what §A.3 promises.

*(Examiner D)*

### R4-06 — **CONFIRMED**

Anchor located, §4.5 line 186, verbatim including *"not by the betting test's information floor. We say so explicitly because the two failure modes have different remedies."* `_cert_eval` populates `out["decline_reason"]` at `run_synthetic.py:79/82/86`, including the structural gate reason. The three `_write_csv` field lists at `:124-127`, `:295-297`, `:347-349` all omit it. I counted occurrences of `insufficient-clusters` across every released artifact: **E1 0, E2 0, E3 0, E4 0, E6 0, summary.md 0.** The `gate_note` in summary.md is derived arithmetically at `:370-375` from `n_sites < 125`, not from any recorded reason. The distinction §4.5 says it is drawing explicitly is unrecoverable from the release.

*(Examiner D)*

### R4-07 — **CONFIRMED**

Anchor located, §4.3 line 174: *"BBSE declines the remaining 95.5% of draws (decline rate 0.955) rather than issue an unsupported certificate."* I tabulated `E2_label_shift.csv` myself:

| α | outcome | count |
|---|---|---|
| 0.10 | `certified=False`, `bbse_reason=failsafe` | **191** |
| 0.10 | `certified=True` | **9** |
| 0.05 | `certified=False`, `bbse_reason=failsafe` | **200** |

Zero `bbse-ill-conditioned`, zero `bbse-degenerate-bootstrap`, zero `bbse-misspecified` — the three declines §3.6 devotes a paragraph to fire **never** in any reported experiment. `failsafe` is set at `shift.py:216` when the walk certifies no threshold, the same outcome the baseline would report. `fit_bbse` computes `c0_ci`, `c1_ci`, `pi_s_ci`, `gap_lo`, `n_boot`, `n_attempts` (`shift.py:118-124`) and `rho_lo/rho_hi/rho_point` (`:148`) into `BBSEFit.diagnostics`; `run_synthetic.py` writes none of them.

*(Examiner D)*

### R4-08 — **CONFIRMED**

Anchor located, §4.1 line 158 (*"we accompany the primary rates with exact (Clopper–Pearson) 95% confidence intervals"*) and §4.3 line 174 (*"the hard-violation rate among them is 0.0"*). Both parts verified independently:

*(a)* I grepped `experiments/run_synthetic.py` for `scipy|clopper|beta.ppf` — **zero hits**; its imports are argparse, csv, json, os, re, matplotlib, numpy, and `certgate.*`. No interval appears in `summary.md`. The four published intervals were computed off-artifact.

*(b)* I recomputed all five relevant Clopper–Pearson intervals:

| k/n | exact 95% CI | manuscript |
|---|---|---|
| 2/200 | [0.0012, 0.0357] | [0.001, 0.036] ✓ |
| 97/200 | [0.4139, 0.5565] | [0.414, 0.557] ✓ |
| 0/200 | [0, 0.0183] | [0, 0.018] ✓ |
| 166/200 | [0.7706, 0.8793] | [0.771, 0.879] ✓ |
| **0/9** | **[0, 0.3363]** | **omitted** |

0.3363 / 0.05 = **6.7×** δ. R4's arithmetic is exact. The flattering interval over 200 and the unflattering one over 9 sit in the same paragraph.
*Co-discovery (outside my set, for the editor to reconcile):* **DS-03, DS-20, R1-09, R2-03, R5-06, R5-65** all flag the missing 0/9 interval from the manuscript alone. R4-08 has the sharpest anchor: it adds the artifact-provenance half (no CP code in the release) that only R4 could see, and the exact 0.336.

*(Examiner D)*

### R4-09 — **CONFIRMED**

Anchors located at §3.2 line 66 and §4.1 line 154 — I grepped `"touched exactly once"` and it appears in exactly those two places. Against `report.py`: `_bootstrap_estimate(head, cal, tau, ...)` at `:86-115` (a 500-draw cluster bootstrap over `cal` sites), `_rm_vs_unweighted(head, cal, tau, ...)` at `:118-139`, `_capped_influence_share(cal)` at `:142-147`, plus `n_carrying` reads at `pipeline.py:134` and `report.py:185`. The referee concedes these feed the estimated/diagnostic tiers only and alleges no validity leak; the finding is that a flat factual claim about the code, repeated twice and load-bearing for the data-discipline argument, is false as written. It is.
*Note for the editor:* **R1-21** and **R2-32** attack the same sentence by a different mechanism (the 23-threshold walk). Same passage, different defect — three referees converging on one sentence is itself signal, but do not merge them: R4-09 is the only one that could open the code.

*(Examiner D)*

### R4-10 — **CONFIRMED**

Anchor located, §4.6 line 196 and the Figure 5 caption at line 308, both verbatim. `E5_explain.json` reads `"n_answered": 200, "n_declined": 2`, `"tau_star": 0.55`; `constants.py:19` `TAU_GRID = np.linspace(0.55, 0.99, 23)` so 0.55 is `TAU_GRID[0]`, the grid floor, and `fixed_sequence_walk` deploys `min(certified, key=tau)`. `mean_abs_phi_declined[0] = 1.722355…` — a mean of two numbers quoted to three decimals, carrying the word "systematically".

*Mitigation I am obliged to record:* §4.6 does state *"answering 200 cases and declining 2"* two sentences earlier, which R4 acknowledges. That blunts the non-disclosure charge for the body but not for the Figure 5 caption, which travels separately and omits it; and it does not touch the inferential claim, which no n=2 sample supports at any level of disclosure. The finding survives on the inference, not only on the disclosure.
*Co-discovery:* the most-replicated finding in the pool — **DS-11, DS-50, R1-30, R2-19, R2-66, R3-07, R3-25, R3-35, R3-42, R5-14** and R4's own R4-46(b). Ten independent flags.

*(Examiner D)*

### R4-11 — **CONFIRMED**

Anchor located, §3.9 line 138, verbatim. I grepped `tests/` for `harness`, `wilson`, `exceedance`, `SIZE_BINS`, `hard_violation`: the only hit is the word "harness" inside a `test_realdata_path.py:11` docstring about the loader contract. **No test file imports `certgate.harness`; no assertion touches `wilson_lcb`, `hard_violation`, `exceedance_reference` or `SIZE_BINS`.** These three functions (`harness.py:23-58`) produce 0.01, 0.485, 0.0, 0.83 and every binomial reference in Table 1 and Figure 1, and `SIZE_BINS` (`:20`) defines the rows of Tables 1 and 2.

*(Examiner D)*

### R4-12 — **CONFIRMED**

Anchor located verbatim at `tests/test_shift.py:72-76`. I traced `certify_bbse`'s return range: `reason` is `fit.reason` when `fit.declined` (`shift.py:189`), `"failsafe"` when nothing certifies (`:216`), else `None` (`:221`). `fit.reason` can only be one of the three named declines. The asserted set `{None} ∪ {failsafe, bbse-degenerate-bootstrap, bbse-ill-conditioned, bbse-misspecified}` is therefore the **complete** range, and step 1 of the same test has already asserted `not fit.declined`, narrowing it further to `{None, "failsafe"}`. The assertion cannot fail. The comment above it claims a certify-and-violate check; the test never computes the target-pool risk at the BBSE-certified threshold. Steps 1 and 2 of the same test are genuine — the ρ interval must cover `RHO_TRUE`, and the baseline must be shown to certify *and* violate first.

*(Examiner D)*

### R4-13 — **CONFIRMED** (on limbs (b) and (c); limb (a) does not survive — see kill log)

Anchors located, §4.4 line 178 and §5.1 line 208, verbatim.

*(b)* `run_E3` collects `verified_risk.append(ev["answered_err_rate"])` at `:278` — and `_cert_eval:93` sets `rate = float(err_ans.mean())`, a **realized** answered error rate — only for draws with `ev["certified"]` at α=0.10, then means them at `:284`. So 0.2022 is the mean of up to 200 realized rates, conditioned on certification, evaluated at the certified τ. `summary.md` stores it under the key `verified_mean_answered_risk_alpha0.10`, which is the honest name. §4.4 calls it *"the true mean answered risk"* and §5.1 *"true answered risk"*, in direct conflict with §3.7 clause (3) (*"It bounds the answered-set error parameter, not any single batch's realized error count"*) — the paper's own load-bearing distinction, contradicted in the one experiment whose subject is definitional rigour.

*(c)* The abort path (`:288-293`, `reason=e3-control-not-poisonous`) is untested: no test file imports `experiments` (verified by grep). §4.4 calls it *"enforced, not decorative"* — a claim about code with no test behind it.

*(Examiner D)*

### R4-14 — **CONFIRMED**

Anchor located, §3.7 line 124: *"The guarantee the certificate makes carries five clauses, all of which survive into the deployed guarantee text."* `report._statement` (`report.py:62-83`) does emit all five. `tests/test_pipeline.py:42-45` asserts exactly three substrings: `"per-target-site"`, `"NOT a bound"`, `"OUT OF SCOPE"`. Unpinned: clause (2), emitted as *"all sites certified from one calibration draw share the same 1-0.05 event"*, and clause (5), the asymptotic-bootstrap disclosure, which `report.py:77` emits only when `"bbse" in modes` — and `modes` here is `combined["modes"]`, the modes that certified the deployed τ, not the requested tuple. No test in the suite asserts either substring, and none inspects a BBSE-deployed statement. A regression dropping clause (5) — which §3.7 and §6.1 both make a centrepiece of the disclosure posture — passes green.

*(Examiner D)*

### R4-15 — **CONFIRMED**

Anchor located, §3.8 line 130: *"For a linear model these attributions are exact Shapley values, with no approximation or sampling [@lundberg2017shap]"*, restated §4.6 line 192 as *"genuine Shapley values, not sampled approximations"*. Three manuscript- and code-side facts verified: (i) the claim is stated **unqualified** — no independence condition, no value-function named, anywhere in the draft; (ii) `explain.py:48` implements `phi = head.coef * z`, i.e. exactly `w_j(x_j − μ_j)`; (iii) the generator induces marginal dependence among the explained features — `data.py:64-71` gives `μ_y = ±(sep/2)·v` with `v` supported on coordinates 0–3 and `x|y ~ N(μ_y, I_d)`, so for `i ≠ j` in 0–3 the marginal `Cov(x_i, x_j) = μ_iμ_j·Var(1{y=1}) > 0`. The additive decomposition is exact and correctly pinned by `test_explain.py`; the Shapley identification is the overreach.
*One link I did not verify in-session:* the exact wording of Lundberg & Lee's independence condition, which I could not open. I note that **DS-16, R1-18, R2-24, R3-01, R3-44, R5-12 and R5-60** assert it independently — seven flags across five reports, the joint-highest in the pool.

*(Examiner D)*

### R4-16 — **CONFIRMED** (with one precision correction)

Anchor located, Table 3 line 337, verbatim. `run_E6` (`:463-465`) builds `cfg = SimConfig()` and `draw_cohort(cfg, 40, rng, site_label_prefix="e6t")` — no `label_base_rate`, no `concept_intercept`. Source and target share the generative prevalence, so the true odds ratio is ρ = 1. `E6_composition.json` records `"rho": 0.8296804526028088`, and `run_synthetic.py:501-504` populates `rho` only when `op["deploy_mode"] == "bbse"` — so the presence of the BBSE row is proof that E6's operative deployment at τ* = 0.77 carries the **label-shift** tag, on unshifted data. §4.7 and Table 3 state neither the deploy mode nor its asymptotic-bootstrap caveat.

*Precision correction:* the finding says the manuscript "reports neither the deploy mode nor the size of that spurious correction." The size *is* printed — ρ̂ = 0.830 appears in both §4.7 and Table 3. What is absent is the true ρ = 1 against which 0.830 is a 17% spurious movement, and the deploy mode. Forward the finding on those two absences.
*Co-discovery:* **DS-48, R1-08, R1-58, R5-54** ask the same question from the manuscript alone; R4-16 is the only one that could establish the *deploy mode* from the artifact.

*(Examiner D)*

### R4-17 — **CONFIRMED**

Anchor located, Data availability line 276, verbatim. Verified against the repository root by direct listing: **no `LICENSE`, no `COPYING`, no `pyproject.toml`, no `setup.py`, no `setup.cfg`, no `.git`** (only `.gitignore`). Dangling paths verified: `README.md:3` → `../audit/readiness-report.md`; README "Relation to v1" → `../testbed/`, `../PROTOCOL.md`; `certgate/certify.py:4` → `../testbed/certify.py`; `certgate/shift.py:8` → `../testbed/modes.py`; `certgate/data.py:3` → `../testbed/generator.py`; `report.py:87` → "v1 report.py:14-35". None resolves inside the release.

**Kill criterion 4 does not apply.** The exemption covers author / affiliation / ORCID / corresponding-author placeholders. The data-availability statement is a substantive editorial requirement, not an author field — and in any case the finding's substance (no licence, no packaging, no version control, dangling provenance paths) is entirely independent of the missing URL.
*Co-discovery:* **DS-07, DS-27, R1-36, R2-40, R5-40** flag the placeholder URL; only R4 could establish the licence, packaging and VCS facts.

*(Examiner D)*

### R4-18 — **CONFIRMED**

I opened four PNGs myself.

- **`E3_concept_shift.png`:** title renders as *"E3 concept-shift negative control (certificate shou"* — truncated mid-word, exactly as alleged. The axes occupy roughly the right half of the canvas; the left half is blank; the vertical "no certificates" annotation sits in that blank margin, far outside the axes. Caption line 304 describes this as the figure carrying the negative-control argument.
- **`E1_validity.png`:** the left panel carries a single x-tick, "0.1". The α = 0.05 category has no tick and its "no certificates" annotation is rendered outside the axes at the far left. Caption line 300 claims *"the $\alpha = 0.05$ rung issues no certificates at 208 sites"* — the panel does not visually show this.
- **`E2_label_shift.png`:** two "no certificates" annotations, one inside the axes near x = 0.05 and one clipped at the far-left margin. The BBSE bar at α = 0.10 is zero-height, i.e. visually identical to absent — and absence is the same figure's encoding for "no certificates".

Cause verified in code: `ax.text(i, DELTA*0.05, ...)` / `ax.text(xpos[i]+dx, ...)` at `:170-173`, `:246-250`, `:316-319` place annotations in **data** coordinates at categories whose bar is `np.nan`.

**Editorial note on the word "embedded":** the manuscript embeds no figures. Its `# Figures` section (lines 298–310) is caption prose with no image markup — the point DS-05 / R1-42 / R2-30 / R3-24 / R3-46 / R5-15 make correctly from the manuscript alone. R4-18 is a finding about the *figure files in the artifact*, which those referees could not see. Both are true; forward both.

*(Examiner D)*

### R4-19 — **CONFIRMED**

Anchor located, §3.6 line 118: *"The modes run as alternatives, each at full $\delta$…"* against §3.5 line 100: *"each is tested at the mode's full betting budget ($\delta$ for the baseline, $\delta_{\text{bet}}$ in the label-shift mode of Section 3.6)"*. Code agrees with §3.5: `pipeline.py:65-66` passes `DELTA` (0.05) to `_baseline_walk`; `shift.py:207` passes `BBSE_DELTA_BET` (0.025). Direct internal contradiction, and §3.6 is the side that is wrong.
*Not a duplicate of* **DS-18 / R1-53 / R5-08**, which flag a *different* §3.5-vs-§3.6 contradiction (maximum-coverage vs most-conservative threshold). Two independent contradictions between the same two sections.

*(Examiner D)*

### R4-20 — **CONFIRMED**

`pipeline.py:149-155`: `if int(target_x.shape[0]) < MIN_ANSWERABLE:` → all-declined report with `gate_reason="pool-too-small"`; `constants.py:24` `MIN_ANSWERABLE = 10`. I grepped the draft for `MIN_ANSWERABLE`, `pool-too-small`, `10 records`: **zero hits each.** §3.3 and §4.5 document the cluster gate; §3.6 documents BBSE's three declines; this fourth gate — the one a real deployment with small daily batches hits first — appears nowhere.

*(Examiner D)*

### R4-21 — **CONFIRMED**

Anchor located, §3.2 line 68, enumeration verbatim. I grepped the draft: `1e-4` → 0 hits, `10^{-4}` → 0, `max_iter` → 0, `MIN_ANSWERABLE` → 0. The only `500` in the draft is inside `[20, 5000]` in §4.1, so `_bootstrap_estimate`'s `n_boot=500` (`report.py:86`) is undocumented. `PI_CLIP = 1e-4` is alluded to obliquely in A.2 as *"the clipped $\rho$"* but never valued; `SD_REL_TOL = 1e-9` and `HEAD_MAX_ITER = 2000` are absent. All are in `constants.py` and all govern the procedure.
*Adjacent to R4-20 on `MIN_ANSWERABLE` but not duplicative:* R4-20 concerns an undocumented decline **gate** (§3.3/§3.4/§3.6); R4-21 concerns the constants **enumeration** (§3.2).

*(Examiner D)*

### R4-23 — **CONFIRMED**

Anchor located, §3.9 line 138: bins written as `$\{<30,\ 30\text{–}100,\ 100\text{–}300,\ >300\}$`. `harness.py:20` `SIZE_BINS = ((0, 30), (30, 100), (100, 300), (300, np.inf))`, and both `run_synthetic.py:150` and `:493` filter with `lo <= size < hi`, so the last bin is **≥ 300**. Tables 1 and 2 render it `[300, $\infty$)`. Off by one endpoint, as alleged. Co-discovered by **R5-43** from the manuscript alone.

*(Examiner D)*

### R4-24 — **CONFIRMED**

Anchor located, §3.1 line 62: *"resting on roughly eighty site-level observations, not the $\sim\!10^5$ record-level ones a naive analysis would claim"*; repeated §5.2 line 212. I instantiated the E1 draw-0 cohort under `SeedSequence([SEED, 1, 0])` and measured:

| pool | sites | records |
|---|---|---|
| whole cohort | 208 | 137,533 |
| train | 83 | 55,538 |
| aux | 42 | 30,581 |
| **cal** | **83** | **51,414** |

The sentence pairs "roughly eighty" (= 83 calibration clusters) with "the ~10⁵ record-level ones", so the parallel term is the calibration records, which number 5.14 × 10⁴ — the stated figure overstates by 1.95×, and the whole cohort (1.38 × 10⁵) overstates by 2.67×. R4's "roughly 2×" is right.

*(Examiner D)*

### R4-25 — **CONFIRMED**

Anchor located, Table 4 caption line 340: *"Certify rate and mean answered-set coverage at certifying points; \"—\" where nothing certifies."* `run_synthetic.py:362-364` computes `mean_coverage=round(float(np.mean(...)) if certs else 0.0, 4)` and plots it unmasked at `:382-383`. Verified in `summary.md`, which records `mean_coverage: 0.0` at all six non-certifying grid cells, and verified visually in `E4_site_sweep.png`: the right panel's α = 0.05 line sits flat on 0.0 through n_sites 60/100/150/208 and the α = 0.10 line through 60/100. The figure shows a measured-looking zero-coverage regime the table declares undefined. (R4's "four grid points" reads correctly as the four x-positions 60, 100, 150, 208; if read as table cells the count is six.)

*(Examiner D)*

### R4-26 — **CONFIRMED**

I counted bare `nan` tokens in the released CSVs myself: **E1 200, E2 591, E3 200, E4 1,340 — total 2,331**, matching R4 exactly. `E6_fairness.csv` and `summary.md` are clean (0). Produced by `_cert_eval:78` `answered_err_rate=float("nan")`. Against the artifact's own documented convention at `run_synthetic.py:151-152` (*"empty bins report None (-> JSON null), never NaN: NaN is an invalid JSON token that breaks downstream parsers"*) and `:488-490`. The JSON paths were disciplined; the CSV path was not.

*(Examiner D)*

### R4-27 — **CONFIRMED**

I read all three entries in `paper/references.bib`:
- `ifac2025abstainexplain` (line 249): `booktitle = {… (ECML PKDD 2024)}`, `year = {2024}` — key says 2025, and the "ifac" prefix matches nothing in the entry.
- `l2lore2025` (line 262): `booktitle = {… (DS-LB 2024)}`, `year = {2024}` — key says 2025.
- `angelopoulos2021ltt` (line 169): `journal = {The Annals of Applied Statistics}`, `year = {2025}` — key says 2021.

Since the manuscript cites by key and the rendered list shows the year, these surface as in-text/reference-list mismatches at proof. Co-discovered by **DS-32, R1-37, R2-38, R3-28, R5-34** — five independent flags.

*(Examiner D)*

### R4-28 — **CONFIRMED**

Anchor located, §3.4 line 94: *"The processing order is a deterministic, SHA-256-seeded permutation of the calibration sites"* — singular. `fixed_sequence_walk` (`certify.py:113-127`) passes **one** `rng` object into every `wsr_reject` call, and `wsr_reject:80-81` does `if rng is not None: z = rng.permutation(z)` — so the walk consumes a fresh permutation per threshold from one advancing stream, and the number drawn is data-dependent because the walk breaks at first failure (`:122-123`). Separately, `shift.py:207` `ok = all(wsr_reject(...) for atoms, r in zip(atom_sets, endpoint_rngs))` iterates a generator and short-circuits, so when the ρ_lo endpoint fails the ρ_hi stream never advances — despite the `shift.py:180-183` docstring claiming per-endpoint streams make the result "order-independent". Neither affects validity (each test is independently level-δ); §3.4's singular description is simply not what runs.

*(Examiner D)*

### R4-29 — **CONFIRMED**

`README.md:26`: *"Suite 53/53 green (~4s)."* `README.md` Quickstart: `python -m pytest tests -q   # ~2 min`. I ran the suite: **69 passed in 3.61s**. §A.3 line 268 correctly says *"The test suite is 69/69 green."* So the manuscript is right and the reader-facing instruction set is stale by 16 tests, and its own two runtime figures (~4s vs ~2 min) disagree with each other. (My 3.61s vs R4's 8.65s is machine variance and immaterial to the count claim.)

*(Examiner D)*

### R4-30 — **CONFIRMED**

Verified at `run_synthetic.py:117` (`run_E1`), `:270` (`run_E3`), `:402` (`run_E5`): each calls `draw_cohort(cfg, 1, rng, …)` — a target pool of **one** freshly drawn site. E5's pool holds 202 records (200 answered + 2 declined per `E5_explain.json`). `run_E6:465` draws 40 sites and §4.7 discloses that; E1, E3 and E5 disclose nothing. Since §3.7 clause (1) scopes the guarantee *per target site*, that E1's 200 "pools" are 200 single-site pools is material.
*Adjacent:* **R2-34** and **R5-62** note from the manuscript that "target pool" is never defined; R4-30 supplies the answer they could not reach.

*(Examiner D)*

### R4-31 — **CONFIRMED**

I grepped `tests/` for `experiments`: **zero hits.** The 632-line file producing every number in §4 is outside the 69-test suite, including `_rate` (`:53-56`), `_cert_eval` (`:74-99`), the E3 poison-verification abort (`:284-293`) that §4.4 calls "enforced", and `_existing_summary_blocks` (`:536-546`), the regex merge.

*(Examiner D)*

### R4-32 — **CONFIRMED**

Anchor located verbatim at `tests/test_certify.py:70-76`: docstring *"Level 5%; empirical rate must stay <= 0.08 (documented tolerance)"* with `assert rej / 800 <= 0.08`, one fixed seed (`default_rng(1)`), 800 reps. §A.1(iv) line 258 says *"The test's boundary behaviour (type-I error at $\mathbb{E}[Z] = \alpha$) is additionally pinned by the unit test suite."* A 0.08 ceiling against a 0.05 nominal pins "not grossly anti-conservative at one seed", not level δ. The test is a real check of a real property (`Z ~ Bernoulli(0.05)` sits exactly at the null boundary) — the finding is about the manuscript's word "pinned", and it holds.

*(Examiner D)*

### R4-33 — **CONFIRMED** (with one count correction)

I counted occurrences in `paper/draft.md`:

| number | occurrences | locations |
|---|---|---|
| 0.9722 | 4 | Abstract, §1, §4.2, §4.5 (parenthetical) |
| 0.01 hard-violation | 5 | Abstract, §1, §4.2, §5.1, Fig 1 caption |
| 48.5% | 5 | Abstract, §1, contribution 2, §4.3, Fig 2 caption |
| 83% | **4** | Abstract, §4.4, §5.1, Fig 3 caption |
| 95.5% | 3 | Abstract, §1, §4.3 |
| 0.0551 / 0.4915 | 3 | §4.2, §5.1, (0.4915 also Fig 1 area) |

So "each restated five times" holds for 48.5% and for the E1 pair taken together; 83% is four. The substantive claim is verified exactly: Figure 1's caption reproduces *"0.01 (2 of 200 calibration draws)"* and *"0.0189 vs 0.4820 for [100,300)"* verbatim from §4.2, Figure 2's reproduces "48.5%", Figure 3's reproduces "83%" — captions restate body numbers rather than describing panel content.

*(Examiner D)*

### R4-34 — **CONFIRMED**

Anchor located, §2.4 line 54: *"certified record-level selective-risk rules overrun their budget by 9–30% under grouped deployment [@zhou2026falsesense]"*, stated as fact and reused in §1 (line 23) and §4 (line 148). `paper/references.bib:284` is `@misc{zhou2026falsesense, … eprint = {2606.15153}, archivePrefix = {arXiv}}`. I enumerated every entry type: **seven `@misc` arXiv preprints** — `yu2026joint` (273), `zhou2026falsesense` (284), `triage2026audit` (294), `fedcrc2026` (305), `score2026` (316), `scrc2025` (326), `thermal2026audit` (337) — i.e. the cited one plus six further, exactly as the finding states, out of 31 entries.
*Co-discovery:* **DS-13, DS-59, R1-20, R1-68, R2-23, R2-69, R5-18, R5-66.**

*(Examiner D)*

### R4-35 — **CONFIRMED**

Anchor located, §2.2 line 46, verbatim. I grepped `references.bib` for `barber|gibbs|beyond exchangeability|covariate shift`: the only hit is `Lee, Barber and Willett` (hierarchical conformal, line 210). **Barber, Candès, Ramdas & Tibshirani (2023), Gibbs/Cherian/Candès, and Tibshirani et al. (2019) are all absent.** The first is the canonical treatment of exactly the failure §2.2 builds its motivation on; the third is what §6.1 should cite where it excludes covariate-shift weighting. R4 correctly concedes the positioning survives all three.
*Co-discovery:* **DS-14, R1-17, R5-19**, and partly **R3-14 / R3-15** on the XAI side.

*(Examiner D)*

### R4-36 — **CONFIRMED** (question, properly anchored)

The factual predicate is R4-01, verified above: `SHIFT_SEP = 1.8` at `run_synthetic.py:40`, used only at `:195` and `:264`, against §4.1's single stated `sep = 2.2`. The three asks (why the drop; the E2/E3 rates at 2.2; whether 1.8 was chosen before or after seeing results at 2.2) are answerable and material. Forward.

*(Examiner D)*

### R4-37 — **CONFIRMED** (question, properly anchored)

Predicate verified: `shift.py:118-124` and `:148` compute `c0_ci`, `c1_ci`, `pi_s_ci`, `gap_lo`, `rho_lo`, `rho_hi`, `rho_point`, `n_boot`, `n_attempts` into `BBSEFit.diagnostics`; `E2_label_shift.csv`'s eleven columns carry none of them; and all 191 declines are `failsafe` (my own tabulation). The single-endpoint-at-full-δ comparison the question asks for is the one measurement that would separate "correctly refusing" from "underpowered". Forward.

*(Examiner D)*

### R4-38 — **CONFIRMED** (question, properly anchored)

Predicate verified: `E6_composition.json` records `rho = 0.8296804526028088` on a cohort built at `run_synthetic.py:463-465` with `SimConfig()` and no shift, so true ρ = 1.

I can partly answer the question's second half from the artifact, which strengthens it: across E1's 200 in-distribution draws at α = 0.10, the deployed mode is **baseline 147, bbse 53** — the BBSE tag wins deployment on **26.5%** of in-distribution draws (E3: 34/200). That is recoverable from `E1_validity.csv`'s `deploy_mode` column and appears nowhere in the manuscript. Forward.

*(Examiner D)*

### R4-39 — **CONFIRMED** (question, properly anchored)

Predicate verified: `pipeline.py:176-185` runs a separate walk per α, each at its mode's full budget; `report.py:205-217` iterates the ladder strictest-first and sets `operative` at the first certified rung (`:212` `if operative is None:  # strictest (first) certified alpha`). §3.5 line 102 says only *"Both budgets $\alpha \in \{0.05, 0.10\}$ are certified by separate walks"*. The manuscript documents the within-mode fixed-sequence argument (§3.5) and the across-mode OR-rule (§3.6) but never the across-rung selection. A real gap in the stated guarantee. Forward.

*(Examiner D)*

### R4-40 — **CONFIRMED** (question, properly anchored)

Predicate verified under R4-17: no licence, no packaging, no VCS. Second half verified: `README.md`'s repository map lists `METHODS.md`, `PAPER-OUTLINE.md` and `SPEC.md` as part of the deliverable. Kill criterion 4 does not reach this — see R4-17. Forward.

*(Examiner D)*

### R4-41 — **CONFIRMED** (question, properly anchored)

Predicate verified: `_existing_summary_blocks` (`:536-546`) parses an existing `summary.md` by regex `^## (E\d)\n(```json\n.*?\n```)` and `_write_summary:562-563` substitutes preserved blocks for experiments not recomputed — so a `--only` run genuinely can assemble a `summary.md` across partial runs. §A.3 line 268 says *"The full grid runs from a single command."* With no provenance block written (R4-05), nothing in the artifact lets a reader tell which happened, and §4.5's explicit E1-vs-E4 208-site distinction makes the answer material. Forward.

*(Examiner D)*

### R4-42 — **CONFIRMED** (confidential, positive — scope of my re-verification stated)

I independently re-verified the parts I could:
- **Test suite:** `python -m pytest tests -q` → **69 passed**, matching §A.3's "69/69 green".
- **Clopper–Pearson:** all four published intervals recomputed and correct to the stated rounding (table under R4-08).
- **Determinism:** `python -m experiments.run_synthetic --only E5,E6` into a clean scratch directory reproduced `E5_explain.json`, `E6_composition.json`, `E6_fairness.csv` **and** `E5_explain.png`, `E6_fairness.png` byte-for-byte by SHA-256.
- **Numbers:** I traced against `summary.md`, the CSVs and the JSONs: 0.9722, 0.01 / 2-of-200, 0.05 exceedance, the four Table 1 bins (2/18/53/127 with 0.0000/0.1111/0.0189/0.0551 vs 0.4063/0.4689/0.4820/0.4915), 0.485, 0.685, 9 certified, 0.955, 0.2022, 0.83, 0.935, the full Table 4 grid including 0.7376 and 0.8455 and 0.9304/0.9715/0.9601/0.9621, the E5 importances 1.157/1.161/1.178/1.155 and gap −0.854 and 0.868/1.722, and the E6 composition 23,325 / 917 / 0.0393 / 1,378.9 / 0.0591 / 1,470 / 0.0630 / ρ̂ 0.830 and bins 0.9191/0.8966/0.9063 and 0.0294/0.0406/0.0348. **Every one matched.**

Not re-verified by me: byte-identity of E1–E4 (I did not re-run the heavy grid) and the universal quantifier "*every* quantitative claim". Everything I checked held, and I found no drifted or fabricated number. The finding stands as stated for the scope I could exercise.

*(Examiner D)*

### R4-43 — **CONFIRMED** (confidential; factual predicate verified, recommendation is the editor's)

Both predicates verified above: R4-01 (sep=1.8 undisclosed in the two headline experiments) and R4-02 (that parameter sits outside the pinned set). The anchor quote from §3.2 — *"it removes the degrees of freedom that would otherwise let a tunable pipeline flatter itself"* — is verbatim at line 68. The characterisation "the exact shape of a researcher degree of freedom" follows from the verified facts; the code comment *"realistic head so shift bites"* is real. Whether disclosure plus a sensitivity table becomes a *condition of acceptance* is a decision reserved to the editor, and I make no call on it.

*(Examiner D)*

### R4-44 — **CONFIRMED** (confidential)

Predicate verified under R4-07: 191/191 declines are the generic `failsafe`; the three named BBSE declines fire zero times; and the discriminating quantities (ρ̂, ρ interval, `gap_lo`, failing endpoint) are computed in `BBSEFit.diagnostics` and written to no artifact. The structural claim is also verified: `certify_bbse` must reject at **both** endpoints (`shift.py:207`) at `BBSE_DELTA_BET = 0.025`, i.e. two tests at half the baseline's budget. So "correctly refusing" and "underpowered at two endpoints on half δ" do predict the same observable, and the artifact as released cannot arbitrate. E2 is currently unfalsifiable from the release, as stated.

*(Examiner D)*

### R4-45 — **CONFIRMED** (confidential)

Both halves verified. The core *is* well tested: I read `test_certify.py:46-67` (`test_mcap_counterexample_regression` — 140 clean + 10 heavy sites, 17.5% true risk, asserts the truncation reading certifies and the influence path refuses) and `test_shift.py:141-164` / `:190-221` (`test_dual_endpoint_soundness_straddling_rho_one` asserts the sign-carrier is affine **and** that the raw atom mean shows the kink, explicitly guarding against re-documenting the false justification; `test_dual_endpoint_loop_requires_both_endpoints` builds two cohorts where each endpoint is separately poisonous). These are genuine adversarial regressions. Against that, `certgate/harness.py` — which decides whether a certificate counts as violated — has **zero** test imports (R4-11). The contrast is real.

*(Examiner D)*

### R4-46 — **CONFIRMED** (confidential)

(a) Predicate verified under R4-03 — the missingness encoder is the only described component wholly absent from the code, and its actual behaviour is the inverse. (b) Predicate verified under R4-10 — `n_declined: 2`, `tau_star: 0.55 = TAU_GRID[0]`. The observation that this is the section the collection's editors will read most closely is consistent with the venue card, on which explainability is the central emphasis.

---

*(Examiner D)*

### R5-01 — CONFIRMED (survivor; DS-02 merged)

> "with probability at least $1-\delta$ over the draw of calibration sites, the influence-weighted answered-set risk — the parameter $R_M$ defined in Section 3.3 — at a new target site is at most $\alpha$" (§3.1) · "$R_M = \frac{\sum_c g_c\, a_c\, e_c}{\sum_c g_c\, a_c}$" (§3.3) · "(1) It is scoped per target site." (§3.7)

The index $c$ in both sums runs over sites, and the betting test in §3.4 tests $\mathbb{E}[Z] \ge \alpha$ over the per-site atoms — a statement about the site population's mean. No step anywhere transports that to a single new site; §3.7 clause (1) asserts per-site scope without derivation, and A.1(ii) reinforces the population reading ("$\mathbb{E}[R_M]$ is a ratio of expectations"). Independently reached by R1-01 and R1-54 — a statistics referee and a forensic referee converging on the paper's headline claim is the strongest co-discovery signal in my set. Remedy questions: DS-47 and R1-54.

*(Examiner A)*

### R5-02 — CONFIRMED

> "The estimand is design-conditional: target features are treated as observed, and it is the label randomness that carries the expectation." (§3.3) · "under $H_0$, $\mathbb{E}[\,1 + \lambda_t(\alpha - Z_t) \mid \mathcal{F}_{t-1}\,] \le 1$, so $K_t$ is a nonnegative supermartingale" (A.1 iii) · "The site-as-unit analysis treats sites as the independent unit and does not model residual cross-site dependence induced by shared time." (§6.1)

Substantive and correct. §3.4 states the null as a **single** expectation, $H_0: \mathbb{E}[Z] \ge \alpha$, which presupposes identically distributed atoms. Under A.1(ii)'s design-conditioning the atoms have site-specific means $\mu_t$, and A.1(iii)'s per-step inequality $1 + \lambda_t(\alpha - \mu_t) \le 1$ fails at any site with $\mu_t < \alpha$ even when the average is $\ge \alpha$ — so the supermartingale property does not follow from the stated null without an exchangeability or i.i.d. assumption on the calibration sites, which the manuscript never states. §6.1 then concedes a dependence structure that would break it. Independently reached in near-identical terms by R1-02; question form at R5-55 and R1-55.

*(Examiner A)*

### R5-03 — CONFIRMED

> "We disclose plainly that this percentile bootstrap box is the single asymptotic step in an otherwise finite-sample chain, and every guarantee statement carries that caveat." (§3.6)

I checked every guarantee statement. §3.7 clause (5) carries it ✓; §6.1 carries it ✓; §1 ¶4 carries it ✓. The **Abstract** does not — "certifies, with finite-sample confidence $1-\delta$, that the error rate among answered cases stays at or below $\alpha$", followed by a label-shift sentence that mentions carrying uncertainty but not asymptotics. The **title** does not — "finite-sample certified selective prediction … with label-shift robustness". The manuscript's own universal quantifier ("every guarantee statement") is falsified by its two most-read lines. Co-discovered by R1-45 for the title limb.

*(Examiner A)*

### R5-04 — CONFIRMED

> Abstract: "certifies, with finite-sample confidence $1-\delta$, that the error rate among answered cases stays at or below $\alpha$" versus §3.7's five clauses

Verified: the abstract's guarantee sentence carries none of (1) per-target-site scope, (2) the shared 1−δ event, (3) parameter-not-count, (4) concept shift out of scope, (5) the BBSE asymptotic link. It does disclose "On a 208-site synthetic cohort," which the editor should credit. This is the one place in the manuscript where **more** hedging is the right revision, and it is compatible with DS-60's warning because it asks for scope clauses the paper already wrote, not for new caveats.

*(Examiner A)*

### R5-05 — CONFIRMED

> §5.1: "E1 shows realized exceedance rising toward its binomial reference (0.0551 against 0.4915 in the largest size bin)" · §4.2: "Across every size bin the observed exceedance sits far below the reference … 0.0551 against 0.4915 in the largest bin), confirming that answered pools are not sitting at the $\alpha$ boundary but well inside it."

A clean internal contradiction on identical numbers, and §4.2 has it right on both counts. Table 1's observed column is 0.0000 / 0.1111 / 0.0189 / 0.0551 — **not monotone rising**; and 0.0551 against 0.4915 is a factor of 8.9 apart, which is not "rising toward". The consequence is not cosmetic: §5.1 uses the sentence to support "It is not a bound on a batch's realized error *count*", and E1's data do not illustrate that point — they show realized counts far below the dispersion reference. Same confusion as R5-48. Co-discovered by R1-26.

*(Examiner A)*

### R5-06 — CONFIRMED (survivor; DS-03 merged. **One clause must be struck.**)

> "conditioning on the 9 draws that did certify ($n_{\text{certified}} = 9$), the hard-violation rate among them is 0.0" (§4.3) · "we accompany the primary rates with exact (Clopper–Pearson) 95% confidence intervals" (§4.1)

Recomputed the exact Clopper–Pearson upper bound for 0/9: **0.3363**, i.e. 6.7× the δ = 0.05 budget. Both anchors verbatim; the omission is real and is the single interval that would show how little was tested.
**Clause the editor must strike:** both DS-03 and R5-06 assert this is "the only rate in the Results reported without the Clopper–Pearson interval." That is **false** — my enumeration (see DS-20) finds intervals on exactly four numbers, with the two overall exceedance rates, both decline rates, all four Table 1 bins, all twelve Table 4 certify rates and every coverage mean equally bare. DS-20 in the *same desk-screen report* says so. Forward the finding without that clause; its force does not depend on it.

*(Examiner A)*

### R5-07 — CONFIRMED

> "Because every rate below is a proportion over $R = 200$ independent draws, we accompany the primary rates with exact (Clopper–Pearson) 95% confidence intervals." (§4.1)

The premise is false as a blanket. Table 1's per-bin exceedances are proportions over 2, 18, 53 and 127 pools (which do sum to 200, confirming one pool per draw), and the BBSE conditional rate is over 9. The sentence's causal structure — *because* every rate is over 200, *therefore* Clopper–Pearson — is what makes it more than pedantry: it is the stated justification for the interval choice, and it does not hold for the stratified rates the paper then reports without intervals. Interlocks with R5-46 and DS-30.

*(Examiner A)*

### R5-09 — CONFIRMED (survivor; DS-12 merged)

> "the validity of the certificate never depends on the quality or calibration of the model producing that score" (§3.8) · "(i) the worst-case confusion gap $(c_1 - c_0) < 0.10$, an ill-conditioned inversion" (§3.6)

The BBSE mode builds the record weights by inverting $q = c_0(1-\pi_t) + c_1\pi_t$ using the classifier's own confusion rates (§3.6), so the certified statistic depends on the head; and the mode refuses to run when the head's confusion gap is too small. A defensible reconciliation exists — model quality governs *availability* (decline) rather than *validity* — but the manuscript nowhere draws that distinction, and §3.8's "never" is unqualified. DS-12's additional limb (no alternative head is ever tested) is verified and is carried by R5-32.

*(Examiner A)*

### R5-10 — CONFIRMED (survivor; DS-10 merged)

> "Real data cannot supply that ground truth, which is what makes it unable to validate a validity claim." (§5.5) · "A certificate counts as violated only when the one-sided 95% Wilson lower confidence bound on the target pool's answered error exceeds $\alpha$ [@wilson1927]." (§3.9)

Decisive pairing. The paper's own primary validity metric — the hard-violation rate, the number required to stay at or below δ, the number reported for E1, E2 and E3 — consumes **only** realized answered errors and a Wilson bound. Retrospective multi-site cohorts supply exactly that. The oracle is used in the paper for one thing only: verifying E3's poison (§4.4). So the stated justification for a synthetic-only evidence base is broader than the paper's own protocol requires. Because §5.5 is the *defence* that would otherwise scope out real-data demands under criterion 5, refuting it also unlocks DS-22 and R5-64. Four-way co-discovery (DS-10 merged; R1-16, R2-26).

*(Examiner A)*

### R5-11 — CONFIRMED (survivor; DS-15 merged)

> "the operative rung is a property of the available cluster count, not of the method — buying $\alpha=0.05$ costs sites, and E4 prices that purchase" (§5.2) · "obstacles that appear only in combination" (§6)

Both claims are comparative and no comparator exists. E4 sweeps *CertGate's own* cluster count; it cannot separate a property of the cluster count from a property of this particular linearized betting construction, whose information floor $\ln(1/\delta)(1-\alpha)/n$ §3.4 itself describes as "a linearized, zero-variance lower bound" — i.e. a bound for this test, not over all procedures. DS-15's comparator list (hierarchical conformal, RCPS/LTT, BBSE without the uncertainty box) is the actionable version and should be carried in the merged text. Co-discovered by R1-10, R1-12, R1-62.

*(Examiner A)*

### R5-12 — CONFIRMED (survivor; DS-16 merged)

> "For a linear model these attributions are exact Shapley values, with no approximation or sampling [@lundberg2017shap]" (§3.8) · "genuine Shapley values, not sampled approximations" (§4.6) · "the class signal lives on a single normalized direction supported on the first four coordinates" (§4.1)

The Linear SHAP identity $\phi_j = w_j(x_j - E[x_j])$ requires either feature independence or the interventional value function; the manuscript states neither. And the generator defeats independence by construction: a two-component label-conditioned mixture whose class means differ along a **single shared direction supported on coordinates 0–3** induces marginal correlation among exactly the features being explained — an inference available from §4.1's text alone, without assuming anything about the covariance. Six-way co-discovery (DS-16 merged; R1-18, R2-24, R3-01/R3-44, R4-15). Question forms: R5-60, R3-37.

*(Examiner A)*

### R5-13 — CONFIRMED (survivor; DS-04 merged)

> §4.1: "This follows the distributional profile reported across multi-site clinical studies — many small-to-large sites with heavy-tailed sizes, single-digit prevalence, and site-level heterogeneity … [@tripodcluster2023; @internalexternal2021]" · §1: "whose lognormal sizes, $\sim$9.5% prevalence, and site random effects follow the distributional profile reported for large multi-site clinical cohorts" — **no citation**

The uncited-introduction limb is fully confirmed: I located line 27 and there is no citation on the sentence. On the §4.1 limb, `tripodcluster2023` is by its own title a **reporting checklist** (TRIPOD-Cluster, BMJ 2023) and cannot be a source of distributional parameters — that much is settled from the bibliography alone. **Residual check:** retrieve Takada et al. 2021 (J Clin Epidemiol 137:83–91) and confirm it reports no site-size distribution, prevalence or between-site heterogeneity parameter; if it does, the §4.1 limb narrows to one citation. Four-way co-discovery (DS-04 merged; R1-19, R2-11).

*(Examiner A)*

### R5-15 — CONFIRMED

> Lines 298–310 contain "**Figure 1. E1 in-distribution validity.**" through "**Figure 6. E6 per-site coverage and answered error.**"

Line numbers exact. My independent scan confirms both limbs — no image markup of any kind in the document, and `Figure N` occurs only inside the Figures section. I also confirm `paper/` contains no image files (TODO.md, draft.md, references.bib, review/). Kept separate from DS-05 because R5-15's line-anchored version and DS-05's search-based version are the same claim from different evidence, and the editor benefits from both being on record; the editor may merge at will.

*(Examiner A)*

### R5-16 — CONFIRMED

> "Both budgets $\alpha \in \{0.05, 0.10\}$ are certified by separate walks and reported as a coverage-versus-$\alpha$ curve." (§3.5)

No coverage-versus-α curve appears in Figures 1–6 or Tables 1–4. Table 4 is the closest artefact — it gives coverage at both α values — but as a function of *site count*, and at the headline 208-site scale the α = 0.05 cell is "—", so no curve exists there at all. The second limb is equally clean: §4.2 reports certify rate, coverage 0.9722, hard-violation 0.01, exceedance 0.05 and Table 1, and **never the realized answered-set error** — the quantity the certificate bounds. E6's Table 2 reports answered error, but for a different deployment at a different threshold. Co-discovered by R1-49; question forms R5-56, R1-61.

*(Examiner A)*

### R5-17 — CONFIRMED (one locator corrected)

> "This is a lightweight, machine-verifiable substitute for pre-registration: it removes the degrees of freedom that would otherwise let a tunable pipeline flatter itself." (§3.2; the phrase repeats at §3.10)

The overreach is the verb "**removes**". A self-authored unit test pins values against drift; it carries no timestamp and no third party, so it cannot establish that the values were fixed *before* results were seen — which is the entire function of pre-registration. The hedges "lightweight" and "substitute" are real and the editor should credit them. **Locator correction:** A.3 repeats the *pinning* claim but not the pre-registration phrase, so "repeated at §3.10 and A.3" should read "§3.10". Note the finding makes no claim about the test suite's contents, so criterion 6 does not apply. Co-discovered by R1-23; R4-02/R4-43 reach a far stronger artifact-based version outside R5's access.

*(Examiner A)*

### R5-18 — CONFIRMED (survivor; DS-13 merged)

> "constructively answers a **published** diagnosis of overconfident selective certificates [@zhou2026falsesense]" (§1, contribution 4) · "the constructive counterpart to the **published** warning" (§4.4) · "certified record-level selective-risk rules overrun their budget by 9–30% under grouped deployment [@zhou2026falsesense]" (§2.4)

All three verbatim. The bibliography entry is `@misc{zhou2026falsesense, … eprint = {2606.15153}, archivePrefix = {arXiv}}` with no venue, no journal, no proceedings — so "published" is used twice in the peer-review sense for an unrefereed preprint, in a manuscript that is otherwise scrupulous about tagging what it can and cannot support. The 9–30% figure is stated as established fact and reproduced nowhere. DS-13's contribution — my independent count of **7 of 31** entries as 2025–26 `@misc` preprints — is carried into the merged text. Four-way co-discovery (DS-13 merged; R1-20, R2-23, R4-34).

*(Examiner A)*

### R5-19 — CONFIRMED

> "The equity question here is scoped narrowly to site size — whether small hospitals receive systematically worse selective service than large ones" (§4.7) · "routing the hard ones to a clinician [@chow1970reject; @elyaniv2010selective]" (§1) · "chosen so that the answer/abstain decision is intrinsically interpretable" (§3.8)

Verified absent from all 31 entries: Jones et al. (ICLR 2021), Gibbs/Cherian/Candès, Barber et al. (2023), Madras (2018), Mozannar (2020), Rudin (2019). The Jones limb is the sharpest: §4.7 runs an equity analysis of selective service, and the canonical result that selective classification magnifies group disparities is exactly the adverse prior art. §4.7's scoping sentence ("demographic and protected-attribute subgroup analysis is beyond this synthetic harness") scopes out an *experiment*, not a *citation*, so criterion 5 does not bite. Kept separate from DS-14 — disjoint work lists, both needed.

*(Examiner A)*

### R5-23 — CONFIRMED

> Abstract: "a hard-violation rate of 0.01 under a 0.05 budget" · §1: "stays at or below a budget $\alpha$" · §3.6: "The two confidence budgets combine as $\delta_{\text{conf}} + \delta_{\text{bet}} = \delta$"

I enumerated all 14 occurrences of "budget". It denotes α at §1, §2.2 ("risk budget"), §3.2/A.3 ("budget ladder"), §4.4, §4.5 ("the stricter budget", "answered-set budget"), §2.4/§4 ("their budget"); and δ at the Abstract, §1 ¶5, §1 contribution 2, §3.5 ("betting budget"), §3.6. The collision is worst inside the **abstract itself**, where "under a 0.05 budget" means δ = 0.05 and, two sentences later, "the stricter $\alpha=0.05$ budget" means α = 0.05. Same numeral, same word, two parameters, one paragraph.

*(Examiner A)*

### R5-24 — CONFIRMED (survivor; DS-24 merged)

> "$\lambda_t = \min\!\left(\sqrt{\frac{2\ln(1/\delta)}{\hat{\sigma}^2_{t-1}\, n}},\; \frac{0.9}{1-\alpha}\right)$, with a variance floor of $10^{-8}$ and the running mean and variance $(\hat{\mu}, \hat{\sigma}^2)$ initialized at $(0.5, 0.25)$" (§3.4)

`n` is used before it is introduced — its only gloss arrives two paragraphs later ("At $n$ clusters no test can certify…") — and it collides with `n_c` (§3.3), `n_cal` (§3.5) and `n_answered` (Table 3). `\hat{\mu}` is initialized and then appears in no displayed formula in the paper. R1-24 adds two further gaps (the variance estimator is undefined; the display uses δ without saying whether the BBSE mode substitutes δ_bet) that the editor should fold in. Question forms: R1-60.

*(Examiner A)*

### R5-26 — CONFIRMED (small; mitigation noted)

> "The cap acts on influence only: it scales each site's whole signed contribution and never censors the error itself, so a site that answers many cases badly still enters at full adverse weight." (§3.3) against "$g_c = \min(n_c, M)$ with $M = 100$"

Recomputed: at the generator's clipped-lognormal maximum of 5,000 records, $g_c/n_c = 100/5000 = $ **1/50**. "Full adverse weight" is literally false for a defined symbol — `weight` is $g_c$, defined four lines earlier, and it is capped. The intended meaning ("full adverse **error**") is recoverable from the same sentence's first clause, which is why this is small; but a terminological collision on a defined symbol inside the estimand's own definition is worth a one-word fix.

*(Examiner A)*

### R5-27 — CONFIRMED (survivor; DS-17 merged. Severity split noted.)

> §3.3: "is provably anti-conservative: a construction with 17.5% true risk certifies at $\alpha = 5\%$ under naive truncation (Appendix A.3; retained as a regression test)" · A.3: "is pinned by a dedicated regression test, in which a construction with 17.5% true risk certifies at $\alpha = 5\%$ under truncation but is correctly refused under the influence-weighting scheme"

I followed the pointer. §3.3 says "provably" and forwards to A.3; A.3 restates the same headline number and forwards to a test. No site configuration, no error rates, no argument appears anywhere. Note that Appendix A is titled "Deferred **proofs**" while A.3 is "Software and reproducibility details" — the construction is not in a proof section at all. The word "provably" is doing work no displayed argument supports. **Severity split for the editor:** DS rated this major, R5 minor; I keep R5-27's sharper two-quote anchor but flag that DS's severity is the better call, since the construction is the sole justification for the influence-weighting estimand. Co-discovered by R1-33.

*(Examiner A)*

### R5-28 — CONFIRMED

> "It is propagated to $[\rho_{\text{lo}}, \rho_{\text{hi}}]$ by *corner-interval coverage*: the clipped $\rho(c_0, c_1, \pi_s)$ is coordinate-wise monotone in each of the three box parameters" (A.2)

I searched every use of "clip" in the manuscript: §4.1 ("clipped lognormal", the generator's size clipping) and §6.1 ("practical clip caps", "the clip cap divides the certification margin", covariate-shift weight clipping). Neither defines a clipping of ρ. The operation is load-bearing — it is what presumably keeps ρ finite at box corners where the BBSE inversion leaves (0,1) — and it appears exactly once, undefined, inside the soundness argument. Interlocks directly with R5-29; question form at R5-61.

*(Examiner A)*

### R5-29 — CONFIRMED

> "(iii) $q$ outside the box's $[c_{0,\text{lo}}, c_{1,\text{hi}}]$ range, meaning the implied prevalence leaves $(0,1)$ and BBSE is misspecified." (§3.6)

Technically correct. The inversion gives $\pi_t = (q - c_0)/(c_1 - c_0)$, so $\pi_t \in (0,1)$ requires $q$ strictly between $c_0$ and $c_1$ **at the corner being evaluated**. Testing $q$ against the *widest* interval $[c_{0,\text{lo}}, c_{1,\text{hi}}]$ admits configurations where, at e.g. the corner $(c_0 = c_{0,\text{hi}},\, c_1 = c_{1,\text{lo}})$, the implied prevalence is negative. So the stated justification is a necessary condition presented as sufficient. The undefined clipping of R5-28 is probably what actually handles this — which is exactly why R5-28 must be answered before this one can be closed.

*(Examiner A)*

### R5-30 — CONFIRMED (strong)

> "*Missingness is handled without a positivity diagnostic.* Missing values pass through the frozen encoder's imputation-and-indicator scheme; we do not add a dedicated positivity (overlap) diagnostic" (§6.1)

I searched the whole manuscript for `encoder`, `imput*`, `indicator` and `missing`: **one match, line 242 only** — this sentence. No encoder appears in §3 Methods, none in §4.1's model description ("The risk head is an L2-regularized logistic regression ($C = 1.0$) fit on $S_{\text{train}}$"), and §3.2's inventory of fitted objects is "the head, the walk order, the confusion-matrix statistics". The generator produces complete features, so there is nothing for such a scheme to act on. A Limitations section that concedes a limitation of a component the paper never describes is a disclosure defect in the section the paper most relies on for credibility. Independently confirmed against the artifact by R4-03.

*(Examiner A)*

### R5-31 — CONFIRMED

> "at practical clip caps, the effective-sample-size loss structurally prevents certification below roughly 400 clusters — the clip cap divides the certification margin under the information floor — outside the operating range this cohort supports" (§6.1)

A specific quantitative frontier claim ("roughly 400 clusters") with no derivation, no clip-cap value, and no experiment — offered as the *reason* a third assumption mode is excluded. Criterion 5 does not kill this: the finding does not demand the covariate-shift mode, it attacks the unsupported claim used to justify excluding it. The claim is also striking against E4, which required a full 200-draw sweep to locate the α = 0.05 frontier at 400 for the modes that *are* shipped.

*(Examiner A)*

### R5-32 — CONFIRMED (survivor; DS-39 merged)

> "A stronger black-box head can be substituted at a visible cost in coverage" (§3.8) · "the gate would then price its selective quality visibly, as a change in certified coverage" (§5.3)

The direction is backwards: a *stronger* head ranks better, so at fixed α more cases clear the bar and coverage should rise. §5.3's neutral "a change in certified coverage" is the correct statement, and the two sentences describe the same substitution. The second limb is verified too — no experiment anywhere swaps the head, so both sentences are untested. Note R3-11 adds the limb neither DS-39 nor R5-32 raises: the substitution also destroys the exact-attribution property that contribution 3 rests on, and §5.3 is silent on that cost.

*(Examiner A)*

### R5-33 — CONFIRMED

> §1: "Three questions in reliable machine learning have mature but separate answers." · §2: "CertGate draws on four literatures that each solve part of the problem and stop one axis short." · §6: "CertGate occupies the intersection of three separately developed lines"

Verified, and the identity of the dropped literature is verified too: §2's four are 2.1 certified selective prediction, 2.2 conformal/cluster exchangeability, 2.3 label shift, 2.4 multi-site clinical validation **and explainable abstention**. §1's three and §6's three are both the first three. So explainable abstention — the collection's central emphasis and the paper's third contribution and half its title — is the literature the manuscript drops from both of its own framings. Corroborates DS-09 and DS-58 structurally rather than rhetorically. Co-discovered by R1-39.

*(Examiner A)*

### R5-36 — CONFIRMED (one limb needs an external check)

> §4.2: "non-zero — consistent with a tight rather than a vacuous certificate [@geifman2017selective]" · §6: "certified selective risk [@chow1970reject; @geifman2017selective]"

The Chow limb is settled **from the manuscript alone**: §2.1 states "The reject option dates to Chow [@chow1970reject]; El-Yaniv and Wiener … formalized the risk–coverage tradeoff, and Geifman and El-Yaniv … turned it into a finite-sample selective-risk certificate." So the paper's own related-work section attributes the certificate to Geifman and *not* to Chow, and §6 then groups both under "certified selective risk". Internal inconsistency, confirmed.
**Residual check on the Geifman limb:** read Geifman & El-Yaniv (2017) and confirm it contains no criterion for reading a non-zero empirical violation rate as evidence of tightness. If it does, that half narrows; the Chow half stands regardless. Co-discovered by R2-37, R1-46.

*(Examiner A)*

### R5-37 — CONFIRMED

> §2.4 closing sentence: "The same certificate shape appears in power-grid contingency screening [@thermal2026audit], so it is not specific to medicine." against §2's stated plan: "We take them in turn, closing each with the nearest work and the gap between what it guarantees and what CertGate does."

Verified: §2.4's gap statement ("CertGate's difference is exact attributions on a certified gate") comes *before* the power-grid sentence, so the section closes on a generality claim rather than on a nearest-work-and-gap statement, breaking the structure §2 announces. The citation is used nowhere else in the paper. And the sentence actively undercuts the manuscript's own venue positioning — see DS-22, DS-58. Co-discovered by R1-47.

*(Examiner A)*

### R5-39 — CONFIRMED (one clause corrected)

> §4.1: "The cohort follows the specification frozen in `data.py`" and "Every experiment runs in mode FULL under protocol seed 20260721" · §4.4: "(`tilt_pushes_risk_above_alpha` true)" and "reason `e3-control-not-poisonous`" · A.3: "The test suite is 69/69 green."

All four verbatim. **Correction:** the clause "specifies its generator … rather than in the paper itself" is not right for the generator — §4.1 *does* give the full specification in the paper (clipped lognormal, log-mean 6.0, log-sigma 1.1, [20, 5000], d = 8, sep = 2.2, prevalence 0.095, $u_c \sim \mathcal{N}(0, 0.5^2)$). The defect is the *attribution* phrasing ("frozen in `data.py`", which makes the code sound authoritative over the paper), plus the two code identifiers in §4.4, the undefined "mode FULL", and the bare test count. Forward with that narrowing. Co-discovered by DS-26, DS-28, R1-35, R2-42.

*(Examiner A)*

### R5-40 — CONFIRMED

> "All data used in this study are synthetic and generated deterministically by the included code, publicly available at [CODE REPOSITORY URL — to be added]." (§ Data availability)

Verified against the reproducibility claims it must support: §3.10 "Every result regenerates deterministically from the released code"; A.3 "Every result regenerates from the released code under a pinned environment (`requirements.txt`)" and "The full grid runs from a single command". Every one of them terminates at an absent URL. Not a criterion-4 placeholder — the exempt class is identity fields. Five-way co-discovery (DS-07, DS-27, R1-36, R2-40, R4-17).

*(Examiner A)*

### R5-41 — CONFIRMED

> §4.6: "This case study uses a deployment with threshold $\tau^* = 0.55$" · §4.7: "E6 uses a separate deployment (threshold $\tau^* = 0.77$; 40 target sites)" · §4.2 reports coverage 0.9722 with no threshold

Verified: no τ* value appears in §4.2, §4.3, §4.4 or §4.5, so the operating point behind every headline number in the paper is unreported; and neither §4.6 nor §4.7 states that its threshold was certified, under which mode, or at which α. Since §3.5's whole apparatus exists to *select* a threshold, never reporting what it selected removes the reader's only handle on the coverage numbers. Question form at R5-59; co-discovered by R1-32, R2-33; DS-46 covers the separate defect that 0.55 is the grid minimum.

*(Examiner A)*

### R5-42 — CONFIRMED (minor; mitigation noted)

> Table 3: "| Predicted-class | 0.0393 | 917 / 23,325 | estimated |" and "| BBSE-implied true-class | 0.0591 | 1,378.9 expected ($\hat{\rho} = 0.830$) | estimated, label-shift assumption |"

Verified, and all three fractions recompute exactly (917/23,325 = 0.0393; 1,378.9/23,325 = 0.0591; 1,470/23,325 = 0.0630). A column headed "Count" holding two exact integers and one non-integer expected value carrying an embedded parameter estimate is a presentation defect — and in a clinical framing, 1,378.9 patients reads oddly. The Tag column does distinguish the three ("estimated", "estimated, label-shift assumption", "diagnostic, harness only"), which the editor should credit as partial mitigation. Co-discovered by R2-43.

*(Examiner A)*

### R5-43 — CONFIRMED

> §3.9: "stratified by answered-set size bins $\{<30,\ 30\text{–}100,\ 100\text{–}300,\ >300\}$" versus Table 1: "[0, 30) / [30, 100) / [100, 300) / [300, $\infty$)"

Verified. "$>300$" excludes 300 while "[300, ∞)" includes it, and "30–100" is ambiguous at both endpoints. Since the bins are the stratification for the paper's diagnostic exceedance number, and Table 2 uses the same half-open convention as Table 1, §3.9 is the one place out of step. Independently confirmed against the code by R4-23.

*(Examiner A)*

### R5-44 — CONFIRMED (survivor; DS-44 merged; mitigation noted)

> Title: "CertGate: finite-sample certified selective prediction for multi-site **clinical risk models**, with label-shift robustness and explainable abstention" · Abstract: "On a 208-site **synthetic** cohort"

Both verified. The abstract does disclose, 190 words in; the title does not, and the title is what gets indexed, cited and read alone. The authors' available defence is that "for multi-site clinical risk models" names the *intended application domain* rather than claiming clinical evaluation — the editor should weigh that, and it is why I keep this at title-accuracy rather than misrepresentation. R5-44's pairing of title against the abstract's own disclosure is what makes it actionable; DS-44 states the same without the mitigation. Co-discovered by R1-45 (which attacks "finite-sample" instead — see R5-03).

*(Examiner A)*

### R5-45 — CONFIRMED (one quote must be struck)

> Abstract: "a confidence guarantee written at the record level is silently overconfident once deployment spans institutions" · §1 ¶3: "A certificate that treats records as exchangeable overruns its stated confidence once deployment is grouped by site"

Both verified as unconditional, and both depend on positive within-site correlation — at zero intraclass correlation, grouping is harmless and a record-level certificate is fine. The paper never states that dependence, and its own motivating figure is a *range* (9–30%, §2.4), which is itself evidence the failure is conditional.
**Quote the editor must strike:** the finding's third instance, §1 ¶1 "that promise is **often** false, in a way the deployed system cannot see," is explicitly hedged by "often" and does not belong in an unhedged-generalization finding. Forward two, not three.

*(Examiner A)*

### R5-46 — CONFIRMED

> §4.2: "Across every size bin the observed exceedance sits far below the reference" · Table 1: "| [0, 30) | 2 | 0.0000 | 0.4063 |"

Verified. "Across every size bin" is asserted over a set that includes a bin holding two pools with a realized rate of 0/2 — an observation that cannot distinguish 0.00 from 0.41 at any useful confidence. Sits directly on top of R5-07 (the n = 200 premise is false for exactly these bins) and DS-30 (no intervals on any bin). The three together make Table 1 the most fixable cluster in the Results: add per-bin denominators, intervals, and drop "every".

*(Examiner A)*

### R5-47 — CONFIRMED

> §4.1: "the class signal lives on a single normalized direction supported on the first four coordinates" · §4.6: "The global standardized importances recover the generator: features 0–3 dominate at 1.157, 1.161, 1.178, and 1.155"

Verified: §4.1 states which coordinates carry signal but never states that the direction loads them **equally**, so near-equal recovered coefficients cannot be checked against anything. What §4.1 does support is the weaker reading "0–3 informative, 4–7 noise" — which is recovery of the support, not of the generator. This matters beyond notation: if the true loading is equal, then features 0–3 are interchangeable by construction and there is no mechanism for feature 0 to be "the dominant abstention driver" (§4.6, DS-11) — which is precisely R3-42's suspicion that the E5 result is n = 2 noise.

*(Examiner A)*

### R5-48 — CONFIRMED

> §3.7 clause (3): "It bounds the answered-set error parameter, not any single batch's realized error *count*, which exceeds $\alpha$ at binomial-dispersion rates even under a valid certificate." · §3.9: "at the boundary the exceedance rate approaches 50% as batches grow"

Sharp and verified. Clause (3) drops "at the boundary" and states as unconditional what §3.9 states conditionally — and the paper's own E1 refutes the unconditional version: the realized exceedance is 0.05 overall and 0.0000/0.1111/0.0189/0.0551 by bin, against binomial-dispersion references of 0.4063–0.4915. §4.2 says so itself ("answered pools are not sitting at the α boundary but well inside it"). Since clause (3) is one of five clauses the paper says "survive into the deployed guarantee text" (§3.7), the overstatement is shipped to deployers. Same root confusion as R5-05.

*(Examiner A)*

### R5-49 — CONFIRMED

> §1 ¶5: "the label-shift mode never certifies *and* violates (the joint event is 0 of 200 draws), declining instead" · §4.3: "conditioning on the 9 draws that did certify"

Verified. "Declining instead" presents declining as the sole alternative to certify-and-violate, when 9 of 200 draws certified safely. The abstract states it correctly ("declining in 95.5% instead"), which shows the authors have the accurate phrasing available. Minor, and the fix is one word ("declining otherwise" → "declining in 95.5% and certifying safely in the rest").

*(Examiner A)*

### R5-50 — CONFIRMED

> §1 contribution 2: "turning a $48.5\%$-violation baseline into a gate that certifies or declines rather than issuing a certificate it cannot support (E2)" · §4.3: "decline rate 0.955"

Verified. "Certifies or declines" is literally true and conveys a balanced disjunction where the realized split is 4.5% / 95.5%. In a contributions list — the passage most likely to be quoted — the omission materially changes what the reader believes the mode does. Co-discovered by R2-02, R1-67, DS-57.

*(Examiner A)*

### R5-52 — CONFIRMED (copyedit; no rendering is wrong)

> §3.1: "resting on roughly eighty site-level observations" · §3.5: "about 83 calibration clusters" · §5.2: "roughly 80 of them at the 208-site scale"

Recomputed: 0.40 × 208 = **83.2**, so all three renderings are *correct*; there are two values (≈80 and 83) and three spellings for one quantity, including "eighty" and "80" in the same document. That makes this a house-style consistency point rather than an error, and the editor should present it as such. Co-discovered by R2-35.

*(Examiner A)*

### R5-53 — CONFIRMED (question stands)

> "Yu and Liu [@yu2026joint] are closest: the same certificate shape — a selected-risk bound with an acceptance floor and a decline option — but over i.i.d. records" (§2.1)

Verified, and the dependency is real: contribution 1's novelty is "the site, not the record, as the unit of independence," so the entire delta against the closest prior work is the clause "but over i.i.d. records". The bibliography entry is `@misc … eprint = {2606.08517}` with no venue. Asking for direct quotation of that work's assumptions is proportionate. Cross-noted with DS-59 (the office-side spot-check) and R5-18.

*(Examiner A)*

### R5-55 — CONFIRMED (question stands)

> A.1(iii): "under $H_0$, $\mathbb{E}[\,1 + \lambda_t(\alpha - Z_t) \mid \mathcal{F}_{t-1}\,] \le 1$, so $K_t$ is a nonnegative supermartingale" · §6.1: "Sites sharing the collection window may be correlated through common temporal shocks"

The remedy question for R5-02, and unanswered anywhere: no sampling assumption on the calibration sites is stated in §3.1, §3.3, §3.4, §4.1 or A.1. The second half (quantify level inflation under the dependence §6.1 concedes) is the harder ask and may reasonably become a stated assumption plus a sensitivity note rather than a derivation. Co-discovered by R1-55.

*(Examiner A)*

### R5-56 — CONFIRMED (question stands)

> §4.2: "The hard-violation rate is 0.01 (2 of 200; exact 95% CI $[0.001, 0.036]$), at or below $\delta = 0.05$ and non-zero — consistent with a tight rather than a vacuous certificate" · §3.4: "an *information floor* $\ln(1/\delta)(1-\alpha)/n$"

Verified: the tightness argument rests entirely on the violation count being non-zero, i.e. on 2 draws. Neither the realized answered-set error distribution nor the achieved certification margin against the information floor is reported anywhere for E1 — and R5-16 shows E1 never reports the answered-set error at all. The comparison the question asks for is the one that would actually evidence tightness, and the paper already computes both quantities.

*(Examiner A)*

### R5-57 — CONFIRMED (question stands)

> "with mean coverage 0.9304 at 150, 0.9715 at the realistic 208-site scale, 0.9601 at 300, and 0.9621 at 400" (§4.5)

The remedy question for DS-31. Note the paper is already alert to run-to-run variation — §4.5 explains the 0.9715-vs-0.9722 difference by independent seeding — so it has the vocabulary to answer this in one sentence with a Monte-Carlo standard error at R = 200. Co-discovered by R2-59.

*(Examiner A)*

### R5-58 — CONFIRMED (survivor; DS-51 merged)

> §3.7 clause (1): "It is scoped per target site." · Table 2: "| [100, 300) | 15 | 0.8966 | 0.0406 |"

The right pairing: the guarantee is stated per site, and the only per-site evidence in the paper is three bin means over 40 sites with no dispersion, no maximum, and no count of sites exceeding α. That is exactly the evidence a bound on a cross-site mean cannot supply (R5-01). R5-58 asks for E1 and E6; DS-51 asked for E6 only, so the broader version survives with DS-51's specific ask ("how many exceed α") carried into it. Co-discovered by R2-61.

*(Examiner A)*

### R5-59 — CONFIRMED (question stands)

> §3.5: "The operating threshold is chosen from a grid of 23 values evenly spaced in $[0.55, 0.99]$" · §4.6: "threshold $\tau^* = 0.55$" · §4.7: "threshold $\tau^* = 0.77$"

Question form of R5-41, verified: no certified threshold is reported for E1–E4, and the two case studies use unexplained and different operating points, one of which is the grid minimum (DS-46). Co-discovered by R2-55, R1-59.

*(Examiner A)*

### R5-60 — CONFIRMED (question stands)

> "For a linear model these attributions are exact Shapley values, with no approximation or sampling [@lundberg2017shap]" (§3.8)

Remedy question for R5-12, unanswered anywhere: the manuscript names neither value function. The reconciliation half is the substantive one — under the conditional/observational value function, correlation among features 0–3 breaks the linear identity; under the interventional one it holds but the attributions answer a different question. Co-discovered by R3-37.

*(Examiner A)*

### R5-61 — CONFIRMED (question stands)

> "the clipped $\rho(c_0, c_1, \pi_s)$ is coordinate-wise monotone in each of the three box parameters, so the minimum and maximum of $\rho$ over the eight box corners bound every interior parameter combination" (A.2)

Remedy question for R5-28 and R5-29 together. It is the right question because monotonicity of the *clipped* function is what makes the corner argument work, and a clip that saturates can be monotone while destroying the interior bound's usefulness — so the answer determines whether A.2's soundness argument holds. Co-discovered by R1-64 (on the adjacent bootstrap-validity question).

*(Examiner A)*

### R5-62 — CONFIRMED (question stands)

> §3.9: "the calibration draw, not the target site, is the unit of replication" · Table 1 pool counts 2 + 18 + 53 + 127

Recomputed: **2 + 18 + 53 + 127 = 200**, exactly R — one target pool per calibration draw. And I verified that "target pool" occurs **exactly once** in the entire manuscript (§3.9, line 138) and is never defined, even though it is the object the hard-violation criterion is evaluated on. So the reader can infer one pool per draw from Table 1's arithmetic but cannot learn what a pool contains. Co-discovered by R2-34; blocks DS-52.

*(Examiner A)*

### R5-63 — CONFIRMED (confidential; one characterization corrected)

> "the influence-weighted answered-set risk — the parameter $R_M$ defined in Section 3.3 — at a new target site is at most $\alpha$" (§3.1) against §3.3's cross-site definition

The right central doubt, and the strongest one in my set: it is co-discovered independently by R1 (R1-01, R1-54, R1-65) and it goes to the paper's headline claim rather than its presentation. **One characterization to correct:** "the homogeneous in-distribution experiment" understates the generator, which does carry site heterogeneity in prevalence ($u_c \sim \mathcal{N}(0, 0.5^2)$, §4.1). The accurate statement is that E1's targets are drawn *exchangeably* with calibration, so no adversarial per-site case is ever tested — which is the same point, correctly stated.

*(Examiner A)*

### R5-64 — CONFIRMED (confidential)

> §4: "No real cohort can supply that ground truth, and a certificate only ever checked against the same unlabeled deployment data it was built on cannot be falsified." · §5.5: "Real data cannot supply that ground truth, which is what makes it unable to validate a validity claim."

Both verbatim, and the four legs of the synthesis are each independently confirmed in my prosecution: the synthetic-only argument overreaches (R5-10); the only comparator is CertGate's own exchangeable mode (R5-11, DS-01); generator realism rests on a reporting checklist (R5-13); and the argument as written would excuse the work from external validation in principle. The referee's framing — that these compose into a rationale for never testing on real data — is fair and is the correct thing to put in front of the editor, because each leg alone reads as a minor fix and the composition does not. Co-discovered by R2-26, R1-16.

*(Examiner A)*

### R5-67 — CONFIRMED (confidential)

> §1 contribution 3: "This supports the certificate above rather than standing as an independent method (E5)." · §4.6: "answering 200 cases and declining 2" · §4.7: "demographic and protected-attribute subgroup analysis is beyond this synthetic harness"

Every limb verified, including the two I checked independently: explainable abstention is dropped from both three-literature framings (R5-33), and the fairness-under-abstention limb is real — `ifac2025abstainexplain` is Lenders et al., "**Interpretable and Fair** Mechanisms for Abstaining Classifiers," cited four times in the manuscript and every time only for reject-option explanation, never for its fairness content. Against a collection whose central emphasis is explainability, this is the fit finding the editor most needs. Co-discovered by R3-41/R3-45, R2-68, DS-09, DS-58.

*(Examiner A)*

### R5-68 — CONFIRMED (confidential; **favourable — must be forwarded**)

> §4.5: "(The 208-site sweep point is a separate run from E1, with independently derived seeds — hence 0.9715 here against E1's 0.9722.)" · Table 1 bin exceedances (0/2, 2/18, 1/53, 7/127)

I independently reproduced this referee's reconciliation and it holds. Table 1's bins recover exactly 10 exceedances over 200 pools = **0.0500**, matching §4.2's stated overall rate to the digit; all four Clopper–Pearson intervals recompute correctly; all three Table 3 fractions recompute from their counts; Table 2's site counts sum to 40; Table 4 matches §4.5 value for value; every abstract number matches the body; every figure caption matches the body. I additionally confirmed the bibliography has **zero dangling citekeys and zero orphaned entries** (96 citation instances, 31 distinct keys, 31 entries). Two soft spots only: the "300+" phrasing (R5-22) and "near-tripling" (DS-29). **The editor should carry this forward explicitly.** Against a report set this critical, a clean arithmetic audit and a voluntarily disclosed cross-run difference are material to the decision, and they corroborate DS-60.

---

*(Examiner A)*

---

## Verified findings — PLAUSIBLE (one stated check settles each)

### DS-34 — PLAUSIBLE

> `note = {arXiv:2606.20115; submitted to DeCaF Workshop, MICCAI 2026}` (fedcrc2026) · `note = {arXiv:2607.13221; submitted to IEEE Transactions on Power Systems}` (thermal2026audit)

Both note fields verified verbatim. Recording another author's *unpublished submission status* is a real etiquette point, but the finding's stated harm is that it "will render in the printed reference list," which is style-dependent.
**Single check that settles it:** render `references.bib` through the Springer Nature CSL style the journal uses and see whether `note` is emitted. If it is dropped, the finding reduces to a package-hygiene note; if it is emitted, it is a substantive correction.

*(Examiner A)*

### DS-35 — PLAUSIBLE

> `@inproceedings{podkopaev2021labelshift, …}` (lines 113–121, no DOI, no eprint) · `@article{elyaniv2010selective, …}` (lines 61–69, no DOI, no eprint) · `@article{lee2025hierarchical, … doi = {10.1145/3786352}` (lines 208–217, no volume, no pages)

Every factual claim in the anchor verified. But the inference that this is *sloppiness* rather than *source reality* is unestablished: JMLR vol. 11 (2010) and PMLR/UAI vol. 161 (2021) historically do not mint DOIs, and an ACM article with a DOI but no volume/pages is the normal state of a just-accepted online-first paper. Note also `geifman2017selective` appears in the finding's location field but does carry an eprint, so it does not belong there.
**Single check that settles it:** look up DOI registration for JMLR 11(53) and PMLR 161, and the current ACM J. Data Science record for 10.1145/3786352. If no DOI exists and no volume has been assigned, the finding dies; if they exist, it stands.

*(Examiner A)*

### DS-43 — PLAUSIBLE

> Document order verified: "# Competing interests" (line 294) → "# Figures" (line 298) → "# Tables" (line 312) → "# References" (line 351)

The order is exactly as the finding states. Whether it is *non-standard for Springer* is a house-style question I cannot settle from the manuscript, and Springer Nature's own templates vary on whether figure legends and tables precede or follow the reference list.
**Single check that settles it:** open Discover Computing's "Submission guidelines → Manuscript structure" and read the required back-matter order. If the journal places tables and figure legends after the references, the finding stands; if before, or if unspecified, it dies.

*(Examiner A)*

### DS-45 — PLAUSIBLE

> "Sites with no answered-eligible records enter as *neutral* atoms $Z_c = \alpha$ rather than being dropped; dropping them would redefine the site population post hoc and quietly change the estimand." (§3.3)

The finding's arithmetic is right: with $a_c = 0$ the site's numerator term $g_c a_c e_c$ and denominator term $g_c a_c$ are both zero, so $R_M$'s **value** is invariant to dropping such sites. But the manuscript's own clause "redefine the site population" concedes and partly answers exactly that — an estimand is a parameter *relative to a population*, and the population does change. Note the operative reason is a third one the manuscript never gives: a neutral atom contributes a wealth factor of exactly $1 + \lambda(\alpha-\alpha) = 1$, so it cannot help certification, but it does inflate $n$ and deflate $\hat\sigma^2$ in $\lambda_t$, making the test strictly more conservative.
**Single check that settles it:** ask the authors whether "change the estimand" means $R_M$'s numeric value (in which case the sentence is wrong and must be replaced) or its reference population (in which case it should say so, and should give the $\lambda_t$ reason instead).

*(Examiner A)*

### DS-50 — PLAUSIBLE (narrowed)

> "the largest answered-to-declined gap of any feature (gap $-0.854$; gap ranking $[0, 3, 2, 1, \dots]$; top gap feature 0). Declines are systematically the cases where feature 0's pull leaves the decision contested" (§4.6)

The question's first limb is partly answered by the manuscript: §4.6 does state the count — "answering 200 cases and declining **2**" — three paragraphs earlier in the same subsection. What survives is (a) justifying "systematically" and "at the cohort level" against n = 2, and (b) the Figure 5 caption, which reports "−0.854; 0.868 answered vs 1.722 declined" and "the dominant systematic abstention driver" with **no** denominator, so a reader seeing only the figure takes it for a cohort statistic.
**Single check that settles it:** decide whether §4.6 ¶1's "declining 2" satisfies the disclosure. If yes, forward only limbs (a) and (b); the count question dies under criterion 2.

*(Examiner A)*

### R1-13 — **PLAUSIBLE**

> §3.3: "Sites with no answered-eligible records enter as *neutral* atoms $Z_c = \alpha$" · §2.1: "Yu and Liu [@yu2026joint] are closest: the same certificate shape — a selected-risk bound with an acceptance floor and a decline option"

The second half is confirmed outright: no coverage floor exists anywhere in the certified object, §3.5
maximizes coverage without constraining it, and §2.1 names the acceptance floor as a *similarity* while
listing CertGate's differences elsewhere — the disadvantage is never conceded.

The first half ("trivially satisfiable by abstaining") is contradicted by the manuscript's own algebra.
$Z_c - \alpha = g_c a_c(e_c-\alpha)/M$ means the certification margin scales *linearly in coverage*: a
zero-answer site contributes exactly $\alpha$, giving wealth factor 1, so a fully abstaining gate yields
$K_t \equiv 1$ and can never reach $1/\delta$. Abstention shrinks the margin rather than manufacturing it.
**The single check:** ask the authors for the minimum certified coverage across E1's 200 draws. If no
low-coverage certificate exists, drop the "trivially satisfiable" clause and forward only the
no-floor/not-conceded half.

*(Examiner B)*

### R1-44 — **PLAUSIBLE**

> §2.2: "false under multi-site clustering, where records within a hospital are not exchangeable with those from an unseen site"

The sentence is loose but not clearly wrong. Read as a claim about the permutation-invariance of the joint
calibration/test sequence — which is what "exchangeable with" ordinarily means in this literature — it is
correct, and it is then already the joint-law statement the referee asks for. Read as a claim about pairwise
marginal comparability it is wrong, since under a site-random-effect model single records from different
sites are marginally identically distributed. **The single check:** ask the authors which reading they
intend. If the joint-law reading, this reduces to a wording preference and should not be forwarded as an
error.

*(Examiner B)*

### R2-11 — PLAUSIBLE

> "This follows the distributional profile reported across multi-site clinical studies … [@tripodcluster2023; @internalexternal2021]." (§4.1, line 152)

`tripodcluster2023` is titled "…TRIPOD-Cluster Checklist" (BMJ 2023) — a reporting checklist, which cannot supply a lognormal(6.0, 1.1) size distribution, a 0.095 base prevalence, or a 0.5 log-odds site SD. That half is settled. **The single check that would settle the rest:** read Takada et al., *J Clin Epidemiol* 2021;137:83–91, and determine whether it reports cluster-size distributions and between-cluster outcome heterogeneity for its cohorts. If it does even partially, the finding must narrow to the three specific parameters rather than claiming neither source supplies anything.
**Correction:** the finding's location field cites the Abstract for a parallel claim. The abstract makes no realism claim; the parallel *uncited* claim is at §1 line 27 ("whose lognormal sizes, ~9.5% prevalence, and site random effects follow the distributional profile reported for large multi-site clinical cohorts"). DS-04 and R5-13 locate it correctly.

*(Examiner C)*

### R3-16 — PLAUSIBLE

> "Reject-option explanation methods [@artelt2022reject; @ifac2025abstainexplain; @l2lore2025] attach no statistical guarantee to the decision; CertGate's difference is exact attributions on a certified gate." (§2.4, line 54)

**Confirmed half:** §2.4 argues only the guarantee axis and nowhere acknowledges a trade on explanation form or actionability. **The single check that would settle it:** confirm from Artelt, Visser & Hammer, "Model Agnostic Local Explanations of Reject" (ESANN 2022, arXiv:2205.07623) that their reject explanations are contrastive/counterfactual in form. If they are, the finding is confirmed as filed; if they are additive, the "axis where the prior art is ahead" disappears and only a weaker one-sidedness observation remains.

*(Examiner C)*

### R3-27 — PLAUSIBLE

> "Reject-option explanation methods [@artelt2022reject; @ifac2025abstainexplain; @l2lore2025] attach no statistical guarantee to the decision" (§2.4, line 54)

The bibliography entry is verified: Lenders, Pugnana, Pellungrini, Calders, Pedreschi & Giannotti, "Interpretable and **Fair** Mechanisms for Abstaining Classifiers", ECML PKDD 2024, doi 10.1007/978-3-031-70368-3_25. The title supports the inference, and the unengaged-fairness half is confirmed (all five citation sites are for reject-option explanation). **The single check that would settle it:** read the Lenders et al. paper and confirm it attaches formal fairness constraints or guarantees to the reject decision. If it does, "attach no statistical guarantee to the decision" is a mischaracterisation of a cited work and the finding is confirmed as filed.

*(Examiner C)*

### R4-22 — **PLAUSIBLE**

Anchors located and accurate: §4.1 line 156 *"Identical inputs produce byte-identical certificates."* (also §3.10 line 144, §A.3 line 268); `report.py:35-36` docstring *"The timestamp is intentionally the only non-deterministic field, so callers comparing runs for determinism must exclude it"*; `test_pipeline.py:58` `dump = lambda r: json.dumps(r["certified"], sort_keys=True, default=str)`. All three facts hold.

But the finding does not allege the manuscript is false — it asks the authors to "say which", and the manuscript's word is **"certificates"**, which it uses throughout (e.g. §3.7 *"The guarantee the certificate makes…"*) to denote the certified object, i.e. exactly `report["certified"]` — the tier the test compares. Under that reading the sentence is already true. My own re-run confirmed the *released artifacts* are byte-identical (E5/E6 including PNG SHA-256), and nothing in the manuscript claims byte-identity for the full report dict.

**The single check that settles it:** determine whether "certificate" anywhere in the manuscript denotes the full report object including the provenance block. I searched and found no such usage — if the editor concurs, the claim is already correct as written and this reduces to an optional one-clause disambiguation, not a defect.

*(Examiner D)*

### R4-47 — **PLAUSIBLE**

Both anchors verified verbatim: §3.8 line 130 *"what the gate adds is that the same exact attributions accompany a certified decision"*; §1 line 21 *"a certified answered-set risk, computed with the cluster as the unit of independence, and robust to label shift"*. Against the venue card, the work does sit on the collection's encouraged list (uncertainty quantification, calibration, OOD robustness, clinical auditability), and R4 properly scopes the opinion ("for whatever it is worth from a reproducibility referee").

Two things stop me confirming it. First, the same §3.8 sentence R4 quotes ends *"— a supporting capability the linear head makes nearly free"*, and §1 contribution 3 ends *"This supports the certificate above rather than standing as an independent method (E5)"* — both verbatim in the draft (lines 130, 33). Explainability is the collection's **central** emphasis, and the manuscript demotes it in the very passages R4 cites for fit. Second, **five other reports reach the opposite conclusion** (DS-58, R1-69, R2-68, R3-41, R3-45, R5-67). Third, the claim that no reservation "requires new experiments beyond a sensitivity re-run" sits awkwardly against R4's own R4-46(b), which asks for E5 to be re-run at a different operating point.

**The single check that settles it:** the venue-fit question belongs to R3's remit, not a reproducibility referee's — the editor should weigh R4-47 against R3's explainability findings rather than treat it as an independent clearance. R4-47's anchors do not address the demotion passages, so it cannot be read as having rebutted them.

---

*(Examiner D)*

### R5-20 — PLAUSIBLE

> "Dunn, Wasserman and Ramdas [@dunn2023hierarchical] and Lee, Barber and Willett [@lee2025hierarchical] supply the cluster-as-unit machinery CertGate reuses" (§2.2)

The tension is real: CertGate's construction as described is influence-capped site atoms + a WSR betting martingale + a fixed-sequence threshold walk, none of which is a hierarchical-conformal construction. But the manuscript corrects itself twice within two sentences and one section — §2.2's own closing sentence, "CertGate reuses the cluster **unit** to certify an answered-set risk budget," and §3.1, "Cluster-as-unit distribution-free inference has precedent in the conformal literature …; we adopt it as the foundation" — which is close to a criterion-2 answer.
**Single check that settles it:** ask the authors whether "machinery" in §2.2 names a construction actually imported from either paper. If yes, they must name it; if no, the fix is the single word "machinery" → "unit", and the finding is a copyedit rather than a misattribution.

*(Examiner A)*

### R5-22 — PLAUSIBLE

> Abstract: "a site-count frontier shows the stricter $\alpha=0.05$ budget needs roughly 300+ sites" · §4.5: "first appears at 300 (certify rate 0.3, coverage 0.7376), and becomes reliable only at 400"

Both quotes verified, and Table 4 confirms certify rate 0.3 at 300 and 1.0 at 400. But "roughly 300**+**" is a lower-bound hedge that is literally satisfied by "reliable only at 400," so this may be imprecision rather than discrepancy. What tips it toward a real finding is that §1 states the same result precisely — "first appears near 300 and stabilizes only at 400" — so the abstract is less accurate than the paper's own introduction.
**Single check that settles it:** decide whether the abstract is held to §1's precision. If yes, the fix is "roughly 300–400 sites, reliably at 400" and the finding stands; if "300+" is accepted as a lower bound, it dies. Co-discovered by R1-34.

*(Examiner A)*

### R5-38 — PLAUSIBLE

> "so no $\delta$-splitting across the grid is needed [@westfall2001fixedsequence; @angelopoulos2021ltt; @bates2021rcps]" (§3.5)

Westfall & Krishen (fixed-sequence multiple testing) and Learn-then-Test are both squarely on point for the claim; RCPS is the loose one, since it controls risk over a nested family by a UCB rather than by a fixed-sequence argument. But an RCPS-style nested-family/UCB construction *does* deliver control over a family without splitting, so the citation is arguably apt in spirit even if the mechanism differs.
**Single check that settles it:** read Bates et al. 2021 (JACM 68(6):43) and determine whether it contains any multiplicity-control argument that bears on selecting one threshold from an ordered grid. If it is purely UCB-over-nested-sets, the citation is misapplied and the finding stands; if it addresses family-wise selection, the finding dies.

*(Examiner A)*

---

## Merged / co-discovered

### Examiner A — desk-screen (DS) and Referee 5 (R5)

Twenty-three findings folded. Every one is genuine co-discovery by two independent referees against the same passage, which is evidence the underlying defect is real — I say so in each case below.

| Merged | Into | Basis |
|---|---|---|
| DS-02 | **R5-01** | R_M cross-site vs per-site. R5-01's anchor carries the $R_M$ formula itself, which is what makes the contradiction visible; DS-02 anchors only the two prose claims. Further co-discovery: R1-01, R1-54, R1-65. |
| DS-03 | **R5-06** | 0/9 without interval. R5-06 gives the exact bound (0.336, which I recomputed as 0.3363) where DS-03 gives "roughly 0.34". Both carry the same false "only rate" clause; see the strike note under R5-06. |
| DS-04 | **R5-13** | Generator realism. R5-13 quotes the uncited §1 sentence verbatim as well as the §4.1 citation, so it evidences both limbs. Further co-discovery: R1-19, R2-11. |
| DS-10 | **R5-10** | Real-data justification. R5-10 pairs §5.5 against **§3.9's Wilson criterion** — the exact mechanism that refutes it. DS-10 pairs it against §3.7, which actually supports the authors. Sharper anchor decides. |
| DS-12 | **R5-09** | Model-agnostic vs confusion gap. Equal facts, tighter anchor. DS-12's extra limb (no alternative head tested) is verified and carried by R5-32. |
| DS-13 | **R5-18** | Preprint reliance. R5-18 covers everything DS-13 does and adds a distinct verifiable error — "published" used twice for an arXiv `@misc`. DS-13's 7-of-31 count is carried into the merged text. Further: R1-20, R2-23, R4-34. |
| DS-15 | **R5-11** | No comparator. R5-11 covers both the §6 "only in combination" claim and §5.2's "not of the method". DS-15's named comparator list (hierarchical conformal, RCPS/LTT, BBSE without the box) is carried in. |
| DS-16 | **R5-12** | Exact-Shapley. R5-12 quotes §3.8 *and* §4.1, evidencing both the missing condition and the generator that violates it. Six-way co-discovery — the most widely independently found defect in the pool. |
| DS-17 | **R5-27** | Counterexample never presented. R5-27 quotes both §3.3 and A.3, showing the pointer's destination is empty; DS-17 quotes only the source. **Severity split flagged:** DS rated major, R5 minor; DS's severity is the better call. |
| DS-24 | **R5-24** | Undefined `n` in the bet. R5-24 names the overloading against `n_c`/`n_cal`, which is what makes it a defect rather than an omission. R1-24 adds two further gaps. |
| DS-39 | **R5-32** | Black-box head backwards. R5-32 adds the verified "untested" limb. R3-11 adds a third limb (the swap also destroys the attribution layer) that neither carries. |
| DS-44 | **R5-44** | Title vs synthetic evidence. R5-44 pairs the title against the abstract's own disclosure, which both sharpens the anchor and supplies the mitigation the editor needs. |
| DS-51 | **R5-58** | Per-site distribution. R5-58 is broader (E1 and E6) and ties the request to §3.7 clause (1)'s own per-site scope. DS-51's specific ask — how many sites exceed α — is carried in. |
| DS-59 | ← **survivor**; R5-66 merged into it | Preprint spot-check. DS-59 names three eprint IDs and is the more actionable office instruction; R5-66's "published" limb is already carried as a major by R5-18. |
| R5-08 | **DS-18** | Two threshold rules. Anchors identical; tiebreak to the earlier-listed ID. Co-discovery: R1-53. |
| R5-14 | **DS-11** | E5 n = 2. DS-11's anchor is the fuller quote and additionally names the Figure 5 gap ranking. Five-way co-discovery. |
| R5-21 | **DS-29** | "Near-tripling". DS-29's "2.32-fold" matches my recomputation (2.3158) exactly; R5-21 rounds to 2.3. |
| R5-25 | **DS-31** | Non-monotone coverage. DS-31 covers all four sweep points including 150 and additionally flags the absent uncertainty; R5-25 covers three. |
| R5-34 | **DS-32** | Citekey years. **DS-32's count of three is correct; R5-34 says "four" and then names three.** Merging into the correctly counted finding disposes of the miscount without losing the co-discovery. Five-way. |
| R5-35 | **DS-33** | Bib header comment. DS-33 quotes all three lines including the verification-date line; R5-35 quotes two. Four-way. |
| R5-51 | **DS-37** | Self-attestation register. DS-37 separates attestation from pre-emption cleanly; R5-51 blends both, and its §5.2 pre-emption limb belongs to DS-38. Both DS findings survive; R5-51 folds into DS-37. |
| R5-54 | **DS-48** | ρ̂ = 0.830 on E6. DS-48 adds the E2 limb (does the same 17% departure operate there, and in which direction relative to safety), which is the limb that matters. Note R5-54's premise "described as an in-distribution study" is an *inference* — the manuscript never states E6's shift status, which is itself part of the required answer. |
| R5-65 | **DS-56** | Abstract's BBSE claim. DS-56 covers both weak abstract sentences; R5-65 covers one. |
| R5-66 | **DS-59** | See DS-59 row. |

**Cross-type overlaps deliberately NOT merged** (same defect, different editorial artifact): DS-47 / R5-63 with R5-01 · R5-55 with R5-02 · R5-56 with R5-16 · R5-57 with DS-31 · R5-59 with R5-41 · R5-60 with R5-12 · R5-61 with R5-28+R5-29 · DS-54 with DS-19 · DS-50 with DS-11 · R5-67 with DS-09 · DS-58 with DS-22 · R5-64 with R5-10. Findings go to the authors; questions ask them to act; confidential notes go to the editor alone. Collapsing these would lose an artifact the decision letter needs.

**Cross-report co-discovery noted but outside my assignment** (for the editor's reconciliation): DS-05/R5-15 ↔ R1-42, R2-30, R3-24, R3-46 · DS-14/R5-19 ↔ R1-17, R2-22, R3-14, R3-15, R4-35 · R5-12 ↔ R1-18, R2-24, R3-01, R3-44, R4-15 · DS-11 ↔ R1-30, R2-19, R3-07, R4-10 · R5-10 ↔ R1-16, R2-26 · DS-32 ↔ R1-37, R2-38, R3-28, R4-27 · R5-30 ↔ R4-03 · DS-57 ↔ R1-67, R4-44.

---

### Examiner B — Referee 1 (R1)

Every merge below is same-defect/same-passage. In each case the question or confidential form supplies a
remedy or an editorial weighting the survivor lacks, so the survivor should be forwarded **carrying that
text**, not replacing it.

| Merged | Into | Note |
|---|---|---|
| R1-48 | **R1-24** | Same defect (bare $n$ undefined in the $\lambda_t$ display). R1-24 has the sharper anchor — it quotes the whole display and lists all three undefined objects. R1-48 supplies the *reason it matters* that R1-24 lacks: §3.3 puts two site counts in play (all atoms vs record-carrying) and $\lambda_t \propto n^{-1/2}$, so the ambiguity changes the bet schedule and hence power. Carry that sentence into R1-24. |
| R1-54 | **R1-01** | Question form of the marginal-vs-conditional gap, same §3.1/§3.3 passages. Adds the disposition the editor needs: restate as a site-population mean, or supply the per-site proof. |
| R1-55 | **R1-02** | Question form, same A.1(ii)/(iii) passages. Adds the demand to name the conditioning regime as a numbered assumption. Forward with my realizable counterexample substituted for the referee's. |
| R1-56 | **R1-11** | Question form, same §4.4 passage. Adds the three specific deliverables: the tilt's generative equation, whether $P(x\mid y)$ changes, and which modes were run. |
| R1-57 | **R1-09** | Question form, same §4.3 passage. Adds the decisive experiment — BBSE certify/decline rates in the no-shift world plus a shift-magnitude sweep. This is the single most actionable request in the report. |
| R1-58 | **R1-08** | Question form, same §4.7/Table 3 passage. Adds the specific measurement: empirical coverage of $[\rho_{\text{lo}},\rho_{\text{hi}}]$ across E1/E2/E6, and whether the box covers $\rho=1$. |
| R1-60 | **R1-24** | Question form, same §3.4 display. Adds nothing beyond the remedy (define $\hat\sigma^2$, define $n$, say where $\hat\mu$ enters). |
| R1-61 | **R1-14** | Question form, same §3.3 passage. Adds the concrete ask: report unweighted record-level answered error beside $R_M$ in E1 and E6, and move $M$. |
| R1-62 | **R1-12** | Question form. Adds the two comparators to require: record-as-unit on the same E1 draws with the same screen, plus one external method. |
| R1-63 | **R1-15** | Question form, same A.2 passage. Adds the ask: write $A$ and $B$ out in both branches of $w_{\max}=\max(1,\rho)$. |
| R1-64 | **R1-22** | Question form, same §3.6/A.2 passages. Adds the two deliverables: define "valid", and evidence that conditioning on validity leaves coverage intact. |
| R1-65 | **R1-01** | Confidential form. Same defect; also carries R1-17's Barber–Candès–Ramdas–Tibshirani omission. Its editorial weight — that the gap is not repairable by rewording and that the contribution shrinks if the claim is honestly restated — should travel with R1-01. |
| R1-66 | **R1-06** | Confidential form; anchors on exactly R1-06's pair (§3.9 + §4.2) and bundles R1-05's wrong-functional point and R1-12's no-comparator point. Note its concession that the manuscript's candour is genuine and the effect is not thought deliberate. |
| R1-67 | **R1-09** | Confidential form, same §4.3 passage. Its judgement — that E2 reads as a declining machine and that this is answerable with one extra experiment — is the editorially useful part. |
| R1-68 | **R1-20** | Confidential form, same preprint set. *Correction:* "seven of thirty" — the bibliography has **31** entries, so it is seven of thirty-one. The seven is right; the denominator is off by one and does not affect the point. |
| R1-70 | **R1-11** | Confidential form of the E3 prior-shift suspicion, same §4.4/§4.1 passages. Adds the consequence the editor must weigh: if E3 is a relabelled prior shift, contribution 4 is not what it claims and the 83% is evidence *against* the BBSE mode. Properly hedged ("I suspect but cannot prove from the manuscript"), so it clears the access rule. |

**Co-discovery outside my assignment**, recorded for the editor's reconciliation. These assigned findings
are independently reached by other referees and should be treated as corroborated, not as four separate
complaints: R1-01 (DS-02, R5-01, DS-47, R5-63); R1-09 (DS-03, R2-03, R5-06, DS-56, R2-65, R5-65); R1-12
(DS-01, DS-15); R1-14 (R2-04, R2-63); R1-16 (DS-10, R2-26, R5-10, R5-64); R1-18 (DS-16, R2-24, R3-01,
R3-44, R4-15, R5-12, R3-37, R5-60 — eight findings, five referees); R1-19 (DS-04, R2-11, R5-13, R2-52);
R1-20 (DS-13, R2-23, R4-34, R5-18, DS-59, R2-69); R1-21 (R2-32, R4-09); R1-23 (R5-17, R4-02, R4-43); R1-24
(DS-24, R5-24); R1-26 (R5-05); R1-27 (DS-30); R1-28 (DS-20, R4-08); R1-29 (DS-31, R2-36, R5-25, R2-59,
R5-57); R1-30 (DS-11, DS-50, R2-19, R2-66, R3-07, R3-25, R3-35, R3-42, R4-10, R4-46, R5-14); R1-32 (R2-33,
R2-55, R3-12, R3-36, R5-41, R5-59, DS-46); R1-33 (DS-17, R5-27); R1-34 (R5-22); R1-35 (DS-26, DS-27, DS-28,
R2-41, R2-42, R5-39, R3-23); R1-36 (DS-07, R2-40, R4-17, R4-40, R5-40); R1-37 (DS-32, R2-38, R3-28, R4-27,
R5-34); R1-38 (DS-33, R2-39, R5-35); R1-39 (R5-33); R1-41 (DS-37, DS-38, R2-47, R5-51); R1-42 (DS-05,
R2-30, R3-24, R3-46, R5-15); R1-43 (R2-45, R3-22); R1-46 (R2-37, R5-36); R1-47 (R5-37); R1-49 (R5-16,
R5-56); R1-50 (DS-40); R1-51 (DS-36); R1-53 (DS-18, R5-08); R1-69 (R3-41, R3-45, R2-68, DS-58, R5-67).

Where a co-discoverer had artifact access and I did not — R4 on `n_declined: 2` (R1-30), on the unpinned
experiment constants (R1-23), on the missing BBSE diagnostics (R1-09) — the artifact-side finding
independently corroborates the manuscript-only finding. That is worth stating in the decision letter: these
are not four referees repeating each other's guesses.

---

### Examiner C — Referee 2 (R2) and Referee 3 (R3)

Each entry below is folded into the survivor named. Where the merge is across referees I say so — independent co-discovery is evidence the underlying defect is real, and the editor should weight it accordingly.

| ID | Merged into | Note |
|---|---|---|
| R2-24 | **R3-01** | Cross-referee co-discovery. R2's version adds two elements worth keeping in the survivor: that features are correlated in *any* real clinical feature set (creatinine/eGFR, HR/shock index), and the consequence for the real-data instantiation §5.5 promises. |
| R3-37 | **R3-01** | Question form. Preserves the sharpest ask: report the empirical correlation matrix and state which value function (interventional/marginal vs conditional/observational) the exactness claim invokes. |
| R3-44 | **R3-01** | R3's confidential restatement; adds only the diagnosis that the authors likely have not read the dependence literature. |
| R3-07 | **R2-19** | Cross-referee co-discovery. **Correction carried:** R3-07's contrast — "every other headline rate in the paper carries an exact 95% CI" — is overstated. The E2 conditional 0/9 rate, all decline rates, and every cell of Tables 1–4 also lack intervals (DS-20, R1-28). |
| R3-35 | **R2-19** | Question form; asks for the declined-case count and whether the gap survives R=200 replication. |
| R3-42 | **R2-19** | Confidential; supplies the mechanism argument (features 0–3 at 1.157/1.161/1.178/1.155 give no reason for feature 0 to differ) that I judge the strongest single reason to expect noise. Preserved in the survivor. |
| R2-66 | **R2-19** | R2's confidential restatement of the same n=2 defect. |
| R2-65 | **R2-03** | Confidential; adds the "null result presented as a safety result" characterisation. |
| R2-63 | **R2-04** | Confidential; adds the recommendation that correcting the abstract be a condition of acceptance. |
| R2-50 | **R2-05** | Question form: report the declined-set positive fraction directly for E1 and E6. |
| R3-40 | **R2-05** | Cross-referee co-discovery of the same defect from the XAI side; preserves the distinct point that fair-abstention work the paper already cites (`ifac2025abstainexplain`) is the natural frame. |
| R2-48 | **R2-06** | Question form: state err_i's functional form, the threshold at which ŷ is formed, and whether FP/FN weigh equally. |
| R2-49 | **R2-07** | Question form; asks the authors to confirm or refute the ≈0.53 sensitivity reconstruction, which my recomputation supports. |
| R2-64 | **R2-07** | Confidential; adds that the absence of any confusion matrix is itself telling. |
| R2-53 | **R2-08** | Question form; the calendar-period item is one entry in R2-08's list. |
| R2-51 | **R2-09** | Question form: does the generator vary P(x|y) or only π_c. |
| R2-67 | **R2-09** | Confidential; the referee's own statement that he could not prove this from the manuscript. My reading of §4.1 settles it: as described, only π_c is site-indexed. |
| R2-56 | **R2-10** | Question form: what diagnostic can a non-contributing hospital run. R2-10's own text already contains the gap ("no diagnostic by which the community hospital could check either"). |
| R2-52 | **R2-11** | Question form: name the empirical sources for log-mean 6.0, log-sigma 1.1, 0.095 and SD 0.5, or label them illustrative. Inherits R2-11's PLAUSIBLE status. |
| R2-58 | **R2-13** | Question form: can R_M take asymmetric costs without breaking A.1(i). |
| R2-57 | **R2-16** | Question form: recertification cadence and monitored quantity, or an explicit out-of-scope statement. |
| R2-61 | **R2-21** | Question form: maximum per-site answered error and count of sites exceeding α. |
| R2-60 | **R2-23** | Question form: is `zhou2026falsesense` clinical, and if not what licenses the transfer. |
| R2-62 | **R2-27** | Question form: how many sites in E1/E6 received zero coverage. |
| R2-55 | **R2-33** | Question form: report τ* for E1–E4 and its variation across draws. |
| R2-59 | **R2-36** | Question form: explain the 208→300 coverage drop and whether it is within Monte Carlo error. |
| R3-28 | **R2-38** | Cross-referee co-discovery; R3-28 covers two of the three key/year mismatches, R2-38 covers all three plus the venue misattribution. |
| R3-45 | **R2-68** | Cross-referee co-discovery of the same venue-fit judgment. Preserves R3-45's distinct point that the educational-XAI framing (one Collection editor's speciality) is engaged nowhere — which I verified independently under R3-18. |
| R3-34 | **R3-04** | Question form; my mathematical correction under R3-04 makes this answerable in one line. |
| R3-43 | **R3-08** | Confidential; adds that the two unreplicated experiments are precisely the two in R3's remit. |
| R2-25 | **R3-10** | Cross-referee co-discovery. Preserves R2-25's two concrete asks (a clinically named worked vignette; an explicit sentence that clinical utility is untested). |
| R3-38 | **R3-10** | Question form: what artefact does a clinician receive, and has any human ever seen one. |
| R3-39 | **R3-11** | Question form: what explanation survives a black-box head, and does Contribution 3. |
| R3-36 | **R3-12** | Question form: was τ*=0.55 certified, in which mode, at which α, on which draw. |
| R3-41 | **R3-13** | Confidential; the "earn the title or change it" recommendation. |
| R2-45 | **R3-22** | Cross-referee co-discovery; R3-22 is broader (covers "base" as well as μ_j). R2-45's distinct ask is preserved: say *why* the training-split mean is the right reference population, which is what makes an attribution interpretable to a clinician. |
| R2-30 | **R3-24** | Cross-referee co-discovery of the figures absence. |
| R3-46 | **R3-24** | R3's confidential restatement; adds that no referee should be asked to sign off on unreviewable explainability evidence. |

---

### Examiner D — Referee 4 (R4)

**None.** No two findings in my assigned set are duplicates of one another.

Referee 4 deliberately runs several defects in parallel registers — a major point, a question to the authors, and a confidential note to the editor — and each register carries content the others do not. Merging them would delete the actionable asks. The linked triads, recorded here so the editor can consolidate the decision letter without losing material:

| defect | major | question | confidential |
|---|---|---|---|
| `sep = 1.8` undisclosed | R4-01, R4-02 | R4-36 | R4-43 |
| BBSE declines undiagnosable | R4-07 | R4-37 | R4-44 |
| `harness.py` untested | R4-11 | — | R4-45 |
| missingness encoder / E5 n=2 | R4-03, R4-10 | — | R4-46 |
| availability, licence, packaging | R4-17 | R4-40 | — |
| provenance not serialised | R4-05 | R4-41 | — |

Adjacent-but-distinct pairs I checked and deliberately did **not** merge: R4-20 (undocumented decline *gate*) vs R4-21 (constants *enumeration*) — different passages; R4-19 (§3.5/§3.6 on δ) vs DS-18/R1-53/R5-08 (§3.5/§3.6 on threshold rule) — two separate contradictions between the same two sections.

**Cross-report co-discoveries** (survivors lie outside my set; flagged for the editor's reconciliation, with the R4 sibling's distinctive contribution named):

| R4 finding | co-discovered by | what R4 adds that the others could not reach |
|---|---|---|
| R4-08 (0/9 no interval) | DS-03, DS-20, R1-09, R2-03, R5-06, R5-65 | that no Clopper–Pearson code exists in the release at all |
| R4-15 (exact Shapley) | DS-16, R1-18, R2-24, R3-01, R3-44, R5-12, R5-60 | the dependence claim grounded in `data.py`'s actual generator |
| R4-10 (E5 n=2) | DS-11, DS-50, R1-30, R2-19, R2-66, R3-07, R3-25, R3-35, R3-42, R5-14 | `n_declined: 2` from the artifact, and τ* = grid floor |
| R4-27 (bib key/year) | DS-32, R1-37, R2-38, R3-28, R5-34 | — (pure co-discovery) |
| R4-34 (preprints) | DS-13, DS-59, R1-20, R1-68, R2-23, R2-69, R5-18, R5-66 | — |
| R4-35 (Barber et al. absent) | DS-14, R1-17, R5-19 | — |
| R4-17/R4-40 (availability) | DS-07, DS-27, R1-36, R2-40, R5-40 | no licence, no packaging, no VCS, dangling `../testbed` paths |
| R4-03 (missingness encoder) | R5-30 | that the code's behaviour is the *inverse* |
| R4-04 (R=200 false for E5/E6) | R3-08, R3-43 | the code proof (`_rng(5)`, `_rng(6)`, no loop) |
| R4-16 (ρ̂ = 0.830 unshifted) | DS-48, R1-08, R1-58, R5-54 | that E6 **deployed under the BBSE tag** |
| R4-23 (bin notation) | R5-43 | `SIZE_BINS` and the `lo <= x < hi` filter |
| R4-30 (single-site pools) | R2-34, R5-62 (adjacent) | the answer: `draw_cohort(cfg, 1, …)` |
| R4-18 (broken figures) | DS-05, R1-42, R2-30, R3-24, R3-46, R5-15 (**complementary, not duplicate**) | the PNGs themselves — see note under R4-18 |

Co-discovery by referees working from disjoint materials is evidence these are real. It is strongest for R4-03 (manuscript-only R5 and artifact-holding R4 converging on a fictional component), R4-15 (seven flags across five reports), and R4-10 (ten flags).

---

---

## Kill log

### Examiner A — desk-screen (DS) and Referee 5 (R5)

### DS-06 — **KILLED** · criterion 2 (the manuscript answers it, inside the finding's own anchor)

**Finding:** "The manuscript contains no reference list — the References section holds only a build note — so seventy-plus in-text citations resolve to nothing a referee can inspect."

**Evidence that defeats it.** The anchor the finding itself quotes is the answer:

> "# References
>
> (Generated from references.bib by pandoc --citeproc at conversion time.)" (draft.md lines 351–353)

The passage states the mechanism and names the source file, and `paper/references.bib` was supplied to every referee under the stated access rules. The finding's operative claim — that the citations "resolve to nothing a referee can inspect" — is refuted by the desk screen's own conduct: **DS-32, DS-33, DS-34 and DS-35 are four findings whose entire evidence is line-level inspection of `references.bib`**, including exact line numbers (1–3, 169–181, 249–260, 262–271). A referee who cites the bibliography by line number in four findings has inspected it.

I also checked the numeric limb, which is the only part that survives contact: I count **96 in-text citation instances across 31 distinct keys**, so "seventy-plus" is correct — and, favourably, **every cited key resolves to a bib entry and every bib entry is cited** (zero dangling, zero orphaned). That is a point in the manuscript's favour, not against it.

**Residual, and what the editor may do with it.** A submitted manuscript should of course carry a rendered reference list, and if the authors submit this markdown without running the conversion, that is a mechanics failure. But that is a one-line production reminder, not the finding as written, and it is not evidence of a defect in the manuscript's scholarship. Do not forward DS-06. If the editor wants the reminder, it belongs beside DS-07 and R5-40 in the submission-mechanics paragraph.

### DS-07 — partial kill · criterion 4 (deliberate placeholder fields)

The finding survives in narrowed form (see Verified findings) but **three of its limbs die**:

> "# Funding
>
> [TO BE COMPLETED]" (lines 278–280) · "# Author contributions
>
> [TO BE COMPLETED]" (lines 282–284) · "# Competing interests
>
> [TO BE COMPLETED]" (lines 294–296)

These are deliberate to-be-filled declaration fields of the same character as `[AUTHOR NAME(S)]`, `[· ORCID]`, `[AFFILIATION — department, institution, city, country]` and `**Corresponding author:** [NAME], [EMAIL]` at lines 3–7, which the office rules exempt. "Author contributions" is squarely an author-identity field. Flagging an unfilled Funding or Competing-interests declaration in a pre-submission draft is flagging a placeholder.

**What survives and must be forwarded:** (a) the Data availability statement's operative content is the placeholder `[CODE REPOSITORY URL — to be added]`, which is a substantive availability claim and not an identity field; and (b) the manuscript carries **no Code availability section** at all — I verified the back matter runs Acknowledgements → Data availability → Funding → Author contributions → Ethics approval → Consent for publication → Competing interests. Limb (a) is co-discovered five ways (DS-27, R5-40, R1-36, R2-40, R4-17).

### Clauses struck from otherwise-surviving findings

These are not kills, but the editor must not forward the quoted words:

1. **R5-06 / DS-03 — "the only rate in the Results reported without the Clopper–Pearson interval."** False. I enumerated every rate in §4.2–§4.5: intervals appear on exactly **four** numbers, and the two overall exceedance rates, both decline rates, all four Table 1 bin exceedances, all twelve Table 4 certify rates and every coverage mean are equally bare. **DS-20, in the same desk-screen report, says exactly this** — the screen contradicts itself. The 0/9 finding does not need the clause and is stronger without it.

2. **DS-19 — "provides no evidence that the BBSE mode ever functions as a correction."** Overstated: 9 draws certified with 0 hard-violations is weak but non-zero evidence. The defensible claim is that a single shift magnitude cannot distinguish a working correction from a shift detector.

3. **DS-23 — "despite being only 241 words and having room to define them."** I count **240** tokens. At or against a typical 250-word Springer cap there is essentially no room, so the rationale is unsupported. The defect (three undefined terms of art) stands; the remedy is substitution, not addition.

4. **R5-45 — the §1 ¶1 quote, "that promise is often false."** Explicitly hedged by "often"; it does not belong in an unhedged-generalization finding. Forward the Abstract and §1 ¶3 instances only.

5. **R5-39 — "specifies its generator … rather than in the paper itself."** §4.1 does give the full generator specification in the paper (clipped lognormal 6.0/1.1, [20, 5000], d = 8, sep = 2.2, prevalence 0.095, $u_c \sim \mathcal{N}(0, 0.5^2)$). The defect is the attribution phrasing plus the code identifiers and test count, not absence of specification.

6. **R5-17 — "repeated at §3.10 and A.3."** A.3 repeats the *pinning* claim but not the pre-registration phrase. Should read "§3.10".

7. **R5-63 — "the homogeneous in-distribution experiment."** The generator is not homogeneous; it carries site random effects $u_c \sim \mathcal{N}(0, 0.5^2)$ (§4.1). The accurate statement — E1's targets are drawn *exchangeably* with calibration, so no adversarial per-site case is tested — makes the same point without the error.

8. **R5-34 — "Four bibliography citekeys."** Three. Disposed of by merging into DS-32, which counts correctly.

9. **R5-54 — "E6, which is described as an in-distribution study with no shift."** The manuscript never describes E6's shift status. The premise is a supportable *inference* from §4.7's "the ~9.5% cohort prevalence," and the absence of any statement is itself part of what the authors must supply.

---

### Examiner B — Referee 1 (R1)

**No finding in this batch was killed.** That is an unusual outcome and I want the basis on the record, so
the editor can see the audit actually ran rather than rubber-stamped. Every quoted anchor was located
verbatim in `paper/draft.md` or `paper/references.bib`; every number the referee supplied was recomputed
and every one was right; no assigned finding demands something the manuscript explicitly and defensibly
scopes out; no assigned finding rests on a code, test-suite or experiment-output fact (the two that come
closest — R1-11 on the E3 generator and R1-15 on the A.2 test suite — are both framed as "the manuscript
does not put this on the page," which is the permitted form); and no assigned finding is about an
author/affiliation/ORCID/corresponding-author placeholder.

Two findings were **downgraded to PLAUSIBLE** rather than killed, with the settling check named in each
entry above:

- **R1-13** — the "trivially satisfiable by abstaining" clause is contradicted by the manuscript's own
  displayed atom identity. $Z_c-\alpha = g_c a_c(e_c-\alpha)/M$ makes the certification margin scale
  linearly in coverage, and a zero-answer site contributes exactly $\alpha$, giving wealth factor 1; a
  fully abstaining gate has $K_t\equiv 1$ and can never reach $1/\delta$. The no-coverage-floor half stands.
- **R1-44** — "records within a hospital are not exchangeable with those from an unseen site" is correct
  under the ordinary joint-law reading of "exchangeable with", and is wrong only under the marginal reading
  the referee assumes. The manuscript does not force either reading.

Six further findings survive but carry a **correction the editor should apply before forwarding**, each
evidenced above:

| Finding | Correction |
|---|---|
| R1-02 | The referee's bets $(\lambda_1,\lambda_2)=(1,0.01)$ are unproducible by the manuscript's own schedule ($\hat\sigma^2\le0.25$, $n\approx83$ ⟹ $\lambda\in[0.54,1.0]$). Substitute the realizable pair $(1.0,0.5)$, which gives $\mathbb{E}[K_2]=1.125>1$; and note that A.1(iii)'s inequality already fails atom-wise for any site with $\mu_t<\alpha$. |
| R1-03 | A.1(ii) does *not* bare-assert that $\mathbb{E}$ of a ratio is a ratio of $\mathbb{E}$s — it derives it from "the denominator … is non-random." That clause is parasitic on R1-02 and should be dropped as an independent error. |
| R1-12 | "No baseline of any kind" is too strong; §4.3 runs an uncorrected exchangeable baseline. The true claim is that it is an internal ablation, with no record-as-unit and no external comparator anywhere. |
| R1-23 | The pre-registration phrase appears twice (§3.2, §3.10), not three times; A.3 restates the pinning without the pre-registration claim. |
| R1-30 | The declined-case count *is* stated ("declining 2") in the finding's own anchor. The correct complaint is that the manuscript never says whether the cohort-level statistic comes from that deployment or a larger one. |
| R1-68 | Seven of **thirty-one** bibliography entries, not thirty. |

Three findings survive but should be forwarded with the manuscript's **partial answer attached**, so the
authors are not asked to supply what they already supplied: R1-06 (§3.9 already concedes the criterion
"evidences the *absence of gross violations at the tested power*"); R1-24 (§3.5 already states which
betting budget each mode spends); R1-31 (§4.5 already distinguishes the cluster gate from the information
floor explicitly, so only §1/§5.2's framing and the grid resolution remain at issue). R1-28's promise
covers "the *primary* rates," not every rate, so the sharp instance to forward is Table 4's certify rates,
not Table 1's diagnostics.

One finding is flagged for **editorial policy rather than fact**: R1-36 (the Data-availability repository
URL). It survives under my kill rule because that rule enumerates author/affiliation/ORCID/
corresponding-author fields and this is none of them, and because §3.10, A.3 and §5.5 stake checkable
reproducibility claims on it. If the office's convention treats all bracketed "to be added" fields as
deliberate, R1-36 dies with them.

### Examiner C — Referee 2 (R2) and Referee 3 (R3)

### R2-41 — **KILLED** under criterion 2 (the manuscript answers it elsewhere)

**The finding:** "The appendix reports a bare passing-test count with no description of what the suite verifies, which conveys no assessable information to a reader." Anchor: "The test suite is 69/69 green." (Appendix A.3)

**The evidence that defeats it.** The manuscript describes what the suite verifies in four places, two of them in the very same paragraph as the anchored sentence:

> "The frozen design constants — split fractions, budget ladder, influence cap $M$, threshold grid, betting-test parameters, and decline thresholds — are pinned to their literal values by a unit test, so any drift fails continuous integration." (A.3, line 268)

> "The anti-conservativity of naive realized-contribution truncation (Section 3.3) is pinned by a dedicated regression test, in which a construction with 17.5% true risk certifies at $\alpha = 5\%$ under truncation but is correctly refused under the influence-weighting scheme." (A.3, line 268)

> "The test's boundary behavior (type-I error at $\mathbb{E}[Z] = \alpha$) is additionally pinned by the unit test suite." (Appendix A.1(iv), line 258)

> "The argument is pinned numerically in the test suite on the deployed normalization, including an interval that straddles $\rho = 1$." (Appendix A.2, line 264)

Four described tests, one of them stated with its full numerical construction. "No description of what the suite verifies" is false as written.

**Why this is a clean kill rather than a technicality.** R2's own report contradicts the finding as indexed: it says "Either summarise what the suite verifies (**the boundary type-I check and the anti-conservativity regression test are the two the paper actually leans on**) or remove the count." The referee knows the manuscript describes them; his actual point is narrower — that the integer 69 is not itself assessable. The Stage-1 index has restated a narrow, sound point as a broad, false one.

**What the editor should forward instead.** The narrow version survives elsewhere in the pool and is not mine to prosecute: **DS-28** ("A unit-test pass count is reported in the manuscript as though it were a result, which is unverifiable at review and not a scientific claim") and **R1-35** carry it correctly. If the editor wants this point in the decision letter, take it from DS-28, not from R2-41.

---

### Examiner D — Referee 4 (R4)

Nothing in this assignment died outright. Every finding was tested against all six criteria; the record of what I tried and what survived:

**R4-13, limb (a) — partial kill under criterion 2 (the manuscript answers it elsewhere).**
The finding's first limb asserts §4.4's *"the harness first verifies the poison"* misstates the order of operations. The code order is as R4 describes: `run_E3` runs the full 200-draw loop (`:267-279`), then computes `verified` (`:284`), then raises (`:288-293`). **But the manuscript's very next clause discloses the true ordering:** *"a tilt that failed to raise true risk above $\alpha$ aborts the run **before any output is written** (reason `e3-control-not-poisonous`)"* (§4.4, line 178). R4 concedes this clause is accurate. Read against it, "first" means "before the result is reported", which is what happens. Limb (a) should not be forwarded.
Limbs (b) — 0.2022 is a mean of *realized* rates called "true risk", contradicting §3.7 clause (3) — and (c) — the abort path has no test — are untouched by that clause and are CONFIRMED above. Forward R4-13 on (b) and (c) only.

**Criterion 4 (placeholder fields) tested and rejected for R4-17 and R4-40.**
Both cite *"publicly available at [CODE REPOSITORY URL — to be added]"*. The exemption is written for author / affiliation / ORCID / corresponding-author placeholders; a data-availability statement is a substantive editorial requirement, not an author field — and R4 anticipates the objection in terms ("This is not an author-placeholder exemption; it is the availability statement itself"). Decisive in any case: both findings carry substance wholly independent of the missing URL, which I verified by direct inspection of the repository root — **no `LICENSE`, no `COPYING`, no `pyproject.toml`, no `setup.py`, no `setup.cfg`, no `.git`** — plus six dangling `../testbed` / `../audit` / `../PROTOCOL.md` references in `README.md`, `certify.py:4`, `shift.py:8`, `data.py:3`, `report.py:87`. Strip the placeholder entirely and both findings stand.

**Criterion 6 (access rules) not applicable to any assigned finding.**
Referee 4 was given `README.md`, `requirements.txt`, `certgate/`, `tests/` and `experiments/` including `experiments/out/`. Every code- and artifact-grounded assertion in R4-01 … R4-47 is within its access grant. Criterion 6 would bar DS/R1/R2/R3/R5 from these assertions, not R4.

**Criterion 3 (wrong numbers) tested exhaustively and rejected — with three corrections that do not defeat their findings.**
I recomputed or recounted every numerical assertion R4 makes. All held. Three are imprecise at the margin and I record the corrections so the decision letter does not repeat them:
- **R4-16:** ρ̂ = 0.830 *is* printed in §4.7 and Table 3, so "reports neither the deploy mode nor the size of that spurious correction" overstates. The verified absences are the deploy mode and the true ρ = 1 against which 0.830 is a 17% spurious movement.
- **R4-33:** 83% appears **four** times, not five (Abstract, §4.4, §5.1, Fig 3 caption). 48.5% and the E1 pair do appear five times each.
- **R4-25:** "four grid points" is correct read as x-positions (60, 100, 150, 208); read as table cells the count is six.
Independently confirmed as exactly right: the 2,331 `nan` tokens (200 / 591 / 200 / 1,340), the 191 `failsafe` declines, the 0/9 upper bound of 0.3363, all four published Clopper–Pearson intervals, `MIN_CAL_CLUSTERS/SPLIT_FRACTIONS[2] = 50/0.40 = 125`, and the ~2× overstatement in R4-24 (51,414 calibration records vs the stated ~10⁵).

**Criterion 1 (misread passage) tested against every anchor and rejected.**
I located each quoted passage in `paper/draft.md` and read it in context. Every quotation is verbatim and in-context. The one wording inaccuracy I found is R4-18's "the six **embedded** figures" — the manuscript embeds no images. That does not kill R4-18, whose anchor is the Figure 3 caption (verbatim) plus the rendered PNG (independently inspected); it means R4-18 is a finding about the artifact's figure files, complementary to the six manuscript-side findings that the submission contains no figures at all. Both must be forwarded.

**Criterion 5 (defensibly scoped out) tested and rejected throughout.**
I searched for scoping passages that would defeat R4-01 (the draft mentions `sep` exactly once, at line 152, and never per-experiment), R4-04 (§4.6/§4.7 say "case study" and "separate deployment" but never state R=1 — an admission of informality at most, not a defended scope boundary), R4-20 (`MIN_ANSWERABLE`, `pool-too-small` and "10 records" return zero hits in the draft), and R4-21 (`1e-4`, `max_iter`, `n_boot=500`, `MIN_ANSWERABLE` all absent). §6.1's limitations list is the manuscript's genuine scoping section and it does defend six exclusions — but none of them covers any assigned finding, and one of the six (*"Missingness is handled without a positivity diagnostic"*) is itself the subject of R4-03.

---

## Examiner notes carried to the editor

### Examiner A — Examiner A — verification of desk-screen (DS) and Referee 5 (R5) findings (section lead-in)

**Scope:** 128 assigned findings (DS-01…DS-60, R5-01…R5-68), prosecuted against `paper/draft.md` (353 lines) and `paper/references.bib` (345 lines). Every anchor below was independently located in the manuscript; every arithmetic claim was independently recomputed.

**Disposition:** 96 CONFIRMED · 8 PLAUSIBLE · 23 MERGED · 1 KILLED.

**Merging policy applied.** Where two assigned findings state the same defect against the same passage *and are the same finding type*, I merged into the sharper anchor. I did **not** merge a `question` or a `confidential` note into a `major`/`minor` finding even when the underlying defect is identical: questions carry an action for the authors and confidential notes are addressed to the editor, so folding them away would destroy an editorial artifact. Those cross-type overlaps are cross-noted instead. Co-discovery by referees outside my assignment (R1, R2, R3, R4) is noted where it applies but not merged — the editor reconciles.

**Independent verification harness.** Recomputed and used throughout:

| Quantity | Recomputed | Manuscript / finding |
|---|---|---|
| Clopper–Pearson 95% upper, 0/9 | **0.3363** | R5-06 "roughly 0.336" ✓; DS-03 "roughly 0.34" ✓ |
| Clopper–Pearson 95% upper, 0/200 | **0.0183** | §4.3 "[0, 0.018]" ✓ |
| Table 1 pools 2+18+53+127 | **200** | = R (one pool per draw) ✓ |
| Table 1 exceedance counts 0,2,1,7 | **10/200 = 0.0500** | §4.2 "realized exceedance rate is 0.05 overall" ✓ exact |
| 0.22 / 0.095 | **2.3158** | §4.3 "a near-tripling" ✗ |
| 0.0630 − 0.0591 | **0.0039 = 0.39 pp** | §4.7 "~0.4-point gap" ✓ (units unstated) |
| Table 3: 917, 1378.9, 1470 / 23,325 | **0.0393, 0.0591, 0.0630** | Table 3 ✓ all three |
| 0.40 × 208 | **83.2** | §3.5 "about 83" ✓ |
| M / n_max = 100 / 5000 | **0.02 = 1/50** | R5-26 "one fiftieth" ✓ |
| Table 2 sites 4+15+21 | **40** | §4.7 "40 target sites" ✓ |
| Abstract length | **240 whitespace tokens** | DS-23 "241 words" ✓ |
| `Figure N` occurrences | **lines 300, 302, 304, 306, 308, 310 only** | all inside `# Figures`; zero body callouts |
| Image markup (`![`, `.png`, `.pdf`, `.svg`, `includegraphics`) | **zero matches** | no figures embedded |
| Citation instances / distinct keys | **96 / 31** | 31 bib entries; **zero dangling keys, zero orphaned entries** |
| `encoder`, `imput*`, `indicator` | **1 match, line 242 only** | §6.1 Limitations, nowhere else |
| Novelty-inflation scan (`novel`, `unprecedented`, `state-of-the-art`, `first time`, `we are the first`, `paradigm`, `breakthrough`) | **zero hits**; every `first` is ordinal | DS-60 ✓ |

---

### Examiner A — One note the editor should carry into the decision letter

My set contains both the harshest findings in the pool and the most important counterweight. **DS-60 and R5-68 must not be dropped.** I verified both independently: the novelty-inflation scan really does return zero hits (every "first" in the manuscript is ordinal), and the arithmetic audit really does reconcile — Table 1's bins recover the stated 0.05 exactly, all four Clopper–Pearson intervals are correct, all three Table 3 fractions recompute, the bibliography has no dangling or orphaned keys, and §4.5 volunteers a cross-run difference no one would have caught. A decision letter built only from the majors would push the authors toward a paper with fewer hedges and the same evidence. The revisions my confirmed findings ask for are, almost without exception, additive: state the sampling assumption (R5-02), state which mean is bounded (R5-01), add the missing interval (R5-06), sweep the shift magnitude (DS-54), report the certified thresholds (R5-41), name the Shapley value function (R5-60), and delete a component that does not exist (R5-30).

### Examiner B — Examiner B — verification of Referee 1 (statistics) (section lead-in)

Assigned: R1-01 … R1-70. Every finding prosecuted against `paper/draft.md` and `paper/references.bib`.
Nothing survived on the referee's say-so; every quote below was located independently in the manuscript.

**Standing note on R1's arithmetic.** I recomputed every number this referee supplies. All of them are
right: 0/9 exact CP upper bound = 0.3363 ("about 0.34"); E4's 0.3 → [0.237, 0.369] ("roughly
[0.24,0.37]"); Table 1's 2/18 → [0.014, 0.347]; median site size e^6.0 = 403; 0.0630 − 0.0591 = 0.0039.
I also recomputed the four intervals the *manuscript* reports — [0.0012, 0.0357], [0.414, 0.557],
[0.771, 0.879], [0, 0.0183] — and all four are correct. Neither party has an arithmetic error. No finding
in this batch dies on criterion 3.

**Independent observation, load-bearing for R1-05 and R1-27.** Table 1's bin pool counts sum to
2+18+53+127 = **200**, exactly R, and the bins reproduce the stated overall exceedance
(0×2 + 0.1111×18 + 0.0189×53 + 0.0551×127 = 10.0 → 10/200 = 0.05). So E1 evaluates **one target pool per
calibration draw**. The manuscript never says this; it matters below.

---

### Examiner C — Examiner C — verification of R2 (clinical/deployment) and R3 (XAI) findings (section lead-in)

**Scope:** 116 assigned findings (R2-01…R2-70, R3-01…R3-46), prosecuted against `paper/draft.md` and `paper/references.bib`.
**Outcome:** 74 CONFIRMED · 3 PLAUSIBLE · 38 MERGED · 1 KILLED.

### Examiner C — Standing corrections that touch several findings

Three factual errors recur across the two reports. None is load-bearing, but the editor should not forward the numbers as written:

1. **The bibliography has 31 entries, not 30.** Verified by `grep -c "^@" references.bib` → 31.
2. **Seven entries are unrefereed arXiv `@misc` preprints, not six.** The full set is `yu2026joint`, `zhou2026falsesense`, `triage2026audit`, `fedcrc2026`, `score2026`, `scrc2025`, `thermal2026audit`. Both R2-23 and R2-69 omit `scrc2025`.
3. **`ifac2025abstainexplain` is cited five times, not four** — draft lines 25, 33, 54, 130, 192. (R2's own prose says "three times" and then lists four locations; the true count is five.)

---

### Examiner C — The two strongest clusters (section lead-in)

Two defects were found independently by five or six of the six referees. That is the strongest evidence in the pool that they are real, and I say so where they appear.

---

### Examiner C — Notes for the editor

**On the boundary case I did not decide.** R2-40 (unresolved code-repository URL) turns on how widely kill criterion 4 is read. I ruled it survives, because the criterion enumerates a closed class of identity fields — author, affiliation, ORCID, corresponding author — that are blinded for review, and because the finding's second limb (no archived or DOI-minted identifier, which Springer requires) is independent of the placeholder. If the office's rule is that *any* bracketed to-be-completed field is off limits, R2-40 dies. Flagging rather than deciding.

**On the two counts that recur.** The bibliography is 31 entries with 7 unrefereed `@misc` preprints. R2-22, R2-23 and R2-69 all say 30/6. Correct the numbers before they reach the authors — a decision letter that miscounts the bibliography invites a rebuttal on the count instead of on the substance.

**On what the confirmations add up to.** Of the 74 confirmed findings, the great majority are absences that would be fixed by addition, not retractions of claims the manuscript makes. The two exceptions — where the manuscript says something the evidence does not support — are R3-01 (the exactness claim omits its assumption on a generator that violates it) and R2-19 (the "systematic" cohort-level driver computed on two cases). Those two are the ones I would not let through unrevised. R2-70 makes the same structural point from the referee's side and I confirmed every anchor in it.

### Examiner D — Examiner D — verification of Referee 4 (reproducibility) (section lead-in)

**Assigned:** R4-01 … R4-47 (all of Referee 4).
**Access exercised:** `paper/draft.md`, `paper/references.bib`, `README.md`, `requirements.txt`, `certgate/`, `tests/`, `experiments/` including `experiments/out/` and four of the six PNGs. I ran `python -m pytest tests -q` (**69 passed in 3.61s**) and re-ran `python -m experiments.run_synthetic --only E5,E6` into a clean scratch directory.

**Headline.** R4 is the only referee with artifact access, and it shows: 44 of 47 findings are code- or artifact-grounded and 43 of those survive contact with the artifact. I found **no** finding in this set that misreads a manuscript passage, and **no** finding whose arithmetic is wrong. Two findings are downgraded to PLAUSIBLE (R4-22, R4-47) and one (R4-13) survives on two of its three limbs with the third substantially answered by the manuscript's own next sentence — recorded in the kill log.

A standing caution for the editor, developed under R4-18 below: R4 writes of "the six **embedded** figures". The manuscript embeds no images at all — the `# Figures` section (draft.md lines 298–310) is caption text only. R4 inspected the PNGs in `experiments/out/`. R4-18 is therefore a finding about the *artifact's figure files*, and DS-05 / R1-42 / R2-30 / R3-24 / R3-46 / R5-15 are findings about the *submitted manuscript*. They are complementary, not duplicative, and both are true.

---
