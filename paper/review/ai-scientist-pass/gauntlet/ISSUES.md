# Phase 3 — ranked issue list (synthesized 2026-08-19)

Inputs: 5 verbatim AI-Scientist v1 reviews (`review-1..5.json`), the area-chair
meta-review with ensemble-averaged scores (`aggregated-review.json`), and 62
specialist findings adversarially verified against the repo
(`specialist-confirmed.json`, 60 confirmed/weakened; `specialist-rejected.json`, 2
rejected). Constraints this list is scoped to: **prose-only** — no published number
changes, no new experiments, no frozen-text changes (`report.py` guarantee string,
SPEC, constants), 20–25 pp main envelope.

> *Citations re-verified against the working tree 2026-08-25.* Line numbers, paths
> and quoted text were re-pointed after the 2026-08-24 comment humanization and the
> 2026-08-25 paper de-labelling; findings, verdicts, scores and numbers are the
> originals and are unchanged.

## Ensemble baseline (Phase 6 comparison target)

| Overall | Decision | Soundness | Presentation | Contribution | Clarity | Originality | Quality | Significance | Confidence |
|---|---|---|---|---|---|---|---|---|---|
| 4/10 ×5 → 4 | Reject ×5 | 3 | 2 | 2 | 2 | 2–3 | 3 | 2 | 4 |

