# Phases 4–5 — cold-read simulation & figure/caption pass (2026-08-20)

After the Phase 4 rewrite, two persona cold-readers (a clinical-informatics
researcher; an applied-ML reviewer) read the compiled 25-page PDF fresh, and
eleven figure agents ran AI-Scientist v2's `img_cap_ref_review` checklist on
every main and SI figure against its caption and in-text callouts. Raw results:
`coldread-figures/raw-results.json`.

## Cold read — verdicts

Both personas called the rewritten paper followable and unusually honest; both
independently caught **two build defects the rewrite itself introduced**, fixed
in commit `a2e8b12`:

- **STOPPER (both readers):** a blank line lost before the §3.8 heading made
  `## Explainability…` print as literal text mid-paragraph, de-numbering the
  section and shifting every "Section 3.8"/"3.9" cross-reference by one.
  *Fixed; rebuilt PDF verified to contain no literal `##`.*
- **Unfinished-build tell (ML reader):** the `wang2026lec` BibTeX `note` field
  printed "VERIFY: PMLR volume and pages not yet indexed" verbatim in the
  reference list. *Fixed (`note = {To appear}`); the VERIFY flag lives on in
  `rewrite/new-references.bib` and TODO for the author to resolve when PMLR
  indexes the volume.*

Of 33 stumbles, the highest-value fixes were applied in the same commit:
"coverage" defined at first use in the abstract; two garden-path sentences
("population calibration sampled", "the budget the walk refuses"); $n$ defined
in the betting formula; "outcome-independent" replacing the misleading
"data-independent" weight; "the published split" given its antecedent; the
per-hospital arm reworded so single-hospital pools no longer appear to
"certify"; P4's falsified-is-good inversion stated plainly; the §3.9
diagnostics sentence split; the 0.506 ≈ 1/2.0 clue made explicit; §3.2's
fractions-count-sites ambiguity resolved; the label-shift stress test's
single-site target pool declared up front; "methods archive" renamed to the
repository's methods document.

**Residual (accepted, logged):** the "site-average-not-per-site" and
"bounds-gross-violation-not-a-rate" caveats still appear ~5×/3× (down from
~11×/6×; the survivors are audit-mandated or frozen-text mirrors — see
VEN-40's verification note); clause (4)'s shared-event consequence still has no
plain-language gloss; the §3.6 BBSE block remains the paper's densest passage
for clinical readers; "skill margin" is defined only in SI A.4.

## Figure pass — 1 major, 28 minor

**Major (needs a plot regeneration — out of scope for a prose-only pass):**
Figure S6's right-panel legend box occludes the top of the record-certify bar
at $s_u = 2.0$, making a ~1.0 rate read as ~0.77.

Minor issues cluster into two groups:

1. **Image-internal (require re-rendering plots, hence out of scope; the plot
   sources still carry repo E-codes in titles/legends, snake_case axis labels
   like `brier_difference` and `n_sites`, a clipped right-panel title in
   Figure S5, fractional tick labels for the integer replicate index in
   Figure 5, phantom α=0.05 legend entries in Figure 5, and an invisible
   zero-height bar convention in S3/S6).** All are recorded in
   `raw-results.json` for a future figure-regeneration pass; regenerating PNGs
   would alter released artifacts and so was deliberately not done here.
2. **Caption/callout polish (prose-fixable):** deferred as low-priority —
   e.g., Figure 1's caption glosses $Z_c$/ρ/δ-shares but not $(c_0, c_1)$/$q_t$;
   Figure 2's caption describes the left panel at α=0.10 only; S2's caption
   says 480 pools where the plot shows the 477 deployed; S4/S6 captions
   describe quantities their plots do not display. None was judged
   submission-blocking by either reader; all are listed in the raw results.

## Disposition

Stoppers fixed and verified in the rebuilt PDF (25 pp main / 15 pp SI);
image-level findings routed to the residual-risk list (figure regeneration is
an artifact-changing operation requiring its own pass under the project's
frozen-artifact discipline).
