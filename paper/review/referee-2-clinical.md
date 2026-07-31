# Referee 2 report — clinical / deployment

**Manuscript:** *CertGate: finite-sample certified selective prediction for multi-site clinical risk models, with label-shift robustness and explainable abstention*
**Venue:** *Discover Computing* — Collection "Intelligent Medicine: ML and Explainable AI for Next-Generation Healthcare"
**Reviewer role:** clinician-informatician; multi-hospital model deployment and model-governance committee

---

## Summary

The paper proposes a wrapper around an already-deployed binary risk model. The wrapper picks a confidence threshold; cases above it get an automated answer, cases below get handed to a person. The claim attached to that wrapper is a certificate: with probability ≥ 1−δ over the draw of calibration *sites*, an influence-weighted error rate among the answered cases at a target site is ≤ α. The statistical machinery is a per-site bounded atom fed to a Waudby-Smith–Ramdas betting martingale, a fixed-sequence threshold walk to avoid δ-splitting across a 23-point threshold grid, and a second "assumption mode" in which BBSE corrects for a shift in outcome prevalence and a cluster bootstrap box over the confusion parameters is tested at its two endpoints so that the correction's own estimation error is charged against the confidence budget. Because the deployed head is L2 logistic regression, every answered and every declined case carries an exact additive attribution, which the paper offers as its explainability layer. Evaluation is entirely on a synthetic 208-site cohort: eight Gaussian-ish features (four informative), 9.5% base prevalence, lognormal site sizes clipped to [20, 5000], and a site random effect on the outcome log-odds. Six experiments report in-distribution validity, a label-shift comparison, a concept-shift negative control, a site-count sweep, an explainability case study, and a per-site-coverage / answered-set-composition study.

My assessment: as a piece of statistical engineering this is careful, and the disclosure discipline (the five guarantee clauses in §3.7, the two-number violation protocol, the explicit concept-shift exclusion, the limitations list in §6.1) is better than most of what crosses my desk. But the paper is a statistics paper wearing clinical clothes, and it is submitted to a *clinical* collection. There is no outcome, no time horizon, no clinical decision threshold, no confusion matrix, no calibration, no net benefit, no fairness beyond site size, no reporting-guideline conformance, and no account whatsoever of what happens to the patients the system declines to answer — which, on the paper's own Table 2 and Table 3 numbers, is where roughly 40% of the cohort's outcomes are sitting. Two findings below are, in my view, disqualifying in their present form: the certified quantity is a site-averaged error rate that the abstract states as a patient-level one (R2-04), and the certified quantity is a symmetric 0-1 error at 9.5% prevalence whose α = 0.10 budget is barely below the no-skill rate (R2-07). Neither is unfixable, but both require the authors to say plainly what the certificate does *not* bound.

---

## Major points

### R2-01 — "Decline" names two operationally unrelated events, and the paper never separates them

> "otherwise it abstains and defers the case to human judgment" (§3.1)
> "BBSE declines the remaining 95.5% of draws (decline rate 0.955) rather than issue an unsupported certificate" (§4.3)
> "The stricter $\alpha = 0.05$ rung certifies nothing at 208 sites (certify rate 0.0): the system declines rather than issue a certificate it cannot support at this cluster count." (§4.2)

These are two different failures and they land on two different people. The first is *per-case abstention*: ~3% of patients (E1 coverage 0.9722) or ~10% (E6, τ* = 0.77) route to a clinician who was going to see the chart anyway. That is a workflow cost. The second is *whole-certificate decline*: the gate cannot be licensed at all, so the hospital gets no automated triage for anybody. That is a service outage. The manuscript uses "decline" for both, and reports the second as a virtue ("declining honestly", in effect) without a single sentence on what the deploying institution does the morning it happens. Please introduce distinct terms (e.g. *abstain* vs *withhold certification*), and add an operational paragraph: on a whole-certificate decline, does the site fall back to the uncertified model, to no model, or to the prior standard of care? §3.6 says "There is no shrinkage and no fallback to the uncorrected baseline anywhere: a decline is the only alternative to a certificate" — that is a statistical statement; the clinical statement it implies (all patients revert to unaided human triage) is nowhere.

### R2-02 — A 95.5% whole-certificate decline rate is presented as a result, not as an operational failure

> "BBSE declines the remaining 95.5% of draws (decline rate 0.955) rather than issue an unsupported certificate, and both modes decline entirely at $\alpha = 0.05$." (§4.3)

Read as a deployment fact this says: under a prevalence shift of the size the paper itself calls routine ("a near-tripling of outcome frequency of the kind that a change in referral pattern or case mix produces", §4.3), the certified system is unavailable 19 times out of 20. A committee weighing whether to license this would immediately ask whether a tool that goes dark under ordinary case-mix drift is worth building the workflow around. The paper never asks. Safety and availability are both requirements; the manuscript optimises one and does not report the other as a cost. At minimum, state the decline rate as a limitation in §6.1 and say what operating regime (how much prevalence drift, at how many sites) keeps the system available.

### R2-03 — BBSE's safety claim rests on 9 certifications, and the paper's headline framing hides the denominator that matters clinically

> "The joint event that matters operationally — a certificate issued *and* hard-violating — occurs 0 times in 200 draws (exact 95% CI $[0, 0.018]$, consistent with the rule-of-three bound $3/200 = 0.015$; both below $\delta$); conditioning on the 9 draws that did certify ($n_{\text{certified}} = 9$), the hard-violation rate among them is 0.0." (§4.3)

To the paper's credit both numbers are given. But the abstract and §1 report only the joint event ("the corrected mode never does"; "never certifies *and* violates (the joint event is 0 of 200 draws)"), and the joint event is trivially small when the certify rate is 4.5%. What a hospital needs to know is: *given that CertGate issued a certificate, how often is it wrong?* The evidence for that is 0/9. Rule of three on the correct denominator is 3/9 = 0.33 — i.e. the manuscript's own data are consistent with a one-in-three conditional violation rate. The [0, 0.018] interval quoted in §4.3 is an interval on the joint event and must not be allowed to do the conditional's work. Please report the conditional Clopper–Pearson interval (0/9 → [0, 0.336]) beside the joint one everywhere the claim appears, including the abstract, and say explicitly that the conditional claim is underpowered at this replication.

### R2-04 — The certified object is a site-averaged error rate; the abstract states it as a patient-level one

> "certifies, with finite-sample confidence $1-\delta$, that the error rate among answered cases stays at or below $\alpha$" (Abstract)
> "a bound on the error rate among the cases it chose to answer" (§1)
> "each site receives a *data-independent* influence weight $g_c = \min(n_c, M)$ with $M = 100$" (§3.3)

