# Desk screen — handling editor

**Manuscript:** *CertGate: finite-sample certified selective prediction for multi-site clinical risk models, with label-shift robustness and explainable abstention*
**Collection:** Intelligent Medicine: Machine Learning and Explainable AI for Next-Generation Healthcare
**Screener:** DS (handling editor)
**Files screened:** `paper/draft.md`, `paper/references.bib`

---

## Summary

The paper proposes a selective-prediction gate ("CertGate") for risk models deployed across many hospitals. The pitch is that the usual confidence guarantee attached to a reject-option classifier is written at the record level, that records within a hospital are not independent, and that the guarantee is therefore overconfident once deployment spans institutions. The fix is to make the *site* the unit of inference: each site is compressed into a single bounded atom $Z_c$ built from an influence-capped, answered-only error contribution, and a Waudby-Smith–Ramdas betting martingale over the sequence of calibration-site atoms tests $H_0:\mathbb{E}[Z]\ge\alpha$, with Ville's inequality supplying a finite-sample level-$\delta$ crossing rule. A threshold is picked by a fixed-sequence walk over 23 candidates ordered on an auxiliary split, so no $\delta$ is spent on multiplicity. A second assumption mode handles label shift by BBSE, wraps the confusion-matrix and source-prevalence estimates in a cluster-bootstrap Bonferroni box, and certifies at both endpoints of the resulting weight interval, splitting $\delta$ into $\delta_{\text{conf}}=\delta_{\text{bet}}=0.025$. Because the deployed head is L2 logistic regression, each answered and each declined case carries an exact additive attribution, and declines additionally report a margin-to-answer.

Evaluation is six experiments on a single synthetic generator: 208 sites, clipped-lognormal site sizes, 9.5% base prevalence, a site random effect, eight abstract features of which four carry signal. E1 reports in-distribution validity (hard-violation 0.01 of 200 draws at $\alpha=0.10$; nothing certifies at $\alpha=0.05$). E2 shifts prevalence to 0.22 and reports the uncorrected mode hard-violating 48.5% while BBSE certifies 9 draws and violates none. E3 injects a verified-poisonous concept tilt and shows the certificate hard-violating 83%. E4 sweeps site count and locates the $\alpha=0.05$ frontier near 300–400 sites. E5 and E6 report attributions, per-site coverage, and a three-way answered-set composition.

**Overall assessment.** The statistical construction is careful, the arithmetic is internally consistent everywhere I checked it (E5's logit margins, the Clopper–Pearson intervals, Table 1's weighted exceedance, the boundedness argument in A.1), and the paper is unusually free of novelty inflation — my grep for "novel", "first to", "state-of-the-art" and similar returned nothing. Those are real virtues and I want them on the record. But the manuscript has two problems a handling editor cannot wave through. First, the central contribution — that the site must be the unit of independence — is never demonstrated by this paper's own experiments; the record-level failure it fixes is imported wholesale from a two-month-old arXiv preprint, and there is no ablation anywhere comparing site-as-unit against record-as-unit certification. Second, this is a statistics paper in a clinical jacket: every number comes from one simulator, the features are integers 0 through 7, no clinician appears, no clinical variable appears, and the explainability layer that this collection exists to showcase is explicitly demoted by the authors to "a supporting capability the linear head makes nearly free." Add an absent figure set, an absent reference list, and three declarations still reading `[TO BE COMPLETED]`, and the manuscript is not currently in submittable condition.

---

## Major points

**DS-01 — The paper's headline contribution is never tested against the alternative it claims to fix.**

> "**A site-as-unit certified selective-prediction gate.** A finite-sample $(\alpha, 1-\delta)$ certificate that bounds the influence-weighted error rate among answered cases with the site, not the record, as the unit of independence. This is the central contribution; the site-count frontier is direct evidence that the combination is not free, since certification is feasible only above a data-dependent cluster count (E1, E4)." (§1, contribution 1)

No experiment in E1–E6 runs a record-as-unit certificate on the same cohort. E2's "uncorrected baseline" is CertGate's own exchangeable mode, not a record-level competitor; it isolates the label-shift correction, not the clustering choice. The sentence quoted above concedes as much by offering the site-count frontier as the evidence — but the frontier shows the cluster method is *expensive*, not that the record method is *wrong*. Necessity requires exactly the comparison the paper does not run: fit the same head on the same cohort, certify at $\alpha=0.10$ treating records as exchangeable, and report the hard-violation rate against oracle labels. The harness already computes oracle risk (§4, "because we control the data-generating process, we can compute the true answered-set risk at each target site"), so this experiment costs almost nothing and would convert the paper's premise from a citation into a result. As it stands the load-bearing claim of the paper is assumed, not shown.

**DS-02 — The guarantee is stated per target site; the test certifies a population-average quantity.**

> "with probability at least $1-\delta$ over the draw of calibration sites, the influence-weighted answered-set risk — the parameter $R_M$ defined in Section 3.3 — at a new target site is at most $\alpha$" (§3.1)
> "(1) It is scoped per target site." (§3.7)
> "a bound on the influence-weighted answered-set error *parameter* $R_M$ at a target site" (§5.1)

What the betting test certifies is $\mathbb{E}[Z]\le\alpha$. Via the paper's own identity $Z_c-\alpha = g_c a_c(e_c-\alpha)/M$, this is equivalent to $\mathbb{E}[g a e]/\mathbb{E}[g a] \le \alpha$ — a ratio of expectations over the *site population*. That is a marginal statement. A single new site drawn from that population can have $e_c$ far above $\alpha$ while the population ratio sits below it; nothing in §3.4 or A.1 upgrades a bound on the mean to a bound at an arbitrary draw. Yet the paper asserts the per-site reading three times, and A.1(ii) reinforces the confusion by writing $R_M$ as a finite sum $\sum_c$ over an index set that is never specified — is $c$ ranging over the realized calibration sites, over the target site's records, or over the site population? The distinction is not cosmetic: §3.7 clause (2) already concedes that all sites certified from one draw share a single $1-\delta$ event, which is the signature of a marginal guarantee, and E6 shows per-site answered error varying across bins (0.0294 / 0.0406 / 0.0348) with the per-site *distribution* never reported. Either prove the per-site claim or restate the guarantee as marginal over the site distribution. If the latter, the abstract, §3.1, §3.7 and §5.1 all need rewriting, and the clinical reading ("what a clinician weighs before trusting an automated triage") changes materially, because a hospital administrator cares about *their* site.

