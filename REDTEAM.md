# REDTEAM — internal red-team pass (audit-playbook rerun on certgate)

**Run:** 2026-07-21 → 22 · 6 adversarial reviewer lenses + independent skeptic verification of every
actionable finding (skeptics default to *refuted*; 2 votes on critical/major, 1 on minor) ·
14 agents, ~1.34M tokens · This is the "internal red-team pass" from PAPER-OUTLINE.md's week 6–7,
pulled forward.

**Verdict: 1 confirmed (major, documentation/justification — the guarantee itself holds), 1 contested
(same defect found independently by a second lens), 3 refuted, 5 notes.** The lenses attacking the
estimand algebra (`influence_atoms`, neutral atoms, M-cap, Hole-1 regression) and the WSR core
(λ predictability, Ville's inequality, fixed-sequence multiplicity, seed rule) returned **zero
findings**. The pipeline/report lens verified the SPEC audit-lesson checklist item by item and found
nothing actionable.

## RESOLUTION (applied 2026-07-22 — suite 53/53 green; independently re-derived, all checks PASS)

- **R1 — FIXED** (fix option 1). SPEC.md, METHODS.md §5, and the `certify_bbse` docstring now carry
  the scale-invariance/convexity justification (sign(E[Z]−α) = sign(A + ρB) is affine, so the
  certifiable set is a convex interval); the false "atom mean is affine / worst case at an endpoint"
  claim is gone everywhere unqualified. New test `test_dual_endpoint_soundness_straddling_rho_one`
  pins the property on the production `wmax=max(1,ρ)` path across an interval straddling ρ=1 (sign-
  carrier second-diff ~1e-16; raw atom mean visibly kinked ~8e-3, guarding against re-affining). The
  certified path itself is unchanged, so all E1–E6 numbers are byte-identical on re-run. R2 was the
  same defect and is closed by the same fix.
- **R3 — salvaged (note-level).** METHODS §7 now states the hard-violation criterion evidences
  absence of *gross* violation at the tested power, with the guarantee resting on the betting test's
  finite-sample level, not the harness.
- **R4 — salvaged.** The PI_CLIP comment (shift.py) and SPEC.md parenthetical now say the range gate
  guards only the widest corner and any inner-corner clip only *widens* [ρ_lo, ρ_hi] (conservative),
  replacing the false "containment only" claim.
- **R5 — salvaged.** Every conditional rate in the E1–E3 summaries now carries `n_certified`, and a
  zero-certificate rung reports `null` (not 0.0) with a "no certificates" figure annotation.
- **N2 — FIXED.** BBSE guarantee text (report.py) now attributes δ_conf=0.025 to the S_aux bootstrap
  box coverage, not the calibration draw.
- **N3 — FIXED** (same change as R5). **N4 — FIXED**: dead `true_risk` parameter removed from
  `exceedance_reference`. **N5 — FIXED**: README E6 coverage quoted as 0.897–0.919.
- **N1 — left as a note** (negligible in the operating regime; degenerate-bootstrap decline covers
  the regime where it wouldn't be). No code change.

---

## CONFIRMED (fix before submission)

### R1 — The BBSE dual-endpoint justification is wrong for the code as written, and the cited test does not exist

*(major · METHODS.md §5, SPEC.md "shift.py" section, `certify_bbse` docstring in shift.py ·
found independently by two lenses — `bbse` (confirmed 2/2 skeptics) and `claims-crosscheck`
(contested 1/2 — the dissent agrees the test-citation clause is false but reads METHODS's
"at fixed weight normalization" qualifier as saving the prose)*

**The claim in the docs.** METHODS §5 (and the `certify_bbse` docstring, and SPEC.md) justify the
dual-endpoint walk by: the certified statistic is *affine in ρ*, so the worst case over [ρ_lo, ρ_hi]
is at an endpoint — "verified numerically in the test suite, including intervals straddling ρ=1."

**What is actually true.** `certify_bbse` builds each endpoint's atoms with its **own**
normalization `wmax = max(1, ρ)` (shift.py:191). Under that per-endpoint normalization the computed
atom mean is *piecewise*: m(ρ)−α = Ā + ρ·B̄ for ρ≤1 but Ā/ρ + B̄ for ρ≥1 — a kink at ρ=1. When
Ā>0 and B̄>0 the maximum is the **interior** point ρ=1, not an endpoint. Both skeptics and both
finders reproduced this numerically on the real `influence_atoms` path (e.g. m−α = 0.212 at ρ=0.2 →
0.274 at ρ=1 → 0.143 at ρ=3; second-difference ≈ 0.05, a real kink). So "affine in ρ" and "worst
case at an endpoint" are both false *for the statistic the code computes*.

**Why the guarantee nevertheless holds (the argument the docs never state).** The statistic is
scale-invariant in the weights, so sign(m(ρ)−α) = sign(Ā + ρ·B̄), which **is** affine in ρ. Hence
the certifiable set {ρ : E[Z] ≤ α} is a convex interval, and both endpoints certifying implies every
interior ρ — including the true ρ* — is certified. In the interior-peak regime (Ā>0, B̄>0), Ā+ρB̄ > 0
for *all* ρ>0, so both endpoints also sit above α and certification correctly fails. Each endpoint's
atoms stay in [0,1] under its own wmax, so each WSR test is individually valid. Verified numerically:
(m(ρ)−α)·max(1,ρ) has second-difference ~1e-15. **No experiment, number, or certificate changes.**

**The test gap.** `test_statistic_affine_in_rho` (tests/test_shift.py:117-133) uses a **fixed**
wmax=5.0 and ρ ∈ {1,2,3} — no straddle of ρ=1 and not the per-endpoint-wmax production path. It
verifies affine-at-fixed-normalization, a different statement. No test in the suite exercises a
straddling interval on the production path, so METHODS's "verified numerically … including intervals
straddling ρ=1" cites a verification that does not exist. Note ρ intervals straddling 1 are the
*common* case near null shift, not an edge case.

**Fix options** (SPEC.md first, per the project invariant):

1. **Recommended (editorial + one test, no certified-path change):** rewrite the justification in
   METHODS §5, SPEC.md, and the `certify_bbse` docstring to the scale-invariance/convexity argument
   above; add a test that exercises `certify_bbse`'s per-endpoint-wmax path across an interval
   straddling ρ=1 (pinning that (m(ρ)−α)·max(1,ρ) is affine / the certifiable set is an interval).
2. Alternative: build both endpoint atom sets with a single shared wmax ≥ max(1, ρ_hi), which makes
   m(ρ) genuinely affine and the existing prose literally true — but this changes certified-path
   numerics (atom values shrink for the lo endpoint), so certificates would not be byte-identical
   with prior runs; higher-risk for no statistical gain.
3. Alternative: additionally test ρ=1 as a third atom set when ρ_lo<1<ρ_hi — closes the interior
   worst case directly but is unnecessary given the convexity argument, and also changes the
   certified path.

---

## CONTESTED (same root cause as R1)

**R2 — "BBSE dual-endpoint soundness claim is false for straddling boxes"** (claims-crosscheck lens).
Same mathematics as R1, filed with a harsher framing. The refuting skeptic's argument: METHODS's
sentence contains the qualifier "at fixed weight normalization," under which the affine claim is
true, and the certified estimand R_M(ρ) is linear-fractional hence monotone in ρ (worst case at an
endpoint for the *risk*, if not for the normalized atom mean); the surviving kernel is only the
false test-citation parenthetical. Either way the action items are identical to R1's fix option 1.

---

## REFUTED (kept for the record — each leaves a cheap paper-hardening item)

- **R3 — Wilson-LCB hard-violation metric under-detects mild violations** (harness lens, filed
  major, refuted 2/2). The math is right — the detector has low power against a certificate
  violating marginally above α — but the guarantee is a *theorem* (WSR + Ville), not something E1
  establishes; WSR type-I is separately unit-tested at the boundary; and METHODS 7 defines the
  metric honestly. *Salvage:* add one sentence to METHODS §7 framing E1 as "no evidence of violation
  at the tested power," and/or a detectability note (smallest excess the R=200 design can see).
- **R4 — PI_CLIP "containment only" comment is wrong at inner box corners** (bbse lens, filed
  minor, refuted). The clip *can* bind at inner corners in principle, but the skeptic instrumented
  all 158 successful BBSE fits across the shipped generators: **0 bindings**, and any binding only
  widens the ρ interval (conservative). *Salvage:* one-line rewording of the comment + SPEC
  parenthetical ("clip only widens the corner interval; range gate protects the widest corner").
- **R5 — E2 BBSE "0.0 violations" rests on 9 certified draws** (harness lens, filed minor,
  refuted). Wrong quantity: the guarantee bounds the *joint* event P(certify AND violate); over all
  200 draws that's 0/200 (rule-of-three UB ≈ 0.015 < δ). Declines satisfy the guarantee vacuously.
  *Salvage:* print n_certified beside every conditional rate in summary/figures.

## NOTES (no action required; consider before submission)

- **N1** Bootstrap validity-conditioning (≥1 pos & ≥1 neg per resample) is a finite-sample selection
  distinct from the disclosed asymptotic caveat — negligible in the operating regime; the
  degenerate decline covers the regime where it wouldn't be.
- **N2** BBSE guarantee text attributes the full 1−δ to "the draw of calibration sites," but
  δ_conf=0.025 is spent over the **S_aux** bootstrap box. Level is right; the randomness-source
  attribution is loose. Cheap fix in `report._statement` for BBSE rows.
- **N3** `hard_violation_rate = 0.0` when a rung never certifies reads, in the E1–E3 figures, like a
  validated point. Emit None/annotate certify_rate=0 rungs.
- **N4** `exceedance_reference(true_risk=…)` is a dead parameter — always called with p=α (the
  boundary curve). Drop it or use it.
- **N5** README states E6 per-site coverage "0.90–0.92"; measured minimum bin is 0.8966. Use "~" (as
  CLAUDE.md does) or quote 0.897–0.919.

## Clean lenses

- **estimand-atoms** — Z_c ∈ [0,1] incl. weighted mode, E[Z]≤α ⟺ R_M≤α with neutral atoms,
  M-cap data-independence, Hole-1 regression adequacy: no findings.
- **wsr-walk** — λ predictability, supermartingale validity under the λ-cap, log-clamp never binds
  in range, fixed-sequence multiplicity argument incl. correlated permutation streams, deploy rule,
  seed-rule collisions: no findings.
- **pipeline-report** — OR-combination, guarantee clauses vs. proof, decline partition, the full
  SPEC audit-lesson checklist (F01…F57, B-5…B-10) item by item, determinism, tier labeling:
  no actionable findings (N2 only).