With lognormal site sizes (log-mean 6.0 → median ≈ 400 records) clipped to [20, 5000], essentially every site hits the M = 100 cap. So $R_M$ is, to a very good approximation, an unweighted average of per-site answered error, and a patient at a 5,000-record site contributes 1/50 of the weight of a patient at a 100-record site. That is a legitimate estimand — but it is *not* "the error rate among answered cases", which is what the abstract and introduction promise and what any clinician or governance officer will read.

A worked case: suppose 42 large sites (3,000 records each) run 20% answered error and 166 small sites (100 records each) run 2%. The certified quantity is (42×0.20 + 166×0.02)/208 ≈ 0.056 — comfortably certified at α = 0.10 — while the error rate actually experienced by answered patients is (42×3000×0.20 + 166×100×0.02)/142,600 ≈ 0.18. The certificate holds and 18% of answered patients are misclassified. Nothing in the manuscript rules this out, because nothing in the manuscript reports patient-weighted answered error or per-site dispersion.

Compounding this, §3.3 contains a sentence I read as actively misleading:

> "The cap acts on influence only: it scales each site's whole signed contribution and never censors the error itself, so a site that answers many cases badly still enters at full adverse weight."

"Full adverse weight" here means full *capped* weight, which for a 5,000-record hospital is 2% of its patient share. Please (a) carry "influence-weighted" into the abstract and §1 sentences, (b) state in one sentence that $R_M$ is close to a per-site average and does not bound the error rate the average answered patient faces, (c) report the record-weighted answered error alongside $R_M$ in E1 and E6, and (d) reword the "full adverse weight" sentence.

### R2-05 — The abstention burden falls on the patients most likely to have the outcome, and the paper names this as a feature

> "the gate earns its low error by answering predominantly easy negatives and abstaining where positives concentrate. That is not a defect; it is what a selective gate on a low-prevalence task should do." (§4.7)

Take the paper's own numbers. E6 answers 23,325 records containing 1,470 true positives (Table 3). Per-site coverage is 0.897–0.919 (Table 2), so the deployment is roughly 25,900 records; at 9.5% base prevalence the cohort holds ≈ 2,460 positives. That leaves ≈ 2,575 declined records carrying ≈ 990 positives — a declined-set prevalence near 38%, and roughly **40% of all the cohort's outcomes sitting in the 10% of patients the system refuses to score**.

Statistically this is exactly what a confidence gate does. Clinically it is the central fact about this system and the paper does not compute it. It means the automated component handles the easy well patients and the entire hard, high-yield fraction is handed back unassisted. It also means the *value* proposition is inverted relative to the motivating scenario in §1: a deterioration gate that abstains on the deteriorating patients has not reduced clinician workload where workload is expensive. And this is a fairness finding, not merely a utility one — systematic abstention concentrated on the sickest patients is a distributional harm even when the answered-set guarantee holds. Please compute and report the declined-set outcome prevalence and the declined-set count explicitly, and retract or heavily qualify "That is not a defect".

### R2-06 — The certified error is never defined, and no confusion-matrix metric appears anywhere

> "$$Z_c = \frac{g_c}{M\, n_c}\sum_{i \in c} \text{ans}_i\,(\text{err}_i - \alpha) + \alpha$$" (§3.3)

`err`$_i$ is the quantity the entire paper certifies and it is never defined. I infer 1{ŷ_i ≠ y_i} with ŷ the argmax, but the manuscript does not say so, does not say at what probability threshold ŷ is formed, and does not say whether false positives and false negatives are weighted equally. For a clinical audience that is not a notational lapse — it is the difference between a guarantee about missed deteriorations and a guarantee about spurious alerts.

Relatedly, the manuscript reports no sensitivity, specificity, PPV, NPV, AUROC, AUPRC, or confusion matrix, on the answered set or anywhere else. A clinical risk-model paper without a confusion matrix is not assessable. Please define `err` formally in §3.3 and add answered-set discrimination metrics to E1 and E6.

### R2-07 — α = 0.10 on symmetric 0-1 error at 9.5% prevalence is close to the no-skill rate, and the implied answered-set sensitivity is roughly one in two

> "the outcome prevalence is roughly 9–10%" (§3.1); "the mean answered error stays well below $\alpha = 0.10$ in every bin (0.0294, 0.0406, 0.0348)" (§4.7)

A classifier that predicts "no event" for every patient achieves 9.5% error on this cohort. The headline budget α = 0.10 is therefore *above* the trivial baseline, and §5.2's defence of it —

> "For any reader tempted to call $\alpha=0.10$ a weak guarantee: the operative rung is a property of the available cluster count, not of the method"

— answers a statistical objection with a statistical reply while leaving the clinical objection untouched. Whether α = 0.10 is weak is a question about what error rate is acceptable for the outcome in question, and the site count cannot settle it.

Worse, the paper's own numbers let one back out what the answered-set classifier is actually doing. Table 3: 23,325 answered, 917 predicted-positive, 1,470 true positive. Take mean answered error ≈ 0.035 (Table 2) → ≈ 816 errors = FP + FN. Solving 917 − TP + 1470 − TP = 816 gives TP ≈ 786, FP ≈ 131, FN ≈ 684. That is **answered-set sensitivity ≈ 0.53** and, combined with R2-05's declined-set estimate, an overall cohort sensitivity near 0.32. The certificate is fully satisfied while the system misses roughly half the outcomes among the patients it *does* answer. This is precisely the pattern that has killed deployed deterioration and sepsis models, and the certificate as constructed is blind to it. Please either certify a clinically meaningful risk (a cost-weighted error, or a bound on FNR conditional on answering) or state explicitly, in §5.1 and in the guarantee text, that the certificate places no constraint on sensitivity.

### R2-08 — There is no outcome, no time horizon, and no prediction time

> "A deterioration or readmission score calibrated on patients from a handful of academic centers…" (§1)
> "we consider multi-site clinical data in which on the order of two hundred collection sites each contribute between 20 and 5,000 records" (§3.1)

Deterioration and readmission are named once, rhetorically, and never again. The evaluation has no outcome definition, no index event, no prediction time, no observation window, no follow-up horizon, no censoring, no competing risks, and no statement of the calendar period the 208-site cohort represents. Every one of these is a required element of a clinical prediction-model report (TRIPOD item set) and every one of them changes what the numbers mean. "208 sites × ~500 records" is a tiny registry if it is one year and a large one if it is ten, and the abstention workload in R2-11 cannot be sized without knowing which. A methods paper on synthetic data can legitimately decline to name an outcome — but then it must stop claiming the clinical framing in its title, abstract and introduction.

