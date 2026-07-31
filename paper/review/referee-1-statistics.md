# Referee 1 — Statistics (distribution-free inference, risk control, selective prediction)

*Discover Computing*, Collection "Intelligent Medicine: Machine Learning and Explainable AI for Next-Generation Healthcare"

Manuscript: "CertGate: finite-sample certified selective prediction for multi-site clinical risk models, with label-shift robustness and explainable abstention" (`paper/draft.md`, with `paper/references.bib`)

---

## Summary

The paper proposes a selective-prediction gate ("CertGate") for multi-site clinical risk models. The pitch is that record-level selective-risk certificates are overconfident when deployment is grouped by hospital, so the unit of statistical independence should be the site. Mechanically: each site is reduced to a single bounded atom $Z_c \in [0,1]$ built from an influence-capped ($M=100$) answered-error contribution; the atoms are fed in a data-independent (SHA-256-seeded) order to a Waudby-Smith–Ramdas betting martingale, and the system "certifies" if the wealth ever crosses $1/\delta$. An operating threshold is chosen by a fixed-sequence walk over a 23-point grid ordered on an auxiliary site pool, so no $\delta$ is split across the grid. Two assumption modes are offered: an exchangeable baseline, and a BBSE label-shift mode in which a cluster bootstrap over the auxiliary sites produces a Bonferroni box on $(c_0,c_1,\pi_s)$, propagated to an interval $[\rho_{\mathrm{lo}},\rho_{\mathrm{hi}}]$ whose two endpoints are certified separately (justified by an affinity/convexity argument in Appendix A.2), with $\delta_{\mathrm{conf}}+\delta_{\mathrm{bet}}=\delta$. A linear head supplies exact additive attributions for answers and for declines. Evaluation is entirely synthetic: 208 sites, lognormal sizes 20–5,000, prevalence 0.095, site random effects, $R=200$ calibration draws, six experiments (in-distribution validity; label shift; a concept-shift negative control; a site-count sweep; explainability case studies; per-site coverage and answered-set composition).

