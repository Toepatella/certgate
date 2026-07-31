# Referee 5 — forensic report

**Manuscript:** *CertGate: finite-sample certified selective prediction for multi-site clinical risk models, with label-shift robustness and explainable abstention*
**Venue:** *Discover Computing*, Collection "Intelligent Medicine: ML and Explainable AI for Next-Generation Healthcare"
**Referee role:** forensic reader (numerical reconciliation, guarantee parsing, citation characterization, register audit)
**Materials read:** `paper/draft.md`, `paper/references.bib`. No figure image files exist in `paper/` — see R5-15.

---

## Summary

The paper proposes CertGate, a wrapper around a deployed binary clinical risk model that decides, per case, whether to answer or abstain, and issues a "certificate" that the error rate among answered cases is at most α with confidence 1−δ. The distinguishing move is that the unit of statistical independence is the *site*, not the record: each site is compressed into a single bounded atom Z_c built from an influence-capped weight g_c = min(n_c, 100), and the atoms are fed to a Waudby-Smith–Ramdas betting martingale whose crossing rule inherits finite-sample level δ from Ville's inequality. A threshold is selected by a fixed-sequence walk down a 23-point grid ordered on a disjoint auxiliary split. A second assumption mode handles outcome-prevalence shift by BBSE confusion-matrix inversion, wraps the estimated weights in a Bonferroni percentile bootstrap box over sites, and certifies at both endpoints of the resulting weight interval, splitting δ into 0.025 for the box and 0.025 for the bet. Because the deployed head is L2 logistic regression, each answer and each abstention carries an additive attribution decomposition, and abstentions are reported with a margin-to-answer. Evidence is six experiments on a synthetic 208-site cohort: in-distribution validity, a label-shift stress test, a concept-shift negative control, a site-count sweep, an explainability case study, and a per-site coverage/composition study.

My assessment. The arithmetic is, with two exceptions, unusually clean — I reconciled the abstract against the body, the body against all four tables and all six figure captions, and recomputed the internal consistency of Table 1 (bin exceedances reproduce the 0.05 overall rate exactly), Table 2 (site counts sum to 40), Table 3 (all three fractions reproduce from their counts), the 9/191 certify/decline split, the Clopper–Pearson intervals, and both declined-case logit margins in E5. Those all hold. The problems are not arithmetic; they are semantic. The central one is that the object the mathematics certifies — the mean of a per-site atom over the site population, i.e. an influence-weighted average risk *across* sites — is repeatedly sold as a promise *at* a target site, and the manuscript never confronts the difference. Around that sit a self-contradicting disclosure discipline (the paper says the asymptotic caveat travels with every guarantee statement; the abstract and title are guarantee statements and it does not travel there), one discussion sentence that reverses the sign of its own Results number, a BBSE headline that rests on nine certified draws whose confidence interval the paper's own protocol requires and does not supply, an evidence base with no comparator procedure anywhere, and six figures that do not exist. The register is genuinely restrained — I found no novelty-spam and no "first"-claims, which I credit — but a handful of unhedged sentences carry load the experiments cannot bear. This is fixable work, not broken work, but it is not fixable by copy-editing.

---

## Major points

### R5-01 — The certified estimand is a cross-site average; the guarantee is stated as a per-site promise. These are different statements and the paper never reconciles them.

> §3.1: "with probability at least $1-\delta$ over the draw of calibration sites, the influence-weighted answered-set risk — the parameter $R_M$ defined in Section 3.3 — **at a new target site** is at most $\alpha$"

> §3.3: "$R_M = \frac{\sum_c g_c\, a_c\, e_c}{\sum_c g_c\, a_c}$, where $a_c$ is the answered fraction and $e_c$ the answered-set error rate at site $c$."

> §3.7, clause (1): "It is scoped per target site."

> §5.1: "a bound on the influence-weighted answered-set error *parameter* $R_M$ at a target site"

$R_M$ as written in §3.3 is a weighted average **over sites** $c$. The test in §3.4 tests $\mathbb{E}[Z] \le \alpha$, and by the paper's own bridge identity $Z_c - \alpha = g_c a_c (e_c-\alpha)/M$, that expectation is the influence-weighted mean of $(e_c - \alpha)$ over the site population. A bound on a population mean does not bound any individual site: a site with $e_c = 0.4$ is entirely compatible with $\mathbb{E}[Z] \le \alpha$ at $\alpha = 0.10$, since other sites offset it. So clause (1), "scoped per target site," asserts something the machinery does not deliver.

The alternative reading makes it worse, not better. If "$R_M$ at a new target site" means $R_M$ evaluated on the single target site, then $g_c$ and $a_c$ cancel and $R_M = e_c$ — the influence weighting, which the whole of §3.3 exists to justify, becomes irrelevant to the promised quantity and is only a device inside the calibration test. Either way the tested object and the promised object differ.

This is not academic. The generator deliberately injects site heterogeneity ($u_c \sim \mathcal{N}(0, 0.5^2)$ on the outcome log-odds, §4.1), which is exactly the regime in which a population mean and a per-site risk diverge. The manuscript reports no per-site distribution of answered risk anywhere — Table 2 gives *bin means* over 40 sites at one threshold, not a per-site maximum or quantile — so a reader cannot check how far apart the two readings are in the authors' own data.

**Fix.** Either (a) restate the guarantee honestly as a bound on the influence-weighted site-population mean answered risk, and delete "per target site" from §3.1, §3.7(1) and §5.1; or (b) prove and validate a genuinely site-conditional statement. If (a), the abstract sentence "certifies … that the error rate among answered cases stays at or below α" also needs the qualification, and a per-site risk histogram from E6 should be added so readers can see the spread the mean is hiding.

### R5-02 — Two incompatible probability spaces underwrite the guarantee; the supermartingale step needs an assumption on calibration sites that is never stated, and §6.1 admits it may fail.

> §3.3: "The estimand is design-conditional: target features are treated as observed, and **it is the label randomness that carries the expectation**."

> §4.1: "the certificate's $1-\delta$ event is **over the draw of calibration sites**."

> A.1(ii): "Because the estimand is design-conditional, the answered fractions $a_c$ and weights $g_c$ are fixed functions of observed features, so the denominator … is non-random"

> A.1(iii): "under $H_0$, $\mathbb{E}[\,1 + \lambda_t(\alpha - Z_t) \mid \mathcal{F}_{t-1}\,] \le 1$"

A.1(ii) needs features (hence sites) held fixed. A.1(iii) needs $\mathbb{E}[Z_t \mid \mathcal{F}_{t-1}] \ge \alpha$ under $H_0$ — and $H_0$ is stated as a statement about the *aggregate* mean, $\mathbb{E}[Z] \ge \alpha$. With sites fixed and only labels random, the aggregate being ≥ α does not make each site's conditional mean ≥ α; a calibration sequence that begins with several low-risk sites drives the wealth up under a true null, and $K_t$ is not a supermartingale. The step goes through only if the calibration sites are i.i.d. (or at least exchangeable) draws from the site population — which is precisely the assumption that A.1(ii) discards. The manuscript never states an i.i.d./exchangeability assumption on the *calibration* sites; §3.6's baseline tag covers only the *target* site ("The target site is assumed exchangeable with the calibration sites").

Worse, §6.1 concedes the assumption may fail:

> §6.1: "*Temporal common-shock correlation is not modeled.* Sites sharing the collection window may be correlated through common temporal shocks … The site-as-unit analysis treats sites as the independent unit and does not model residual cross-site dependence induced by shared time."

Framed as a modelling omission, this is in fact a threat to the finite-sample level of the test: cross-site dependence breaks the martingale property that Ville's inequality is applied to. The limitation should say so.

**Fix.** State the calibration-site sampling assumption explicitly as an assumption of Theorem/A.1, reconcile it with the design-conditional framing (or drop the latter), and relabel the temporal-correlation limitation as a validity caveat rather than a modelling one.

