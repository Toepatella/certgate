# CertGate manuscript — TODO (open items for the human author)

Draft: `paper/draft.md` · References: `paper/references.bib`
Status 2026-08-21: slim pass landed and `revision-2` merged to `main` — suite 267 passed / 3 skipped; paper trimmed in place to the Discover Computing bar (no venue page limit; abstract 248 words, structured; build 25 pp main + 18 pp SI); claim-trace guard green at 84 traced tokens. The dated status paragraphs below are historical records.
Status 2026-07-30 (truth-sync): `draft.md` resynced to the 2026-07-25 correctness audit
(CODE-AUDIT.md V1–V27) and the 2026-07-25 experiment rerun. Retired the per-target-site estimand
in favour of the site-population average with its mandatory dispersion clause (V1), the "q_t is
exact" premise (V2) and the "single asymptotic link" claim (V13); added the operative-rung
1−2δ clause (V27) and the four-parameter/16-corner BBSE box; replaced every experiment number
with the sep=2.2 rerun values. Sections touched: Abstract; §1 (¶4, ¶5, contributions 1/2/4);
§3.1, §3.2, §3.3, §3.4, §3.5, §3.6, §3.7, §3.9, §3.10; §4.1–§4.7; §5.1; §6 and §6.1; A.1, A.2,
A.3; Figures 1–6; Tables 1–4. Two notes for the human author — *[OBSOLETE 2026-08-10: both
resolved long since. The suite is 266 passed / 3 skipped as of 2026-08-10 (it was 136/1 when
this note was written); A.3 no longer states any absolute count (it says what the suite pins,
closing DS-28/R1-35/R2-41); CLAUDE.md's status line is current. Kept only as the historical
note it was.]* — (a) TODO §0 below still cites
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

*(Compressed 2026-08-10 under the single-source policy: the numbers this section used to
restate live in draft.md §3.1/§3.3/§4.9, Tables 5–7, and `experiments/out/`; the full closure
narrative is in the git history of this file.)*

**CLOSED this pass:** **S2-2** (the three deployment rules act at different levels and never
conflicted — §3.5/§3.6 now say so; answers `R1-59`); **S2-13** + **S2-25** (Table 5 constants
justification; §4.9/Table 6 M-sweep shows the frozen cap is not tuned — every larger M
certifies no more; also fixed `R5-26`, `R1-14`); **S2-28** (§3.1 clinical-target block, §4.1
outcome-and-time disclosure, Table 7 operating characteristics — the FN asymmetry and the
near-trivial-rule honesty are stated in the draft, not here). *PLAUSIBLE findings settled:*
`DS-45` (silent sites don't move R_M's value; §3.3 says what they do change), `R1-13` (minimum
certified coverage rules out the abstain-to-pass limb; §4.2 states it), `R2-27`
(record-carrying-but-silent case occurs zero times; §3.3/§4.7 say so). Half of **S2-1** closed
along the way (§3.6's "each at full δ" was false and is fixed).

**STILL OPEN:** the other half of **S2-1** (a stated error probability for the *deployed*
decision across modes and rungs); **S2-26** (no calibration diagnostic in the certified path —
the post-hoc panel is descriptive and §4.7 labels it so); S2-13's decline-thresholds sweep
(only M is swept; §6.1 says so).

**Reproducibility gap you should close.** Tables 6 and 7 come from a new read-only module,
`experiments/panel_s2_tables.py` (`python -m experiments.panel_s2_tables [R]`, ~2 min at
R=200, prints JSON, writes nothing to `experiments/out/`). It reseeds the same draws through
`run_synthetic`'s own rule and **hard-asserts** that its replay reproduces every
baseline-deploying draw's certified τ from the released `E1_validity.csv` (194/194, zero
mismatches) before emitting anything. But it is *not* wired into `run_synthetic.py`'s CSV and
summary writers, so `python -m experiments.run_synthetic` alone does not regenerate those two
tables — §3.10 and A.3 have been narrowed to say so honestly. Folding it into the driver (and
into `summary.md`) is the follow-up, and belongs with panel item **S2-24**.