What the paper actually shows is narrower than what it says it shows. Several things are genuinely well done and I want them on the record: the calibration draw (not the target site) is correctly identified as the unit of replication; the two-number violation protocol correctly separates a parameter claim from a realized-count claim; the E3 negative control is gated on a pre-check that it can fail; the BBSE mode declines rather than silently falling back; the dual-endpoint convexity argument in A.2 has the right logical shape (it needs only one endpoint's level, not a union bound); and the asymptotic bootstrap step is disclosed rather than buried.

But the central guarantee is not the guarantee that is proved. Appendix A.1 establishes a statement about a *population mean over sites* — $\mathbb{E}[Z]$ versus $\alpha$ — and the manuscript sells it in §3.1 and §3.7 as a promise about "a new target site." Those are different objects and, with a site random effect of $\mathrm{sd}=0.5$ on the outcome log-odds baked into the paper's own generator, they are quantitatively very different objects. Compounding this, A.1 (ii) and A.1 (iii) lean on mutually incompatible conditioning regimes: design-conditioning is invoked to make the estimand a clean ratio, and an i.i.d.-style common-mean argument is invoked to make the wealth a supermartingale. Under the former the atoms are independent but *not identically distributed*, and the product $\prod_t(1+\lambda_t(\alpha-\mu_t))$ can exceed 1 under the stated composite null. Beyond the proof, the empirical case rests on a hard-violation screen that measures an unweighted record-level binomial quantity rather than the certified influence-weighted parameter; the E2 headline is carried by nine certified draws; and there is no baseline of any kind — the record-as-unit failure that motivates the whole paper is never demonstrated in the paper's own harness, and no external method is run. Recommendation: major revision.

---

## Major points

**R1-01 — The guarantee that is advertised (per target site) is never the guarantee that is proved (a mean over sites).**

> §3.1: "with probability at least $1-\delta$ over the draw of calibration sites, the influence-weighted answered-set risk — the parameter $R_M$ defined in Section 3.3 — at a new target site is at most $\alpha$"
> §3.7: "(1) It is scoped per target site."

$R_M$ as displayed in §3.3 is $\sum_c g_c a_c e_c / \sum_c g_c a_c$ — a sum *over sites*. It is a population aggregate, not a per-site quantity. Appendix A.1 (ii) then establishes only that $\operatorname{sign}(\mathbb{E}[Z]-\alpha) = \operatorname{sign}(R_M-\alpha)$, i.e. a statement about the aggregate. Nowhere in A.1, A.2 or §3 is there a step that transports a bound on a cross-site aggregate to a bound on the risk *at one new site*. Under the paper's own generator ($u_c \sim \mathcal N(0,0.5^2)$ on the outcome log-odds, §4.1) sites differ substantially, so $\mathbb{E}_c[\text{risk}_c] \le \alpha$ is entirely compatible with a large fraction of individual sites exceeding $\alpha$. This is the distinction between marginal and conditional validity and it is the single most important thing a statistician reads this paper for. Either (a) restate the guarantee honestly as a bound on the site-population mean of the influence-weighted answered risk, and rewrite §3.1, §3.7 (1), the abstract and §5.1 accordingly; or (b) prove a per-site statement, which distribution-free will require a group-conditional or multivalid construction (see R1-17) and will not come free. Related: the E1 evidence cannot adjudicate this either way, because the violation screen is applied per *draw*, not per site.

**R1-02 — A.1 (ii) and A.1 (iii) require incompatible conditioning; under the design-conditional reading the wealth process is not a supermartingale under the stated null.**

> A.1 (ii): "Because the estimand is design-conditional, the answered fractions $a_c$ and weights $g_c$ are fixed functions of observed features, so the denominator $\sum_c g_c a_c$ of $R_M$ is non-random"
> A.1 (iii): "under $H_0$, $\mathbb{E}[\,1 + \lambda_t(\alpha - Z_t) \mid \mathcal{F}_{t-1}\,] \le 1$, so $K_t$ is a nonnegative supermartingale"

If we condition on the design (all site features fixed), the atoms $Z_1,\dots,Z_n$ are independent but have *heterogeneous, site-specific* means $\mu_c$. The null is stated as a single scalar condition $H_0:\mathbb{E}[Z]\ge\alpha$, which under design-conditioning can only mean the average $\bar\mu \ge \alpha$. But $\mathbb{E}[K_n] = \prod_t (1+\lambda_t(\alpha-\mu_t))$, and with a *varying* $\lambda_t$ this product can exceed 1 even when $\sum_t(\alpha-\mu_t)\le 0$: take $n=2$, $\alpha-\mu_1=+0.5$, $\alpha-\mu_2=-0.5$, $\lambda_1=1$, $\lambda_2=0.01$, giving $1.5\times0.995 = 1.4925 > 1$. The supermartingale property therefore requires either (i) $\mu_c \ge \alpha$ for *every* $c$ — a far stronger null than the one stated, under which the certified alternative is only "some site's atom mean is below $\alpha$" — or (ii) that the $Z_c$ are i.i.d. draws from a site superpopulation with a single common mean, which is the unconditional reading that A.1 (ii) explicitly disclaims. The paper cannot have both. Please pick one regime, state it as a numbered assumption, and redo A.1 under it. If you take the i.i.d.-over-sites reading (which I believe is what the code does), then A.1 (ii)'s "the denominator is non-random" is false and the null-equivalence step must be redone as a ratio of expectations (see R1-03).

**R1-03 — "$\mathbb{E}[Z] \le \alpha \iff R_M \le \alpha$" is false as written; $R_M$ is defined as a realized ratio and then used as a parameter.**

> §3.3: "constructed so that $\mathbb{E}[Z] \le \alpha \iff R_M \le \alpha$"
> A.1 (ii): "$\mathbb{E}[R_M]$ is a ratio of expectations with no approximation … so testing $\mathbb{E}[Z] \ge \alpha$ is testing $R_M \ge \alpha$ exactly."

$R_M$ in §3.3 is a finite sum over realized sites with realized $e_c$: a random variable. $\mathbb{E}[Z]$ is a number. The stated equivalence can only hold between $\mathbb{E}[Z]$ and the *population* functional $R_M^{\mathrm{pop}} = \mathbb{E}[g\,a\,e]/\mathbb{E}[g\,a]$ — which is what the algebra actually delivers, since $\operatorname{sign}(\mathbb{E}[Z]-\alpha)=\operatorname{sign}(\mathbb{E}[g\,a\,e]-\alpha\,\mathbb{E}[g\,a])$. Note also that A.1 (ii) writes "$\mathbb{E}[R_M]$ is a ratio of expectations", which is itself wrong: the expectation of a ratio is not the ratio of expectations, unless the denominator is non-random (the claim R1-02 shows you cannot sustain). Define $R_M^{\mathrm{pop}}$ explicitly, distinguish it typographically from any realized $\hat R_M$, and state which one the certificate bounds. This is not pedantry: three separate places in the paper (§3.1, §3.7 (3), §5.1) turn on the parameter/realization distinction, and the definition that anchors them is ambiguous.

**R1-04 — Two assumption modes each run at full $\delta$ with an "either" deployment rule is up to $2\delta$ exposure, and the guarantee wording does not repair it.**

> §3.6: "**Combination.** The modes run as alternatives, each at full $\delta$, and we deploy the most conservative certified threshold. A mode is listed in the combined guarantee only if its own certified prefix contains the deployed threshold, so the OR-guarantee reads 'if *either* tagged assumption holds…'"

Consider a world where the exchangeability assumption in fact holds. The baseline test falsely certifies with probability $\le\delta$. But the BBSE test *also* runs, at its own full $\delta$, and may falsely certify; if its threshold is the one deployed, the deployed certificate is wrong while the stated antecedent ("either tagged assumption holds") is satisfied — a reader following the guarantee text is misled. The false-certification event for the deployed decision is a union over modes, and the union bound gives $2\delta$, not $\delta$. The "OR" phrasing shifts the burden onto the reader to notice that the mode whose assumption holds is not necessarily the mode that produced the deployed threshold. Fix: either split $\delta$ across modes, or restrict the deployment rule so that only the mode whose assumption is asserted can supply the threshold, or state the combined exposure as $2\delta$ in the guarantee text. The same question arises for the two $\alpha$ rungs run in parallel (§3.5, "Both budgets $\alpha \in \{0.05,0.10\}$ are certified by separate walks"): if a deployer reads off whichever rung certifies, that is a second selection not accounted for.

**R1-05 — The hard-violation screen measures the wrong estimand, and it does so with a record-level i.i.d. binomial device inside a paper whose thesis is that record-level i.i.d. is wrong.**

> §3.9: "A certificate counts as violated only when the one-sided 95% Wilson lower confidence bound on the target pool's answered error exceeds $\alpha$ [@wilson1927]."

The certified object is $R_M$: influence-*weighted*, with $g_c=\min(n_c,100)$, aggregated across sites. The measured object is the *unweighted* answered error of a target pool. These are different functionals, and the paper never states the relationship between them or bounds the gap. Two consequences. (a) A certificate could be violated in the certified metric while the screen passes, and vice versa — so E1's 0.01 does not evidence what the guarantee is about. (b) The Wilson interval treats answered records as independent Bernoulli draws. If the target pool spans a site (or several), within-site correlation makes the true interval wider, so the Wilson lower bound is too high and violations are over-declared. That direction is benign for E1 (it makes the reported 0.01 conservative) but *not* benign for E2 and E3, where the inflated screen inflates the headline numbers 48.5% and 83% that carry the paper's two motivating arguments. At minimum: report the influence-weighted realized risk alongside the unweighted one, and use a cluster-robust interval (or report the sensitivity of the E2/E3 rates to the intra-site correlation you built into the generator).

**R1-06 — The acceptance criterion compares the Wilson screen's own false-positive rate to $\delta$, and both are 0.05.**

> §3.9: "one-sided 95% Wilson lower confidence bound … We require this to hold for at most $\delta$ of certificates"
> §4.2: "The hard-violation rate is 0.01 (2 of 200; exact 95% CI $[0.001, 0.036]$), at or below $\delta = 0.05$"

A system whose true answered risk sits exactly at $\alpha$ — the boundary case, i.e. the tightest *valid* system — will trip a one-sided 95% screen on roughly 5% of draws purely from the screen's own error, which is precisely $\delta$. So the criterion "hard-violation rate $\le \delta$" is on the edge of being uninformative exactly where it matters most, and it is not a test of $P(\text{certify and } R_M > \alpha) \le \delta$: the screen's error and the certificate's budget are different quantities that happen to share the numeral 0.05. §3.9's closing paragraph gestures at this ("evidences the *absence of gross violations at the tested power*") and I credit that honesty, but the paper should state explicitly that the reported hard-violation rate is a *downward-biased estimate* of the true violation rate, give the screen's power against a stated excess (e.g. true risk $= 1.5\alpha$) at the observed pool sizes, and decouple the screen level from $\delta$ so the two numbers are not confusable.

**R1-07 — The target predicted-positive rate $q$ is treated as exact, which removes a genuine uncertainty source from the BBSE box.**

> §3.6: "observe the target predicted-positive rate $q$ (which is exact under the design-conditional estimand), and invert the black-box shift equation $q = c_0(1-\pi_t) + c_1\pi_t$"

The *value* of $q$ is indeed a deterministic function of the target features. But the equation $q = c_0(1-\pi_t)+c_1\pi_t$ is a population identity in $\mathbb{E}[q]$ under the target label law, not in the realized $q$. Substituting the realized $q$ for its expectation introduces error of order $n_{\mathrm{target}}^{-1/2}$ in $\hat\pi_t$ (and hence in $\hat\rho$) which the box on $(c_0,c_1,\pi_s)$ does not carry. For a small target site (the generator allows 20 records) this term will dominate the confusion-matrix term. The "design-conditional" framing does not eliminate it; it relocates it. Please either add $q$ to the uncertainty box with its own Bonferroni share, or demonstrate that the omitted term is negligible at the smallest site sizes the method admits, and say which.

**R1-08 — The single asymptotic link is never validated empirically, and the one number bearing on it is discouraging.**

> §3.6: "We disclose plainly that this percentile bootstrap box is the single asymptotic step in an otherwise finite-sample chain"
> §4.7 / Table 3: "the BBSE-implied true-class fraction is 0.0591 … $\hat{\rho} = 0.830$"

The paper is admirably explicit that the bootstrap box carries $\delta_{\mathrm{conf}}=0.025$ of the budget on an asymptotic argument. It then never checks that the box does what it claims. No experiment reports the empirical coverage of $[\rho_{\mathrm{lo}},\rho_{\mathrm{hi}}]$ for the true $\rho$ over the 200 draws — which is trivial to measure in a synthetic harness with oracle access, and is exactly the number a referee needs to price the asymptotic step. Worse, the one directly relevant datum runs the wrong way: E6 appears to be an unshifted deployment, in which the true odds ratio is $\rho=1$, yet $\hat\rho=0.830$ — a 17% error at the null. The manuscript describes the downstream 0.4-percentage-point discrepancy as "the visible cost of the label-shift correction's estimation step" and does not remark that $\hat\rho$ itself is nowhere near its null value. A coverage table for the box across E1/E2/E6, and a statement of what the residual $\hat\rho$ bias does to the certificate, is required before the $\delta_{\mathrm{conf}}$ accounting can be taken at face value.

**R1-09 — E2's headline rests on nine certified draws, and the paper never measures what the BBSE mode costs when nothing is wrong.**

> §4.3: "the joint event … occurs 0 times in 200 draws … conditioning on the 9 draws that did certify ($n_{\text{certified}} = 9$), the hard-violation rate among them is 0.0. BBSE declines the remaining 95.5% of draws"
> Abstract: "the corrected mode never does, declining in 95.5% instead"

The joint-event CI $[0,0.018]$ is small mostly because the mode almost never certifies; a procedure that always declines attains it trivially. The number that speaks to conditional validity is 0/9, whose exact 95% upper bound is about 0.34 — i.e. uninformative. §4.1 promises Clopper–Pearson intervals on "every rate below"; this one, the one that would qualify the headline, is reported bare as "0.0". Separately, and more consequentially, nothing in the paper measures the BBSE mode's *false-decline* rate: what fraction of E1's no-shift draws would BBSE decline? Without that, "certifies or declines rather than issuing a certificate it cannot support" (contribution 2) is unfalsifiable — a mode that declines unconditionally satisfies it. Please report (i) the CP interval on 0/9, (ii) BBSE's certify/decline rates in the E1 world, and (iii) a shift-magnitude sweep showing where BBSE transitions from certifying to declining. Then the reader can judge whether the correction is useful or merely safe.

**R1-10 — The "information floor" is presented as a property of the problem; it is a property of this particular test, and no lower bound is proved.**

> §3.4: "We summarize this with an *information floor* $\ln(1/\delta)(1-\alpha)/n$ — a linearized, zero-variance lower bound"
> §5.2: "the operative rung is a property of the available cluster count, not of the method"
> §1: "so at the 208-site scale $\alpha = 0.10$ is the operative rung — a property of how many hospitals contribute, not of the method."

$\ln(1/\delta)(1-\alpha)/n$ is a linearization of what *this* betting construction with *this* $\lambda$ cap can achieve at zero variance. It is not a minimax lower bound over all procedures for this estimand, and the paper proves none. A different test — a tighter empirical-Bernstein bound, a non-linearized atom, a smaller cap $M$, a variance-adaptive estimand — could plausibly certify $\alpha=0.05$ at 208 sites. Asserting twice (§1 and §5.2) that the frontier is "not of the method" is a claim about all methods and is unsupported. Either prove a lower bound for the estimand, or downgrade the language to "a property of this procedure at this cluster count", and remove the defensive framing in §5.2 ("For any reader tempted to call $\alpha=0.10$ a weak guarantee"). Note that the same overreach appears in contribution 1: "the site-count frontier is direct evidence that the combination is not free" — a frontier for one implementation is not evidence about the combination.

**R1-11 — The concept-shift negative control may not be a concept shift; the manuscript gives no generator equation and never says which mode was run.**

> §4.4: "We inject a posterior tilt (concept intercept 2.0) and the harness first *verifies the poison*"
> §4.4: "the $\alpha = 0.10$ certificate certifies all 200 draws and hard-violates 83% of them"

Under the paper's own generator (§4.1: Gaussian class signal, prevalence entering through a log-odds intercept $\mathrm{logit}(0.095)+u_c$), $\mathrm{logit}\,P(y\mid x)$ is linear in $x$ plus the prior log-odds. Adding a constant 2.0 to that intercept is *arithmetically identical to a prior/label shift* — it multiplies the prior odds by $e^{2}\approx 7.4$. Whether E3 is a genuine change in $P(y\mid x)$ that leaves $P(x\mid y)$ variable, or simply a prevalence move dressed up as concept shift, depends entirely on implementation details the manuscript does not give. This matters enormously: if E3 is really a label shift, then (a) it is *in scope* for the BBSE mode, not out of scope, and (b) an 83% hard-violation rate would be evidence that the label-shift mode failed, not evidence that the tag is load-bearing. §4.4 never says which mode produced the 83%; nor does Figure 3's caption. Please give the tilt's generative equation, state explicitly whether $P(x\mid y)$ changes under it, and report both modes' behaviour under E3. As written, the paper's fourth contribution ("A validation design that can fail") is not verifiable from the manuscript.

**R1-12 — There is no baseline of any kind; the motivating failure is imported, not demonstrated.**

> §1: "A certificate that treats records as exchangeable overruns its stated confidence once deployment is grouped by site — a failure recently documented for record-level selective-risk rules under grouped deployment [@zhou2026falsesense]"
> §4.2–§4.7: no record-level or external comparator appears in any experiment.

The paper's premise is that the record-as-unit certificate fails under site clustering. The harness has oracle labels and a site-structured generator — it is the ideal place to *show* this — and it never does. E1 runs only the site-as-unit method; E2 compares the method to an uncorrected version of itself; E3 and E4 vary the environment, not the method. Consequently the paper's core empirical claim is borrowed from a 2026 arXiv preprint (R1-20) rather than established. Nor is any external method run: not Geifman–El-Yaniv record-level SGR, not the hierarchical conformal machinery of Dunn et al. or Lee et al. that §2.2 says CertGate "reuses", and not the paper's self-declared closest competitor Yu and Liu. For a paper whose contribution is explicitly the *combination* of three literatures, the absence of any comparator makes it impossible to see what the combination bought. Add, at minimum, a record-as-unit certificate on the same E1 draws with the same violation screen.

**R1-13 — The certificate has no coverage floor, so it is trivially satisfiable by abstaining — and the paper's own "closest work" has one.**

> §3.3: "Sites with no answered-eligible records enter as *neutral* atoms $Z_c = \alpha$"
> §2.1: "Yu and Liu [@yu2026joint] are closest: the same certificate shape — a selected-risk bound with an acceptance floor and a decline option"

Nothing in the procedure prevents a certificate from being earned by answering almost nothing: a site with $a_c=0$ contributes exactly $\alpha$ and drops out of $R_M$'s denominator. Coverage is reported as a descriptive number (0.9722, 0.9304, …) but never constrained. The paper notices the adjacent risk — §3.8's composition analysis guards against "answering only easy negatives" — and §4.7 admits the gate does exactly that ("the gate earns its low error by answering predominantly easy negatives and abstaining where positives concentrate"). But an acceptance floor is the standard structural remedy, and §2.1 states that the nearest prior work *has* one. The draft cites this as a similarity while claiming CertGate's advantage lies elsewhere; it should concede that on this axis the prior work is stronger, and either add an acceptance floor to the certified object or state plainly that coverage is uncontrolled and must be checked separately by the deployer.

**R1-14 — The influence cap changes the estimand into something no clinician or auditor asked for, and the relationship to the patient-level error rate is never given.**

> §3.3: "each site receives a *data-independent* influence weight $g_c = \min(n_c, M)$ with $M = 100$"
> §4.1: site sizes "drawn from a clipped lognormal (log-mean 6.0, log-sigma 1.1, clipped to $[20, 5000]$)"

With $\log$-mean 6.0 the median site holds about 400 records, so the majority of sites are capped and $R_M$ is close to an *unweighted average across large sites*. A 5,000-record hospital enters with the same influence as a 100-record one. The consequence is that $R_M$ can sit below $\alpha$ while the fraction of *answered patients* who are misclassified sits above it, if errors concentrate at large sites. The paper never states this, never reports the record-level answered error alongside $R_M$ in any experiment, and offers no sensitivity analysis on $M$ (a frozen constant justified only as "fixed a priori"). For a clinical venue this is the gap between the certified number and the number a hospital safety committee will ask about. Please report both quantities in E1 and E6, and show how the certified/realized picture moves across $M \in \{50,100,200,\infty\}$.

**R1-15 — A.2's load-bearing algebraic claim is asserted, never derived, and deferred to a test suite the referee cannot inspect; the paper contains no formal theorem statement anywhere.**

> A.2: "the sign that decides certification factors as $\operatorname{sign}(\mathbb{E}[Z(\rho)] - \alpha) = \operatorname{sign}(A + \rho B)$ with $(A, B)$ free of $\rho$ — affine in $\rho$."
> A.2: "The argument is pinned numerically in the test suite on the deployed normalization, including an interval that straddles $\rho = 1$."

The entire dual-endpoint soundness argument turns on this factorization, and $A$ and $B$ are never written down in terms of the atoms, the weights, or $w_{\max}=\max(1,\rho)$. The reader is told the raw atom mean is kinked at $\rho=1$ but that the sign-determining product is not, and then referred to unit tests. A referee cannot verify a mathematical claim by being told a test passes. Derive $A$ and $B$ explicitly, in both branches of $\max(1,\rho)$, and show the affinity survives the kink. More generally: this manuscript makes a formal guarantee its headline and contains no numbered assumption list, no theorem statement, and no proposition connecting the composed procedure (threshold walk $\times$ two modes $\times$ two rungs $\times$ endpoint pair) to the advertised $(\alpha,1-\delta)$ claim. A.1 covers one test in isolation; A.2 covers one pair of endpoints. Nothing covers the composition that is actually deployed.

**R1-16 — The justification for a synthetic-only evaluation rests on a claim that is false.**

> §5.5: "Real data cannot supply that ground truth, which is what makes it unable to validate a validity claim."

Retrospective multi-site clinical cohorts have observed outcome labels. The realized answered error at a held-out target site is therefore *directly observable* in real data, and the influence-weighted risk is estimable with a quantified standard error. What real data cannot supply is the exact *parameter* $R_M$ noise-free — that is a variance problem, not an impossibility, and it is the ordinary condition of every empirical validation in the clinical prediction literature the paper cites (TRIPOD-Cluster, internal–external cross-validation). As written, a demonstrably too-strong epistemic claim is doing the work of excusing the absence of any real-data experiment, in a submission to a *clinical* collection. Soften the claim to what is true (oracle access gives noise-free ground truth and therefore sharper validation), and either add a real or semi-synthetic multi-site cohort, or state prominently in the abstract and §1 that the evaluation is synthetic-only. At present the abstract says "On a 208-site synthetic cohort" once and the limitation is not restated in the contributions list.

**R1-17 — Missing prior art, some of it directly adverse to the paper's positioning.**

Not cited, and each bears on a specific claim:

- **Barber, Candès, Ramdas, Tibshirani, "The limits of distribution-free conditional predictive inference" (*Information and Inference*, 2021).** This is the impossibility result for non-trivial conditional distribution-free guarantees. §3.7's "scoped per target site" claim (R1-01) has to be reconciled with it. Its absence is the most serious omission in the bibliography.
- **Jung, Noarov, Ramalingam, Roth, "Batch multivalid conformal prediction" (ICLR 2023)** and **Bastani, Gupta, Jung, Noarov, Ramalingam, Roth, "Practical adversarial multivalid conformal prediction" (NeurIPS 2022).** These are the constructive route to group-conditional (i.e. per-site) validity and are the natural comparator for a paper whose selling point is a group as the unit.
- **Snell, Zollo, Deng, Pitassi, Zemel, "Quantile risk control" (ICLR 2023).** Controls quantiles of the risk distribution rather than its mean — precisely the tool for the parameter-versus-per-site-excursion problem §3.7 (3) and §5.1 wrestle with.
- **Lu, Yu, Karimireddy, Jordan, Raskar, "Federated conformal predictors for distributed uncertainty quantification" (ICML 2023).** §5.4 discusses cross-institutional deployment citing only a 2026 preprint; this is the established reference.
- **Cortes, DeSalvo, Mohri, "Learning with rejection" (ALT 2016).** §2.1 claims the reject-option lineage and jumps 1970 → 2010 → 2017; the modern learning-theoretic treatment is absent.
- **Tibshirani, Barber, Candès, Ramdas, "Conformal prediction under covariate shift" (NeurIPS 2019)** and **Barber, Candès, Ramdas, Tibshirani, "Conformal prediction beyond exchangeability" (*Annals of Statistics*, 2023).** §6.1 excludes covariate shift and §2.2 discusses failures of exchangeability; neither canonical reference appears.
- **Jones, Sagawa, Koh, Kumar, Liang, "Selective classification can magnify disparities across groups" (ICLR 2021).** §4.7 raises exactly this question ("whether small hospitals receive systematically worse selective service") without the reference that established it.
- **Field and Welsh, "Bootstrapping clustered data" (*JRSS-B*, 2007).** §3.6 and A.2 use a cluster bootstrap with no reference and no statement of the regularity conditions under which its percentile intervals are asymptotically valid — which is the load-bearing assumption behind $\delta_{\mathrm{conf}}$.
- **Aas, Jullum, Løland, "Explaining individual predictions when features are dependent" (*Artificial Intelligence*, 2021).** See R1-18.

The positioning that survives contact: the combination of cluster-unit inference with a selective-risk budget and an uncertainty-carrying label-shift correction does appear to be unoccupied. The positioning that does not survive: the "per target site" scope claim, which runs into the first reference above, and the implicit suggestion that group-conditional guarantees are otherwise unavailable, which runs into the second and third.

**R1-18 — "Exact Shapley values" is true only under feature independence, which the paper's own generator violates.**

> §3.8: "For a linear model these attributions are exact Shapley values, with no approximation or sampling [@lundberg2017shap]."
> §4.6: "genuine Shapley values, not sampled approximations [@lundberg2017shap]"

$\phi_j = w_j(x_j-\mu_j)$ is the Shapley value of a linear model only for the *interventional* value function, or equivalently for the conditional value function **under feature independence** — this is exactly the assumption behind Lundberg and Lee's LinearSHAP. The manuscript's generator (§4.1) puts the class signal on a shared direction across the first four coordinates, so features 0–3 are marginally correlated through the class label. Under conditional (observational) Shapley values with dependent features, $w_j(x_j-\mu_j)$ is not the Shapley value. The cited reference supports the claim only with the independence caveat, which the manuscript omits and states twice as unqualified exactness. Add the caveat, name which value function you mean (interventional vs conditional), and cite Aas et al. Given that explainability is the central emphasis of this collection, an incorrect exactness claim in the explanation layer is not a small matter.

**R1-19 — The generator's parameters are attributed to references that do not contain them.**

> §4.1: "This follows the distributional profile reported across multi-site clinical studies — many small-to-large sites with heavy-tailed sizes, single-digit prevalence, and site-level heterogeneity — … [@tripodcluster2023; @internalexternal2021]"
> §1: "whose lognormal sizes, $\sim$9.5% prevalence, and site random effects follow the distributional profile reported for large multi-site clinical cohorts"

TRIPOD-Cluster (Debray et al., *BMJ* 2023) is a reporting checklist. Takada et al. (*J Clin Epidemiol* 2021) is a methodological study of internal–external cross-validation. Neither is a source for log-mean 6.0, log-sigma 1.1, a base prevalence of 0.095, or a site random-effect standard deviation of 0.5 on the log-odds scale. Since the entire empirical case is synthetic, the realism of these five numbers is load-bearing, and each needs a citation to an actual cohort description — or an explicit statement that they were chosen by the authors as plausible and are not sourced. A sensitivity analysis over the site random-effect SD would also help, since that parameter governs exactly the between-site heterogeneity that R1-01 turns on.

**R1-20 — Load-bearing empirical and positioning claims rest entirely on unrefereed 2025–26 arXiv preprints.**

> §2.4: "certified record-level selective-risk rules overrun their budget by 9–30% under grouped deployment [@zhou2026falsesense]"
> §2.1: "Yu and Liu [@yu2026joint] are closest"

Seven entries in the bibliography (`zhou2026falsesense`, `triage2026audit`, `yu2026joint`, `score2026`, `scrc2025`, `fedcrc2026`, `thermal2026audit`) are `@misc` arXiv preprints, none peer-reviewed. Between them they carry: the paper's motivating empirical claim (with a specific "9–30%" figure quoted in the body), the identity of the closest competitor and hence the entire novelty argument, and the federated-learning positioning of §5.4. A quantitative claim taken from an unrefereed preprint should be attributed as such in the sentence ("a recent preprint reports…"), and the novelty positioning should be restated against the peer-reviewed literature so it does not collapse if one preprint turns out to say something else. I could not verify any of these seven from the manuscript.

**R1-21 — "$S_{\text{cal}}$ is touched exactly once" is contradicted by the procedure described two sections later.**

> §3.2: "$S_{\text{cal}}$ (40%, used for certification only and touched exactly once, by the certification test)"; repeated verbatim in §4.1.
> §3.5: "we walk the grid in a fixed sequence … each is tested at the mode's full betting budget … and the walk stops at the first failure."

Up to 23 thresholds are tested on $S_{\text{cal}}$, for each of two modes, at each of two $\alpha$ rungs — as many as 92 tests on the same pool. The fixed-sequence construction may well control FWER within one walk (and I accept the $\delta$-splitting argument for that), but "touched exactly once" is simply not what happens, and it is the sentence a reader relies on to believe the calibration pool is uncontaminated. Rewrite it as "used only by the certification tests, and never for fitting, ordering, or diagnostics", and state the total number of tests performed against it.

**R1-22 — The bootstrap takes quantiles over a validity-selected subsample; the selection is not accounted for in $\delta_{\mathrm{conf}}$.**

> §3.6: "(ii) fewer than 2,000 valid resamples within 4,000 attempts, a degenerate bootstrap pool for which we refuse to take quantiles over a silently reduced draw count"
> A.2: "a cluster bootstrap of the $S_{\text{aux}}$ sites that requires 2,000 valid resamples within at most 4,000 attempts"

Retaining only "valid" resamples and quantiling over them is itself a selection: the retained set is the bootstrap distribution *conditional on validity*, not the bootstrap distribution. If invalidity correlates with the parameter values (e.g. resamples with small $c_1-c_0$ are both more likely invalid and more informative about the tail of $\rho$), the percentile box is biased inward and its coverage falls below $1-\delta_{\mathrm{conf}}/3$ per coordinate. The manuscript frames the rule as protecting against a reduced draw count, which addresses Monte-Carlo error but not selection. Please define "valid", characterise what makes a resample invalid, and either show the selection is ignorable or report the box's empirical coverage under it (see R1-08).

**R1-23 — Constants pinned by a unit test are not a substitute for pre-registration, and the claim is made three times.**

> §3.2: "This is a lightweight, machine-verifiable substitute for pre-registration: it removes the degrees of freedom that would otherwise let a tunable pipeline flatter itself."
> Repeated at §3.10 ("a lightweight, machine-verifiable substitute for pre-registration") and A.3.

A unit test asserts that the constants currently equal certain literals. It carries no timestamped commitment that those literals were chosen before the results were seen, and nothing stops an author from changing a constant and re-pinning it. What it verifies is internal consistency, not temporal priority — which is the entire content of pre-registration. The claim should be downgraded to what is true ("constants are frozen and their values are machine-checked, so drift is detectable in version control"), and stated once rather than three times.

---

## Minor points

**R1-24 — Undefined and unused symbols in the betting-test display.**

> §3.4: "$\lambda_t = \min\!\left(\sqrt{\frac{2\ln(1/\delta)}{\hat{\sigma}^2_{t-1}\, n}},\; \frac{0.9}{1-\alpha}\right)$, with a variance floor of $10^{-8}$ and the running mean and variance $(\hat{\mu}, \hat{\sigma}^2)$ initialized at $(0.5, 0.25)$."

Three problems in one display. (a) $n$ is never defined; elsewhere $n_c$ is a site's record count, $n_{\text{cal}}$ the calibration site count, and $n$ the pool count in Table 1. (b) $\hat\sigma^2_{t-1}$ is never defined as an estimator — over which atoms, with what centring, with what weighting. (c) $\hat\mu$ is initialized but appears in no displayed formula, which suggests the displayed $\lambda_t$ is not the implemented one (WSR's empirical variance estimate uses the running mean). Also unstated: in the BBSE mode, does $\ln(1/\delta)$ in $\lambda_t$ use $\delta$ or $\delta_{\mathrm{bet}}$?