### R2-09 — The generator's site heterogeneity *is* label shift; the paper's "case mix" claims are not supported by the generator it describes

> "sites differ in both prevalence and case mix" (§3.1)
> "Site heterogeneity enters through a site random effect $u_c \sim \mathcal{N}(0, 0.5^2)$ that shifts each site's outcome log-odds, $\pi_c = \sigma(\mathrm{logit}(0.095) + u_c)$, so per-site prevalence varies around the 9.5% mark and no two sites share an identical case mix." (§4.1)

As described, features are drawn from class-conditional distributions that are identical at every site; only the mixing weight $\pi_c$ varies. So $P(x \mid y)$ is site-invariant *by construction*, and site heterogeneity in this cohort is exactly and only label shift. Two consequences.

First, "sites differ in … case mix" and "no two sites share an identical case mix" are false as written, unless "case mix" is being used to mean "class mix". In multi-site clinical work, case mix means the distribution of patients — comorbidity burden, acuity, demographics, referral pattern — not the outcome rate. Please fix the wording or the generator.

Second, and more seriously: the BBSE mode's core assumption ("the class-conditional feature distribution $P(x \mid y)$ is held invariant", §3.6) is true by construction in the only cohort on which it is evaluated. E2 is therefore a test under conditions the correction assumes. That is worth doing, but it cannot support any inference about behaviour under the site heterogeneity that actually breaks multi-site models: different instruments, assay platforms, EHR vendors, coding conventions, documentation habits, and care pathways, all of which move $P(x \mid y)$. Please add a generator arm with site-level $P(x \mid y)$ perturbation and report what BBSE does there — I expect it to be somewhere between E2 and E3, and the reader deserves to know where.

### R2-10 — The motivating scenario is the one scenario neither assumption mode covers

> "A deterioration or readmission score calibrated on patients from a handful of academic centers is deployed at a community hospital that contributed no training records" (§1)
> "A third assumption mode that reweights by feature-density ratios is not offered…" (§6.1)
> "*There is no out-of-support screen.*" (§6.1)

The opening scenario is an academic-to-community transfer. That is a covariate-shift problem before it is a label-shift problem: the community hospital's patients are systematically different, not merely differently prevalent. The paper excludes covariate-shift weighting by design, ships no out-of-support screen, and evaluates on a 40/20/40 *random* partition of sites drawn from one homogeneous generator — i.e. the split is exchangeable by construction, which is the opposite of the motivating case. The manuscript is honest about each of these individually in §6.1, but never connects them, so a reader finishes §1 believing the community-hospital problem is what CertGate solves. Please state in §1 or §5.1 that the exchangeable mode assumes the community hospital *is* exchangeable with the academic ones, that the BBSE mode relaxes only the prevalence part of that, and that the method offers no diagnostic by which the community hospital could check either.

### R2-11 — The realism claim is hung on two citations that cannot support it

> "This follows the distributional profile reported across multi-site clinical studies — many small-to-large sites with heavy-tailed sizes, single-digit prevalence, and site-level heterogeneity — while remaining fully known, in keeping with the cluster-as-unit reporting culture that motivates the design [@tripodcluster2023; @internalexternal2021]." (§4.1; same claim in the Abstract, "follow the distributional profile reported for large multi-site clinical cohorts")

`tripodcluster2023` is the TRIPOD-Cluster *reporting checklist* (Debray et al., BMJ 2023) and `internalexternal2021` is Takada et al. on internal–external cross-validation (J Clin Epidemiol 2021). Neither is a source for a lognormal(6.0, 1.1) site-size distribution, for a 0.095 base prevalence, or for a site random effect of SD 0.5 on the log-odds. A checklist tells you what to report; it does not report distributional parameters. This is the one place where the paper's whole claim to clinical realism is made, and the citations do not say what the sentence needs them to say. Either cite an empirical multi-site cohort (e.g. an IECV meta-analysis reporting between-site τ² for the outcome in question) that actually pins these values, or downgrade the claim to "chosen to be broadly consistent with, but not calibrated to, published multi-site cohorts" and say so in the abstract too. The 0.5 log-odds SD in particular needs a source or an explicit "arbitrary" label.

### R2-12 — No calibration reporting of any kind

The collection card names calibration explicitly, and the manuscript touches it only to dismiss its relevance:

> "the validity of the certificate never depends on the quality or calibration of the model producing that score" (§3.8)

True and well-put for *validity*. But the deployed head is a probability model, the gate thresholds a probability, the abstention explanation is expressed in logits, and the BBSE inversion depends on confusion rates that move with calibration. There is no calibration plot, no calibration-in-the-large, no calibration slope, no Brier score, no ECE, and — the one that matters for a multi-site paper — no per-site calibration. Van Calster et al.'s "Achilles heel" argument is the standard reference and is not cited. At this venue the absence is conspicuous. Add per-site calibration for the deployed head, at minimum in E6 where per-site quantities are already being computed.

### R2-13 — No net benefit, no decision-curve analysis, no asymmetric costs

The entire framework certifies a symmetric 0-1 error. In every clinical use the paper gestures at — deterioration, readmission, triage — a false negative and a false positive have costs differing by an order of magnitude or more. Nothing in §3.3, §3.5 or §5.1 acknowledges this, and no net-benefit or decision-curve analysis appears (Vickers & Elkin is the standard method and is not cited). Two questions the authors should answer in the text: (a) can $R_M$ be replaced by a cost-weighted risk without breaking the boundedness argument in Appendix A.1(i)? I believe it can, with a rescaled atom, and if so it is a cheap and highly venue-relevant addition; (b) if not, say so as a limitation.

### R2-14 — No reporting-guideline conformance, at a venue where it is expected

TRIPOD-Cluster is cited twice, but only as evidence that *other people* treat the site as the unit:

> "Clinical practice already treats the site as the unit — TRIPOD-Cluster [@tripodcluster2023] and internal–external cross-validation [@internalexternal2021] — but reports point estimates, not certificates." (§2.4)

The paper does not claim conformance to TRIPOD, TRIPOD+AI (Collins et al., BMJ 2024 — uncited), or DECIDE-AI (Vasey et al., Nat Med 2022 — uncited), and supplies no checklist. I accept that a synthetic methods paper cannot complete TRIPOD+AI in full. But it can (a) cite TRIPOD+AI as the standard its eventual real-data instantiation will be held to, (b) complete the items that *are* applicable (model specification, predictor definitions, sample size, missing data, model performance), and (c) state the items it cannot complete and why. As submitted, a reader cannot tell whether the authors know these guidelines exist. Given that a large fraction of the collection's readership will be clinicians, this is a real venue-fit cost.