### R5-03 — The paper asserts that the asymptotic caveat travels with every guarantee statement. It does not travel to the abstract or the title.

> §3.6: "We disclose plainly that this percentile bootstrap box is the single asymptotic step in an otherwise finite-sample chain, and **every guarantee statement carries that caveat**."

> §3.7, clause (5): "The BBSE percentile bootstrap box is the single asymptotic link … **disclosed wherever the guarantee is stated**"

> §6.1: "This is disclosed wherever the guarantee is stated"

Now the abstract, which is a guarantee statement:

> Abstract: "certifies, with **finite-sample** confidence $1-\delta$, that the error rate among answered cases stays at or below $\alpha$. The method rests on two moves: an influence-weighted answered-set risk certified by a betting martingale over sites (a distribution-free, finite-sample sequential test), and a label-shift mode built on black-box shift estimation that **carries its own estimation uncertainty inside the guarantee** rather than assuming the correction is exact."

And the title:

> "CertGate: **finite-sample** certified selective prediction for multi-site clinical risk models, **with label-shift robustness** and explainable abstention"

The abstract states the finite-sample property twice, describes the label-shift mode's uncertainty handling in one sentence, and never says the label-shift mode's confidence budget rests on an asymptotic percentile bootstrap. The title binds "finite-sample" and "label-shift robustness" in one noun phrase. A reader who reads only the abstract and title — which is most readers — acquires exactly the belief §3.6 promises they will not acquire. This is a self-refuting disclosure claim and the easiest major finding in the paper to fix.

**Fix.** Add to the abstract, e.g., "(the label-shift mode's weight interval is bootstrap-based and is the one asymptotic step)", and either qualify the title or drop "finite-sample" from it.

### R5-04 — The gap between what is certified and what an abstract-only reader will believe is certified.

Task-2 deliverable. Parsing §3.7 clause by clause:

**(a) What is actually certified.**

1. **Quantity.** The influence-weighted answered-set error *parameter* — an expectation, with site-level influence caps at M = 100 — not any batch's realized error count (§3.7(3)), and (per R5-01, as the mathematics stands) a mean over the site population rather than a per-site value.
2. **Probability.** One event of probability ≥ 1−δ, over the draw of calibration sites, **shared by every site certified from that draw** (§3.7(2)). Certify 50 hospitals from one calibration draw and you have one 95% event, not fifty.
3. **Conditionality.** Valid only *if* one explicitly named assumption holds — exchangeability, or label-shift-only with $P(x\mid y)$ invariant (§3.6). No claim is made when neither holds.
4. **Exclusion.** Concept shift is out of scope and the certificate "can be confidently wrong" under it (§3.7(4)).
5. **Chain.** Finite-sample in the baseline mode; in the label-shift mode, δ splits 0.025/0.025 and the 0.025 box coverage is asymptotic (§3.7(5)).
6. **Operating point.** Only α = 0.10 is achievable at the 208-site scale; α = 0.05 certifies nothing (§4.2, §4.5).
7. **Evidence.** All of it synthetic; validity is checked against a deliberately conservative Wilson-bound criterion that "evidences the *absence of gross violations at the tested power*" (§3.9), not validity.

**(b) What a hurried, sympathetic reader believes after abstract + introduction.**

1. "If I deploy this at my hospital, at most 10% of the cases it answers will be wrong, with 95% confidence." Created by: *"certifies, with finite-sample confidence $1-\delta$, that the error rate among answered cases stays at or below $\alpha$"* (abstract). Nothing in that sentence signals parameter-not-count, population-mean-not-site, or shared-event.
2. "The whole method is finite-sample, including under label shift." Created by the title and by the abstract's two uses of "finite-sample" (R5-03).
3. "Each certified site gets its own 95% guarantee." Nothing in the abstract or introduction contradicts this; §3.7(2) states the correction once and it is never repeated in §5 or §6.
4. "Under label shift the corrected mode is safe." Created by *"the uncorrected baseline certifies and violates in 48.5% of draws, while the corrected mode never does"* (abstract). See R5-06: "never does" is measured over nine certified draws.
5. "The system was validated and it passed." Created by *"a hard-violation rate of 0.01 under a 0.05 budget"* (abstract), with the §3.9 caveat that this is a low-power screen appearing exactly once and never again.
6. "0.05 is available if you have about 300 sites." Created by *"a site-count frontier shows the stricter $\alpha=0.05$ budget needs roughly 300+ sites"* (abstract). At 300 the certify rate is 0.3 (Table 4). See R5-22.

The gap is items 1–5. Item 1 is the one I would insist on: the abstract's guarantee sentence carries none of the five §3.7 clauses, and §5.1 — which exists to restate the guarantee precisely — restores only three of them.

**Fix.** Rewrite the abstract's guarantee sentence to carry at minimum: the parameter-vs-count distinction, the shared-event scope, and the assumption tag; and repeat the shared-event clause in §5.1 and §6.

### R5-05 — §5.1 describes E1's own numbers backwards.

> §5.1: "It is not a bound on a batch's realized error *count* — E1 shows realized exceedance **rising toward its binomial reference** (0.0551 against 0.4915 in the largest size bin) even while the hard-violation rate stays at 0.01"

> §4.2: "Across every size bin the observed exceedance sits **far below the reference** (for example 0.0189 observed against 0.4820 expected in the 100–300 bin, and 0.0551 against 0.4915 in the largest bin), confirming that answered pools are not sitting at the $\alpha$ boundary but well inside it."

The same pair of numbers, 0.0551 and 0.4915, is used in §4.2 to argue "far below" and in §5.1 to argue "rising toward". 0.0551 is one ninth of 0.4915. Nor is the observed series rising: across Table 1's bins it runs 0.0000, 0.1111, 0.0189, 0.0551 — non-monotone in either reading of "rising".

The rhetorical work §5.1 is trying to do is real (a parameter bound is not a count bound), but E1 is the wrong evidence for it, because E1's answered pools are nowhere near the α boundary. As written, the sentence claims the manuscript demonstrated frequent realized-count exceedance. It demonstrated the opposite: 10 pools out of 200.

**Fix.** Delete the E1 appeal from §5.1 and make the parameter/count point analytically (as §3.9 already does), or run a boundary-case demonstration in which the realized exceedance actually approaches the binomial reference.

### R5-06 — The BBSE headline ("never certifies and violates") is measured on nine opportunities, and the one confidence interval that would show this is the one the paper omits.

> §4.3: "the joint event that matters operationally — a certificate issued *and* hard-violating — occurs 0 times in 200 draws (exact 95% CI $[0, 0.018]$ …); conditioning on the 9 draws that did certify ($n_{\text{certified}} = 9$), **the hard-violation rate among them is 0.0**."

> §4.1: "Because every rate below is a proportion over $R = 200$ independent draws, we accompany the primary rates with exact (Clopper–Pearson) 95% confidence intervals."

Every other rate in §4.2–§4.5 carries a Clopper–Pearson interval. The conditional rate — 0 of 9 — does not. Its exact 95% upper bound is ≈ 0.336. That is, the manuscript's own data are consistent with BBSE hard-violating up to roughly one certificate in three, *conditional on issuing one*. That interval is the single most decision-relevant number for a clinician deciding whether to trust a BBSE-mode certificate, and it is the only rate in the results section without an interval.

The joint-event interval [0, 0.018] is not a substitute: it is small mainly because BBSE declined 191/200 draws. A gate that declines everything achieves a joint rate of 0 trivially. The paper is aware of this — the two-number protocol of §3.9 exists precisely to prevent it — but then reports the conditional number without its uncertainty.

**Fix.** Report the Clopper–Pearson interval on 0/9 and say plainly in §4.3 and in the abstract that the conditional safety claim is low-powered. Better: increase R for E2, or report a shifted-target regime in which BBSE certifies often enough to be tested.

### R5-07 — §4.1's blanket statement about confidence intervals is false for two of the rates that follow.