**R1-25 — The bet deviates from the cited form without saying so.** §3.4 attributes the construction to [@waudbysmith2024betting], whose predictable-mixture bet scales as $(\hat\sigma^2_{t-1}\,t\log(1+t))^{-1/2}$; the manuscript uses a fixed $n$ in place of $t\log(1+t)$. Using a fixed, data-independent $n$ preserves predictability so I do not believe validity is harmed, but the deviation should be stated and its effect on power discussed, since it changes the bet schedule materially at small $t$.

**R1-26 — §4.2 and §5.1 describe the same two numbers in opposite terms.**

> §4.2: "Across every size bin the observed exceedance sits far below the reference (for example … 0.0551 against 0.4915 in the largest bin)"
> §5.1: "E1 shows realized exceedance *rising toward* its binomial reference (0.0551 against 0.4915 in the largest size bin)"

0.0551 against 0.4915 is an order of magnitude below, not "rising toward". §5.1's sentence misdescribes its own data and undercuts §4.2's (correct) reading.

**R1-27 — Table 1's binomial reference is undefined and its smallest bins carry no uncertainty.** The caption says "observed versus binomial reference" and the body calls it "the exceedance a perfectly valid boundary-case certificate would show purely from label dispersion", but the reference's parameters are never given: which $n$ within a bin (the bin's midpoint? each pool's own size, averaged?), and at what $p$. The $[0,30)$ row reports 0.0000 from $n=2$ pools and the $[30,100)$ row 0.1111 from $n=18$ (exact 95% CI roughly $[0.014, 0.347]$); no interval is shown for any row, yet §4.2 asserts a comparison across "every size bin".