Calibration note: the harvested reviewer form is NeurIPS-normed ("prestigious ML
venue", reject-if-unsure system prompt), so the Decision is against a top-ML-venue
bar, not Discover Computing's. The load-bearing signal is the weakness list —
unanimous items especially — and the uniform **Presentation/Clarity = 2**, which is
exactly what Phase 4 exists to fix. Soundness 3/4 with the core called "technically
sound as far as every reviewer could verify."

## MUST-FIX (prose-actionable now; a venue reviewer would fault these)

**M1. Register: undefined terms of art at first use** (VEN-1 rung; VEN-5 WSR;
VEN-7 BBSE/"cluster-robust box"/"four corrected parameters"; VEN-10 max-softmax;
VEN-16 betting/wealth-process vocabulary; VEN-17 filtration notation; VEN-19
certification margin/learn-then-test/δ-splitting; VEN-20 c0/c1/ρ never named in
words; VEN-29 failsafe/misspecified decline codes). Fix: plain-words gloss at first
use, everywhere; "rung" gets a one-clause definition in the abstract and §1.

**M2. Abstract rewrite** (VEN-2 jargon stack; VEN-3 90-word semicolon-chain
Results; VEN-4 Conclusions is a bare number). Same facts, same numbers, readable by
a health-informatics reader; Conclusions states what was learned.

**M3. Internal codenames out of the main text** (user directive + VEN-6: bare
E1–E7 before §4, ~42 main-text hits). Each experiment gets a descriptive name
(validity grid / label-shift stress test / concept-shift control / site-count
frontier / attribution study / coverage-and-composition study / record-as-unit
comparator); §4.2–4.8 headings renamed; one mapping note stays in SI A.3 (repo
artifacts keep E-names) — as applied 2026-08-20; that note was deleted 2026-08-25
and the mapping moved to the paper's Code availability section, which names the
`E1_`–`E9_` artifact prefixes against the same descriptive names, so VEN-6's
underlying complaint is closed at least as firmly on the current text. P1–P7 stay only inside §4.10's predictions paragraph,
properly introduced as protocol labels; F-A–F-E replaced by descriptive phrases
(VEN-37: the five failure criteria are named, not coded).

**M4. Caveat deduplication** (VEN-39 "20 re-splits bound gross violation" ×6;
VEN-40 "site-average, not per-site" ×~11; VEN-41 composition disclosure ×4 near-
verbatim; VEN-49 "declines rather than…/honest" ×≥7; VEN-11 always-negative caveat
×4; VEN-8 intro para 4 duplicates abstract; VEN-12 pre-registration-by-test
software register ×4; VEN-28/30/34 table-restating sentences and captions). Fix:
each caveat stated prominently ONCE (§3.7 for estimand scope; §4.10 for re-splits
and composition), referenced elsewhere; captions stop re-arguing the body.

**M5. The base-rate fact stated plainly where the certificate is sold** (SKP-1
MAJOR CONFIRMED; meta-review's "most damaging point", unanimous). Using only
numbers already in the draft (α=0.10; pool mortality 0.090; answered 0.046;
synthetic always-negative 0.1039): say once, in §4.10 and echoed in Discussion,
that at this prevalence an always-negative rule sits near the α=0.10 budget, so
the certified rung's value is the certificate-plus-disclosures machinery, not
headroom over the base rate. No new numbers; the sentence the skeptic could not
find must exist.

**M6. E7/record-vs-site claims scoped to what the artifact shows** (SKP-2
WEAKENED; meta W5). Keep "up to twice δ under between-site heterogeneity" (already
scoped) but stop implying failure at the default heterogeneity: name that the
2δ-scale violation is the high-heterogeneity arm and that the α=0.10 rung shows
the two units nearly indistinguishable. Existing numbers only (3.5%/9.6%).

**M7. Label-shift-mode framing: evidenced by refusal** (meta W3, unanimous;
STAT-4 residue). §4.3/§4.10/abstract wording: the mode's demonstrated behavior is
correct refusal + null-point certification; do not let "robustness" read as
"certifies under shift". Scope "finite-sample" explicitly to the exchangeable mode
where the two modes are contrasted (§3.6 already carries the 0.038 disclosure;
add METHODS' "read the printed ≥0.95 with this shortfall in mind" sentence).

**M8. Statistics prose corrections** (all verified prose-actionable):
- STAT-1: "no assumption beyond boundedness" (§3.4, A.1(iv)) → "no distributional
  assumption beyond boundedness and the sampling condition of Assumption 1";
  fix Table S1's bet-cap row attribution.
- STAT-2: BBSE estimand gloss (§3.6): "reweighted to the target class prevalence"
  → add the influence-weighted-source-prevalence qualifier.
- STAT-3: A.2 "clip only widens the interval" → replace with the correct
  monotone-corner argument (SPEC/docstring wording).
- STAT-5: §6.1 population sentence → superpopulation reading ("the process that
  generated the eICU hospitals surviving the predicates"), consistent with
  Assumption 1; without-replacement variant named as future work.

**M9. §4.10 de-jargonized** (VEN-36 release-gate software terms; VEN-38 Table 2
caption carries a 200-word argument + ETL row labels; VEN-44 leak-screen ETL
logic; VEN-45 amendment wording; VEN-46 Scope paragraph ETL jargon; SKP-6 leak
screen read as clearance; SKP-7 A1 not marked pre-data). Fixes: captions describe,
body argues; leak-screen paragraph says in clinical terms what fired, that the
association sits at the cap's magnitude inverted, and why it is a caution rather
than a clearance; "the amendment that identified APACHE absence" explicitly marked
as logged before the extract was read (A1, data-seen NO) and distinguished from
the one post-hoc amendment (A6); predictions paragraph states plainly which tests
could have hurt the method.

**M10. Eight must-cite additions** (Phase 2): lee2025hierarchicalevalues,
fernandes2026abductivereject (also one clause in §1 contribution 3),
plassier2023federatedlabelshift, alexandari2018abstention, podkopaev2022tracking,
wang2026lec, liu2026certifyrefuse, cpmors2024jmir — verified entries in
`../rewrite/new-references.bib`; positioning clauses per PHASE2-NOVELTY.md.

**M11. Claim-audit fixes** (Phase 1): "roughly 80 calibration hospitals" → 74
(P1-1); "three quarters of answered errors" gets "on the synthetic grid" (P1-4);
0.038 box probe marked as a design-time measurement not in the released grid
(P1-2); "~400 clusters" covariate-shift figure hedged as an effective-sample-size
estimate (P1-3).

**M12. Structural readability** (VEN-13 atom paragraph lead-in; VEN-23 §3.7 seven
dense clauses → intro sentence + enumerated clauses; VEN-9 Figure 1 caption
defines its notation in words; VEN-33 §4.7 panel paragraph gets the panel's
purpose in plain words and drops 6-decimal asides; VEN-48 §6.1 split into
paragraphs; VEN-35 E7 paragraph unpacked; VEN-47 §5 noun stacks).

## SHOULD-FIX (clear improvements, same constraints)

S1. VEN-14 minimum-cluster gate introduced before use; S2. VEN-15 internal clause
nicknames dropped; S3. VEN-18 "information floor" named in words at first use;
S4. VEN-22 OR-guarantee/concept-tilt gloss; S5. VEN-24 "parameter, not count"
concrete example clause; S6. VEN-26 metric names defined before use in §3.9;
S7. VEN-27 implementation details thinned in §4.1; S8. VEN-31 code-style array
literals → prose; S9. VEN-32 "concept intercept 2.0" plain phrasing + thin
"load-bearing"; S10. VEN-42/43 six-decimal asides removed from captions/prose
(numbers live in tables; removal, never re-rounding); S11. VEN-50 one name per
concept (certified quantity; experiment arms); S12. SKP-3 one sentence connecting
the abstention drivers (severity axis) to the composition effect; S13. SKP-4
comparator framing: state the APACHE-IVa comparison is on the head's chosen
denominator; S14. SKP-5 concept-control framing: one clause that the control
tests the harness's ability to register a violation at one magnitude.

## FUTURE / REBUTTAL (valid; needs experiments, new numbers, or author decisions — out of scope for this pass)

F1. External cluster-aware comparator arm (Hoeffding/empirical-Bernstein/t/cluster
bootstrap on the same atoms; hierarchical CRC) — meta W4, unanimous; top rebuttal
priority. F2. Boundary stress arm with true answered risk near α (meta W6).
F3. BBSE certify-rate sweep at intermediate shifts + a configuration where it
certifies under genuine shift (meta W3, Q3). F4. Non-linear/weaker head arm
(meta W8). F5. eICU answered-set sensitivity/specificity/PPV/NPV per re-split +
patient-subgroup breakdowns (meta W8, Q9) — panel JSON holds some inputs but the
derived table is a new-numbers change. F6. Without-replacement (finite-population)
betting variant (STAT-5's deeper fix). F7. Class-conditional / cost-weighted /
FNR-bounding atoms (meta W7). F8. Title decision for the author: whether
"label-shift robustness" stays in the title given M7's scoping (prose scoping
applied in this pass; title unchanged pending author sign-off).

## REJECTED (verified against repo history)

R1. VEN-21 (BBSE miscoverage disclosure "repeated three times" → remedy would
touch the frozen guarantee text; the §3.7 instance mirrors `report.py`'s frozen
string, pinned by `tests/test_report.py`). R2. VEN-25 (SHAP-equivalence "jargon"
is the audit-mandated conditioning from S1-3, closing five referees' items; the
named value function must stay).