**DS-03 — The E2 safety headline rests on nine certified draws, and the one uninformative rate is the only rate reported without a confidence interval.**

> "The joint event that matters operationally — a certificate issued *and* hard-violating — occurs 0 times in 200 draws (exact 95% CI $[0, 0.018]$ ...); conditioning on the 9 draws that did certify ($n_{\text{certified}} = 9$), the hard-violation rate among them is 0.0." (§4.3)
> "we accompany the primary rates with exact (Clopper–Pearson) 95% confidence intervals." (§4.1)

Every other rate in §4.2–§4.4 carries a Clopper–Pearson interval. The conditional rate 0/9 does not — and it is the only one where the interval would be embarrassing: the exact 95% upper bound on 0/9 is roughly 0.34, i.e. the data are consistent with a conditional hard-violation rate approaching seven times $\delta$. The joint-event CI of $[0,0.018]$ is a valid number but it is mostly measuring the decline rate, not the correction's soundness; a mode that declined 200/200 would also score 0 joint violations with the same interval. The abstract's "the corrected mode never does" and contribution 2's "keeps the guarantee valid under outcome-prevalence shift" are both underwritten by nine draws. Report the conditional interval, and either raise $R$ substantially for the certified subset or state plainly that E2 establishes the *absence of a fallback* rather than the *validity of the correction*.

**DS-04 — The generator's claim to clinical realism is asserted without a supporting source, and the citation attached to the nearest sentence does not support it.**

> "On a synthetic cohort of 208 sites whose lognormal sizes, $\sim$9.5% prevalence, and site random effects follow the distributional profile reported for large multi-site clinical cohorts, the certificate is valid but not vacuous." (§1 — no citation)
> "This follows the distributional profile reported across multi-site clinical studies — many small-to-large sites with heavy-tailed sizes, single-digit prevalence, and site-level heterogeneity — while remaining fully known, in keeping with the cluster-as-unit reporting culture that motivates the design [@tripodcluster2023; @internalexternal2021]." (§4.1)

`tripodcluster2023` is Debray et al., *TRIPOD-Cluster Checklist*, BMJ 2023 — a reporting guideline. `internalexternal2021` is Takada et al., *J Clin Epidemiol* 2021, on internal–external cross-validation. Neither reports an empirical distribution of site sizes, and neither supports lognormal(log-mean 6.0, log-sigma 1.1) clipped to [20, 5000], base prevalence 0.095, or a site random effect $u_c\sim\mathcal{N}(0,0.5^2)$. The citation supports the clause about "reporting culture"; it is doing duty for the clause about "distributional profile," which is the load-bearing one. Since the *entire* evidence base of the paper is this generator, its calibration to reality is not a detail — it is the bridge between the results and the clinical claim in the title. Cite a source that actually reports multi-site size and prevalence distributions (a published multi-centre cohort, a registry description), or drop the realism claim and present the generator as a stylized construction chosen for oracle access alone.

**DS-05 — No figures are present in the manuscript, and no figure is called out in the text.**

> "# Figures / **Figure 1. E1 in-distribution validity.** Left: ..." (§Figures)

The `# Figures` section contains six captions and nothing else. I searched the file for image embeds (`![...]`) and found zero. I then searched the entire body — everything before the `# Figures` heading — for the strings "Figure" and "Fig." and found zero occurrences. So: the figures do not exist in the submitted file, and even if the image files were supplied separately, not one of the six is referenced from the narrative. Tables fare better (Table 1 called at §4.2, Table 2 and 3 at §4.7, Table 4 at §4.5 and §5.2) but Figures 1–6 are orphaned entirely. Every figure must be embedded and called out at the point it supports the argument. This alone would normally stop a submission at the office.

**DS-06 — There is no reference list.**

> "# References
> (Generated from references.bib by pandoc --citeproc at conversion time.)" (§References)

The submitted manuscript ends with a build note where the bibliography should be. Seventy-plus in-text citation instances resolve to nothing a reader or referee can inspect. I verified separately that all 31 keys used in the body do exist in `references.bib` and that no bib entry is uncited — that part is clean — but the manuscript as submitted has no reference section. Run the conversion before submitting.

**DS-07 — The declarations block is incomplete, and the data availability statement is non-functional.**

> "All data used in this study are synthetic and generated deterministically by the included code, publicly available at [CODE REPOSITORY URL — to be added]." (§Data availability)
> "# Funding / [TO BE COMPLETED]" · "# Author contributions / [TO BE COMPLETED]" · "# Competing interests / [TO BE COMPLETED]"

Present and adequate: Ethics approval and consent ("Not applicable: the study involves no human subjects and no patient data; all data are synthetic") and Consent for publication. Present but inadequate: Data availability — the paper's *entire* evidence base is code-generated, so an absent repository URL makes the statement void, not merely incomplete. Absent entirely: **Code availability**, which Springer Nature expects as its own declaration and which for this manuscript is arguably more important than data availability. Absent (as placeholders): Funding, Author contributions, Competing interests. These are not the exempt author/affiliation placeholders; they are declarations, and Springer's editorial policy requires all three to be filled before a manuscript can be sent out. Note also that §3.10 and A.3 promise reproducibility in detail ("one command reproduces every figure and table") while the command targets a repository that does not yet have an address.