**R1-28 — The stated interval policy is not applied to any table.** §4.1 says "we accompany the primary rates with exact (Clopper–Pearson) 95% confidence intervals." Tables 1, 2, 3 and 4 contain none. E4's certify rate of 0.3 at 300 sites (Table 4) — the number that fixes the $\alpha=0.05$ frontier — has an exact 95% interval of roughly $[0.24,0.37]$ that is never shown.

**R1-29 — Coverage means are reported to four significant figures with no Monte-Carlo error, and their differences are not shown to be distinguishable.**

> §4.5: "mean coverage 0.9304 at 150, 0.9715 at the realistic 208-site scale, 0.9601 at 300, and 0.9621 at 400"

No standard error accompanies any of these. The sequence is non-monotone in site count (0.9715 at 208 exceeds 0.9601 at 300), which is unremarked and, absent an MC error, uninterpretable. I credit the disclosure that E1's 0.9722 and E4's 0.9715 come from independently seeded runs — that gap is itself an estimate of the noise floor, and it is larger than differences the text treats as meaningful. Two further issues in the same table: coverage is averaged *conditional on certifying* (at 300 sites, over the 30% that certified), which is a selected average and is not labelled as one; and no MC error is given for the abstract's headline 0.9722.

**R1-30 — E5's cohort-level abstention claim rests on two declined cases.**

