# Phase 2 — novelty & related-work recheck (2026-08-15)

AI-Scientist v1's novelty loop (harsh-critic default, iterative Semantic Scholar /
web querying, explicit novel/not-novel decision) applied to the manuscript's five
stated contribution claims across six topic lanes, then synthesized by a verifier
that re-opened every verdict-driving abstract. Lane files: `novelty/*.json` (~60
candidate papers); full verdict: `novelty/VERDICT.md`. This supplements, not
replaces, the planned late-September re-check.

| # | Contribution | Verdict |
|---|---|---|
| 1 | Site-as-unit certified selective gate (headline) | **STILL_NOVEL** — nothing found makes the site the unit of independence for a finite-sample certificate on a gate's answered-set error; nearest objects each one axis short and already cited (SCoRE, Yu & Liu, SCRC, Zhou & Wang, Dunn et al., Lee-Barber-Willett, Shahid). One uncited same-seam paper: Lee & Ren 2025 (hierarchical conformal e-values, FDR via e-BH — different error criterion, no betting, no shift mode). |
| 2 | BBSE label-shift mode with honest budget | **NEAR_MISS** on components — Plassier et al. ICML 2023 (federated conformal under label shift) and Alexandari et al. 2018 (abstention under label shift) are uncited pairing precedents; the four-parameter cluster-bootstrap box inside a betting certificate's δ split with a decline branch is not found anywhere. |
| 3 | Exact attributions on certified decisions | **NEAR_MISS** on the explanation component — Fernandes & Rocha, XAI 2026 explain why a linear reject-option classifier rejected an instance (same object, no certificate, no sites). Differentiator (attribution on a *certified* decision) holds and is already framed modestly. |
| 4 | Falsifiable validation design | **STILL_NOVEL** — Zhou & Wang 2026 (cited) is the diagnosis; no paper pre-verifies a negative control's power to fail. |
| 5 | eICU end-to-end under a pre-frozen protocol | **STILL_NOVEL** — no prior certified gate on eICU / any multi-hospital cohort with the hospital as unit. Uncited descriptive eICU neighbours: CPMORS (JMIR 2024, conformal + SHAP + clinician-review flag, eICU external validation). |

**Collisions: 0.** The two secondary contributions are near-misses on their
components, not their combinations; both are already framed as supporting the
headline, so the fix is citation plus one positioning clause each — no re-scoping.

## Must-cite additions (8; none in `references.bib`)

Applied in Phase 4 to related work only (constraint: touch related work only for
true collisions or must-cite near-misses):

1. Lee & Ren 2025, *Selection from Hierarchical Data with Conformal e-values*, arXiv 2501.02514 — §2 cluster-exchangeability paragraph, positioned (FDR over selected individuals via e-BH; no 1−δ gate certificate; no betting; no shift mode).
2. Fernandes & Rocha 2026, *Concisely Explaining the Doubt: Minimum-Size Abductive Explanations for Linear Models with a Reject Option*, XAI 2026 / arXiv 2603.14096 — §2 explainable-abstention sentence, beside Artelt 2023 / IFAC 2024.
3. Plassier et al. 2023, *Conformal Prediction for Federated Uncertainty Quantification Under Label Shift*, ICML 2023 / arXiv 2306.05131 — §2 label-shift paragraph.
4. Alexandari, Kundaje & Shrikumar 2018 (rev. 2022), *A General Framework for Abstention Under Label Shift*, arXiv 1802.07024 — §2 label-shift paragraph (preprint; cite as such).
5. Podkopaev & Ramdas 2022, *Tracking the risk of a deployed model and detecting harmful distribution shifts*, ICLR 2022 / arXiv 2110.06177 — §2 certified-selective-prediction paragraph, beside Waudby-Smith & Ramdas (same betting machinery on deployed-model risk, as sequential monitoring).
6. Wang et al. 2026, *LEC: Linear Expectation Constraints for Selection-Conditioned Risk Control…*, ICML 2026 / arXiv 2512.01556 — the §2 "2025–26 wave" list (peer-reviewed member of the wave).
7. Liu, Qiao, Zhang & Chen 2026, *Certify or Refuse: … Selective Risk Control with Coverage Floors under Covariate Shift*, arXiv 2608.10893 — one clause after Yu & Liu (exact vocabulary overlap; covariate shift is outside our scope). Lowest confidence of the eight (four days old at check time).
8. CPMORS, *J Med Internet Res* 26:e50369 (2024), doi 10.2196/50369 — §2 multi-site clinical validation paragraph (conformal + SHAP + clinician-review flag on eICU). Author list to be taken from the JMIR record when adding.

Recommended-not-required (not applied; see VERDICT.md): Xu et al. NeurIPS 2024;
Ramdas et al. Statist. Sci. 2023; Hendrickx et al. 2024; Liu et al. ICML 2024;
Lu et al. ICML 2023; Choi 2026; Liang et al. TMLR 2024; Gong et al. JBHI 2026;
Subasri et al. JAMA Netw Open 2025.

## Provenance / trust note

Verifier abstract-checked every verdict-driving paper on 2026-08-15 (arXiv pages
for 2501.02514, 2603.14096, 1802.07024, 2306.05131, 2603.24704, 2608.10893,
2512.01556, 2110.06177; JMIR e50369 via PubMed/PMC). Bibliographic details for the
eight additions must still be spot-checked by the author against the source
records before submission (same standard as `paper/TODO.md §6`).
