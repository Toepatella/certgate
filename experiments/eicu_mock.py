#!/usr/bin/env python3
"""A schema-faithful MOCK of the eICU-CRD v2.0 corpus.

Emits five gzipped CSVs -- patient, hospital, apacheApsVar, apachePredVar,
apachePatientResult -- carrying the real eICU-CRD v2.0 column names in the real
DDL column order. The surrogate id comes first, as MIT-LCP's positional
`\\copy` load requires and as the eicu.mit.edu doc pages do not show.

Nothing here comes from the licensed extract. Every distribution is a declared
generator parameter, so this file ships freely and the extract never has to.

Its job is to be hostile in exactly the ways eICU is hostile, so that
experiments/eicu_etl.py meets the traps before the credentialed download
exists. Each planted wart is a named, testable contract (W1-W16 below), and
tests/test_eicu_path.py asserts them one by one.

  W1  age is VARCHAR with the literal ceiling token '> 89' (note the space)
      and blanks; a naive int(age) raises. Kept, not dropped (protocol A.5.1).
  W2  hospitaldischargestatus in {'Alive','Expired',''} and nothing else. The
      blanks are stays with no usable outcome.
  W3  the undocumented -1 sentinel across every apacheApsVar / apachePredVar
      numeric, at a rate that varies by site (T-2, T-3).
  W4  '' in the same columns -- the documented SQL NULL (NULL '' in the
      MIT-LCP loader) and a second, independent missing channel. Handle only
      one of W3/W4 and a finite -1 poisons the matrix.
  W5  apachePatientResult carries both an 'IV' and an 'IVa' row for most stays,
      a minority only one. predictedhospitalmortality is a string holding a
      probability, with '-1' for unavailable (T-8, T-9).
  W6  APACHE coverage is site-correlated (EICU_MOCK_APS_SITE_BANDS, after the
      data paper's Table 8), and whole hospitals carry zero
      apachePatientResult rows (EICU_MOCK_RESULT_ZERO_SITE_SHARE). That
      site-selection trap is why the table stays out of the feature allowlist.
  W7  several unit stays per patienthealthsystemstayid, with negative
      hospitaladmitoffset where the earliest stay has the highest (least
      negative) offset, and unitvisitnumber sometimes not starting at 1. The
      first multi-stay admission emitted also carries the planted pair
      hospitaladmitoffset (-14, -22) at equal unitvisitnumber, so a known pair
      exercises the first-stay tie-break.
  W8  commas, quotes, embedded newlines and CRLF inside quoted
      apacheadmissiondx, hospitaldischargelocation, physicianspeciality.
  W9  heavy-tailed stays per hospital (lognormal site weights,
      --site-sigma) with an EICU_MOCK_MIN_STAYS_PER_SITE floor.
  W10 decimal-point entry errors in admissionweight / admissionheight
      (544.00 kg, 612.6 cm), and 0 -- not -1 -- as their missing encoding.
  W11 fio2 in both conventions (0.21-1.0 and 21-100) and temperature with
      Fahrenheit contamination, plus values outside both windows (T-10).
  W12 duplicate patientunitstayid rows in apacheApsVar / apachePredVar.
  W13 hospital with blank numbedscategory/region, teachingstatus in both
      renderings ('True'/'False' and 't'/'f'), and both bed-band spellings
      ('250-499'/'>=500' and '250-500'/'>500') mixed across rows.
  W14 a uniquepid appearing at two hospitalids -- correlated records that
      assert_site_disjoint, which compares site labels, cannot see (T-5).
  W15 a UTF-8 BOM on patient.csv.gz.
  W16 unlisted categorical levels below EICU_MAX_OTHER_SHARE, so the frozen
      tuples' OTHER bucket is exercised without tripping the drift gate.
      --drift pushes gender over the cap, for the drift-gate test (T-7).

Two rows are planted verbatim for the sentinel tests. The first apacheApsVar
row written has every numeric at '-1', the second every numeric at ''. Both
must reach the feature matrix as aps_*__missing == 1.0, never as a finite -1.

--signal is on by default, unlike synth_fixture: a mortality corpus with no
outcome has no use here. It plants a latent severity z ~ N(0,1) per stay, and
every allowed feature is a noisy view of z -- age, the 24 apacheApsVar
physiology columns, the 19 apachePredVar comorbidity flags.

The outcome is drawn from P(death) = sigmoid(a + EICU_MOCK_SIGNAL_B*z + u_site)
with a per-site random effect u_site ~ N(0, EICU_MOCK_SITE_SIGMA_U^2) and `a`
solved from EICU_MOCK_BASE_RATE. Prevalence lands on 9.5% with real
between-site heterogeneity, and mortality is genuinely predictable: head AUC
0.69 held out at full scale, against a ceiling of Phi(B/sqrt(2)) = 0.73.

That ceiling is also a limit, stated here rather than discovered later. At the
frozen EICU_MOCK_SIGNAL_B = 0.85, run_certgate declines every rung at both
frozen corpus sizes; the calibration note on EICU_MOCK_SIGNAL_LOAD carries the
margin-versus-floor numbers. The contracted test asserts an honest outcome, not
certification, so a decline is conformant -- and only that branch is exercised.

The leak columns -- diedinhospital, actualhospitalmortality,
unitdischargestatus, the discharge offsets, the APACHE-IVa predictions and the
rest -- are emitted and correctly correlated with the outcome on purpose. That
is what lets assert_no_leak_columns prove the ETL excludes them.

Byte-determinism, an identical contract to synth_fixture.TableWriter:
  - the gzip header is frozen with filename="", mtime=0
  - io.TextIOWrapper(newline="") lets csv.writer own the line endings
  - every stream is a random.Random seeded from an f-string
  - surrogate-id counters are per table, so a --tables subset is a
    byte-identical projection of the full run

The plan always runs in full regardless of --tables. The signal draws live in
dedicated `signal:` / `signal-site:` streams, so --no-signal restores the
label-free draw without shifting any stream, and --site-sigma 0 restores
uniform site assignment.

Usage:
    python -m experiments.eicu_mock --out ./eicu-mock
    python -m experiments.eicu_mock --stays 200859 --sites 208 --out ./eicu-full
    python -m experiments.eicu_mock --tables patient,hospital --out ./eicu-two
    python -m experiments.eicu_mock --drift --out ./eicu-drift

Stdlib only.

Refs: SPEC "Real-data protocol (eICU-CRD v2.0)"; EICU-PROTOCOL.md; risk
register T-2, T-3, T-6, T-8, T-10, T-11.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import math
import os
import random
import sys
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Generator parameters. These live at the top of the generator; protocol
# constants live at the top of eicu_etl.py.
# Pinned literally by tests/test_constants.py::test_eicu_mock_constants_pinned.
# Ref: audit V7.
# ---------------------------------------------------------------------------

EICU_MOCK_SEED = 20260801
EICU_MOCK_SMALL_SITES = 180
EICU_MOCK_SMALL_STAYS = 9000
EICU_MOCK_FULL_SITES = 208
EICU_MOCK_FULL_STAYS = 200859
EICU_MOCK_MIN_STAYS_PER_SITE = 12
EICU_MOCK_SITE_SIGMA = 1.1          # lognormal sd of site weights; 0 = uniform
EICU_MOCK_SITE_SIGMA_U = 0.5        # per-site outcome random effect sd
EICU_MOCK_SIGNAL_B = 0.85           # latent-severity slope (log-odds per unit z)
EICU_MOCK_BASE_RATE = 0.095         # matches the synthetic generator and the
                                    # literature's 8.4-9.9% in-hospital mortality
EICU_MOCK_MULTISTAY_RATE = 0.17     # share of hospital admissions with >1 unit stay
EICU_MOCK_AGE_MASK_RATE = 0.035     # '> 89' share (7081/200859)
EICU_MOCK_STATUS_MISSING_RATE = 0.0087   # blank hospitaldischargestatus (1751/200859)
EICU_MOCK_APS_SITE_BANDS = ((0.0048, 0.10), (0.0673, 0.40),
                            (0.1490, 0.70), (0.7788, 0.92))
                            # (share of sites, that band's per-stay coverage)
                            # -- the data paper's Table 8
EICU_MOCK_RESULT_ZERO_SITE_SHARE = 0.0865  # hospitals with no apachePatientResult rows
EICU_MOCK_SENTINEL_RATE = 0.18      # per-cell -1 rate, modulated per site
EICU_MOCK_EMPTY_RATE = 0.04         # per-cell '' rate (2nd missing channel)
EICU_MOCK_DUP_RATE = 0.002          # duplicate patientunitstayid in aps/predvar
EICU_MOCK_CROSS_SITE_PID_RATE = 0.004    # uniquepid appearing at two hospitalids
EICU_MOCK_DIRTY_RATE = 0.02         # text fields getting commas/quotes/newlines
EICU_MOCK_TABLES = ("patient", "hospital", "apacheApsVar",
                    "apachePredVar", "apachePatientResult")
EICU_MOCK_HEADER_CASES = ("camel", "lower")

# Mirrors eicu_etl.EICU_MIN_TOTAL_SITES. Duplicated for the same reason the
# level tuples below are: importing eicu_etl would pull numpy into a
# stdlib-only module. tests/test_eicu_path.py pins the duplication.
EICU_MOCK_MIN_TOTAL_SITES = 149

# Secondary rates, all generator parameters (not protocol).
EICU_MOCK_AGE_BLANK_RATE = 0.004    # '' age -- the other int() trap
EICU_MOCK_PEDIATRIC_RATE = 0.012    # under-18 stays, so S3's adult gate has work
EICU_MOCK_UNLISTED_RATE = 0.02      # W16: unlisted levels, below the 0.05 cap
EICU_MOCK_DRIFT_RATE = 0.09         # --drift: gender over the 0.05 cap
EICU_MOCK_ICU_DEATH_SHARE = 0.72    # share of hospital deaths that die in the ICU
EICU_MOCK_RESULT_COVERAGE = (0.75, 0.98)   # per-site apachePatientResult coverage
EICU_MOCK_SINGLE_VERSION_RATE = 0.11       # stays with only one apacheversion row
EICU_MOCK_PRED_UNAVAILABLE_RATE = 0.09     # predictedhospitalmortality == '-1'
EICU_MOCK_RECENT_PID_POOL = 512            # bounded pool backing W14

# --- categorical level tuples ---------------------------------------------
# A deliberate, tested duplication of eicu_etl's EICU_LEVELS_*. Importing them
# would pull numpy into this stdlib-only module, so
# tests/test_eicu_path.py::test_mock_level_tuples_match_the_etl_tuples asserts
# the two copies are equal.
# The terminal "OTHER" entry is the ETL's drift bucket, never a raw value --
# this generator never emits it.

EICU_MOCK_LEVELS_GENDER = ("Female", "Male", "Other", "Unknown", "", "OTHER")
EICU_MOCK_LEVELS_ETHNICITY = ("African American", "Asian", "Caucasian", "Hispanic",
                              "Native American", "Other/Unknown", "", "OTHER")
EICU_MOCK_LEVELS_ADMITSOURCE = ("Acute Care/Floor", "Chest Pain Center", "Direct Admit",
                                "Emergency Department", "Floor", "ICU", "ICU to SDU",
                                "Observation", "Operating Room", "Other", "Other Hospital",
                                "Other ICU", "PACU", "Recovery Room",
                                "Step-Down Unit (SDU)", "", "OTHER")
EICU_MOCK_LEVELS_UNITTYPE = ("CCU-CTICU", "CSICU", "CTICU", "Cardiac ICU", "MICU",
                             "Med-Surg ICU", "Neuro ICU", "SICU", "", "OTHER")
EICU_MOCK_LEVELS_UNITSTAYTYPE = ("admit", "readmit", "stepdown/other", "transfer",
                                 "", "OTHER")

# Emission weights over the listed levels; the terminal "OTHER" is excluded,
# being the ETL's bucket rather than a value. Lengths are asserted at import.
_W_GENDER = (0.462, 0.531, 0.003, 0.002, 0.002)
_W_ETHNICITY = (0.108, 0.017, 0.774, 0.038, 0.007, 0.041, 0.015)
_W_ADMITSOURCE = (0.061, 0.004, 0.079, 0.397, 0.121, 0.028, 0.004, 0.012,
                  0.131, 0.017, 0.088, 0.021, 0.014, 0.006, 0.011, 0.006)
_W_UNITTYPE = (0.118, 0.041, 0.038, 0.086, 0.216, 0.351, 0.061, 0.086, 0.003)
_W_UNITSTAYTYPE = (0.884, 0.041, 0.032, 0.036, 0.007)

# W16 / --drift: values deliberately absent from the frozen tuples.
_UNLISTED_GENDER = ("Not Specified",)
_UNLISTED_ETHNICITY = ("Other",)
_UNLISTED_ADMITSOURCE = ("Home", "Nursing Home")
_UNLISTED_UNITTYPE = ("Cardiac Surgery ICU",)
_UNLISTED_UNITSTAYTYPE = ("stepdown",)
_DRIFT_GENDER = ("F", "M")

# --- latent-severity model --------------------------------------------------
# The intercept is derived from EICU_MOCK_BASE_RATE rather than pinned, so the
# advertised prevalence and the emitted prevalence cannot drift apart.
# The logistic-normal correction lambda = 1/sqrt(1 + pi*s^2/8) maps the
# marginal mean back onto the logit scale for s^2 = B^2 + sigma_u^2.
_SIGNAL_SD = math.sqrt(EICU_MOCK_SIGNAL_B ** 2 + EICU_MOCK_SITE_SIGMA_U ** 2)
_SIGNAL_LAMBDA = 1.0 / math.sqrt(1.0 + math.pi * _SIGNAL_SD ** 2 / 8.0)
EICU_MOCK_SIGNAL_INTERCEPT = (
    math.log(EICU_MOCK_BASE_RATE / (1.0 - EICU_MOCK_BASE_RATE)) / _SIGNAL_LAMBDA)

# How strongly each ALLOWED feature leaks z. No leak column carries a loading:
# the leaks are driven by the outcome directly, which is the point.
#
# Calibration note (measured, not guessed). EICU_MOCK_SIGNAL_B alone fixes the
# AUC ceiling -- a score that recovered z perfectly would reach
# Phi(B/sqrt(2)) = 0.73 at B = 0.85. The loadings decide only how much of that
# ceiling a head reaches, so severity sits in the drivers a clinician would
# name (GCS motor, mean BP, BUN, creatinine, respiratory rate, urine output,
# age) instead of spreading thin over twenty weak columns. Measured on the
# small arm: single-column AUC 0.62-0.63; head AUC 0.59 held out at 9 000
# stays, 0.66 once the split can fit 161 coefficients on more than ~270 events.
#
# Certification is not reachable at B = 0.85 at the two frozen corpus sizes.
# The walk needs the best margin max_tau cov*(alpha - risk) to clear
# certify.margin_floor(n_carrying, DELTA, alpha). An oracle ranking by true
# risk -- which no head can beat -- gives 0.0354 at alpha = 0.10, against a
# floor of 0.0428 at EICU_MOCK_SMALL_SITES = 180 (63 calibration clusters) and
# 0.0359 at EICU_MOCK_FULL_SITES = 208 (75). Both frozen arms therefore
# decline, and the default suite exercises the decline branch.
#
# Those two sizes are the whole of that claim. margin_floor scales as
# 1/n_carrying, so the floor drops below 0.0354 at n_carrying = 77
# (~217 hospitals), and a 900- or 1500-hospital mock certifies alpha = 0.10
# with this constant untouched -- which is what
# tests/test_eicu_path.py::test_large_mock_reaches_the_certified_branch
# (CERTGATE_EICU_LARGE=1, 900 hospitals) exercises. Raising EICU_MOCK_SIGNAL_B
# to 2.0 (synth_fixture.SIGNAL_B, matching certgate SimConfig.sep = 2.2) lifts
# the oracle margin to 0.0585 and would reach the certified branch at the
# frozen sizes too, but that is a SPEC + test_constants change.
#
# Ref: audit E-20 (2026-07-31).
EICU_MOCK_SIGNAL_LOAD = {
    "age": 15.0,                # years, on gauss(63, 16), clamped to [18, 89]
    "aps_urine": -1250.0,
    "aps_wbc": 6.0,
    "aps_temperature": -0.62,
    "aps_respiratoryrate": 9.0,
    "aps_sodium": 3.6,
    "aps_heartrate": 24.0,
    "aps_meanbp": -26.0,
    "aps_ph": -0.075,
    "aps_hematocrit": -4.5,
    "aps_creatinine": 1.50,
    "aps_albumin": -0.85,
    "aps_pao2": -24.0,
    "aps_pco2": 6.0,
    "aps_bun": 20.0,
    "aps_glucose": 40.0,
    "aps_bilirubin": 0.95,
    "aps_fio2": 0.115,
    "gcs": -1.50,               # GCS components fall as severity rises
    "aps_flag": 1.30,           # logit shift: intubated / vent / dialysis / meds
    "apv_flag": 0.90,           # logit shift: comorbidity + treatment flags
    "apv_ejectfx": -11.0,
    "comparator": 0.90,         # the APACHE-IVa prediction (a denylisted column)
}


# ---------------------------------------------------------------------------
# Schema -- verbatim DDL column names in verbatim DDL column order
# ---------------------------------------------------------------------------
# Source: MIT-LCP/eicu-code build-db/postgres/postgres_create_tables.sql.
# The surrogate id comes first in apacheapsvar / apachepredvar /
# apachepatientresult, and the eicu.mit.edu doc pages list a different order.
# The MIT-LCP \copy load is positional against the DDL, so addressing columns
# by position against the doc pages silently loads the wrong data.

EICU_MOCK_SCHEMA: dict[str, tuple[tuple[str, str], ...]] = {
    "patient": (
        ("patientunitstayid", "INT"),
        ("patienthealthsystemstayid", "INT"),
        ("gender", "VARCHAR(25)"),
        ("age", "VARCHAR(10)"),
        ("ethnicity", "VARCHAR(50)"),
        ("hospitalid", "INT"),
        ("wardid", "INT"),
        ("apacheadmissiondx", "VARCHAR(1000)"),
        ("admissionheight", "NUMERIC(10,2)"),
        ("hospitaladmittime24", "VARCHAR(8)"),
        ("hospitaladmitoffset", "INT"),
        ("hospitaladmitsource", "VARCHAR(30)"),
        ("hospitaldischargeyear", "SMALLINT"),
        ("hospitaldischargetime24", "VARCHAR(8)"),
        ("hospitaldischargeoffset", "INT"),
        ("hospitaldischargelocation", "VARCHAR(100)"),
        ("hospitaldischargestatus", "VARCHAR(10)"),
        ("unittype", "VARCHAR(50)"),
        ("unitadmittime24", "VARCHAR(8)"),
        ("unitadmitsource", "VARCHAR(100)"),
        ("unitvisitnumber", "INT"),
        ("unitstaytype", "VARCHAR(15)"),
        ("admissionweight", "NUMERIC(10,2)"),
        ("dischargeweight", "NUMERIC(10,2)"),
        ("unitdischargetime24", "VARCHAR(8)"),
        ("unitdischargeoffset", "INT"),
        ("unitdischargelocation", "VARCHAR(100)"),
        ("unitdischargestatus", "VARCHAR(10)"),
        ("uniquepid", "VARCHAR(10)"),
    ),
    "hospital": (
        ("hospitalid", "INT NOT NULL"),
        ("numbedscategory", "VARCHAR(32)"),
        ("teachingstatus", "BOOLEAN"),
        ("region", "VARCHAR(64)"),
    ),
    "apacheApsVar": (
        ("apacheapsvarid", "INT"),
        ("patientunitstayid", "INT"),
        ("intubated", "SMALLINT"),
        ("vent", "SMALLINT"),
        ("dialysis", "SMALLINT"),
        ("eyes", "SMALLINT"),
        ("motor", "SMALLINT"),
        ("verbal", "SMALLINT"),
        ("meds", "SMALLINT"),
        ("urine", "DOUBLE PRECISION"),
        ("wbc", "DOUBLE PRECISION"),
        ("temperature", "DOUBLE PRECISION"),
        ("respiratoryrate", "DOUBLE PRECISION"),
        ("sodium", "DOUBLE PRECISION"),
        ("heartrate", "DOUBLE PRECISION"),
        ("meanbp", "DOUBLE PRECISION"),
        ("ph", "DOUBLE PRECISION"),
        ("hematocrit", "DOUBLE PRECISION"),
        ("creatinine", "DOUBLE PRECISION"),
        ("albumin", "DOUBLE PRECISION"),
        ("pao2", "DOUBLE PRECISION"),
        ("pco2", "DOUBLE PRECISION"),
        ("bun", "DOUBLE PRECISION"),
        ("glucose", "DOUBLE PRECISION"),
        ("bilirubin", "DOUBLE PRECISION"),
        ("fio2", "DOUBLE PRECISION"),
    ),
    "apachePredVar": (
        ("apachepredvarid", "INT"),
        ("patientunitstayid", "INT"),
        ("sicuday", "SMALLINT"),
        ("saps3day1", "SMALLINT"),
        ("saps3today", "SMALLINT"),
        ("saps3yesterday", "SMALLINT"),
        ("gender", "SMALLINT"),
        ("teachtype", "SMALLINT"),
        ("region", "SMALLINT"),
        ("bedcount", "SMALLINT"),
        ("admitsource", "SMALLINT"),
        ("graftcount", "SMALLINT"),
        ("meds", "SMALLINT"),
        ("verbal", "SMALLINT"),
        ("motor", "SMALLINT"),
        ("eyes", "SMALLINT"),
        ("age", "SMALLINT"),
        ("admitdiagnosis", "VARCHAR(11)"),
        ("thrombolytics", "SMALLINT"),
        ("diedinhospital", "SMALLINT"),
        ("aids", "SMALLINT"),
        ("hepaticfailure", "SMALLINT"),
        ("lymphoma", "SMALLINT"),
        ("metastaticcancer", "SMALLINT"),
        ("leukemia", "SMALLINT"),
        ("immunosuppression", "SMALLINT"),
        ("cirrhosis", "SMALLINT"),
        ("electivesurgery", "SMALLINT"),
        ("activetx", "SMALLINT"),
        ("readmit", "SMALLINT"),
        ("ima", "SMALLINT"),
        ("midur", "SMALLINT"),
        ("ventday1", "SMALLINT"),
        ("oobventday1", "SMALLINT"),
        ("oobintubday1", "SMALLINT"),
        ("diabetes", "SMALLINT"),
        ("managementsystem", "SMALLINT"),
        ("var03hspxlos", "DOUBLE PRECISION"),
        ("pao2", "DOUBLE PRECISION"),
        ("fio2", "DOUBLE PRECISION"),
        ("ejectfx", "DOUBLE PRECISION"),
        ("creatinine", "DOUBLE PRECISION"),
        ("dischargelocation", "SMALLINT"),
        ("visitnumber", "SMALLINT"),
        ("amilocation", "SMALLINT"),
        ("day1meds", "SMALLINT"),
        ("day1verbal", "SMALLINT"),
        ("day1motor", "SMALLINT"),
        ("day1eyes", "SMALLINT"),
        ("day1pao2", "DOUBLE PRECISION"),
        ("day1fio2", "DOUBLE PRECISION"),
    ),
    "apachePatientResult": (
        ("apachepatientresultsid", "INT NOT NULL"),
        ("patientunitstayid", "INT NOT NULL"),
        ("physicianspeciality", "VARCHAR(50)"),
        ("physicianinterventioncategory", "VARCHAR(50)"),
        ("acutephysiologyscore", "INT"),
        ("apachescore", "INT"),
        ("apacheversion", "VARCHAR(5) NOT NULL"),
        ("predictedicumortality", "VARCHAR(50)"),
        ("actualicumortality", "VARCHAR(50)"),
        ("predictediculos", "DOUBLE PRECISION"),
        ("actualiculos", "DOUBLE PRECISION"),
        ("predictedhospitalmortality", "VARCHAR(50)"),
        ("actualhospitalmortality", "VARCHAR(50)"),
        ("predictedhospitallos", "DOUBLE PRECISION"),
        ("actualhospitallos", "DOUBLE PRECISION"),
        ("preopmi", "INT"),
        ("preopcardiaccath", "INT"),
        ("ptcawithin24h", "INT"),
        ("unabridgedunitlos", "DOUBLE PRECISION"),
        ("unabridgedhosplos", "DOUBLE PRECISION"),
        ("actualventdays", "DOUBLE PRECISION"),
        ("predventdays", "DOUBLE PRECISION"),
        ("unabridgedactualventdays", "DOUBLE PRECISION"),
    ),
}

# The allowlisted numeric blocks, in DDL order. Kept here (rather than imported)
# for the stdlib-only reason above; the ETL owns the authoritative tuples.
_APS_NUMERIC = tuple(c for c, _ in EICU_MOCK_SCHEMA["apacheApsVar"]
                     if c not in ("apacheapsvarid", "patientunitstayid"))
_APV_ALLOWED = ("graftcount", "thrombolytics", "aids", "hepaticfailure",
                "lymphoma", "metastaticcancer", "leukemia", "immunosuppression",
                "cirrhosis", "electivesurgery", "activetx", "readmit", "ima",
                "midur", "ventday1", "oobventday1", "oobintubday1", "diabetes",
                "ejectfx")


# ---------------------------------------------------------------------------
# Header rendering: camelCase from a frozen token vocabulary
# ---------------------------------------------------------------------------
# The released CSVs carry lowercase headers; a re-export may not. read_table
# lowercases whatever it reads, so both renderings must parse identically, and
# --header-case is the wart that proves it.
# The camel spelling is derived from a frozen token list, longest match from
# the left, and every schema column is checked at import. An unsplittable name
# is a defect in this vocabulary and raises here, not three tables later.

_CAMEL_TOKENS = (
    "acute", "active", "actual", "admission", "admit", "age", "aids", "albumin",
    "ami", "apache", "aps", "bed", "beds", "bilirubin", "bp", "bun", "cancer",
    "cardiac", "category", "cath", "cirrhosis", "count", "creatinine", "day",
    "day1", "days", "diabetes", "diagnosis", "dialysis", "died", "discharge",
    "dx", "eject", "elective", "ethnicity", "eyes", "failure", "fio2", "fx",
    "gender", "glucose", "graft", "health", "heart", "height", "hematocrit",
    "hepatic", "hosp", "hospital", "icu", "id", "ima", "immunosuppression",
    "in", "intervention", "intub", "intubated", "leukemia", "location", "los",
    "lymphoma", "management", "mean", "meds", "metastatic", "mi", "midur",
    "mortality", "motor", "num", "number", "oob", "offset", "pao2", "patient",
    "pco2", "pgender", "ph", "physician", "physiology", "pid", "pred",
    "predicted", "preop", "ptca", "rate", "readmit", "region", "respiratory",
    "result", "results", "saps3", "score", "sicu", "sodium", "source",
    "speciality", "status", "stay", "surgery", "system", "teach", "teaching",
    "temperature", "thrombolytics", "time24", "today", "tx", "type",
    "unabridged", "unique", "unit", "urine", "var", "var03hspxlos", "verbal",
    "vent", "version", "visit", "ward", "wbc", "weight", "within24h", "year",
    "yesterday",
)


def _split_tokens(name: str):
    """Greedy longest-match split of a DDL column name; None if unsplittable."""
    out, i = [], 0
    while i < len(name):
        best = ""
        for t in _CAMEL_TOKENS:
            if len(t) > len(best) and name.startswith(t, i):
                best = t
        if not best:
            return None
        out.append(best)
        i += len(best)
    return out


def _camel(name: str) -> str:
    """DDL column name -> its camelCase rendering; raises if unsplittable.

    'patientunitstayid' -> 'patientUnitStayId'.
    """
    toks = _split_tokens(name)
    if toks is None:
        raise ValueError(
            f"eicu_mock._camel: no token split for column, got {name!r} "
            f"(reason=mock-camel-vocabulary)")
    return toks[0] + "".join(t[:1].upper() + t[1:] for t in toks[1:])


EICU_MOCK_CAMEL: dict[str, str] = {
    col: _camel(col)
    for cols in EICU_MOCK_SCHEMA.values() for col, _ in cols
}

assert len(EICU_MOCK_LEVELS_GENDER) - 1 == len(_W_GENDER)
assert len(EICU_MOCK_LEVELS_ETHNICITY) - 1 == len(_W_ETHNICITY)
assert len(EICU_MOCK_LEVELS_ADMITSOURCE) - 1 == len(_W_ADMITSOURCE)
assert len(EICU_MOCK_LEVELS_UNITTYPE) - 1 == len(_W_UNITTYPE)
assert len(EICU_MOCK_LEVELS_UNITSTAYTYPE) - 1 == len(_W_UNITSTAYTYPE)


# ---------------------------------------------------------------------------
# Vocabularies
# ---------------------------------------------------------------------------

# W8: apacheadmissiondx is high-cardinality free text whose real values carry
# commas and parentheses, and eICU renders some as pipe-delimited paths.
ADMIT_DX = (
    "Sepsis, pulmonary",
    "Sepsis, renal/UTI (including bladder infection)",
    "Rhythm disturbance (atrial, supraventricular)",
    "CVA, cerebrovascular accident/stroke",
    "Diabetic ketoacidosis",
    "Overdose, sedatives, hypnotics, antipsychotics, benzos",
    "CHF, congestive heart failure",
    "Pneumonia, bacterial",
    "GI bleeding, upper",
    "Cardiovascular|Chest Pain|Unstable Angina",
    "Neurologic|Altered mental status|Encephalopathy",
    "Pulmonary|Respiratory failure|Acute",
    "Renal|Acute kidney injury|Sepsis-associated",
    "",
)
DISCHARGE_LOCATION = ("Home", "Skilled Nursing Facility", "Rehabilitation",
                      "Other Hospital", "Nursing Home", "Other External", "")
DEATH_LOCATION = "Death"
UNIT_DISCHARGE_LOCATION = ("Floor", "Step-Down Unit (SDU)", "Home",
                          "Other ICU", "Telemetry", "Acute Care/Floor", "")
PHYSICIAN_SPECIALITY = (
    "critical care medicine (CCM)", "internal medicine", "pulmonology",
    "surgery-critical care", "cardiology", "anesthesiology",
    "family practice", "hospitalist", "",
)
PHYSICIAN_INTERVENTION = ("No Intervention", "Critical Care", "Monitoring",
                          "Complex Care", "")
# W13: both bed-band spellings, mixed across rows.
BED_BANDS_A = ("<100", "100 - 249", "250 - 499", ">= 500", "")
BED_BANDS_B = ("<100", "100 - 249", "250-500", ">500", "")
REGIONS = ("Midwest", "Northeast", "South", "West", "")
APACHE_VERSIONS = ("IV", "IVa")

# W8: values engineered to break a naive line-based reader.
NASTY_TEXT = (
    "value, with comma",
    'value "with quotes"',
    "value\nwith newline",
    "value\r\nwith crlf",
    "  leading and trailing  ",
    "",
)


@dataclass
class MockConfig:
    stays: int = EICU_MOCK_SMALL_STAYS
    sites: int = EICU_MOCK_SMALL_SITES
    seed: int = EICU_MOCK_SEED
    out: str = "./eicu-mock"
    compresslevel: int = 6
    header_case: str = "camel"          # in EICU_MOCK_HEADER_CASES
    tables: list[str] = field(default_factory=lambda: list(EICU_MOCK_TABLES))
    signal: bool = True                 # on by default (see module docstring)
    warts: bool = True
    site_sigma: float = EICU_MOCK_SITE_SIGMA
    drift: bool = False                 # push one categorical past the cap
    emit_ddl: bool = False


# ---------------------------------------------------------------------------
# Value helpers
# ---------------------------------------------------------------------------
# _num/_integer/_hhmmss below, and make_counter/TableWriter/NullWriter further
# down, are duplicated from synth_fixture by design -- eicu_mock is
# stdlib-only (test_etl_imports_no_undeclared_dependency).

def _num(value, dp: int) -> str:
    """Fixed-point render; None becomes an empty field (a CSV NULL)."""
    if value is None:
        return ""
    return f"{value:.{dp}f}"


def _integer(value) -> str:
    return "" if value is None else str(int(value))


def _sigmoid(x: float) -> float:
    if x >= 0.0:
        return 1.0 / (1.0 + math.exp(-min(x, 60.0)))
    e = math.exp(max(x, -60.0))
    return e / (1.0 + e)


def _hhmmss(rng: random.Random) -> str:
    """Wall-clock-of-day as VARCHAR(8), deliberately unlinked from the offsets."""
    return f"{rng.randrange(24):02d}:{rng.randrange(60):02d}:{rng.randrange(60):02d}"


def _weighted(rng: random.Random, values, weights):
    """Deterministic weighted choice, consuming exactly one draw."""
    r = rng.random() * sum(weights)
    acc = 0.0
    for v, w in zip(values, weights):
        acc += w
        if r < acc:
            return v
    return values[-1]


def _level(rng: random.Random, cfg: MockConfig, levels, weights,
           unlisted, drifted: bool) -> str:
    """One categorical value.

    Always draws exactly three numbers, so --no-warts and --drift change the
    value, never the stream position. levels excludes the terminal "OTHER"
    bucket, which belongs to the ETL and is not a datum.
    """
    r_un = rng.random()
    pick_un = rng.randrange(0, 64)
    listed = _weighted(rng, levels[:-1], weights)
    if not cfg.warts:
        return listed
    rate = EICU_MOCK_DRIFT_RATE if (drifted and cfg.drift) else EICU_MOCK_UNLISTED_RATE
    if r_un < rate:
        return unlisted[pick_un % len(unlisted)]
    return listed


def _dirty(rng: random.Random, cfg: MockConfig, clean: str) -> str:
    """W8: occasionally swap in a value engineered to break a naive CSV reader."""
    r = rng.random()
    pick = rng.randrange(0, 64)
    if cfg.warts and r < EICU_MOCK_DIRTY_RATE:
        return NASTY_TEXT[pick % len(NASTY_TEXT)]
    return clean


def _heavy_tail(rng: random.Random, mean: float, sigma: float = 1.0) -> float:
    """Lognormal draw with the requested arithmetic mean."""
    mu = math.log(mean) - (sigma ** 2) / 2.0
    return rng.lognormvariate(mu, sigma)


def make_counter(start: int = 1):
    box = [start]

    def nxt() -> int:
        v = box[0]
        box[0] += 1
        return v

    return nxt


# ---------------------------------------------------------------------------
# Writer -- byte-determinism contract, identical to synth_fixture.TableWriter
# ---------------------------------------------------------------------------

class TableWriter:
    """Streaming gzip CSV writer for one table, counting rows as it goes.

    mtime=0 and filename="" freeze the gzip header, so "same seed + same args =
    byte-identical output" holds for the .csv.gz bytes themselves, not just
    their decompressed content. gzip.open would stamp wall-clock mtime into
    header bytes 4:8 and silently break that.

    newline="" lets csv.writer own the line endings.
    """

    def __init__(self, path: str, columns: list[str], compresslevel: int,
                 encoding: str = "utf-8"):
        self.path = path
        self.columns = columns
        self.rows = 0
        self._raw = open(path, "wb")
        gz = gzip.GzipFile(filename="", mode="wb", fileobj=self._raw,
                           compresslevel=compresslevel, mtime=0)
        self._fh = io.TextIOWrapper(gz, encoding=encoding, newline="")
        self._w = csv.writer(self._fh, quoting=csv.QUOTE_MINIMAL)
        self._w.writerow(columns)

    def write(self, row: list) -> None:
        self._w.writerow(row)
        self.rows += 1

    def close(self) -> None:
        self._fh.close()      # flushes the TextIOWrapper and closes the GzipFile
        self._raw.close()     # GzipFile(fileobj=...) never closes the fileobj


class NullWriter:
    """Stands in for an excluded table; write/close are no-ops."""

    rows = 0

    def write(self, row) -> None:  # noqa: D102
        pass

    def close(self) -> None:  # noqa: D102
        pass


# ---------------------------------------------------------------------------
# Site plan: ids, heavy-tailed weights, APACHE coverage bands
# ---------------------------------------------------------------------------

def _hospital_ids(rng: random.Random, n_sites: int) -> list[int]:
    """Strictly increasing, non-contiguous hospitalids, as in eICU (59, 73...).

    The ETL's hosp-{int(hospitalid)} canonicalisation makes the gaps harmless.
    """
    ids, hid = [], 0
    for _ in range(n_sites):
        hid += rng.randrange(1, 6)
        ids.append(hid)
    return ids


def _site_weights(seed: int, n_sites: int, sigma: float) -> list[float]:
    """W9: lognormal site weights, drawn from a dedicated stream.

    sigma == 0 restores uniform site sizes exactly.
    """
    if sigma <= 0.0:
        return [1.0] * n_sites
    wrng = random.Random(f"{seed}:site-weights")
    return [wrng.lognormvariate(0.0, sigma) for _ in range(n_sites)]


def _site_quotas(weights: list[float], total: int, floor_: int) -> list[int]:
    """Per-site stay quotas: a hard floor plus a weight-proportional remainder.

    The leftover goes to the largest fractional parts, deterministically. That
    floor makes EICU_MOCK_SMALL_SITES = 180 yield 63 record-carrying
    calibration clusters every time. MIN_CAL_CLUSTERS = 50 counts carrying
    clusters, and an empty hospital is not one.
    """
    n = len(weights)
    base = floor_ * n
    if total < base:
        raise ValueError(
            f"eicu_mock._site_quotas: {n} sites at a floor of {floor_} stays "
            f"each need {base} stays, got {total} (reason=mock-too-few-stays)")
    rest = total - base
    w_sum = sum(weights)
    exact = [rest * w / w_sum for w in weights]
    q = [int(e) for e in exact]
    left = rest - sum(q)
    order = sorted(range(n), key=lambda i: (-(exact[i] - q[i]), i))
    for i in order[:left]:
        q[i] += 1
    return [floor_ + qi for qi in q]


def _site_apache(seed: int, n_sites: int) -> list[dict]:
    """W6 / T-3: the per-site APACHE coverage plan.

    Coverage band, zero-result flag and sentinel modulation, all drawn from the
    dedicated apache-coverage stream. Site-correlated absence is the dataset
    authors' own finding ("reliability and completion of data elements varies
    on a hospital and/or ICU level"), and a real covariate-shift channel that
    CertGate v2 scope-cut.

    The mock plants it so preflight can measure it -- sentinel_site_dispersion,
    apache_coverage_by_site -- instead of the pipeline imputing it away.
    """
    rng = random.Random(f"{seed}:apache-coverage")
    cum, acc = [], 0.0
    for share, cov in EICU_MOCK_APS_SITE_BANDS:
        acc += share
        cum.append((acc, cov))
    total_share = acc
    out = []
    for _ in range(n_sites):
        r = rng.random() * total_share
        cov = cum[-1][1]
        band = len(cum) - 1
        for bi, (edge, c) in enumerate(cum):
            if r < edge:
                cov, band = c, bi
                break
        zero_result = rng.random() < EICU_MOCK_RESULT_ZERO_SITE_SHARE
        p_result = rng.uniform(*EICU_MOCK_RESULT_COVERAGE)
        sentinel_mult = min(2.5, max(0.25, math.exp(rng.gauss(0.0, 0.55))))
        out.append(dict(band=band, aps_coverage=cov, zero_result=zero_result,
                        result_coverage=0.0 if zero_result else p_result,
                        sentinel_rate=min(0.75, EICU_MOCK_SENTINEL_RATE * sentinel_mult)))
    return out


# ---------------------------------------------------------------------------
# The plan: patients -> hospital admissions -> unit stays
# ---------------------------------------------------------------------------

def plan_stays(rng: random.Random, cfg: MockConfig, hospitals: list[int],
               quotas: list[int], site_apache: list[dict], u_site: dict):
    """Yield one dict per unit stay, lazily, so memory stays flat at any scale.

    Signal draws use the dedicated `signal:` / `signal-site:` streams, so
    --no-signal changes values, never stream positions (synth_fixture's rule).

    Every structural decision is made here: site, admission, visit number,
    offsets, APACHE presence. The plan always runs in full regardless of
    --tables, which is what makes a --tables subset an identical projection.
    """
    stayid = 141_168            # ids start in a plausible band, not at 1
    hsid = 200_000
    pid_ord = 0
    recent_pids: list[str] = []
    planted_offsets = False
    emitted = 0

    for si, hid in enumerate(hospitals):
        cov = site_apache[si]
        remaining = quotas[si]
        while remaining > 0:
            pid_ord += 1
            own_pid = f"{(pid_ord // 100000) % 1000:03d}-{pid_ord % 100000:05d}"
            r_cross = rng.random()
            pick = rng.randrange(0, 4096)
            # W14: a uniquepid that already appeared at another hospitalid.
            # assert_site_disjoint compares site labels and cannot see this.
            # The preflight measures it and the protocol discloses it (T-5).
            if recent_pids and r_cross < EICU_MOCK_CROSS_SITE_PID_RATE:
                pid = recent_pids[pick % len(recent_pids)]
            else:
                pid = own_pid
            recent_pids.append(own_pid)
            if len(recent_pids) > EICU_MOCK_RECENT_PID_POOL:
                recent_pids.pop(0)

            n_admissions = 1 if rng.random() < 0.88 else 2
            for _ in range(n_admissions):
                if remaining <= 0:
                    break
                hsid += rng.randrange(1, 40)
                # W7: several unit stays per hospital admission.
                n_stays = 1
                if rng.random() < EICU_MOCK_MULTISTAY_RATE:
                    n_stays = 2 if rng.random() < 0.82 else 3
                # W7: unitvisitnumber does not always start at 1.
                visit0 = 1 if rng.random() < 0.97 else rng.randrange(2, 4)
                # Pre-ICU minutes: the gap between hospital and unit admission.
                # A direct ICU admission gives offset exactly 0; a long ward
                # stay before the ICU pushes it past EICU_WINDOW_PRE_ICU_HRS.
                # Both edges of the ETL's plausibility window must be populated
                # or the window branch is never exercised.
                r_gap = rng.random()
                gap0 = int(_heavy_tail(rng, 340.0, 1.25))
                long_gap = rng.randrange(0, 46000)
                if r_gap < 0.055:
                    gap0 = 0
                elif r_gap < 0.072:
                    gap0 += 43200 + long_gap
                plant = (cfg.warts and not planted_offsets and n_stays >= 2
                         and remaining >= 2)
                if plant:
                    planted_offsets = True

                offset = -gap0
                for k in range(n_stays):
                    if remaining <= 0:
                        break
                    stayid += rng.randrange(1, 30)
                    # 335 units across 208 hospitals: ~1.6 wards per hospital.
                    # wardid is denylisted as a feature: it is the same site
                    # identity one level down (protocol A.4).
                    ward = hid * 100 + rng.randrange(1, 3)
                    los = int(_heavy_tail(rng, 2100.0, 0.95))     # unit LOS, minutes
                    inter = rng.randrange(30, 2600)               # ward time between stays
                    ward_extra = int(_heavy_tail(rng, 3600.0, 1.05))
                    r_aps = rng.random()
                    r_flip = rng.random()
                    r_result = rng.random()

                    if cfg.signal:
                        srng = random.Random(f"{cfg.seed}:signal:{stayid}")
                        z = srng.gauss(0.0, 1.0)
                        logit = (EICU_MOCK_SIGNAL_INTERCEPT
                                 + EICU_MOCK_SIGNAL_B * z + u_site[hid])
                        y = srng.random() < _sigmoid(logit)
                    else:
                        srng = random.Random(f"{cfg.seed}:signal:{stayid}")
                        srng.gauss(0.0, 1.0)                       # same positions
                        z = 0.0
                        y = srng.random() < EICU_MOCK_BASE_RATE

                    aps_present = r_aps < cov["aps_coverage"]
                    # apachePredVar tracks apacheApsVar almost exactly -- the
                    # data paper reports 0.00% of hospitals lacking either.
                    # A thin disagreement keeps both presence flags useful.
                    apv_present = aps_present if r_flip > 0.03 else not aps_present
                    result_present = r_result < cov["result_coverage"]

                    visit = visit0 + k
                    stay_offset = offset
                    if plant and k < 2:
                        # W7 (planted): equal unitvisitnumber, offsets -14/-22.
                        # argmin(unitvisitnumber) ties, so the max-offset
                        # tie-break decides -- and must pick -14.
                        visit = visit0
                        stay_offset = -14 if k == 0 else -22

                    yield dict(
                        stayid=stayid, hsid=hsid, pid=pid, hid=hid, ward=ward,
                        site_index=si, visit=visit, admit_offset=stay_offset,
                        los=los, ward_extra=ward_extra,
                        aps_present=aps_present, apv_present=apv_present,
                        result_present=result_present,
                        z=z, y=y, planted=plant and k < 2,
                    )
                    emitted += 1
                    remaining -= 1
                    offset -= (los + inter)


# ---------------------------------------------------------------------------
# Row builders
# ---------------------------------------------------------------------------

def build_hospital_row(rng: random.Random, cfg: MockConfig, hid: int) -> list:
    """W13: blank bands and regions, and two spellings of everything else.

    teachingstatus appears in both renderings, and both bed-band spellings are
    mixed across rows. preflight reads these literals rather than hard-coding
    them -- the only honest way to report a vocabulary nobody has seen yet.
    """
    band_a = rng.choice(BED_BANDS_A)
    band_b = rng.choice(BED_BANDS_B)
    r_spell = rng.random()
    teach = rng.random() < 0.28
    r_render = rng.random()
    region = rng.choice(REGIONS)
    if cfg.warts:
        beds = band_b if r_spell < 0.35 else band_a
        status = ("t" if teach else "f") if r_render < 0.30 else ("True" if teach else "False")
    else:
        beds = band_a
        status = "True" if teach else "False"
    return [hid, beds, status, region]


def build_patient_row(rng: random.Random, cfg: MockConfig, s: dict) -> list:
    """The cohort spine, the label, the site key and the admission-time features.

    Every allowed feature here is a noisy view of the latent severity z. Every
    leak column -- hospitaldischargelocation, unitdischargestatus, the two
    discharge offsets, dischargeweight -- is driven by the outcome on purpose,
    so assert_no_leak_columns has something real to exclude.
    """
    z = s["z"]
    y = s["y"]

    # --- age (W1): '> 89' is kept by the protocol, not dropped -------------
    r_age = rng.random()
    age_num = rng.gauss(63.0 + EICU_MOCK_SIGNAL_LOAD["age"] * z, 16.0)
    ped_age = rng.randrange(15, 18)
    r_ped = rng.random()
    if r_age < EICU_MOCK_AGE_MASK_RATE:
        age = "> 89"
    elif r_age < EICU_MOCK_AGE_MASK_RATE + EICU_MOCK_AGE_BLANK_RATE:
        age = ""
    elif r_ped < EICU_MOCK_PEDIATRIC_RATE:
        age = str(ped_age)                       # S3's adult gate has work to do
    else:
        age = str(int(min(89.0, max(18.0, age_num))))

    gender = _level(rng, cfg, EICU_MOCK_LEVELS_GENDER, _W_GENDER,
                    _UNLISTED_GENDER if not cfg.drift else _DRIFT_GENDER, True)
    ethnicity = _level(rng, cfg, EICU_MOCK_LEVELS_ETHNICITY, _W_ETHNICITY,
                       _UNLISTED_ETHNICITY, False)
    hadmitsrc = _level(rng, cfg, EICU_MOCK_LEVELS_ADMITSOURCE, _W_ADMITSOURCE,
                       _UNLISTED_ADMITSOURCE, False)
    uadmitsrc = _level(rng, cfg, EICU_MOCK_LEVELS_ADMITSOURCE, _W_ADMITSOURCE,
                       _UNLISTED_ADMITSOURCE, False)
    unittype = _level(rng, cfg, EICU_MOCK_LEVELS_UNITTYPE, _W_UNITTYPE,
                      _UNLISTED_UNITTYPE, False)
    staytype = _level(rng, cfg, EICU_MOCK_LEVELS_UNITSTAYTYPE, _W_UNITSTAYTYPE,
                      _UNLISTED_UNITSTAYTYPE, False)

    # --- height / weight (W10): the missing encoding here is 0, NOT -1 ------
    h_raw = rng.gauss(169.0, 11.0)
    w_raw = max(30.0, rng.gauss(84.0 - 1.5 * z, 26.0))
    r_h, r_w = rng.random(), rng.random()
    r_hbad, r_wbad = rng.random(), rng.random()
    if r_h < 0.075:
        height = "0"
    elif cfg.warts and r_hbad < 0.004:
        height = _num(h_raw * 3.6, 2)            # decimal-point error: 612.6 cm
    else:
        height = _num(h_raw, 2)
    if r_w < 0.045:
        weight = "0"
    elif cfg.warts and r_wbad < 0.004:
        weight = _num(w_raw * 6.4, 2)            # decimal-point error: 544.00 kg
    else:
        weight = _num(w_raw, 2)

    # --- the outcome (W2) --------------------------------------------------
    r_status = rng.random()
    if r_status < EICU_MOCK_STATUS_MISSING_RATE:
        status = ""                              # no usable outcome: S2 drops it
    else:
        status = "Expired" if y else "Alive"
    icu_death = y and rng.random() < EICU_MOCK_ICU_DEATH_SHARE

    # --- leak columns, correlated with the outcome on purpose --------------
    unit_los = max(30, int(s["los"] * (0.62 if y else 1.0)))
    hosp_los = unit_los + max(0, int(s["ward_extra"] * (0.45 if y else 1.0)))
    disch_loc = (DEATH_LOCATION if (y and status == "Expired")
                 else rng.choice(DISCHARGE_LOCATION))
    unit_loc = DEATH_LOCATION if icu_death else rng.choice(UNIT_DISCHARGE_LOCATION)
    unit_status = "Expired" if icu_death else ("Alive" if status else "")
    disch_weight = "" if rng.random() < 0.62 else _num(max(30.0, w_raw - 1.8), 2)

    return [
        s["stayid"],
        s["hsid"],
        gender,
        age,
        ethnicity,
        s["hid"],                                        # site -- denylisted as a feature
        s["ward"],                                       # denylisted as a feature
        _dirty(rng, cfg, rng.choice(ADMIT_DX)),          # W8
        height,
        _hhmmss(rng),
        s["admit_offset"],                               # W7: negative minutes
        hadmitsrc,
        rng.choice((2014, 2015)),
        _hhmmss(rng),
        hosp_los,                                        # LEAK: post-hoc LOS
        _dirty(rng, cfg, disch_loc),                     # LEAK: 'Death'
        status,                                          # the label
        unittype,
        _hhmmss(rng),
        uadmitsrc,
        s["visit"],
        staytype,
        weight,
        disch_weight,                                    # LEAK: measured at discharge
        _hhmmss(rng),
        unit_los,                                        # LEAK: post-hoc ICU LOS
        unit_loc,                                        # LEAK
        unit_status,                                     # LEAK: ICU mortality
        s["pid"],
    ]


# --- apacheApsVar -----------------------------------------------------------
# (mean, sd, load-key, floor, decimals) for the plain gaussian columns. The
# ordinal, binary and unit-ambiguous columns are handled by name instead.
_APS_GAUSS = {
    "urine": (2600.0, 900.0, "aps_urine", 0.0, 0),
    "wbc": (11.2, 5.5, "aps_wbc", 0.1, 1),
    "respiratoryrate": (19.0, 6.0, "aps_respiratoryrate", 0.0, 0),
    "sodium": (138.0, 5.0, "aps_sodium", 0.0, 0),
    "heartrate": (88.0, 19.0, "aps_heartrate", 0.0, 0),
    "meanbp": (88.0, 18.0, "aps_meanbp", 0.0, 0),
    "ph": (7.37, 0.08, "aps_ph", 0.0, 2),
    "hematocrit": (33.0, 6.0, "aps_hematocrit", 0.0, 1),
    "creatinine": (1.35, 0.95, "aps_creatinine", 0.0, 2),
    "albumin": (3.10, 0.60, "aps_albumin", 0.0, 1),
    "pao2": (92.0, 28.0, "aps_pao2", 0.0, 0),
    "pco2": (41.0, 9.0, "aps_pco2", 0.0, 0),
    "bun": (24.0, 13.0, "aps_bun", 0.0, 0),
    "glucose": (145.0, 55.0, "aps_glucose", 0.0, 0),
    "bilirubin": (1.0, 1.1, "aps_bilirubin", 0.0, 1),
}
# (top, base, spread): Glasgow components. Lower is worse, so the load is
# applied with a negative sign through EICU_MOCK_SIGNAL_LOAD["gcs"].
_APS_ORDINAL = {"eyes": (4, 3.6, 0.75), "motor": (6, 5.4, 1.10),
                "verbal": (5, 4.2, 1.20)}
# base logit for the 0/1 columns
_APS_BINARY = {"intubated": -1.75, "vent": -1.35, "dialysis": -3.1, "meds": -2.4}


def _aps_value(rng: random.Random, col: str, z: float, warts: bool) -> str:
    """One apacheApsVar cell, before the sentinel/empty injection.

    Every allowlisted column has non-negative physiological support. The ETL
    treats any negative other than exactly -1.0 as an unrecognised sentinel and
    aborts (reason=unexpected-negative-sentinel, T-2). So this generator must
    never emit a negative that is not the sentinel itself.

    Draws are position-identical whether or not warts is set: W11's unit
    conventions change the emitted value, never the stream.
    """
    if col in _APS_BINARY:
        p = _sigmoid(_APS_BINARY[col] + EICU_MOCK_SIGNAL_LOAD["aps_flag"] * z)
        return "1" if rng.random() < p else "0"
    if col in _APS_ORDINAL:
        top, base, spread = _APS_ORDINAL[col]
        v = rng.gauss(base + EICU_MOCK_SIGNAL_LOAD["gcs"] * z, spread)
        return str(int(min(top, max(1, round(v)))))
    if col == "temperature":
        v = rng.gauss(36.9 + EICU_MOCK_SIGNAL_LOAD["aps_temperature"] * z, 0.9)
        v = min(41.5, max(33.0, v))
        r = rng.random()
        if warts and r < 0.06:           # W11: Fahrenheit contamination
            return _num(v * 9.0 / 5.0 + 32.0, 1)
        if warts and r < 0.075:          # outside BOTH windows -> missing
            return "0.0"
        return _num(v, 1)
    if col == "fio2":
        v = rng.gauss(0.42 + EICU_MOCK_SIGNAL_LOAD["aps_fio2"] * z, 0.16)
        v = min(1.0, max(0.22, v))
        r = rng.random()
        if warts and r < 0.42:           # W11: the percent convention
            return _num(v * 100.0, 1)
        if warts and r < 0.45:           # outside both windows -> missing
            return _num(v * 0.35, 2)
        return _num(v, 2)
    mean, sd, key, floor_, dp = _APS_GAUSS[col]
    v = rng.gauss(mean + EICU_MOCK_SIGNAL_LOAD[key] * z, sd)
    return _num(max(floor_, v), dp)


def build_aps_row(rng: random.Random, cfg: MockConfig, s: dict, next_id,
                  sentinel_rate: float, plant: int) -> list:
    """One apacheApsVar row.

    plant is 0 for the all-'-1' row, 1 for the all-'' row (tests 8 and 9), -1
    otherwise. Cells are drawn first and then overridden, so plants cost no
    stream position.
    """
    cells = []
    for col in _APS_NUMERIC:
        raw = _aps_value(rng, col, s["z"], cfg.warts)
        r = rng.random()
        if plant == 0:
            cells.append("-1")                       # W3, planted
        elif plant == 1:
            cells.append("")                         # W4, planted
        elif r < sentinel_rate:
            cells.append("-1")                       # W3: the undocumented sentinel
        elif r < sentinel_rate + EICU_MOCK_EMPTY_RATE:
            cells.append("")                         # W4: the documented SQL NULL
        else:
            cells.append(raw)
    return [next_id(), s["stayid"]] + cells


# --- apachePredVar ----------------------------------------------------------
# base logit for the allowlisted 0/1 comorbidity/treatment flags
_APV_BINARY = {
    "thrombolytics": -4.5, "aids": -5.5, "hepaticfailure": -4.2,
    "lymphoma": -5.0, "metastaticcancer": -3.6, "leukemia": -5.2,
    "immunosuppression": -3.4, "cirrhosis": -4.0, "electivesurgery": -1.6,
    "activetx": 0.9, "readmit": -2.2, "ima": -4.8, "midur": -4.6,
    "ventday1": -1.9, "oobventday1": -2.1, "oobintubday1": -2.3,
    "diabetes": -1.3,
}
# Flags whose direction is protective (elective surgery, an arterial graft).
_APV_PROTECTIVE = ("electivesurgery", "ima")


def _apv_allowed_value(rng: random.Random, col: str, z: float) -> str:
    """One allowlisted apachePredVar cell, before sentinel injection.

    Non-negative support, for the same reason as _aps_value.
    """
    if col == "graftcount":
        return str(0 if rng.random() < 0.94 else rng.randrange(1, 6))
    if col == "ejectfx":
        v = rng.gauss(52.0 + EICU_MOCK_SIGNAL_LOAD["apv_ejectfx"] * z, 12.0)
        return _num(min(80.0, max(5.0, v)), 0)
    load = EICU_MOCK_SIGNAL_LOAD["apv_flag"]
    if col in _APV_PROTECTIVE:
        load = -load
    p = _sigmoid(_APV_BINARY[col] + load * z)
    return "1" if rng.random() < p else "0"


def build_apv_row(rng: random.Random, cfg: MockConfig, s: dict, next_id,
                  sentinel_rate: float) -> list:
    """One apachePredVar row.

    The columns the protocol excludes are emitted with their documented
    content. The "set to default value" / "Not used" / XXX constants really are
    constant: sicuday, saps3*, teachtype, region, bedcount, managementsystem,
    var03hspxlos. gender, age, verbal, motor, eyes, meds, creatinine, pao2 and
    fio2 really are duplicates of patient / apacheApsVar.

    diedinhospital is the outcome as an integer -- the corpus's most dangerous
    leak, and why assert_no_leak_columns is a test rather than a comment.
    """
    z, y = s["z"], s["y"]
    cells: dict[str, str] = {}
    for col, _t in EICU_MOCK_SCHEMA["apachePredVar"]:
        if col in ("apachepredvarid", "patientunitstayid"):
            continue
        if col in _APV_ALLOWED:
            raw = _apv_allowed_value(rng, col, z)
            r = rng.random()
            if r < sentinel_rate:
                cells[col] = "-1"
            elif r < sentinel_rate + EICU_MOCK_EMPTY_RATE:
                cells[col] = ""
            else:
                cells[col] = raw
            continue
        # --- excluded columns ---------------------------------------------
        if col in ("sicuday", "saps3day1", "saps3today", "saps3yesterday",
                   "teachtype", "region", "bedcount", "managementsystem"):
            cells[col] = "-1"                       # documented constants
        elif col == "var03hspxlos":
            cells[col] = "-1"                       # "Not used"
        elif col == "diedinhospital":
            cells[col] = "1" if y else "0"          # LEAK: the outcome
        elif col == "dischargelocation":
            cells[col] = "2" if y else str(rng.randrange(1, 8))   # LEAK
        elif col == "gender":
            cells[col] = str(rng.randrange(0, 2))
        elif col == "age":
            cells[col] = str(int(min(90, max(16, rng.gauss(
                63.0 + EICU_MOCK_SIGNAL_LOAD["age"] * z, 16.0)))))
        elif col in ("verbal", "day1verbal"):
            cells[col] = _aps_value(rng, "verbal", z, cfg.warts)
        elif col in ("motor", "day1motor"):
            cells[col] = _aps_value(rng, "motor", z, cfg.warts)
        elif col in ("eyes", "day1eyes"):
            cells[col] = _aps_value(rng, "eyes", z, cfg.warts)
        elif col in ("meds", "day1meds"):
            cells[col] = _aps_value(rng, "meds", z, cfg.warts)
        elif col in ("pao2", "day1pao2"):
            cells[col] = _aps_value(rng, "pao2", z, cfg.warts)
        elif col in ("fio2", "day1fio2"):
            cells[col] = _aps_value(rng, "fio2", z, cfg.warts)
        elif col == "creatinine":
            cells[col] = _aps_value(rng, "creatinine", z, cfg.warts)
        elif col == "admitdiagnosis":
            cells[col] = str(rng.randrange(100, 1900))
        elif col in ("visitnumber",):
            cells[col] = str(s["visit"])
        elif col in ("admitsource", "amilocation"):
            cells[col] = str(rng.randrange(0, 8))
    ordered = [cells[c] for c, _ in EICU_MOCK_SCHEMA["apachePredVar"]
               if c not in ("apachepredvarid", "patientunitstayid")]
    return [next_id(), s["stayid"]] + ordered


# --- apachePatientResult ----------------------------------------------------

def build_result_rows(rng: random.Random, cfg: MockConfig, s: dict, next_id):
    """W5 / T-8 / T-9: one row per apacheversion, usually 'IV' and 'IVa' both.

    predictedhospitalmortality is VARCHAR(50) holding a probability, with '-1'
    for unavailable. Comparing it as a string ('-1' > '0' lexically) is the
    silent way to get the comparator wrong, so the ETL must float() first.

    Nothing in this table may become a feature. 8.65% of hospitals have zero
    rows here, so any feature drawn from it is either a site-restricted cohort
    or a perfect site indicator (protocol A.6).
    """
    z, y = s["z"], s["y"]
    single = rng.random() < EICU_MOCK_SINGLE_VERSION_RATE
    only = APACHE_VERSIONS[rng.randrange(0, 2)]
    versions = (only,) if single else APACHE_VERSIONS
    icu_death = y and rng.random() < EICU_MOCK_ICU_DEATH_SHARE
    aps_score = int(min(160, max(0, rng.gauss(46.0 + 14.0 * z, 18.0))))
    speciality = _dirty(rng, cfg, rng.choice(PHYSICIAN_SPECIALITY))     # W8
    intervention = rng.choice(PHYSICIAN_INTERVENTION)
    for ver in versions:
        bump = 3 if ver == "IVa" else 0
        p_h = _sigmoid(EICU_MOCK_SIGNAL_INTERCEPT
                       + EICU_MOCK_SIGNAL_LOAD["comparator"] * z
                       + rng.gauss(0.0, 0.45))
        p_i = p_h * 0.72
        unavailable = rng.random() < EICU_MOCK_PRED_UNAVAILABLE_RATE
        icu_los = s["los"] / 1440.0
        hosp_los = (s["los"] + s["ward_extra"]) / 1440.0
        vent_days = 0.0 if rng.random() < 0.62 else max(0.0, rng.gauss(2.6, 2.2))
        yield [
            next_id(),
            s["stayid"],
            speciality,
            intervention,
            aps_score,                                   # APACHE-III APS, denylisted
            aps_score + bump + rng.randrange(0, 30),     # APACHE-III score, denylisted
            ver,
            "-1" if unavailable else repr(p_i),          # string probability
            "EXPIRED" if icu_death else "ALIVE",         # LEAK
            _num(max(0.2, rng.gauss(3.1, 1.4)), 4),
            _num(icu_los, 4),                            # LEAK: post-hoc
            "-1" if unavailable else repr(p_h),          # the comparator, denylisted
            "EXPIRED" if y else "ALIVE",                 # LEAK: the outcome as text
            _num(max(0.5, rng.gauss(6.4, 3.0)), 4),
            _num(hosp_los, 4),                           # LEAK: post-hoc
            _integer(rng.randrange(0, 2) if rng.random() < 0.2 else -1),
            _integer(rng.randrange(0, 2) if rng.random() < 0.2 else -1),
            _integer(rng.randrange(0, 2) if rng.random() < 0.2 else -1),
            _num(icu_los, 4),                            # LEAK
            _num(hosp_los, 4),                           # LEAK
            _num(vent_days, 4),                          # LEAK
            _num(max(0.0, rng.gauss(1.9, 1.5)), 4),
            _num(vent_days, 4),                          # LEAK
        ]


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def generate(cfg: MockConfig) -> dict:
    """Write the table CSVs and manifest.json into <out>; return the manifest.

    Streams to disk per stay, so memory is flat at 9 000 stays and at 200 859.
    """
    if cfg.sites < EICU_MOCK_MIN_TOTAL_SITES and cfg.signal:
        raise ValueError(
            f"eicu_mock.generate: a signalled corpus must carry at least "
            f"{EICU_MOCK_MIN_TOTAL_SITES} sites (eicu_etl.site_split's floor -- "
            f"below it the 40/20/40 remainder cannot yield MIN_CAL_CLUSTERS "
            f"calibration sites), got {cfg.sites} (reason=mock-too-few-sites)")
    if cfg.header_case not in EICU_MOCK_HEADER_CASES:
        raise ValueError(
            f"eicu_mock.generate: header_case must be one of "
            f"{EICU_MOCK_HEADER_CASES}, got {cfg.header_case!r} "
            f"(reason=mock-bad-header-case)")
    unknown = [t for t in cfg.tables if t not in EICU_MOCK_TABLES]
    if unknown:
        raise ValueError(
            f"eicu_mock.generate: unknown table(s), got {unknown!r} "
            f"(reason=mock-unknown-table)")

    os.makedirs(cfg.out, exist_ok=True)

    hrng = random.Random(f"{cfg.seed}:hospital")
    hospitals = _hospital_ids(hrng, cfg.sites)
    weights = _site_weights(cfg.seed, cfg.sites, cfg.site_sigma)
    quotas = _site_quotas(weights, cfg.stays, EICU_MOCK_MIN_STAYS_PER_SITE)
    site_apache = _site_apache(cfg.seed, cfg.sites)
    # The per-site random effect is a value, cached per site. random.Random
    # caches a second normal inside gauss, so re-seeding and taking the first
    # draw is the only way "same site -> same u" holds.
    u_site = {hid: random.Random(f"{cfg.seed}:signal-site:{hid}").gauss(
        0.0, EICU_MOCK_SITE_SIGMA_U) for hid in hospitals}

    writers: dict[str, TableWriter | NullWriter] = {}
    for name, cols in EICU_MOCK_SCHEMA.items():
        if name not in cfg.tables:
            writers[name] = NullWriter()
            continue
        header = [(EICU_MOCK_CAMEL[c] if cfg.header_case == "camel" else c)
                  for c, _ in cols]
        # W15: a UTF-8 BOM on patient.csv.gz. read_table opens with
        # encoding="utf-8-sig", which strips it and is a no-op elsewhere.
        enc = "utf-8-sig" if (name == "patient" and cfg.warts) else "utf-8"
        writers[name] = TableWriter(os.path.join(cfg.out, f"{name}.csv.gz"),
                                    header, cfg.compresslevel, encoding=enc)

    counters = {name: make_counter(1) for name in EICU_MOCK_SCHEMA}
    rng_plan = random.Random(f"{cfg.seed}:plan")

    stays_written = 0
    deaths = 0
    admissions = set()
    aps_rows = 0
    try:
        if isinstance(writers["hospital"], TableWriter):
            for hid in hospitals:
                writers["hospital"].write(build_hospital_row(hrng, cfg, hid))

        for s in plan_stays(rng_plan, cfg, hospitals, quotas, site_apache, u_site):
            sid = s["stayid"]
            sentinel_rate = site_apache[s["site_index"]]["sentinel_rate"]

            if isinstance(writers["patient"], TableWriter):
                writers["patient"].write(build_patient_row(
                    random.Random(f"{cfg.seed}:patient:{sid}"), cfg, s))

            if s["aps_present"] and isinstance(writers["apacheApsVar"], TableWriter):
                rt = random.Random(f"{cfg.seed}:apacheApsVar:{sid}")
                plant = aps_rows if (cfg.warts and aps_rows < 2) else -1
                row = build_aps_row(rt, cfg, s, counters["apacheApsVar"],
                                    sentinel_rate, plant)
                writers["apacheApsVar"].write(row)
                aps_rows += 1
                # W12: a duplicate patientunitstayid with a fresh surrogate id.
                # None of these tables declares the stay id unique, so a naive
                # join silently inflates the cluster sizes feeding the
                # influence cap (T-8).
                if cfg.warts and rt.random() < EICU_MOCK_DUP_RATE:
                    writers["apacheApsVar"].write(
                        [counters["apacheApsVar"]()] + row[1:])
                    aps_rows += 1

            if s["apv_present"] and isinstance(writers["apachePredVar"], TableWriter):
                rt = random.Random(f"{cfg.seed}:apachePredVar:{sid}")
                row = build_apv_row(rt, cfg, s, counters["apachePredVar"],
                                    sentinel_rate)
                writers["apachePredVar"].write(row)
                if cfg.warts and rt.random() < EICU_MOCK_DUP_RATE:
                    writers["apachePredVar"].write(
                        [counters["apachePredVar"]()] + row[1:])

            if s["result_present"] and isinstance(
                    writers["apachePatientResult"], TableWriter):
                rt = random.Random(f"{cfg.seed}:apachePatientResult:{sid}")
                for row in build_result_rows(rt, cfg, s,
                                             counters["apachePatientResult"]):
                    writers["apachePatientResult"].write(row)

            admissions.add(s["hsid"])
            deaths += 1 if s["y"] else 0
            stays_written += 1
            if stays_written % 5000 == 0:
                print(f"[eicu-mock] {stays_written}/{cfg.stays} stays",
                      file=sys.stderr)
    finally:
        for w in writers.values():
            w.close()

    band_counts = [0] * len(EICU_MOCK_APS_SITE_BANDS)
    for c in site_apache:
        band_counts[c["band"]] += 1
    manifest = {
        "seed": cfg.seed,
        "stays_requested": cfg.stays,
        "stays_written": stays_written,
        "admissions": len(admissions),
        "sites": cfg.sites,
        "site_size_sigma": cfg.site_sigma,
        "base_rate": EICU_MOCK_BASE_RATE,
        "header_case": cfg.header_case,
        "signal": cfg.signal,
        "warts": cfg.warts,
        "drift": cfg.drift,
        "row_counts": {name: w.rows for name, w in writers.items()
                       if isinstance(w, TableWriter)},
        "apache_site_coverage_bands": [
            {"share_declared": share, "coverage": cov, "n_sites": band_counts[i]}
            for i, (share, cov) in enumerate(EICU_MOCK_APS_SITE_BANDS)],
        "sites_with_zero_result_rows": sum(1 for c in site_apache if c["zero_result"]),
    }
    with open(os.path.join(cfg.out, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)

    if cfg.emit_ddl:
        with open(os.path.join(cfg.out, "schema.sql"), "w") as fh:
            for name, cols in EICU_MOCK_SCHEMA.items():
                fh.write(f"DROP TABLE IF EXISTS {name.lower()} CASCADE;\n")
                fh.write(f"CREATE TABLE {name.lower()}\n(\n")
                fh.write(",\n".join(f"    {c} {t}" for c, t in cols))
                fh.write("\n);\n\n")

    return manifest


def parse_args(argv=None) -> MockConfig:
    p = argparse.ArgumentParser(
        description="Generate a schema-faithful eICU-CRD v2.0 MOCK corpus "
                    "(real column names, real DDL order, every documented wart).")
    p.add_argument("--stays", type=int, default=EICU_MOCK_SMALL_STAYS,
                   help=f"unit stays to emit (default {EICU_MOCK_SMALL_STAYS}; "
                        f"the full-scale arm is {EICU_MOCK_FULL_STAYS})")
    p.add_argument("--sites", type=int, default=EICU_MOCK_SMALL_SITES,
                   help=f"hospitals (default {EICU_MOCK_SMALL_SITES}; "
                        f"the real corpus has {EICU_MOCK_FULL_SITES})")
    p.add_argument("--seed", type=int, default=EICU_MOCK_SEED,
                   help="RNG seed; same seed + same args = byte-identical output")
    p.add_argument("--out", default="./eicu-mock", help="output directory")
    p.add_argument("--compresslevel", type=int, default=6, choices=range(0, 10))
    p.add_argument("--header-case", default="camel",
                   help="header row spelling: camel|lower (the released CSVs "
                        "are lowercase; a re-zip may not be, and read_table "
                        "must not care)")
    p.add_argument("--tables", default="",
                   help="comma-separated subset to emit (default: all); the "
                        "selected tables are byte-identical to the same tables "
                        "of a full run at the same seed")
    p.add_argument("--no-signal", action="store_true",
                   help="emit a label-free outcome draw instead of the latent "
                        "severity model (stream positions are unchanged)")
    p.add_argument("--no-warts", action="store_true",
                   help="drop the CSV-hostile and unit-ambiguous plants (W8, "
                        "W10-W13, W15, W16 and the planted rows); the "
                        "structural warts W1-W7, W9 and W14 always stay")
    p.add_argument("--site-sigma", type=float, default=EICU_MOCK_SITE_SIGMA,
                   help="lognormal sd of per-site weights (default "
                        f"{EICU_MOCK_SITE_SIGMA}); 0 gives uniform site sizes")
    p.add_argument("--drift", action="store_true",
                   help="push `gender` past EICU_MAX_OTHER_SHARE, so "
                        "build_raw(strict_levels=True) must raise "
                        "categorical-level-drift")
    p.add_argument("--emit-ddl", action="store_true", help="also write schema.sql")
    a = p.parse_args(argv)

    tables = [t.strip() for t in a.tables.split(",") if t.strip()] or list(EICU_MOCK_TABLES)
    unknown = sorted(set(tables) - set(EICU_MOCK_TABLES))
    if unknown:
        p.error(f"unknown table(s): {', '.join(unknown)}. "
                f"Valid: {', '.join(EICU_MOCK_TABLES)}")
    if a.header_case not in EICU_MOCK_HEADER_CASES:
        p.error(f"unknown --header-case: {a.header_case!r}. "
                f"Valid: {', '.join(EICU_MOCK_HEADER_CASES)}")

    return MockConfig(
        stays=a.stays,
        sites=a.sites,
        seed=a.seed,
        out=a.out,
        compresslevel=a.compresslevel,
        header_case=a.header_case,
        tables=tables,
        signal=not a.no_signal,
        warts=not a.no_warts,
        site_sigma=a.site_sigma,
        drift=a.drift,
        emit_ddl=a.emit_ddl,
    )


def main(argv=None) -> int:
    cfg = parse_args(argv)
    print(f"[eicu-mock] {cfg.stays} stays / {cfg.sites} hospitals -> {cfg.out} "
          f"(seed={cfg.seed}, signal={cfg.signal}, warts={cfg.warts})",
          file=sys.stderr)
    manifest = generate(cfg)
    print("\n[eicu-mock] row counts:", file=sys.stderr)
    width = max(len(k) for k in manifest["row_counts"]) if manifest["row_counts"] else 1
    for name, count in manifest["row_counts"].items():
        print(f"  {name.ljust(width)}  {count:>12,}", file=sys.stderr)
    print(f"[eicu-mock] stays written {manifest['stays_written']:,} across "
          f"{manifest['admissions']:,} hospital admissions; "
          f"{manifest['sites_with_zero_result_rows']} hospitals with ZERO "
          f"apachePatientResult rows", file=sys.stderr)
    print(f"[eicu-mock] wrote {cfg.out}/manifest.json", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