**DS-08 — "Coverage" is used in two incompatible senses and defined in neither.**

> "hierarchical conformal methods deliver coverage whose unit of independence is the group" (§1) — conformal sense: probability the true label lies in the prediction set.
> "the $\alpha = 0.10$ rung certifies every one of the 200 draws (certify rate 1.0) at mean answered-set coverage 0.9722" (§4.2) — selective sense: the fraction of cases answered.
> "the first two guarantee coverage, not selective risk" (§2.2) — conformal sense again.

The paper never defines either. §3.3 defines $a_c$ as "the answered fraction" but never links it to the word "coverage." The abstract leads with "0.9722 mean coverage" to a readership that will read it as conformal coverage, which would be a very different and much stronger claim. Compounding this, it is never stated what the mean is taken over: sites, records, or influence weights. Define coverage explicitly at first use in §3, and either avoid the word for the conformal notion in §1–§2 or disambiguate every occurrence.

**DS-09 — Explainability, the collection's central emphasis, is demoted by the authors and never evaluated as explanation.**

> "This supports the certificate above rather than standing as an independent method (E5)." (§1, contribution 3)
> "a supporting capability the linear head makes nearly free." (§3.8)
> "declined because feature A pulls toward positive while features B and C pull toward negative, leaving confidence below the certified bar." (§3.8)
> "feature 0 is the dominant abstention driver: its mean absolute attribution is 0.868 on answered cases but 1.722 on declined cases" (§4.6)

E5 establishes that a linear model's coefficients recover the coefficients of a linear generator, and that the arithmetic of the margin-to-answer is correct. That is a sanity check on an implementation, not an evaluation of an explanation. There is no faithfulness metric, no stability or robustness analysis of the attributions, no comparison against any alternative attribution method, no clinician assessment, and no clinical semantics — the features are literally indices 0–7 with 0–3 informative by construction, so "feature 0 is the dominant abstention driver" carries no interpretable content. For a collection whose framing is explainability "both as a transparency requirement and as an educational aid for clinicians," and one of whose editors works on XAI education, this is the axis the paper is weakest on and the one it can least afford to be weak on. The honest structural fix is either to build the explainability layer up into a contribution the collection can use (semantically named features, a clinician-facing abstention report, some evaluation of whether the explanation helps a human decide) or to acknowledge that the paper's centre of gravity is the certificate and target a methods venue.

**DS-10 — The justification for using no real data is wrong on its own terms and contradicts the paper's own §3.7.**

> "Real data cannot supply that ground truth, which is what makes it unable to validate a validity claim." (§5.5)
> "(3) It bounds the answered-set error parameter, not any single batch's realized error count, which exceeds $\alpha$ at binomial-dispersion rates even under a valid certificate." (§3.7)

A multi-site clinical cohort with observed outcomes supplies exactly what §3.9's hard-violation protocol consumes: the realized answered error at each target pool, from which the Wilson lower bound is computed. That is the same instrument the synthetic harness uses to score violations — §3.9 never touches the oracle *parameter*, only the realized count and its Wilson bound. What real data cannot supply is the true risk *parameter*, and the paper's own §3.7 clause (3) insists the certificate is about the parameter, not the count. So the sentence in §5.5 simultaneously overstates ("cannot ... validate a validity claim") and cuts against the paper's own careful distinction. This matters because it is the argument load-bearing for the paper having zero real data in a clinical collection. Replace it with the accurate and much weaker claim: real data gives lower-powered falsification, synthetic gives oracle access, and both are wanted.

**DS-11 — A cohort-level, "systematic" claim is computed over two declined cases.**

> "This case study uses a deployment with threshold $\tau^* = 0.55$, answering 200 cases and declining 2." (§4.6)
> "At the cohort level, feature 0 is the dominant abstention driver: its mean absolute attribution is 0.868 on answered cases but 1.722 on declined cases, the largest answered-to-declined gap of any feature (gap $-0.854$; gap ranking $[0, 3, 2, 1, \dots]$; top gap feature 0). Declines are systematically the cases where feature 0's pull leaves the decision contested" (§4.6)

Read as written, the declined-case mean of 1.722, the gap of $-0.854$, the full gap ranking across all eight features, and Figure 5's right panel are all computed from $n=2$. The word "systematically" cannot be supported by two points, and a gap ranking over eight features from two observations is noise. If a different and larger deployment supplied the cohort-level profile, the paper does not say so — which is itself the defect. Either state the denominator explicitly and re-run at a threshold that produces a usable declined set, or delete the cohort-level claim and Figure 5's right panel.

**DS-12 — The model-agnosticism claim is contradicted within the paper and is never tested.**

> "The gate itself is model-agnostic: the score only *ranks* cases, and the validity of the certificate never depends on the quality or calibration of the model producing that score." (§3.8)
> "We estimate the classifier's confusion rates $c_0 = P(\hat{y}=1 \mid y=0)$ and $c_1 = P(\hat{y}=1 \mid y=1)$ on $S_{\text{aux}}$ ... Certification then reweights each calibration record by class" (§3.6)
> "(i) the worst-case confusion gap $(c_1 - c_0) < 0.10$, an ill-conditioned inversion" (§3.6)

In the label-shift mode the classifier's confusion structure enters the certified statistic through the weights, and the mode refuses to run at all if the classifier is too weak. That is a direct dependence of the certificate on the model's quality, and it is the mode the paper spends most of §3.6 and all of E2 on. The bootstrap box covers *sampling* uncertainty in $(c_0,c_1)$, not the possibility that the confusion structure differs at the target site. Separately, no experiment substitutes any other head — so the agnosticism claim, restricted to the baseline mode where it is true, is still untested. Qualify the sentence to the exchangeable mode and, ideally, run one experiment with a gradient-boosted or MLP head to show the coverage price the paper says exists.

**DS-13 — The motivating empirical claim, quantified to a range, is sourced to a single unrefereed preprint two months old.**