> §4.6: "This case study uses a deployment with threshold $\tau^* = 0.55$, answering 200 cases and declining 2."
> §4.6: "At the cohort level, feature 0 is the dominant abstention driver: its mean absolute attribution is 0.868 on answered cases but 1.722 on declined cases … Declines are systematically the cases where feature 0's pull leaves the decision contested"

If "the cohort" is this deployment, then 1.722 is a mean over $n=2$, the gap ranking $[0,3,2,1,\dots]$ is a ranking derived from two observations, and "systematically" is unsupported. If it is a different, larger deployment, the manuscript does not say so. Figure 5's caption repeats the numbers without the sample size. Either state the declined-case count behind the cohort statistics, or run the analysis on a deployment with enough declines to support the word "systematically".

**R1-31 — E4's "switch-on at 150" is confounded with a frozen constant and with the grid resolution.** §4.5 states that the 60- and 100-site points are refused by the 50-record-carrying-cluster gate rather than by the information floor — good — but then §5.2 and the abstract present 150 as a capacity frontier ("$\alpha=0.10$ becomes reachable around 150 sites"). Below 150 the gate refuses regardless of the test, so the experiment cannot distinguish the statistical frontier from the arbitrary constant 50. The sweep grid $\{60,100,150,208,300,400\}$ also has no point between 100 and 150, nor between 208 and 300, nor between 300 and 400, so every "first appears at" statement is grid-resolution-limited. Add points, and report where the floor alone would bind with the cluster gate relaxed.

