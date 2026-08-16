# Phase 1 — claim–artifact audit of `paper/draft.md` (2026-08-15)

Ten independent tracer agents, one per draft section, extracted every quantitative
claim in their line range and traced it to the canonical artifact home
(`experiments/out*/`, `certgate/constants.py`, `tests/test_constants.py`). Full
per-claim inventories: `claim-audit/01…10-*.json` (577 claims). This is the
AI-Scientist "experiment" stage recast as a check: nothing was re-run.

| Section (draft lines) | claims | TRACED | DRIFT | UNVERIF. | ANALYTIC | OUT_OF_SCOPE |
|---|---|---|---|---|---|---|
| 01 Title/abstract/§1/§2 (1–47) | 40 | 33 | 0 | 0 | 4 | 3 |
| 02 §3 Methods (48–119) | 60 | 48 | 0 | 1 | 11 | 0 |
| 03 §4.1–4.4 E1–E3 (120–141) | 65 | 59 | 0 | 0 | 5 | 1 |
| 04 §4.5–4.9 E4–E7 + sens (142–163) | 44 | 39 | 0 | 0 | 4 | 1 |
| 05 §4.10 eICU (164–191) | 92 | 90 | 0 | 0 | 1 | 1 |
| 06 §5–6 Discussion/Conclusion (192–207) | 29 | 22 | 1 | 2 | 2 | 2 |
| 07 SI A.1–A.3 (208–277) | 69 | 57 | 0 | 0 | 8 | 4 |
| 08 SI A.4–A.5 (278–353) | 94 | 90 | 0 | 0 | 4 | 0 |
| 09 Backmatter + Figures (354–397) | 43 | 37 | 0 | 0 | 0 | 6 |
| 10 Tables (398–436) | 41 | 38 | 0 | 0 | 2 | 1 |
| **Total** | **577** | **513** | **1** | **3** | **41** | **19** |

Every result number in §4, the SI, the figure captions and the tables traces to
an artifact (rounding of higher-precision artifact values noted per claim; the
E6-4dp / panel-6dp asymmetry is the round-once invariant, not drift). The four
non-clean items are all in prose sections (§3, §5–6):

## Findings

**P1-1 · DRIFT (soft) — "roughly 80 calibration hospitals" (§5, line 194).**
`EICU_certificate.json diagnostic.n_cal = 74`, `EICU_pooled.csv n_cal_carrying = 74`
on all 40 rows, and the draft's own §4.10 / Figure 5 / Table 3 captions say 74.
"~80" is inherited from `METHODS.md:11`. → **Fix in Phase 4:** "the 74 calibration
hospitals". Prose-only; the published number is 74.

**P1-2 · UNVERIFIABLE — BBSE box joint miscoverage 0.038 vs nominal ≤ 0.019 (§3.6
line 94; §6.1 line 206).** A design-time probe (400 replicates at 42 and 83
auxiliary sites) recorded in `METHODS.md:43` since the freeze commit; `SPEC.md:836`
defers to METHODS; no JSON/CSV/test pins it and no script regenerates it. Not
drift — no artifact disagrees — and the number is *self-critical* (miscoverage
larger than nominal), so its presence is honest disclosure. → **Fix in Phase 4:**
keep, and mark it as a design-time probe not part of the released grid, so a
reader does not look for it in the artifacts. Residual risk: unreproducible from
the release; a future run could pin it.

**P1-3 · UNVERIFIABLE — covariate-shift scope cut "below roughly 400 clusters"
(§6.1).** Effective-sample-size rationale recorded in `README.md` (audit F34) and
`paper/TODO.md §8`; the arithmetic is not derived in SPEC or the manuscript
(previously reviewer item R5-31). → **Fix in Phase 4:** hedge as an
effective-sample-size estimate, not a measured frontier. Residual risk noted.

**P1-4 · caution (TRACED, cohort-ambiguous) — "roughly three quarters of answered
errors are false negatives at this prevalence" (§6.1 line 206).** Traces to the
synthetic grid (SI Table S5: E1 0.769, E6 0.756). On the eICU answered sets the
share is ≈0.96. → **Fix in Phase 4:** name the cohort ("on the synthetic grid").

## Bottom line

Zero hard drift across 577 claims: the 2026-08-10 single-source sweep held. One
loose paraphrase (74 → "~80") and three prose numbers without an artifact home,
all confined to the Methods/Discussion narrative and all fixable by wording.
