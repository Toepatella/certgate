# Revision 2 — final report (2026-08-20)

Closes the plan of 2026-08-14 ("closing the score-pinning weaknesses"). Everything below
ran on branch `revision-2`; the harvested SakanaAI reviewer ensemble (5 × NeurIPS-form
reviewers + meta-review, per `../ai-scientist-harvest/HARVESTED/README.md`) is the
scoring instrument throughout. Full final-run JSON: `final-rescore.json` (this
directory). One caveat on the final panel: reviewer `final-1` died on an Anthropic
safeguards API error (`[reasoning_extraction]`, infrastructure, not a judgment), so the
final ensemble aggregates **4 of 5** reviewers.

## Score trajectory (same ensemble, three gates)

| Field         | Pre-rewrite (main) | Post-rewrite (ai-scientist-pass) | Post-revision-2 (this branch) |
|---------------|:---:|:---:|:---:|
| Overall       | 4   | 4   | **5** |
| Decisions     | Reject ×5 | Reject ×5 | Reject ×3 + **Accept ×1** (Overalls 4,4,4,6) |
| Originality   | 2   | 3   | 3 |
| Quality       | 3   | 3   | 3 |
| Clarity       | 2   | 3   | 3 |
| Significance  | 2   | 2   | 2 (one reviewer at 3) |
| Soundness     | 3   | 3   | 3 |
| Presentation  | 2   | 3   | 3 |
| Contribution  | 2   | 2   | **3** |

Against the plan's bar (Sig/Contrib ≥3, Overall ≥6): **Contribution met, Overall 5 of 6,
Significance still 2** — the field the plan pre-identified as ceiling-bound: the ensemble's
residual objection is that the certified rung sits near the base rate on this cohort, which
is a property of the estimand and the honest disclosure, not a fixable defect. The plan's
own calibration ("5–6 borderline is the realistic NeurIPS-rubric ceiling for a composition
paper; that over-covers the actual venue's applied-clinical-ML bar") is exactly where the
paper landed, with the ensemble's first Accept.

## What moved the score (the four unanimous weaknesses, all closed)

1. **No valid comparator on the same atoms** → E8-A: four alternative one-sided UCB walks
   (Hoeffding, Maurer–Pontil EB, Student-t, site-bootstrap) on identical atoms and walk
   order. Result: WSR dominates every *valid* bound (Hoeffding certifies nothing; MP-EB
   only α=0.10 at 400 sites); the two asymptotic bounds certify everything and run at
   nominal exceedance (~0.05) with zero safety margin, vs WSR's 0.0. Paper §4.11.
2. **FNR uncertified / rung near base rate** → E9-B: the label-weighted atom certifies
   FNR budgets on synthetic (0.55 first issuable at 400 sites; 0.4 never; every issued
   certificate held), and the eICU derived FNR ≈0.87 is reported post-hoc as the priced
   consequence of the symmetric loss. Paper §4.13 + §4.10 + §3.3.
3. **Label-shift mode never positively demonstrated** → E9-A: the BBSE power frontier —
   0/0/0.38/0.94 certify rate across 208→1200 source sites under a 40-site declared
   target, zero exceedances, box width 3.47→2.22; the single-site declared-target arm
   plateaus at 0.40 with measured exceedance 0.10 — the pre-declared "multi-site declared
   target or not at all" finding. Paper §4.13.
4. **Validity unstressed** → E8-B label-noise stress frontier (certify rate collapses
   1.0→0.02 across η=0.01→0.04 with **zero** exceedances — declines-before-violates) and
   E8-C alternative heads (GBM + feature-denied; every head certifies with zero
   exceedances; the denied head pays as coverage 0.88 vs 0.98). Paper §4.12.

Plus the open reviewer items: S2-28-eICU (derived confusion table → Table S7),
S2-36 (subgroup panel → Table S8 + `out-subgroups/`), S2-26/S2-27 (heads, E8-C).

## Residue pass (the one permitted, 2026-08-20)

Two prose-only edits from the final panel's still-actionable weaknesses, then freeze:

- **Equity deployment consequence** (§4.10): one sentence stating that the deferred
  workload concentrates on the oldest/sickest and an adopting site should staff the
  deferral pathway accordingly.
- **Assumption-1 temporal exposure sharpened** (§6.1): the real cohort's re-splits
  partition one fixed hospital list within a single 2014–2015 window.

Compensating micro-cuts (4 sentences tightened) held the build at **25 pp main + 19 pp
SI**; `revision_guard.py` green (104 added distinct numeric tokens, all traced to
artifacts in `claim-trace.md`; no bare E-codes in main text); suite **281 passed /
3 skipped**; every released E1–E7 artifact and the real-data certificate byte-identical
throughout (P0.0 control 22/22, post-E8/E9 grid 22/22, landing 7/7, `run_eicu` rerun ×2).

**No further re-score.** The plan allows one residue pass then freeze; at n=4 reviewers
another ensemble roll is variance, not signal. FROZEN as the submission candidate.

## Deliverables ledger

- Experiments: `experiments/comparators.py`, `run_E8`/`run_E9` in `run_synthetic.py`
  (streams 8/9, constants pinned), `experiments/panel_confusion_tables.py`,
  eICU subgroup block in `run_eicu.py` (+`out-subgroups/`), all artifacts in
  `experiments/out/` with E1–E7 blocks preserved byte-identical.
- SPEC: E8/E9 sections with pre-committed two-sided readings, outcome-weighted-atom
  section, EICU-SUBGROUPS pin amendment 2026-08-20 (SPEC→code→tests ordering kept).
- Paper: §§4.11–4.13 new; §4.10 + §3.3 + §6.1 + abstract/contributions updated; mains
  Fig 1–4 / Tables 1–2; SI S1–S9 / Tables S1–S9. Built PDFs in `paper/build/out/`.
- Review corpus: this directory (`PHASE0-PROBES.md`, `claim-trace.md`,
  `revision_guard.py`, `final-rescore.json`, this report).

## Remaining (user-owned)

`[[TBC]]` author facts · LICENSE/CITATION.cff name · repo-public confirmation · Zenodo
v1.0.0 DOI at the final tag · wang2026lec PMLR volume when indexed · optional figure
cosmetics (S6 legend occlusion; E-codes inside plot internals). Submission deadline
2026-10-05.
