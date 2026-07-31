# EICU-PROTOCOL — frozen real-data protocol (eICU-CRD v2.0)

Companion to `SPEC.md` § *Real-data protocol (eICU-CRD v2.0)*, which is the binding engineering
contract for `experiments/eicu_mock.py`, `experiments/eicu_etl.py`, `experiments/run_eicu.py` and
`tests/test_eicu_path.py`. This document is the scientific half: the cohort, the label, the feature
allowlist, the split, the predictions, and the ways the result is allowed to come out negative.

---

## 0. Status, freeze date, and what the pre-registration claim is worth

**Frozen 2026-07-30, before any eICU record was observed.** At the time of writing no member of the
project held the extract. Everything below — the inclusion predicates, the 161-column feature
allowlist, the 36-entry leak denylist, the split arithmetic, the seven numbered predictions, the
five failure criteria — was written from public documentation only: the MIT-LCP DDL
(`eicu-code/build-db/postgres/postgres_create_tables.sql`), the eICU-CRD data-descriptor paper, the
published column documentation, and MIT-LCP's own cohort SQL. No number in this document was
measured by us.

**Headline claim this protocol is designed to test.** If the certificate behaves on real multi-site
data roughly as it does on the synthetic grid, then at 208 hospitals the α = 0.10 rung should
certify with its aggregate exceedance rate inside δ = 0.05, while α = 0.05 should remain out of
reach. Everything else here is either a condition that makes that test interpretable, or a way for
it to come out negative.

**What "frozen" means, and what it does not.** It means this file and the constant pins in
`experiments/eicu_etl.py` + `tests/test_constants.py` are committed, with their own dated commit,
before the extract is downloaded, and the paper reports that commit hash. It does **not** mean
registration with a third party. The ordering claim rests on the commit history of a repository the
authors control, which is weaker evidence than an external registry timestamp, and it should be read
that way. The mitigation available to us is mechanical rather than institutional: the values are
pinned literally by a unit test (audit F13), so a post-hoc edit to a protocol constant turns CI red
and appears in the diff.

