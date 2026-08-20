# ai-scientist-pass — final change report (2026-08-20)

A Sakana AI-Scientist-style end-to-end verification pass over the finished
CertGate project: v1's reviewer ensemble and novelty check plus v2's figure
review, harvested verbatim (Apache-2.0; provenance in
`../../../ai-scientist-harvest/HARVESTED/README.md`, commits `1de1dbc` v1 /
`96bd516` v2) and rebuilt as a *check* of frozen work — nothing generated,
no experiment re-run, no frozen text or constant touched. All LLM calls ran
through Claude in-session (`OPENAI_API_KEY` unset by user direction).

## Phase results

| Phase | Deliverable | Outcome |
|---|---|---|
| H Harvest | `ai-scientist-harvest/HARVESTED/` | reviewer form + few-shots, novelty prompts, VLM figure checklist, verbatim with provenance |
| 0 Ground truth | — | 266 passed / 3 skipped; 25 pp main + 15 pp SI + 30 pp compact |
| 1 Claim audit | `PHASE1-CLAIM-AUDIT.md`, `claim-audit/*.json` | **577 claims, 0 hard drift**; 1 soft (74 vs "~80", fixed) + 3 unsourced prose numbers (labeled) |
| 2 Novelty | `PHASE2-NOVELTY.md`, `novelty/` | **0 collisions**; headline still novel; 2 component near-misses; 8 must-cite additions applied |
| 3 Gauntlet | `ISSUES.md`, `gauntlet/` | 5 verbatim reviewers → Overall 4 / Reject ×5 baseline; 60 verified specialist findings → 12 must-fix, 14 should-fix, 8 future, 2 rejected |
| 4 Rewrite | `paper/draft.md` (commits `a2ac193`, `a2e8b12`) | all 12 must-fix applied; guard green; envelope held at 25 pp |
| 4b Cold read | `PHASE4-5-COLDREAD-FIGURES.md` | 2 stoppers (both introduced by the rewrite build — fixed), 13 top stumbles fixed |
| 5 Figures | same + `coldread-figures/` | 1 major + 28 minor; image-level items need a figure-regeneration pass (out of scope), caption items logged |
| 6 Regression | `gauntlet/rescore-results.json` | see below; suite re-run green (266/3) |

## What changed in the manuscript (prose only; verified by `rewrite/rewrite_guard.py`)

- **Codenames**: 42 bare E/P main-text hits → 0 bare E-codes; P1–P7 confined to
  §4.10 as introduced protocol labels; §4.2–4.8 renamed descriptively; one
  label-mapping paragraph added to SI A.3.
- **Register**: every term of art glossed at first use (rung, WSR, BBSE, box,
  failsafe/misspecified, coverage, information floor, wealth process); abstract
  rewritten; §4.10's ETL/software register translated; Table 2's 200-word
  caption argument moved to SI A.3.
- **Dedup**: dispersion caveat ~11→~5 (survivors audit-mandated/frozen),
  re-splits caveat 6→3, composition disclosure 4→2 + conclusion echo,
  "honest/declines-rather-than" family ≥7→2, "currencies" 3→1,
  "load-bearing" → 0 in main.
- **Honesty upgrades from the gauntlet**: the base-rate fact stated baldly in
  §4.10 (always-negative meets α=0.10 at 0.0898); record-vs-site claims scoped
  to the high-heterogeneity arm with the real cohort placed below the default
  arm; label-shift mode framed as evidenced-by-refusal, finite-sample claim
  scoped to the exchangeable mode; leak screen reworded as caution not
  clearance; pre-data amendment (A1) explicitly distinguished from the post-hoc
  one (A6); P4's falsified-is-good inversion stated plainly.
- **Statistics prose (STAT-1..5)**: boundedness claims now name Assumption 1's
  sampling condition (§3.4, A.1(iv), Table S1 bet-cap row); BBSE estimand
  approximation disclosed (§3.6); A.2's clip argument corrected to the
  monotone-corner form; §6.1's population reads as a superpopulation with the
  without-replacement variant named as future work.
- **Citations**: 8 verified additions (lee2025hierarchicalevalues,
  fernandes2026abductivereject, plassier2023federatedlabelshift,
  alexandari2018abstention, podkopaev2022tracking, wang2026lec,
  liu2026certifyrefuse, cpmors2024jmir) with positioning clauses in §1/§2.
- **Numbers**: zero new distinct numeric tokens (guard-enforced); removals only
  (values remain in tables/artifacts). Structure, floats, callouts, [[TBC]]
  set, and subsection numbering byte-compatible with `make_submission.py`.

## Before/after — the same verbatim reviewer ensemble

| Field | pre-rewrite | post-rewrite |
|---|---|---|
| Presentation | **2** (unanimous) | **3** (2,2,3,3,3) |
| Clarity | **2** (unanimous) | **3** (2,2,3,3,3) |
| Originality | 2–3 | 3 |
| Quality / Soundness / Confidence | 3 / 3 / 4 | 3 / 3 / 4 |
| Significance / Contribution | 2 / 2 | 2 / 2 |
| Overall / Decision | 4 / Reject ×5 | 4 / Reject ×5 |

No score dropped; the writing scores — the pass's target — moved. Overall is
pinned by method-level findings (novelty-as-composition; the operative rung's
thin headroom over the base rate; label-shift evidenced by refusal; no external
cluster-aware comparator), which are experiment questions, not writing ones,
and which the NeurIPS-normed reviewer weighs against a top-ML-venue bar rather
than the target collection's. Post-rewrite re-trace: 306 claims, 0 hard drift.

## Residual risks / open items

1. **FUTURE/REBUTTAL experiment items** (ISSUES.md F1–F8): external cluster-aware
   comparator arm (top priority for a rebuttal), boundary stress arm, BBSE
   certify-rate sweep, non-linear head, eICU answered-set sensitivity/subgroup
   table, without-replacement variant, cost-weighted atoms, and the author's
   title decision on "label-shift robustness".
2. **Figure regeneration pass** (S6 legend occlusion is the one major; plot
   titles still carry E-codes; full list in `coldread-figures/raw-results.json`)
   — touches released artifacts, so it needs its own decision.
3. **wang2026lec** PMLR volume/pages unindexed (note field now "To appear");
   the 8 new bib entries await the author's own spot-check per TODO §6 standard.
4. Prose items accepted as-is: remaining caveat repetitions (audit-mandated),
   clause (4) without a plain gloss, §3.6 density for clinical readers,
   "2014–2015" sourced to the data descriptor (citation-territory), 89.5% and
   the 9–30% literature figure remain prose-sourced as before.
5. Branch `ai-scientist-pass` is left **unmerged** for author review.