> "certified record-level selective-risk rules overrun their budget by 9–30% under grouped deployment [@zhou2026falsesense]" (§2.4)
> "a failure recently documented for record-level selective-risk rules under grouped deployment [@zhou2026falsesense] and prevalence shift [@triage2026audit]." (§1)

`zhou2026falsesense` is `arXiv:2606.15153` (2026, two authors, no venue). `triage2026audit` is `arXiv:2605.20956`. Both are unrefereed. Combined with DS-01 — the paper runs no record-level baseline of its own — the entire premise of the manuscript rests on numbers a referee cannot check and the authors did not reproduce. This is not an objection to citing preprints; it is an objection to a paper's foundation being a preprint's unreplicated number. The same pattern recurs at `yu2026joint` (`arXiv:2606.08517`), against which §2.1 positions the paper's novelty ("Yu and Liu are closest"), and at `score2026`, `fedcrc2026`, `scrc2025`, `thermal2026audit`. Of 31 references, seven are 2025–26 arXiv preprints and they carry a disproportionate share of the positioning. Reproduce the record-level failure in E1 (see DS-01), and where a preprint's specific number is quoted, mark it as such.

**DS-14 — Missing prior art, four bodies of it, three of them clinical.**

The bibliography is well-curated within the four literatures the paper names, but it omits work that bears directly on the claims:

- **Learning to defer / human–AI deferral.** The paper's framing sentence is "routing the hard ones to a clinician [@chow1970reject; @elyaniv2010selective]" (§1) — Chow and El-Yaniv are the reject-option lineage, which abstains *without* modelling the human. There is a whole literature on deferral to an expert: Madras, Pitassi & Zemel, *Predict Responsibly: Improving Fairness and Accuracy by Learning to Defer* (NeurIPS 2018); Mozannar & Sontag, *Consistent Estimators for Learning to Defer to an Expert* (ICML 2020). Neither is cited. Most damagingly for this collection, **Dvijotham et al., *Enhancing the reliability and accuracy of AI-enabled diagnosis via complementarity-driven deferral to clinicians* (Nature Medicine, 2023)** — the flagship clinical deferral paper — is absent. A clinical-AI collection editor will notice.
- **Conformal prediction beyond exchangeability.** Barber, Candès, Ramdas & Tibshirani, *Conformal prediction beyond exchangeability* (Annals of Statistics, 2023) gives distribution-free guarantees when exchangeability fails, with a coverage gap controlled by the size of the departure. The paper's §2.2 opens by declaring exchangeability "false under multi-site clustering" and does not engage the standard reference for exactly that situation. Relatedly, Tibshirani, Barber, Candès & Ramdas, *Conformal prediction under covariate shift* (NeurIPS 2019) is the natural citation for the covariate-shift mode §6.1 declines to build, and is absent.
- **The clinical XAI critique.** Ghassemi, Oakden-Rayner & Beam, *The false hope of current approaches to explainable artificial intelligence in health care* (Lancet Digital Health, 2021) is the reference point for any claim that feature attributions help clinicians. The paper makes such a claim implicitly throughout §3.8 and cites nothing on the sceptical side. Rudin, *Stop explaining black box machine learning models for high stakes decisions and use interpretable models instead* (Nature Machine Intelligence, 2019) would in fact *support* the paper's choice of a linear head and is also absent.
- The paper's positioning survives contact with all of these — none of them certifies a cluster-level selective risk — but the omissions are conspicuous, and the Dvijotham and Ghassemi omissions are specifically conspicuous *for this collection*.

**DS-15 — No comparison against any external method.**

The only baseline anywhere is CertGate's own uncorrected mode (§4.3). §2.1–§2.3 name the nearest work in each literature — Yu & Liu [@yu2026joint], Dunn et al. [@dunn2023hierarchical], Lee et al. [@lee2025hierarchical], Si et al. [@si2024pac], Bates et al. [@bates2021rcps] — and the paper's claim is that these solve parts of the problem separately. A combination paper should show what happens when each part is deployed alone on the same cohort: hierarchical conformal at the cluster level, RCPS or LTT applied to the answered-set risk, BBSE without the uncertainty box. Without that, "Assembling them is not automatic" (§6) is an assertion. At minimum, the BBSE-without-box ablation is nearly free and would directly price contribution 2.

**DS-16 — The Shapley exactness claim omits the condition it requires.**

> "For a linear model these attributions are exact Shapley values, with no approximation or sampling [@lundberg2017shap]." (§3.8)
> "genuine Shapley values, not sampled approximations [@lundberg2017shap]" (§4.6)

$\phi_j(x)=w_j(x_j-\mu_j)$ is the exact Shapley value for a linear model under the *interventional* (marginal) value function, or under the conditional value function *when features are independent* — which is the assumption Lundberg & Lee state for their linear case. The manuscript states neither qualifier. In the generator the class signal lives on "a single normalized direction supported on the first four coordinates" (§4.1), so features 0–3 are not independent conditional on class, and a reader is entitled to ask which value function is intended. Name the variant and state the condition; one clause fixes it.

**DS-17 — A load-bearing counterexample is asserted, never shown.**

> "The natural fix — capping each site's *realized* contribution — is provably anti-conservative: a construction with 17.5% true risk certifies at $\alpha = 5\%$ under naive truncation (Appendix A.3; retained as a regression test)." (§3.3)
> "The anti-conservativity of naive realized-contribution truncation (Section 3.3) is pinned by a dedicated regression test, in which a construction with 17.5% true risk certifies at $\alpha = 5\%$ under truncation but is correctly refused under the influence-weighting scheme." (A.3)

This construction is the sole justification for the influence-weighting design — the estimand the whole certificate is built on. A.3 restates the claim but does not give the construction; there is no site configuration, no numbers, no argument. A referee cannot verify it from the manuscript, and "provably anti-conservative" is claimed on the strength of one unspecified numerical instance rather than a proof. Move the construction into Appendix A (it should take half a page: site sizes, per-site answered fractions, per-site errors, the two resulting certificates) or downgrade "provably" to "demonstrably, by the construction in Appendix A.x."

