# Paper outline — Discover Computing, "Intelligent Medicine: ML and Explainable AI" collection

**Deadline 2026-10-05** · open access · median 22 days to first decision · article type: Research.
Working title: *CertGate: finite-sample certified selective prediction for multi-site clinical risk models, with label-shift robustness and explainable abstention.*

## Fit to the collection's stated topics

| Collection topic | Where the paper delivers |
|---|---|
| Fairness, causality, robustness, and trustworthy ML — "calibration and uncertainty quantification, out-of-distribution robustness, explainability for clinical auditability" | The entire method: finite-sample certificates, label-shift robustness, honest concept-shift boundary, per-site fairness tables |
| Explainable AI as transparency + educational aid | Intrinsically interpretable head; exact local attributions; **abstention explanations** (novel angle: explaining why the system says "I don't know") |
| Predictive modeling for diagnosis/prognosis, risk stratification | Selective risk prediction on a realistic multi-site clinical simulation (and real data if access lands pre-deadline) |
| Federated / cross-institutional collaboration | Framing only: site-clustered guarantees are the statistical substrate any cross-institutional deployment needs; one paragraph in discussion (do not overclaim federation) |
| Ethical / human-centered deployment | Abstention as a first-class, explained output routing cases to clinicians |

## Section plan

1. **Introduction** — the deployment gap: risk models cross sites; record-level confidence is silently wrong under clustering; abstention must be principled *and explained*. Contributions: (C1) site-clustered finite-sample selective-risk certificates via betting martingales + influence capping; (C2) label-shift-robust certification with estimation uncertainty inside the guarantee; (C3) explainable abstention; (C4) an honest-validation design (negative controls verified capable of failing; two-number violation protocol).
2. **Related work** — selective prediction/learn-then-test; conformal prediction (why record-level exchangeability fails here; cluster-conformal gap); label shift (BBSE line); betting/e-value confidence sequences; XAI in clinical ML (position abstention-explanation against SHAP-style answer-explanation).
3. **Methods** — METHODS.md §§1–7 nearly verbatim.
4. **Experiments** — E1–E6; headline figures: (i) coverage-vs-α certified curve with violation rates; (ii) label-shift: baseline violates ~100% / BBSE certifies-or-declines with ≤δ violations; (iii) the feasibility frontier over site counts (capacity planning: "how many hospitals buy which guarantee"); (iv) abstention-explanation case panel; (v) per-site fairness/composition table.
5. **Discussion** — what certification does and does not buy; the concept-shift boundary as a feature of honest ML, not a bug; site count as the true capacity constraint (not record count); path to real-data deployment.
6. **Limitations** — METHODS.md §9 verbatim.
7. **Reproducibility statement** — pinned environment, seeds, one-command grid, provenance-stamped artifacts. (Discover Computing values this; it is cheap for us because it is already true.)

## Reviewer-risk table (pre-empt in the text)

| Likely objection | Pre-emption |
|---|---|
| "Only synthetic data" | Generator parameters mirror a documented real multi-site cohort (208 sites, lognormal sizes 20–5000, 9.5% prevalence, site random effects); every mechanism is exact by construction so ground truth is available for validation — which real data cannot provide; real-data application named as ongoing work. |
| "Why not conformal prediction?" | Related-work paragraph: record-level exchangeability is false under site clustering; cluster-level conformal gives per-record guarantees too weak for an answered-set risk budget; our estimand is the answered-set risk, not per-record coverage. |
| "Isn't α=0.10 a weak guarantee?" | The information floor makes this a property of ~80-cluster data, not of the method — E4 shows exactly what stricter budgets cost in sites; a guarantee calibrated to what the data supports is the honest offer. |
| "Logistic regression is too simple" | The gate is model-agnostic (score only ranks); logistic is chosen *for* the XAI requirement; E-appendix can swap a GBM head and show the coverage/interpretability trade. |
| "The bootstrap step isn't finite-sample" | Disclosed in the guarantee text itself; flagged as the single asymptotic link; finite-sample confusion-set replacement named as future work. |
| "Negative control seems to show the method failing" | Framed as C4: a control that cannot fail proves nothing; certificates *must* fail under concept shift, and showing it is the honesty contribution. |

## Timeline to 2026-10-05

- **Weeks 1–2:** implementation green (tests + full grid), figures v1.
- **Weeks 3–5:** paper draft (Methods is already written; Intro/Related/Discussion new).
- **Weeks 6–7:** internal red-team pass (rerun the audit playbook on certgate), polish figures, reproducibility check on a clean machine.
- **Week 8–9:** submit (~2 weeks of slack before the deadline).
- If real-data access lands by ~week 5: add a real-data section via `validate.from_raw` loader; otherwise submit synthetic-only.
