# Referee 3 — Explainable AI / Trustworthy ML

**Manuscript:** *CertGate: finite-sample certified selective prediction for multi-site clinical risk models, with label-shift robustness and explainable abstention*
**Venue:** *Discover Computing*, Collection "Intelligent Medicine: Machine Learning and Explainable AI for Next-Generation Healthcare"
**Reviewer remit:** attribution method, abstention explanation, evaluation of explanation quality, XAI prior art, collection fit.

---

## Summary

The paper proposes a selective-prediction gate for multi-site clinical risk models. Its statistical core treats the site rather than the record as the unit of independence and certifies, with finite-sample confidence $1-\delta$, that an influence-weighted error rate on the *answered* subset stays at or below $\alpha$. Certification is done with a Waudby-Smith–Ramdas betting martingale over calibration sites, the operating threshold is picked by a fixed-sequence walk, and a second assumption mode corrects for outcome-prevalence shift via BBSE while carrying the correction's own estimation uncertainty into the confidence budget through a cluster bootstrap. Six experiments on a 208-site synthetic cohort report validity in distribution (E1), the label-shift failure and its repair (E2), a verified-falsifiable concept-shift negative control (E3), a site-count feasibility frontier (E4), and two studies I am chiefly responsible for: an explainability case study (E5) and a per-site coverage and answered-set composition study (E6).

The explanation contribution, as the title, abstract and Contribution 3 present it, is that "every answer and every abstention additionally carries an exact feature attribution" because "the deployed head is L2-regularized logistic regression with $C = 1.0$" (§3.8). Concretely: standardized coefficients as a global view; $\phi_j(x) = w_j(x_j - \mu_j)$ as local attributions, asserted to be "exact Shapley values, with no approximation or sampling"; and, for declined cases, a scalar margin-to-answer $m(x) = \mathrm{logit}\,\tau^* - |\mathrm{logit}\,\hat p(x)|$ plus "the signed feature attributions of the confidence deficit". E5 exhibits three cases and one cohort-level statistic.

**Overall assessment.** The statistical machinery is not my lane and I do not comment on it. On my lane, the verdict is uncomfortable for a collection that puts explainability at its centre: the manuscript contributes no explanation method, and it says so itself ("a supporting capability the linear head makes nearly free", §3.8). That could be acceptable if the explanation layer were rigorously evaluated and honestly billed. It is neither. The word "exact" is carrying rhetorical weight for what is, on a linear model, an identity; the abstention-explanation quantity that constitutes the paper's distinctive claim is never defined; explanation quality is never evaluated by any protocol — faithfulness and plausibility are not distinguished, the words do not appear in the manuscript, and no human ever sees an explanation; and the one quantitative explanation result, the "dominant abstention driver", rests on **two** declined cases. Meanwhile the title, abstract and keywords bill explainable abstention as a co-equal headline. That gap between billing and substance is the central problem I am reporting.

---

## Major points

### R3-01 — The "exact Shapley values" claim omits the feature-independence assumption it requires, and the paper's own generator appears to violate it.

> "For a linear model these attributions are exact Shapley values, with no approximation or sampling [@lundberg2017shap]." (§3.8)

The formula $\phi_j(x) = w_j(x_j - \mu_j)$ is exactly Lundberg & Lee's *Linear SHAP*, and in that paper it is derived under an explicitly stated assumption of **feature independence** (equivalently, under the interventional/marginal value function). Under feature dependence, the conditional-expectation Shapley values for the same linear model are *not* $w_j(x_j-\mu_j)$; the discrepancy is the entire subject of Aas, Jullum & Løland, "Explaining individual predictions when features are dependent: More accurate approximations to Shapley values" (*Artificial Intelligence* 298:103502, 2021), and of Chen, Janizek, Lundberg & Lee, "True to the Model or True to the Data?" (2020). Neither is cited; neither is the choice of value function stated anywhere in the manuscript.

This is not a pedantic point here, because the manuscript's own data-generating process induces marginal dependence among exactly the features it then explains:

> "the class signal lives on a single normalized direction supported on the first four coordinates, with the two class means separated by $\mathrm{sep} = 2.2$ along that direction" (§4.1)

A two-component mixture with class-dependent means along a shared direction makes features 0–3 marginally correlated. So the assumption under which the attributions are "exact" is, on the paper's own cohort, false — or at minimum, unstated and unchecked. **Fix:** state the value function explicitly (interventional, marginal expectation over the training split), replace "exact Shapley values" with "exact interventional (marginal) Shapley values under the independence value function", cite Aas et al. and Chen et al., and report the empirical feature correlation matrix of the generator so the reader can judge how far the two formulations diverge.

### R3-02 — The attribution layer is a restatement of the deployed model, not an explanation contribution, and the manuscript should say so in the abstract rather than only in a subordinate clause.

> "The deployed head is L2-regularized logistic regression with $C = 1.0$, chosen so that the answer/abstain decision is intrinsically interpretable." (§3.8)

The model has 8 features and is linear. The "explanation" $\phi_j(x) = w_j(x_j-\mu_j)$ with $\mathrm{logit}(\hat p(x)) = \text{base} + \sum_j \phi_j$ is the model's own arithmetic, re-parenthesised. There is no approximation being made, no surrogate being fitted, no sampling — precisely because there is nothing to approximate. An attribution layer over an intrinsically interpretable model is a restatement, and a referee has to say so plainly: **the manuscript proposes no explanation method.** It selects an interpretable model class and then reports the model.