**DS-18 — The deployment rule is stated two different ways.**

> "We deploy the maximum-coverage threshold in the certified prefix." (§3.5)
> "The modes run as alternatives, each at full $\delta$, and we deploy the most conservative certified threshold." (§3.6, "Combination")

Maximum coverage means the least conservative threshold (lowest $\tau$, most cases answered). These are opposite selection rules. If §3.6 means "most conservative *across modes*" and §3.5 means "maximum coverage *within* a mode's prefix," say so — as written the reader cannot tell which threshold is deployed, and E5 ($\tau^*=0.55$, the grid minimum) versus E6 ($\tau^*=0.77$) does not disambiguate it.

**DS-19 — Label shift is tested at exactly one magnitude, and that magnitude produces a 95.5% decline rate.**

> "We shift site-level prevalence from the source value of 0.095 up to a target base rate of 0.22" (§4.3)
> "BBSE declines the remaining 95.5% of draws (decline rate 0.955)" (§4.3)

One point on one axis. The reader cannot tell whether BBSE certifies usefully at a 1.3× shift and collapses at 2.3×, or declines nearly everywhere at every magnitude. That distinction decides whether contribution 2 describes a working correction or a shift detector. Contribution 2's phrasing — "keeps the guarantee valid under outcome-prevalence shift" — reads as the former; the single data point supports only the latter. A sweep over target prevalence in, say, $\{0.10, 0.13, 0.16, 0.19, 0.22\}$ reporting certify rate and coverage is the obvious missing experiment and would materially strengthen the paper.

**DS-20 — The stated confidence-interval protocol is applied selectively.**

> "Because every rate below is a proportion over $R = 200$ independent draws, we accompany the primary rates with exact (Clopper–Pearson) 95% confidence intervals." (§4.1)

Intervals appear on three numbers: E1's 0.01, E2's 0.485 and 0.0-joint, E3's 0.83. They do not appear on: E2's conditional 0/9 (see DS-03), E2's decline rate 0.955, any of Table 1's four observed exceedances, any of Table 4's twelve certify rates — including the 0.3 at 300 sites, which is the single most uncertain and most quoted number in E4 — or any coverage mean anywhere. Either apply the protocol uniformly or narrow the stated scope of the sentence in §4.1.

**DS-21 — E3 does not say which assumption mode produced the violating certificates.**

> "Given a genuinely poisonous shift, the $\alpha = 0.10$ certificate certifies all 200 draws and hard-violates 83% of them" (§4.4)

The paper ships two modes. E2 reports both separately and by name. E3 reports "the certificate," singular. If the BBSE mode also certified all 200 draws under concept shift, that is a substantive and interesting result — it would show the decline machinery does not incidentally catch concept shift — and it should be stated. If only the baseline was run, say so. As written the negative control's scope is ambiguous.

**DS-22 — Scope fit: the manuscript is a distribution-free inference paper, and it says so itself.**

> "The same certificate shape appears in power-grid contingency screening [@thermal2026audit], so it is not specific to medicine." (§2.4)
> "Each record carries $d = 8$ features; the class signal lives on a single normalized direction supported on the first four coordinates ... so features 0–3 are informative and features 4–7 are noise." (§4.1)
> "Applying CertGate to a real multi-site cohort is ongoing work." (§5.5)

The collection is *Intelligent Medicine: ML and Explainable AI for Next-Generation Healthcare*, with explainability as its central emphasis. This manuscript contains: no patient data, no clinical variable, no clinical outcome, no clinician, no care pathway, no institutional deployment, and — by the authors' own sentence — no domain specificity. The clinical content is the framing of §1 and the two multi-site-validation citations in §2.4. Against that, the paper does genuinely target the multi-site clinical deployment setting, it does cite TRIPOD-Cluster and IECV practice appropriately, uncertainty quantification and OOD robustness are explicitly in the collection's encouraged list, and explainable abstention is a declared contribution. My honest read: it is on the boundary and lands on the wrong side of it as currently written, mainly because of DS-09 (explainability demoted and unevaluated) and the absence of any clinical instantiation. A real or semi-synthetic clinical cohort with named clinical features, plus an explainability layer built up rather than down, would move it decisively inside scope.

---

## Minor points

**DS-23 — The abstract uses three terms of art it does not define.** "at $\alpha=0.10$ the gate certifies all 200 calibration draws at 0.9722 mean coverage with a hard-violation rate of 0.01 under a 0.05 budget" (Abstract). "Hard-violation rate" is the paper's own coinage, defined only in §3.9. "Coverage" is ambiguous (DS-08). "Calibration draws" is undefined. At 241 words the abstract is comfortably within Springer's limit and has room to define them.

**DS-24 — The betting formula contains an undefined symbol and an unused one.** "$\lambda_t = \min\!\left(\sqrt{\frac{2\ln(1/\delta)}{\hat{\sigma}^2_{t-1}\, n}},\; \frac{0.9}{1-\alpha}\right)$, with a variance floor of $10^{-8}$ and the running mean and variance $(\hat{\mu}, \hat{\sigma}^2)$ initialized at $(0.5, 0.25)$" (§3.4). $n$ is never defined — is it $n_{\text{cal}}$, or the running index $t$? The two give different bets and the standard WSR predictable plug-in uses a growing index. And $\hat{\mu}$ is initialized but appears in no displayed equation; presumably it feeds $\hat\sigma^2_{t-1}$, but that is left to the reader.

**DS-25 — "base" is undefined in the attribution identity.** "$\text{logit}(\hat{p}(x)) = \text{base} + \sum_j \phi_j$" (§3.8). Presumably the intercept plus $\sum_j w_j\mu_j$; say so, since the exactness of the decomposition is the claim being made.