**R1-32 — E5 and E6 deploy different thresholds with no explanation, and neither is tied to E1's operating point.** §4.6 uses $\tau^*=0.55$ (the minimum of the grid, implying the whole grid certified) with coverage $200/202 \approx 0.99$; §4.7 uses $\tau^*=0.77$ with per-site coverage around 0.90; E1 reports mean coverage 0.9722. Three deployments, three operating points, no statement of how each was reached.

**R1-33 — "Provably anti-conservative" is supported by a construction that is never shown.**

> §3.3: "The natural fix — capping each site's *realized* contribution — is provably anti-conservative: a construction with 17.5% true risk certifies at $\alpha = 5\%$ under naive truncation (Appendix A.3; retained as a regression test)."

A.3 mentions the regression test but gives no construction. "Provably" promises a proof; what is offered is a counterexample the reader cannot see. Either display the construction (it should be a few lines) or write "we exhibit a construction in which…".

**R1-34 — The abstract understates E4 relative to §4.5.** Abstract: "a site-count frontier shows the stricter $\alpha=0.05$ budget needs roughly 300+ sites." §4.5: "first appears at 300 (certify rate 0.3 …) and becomes reliable only at 400." A 30% certify rate is not a budget being "needed at 300+"; align the abstract with §4.5.

**R1-35 — Code-internal facts appear in the manuscript.** §4.1 "the specification frozen in `data.py`"; §5.5 "the implementation includes a `from_raw` loader"; §4.1 "Every experiment runs in mode FULL" (undefined); A.3 "The test suite is 69/69 green." A test count is not a scientific result and is unverifiable at review; a file name is not a specification. Replace `data.py` with the specification itself (which §4.1 mostly gives anyway), define or drop "mode FULL", and drop the test count.

**R1-36 — Every reproducibility claim rests on code whose location is a placeholder.** Data availability: "publicly available at [CODE REPOSITORY URL — to be added]". §3.10, A.3, §5.5 and the Data availability statement all rely on the released code; with no URL, none of them is checkable. (I flag this as substantive, not as a formatting placeholder, because the reproducibility claims are load-bearing.)