> **OPEN, AS OF 2026-07-31: THE REPOSITORY DOES NOT YET EXIST.** `git rev-parse
> --is-inside-work-tree` returns *"fatal: not a git repository"* in the project directory. So at
> the time of writing: `.gitignore` is inert (nothing is tracked and nothing is ignored, which also
> makes SPEC's "the data directory is gitignored" and `.gitignore`'s "`experiments/out/` is
> intentionally tracked" both untrue); §14.1's steps 0 and 10 error; and **the ordering claim above
> has no timestamp of any kind.** Until step 0 of the operator checklist is run — `git init`, then
> a dated commit of this file plus the pins, *before* the download — the honest statement in the
> paper is "written before the extract was obtained, with no external or version-control
> timestamp", which is materially weaker than what this section otherwise claims. The in-process
> DUA gate is unaffected and was verified independently: `run_eicu.assert_aggregate_only` refuses
> forbidden keys and any sequence over 512 elements, and `eicu_etl._bump` caps every value-count
> dict at 200 entries upstream of it.

**Amendments.** Any change to sections 2–13 after 2026-07-30 must be recorded here, in the log
below, with a date, the exact before/after, and a reason — not silently applied. An amendment made
*after* the extract has been read is a post-hoc decision and must be labelled as one wherever the
affected number is reported. The one class of change that is expected and legitimate is a
categorical level tuple that turns out to be wrong (§5.4, T-7): the drift gate exists to force that
correction into a visible SPEC + constants diff rather than absorb it.

| # | date | section | change | reason | data seen at time of change? |
|---|---|---|---|---|---|
| A1 | 2026-07-31 | §5.5, §12.2, §9 (P4), §10 (F-D), §11 | APACHE missingness reclassified from purely site-informative to jointly site- AND **outcome**-informative. Added: `n_positive`/`prevalence` on every attrition step; `outcome_stratified_missingness` and `apache_absent_los` to preflight; the `outcome-informative-missingness` abort at `EICU_MAX_OUTCOME_PREVALENCE_RATIO = 2.0`; the declared `apache-linked` arm; F-D rewritten into three legs, two of which depend on neither α nor coverage. | Three adversarial verifiers demonstrated in-harness that outcome-correlated APACHE-row absence converts a decline into a certificate while every declared defense stays silent, and that P4 being satisfied is the leak's signature. | **NO** — planted into the mock corpus; no eICU byte read |
| A2 | 2026-07-31 | §5.3 | `fio2` windows applied lower-CLOSED, so room air (0.21 / 21) is kept. Temperature windows unchanged (lower-open). | Room air is the modal value of a ventilation-linked column and ventilation status is site-correlated; discarding it manufactured the very informative-missingness channel this protocol guards. | **NO** |
| A3 | 2026-07-31 | §5.4a (new) | The nine `apachePredVar` treatment/intervention flags whose measurement timing cannot be cited are NAMED, and `outcome_screen` settles them from data before any certificate. | The denylist applied a "timing unverified" standard to two `apachePatientResult` columns and none at all to `activetx` and eight siblings. | **NO** |
| A4 | 2026-07-31 | §14.1 | Reference-identity counts taken at S0; typed read-boundary errors; `unrecognised-null-token`; `duplicate-stay-id`; preflight no longer raises on an unknown outcome level; decidable `header_case_as_read`; operator checklist corrected (git precondition, no absolute test count, decline expectation scoped to the frozen corpus sizes). | Ingest-boundary defects, each demonstrated. The reference-count one would have aborted the mandatory first command on the CORRECT extract. | **NO** |
| A5 | 2026-07-31 | §12.5 (T-26, T-27) | An absent or UNLINKED APACHE block now aborts: `unparseable-join-key` when a child table's `patientunitstayid` tokens fail integer parse past `EICU_MAX_UNPARSEABLE_SHARE`, and `apache-coverage-collapse` when a cohort of ≥ `EICU_MIN_OUTCOME_STRATUM` stays has a presence stratum below that floor. The `unrecognised-null-token` gate widened to the three `patient` numerics. No new constant; both legs reuse frozen thresholds. | Arrival-day audit (2026-07-31, three verifiers): a float-formatted join key (`141258.0`), a header-only child table, and a row-count-preserving key shift each CERTIFIED with 89/161 constant columns, zero warnings, and E-9's `gate_applies=false` — total absence bypassed the leak gate partial absence trips. Separately, Postgres `\N` in `patient.admissionweight` zeroed the column silently, and in `hospitaladmitoffset` silently changed first-stay selection with no ledger trace. | **NO** — demonstrated on mock corpora; no eICU byte read |

| A6 | 2026-07-31 | §5.3, §12.5 (T-2) | `unexpected-negative-sentinel` now aborts only when a column's negative-not-`-1` mass exceeds the already-frozen `EICU_MAX_UNPARSEABLE_SHARE = 0.01`; below it the cells become missing (which `_parse_apache_cell` already did) and a `[MEASURE]` warning names column, count and share. No new constant. | The released extract carries **exactly one** such cell in 4.1M: `apacheApsVar.urine = -11245.5648` at `patientunitstayid = 1805017` (in cohort), against a support that is otherwise contiguous and non-negative (min 0, median 1447.6, max 269323.7, 1824 zeros, n = 84,062 observed). §5.3 pre-specified that the "value < 0 ⇒ missing" rule is adopted **only after the histogram proves the support is contiguous and non-negative**; that histogram was run and it does. The abort was a look-at-this gate, not a correctness gate: the value maps to NaN either way, so no study number changes. | **YES** — first post-hoc amendment; the extract had been read. Every number affected by it must carry the post-hoc label. |

A6 is the **only** post-hoc amendment and the only one that RELAXES a refusal; it is bounded by a
pre-existing frozen constant, changes no computed value, and its triggering evidence (the urine
histogram) is recorded above. Every A1–A5 change is a **tightening**: each adds a measurement or a refusal, and none relaxes
a threshold, widens a vocabulary, or admits a column. All were made before the extract was
downloaded, and all are pinned by `tests/test_constants.py`.

**Order of operations (binding).** `SPEC.md` § *Real-data protocol* lands first →
`certgate/constants.py` stays untouched (no eICU constant enters the core package; the eICU path is
an experiment and follows the `run_synthetic.py` precedent) → `tests/test_constants.py` gains the
eICU pin block → then code. `EICU-PROTOCOL.md` is committed before the extract is opened.

---

## 1. Data source, version, access conditions, redistribution

- **Dataset:** eICU Collaborative Research Database, **v2.0**, PhysioNet. Approximately 200,859 unit
  stays / 139,367 patients / 208 hospitals / 335 units; discharges 2014–2015; ICU stays from
  hospitals participating in the Philips eICU programme.
- **Distribution:** a zip of gzipped CSVs, one per table, plus `LICENSE.txt` and `SHA256SUMS.txt`.
- **Tables read (five, ~35 MB gzipped):** `patient`, `hospital`, `apacheApsVar`, `apachePredVar`,
  `apachePatientResult`. The multi-GB time-series tables (`vitalPeriodic`, `nurseCharting`, `lab`,
  `intakeOutput`, …) are **out of scope for v1** and are never opened; §13 records this as a
  deviation from most published eICU mortality benchmarks.
- **Access conditions:** credentialed PhysioNet access, completed CITI human-subjects training, and a
  signed Data Use Agreement (PhysioNet Credentialed Health Data License 1.5.0 + DUA 1.5.0).
- **Redistribution prohibition:** the data may not be committed to this repository, shared, or
  redistributed. Derived **record-level** artifacts are restricted by the same DUA. §15 is the
  operative compliance section; `run_eicu.assert_aggregate_only` is its enforcement.

Row counts and site/patient counts are pre-registered as `EICU_REFERENCE_ROW_COUNTS` /
`EICU_REFERENCE_SITES` / `EICU_REFERENCE_PATIENTS` and checked by the preflight
(`expect_reference=True`). They are documentation-derived expectations, not measurements. A mismatch
is a stop condition (F-C), and the correct response is to establish *which* dataset is in hand — not
to relax the constant.

---

## 2. Cohort definition

### 2.1 Executable inclusion / exclusion predicates

Applied in this order to rows of `patient`. Each step is a named entry in the attrition ledger
(§11) recording **both** `n_stays` and `n_sites`.

| step | predicate | disposition of failures |
|---|---|---|
| **S0** `raw-unit-stays` | every row of `patient.csv.gz` | — |
| **S1** `site-parseable` | `int(row['hospitalid'].strip())` succeeds | drop, counted `hospitalid-unparseable` |
| **S2** `outcome-known` | `row['hospitaldischargestatus'].strip() in {'Alive','Expired'}` | `''` drops, counted `outcome-missing`; **any other non-empty value raises** `EicuError(... reason=unknown-outcome-level)` |
| **S3** `adult` | `parse_age(row['age']) is not None and >= EICU_MIN_AGE (18)` | drop, counted `age-unparseable` |
| **S4** `first-stay` | one stay per `patienthealthsystemstayid`: `argmin unitvisitnumber`, tie-broken by `argmax hospitaladmitoffset`, final tie-break `argmin patientunitstayid` | later stays dropped |
| **S5** `primary-cohort` | identity — the ledger closes here | — |

`parse_age`: `''` → `None` (drop); `'> 89'` → `90.0` (**kept**, `age_masked = 1`); otherwise
`float(int(t))`, and a parse failure drops and is counted.

**S4 sign note.** `hospitaladmitoffset` is minutes relative to hospital admission and is
**negative**, so the *earliest* unit stay carries the *highest* (least negative) offset. A tie-break
on `argmin` here would select the latest stay. The third tie-break on `patientunitstayid` exists only
for determinism.

**S2 raises rather than drops on an unrecognised outcome level.** A third value would mean either a
different dataset version or a parse fault; either way the label semantics are no longer the ones
this protocol registered, and continuing would produce numbers about an unknown quantity.

Three filters that appear in most published eICU cohorts are **deliberately absent**. Each omission
is argued below rather than asserted, because each of them would improve the headline numbers.

### 2.2 Why no length-of-stay floor

The most-cited eICU mortality benchmark restricts to stays of ≥ 48 h (variants use ≥ 24 h). We do
not, for three reasons that compound:

1. **Immortal time.** Conditioning on survival-to-horizon removes exactly the patients who die
   fastest — the ones a mortality gate most needs to get right — and does so differentially by
   severity.
2. **It uses post-outcome information in cohort construction.** The criterion is computed from
   `unitdischargeoffset` / `hospitaldischargeoffset`, both on the leak denylist (§6). Excluding a
   column from the *features* does not neutralise its use in *selection*; only omitting the filter
   does. This is a distinct class of leak from the feature denylist and is named separately in §6.
3. **The amount of conditioning differs by hospital.** ICU discharge practice varies across sites, so
   an LOS floor is a site-correlated exclusion, and site-correlated exclusions move the population
   the certificate's estimand refers to (§12.1).

Cost of the omission: the cohort contains short stays for which day-1 APACHE physiology may be thin,
which will show up as higher `__missing` rates and is measured, not assumed.

### 2.3 Why no minimum-stays-per-hospital filter

A Johnson-style `≥ 500 stays` hospital filter leaves roughly 46 hospitals. Under the split of §7 that
is about 18 calibration clusters, against `MIN_CAL_CLUSTERS = 50` (audit B-5) — `run_certgate` would
return `insufficient-clusters` and no certificate could exist. The filter is not a modelling
preference here; it is a direct threat to feasibility. Small hospitals stay in, and the heavy-tailed
size distribution is handled where it belongs: by the influence cap `M_INFLUENCE = 100` on the atoms
(METHODS §3), not by deleting sites.

### 2.4 Why no APACHE-availability filter in the primary arm

The data descriptor reports that **8.65% of the 208 hospitals (≈ 18) contribute zero
`apachePatientResult` rows**, while 0.00% lack `apacheApsVar` / `apachePredVar`. Restricting the
cohort to APACHE-covered stays would therefore delete whole hospitals and thin many more. Under the
site-as-unit design the certificate's estimand is an average over the *site population* from which
calibration was drawn (audit V1); deleting sites changes that population, and therefore changes the
claim, without changing a word of the guarantee text. The primary arm does not restrict. Coverage is
measured as attrition (§11) and reported.

### 2.5 The two declared sensitivity arms

`EICU_ARMS = ("primary", "apache-linked", "apache-complete")`.

**`apache-linked`** (added 2026-07-31, amendment A1) adds to S5: `aps_present and apv_present`.
It restricts to stays whose **day-1 APACHE window is complete**, which makes the two presence flags
constant and information-free. Its purpose is to pay the immortal-time cost of that restriction
**explicitly** rather than take the outcome-informative-absence leak silently (§5.5): conditioning
on the day-1 window closing conditions on survival to that horizon, exactly the objection §2.2
raises against a `>= 24h` LOS floor, and the amount of conditioning differs by hospital. It is
therefore never a headline, it is mandatory whenever the §5.5 gate fires, and its `n_sites` and
prevalence are printed beside the primary arm's wherever it appears.

**`apache-complete`** adds to S5:
`aps_present and apv_present and comparator_predicted_mortality is finite`. It exists to *quantify*
the site-selection effect against the primary arm, never as a headline. Wherever it appears its own
`n_sites` and site population must be printed beside the primary arm's, and any guarantee sentence
derived from it names the APACHE-contributing hospital population explicitly (§12.1).

---

## 3. Label

- **Source column:** `patient.hospitaldischargestatus` (`VARCHAR(10)`), i.e. **in-hospital
  mortality**.
- **Positive value:** `"Expired"` (`EICU_POSITIVE_LABEL`); negative `"Alive"`.
- The ETL emits `y_raw` as a **list of raw two-valued strings**. It never builds a bool array by
  hand; `coerce_labels` / `from_raw` own the two-value contract (SPEC `validate.py`, audit
  F05/F35/F37). Because S2 has already dropped `''` and raised on any third level, exactly two
  distinct values are observed on every fitting cohort.
- **Missing outcomes are dropped, never imputed and never coerced.** MIT-LCP's own
  `icustay_detail.sql` maps the blank to `NULL`; the documented blank share is ~0.87%
  (1,751 / 200,859). Those stays carry no usable outcome and any imputation would be a fabricated
  label at the exact rate that differs across hospitals.
- `require_both_classes=False` is used for **target pools only** — a single held-out hospital may
  legitimately be all-`Alive` at ~9% prevalence, and `from_raw`'s opt-in admits that case when
  exactly one distinct value is observed (SPEC `validate.py`). Fitting cohorts keep the strict
  default.
- ICU mortality (`patient.unitdischargestatus`) is **not** the label and is on the leak denylist.

---

## 4. Site key: `hospitalid`, and why the hospital is the unit

**Site = `patient.hospitalid`** (208 distinct values), emitted as one canonical spelling per
hospital: `EICU_SITE_PREFIX + str(int(hospitalid))` → `"hosp-420"`. Parsing through `int()` before
formatting guarantees a single spelling, so `densify_sites`' near-duplicate collision raise
(`'420'` vs `'0420'` vs `'420.0'`; audit V4/V10) cannot fire on our own output — the check stays
live for genuinely dirty input.

**Not the record.** Records inside one hospital share a documentation interface, a care protocol, a
case mix, a coding convention, and the staff producing all four. The data descriptor states directly
that reliability and completion of data elements vary at the hospital and ICU level. Treating
records as independent is the anti-conservatism experiment E7 measures in-harness rather than cites:
the record-unit certifier grants α = 0.05 in 99–100% of the draws the site-unit walk refuses in
100%, then exceeds its aggregate budget in 3.5%–9.6% of them depending on between-site heterogeneity.
That is the design decision this protocol carries onto real data.

**Not the ward.** `wardid` has 335 values, several per hospital. Splitting on it would over-count
clusters *within* a hospital and reintroduce the same dependence one level down, buying apparent
statistical strength that does not exist.

`hospitalid` and `wardid` are both on the feature denylist. A head that can read the site off the
feature vector can memorise site-specific mortality and destroy the between-site generalisation the
certificate rests on.

---

## 5. Feature allowlist — deny by default

Width **`EICU_N_FEATURES = 161`**, pinned literally. `FEATURE_NAMES` is built by concatenating the
same tuples used to construct the one-hot blocks, so names and columns cannot drift apart; `build_raw`
ends with `assert x.shape == (n, len(FEATURE_NAMES))` and `len(FEATURE_NAMES) == EICU_N_FEATURES`.

Missing / out-of-window / sentinel values become `NaN` in `build_raw`, are mean-imputed from
**S_train rows only** (§5.6), and every imputable column carries an immediately adjacent
`<name>__missing` 0/1 float64 sibling.

The five blocks below are the allowlist itself, and they sum to 8 + 1 + 64 + 48 + 38 + 2 = 161.
§§5.1–5.6 then argue the individual policies the blocks invoke, and §§5.7–5.8 record two tables that
contribute nothing and why.

**Block 1 — `patient` numerics (4 columns → 8 features, plus 1 indicator).**

| source column | transformation | feature name(s) |
|---|---|---|
| `patient.age` | `''` → NaN; `'> 89'` → `90.0`; else `float(int(t))`. Cohort already requires ≥ 18. | `age`, `age__missing` |
| `patient.age` | `1.0` iff the token was exactly `EICU_AGE_MASK_TOKEN = "> 89"`, else `0.0` | `age_masked` (no `__missing` sibling — it is an indicator and is never NaN) |
| `patient.admissionheight` | `''` / `0` / outside `EICU_WINDOW_HEIGHT_CM = (100.0, 250.0)` → NaN, counted | `admissionheight`, `admissionheight__missing` |
| `patient.admissionweight` | `''` / `0` / outside `EICU_WINDOW_WEIGHT_KG = (20.0, 300.0)` → NaN, counted | `admissionweight`, `admissionweight__missing` |
| `patient.hospitaladmitoffset` | `-offset / 60.0`; outside `EICU_WINDOW_PRE_ICU_HRS = (0.0, 720.0)` → NaN, counted | `pre_icu_hours`, `pre_icu_hours__missing` |

The height/weight windows exist because decimal-point entry errors are documented in this dataset
(544 kg, 612 cm) and `0` — not `-1` — is the missing encoding for these two columns. An outlier of
that size survives standardization and distorts a linear head (T-11).

**Block 2 — `patient` categorical one-hots (64 columns).**

Levels are frozen tuples; each renders as `<column>=<level>`, with the empty-string level rendering
as `<column>=EMPTY`:

```python
EICU_LEVELS_GENDER      = ("Female","Male","Other","Unknown","","OTHER")                       #  6
EICU_LEVELS_ETHNICITY   = ("African American","Asian","Caucasian","Hispanic",
                           "Native American","Other/Unknown","","OTHER")                        #  8
EICU_LEVELS_ADMITSOURCE = ("Acute Care/Floor","Chest Pain Center","Direct Admit",
                           "Emergency Department","Floor","ICU","ICU to SDU","Observation",
                           "Operating Room","Other","Other Hospital","Other ICU","PACU",
                           "Recovery Room","Step-Down Unit (SDU)","","OTHER")                   # 17
EICU_LEVELS_UNITTYPE    = ("CCU-CTICU","CSICU","CTICU","Cardiac ICU","MICU","Med-Surg ICU",
                           "Neuro ICU","SICU","","OTHER")                                       # 10
EICU_LEVELS_UNITSTAYTYPE= ("admit","readmit","stepdown/other","transfer","","OTHER")            #  6
```

Applied to `gender` (6), `ethnicity` (8), `hospitaladmitsource` (17), `unitadmitsource` (17, same
tuple), `unittype` (10), `unitstaytype` (6) = **64**. The blank string is a *listed* level, not
drift. The terminal bucket is spelled `OTHER` in caps to distinguish it from eICU's own `Other` and
`Other/Unknown` levels, which are listed.

Two `patient` columns are excluded and neither is a leak:

- `unitvisitnumber` — after S4 it is ≈ 1 for nearly every row. A near-constant column trips
  `model.SD_REL_TOL`'s guarded standardization, yields a coefficient of exactly 0.0, and produces an
  identically zero attribution that reads as "this feature does not matter" when it actually means
  "this column has no variance" (T-14). Reported as a preflight histogram instead.
- `apacheadmissiondx` — high-cardinality pipe-delimited free text. Its level list cannot be
  pre-registered without seeing the data, which is precisely the thing this document forbids.

**Block 3 — `apacheApsVar` day-1 physiology (24 columns → 48 features).**

```python
EICU_APS_NUMERIC = ("intubated","vent","dialysis","eyes","motor","verbal","meds","urine","wbc",
                    "temperature","respiratoryrate","sodium","heartrate","meanbp","ph",
                    "hematocrit","creatinine","albumin","pao2","pco2","bun","glucose",
                    "bilirubin","fio2")
```

Feature names `aps_<col>` and `aps_<col>__missing`. Transformation: the dual sentinel policy of §5.2
plus the unit normalisations of §5.3.

The ordinal/binary columns (`intubated`, `vent`, `dialysis`, `eyes` 1–4, `motor` 1–6, `verbal` 1–5,
`meds`) enter as plain numerics with a missing sibling. The preflight separately tabulates their
exact observed value sets and warns on anything outside `{documented range} ∪ {-1} ∪ {0}`.

**Block 4 — `apachePredVar` day-1 comorbidity and treatment flags (19 columns → 38 features).**

```python
EICU_APV_NUMERIC = ("graftcount","thrombolytics","aids","hepaticfailure","lymphoma",
                    "metastaticcancer","leukemia","immunosuppression","cirrhosis",
                    "electivesurgery","activetx","readmit","ima","midur","ventday1",
                    "oobventday1","oobintubday1","diabetes","ejectfx")
```

Feature names `apv_<col>` and `apv_<col>__missing`.

Excluded from `apachePredVar`, in three groups (the reasons are carried in the denylist test):

- **Documented constants** — `sicuday`, `saps3day1`, `saps3today`, `saps3yesterday`, `teachtype`,
  `region`, `bedcount`, `managementsystem`, `var03hspxlos`. The column documentation marks these
  "set to default value" / "Not used" / literally `XXX`. They are zero-variance, and `region`,
  `teachtype`, `bedcount` are **not** the hospital's real metadata (that lives in `hospital`, which
  contributes no features either — §5.7).