### R2-15 — The paper's central object — the certificate — is never shown

The manuscript is about a certificate. It contains no example of one. §3.7 enumerates five clauses the guarantee text carries but never quotes the text; §3.10 and Appendix A.3 describe "a provenance block recording package versions, seeds, and input hashes", which is software metadata, not a clinical governance artifact.

I cannot assess auditability without seeing the artifact. Please add a figure or boxed exhibit showing one complete certificate exactly as a deploying site would receive it: the assumption tag, α, δ, the deployed τ*, the certified prefix, the calibration site count, the date, the five clauses in full sentences, and whatever decline reasons apply. This is the single highest-value addition the paper could make for this collection, and it costs one page.

### R2-16 — No recertification cadence, no monitoring plan, no expiry

The certificate is a statement over the draw of calibration sites at one moment. Real deployments drift — case mix, coding, care pathways, upstream data pipelines. §6.1 notes that temporal common-shock correlation is not modelled, but there is no statement anywhere of how often a certificate must be re-earned, what quantity a site monitors between recertifications, what threshold triggers re-certification, or whether a certificate expires. A model-governance committee cannot license something with no defined review interval. The continual-monitoring literature (e.g. Feng et al., npj Digital Medicine 2022, on continual monitoring and updating of clinical AI) is not cited. Add a paragraph in §5, even if the answer is "this is future work" — but say it.

### R2-17 — No regulatory or accountability framing

Nothing in the manuscript mentions software-as-a-medical-device / clinical decision support classification, the EU AI Act high-risk regime, algorithm-transparency requirements, local IRB or model-oversight review, or who is accountable when an *answered* case is wrong. Adding a gate that suppresses a model's output in some cases is a change to the intended use of the underlying tool and would be treated as such by any regulator. There is also no discussion of automation bias: a case marked "certified" is more likely to be deferred to uncritically by the clinician than an uncertified one, so the gate can *increase* harm on the answered set even while bounding its error rate. For a collection explicitly emphasising clinical auditability, a paragraph on each is the minimum.

### R2-18 — The certificate bounds a parameter; governance audits counts, and no bridge is offered

> "(3) It bounds the answered-set error parameter, not any single batch's realized error *count*, which exceeds $\alpha$ at binomial-dispersion rates even under a valid certificate." (§3.7)

This clause is correct, well-stated, and — for a hospital quality-and-safety committee — the crux of the whole paper's usability. A committee reviews realized events. On the paper's own E1 data the realized exceedance rate is 0.05 overall and 0.0551 in the largest size bin, against a hard-violation rate of 0.01. So a committee monitoring realized answered error at a site will see exceedances several times more often than the certificate is actually violated, and the manuscript gives them no rule for distinguishing the two. The Wilson-lower-bound criterion in §3.9 *is* such a rule — but it is presented as a validation-harness device, not as an operational monitoring procedure. Please promote it: state explicitly that a deploying site should audit with the one-sided Wilson bound, give the sample size at which that audit has useful power, and say what a site should do when the bound is exceeded.

### R2-19 — The cohort-level abstention-driver result is computed on two declined cases

> "This case study uses a deployment with threshold $\tau^* = 0.55$, answering 200 cases and declining 2." (§4.6)
> "At the cohort level, feature 0 is the dominant abstention driver: its mean absolute attribution is 0.868 on answered cases but 1.722 on declined cases, the largest answered-to-declined gap of any feature (gap $-0.854$; gap ranking $[0, 3, 2, 1, \dots]$; top gap feature 0). Declines are systematically the cases where feature 0's pull leaves the decision contested…" (§4.6)

The declined mean is a mean over n = 2. "At the cohort level", "systematically", a gap ranking over all eight features, and Figure 5's right panel all rest on two observations. This is the sole empirical demonstration of the capability §3.8 promises ("At the cohort level, the attribution profiles of the answered and declined populations identify systematic abstention drivers"), i.e. the sole evidence for contribution 3. It does not support the words attached to it. Rerun E5 at an operating point that produces a declined set large enough to characterise — the E6 deployment at τ* = 0.77 declines on the order of 2,500 records and would serve — and report dispersion, not just means.

### R2-20 — Fairness is scoped away, and the one fairness-titled reference in the bibliography is cited for something else

> "The equity question here is scoped narrowly to site size — whether small hospitals receive systematically worse selective service than large ones; demographic and protected-attribute subgroup analysis is beyond this synthetic harness." (§4.7)

"Beyond this synthetic harness" is not accurate. The harness has eight features chosen by the authors; nothing prevented one from being a protected attribute with a site-varying distribution, which would let the paper measure exactly the harm that matters — differential abstention rates and differential answered-set error across groups. The scoping is a design choice presented as a constraint.

This matters more than usual because the collection explicitly encourages fairness work, "fairness" does not appear in the keywords, and §2 has no fairness subsection. It also matters because the paper's own R2-05 result *is* a fairness result in disguise. Note further that `ifac2025abstainexplain` — "Interpretable and **Fair** Mechanisms for Abstaining Classifiers" (Lenders et al., ECML PKDD 2024) — is cited three times (§1, §2.4, §3.8, §4.6) purely for reject-option explanation, with its fairness content never engaged, even though it is the closest published work to the gap the authors are declaring out of scope. Madras, Pitassi & Zemel, "Predict responsibly: improving fairness and accuracy by learning to defer" (NeurIPS 2018) is the other obvious anchor and is absent.

### R2-21 — The site-size equity result rests on 40 sites, 4 of them in the smallest populated bin, with no dispersion reported

> "Coverage is essentially flat across bins — 0.9191, 0.8966, and 0.9063 … with no size-based coverage collapse (range 0.897–0.919; the smallest populated bin holds 4 sites), and the mean answered error stays well below $\alpha = 0.10$ in every bin (0.0294, 0.0406, 0.0348). Small sites are neither over-answered nor starved." (§4.7; Table 2)

Table 2 reports bin *means* over 4, 15 and 21 sites, with the [0,30) bin empty. The conclusion "Small sites are neither over-answered nor starved" is asserted from four sites. Worse, a bin mean conceals exactly the failure a governance committee cares about: a single site with 25% answered error or 40% coverage would be invisible here. Please report, per bin, the minimum coverage, the maximum answered error, and the number of sites whose answered error exceeds α — and report how many sites received zero coverage (see R2-27). Without the maximum, Table 2 cannot support any equity claim.