## 0. Real clinical dataset — RESOLVED (the eICU section is written, 2026-08-01)

*(The original reviewer-priority item — "add at least one real clinical dataset" — is closed:
the extract ran 2026-07-31 and the manuscript carries it. Compressed 2026-08-10; the landing's
full enumeration is in this file's git history and in `draft.md` itself.)*

`draft.md` carries **§4.10**, Tables 8–9, Figure 8, the rewritten Abstract and §5.5 (retiring
the "real data cannot supply that ground truth" sentence four referees flagged —
`decision-letter.md` item 13), the new §6.1 limitations, and the eICU bibliography block
(verified — see the blockquote below). The parked real-data panel paragraph went in **VERBATIM**,
landing in **Appendix A.4** after the length pass; §4.10 paraphrases two of its numbers and
points to A.4 for the rest. The synthetic half was already done (§4.7 panel paragraph, Table 5
post-hoc sub-block, §6.1 ECE-bias sentence).

**A three-agent adversarial verification pass was run on the new material and found six BLOCKING
defects, all now fixed.** Recording them, because four were mine and the pattern is instructive:

1. **A fabricated ethics provenance.** The first Ethics rewrite asserted MIT IRB approval with a
   consent waiver for eICU-CRD. That is MIMIC's provenance, not eICU's — eICU rests on Safe
   Harbor de-identification certified by an independent privacy expert. A fabricated
   named-institution approval inside a submission declaration is exactly what a Springer
   integrity check verifies. Now states Safe Harbor certification and no IRB claim.
2. **A single-replicate count attached to a 20-replicate mean.** "coverage 0.890 over a pooled
   target pool of 15,169 records" — 15,169 is replicate 0's pool. Pool sizes range 13,667–27,021.
3. **A calibration-pool estimate reported as the target pool's.** The 0.0387 (95% 0.0356–0.0422)
   is the estimated tier's bootstrap over the 74 *calibration* hospitals. Replicate 0's *target*
   pool answered error is 0.0419. Both are now named for what they are.
4. **P2's comparison used a statistic the paper names differently elsewhere.** The eICU 0.027 was
   compared against the 0.02 the paper quotes in Figure 1 and §5.1 — but that 0.02 is E1's
   per-site *hard-violation* rate, a different statistic. Against the same statistic
   (`mean_per_site_exceed_frac` = 0.055) the comparison holds and is now stated that way.
5. **A pre-extract projection stated as measured fact.** The "500-stay threshold leaves roughly 46
   hospitals" is the protocol's pre-extract projection; the released extract leaves 99 of 207.
   Both are now given, and the conclusion (still under the 50-cluster floor) survives.
6. **P4 reported as a flat falsification when it is partial.** `aps_heartrate__missing` ranks
   third on re-splits 2 and 5 of 20. Since a *confirmed* P4 is the leak's signature, compressing a
   partial hit into a clean miss deletes exactly the observations a leak-hunting reader needs.

The same pass also caught that §4.10 **under-reported its own strongest result**: `aps_motor` is
the top abstention driver on **20 of 20** re-splits (fio2 top-3 on 13, `apv_oobintubday1` on 10).
That is the replication standard §4.6 set and met with a null; on real data it returns a stable,
clinically legible answer, and it now has its own paragraph ("What the abstentions point at")
connecting it to the explainability contribution — the collection's deciding axis.

> **VERIFIED 2026-08-10 (§6 policy) — the spot-check ran; see §6 for the full record.** All four
> entries checked against primary sources (PubMed/Crossref + the PhysioNet project page):
> `pollard2018eicu`, `goldberger2000physionet`, `zimmerman2006apache` field-perfect;
> `pollard2019eicudb`'s DOI 10.13026/C2WM1R **confirmed as the version-2.0-specific DOI** (the
> concept DOI is 10.13026/0pzc-dm64; v2.0 of 2019-04-15 is still the latest). The Ethics
> de-identification wording was re-checked against the project page and now names Privacert and
> HIPAA Certification no. 1031219-2. Two corrections came out of the check: PhysioNet's requested
> platform citation (`pollard2026physionet`, Nature Health 2026) was missing and is now cited, and
> the citation obligation was mis-attributed to the DUA — the agreement's ten clauses contain no
> citation term; it is a request on the project page. Draft and this file are reworded accordingly.