- **Duplicates of a quantity already sourced elsewhere** — `gender`, `age`, `verbal`, `motor`,
  `eyes`, `meds`, `day1*`, `creatinine`, `pao2`, `fio2`. One source per quantity.
- **Coded duplicates or sparse** — `admitsource`, `visitnumber`, `amilocation`.

`diedinhospital`, `dischargelocation`, `saps3today`, `saps3yesterday`, `var03hspxlos` are
additionally leaks (§6).

**Block 5 — the two APACHE presence flags (2 columns).** `aps_present`, `apv_present`; argued in
§5.5.

### 5.1 The `'> 89'` policy — kept, not dropped

`patient.age` is `VARCHAR(10)` and ages over 89 are HIPAA-masked as the literal string `'> 89'`
(documented at roughly 7,081 stays). Most published cohort code maps it to 90 and then drops it with
a `max_age = 89` filter. We keep it, mapped to `EICU_AGE_MASK_VALUE = 90.0`, with an explicit
`age_masked` indicator.

The reason is the same one that governs §2.2 and §2.4: the masked stratum is mortality-enriched, and
its *share varies by hospital* with case mix, so dropping it is a site-correlated exclusion. Keeping
it with a flag makes the age ceiling visible to the head and to the attributions instead of encoding
it as a silent 90-year-old cohort. A naive `int(age)` raises on both `'> 89'` and the blank, which is
why `parse_age` is a named predicate in §2.1 rather than an inline cast.

### 5.2 The `-1` / `''` dual sentinel policy

For **every** allowlisted `apacheApsVar` and `apachePredVar` column:

```
raw == ''                 -> NaN, counted            # the documented SQL NULL (MIT-LCP loads NULL '')
float(raw) == -1.0        -> NaN, counted            # the UNDOCUMENTED sentinel
float(raw) <  0.0         -> NaN, counted 'other-negative' AND appended to meta['warnings']
float(raw) unparseable    -> NaN, counted 'unparseable'
```

Both channels must be handled. The column documentation says these fields are "set to NULL when not
present"; the released CSVs use `-1` anyway, and this is reported in the eICU literature rather than
in the schema. Handling only the empty string leaves a finite `-1` in the matrix — plausible,
non-`NaN`, and invisible to every validity check `make_cohort` performs (T-2).

Every allowlisted column has non-negative physiological support, so a negative value that is not
exactly `-1.0` is an unrecognised sentinel. `build_raw` raises
`EicuError(... reason=unexpected-negative-sentinel)` rather than mapping it to missing. The general
rule "negative ⇒ missing" is adopted only *after* the preflight histogram shows the support is
contiguous and non-negative — not before.

### 5.3 `fio2` and `temperature` unit normalisation

Applied **before** the window test, each counted in `meta["unit_conversions"]`:

```
fio2        : v in EICU_WINDOW_FIO2_FRAC [0.21, 1.0]   -> v                 # fraction convention
              v in EICU_WINDOW_FIO2_PCT  [21.0, 100.0] -> v / 100.0         # percent convention
              else                                     -> NaN
temperature : v in EICU_WINDOW_TEMP_C (25.0, 45.0)     -> v
              v in EICU_WINDOW_TEMP_F (77.0, 113.0)    -> (v - 32) * 5/9    # Fahrenheit
              else                                     -> NaN
```

The windows do not overlap, so the mapping is unambiguous — and the fraction branch is tested
first, so `21.0` is unambiguous too. Both conventions are finite and plausible numbers, so nothing
downstream would flag the contamination (T-10).

**The `fio2` windows are lower-CLOSED (amendment A2).** They were lower-open, which discarded
`fio2 == 0.21` (equivalently `21`) — **room air** — as missing, counted only in a
`unit_conversions` sub-key. Room air is a physiologically valid, modal observation on a
ventilation-linked column, and ventilation status is site-correlated: dropping it would convert the
commonest value of that column into exactly the informative-missingness channel §12.2 undertakes to
guard, and its magnitude on the real extract was unknown until the extract was read. Kept, counted
as `aps_fio2:room-air-fraction` / `:room-air-percent`, and pinned behaviourally in
`tests/test_constants.py`.

The **temperature** windows stay lower-open: unlike `fio2` there is no convention value at either
endpoint, only implausible physiology (exactly 25.0 °C or 45.0 °C). Mass falling outside *both*
temperature or fio2 windows is no longer silent either — `preflight` warns when it exceeds
`EICU_MAX_UNPARSEABLE_SHARE` of observed values, because a large residue means a third unit
convention and the fix is a SPEC diff, not a quiet loss.

### 5.4 Categorical level tuples and the 5% drift gate

Matching is on the **stripped, case-sensitive** raw value. A value not in the tuple maps to the
terminal `OTHER` level and is counted. If, for any column,
`other_count / n > EICU_MAX_OTHER_SHARE = 0.05`, then `build_raw(strict_levels=True)` raises
`EicuError(... reason=categorical-level-drift)`, naming the column, the share, the cap, and the top
unlisted values.