### R2-22 — The clinical-deployment and clinical-governance literatures are essentially absent

The bibliography's clinical content is two items (TRIPOD-Cluster; Takada et al. IECV) plus three 2026 preprints. For a paper whose title, abstract, introduction and §5.4–5.5 all trade on clinical deployment, that is not sufficient coverage. Closest work I would expect to see, none of it cited:

- **Wong et al., "External validation of a widely implemented proprietary sepsis prediction model in hospitalized patients", JAMA Intern Med 2021.** The canonical instance of the failure the paper's §1 invokes. Its positioning survives citation — indeed it strengthens the motivation — but its absence makes §1 read as hypothetical when it is documented.
- **Finlayson et al., "The clinician and dataset shift in artificial intelligence", NEJM 2021.** The clinical taxonomy of exactly the shifts §3.6 modes are built around. Its absence is why the paper's shift vocabulary reads as ML-native rather than clinically grounded.
- **Dvijotham et al., "Enhancing the reliability and accuracy of AI-enabled diagnosis via complementarity-driven deferral to clinicians" (CoDoC), Nat Med 2023.** This is the closest *clinical* selective-prediction / deferral system I know, evaluated on real cohorts. The draft's positioning as combining selective prediction with clinical deployment does not survive contact with it unaddressed — CertGate's distinction (a finite-sample cluster-level certificate) is real, but the paper must say so against CoDoC rather than against a literature of purely methodological reject-option papers.
- **Mozannar & Sontag, "Consistent estimators for learning to defer to an expert", ICML 2020; Raghu et al., "The algorithmic automation problem: prediction, triage, and human effort", 2019; Madras et al., NeurIPS 2018.** The learning-to-defer literature is the one that actually studies what happens *after* abstention — expert cost, complementarity, fairness of deferral. Its total absence is why R2-01 and R2-05 are open.
- **Sendak et al., "Presenting machine learning model information to clinical end users with model facts labels", npj Digit Med 2020.** Directly the artifact question of R2-15: what a clinician-facing model disclosure should contain. The paper is proposing a governance artifact and does not engage the existing proposal for one.
- **Obermeyer et al., Science 2019** (algorithmic bias in health), **Van Calster et al., BMC Med 2019** (calibration), **Vickers & Elkin, Med Decis Making 2006** (decision curves), **Collins et al., BMJ 2024** (TRIPOD+AI), **Vasey et al., Nat Med 2022** (DECIDE-AI), **Feng et al., npj Digit Med 2022** (continual monitoring), **Goddard et al., JAMIA 2012** (automation bias), **Futoma et al., Lancet Digit Health 2020** (the myth of generalisability — directly relevant to §5.4's cross-institutional framing), **Kompa et al., npj Digit Med 2021** (communicating uncertainty in medical ML).

I do not expect all of these. I do expect a clinical-deployment paragraph in §2 that engages at least the deferral, governance-artifact and reporting-guideline strands.

### R2-23 — The paper's motivating empirical claims are sourced entirely to unrefereed 2026 preprints, one of them from a different domain

> "a failure recently documented for record-level selective-risk rules under grouped deployment [@zhou2026falsesense] and prevalence shift [@triage2026audit]" (§1)
> "certified record-level selective-risk rules overrun their budget by 9–30% under grouped deployment [@zhou2026falsesense]" (§2.4)

`zhou2026falsesense`, `triage2026audit`, `yu2026joint`, `score2026`, `fedcrc2026` and `thermal2026audit` are all `@misc` arXiv entries from 2025–26 with no peer-reviewed venue (`fedcrc2026`'s note says "submitted to DeCaF Workshop"; `thermal2026audit`'s says "submitted to IEEE Transactions on Power Systems"). The quantitative "9–30%" figure that motivates the paper's core design decision rests on one of them.

Two consequences. First, that figure should be attributed in-text as a preprint result, not stated as established fact. Second, `zhou2026falsesense`'s title is "False Sense of Safety in Selective **Signal** Classification" — a signal-classification audit. §1 and §2.4 use it to license a claim about record-level selective-risk rules under *clinical* grouped deployment. If the underlying study is not clinical, the transfer must be argued, not assumed. Please state each preprint's status and say explicitly which of these results are clinical and which are not.

Separately:

> "The same certificate shape appears in power-grid contingency screening [@thermal2026audit], so it is not specific to medicine." (§2.4)

In a submission to a clinical-medicine collection, a sentence arguing the method is not specific to medicine works against you and adds nothing. I would cut it.

### R2-24 — "Exact Shapley values" omits the independence condition the cited source requires

> "For a linear model these attributions are exact Shapley values, with no approximation or sampling [@lundberg2017shap]." (§3.8; repeated in §4.6, "genuine Shapley values, not sampled approximations")

Lundberg & Lee's Linear SHAP result gives $\phi_j = w_j(x_j - E[x_j])$ **under an assumption of feature independence**. With dependent features the exact Shapley values differ, sometimes substantially. In this generator features 0–3 are marginally correlated through the class mixture (that is what makes them informative), and in any real clinical feature set the correlation is severe — creatinine and eGFR, heart rate and shock index, and so on. So as written the sentence claims more than the citation supports. Please add the independence condition, state whether it holds in the generator, and note the consequence for the real-data instantiation the paper promises in §5.5 — this is exactly where an explainability claim in a clinical XAI collection will be pressed.

### R2-25 — The explainability layer has never been seen by a clinician, and the collection's central emphasis is clinician-facing explainability

> "declined because feature A pulls toward positive while features B and C pull toward negative, leaving confidence below the certified bar." (§3.8)
> "A declined case (index 38, score 0.5262) sits just short, with a positive margin-to-answer of 0.0956 logit units; a near-threshold declined case (index 102, score 0.5445) is even closer, margin 0.0223." (§4.6)

This collection frames explainability both as a transparency requirement and as an educational aid for clinicians. The paper's explanations are attributions over eight anonymous synthetic features, reported as record indices and logit margins to four significant figures. No clinician has seen them; there is no comprehensibility evaluation, no actionability assessment, no user study, not even a mock-up of what the abstention message would look like in an EHR inbox. "Feature 0 is the dominant abstention driver" is not an explanation a clinician can use, and a margin of 0.0223 logits is not a quantity anyone at the bedside can act on.

I am not asking for a user study in this paper. I am asking for (a) one worked vignette in which the eight features are given plausible clinical names and the abstention message is written out as a clinician would receive it, and (b) an honest sentence in §5 saying that the explainability layer's clinical utility is untested. As submitted, the paper's third contribution is the weakest evidenced and it is the one the collection cares most about.

### R2-26 — "Real data cannot validate a validity claim" is an overreach used to excuse the absence of any external validation

> "Real data cannot supply that ground truth, which is what makes it unable to validate a validity claim." (§5.5)
> "The synthetic-first posture is a deliberate validation choice, not a deferral." (§5.5)

The first sentence is too strong. Real data cannot supply the true risk *parameter* $R_M$ — agreed. It can supply realized outcomes at held-out sites, from which one estimates violation rates by exactly the Wilson-bound procedure §3.9 already defines, over repeated site-disjoint splits. That is standard IECV practice and it is what the field means by external validation. As written, the sentence functions as a blanket argument that real-data validation is impossible in principle, which would excuse the paper from ever doing it.

I would accept a synthetic-only paper at this venue *if* the framing were: synthetic data is required to check the coverage property against oracle truth, and real data is required to check that the assumptions and the operating regime survive contact with a hospital — and we have done the first only. Please rewrite §5.5 to that effect and drop "not a deferral". Relatedly:

> "The route to real data is concrete: the implementation includes a `from_raw` loader and a worked example that carries a cohort through the same site-disjoint pipeline."

A data loader is not a route to real data. The barriers are outcome ascertainment, label latency, site count, governance approval and site heterogeneity — none of which a loader touches. Either describe the actual route (which cohort, how many sites, what outcome, what approvals) or delete the sentence.

### R2-27 — A site where the gate answers nobody is scored as exactly at budget

> "Sites with no answered-eligible records enter as *neutral* atoms $Z_c = \alpha$ rather than being dropped; dropping them would redefine the site population post hoc and quietly change the estimand." (§3.3)

The statistical reasoning is sound and I would not want it changed. But the deployment consequence is not stated anywhere: a hospital at which the system answers zero patients — a total service failure from that hospital's point of view — contributes to the certificate as though it were performing exactly at budget. A certificate can therefore be earned in part by sites at which the tool did nothing. Table 2's empty [0,30) bin means this case is never exercised in the reported results. Please (a) state this consequence in §3.7 or §5.1, and (b) report, in E1 and E6, how many sites received zero coverage.

### R2-28 — Every decline gate is statistical; none is clinical

> "There are three declines: (i) the worst-case confusion gap $(c_1 - c_0) < 0.10$ … (ii) fewer than 2,000 valid resamples within 4,000 attempts … and (iii) $q$ outside the box's $[c_{0,\text{lo}}, c_{1,\text{hi}}]$ range, meaning the implied prevalence leaves $(0,1)$ and BBSE is misspecified." (§3.6)

Gate (iii) only checks that the BBSE-implied target prevalence is a number between 0 and 1. Nothing checks that it is *clinically plausible*. A readmission cohort whose implied 30-day prevalence inverts to 0.55 is obviously wrong and would sail through this gate. A one-line plausibility band on $\pi_t$ — supplied by the deploying institution from its own historical rate — would be trivial to add and would be the first genuinely clinical safeguard in the pipeline. Gate (i)'s threshold, $c_1 - c_0 \geq 0.10$, is Youden's J at the operating point and is a very weak bar; please justify 0.10 or say it is arbitrary.

### R2-29 — The risk head is well-specified on its own generator, and no degradation sensitivity is reported

The head is L2 logistic regression fit on $S_\text{train}$ from the same linear-separable generator that produced the labels — i.e. the model class contains the truth. Real deployed risk models are misspecified, trained on an older era, miscalibrated at new sites, and frequently proprietary. §3.8 correctly notes that certificate *validity* does not depend on model quality, but every reported coverage number, the feasibility frontier in E4, and the whole utility case depend on it entirely. A single sensitivity arm — the same pipeline with a deliberately degraded or misspecified head — would tell the reader how much of E1's 0.9722 coverage is the gate and how much is the fact that the model is right by construction. Without it, the coverage numbers are upper bounds of unknown tightness.

---

## Minor points

### R2-30 — No figures are embedded in the manuscript
The `# Figures` section contains six captions and no images; the file contains no image references at all. I have reviewed Figures 1–6 on their captions alone, which is not review. Please attach the figures.

### R2-31 — "Coverage" is used in two incompatible senses
§2.2 uses it in the conformal sense ("the first two guarantee coverage, not selective risk"); §4.2 onward uses it to mean answered fraction ("mean answered-set coverage 0.9722"). In clinical epidemiology "coverage" additionally means population reach. Please use "answered fraction" or "acceptance rate" for the selective quantity and reserve "coverage" for the conformal sense.

### R2-32 — "$S_\text{cal}$ … touched exactly once" contradicts the threshold walk
> "$S_{\text{cal}}$ (40%, used for certification only and touched exactly once, by the certification test)" (§3.2)

But §3.5 walks a 23-point grid, testing candidates sequentially on $S_\text{cal}$ until first failure. The fixed-sequence argument handles the multiplicity correctly; the phrase "touched exactly once" is nonetheless inaccurate and will be read as a stronger data-hygiene claim than is true. Reword to "used only by the certification walk".

### R2-33 — The deployed operating threshold is never reported for the headline experiments
τ* appears only in E5 (0.55) and E6 (0.77). E1–E4, which carry every headline number, report no threshold. The operating threshold is the single most operationally consequential output of the whole procedure. Report it (mean and range over draws) for E1–E4, and reconcile why the two case studies use such different values.

### R2-34 — "Target pool" is never defined
§3.9 scores violations on "the target pool's answered error"; §3.7 scopes the guarantee "per target site"; §4.7 uses "40 target sites". Table 1's 200 pools with answered-set sizes reaching >300 could be single sites or aggregates. Define it.

### R2-35 — Calibration-cluster count is stated inconsistently
"roughly eighty site-level observations" (§3.2), "about 83 calibration clusters" (§3.5), "roughly 80 of them" (§5.2). 208 × 0.4 = 83.2. Use one figure.

### R2-36 — E4 coverage is non-monotone in site count and this is not explained
> "mean coverage 0.9304 at 150, 0.9715 at the realistic 208-site scale, 0.9601 at 300, and 0.9621 at 400" (§4.5; Table 4)

Coverage rises to 208, falls at 300, rises slightly at 400. If more calibration clusters buy a tighter certificate, coverage should be monotone. Either explain the mechanism (I suspect an interaction with the threshold walk's stopping point) or report Monte Carlo error bars on the coverage column so the reader can see whether the dip is noise.

### R2-37 — A citation is attached to a sentence it does not support
> "at or below $\delta = 0.05$ and non-zero — consistent with a tight rather than a vacuous certificate [@geifman2017selective]." (§4.2)

Geifman & El-Yaniv (2017) cannot speak to the tightness of *this* certificate on *this* cohort. Drop the citation or move it to where the (α, δ) convention is introduced (§3.1 already does this correctly).

### R2-38 — Bibliography: citekey/year mismatches and one mislabelled venue
- `ifac2025abstainexplain` has `year = {2024}` and is an **ECML PKDD 2024** paper (Lenders et al.), not an IFAC one. The key is doubly misleading.
- `l2lore2025` has `year = {2024}` (DS-LB 2024).
- `angelopoulos2021ltt` has `year = {2025}` (Ann Appl Stat).
These will render inconsistently against in-text keys and should be regularised.

### R2-39 — `references.bib` ships an internal working comment
> "% CertGate manuscript references — every entry verified against its primary source on 2026-07-24 … see paper/TODO.md for the one unverified candidate, scireports2026deferral, which is deliberately NOT in this file"

An internal note pointing at a to-do file, naming a reference that was considered and dropped, should not be in a submitted artifact. Strip the header comment before submission. (I also note the dropped key concerns *deferral* — see R2-22.)

### R2-40 — Code repository URL is unresolved in a reproducibility-central paper
> "publicly available at [CODE REPOSITORY URL — to be added]" (Data availability)

Every claim in §3.10 and Appendix A.3 depends on the code being available. This must be a resolvable, versioned, archived link (DOI-minted) at submission, not at acceptance.

### R2-41 — "The test suite is 69/69 green" is uninterpretable to a reader
Appendix A.3. A count of passing tests with no description of what they test conveys nothing and reads as reassurance rather than evidence. Either summarise what the suite verifies (the boundary type-I check and the anti-conservativity regression test are the two the paper actually leans on) or remove the count.

### R2-42 — The cohort specification is delegated to a source file
> "The cohort follows the specification frozen in `data.py`" (§4.1)

The parameters are in fact given in the same paragraph, so the pointer is unnecessary and, for a clinical readership, signals that the authoritative cohort definition lives in code. Remove the pointer or invert it ("the code implements the specification below").

### R2-43 — Over-precision throughout
"0.9722 mean coverage" and "0.9715" from 200 draws; "1,378.9 expected" positives (a fractional patient count, Table 3); margins of "0.0956" and "0.0223" logits; global importances at "1.157, 1.161, 1.178, and 1.155". Two to three significant figures is the honest resolution for everything derived from 200 replicates, and expected counts should be reported as intervals, not fractional patients.

### R2-44 — "max-softmax" for a binary outcome
§3.1: "a bounded score $s(x) \in [0.5, 1]$ — the max-softmax of a probabilistic classifier over the binary outcome". For a binary outcome this is $\max(\hat p, 1-\hat p)$; "max-softmax" imports multiclass vocabulary unnecessarily and obscures the crucial fact that the abstention region is centred on $\hat p = 0.5$. State it as $\max(\hat p, 1-\hat p)$ and note where the abstention band sits relative to the clinical decision threshold (see R2-07).

### R2-45 — $\mu_j$ in the attribution formula is undefined
§3.8 defines $\phi_j(x) = w_j(x_j - \mu_j)$ and specifies $\text{sd}_j$ as "the training-split standard deviation of feature $j$" but never says what $\mu_j$ is. Presumably the training-split mean; say so, and say why the training split rather than the deployment site's mean is the right reference point — for a clinical reader the choice of reference population is precisely what makes an attribution interpretable or not.

### R2-46 — Keywords omit the collection's own emphases
"Selective prediction · Distribution-free uncertainty quantification · Cluster-robust inference · Label shift · Explainable abstention · Clinical risk prediction" contains no fairness, no calibration, no auditability, no clinical decision support. For a collection whose card names fairness, calibration and clinical auditability explicitly, this is a missed indexing opportunity — and, if the paper cannot honestly claim those keywords, that is itself informative about fit.

### R2-47 — "The rigor that constructively answers a published diagnosis" is inflated
§1, contribution 4. The "published diagnosis" is an arXiv preprint (R2-23), and describing one's own validation design as "the rigor that constructively answers" it is the one genuinely immodest phrase in an otherwise well-controlled manuscript. "a constructive response to" would do the same work. Similarly "the reading is honest" (§4.7) and "Its posture throughout is disclosure" (§6) are self-assessments better left to the reader. I note for the record that the paper's hedging elsewhere is appropriate and should not be reduced.

---

## Questions to authors

### R2-48
What exactly is $\text{err}_i$? State the functional form, the probability threshold at which $\hat y$ is formed, and whether false positives and false negatives enter with equal weight.

### R2-49
Please supply the answered-set confusion matrix for E1 and E6. My reconstruction from Table 3 and Table 2 gives answered-set sensitivity ≈ 0.53 (TP ≈ 786, FP ≈ 131, FN ≈ 684). Is that correct? If so, does the paper still wish to describe α = 0.10 as a meaningful clinical guarantee?

### R2-50
What fraction of the cohort's true positives fall in the *declined* set, in E1 and in E6? My estimate from Table 3 plus Table 2 coverage is roughly 40%. Please report the number directly rather than leaving it to be inferred.

### R2-51
Does the generator vary $P(x \mid y)$ across sites, or only $\pi_c$? If only $\pi_c$, please reconcile with "sites differ in both prevalence and case mix" (§3.1) and "no two sites share an identical case mix" (§4.1), and state that BBSE's invariance assumption holds by construction in E2.

### R2-52
Where do $\text{log-mean} = 6.0$, $\text{log-sigma} = 1.1$, prevalence $0.095$, and $u_c \sim \mathcal{N}(0, 0.5^2)$ come from? Name the empirical cohorts or meta-analyses that report these, or state that they are illustrative.

### R2-53
What calendar period does the 208-site, ~10⁵-record cohort represent? Without it, no abstention workload can be sized.

### R2-54
For a realistic deployment — say 50,000 patient-encounters per year across 20 hospitals — how many cases per site per day does the gate abstain on at the certified τ*, and who reviews them? A single worked number would answer R2-01 and R2-02 together.

### R2-55
What operating threshold τ* is deployed in E1, E2, E3 and E4, and how much does it vary across the 200 draws?

### R2-56
A hospital that contributed no calibration records wants to know whether the exchangeable tag applies to it. What does it check? §6.1 says there is no out-of-support screen, so is the honest answer "nothing"?

### R2-57
How often must a certificate be re-earned, and what does a site monitor in between? If the answer is that this is out of scope, please say so in §5.

### R2-58
Can $R_M$ be replaced by a cost-weighted error (asymmetric FN/FP costs) without breaking the boundedness argument of Appendix A.1(i)? If yes, this would substantially strengthen the paper's clinical claim at low cost.

### R2-59
Why is E4 mean coverage non-monotone in site count (0.9715 at 208, 0.9601 at 300)? Is the difference within Monte Carlo error?

### R2-60
Is `zhou2026falsesense` a clinical study? Its title refers to selective *signal* classification. If it is not clinical, on what basis does §2.4 transfer its "9–30%" overrun figure to multi-site clinical deployment?

### R2-61
Per-site answered error is reported only as bin means (Table 2). What is the maximum per-site answered error observed, and how many sites exceeded α while the certificate held?

### R2-62
How many sites in E1/E6 received zero coverage (i.e. entered as neutral atoms with $Z_c = \alpha$)?

---

## Confidential comments to the editor

### R2-63
My sharpest concern is R2-04. The abstract sells "the error rate among answered cases" and the method certifies a site-averaged rate in which a patient at a 5,000-record hospital counts one-fiftieth of a patient at a 100-record hospital. I do not think this is deliberate misdirection — §3.3 and contribution 1 both say "influence-weighted" — but the two most-read sentences in the paper drop the qualifier, and a clinical readership will not reconstruct it. If this paper is accepted with the abstract as written, it will be cited for a claim it does not make. I would make correcting the abstract a condition of acceptance regardless of what else happens.

### R2-64
Second sharpest: R2-07. The paper certifies symmetric 0-1 error at 9.5% prevalence with α = 0.10 — a budget *above* the always-negative baseline — and my reconstruction from its own tables puts answered-set sensitivity near 0.5 and overall cohort sensitivity near 0.3. I could not nail this down because no confusion matrix is reported anywhere, which is itself telling. If my arithmetic is right, the paper's central clinical claim is that it can certify a system that misses most of the events. That is not fraudulent — it is what the estimand says — but it needs to be visible in §5.1, not left for a referee to derive. If the authors' response confirms the numbers and they decline to surface them, I would move to reject.

### R2-65
I believe E2 is a null result presented as a safety result. Nine certifications out of 200 draws is not evidence that BBSE is safe when it certifies; it is evidence that BBSE almost never certifies. The joint-event framing (0/200) is technically correct and rhetorically load-bearing, and it appears in the abstract without the conditional denominator. The correct reading is "BBSE turns a 48.5%-violation system into a system that is unavailable 95.5% of the time, with too few certifications to say whether it is safe when available." That is a defensible and interesting result. It is not the result the abstract reports.

### R2-66
The explainability contribution — which is the collection's central emphasis and therefore the main venue-fit argument — is evidenced by a cohort-level analysis over two declined cases (R2-19). I flag this as the specific point at which I think the paper's ambitions and its evidence diverge most visibly. It is also trivially fixable, which makes it a good test of author responsiveness.

### R2-67
I suspect but could not prove that the generator's site heterogeneity is purely label shift (R2-09). If confirmed, E2 is a test of BBSE under conditions BBSE assumes, and the paper's label-shift claim is much weaker than it reads. I would want the authors' answer to R2-51 before forming a final view. If they confirm it and add a $P(x\mid y)$-perturbation arm, this could become the paper's most interesting experiment; if they confirm it and do nothing, contribution 2 is substantially overstated.

### R2-68
On venue fit: the collection card's emphases are explainability (central), fairness, calibration, uncertainty quantification, OOD robustness, clinical auditability, human-centred design. This paper scores strongly on uncertainty quantification, moderately on OOD robustness, and weakly-to-absently on explainability-as-evidenced, fairness, calibration, auditability-as-artifact, and human-centred design. The statistics are the strongest part and are not what the collection is for. I would not reject on fit — the cluster-as-unit insight is genuinely relevant to multi-hospital deployment and I would like to see it in the clinical literature — but the clinical apparatus has to be built, not gestured at.

### R2-69
A structural worry I want on record: six of the thirty bibliography entries are unrefereed 2026 arXiv preprints, and three of them carry load-bearing positioning claims including the quantitative motivation for the paper's core design choice. Two carry "submitted to" notes. If any of those preprints does not survive review, the manuscript's framing of its own novelty and motivation changes. I would ask the editorial office to check the current status of `zhou2026falsesense`, `triage2026audit` and `yu2026joint` before a final decision, since `yu2026joint` in particular is characterised in §2.1 as the nearest prior work and the entire delta claim rests on that characterisation being accurate.

### R2-70
Credit where due: the five-clause guarantee statement (§3.7), the two-number violation protocol (§3.9), the verified-falsifiable negative control (§4.4), and the limitations list (§6.1) are unusually disciplined and I would not want revision to sand them down. The register is restrained — one mildly inflated phrase (R2-47) and nothing else. My objections are almost entirely about what is missing on the clinical side, not about overreach in what is present. This is a paper that can be fixed by addition.

---

## Recommendation

**Major revision.**

The statistical contribution is real and the disclosure discipline is above average, but this is submitted to a clinical collection whose central emphasis is explainability and which explicitly encourages fairness, calibration and clinical auditability — and on those axes the manuscript is currently thin to absent. The certified quantity is misstated in the abstract as a patient-level error rate when it is a site-averaged one (R2-04); the budget α = 0.10 sits above the no-skill rate for a 9.5%-prevalence outcome and the implied answered-set sensitivity, reconstructed from the paper's own tables, is around 0.5 (R2-07); the cost of abstention — who absorbs it, at what volume, and the fact that roughly 40% of the cohort's outcomes land in the declined set — is never computed (R2-01, R2-05); there is no outcome definition, no time horizon, no calibration, no net benefit, no reporting-guideline conformance, and no fairness analysis beyond site size (R2-08, R2-12, R2-13, R2-14, R2-20); the certificate itself is never displayed, which for a paper about auditability is a gap I would close before anything else (R2-15); and the clinical-deployment and learning-to-defer literatures are essentially uncited (R2-22). None of this is fatal to the underlying idea, and most of it is addition rather than retraction — the cluster-as-unit framing is the right insight for multi-hospital deployment and I want it in this literature. But as written the paper claims a clinical relevance its evidence does not yet license, and at this venue that claim is exactly what will be read.