I want to be fair: the body already half-concedes this ("a supporting capability the linear head makes nearly free", §3.8; "This supports the certificate above rather than standing as an independent method", Contribution 3). The problem is that the concession lives in the body while the promise lives in the title, abstract and keywords (see R3-13). **Fix:** the abstract should state that the explanation layer is the read-out of an intrinsically interpretable head, not a new attribution method. This is a legitimate and defensible design position — Rudin (2019) argues for exactly it — but it has to be *claimed as such*, not dressed as an attribution contribution.

### R3-03 — "Certified decision" is not a property any individual record possesses; the sole claimed novelty of the explanation contribution does not survive the paper's own §3.7.

The whole differentiator of the explanation layer is stated three times as *attachment to a certified decision*:

> "the contribution is the attachment of explanation to a *certified* decision, extending reject-option explanation work that carries no statistical guarantee" (Contribution 3)
> "CertGate's difference is exact attributions on a certified gate." (§2.4)
> "what the gate adds is that the same exact attributions accompany a certified decision" (§3.8)

But the manuscript's own guarantee text forbids reading "certified" as a record-level property:

> "(3) It bounds the answered-set error parameter, not any single batch's realized error count, which exceeds $\alpha$ at binomial-dispersion rates even under a valid certificate." (§3.7)
> "(2) All sites certified from one calibration draw share a single $1-\delta$ event, not an independent guarantee each." (§3.7)

So an individual answered record carries no certified property whatsoever; the certified object is a site-level parameter under a shared $1-\delta$ event. "Exact attributions on a certified gate" is therefore an accurate but much weaker statement than "explanation attached to a certified decision", and the explanation-layer novelty reduces to: *a certified gate exists, and separately, off-the-shelf linear attributions are computed on the same records.* Any attribution method could be bolted to any certified gate with identical justification. **Fix:** either drop the "certified decision" framing at the record level and replace it with "attributions computed on the decisions of a gate whose site-level answered-set risk is certified", or explain what statistical property, if any, the *explanation itself* inherits. It appears to inherit none.

Compounding this: the E5 case study, which is the sole demonstration of the claim, never states that its deployment was certified at all (see R3-12).

### R3-04 — The abstention-explanation quantity — the paper's distinctive claim — is never defined, and it is not additively decomposable, so "exact" cannot transfer to it.

> "we report the margin-to-answer $m(x) = \text{logit}\,\tau^* - |\text{logit}\,\hat{p}(x)| > 0$ together with the signed feature attributions of the confidence deficit" (§3.8)

There is no formula for "the signed feature attributions of the confidence deficit" anywhere in the manuscript, and there cannot be a straightforward exact one. The prediction $\mathrm{logit}\,\hat p(x) = \text{base} + \sum_j \phi_j$ is additive in $\phi_j$; the *deficit* $m(x) = \mathrm{logit}\,\tau^* - |\text{base} + \sum_j \phi_j|$ is not, because of the absolute value and the additive constant $\mathrm{logit}\,\tau^*$. Attributing $m(x)$ to features is a genuinely different attribution problem — one whose answer depends on how you handle the non-linearity and the constant, and whose "exact Shapley" solution is *not* $\phi_j$. The manuscript slides from an exactness claim about the prediction to an exactness claim about the abstention:

> "the same exact attributions accompany a certified decision" (§3.8)
> "the answer/abstain decision comes with exact additive attributions $\phi_j$ — genuine Shapley values" (§4.6)

Note the second quotation: it says the *answer/abstain decision* comes with exact additive attributions. It does not. The *score* does. The abstain decision is a thresholded function of $|\cdot|$ of that score. **Fix:** give the formula for the deficit attribution, state its value function, and either prove the exactness claim for it or restrict "exact" to the prediction attributions and say plainly that declined-case attributions are the prediction attributions re-displayed with a margin number beside them.

### R3-05 — The abstention explanation actually demonstrated collapses into a restatement of the margin, and is weaker than the template promised in the Methods.

Methods promise a contrastive, feature-named narrative:

> "declined because feature A pulls toward positive while features B and C pull toward negative, leaving confidence below the certified bar." (§3.8)

Results deliver this:

> "so the abstention reads as 'declined because the informative features leave confidence below the certified bar' rather than an opaque refusal." (§4.6)

The delivered sentence names no feature, no direction and no contrast. It says only *confidence was low* — which is exactly and only what the scalar $m(x)$ already reported, and exactly what any confidence-thresholded reject option says without any attribution layer at all. The demonstrated abstention explanation therefore adds nothing over the abstention rule itself. The three case studies (§4.6, indices 48, 38, 102) report scores and margins — 0.99997, 0.5262 with $m = 0.0956$, 0.5445 with $m = 0.0223$ — and **not a single per-feature $\phi_j$ value for any declined case**. The claim "In each declined case the signed attributions localize the confidence deficit to specific features" is asserted without exhibiting one number. **Fix:** print the full signed attribution vector for each declined case, and show the Methods-promised template instantiated with actual feature indices and directions.

### R3-06 — A gap in mean *absolute* attribution cannot identify an "abstention driver", because abstention in a linear model is caused by cancellation of the signed sum, which is a joint property no additive per-feature statistic can localize.