This is the loud boundary for the one part of the protocol that could not be verified before
freezing: a vocabulary frozen without seeing the data may simply be wrong. The gate turns that from
a silent absorption (the head learns a drift bucket that is really "this hospital spells gender
`F`") into a visible SPEC + constants diff, re-pinned in `test_constants.py` and recorded in the
amendment log of §0. `preflight` and `build_raw(strict_levels=False)` do not raise; they report the
unlisted-value table. This is why the preflight is mandatory before certification.

### 5.4a Nine allowlisted flags whose measurement timing is not verifiable from documentation

The denylist excludes `apachepatientresult.physicianspeciality` and
`physicianinterventioncategory` under the reason *"leak-suspect: assignment timing relative to
outcome unverified"*. That standard has to reach nine `apachePredVar` treatment/intervention flags
too, and it did not:

`activetx`, `thrombolytics`, `graftcount`, `electivesurgery`, `ventday1`, `oobventday1`,
`oobintubday1`, `ima`, `midur`.

`activetx` is the sharpest case: in APACHE IV it encodes active treatment versus comfort measures,
a decision made *during* the stay and adjacent to death by definition. None of the nine has a
timing citation in the DDL comments, and the DDL is not a trustworthy source here — the entire `-1`
sentinel policy (§5.2) exists because the column documentation says values are "set to NULL when
not present" and the released CSVs use `-1` anyway.

So the question is settled from the **data**, before any certificate exists.
`eicu_etl.outcome_screen(x_raw, meta)` reports, for every one of the 161 features, the outcome
prevalence by stratum (binary) or in the top versus bottom decile (continuous) plus a univariate
rank AUC; `run_eicu` writes it to `EICU_diagnostics.json` (`outcome_screen`, with
`timing_unverified_auc` keyed by the nine names) and raises a `[MEASURE]` warning for every feature
past the pre-registered band `EICU_FEATURE_AUC_REVIEW = 0.75`. A flagged column must be re-audited
for measurement timing before any number is reported; if the timing cannot be established, it moves
to the denylist under the same reason already used for the two `apachePatientResult` columns, as an
amendment under §0. On the clean mock every one of the nine measures between 0.45 and 0.57.

### 5.5 The two APACHE presence flags — jointly site- AND outcome-informative

`aps_present`, `apv_present` — `1.0` iff the stay carried a row in that table.

These are features, not hidden state. Whole-row APACHE absence is already fully representable
through the 43 `__missing` siblings, which all flip together; suppressing an explicit flag would not
remove the information, only smear it across 43 columns and make the attributions unreadable. Naming
it in one column also lets the abstention explanations say *"declined because this hospital
contributes no day-1 physiology"*. Registered as prediction **P4**.

**The correction (2026-07-31, amendment A1).** The paragraph above was the whole justification, and
it was only half the story. It treats absence as a **site** channel — threat T-3. Absence is also an
**outcome** channel, and that half is a leak:

> The APACHE day-1 variables are defined over the first 24 hours. A stay that ends *because the
> patient died* before that window closes has no `apacheApsVar` / `apachePredVar` row at all. So
> `aps_present` / `apv_present` and the 43 `__missing` siblings partly encode "this patient died
> early".

§2.2's own cost note already named the mechanism — *"the cohort contains short stays for which day-1
APACHE physiology may be thin, which will show up as higher `__missing` rates and is measured, not
assumed"* — and then classified it as a measurement artifact. Those stays are short **because the
patient died**. Classifying the mechanism correctly is the difference between a diagnostic and an
alarm.

**Why every declared defense was blind to it.** The 36-entry denylist matches column NAMES, and
absence has no column. The `-1` gate is about values. The drift gate is about categoricals. The
preflight printed APACHE coverage, which barely moves. And F-D required `α = 0.05` AND
`coverage > 0.90` AND `R_M < 0.01`, so a leak certifying `α = 0.10` at coverage 0.86 passed
underneath it. Worse, **P4 pre-registers the leak's signature as a confirmation**: on a leak-planted
corpus `EICU_diagnostics.json` returns exactly what P4 predicts — `aps_present` gap −1.21 at rank 1,
`apv_present` at rank 2.

**Measured, planting the mechanism into the mock and changing nothing else** (180 hospitals / 9000
stays; out-of-sample calibration-split AUC, and the same head with the 49 missingness/presence
columns ablated):

| corpus | aps coverage | prevalence ratio absent : present | head AUC | ablated AUC | drop |
|---|---|---|---|---|---|
| clean | 0.862 | 1.11 | 0.597 | 0.613 | −0.016 |
| p = 0.10 | 0.853 | 1.87 | 0.608 | 0.600 | +0.008 |
| p = 0.20 | 0.845 | 2.66 | 0.631 | 0.595 | +0.035 |
| p = 0.30 | 0.835 | 3.86 | 0.671 | 0.589 | +0.082 |
| p = 0.75 | 0.803 | 14.51 | 0.835 | 0.587 | +0.248 |

The p = 0.15 arm's coverage (0.850) is indistinguishable from the released extract's
171 177 / 200 859 = 0.852. **Coverage cannot be the screen.** End to end at 208 hospitals the clean
corpus declines every rung at coverage 0.00 and the p = 0.75 corpus certifies `α = 0.10` at
τ = 0.790, coverage 0.857 — and the old F-D reported `fired: false, n_hits: 0`.

**What replaces it — three gates at three sensitivities, all pre-registered.**

1. **Measured.** `preflight` emits `outcome_stratified_missingness` (per presence flag and per
   `__missing` sibling: outcome prevalence in each stratum and their ratio) and `apache_absent_los`
   (the LOS distribution of APACHE-absent versus APACHE-present stays — the measurement that
   *separates* the site channel from the outcome channel). Every `EICU_ATTRITION_STEPS` entry
   carries `n_positive` and `prevalence`, so the ledger itself shows the collapse.
2. **Aborted.** `build_raw(arm="primary")` raises `reason=outcome-informative-missingness` when
   either presence flag's absent : present prevalence ratio exceeds
   `EICU_MAX_OUTCOME_PREVALENCE_RATIO = 2.0` with both strata at least
   `EICU_MIN_OUTCOME_STRATUM = 100` stays. The message names the two remedies and explicitly
   refuses a widened cap.
3. **Alarmed at runtime.** F-D legs 1 and 2 (§10), computed every replicate on the real extract.

**The declared escape (§2.5): `--arm apache-linked`.** Restricting to stays whose day-1 window is
complete makes both flags constant and information-free. It is an immortal-time-selected cohort —
that is the price, it is *stated*, and its site count and prevalence are reported beside the primary
arm's. The position this protocol previously held was to take the leak in order to avoid the
immortal-time filter, without saying so. The arm makes the trade explicit and lets the reader see
both sides of it.

### 5.6 Imputation is fit on S_train only — the transductive leak

`impute(x_raw, fit_idx=idx['train'])`. Column means are computed on the S_train row indices and
applied to all four splits. Computing them on the pooled matrix would let the target pool's
covariate distribution into the training features — a transductive leak that no downstream gate
catches, because the resulting matrix is finite, correctly shaped, and site-disjoint. A column
entirely NaN within S_train falls back to `EICU_IMPUTE_FALLBACK = 0.0`, counted, and the
`{feature_name: value_used}` map is recorded in provenance (audit F49/V11).

### 5.7 `apachePatientResult` and `hospital` contribute no features

**`apachePatientResult`** is read for the APACHE-IVa comparator (`predictedhospitalmortality`) and
for the coverage ledger, nothing else — see §2.4 for the site-deletion argument. Two further points:
`acutephysiologyscore` and `apachescore` are *APACHE III* scores despite the table name, so
describing them as an "APACHE IV score" would be factually wrong; and `predictedhospitalmortality` is
`VARCHAR(50)`, a string holding a probability with `-1` for unavailable, so it is parsed with
`float()` **first** and compared afterwards (a string comparison such as `> '0'` accepts `'-1'`;
T-9).

**`hospital`** supplies `numbedscategory`, `teachingstatus`, `region` — all constant within a site.
They are not leaks, but under a site-as-unit design their coefficients would be identified purely
from between-site variation (~75 training sites, not ~60k records), so their effective sample size is
two orders of magnitude below what the record count suggests, and they are the cleanest available
site proxies. They are read as strata for the per-site diagnostic table and never enter `x`.

### 5.8 Deduplication

None of these tables declares `patientunitstayid` unique.

- `apacheApsVar`, `apachePredVar`: assert one row per stay; on violation keep `min(apacheapsvarid)` /
  `min(apachepredvarid)` and report the count in `meta["dedup_counts"]`.
- `apachePatientResult`: one row per `(stay, apacheversion)`, keeping `min(apachepatientresultsid)`
  within each. Version preference `EICU_APACHE_VERSION_PREFERENCE = ("IVa", "IV")` — `IVa` if
  present, else `IV` — recorded per stay as a diagnostic, never as a feature (its availability is
  site-correlated). The documented row counts do not close arithmetically
  (297,064 ≠ 2 × 171,177), so the rows-per-stay histogram is a preflight output rather than an
  assumption (T-8).

---

## 6. Leak denylist

`EICU_LEAK_DENYLIST` is a tuple of `(source_column, reason)` pairs. `assert_no_leak_columns` is a
**test**, not a comment: for every entry it asserts the column name is absent from `FEATURE_NAMES`
bare, under the `aps_` / `apv_` prefixes, with or without the `__missing` suffix, and as a `<col>=`
one-hot stem.

| # | column | reason |
|---|---|---|
| 1 | `apachepredvar.diedinhospital` | the outcome itself, as an integer |
| 2 | `apachepatientresult.actualhospitalmortality` | the outcome as a string |
| 3 | `apachepatientresult.actualicumortality` | ICU mortality outcome |
| 4 | `patient.hospitaldischargestatus` | the outcome (label column; never a feature) |
| 5 | `patient.unitdischargestatus` | ICU-death outcome (`'Expired'`) |
| 6 | `patient.hospitaldischargelocation` | values include `'Death'` |
| 7 | `patient.unitdischargelocation` | post-outcome disposition |
| 8 | `patient.hospitaldischargeoffset` | length of stay, post-hoc |
| 9 | `patient.unitdischargeoffset` | ICU length of stay, post-hoc |
| 10 | `patient.hospitaldischargetime24` | post-hoc timestamp |
| 11 | `patient.unitdischargetime24` | post-hoc timestamp |
| 12 | `patient.dischargeweight` | measured at discharge |
| 13 | `apachepatientresult.actualiculos` | post-hoc |
| 14 | `apachepatientresult.actualhospitallos` | post-hoc |
| 15 | `apachepatientresult.unabridgedunitlos` | post-hoc |
| 16 | `apachepatientresult.unabridgedhosplos` | post-hoc |
| 17 | `apachepatientresult.actualventdays` | post-hoc |
| 18 | `apachepatientresult.unabridgedactualventdays` | post-hoc |
| 19 | `apachepredvar.saps3today` | intra-stay update (and a documented constant) |
| 20 | `apachepredvar.saps3yesterday` | intra-stay update (and a documented constant) |
| 21 | `apachepredvar.var03hspxlos` | post-hoc LOS-derived ("Not used") |
| 22 | `apachepredvar.dischargelocation` | post-outcome disposition |
| 23 | `patient.hospitalid` | site identifier — memorisation, fatal to between-site generalisation |
| 24 | `patient.wardid` | unit identifier — same |
| 25 | `patient.hospitaldischargeyear` | temporal split variable, confounded with site enrolment |
| 26 | `apachepatientresult.predictedhospitalmortality` | the comparator being competed against |
| 27 | `apachepatientresult.predictedicumortality` | comparator |
| 28 | `apachepatientresult.predictediculos` | comparator |
| 29 | `apachepatientresult.predictedhospitallos` | comparator |
| 30 | `apachepatientresult.predventdays` | comparator |
| 31 | `apachepatientresult.apachescore` | APACHE-III composite of the same APS inputs; the table has 8.65% zero-coverage sites |
| 32 | `apachepatientresult.acutephysiologyscore` | same |
| 33 | `apachepatientresult.physicianspeciality` | leak-suspect: assignment timing relative to outcome unverified |
| 34 | `apachepatientresult.physicianinterventioncategory` | leak-suspect: same |
| 35 | `patient.apacheadmissiondx` | **not a leak** — excluded as un-pre-registrable high-cardinality free text |
| 36 | `patient.unitvisitnumber` | **not a leak** — excluded as near-constant after the first-stay rule |

**A class the denylist cannot fix.** `unitdischargeoffset` and `hospitaldischargeoffset` become
*post-outcome quantities used in cohort construction* the moment a minimum-LOS criterion is applied.
Removing them from the feature matrix does not neutralise that use; only omitting the filter does
(§2.2). Entries 33 and 34 are excluded on suspicion rather than proof — we could not verify from the
documentation when physician specialty is assigned relative to the outcome, and an unverifiable
timing argument is not a reason to include a column.

---

## 7. Split policy and the 208-hospital arithmetic

```python
EICU_N_TARGET_SITES   = 24
EICU_SPLIT_NAMESPACE  = 9        # rng namespace tag for the eICU path
EICU_MIN_TOTAL_SITES  = 149      # SUFFICIENT floor for cal >= MIN_CAL_CLUSTERS
EICU_SPLIT_REPLICATES = 20
```

`site_split(site_raw, replicate=r)` sorts the unique site labels, shuffles them with
`np.random.default_rng(np.random.SeedSequence([SEED, EICU_SPLIT_NAMESPACE, r]))`, holds out the
first `EICU_N_TARGET_SITES` as the target population, and partitions the remainder by
`SPLIT_FRACTIONS = (0.40, 0.20, 0.40)` — **imported from `certgate.constants`, never re-literalled**
(audit F15/F34).

| scale | sites | held out | remainder | train | aux | **cal** | vs `MIN_CAL_CLUSTERS = 50` |
|---|---|---|---|---|---|---|---|
| real extract | 208 | 24 | 184 | `int(73.6)` = 73 | `int(36.8)` = 36 | **75** | 50% headroom |
| protocol floor | 149 | 24 | 125 | `int(50.0)` = 50 | `int(25.0)` = 25 | **50** | exactly at the gate (fires on `< 50`) |
| small mock arm | 180 | 24 | 156 | `int(62.4)` = 62 | `int(31.2)` = 31 | **63** | 26% headroom |

`EICU_MIN_TOTAL_SITES = 149` is a **sufficient** floor, not the tight one. The two `int()`
truncations make the calibration count non-monotone in the total — 148 sites yield 51
calibration clusters while 149 yield exactly 50 — so the property the constants test pins is
"at and above 149 the projection *always* clears `MIN_CAL_CLUSTERS`, and some total below it
does not." The tight breakpoint is 146; the constant keeps three sites of slack, which is the
correct direction for a pre-registered floor.

`EICU_N_TARGET_SITES = 24` is chosen so that (i) `24 ≥ 2 × BBSE_MIN_TARGET_SITES` gives the pooled
arm a real cluster count for the `q_t` bootstrap, (ii) 24 single-hospital pools are enough to
*measure* between-site dispersion rather than anecdote it, and (iii) the remainder still leaves
75 calibration sites.

`site_split` raises `EicuError(reason=too-few-sites)` below `EICU_MIN_TOTAL_SITES` and
`EicuError(reason=too-few-cal-clusters)` if the calibration count falls short, and asserts
**pairwise** disjointness — a deliberate strengthening over `fixture_etl.site_split`, whose
`assert not (a & b & c)` tests a triple intersection and passes on a two-way overlap.

**Records never cross a boundary.** Splitting is on the site label and every record inherits its
hospital's assignment. `assert_site_disjoint(train=, aux=, cal=)` runs before every `run_certgate`
(audit F03), and target disjointness is checked at the record level as well when `target_site_id` is
supplied (audit V9).

**The headroom is not decorative.** Some hospitals may contribute zero stays to the primary cohort
after S1–S4, and the gate counts **record-carrying** calibration clusters (audit B-5), not label
counts. `MIN_CAL_CLUSTERS` returns a report with `reason="insufficient-clusters"` rather than
raising, so `run_eicu` branches on `report["reason"]` and never treats a gated run as a successful
certification of nothing (T-12).

**Replication arm.** `replicate` indexes an independent re-split; `replicate=0` is the published
primary split, and `--replicates 20` (`= EICU_SPLIT_REPLICATES`) is the validity arm scored by F-A.
The 20 re-splits share one hospital population, so they are not independent draws of the site
population; §10 states what that costs.

---

## 8. Target-pool policy

Both arms run on every replicate.

**Arm 1 — per-hospital, single-site pools (24 per replicate).** One `run_certgate` per held-out
hospital, `target_label = f"hosp-{h}"`, `target_site_id` = that hospital's per-record labels, so
`K == 1`. The column is supplied even though the pool is one site: `K == 1` takes the identical exact
two-sided Clopper–Pearson `q_t` path that `None` takes (`BBSE_MIN_TARGET_SITES` is enforced only for
`2 ≤ K < 10`), and supplying it additionally buys `densify_sites` validation, the record-level
disjointness assertion against train/aux/cal, provenance binding of the dense array and its canonical
labels, and `diagnostic["target_site_id_supplied"] == True`. There is no statistical difference and
no cost. Pools below `MIN_ANSWERABLE = 10` records return a `pool-too-small` report — not an
exception — and are recorded as such (audit B-6/F42).

**Arm 2 — pooled multi-site (1 per replicate).** All 24 held-out hospitals,
`target_label = EICU_POOLED_TARGET_LABEL = "eicu-target-pool"` (chosen so its normalised form cannot
collide with any `hosp-NNN` label), `target_site_id` supplied with `K = 24 ≥ BBSE_MIN_TARGET_SITES`,
so `q_t` takes the cluster bootstrap.

`target_site_id` is never omitted. Omitting it is the caller **declaring** the pool is a single site,
which substitutes an interval that under-covers a multi-hospital pool (SPEC `shift.py`, audit V2).

The per-hospital arm exists to measure what the pooled certificate does not bound: the spread of
answered error across individual hospitals (§12.1, prediction P2).

---

## 9. A-priori predictions

Frozen 2026-07-30. Each names the exact artifact field that settles it; each is falsified by its
negation. `run_preflight` copies this table verbatim into `EICU-SUMMARY.md` § `EICU-PREDICTIONS`
before any certificate exists.

| id | prediction | settled by |
|---|---|---|
| **P1** | At 208 hospitals (75 calibration sites), **α = 0.10 certifies** on the pooled arm and **α = 0.05 does not**, in ≥ 15 of the 20 replicates. Basis: the synthetic E4 frontier — α = 0.10 certifies from ~150 sites, α = 0.05 first appears near 300 and is reliable only by 400. | `EICU_pooled.csv` `certified` × `alpha` |
| **P2** | The per-site dispersion diagnostic on the pooled target pool at the deployed τ is **> 0.02 and inside [0.05, 0.30]** — real hospitals more heterogeneous than the synthetic generator at `s_u = 0.5` (0.02), closer to its `s_u = 2.0` arm (0.10). | `EICU_pooled.csv` `per_site_exceed_frac` |
| **P3** | **BBSE contributes no certificate**: it declines on ≥ 90% of the 25 pools per replicate, with `bbse-misspecified` or `bbse-ill-conditioned` modal. Basis: E2's 200/200 declines plus the coarse 2000-draw `q_t` tail widening the 16-corner box. Falsified if BBSE certifies a τ the baseline walk does not. | `decline_reason`, `mode_outcomes` |
| **P4** | APACHE-absence features (`aps_present`, `apv_present`, or an `aps_*__missing` / `apv_*__missing` sibling) appear in the **top 3** of the abstention `gap_ranking` on the pooled arm. Basis: absence is site-correlated by the dataset authors' own account. **P4 IS ALSO THE LEAK'S SIGNATURE** (amendment A1): on a corpus with outcome-correlated APACHE-row absence planted, this is exactly what the ranking returns (`aps_present` gap −1.21 at rank 1, `apv_present` at rank 2). P4 is therefore settled as CONFIRMED only when every F-D leg is clear and §5.5's prevalence-ratio gate has not fired; otherwise the same observation is settled as EVIDENCE FOR THE LEAK. A prediction whose confirmation and whose failure mode look identical is not settled by the observation alone. | `EICU_diagnostics.json` `abstention_gap_ranking`, jointly with `leak_probe` and `outcome_missingness` |
| **P5** | The per-hospital arm returns `pool-too-small` for **≥ 1 and ≤ 6** of the 24 target hospitals (heavy-tailed sizes; ~78% of hospitals have < 500 stays). | `EICU_per_site.csv` `reason` |
| **P6** | Mean coverage at the operative rung on the pooled arm is in **[0.60, 0.95]**. | `EICU_pooled.csv` `coverage` |
| **P7** | Primary-cohort size lands in **[130 000, 175 000]** stays across **208** sites, and `apache-result-linked` retains **≤ 195** sites — the APACHE-result restriction visibly deletes ≥ 13 hospitals. | `EICU_attrition.csv` |

**Ordering caveat, stated rather than glossed.** P5 and P7 are settled by quantities the *preflight*
computes, and the preflight is also what writes this table into the run artifact. Their evidential
value therefore rests on this document's commit predating the download, not on the summary-writing
step. P1–P4 and P6 require a certificate and are settled strictly after. No prediction may be
revised once the preflight has run; a revision is an amendment under §0 and is labelled post-hoc.

---

## 10. Pre-declared failure criteria

Stated before the run, so that a negative result cannot be reinterpreted afterwards.

**F-A — validity failure (the method is wrong).** Across the 20 re-splits, each issuing its own
certificate at the operative rung and each scored against **its own** held-out 24-hospital pool, the
fraction of certified replicates whose influence-weighted answered risk `R_M` on that pool exceeds α
is **> DELTA = 0.05**. One exceedance in 20 is within budget and is not a failure; two of 20
(0.10 > 0.05) is.

*Power is explicitly limited.* Twenty replicates cannot resolve a δ = 0.05 rate, and the replicates
share one hospital population, so they are not independent draws of the calibration site population.
The result must be written as a bounded observation — the absence of gross violations at the tested
power — and never as "validity confirmed."

**F-B — feasibility failure (the method is useless here).** No rung certifies on any replicate on the
pooled arm, **or** the operative rung's mean coverage is `< 0.20`. Answering fewer than a fifth of
cases is not a deployable gate.

**F-C — protocol failure (the run must not produce numbers).** Any of: the leak-denylist test fails;
`preflight(expect_reference=True)` raises `reference-row-count-mismatch`; the categorical drift gate
fires; `assert_aggregate_only` fires; `x` is non-finite; `assert_site_disjoint` raises. The run
aborts and writes no certificate.

**F-D — the unfalsifiable-success failure, in THREE legs.** This criterion exists because a good
number is the one outcome nobody investigates. It fires if **any** leg fires; if it fires, the run
is treated as failed until the denylist, the first-stay rule, the dedup logic **and the APACHE
presence channel (§5.5)** have been re-audited, and it is never reported as a headline.

*Leg 1 — implausible discrimination.* The head's own out-of-sample AUC on the site-disjoint
calibration split exceeds `EICU_LEAK_AUC_CEILING = 0.90`. APACHE-IVa, a purpose-built and
expensively curated day-1 score, reaches roughly 0.87 on hospital mortality in eICU; a 161-column
logistic head that beats 0.90 *from the same day-1 inputs* is a leak before it is a result.

*Leg 2 — the missingness block carries the model.* Ablating the 49 missingness/presence columns
costs more than `EICU_LEAK_ABLATION_MAX_DROP = 0.05` of AUC. Measured on the mock: clean −0.016;
outcome-correlated absence at p = 0.30 +0.082; at p = 0.75 +0.248.

*Leg 3 — the original.* α = 0.05 certifies at 208 hospitals **with coverage > 0.90** and fresh-pool
`R_M` near zero, contradicting the E4 frontier.

**Why three legs (amendment A1/E-10).** Leg 3 was the whole criterion, and it is conditioned on
`α == 0.05` AND `coverage > 0.90` AND `R_M < 0.01`. A demonstrated leak — outcome-correlated
APACHE-row absence — certified `α = 0.10` at coverage 0.857 and passed straight underneath it:
`EICU-SUMMARY.md` reported `F-D fired: false, n_hits: 0`. Legs 1 and 2 depend on **neither α nor
coverage**, and both are computed every replicate inside `run_eicu` (written to
`EICU_pooled.csv`'s `head_auc_oos` / `head_auc_ablated` / `ablation_drop` / `leak_alarm` columns and
to `EICU_diagnostics.json`'s `leak_probe`), so the check exists on the real extract and not only
inside pytest — where the mock's Bayes-optimal ceiling does not apply and only a runtime number can
bound it.

The two legs have different sensitivities *and* cover different halves of the channel, which is why
both are kept: whole-row absence is caught earliest by §5.5's prevalence-ratio abort, while
**cell-level** outcome-correlated missingness leaves the presence flags untouched and is caught only
by leg 2. `tests/test_eicu_path.py` plants both and asserts the corresponding gate fires.

**F-E — estimand-population failure.** If the primary arm's `n_sites` at `primary-cohort` is
materially below 208 (say `< 200`), the certificate's site-population average no longer refers to the
eICU hospital population but to "hospitals that survived our filters", and every guarantee sentence
must be re-scoped to the surviving population by name. This is a reporting obligation, not an abort.

---

## 11. Attrition ledger and the site-selection statistic

```python
EICU_ATTRITION_STEPS = ("raw-unit-stays", "site-parseable", "outcome-known", "adult",
                        "first-stay", "primary-cohort",
                        "apache-aps-linked", "apache-result-linked", "apache-complete-arm")
```

Every step records `{"step", "n_stays", "n_sites", "n_positive", "prevalence"}`. The last three
steps are **diagnostic**: they turn the site-correlated APACHE selection into a number in the
primary arm without applying it as a filter.

**`n_positive` is not decoration (amendment A1).** The ledger previously recorded only `n_stays` and
`n_sites`, so it could show that the `apache-aps-linked` step *loses* stays but not that the stays
it loses are disproportionately **deaths** — which is the entire signature of the outcome-informative
absence channel (§5.5). On a leak-planted mock the prevalence falls from 0.094 at `primary-cohort`
to 0.025 at `apache-aps-linked` while `n_stays` moves by an unremarkable amount; with `n_positive`
recorded, the ledger states the problem on its own line. `preflight` and `run_eicu`
(`EICU_attrition.csv`) both carry it.

The headline site-selection statistic is `n_sites` at `apache-result-linked` versus `n_sites` at
`primary-cohort` — documentation implies roughly 190 versus 208. It is reported in the paper
regardless of which way it comes out, because it is the quantity that sets the scope of the
`apache-complete` arm's estimand (§12.1) and it is the evidence for §2.4's choice.

`preflight` additionally reports `site_stay_counts[stage]` — min, q1, median, q3, max, mean, and the
counts of sites below 20 / 50 / 100 / 500 stays — at every stage, because no published source gives
the per-hospital stay distribution and the calibration cluster count depends on it (T-12).

---

## 12. Threats to validity

Four of these need prose, because a table row cannot state them precisely enough. The remainder are
the frozen build-risk register, reproduced compactly in §12.5.

### 12.1 The estimand's population is not "US hospitals" (T-4, F-E)

The certificate bounds the influence-weighted answered-set risk **averaged over the site population
from which the calibration sites were drawn**, with the probability statement over the calibration
draw (audit V1; METHODS §3; the guarantee text in `report.py` is frozen by `tests/test_report.py`
with the site-population-average, between-site-dispersion, not-a-realized-count, baseline-only
shared-event, operative-rung-selection, concept-out-of-scope, and BBSE-four-parameter-box clauses).
Naming that population correctly is therefore part of stating the result, and it is narrower than a
casual reading suggests, at three nested levels:

1. **eICU is not a sample of US hospitals.** The 208 hospitals are those participating in the Philips
   eICU programme and consenting to contribute 2014–2015 discharges. Participation is not random with
   respect to size, region, teaching status, or tele-ICU adoption. Nothing in the certificate extends
   to hospitals outside that programme, and no sentence in the paper may imply otherwise.
2. **The primary arm's population is the eICU hospitals surviving S1–S4.** If that count falls
   materially below 208, F-E requires the guarantee text to be re-scoped by name to the surviving
   population.
3. **The `apache-complete` arm's population is the APACHE-contributing hospitals only.** Roughly 18
   of 208 hospitals contribute no `apachePatientResult` rows, and coverage is partial in many more,
   so restricting to APACHE-complete stays deletes and thins sites non-randomly. Any number from that
   arm refers to *"hospitals contributing complete APACHE records to eICU-CRD v2.0"* — a different
   and smaller population than the primary arm's. The two site counts are printed side by side
   wherever the arm appears, and the arm is never the headline.

The related exposure is that the certificate is a population **average** and bounds no individual
hospital's answered error rate. Under between-site heterogeneity, the fraction of hospitals exceeding
α is governed by a dispersion the certificate neither measures nor bounds. The per-hospital arm (§8)
exists to measure it; P2 predicts it will be materially larger than the synthetic `s_u = 0.5` value.
Any sentence reading the eICU result as a per-hospital guarantee is the claim audit V1 removed.

### 12.2 APACHE missingness is TWO channels: a covariate-shift channel this method does not cover, and an outcome channel that is a leak (T-3, T-2, E-9)

**Read §5.5 first.** The section below was written as if missingness were purely site-informative;
amendment A1 corrected that. There are two channels sharing one set of columns:

*The outcome channel (a LEAK, not a limitation).* The day-1 APACHE window does not close for a stay
that ends because the patient died, so whole-row absence is a partial outcome proxy with no column
name. This is not something to state as a threat and live with — it is gated: measured in
`outcome_stratified_missingness` / `apache_absent_los` / the ledger's `n_positive`, aborted by
`outcome-informative-missingness` at `EICU_MAX_OUTCOME_PREVALENCE_RATIO = 2.0`, alarmed at runtime
by F-D legs 1 and 2, and escaped explicitly by `--arm apache-linked`. The full argument, the
measured dose-response and the demonstration that the old defenses were structurally blind to it
are in §5.5.

*The site channel (a genuine limitation, unchanged).* The remainder of this section.

The data descriptor states plainly that data completion varies at the hospital and ICU level —
different units have different documentation interfaces. Missingness is therefore **site-informative**:
the pattern of `__missing` siblings and the two presence flags carry hospital identity. Two
consequences, and only the first is handled.

*Handled.* The `-1` / `''` dual sentinel policy (§5.2) and the per-column negative-mass abort keep
missingness from entering the matrix as a finite number, and the preflight publishes
`sentinel_site_dispersion` (per-site `-1` rate: mean, sd, p10/p50/p90) and `apache_coverage_by_site`
per table, so the dispersion is a printed quantity rather than an assumption.

*Not handled.* Site-varying missingness means `P(x)` differs between calibration hospitals and a
target hospital. That is covariate shift, and **CertGate v2 has no covariate-shift mode** — A1 was
scope-cut because importance weighting provably cannot certify below roughly 400 clusters at
practical clip caps (audit F34; README "Scope — what is OUT"). The baseline mode's tag is
exchangeability, which this channel can falsify; the BBSE mode's tag covers outcome-prevalence shift
only, with `P(x|y)` assumed invariant, which this channel can also falsify. Neither tag covers it.
The result is that a hospital whose interface differs sharply from the calibration hospitals is
outside the assumption set of every mode offered, and the certificate says nothing there. We surface
the channel (the diagnostics above, plus `aps_present` / `apv_present` as named features so the
abstention explanations can point at it — P4) rather than imputing it away, and we state the
limitation instead of claiming robustness the method does not have.

### 12.3 Records are not independent within a patient (T-5)

Three levels of dependence, with different fates.

*Within a hospital admission* — multiple unit stays (`unitvisitnumber`) for one
`patienthealthsystemstayid`. Removed by S4: exactly one stay per admission.

*Across admissions at the same hospital* — one `uniquepid` with several hospital admissions
contributes several records. These remain, and they are **absorbed by the design rather than
removed**: the atoms are per-site and the betting test runs over sites, so records within a site are
never assumed independent. Repeat admissions inflate `n_c`, which affects the influence weight
`g_c = min(n_c, M)` and hence how much that hospital counts, but not the validity of the site-level
test. This is one of the concrete payoffs of the site-as-unit choice and is worth stating explicitly,
because the record-level alternative would be biased here.

*Across hospitals* — a `uniquepid` appearing at two `hospitalid`s puts correlated records into two
splits without tripping any gate; `assert_site_disjoint` compares site labels only. The preflight
measures `cross_site_patients.n_uniquepid_multi_hospital` and its share. If the share exceeds
`EICU_MAX_CROSS_SITE_PATIENT_SHARE = 0.01`, the preflight warns and `run_certification` records it in
the certificate JSON; it does not abort. The measured share is a **lower bound** — de-identification
may split one person across several `uniquepid` values, and we cannot detect that. The response is
disclosure rather than a filter, because a filter on cross-hospital patients would itself be
site-correlated (referral centres would lose more records than community hospitals), reintroducing
the selection problem of §2.2 to fix a smaller one.

### 12.4 The certificate is void under concept shift, and concept shift is undetectable here (T-19)

If `P(y|x)` differs between the calibration hospitals and a target hospital — different treatment
protocols, different thresholds for ICU admission, different end-of-life practice — then both
assumption tags are false and the certificate can be confidently wrong. This is not a residual
concern in a 208-hospital 2014–2015 US ICU cohort; heterogeneity in care process is one of the
things the dataset exists to study.

No unlabeled-data method can detect it. BBSE assumes `P(x|y)` invariant and estimates only a
prevalence ratio; a genuine change in the outcome mechanism is indistinguishable from ordinary
covariate variation without labels. The synthetic negative control E3 shows the failure directly:
with the tilt verified to push true answered risk to 0.161 > α, the certificate hard-violates 70% of
the time and violates the aggregate estimand on 100% of certificates. The assumption tag is what
carries the claim.

The eICU run holds outcome labels for the target hospitals, so it can *measure* the failure through
the oracle scoring path — but that measurement is available only because the study is retrospective.
A deployment has no such instrument, which is the reason the tag must be reported with the number
rather than assumed away. T-19 is added by this document — the interface contract's frozen register
runs T-1 to T-18, all of which are implementation risks with a diagnostic attached. This one has no
diagnostic, because none exists; it is carried in §12.5 so the numbering is contiguous, with its
response column saying so.

### 12.5 Build-risk register (frozen with the interface contract)

| id | risk | preflight field / gate | response |
|---|---|---|---|
| T-1 | Outcome leakage from an allowlisted column | not a preflight check — `assert_no_leak_columns` in CI, plus F-D | abort; re-audit denylist and dedup before reporting anything |
| T-2 | `-1` flows through as a finite value | `sentinels[t][col]`: `n_minus_one`, `n_other_negative`, `min_positive`, `p01` | negative mass not exactly at `-1.0` raises `unexpected-negative-sentinel` **above `EICU_MAX_UNPARSEABLE_SHARE = 0.01` of rows**; below it the cells become missing and a `[MEASURE]` warning names column, count and share (amendment **A6**, post-hoc — the released extract carries exactly one such cell, `urine = -11245.5648`, against an otherwise contiguous non-negative support) |
| T-3 | Site-correlated APACHE missingness acts as a site proxy | `apache_coverage_by_site[t]`, `sentinel_site_dispersion` | named as `aps_present` / `apv_present`; §12.2; never filtered |
| T-4 | APACHE restriction changes the estimand's population | `attrition`: `n_sites` at `apache-result-linked` vs `primary-cohort` | primary arm never restricts; §12.1; F-E |
| T-5 | Records not independent within patient; cross-hospital `uniquepid` | `cross_site_patients`, `n_healthsystemstays`, `unitvisitnumber_hist` | §12.3 — S4 plus disclosure |
| T-6 | Wrong download / version / re-zip with different case | `tables[t].rows` vs `EICU_REFERENCE_ROW_COUNTS`; `n_hospitals`; `n_uniquepid`; `header_case_as_read` | `expect_reference=True` raises `reference-row-count-mismatch`; filename and header resolution are case-insensitive |
| T-7 | Categorical vocabulary frozen without the data is wrong | `categorical_drift[col]`: `other_share`, `top_unlisted`, `exceeds_cap` | over 5% raises `categorical-level-drift`; fix is a visible SPEC + constants diff and an amendment |
| T-8 | `apachePatientResult` rows-per-stay is not 2 | `apache[t].rows_per_stay_hist`, `n_stays_gt1_row`, `apache_versions` | explicit dedup by `min(surrogate_id)` within `(stay, version)`, counts reported |
| T-9 | `predictedhospitalmortality` compared as a string (`'-1' > '0'`) | `apache_versions.version_x_pred_unavailable` | `float()` first, always; `'-1'` → NaN |
| T-10 | `fio2` in two conventions; Fahrenheit temperatures | `fio2_convention`, `temperature_convention` | frozen non-overlapping windows; conversions counted; outside both → missing |
| T-11 | Decimal-point entry errors in height/weight; `0` as missing | `sentinels['patient']`: `n_zero`, `p01`, `p99`, `max` | frozen plausibility windows → missing + indicator, counted |
| T-12 | Heavy-tailed hospital sizes drop carrying calibration clusters below 50 | `site_stay_counts[stage]` at every stage | 24-site holdout leaves 75; `site_split` raises `too-few-cal-clusters`; `run_eicu` branches on `report["reason"]`, never on exception-or-not |
| T-13 | Standardization silently lost (`sd_safe = 1.0` guard) | `sentinels` per-column `p01/p50/p99/max` | allowlist contains no raw timestamp or surrogate key; `pre_icu_hours` is scaled and windowed |
| T-14 | A one-hot level absent from S_train → zero coefficient, zero attribution | `categorical_drift` plus per-level train counts in `meta` | listed in `meta["warnings"]` and named in the paper's limitations |
| T-15 | BBSE declines everywhere and the label-shift arm has nothing to say | not preventable — registered as P3; `gap_lo`, `q_ci`, `n_target_sites` written to `EICU_diagnostics.json` | reported as a finding: the correction refuses rather than guesses. Falsified only if BBSE certifies a τ baseline does not |
| T-16 | Memory / runtime across 20 replicates | `preflight` row counts before anything is allocated | three streaming passes; `build_raw` once, then loop `site_split` + `impute`; matrix ≈ 193 MB |
| T-17 | Record-level data escapes into the tracked `experiments/out/` | not a preflight check — `assert_aggregate_only` on every write; test 19 | `EICU_FORBIDDEN_OUT_KEYS` + `EICU_MAX_OUTPUT_LEN = 512`; `answered_mask` replaced by its `.sum()` |
| T-18 | The pre-registration is not credible because it can be edited afterwards | `preflight` writes §9 into `EICU-SUMMARY.md` before any certificate exists; `EICU_provenance.json` timestamps it | dated commit of this file + constants pins before the download; §0 states what that is and is not worth |
| T-19 | Concept shift voids the certificate and is undetectable from unlabeled data | none — no diagnostic exists | §12.4; the assumption tag is reported with every number; E3 is the demonstration |
| **T-20** | **APACHE-row absence is OUTCOME-informative** — the day-1 window does not close for a stay that ends because the patient died, so the presence flags and 43 `__missing` siblings are a partial outcome proxy with NO COLUMN NAME (invisible to T-1's name denylist, to T-2's value gate, to T-7's vocabulary gate, and to the old single-leg F-D) | `outcome_stratified_missingness`; `apache_absent_los`; `attrition[*].n_positive` / `.prevalence`; runtime `leak_probe` | `build_raw(arm="primary")` raises `outcome-informative-missingness` past `EICU_MAX_OUTCOME_PREVALENCE_RATIO = 2.0`; F-D legs 1–2; declared escape `--arm apache-linked` (§5.5, §12.2) |
| **T-21** | **A NULL token that is not `''`** (Postgres text-format `\N`) makes all 43 allowlisted APACHE numerics 100% missing and 86 of 161 coefficients exactly 0.0, while `build_raw` succeeds with an empty `warnings` list — the opposite direction of T-2, which had no guard | `unparseable_tokens[t][col]` and `.over_cap`, with the offending TOKENS retained, not just counted | `build_raw` raises `unrecognised-null-token` past `EICU_MAX_UNPARSEABLE_SHARE = 0.01` |
| **T-22** | **Measurement timing unverifiable** for nine allowlisted `apachePredVar` treatment flags (`activetx` above all), while the denylist applies a "timing unverified" standard to two `apachePatientResult` columns | `outcome_screen`: per-feature stratum prevalence and univariate AUC, in `EICU_diagnostics.json` | every feature past `EICU_FEATURE_AUC_REVIEW = 0.75` is flagged for timing re-audit before any number is reported (§5.4a) |
| **T-23** | **`patientunitstayid` duplicated in `patient`** — the two cohort scans resolved it differently (scan A last-wins for label and site, scan B first-wins for features), filing one patient's covariates under another row's outcome and hospital, mis-accounted as a first-stay drop | none needed — it is a primary-key violation | `duplicate-stay-id` raise in `_select_cohort`, with a belt-and-braces raise in scan B |
| **T-24** | **A read-boundary failure escapes untyped** — a non-UTF-8 byte or a partial unzip surfaced as a bare `UnicodeDecodeError`/`EOFError` naming neither the table nor the file, on a five-table multi-GB extract | none — the raise itself is the report | `undecodable-table` / `truncated-table`, naming the table, the path and the byte offset reached |
| **T-25** | **A gate fires on the CORRECT extract** — `n_uniquepid` was counted post-filter and compared against the pre-filter published total, so the mandatory arrival-day `preflight(expect_reference=True)` would have aborted on the genuine v2.0 extract, writing no artifact at all | `patient.n_uniquepid` / `.n_hospitals` are RAW S0 counts; `.n_uniquepid_cohort` / `.n_hospitals_cohort` are the cohort diagnostic | dataset identity and cohort diagnostic are different quantities and are named differently; a regression test pins the constants to a corpus's true totals and asserts NO raise |
| **T-26** | **A join-key FORMAT artifact or key mismatch UNLINKS a child table** — `patientunitstayid` as `141258.0` (pandas float round-trip), scientific notation, a header-only table, or a key shift with row counts intact: 89/161 columns collapse to the fallback, both presence flags die, E-9's `gate_applies` goes false (total absence bypasses the leak gate), and `EICU_REFERENCE_ROW_COUNTS` cannot see the key-shift route | `join_key_unparseable` in `build_raw` meta; `n_key_unparseable` per child table in preflight; both raises projected in `invalid_conditions` (A5) | `unparseable-join-key` past `EICU_MAX_UNPARSEABLE_SHARE`, naming table and tokens; `apache-coverage-collapse` when `n_present < EICU_MIN_OUTCOME_STRATUM ≤ n_cohort` — E-9 must stay evaluable |
| **T-27** | **A non-`''` NULL token in a `patient` numeric flows silently** — the E-15 gate was `aps_`/`apv_`-scoped, so `\N` zeroed `admissionheight`/`admissionweight` unalarmed, and in `hospitaladmitoffset` silently changed §2.1 first-stay selection (the tie-breaker column) with no attrition trace | `sentinels.patient.<col>.n_unparseable`; `unparseable_tokens.over_cap` (A5) | `unrecognised-null-token` covers every allowlisted numeric; `_parse_windowed` samples the offending tokens so the abort NAMES them |

---

## 13. Deviations from published eICU cohort conventions

| # | convention | our choice | reason |
|---|---|---|---|
| 1 | ICU stay ≥ 24 h or ≥ 48 h | no LOS floor | immortal-time selection; uses post-outcome offsets in cohort construction; site-heterogeneous (§2.2) |
| 2 | hospitals with ≥ 500 stays | no minimum | leaves ~46 hospitals → ~18 calibration clusters → `insufficient-clusters` (§2.3) |
| 3 | `age > 89` dropped via `max_age = 89` | kept, mapped to 90.0, flagged `age_masked` | dropping removes a mortality-enriched stratum whose share varies by hospital — a site-correlated exclusion (§5.1) |
| 4 | restrict to APACHE-scored stays | primary arm does not restrict; declared sensitivity arm does | deletes ~18 hospitals and moves the estimand's population (§2.4, §12.1) |
| 5 | first-24h vitals / labs from the time-series tables | five tables only; no time-series features | ~4 GB out of scope for v1; the certificate is about the gate, not about beating a physiology benchmark. Cost: a weaker head than the literature's, which affects coverage but not validity |
| 6 | random record-level or patient-level split | site-disjoint split, hospital = cluster | the design decision the method is about (§4) |
| 7 | ICU mortality, or a composite outcome | in-hospital mortality from `hospitaldischargestatus` | single documented column, two levels, drop-never-impute (§3) |
| 8 | elaborate imputation (MICE, GAIN, carry-forward) | mean imputation fit on S_train, plus an explicit indicator per column | keeps missingness visible to the model and to the attributions; avoids a transductive channel (§5.6) |
| 9 | drop hospitals by region / teaching status / bed count | no such filter | those columns are site-constant site proxies and are excluded as features rather than used as filters (§5.7) |
| 10 | first ICU stay per hospital admission | **followed**, with the tie-break made explicit | the standard convention; the offset sign trap makes the tie-break worth writing down (§2.1) |

Deviations 1–4 all make certification *harder* or the cohort *messier* than the conventional choices
would. That direction is intentional: each conventional filter buys a cleaner cohort by conditioning
on something correlated with the site, and the site is the unit the guarantee is stated over.

---

## 14. Reproduction

### 14.1 Operator checklist — in order, when the zip lands

The order is part of the protocol: step 5 must pass before step 6 is run, and step 9 must happen
before anything is written up.

```
0.  BEFORE downloading — confirm the freeze is committed and CI is green.

    THE PROJECT DIRECTORY IS NOT YET A GIT WORKING TREE (verified 2026-07-31:
    `git rev-parse --is-inside-work-tree` -> "fatal: not a git repository"). Until it is,
    .gitignore is inert, nothing is tracked or ignored, §0's ordering claim has no
    timestamp of any kind, and steps 0 and 10 below cannot run. Create it FIRST, and make
    the freeze commit before the extract exists on disk:

      git init
      git add -A                                  # .gitignore already denies *.csv.gz, eicu-*/
      git status --short | grep -i eicu           # MUST show no extract or mock corpus
      git commit -m "freeze: eICU-CRD v2.0 protocol + constant pins, pre-extract"

    Then, and only then:
    git log --oneline -1 -- EICU-PROTOCOL.md experiments/eicu_etl.py tests/test_constants.py
    python -m pytest tests -q     # green, including
                                  #   tests/test_constants.py::test_eicu_protocol_constants_pinned
                                  #   tests/test_constants.py::test_eicu_mock_constants_pinned
                                  # (an absolute test count here goes stale on every new test
                                  #  and is a false go/no-go signal — check GREEN and those two)
    Record the commit hash; it is the pre-registration reference reported in the paper.
    If the repository is not created before the download, §0's ordering claim must be
    softened in the paper to "written before, with no external or version-control
    timestamp" — which materially weakens it.

1.  Add the data directory to .gitignore BEFORE the extract exists on disk.
    A path outside the repository is preferred; a gitignored path inside it is the minimum.

2.  Download the zip from PhysioNet under the credentialed account. Do not unzip into the repo.

3.  Verify integrity against the shipped manifest, from inside the extract directory:
      sha256sum -c SHA256SUMS.txt                          # Git Bash
      Get-FileHash *.gz -Algorithm SHA256                  # PowerShell, compare manually
    A mismatch stops here.

4.  Exercise the full-scale mock first, so a failure is attributable to the code and not the data:
      $env:CERTGATE_EICU = "1"; python -m pytest tests/test_eicu_path.py -q     # PowerShell
      CERTGATE_EICU=1 python -m pytest tests/test_eicu_path.py -q               # Git Bash
    EXPECT A DECLINE AT THE TWO FROZEN CORPUS SIZES (180 and 208 hospitals) -- and ONLY
    there. At the frozen EICU_MOCK_SIGNAL_B = 0.85 the mock's outcome has a Bayes-optimal
    AUC of 0.726, the fitted head reaches 0.60 out of sample, and an ORACLE ranking's best
    margin 0.0354 sits below certify.margin_floor: 0.0428 at the small arm's 63 calibration
    clusters and 0.0359 at the full arm's 75.
    THE COMPARISON DOES NOT GENERALISE. margin_floor scales as 1/n_carrying, so the floor
    first drops BELOW 0.0354 at n_carrying = 77 (~217 hospitals): a mock generated at 900
    or 1500 hospitals CERTIFIES alpha = 0.10 with the pre-registered constant untouched.
    That is correct behaviour, not a broken pipeline. The certified branch is exercised by
      $env:CERTGATE_EICU_LARGE = "1"; python -m pytest tests/test_eicu_path.py -q -k large
    which builds a 900-hospital mock and asserts the same HONESTY contract.
    This step proves the pipeline RUNS end to end at the real scale.

5.  PREFLIGHT — mandatory, non-certifying, with the reference check ON:
      python -m experiments.run_eicu --data <DATA_DIR> --preflight
    Read experiments/out/EICU_preflight.json in full before running anything else. Specifically:
      - reference_check.invalid_conditions EMPTY — it names every raise build_raw will make
      - tables[*].rows_match_reference all true                       (T-6)
      - tables[*].header_case_as_read == "lower" on the released extract  (T-6, E-17)
      - categorical_drift[*].exceeds_cap all false                    (T-7)
      - sentinels[*][*].n_other_negative == 0 and min_positive >= 0   (T-2)
      - unparseable_tokens.over_cap EMPTY — a non-'' NULL token       (E-15)
      - outcome_stratified_missingness.aps_present / .apv_present:
          prevalence_ratio vs EICU_MAX_OUTCOME_PREVALENCE_RATIO = 2.0 (E-9)  <-- READ THIS
          ONE FIRST. It is the screen for the ONE leak channel that has no column name and
          that no denylist can see. If it is over the cap, build_raw will refuse the primary
          arm and the answer is step 8b, NOT a widened cap.
      - apache_absent_los: aps_absent vs aps_present median LOS       (E-9)
          Materially shorter absent stays means the day-1 window did not close BECAUSE THE
          STAY ENDED — i.e. the outcome channel, not the site channel.
      - attrition: n_sites AND prevalence at primary-cohort vs apache-aps-linked (E-9, T-4,
          F-E, P7). A prevalence collapse across that step is the same alarm.
      - site_stay_counts['primary-cohort'].n_below_20                 (T-12, P5)
      - cross_site_patients share vs 0.01                             (T-5)
      - warnings: empty, or every entry understood
    Any F-C condition here stops the run. A drift-gate hit is an amendment under §0, not a
    quiet widening of a level tuple.

6.  PRIMARY RUN — the published split (replicate 0):
      python -m experiments.run_eicu --data <DATA_DIR> --replicates 1
    Then, BEFORE reading any coverage or tau: check EICU_pooled.csv's leak_alarm column and
    EICU_diagnostics.json's leak_probe / outcome_screen blocks (F-D legs 1 and 2, E-10).
    A fired alarm FAILS the run regardless of how good the certificate looks.

7.  VALIDITY ARM — the 20 re-splits scored by F-A:
      python -m experiments.run_eicu --data <DATA_DIR> --replicates 20
    Long-running; start it in the background and confirm the process is alive rather than
    trusting a run started across a session boundary.

8a. SENSITIVITY ARM — reported beside the primary arm, never as a headline:
      python -m experiments.run_eicu --data <DATA_DIR> --arm apache-complete --replicates 20

8b. THE IMMORTAL-TIME ARM — mandatory IF step 5's outcome_stratified_missingness screen or
    step 6's leak alarm fired, optional otherwise, never a headline:
      python -m experiments.run_eicu --data <DATA_DIR> --arm apache-linked --replicates 20
    This restricts to stays whose day-1 APACHE window is COMPLETE, so aps_present /
    apv_present become constant and information-free. It is an immortal-time-selected
    cohort — that is the price, and its n_sites and prevalence must be reported beside the
    primary arm's wherever it appears (§2.5, §5.5, §12.2).

9.  Check F-A / F-B / F-D (ALL THREE LEGS) against the results BEFORE writing any prose
    about them, and settle P1-P7 from the named fields in §9. Record every settled
    prediction, including the ones that came out wrong. P4 in particular is settled as
    CONFIRMED only when every F-D leg is clear — otherwise it is the leak's signature
    (§9, E-12).

10. Confirm no record-level artifact reached experiments/out/:
      git status --short experiments/out/
    (requires step 0's repository; without it this check is MANUAL — list the directory and
    inspect every file by hand.)
    Every file there must be aggregate: CSVs of per-site or per-replicate rows, JSON of counts
    and rates, PNGs. Nothing keyed by patientunitstayid or uniquepid.
```

A smoke path exists for wiring changes and does not require the extract:

```
python -m experiments.eicu_mock --out <SCRATCH>/eicu-mock
python -m experiments.run_eicu --data <SCRATCH>/eicu-mock --preflight --no-reference-check
python -m experiments.run_eicu --data <SCRATCH>/eicu-mock --quick
```

### 14.2 Artifacts

| file (in `--out`, default `experiments/out`) | contents |
|---|---|
| `EICU_preflight.json` | the full preflight dict, aggregate-only |
| `EICU_attrition.csv` | `step, n_stays, n_sites, arm` |
| `EICU_pooled.csv` | per replicate × α: certified, τ, deploy mode, coverage, answered error, `rm_fresh`, `rm_exceed`, `per_site_exceed_frac`, `n_cal_carrying`, `decline_reason` |
| `EICU_per_site.csv` | per replicate × hospital × α, with `numbedscategory` / `teachingstatus` / `region` strata and APACHE coverage |
| `EICU_comparator.csv` | APACHE-IVa comparator rates on the answered set |
| `EICU_diagnostics.json` | per-site missingness dispersion, coverage bands, categorical drift, `abstention_gap_ranking`, three-way composition |
| `EICU_certificate.json` | replicate-0 pooled report, arrays stripped, `answered_mask` replaced by its `.sum()` |
| `EICU_pooled.png`, `EICU_per_site.png` | figures |
| `EICU-SUMMARY.md` | sections `EICU-PREFLIGHT`, `EICU-PREDICTIONS`, `EICU-POOLED`, `EICU-PERSITE`, `EICU-COMPARATOR` |
| `EICU_provenance.json` | package versions, python version, seeds, input hashes, UTC stamp |

`run_eicu` never writes `summary.md`: `run_synthetic._existing_summary_blocks` parses `^## (E\d)` —
a single digit — so an `## EICU` section there would be unparseable and clobbered on the next partial
`--only` rerun. The eICU path owns `EICU-SUMMARY.md`.

### 14.3 Seeds and determinism

Everything derives from `certgate.constants.SEED = 20260721`.

- Split: `np.random.SeedSequence([SEED, EICU_SPLIT_NAMESPACE = 9, replicate])`.
- Certification permutations: `certification_rng(alpha, mode_idx, stream)` — sha256 only, and free of
  any target identifier (audit V3/B-10), so one calibration draw yields one shared 1−δ event across
  all target pools in baseline mode.
- BBSE bootstrap: seeded from sha256 of the **target data** (dtype + shape + bytes of `target_x`,
  plus the dense target site partition), never from the free-text target label.
- Imputation fill values are recorded in `meta['impute_fill']` and enter provenance.
- Mock corpus: `EICU_MOCK_SEED = 20260801`, byte-deterministic
  (`gzip.GzipFile(filename="", mtime=0, fileobj=...)` + `io.TextIOWrapper(newline="")`).

Identical inputs must produce byte-identical certificates. Any change to this is a SPEC change.

---

## 15. Compliance

- **Access.** eICU-CRD v2.0 requires credentialed PhysioNet access, completed CITI human-subjects
  training, and a signed DUA (PhysioNet Credentialed Health Data License 1.5.0 + Data Use Agreement
  1.5.0). Only credentialed project members run any command in §14 that touches `--data`.
- **No redistribution.** The extract is not committed, not attached to the manuscript, not uploaded
  to any shared drive or issue tracker, and not pasted into a model context. Reviewers who want the
  data obtain it from PhysioNet under their own credentials.
- **Gitignored.** The data directory is added to `.gitignore` before the extract exists on disk
  (checklist step 1). A path outside the repository tree is preferred.
- **No record-level artifacts.** The DUA restricts derived record-level artifacts, and
  `experiments/out/` is a *tracked* directory. `run_eicu.assert_aggregate_only` sits on every write:
  it refuses any payload carrying `EICU_FORBIDDEN_OUT_KEYS` (`stay_id`, `patient_id`, `admission_id`,
  `site_raw`, `y_raw`, `answered_mask`, `x`, `site_id`, `comparator_predicted_mortality`,
  `split_idx`) or any list/array longer than `EICU_MAX_OUTPUT_LEN = 512` — above every plausible
  aggregate (208 sites, 24 pools, 20 replicates) and below every record-level array.
  `report["answered_mask"]` is replaced by its `.sum()` before serialisation.
- **Published outputs are aggregate.** Certificates, per-site rates, attrition counts, coverage
  bands, drift tables. No row of any released file is keyed by `patientunitstayid` or `uniquepid`.
- **Code deposit.** The code that produces the numbers is released; the data is not. Reproduction by
  a third party requires their own credentialed download, which is the intended arrangement.
- **Citation.** Any use of eICU-CRD cites the data-descriptor paper and the PhysioNet resource, per
  the license.

---

*Frozen 2026-07-30. Amendments go in the log in §0, with a date, a reason, and whether the data had
been seen.*