**DS-26 — An implementation flag leaks into the manuscript.** "Every experiment runs in mode FULL under protocol seed 20260721" (§4.1). "Mode FULL" is undefined and means nothing to a reader; it appears to be a harness setting. Contrast with "--quick", which is not mentioned — so the reader cannot tell what FULL is the alternative to.

**DS-27 — Four unresolvable code references.** "the specification frozen in `data.py`" (§4.1); "the implementation includes a `from_raw` loader and a worked example" (§5.5); "a pinned environment (`requirements.txt`)" and "`python -m experiments.run_synthetic`" (A.3). All point into a repository whose URL is a placeholder (DS-07). A manuscript should be readable without the artifact; §4.1 in particular should state the generator specification in prose (it mostly does) rather than deferring to a filename.

**DS-28 — A test-suite pass count is reported as a result.** "The test suite is 69/69 green." (A.3). This is not a scientific finding, it is unverifiable at screen, and it will date badly. Reproducibility is already covered by the pinned environment, the seeding rule and the single-command claim.

**DS-29 — "Near-tripling" describes a 2.3× change.** "from the source value of 0.095 up to a target base rate of 0.22 — a near-tripling of outcome frequency" (§4.3). $0.22/0.095 = 2.32$. "More than a doubling" is accurate and loses nothing.

**DS-30 — Table 1's reference column is not reproducible from the paper.** "| Answered-set size bin | Pools ($n$) | Observed exceedance | Binomial reference |" with values 0.4063 / 0.4689 / 0.4820 / 0.4915 (Table 1). The text describes it as "the exceedance a perfectly valid boundary-case certificate would show purely from label dispersion" (§4.2), but neither the caption nor the body states the batch size or success probability used per bin, so a reader cannot regenerate the column. The caption also does not stand alone — it must, per Springer style.

**DS-31 — Table 4's coverage column is non-monotone and uncommented.** At $\alpha=0.10$: 0.9304 (150) → 0.9715 (208) → 0.9601 (300) → 0.9621 (400). Coverage rises, falls, then rises as sites are added. §4.5 quotes all four numbers and offers no explanation; the natural reader question — is this Monte-Carlo noise or structure? — is unanswered, and without CIs (DS-20) it is unanswerable.

**DS-32 — Three citekeys disagree with their own entries' years and venues.** `ifac2025abstainexplain` resolves to `year = {2024}`, ECML PKDD 2024 — the key says 2025 and "ifac", which is a different organisation entirely. `l2lore2025` resolves to `year = {2024}`, DS-LB 2024. `angelopoulos2021ltt` resolves to `year = {2025}`, *Annals of Applied Statistics*. Harmless to rendering, but they will confuse anyone maintaining the file and they suggest the keys were minted before the entries were verified.

**DS-33 — The bibliography carries an internal working comment.** `references.bib` lines 1–3: "% CertGate manuscript references — every entry verified against its primary source on 2026-07-24 ... see paper/TODO.md for the one unverified candidate, scireports2026deferral, which is deliberately NOT in this file". A submitted `.bib` should not point at the authors' to-do file or name a citation they considered and rejected. Strip it.

**DS-34 — Two entries advertise other authors' submission status.** `fedcrc2026`: `note = {arXiv:2606.20115; submitted to DeCaF Workshop, MICCAI 2026}`. `thermal2026audit`: `note = {arXiv:2607.13221; submitted to IEEE Transactions on Power Systems}`. These notes will render in the reference list. Reporting where someone else's unpublished work is under review is not standard practice and is discourteous to those authors.

**DS-35 — Bibliography completeness is inconsistent.** Most entries carry a DOI or an arXiv eprint. `podkopaev2021labelshift` (PMLR v161, pages given) has neither. `elyaniv2010selective` (JMLR 11) has neither. `geifman2017selective` has an eprint but no pages. `lee2025hierarchical` has a DOI but no volume or pages. Bring them to a common standard.

**DS-36 — Unit slip in a percentage comparison.** "the ~0.4-point gap between the BBSE-implied and oracle fractions" (§4.7). The gap is $0.0630-0.0591=0.0039$, i.e. 0.39 *percentage points*. "Point" is ambiguous next to fractions expressed on $[0,1]$.

**DS-37 — Register: the paper repeatedly attests to its own honesty.** "We do not paper over this." (§3.6) · "Demonstrating the failure openly is validation rigor" (§4.4) · "the reading is honest" (§4.7) · "Its posture throughout is disclosure" (§6) · plus "disclosed"/"disclose" at §1, §3.6, §3.7 and §6.1. Eight instances of the motif. The paper's disclosures are in fact good — clauses (1)–(5) of §3.7 are exactly the sort of scoping referees rarely see — which is precisely why announcing them is unnecessary. Let the disclosures do the work and cut the commentary about them.

**DS-38 — Register: the paper argues with its referees inside the text.** "For any reader tempted to call $\alpha=0.10$ a weak guarantee: the operative rung is a property of the available cluster count, not of the method" (§5.2). "That is not a defect; it is what a selective gate on a low-prevalence task should do." (§4.7). "A negative control that cannot fail proves nothing." (§4.4). Pre-emptive rebuttal reads as defensiveness and invites the objection it deflects. State the finding; let §5 do the interpreting without addressing the sceptic directly.

**DS-39 — A cost/benefit sentence reads backwards and conflicts with §5.3.** "A stronger black-box head can be substituted at a visible cost in coverage" (§3.8) versus "the gate would then price its selective quality visibly, as a change in certified coverage" (§5.3). §3.8 says substituting a stronger head *costs* coverage, which is the opposite of what a stronger head should do; §5.3 says it *changes* coverage, which is neutral and correct. Presumably §3.8 means the linear head costs coverage relative to a black box. Rewrite.

