# CertGate manuscript — TODO (open items for the human author)

Draft: `paper/draft.md` · References: `paper/references.bib`
Status 2026-07-30 (truth-sync): `draft.md` resynced to the 2026-07-25 correctness audit
(CODE-AUDIT.md V1–V27) and the 2026-07-25 experiment rerun. Retired the per-target-site estimand
in favour of the site-population average with its mandatory dispersion clause (V1), the "q_t is
exact" premise (V2) and the "single asymptotic link" claim (V13); added the operative-rung
1−2δ clause (V27) and the four-parameter/16-corner BBSE box; replaced every experiment number
with the sep=2.2 rerun values. Sections touched: Abstract; §1 (¶4, ¶5, contributions 1/2/4);
§3.1, §3.2, §3.3, §3.4, §3.5, §3.6, §3.7, §3.9, §3.10; §4.1–§4.7; §5.1; §6 and §6.1; A.1, A.2,
A.3; Figures 1–6; Tables 1–4. Two notes for the human author: (a) TODO §0 below still cites
"69/69 tests" from the 2026-07-23 readiness audit; (b) the suite measured on 2026-07-30 is
136 passed + 1 skipped (137 collected), not the 135/135 recorded in CLAUDE.md — A.3 now states
the measured figure, and CLAUDE.md's status line needs the same correction.
Status 2026-07-24: manuscript complete; revised through THREE author-feedback rounds (novelty
softened to a single "we combine" framing with zero "first" claims; explainability demoted to
an implementation feature; ~9% net prose cut on top of the earlier trims while Methods gained
an explicit four-step validity argument for the central theorem); adversarial reviewer panel
run on the final text. Every empirical number traces to `experiments/out/`; every citation
verified against a primary source.

---

## 0-pre. Panel S2 writing pass, 2026-07-30 — what closed and what is still open

Three work-items from `review/revision-plan.md` were written this pass. Every number below
regenerates from the repo; none was estimated.

**S2-2 · deployment-rule reconciliation — CLOSED.** The two rules never conflicted; the paper
just never said they act at different levels. §3.5 now states all three explicitly (within a
mode → lowest certified τ = maximum coverage; across modes → largest of those, i.e. most
conservative; across rungs → strictest certified α) and §3.6's Combination paragraph states the
non-conflict directly. `R1-59`'s open question — *on which pool is the deciding coverage
measured?* — is answered outright: **none, and none is needed**, because {x : s(x) ≥ τ} is
nested and decreasing in τ, so the lowest certified τ maximizes coverage on every pool at once.
Reported coverage is a separate quantity, measured on the target pool after τ* is fixed.
Verified against `certify.fixed_sequence_walk` (`deployed = min(certified, key=tau)`) and
`report._combine_alpha` (`deploy = max(cert, key=tau)`). Mirrored into `METHODS.md` §2/§4 and
`SPEC.md`'s `certify.py` block.
*Carried along, because the sentence being rewritten contained it:* §3.6's "each at full δ" was
FALSE (`pipeline._baseline_walk` spends `DELTA`, `shift.certify_bbse` spends `BBSE_DELTA_BET`)
and is corrected in both `draft.md` and `METHODS.md`. That closes half of **S2-1**; the other
half — a stated error probability for the *deployed* decision across modes and rungs — is still
open.

