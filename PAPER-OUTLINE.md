# Paper outline — Discover Computing, "Intelligent Medicine: ML and Explainable AI" collection

> **STATUS 2026-08-10 — this outline is the PRE-DRAFT planning record and parts are
> superseded by events.** The draft (`paper/draft.md`) is written and carries things this
> outline planned as contingencies: the real eICU-CRD v2.0 extract arrived 2026-07-31 and
> §4.10 + Tables 1/2 + Figure 2 (then numbered Tables 8/9 + Figure 8) report the certified run
> (so "real data if access lands" below is settled — it landed); the experiment grid is
> E1–**E9** (E7 record-as-unit comparator added 2026-07-30; E8 comparator + stress suite and
> E9 power frontiers added 2026-08-20); the released E2 result is baseline hard-violates 39.5%
> (aggregate-estimand 97.5%) with BBSE declining 200/200 — not the "~100% / certifies-or-
> declines" sketch below; §6.1 now carries eleven limitations, several beyond METHODS §9;
> and the internal red-team ran early (2026-07-22). The reviewer-risk table's
> "ground truth — which real data cannot provide" line was retired by draft §5's closing
> paragraph (then §5.5) (a retrospective cohort CAN measure a violation; what it cannot supply
> is a KNOWN data-generating process; the retired phrase itself has no current match in the
> draft). Read this file for the venue-fit reasoning and the risk
> table's pre-emption strategy; read `paper/draft.md` + `paper/TODO.md` for current truth.
>
> Citations re-verified against the working tree 2026-08-25: figure, table and section pointers
> were re-pointed after the 2026-08-24 comment humanization and the 2026-08-25 paper
> de-labelling; findings, verdicts and numbers are the originals and are unchanged.

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
4. **Experiments** — E1–E6 *(as built: E1–E9)*; headline figures: (i) coverage-vs-α certified curve with violation rates; (ii) label-shift: baseline violates ~100% / BBSE certifies-or-declines with ≤δ violations; (iii) the feasibility frontier over site counts (capacity planning: "how many hospitals buy which guarantee"); (iv) abstention-explanation case panel; (v) per-site fairness/composition table.
5. **Discussion** — what certification does and does not buy; the concept-shift boundary as a feature of honest ML, not a bug; site count as the true capacity constraint (not record count); path to real-data deployment.
6. **Limitations** — METHODS.md §9 verbatim.
7. **Reproducibility statement** — pinned environment, seeds, one-command grid, provenance-stamped artifacts. (Discover Computing values this; it is cheap for us because it is already true.)

## Reviewer-risk table (pre-empt in the text)

| Likely objection | Pre-emption |
|---|---|
| "Only synthetic data" | SETTLED 2026-07-31: the eICU-CRD v2.0 extract ran end to end and draft §4.10 reports it. The synthetic arm's continuing role is oracle access — a *known* data-generating process, which a real cohort cannot supply (a real cohort CAN measure a violation; see draft §5's closing paragraph, then §5.5 — the old "which real data cannot provide" phrasing was retired by the editorial panel, decision-letter item 13, and has no current match in the draft). |
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