> "At the cohort level, feature 0 is the dominant abstention driver: its mean absolute attribution is 0.868 on answered cases but 1.722 on declined cases, the largest answered-to-declined gap of any feature" (§4.6)
> "identifying it as the dominant systematic abstention driver" (Figure 5 caption)

A case is declined precisely when $|\text{base} + \sum_j \phi_j|$ is *small* — that is, when the signed contributions cancel. A feature with a *large* mean $|\phi_j|$ on declined cases is, by construction, a feature that had to be cancelled by something else. Calling it "the driver" is a causal reading that the statistic does not license: it cannot distinguish (a) "this feature causes contested cases", (b) "declined cases happen to take extreme values on this feature", and (c) "this feature has the largest variance, so it dominates any absolute-magnitude comparison". Whatever the underlying cause, the abstention is a property of the *configuration*, not of a feature, and additive attributions are the wrong instrument for locating it.

The generator makes this worse, because it is close to symmetric across the informative features:

> "features 0–3 dominate at 1.157, 1.161, 1.178, and 1.155" (§4.6)

Four near-identical standardized coefficients on a signal supported by a single normalized direction give no principled reason for feature 0 to differ from features 1–3 in abstention behaviour. **Fix:** either propose a statistic that is actually about cancellation (e.g. the distribution of the signed sum's decomposition, or a contrastive/counterfactual measure of how much each feature would have to move to cross the bar), or withdraw the causal language and report the gap as a descriptive observation with no driver interpretation.

### R3-07 — The cohort-level abstention-driver result rests on two declined cases, and is stated as an unhedged generalization.

> "This case study uses a deployment with threshold $\tau^* = 0.55$, answering 200 cases and declining 2." (§4.6)

Then, in the same subsection:

> "its mean absolute attribution is 0.868 on answered cases but 1.722 on declined cases" (§4.6)
> "Declines are **systematically** the cases where feature 0's pull leaves the decision contested" (§4.6, emphasis mine)

The declined-case mean is a mean over $n = 2$ — and both of those two cases are individually enumerated earlier in the same paragraph (indices 38 and 102). No standard error, no confidence interval, no replication, no permutation check is reported for the gap of $-0.854$ or for the "gap ranking $[0, 3, 2, 1, \dots]$". Every other headline rate in the paper is reported with an exact 95% interval over $R = 200$ draws (§4.1, §4.2, §4.3, §4.4); the one explainability result is reported with nothing. The word "systematically", and the Figure 5 caption's "dominant systematic abstention driver", are unhedged generalizations from two observations. This is the single most quotable weakness in my section of the paper, and it directly contradicts the manuscript's otherwise disciplined register. **Fix:** rerun E5 at an operating point that produces a non-trivial number of declines, aggregate over the same $R = 200$ replication design used elsewhere, and report the gap with an interval. If the gap does not survive, say so.

### R3-08 — §4.1 states a replication design that E5 and E6 do not follow, and the manuscript does not flag the exception.

> "**Replication design.** Every experiment runs in mode FULL under protocol seed 20260721, over the $\alpha \in \{0.05, 0.10\}$ ladder at confidence $1-\delta$ with $\delta = 0.05$, and replicates over $R = 200$ independent calibration draws." (§4.1)

E5 is "a deployment with threshold $\tau^* = 0.55$" (§4.6) and E6 "uses a separate deployment (threshold $\tau^* = 0.77$; 40 target sites)" (§4.7) — singular deployments, one $\alpha$, no $R$, no intervals. Neither subsection reports a replication count and neither acknowledges departing from the stated design. So "every experiment ... replicates over $R = 200$" is not true as written, and the two experiments it is false for are exactly the two carrying the explainability and composition claims. **Fix:** either replicate E5/E6 under the stated design, or amend §4.1 to say which experiments are single-draw case studies and why, and mark every number in §4.6/§4.7 as single-draw.

### R3-09 — Explanation quality is never evaluated. Faithfulness and plausibility are not distinguished; the words do not occur in the manuscript.

I searched the manuscript for "faithful", "plausib", "user study" and "human evaluation": **zero occurrences of each.** There is no faithfulness protocol (no deletion/insertion or retrain-and-evaluate test), no plausibility protocol (no expert agreement, no ground-truth-rationale comparison), and no sanity check of any kind. The only quantitative statement offered as evidence about the explanations is:

> "The global standardized importances recover the generator: features 0–3 dominate at 1.157, 1.161, 1.178, and 1.155, while features 4–7 are negligible ($|\cdot| \le 0.036$)." (§4.6)

Let me be precise about what this does and does not establish. It establishes that the **fitted logistic regression recovered the generative signal**. That is a statement about model fit, not about explanation quality. And in this setting the two cannot be separated, because the "explanation" is an algebraic identity on the fitted coefficients: if the model recovers the signal, the attributions recover it too, necessarily. Faithfulness is therefore true *by construction* and the check is vacuous as explanation evidence; plausibility is untouched, because plausibility is a property of how a human reads the explanation and no human is involved. The distinction the manuscript needs, and never draws, is the one set out in Jacovi & Goldberg, "Towards Faithfully Interpretable NLP Systems: How Should We Define and Evaluate Faithfulness?" (ACL 2020), and the evaluation taxonomy (functionally-grounded / human-grounded / application-grounded) in Doshi-Velez & Kim, "Towards A Rigorous Science of Interpretable Machine Learning" (2017). Neither is cited.

The recovery check is also very low-power on its own terms: four coefficients within 0.023 of each other against four near-zero ones is a ground truth that any method assigning nonzero weight to informative features passes. **Fix:** at minimum, add a functionally-grounded protocol on the *abstention* explanation specifically (does the declined-case explanation predict which perturbations flip the case into the answer region?), and state explicitly which evaluation tier is and is not attempted.

### R3-10 — No human evaluation, and no feature in the manuscript carries clinical meaning, so the clinician-facing claim is entirely undemonstrated.

The paper's framing is clinician-facing:

> "routing the hard ones to a clinician [@chow1970reject; @elyaniv2010selective]. The promise attached to such a gate is a bound on the error rate among the cases it chose to answer, holding with high confidence — what a clinician weighs before trusting an automated triage, and what an auditor asks to see documented." (§1)
> "otherwise it abstains and defers the case to human judgment." (§3.1)

Yet every feature in the manuscript is an index: "$d = 8$ features", "features 0–3 are informative and features 4–7 are noise" (§4.1); the case studies identify features by number. So the artefact a clinician would receive on a declined case is a margin in logit units plus signed weights on unnamed synthetic covariates. Nothing in the manuscript establishes that this is interpretable, actionable, or at the right granularity for a deferred clinical case; no clinician, and no human of any description, is reported to have looked at one. The absence of human-subject evaluation is defensible in a synthetic-first paper — but then the clinician-facing rhetoric must come down accordingly, and the manuscript must say that no human evaluation was performed. It currently says neither. **Fix:** add an explicit statement that no human evaluation was conducted and that clinical actionability is unestablished; downgrade §1's assertions about what clinicians weigh (which are also uncited — see R3-33).

### R3-11 — The explanation contribution does not survive the model-agnostic framing the paper simultaneously claims.

> "The gate itself is model-agnostic: the score only *ranks* cases ... A stronger black-box head can be substituted at a visible cost in coverage; we use logistic regression here because the explainability requirement, not the certificate, calls for a transparent head." (§3.8)
> "A black-box head can be swapped in; the gate would then price its selective quality visibly, as a change in certified coverage" (§5.3)

If a black-box head is swapped in, the exact-attribution property is gone, the abstention explanation loses its decomposition, and the paper's entire third contribution evaporates — yet §5.3 discusses only the coverage cost of the swap and is silent on the explanation cost. For a submission to a collection built around explainability, "our explainability contribution holds only in the configuration we happened to deploy, and the paper elsewhere recommends a configuration in which it does not hold" is a structural problem, not a detail. **Fix:** §5.3 must state what explanation the system provides under a black-box head (KernelSHAP on the head? nothing?) and what is lost; or the model-agnostic claim must be scoped to the certificate only, with an explicit statement that the explainability claim is not model-agnostic.

### R3-12 — The explainability case study runs at the loosest threshold on the grid, where abstention barely occurs, and never states whether that deployment was certified.

> "This case study uses a deployment with threshold $\tau^* = 0.55$, answering 200 cases and declining 2." (§4.6)

$\tau^* = 0.55$ is the minimum of the threshold grid ("a grid of 23 values evenly spaced in $[0.55, 0.99]$", §3.5). The resulting coverage is $200/202 \approx 0.990$, which is not an operating point reported anywhere else in the paper (E1 reports 0.9722, E6 uses $\tau^* = 0.77$ at $\approx 0.90$ coverage). So the *abstention*-explanation experiment is conducted at the operating point where abstention is rarest — which is both why $n_{\text{declined}} = 2$ (R3-07) and why the case study is least representative of deployment. Nor does §4.6 state that this threshold was certified, under which mode, or at which $\alpha$. Given that "attachment to a *certified* decision" is the stated novelty (R3-03), the demonstration does not demonstrate the claim. **Fix:** run E5 at the certified deployed threshold from E1 or E6, state the mode and $\alpha$, and report the certification status of the exhibited threshold.

### R3-13 — The title, abstract and keywords bill explainable abstention as a co-headline contribution; the body demotes it to "nearly free". Given this collection, the editors need this resolved explicitly.

Title: "...with label-shift robustness and **explainable abstention**." Keywords: "Explainable abstention". Abstract: "so the gate can explain what it refuses as well as what it predicts."

Body: "This supports the certificate above rather than standing as an independent method (E5)" (Contribution 3); "a supporting capability the linear head makes nearly free" (§3.8); "**This is the central contribution**" — of Contribution 1, the certified gate.

**My direct answer to the question the editors will ask:** explainability in this paper is **ornamental to the method and integral only to the framing.** Delete §3.8, §4.6 and Figure 5 and nothing else in the paper changes — no certificate, no bound, no experiment E1–E4, no limitation. Nothing in the statistical machinery consumes an attribution. The one place explanation-adjacent output feeds back into the argument is the three-way composition analysis (§4.7), and that is an audit diagnostic, not an explanation (and see R3-19). The paper is, in substance, a certified-selective-prediction paper with an interpretable head. That is a real paper. It is not, on its current evidence, an explainability paper, and for a collection whose central emphasis is explainability that mismatch is the fit question. **Fix:** either invest in the explanation layer to the point where it earns the title (evaluation protocol, a defined abstention-explanation quantity, non-trivial $n$, human or task-grounded assessment), or retitle and re-abstract so that the explanation layer is presented as a design property of the deployed head rather than a contribution.

### R3-14 — The clinical-XAI literature is absent, including work directly adversarial to the paper's framing.

The manuscript makes clinical-explainability claims and cites, for explanation, only Lundberg & Lee (2017), Artelt et al. (2022), Lenders et al., and Punzi et al. Not cited, and all directly on point:

- **Ghassemi, Oakden-Rayner & Beam, "The false hope of current approaches to explainable artificial intelligence in health care" (*Lancet Digital Health*, 2021)** — argues that feature-attribution explanations do not deliver the trust and auditability claimed for them in clinical settings. This is the single most important missing citation: a paper asserting "what a clinician weighs before trusting an automated triage, and what an auditor asks to see documented" (§1) must engage the standing counter-argument. Not engaging it will read to a clinical-informatics editor as unawareness.
- **Tonekaboni, Joshi, McCradden & Goldenberg, "What Clinicians Want: Contextualizing Explainable Machine Learning for Clinical End Use" (MLHC 2019)** — the empirical study of what clinicians actually require from explanations; it would supply the evidence base §1 currently asserts without one.
- **Rudin, "Stop explaining black box machine learning models for high stakes decisions and use interpretable models instead" (*Nature Machine Intelligence*, 2019)** — this one *supports* the paper. §3.8's decision to deploy a transparent head "because the explainability requirement, not the certificate, calls for a transparent head" is precisely Rudin's argument, and citing it would convert an unanchored design choice into a positioned one.

**Fix:** cite and engage all three; the Ghassemi et al. engagement should be substantive, not a courtesy citation.

### R3-15 — The closest prior art on explaining *uncertainty-driven* rejection is missing.

The paper's distinctive claim is explaining *why the system declined* when the decline is caused by low confidence. The closest existing work is:

- **Antorán, Bhatt, Adel, Weller & Hernández-Lobato, "Getting a CLUE: A Method for Explaining Uncertainty Estimates" (ICLR 2021)** — explains *why a model is uncertain about this input* by finding the minimal change that would make it certain. This is exactly the abstention-explanation problem, solved contrastively rather than by attribution, and it is not cited. Its existence bears directly on the manuscript's claim to be doing something reject-option explanation work does not.
- **Wachter, Mittelstadt & Russell, "Counterfactual Explanations Without Opening the Black Box" (Harvard JL & Tech, 2018)** — the canonical counterfactual/recourse form, which is the natural answer to "what would have to be true for this case to be answerable?" — a question a clinician receiving a deferral would actually ask, and which the paper's margin-plus-attribution artefact does not answer.

**Fix:** cite both, and state why attribution rather than a contrastive form was chosen for the declined case — noting that the counterfactual form is arguably strictly more actionable here (see R3-16).

### R3-16 — The positioning against Artelt et al. survives on the guarantee axis but not on the actionability axis, and the manuscript only argues the axis it wins.

> "Reject-option explanation methods [@artelt2022reject; @ifac2025abstainexplain; @l2lore2025] attach no statistical guarantee to the decision; CertGate's difference is exact attributions on a certified gate." (§2.4)
> "extending reject-option explanation work that carries no statistical guarantee" (Contribution 3)

Artelt, Visser & Hammer's "Model Agnostic Local Explanations of Reject" (ESANN 2022) produces *contrastive/counterfactual* local explanations of a reject — statements of the form "this would not have been rejected if …". That is a strictly more actionable artefact for a deferred case than a signed weight vector plus a margin. The manuscript compares only on the axis where it wins (statistical guarantee) and does not acknowledge the axis where the cited prior art is ahead (explanation form and actionability). A reader who knows Artelt et al. will notice. **Fix:** state the trade honestly — "prior reject-option explanations are contrastive and more directly actionable but carry no guarantee; ours are additive and carry a site-level certificate on the gate that produced them" — which is a defensible and more credible positioning than the current one.

### R3-17 — The Limitations section lists six limitations and not one of them concerns explanation.

§6.1 lists: concept shift, excluded covariate-shift mode, no out-of-support screen, unmodelled temporal correlation, missingness without a positivity diagnostic, and the BBSE bootstrap's asymptotic step. Every one is statistical. Absent: no evaluation of explanation quality; no human evaluation; the independence assumption behind the exactness claim (R3-01); the loss of the explanation layer under a black-box head (R3-11); the $n=2$ basis of the abstention-driver result (R3-07); the absence of any clinical semantics for the explained features (R3-10). For a submission whose title advertises explainable abstention to a collection centred on explainability, a limitations section that is silent on explainability is a conspicuous asymmetry — especially given the manuscript's stated posture: "Its posture throughout is disclosure" (§6). **Fix:** add an explainability paragraph to §6.1 covering at least the exactness assumption, the absence of explanation-quality evaluation, and the absence of human evaluation.

### R3-18 — The collection's educational framing is not engaged at any point.

The Collection frames XAI both as a transparency requirement and as an **educational aid for clinicians**, and one of the two Collection editors works specifically on XAI education. The manuscript contains no occurrence of "education", "training", "human-centered/human-centred", "workflow", or any discussion of how a clinician learns from, is trained by, or builds a mental model of the gate. Its only human-facing sentences are "routing the hard ones to a clinician" (§1) and "defers the case to human judgment" (§3.1). Even the composition analysis, which is the artefact most plausibly useful for teaching a clinician *what kind of case the gate systematically avoids* (§4.7: "the gate earns its low error by answering predominantly easy negatives and abstaining where positives concentrate"), is framed purely as an internal audit. **Fix:** a short subsection on what the abstention explanation and composition profile teach a clinician about the model's competence boundary would engage the collection's framing at low cost, and the material for it is already in §4.7.

### R3-19 — The one explanation-adjacent artefact that is genuinely load-bearing works only in the synthetic harness, so the auditability it provides does not transfer to deployment.

> "A fourth artifact guards against a subtler failure. The answered-set class composition is reported three ways — the predicted-class positive fraction (estimated), the BBSE-implied true-class fraction (estimated, and tagged with its label-shift assumption), and the oracle true-class fraction (available in the synthetic harness only)" (§3.8)
> "But without the oracle column one could not confirm the certificate was not being earned by hiding a large positive load" (§4.7)

The second quotation is the manuscript stating, in its own words, that the guard fails without oracle labels — i.e. in every real deployment. So the artefact the paper presents as protecting against a certificate "earned by answering only easy negatives" is unavailable exactly where it would matter. This is honest, and I credit the honesty, but it means the deployment-time audit story is thinner than §3.8 implies. It also interacts with R3-13: this is the one artefact in the explainability section that does real work, and it does not survive the transition to real data. **Fix:** state in §3.8 (not only in §4.7) that the third column is harness-only, and discuss what a real-deployment substitute would be — e.g. a prospectively labelled audit sample of the answered set.

---

## Minor points

### R3-20 — Register: "exact" and "genuine" are repeated past the point of usefulness for what is a tautology.

"exact feature attribution" (Abstract); "exact linear attributions" (§1); "Exact explanations attached to every certified decision" (Contribution 3 heading); "exact additive attributions" (§2.4 as "exact attributions", §3.8, §4.6); "exact Shapley values" (§3.8); "genuine Shapley values, not sampled approximations" (§4.6). The contrast in the last one — drawn against KernelSHAP — flatters a property that follows from choosing a linear model, and reads as the paper marketing an identity. This is the one place where the manuscript's otherwise restrained register slips. Suggest reducing to one statement of exactness with its assumption attached, and deleting "genuine ... not sampled approximations".

### R3-21 — Standardized coefficients are described as giving "strength of each feature", which is a feature-importance reading they do not support under correlation.

> "*Globally*, the standardized coefficients — the coefficients learned on standardized inputs — give the direction and strength of each feature." (§3.8)

A standardized coefficient is a conditional effect given the other features in the model, not a marginal importance; under correlated inputs the two diverge, and the manuscript then uses these coefficients as ground-truth-recovery evidence (§4.6). Recommend "the direction and magnitude of each feature's conditional effect".

### R3-22 — Undefined symbols in the attribution definition.

> "$\phi_j(x) = w_j(x_j - \mu_j)$ with $\text{logit}(\hat{p}(x)) = \text{base} + \sum_j \phi_j$" (§3.8)

$\mu_j$ is never defined (training-split feature mean, presumably — $\text{sd}_j$ *is* defined in the same sentence, which makes the omission more conspicuous), and "base" is never defined (intercept plus $\sum_j w_j\mu_j$, presumably). Define both.

### R3-23 — Internal artefact keys leak into the prose.

> "(gap $-0.854$; gap ranking $[0, 3, 2, 1, \dots]$; top gap feature 0)" (§4.6)

"gap ranking" is undefined, the ellipsis silently hides features 4–7, and "top gap feature 0" reads as a serialized output field rather than a sentence. Same pattern at §4.4: "(`tilt_pushes_risk_above_alpha` true)" and "reason `e3-control-not-poisonous`". Recommend expressing these in prose.

### R3-24 — The Figures section contains captions only; no figure images are embedded or referenced.

The manuscript's "# Figures" section (lines following "**Figure 1. E1 in-distribution validity.**") consists of six caption paragraphs. There is no image syntax, no file path, and no `.png`/`.pdf`/`.svg` reference anywhere in the document. I could not inspect Figure 5, which is the only figure in my remit, and my assessment of it rests entirely on its caption text. If figures were meant to be part of this submission, they are not in it; if they are supplied separately, the manuscript should reference them by file.

### R3-25 — Figure 5's caption omits the sample size behind its right panel.

> "Right: the answered-minus-declined gap in mean absolute attribution per feature; feature 0 shows the largest gap ($-0.854$; 0.868 answered vs 1.722 declined), identifying it as the dominant systematic abstention driver." (Figure 5)

The caption does not disclose that the declined side is two cases (§4.6). A reader seeing only the figure would take this for a cohort statistic. The caption must carry $n_{\text{answered}} = 200$, $n_{\text{declined}} = 2$.

### R3-26 — "At the cohort level" is undefined in E5.

§4.6 uses "cohort level" for a set of 202 records from an unstated number of sites over an unstated number of draws. Given that the whole paper turns on the site being the unit, an explainability statistic aggregated over an unspecified site structure should say how many sites contribute and whether the aggregation respects the site unit.

### R3-27 — Lenders et al. is mis-described by the sentence that cites it, and its fairness content — directly relevant to this collection — is left unengaged.

> "Reject-option explanation methods [@artelt2022reject; @ifac2025abstainexplain; @l2lore2025] attach no statistical guarantee to the decision" (§2.4)

The bibliography entry is Lenders, Pugnana, Pellungrini, Calders, Pedreschi & Giannotti, "Interpretable and Fair Mechanisms for Abstaining Classifiers" (ECML PKDD 2024). That work is centrally about *fairness constraints on abstention* — i.e. it does attach statistical properties to the reject decision, just not risk-control ones. The citing sentence therefore does not accurately characterise the cited work. This matters twice over: fairness is on the collection's explicitly encouraged list, and §4.7 scopes CertGate's equity analysis narrowly ("The equity question here is scoped narrowly to site size ... demographic and protected-attribute subgroup analysis is beyond this synthetic harness"). The natural comparison — abstention that is systematically concentrated on certain subpopulations — is exactly Lenders et al.'s subject and is not engaged. Recommend correcting the characterisation and adding one sentence relating CertGate's abstention profile to fair-abstention work.

### R3-28 — Bibliography key/year mismatches.

`ifac2025abstainexplain` carries `year = {2024}` (ECML PKDD 2024); the key says 2025, and the "ifac" prefix does not correspond to the venue in the entry. `l2lore2025` carries `year = {2024}` (DS-LB 2024); the key says 2025. Keys are cosmetic, but citation keys that disagree with their own entries invite miscitation downstream; and if any in-text discussion implies a 2025 date it will be wrong.

### R3-29 — The reject-option lineage skips its modern canonical formulation and its survey.

§2.1 runs Chow (1970) → El-Yaniv & Wiener (2010) → Geifman & El-Yaniv (2017). Missing: **Cortes, DeSalvo & Mohri, "Learning with Rejection" (ALT 2016)**, the standard modern formulation with calibrated surrogate losses, and **Hendrickx, Perini, Van der Plas, Meert & Davis, "Machine Learning with a Reject Option: A Survey" (*Machine Learning*, 2024)**, which is the natural anchor for the lineage and includes discussion of explaining rejection. Their absence is noticeable in a paper whose title contains "abstention".

### R3-30 — The Shapley lineage is carried by a single citation.

The manuscript uses "Shapley values" as a technical term and cites only Lundberg & Lee (2017). Missing: **Shapley (1953)** for the solution concept itself; **Štrumbelj & Kononenko, "Explaining prediction models and individual predictions with feature contributions" (*Knowledge and Information Systems*, 2014)**, which introduced Shapley-value attribution for prediction models before SHAP; and **Kumar, Venkatasubramanian, Scheidegger & Friedler, "Problems with Shapley-value-based explanations as feature importance measures" (ICML 2020)**, which is the standing critique of exactly the interpretive move §4.6 makes when it reads attribution magnitudes as drivers (see R3-06).

### R3-31 — Learning-to-defer is absent although the system defers to a clinician.

§1 "routing the hard ones to a clinician" and §3.1 "defers the case to human judgment" place the paper adjacent to the learning-to-defer literature — **Madras, Pitassi & Zemel, "Predict Responsibly: Improving Fairness and Accuracy by Learning to Defer" (NeurIPS 2018)** and **Mozannar & Sontag, "Consistent Estimators for Learning to Defer to an Expert" (ICML 2020)** — which models the human the case is deferred *to*. CertGate's abstention is expert-agnostic (it never models what the clinician does with the deferred case), and saying so explicitly against this literature would be a cheap and honest scoping statement.

### R3-32 — Structural: "Three artifacts" followed by "A fourth artifact", the fourth reported under a different experiment.

§3.8 opens "Three artifacts make the gate explainable" and then adds "A fourth artifact guards against a subtler failure" two paragraphs later. That fourth artefact's results appear not in E5 (the explainability experiment) but in §4.7 under E6. Recommend either "Four artifacts" with the composition analysis reported in E5, or moving the composition artefact out of §3.8 into the validation section where its results live.

### R3-33 — §1's claims about clinician and auditor behaviour carry no citation.

> "what a clinician weighs before trusting an automated triage, and what an auditor asks to see documented" (§1)

Two empirical claims about human behaviour, both uncited. Tonekaboni et al. (2019) would support the first (with qualifications); the auditability claim needs either a regulatory or empirical anchor or should be softened to a design motivation rather than a statement of fact.

---

## Questions to authors

### R3-34
Give the exact formula for "the signed feature attributions of the confidence deficit" (§3.8). Since $m(x) = \mathrm{logit}\,\tau^* - |\text{base} + \sum_j \phi_j|$ is not additive in $\phi_j$, what quantity is being attributed, under what value function, and in what sense is it "exact"?

### R3-35
How many declined cases underlie the cohort-level statistic "mean absolute attribution ... 1.722 on declined cases" and the gap of $-0.854$ (§4.6, Figure 5)? If it is the two declined cases stated in the same subsection, what is the sampling variability of that gap, and does the ranking $[0, 3, 2, 1, \dots]$ survive replication over the $R=200$ design used elsewhere?

### R3-36
Was the E5 deployment threshold $\tau^* = 0.55$ certified — under which assumption mode, at which $\alpha$, and on which calibration draw? If it was not certified, on what basis does E5 demonstrate "the attachment of explanation to a *certified* decision" (Contribution 3)?

### R3-37
Are the eight generator features mutually independent, marginally and class-conditionally? Given that the class signal is placed on a shared direction over coordinates 0–3 (§4.1), please report the empirical correlation matrix and state which Shapley value function (interventional/marginal versus conditional/observational) the exactness claim in §3.8 refers to.

### R3-38
What, concretely, does a clinician see when a case is declined — the margin in logit units, a ranked $\phi_j$ list, a natural-language template, something else? Has any clinician, or any human evaluator, ever been shown one of these artefacts, and if not, on what basis is the abstention explanation described as clinician-facing?

### R3-39
Under the black-box head that §5.3 says "can be swapped in", what explanation does the system produce for an abstention, and does Contribution 3 survive that substitution? If it does not, should the model-agnostic claim and the explainability claim be presented as mutually exclusive configurations?

### R3-40
Do the answered and declined populations differ systematically in ways that would matter for equity beyond site size — for example, does abstention concentrate on the positive class? §4.7's composition analysis suggests it does ("abstaining where positives concentrate"), which is an abstention-fairness result the explanation section could report directly. Why is it not framed that way?

---

## Confidential comments to the editor

### R3-41
My blunt reading: this is a competent certified-selective-prediction paper wearing an explainability title because the collection asks for one. The explanation layer contributes no method — it is the algebraic read-out of a deliberately chosen linear model — and the manuscript, to its credit, admits as much in the body ("a supporting capability the linear head makes nearly free") while the title, abstract and keywords say otherwise. If the statistical referees find the core sound, my recommendation would be to require the authors either to earn the title or to change it. I would not accept it with the current billing.

### R3-42
The single result I most suspect is the "dominant systematic abstention driver" (§4.6, Figure 5). The declined set is two cases, both enumerated by index in the same paragraph, and the generator gives features 0–3 near-identical coefficients (1.157, 1.161, 1.178, 1.155) — so there is no mechanism by which feature 0 should differ. I cannot prove it is noise from the manuscript alone, because no variance, interval or replication is reported for it — uniquely among the paper's quantitative claims. My working assumption is that it will not survive replication, and I would make replication a condition of revision rather than a suggestion.

### R3-43
Related and, to me, more troubling as a matter of manuscript discipline: §4.1 asserts that "**Every experiment** runs ... and replicates over $R = 200$ independent calibration draws", and both E5 and E6 are single deployments with no replication count and no intervals. The rest of the paper is scrupulous about intervals — Clopper–Pearson everywhere, a rule-of-three sanity check in E2. The two unreplicated experiments being precisely the two in my remit is either coincidence or a signal about where the effort went. I flag it because if a reader spots it after publication it reads as overstatement rather than oversight.

### R3-44
The word "exact" appears seven times attached to the attributions, plus "genuine Shapley values, not sampled approximations". For a linear model this is an identity, not an achievement, and it is stated without the feature-independence assumption that Lundberg & Lee's linear result requires — on a generator that appears to violate that assumption. I do not think this is deceptive; I think the authors have not read the dependence literature (Aas et al. 2021; Chen et al. 2020). But it means the paper's most-repeated explanation claim is, as written, technically unsupported, and that is a poor look in a collection whose editors will be reading the XAI content closely.

### R3-45
Collection fit, since you will need a judgment: on the venue card's *encouraged* list this paper scores well on uncertainty quantification, calibration-adjacent work, OOD robustness (label shift), and clinical auditability. On the *central emphasis* — explainability — it scores poorly on substance and is silent on the educational framing that one of your two Collection editors specialises in. My honest view is that the paper's fit is real but sits on the encouraged list rather than on the central emphasis, and the authors have papered over that by putting "explainable abstention" in the title. A revision that (a) evaluates the abstention explanation properly, (b) engages Ghassemi et al. (2021) and the clinician-facing literature, and (c) adds even a short treatment of what the gate teaches a clinician about its own competence boundary, would move it onto the central emphasis legitimately.

### R3-46
I could not see the figures. The submitted manuscript contains six caption paragraphs and no images or image references. My assessment of Figure 5 is based on its caption alone. If the figures exist and were simply not included in what I received, that should be corrected before the next round; if they do not exist, then the explainability evidence in this paper is currently unreviewable and no referee should be asked to sign off on it.

---

## Recommendation

**Major revision.**

The paper belongs at this venue and in this collection's neighbourhood: cluster-robust uncertainty quantification, label-shift robustness and clinical auditability are all explicitly encouraged, and the disclosure-first posture around the certificate is exactly the register a clinical-ML collection should reward. But the collection's *central emphasis* is explainability, and on that axis the submission does not currently hold up. It contributes no explanation method and says so only in subordinate clauses while the title and abstract promise otherwise (R3-13); its exactness claim omits the assumption it depends on, on a generator that appears to violate it (R3-01); the abstention-explanation quantity that constitutes its distinctive claim is never defined and is not exactly decomposable (R3-04); the explanation that is actually demonstrated collapses into the margin number it was meant to unpack (R3-05); explanation quality is never evaluated by any protocol, with faithfulness and plausibility never distinguished and no human ever consulted (R3-09, R3-10); and the one quantitative explainability result rests on two declined cases at the loosest threshold on the grid, in an experiment that silently departs from the paper's own replication design (R3-07, R3-08, R3-12). The clinical-XAI literature that would situate all of this — Ghassemi et al., Tonekaboni et al., Rudin, Jacovi & Goldberg, Antorán et al. — is absent (R3-09, R3-14, R3-15). None of this is fatal: the fixes are a defined deficit attribution, a properly replicated E5 at a certified threshold, an evaluation protocol that names which tier it attempts, an honest re-billing of the explanation layer, and roughly a dozen citations. That is a major revision, not a rejection, and I would be willing to see it again.