**R1-37 — Bibliography key/year mismatches.** `ifac2025abstainexplain` has `year = {2024}` and an ECML PKDD 2024 booktitle; `l2lore2025` has `year = {2024}` (DS-LB 2024); `angelopoulos2021ltt` has `year = {2025}` (AoAS). Keys are internal, but with author–year citation styles the mismatch propagates into rendered text, and `ifac2025` additionally suggests IFAC, which the entry is not.

**R1-38 — Internal process leaks into the submitted bibliography.** `references.bib` lines 1–3: "every entry verified against its primary source on 2026-07-24 … see paper/TODO.md for the one unverified candidate, `scireports2026deferral`, which is deliberately NOT in this file". A submitted artifact should not reference an internal TODO file, and should not advertise that a candidate reference was excluded as unverified.

**R1-39 — Three literatures or four?** §1: "Three questions in reliable machine learning have mature but separate answers", and the closing paragraph of §1 and §6 both list three lines. §2: "CertGate draws on four literatures", with four subsections. Pick one count.

**R1-40 — Contribution 4 is listed as a primary contribution and then demoted twice.** §1 contribution 4 claims "A validation design that can fail", immediately qualified as "rather than a new validation philosophy"; §5.1 then says "The negative control is validation design, not a headline contribution." If it is not a contribution, do not list it among the primary contributions.

**R1-41 — Defensive register.** Several passages argue with an imagined critic rather than stating results: §5.2 "For any reader tempted to call $\alpha=0.10$ a weak guarantee"; §3.6 "We do not paper over this"; §4.4 "A negative control that cannot fail proves nothing"; §4.7 "the reading is honest" and "That is not a defect; it is what a selective gate on a low-prevalence task should do"; §6 "Its posture throughout is disclosure." The prose is otherwise commendably restrained — I found no "first ever", no repeated "novel", and the hedging that is present is appropriate and should be kept — but these rhetorical asides are padding and, in §5.2's case, carry an unproved claim (R1-10).