**DS-40 — Three frozen constants are stated without justification.** "the worst-case confusion gap $(c_1 - c_0) < 0.10$"; "fewer than 2,000 valid resamples within 4,000 attempts" (§3.6); the influence cap "$M = 100$" (§3.3). §3.2 explains why constants are frozen (a pre-registration substitute — a good device) but not why *these* values. $M=100$ in particular sets the estimand, since it decides how much a 5,000-record site is downweighted relative to a 100-record one; a sensitivity check on $M$ would be worth more than most of E5.

**DS-41 — An unsupported claim about what clinicians and auditors want.** "The promise attached to such a gate is a bound on the error rate among the cases it chose to answer, holding with high confidence — what a clinician weighs before trusting an automated triage, and what an auditor asks to see documented." (§1). Two empirical claims about two professional audiences, with no citation and no evidence. In a clinical collection this sentence will be read closely. Either cite work on clinician trust in automated triage and on regulatory audit expectations, or hedge it to "the kind of assurance a clinical governance process is likely to ask for."

**DS-42 — The "problem setting" is the simulator.** §3.1 opens "We consider multi-site clinical data in which on the order of two hundred collection sites each contribute between 20 and 5,000 records, the outcome prevalence is roughly 9–10%" — which is, parameter for parameter, §4.1's generator (208 sites, clipped to [20, 5000], base prevalence 0.095). Presenting the generator's settings as the general problem setting makes the method's scope circular. Given DS-04, the fix is the same: source the setting from real cohorts, then show the generator matches it.

**DS-43 — Section ordering is non-standard.** Current order: Conclusion → Appendix A → Acknowledgements → declarations → Figures → Tables → References. Springer expects the declarations block after the main text and appendices and immediately before the references, with figures and tables either placed in text or supplied after the reference list per the journal's instructions. As it stands the Figures and Tables sections sit between "Competing interests" and "References," which will need rearranging at production regardless.

**DS-44 — The title promises clinical risk models; the paper has none.** "CertGate: finite-sample certified selective prediction for multi-site clinical risk models..." Given DS-22, either the paper acquires a clinical instantiation or the title should say "for multi-site clustered risk models" and let §1 make the clinical motivation.

**DS-45 — The stated reason for keeping neutral atoms is not the right one.** "Sites with no answered-eligible records enter as *neutral* atoms $Z_c = \alpha$ rather than being dropped; dropping them would redefine the site population post hoc and quietly change the estimand." (§3.3). A site with $a_c=0$ contributes $g_c a_c e_c = 0$ to the numerator of $R_M$ and $g_c a_c = 0$ to its denominator, so dropping such sites leaves $R_M$ unchanged; what changes is $n$, hence the bet sequence and the power of the test, and the definition of the site population for the *feasibility gate*. The design choice looks right; the justification given for it does not match the estimand as defined.

**DS-46 — The explainability case study uses a barely-selective operating point with no rationale.** E5 runs at $\tau^*=0.55$ (the minimum of the stated grid $[0.55, 0.99]$), answering 200 and declining 2; E6 runs at $\tau^*=0.77$. Neither section explains why the abstention-explanation study — the one whose entire subject is declined cases — is conducted at the threshold that produces almost no declines. See DS-11.

---

## Questions to authors

**DS-47.** Over what index set is $R_M = \sum_c g_c a_c e_c / \sum_c g_c a_c$ defined — the realized calibration sites, the target site's records, or the population of sites? And is the certified statement a bound on the risk at a single new site, or on the population-weighted average over sites? Please answer both parts explicitly; §3.1, §3.7(1), §5.1 and A.1(ii) can be read either way (DS-02).

**DS-48.** E6 is run on the unshifted cohort, yet Table 3 reports $\hat{\rho} = 0.830$ — a 17% departure from the value 1 that no shift should imply. What accounts for it? Is it finite-sample noise in the confusion estimates, a systematic bias in the BBSE inversion at 9.5% prevalence, or an artefact of computing $\rho$ on the answered subset rather than the full pool? If it is bias, does the same bias operate in E2, and in which direction relative to safety?

**DS-49.** §3.6 states "The modes run as alternatives, each at full $\delta$," and that the combined statement reads "if *either* tagged assumption holds." For a deployer who does not know which assumption holds and therefore reads the disjunction, is the error probability $\delta$ or $2\delta$? Please give the formal statement for the combined output, not just for each mode conditional on its own assumption.

**DS-50.** How many declined cases underlie the cohort-level attribution profile in §4.6 and the right panel of Figure 5? If it is the two declines of the $\tau^*=0.55$ deployment, on what basis is "systematically" used, and what is the sampling variability of the reported gap ranking $[0,3,2,1,\dots]$?

**DS-51.** E6 reports mean answered error per size *bin* (0.0294, 0.0406, 0.0348). What is the distribution across the 40 individual target sites, and how many of them have realized answered error above $\alpha = 0.10$? This is the number a hospital would ask for, and it is the number that would distinguish a per-site guarantee from a marginal one (DS-02).

**DS-52.** What is "mean answered-set coverage 0.9722" the mean of — an unweighted average of per-site answered fractions, a record-weighted average, or an influence-weighted one? Given that the certified estimand is influence-weighted and site sizes span 20 to 5,000, the three differ materially.

**DS-53.** Was any real or semi-synthetic multi-site cohort attempted before the synthetic-only design was settled on? §5.5 says "the implementation includes a `from_raw` loader and a worked example," which suggests the pipeline is ready. What specifically blocked a real-data run — data access, site count, outcome availability?

**DS-54.** At what target prevalence does the BBSE mode's certify rate become non-trivial? Is there any shift magnitude at which it both certifies a majority of draws and does not violate, or is 0.095 → 0.22 already past the point where the mode can do anything but decline (DS-19)?

---

## Confidential comments to the editor