**S2-13 · constants justification + sensitivity — CLOSED.** New **Table 5** gives every frozen
constant with its role and the basis for the value (which also completes §3.2's enumeration and
so closes **S2-25**: `MIN_ANSWERABLE = 10`, `PI_CLIP = 1e-4`, `SD_REL_TOL = 1e-9`,
`HEAD_MAX_ITER = 2000`, `n_boot = 500` all now appear with values). New **§4.9 + Table 6** sweep
the one constant that moves the certificate: E1's `s_u=0.5` arm, baseline mode, R=200, at
M ∈ {25, 50, 100, 200, 500, 1000, 5000}, walk order and calibration walk re-derived at each M
and each certificate rescored against R_M *at that same M*. Result: a plateau over M ≤ 200
(certify 1.0, τ* ≈ 0.552–0.566, coverage 0.980–0.984) and a collapse above it (M=1000 → 0.03;
M=5000, where g_c = n_c for every site, → 0.0). Every larger M certifies *less*, so M=100 is
demonstrably not tuned to make certification easy. α=0.05 unreachable at every M.
Also fixed/added: §3.3's "full adverse **weight**" → "full adverse **error rate**" (`R5-26`);
the cap arithmetic stated in §3.3 (89.5% of sites capped, 86% of records above their own cap,
min g_c/n_c = 1/50, a 5,000-record and a 100-record site carry identical influence — `R1-14`);
record-level answered error reported beside R_M in §4.2 (0.0566 vs 0.0567) and §4.7 (0.0555 vs
0.0619 — E6 is where they separate); a new §6.1 limitation stating that only M is swept.
*PLAUSIBLE findings settled:* **`DS-45`** — dropping empty/silent sites does NOT change R_M's
numeric value (with a_c = 0 both terms vanish); what it changes is the reference population and
the bet schedule (a neutral atom contributes wealth factor 1 but still occupies a sequence
position and still counts in the n setting λ_t), and §3.3 now says exactly that.
**`R1-13`** — minimum certified coverage across E1's 200 draws is **0.871**, so no
low-coverage certificate exists and the "trivially satisfiable by abstaining" limb is dropped;
§4.2 states the minimum. **`R2-27`** — the record-carrying-but-answers-nothing case occurs
**zero** times across E1's 200 draws and E6's deployment; §3.3 and §4.7 say so rather than
leaving it unmeasured.

**S2-28 · clinical target, loss, operating point — CLOSED.** §3.1 gains a specification block
(outcome pinned by index event / prediction time / ascertainment window; ŷ = 1[p̂ ≥ 1/2];
err_i = 1[ŷ ≠ y]; s(x) symmetric about p̂ = 1/2 so the gate adds no clinical threshold of its
own; symmetric 0–1 loss stated as a modelling choice). §4.1 gains an **Outcome and time**
paragraph disclosing what the synthetic harness does *not* instantiate — no time axis, no
censoring, no competing risks — so §3.1 reads as a requirement on a real deployment, not as a
description of `data.py`. New **Table 7** gives answered/declined confusion-derived operating
characteristics for E1 (pooled, R=200) and E6. The two disclosures that matter:
- **answered-set sensitivity 0.550 (E1) / 0.541 (E6)**, and **77% / 76% of answered errors are
  false negatives** — the asymmetry the symmetric loss does not price;
- **an always-negative rule errs at 0.1039 on E1's pools and 0.0968 on E6's**, so α = 0.10 is
  only marginally stricter than the trivial rule. §3.1 and §4.2 now say this plainly and point
  at sensitivity and composition as the columns that carry the evidence instead.
Declined-set positive fraction is **0.492 (E1) / 0.462 (E6)** against ~0.10 in the pool — a
~4.7× enrichment, routing 8.6% of all positives to a clinician. §5.4 gains the paragraph
mapping §1's community-hospital scenario onto the three assumption cases (`R2-10`), and §6.1 a
limitation on the symmetric loss and the inherited p̂ = 1/2 boundary.

**Still open inside these items.** S2-28 asked for a *clinical* framing of the FP/FN weighing;
what is written states the asymmetry and its size but proposes no cost ratio — deliberate, since
none is defensible without a named decision. No calibration diagnostic is reported (that is
**S2-26**, untouched here). S2-13's "ideally the two decline thresholds" sweep is not run — only
M is swept, and §6.1 says so.

**Reproducibility gap you should close.** Tables 6 and 7 come from a new read-only module,
`experiments/panel_s2_tables.py` (`python -m experiments.panel_s2_tables [R]`, ~2 min at
R=200, prints JSON, writes nothing to `experiments/out/`). It reseeds the same draws through
`run_synthetic`'s own rule and **hard-asserts** that its replay reproduces every
baseline-deploying draw's certified τ from the released `E1_validity.csv` (194/194, zero
mismatches) before emitting anything. But it is *not* wired into `run_synthetic.py`'s CSV and
summary writers, so `python -m experiments.run_synthetic` alone does not regenerate those two
tables — §3.10 and A.3 have been narrowed to say so honestly. Folding it into the driver (and
into `summary.md`) is the follow-up, and belongs with panel item **S2-24**.