> §4.1: "Because **every rate below is a proportion over $R = 200$ independent draws**, we accompany the primary rates with exact (Clopper–Pearson) 95% confidence intervals."

Two counterexamples appear within two pages. Table 1's per-bin exceedances are proportions over 2, 18, 53 and 127 pools, not 200. The BBSE conditional hard-violation rate is a proportion over 9. Neither carries an interval, and the [0, 30) bin's "0.0000" is a proportion over two pools.

This matters because §4.2 then makes a claim across all bins including the n = 2 one — see R5-46.

**Fix.** Restate as "the primary certify/violation/decline rates are proportions over R = 200"; attach $n$ and an interval (or an explicit "not interpretable at this $n$") to each Table 1 bin and to the conditional BBSE rate.

### R5-08 — §3.5 and §3.6 specify opposite deployment rules.

> §3.5: "**We deploy the maximum-coverage threshold in the certified prefix.**"

> §3.6, *Combination*: "The modes run as alternatives, each at full $\delta$, and **we deploy the most conservative certified threshold**."

The prefix is ordered "most conservative first" (§3.5); its maximum-coverage element is its *last* element, i.e. the least conservative certified threshold. §3.6 says the opposite. Charitably §3.6 means "the more conservative of the two modes' selected thresholds," but as written the manuscript specifies two mutually exclusive deployment rules, and the reader cannot tell which produced any reported number. Since coverage is a headline result (0.9722, 0.9715, 0.9304, …), the ambiguity is load-bearing.

**Fix.** One sentence: "within each mode we deploy the maximum-coverage certified threshold; across modes we deploy the more conservative of the two mode-selected thresholds."

### R5-09 — "The validity of the certificate never depends on the quality or calibration of the model" is contradicted by the paper's own BBSE decline rule.

> §3.8: "The gate itself is model-agnostic: the score only *ranks* cases, and **the validity of the certificate never depends on the quality or calibration of the model producing that score.**"

> §3.6: "There are three declines: (i) the worst-case confusion gap $(c_1 - c_0) < 0.10$, an ill-conditioned inversion"

In the BBSE mode the record weights are obtained by inverting the classifier's confusion matrix, so the certified statistic is a function of classifier quality; §3.6 declines outright when the classifier separates too weakly, and BBSE's correctness additionally requires the auxiliary-split confusion rates to transfer unchanged to the target — an assumption about the model, not about the gate. "Never" is therefore false for one of the paper's two modes, and §3.8 does not scope its claim to the baseline.

**Fix.** "In the baseline mode the validity of the certificate does not depend on the score's calibration; in the label-shift mode it depends on the classifier's confusion rates transferring to the target, which is why §3.6 declines on an ill-conditioned inversion."

### R5-10 — The justification for a synthetic-only evidence base contradicts the paper's own violation criterion.

> §4 (opening): "**No real cohort can supply that ground truth**, and a certificate only ever checked against the same unlabeled deployment data it was built on cannot be falsified."

> §5.5: "**Real data cannot supply that ground truth, which is what makes it unable to validate a validity claim.**"

The §3.9 hard-violation criterion is:

> §3.9: "A certificate counts as violated only when the one-sided 95% Wilson lower confidence bound on **the target pool's answered error** exceeds $\alpha$"

That statistic requires outcome labels on the target pool and nothing else. Retrospective multi-site clinical cohorts routinely carry outcome labels; that is what external validation *is*, and the manuscript cites two references on exactly that practice (@tripodcluster2023, @internalexternal2021). So the paper's own falsification test is computable on real labelled data, and §5.5's claim that real data is "unable to validate a validity claim" is false as stated.

What real data genuinely cannot supply is the *true risk parameter* $e_c$ noiselessly, and the E3-style ability to verify that a shift is poisonous before running the control. That is a much narrower claim and it would carry the synthetic-first argument perfectly well.

**Fix.** Replace both sentences with the narrow version: real cohorts give realized answered error (enough to falsify a certificate) but not the true risk parameter or a verifiable poison, which is what the negative-control design requires.

### R5-11 — No comparator procedure appears anywhere, yet two claims require one.

> §5.2: "the operative rung is a property of the available cluster count, **not of the method** — buying $\alpha=0.05$ costs sites, and E4 prices that purchase."

> §6: "Assembling them is not automatic: the influence-weighted estimand, the cluster-robust BBSE box, and decline behavior at practical site scales are **obstacles that appear only in combination**"

Every comparison in the paper is CertGate against a deliberately crippled version of itself (E2's uncorrected baseline; A.3's naive-truncation regression test). There is no comparison against any alternative certification procedure at the cluster level — not hierarchical conformal (@dunn2023hierarchical, @lee2025hierarchical, both cited as the nearest machinery), not an RCPS/empirical-Bernstein bound on site means, not a cluster bootstrap, not a plain Hoeffding bound on the 83 atoms.

Without one, "not of the method" is unsupported: a tighter test at the same 83 clusters might certify α = 0.05, in which case the frontier is a property of the WSR construction, the influence cap, and the fixed-sequence walk. Likewise "obstacles that appear only in combination" is an assertion about a counterfactual that was never run.

**Fix.** Add at least one cluster-level comparator to E1 and E4 — even a Hoeffding or empirical-Bernstein bound on the same atoms would do — and either substantiate or soften "not of the method".

### R5-12 — The "exact Shapley values" claim omits the condition its own citation attaches, and the paper's generator violates that condition.

> §3.8: "For a linear model these attributions are **exact Shapley values, with no approximation or sampling** [@lundberg2017shap]."

> §4.6: "exact additive attributions $\phi_j$ — **genuine Shapley values, not sampled approximations** [@lundberg2017shap]"

Lundberg & Lee's Linear SHAP result — $\phi_j = w_j(x_j - \mathbb{E}[x_j])$, exactly the paper's formula — is derived **under an assumption of feature independence**. Whether the formula remains the Shapley value without that assumption depends on which value function is used (it is the interventional/marginal Shapley value in general; it is not the conditional-expectation one). The manuscript states neither the assumption nor the convention.

The generator does not satisfy independence. Per §4.1 the data are a label-conditioned mixture with the class means separated along a direction supported on coordinates 0–3; marginalizing over $y$ makes features 0–3 mutually correlated by construction. So the strong reading of "exact Shapley values" fails in the paper's own data.

**Fix.** State the convention: "these are exact interventional (marginal) Shapley values for a linear model; under the conditional-expectation convention exactness additionally requires feature independence, which the generator does not satisfy." One sentence, and the contribution survives intact — the *additive decomposition of the logit* is exact by algebra regardless, which is what the abstention explanation actually uses.

### R5-13 — The realism of the generator is hung on two citations that cannot carry it, and the introduction's version of the claim carries no citation at all.

> §1: "On a synthetic cohort of 208 sites **whose lognormal sizes, ~9.5% prevalence, and site random effects follow the distributional profile reported for large multi-site clinical cohorts**, the certificate is valid but not vacuous." — *no citation attached*

> §4.1: "This follows the distributional profile reported across multi-site clinical studies — many small-to-large sites with heavy-tailed sizes, single-digit prevalence, and site-level heterogeneity — while remaining fully known, in keeping with the cluster-as-unit reporting culture that motivates the design [@tripodcluster2023; @internalexternal2021]."

@tripodcluster2023 is the TRIPOD-Cluster **reporting checklist** (BMJ 2023). A checklist prescribes what authors should report; it does not report an empirical distribution of site sizes, prevalences, or random-effect variances. @internalexternal2021 (Takada et al., J Clin Epidemiol) is a methodological study of internal–external cross-validation; it is not a source for a size distribution either. Neither can underwrite log-mean 6.0, log-sigma 1.1, clipping at [20, 5000], base prevalence 0.095, or $u_c \sim \mathcal{N}(0, 0.5^2)$.

Since the paper's entire empirical case lives on this generator, and since §4 argues that synthetic data is *superior* to real data for this purpose (R5-10), the claim that the generator matches real multi-site cohorts is doing more work here than in an ordinary simulation study.