**DS-55.** **Would I have sent it out? Yes — but only after the authors fix the submission mechanics, and only to referees who can check a martingale argument.** The mechanics are non-negotiable: no figures in the file (DS-05), no reference list (DS-06), three declarations reading `[TO BE COMPLETED]` and a dead data-availability URL (DS-07). Our office would bounce it for those alone, and correctly. Beyond that, my genuine worry is refereeing capacity. Appendix A.1 and A.2 are the load-bearing parts of this paper, and checking them requires someone comfortable with predictable-plugin betting supermartingales, Ville's inequality, and the affine-in-$\rho$ argument. Neither collection editor's stated expertise (performance evaluation / Green AI / philosophy of AI; AI in healthcare / process mining / medical informatics / XAI education) covers that, and our clinical-AI referee pool largely will not either. If this goes out, at least one referee must be recruited from distribution-free UQ, not from the collection's usual list. If we cannot recruit that person, we will accept or reject this paper on its prose, which would be the worst outcome available.

**DS-56.** **My sharpest doubt is that the paper's premise is borrowed and its headline result is $n=9$.** DS-01 and DS-03 together are what I actually think is wrong here. The entire reason to build a cluster-level certificate is that record-level certificates fail under grouping — and the authors demonstrate that exactly nowhere, citing instead `arXiv:2606.15153` for a "9–30%" overrun they did not reproduce. Meanwhile the label-shift result that occupies the second contribution slot and a third of the abstract comes down to nine certified draws with the confidence interval conspicuously omitted from that one number while appearing on every other. I do not think this is deliberate — the paper is careful and self-critical elsewhere, and its scoping clauses in §3.7 are better than most submissions manage — but the effect is that the two strongest-sounding sentences in the abstract are the two least supported by the experiments.

**DS-57.** **A suspicion I could not nail down.** The BBSE mode declines 95.5% of draws under the one shift tested and issues no certificate at all at $\alpha=0.05$ in either mode. I cannot tell from the manuscript whether the decline behaviour reflects a correctly calibrated refusal — the story the paper tells — or simply a mode that is underpowered at 83 calibration clusters once the $\delta$ budget is split in half and the weight interval is widened by a Bonferroni box at $\delta_{\text{conf}}/3$. Those look identical from the outside and have opposite implications: the first is the paper's contribution, the second is a symptom. The single-magnitude design (DS-19) is what makes them indistinguishable, and I would press hard on DS-54 in any revision.

**DS-58.** **On collection fit I am more negative than my recommendation implies.** Read the sentence at §2.4 — "The same certificate shape appears in power-grid contingency screening, so it is not specific to medicine" — next to the collection's framing, and it is close to self-disqualifying. The paper is a distribution-free inference contribution with a clinical motivation and no clinical content, and it says so. Explainability, which is the collection's stated centre of gravity, is contribution 3 of 4 and is described by the authors themselves as "nearly free" and as something that "supports the certificate above rather than standing as an independent method." Striani in particular will read that and ask why it is in his collection. If the authors want the collection, the revision that matters is not statistical — it is a real or semi-synthetic cohort with named clinical features and an abstention report a clinician could actually read. If they do not want to do that, they should be told candidly that this paper is stronger at a methods venue, and that we would be doing them no favours by publishing it where its main contribution is unrefereeable.

**DS-59.** **Flag for the editorial office: seven of thirty-one references are 2025–26 arXiv preprints, and they carry disproportionate weight.** `zhou2026falsesense`, `triage2026audit`, `yu2026joint`, `score2026`, `scrc2025`, `fedcrc2026`, `thermal2026audit`. These supply the paper's motivating failure claim (DS-13), its "closest work" positioning (§2.1), and its claim to cross-domain generality (§2.4). I cannot verify at screen that these preprints exist, are correctly attributed, or say what the draft says they say. Please have the office spot-check the three that matter — `zhou2026falsesense`, `triage2026audit`, `yu2026joint` — before the paper is assigned. The bibliography also still carries the authors' own working comment pointing at `paper/TODO.md` and naming a rejected candidate citation (DS-33); that should be stripped before anything is circulated.

**DS-60.** **One thing I want protected in revision.** This draft is genuinely restrained: I searched it for "novel", "first to", "state-of-the-art", "unprecedented" and "breakthrough" and got zero hits, which is rare. The hedging in §3.9 ("evidences the *absence of gross violations at the tested power*, rather than confirming validity") and the five-clause scoping in §3.7 are exactly right and should survive revision untouched. My register findings (DS-37, DS-38) are about the *opposite* failure — the paper announcing its own honesty and pre-arguing with referees — and should not be read as an instruction to hedge less. If a revision responds to DS-01 through DS-22 by adding confidence rather than experiments, that would be worse than the current draft.

---

## Recommendation

**Major revision.**

The statistical core is serious work, carefully executed and, so far as I could check from the manuscript alone, arithmetically sound throughout. But the manuscript is not currently in submittable condition — figures absent, reference list absent, three declarations unfilled, data-availability URL a placeholder — and beyond the mechanics it has a structural evidence problem: the site-as-unit premise that justifies the whole construction is imported from an unrefereed preprint and never demonstrated here (DS-01), the label-shift headline rests on nine certified draws with its interval suppressed (DS-03), the guarantee is stated per-site while the test certifies a population average (DS-02), and no external method is compared against anywhere (DS-15). Against the venue card the fit is the harder problem: *Discover Computing*'s "Intelligent Medicine" collection puts explainability at the centre and is framed clinically, and this paper contains no patient data, no clinical variable, no clinician, features named 0 through 7, an explainability layer the authors themselves call "nearly free," and an explicit statement that the method "is not specific to medicine." A revision that (i) runs the record-level ablation, (ii) sweeps the shift magnitude, (iii) builds the explainability contribution up into something a clinician could use on a cohort with clinical semantics, and (iv) completes the submission apparatus would be a strong candidate for this collection. Without at least (i), (iii) and (iv), it is a methods paper in the wrong room, and I would rather tell the authors that now than after three referees have spent a month on it.