## 0. Real clinical dataset (highest-value item — needs data access only you have)

Reviewer-priority feedback: "Add at least one real clinical dataset, even if only the baseline
mode can be demonstrated." This cannot be done from the repo — no real data exists in it — but
the pipeline is ready today: `certgate/validate.py:from_raw` is the loader contract,
`examples/real_data_example.py` is the worked CSV→certificate walkthrough, and the real-data
readiness audit (2026-07-23) verified the full path end-to-end (suite green incl. from_raw
round-trips; a hostile-fixture integration test now also covers it — see
experiments/synth_fixture.py). If a documented multi-site cohort lands before the 2026-10-05 deadline, the
addition is one experiment section + one table; PAPER-OUTLINE.md's timeline already budgets
for this. Until then the paper stands on the synthetic study, defended in §4.1/§5.

## 0b. Venue-fit assessment (Discover Computing / "Intelligent Medicine" collection)

Verdict from a 3-agent check (topic map + live journal-profile research + exemplar comparison),
2026-07-24: **on-topic, but form-risky; the real dataset is the decisive mitigant.**

- **Topic fit: strong.** Collection Topic 5 ("calibration and uncertainty quantification,
  out-of-distribution robustness, and explainability techniques designed for clinical
  auditability") is a direct hit; the collection text invites "ML theory, methods, and
  applications." Topics 1 and 6 partial; Topic 4 (federated) adjacent by the paper's own
  admission; Topics 2/3/7 out of scope. No paper hits all seven — this is fine.
- **Form fit: weak precedent (the real risk).** Across 2025–26, Discover Computing (journal
  10791, formerly the Information Retrieval Journal) shows NO finite-sample / conformal /
  selective-prediction / risk-control methods paper; all recent healthcare articles are applied
  real-cohort clinical ML with XAI (lung-cancer survival 10791-026-10014-2; cardiovascular risk
  10791-026-09973-3; Pentraxin-3 sepsis 29:344). CertGate's genre conventionally publishes at
  arXiv / Annals of Applied Statistics / Statistics and Computing / IJDSA / ML conferences.
  A synthetic-only methods paper would be an outlier here.
- **Data: the deciding factor.** The one published collection exemplar and every healthcare
  paper in the journal use real cohorts. A real multi-site run (even baseline mode) converts a
  risky outlier into a defensible fit and answers the biggest reviewer objection. If real data
  does NOT land before 2026-10-05, consider AoAS / Statistics and Computing / IJDSA as more
  natural homes for a synthetic-only version.
- **Explainability tension:** the collection's central emphasis is XAI, and we demoted it. Net
  assessment: the demotion is honest (our attributions are auditability, not the "educational
  aid / causal reasoning" the collection foregrounds) and the title already leads on
  certification, so keep explainability VISIBLE as clinical auditability rather than re-promote
  it. Don't let the title/abstract disown it.
- **Actions already captured:** real data (§0), numbered-Vancouver refs (§3). Optional: two
  Discussion bridge sentences in the collection's vocabulary (trustworthy / cluster-level
  fairness / cross-institutional) without overclaiming federation.

Sources: link.springer.com/journal/10791/aims-and-scope; /updates/26580658 (IR-Journal lineage);
/collections/gjbedjebba (collection call); exemplar 10.1007/s10791-026-10203-z.

## 1. Author metadata (blocking — front matter placeholders)

- `[AUTHOR NAME(S)]`, `[ORCID]`, `[AFFILIATION — department, institution, city, country]`,
  corresponding-author `[NAME], [EMAIL]` at the top of `draft.md`.

## 2. Declarations to complete (blocking)

Declarations are now formatted as INDIVIDUAL sections mirroring the accepted collection exemplar
(Discov Computing 29:344): Data availability, Funding, Author contributions, Ethics approval and
consent to participate, Consent for publication, Competing interests (plus an optional
Acknowledgements). Filled already: Data availability (synthetic, code-generated; folds in the
code URL exemplar-style), Ethics (Not applicable — synthetic), Consent for publication (Not
applicable). Still `[TO BE COMPLETED]`:

- **Funding** — statement (or "The authors received no funding for this work.").
- **Competing interests** — declaration.
- **Author contributions** — CRediT-style statement.
- **Code repository URL** — appears once, inside Data availability (`[CODE REPOSITORY URL — to be added]`).
- **Acknowledgements** — optional; delete the placeholder if unused.

Note: the exemplar renders declarations as individual sections (Springer's XML pipeline splits
them regardless of submission format). Springer's manuscript *guidance* alternatively allows a
single "Statements and Declarations" umbrella with bold run-in subheadings — either is accepted;
the individual-section form here matches the accepted exemplar. Trivially reversible if the
submission system prefers the umbrella.

## 3. Journal formatting — decisions you must confirm on the live guidelines

The per-journal Discover Computing submission page (Springer journal 10791) is behind an auth
wall, so two items could not be pulled directly and need your confirmation:

- **Reference / citation style (CSL) — RESOLVED (verify once).** The published collection
  exemplar (Discov Computing 29:344, 2026) uses **numbered, Vancouver/Springer-basic references
  with in-text `[n]`** — that is Discover Computing's de-facto style. Convert with a
  `springer-vancouver`-family CSL: `pandoc draft.md --citeproc --bibliography=references.bib
  --csl=springer-vancouver.csl -o …`; the `[@key]` citations render to `[1], [2], …`
  automatically. (Do not hand-format the bibliography; let CSL do it. Confirm against the live
  guidelines when you have login access, but the exemplar is strong evidence.)
- **Abstract length / structure.** Confirm the 250-word cap and that an unstructured abstract is
  accepted (current abstract is 248 words, unstructured).

Confirmed and already applied from Springer's standardized author instructions:
- "Statements and Declarations" section + subheading set and order (see §2).
- Title-block order (title → authors/ORCID → affiliation → corresponding author → abstract →
  keywords), numbered sections 1–7.

Conversion notes:
- Target format: Springer accepts LaTeX (**sn-jnl / sn-article-template**, on Overleaf) or Word.
  From this markdown master, `pandoc draft.md --citeproc --bibliography=references.bib -o …`
  produces either; for LaTeX, convert into the sn-jnl template shell.
- Some equations use pandoc **display math** `$$…$$` (R_M, Z_c, WSR wealth/λ). Confirm the
  conversion pipeline renders display math, or move them into the template's equation
  environment.
- Keywords currently use middot (`·`) separators — adjust to house style (some Springer journals
  use semicolons).

## 4. Title — working title kept; alternatives to consider

Current (unchanged working title): *CertGate: finite-sample certified selective prediction for
multi-site clinical risk models, with label-shift robustness and explainable abstention.*

Alternatives:
1. *Certified selective prediction for multi-site clinical risk models: site-as-unit guarantees
   under label shift with explainable abstention.*
2. *CertGate: site-as-unit finite-sample risk certificates for clinical selective prediction,
   robust to label shift and explainable at abstention.*
3. *When record-level confidence lies: certified selective prediction across clinical sites with
   label-shift robustness and explainable abstention.* (punchier; less conventional for the venue)

## 5. Figures — polish wishes (source PNGs in `experiments/out/`)

The six figures are mapped to captions in `draft.md`; regenerating the PNGs is a repo (code)
task and out of scope for the paper directory. Wishes flagged while writing the captions:

- **Fig 3 (E3):** the PNG title is truncated (`…certificate shou…`); regenerate with a shorter
  title or tighter layout so the full text shows.
- **Fig 2 (E2):** the BBSE bar sits at 0.0 and is nearly invisible; add an on-figure annotation
  ("BBSE: 0/9 violations, certified 9/200, declined 95.5%") so the decline story reads without
  the caption.
- **Figs 1/2/3:** the α=0.05 "no certificates" marker is a faint rotated label in a large empty
  margin; make it a clear labeled bar.
- **Fig 5 (E5):** annotate feature 0 as the top abstention driver (gap −0.854) on the gap panel.
- **Fig 6 (E6):** only mean answered error is plotted; per-site coverage (0.897–0.919) lives only
  in Table 2 — consider a second panel/twin axis so "no coverage collapse" is visible in the figure.
- **Fig 4 (E4):** mark the 208-site operating point (e.g. a vertical guide) so the operative rung
  reads directly.
- Table 4 (E4 grid) is optional: every value is stated in-text, so drop it if length is tight.
- **In-text figure callouts:** Figures 1–6 are currently referenced only via their captions; add "(Figure N)" callouts at the relevant points in Results (E1→Fig 1, etc.) during typesetting so each figure is cited in the body, per journal convention.

## 5a. Confidence intervals — what was added, and the one gap needing a re-run

Added this session (computed exactly from the recorded counts with Clopper–Pearson, scipy-verified,
NOT estimated): E1 hard-violation 2/200 → 95% CI [0.001, 0.036]; E2 baseline 97/200 → [0.414, 0.557];
E2 BBSE joint 0/200 → [0, 0.018] (consistent with the rule-of-three 0.015); E3 166/200 → [0.771, 0.879].
A sentence in §4.1 states that all primary rates carry exact CIs.

**GAP (needs an experiment re-run — I cannot produce these from the recorded artifacts):** the
*mean-coverage* figures (E1 0.9722; E4's 0.9304/0.9715/0.9601/0.9621 and 0.7376/0.8455; E6 per-site
coverage) are means over draws, and the per-draw standard deviations are not in `experiments/out/`.
To report SEs/CIs on coverage, re-run the grid emitting per-draw coverage SDs (or bootstrap them),
then add "± SE" or a CI to those figures. Cheap to do, and it closes the reviewer request fully —
but it changes `experiments/out/`, so it is yours to run.

## 5b. Methods length — where further cuts remain (if a top-ML reviewer pushes)

The two full proofs are now in Appendix A (A.1 validity, A.2 dual-endpoint soundness), so main-text
§3.4/§3.6 are down to theorem + intuition + pointer — the primary length lever the reviewer feedback
asked for. The pre-registration (§3.2) and budget-ladder (§3.5) paragraphs were also compressed. If a
further cut is wanted without touching rigor, the remaining compressible spots are: §3.10 (software/
reproducibility — could shorten the pinned-version list to a one-line pointer to `requirements.txt`),
§3.6's three decline conditions (could tabulate), and the concept-shift statement, which still appears
in §3.6, §3.7 clause (4), §4.4, §5.1 and §6.1 — each in a distinct role (mode boundary, guarantee
clause, experiment, discussion, limitation), so they were kept, but §5.1's restatement could reference
§4.4 instead. Say the word and I'll do a targeted pass on any of these.

## 6. Unverified / excluded citation (do NOT cite until verified)

- **`scireports2026deferral`** — "Conformal selective prediction with cost aware deferral for safe
  clinical triage under distribution shift", *Scientific Reports* 2026 (s41598-026-40637-w).
  Auth-walled this session; the primary page could not be fetched, and the author list
  (tentatively Kwon & Kim, from a search snippet) is unconfirmed. **Deliberately excluded from
  `references.bib` and cited nowhere.** It is a record-level clinical cousin; if you can access
  the article and confirm metadata, it is a reasonable add to the Related-work clinical stream.

## 7. Optional related-work additions (verified in passing; not currently cited)

Surfaced during citation verification; each is a legitimate add if you want deeper coverage:

- **Alexandari, Kundaje & Shrikumar (ICML 2020)**, MLLS / bias-corrected calibration — companion
  to `garg2020unified` in the label-shift stream.
- **Farinhas et al., "Non-Exchangeable Conformal Risk Control" (arXiv 2310.01262)** — closest
  precedent for departing from record exchangeability; a natural comparison in the conformal stream.
- **"A hierarchical conformal framework … multi-hospital settings" (Sci. Rep. 2026,
  s41598-026-37450-w)** — multi-hospital conformal *coverage* (non-alarm class); a coverage-side
  contrast that sharpens the selective-risk delta.
- **Artelt et al., Neurocomputing 2023** ("I do not know! but why?", DOI 10.1016/j.neucom.2023.126722)
  — journal extension of `artelt2022reject`; swap in if you prefer the fuller version.

## 8. Content point left for your call

- **Covariate-shift ~400-cluster claim (Limitations).** The text says a covariate-shift mode
  "structurally prevents certification below roughly 400 clusters — the clip cap divides the
  certification margin under the information floor." That arithmetic is recorded in `README.md`
  (audit F34) but is **not** derived in SPEC.md or the manuscript. Decide whether to (a) reproduce
  the short derivation in an appendix / Methods so the claim is self-contained, or (b) keep the
  softened "structurally" hedge as-is. Currently hedged, no absolute "provably".

## 9. Process note — what ran this session

- **Ran:** citation verification (3 agents, 31 entries primary-source-verified; prior-art alarm
  negative), section drafting + intro judge-panel, Related-work + assembly, a line-by-line
  claims audit (ZERO discrepancies after round 2), and — after the third feedback round — the
  **three adversarial reviewer personas** (statistician on the guarantee chain, clinical-ML/XAI
  on venue fit, skeptical methods reviewer on the "glued-together" objection) plus a fresh
  claims-audit pass on the final text. Panel outcomes and any surviving points: §10 below.
- **Feedback round 2 applied:** single hedged novelty claim; no "intersection is empty";
  Related Work −37%; intro tightened; Methods §3.6 given breathing room; branding phrases
  thinned ("load-bearing" ×1, "honest" ×2 neutral, "false sense of safety" removed).
## 10. Adversarial panel outcomes (run on the final text) and open judgment calls

**Verdicts.** Statistician: "the guarantee chain holds under statistical attack" — every step of
the §3.4 validity argument re-derived independently; zero major findings. Skeptic (opening from
"conformal/DWR + RCPS glued together"): "I would NOT reject on those grounds — the
anti-conservativity counterexample and E4 dismantle that read"; names synthetic-only scope as
the paper's one genuine ceiling. Clinical-XAI: credible venue fit once the explainability
altitude and cohort-sourcing were fixed (both now applied). Claims auditor: **zero
discrepancies** (88 numbers, 31 citations, 14 math statements — including the new algebra).

**All confirmed findings were applied**, including: the design-conditional exactness clause in
validity step (ii); §3.1 aligned to the certified parameter $R_M$; the walk's per-mode betting
budget ($\delta$ vs $\delta_{bet}$); E1 tightness rhetoric softened to "consistent with";
abstract rebuilt at a consistent altitude (238 words, jargon glossed); "documented cohort"
softened to an indefinite distributional-profile claim; E6 retitled "coverage uniformity" with
an explicit scope sentence and the 4-site-bin caveat; the E1-vs-E4 0.9722/0.9715 coverage pair
explained (separate runs, independent seeds); ~350 further words of exact-duplicate prose cut.

**Left for you (judgment calls, not defects):**
- **Skeptic's counter-suggestion on novelty:** state the verified absence result as a fact —
  "To our knowledge no existing method certifies a finite-sample selective-risk budget with the
  cluster, rather than the record, as the unit of exchangeability." The skeptic argues this
  sharpens the delta without a priority boast; it conflicts with your stated aversion to
  "to our knowledge", so it was NOT applied. The 30+-query verified search supports it if you
  want it.
- **Cohort naming:** if you can name the documented multi-site cohort the generator was
  calibrated against, cite it in §4.1 and restore the stronger "mirrors" claim.
- **Title scope (clinical reviewer, minor):** the layer explains answers AND abstentions;
  "explainable abstention" slightly undersells. Only worth touching if you retitle anyway;
  the panel's net recommendation is to KEEP explainability in the title for venue fit.

- **Feedback round 3 applied:** "to our knowledge…first" → "we combine" (zero first-claims
  anywhere); explainability demoted from headline contribution to implementation feature
  (intro bullet removed; §3.8/§4.6 reframed); further ~350-word repetition cut (site-as-unit,
  concept-shift-out-of-scope, and parameter-vs-count restatements deduplicated; Discussion
  opening paragraphs merged); central theorem made explicit — the identity
  Z_c − α = g_c·a_c·(e_c − α)/M added in §3.3 and a four-step validity argument
  (boundedness / null equivalence / supermartingale / Ville) added in §3.4.