**R1-42 — No figures are included.** The manuscript ships a "# Figures" section containing six captions and no images; nothing in the file embeds or references an image asset. Several caption claims (e.g. Figure 4's "shaded region marks sites declined by the 50-record-carrying-cluster gate") can only be checked against a plot. Submit the figures.

**R1-43 — $\mu_j$ is undefined.** §3.8: "$\phi_j(x) = w_j(x_j - \mu_j)$". $\mathrm{sd}_j$ is carefully defined as the training-split standard deviation; $\mu_j$ is not defined at all (presumably the training-split mean, but this must be said, since it fixes the attribution baseline).

**R1-44 — Imprecise statement of the exchangeability failure.** §2.2: "distribution-free coverage under exchangeability of the calibration and test points — false under multi-site clustering, where records within a hospital are not exchangeable with those from an unseen site." What fails is exchangeability of the *joint* record sequence when records are clustered and sites are drawn; individual records from different sites can be marginally identically distributed. State the failure at the level of the joint law.

**R1-45 — The title advertises "finite-sample" for a paper one of whose two headline modes is not.** "CertGate: finite-sample certified selective prediction … with label-shift robustness". §3.6, §3.7 (5) and §6.1 all disclose that the BBSE mode's bootstrap box is asymptotic. The disclosure is good; the title conjoins the two properties in a way that lets a reader carry "finite-sample" onto the label-shift mode. Consider qualifying the title.

**R1-46 — 2/200 is very weak evidence of tightness, and the citation does not support the concept.** §4.2: "The hard-violation rate is 0.01 … and non-zero — consistent with a tight rather than a vacuous certificate [@geifman2017selective]." The exact interval $[0.001,0.036]$ is consistent with true rates anywhere from near-zero to 0.036, i.e. with a fairly slack certificate too; and Geifman and El-Yaniv (2017) is a method paper, not a source for a tightness criterion.

**R1-47 — The power-grid citation is a weak generality argument and off-target for this venue.** §2.4: "The same certificate shape appears in power-grid contingency screening [@thermal2026audit], so it is not specific to medicine." Shape resemblance in an unrefereed preprint from another domain does not establish generality, and in a submission to a clinical-ML collection the sentence spends credibility for nothing.

**R1-48 — It is unstated whether neutral atoms enter $n$.** §3.3 says empty sites enter as neutral atoms $Z_c=\alpha$ and that "the minimum-cluster gate that governs feasibility counts only *record-carrying* sites". Since $\lambda_t \propto n^{-1/2}$ (§3.4), whether $n$ counts neutral atoms changes the bet schedule and hence the power. Two different site counts are in play; say which is used where.

**R1-49 — E1 never reports the oracle true answered risk, although the harness has oracle access.** §4 justifies the synthetic design precisely by oracle access ("we can compute the true answered-set risk at each target site"), and then E1 reports only coverage, certify rate and violation rates. The true risk relative to $\alpha$ is the number that tells the reader how much slack the certificate is operating on — and given the information floor $\ln(1/\delta)(1-\alpha)/n \approx 0.033$ at $n\approx83$, it is presumably around 0.06 or below. Report it.

**R1-50 — No ablations on the frozen constants.** $M=100$, the 50-cluster minimum, the $\delta_{\mathrm{conf}}/\delta_{\mathrm{bet}} = 0.025/0.025$ split, the $(c_1-c_0) \ge 0.10$ decline threshold, the 2,000/4,000 resample rule, and the 23-point grid are all fixed a priori (§3.2) and none is varied anywhere. Freezing constants is good practice; it does not remove the reader's need to know how the results move with them.

**R1-51 — Ambiguous "point" units.** §4.7: "the ~0.4-point gap between the BBSE-implied and oracle fractions". $0.0630-0.0591 = 0.0039$, i.e. 0.39 *percentage* points. Say percentage points.

**R1-52 — Rule-of-three phrasing.** §4.3: "exact 95% CI $[0, 0.018]$, consistent with the rule-of-three bound $3/200 = 0.015$". The exact upper bound (0.0183) exceeds the rule-of-three approximation, so "consistent with" is doing loose work; either drop the rule-of-three aside or say it is an approximation that is slightly anti-conservative here.

**R1-53 — Contradictory deployment rules.** §3.5: "We deploy the maximum-coverage threshold in the certified prefix." §3.6: "we deploy the most conservative certified threshold." Maximum-coverage is the least conservative threshold in the prefix; most-conservative is the other end. Presumably these operate at different levels (within a mode vs across modes) but as written they read as contradictory instructions.

---

## Questions to authors

**R1-54** — Is the certified object a bound on $\mathbb{E}_{\text{sites}}[\,\cdot\,]$ (a mean over the site population) or a bound on the risk at an individual target site? If the former, will you restate §3.1, §3.7 (1), the abstract and §5.1 accordingly? If the latter, where is the proof?

**R1-55** — Under which conditioning regime is A.1 intended to hold: design-conditional (features fixed, atoms independent non-identically distributed) or i.i.d. over sites (atoms exchangeable with a common mean)? Under the first, please address the counterexample in R1-02 showing $\mathbb{E}[K_n]$ can exceed 1 under the stated composite null.

**R1-56** — Please give the generative equation for the E3 "concept intercept 2.0" tilt. Does $P(x \mid y)$ change under it? If it does not, in what sense is E3 a concept shift rather than a prior shift that the BBSE mode is designed to correct — and which mode(s) produced the reported 83%?

**R1-57** — What are the BBSE mode's certify and decline rates in the E1 (no-shift) world, and how do they vary with shift magnitude between prevalence 0.095 and 0.22?

**R1-58** — What is the empirical coverage of the bootstrap box $[\rho_{\mathrm{lo}},\rho_{\mathrm{hi}}]$ for the true $\rho$, over the 200 draws, in each of E1, E2 and E6? Given $\hat\rho = 0.830$ in the apparently unshifted E6, does the box cover $\rho=1$?

**R1-59** — On what data is "the maximum-coverage threshold in the certified prefix" (§3.5) selected — $S_{\text{aux}}$, $S_{\text{cal}}$, or the target features? If $S_{\text{cal}}$, please state why the fixed-sequence FWER argument still licenses the selection.

**R1-60** — Does $n$ in the $\lambda_t$ formula count neutral (record-free) atoms, and what is $\hat\sigma^2_{t-1}$ precisely? Please also state where $\hat\mu$ enters, since it is initialized but never used in any displayed expression.

**R1-61** — In E1 and E6, what is the *unweighted record-level* answered error, and how does it compare to the certified influence-weighted $R_M$? How does the comparison move as $M$ varies?

**R1-62** — Can you supply a record-as-unit selective-risk certificate run on the same E1 draws with the same screen, so that the motivating failure is demonstrated rather than cited? And a comparison against at least one of Dunn et al. (2023), Lee et al. (2025), or Yu and Liu?

**R1-63** — Please write down $A$ and $B$ from A.2 explicitly, in both branches of $w_{\max}=\max(1,\rho)$, so the affinity claim can be checked on the page.

**R1-64** — What defines a "valid" bootstrap resample in the 2,000-of-4,000 rule, and what evidence is there that conditioning on validity leaves the percentile box's coverage intact?

---

## Confidential comments to the editor

**R1-65** — My sharpest objection is R1-01, and I do not think it is repairable by rewording alone. The paper's whole selling proposition is that the site is the right unit of independence, and the guarantee it then proves is a statement about a *mean over sites*. A mean-over-sites bound is exactly the kind of marginal guarantee that the cluster framing was supposed to improve on. The paper sells it as a per-target-site promise in the abstract, §3.1 and §3.7 (1). Either the authors weaken the claim — in which case the contribution shrinks considerably, because the marginal-versus-conditional gap is the interesting part of the problem — or they need a group-conditional construction they do not currently have. Barber–Candès–Ramdas–Tibshirani (2021) says the strong version cannot be had distribution-free, and it is not cited.

**R1-66** — The second thing I would not let past is that the evaluation is configured so that E1 cannot really fail. The screen is a conservative Wilson lower bound on the wrong (unweighted, record-level) functional, its own false-positive rate equals $\delta$, and there is no comparator. I do not think this is deliberate — the paper is unusually candid about the parameter/count distinction and about the screen's low power, which is more self-awareness than most submissions offer — but the net effect is that the headline validity result is close to unfalsifiable in the direction that matters. E3's 83% shows the screen has power when something is badly wrong, which is reassuring but does not establish sensitivity at the margin the certificate actually operates on.

**R1-67** — E2 is, on the numbers as given, a declining machine. BBSE certified 9 of 200 draws. The abstract's "the corrected mode never does" is 0/9 with an exact upper bound of about 0.34. There is no measurement of how often BBSE declines when nothing is wrong, so we cannot distinguish "a correction that keeps the guarantee honest" from "a mode that almost always refuses". I suspect the latter is closer to the truth, and the one incidental datum in the paper — $\hat\rho = 0.830$ in an apparently unshifted E6 — points that way. This is answerable with a single extra experiment (R1-57) and the authors should be required to run it.

**R1-68** — I could not verify seven of the thirty bibliography entries, all 2025–26 arXiv preprints, and they carry disproportionate weight: the motivating "9–30%" number, the identity of the closest competitor, and the federated positioning. If `yu2026joint` is not what the draft says it is, §2.1's novelty argument moves. I would ask the authors to restate the positioning against peer-reviewed work so the contribution claim does not hinge on unrefereed material. I also note the bibliography header advertises an internal TODO file and an excluded unverified reference; that should be cleaned before any version reaches production.

**R1-69** — On venue fit: the statistical machinery is the substance here, and explainability — the collection's central emphasis — is thin. It is one section (§3.8), one experiment (E5) built on a deployment with two declined cases, and a claim of Shapley exactness that is only correct under a feature-independence assumption the paper's own generator violates (R1-18). §5.1 and contribution 3 both concede the explanation layer "supports the certificate above rather than standing as an independent method". Combined with the total absence of clinical data, my honest view is that this is a good methodological-statistics paper aimed at the wrong readership, and that its acceptance here should be conditional on both a real or semi-synthetic clinical cohort and a substantially strengthened explanation layer.

**R1-70** — What I could not nail down but suspect: that E3 is a relabelled prior shift rather than a concept shift (R1-11). If so, the fourth contribution is not what it says it is, and the 83% figure is evidence against the label-shift mode rather than evidence for the assumption tag. This is decidable from three lines of the generator and I would make the answer a condition of any revision.

---

## Recommendation

**Major revision.**

The paper is doing real statistical work and its instincts are mostly right: the cluster as the unit of independence is the correct framing for multi-site clinical deployment, the calibration draw is correctly identified as the replication unit, the parameter-versus-realized-count distinction is handled with more care than is usual, and the asymptotic step in the label-shift mode is disclosed rather than hidden. But the guarantee stated in the abstract and §3.1 is not the guarantee proved in Appendix A.1 (R1-01), and the two halves of that proof rest on incompatible conditioning assumptions (R1-02). Those are not presentational defects. Alongside them sit an evaluation with no comparator of any kind (R1-12), a violation screen aimed at a different functional from the certified one (R1-05, R1-06), a label-shift headline carried by nine draws with no false-decline measurement (R1-09), an unvalidated bootstrap box carrying half the error budget (R1-08), and an explainability layer whose exactness claim is incorrect as stated (R1-18). Against the venue card: the collection wants explainability as the central emphasis and clinical or epidemiological grounding, and this submission delivers a synthetic-only statistics paper with explainability as a supporting section that the authors themselves twice describe as secondary. I would be glad to see it again with the guarantee restated to what is proved, a per-site claim either established or withdrawn, a record-as-unit baseline in the harness, the BBSE mode's decline behaviour under the null measured, and a real multi-site cohort — but I cannot recommend acceptance on the present statement of the guarantee.