> **RESIDUAL JUDGEMENT CALL.** §4.10 is 1,768 words against 757 for the largest existing Results
> subsection. The verifier flagged the disproportion fairly — the section that can settle least
> occupies the most space. Material that structurally belonged elsewhere has been moved (the
> post-hoc panel to Appendix A.4, the compliance exposures to §6.1, the cohort-filter argument
> into Table 8's caption); what remains is content no other subsection carries. Cutting further
> means dropping disclosures. Left as is, flagged for the author.

The paragraph as parked is retained below for provenance — it is the text that was dropped in.

> On the pooled 24-hospital target arm (replicate 0, $\alpha = 0.10$, $\tau^* = 0.850$, coverage
> 0.854638; 15,169 records, 12,964 answered), the same panel returns an answered-set expected
> calibration error of 0.004757 (95% CI 0.002591–0.009664) against 0.022430 (0.009290–0.049626)
> on the declined set, a weak-calibration slope of 1.082649 (0.991115–1.233626) with intercept
> 0.305678, and an answered Brier score of 0.038438 (0.031158–0.044759). Against APACHE-IVa on
> the denominator-matched subset — the 10,404 answered records (share 0.80253, over 22 hospitals)
> that carry a reference probability — the reference scores 0.038079 (0.031912–0.043270) and the
> head 0.037104 (0.030803–0.042137), a paired difference of 0.000975 (0.000136–0.001684) in the
> head's favour, computed inside one shared resample rather than by differencing the two
> intervals. The skill margin on the answered set is 0.003934 (0.001796–0.005850) against a
> constant always-negative error rate of 0.045819, and the answered-minus-all contrast is
> $-0.006021$ ($-0.009365$ to $-0.003328$). This panel is post-hoc — added after the extract was
> read, outside the pre-extract freeze — and settles none of the pre-registered predictions. It
> is reported because the composition disclosure already established that the gate earns its low
> answered error partly by abstaining where deaths concentrate (answered oracle positive fraction
> 0.045819 against the pool's 0.089788); the skill margin is the number that says how much of
> what remains is accuracy rather than selection, and at 0.003934 on the answered set against
> 0.045351 on the declined set it is thin.

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

## 0c. Full-pipeline rerun verification (2026-08-10)

The complete real-extract pipeline was rerun end to end — preflight with the reference check ON,
then `--replicates 20` — into a scratch `out-verify/` (deleted after the check) on the same extract
(`data_sha 3744bf91…`). Result: **byte-identical to the committed `experiments/out/` up to
timestamp lines.** 11 of 14 artifacts byte-equal, including both PNGs, `EICU_diagnostics.json` and
`EICU_preflight.json`; the only diffs were `timestamp_utc` / `_run.utc` lines in `EICU-SUMMARY.md`,
`EICU_certificate.json` and `EICU_provenance.json`. The full test matrix ran the same day:
266 passed / 3 skipped on the default suite, and 267 passed / 2 skipped under each of
`CERTGATE_FIXTURE=1`, `CERTGATE_EICU=1`, `CERTGATE_EICU_LARGE=1`.

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
- ~~Code repository URL~~ — FILLED 2026-08-10 (https://github.com/Toepatella/certgate in Data
  availability); what remains is confirming the repo is PUBLIC before submission (§6a).
- **Acknowledgements** — optional; delete the placeholder if unused.

Note: the exemplar renders declarations as individual sections (Springer's XML pipeline splits
them regardless of submission format). Springer's manuscript *guidance* alternatively allows a
single "Statements and Declarations" umbrella with bold run-in subheadings — either is accepted;
the individual-section form here matches the accepted exemplar. Trivially reversible if the
submission system prefers the umbrella.

## 3. Journal formatting — decisions you must confirm on the live guidelines

**[RESOLVED 2026-08-10 — the live guidelines were fetched and both open items are settled.]**
Confirmed against https://link.springer.com/journal/10791/submission-guidelines and three
published Discover Computing articles: article type **Research**; submission via **Snapp**
(https://submission.nature.com/new-submission/10791/3) with a **cover letter required**
(`paper/cover-letter.md`); abstract **< 250 words** (structured accepted — the published
clinical exemplar 10.1007/s10791-026-10014-2 uses Background/Methods/Results/Conclusion, and
the draft's abstract is structured at 248 words by whitespace count, re-measured 2026-08-21 after the venue-bar trim); keywords are Snapp
metadata only (no published article renders them); **numbered square-bracket citations** with
an NLM/Vancouver list carrying **full DOI links** (LaTeX route: `sn-jnl.cls` +
`sn-vancouver-num.bst`, class option `sn-vancouver-num` — implemented in
`paper/make_submission.py`); figures/tables placed in the body at first reference (the build
script does this mechanically); Funding / Data availability / Ethics declarations mandatory —
a missing Funding statement gets the manuscript returned. Display math survives the pandoc →
sn-jnl pipeline (verified in the compiled PDF). The original notes are kept below for
provenance:

- **Reference / citation style (CSL) — RESOLVED (verify once).** The published collection
  exemplar (Discov Computing 29:344, 2026) uses **numbered, Vancouver/Springer-basic references
  with in-text `[n]`** — that is Discover Computing's de-facto style. Convert with a
  `springer-vancouver`-family CSL: `pandoc draft.md --citeproc --bibliography=references.bib
  --csl=springer-vancouver.csl -o …`; the `[@key]` citations render to `[1], [2], …`
  automatically. (Do not hand-format the bibliography; let CSL do it. Confirm against the live
  guidelines when you have login access, but the exemplar is strong evidence.)
- **Abstract length / structure.** Confirm the 250-word cap and that an unstructured abstract is
  accepted (current abstract is 249 words by whitespace count, re-measured 2026-08-10 after the
  replicate-0 scope label was added; unstructured).

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

*[Numbers refreshed 2026-08-10 against the released artifacts — several wishes below were
written before the R=200 rerun and carried stale values; the corrected values are in-line.
There are EIGHT figures now (E7 and eICU added), not six.]*

**[APPLIED 2026-08-10 — the S1-6 repair pass landed in `run_synthetic.py` and the grid was
re-run at R=200 with every CSV/JSON artifact byte-identical (plotting-only change).** E1/E2/E3
now use numeric category axes (a nan bar no longer eats its tick), in-axes "no certificates"
markers, and value-labeled bars so a true 0.0 reads as a labeled zero rather than an absence;
E2 carries an on-figure BBSE annotation computed from the run's own summary (never hardcoded)
plus a null-shift guide on the sweep panel; E3's title is shortened and renders in full; Fig 4
has the 208-site operating-point guide; Fig 6 gained the per-site-coverage panel. Fig 5's
single-draw annotation stays retired as decided below; Table 4 kept.]

The eight figures are mapped to captions in `draft.md` (and the figure → artifact table now
lives in `README.md` § Paper); regenerating the PNGs is a repo (code)
task and out of scope for the paper directory. Wishes flagged while writing the captions:

- **Fig 3 (E3):** the PNG title is truncated (`…certificate shou…`); regenerate with a shorter
  title or tighter layout so the full text shows.
- **Fig 2 (E2):** the BBSE bar sits at 0.0 and is nearly invisible; add an on-figure annotation
  (correct values: "BBSE at the anchor shift: declined 200/200, certify-and-violate 0/200; the
  9% certify rate belongs to the NULL-shift sweep point") so the decline story reads without
  the caption. *(The old suggested text "0/9 violations, certified 9/200, declined 95.5%"
  conflated the anchor run with the null-shift sweep point — do not use it.)*
- **Figs 1/2/3:** the α=0.05 "no certificates" marker is a faint rotated label in a large empty
  margin; make it a clear labeled bar.
- **Fig 5 (E5):** the single-draw feature-0 annotation idea is RETIRED — the R=200 replication
  returned the null (modal top-gap share 0.274 ≈ chance), and §4.6 reports the null as a null;
  annotating feature 0 as "the driver" would contradict the paper's own finding.
- **Fig 6 (E6):** only mean answered error is plotted; per-site coverage (0.980–0.990, Table 2)
  lives only in the table — consider a second panel/twin axis so "no coverage collapse" is
  visible in the figure.
- **Fig 4 (E4):** mark the 208-site operating point (e.g. a vertical guide) so the operative rung
  reads directly.
- Table 4 (E4 grid) is optional: every value is stated in-text, so drop it if length is tight.
- **In-text figure callouts:** DONE 2026-08-10 — every figure (1–8) is now called out at its
  discussion point in the body. What remains for typesetting is EMBEDDING the images in the
  submission package (revision-plan S1-6's other half).

## 5a. Confidence intervals — what was added, and the one gap needing a re-run

*[Counts refreshed 2026-08-10 — the figures below originally recorded the PRE-rerun counts
(2/200, 97/200, 166/200), which no longer match the released artifacts; an author trusting the
old paragraph would have re-inserted three wrong intervals. Current values:]*
Computed exactly from the recorded counts with Clopper–Pearson (scipy-verified, NOT estimated):
E1 per-site hard-violation 4/200 → the draft reports the rate 0.02 with the dispersion framing;
E2 baseline 79/200 → 95% CI [0.327, 0.466]; E2 BBSE joint 0/200 → [0, 0.018] (consistent with
the rule-of-three 0.015); E3 140/200 → [0.631, 0.763]. The draft already carries these exact
values (§4.2/§4.3/§4.4). A sentence in §4.1 states that all primary rates carry exact CIs.

**GAP (needs an experiment re-run — I cannot produce these from the recorded artifacts):** the
*mean-coverage* figures (E1 0.9828; E4's 0.9372/0.9818/0.9754/0.9641 and 0.7296/0.8516; E6 per-site
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

## 6. Unverified / excluded citations (do NOT cite until verified)

- **`scireports2026deferral`** — RESOLVED 2026-08-10: confirmed on BOTH Crossref
  (api.crossref.org/works/10.1038/s41598-026-40637-w) and the nature.com article page.
  Authors **Kwon, Hyun and Kim, Dae-Jin**; Sci. Rep. 16:10016, published 2026-02-20; the
  published title spells "cost aware" unhyphenated. Now in `references.bib` and cited in §2.4
  (neutrally — we verified metadata, not its methods, so the sentence makes no claim about its
  unit of exchangeability).
- **`pollard2019eicudb`** — VERIFIED 2026-08-10 against https://physionet.org/content/eicu-crd/2.0/.
  DOI 10.13026/C2WM1R is confirmed as the **version-2.0-specific** DOI (concept DOI:
  10.13026/0pzc-dm64, related via HasVersion per DataCite; v2.0, published 2019-04-15, is still
  the only and latest version). Entry updated to the page's requested form: "Celi, Leo Anthony",
  `month = apr`, RRID:SCR_007345, url. **Caveat kept on file: DataCite's record for C2WM1R is
  wrong** (year 2017, four creators) — never re-import this entry from DataCite; the project
  page's citation block is authoritative. Correction of record: the citation obligation is a
  request on the project page ("When using this resource, please cite"), **not** a DUA term —
  the agreement's ten clauses contain no citation/attribution language (checked at
  physionet.org/content/eicu-crd/view-dua/2.0/, unauthenticated). The page also requests the
  PhysioNet platform citation, so `pollard2026physionet` (Nature Health 1(8):792–795, 2026, DOI
  10.1038/s44360-026-00096-z, Crossref-verified) is now in the bib and cited at both eICU
  citation sites. The three siblings (`pollard2018eicu`, `goldberger2000physionet`,
  `zimmerman2006apache`) were re-verified field-by-field 2026-08-10 (PubMed + Crossref): all
  correct as written. Legacy flags resolved the same day: `l2lore2025` year corrected 2024→2025
  (CEUR Vol-3928 was published 2025 for the 2024 event); `angelopoulos2021ltt` (AOAS 19(2), 2025)
  and `ifac2025abstainexplain` (ECML PKDD 2024, pages 416–433 added) confirmed correct — the
  key/year vintage differences are labels, not errors.

## 6a. SUBMISSION BLOCKERS (facts only the authors can supply — added 2026-08-10)

**[Status 2026-08-10, submission-package session: every author blank is now a grep-able
`[[TBC:...]]` token (in `draft.md`, `LICENSE`, `CITATION.cff`, `paper/cover-letter.md`), each
carrying its ready-made "if none" wording inline. The build script
(`paper/make_submission.py`) prints the full token list as a warning banner on every build, so
nothing can ship silently incomplete. A `# Code availability` section now exists (SN code
policy wants a permanent DOI, not a bare GitHub link), which adds the Zenodo item below.]**

- [ ] Author name(s) + ORCID (`[[TBC:author-names]]`, `[[TBC:orcid]]`)
- [ ] Affiliation — department, institution, city, country (`[[TBC:affiliation]]`)
- [ ] Corresponding author name + email (`[[TBC:corresponding-*]]`)
- [ ] **Funding** statement (mandatory even if "none" — default wording is inline in the token)
- [ ] **Author contributions** (mandatory at Discover Computing — CRediT example inline)
- [ ] **Competing interests** (mandatory even if "none" — default wording inline)
- [ ] Acknowledgements (optional — delete the section if unused)
- [ ] Author name into `LICENSE` (MIT) and `CITATION.cff`
- [ ] **Mint the Zenodo DOI**: link GitHub → Zenodo, create a `v1.0.0` release at the
      submission-candidate tag, paste the DOI into `# Code availability` and `CITATION.cff`
- [ ] Confirm https://github.com/Toepatella/certgate is PUBLIC before submission — the Data
      availability section now names it, and DUA clause 9 requires contributing the code to an
      open repository when results are disseminated. (Do this AFTER the LICENSE name is filled.)

## 7. Optional related-work additions — APPLIED 2026-08-10

All four were re-verified against primary sources (PMLR page, arXiv/ICLR, Crossref + publisher
pages) and are now cited:

- **`alexandari2020labelshift`** (ICML 2020, PMLR v119 pp. 222–232) — cited in §2.3 as the
  maximum-likelihood variant in the label-shift stream.
- **`farinhas2024nonexchangeable`** (published ICLR 2024, not just the arXiv) — cited in §2.2
  as the closest precedent for departing from record exchangeability (in-expectation risk).
- **`shahbazi2026hierarchical`** (Sci. Rep. 16:6564, DOI 10.1038/s41598-026-37450-w) — cited in
  §2.2 as multi-hospital hierarchical conformal *coverage*.
- **`artelt2023rejectjournal`** (Neurocomputing 558:126722) — swapped in for `artelt2022reject`
  everywhere (the journal version supersedes the ESANN paper; old entry removed, all-cited /
  no-dangling preserved).

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
explained (separate runs, independent seeds) *[those were the pre-rerun values; the R=200 rerun
moved the pair to 0.9828/0.9818, which the draft now states — same explanation, new numbers]*;
~350 further words of exact-duplicate prose cut.

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