**Fix.** Cite one or more actual multi-site clinical cohorts with reported site-size distributions and between-site heterogeneity (e.g. a published IECV study reporting τ² for the outcome), and either match the parameters to them or state plainly that the parameters are stylized and uncalibrated.

### R5-14 — A "cohort level" systematic abstention driver is inferred from two declined cases.

> §4.6: "This case study uses a deployment with threshold $\tau^* = 0.55$, **answering 200 cases and declining 2**."

> §4.6: "**At the cohort level**, feature 0 is the dominant abstention driver: its mean absolute attribution is 0.868 on answered cases but **1.722 on declined cases**, the largest answered-to-declined gap of any feature (gap $-0.854$ …). **Declines are systematically the cases** where feature 0's pull leaves the decision contested"

The declined-case mean is a mean of two numbers. "At the cohort level", "dominant", "systematic abstention drivers" (§3.8 promises the same at cohort level) and "systematically" are all unsupported at n = 2, and the "gap ranking $[0, 3, 2, 1, \dots]$" over 8 features is a ranking of eight two-point means. Figure 5's caption repeats the claim: "identifying it as the dominant systematic abstention driver."

Given that explainability is the *central* emphasis of the target collection, this is the thinnest evidence in the paper attached to its most venue-relevant contribution.

**Fix.** Run E5 at an operating point that produces a usable number of declines (E6's $\tau^*=0.77$ yields ~10% abstention over 40 sites — roughly 2,600 declines), report the answered/declined attribution profiles there with dispersion, and reserve $\tau^*=0.55$ for the three individual case vignettes.

### R5-15 — The manuscript has six figure captions, no figures, and no in-text figure callouts.

Lines 298–310 contain "**Figure 1.**" through "**Figure 6.**" as bold captions. There is no image markup (`![...]`) anywhere in `draft.md`, and no image files exist in `paper/` (directory contains only `TODO.md`, `draft.md`, `references.bib`, `review/`). Independently, the strings "Figure 1" … "Figure 6" appear **nowhere in Sections 1–6 or the appendices** — every figure is orphaned, never referred to from the text that it illustrates. Tables, by contrast, are all called out correctly (Table 1 in §4.2, Table 2 and Table 3 in §4.7, Table 4 in §4.5 and §5.2).

**Fix.** Supply the six figures and add in-text callouts at the points where each is discussed (§4.2, §4.3, §4.4, §4.5, §4.6, §4.7).

### R5-16 — A promised results artifact is missing, and E1 never reports the quantity being certified.

> §3.5: "Both budgets $\alpha \in \{0.05, 0.10\}$ are certified by separate walks and **reported as a coverage-versus-$\alpha$ curve**."

No such curve appears in §4, in the four tables, or in the six figure captions. With only two α values and one of them certifying nothing, a "curve" is two points, one of which is empty.

Separately and more importantly: §4.2 reports E1's certify rate (1.0), coverage (0.9722), hard-violation rate (0.01) and exceedance (0.05) — but never reports the **answered-set error itself**. The certified quantity is absent from the experiment that validates the certificate. A reader cannot tell whether the answered risk was 0.02 or 0.09 against α = 0.10, and therefore cannot judge how much slack the certificate has, cannot check the §3.4 information-floor claim ($\ln(1/\delta)(1-\alpha)/n \approx 0.033$ at n = 83) against the data, and cannot assess whether E1's low violation rate reflects a tight certificate or an over-conservative operating point. §4.2 asserts tightness — "non-zero — consistent with a tight rather than a vacuous certificate" — on the strength of two violated draws.

**Fix.** Add mean and quantiles of the realized answered-set error to §4.2 (and to E2/E3), and either produce the coverage-versus-α curve or delete the promise.

### R5-17 — "A substitute for pre-registration" is asserted three times and is not one.

> §3.2: "This is a **lightweight, machine-verifiable substitute for pre-registration**: it **removes the degrees of freedom** that would otherwise let a tunable pipeline flatter itself."

> §3.10: "the frozen constants are pinned by a unit test (**a lightweight, machine-verifiable substitute for pre-registration**)"

> A.3: "are pinned to their literal values by a unit test, so any drift fails continuous integration."

Pre-registration derives its force from a timestamped, third-party-held record made *before* the data are seen. A unit test in the authors' own repository, written by the authors at a time only they know, provides no such record: it prevents *drift after the constants were chosen*, which is a genuine and worthwhile property, but it says nothing about how many constant settings were tried before the pinned ones were frozen. "Removes the degrees of freedom" is therefore too strong — it removes post-freeze degrees of freedom only.

The claim is repeated verbatim in three places, which for a paper otherwise disciplined about repetition is conspicuous.

**Fix.** State it once, accurately: "the constants are frozen and pinned by a unit test, which prevents post-hoc drift; it is not a substitute for third-party pre-registration, since the freeze date is not externally attested."

### R5-18 — A preprint is called "published" twice, and a quantitative claim with no visible provenance is attributed to it.

> §1, contribution 4: "the rigor that constructively answers a **published diagnosis** of overconfident selective certificates [@zhou2026falsesense]"

> §4.4: "the constructive counterpart to **the published warning** that selective certificates can mislead when their assumptions are not checked [@zhou2026falsesense]"

The bibliography entry is `@misc{zhou2026falsesense, … eprint = {2606.15153}, archivePrefix = {arXiv}, note = {arXiv:2606.15153}}` — an arXiv preprint with no journal, no proceedings, and no peer review. Calling it "published" twice, in the contributions list and in a results section, materially inflates the authority the manuscript borrows.

The same reference carries a precise quantitative claim:

> §2.4: "certified record-level selective-risk rules **overrun their budget by 9–30%** under grouped deployment [@zhou2026falsesense]"

A referee cannot check whether "9–30%" is an absolute overrun, a relative one, or a range across settings, and the paper's own motivating premise rests on it.

More broadly, five of the manuscript's positioning citations — @yu2026joint, @zhou2026falsesense, @triage2026audit, @fedcrc2026, @score2026 — are 2026 arXiv preprints, and they collectively carry the "nearest work", the "documented failure", and the "gap" that define the contribution (§1, §2.1, §2.2, §2.4). The §2.1 claim "Yu and Liu are closest … but over i.i.d. records" is the single sentence on which the novelty of the site-as-unit contribution rests.

**Fix.** Replace "published" with "recent preprint" in both places; state what the 9–30% figure measures; and — because novelty here is load-bearing — corroborate the "over i.i.d. records" characterization of @yu2026joint with a direct quotation or an explicit statement of its assumption.

### R5-19 — Missing prior art, including one paper that bears directly on the paper's own equity analysis.

Named by author/title, all absent from `references.bib`:

1. **Jones, Sagawa, Koh, Kumar, Liang, "Selective Classification Can Magnify Disparities Across Groups", ICLR 2021.** The central known result about selective prediction and groups: abstention improves average accuracy while *worsening* it for worst-group members. §4.7 opens an equity analysis — "whether small hospitals receive systematically worse selective service than large ones" — with no reference to this literature, and Table 2's flat coverage is presented as reassurance without engaging the mechanism Jones et al. identified. For a collection that explicitly encourages fairness, this omission is the most consequential.
2. **Gibbs, Cherian, Candès, "Conformal Prediction with Conditional Guarantees" (2023; JRSS-B 2025)**, and **Vovk's Mondrian / conditional-validity line ("Conditional validity of inductive conformal predictors", ACML 2012).** These are the standard machinery for exactly the marginal-vs-conditional distinction that R5-01 identifies as the paper's central semantic gap. §2.2 discusses cluster exchangeability without mentioning conditional conformal at all.
3. **Barber, Candès, Ramdas, Tibshirani, "Conformal Prediction Beyond Exchangeability", Annals of Statistics 2023.** §2.2's argument is that exchangeability fails under multi-site clustering; the canonical treatment of what survives when exchangeability fails is uncited.
4. **Madras, Pitassi, Zemel, "Predict Responsibly: Improving Fairness and Accuracy by Learning to Defer", NeurIPS 2018; Mozannar & Sontag, "Consistent Estimators for Learning to Defer to an Expert", ICML 2020.** §1's framing — "routing the hard ones to a clinician" — *is* learning-to-defer. The literature is not mentioned once, and it is the literature a clinical-ML reader will expect.
5. **Rudin, "Stop Explaining Black Box Machine Learning Models for High Stakes Decisions and Use Interpretable Models Instead", Nature Machine Intelligence 2019.** §3.8's argument for a transparent linear head over a stronger black-box one is Rudin's argument, uncited, in a manuscript submitted to an explainability-centred collection.

Also worth adding: **Podkopaev & Ramdas, "Tracking the risk of a deployed model and detecting harmful distribution shifts", ICLR 2022** — the closest work in machinery to §3.4's betting construction; the manuscript cites only their 2021 label-shift paper.

Does the positioning survive? Mostly yes. None of these certifies an answered-set risk with the cluster as the unit *and* a label-shift correction carrying its own uncertainty. But (2) and (3) sharpen R5-01 considerably — the conditional-conformal literature exists precisely because marginal guarantees do not transfer to individual groups — and (1) is a direct challenge to §4.7's conclusions.

### R5-20 — "The cluster-as-unit machinery CertGate reuses" — nothing from those papers is reused.

> §2.2: "Dunn, Wasserman and Ramdas [@dunn2023hierarchical] and Lee, Barber and Willett [@lee2025hierarchical] **supply the cluster-as-unit machinery CertGate reuses**"

CertGate's construction is a per-site linearized atom fed to a WSR betting martingale. It uses no subsampling scheme, no hierarchical conformal score, no double-bootstrap, and no other apparatus from either paper. What it borrows is the *idea* that the cluster is the unit — which is how §3.1 correctly puts it ("Cluster-as-unit distribution-free inference has precedent in the conformal literature …; we adopt it as the foundation") and how §2.2's own closing sentence puts it ("CertGate reuses the cluster unit"). Only the "machinery" phrasing overstates.

**Fix.** "supply the precedent for cluster-as-unit distribution-free inference, which CertGate adopts (though not their conformal constructions)".

---

## Minor points

### R5-21 — "Near-tripling" describes a 2.3× change.

> §4.3: "We shift site-level prevalence from the source value of 0.095 up to a target base rate of 0.22 — **a near-tripling** of outcome frequency"

0.22 / 0.095 = 2.32. That is a shade over a doubling, not near a tripling. The abstract states the shift without characterizing it ("a prevalence shift from 0.095 to 0.22"), which is the correct treatment. **Fix:** "a more-than-doubling" or "a 2.3-fold increase".

### R5-22 — The abstract's site-count summary is weaker than the body's.

> Abstract: "a site-count frontier shows the stricter $\alpha=0.05$ budget **needs roughly 300+ sites**."

> §4.5: "first appears at 300 (**certify rate 0.3**, coverage 0.7376), and becomes **reliable only at 400**"

"Needs roughly 300+" invites the reading "300 suffices". At 300 the gate certifies 30% of draws. **Fix:** "needs 300 sites before it appears at all and roughly 400 before it is reliable."

### R5-23 — "Budget" denotes both α and δ, and the abstract uses it ambiguously.

α is called a budget (§1 "a budget $\alpha$"; §3.5 "the budget ladder"; §4.4 "the $\alpha=0.10$ budget"); δ is also called a budget (§3.6 "The two confidence budgets"; §1 "inside the $\delta=0.05$ budget"). In the abstract:

> "a hard-violation rate of 0.01 **under a 0.05 budget**"

Since α = 0.05 is itself one of the two rungs discussed two sentences later, a reader can plausibly read "0.05 budget" as the α rung. **Fix:** write "under the $\delta = 0.05$ confidence budget", and reserve "budget" for α throughout.

### R5-24 — Overloaded and undefined symbols in the betting-test definition.

> §3.4: "$\lambda_t = \min\!\left(\sqrt{\frac{2\ln(1/\delta)}{\hat{\sigma}^2_{t-1}\, n}},\; \frac{0.9}{1-\alpha}\right)$, with a variance floor of $10^{-8}$ and the running mean and variance $(\hat{\mu}, \hat{\sigma}^2)$ initialized at $(0.5, 0.25)$."

(a) $n$ is never defined at this point; $n_c$ has just been used in §3.3 for a site's record count, and $n_{\text{cal}}$ appears two sentences later. Presumably $n = n_{\text{cal}}$, but the reader must guess. (b) $\hat{\mu}$ is introduced with an initial value and never appears in any displayed formula — its role in updating $\hat\sigma^2$ is left implicit. (c) §3.4 then writes "At $n$ clusters no test can certify…", a third usage. **Fix:** define $n_{\text{cal}}$ once and use it consistently; give the $\hat\sigma^2_t$ update.

### R5-25 — E4 coverage is non-monotone in site count and this is not remarked on.

> Table 4, α = 0.10 coverage: 150 → 0.9304; 208 → 0.9715; 300 → **0.9601**; 400 → **0.9621**.

Coverage rises from 150 to 208, then *falls* at 300 and barely recovers at 400. More calibration sites should permit a less conservative certified threshold and thus higher coverage. The manuscript explains the 208-vs-E1 discrepancy (0.9715 vs 0.9722, different seeds) but says nothing about the larger 208-vs-300 drop of 0.011. **Fix:** report Monte-Carlo error on the coverage column and comment, or explain the mechanism.

### R5-26 — "Full adverse weight" contradicts the definition of the cap.

> §3.3: "The cap acts on influence only: it scales each site's whole signed contribution and never censors the error itself, so a site that answers many cases badly still **enters at full adverse weight**."

The weight is exactly what is capped: $g_c = \min(n_c, 100)$, so a 5,000-record site enters at 1/50 of its record count. The intended point — that $e_c$ is not truncated — is correct and worth making; "full adverse weight" states the opposite of the definition two lines above. **Fix:** "still enters with its error rate uncensored, at its (capped) influence weight."

### R5-27 — §3.3 promises a construction in Appendix A.3; A.3 contains no construction.

> §3.3: "The natural fix — capping each site's *realized* contribution — is **provably anti-conservative**: a construction with 17.5% true risk certifies at $\alpha = 5\%$ under naive truncation (**Appendix A.3**; retained as a regression test)."

A.3 is "Software and reproducibility details" and its only mention is: "The anti-conservativity … is pinned by a dedicated regression test, in which a construction with 17.5% true risk certifies at $\alpha = 5\%$ under truncation but is correctly refused under the influence-weighting scheme." That restates the claim; it does not give the construction. The word "provably" plus a forward reference sets up a proof the appendix does not deliver. **Fix:** give the construction (it should be a few lines), or drop "provably" and the appendix pointer.

### R5-28 — "Clipped $\rho$" is undefined inside a soundness argument.

> A.2: "It is propagated to $[\rho_{\text{lo}}, \rho_{\text{hi}}]$ by *corner-interval coverage*: **the clipped $\rho(c_0, c_1, \pi_s)$** is coordinate-wise monotone in each of the three box parameters"

Clipping is never defined — not the bounds, not where in the pipeline it is applied. It also interacts with the monotonicity argument at exactly the corners where the argument is delicate (corners for which the implied $\pi_t$ leaves $(0,1)$). I checked the monotonicity itself and it holds for the unclipped map — $\partial\pi_t/\partial c_0 = (q-c_1)/(c_1-c_0)^2 \le 0$, $\partial\pi_t/\partial c_1 = -(q-c_0)/(c_1-c_0)^2 \le 0$, $\rho$ decreasing in $\pi_s$ — so the corner argument is sound where it is defined. **Fix:** define the clip and state why it preserves coordinate-wise monotonicity.

### R5-29 — Decline rule (iii) is justified by a property it does not enforce.

> §3.6: "(iii) $q$ outside the box's $[c_{0,\text{lo}}, c_{1,\text{hi}}]$ range, **meaning the implied prevalence leaves $(0,1)$** and BBSE is misspecified."

$\pi_t = (q - c_0)/(c_1 - c_0)$ lies in $(0,1)$ iff $q \in (c_0, c_1)$. The rule uses the *widest* interval, $[c_{0,\text{lo}}, c_{1,\text{hi}}]$, so a $q$ that passes the rule can still fall below $c_{0,\text{hi}}$ or above $c_{1,\text{lo}}$, at which point some box corners imply $\pi_t \notin (0,1)$. The stated justification ("meaning the implied prevalence leaves (0,1)") therefore holds in one direction only. This is presumably what the undefined clip in A.2 handles, but the two sections do not connect. **Fix:** state the rule as "declines when *no* point in the box admits a valid inversion", and cross-reference the clip.

### R5-30 — An undefined component appears only in the limitations.

> §6.1: "*Missingness is handled without a positivity diagnostic.* Missing values pass through **the frozen encoder's imputation-and-indicator scheme**"

No encoder is described anywhere in §3 or §4; §4.1's generator produces $d=8$ complete Gaussian-mixture features with no missingness. A reader meets "the frozen encoder" for the first and only time in the limitations, applied to a mechanism the manuscript's data does not contain. **Fix:** either describe the encoder in §3 as part of the real-data path, or move this limitation into §5.5 as a forward-looking note about real data.

### R5-31 — An unsupported number in the limitations.

> §6.1: "at practical clip caps, the effective-sample-size loss **structurally prevents certification below roughly 400 clusters** — the clip cap divides the certification margin under the information floor"

No derivation, no experiment, and no clip-cap value are given. Since E4 stops at 400 clusters, this number sits exactly at the edge of the evidence and cannot be checked against it. **Fix:** give the one-line ESS argument, or write "we expect a substantial effective-sample-size penalty" without a number.

### R5-32 — The black-box-head claim is garbled and untested.

> §3.8: "**A stronger black-box head can be substituted at a visible cost in coverage**; we use logistic regression here because the explainability requirement, not the certificate, calls for a transparent head."

As written this says substituting a *stronger* head *costs* coverage, which is backwards — a better-ranking score should permit more answers at the same certified risk. The intended claim is presumably that using the weaker transparent head costs coverage relative to a black-box one. Either way, no experiment swaps the head, so §5.3's "the gate would then price its selective quality visibly, as a change in certified coverage" is an untested prediction stated in the indicative. **Fix:** repair the sentence and mark both as conjecture, or run the ablation.

### R5-33 — The manuscript counts its own literatures three different ways, and demotes explainability.

> §1: "**Three questions** in reliable machine learning have mature but separate answers."
> §2: "CertGate draws on **four literatures** that each solve part of the problem"
> §6: "CertGate occupies the intersection of **three separately developed lines**"

The literature that appears in the four-count but not the three-counts is explainable abstention. At a collection whose stated centre is explainability, the framing that survives into the introduction and conclusion is the one that leaves it out; §1's contribution 3 reinforces this — "This supports the certificate above rather than standing as an independent method." **Fix:** make the count consistent, and see the confidential note on venue fit.

### R5-34 — Citekey/year mismatches in the bibliography.

- `angelopoulos2021ltt` — entry is `year = {2025}` (Ann. Appl. Stat. 19(2)). Key says 2021 (the arXiv year).
- `ifac2025abstainexplain` — entry is `year = {2024}`, ECML PKDD 2024, Springer LNCS. The key's "ifac" prefix corresponds to no part of the entry, and "2025" contradicts the year field.
- `l2lore2025` — entry is `year = {2024}` (Discovery Science 2024 Late Breaking, CEUR Vol-3928). Key says 2025.
- `score2026` — the key gives no hint of Bai & Jin, "Conformal Selective Prediction with General Risk Control".

Harmless to citeproc, but they will produce confusing author-year renderings if the style is changed, and the mismatched years invite a reader to think a 2024 paper is 2025. **Fix:** align keys with entry years.

### R5-35 — The submitted bibliography contains an internal working note.

> `references.bib`, lines 1–3: "% CertGate manuscript references — every entry verified against its primary source on 2026-07-24 % (arXiv abstract page, DOI/Crossref record, or publisher/proceedings page; **see paper/TODO.md for the one unverified candidate, scireports2026deferral, which is deliberately NOT in this file**)."

A pointer to an internal to-do file, and the name of a deliberately excluded reference, in a file submitted to the journal. **Fix:** strip the comment block before submission.

### R5-36 — Two citations attached to sentences they do not support.

> §4.2: "The hard-violation rate is 0.01 … at or below $\delta = 0.05$ and non-zero — **consistent with a tight rather than a vacuous certificate** [@geifman2017selective]."

Geifman & El-Yaniv 2017 introduces a selective-risk bound; it establishes nothing about interpreting a non-zero empirical violation rate as evidence of tightness. The citation is decorative here.

> §6: "certified selective risk [@chow1970reject; @geifman2017selective]"

Chow 1970 gives the Bayes-optimal error–reject tradeoff. It contains no certificate, no finite-sample bound, and no confidence parameter. §2.1 gets this right ("The reject option dates to Chow"); §6 folds it into "certified selective risk". **Fix:** drop @geifman2017selective from the §4.2 sentence; in §6 cite Chow as the reject-option origin, separately from the certification line.

### R5-37 — A decorative citation with a non-sequitur conclusion.

> §2.4: "**The same certificate shape appears in power-grid contingency screening [@thermal2026audit], so it is not specific to medicine.**"

This closes §2.4 — a section on multi-site clinical validation and explainable abstention — without identifying a gap, a relation, or a difference, which is the stated job of every other paragraph in §2 ("closing each with the nearest work and the gap"). And "so it is not specific to medicine" is an argument for generality that the manuscript never uses again. **Fix:** delete, or relocate to §5 as a generality remark with a stated relation.

### R5-38 — RCPS in the fixed-sequence citation triple.

> §3.5: "so no $\delta$-splitting across the grid is needed [@westfall2001fixedsequence; @angelopoulos2021ltt; @bates2021rcps]."

Westfall & Krishen supplies the fixed-sequence procedure and LTT supplies the learn-then-test framing that permits it; RCPS is a UCB-based construction and does not bear on δ-splitting across a grid. **Fix:** drop @bates2021rcps from this triple (it is properly cited in §2.1).

### R5-39 — Codebase artifacts in the prose.

> §4.1: "The cohort follows the specification frozen in `data.py`"
> §4.1: "Every experiment runs in **mode FULL** under protocol seed 20260721"
> §4.4: "(`tilt_pushes_risk_above_alpha` true)" and "(reason `e3-control-not-poisonous`)"
> §5.5: "the implementation includes a `from_raw` loader"
> A.3: "**The test suite is 69/69 green.**"

A manuscript must specify the generator in the manuscript, not by reference to a source filename; "mode FULL" is undefined jargon; identifier and reason-string names are implementation detail; and a test count is not evidence a referee can weigh. **Fix:** state the generator parameters in a table (most already appear in §4.1 prose), define or delete "mode FULL", paraphrase the flag names, and delete the test count.

### R5-40 — Every reproducibility claim is currently unverifiable.

> Data availability: "publicly available at **[CODE REPOSITORY URL — to be added]**"

The manuscript's reproducibility apparatus — byte-identical certificates, the SHA-256 seeding rule, the pinned-constants test, the 69/69 suite, `data.py`, `from_raw` — all resolve to a repository that does not yet have an address. I note this as a submission-completeness item rather than a scientific fault, but every claim in §3.10 and A.3 depends on it.

### R5-41 — Three different operating points across E1, E5 and E6, with no stated relationship and no certified threshold reported anywhere.

E5 uses $\tau^* = 0.55$ (§4.6); E6 uses $\tau^* = 0.77$ (§4.7); E1 reports coverage 0.9722 (§4.2) but never states which threshold produced it, and neither do E2, E3 or E4. So the explainability evidence (E5) and the equity/composition evidence (E6) are gathered at two operating points, neither of which is shown to be the certified operating point of the validity experiment. No reason is given for the choice of either.

Also: E5's target-pool size is never stated. It is inferable as 202 (200 answered + 2 declined), which is a very small deployment for the "cohort level" language of R5-14.

**Fix.** Report the certified $\tau^*$ (mean, or distribution over draws) for E1–E4, and either run E5/E6 at that threshold or justify the deviation.

### R5-42 — Table 3's Count column mixes three incommensurable quantities.

| Estimator | Positive fraction | Count | Tag |
|---|---|---|---|
| Predicted-class | 0.0393 | 917 / 23,325 | estimated |
| BBSE-implied true-class | 0.0591 | 1,378.9 expected ($\hat{\rho}=0.830$) | estimated, label-shift assumption |
| Oracle true-class | 0.0630 | 1,470 / 23,325 | diagnostic, harness only |

A count, a non-integer expectation with an embedded parameter estimate, and a count. All three fractions do reconcile against their counts (917/23325 = 0.03931; 1378.9/23325 = 0.05912; 1470/23325 = 0.06302) — I checked. But the header "Count" is wrong for row 2. **Fix:** rename the column "Count or expected count", or split into two columns.

### R5-43 — Bin notation differs between prose and tables, ambiguously at the endpoints.

> §3.9: "stratified by answered-set size bins $\{<30,\ 30\text{–}100,\ 100\text{–}300,\ >300\}$"

Tables 1 and 2 use $[0,30)$, $[30,100)$, $[100,300)$, $[300,\infty)$. The prose form leaves 30, 100 and 300 in two bins each (or, reading ">300" strictly, leaves 300 in none). **Fix:** use the half-open interval notation everywhere.

### R5-44 — The title asserts a clinical setting the paper does not enter.

> Title: "…certified selective prediction **for multi-site clinical risk models**…"

All data are synthetic; the abstract discloses this correctly ("On a 208-site synthetic cohort"), the title does not. For a clinical venue the title as written will be read as a clinical study. **Fix:** "…for multi-site clinical risk models: a synthetic-cohort study", or similar.

### R5-45 — Unhedged generalizations in the abstract and introduction.

> Abstract: "a confidence guarantee written at the record level **is silently overconfident** once deployment spans institutions."
> §1: "Under the way multi-site clinical data is actually distributed, **that promise is often false**, in a way the deployed system cannot see."
> §1: "A certificate that treats records as exchangeable **overruns its stated confidence** once deployment is grouped by site"

All three state as unconditional fact what is a possibility whose realization depends on the degree of within-site correlation; a record-level guarantee is not overconfident when the intraclass correlation is negligible. The third is anchored only to a 2026 preprint (R5-18). **Restrained versions:** "can be overconfident"; "that promise can fail"; "can overrun its stated confidence, in proportion to within-site correlation".

I note for balance that the manuscript contains **no** novelty-spam: no "first", no "novel", no "state of the art", and the hedges that are present ("consistent with", "we expect", "roughly", "relevance, not a federated method") are doing honest work and should be kept. The register problems are concentrated in the handful of sentences quoted here and in R5-51.

### R5-46 — A cross-bin claim that includes a bin of two.

> §4.2: "**Across every size bin** the observed exceedance sits far below the reference"

Table 1's $[0,30)$ bin has $n = 2$ pools and an observed exceedance of 0.0000. Nothing can sit "far below" a reference on two observations. **Fix:** "across the three bins with adequate support ($n \ge 18$)".

### R5-47 — The "recovers the generator" claim depends on an unstated generator detail.

> §4.1: "the class signal lives on **a single normalized direction supported on the first four coordinates**"
> §4.6: "The global standardized importances **recover the generator**: features 0–3 dominate at 1.157, 1.161, 1.178, and 1.155"

The near-equality of the four coefficients is only evidence of recovery if the generating direction loads the four coordinates equally. §4.1 says the direction is normalized and supported on coordinates 0–3, but not that the loadings are equal. **Fix:** state the loadings.

### R5-48 — A qualifier stated in §3.9 is dropped in §3.7.

> §3.9: "**at the boundary** the exceedance rate approaches 50% as batches grow"
> §3.7, clause (3): "not any single batch's realized error count, **which exceeds $\alpha$ at binomial-dispersion rates** even under a valid certificate"

The near-50% dispersion behaviour holds when the true risk sits *at* α. Clause (3) states it unconditionally, which is what then licenses §5.1's reversed claim (R5-05). E1's own data — realized exceedance 0.05 against references near 0.48 — show the unconditioned version is false for this system. **Fix:** restore "when the true risk sits at the α boundary" to clause (3).

### R5-49 — The introduction's E2 summary omits the nine certified draws.

> §1: "the label-shift mode never certifies *and* violates (the joint event is 0 of 200 draws), **declining instead**."

"Declining instead" reads as "declining in all other draws"; in fact BBSE certified 9 draws (§4.3). The abstract handles this correctly ("declining in 95.5% instead"). **Fix:** match the abstract's phrasing.

### R5-50 — Contribution 2 understates the decline rate that is its main empirical result.

> §1, contribution 2: "turning a $48.5\%$-violation baseline into **a gate that certifies or declines** rather than issuing a certificate it cannot support (E2)."

"Certifies or declines" implies a working alternation; the measured behaviour is 4.5% certify / 95.5% decline. **Fix:** "into a gate that declines in 95.5% of draws rather than issuing a certificate it cannot support".

### R5-51 — Self-evaluative and pre-emptive phrasing.

> §4.7: "**the reading is honest**"
> §6: "**Its posture throughout is disclosure**"
> §5.2: "**For any reader tempted to call $\alpha=0.10$ a weak guarantee:** the operative rung is a property of the available cluster count, not of the method"
> §4.4: "**A negative control that cannot fail proves nothing.**" / "Demonstrating the failure openly **is validation rigor**"
> §3.6: "**We do not paper over this.**"

Each substitutes an assertion of virtue for the demonstration of it, and §5.2's pre-emption additionally makes a claim the paper cannot support (R5-11). **Restrained versions:** "the answered set's positive fraction sits below the cohort prevalence by all three estimators"; delete "Its posture throughout is disclosure"; "the operative rung reflects the available cluster count under this test; whether a tighter cluster-level test could reach α = 0.05 at 83 clusters is untested here"; keep the negative-control aphorism but drop "is validation rigor"; delete "We do not paper over this."

### R5-52 — The calibration-cluster count is given three different ways.

> §3.1: "resting on **roughly eighty** site-level observations"
> §3.5: "**about 83** calibration clusters"
> §5.2: "**roughly 80** of them at the 208-site scale"

40% of 208 is 83.2, so §3.5 is right and the other two round down without saying so. Trivial, but the number is the paper's central rhetorical point ("site count, not record count") and should be stated identically each time.

---

## Questions to authors

### R5-53
§2.1 states that Yu and Liu [@yu2026joint] give "the same certificate shape — a selected-risk bound with an acceptance floor and a decline option — but **over i.i.d. records**." The novelty of contribution 1 depends entirely on that last clause. Can you quote the assumption from that paper verbatim, and confirm it does not admit grouped or hierarchical data?

### R5-54
Table 3 reports a BBSE-implied composition with $\hat{\rho} = 0.830$ in E6, which §4.7 describes as an in-distribution study. Why is a label-shift correction being applied and reported in an experiment with no shift, and what does $\hat\rho = 0.830$ (implying a target prevalence *below* source) indicate about the estimator's bias in the null case?

### R5-55
A.1(iii) requires $\mathbb{E}[Z_t \mid \mathcal{F}_{t-1}] \ge \alpha$ under $H_0$. Under what assumption on the calibration sites does that hold — i.i.d. draws, exchangeability, or something weaker — and how does that assumption coexist with §3.3's statement that "target features are treated as observed, and it is the label randomness that carries the expectation"? Concretely: if the 83 calibration sites are correlated through the shared collection window that §6.1 acknowledges, does the crossing rule still have level δ, and by how much is it inflated?

### R5-56
What is the mean (and, say, 10th/90th percentile) realized answered-set error in E1 at α = 0.10, and how does the achieved certification margin compare with the information floor $\ln(1/\delta)(1-\alpha)/n \approx 0.033$ at $n = 83$? Without these, the "tight rather than vacuous" claim in §4.2 rests only on two violated draws.

### R5-57
Table 4's α = 0.10 coverage is non-monotone: 0.9715 at 208 sites, 0.9601 at 300, 0.9621 at 400. Is this Monte-Carlo noise (if so, what is its magnitude at R = 200?) or a systematic effect of the fixed-sequence walk at larger $n_{\text{cal}}$?

### R5-58
Since $\mathbb{E}[Z] \le \alpha$ bounds an influence-weighted mean across sites, what is the *distribution* of true answered-set risk across target sites in E1 and E6 — specifically the maximum and the 90th percentile? If some sites materially exceed α while the certificate holds, §3.7's clause (1) ("scoped per target site") needs rewriting; if none do, that is a result worth reporting.

### R5-59
What certified thresholds $\tau^*$ does the fixed-sequence walk actually select in E1, E2 and E3 (distribution over the 200 draws)? And why do E5 ($\tau^*=0.55$) and E6 ($\tau^*=0.77$) use two different operating points, neither reported as the certified one?

### R5-60
For the exact-Shapley claim: which value function do you use — interventional/marginal or conditional? If conditional, how do you reconcile exactness with the marginal correlation among features 0–3 induced by the label-conditioned mixture in §4.1?

### R5-61
Section 3.6 declines when "$q$ outside the box's $[c_{0,\text{lo}}, c_{1,\text{hi}}]$ range, meaning the implied prevalence leaves $(0,1)$". For $q$ inside that widest interval but outside $(c_{0,\text{hi}}, c_{1,\text{lo}})$, some box corners imply $\pi_t \notin (0,1)$. What exactly does the "clipping" in A.2 do at those corners, and does the corner-monotonicity argument still bound every interior $\rho$?

### R5-62
Table 1's smallest bin has two pools. What determines how many target pools land in each size bin — is the target pool one site per draw, or a pooled set of sites? §3.9 says "the calibration draw, not the target site, is the unit of replication" but never states how many target sites each draw evaluates.

---

## Confidential comments to the editor

### R5-63
My central doubt is R5-01, and I want to state it without hedging. The mathematics in §3.3–§3.4 and Appendix A.1 certifies the mean of a per-site atom over a site population. That is an *average across hospitals*. The paper sells it, in §3.1, in guarantee clause (1), and again in §5.1, as a promise *at* a hospital. Those are different claims, and the difference is the whole reason the conditional-conformal literature exists — a literature the manuscript does not cite (R5-19). I do not think this is deliberate misdirection; I think the authors slid between the two readings and never noticed, because their in-distribution experiment uses a homogeneous site population where the readings nearly coincide. But it is the paper's headline promise and it is currently wrong as stated. If the authors' response is "we meant the population mean", the paper is publishable with a rewritten guarantee and a weaker but honest abstract. If the response is "we meant per-site", they need a new proof.

### R5-64
The second doubt is that the evidence base is closed. Everything is synthetic; the only comparator is a deliberately broken version of the same system; the generator's realism is underwritten by a reporting checklist (R5-13); and the paper argues at two points that real data is *inferior* evidence for its claim (R5-10) — an argument I showed is contradicted by the paper's own falsification criterion. The combination is uncomfortable: a system whose validity is defined by a test only its own harness can run. I do not think this is fatal for a methods paper, but I would not let §4's opening paragraph and §5.5 stand as written, because together they construct a rationale for never having to test on real data.

### R5-65
The BBSE result is thinner than it looks and the abstract does not say so. "The corrected mode never does [certify and violate]" is 0/200 on the joint event, but only 9 draws ever gave it the chance; the conditional rate is 0/9, exact upper bound ≈ 0.336, and that interval is the one number in the results section the authors omitted despite promising in §4.1 to supply intervals for every rate (R5-06, R5-07). I do not allege the omission is strategic — the joint-event interval is reported and is the right primary number — but it is exactly the omission that makes a weak result read as a strong one, and it needs to be fixed before publication regardless of intent.

### R5-66
Positioning risk. The gap the paper claims — nobody has done cluster-as-unit certified selective risk with label-shift uncertainty inside the budget — rests on five 2026 arXiv preprints I cannot check (R5-18), two of which (@yu2026joint, @zhou2026falsesense) carry essentially the entire novelty argument, and one of which is twice described as "published" when it is not. If @yu2026joint turns out to handle grouped data, contribution 1 collapses to an incremental variant. I would ask the handling editor to have those two characterizations independently verified before acceptance; they are single points of failure for the paper's claim to novelty and they are trivially checkable.

### R5-67
Venue fit, stated plainly. This collection's centre is explainability — framed as transparency *and* as an educational aid for clinicians. The manuscript's explainability contribution is explicitly demoted by the authors themselves ("This supports the certificate above rather than standing as an independent method"), is dropped from the three-literature framings in §1 and §6 (R5-33), and is evidenced by a case study of 200 answered and **2** declined cases from which a "cohort level" "systematic abstention driver" is inferred (R5-14). There is no clinician-facing evaluation, no user study, no comparison to any alternative explanation method, and no engagement with the fairness literature on selective prediction (R5-19, item 1) despite §4.7 opening an equity analysis. The statistical contribution is the real contribution here and it is a good one; but as submitted this is a distribution-free-inference paper wearing an XAI badge, and I think the editors should decide with that clearly in view. Fixing R5-14 — rerunning E5 at an operating point that produces thousands of abstentions — would go a long way, and is cheap.

### R5-68
One thing I want on the record in the paper's favour, because my report is long and negative by construction. I reconciled every number in the abstract against the body, every body number against its table and its figure caption, and the internal arithmetic of all four tables (Table 1's bin exceedances reproduce the stated 0.05 overall rate exactly; Table 2's site counts sum to 40; all three Table 3 fractions reproduce from their counts; the 9-certified/191-declined split reconciles with 0.955; both E5 declined-case logit margins reproduce to the stated precision from the quoted scores and $\tau^*=0.55$; the Clopper–Pearson intervals are correct; the 50-cluster gate reconciles with the ~125-site threshold via the 40% split). I found **no** arithmetic errors and one deliberately disclosed cross-run difference (0.9722 vs 0.9715). That is a better record than most manuscripts I referee, and the deficiencies above are semantic and evidentiary, not sloppiness.

---

## Recommendation

**Major revision.**

The statistical core is careful and the numerical record is clean, which makes this worth revising rather than rejecting; the topic — cluster-as-unit uncertainty quantification with abstention for cross-institutional clinical deployment — sits squarely inside the collection's encouraged list (uncertainty quantification, calibration, OOD robustness, clinical auditability). But three things must change before it can be published. First, the guarantee must be restated to match what is proved: an influence-weighted mean over the site population, not a per-site promise (R5-01), with the abstract carrying the §3.7 clauses it currently drops and the asymptotic BBSE caveat the paper claims it already carries (R5-03, R5-04). Second, the discussion sentence that reverses its own Results number must go, and the missing confidence interval on the BBSE conditional rate must be supplied (R5-05, R5-06, R5-07). Third — and this is what decides venue fit as much as quality — the explainability layer needs an evidence base larger than two declined cases, and the paper must engage the fairness-under-selective-prediction literature it currently omits (R5-14, R5-19). None of these requires new methodology; all three require the authors to say what they actually did. The figures, which do not currently exist in the submitted materials, must also be supplied (R5-15).
