"""SPEC section "Real-data protocol (eICU-CRD v2.0)": eICU extract -> CertGate cohorts.

Reads a released (or mock) eICU-CRD v2.0 extract directory -- five gzipped
CSVs, ``patient`` / ``hospital`` / ``apacheApsVar`` / ``apachePredVar`` /
``apachePatientResult`` -- with the ``csv`` module (NEVER line-based tools:
``apacheadmissiondx`` and the discharge-location fields carry embedded
newlines/commas/quotes), and emits a finite float64 feature matrix, the RAW
two-valued outcome strings, and the RAW site identifiers, ready for
``certgate.validate.from_raw``.

The protocol is frozen in ``EICU-PROTOCOL.md`` and pre-registered BEFORE the
extract was read; this module is its executable form. Four disciplines are
load-bearing and every one traces to a stated risk:

* **Deny by default** (T-1). ``FEATURE_NAMES`` is built by concatenating the
  same frozen tuples used to one-hot, so names and columns cannot drift, and
  ``assert_no_leak_columns`` runs at IMPORT time over ``EICU_LEAK_DENYLIST`` --
  a leak cannot even be imported, let alone certified.
* **Dual-channel missingness** (T-2). Both ``''`` (the documented SQL NULL --
  the MIT-LCP loader is ``NULL ''``) AND the literal ``-1`` (the UNdocumented
  APACHE sentinel) map to NaN. Handling only one poisons the matrix with a
  finite ``-1``. Negative mass anywhere else is an unrecognised sentinel and
  ABORTS (``reason=unexpected-negative-sentinel``) rather than flowing.
* **Site-informative missingness is measured, never imputed away** (T-3/T-4).
  CertGate v2 scope-cut covariate-shift mode, and the dataset authors state
  that data completion varies by hospital, so ``preflight`` reports per-site
  sentinel dispersion and per-site APACHE coverage, and APACHE availability
  enters the ATTRITION LEDGER -- it is never applied as a filter in the
  primary arm.
* **Imputation is fit on S_train rows ONLY**. Pooled-matrix means would let the
  target pool's covariate distribution into the training features: a
  transductive leak no downstream gate catches.

The site (``patient.hospitalid``) is the unit of statistical independence;
``hospitalid`` and ``wardid`` are on the feature denylist because a head that
can read the site off the feature vector destroys the between-site
generalisation the certificate rests on (audit V1's estimand is a SITE
POPULATION AVERAGE).

Stdlib + numpy only.
"""
from __future__ import annotations

import csv
import gzip
import math
import os
import sys
import zlib
from collections import Counter, defaultdict

import numpy as np

from certgate.constants import SEED, SPLIT_FRACTIONS, MIN_CAL_CLUSTERS

# apacheadmissiondx is VARCHAR(1000) and text fields carry embedded newlines:
# the default 128 KiB field cap is not obviously safe on a hostile extract.
csv.field_size_limit(10 ** 7)


# =============================================================== errors =====

class EicuError(ValueError):
    """Every eICU-boundary rejection (SPEC "Real-data protocol"; audit F05/F35).

    Message form::

        eicu_etl.<function>: <what failed>, got <repr> (reason=<tag>)

    The reason-tag vocabulary is a CLOSED set (tests match on these
    substrings)::

        missing-table            duplicate-header          missing-column
        undecodable-table        truncated-table
        unknown-outcome-level    unknown-arm               categorical-level-drift
        unexpected-negative-sentinel                       unrecognised-null-token
        unparseable-join-key     apache-coverage-collapse
        outcome-informative-missingness                    duplicate-stay-id
        reference-row-count-mismatch
        too-few-sites            too-few-cal-clusters      impute-fit-empty
        nonfinite-after-impute   leak-column-in-features   feature-width-mismatch
        record-level-output      hospitalid-unparseable    empty-cohort

    ``record-level-output`` is raised by ``run_eicu.assert_aggregate_only``,
    which imports this type; it is listed here because the vocabulary is
    closed and shared.
    """


_UNSET = object()


def _err(func: str, what: str, got=_UNSET, *, reason: str) -> EicuError:
    """Build the house-format ``EicuError`` (message form in ``EicuError``)."""
    if got is _UNSET:
        return EicuError(f"eicu_etl.{func}: {what} (reason={reason})")
    return EicuError(f"eicu_etl.{func}: {what}, got {got!r} (reason={reason})")


# ============================================================ constants =====
# B.0: protocol constants live HERE, at module top of the experiment module --
# certgate/constants.py is NOT touched (no eICU constant enters the core
# package). Every name below is pinned literally by tests/test_constants.py
# (the run_synthetic.py precedent, extended); a red constants test is a design
# change, not a nuisance (audit F13).

EICU_TABLES = ("patient", "hospital", "apacheApsVar", "apachePredVar",
               "apachePatientResult")
EICU_SITE_PREFIX = "hosp-"
EICU_LABEL_COLUMN = "hospitaldischargestatus"
EICU_POSITIVE_LABEL = "Expired"
EICU_NEGATIVE_LABEL = "Alive"
EICU_MIN_AGE = 18
EICU_AGE_MASK_TOKEN = "> 89"
EICU_AGE_MASK_VALUE = 90.0
EICU_SENTINEL_MISSING = -1.0
EICU_IMPUTE_FALLBACK = 0.0
EICU_APACHE_VERSION_PREFERENCE = ("IVa", "IV")
EICU_MAX_OTHER_SHARE = 0.05
EICU_MAX_CROSS_SITE_PATIENT_SHARE = 0.01
EICU_N_TARGET_SITES = 24
EICU_SPLIT_NAMESPACE = 9
EICU_SPLIT_REPLICATES = 20
EICU_MIN_TOTAL_SITES = 149      # SUFFICIENT floor, not the tight one: int()
                                # truncation in the 40/20/40 split makes the
                                # calibration count non-monotone in the total
                                # (148 -> 51, 149 -> 50), so the checkable
                                # property is "at and above 149 the projection
                                # always clears MIN_CAL_CLUSTERS". The tight
                                # breakpoint is 146; this keeps 3 sites of slack.
EICU_N_FEATURES = 161
EICU_ARMS = ("primary", "apache-linked", "apache-complete")
EICU_POOLED_TARGET_LABEL = "eicu-target-pool"

# ---- the outcome-informative-missingness gates (2026-07-31 audit, E-9) -----
# APACHE day-1 variables are defined over the first 24 hours, so a stay that
# ends BECAUSE THE PATIENT DIED before the window closes carries no
# apacheApsVar/apachePredVar row. Whole-row absence is therefore not only
# SITE-informative (threat T-3) but partly an OUTCOME PROXY -- a leak channel
# with no column name, invisible to a name denylist, to the -1 gate, to the
# drift gate, and to the old alpha/coverage-conditioned F-D.
EICU_MAX_OUTCOME_PREVALENCE_RATIO = 2.0   # absent:present prevalence ratio; above
                                          # this the presence flags are an outcome
                                          # proxy and build_raw ABORTS
EICU_MIN_OUTCOME_STRATUM = 100            # both strata must be populated for the
                                          # ratio to mean anything
EICU_FEATURE_AUC_REVIEW = 0.75            # outcome_screen: a univariate AUC past this
                                          # flags the column for timing re-audit
# A NULL token that is not '' (Postgres text format writes \N) turns every
# allowlisted APACHE numeric into 100% missing while build_raw succeeds; the
# -1 gate protects only the opposite direction.
EICU_MAX_UNPARSEABLE_SHARE = 0.01
_NULL_TOKEN_CARDINALITY_CAP = 8           # bounded retention of offending tokens

EICU_ATTRITION_STEPS = ("raw-unit-stays", "site-parseable", "outcome-known",
                        "adult", "first-stay", "primary-cohort",
                        "apache-aps-linked", "apache-result-linked",
                        "apache-complete-arm")

EICU_REFERENCE_ROW_COUNTS = {"patient": 200859, "hospital": 208,
                             "apacheApsVar": 171177, "apachePredVar": 171177,
                             "apachePatientResult": 297064}
EICU_REFERENCE_SITES = 208
EICU_REFERENCE_PATIENTS = 139367
EICU_REFERENCE_UNIT_STAYS = 200859

# ---- feature blocks (A.5) --------------------------------------------------

EICU_PATIENT_NUMERIC = ("age", "admissionheight", "admissionweight",
                        "pre_icu_hours")

EICU_LEVELS_GENDER = ("Female", "Male", "Other", "Unknown", "", "OTHER")
EICU_LEVELS_ETHNICITY = ("African American", "Asian", "Caucasian", "Hispanic",
                         "Native American", "Other/Unknown", "", "OTHER")
EICU_LEVELS_ADMITSOURCE = ("Acute Care/Floor", "Chest Pain Center",
                           "Direct Admit", "Emergency Department", "Floor",
                           "ICU", "ICU to SDU", "Observation", "Operating Room",
                           "Other", "Other Hospital", "Other ICU", "PACU",
                           "Recovery Room", "Step-Down Unit (SDU)", "", "OTHER")
EICU_LEVELS_UNITTYPE = ("CCU-CTICU", "CSICU", "CTICU", "Cardiac ICU", "MICU",
                        "Med-Surg ICU", "Neuro ICU", "SICU", "", "OTHER")
EICU_LEVELS_UNITSTAYTYPE = ("admit", "readmit", "stepdown/other", "transfer",
                            "", "OTHER")

# Order here IS the one-hot block order in FEATURE_NAMES (A.5.8).
EICU_CATEGORICALS = (("gender", EICU_LEVELS_GENDER),
                     ("ethnicity", EICU_LEVELS_ETHNICITY),
                     ("hospitaladmitsource", EICU_LEVELS_ADMITSOURCE),
                     ("unitadmitsource", EICU_LEVELS_ADMITSOURCE),
                     ("unittype", EICU_LEVELS_UNITTYPE),
                     ("unitstaytype", EICU_LEVELS_UNITSTAYTYPE))

EICU_APS_NUMERIC = ("intubated", "vent", "dialysis", "eyes", "motor", "verbal",
                    "meds", "urine", "wbc", "temperature", "respiratoryrate",
                    "sodium", "heartrate", "meanbp", "ph", "hematocrit",
                    "creatinine", "albumin", "pao2", "pco2", "bun", "glucose",
                    "bilirubin", "fio2")

EICU_APV_NUMERIC = ("graftcount", "thrombolytics", "aids", "hepaticfailure",
                    "lymphoma", "metastaticcancer", "leukemia",
                    "immunosuppression", "cirrhosis", "electivesurgery",
                    "activetx", "readmit", "ima", "midur", "ventday1",
                    "oobventday1", "oobintubday1", "diabetes", "ejectfx")

# ---- plausibility windows and the two frozen unit normalisations (A.5.6) ---
# Interval semantics are stated per window; they are NOT symmetric, and the
# fio2/temperature pairs are non-overlapping by construction so the convention
# mapping is unambiguous (T-10).
EICU_WINDOW_HEIGHT_CM = (100.0, 250.0)        # inclusive; 0/'' are the missing encodings
EICU_WINDOW_WEIGHT_KG = (20.0, 300.0)         # inclusive
EICU_WINDOW_PRE_ICU_HRS = (0.0, 720.0)        # inclusive
EICU_WINDOW_FIO2_FRAC = (0.21, 1.0)           # [lo, hi]  -- fraction convention
EICU_WINDOW_FIO2_PCT = (21.0, 100.0)          # [lo, hi]  -- percent convention
                                              # LOWER-CLOSED (2026-07-31 audit, E-18):
                                              # fio2 == 0.21 (== 21) is ROOM AIR, the
                                              # modal value of a ventilation-linked
                                              # column, and ventilation status is
                                              # site-correlated -- discarding it would
                                              # manufacture exactly the informative-
                                              # missingness channel this protocol
                                              # undertakes to guard. The fraction branch
                                              # is tested FIRST, so 21.0 is unambiguous.
EICU_WINDOW_TEMP_C = (25.0, 45.0)             # (lo, hi)  -- Celsius
EICU_WINDOW_TEMP_F = (77.0, 113.0)            # (lo, hi)  -- Fahrenheit contamination

# Documented ordinal supports, used ONLY by preflight to warn on values outside
# {documented range} u {-1} u {0} (A.5.6). They are never a filter.
EICU_ORDINAL_COLUMNS = ("intubated", "vent", "dialysis", "eyes", "motor",
                        "verbal", "meds")
EICU_ORDINAL_RANGES = {"intubated": (0, 1), "vent": (0, 1), "dialysis": (0, 1),
                       "eyes": (1, 4), "motor": (1, 6), "verbal": (1, 5),
                       "meds": (0, 1)}

# ---- leak denylist (A.7): deny by default, 36 entries ----------------------
# Entries are (qualified source column, reason). assert_no_leak_columns is a
# TEST, not a comment (T-1), and also runs at import.
EICU_LEAK_DENYLIST = (
    ("apachepredvar.diedinhospital", "the outcome itself, as an integer"),
    ("apachepatientresult.actualhospitalmortality", "the outcome as a string"),
    ("apachepatientresult.actualicumortality", "ICU mortality outcome"),
    ("patient.hospitaldischargestatus", "the outcome (label column; never a feature)"),
    ("patient.unitdischargestatus", "ICU-death outcome ('Expired')"),
    ("patient.hospitaldischargelocation", "values include 'Death'"),
    ("patient.unitdischargelocation", "post-outcome disposition"),
    ("patient.hospitaldischargeoffset", "length of stay, post-hoc"),
    ("patient.unitdischargeoffset", "ICU length of stay, post-hoc"),
    ("patient.hospitaldischargetime24", "post-hoc timestamp"),
    ("patient.unitdischargetime24", "post-hoc timestamp"),
    ("patient.dischargeweight", "measured at discharge"),
    ("apachepatientresult.actualiculos", "post-hoc"),
    ("apachepatientresult.actualhospitallos", "post-hoc"),
    ("apachepatientresult.unabridgedunitlos", "post-hoc"),
    ("apachepatientresult.unabridgedhosplos", "post-hoc"),
    ("apachepatientresult.actualventdays", "post-hoc"),
    ("apachepatientresult.unabridgedactualventdays", "post-hoc"),
    ("apachepredvar.saps3today", "intra-stay update (and a documented constant)"),
    ("apachepredvar.saps3yesterday", "intra-stay update (and a documented constant)"),
    ("apachepredvar.var03hspxlos", "post-hoc LOS-derived ('Not used')"),
    ("apachepredvar.dischargelocation", "post-outcome disposition"),
    ("patient.hospitalid", "SITE identifier -- memorisation, fatal to between-site generalisation"),
    ("patient.wardid", "unit identifier -- same"),
    ("patient.hospitaldischargeyear", "temporal split variable, confounded with site enrolment"),
    ("apachepatientresult.predictedhospitalmortality", "the comparator being competed against"),
    ("apachepatientresult.predictedicumortality", "comparator"),
    ("apachepatientresult.predictediculos", "comparator"),
    ("apachepatientresult.predictedhospitallos", "comparator"),
    ("apachepatientresult.predventdays", "comparator"),
    ("apachepatientresult.apachescore",
     "APACHE-III composite of the same APS inputs; table has 8.65% zero-coverage sites"),
    ("apachepatientresult.acutephysiologyscore", "same"),
    ("apachepatientresult.physicianspeciality",
     "leak-suspect: assignment timing relative to outcome unverified"),
    ("apachepatientresult.physicianinterventioncategory", "leak-suspect: same"),
    ("patient.apacheadmissiondx",
     "not a leak -- excluded as un-pre-registrable high-cardinality free text"),
    ("patient.unitvisitnumber",
     "not a leak -- excluded as near-constant after the first-stay rule"),
)

#: Bare column names of the denylist (derived; the assertion surface).
EICU_LEAK_COLUMNS = tuple(sorted({c.split(".")[-1]
                                  for c, _ in EICU_LEAK_DENYLIST}))


# ---- required columns, addressed BY NAME (never by position) ---------------
# The MIT-LCP \copy load is POSITIONAL against the DDL, which puts the
# surrogate id FIRST -- contradicting the eicu.mit.edu doc pages. Addressing by
# name is the only safe read (T-6).
EICU_REQUIRED_COLUMNS = {
    "patient": ("patientunitstayid", "patienthealthsystemstayid", "gender",
                "age", "ethnicity", "hospitalid", "admissionheight",
                "hospitaladmitoffset", "hospitaladmitsource",
                "hospitaldischargestatus", "hospitaldischargeyear", "unittype",
                "unitadmitsource", "unitvisitnumber", "unitstaytype",
                "admissionweight", "unitdischargestatus", "uniquepid"),
    "hospital": ("hospitalid", "numbedscategory", "teachingstatus", "region"),
    "apacheApsVar": ("apacheapsvarid", "patientunitstayid") + EICU_APS_NUMERIC,
    "apachePredVar": ("apachepredvarid", "patientunitstayid") + EICU_APV_NUMERIC,
    "apachePatientResult": ("apachepatientresultsid", "patientunitstayid",
                            "apacheversion", "predictedhospitalmortality"),
}


# ---- FEATURE_NAMES (A.5.8): names and columns cannot drift -----------------

def _pairs(prefix, cols):
    """``<prefix><col>`` immediately followed by its ``__missing`` sibling."""
    out = []
    for c in cols:
        out.append(f"{prefix}{c}")
        out.append(f"{prefix}{c}__missing")
    return out


def _onehot_names(col, levels):
    """One-hot names over a FROZEN level tuple; ``''`` renders as ``EMPTY``."""
    return [f"{col}={(v if v else 'EMPTY')}" for v in levels]


FEATURE_NAMES = tuple(
    _pairs("", EICU_PATIENT_NUMERIC)                                    # 8
    + ["age_masked"]                                                    # 1
    + _onehot_names("gender", EICU_LEVELS_GENDER)                       # 6
    + _onehot_names("ethnicity", EICU_LEVELS_ETHNICITY)                 # 8
    + _onehot_names("hospitaladmitsource", EICU_LEVELS_ADMITSOURCE)     # 17
    + _onehot_names("unitadmitsource", EICU_LEVELS_ADMITSOURCE)         # 17
    + _onehot_names("unittype", EICU_LEVELS_UNITTYPE)                   # 10
    + _onehot_names("unitstaytype", EICU_LEVELS_UNITSTAYTYPE)           # 6
    + _pairs("aps_", EICU_APS_NUMERIC)                                  # 48
    + _pairs("apv_", EICU_APV_NUMERIC)                                  # 38
    + ["aps_present", "apv_present"]                                    # 2
)                                                                       # = 161

FEATURE_INDEX = {name: i for i, name in enumerate(FEATURE_NAMES)}


def feature_names() -> list:
    """``list(FEATURE_NAMES)`` -- the frozen, deny-by-default allowlist."""
    return list(FEATURE_NAMES)


def assert_no_leak_columns(names) -> None:
    """Refuse any denylisted source column in ``names`` (A.7; T-1).

    Raises ``EicuError`` (``reason=leak-column-in-features``) if any
    ``EICU_LEAK_DENYLIST`` column appears bare, under the ``aps_``/``apv_``
    prefixes, with or without the ``__missing`` suffix, or as a ``<col>=``
    one-hot stem. A leak here produces a spectacular and entirely fake result,
    so the check is an assertion that runs at IMPORT and again inside
    ``build_raw`` -- never a comment.
    """
    forbidden = {}
    stems = {}
    for col in EICU_LEAK_COLUMNS:
        for pre in ("", "aps_", "apv_"):
            forbidden[f"{pre}{col}"] = col
            forbidden[f"{pre}{col}__missing"] = col
        stems[f"{col}="] = col
    hits = []
    for name in names:
        if name in forbidden:
            hits.append((name, forbidden[name]))
            continue
        for stem, col in stems.items():
            if name.startswith(stem):
                hits.append((name, col))
                break
    if hits:
        raise _err("assert_no_leak_columns",
                   "denylisted source column(s) reached the feature matrix "
                   "(feature name, denied column)", sorted(hits),
                   reason="leak-column-in-features")


# The frozen width and the denylist are invariants of the MODULE, not of a
# call: an import that violates either must fail loudly rather than wait for a
# certificate to be issued from a poisoned matrix.
if len(FEATURE_NAMES) != EICU_N_FEATURES:
    raise _err("<module>",
               f"FEATURE_NAMES width {len(FEATURE_NAMES)} != EICU_N_FEATURES "
               f"{EICU_N_FEATURES}", reason="feature-width-mismatch")
if len(set(FEATURE_NAMES)) != len(FEATURE_NAMES):
    raise _err("<module>", "FEATURE_NAMES contains duplicates",
               reason="feature-width-mismatch")
assert_no_leak_columns(FEATURE_NAMES)


# ---- column-index maps (built once, from FEATURE_NAMES) --------------------

_IDX_PATIENT = tuple((FEATURE_INDEX[c], FEATURE_INDEX[c + "__missing"])
                     for c in EICU_PATIENT_NUMERIC)
_IDX_APS = tuple((FEATURE_INDEX["aps_" + c], FEATURE_INDEX["aps_" + c + "__missing"])
                 for c in EICU_APS_NUMERIC)
_IDX_APV = tuple((FEATURE_INDEX["apv_" + c], FEATURE_INDEX["apv_" + c + "__missing"])
                 for c in EICU_APV_NUMERIC)
_IDX_CAT = tuple((col, {lv: FEATURE_INDEX[f"{col}={(lv if lv else 'EMPTY')}"]
                        for lv in levels}, levels[-1])
                 for col, levels in EICU_CATEGORICALS)
_IDX_AGE_MASKED = FEATURE_INDEX["age_masked"]
_IDX_APS_PRESENT = FEATURE_INDEX["aps_present"]
_IDX_APV_PRESENT = FEATURE_INDEX["apv_present"]

_PARENT_COLS = np.array([a for a, _ in _IDX_PATIENT]
                        + [a for a, _ in _IDX_APS]
                        + [a for a, _ in _IDX_APV], dtype=int)
_MISSING_COLS = np.array([b for _, b in _IDX_PATIENT]
                         + [b for _, b in _IDX_APS]
                         + [b for _, b in _IDX_APV], dtype=int)
_PARENT_NAME = {int(j): FEATURE_NAMES[int(j)] for j in _PARENT_COLS}

_OTHER_CARDINALITY_CAP = 200      # unlisted-value counters are bounded


# ============================================================== readers =====

def _resolve_table_path(data_dir, table) -> str:
    """Case-INSENSITIVE resolution of ``<table>.csv.gz`` (T-6).

    The released zip is CamelCase; a re-zip may not be. Raises ``EicuError``
    (``reason=missing-table``) if no case-variant exists.
    """
    want = f"{table.lower()}.csv.gz"
    try:
        entries = os.listdir(data_dir)
    except OSError as e:
        raise _err("read_table",
                   f"cannot list extract directory for table {table!r}",
                   data_dir, reason="missing-table") from e
    for name in sorted(entries):
        if name.lower() == want:
            return os.path.join(data_dir, name)
    raise _err("read_table",
               f"no case-variant of {want!r} in the extract directory",
               data_dir, reason="missing-table")


def _lower_header(raw_header, table, path):
    """Strip + lowercase a header row; raise on a lowercase-collision."""
    lower = [h.strip().lower() for h in raw_header]
    seen = {}
    for i, h in enumerate(lower):
        if h in seen:
            raise _err("read_table",
                       f"table {table!r} has two headers that lowercase to the "
                       f"same name at positions {seen[h]} and {i}",
                       (raw_header[seen[h]], raw_header[i]),
                       reason="duplicate-header")
        seen[h] = i
    return lower


#: Read-boundary failures that must become TYPED, table-naming errors.
#: ``UnicodeDecodeError``'s "position N" is a decode-BUFFER offset, not a byte
#: or row offset in the file, and neither it nor ``EOFError`` carries the table
#: name -- on a five-table extract the operator cannot tell which file failed
#: (2026-07-31 audit, E-14).
_READ_ERRORS = (UnicodeDecodeError, EOFError, gzip.BadGzipFile, zlib.error,
                OSError)


def _read_reason(exc):
    """Reason tag for a read-boundary failure: decode vs decompression."""
    return ("undecodable-table" if isinstance(exc, UnicodeDecodeError)
            else "truncated-table")


def _read_failure(func, table, path, exc, fh=None):
    """Typed re-raise naming the table, the path and (where the stream can
    still be interrogated) the byte offset reached."""
    where = ""
    try:                                    # best effort; never masks `exc`
        buf = getattr(fh, "buffer", None)
        if buf is not None:
            where = f" at byte offset {buf.tell()}"
    except Exception:                       # noqa: BLE001 - diagnostic only
        where = ""
    return _err(func,
                f"table {table!r} at {path} could not be decoded/decompressed"
                f"{where}: {type(exc).__name__}: {exc}", reason=_read_reason(exc))


def _read_header(path, table):
    """Return ``(raw_header, lower_header)`` without consuming the table."""
    fh = None
    try:
        with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as fh:
            r = csv.reader(fh)
            try:
                raw = next(r)
            except StopIteration:
                raise _err("read_table", f"table {table!r} has no header row",
                           path, reason="missing-column") from None
    except _READ_ERRORS as e:
        raise _read_failure("read_table", table, path, e, fh) from e
    return raw, _lower_header(raw, table, path)


def require_columns(header_lower, table, needed) -> None:
    """Raise ``EicuError`` (``reason=missing-column``) naming the table, the
    missing names, and the header as read (SPEC "Real-data protocol")."""
    have = set(header_lower)
    missing = [c for c in needed if c not in have]
    if missing:
        raise _err("require_columns",
                   f"table {table!r} is missing required column(s) {missing!r}; "
                   f"header as read", list(header_lower),
                   reason="missing-column")


def read_table(data_dir, table, *, limit=None):
    """Yield lowercase-keyed dict rows from a gzipped eICU CSV.

    Resolves ``<table>.csv.gz`` case-INSENSITIVELY against the directory
    listing (the released zip is CamelCase; a re-zip may not be), opens with
    ``gzip.open(path, "rt", encoding="utf-8-sig", newline="")`` -- ``utf-8-sig``
    strips a BOM if present and is a no-op otherwise -- and reads with
    ``csv.reader`` taking the header via ``next(r)``. Header names are
    ``.strip()``ed and ``.lower()``ed, so the CamelCase/lowercase ambiguity
    cannot silently mismatch; columns are ALWAYS addressed BY NAME, never by
    position (the MIT-LCP ``\\copy`` load is positional against the DDL, which
    puts the surrogate id FIRST, contradicting the eicu.mit.edu doc pages).

    Raises ``EicuError`` (``reason=missing-table``) if no case-variant exists,
    (``reason=duplicate-header``) if two headers lowercase to the same name,
    (``reason=missing-column``) if the table lacks a column this module
    addresses (``EICU_REQUIRED_COLUMNS``), and (``reason=undecodable-table`` /
    ``reason=truncated-table``) on a non-UTF-8 byte or a partial/corrupt gzip
    -- a bare ``UnicodeDecodeError``/``EOFError`` names neither the table nor
    the file. Short rows are padded with ``''`` (the two missing channels are
    equivalent downstream) and completely blank rows are skipped; a generator,
    so the file is never materialised.
    """
    path = _resolve_table_path(data_dir, table)
    fh = None
    try:
        with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as fh:
            r = csv.reader(fh)
            try:
                raw_header = next(r)
            except StopIteration:
                raise _err("read_table", f"table {table!r} has no header row",
                           path, reason="missing-column") from None
            header = _lower_header(raw_header, table, path)
            require_columns(header, table, EICU_REQUIRED_COLUMNS.get(table, ()))
            ncols = len(header)
            emitted = 0
            for row in r:
                if not row or (len(row) == 1 and not row[0].strip()):
                    continue
                if len(row) < ncols:
                    row = row + [""] * (ncols - len(row))
                yield {header[i]: row[i] for i in range(ncols)}
                emitted += 1
                if limit is not None and emitted >= limit:
                    return
    except _READ_ERRORS as e:
        raise _read_failure("read_table", table, path, e, fh) from e


# ========================================================= cell parsers =====

def _maybe_float(s):
    """``''``/whitespace/junk/non-finite -> ``None``; else ``float``.

    Non-finite is folded into "missing" deliberately: a cell literally reading
    ``inf`` or ``nan`` parses under ``float()`` and would otherwise survive
    into the matrix, which ``make_cohort`` rejects only at the very end.
    """
    if s is None:
        return None
    t = s.strip()
    if not t:
        return None
    try:
        v = float(t)
    except ValueError:
        return None
    return v if math.isfinite(v) else None


def _maybe_int(s):
    """Integral token -> ``int``; anything else -> ``None`` (never raises)."""
    if s is None:
        return None
    t = s.strip()
    if not t:
        return None
    try:
        return int(t)
    except ValueError:
        return None


def parse_age(token):
    """``patient.age`` (VARCHAR(10)) -> float years, per A.2/A.5.1.

    ``''`` -> ``None`` (the caller drops, counted ``age-unparseable``);
    ``'> 89'`` -> ``90.0`` (KEPT, with ``age_masked = 1``); anything else
    ``float(int(t))`` -- ``int()`` FIRST so a non-integral residue raises
    rather than silently rounding. The naive ``int(row['age'])`` raises on the
    HIPAA ceiling token, which is exactly the trap
    ``experiments/synth_fixture.py`` already models as ``attr_band``.

    ``'> 89'`` is kept rather than dropped because ~3.5% of stays carry it, it
    is a mortality-enriched stratum, and its share varies BY HOSPITAL -- so
    dropping it is a site-correlated exclusion, the precise mechanism this
    protocol must not quietly introduce.
    """
    t = (token or "").strip()
    if not t:
        return None
    if t == EICU_AGE_MASK_TOKEN:
        return EICU_AGE_MASK_VALUE
    return float(int(t))


def _new_sentinel_counter():
    return {"empty": 0, "minus_one": 0, "other_negative": 0, "unparseable": 0}


def _note_null_token(tokens, key, t):
    """Retain a BOUNDED sample of the tokens that failed ``float()``.

    A count alone cannot tell the operator that the extract's NULL token is
    ``'\\N'`` rather than ``''``; the token can, and it is the difference
    between a one-line fix and a silently information-free matrix
    (2026-07-31 audit, E-15).
    """
    if tokens is None:
        return
    c = tokens.setdefault(key, Counter())
    if t in c or len(c) < _NULL_TOKEN_CARDINALITY_CAP:
        c[t] += 1
    else:
        c["__other__"] += 1


def _parse_apache_cell(col, raw, key, sent, unit, win, tokens=None):
    """One allowlisted APACHE numeric -> value or NaN (A.5.6; T-2/T-10).

    Dual missing channel: ``''`` (the documented SQL NULL) AND the literal
    ``-1`` (the UNdocumented sentinel) both map to NaN and are counted
    SEPARATELY. Any other negative is an unrecognised sentinel: it is mapped
    to NaN, counted as ``other_negative``, and ``build_raw`` ABORTS on a
    non-zero count -- every allowlisted column has non-negative physiological
    support, so a negative that is not exactly ``-1`` must not flow.

    The two frozen unit normalisations are applied BEFORE the window test and
    counted in ``meta['unit_conversions']``; the fio2 and temperature window
    pairs do not overlap, so the convention mapping is unambiguous.
    """
    s = sent[key]
    t = (raw or "").strip()
    if not t:
        s["empty"] += 1
        return math.nan
    try:
        v = float(t)
    except ValueError:
        s["unparseable"] += 1
        _note_null_token(tokens, key, t)
        return math.nan
    if not math.isfinite(v):
        s["unparseable"] += 1
        _note_null_token(tokens, key, t)
        return math.nan
    if v == EICU_SENTINEL_MISSING:
        s["minus_one"] += 1
        return math.nan
    if v < 0.0:
        s["other_negative"] += 1
        return math.nan
    if col == "fio2":
        lo, hi = EICU_WINDOW_FIO2_FRAC
        plo, phi = EICU_WINDOW_FIO2_PCT
        # LOWER-CLOSED, fraction branch first: fio2 == 0.21 (== 21) is ROOM
        # AIR, a valid modal observation on a ventilation-linked column, and
        # ventilation status is site-correlated (2026-07-31 audit, E-18).
        if lo <= v <= hi:
            if v == lo:
                unit[f"{key}:room-air-fraction"] += 1
            return v
        if plo <= v <= phi:
            unit[f"{key}:percent-to-fraction"] += 1
            if v == plo:
                unit[f"{key}:room-air-percent"] += 1
            return v / 100.0
        win[key] += 1
        return math.nan
    if col == "temperature":
        clo, chi = EICU_WINDOW_TEMP_C
        flo, fhi = EICU_WINDOW_TEMP_F
        if clo < v < chi:
            return v
        if flo < v < fhi:
            unit[f"{key}:fahrenheit-to-celsius"] += 1
            return (v - 32.0) * 5.0 / 9.0
        win[key] += 1
        return math.nan
    return v


def _parse_windowed(raw, key, window, sent, win, transform=None, tokens=None):
    """A ``patient`` numeric under a frozen plausibility window (T-11).

    ``0`` is the missing encoding for height/weight (not ``-1``) and falls out
    of the window by construction; decimal-point entry errors (544 kg, 612 cm)
    do too. Out-of-window values become NaN + indicator, counted in
    ``window_clipped_counts`` -- never clipped to the boundary, which would
    invent an observation.

    Unparseable tokens are SAMPLED via ``tokens``, exactly as
    ``_parse_apache_cell`` does: the E-15 gate covers every allowlisted
    numeric, and the patient block's ``hospitaladmitoffset`` doubles as the
    first-stay tie-breaker, so a silent zeroing here also silently reorders
    cohort selection (2026-07-31 arrival-day audit, E-22).
    """
    s = sent[key]
    t = (raw or "").strip()
    if not t:
        s["empty"] += 1
        return math.nan
    v = _maybe_float(t)
    if v is None:
        s["unparseable"] += 1
        _note_null_token(tokens, key, t)
        return math.nan
    if transform is not None:
        v = transform(v)
        if not math.isfinite(v):
            s["unparseable"] += 1
            return math.nan
    lo, hi = window
    if not (lo <= v <= hi):
        win[key] += 1
        return math.nan
    return v


# ====================================================== cohort selection ====

def _dist_summary(values):
    """Frozen per-site distribution summary (``site_stay_counts[stage]``)."""
    arr = np.asarray(sorted(values), dtype=float)
    if arr.size == 0:
        return {"min": None, "q1": None, "median": None, "q3": None,
                "max": None, "mean": None, "n_below_20": 0, "n_below_50": 0,
                "n_below_100": 0, "n_below_500": 0, "n_sites": 0}
    return {"min": float(arr.min()),
            "q1": float(np.percentile(arr, 25)),
            "median": float(np.percentile(arr, 50)),
            "q3": float(np.percentile(arr, 75)),
            "max": float(arr.max()),
            "mean": float(arr.mean()),
            "n_below_20": int((arr < 20).sum()),
            "n_below_50": int((arr < 50).sum()),
            "n_below_100": int((arr < 100).sum()),
            "n_below_500": int((arr < 500).sum()),
            "n_sites": int(arr.size)}


def _spread(values):
    """``{mean, sd, p10, p50, p90}`` over a per-site rate vector."""
    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0:
        return {"mean": None, "sd": None, "p10": None, "p50": None, "p90": None}
    return {"mean": float(arr.mean()), "sd": float(arr.std()),
            "p10": float(np.percentile(arr, 10)),
            "p50": float(np.percentile(arr, 50)),
            "p90": float(np.percentile(arr, 90))}


def _share(k, n):
    """Empty-bin discipline: a rate over a zero denominator is ``None``."""
    return (float(k) / float(n)) if n else None


def _bump(counter, key):
    """Bounded value counter: cardinality past the cap folds into a bucket."""
    if key in counter or len(counter) < _OTHER_CARDINALITY_CAP:
        counter[key] += 1
    else:
        counter["__overflow__"] += 1


class _Quantiles:
    """Chunked exact-quantile accumulator (memory-flat, no value retention).

    Values land in a small Python buffer that is folded into compact float64
    chunks; peak memory is the chunks, not a list of boxed Python floats.
    Exactness matters: the ``-1``-sentinel decision in T-2 is only adopted
    AFTER the histogram proves the column's support is contiguous and
    non-negative, and a sampled p01 cannot prove that.
    """

    __slots__ = ("_buf", "_chunks")
    CHUNK = 65536

    def __init__(self):
        self._buf = []
        self._chunks = []

    def add(self, v):
        self._buf.append(v)
        if len(self._buf) >= self.CHUNK:
            self._chunks.append(np.asarray(self._buf, dtype=np.float64))
            self._buf = []

    def values(self):
        chunks = list(self._chunks)
        if self._buf:
            chunks.append(np.asarray(self._buf, dtype=np.float64))
        if not chunks:
            return np.zeros(0, dtype=np.float64)
        return np.concatenate(chunks)

    def summary(self):
        arr = self.values()
        if arr.size == 0:
            return {"min_positive": None, "p01": None, "p50": None,
                    "p99": None, "max": None}
        pos = arr[arr > 0.0]
        return {"min_positive": float(pos.min()) if pos.size else None,
                "p01": float(np.percentile(arr, 1)),
                "p50": float(np.percentile(arr, 50)),
                "p99": float(np.percentile(arr, 99)),
                "max": float(arr.max())}


def _select_cohort(data_dir, *, profile=False, verbose=False,
                   strict_outcome=True):
    """Scan A over ``patient``: the executable predicates S0-S5 (A.2).

    Returns the selected stay ids (one per hospital admission), the attrition
    ledger for the first six steps, the drop counters, the cross-hospital
    patient diagnostic, the RAW S0 identity counts, and -- when
    ``profile=True`` -- the raw-table categorical/age/offset profile the
    preflight reports.

    The first-stay rule is ``argmin unitvisitnumber``, tie-broken by ``argMAX
    hospitaladmitoffset`` (the offsets are NEGATIVE minutes, so the EARLIEST
    stay has the HIGHEST offset -- the sign trap W7), then ``argmin
    patientunitstayid`` for determinism. NO LOS floor, NO minimum-stays-per-
    hospital filter, NO APACHE filter: each of those three omissions is
    deliberate and argued in EICU-PROTOCOL 2.2-2.4.

    ``strict_outcome=False`` (used by ``preflight`` ONLY) collects unknown
    ``hospitaldischargestatus`` levels into a bounded counter and drops those
    stays instead of raising, so the step whose job is to TABULATE value sets
    against the frozen expectations cannot be aborted by the very drift it
    exists to report (2026-07-31 audit, E-16). ``build_raw`` keeps the raise.

    ``patientunitstayid`` is the PRIMARY KEY of ``patient``: a repeat raises
    ``duplicate-stay-id``. Silently resolving it is not available, because
    scan A (here) would keep the LAST row's label and site while scan B keeps
    the FIRST row's features -- one patient's covariates filed under another
    row's outcome and another row's hospital (2026-07-31 audit, E-11).
    """
    drop = Counter()
    warn = []
    step_stays = Counter()
    step_sites = {s: set() for s in EICU_ATTRITION_STEPS[:6]}
    step_site_counts = {s: Counter() for s in EICU_ATTRITION_STEPS[:6]}
    step_pos = Counter()            # E-9: n_positive per step, hence prevalence
    best = {}                       # admission key -> (sort key, stay id)
    stay_meta = {}                  # stay id -> (site label, admission int, y raw)
    pid_site = {}                   # uniquepid -> first site label seen
    pid_multi = set()
    n_uniquepid = 0
    unknown_status = Counter()
    # RAW S0 identity counts (E-13): EICU_REFERENCE_PATIENTS / _SITES /
    # _UNIT_STAYS are the dataset's WHOLE-TABLE headline numbers, so they must
    # be compared against counts taken BEFORE any predicate. The post-filter
    # counts are a cohort diagnostic and are reported under distinct keys.
    raw_pids = set()
    raw_sites = set()

    prof = None
    if profile:
        prof = {
            "age_tokens": Counter(),
            "gender": Counter(), "ethnicity": Counter(),
            "hospitaldischargestatus": Counter(), "unitdischargestatus": Counter(),
            "hospitaldischargeyear": Counter(), "unittype": Counter(),
            "unitstaytype": Counter(), "hospitaladmitsource": Counter(),
            "unitadmitsource": Counter(), "unitvisitnumber_hist": Counter(),
            "hospitaladmitoffset_sign": Counter(),
            "sent": {k: _new_sentinel_counter() for k in
                     ("age", "admissionheight", "admissionweight",
                      "hospitaladmitoffset")},
            "zero": Counter(),
            "q": {k: _Quantiles() for k in
                  ("age", "admissionheight", "admissionweight",
                   "hospitaladmitoffset")},
        }

    for row in read_table(data_dir, "patient"):
        # ---- S0 raw-unit-stays
        site_token = (row["hospitalid"] or "").strip()
        step_stays["raw-unit-stays"] += 1
        step_sites["raw-unit-stays"].add(site_token)
        step_site_counts["raw-unit-stays"][site_token] += 1
        _raw_site = _maybe_int(site_token)
        if _raw_site is not None:
            raw_sites.add(_raw_site)
        raw_uid = (row["uniquepid"] or "").strip()
        if raw_uid:
            raw_pids.add(raw_uid)
        if (row[EICU_LABEL_COLUMN] or "").strip() == EICU_POSITIVE_LABEL:
            step_pos["raw-unit-stays"] += 1

        if profile:
            for col in ("gender", "ethnicity", "hospitaldischargestatus",
                        "unitdischargestatus", "hospitaldischargeyear",
                        "unittype", "unitstaytype", "hospitaladmitsource",
                        "unitadmitsource"):
                _bump(prof[col], (row[col] or "").strip())
            tok = (row["age"] or "").strip()
            if not tok:
                prof["age_tokens"]["__blank__"] += 1
            elif _maybe_float(tok) is not None:
                prof["age_tokens"]["__numeric__"] += 1
            else:
                _bump(prof["age_tokens"], tok)
            _bump(prof["unitvisitnumber_hist"], (row["unitvisitnumber"] or "").strip())
            off = _maybe_float(row["hospitaladmitoffset"])
            if off is None:
                prof["hospitaladmitoffset_sign"]["unparseable"] += 1
            elif off < 0:
                prof["hospitaladmitoffset_sign"]["negative"] += 1
            elif off == 0:
                prof["hospitaladmitoffset_sign"]["zero"] += 1
            else:
                prof["hospitaladmitoffset_sign"]["positive"] += 1
            for col in ("age", "admissionheight", "admissionweight",
                        "hospitaladmitoffset"):
                t = (row[col] or "").strip()
                if not t:
                    prof["sent"][col]["empty"] += 1
                    continue
                v = _maybe_float(t) if col != "age" else (
                    EICU_AGE_MASK_VALUE if t == EICU_AGE_MASK_TOKEN
                    else _maybe_float(t))
                if v is None:
                    prof["sent"][col]["unparseable"] += 1
                    continue
                if v == EICU_SENTINEL_MISSING:
                    prof["sent"][col]["minus_one"] += 1
                elif v < 0.0 and col != "hospitaladmitoffset":
                    prof["sent"][col]["other_negative"] += 1
                if v == 0.0:
                    prof["zero"][col] += 1
                prof["q"][col].add(v)

        # ---- S1 site-parseable
        try:
            site = EICU_SITE_PREFIX + str(int(site_token))
        except ValueError:
            drop["hospitalid-unparseable"] += 1
            continue
        step_stays["site-parseable"] += 1
        step_sites["site-parseable"].add(site)
        step_site_counts["site-parseable"][site] += 1
        pos = ((row[EICU_LABEL_COLUMN] or "").strip() == EICU_POSITIVE_LABEL)
        if pos:
            step_pos["site-parseable"] += 1

        # ---- S2 outcome-known  ('' DROPS; any third level RAISES)
        status = (row[EICU_LABEL_COLUMN] or "").strip()
        if not status:
            drop["outcome-missing"] += 1
            continue
        if status not in (EICU_POSITIVE_LABEL, EICU_NEGATIVE_LABEL):
            if strict_outcome:
                raise _err("_select_cohort",
                           f"{EICU_LABEL_COLUMN} carries a third level; the "
                           f"label contract admits exactly "
                           f"{{{EICU_POSITIVE_LABEL!r}, "
                           f"{EICU_NEGATIVE_LABEL!r}}} and '' (dropped); "
                           f"build_raw will refuse this extract", status,
                           reason="unknown-outcome-level")
            _bump(unknown_status, status)
            drop["outcome-unknown-level"] += 1
            continue
        step_stays["outcome-known"] += 1
        step_sites["outcome-known"].add(site)
        step_site_counts["outcome-known"][site] += 1
        if pos:
            step_pos["outcome-known"] += 1

        # ---- S3 adult ('> 89' KEPT as 90.0)
        try:
            age = parse_age(row["age"])
        except ValueError:
            age = None
        if age is None:
            drop["age-unparseable"] += 1
            continue
        if age < EICU_MIN_AGE:
            drop["under-age"] += 1
            continue
        step_stays["adult"] += 1
        step_sites["adult"].add(site)
        step_site_counts["adult"][site] += 1
        if pos:
            step_pos["adult"] += 1

        # ---- S4 first-stay per hospital admission
        stay_id = _maybe_int(row["patientunitstayid"])
        if stay_id is None:
            drop["stayid-unparseable"] += 1
            continue
        if stay_id in stay_meta:
            # E-11: the PRIMARY KEY of `patient`. A repeat means a corrupt or
            # concatenated extract; resolving it silently would make scan A
            # (last row wins) and scan B (first row wins) disagree.
            raise _err("_select_cohort",
                       "patientunitstayid is the PRIMARY KEY of `patient` and "
                       "repeats; a duplicate would file one row's features "
                       "under another row's outcome and hospital (scan A keeps "
                       "the last, scan B the first). This is a corrupt or "
                       "concatenated extract, not something to resolve",
                       stay_id, reason="duplicate-stay-id")
        adm_int = _maybe_int(row["patienthealthsystemstayid"])
        if adm_int is None:
            adm_key = f"stay:{stay_id}"      # its own admission, counted below
            drop["admission-id-missing"] += 1
            adm_int = -1
        else:
            adm_key = adm_int
        visit = _maybe_float(row["unitvisitnumber"])
        offset = _maybe_float(row["hospitaladmitoffset"])
        key = (visit if visit is not None else math.inf,
               -offset if offset is not None else math.inf,
               stay_id)
        prev = best.get(adm_key)
        if prev is None or key < prev[0]:
            best[adm_key] = (key, stay_id)
        stay_meta[stay_id] = (site, adm_int, status)

        uid = (row["uniquepid"] or "").strip()
        if uid:
            seen = pid_site.get(uid)
            if seen is None:
                pid_site[uid] = site
                n_uniquepid += 1
            elif seen != site:
                pid_multi.add(uid)

    selected = {}
    for _key, stay_id in best.values():
        selected[stay_id] = stay_meta[stay_id]
    drop["not-first-stay"] = int(step_stays["adult"] - len(selected))

    for stay_id, (site, _adm, y) in selected.items():
        step_stays["first-stay"] += 1
        step_sites["first-stay"].add(site)
        step_site_counts["first-stay"][site] += 1
        step_stays["primary-cohort"] += 1
        step_sites["primary-cohort"].add(site)
        step_site_counts["primary-cohort"][site] += 1
        if y == EICU_POSITIVE_LABEL:
            step_pos["first-stay"] += 1
            step_pos["primary-cohort"] += 1

    if drop.get("admission-id-missing"):
        warn.append(
            f"[MEASURE] {drop['admission-id-missing']} stays carry a blank or "
            f"unparseable patienthealthsystemstayid; each was treated as its "
            f"OWN admission by the first-stay rule (a fallback, not a drop)")

    if unknown_status:
        warn.append(
            f"[MEASURE] E-16: {EICU_LABEL_COLUMN} carries level(s) outside "
            f"{{{EICU_POSITIVE_LABEL!r}, {EICU_NEGATIVE_LABEL!r}, ''}}: "
            f"{dict(sorted(unknown_status.items()))!r}. Those "
            f"{drop['outcome-unknown-level']} stays are DROPPED here so the "
            f"profile can be completed; build_raw WILL raise "
            f"unknown-outcome-level on this extract")

    # E-9: n_positive (hence prevalence) at every step, so the ledger itself
    # shows an outcome-correlated selection instead of hiding it in n_stays.
    attrition = [{"step": s, "n_stays": int(step_stays[s]),
                  "n_sites": len(step_sites[s]),
                  "n_positive": int(step_pos[s]),
                  "prevalence": _share(step_pos[s], step_stays[s])}
                 for s in EICU_ATTRITION_STEPS[:6]]

    cross = {"n_uniquepid": int(n_uniquepid),
             "n_uniquepid_multi_hospital": int(len(pid_multi)),
             "share": _share(len(pid_multi), n_uniquepid),
             "cap": EICU_MAX_CROSS_SITE_PATIENT_SHARE}
    share = cross["share"]
    if share is not None and share > EICU_MAX_CROSS_SITE_PATIENT_SHARE:
        warn.append(
            f"[MEASURE] T-5: {cross['n_uniquepid_multi_hospital']} uniquepid "
            f"({share:.4f} > cap {EICU_MAX_CROSS_SITE_PATIENT_SHARE}) appear at "
            f"more than one hospitalid; assert_site_disjoint compares site "
            f"LABELS only, so these are correlated records across splits. This "
            f"is a LOWER bound (de-identification may split one person across "
            f"several uniquepid) and is disclosed, never filtered -- a filter "
            f"would itself be site-correlated")

    if verbose:
        print(f"[eicu] cohort scan: {step_stays['raw-unit-stays']} raw stays -> "
              f"{len(selected)} primary-cohort stays over "
              f"{len(step_sites['primary-cohort'])} sites; drops={dict(drop)}",
              file=sys.stderr)

    return {"selected": selected, "attrition": attrition, "drop": drop,
            "cross": cross, "site_counts": step_site_counts,
            "n_patient_rows": int(step_stays["raw-unit-stays"]),
            "profile": prof, "warnings": warn,
            "n_healthsystemstays": len(best),
            "unknown_status": dict(sorted(unknown_status.items())),
            "n_uniquepid_raw": len(raw_pids),
            "n_hospitals_raw": len(raw_sites)}


def _prevalence_contrast(y_pos, flag, label):
    """Outcome prevalence in the ``flag`` / ``not flag`` strata, and the ratio.

    ``flag`` is the PRESENCE indicator, so the reported ratio is
    ``prevalence(absent) / prevalence(present)`` -- the direction in which an
    outcome-informative absence channel shows up (2026-07-31 audit, E-9).
    """
    y = np.asarray(y_pos, dtype=bool)
    f = np.asarray(flag, dtype=bool)
    n1, n0 = int(f.sum()), int((~f).sum())
    p1 = float(y[f].mean()) if n1 else None
    p0 = float(y[~f].mean()) if n0 else None
    ratio = (p0 / p1) if (p0 is not None and p1 not in (None, 0.0)) else None
    return {"feature": label,
            "n_present": n1, "n_absent": n0,
            "prevalence_present": None if p1 is None else round(p1, 6),
            "prevalence_absent": None if p0 is None else round(p0, 6),
            "prevalence_ratio": None if ratio is None else round(ratio, 4),
            "cap": EICU_MAX_OUTCOME_PREVALENCE_RATIO,
            "min_stratum": EICU_MIN_OUTCOME_STRATUM,
            "gate_applies": bool(n1 >= EICU_MIN_OUTCOME_STRATUM
                                 and n0 >= EICU_MIN_OUTCOME_STRATUM)}


def _outcome_missingness(y_raw, aps_present, apv_present):
    """The two whole-table presence flags, cross-tabulated against the outcome."""
    y_pos = np.asarray([v == EICU_POSITIVE_LABEL for v in y_raw], dtype=bool)
    return {"aps_present": _prevalence_contrast(y_pos, aps_present, "aps_present"),
            "apv_present": _prevalence_contrast(y_pos, apv_present, "apv_present")}


def outcome_screen(x_raw, meta, *, names=None, review=EICU_FEATURE_AUC_REVIEW):
    """Screen EVERY allowlisted feature against the outcome, before certifying.

    The denylist applies a "leak-suspect: timing relative to outcome
    unverified" standard to two ``apachePatientResult`` columns; the same
    standard has to reach the nine ``apachePredVar`` treatment/intervention
    flags (``activetx`` above all -- active treatment versus comfort measures
    is decided DURING the stay and is adjacent to death by definition), and
    nothing in the DDL comments can settle it on a dataset whose sentinel
    convention the DDL already gets wrong. So it is settled from the DATA,
    before any certificate exists (2026-07-31 audit, E-19).

    Returns an AGGREGATE-ONLY dict: per feature, the outcome prevalence by
    stratum (binary columns) or in the top vs bottom decile (continuous), the
    univariate rank AUC, and a ``flagged`` list of every feature whose
    ``|AUC - 0.5|`` puts it past ``review``. NaN in ``x_raw`` is treated as its
    own stratum for binary columns and ignored for the decile contrast, so the
    screen works on the RAW (pre-imputation) matrix -- which is the only place
    the missingness channel is still visible.
    """
    x = np.asarray(x_raw, dtype=np.float64)
    names = list(FEATURE_NAMES if names is None else names)
    y = np.asarray([v == EICU_POSITIVE_LABEL for v in meta["y_raw"]], dtype=bool)
    if x.shape[0] != y.shape[0] or x.shape[1] != len(names):
        raise _err("outcome_screen",
                   "x_raw / meta['y_raw'] / names disagree on shape",
                   (x.shape, y.shape, len(names)),
                   reason="feature-width-mismatch")
    out, flagged = {}, []
    base = float(y.mean()) if y.size else None
    for j, name in enumerate(names):
        col = x[:, j]
        good = np.isfinite(col)
        entry = {"kind": None, "auc": None, "n_finite": int(good.sum()),
                 "hi": None, "lo": None}
        if good.sum() >= 2 and y[good].any() and not y[good].all():
            auc = _rank_auc(col[good], y[good])
            entry["auc"] = None if auc is None else round(auc, 6)
        vals = col[good]
        uniq = np.unique(vals) if vals.size else vals
        if uniq.size <= 2:
            entry["kind"] = "binary"
            hi = good & (col > 0.0)
            lo = good & (col <= 0.0)
            entry["hi"] = {"n": int(hi.sum()),
                           "prevalence": _share(int(y[hi].sum()), int(hi.sum()))}
            entry["lo"] = {"n": int(lo.sum()),
                           "prevalence": _share(int(y[lo].sum()), int(lo.sum()))}
        elif vals.size >= 10:
            entry["kind"] = "continuous"
            q10, q90 = (float(v) for v in np.percentile(vals, [10.0, 90.0]))
            hi = good & (col >= q90)
            lo = good & (col <= q10)
            entry["hi"] = {"n": int(hi.sum()), "cut": round(q90, 6),
                           "prevalence": _share(int(y[hi].sum()), int(hi.sum()))}
            entry["lo"] = {"n": int(lo.sum()), "cut": round(q10, 6),
                           "prevalence": _share(int(y[lo].sum()), int(lo.sum()))}
        else:
            entry["kind"] = "degenerate"
        out[name] = entry
        if entry["auc"] is not None and abs(entry["auc"] - 0.5) > (review - 0.5):
            flagged.append({"feature": name, "auc": entry["auc"]})
    flagged.sort(key=lambda d: (-abs(d["auc"] - 0.5), d["feature"]))
    return {"base_prevalence": None if base is None else round(base, 6),
            "review_auc": review, "n_features": len(names),
            "features": out, "flagged": flagged,
            "outcome_missingness": _outcome_missingness(
                meta["y_raw"], meta["aps_present"], meta["apv_present"])}


def _rank_auc(v, y):
    """Tie-averaged Mann-Whitney AUC; ``None`` when either class is absent."""
    v = np.asarray(v, dtype=np.float64)
    y = np.asarray(y, dtype=bool)
    n = int(v.shape[0])
    n1 = int(y.sum())
    n0 = n - n1
    if n1 == 0 or n0 == 0:
        return None
    order = np.argsort(v, kind="mergesort")
    s = v[order]
    ranks = np.empty(n, dtype=np.float64)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and s[j + 1] == s[i]:
            j += 1
        ranks[order[i:j + 1]] = 0.5 * (i + j) + 1.0
        i = j + 1
    return float((ranks[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


# =============================================================== build ======

def build_raw(data_dir, *, arm="primary", strict_levels=True, verbose=True):
    """``(x_raw, feature_names, meta)`` -- the deny-by-default feature build.

    ``x_raw`` is ``(n, EICU_N_FEATURES)`` float64 with NaN in every IMPUTABLE
    feature column; indicator/one-hot/presence columns are already finite 0/1.
    ``x_raw`` is NOT admissible to ``make_cohort`` -- call ``impute()`` first
    (which is also where the transductive-leak rule lives).

    Three streaming passes, memory-bounded:

      1. ``patient`` -> cohort predicates S0-S5, the patient feature block
         written straight into the preallocated matrix, and ``stay_id ->
         row_index`` built as a ``dict[int, int]``. No column strings are
         retained. (Two scans of the 9.9 MB gz table: the first-stay rule
         cannot be resolved until every stay of an admission has been seen, so
         scan A selects and scan B fills. Retaining candidate feature values
         instead would cost the full 200k x 161 matrix -- more memory than the
         cohort it is selecting.)
      2. ``apacheApsVar``, ``apachePredVar`` -> per-row lookup + fill of the
         24/19 numeric blocks and their siblings; dedup by min surrogate id.
      3. ``apachePatientResult`` -> COMPARATOR ONLY (version preference,
         ``float()`` of ``predictedhospitalmortality``; ``'-1'`` -> NaN).

    Raises ``EicuError``: unknown arm (``reason=unknown-arm``); a third outcome
    level (``reason=unknown-outcome-level``); level drift over the cap when
    ``strict_levels=True`` (``reason=categorical-level-drift``); an allowlisted
    numeric with negative mass NOT at exactly ``-1.0``
    (``reason=unexpected-negative-sentinel``); empty cohort
    (``reason=empty-cohort``).
    Asserts ``x_raw.shape == (n, len(FEATURE_NAMES))`` and
    ``len(FEATURE_NAMES) == EICU_N_FEATURES``.
    ``verbose`` prints ONE line to ``sys.stderr`` prefixed ``'[eicu] '``.

    ``meta`` keys (frozen): ``n, arm, n_features, site_raw, y_raw, stay_id,
    admission_id, patient_id, aps_present, apv_present,
    comparator_apache_version, comparator_predicted_mortality, imputable_cols,
    missing_counts, sentinel_counts, window_clipped_counts, unit_conversions,
    unparseable_tokens, outcome_missingness, categorical_other_counts,
    categorical_other_shares, attrition, drop_counts, dedup_counts,
    cross_site_patients, site_meta`` -- plus ``warnings``, which A.5.6 and T-14
    mandate by name.

    Three aborts beyond the frozen set, all added 2026-07-31: a NULL token that
    is not ``''`` (``unrecognised-null-token``, E-15), a duplicate
    ``patientunitstayid`` (``duplicate-stay-id``, E-11), and OUTCOME-informative
    APACHE-row absence in the primary arm (``outcome-informative-missingness``,
    E-9). Every ``attrition`` entry additionally carries ``n_positive`` and
    ``prevalence``.
    """
    if arm not in EICU_ARMS:
        raise _err("build_raw", f"arm must be one of {EICU_ARMS!r}", arm,
                   reason="unknown-arm")
    if len(FEATURE_NAMES) != EICU_N_FEATURES:
        raise _err("build_raw",
                   f"FEATURE_NAMES width {len(FEATURE_NAMES)} != "
                   f"EICU_N_FEATURES {EICU_N_FEATURES}",
                   reason="feature-width-mismatch")
    assert_no_leak_columns(FEATURE_NAMES)

    sel = _select_cohort(data_dir, profile=False, verbose=False)
    selected = sel["selected"]
    if not selected:
        raise _err("build_raw",
                   "the primary cohort is empty after S0-S5; nothing to build",
                   data_dir, reason="empty-cohort")

    n = len(selected)
    x = np.zeros((n, len(FEATURE_NAMES)), dtype=np.float64)
    x[:, _PARENT_COLS] = np.nan            # every imputable parent starts missing
    x[:, _MISSING_COLS] = 1.0              # ... and every sibling starts at 1

    sent = {}
    for c in EICU_PATIENT_NUMERIC:
        sent[c] = _new_sentinel_counter()
    for c in EICU_APS_NUMERIC:
        sent["aps_" + c] = _new_sentinel_counter()
    for c in EICU_APV_NUMERIC:
        sent["apv_" + c] = _new_sentinel_counter()
    unit = Counter()
    win = Counter()
    null_tokens = {}                       # E-15: bounded unparseable-token sample
    other_counts = {col: 0 for col, _ in EICU_CATEGORICALS}
    other_values = {col: Counter() for col, _ in EICU_CATEGORICALS}
    warn = list(sel["warnings"])

    site_raw, y_raw, patient_id = [], [], []
    stay_arr = np.zeros(n, dtype=np.int64)
    adm_arr = np.zeros(n, dtype=np.int64)
    row_of = {}

    # ---- pass 1 (scan B): the patient feature block -------------------------
    i = 0
    for row in read_table(data_dir, "patient"):
        stay_id = _maybe_int(row["patientunitstayid"])
        if stay_id is None or stay_id not in selected:
            continue
        if stay_id in row_of:
            # Unreachable: scan A already raised duplicate-stay-id. Kept as a
            # belt-and-braces raise so the two scans can never silently
            # disagree about which duplicate wins (2026-07-31 audit, E-11).
            raise _err("build_raw",
                       "patientunitstayid repeats between the two cohort scans",
                       stay_id, reason="duplicate-stay-id")
        site, adm_int, status = selected[stay_id]
        row_of[stay_id] = i
        stay_arr[i] = stay_id
        adm_arr[i] = adm_int
        site_raw.append(site)
        y_raw.append(status)
        patient_id.append((row["uniquepid"] or "").strip())

        token = (row["age"] or "").strip()
        age = parse_age(token)             # S3 guarantees this parses and is >= 18
        x[i, _IDX_PATIENT[0][0]] = age
        x[i, _IDX_PATIENT[0][1]] = 0.0
        if token == EICU_AGE_MASK_TOKEN:
            x[i, _IDX_AGE_MASKED] = 1.0

        for (col, window, raw, transform) in (
                ("admissionheight", EICU_WINDOW_HEIGHT_CM,
                 row["admissionheight"], None),
                ("admissionweight", EICU_WINDOW_WEIGHT_KG,
                 row["admissionweight"], None),
                ("pre_icu_hours", EICU_WINDOW_PRE_ICU_HRS,
                 row["hospitaladmitoffset"], lambda v: -v / 60.0)):
            j = EICU_PATIENT_NUMERIC.index(col)
            v = _parse_windowed(raw, col, window, sent, win, transform,
                                null_tokens)
            if math.isfinite(v):
                x[i, _IDX_PATIENT[j][0]] = v
                x[i, _IDX_PATIENT[j][1]] = 0.0

        for col, level_idx, fallback in _IDX_CAT:
            value = (row[col] or "").strip()
            j = level_idx.get(value)
            if j is None:
                j = level_idx[fallback]
                other_counts[col] += 1
                _bump(other_values[col], value)
            x[i, j] = 1.0
        i += 1

    if i != n:                             # a selected stay vanished between scans
        raise _err("build_raw",
                   f"scan B filled {i} rows for {n} selected stays; the extract "
                   f"changed under the ETL", data_dir, reason="empty-cohort")

    # ---- categorical drift gate (T-7) --------------------------------------
    other_shares = {col: _share(other_counts[col], n) for col, _ in EICU_CATEGORICALS}
    for col, _levels in EICU_CATEGORICALS:
        share = other_shares[col] or 0.0
        top = sorted(((v, c) for v, c in other_values[col].items()),
                     key=lambda kv: (-kv[1], kv[0]))[:8]
        if share > EICU_MAX_OTHER_SHARE:
            msg = (f"eicu_etl.build_raw: categorical level drift in {col!r}: "
                   f"{share:.3f} of rows fell to the OTHER bucket "
                   f"(cap {EICU_MAX_OTHER_SHARE}); top unlisted values {top!r} "
                   f"-- the frozen level tuple is a pre-registered protocol "
                   f"constant; widen it in SPEC.md and constants, do not let "
                   f"the head learn a drift bucket "
                   f"(reason=categorical-level-drift)")
            if strict_levels:
                raise EicuError(msg)
            warn.append("[MEASURE] " + msg)

    # ---- pass 2: apacheApsVar + apachePredVar ------------------------------
    dedup = Counter()
    aps_present = np.zeros(n, dtype=bool)
    apv_present = np.zeros(n, dtype=bool)
    join_tokens = {}                       # E-21: bounded sample of bad key tokens
    join_counts = {}
    for table, id_col, cols, idx, prefix, present in (
            ("apacheApsVar", "apacheapsvarid", EICU_APS_NUMERIC, _IDX_APS,
             "aps_", aps_present),
            ("apachePredVar", "apachepredvarid", EICU_APV_NUMERIC, _IDX_APV,
             "apv_", apv_present)):
        kept = {}
        n_rows_t = 0
        n_badkey = 0
        for row in read_table(data_dir, table):
            n_rows_t += 1
            stay_id = _maybe_int(row["patientunitstayid"])
            if stay_id is None:
                # E-21: a non-empty key that fails integer parse is a FORMAT
                # artifact (pandas writes '141258.0'), and skipping it unread
                # unlinks the row from every downstream gate.
                tok = (row["patientunitstayid"] or "").strip()
                if tok:
                    n_badkey += 1
                    _note_null_token(join_tokens, table, tok)
                continue
            r = row_of.get(stay_id)
            if r is None:
                continue
            sid = _maybe_int(row[id_col])
            sid = math.inf if sid is None else sid
            if r in kept:
                dedup[table] += 1
                if sid >= kept[r]:         # keep min(surrogate id), report the rest
                    continue
            kept[r] = sid
            present[r] = True
            for k, col in enumerate(cols):
                key = prefix + col
                v = _parse_apache_cell(col, row[col], key, sent, unit, win,
                                       null_tokens)
                a, b = idx[k]
                if math.isfinite(v):
                    x[r, a] = v
                    x[r, b] = 0.0
                else:
                    x[r, a] = np.nan
                    x[r, b] = 1.0
        join_counts[table] = {"n_rows": int(n_rows_t),
                              "n_key_unparseable": int(n_badkey)}
        if n_rows_t and (n_badkey / n_rows_t) > EICU_MAX_UNPARSEABLE_SHARE:
            top = sorted(join_tokens.get(table, Counter()).items(),
                         key=lambda kv: (-kv[1], kv[0]))[:4]
            raise _err(
                "build_raw",
                f"{table}.patientunitstayid fails integer parse in more than "
                f"EICU_MAX_UNPARSEABLE_SHARE={EICU_MAX_UNPARSEABLE_SHARE} of "
                f"rows ({n_badkey} of {n_rows_t}) -- a float or "
                f"scientific-notation re-export of the JOIN KEY (pandas "
                f"writes '141258.0') unlinks the whole table: every row is "
                f"skipped UNREAD, so no cell-level gate can fire, all "
                f"{prefix}* columns collapse to the imputation fallback, and "
                f"the row counts still match the reference (2026-07-31 "
                f"audit, E-21) (token -> count)",
                [[t, int(c)] for t, c in top],
                reason="unparseable-join-key")
    x[:, _IDX_APS_PRESENT] = aps_present.astype(np.float64)
    x[:, _IDX_APV_PRESENT] = apv_present.astype(np.float64)

    # ---- unrecognised-sentinel abort (T-2; threshold = amendment A6) -------
    # The cells ALWAYS become missing (_parse_apache_cell maps v < 0 to NaN).
    # The raise is a look-at-this gate, and it fires once a column's share of
    # such cells is material: EICU_MAX_UNPARSEABLE_SHARE, the same frozen
    # constant E-15/E-21 use. Sub-threshold mass is reported, not aborted --
    # the released extract carries ONE such cell in ~4.1M
    # (apacheApsVar.urine = -11245.5648) against an otherwise contiguous
    # non-negative support, and refusing the study over it would be theatre.
    # A6 is POST-HOC (the extract had been read); EICU-PROTOCOL.md SS0 requires
    # every number derived from this extract to carry that label.
    negatives = {k: v["other_negative"] for k, v in sent.items()
                 if k.startswith(("aps_", "apv_")) and v["other_negative"]}
    over_neg = {k: {"n_other_negative": int(v), "share": round(v / n, 8)}
                for k, v in negatives.items()
                if n and (v / n) > EICU_MAX_UNPARSEABLE_SHARE}
    if over_neg:
        raise _err("build_raw",
                   f"allowlisted APACHE numeric(s) carry negative mass NOT at "
                   f"exactly -1.0 in more than "
                   f"EICU_MAX_UNPARSEABLE_SHARE={EICU_MAX_UNPARSEABLE_SHARE} "
                   f"of cohort rows; every allowlisted column has non-negative "
                   f"physiological support, so this is an UNRECOGNISED sentinel "
                   f"at a material rate and must abort rather than flow into "
                   f"the matrix (column -> count/share)",
                   dict(sorted(over_neg.items())),
                   reason="unexpected-negative-sentinel")
    if negatives:
        warn.append(
            f"[MEASURE] T-2/A6: negative mass NOT at exactly -1.0, below the "
            f"{EICU_MAX_UNPARSEABLE_SHARE} abort threshold, mapped to missing "
            f"in {dict(sorted(negatives.items()))!r} over {n} cohort rows. "
            f"A6 is the one POST-HOC protocol amendment; label every number "
            f"derived from this extract accordingly")

    # ---- unrecognised-NULL-token abort (E-15/E-22) -------------------------
    # The -1 gate protects one direction only. A re-export whose NULL token is
    # Postgres text-format '\N' (or 'NULL'/'NA') makes every allowlisted
    # numeric 100% missing, every __missing sibling the constant 1.0, and 86
    # of 161 coefficients exactly 0.0 -- while build_raw SUCCEEDS and
    # `warnings` stays empty. The token is named, not just counted. The gate
    # covers EVERY key in `sent`, not only aps_/apv_: the patient block's
    # pre_icu_hours is fed by hospitaladmitoffset, the first-stay tie-breaker,
    # so a silent zeroing there also silently reorders cohort selection.
    unparseable = {}
    for key, counter in sent.items():
        k = counter["unparseable"]
        if k and n and (k / n) > EICU_MAX_UNPARSEABLE_SHARE:
            top = sorted(null_tokens.get(key, Counter()).items(),
                         key=lambda kv: (-kv[1], kv[0]))[:4]
            unparseable[key] = {"n_unparseable": int(k),
                                "share": round(k / n, 6),
                                "top_tokens": [[t, int(c)] for t, c in top]}
    if unparseable:
        raise _err("build_raw",
                   f"allowlisted numeric(s) are unparseable in more "
                   f"than EICU_MAX_UNPARSEABLE_SHARE="
                   f"{EICU_MAX_UNPARSEABLE_SHARE} of cohort rows -- this is an "
                   f"UNRECOGNISED NULL TOKEN (the MIT-LCP loader is NULL '', "
                   f"but a Postgres text-format re-export writes '\\N'), and "
                   f"letting it flow would leave the column constant at the "
                   f"imputation fallback and its __missing sibling constant at "
                   f"1.0 while a certificate is issued about a model that saw "
                   f"no physiology (E-15; patient numerics E-22) "
                   f"(column -> tokens)",
                   dict(sorted(unparseable.items())),
                   reason="unrecognised-null-token")

    # ---- outcome-informative-missingness abort (E-9) -----------------------
    outcome_missing = _outcome_missingness(y_raw, aps_present, apv_present)

    # ---- apache-coverage-collapse abort (E-21, leg 2) ----------------------
    # E-9's ratio gate needs BOTH strata at EICU_MIN_OUTCOME_STRATUM, so a
    # TOTALLY absent or unlinked block turns gate_applies false and certifies
    # what partial absence would abort. When the cohort is large enough that
    # the E-9 gate is supposed to be evaluable, a presence stratum that cannot
    # reach the floor is a broken extract, not a legitimate corpus. The scale
    # condition keeps the gate silent on tiny single-trap test corpora.
    if arm == "primary" and n >= EICU_MIN_OUTCOME_STRATUM:
        starved = {k: {"n_present": v["n_present"], "n_absent": v["n_absent"]}
                   for k, v in outcome_missing.items()
                   if v["n_present"] < EICU_MIN_OUTCOME_STRATUM}
        if starved:
            raise _err(
                "build_raw",
                f"the APACHE block is absent or UNLINKED for (nearly) the "
                f"whole cohort: a presence stratum cannot reach "
                f"EICU_MIN_OUTCOME_STRATUM={EICU_MIN_OUTCOME_STRATUM} although "
                f"the cohort has {n} stays, so the E-9 "
                f"outcome-informative-missingness gate is UNEVALUABLE and 89 "
                f"of 161 feature columns are constant. Demonstrated routes: a "
                f"float/scientific join-key re-export, a header-only child "
                f"table, a key mismatch that keeps every ROW COUNT intact "
                f"(EICU_REFERENCE_ROW_COUNTS cannot see it). Fix the extract "
                f"or the join; do NOT relax the floor (2026-07-31 audit, "
                f"E-21) (flag -> strata)",
                dict(sorted(starved.items())),
                reason="apache-coverage-collapse")

    if arm == "primary":
        offenders = {k: v for k, v in outcome_missing.items()
                     if v["gate_applies"] and v["prevalence_ratio"] is not None
                     and v["prevalence_ratio"] > EICU_MAX_OUTCOME_PREVALENCE_RATIO}
        if offenders:
            raise _err(
                "build_raw",
                f"APACHE-row ABSENCE is OUTCOME-informative, not merely "
                f"site-informative: the day-1 window does not close for a stay "
                f"that ends because the patient died, so the presence flags and "
                f"the 43 __missing siblings are a partial outcome proxy with no "
                f"column name -- invisible to EICU_LEAK_DENYLIST, to the -1 "
                f"gate and to the drift gate. Observed absent:present outcome "
                f"prevalence ratio exceeds "
                f"EICU_MAX_OUTCOME_PREVALENCE_RATIO="
                f"{EICU_MAX_OUTCOME_PREVALENCE_RATIO}. Do NOT widen the cap: "
                f"either run arm='apache-linked' (which restricts to stays "
                f"whose day-1 window is complete and pays the immortal-time "
                f"cost EXPLICITLY) or drop the presence flags from the "
                f"allowlist -- both are SPEC changes (flag -> strata)",
                {k: {kk: vv for kk, vv in v.items() if kk != "gate_applies"}
                 for k, v in sorted(offenders.items())},
                reason="outcome-informative-missingness")

    # ---- pass 3: apachePatientResult (COMPARATOR ONLY) ---------------------
    big = np.iinfo(np.int64).max
    res_seen = {v: np.zeros(n, dtype=bool) for v in EICU_APACHE_VERSION_PREFERENCE}
    res_id = {v: np.full(n, big, dtype=np.int64) for v in EICU_APACHE_VERSION_PREFERENCE}
    res_pred = {v: np.full(n, np.nan) for v in EICU_APACHE_VERSION_PREFERENCE}
    result_linked = np.zeros(n, dtype=bool)
    version_counts = Counter()
    n_rows_res = 0
    n_badkey_res = 0
    for row in read_table(data_dir, "apachePatientResult"):
        n_rows_res += 1
        stay_id = _maybe_int(row["patientunitstayid"])
        if stay_id is None:
            tok = (row["patientunitstayid"] or "").strip()
            if tok:
                n_badkey_res += 1
                _note_null_token(join_tokens, "apachePatientResult", tok)
            continue
        r = row_of.get(stay_id)
        if r is None:
            continue
        result_linked[r] = True
        version = (row["apacheversion"] or "").strip()
        version_counts[version] += 1
        if version not in res_seen:
            continue
        sid = _maybe_int(row["apachepatientresultsid"])
        sid = big if sid is None else sid
        if res_seen[version][r]:
            dedup["apachePatientResult"] += 1
            if sid >= res_id[version][r]:
                continue
        res_seen[version][r] = True
        res_id[version][r] = sid
        # VARCHAR(50) holding a probability: float() FIRST, then compare.
        # A string comparison ('-1' > '0') is a bug (T-9).
        pv = _maybe_float(row["predictedhospitalmortality"])
        res_pred[version][r] = (np.nan if pv is None
                                or pv == EICU_SENTINEL_MISSING else pv)

    join_counts["apachePatientResult"] = {
        "n_rows": int(n_rows_res), "n_key_unparseable": int(n_badkey_res)}
    if n_rows_res and (n_badkey_res / n_rows_res) > EICU_MAX_UNPARSEABLE_SHARE:
        top = sorted(join_tokens.get("apachePatientResult", Counter()).items(),
                     key=lambda kv: (-kv[1], kv[0]))[:4]
        raise _err(
            "build_raw",
            f"apachePatientResult.patientunitstayid fails integer parse in "
            f"more than EICU_MAX_UNPARSEABLE_SHARE="
            f"{EICU_MAX_UNPARSEABLE_SHARE} of rows ({n_badkey_res} of "
            f"{n_rows_res}) -- the comparator table is UNLINKED by a join-key "
            f"format artifact (2026-07-31 audit, E-21) (token -> count)",
            [[t, int(c)] for t, c in top],
            reason="unparseable-join-key")

    comp_version = [""] * n
    comp_pred = np.full(n, np.nan)
    for v in EICU_APACHE_VERSION_PREFERENCE:          # ('IVa', 'IV')
        take = res_seen[v] & np.array([cv == "" for cv in comp_version])
        for r in np.nonzero(take)[0]:
            comp_version[int(r)] = v
            comp_pred[int(r)] = res_pred[v][int(r)]

    # ---- attrition: the APACHE steps are DIAGNOSTIC, never a filter --------
    site_arr = np.asarray(site_raw, dtype=object)
    complete = aps_present & apv_present & np.isfinite(comp_pred)
    linked = aps_present & apv_present
    y_pos_arr = np.asarray([v == EICU_POSITIVE_LABEL for v in y_raw], dtype=bool)
    attrition = list(sel["attrition"])
    for step, mask in (("apache-aps-linked", aps_present),
                       ("apache-result-linked", result_linked),
                       ("apache-complete-arm", complete)):
        n_step = int(mask.sum())
        n_pos_step = int(y_pos_arr[mask].sum())
        attrition.append({"step": step, "n_stays": n_step,
                          "n_sites": len(set(site_arr[mask].tolist())),
                          "n_positive": n_pos_step,
                          "prevalence": _share(n_pos_step, n_step)})

    # E-9: the ledger's own prevalence collapse is the headline diagnostic for
    # outcome-informative APACHE absence. n_stays alone cannot show it.
    prev_primary = attrition[5]["prevalence"]
    prev_aps = attrition[6]["prevalence"]
    if prev_primary and prev_aps and prev_aps < prev_primary:
        warn.append(
            f"[MEASURE] E-9: prevalence falls from {prev_primary:.4f} at "
            f"primary-cohort to {prev_aps:.4f} at apache-aps-linked -- APACHE-row "
            f"absence is OUTCOME-correlated, not only site-correlated; the day-1 "
            f"window does not close for a stay that ends because the patient "
            f"died. aps_present/apv_present and the 43 __missing siblings carry "
            f"that signal and no name denylist can see it")

    prim_sites = attrition[5]["n_sites"]
    res_sites = attrition[7]["n_sites"]
    if res_sites < prim_sites:
        warn.append(
            f"[MEASURE] T-4: apachePatientResult coverage deletes "
            f"{prim_sites - res_sites} of {prim_sites} sites "
            f"({res_sites} retained). The primary arm does NOT restrict; any "
            f"arm that does refers to a DIFFERENT site population, and audit "
            f"V1's estimand is a site-population average")
    if prim_sites < EICU_REFERENCE_SITES:
        warn.append(
            f"[MEASURE] F-E: the primary cohort spans {prim_sites} sites, not "
            f"{EICU_REFERENCE_SITES}; every guarantee sentence must be "
            f"re-scoped to the surviving site population BY NAME")

    # ---- arm subsetting (declared sensitivity arms, never the headline) ----
    # `apache-linked` (E-9) restricts to stays whose day-1 window is COMPLETE,
    # making the presence flags constant and information-free. It is an
    # IMMORTAL-TIME-SELECTED cohort -- that is the price, it is stated, and its
    # n_sites and prevalence are reported beside the primary arm's wherever it
    # appears. `apache-complete` additionally requires the comparator and so
    # additionally deletes the ~18 zero-coverage hospitals (T-4).
    if arm in ("apache-linked", "apache-complete"):
        mask = linked if arm == "apache-linked" else complete
        keep = np.nonzero(mask)[0]
        if keep.size == 0:
            raise _err("build_raw",
                       f"the {arm} arm is empty (no stay satisfies its "
                       f"linkage requirement)", data_dir,
                       reason="empty-cohort")
        x = x[keep]
        site_raw = [site_raw[int(r)] for r in keep]
        y_raw = [y_raw[int(r)] for r in keep]
        patient_id = [patient_id[int(r)] for r in keep]
        stay_arr = stay_arr[keep]
        adm_arr = adm_arr[keep]
        aps_present = aps_present[keep]
        apv_present = apv_present[keep]
        comp_version = [comp_version[int(r)] for r in keep]
        comp_pred = comp_pred[keep]
        n = int(keep.size)

    if x.shape != (n, len(FEATURE_NAMES)):
        raise _err("build_raw", f"matrix shape {x.shape} != "
                   f"{(n, len(FEATURE_NAMES))}", reason="feature-width-mismatch")

    nan_mask = np.isnan(x)
    imputable_cols = sorted(int(j) for j in np.nonzero(nan_mask.any(axis=0))[0])
    stray = [FEATURE_NAMES[int(j)] for j in np.nonzero(nan_mask.any(axis=0))[0]
             if int(j) not in _PARENT_NAME]
    if stray:
        raise _err("build_raw",
                   "NaN reached a column that is not an imputable parent "
                   "(indicator/one-hot/presence columns must be finite)", stray,
                   reason="nonfinite-after-impute")
    if np.isinf(x).any():
        raise _err("build_raw", "infinite value in the raw feature matrix",
                   reason="nonfinite-after-impute")
    missing_counts = {FEATURE_NAMES[int(j)]: int(nan_mask[:, int(j)].sum())
                      for j in _PARENT_COLS}
    if missing_counts.get("age", 0) == 0:
        warn.append(
            "[MEASURE] T-14: 'age__missing' is identically zero by construction "
            "(S3 drops unparseable ages), so the column is near-constant, hits "
            "model.SD_REL_TOL's guard, and carries a zero attribution")

    site_meta = _site_meta(site_raw, y_raw, aps_present, apv_present)
    # Recomputed POST-subset: in the apache-linked arm both flags are constant
    # by construction, and the reported contrast must say so rather than repeat
    # the primary arm's number.
    outcome_missingness = _outcome_missingness(y_raw, aps_present, apv_present)

    meta = {
        "n": int(n), "arm": arm, "n_features": len(FEATURE_NAMES),
        "site_raw": site_raw, "y_raw": y_raw,
        "stay_id": stay_arr, "admission_id": adm_arr, "patient_id": patient_id,
        "aps_present": aps_present, "apv_present": apv_present,
        "comparator_apache_version": comp_version,
        "comparator_predicted_mortality": comp_pred,
        "imputable_cols": imputable_cols,
        "missing_counts": missing_counts,
        "sentinel_counts": {k: dict(v) for k, v in sorted(sent.items())},
        "window_clipped_counts": dict(sorted(win.items())),
        "unit_conversions": dict(sorted(unit.items())),
        "unparseable_tokens": {k: dict(sorted(v.items()))
                               for k, v in sorted(null_tokens.items())},
        "join_key_unparseable": {k: dict(v) for k, v
                                 in sorted(join_counts.items())},
        "outcome_missingness": outcome_missingness,
        "categorical_other_counts": dict(other_counts),
        "categorical_other_shares": other_shares,
        "attrition": attrition,
        "drop_counts": dict(sorted(sel["drop"].items())),
        "dedup_counts": dict(sorted(dedup.items())),
        "cross_site_patients": sel["cross"],
        "site_meta": site_meta,
        "warnings": warn,
    }
    if verbose:
        print(f"[eicu] arm={arm}: {n} stays x {x.shape[1]} features over "
              f"{len(site_meta)} sites; imputable={len(imputable_cols)} cols; "
              f"aps={int(aps_present.sum())} apv={int(apv_present.sum())} "
              f"comparator={int(np.isfinite(comp_pred).sum())}; "
              f"dedup={dict(dedup)}", file=sys.stderr)
    return x, list(FEATURE_NAMES), meta


def _site_meta(site_raw, y_raw, aps_present, apv_present):
    """Per-site aggregate strata (<= 208 entries; aggregate-only by shape)."""
    n_stays = Counter()
    n_pos = Counter()
    n_aps = Counter()
    n_apv = Counter()
    for k, s in enumerate(site_raw):
        n_stays[s] += 1
        if y_raw[k] == EICU_POSITIVE_LABEL:
            n_pos[s] += 1
        if bool(aps_present[k]):
            n_aps[s] += 1
        if bool(apv_present[k]):
            n_apv[s] += 1
    return {s: {"n_stays": int(n_stays[s]),
                "n_positive": int(n_pos[s]),
                "prevalence": _share(n_pos[s], n_stays[s]),
                "aps_coverage": _share(n_aps[s], n_stays[s]),
                "apv_coverage": _share(n_apv[s], n_stays[s])}
            for s in sorted(n_stays)}


# ============================================================== impute ======

def impute(x_raw, fit_idx, *, verbose=False):
    """Mean-impute every NaN with column means computed on ``x_raw[fit_idx]`` ONLY.

    ``fit_idx`` MUST be the S_train row indices. Computing the mean on the
    pooled matrix would let the target pool's covariate distribution into the
    training features -- a transductive leak that no downstream gate catches. A
    column that is entirely NaN within ``fit_idx`` falls back to
    ``EICU_IMPUTE_FALLBACK = 0.0``, counted.

    Returns ``(x, fill)`` where ``x`` is finite float64 and ``fill`` is
    ``{feature_name: value_used}`` (the determinism record; it goes into
    provenance). Raises ``EicuError`` (``reason=impute-fit-empty``) on an empty
    ``fit_idx`` and (``reason=nonfinite-after-impute``) if any NaN/inf survives.
    """
    x_raw = np.asarray(x_raw, dtype=np.float64)
    fit = np.asarray(fit_idx, dtype=int).ravel()
    if fit.size == 0:
        raise _err("impute",
                   "fit_idx is empty; imputation means MUST come from S_train "
                   "rows (a pooled-matrix mean is a transductive leak)",
                   fit.shape, reason="impute-fit-empty")
    if fit.min() < 0 or fit.max() >= x_raw.shape[0]:
        raise _err("impute", "fit_idx out of range for x_raw",
                   (int(fit.min()), int(fit.max()), x_raw.shape[0]),
                   reason="impute-fit-empty")

    x = x_raw.copy()
    names = (FEATURE_NAMES if x.shape[1] == len(FEATURE_NAMES)
             else tuple(f"col{j}" for j in range(x.shape[1])))
    fill, n_fallback = {}, 0
    nan_cols = np.nonzero(np.isnan(x).any(axis=0))[0]
    for j in nan_cols:
        j = int(j)
        col = x_raw[fit, j]
        good = np.isfinite(col)
        if good.any():
            value = float(col[good].mean())
        else:
            value = float(EICU_IMPUTE_FALLBACK)
            n_fallback += 1
        fill[names[j]] = value
        mask = np.isnan(x[:, j])
        x[mask, j] = value

    if not np.isfinite(x).all():
        bad = [names[int(j)] for j in
               np.nonzero(~np.isfinite(x).all(axis=0))[0]]
        raise _err("impute",
                   "non-finite value survived imputation; make_cohort would "
                   "reject this matrix (column(s))", bad,
                   reason="nonfinite-after-impute")
    if verbose:
        print(f"[eicu] imputed {len(fill)} columns from {fit.size} S_train rows "
              f"({n_fallback} all-NaN-in-train -> fallback "
              f"{EICU_IMPUTE_FALLBACK})", file=sys.stderr)
    return x, fill


# =============================================================== split ======

def site_split(site_raw, *, replicate=0):
    """Deterministic BY-SITE partition (A.8). Records never cross a boundary.

    Holds out ``EICU_N_TARGET_SITES = 24`` hospitals, then splits the remainder
    ``SPLIT_FRACTIONS`` (0.40 / 0.20 / 0.40) -- imported, never re-literalled.
    At 208 hospitals: rest 184 -> train 73 / aux 36 / **cal 75** against
    ``MIN_CAL_CLUSTERS = 50``, i.e. 50% headroom.

    Disjointness is asserted PAIRWISE -- a deliberate deviation from
    ``fixture_etl.site_split``, whose ``assert not (a & b & c)`` is a TRIPLE
    intersection and is strictly weaker (it passes on any two-way overlap).

    Keys are exactly ``('train','aux','cal','target')``; index arrays are
    ``dtype=int``. Raises ``EicuError`` (``reason=too-few-sites``) below
    ``EICU_MIN_TOTAL_SITES`` and (``reason=too-few-cal-clusters``) if
    ``len(cal) < MIN_CAL_CLUSTERS``.
    """
    uniq = sorted(set(site_raw))
    if len(uniq) < EICU_MIN_TOTAL_SITES:
        raise _err("site_split",
                   f"the 40/20/40 remainder cannot yield MIN_CAL_CLUSTERS="
                   f"{MIN_CAL_CLUSTERS} calibration sites below "
                   f"EICU_MIN_TOTAL_SITES={EICU_MIN_TOTAL_SITES} total sites",
                   len(uniq), reason="too-few-sites")
    rng = np.random.default_rng(
        np.random.SeedSequence([SEED, EICU_SPLIT_NAMESPACE, int(replicate)]))
    shuffled = [uniq[i] for i in rng.permutation(len(uniq))]
    target = set(shuffled[:EICU_N_TARGET_SITES])
    rest = shuffled[EICU_N_TARGET_SITES:]
    n_tr = int(len(rest) * SPLIT_FRACTIONS[0])
    n_aux = int(len(rest) * SPLIT_FRACTIONS[1])
    train = set(rest[:n_tr])
    aux = set(rest[n_tr:n_tr + n_aux])
    cal = set(rest[n_tr + n_aux:])

    assert not (train & aux), "site_split: train/aux overlap"
    assert not (train & cal), "site_split: train/cal overlap"
    assert not (aux & cal), "site_split: aux/cal overlap"
    assert not (train & target), "site_split: train/target overlap"
    assert not (aux & target), "site_split: aux/target overlap"
    assert not (cal & target), "site_split: cal/target overlap"
    assert len(train | aux | cal | target) == len(uniq), "site_split: coverage"

    if len(cal) < MIN_CAL_CLUSTERS:
        raise _err("site_split",
                   f"the split leaves fewer than MIN_CAL_CLUSTERS="
                   f"{MIN_CAL_CLUSTERS} calibration sites; run_certgate would "
                   f"return insufficient-clusters", len(cal),
                   reason="too-few-cal-clusters")

    idx = {k: [] for k in ("train", "aux", "cal", "target")}
    for i, s in enumerate(site_raw):
        if s in target:
            idx["target"].append(i)
        elif s in train:
            idx["train"].append(i)
        elif s in aux:
            idx["aux"].append(i)
        else:
            idx["cal"].append(i)
    sets = {"train": train, "aux": aux, "cal": cal, "target": target}
    return {k: np.asarray(v, dtype=int) for k, v in idx.items()}, sets


def labels(meta) -> list:
    """The raw two-valued outcome strings, one per record ('Expired'/'Alive').

    Returns ``list(meta['y_raw'])``. Never a bool array -- ``coerce_labels``
    owns the two-value contract, and S2 has already dropped ``''`` and raised
    on any third level, so a fitting cohort is guaranteed exactly two observed
    values.
    """
    return list(meta["y_raw"])


def build_matrix(data_dir, *, arm="primary", strict_levels=True, replicate=0,
                 verbose=True):
    """Convenience one-call path: ``build_raw`` -> ``site_split(replicate)`` ->
    ``impute(fit_idx=idx['train'])``.

    Returns ``(x, feature_names, meta)`` with ``meta`` additionally carrying
    ``'split_idx'`` (dict of int arrays), ``'split_sites'`` (dict of str sets)
    and ``'impute_fill'``. Used by ``run_eicu`` for a SINGLE replicate and by
    the tests; the multi-replicate runner calls ``build_raw`` ONCE and loops
    ``site_split`` + ``impute`` (re-reading a 200k-row extract 20 times is a
    build error, not a style preference -- T-16).
    """
    x_raw, names, meta = build_raw(data_dir, arm=arm,
                                   strict_levels=strict_levels, verbose=verbose)
    idx, sets = site_split(meta["site_raw"], replicate=replicate)
    x, fill = impute(x_raw, idx["train"], verbose=verbose)
    meta["split_idx"] = idx
    meta["split_sites"] = sets
    meta["impute_fill"] = fill
    return x, names, meta


# ============================================================ preflight =====
# The A.11 predictions are written HERE, by the non-certifying preflight, so
# the pre-registration is emitted BEFORE any certificate exists (T-18).

EICU_PREDICTIONS = (
    {"id": "P1",
     "prediction": "At 208 hospitals (75 calibration sites), alpha = 0.10 "
                   "certifies on the pooled arm and alpha = 0.05 does not, in "
                   ">= 15 of the 20 replicates. Basis: E4's synthetic frontier "
                   "-- alpha=0.10 certifies from ~150 sites, alpha=0.05 first "
                   "appears ~300 and is reliable only by 400.",
     "settled_by": "EICU_pooled.csv `certified` by `alpha`"},
    {"id": "P2",
     "prediction": "The per-site dispersion diagnostic on the pooled target "
                   "pool at the deployed tau (_per_site_exceed_frac) is > 0.02 "
                   "and lands in [0.05, 0.30] -- real hospitals are more "
                   "heterogeneous than the synthetic generator at s_u = 0.5 "
                   "(which gave 0.02) and closer to its s_u = 2.0 arm (0.10).",
     "settled_by": "EICU_pooled.csv `per_site_exceed_frac`"},
    {"id": "P3",
     "prediction": "BBSE contributes no certificate: it declines on >= 90% of "
                   "the 25 pools per replicate, with bbse-misspecified or "
                   "bbse-ill-conditioned the modal reason. Basis: E2's 200/200 "
                   "declines, plus the coarse 2000-draw q_t tail widening the "
                   "16-corner box. Falsified if BBSE certifies a tau the "
                   "baseline walk does not.",
     "settled_by": "`decline_reason` / `mode_outcomes` columns"},
    {"id": "P4",
     "prediction": "APACHE-absence features (aps_present, apv_present, or an "
                   "aps_*__missing / apv_*__missing sibling) appear in the top "
                   "3 of the abstention gap_ranking on the pooled arm. Basis: "
                   "absence is site-correlated by the dataset authors' own "
                   "account.",
     "settled_by": "EICU_diagnostics.json `abstention_gap_ranking`"},
    {"id": "P5",
     "prediction": "The per-hospital arm returns pool-too-small for >= 1 and "
                   "<= 6 of the 24 target hospitals (heavy-tailed hospital "
                   "sizes; ~78% of hospitals have < 500 stays).",
     "settled_by": "EICU_per_site.csv `reason`"},
    {"id": "P6",
     "prediction": "Mean coverage at the operative rung on the pooled arm is "
                   "in [0.60, 0.95].",
     "settled_by": "EICU_pooled.csv `coverage`"},
    {"id": "P7",
     "prediction": "Primary-cohort size lands in [130 000, 175 000] stays "
                   "across 208 sites, and apache-result-linked retains <= 195 "
                   "sites -- i.e. the APACHE-result restriction visibly "
                   "deletes >= 13 hospitals.",
     "settled_by": "EICU_attrition.csv"},
)


def _header_case(raw_header):
    """``'camel' | 'lower' | 'mixed'`` as READ (T-6: a re-zip may re-case).

    The verdict must be DECIDABLE from the header alone (2026-07-31 audit,
    E-17). The old rule -- "camel iff EVERY name carries an upper-case
    character" -- called a fully camelCase header ``'mixed'`` on four of the
    five tables, because single-token names (``age``, ``gender``, ``ph``,
    ``urine``, ``region``) cannot express case at all; and ``'mixed'`` reads as
    "some columns were re-cased and some were not", a materially different and
    misleading diagnosis in exactly the direction T-6 exists to detect.

    ``lower``  no name carries an upper-case character (the released extract).
    ``camel``  at least one does and every name is alphanumeric -- a
               case-varied rendering of the same names.
    ``mixed``  at least one name carries an upper-case character AND at least
               one carries a separator (``_``): a re-export from another tool.
    """
    names = [h.strip() for h in raw_header]
    n_upper = sum(1 for h in names if any(c.isupper() for c in h))
    if n_upper == 0:
        return "lower"
    if all(h.isalnum() for h in names if h):
        return "camel"
    return "mixed"


def _scan_apache(data_dir, table, cols, prefix, stay_site, cohort_site_stays,
                 ordinal=False, stay_positive=None):
    """Profile one APACHE table: sentinels, quantiles, per-site dispersion.

    Sentinel histograms cover EVERY row of the table (a table profile);
    per-site dispersion and coverage cover only cohort-linked rows, because a
    site is only meaningful through the cohort's stay -> hospital map.

    ``stay_positive`` (cohort stay id -> outcome bool) additionally accumulates
    the OUTCOME-stratified per-column missingness counts that E-9 requires:
    for each allowlisted column, ``[n_missing, n_missing_positive, n_present,
    n_present_positive]`` over cohort-linked rows. Stays with NO row in this
    table at all are added by ``preflight``, which knows the cohort.
    """
    sent = {c: _new_sentinel_counter() for c in cols}
    zero = Counter()
    q = {c: _Quantiles() for c in cols}
    per_site = {c: defaultdict(lambda: [0, 0, 0]) for c in cols}   # n, -1, missing
    rows_per_stay = Counter()
    linked_stays = set()
    ordinals = {c: Counter() for c in EICU_ORDINAL_COLUMNS} if ordinal else {}
    fio2 = Counter()
    temp = Counter()
    n_rows = 0
    null_tokens = {}
    # E-9: [n_missing, n_missing_pos, n_present, n_present_pos] per column.
    by_outcome = {c: [0, 0, 0, 0] for c in cols}
    seen_cohort = set()

    n_key_unparseable = 0
    for row in read_table(data_dir, table):
        n_rows += 1
        stay_id = _maybe_int(row["patientunitstayid"])
        if stay_id is None:
            # E-21: profile the join-key format so preflight can project the
            # unparseable-join-key raise before any certification is run.
            tok = (row["patientunitstayid"] or "").strip()
            if tok:
                n_key_unparseable += 1
                _note_null_token(null_tokens, "patientunitstayid", tok)
        if stay_id is not None:
            rows_per_stay[stay_id] += 1
        site = stay_site.get(stay_id) if stay_id is not None else None
        if site is not None:
            linked_stays.add(stay_id)
        first_cohort_row = False
        pos = None
        if site is not None and stay_positive is not None:
            first_cohort_row = stay_id not in seen_cohort
            if first_cohort_row:
                seen_cohort.add(stay_id)
                pos = bool(stay_positive.get(stay_id, False))
        for c in cols:
            t = (row[c] or "").strip()
            s = sent[c]
            missing = True
            if not t:
                s["empty"] += 1
            else:
                v = _maybe_float(t)
                if v is None:
                    s["unparseable"] += 1
                    _note_null_token(null_tokens, c, t)
                elif v == EICU_SENTINEL_MISSING:
                    s["minus_one"] += 1
                else:
                    if v < 0.0:
                        s["other_negative"] += 1
                    if v == 0.0:
                        zero[c] += 1
                    q[c].add(v)
                    missing = False
            if site is not None:
                cell = per_site[c][site]
                cell[0] += 1
                if t.strip() and _maybe_float(t) == EICU_SENTINEL_MISSING:
                    cell[1] += 1
                if missing:
                    cell[2] += 1
            if first_cohort_row:
                b = by_outcome[c]
                if missing:
                    b[0] += 1
                    b[1] += int(pos)
                else:
                    b[2] += 1
                    b[3] += int(pos)
        if ordinal:
            for c in EICU_ORDINAL_COLUMNS:
                _bump(ordinals[c], (row[c] or "").strip())
        if "fio2" in row:
            v = _maybe_float(row["fio2"])
            if v is None:
                fio2["n_missing"] += 1
            elif v == EICU_SENTINEL_MISSING:
                fio2["n_minus_one"] += 1
            else:
                fio2["n_le_1" if v <= 1.0 else "n_gt_1"] += 1
                if v > 100.0:
                    fio2["n_gt_100"] += 1
                lo, hi = EICU_WINDOW_FIO2_FRAC
                plo, phi = EICU_WINDOW_FIO2_PCT
                if lo < v <= hi:
                    fio2["n_in_frac_window"] += 1
                elif plo < v <= phi:
                    fio2["n_in_pct_window"] += 1
                else:
                    fio2["n_out_of_both"] += 1
                if v == lo:
                    fio2["n_eq_frac_floor"] += 1
                if v == plo:
                    fio2["n_eq_pct_floor"] += 1
        if "temperature" in row:
            v = _maybe_float(row["temperature"])
            if v is None:
                temp["n_missing"] += 1
            elif v == EICU_SENTINEL_MISSING:
                temp["n_minus_one"] += 1
            else:
                clo, chi = EICU_WINDOW_TEMP_C
                flo, fhi = EICU_WINDOW_TEMP_F
                if clo < v < chi:
                    temp["n_in_c_window"] += 1
                elif flo < v < fhi:
                    temp["n_in_f_window"] += 1
                else:
                    temp["n_out_of_both"] += 1
                if v > chi:
                    temp["n_gt_45"] += 1

    sentinels = {}
    for c in cols:
        s = sent[c]
        entry = {"n": n_rows, "n_empty": s["empty"], "n_minus_one": s["minus_one"],
                 "n_other_negative": s["other_negative"],
                 "n_unparseable": s["unparseable"], "n_zero": int(zero[c])}
        entry.update(q[c].summary())
        sentinels[c] = entry

    dispersion = {}
    for c in cols:
        rates_m1, rates_miss = [], []
        for site in cohort_site_stays:
            cell = per_site[c].get(site)
            if not cell or cell[0] == 0:
                continue
            rates_m1.append(cell[1] / cell[0])
            rates_miss.append(cell[2] / cell[0])
        d = _spread(rates_m1)
        dispersion[c] = {"mean_site_minus_one_rate": d["mean"],
                         "sd_site_minus_one_rate": d["sd"],
                         "p10": d["p10"], "p50": d["p50"], "p90": d["p90"],
                         "mean_site_missing_rate": _spread(rates_miss)["mean"],
                         "sd_site_missing_rate": _spread(rates_miss)["sd"]}

    hist = Counter()
    n_gt1 = 0
    for c in rows_per_stay.values():
        hist[str(c) if c < 10 else "10+"] += 1
        if c > 1:
            n_gt1 += 1

    return {"n_rows": n_rows, "n_distinct_stays": len(rows_per_stay),
            "n_key_unparseable": int(n_key_unparseable),
            "rows_per_stay_hist": dict(sorted(hist.items())),
            "n_stays_gt1_row": n_gt1, "sentinels": sentinels,
            "dispersion": dispersion, "linked_stays": linked_stays,
            "ordinals": {k: dict(v) for k, v in ordinals.items()},
            "fio2": dict(fio2), "temperature": dict(temp),
            "by_outcome": by_outcome,
            "null_tokens": {k: dict(sorted(v.items()))
                            for k, v in sorted(null_tokens.items())}}


def _coverage_by_site(linked_stays, stay_site, cohort_site_stays):
    """Per-site coverage summary for one APACHE table (T-3/T-4)."""
    linked = Counter()
    for s in linked_stays:
        site = stay_site.get(s)
        if site is not None:
            linked[site] += 1
    rates = [linked[site] / n for site, n in cohort_site_stays.items() if n]
    out = _spread(rates)
    arr = np.asarray(rates, dtype=float)
    out["n_sites_zero"] = int((arr == 0.0).sum()) if arr.size else 0
    out["n_sites_below_0.2"] = int((arr < 0.2).sum()) if arr.size else 0
    out["n_linked_stays"] = int(sum(linked.values()))
    return out, linked


def preflight(data_dir, *, expect_reference=False, verbose=True) -> dict:
    """Validate and PROFILE an extract WITHOUT building features or certifying.

    Streams all five tables. Returns an AGGREGATE-ONLY, JSON-serialisable dict
    (no record-level arrays; every list is a value-count or a quantile
    summary). ``expect_reference=True`` turns a row-count / site-count /
    patient-count mismatch against ``EICU_REFERENCE_*`` into ``EicuError``
    (``reason=reference-row-count-mismatch``) -- pass it for the real extract,
    omit it for the mock.

    This is the loud boundary for everything that cannot be verified from the
    DDL: the undocumented ``-1`` sentinel and its PER-SITE dispersion (T-2/T-3),
    the frozen categorical vocabulary (T-7), the multi-row
    ``apachePatientResult`` (T-8), the fio2/temperature unit ambiguity (T-10),
    the implausible-physiology channel (T-11), and the heavy-tailed hospital
    sizes that decide whether ``MIN_CAL_CLUSTERS`` is reachable at all (T-12),
    the OUTCOME-informative half of the APACHE missingness channel (E-9:
    ``outcome_stratified_missingness``, ``apache_absent_los``, and
    ``n_positive`` on every attrition step), and an extract whose NULL token is
    not ``''`` (E-15: ``unparseable_tokens``).

    It does NOT raise on the conditions it exists to PROFILE -- categorical
    drift, an unknown outcome level, an unrecognised NULL token, an
    outcome-informative presence flag. Each is reported exactly and listed in
    ``reference_check["invalid_conditions"]`` naming the raise ``build_raw``
    WILL make, so the fix is a visible SPEC diff rather than an absorption. It
    builds no features and certifies nothing; the ONLY raise is the
    reference-identity check under ``expect_reference=True``.
    """
    warnings = []

    # ---- table resolution + headers (cheap, before anything is allocated) --
    tables = {}
    raw_headers = {}
    for t in EICU_TABLES:
        path = _resolve_table_path(data_dir, t)
        raw, lower = _read_header(path, t)
        require_columns(lower, t, EICU_REQUIRED_COLUMNS.get(t, ()))
        raw_headers[t] = raw
        tables[t] = {"path": os.path.basename(path), "rows": None,
                     "header": list(lower),
                     # E-17: the verdict AND the evidence it was drawn from,
                     # so a wrong verdict is checkable rather than trusted.
                     "header_raw": [h.strip() for h in raw],
                     "header_case_as_read": _header_case(raw),
                     "n_names_with_uppercase": sum(
                         1 for h in raw if any(c.isupper() for c in h.strip())),
                     "reference_rows": EICU_REFERENCE_ROW_COUNTS.get(t),
                     "rows_match_reference": None}
    if verbose:
        print(f"[eicu] preflight: {len(tables)} tables resolved in {data_dir}",
              file=sys.stderr)

    # ---- patient (scan A: predicates + raw profile) ------------------------
    # strict_outcome=False (E-16): an unexpected hospitaldischargestatus token
    # must not abort the step whose job is to TABULATE value sets.
    sel = _select_cohort(data_dir, profile=True, verbose=verbose,
                         strict_outcome=False)
    selected = sel["selected"]
    prof = sel["profile"]
    warnings.extend(sel["warnings"])
    tables["patient"]["rows"] = sel["n_patient_rows"]

    stay_site = {sid: meta[0] for sid, meta in selected.items()}
    cohort_site_stays = Counter(stay_site.values())
    n_pos = Counter()
    for sid, (site, _adm, status) in selected.items():
        if status == EICU_POSITIVE_LABEL:
            n_pos[site] += 1
    prevalence_rates = [n_pos[s] / n for s, n in cohort_site_stays.items() if n]
    site_prevalence = _spread(prevalence_rates)
    site_prevalence["n_sites"] = len(cohort_site_stays)
    site_prevalence["overall"] = _share(sum(n_pos.values()), len(selected))

    age_tokens = {k: v for k, v in prof["age_tokens"].most_common(12)}
    for k in ("__numeric__", "__blank__"):
        age_tokens[k] = int(prof["age_tokens"][k])
    for tok in prof["age_tokens"]:
        if tok not in ("__numeric__", "__blank__") and ">" in tok \
                and tok != EICU_AGE_MASK_TOKEN:
            warnings.append(
                f"[MEASURE] an age ceiling token {tok!r} is present that is NOT "
                f"the frozen EICU_AGE_MASK_TOKEN {EICU_AGE_MASK_TOKEN!r}; those "
                f"stays currently DROP as age-unparseable (a site-correlated "
                f"exclusion) -- widen the constant in SPEC.md, do not patch here")

    patient_block = {
        # E-13: `n_hospitals` / `n_uniquepid` are the DATASET IDENTITY counts
        # and are taken at S0 over every patient row, because
        # EICU_REFERENCE_SITES / _PATIENTS are whole-table headline numbers.
        # The post-filter counts are a COHORT diagnostic and are named as such
        # -- comparing them against the published totals made the mandatory
        # first command abort on the genuine extract.
        "n_rows": sel["n_patient_rows"],
        "n_hospitals": sel["n_hospitals_raw"],
        "n_uniquepid": sel["n_uniquepid_raw"],
        "n_hospitals_cohort": len({s for s in stay_site.values()}),
        "n_uniquepid_cohort": sel["cross"]["n_uniquepid"],
        "n_healthsystemstays": sel["n_healthsystemstays"],
        "age_tokens": age_tokens,
        "gender": dict(prof["gender"]), "ethnicity": dict(prof["ethnicity"]),
        "hospitaldischargestatus": dict(prof["hospitaldischargestatus"]),
        "unitdischargestatus": dict(prof["unitdischargestatus"]),
        "hospitaldischargeyear": dict(prof["hospitaldischargeyear"]),
        "unittype": dict(prof["unittype"]),
        "unitstaytype": dict(prof["unitstaytype"]),
        "hospitaladmitsource": dict(prof["hospitaladmitsource"]),
        "unitadmitsource": dict(prof["unitadmitsource"]),
        "hospitaladmitoffset_sign": dict(prof["hospitaladmitoffset_sign"]),
        "unitvisitnumber_hist": dict(prof["unitvisitnumber_hist"]),
        "n_admissions_min_visit_not_1": None,       # filled below
        "site_prevalence": site_prevalence,         # parent-task requirement
    }

    # ---- patient (scan B: cohort-restricted vocabulary + missingness) ------
    other_counts = {col: 0 for col, _ in EICU_CATEGORICALS}
    other_values = {col: Counter() for col, _ in EICU_CATEGORICALS}
    pat_per_site = {c: defaultdict(lambda: [0, 0])
                    for c in EICU_PATIENT_NUMERIC}
    n_cohort = 0
    n_min_visit_not_1 = 0
    sink = _new_sentinel_counter()
    sinks = {c: sink for c in EICU_PATIENT_NUMERIC}
    drop_win = Counter()
    los_by_stay = {}
    for row in read_table(data_dir, "patient"):
        stay_id = _maybe_int(row["patientunitstayid"])
        if stay_id is None or stay_id not in selected:
            continue
        n_cohort += 1
        site = stay_site[stay_id]
        # E-9: ICU length of stay, read as a DIAGNOSTIC only (it is on the
        # feature denylist and stays there). The LOS distribution of
        # APACHE-ABSENT versus APACHE-PRESENT stays is the measurement that
        # separates the SITE channel from the OUTCOME channel: if the absent
        # stays are systematically short, they are short because they ended.
        los = _maybe_float(row.get("unitdischargeoffset", ""))
        if los is not None:
            los_by_stay[stay_id] = los / 60.0
        visit = _maybe_float(row["unitvisitnumber"])
        if visit is None or visit != 1.0:
            n_min_visit_not_1 += 1
        for col, levels in EICU_CATEGORICALS:
            value = (row[col] or "").strip()
            if value not in levels:
                other_counts[col] += 1
                _bump(other_values[col], value)
        try:
            age_v = parse_age((row["age"] or "").strip())
        except ValueError:
            age_v = None
        vals = {
            "age": age_v,
            "admissionheight": _parse_windowed(row["admissionheight"],
                                               "admissionheight",
                                               EICU_WINDOW_HEIGHT_CM, sinks,
                                               drop_win),
            "admissionweight": _parse_windowed(row["admissionweight"],
                                               "admissionweight",
                                               EICU_WINDOW_WEIGHT_KG, sinks,
                                               drop_win),
            "pre_icu_hours": _parse_windowed(row["hospitaladmitoffset"],
                                             "pre_icu_hours",
                                             EICU_WINDOW_PRE_ICU_HRS, sinks,
                                             drop_win, lambda v: -v / 60.0),
        }
        for c, v in vals.items():
            cell = pat_per_site[c][site]
            cell[0] += 1
            if v is None or not math.isfinite(v):
                cell[1] += 1
    patient_block["n_admissions_min_visit_not_1"] = int(n_min_visit_not_1)

    categorical_drift = {}
    for col, _levels in EICU_CATEGORICALS:
        share = _share(other_counts[col], n_cohort)
        top = sorted(other_values[col].items(), key=lambda kv: (-kv[1], kv[0]))[:8]
        exceeds = bool(share is not None and share > EICU_MAX_OTHER_SHARE)
        categorical_drift[col] = {"other_share": share,
                                  "other_count": int(other_counts[col]),
                                  "top_unlisted": [[v, int(c)] for v, c in top],
                                  "exceeds_cap": exceeds}
        if exceeds:
            warnings.append(
                f"[MEASURE] T-7: categorical level drift in {col!r}: "
                f"{share:.3f} > cap {EICU_MAX_OTHER_SHARE}; build_raw"
                f"(strict_levels=True) WILL raise categorical-level-drift. Fix "
                f"is a visible SPEC + constants diff, re-pinned in "
                f"test_constants.py -- never a widened OTHER bucket")

    # ---- APACHE tables -----------------------------------------------------
    stay_positive = {sid: (status == EICU_POSITIVE_LABEL)
                     for sid, (_s, _a, status) in selected.items()}
    aps = _scan_apache(data_dir, "apacheApsVar", EICU_APS_NUMERIC, "aps_",
                       stay_site, cohort_site_stays, ordinal=True,
                       stay_positive=stay_positive)
    apv = _scan_apache(data_dir, "apachePredVar", EICU_APV_NUMERIC, "apv_",
                       stay_site, cohort_site_stays,
                       stay_positive=stay_positive)
    tables["apacheApsVar"]["rows"] = aps["n_rows"]
    tables["apachePredVar"]["rows"] = apv["n_rows"]

    # ---- apachePatientResult (comparator + coverage diagnostic ONLY) -------
    res_rows = 0
    res_per_stay = Counter()
    res_linked = set()
    version_counts = Counter()
    version_pred = {}
    pred_by_version = {v: {} for v in EICU_APACHE_VERSION_PREFERENCE}
    for row in read_table(data_dir, "apachePatientResult"):
        res_rows += 1
        stay_id = _maybe_int(row["patientunitstayid"])
        if stay_id is not None:
            res_per_stay[stay_id] += 1
            if stay_id in stay_site:
                res_linked.add(stay_id)
        version = (row["apacheversion"] or "").strip()
        version_counts[version] += 1
        bucket = version_pred.setdefault(
            version, {"available": 0, "minus_one": 0, "empty": 0})
        raw = (row["predictedhospitalmortality"] or "").strip()
        # VARCHAR(50) holding a probability: float() FIRST (T-9).
        pv = _maybe_float(raw)
        if not raw:
            bucket["empty"] += 1
        elif pv is None:
            bucket["empty"] += 1
        elif pv == EICU_SENTINEL_MISSING:
            bucket["minus_one"] += 1
        else:
            bucket["available"] += 1
            if version in pred_by_version and stay_id in stay_site:
                pred_by_version[version].setdefault(stay_id, pv)
    tables["apachePatientResult"]["rows"] = res_rows

    res_hist = Counter()
    res_gt1 = 0
    for c in res_per_stay.values():
        res_hist[str(c) if c < 10 else "10+"] += 1
        if c > 1:
            res_gt1 += 1
    if res_gt1:
        warnings.append(
            f"[MEASURE] T-8: {res_gt1} stays carry >1 apachePatientResult row "
            f"(297,064 != 2 x 171,177 in the released extract); dedup is "
            f"min(apachepatientresultsid) within (stay, version) with version "
            f"preference {EICU_APACHE_VERSION_PREFERENCE!r}, counted in "
            f"meta['dedup_counts'] -- a naive join would silently duplicate "
            f"records and inflate the cluster sizes feeding the influence cap")

    comp_ok = set()
    for sid in stay_site:
        for v in EICU_APACHE_VERSION_PREFERENCE:
            if sid in pred_by_version[v]:
                comp_ok.add(sid)
                break

    # ---- hospital (strata; contributes NO features) ------------------------
    hosp_rows = 0
    hospital = {"numbedscategory": Counter(), "teachingstatus": Counter(),
                "region": Counter()}
    for row in read_table(data_dir, "hospital"):
        hosp_rows += 1
        for col in hospital:
            _bump(hospital[col], (row[col] or "").strip())
    tables["hospital"]["rows"] = hosp_rows
    hospital = {k: dict(v) for k, v in hospital.items()}

    # ---- attrition (the three APACHE steps are DIAGNOSTIC, never a filter) -
    attrition = list(sel["attrition"])
    site_stay_counts = {step["step"]: _dist_summary(sel["site_counts"][step["step"]].values())
                        for step in attrition}
    for step, stays in (("apache-aps-linked", aps["linked_stays"]),
                        ("apache-result-linked", res_linked),
                        ("apache-complete-arm",
                         aps["linked_stays"] & apv["linked_stays"] & comp_ok)):
        counts = Counter(stay_site[s] for s in stays if s in stay_site)
        n_step = int(sum(counts.values()))
        # E-9: n_positive per step, so the ledger itself shows an
        # outcome-correlated selection instead of hiding it inside n_stays.
        n_pos_step = int(sum(1 for s in stays
                             if s in stay_site and stay_positive.get(s)))
        attrition.append({"step": step, "n_stays": n_step,
                          "n_sites": len(counts),
                          "n_positive": n_pos_step,
                          "prevalence": _share(n_pos_step, n_step)})
        site_stay_counts[step] = _dist_summary(counts.values())

    prev_primary = attrition[5]["prevalence"]
    prev_aps = attrition[6]["prevalence"]
    if prev_primary and prev_aps and prev_aps < prev_primary:
        warnings.append(
            f"[MEASURE] E-9: prevalence falls from {prev_primary:.4f} at "
            f"primary-cohort to {prev_aps:.4f} at apache-aps-linked; APACHE-row "
            f"absence is OUTCOME-correlated, not only site-correlated")

    aps_cov, _ = _coverage_by_site(aps["linked_stays"], stay_site, cohort_site_stays)
    apv_cov, _ = _coverage_by_site(apv["linked_stays"], stay_site, cohort_site_stays)
    res_cov, _ = _coverage_by_site(res_linked, stay_site, cohort_site_stays)
    if res_cov["n_sites_zero"]:
        warnings.append(
            f"[MEASURE] T-4: {res_cov['n_sites_zero']} hospitals have ZERO "
            f"apachePatientResult rows. The primary arm draws NO feature from "
            f"that table: restricting to APACHE-covered stays would delete "
            f"those hospitals and CHANGE THE SITE POPULATION the "
            f"site-population-average estimand refers to (audit V1)")

    # ---- patient-block per-site missingness dispersion ---------------------
    pat_dispersion = {}
    for c in EICU_PATIENT_NUMERIC:
        rates = [cell[1] / cell[0] for cell in pat_per_site[c].values() if cell[0]]
        d = _spread(rates)
        pat_dispersion[c] = {"mean_site_minus_one_rate": 0.0,
                             "sd_site_minus_one_rate": 0.0,
                             "p10": d["p10"], "p50": d["p50"], "p90": d["p90"],
                             "mean_site_missing_rate": d["mean"],
                             "sd_site_missing_rate": d["sd"]}

    patient_sent = {}
    for c in ("age", "admissionheight", "admissionweight", "hospitaladmitoffset"):
        s = prof["sent"][c]
        entry = {"n": sel["n_patient_rows"], "n_empty": s["empty"],
                 "n_minus_one": s["minus_one"],
                 "n_other_negative": s["other_negative"],
                 "n_unparseable": s["unparseable"], "n_zero": int(prof["zero"][c])}
        entry.update(prof["q"][c].summary())
        patient_sent[c] = entry

    # ---- ordinal supports (documented range u {-1} u {0}) ------------------
    ordinal_value_sets = aps["ordinals"]
    for c, counts in ordinal_value_sets.items():
        lo, hi = EICU_ORDINAL_RANGES[c]
        stray = []
        for tok, k in counts.items():
            v = _maybe_float(tok)
            if v is None or v == EICU_SENTINEL_MISSING or v == 0.0:
                continue
            if not (lo <= v <= hi):
                stray.append((tok, int(k)))
        if stray:
            warnings.append(
                f"[MEASURE] apacheApsVar.{c} carries value(s) outside the "
                f"documented support [{lo}, {hi}] u {{-1, 0}}: "
                f"{sorted(stray)[:6]!r}")

    # ---- OUTCOME-stratified missingness (E-9) ------------------------------
    # The load-bearing screen the old protocol had nowhere: APACHE day-1 rows
    # do not exist for stays that end before the window closes, so absence is a
    # partial OUTCOME proxy and not merely the site proxy T-3 describes. Every
    # entry is (missing stratum, present stratum, ratio) over the COHORT.
    def _contrast(name, n_miss, k_miss, n_pres, k_pres):
        p_miss = _share(k_miss, n_miss)
        p_pres = _share(k_pres, n_pres)
        ratio = (p_miss / p_pres) if (p_miss is not None and p_pres) else None
        return {"feature": name, "n_missing": int(n_miss),
                "n_present": int(n_pres),
                "prevalence_missing": None if p_miss is None else round(p_miss, 6),
                "prevalence_present": None if p_pres is None else round(p_pres, 6),
                "prevalence_ratio": None if ratio is None else round(ratio, 4),
                "cap": EICU_MAX_OUTCOME_PREVALENCE_RATIO,
                "gate_applies": bool(n_miss >= EICU_MIN_OUTCOME_STRATUM
                                     and n_pres >= EICU_MIN_OUTCOME_STRATUM)}

    n_cohort_total = len(selected)
    n_cohort_pos = int(sum(stay_positive.values()))
    outcome_missingness = {}
    for tag, block, cols, linked in (
            ("aps_present", aps, EICU_APS_NUMERIC, aps["linked_stays"]),
            ("apv_present", apv, EICU_APV_NUMERIC, apv["linked_stays"])):
        n_pres = len(linked)
        k_pres = int(sum(stay_positive.get(s, False) for s in linked))
        outcome_missingness[tag] = _contrast(
            tag, n_cohort_total - n_pres, n_cohort_pos - k_pres, n_pres, k_pres)
        # stays with NO row in this table are missing for EVERY column of it
        n_unlinked = n_cohort_total - n_pres
        k_unlinked = n_cohort_pos - k_pres
        prefix = "aps_" if tag == "aps_present" else "apv_"
        for c in cols:
            b = block["by_outcome"][c]
            outcome_missingness[f"{prefix}{c}__missing"] = _contrast(
                f"{prefix}{c}__missing", b[0] + n_unlinked, b[1] + k_unlinked,
                b[2], b[3])
    def _los_summary(stays):
        vals = [los_by_stay[s] for s in stays if s in los_by_stay]
        d = _dist_summary(vals) if vals else _dist_summary([])
        return {"n": len(vals), "min": d["min"], "q1": d["q1"],
                "median": d["median"], "q3": d["q3"], "max": d["max"],
                "mean": d["mean"]}

    absent_aps = [s for s in selected if s not in aps["linked_stays"]]
    apache_absent_los = {
        "unit": "hours",
        "note": ("unitdischargeoffset is a DENYLISTED feature read here as a "
                 "diagnostic ONLY (E-9). If APACHE-absent stays are "
                 "systematically shorter, absence is outcome-informative: the "
                 "day-1 window did not close because the stay ended."),
        "aps_absent": _los_summary(absent_aps),
        "aps_present": _los_summary(aps["linked_stays"]),
        "aps_absent_positive": _los_summary(
            [s for s in absent_aps if stay_positive.get(s)]),
        "n_los_unavailable": int(len(selected) - len(los_by_stay))}

    worst = sorted((e for e in outcome_missingness.values()
                    if e["gate_applies"] and e["prevalence_ratio"] is not None),
                   key=lambda e: -e["prevalence_ratio"])[:6]
    over = [e for e in worst
            if e["prevalence_ratio"] > EICU_MAX_OUTCOME_PREVALENCE_RATIO]
    if over:
        warnings.append(
            f"[MEASURE] E-9: OUTCOME-informative missingness -- "
            f"{len(over)} indicator(s) show an absent:present outcome "
            f"prevalence ratio over the cap "
            f"{EICU_MAX_OUTCOME_PREVALENCE_RATIO}; worst "
            f"{[(e['feature'], e['prevalence_ratio']) for e in over[:4]]!r}. "
            f"APACHE day-1 rows do not exist for a stay that ends because the "
            f"patient died, so this channel is a LEAK, not the site channel "
            f"T-3 describes, and prediction P4 being satisfied is its SIGNATURE "
            f"rather than a confirmation")

    # ---- unrecognised sentinels (build_raw will ABORT on these) ------------
    for label, block in (("apacheApsVar", aps), ("apachePredVar", apv)):
        bad = {c: e["n_other_negative"] for c, e in block["sentinels"].items()
               if e["n_other_negative"]}
        over = {c: k for c, k in bad.items()
                if block["sentinels"][c]["n"]
                and (k / block["sentinels"][c]["n"]) > EICU_MAX_UNPARSEABLE_SHARE}
        if over:
            warnings.append(
                f"[MEASURE] T-2: {label} carries negative mass NOT at exactly "
                f"-1.0 in {dict(sorted(over.items()))!r}, over "
                f"{EICU_MAX_UNPARSEABLE_SHARE} of rows; build_raw WILL raise "
                f"unexpected-negative-sentinel. The rule 'value < 0 => missing' "
                f"is adopted only AFTER the histogram proves the support is "
                f"contiguous and non-negative -- do not widen it here")
        elif bad:
            warnings.append(
                f"[MEASURE] T-2/A6: {label} carries negative mass NOT at "
                f"exactly -1.0 in {dict(sorted(bad.items()))!r}, BELOW the "
                f"{EICU_MAX_UNPARSEABLE_SHARE} abort threshold: the cells map "
                f"to missing and the run proceeds (amendment A6, POST-HOC). "
                f"Inspect the column's support before trusting it")

    # ---- unrecognised NULL TOKEN (E-15/E-22): opposite direction of T-2 ----
    unparseable_over = {}
    for label, block in (("apacheApsVar", aps), ("apachePredVar", apv)):
        for c, e in block["sentinels"].items():
            n = e["n"]
            k = e["n_unparseable"]
            if n and k and (k / n) > EICU_MAX_UNPARSEABLE_SHARE:
                unparseable_over[f"{label}.{c}"] = {
                    "n_unparseable": int(k), "share": round(k / n, 6),
                    "top_tokens": block["null_tokens"].get(c, {})}
    # E-22: the patient numerics are gated by the SAME raise; the first
    # version of this projection was APACHE-only, so a '\N' in
    # admissionweight (or in hospitaladmitoffset, the first-stay tie-breaker)
    # was projected as clean while build_raw silently zeroed the column.
    for c in ("admissionheight", "admissionweight", "hospitaladmitoffset"):
        e = patient_sent[c]
        n = e["n"]
        k = e["n_unparseable"]
        if n and k and (k / n) > EICU_MAX_UNPARSEABLE_SHARE:
            unparseable_over[f"patient.{c}"] = {
                "n_unparseable": int(k), "share": round(k / n, 6),
                "top_tokens": {}}
    if unparseable_over:
        sample = sorted(unparseable_over.items())[:4]
        warnings.append(
            f"[MEASURE] E-15: {len(unparseable_over)} allowlisted "
            f"numeric(s) are unparseable in more than "
            f"{EICU_MAX_UNPARSEABLE_SHARE} of rows -- the extract's NULL token "
            f"is not '' (a Postgres text-format re-export writes '\\N'). Left "
            f"alone this makes the parent constant at the imputation fallback "
            f"and its __missing sibling constant at 1.0, zeroing 86 of 161 "
            f"coefficients while a certificate is still issued. build_raw WILL "
            f"raise unrecognised-null-token (patient numerics: E-22). Sample: "
            f"{[(k, v['top_tokens']) for k, v in sample]!r}")

    # ---- fio2 / temperature mass outside BOTH frozen windows (E-18) --------
    for label, block in (("apacheApsVar", aps), ("apachePredVar", apv)):
        for what, conv in (("fio2", block["fio2"]),
                           ("temperature", block["temperature"])):
            out_of = int(conv.get("n_out_of_both", 0))
            n_obs = out_of + sum(int(conv.get(k, 0)) for k in
                                 ("n_in_frac_window", "n_in_pct_window",
                                  "n_in_c_window", "n_in_f_window"))
            if n_obs and (out_of / n_obs) > EICU_MAX_UNPARSEABLE_SHARE:
                warnings.append(
                    f"[MEASURE] T-10/E-18: {label}.{what} has {out_of} of "
                    f"{n_obs} observed values outside BOTH frozen windows "
                    f"({out_of / n_obs:.4f}); those become missing. The fio2 "
                    f"windows are lower-CLOSED so room air (0.21 / 21) is kept; "
                    f"a large residue here means a third unit convention, and "
                    f"the fix is a SPEC + constants diff, not a silent loss")

    # ---- reference check + projected split arithmetic ----------------------
    mismatches = []
    for t, entry in tables.items():
        ref = entry["reference_rows"]
        entry["rows_match_reference"] = (None if ref is None
                                         else bool(entry["rows"] == ref))
        if ref is not None and entry["rows"] != ref:
            mismatches.append({"what": f"{t}.rows", "got": entry["rows"],
                               "expected": ref})
    # Identity is checked against the RAW S0 counts (E-13); the split
    # projection below uses the COHORT site count, which is what site_split
    # actually partitions.
    if patient_block["n_hospitals"] != EICU_REFERENCE_SITES:
        mismatches.append({"what": "n_hospitals",
                           "got": patient_block["n_hospitals"],
                           "expected": EICU_REFERENCE_SITES})
    if patient_block["n_uniquepid"] != EICU_REFERENCE_PATIENTS:
        mismatches.append({"what": "n_uniquepid",
                           "got": patient_block["n_uniquepid"],
                           "expected": EICU_REFERENCE_PATIENTS})
    if sel["n_patient_rows"] != EICU_REFERENCE_UNIT_STAYS:
        mismatches.append({"what": "n_unit_stays",
                           "got": sel["n_patient_rows"],
                           "expected": EICU_REFERENCE_UNIT_STAYS})

    n_sites = patient_block["n_hospitals_cohort"]
    rest = max(0, n_sites - EICU_N_TARGET_SITES)
    n_tr = int(rest * SPLIT_FRACTIONS[0])
    n_aux = int(rest * SPLIT_FRACTIONS[1])
    n_cal = rest - n_tr - n_aux
    split_projection = {"n_sites": n_sites, "n_target": EICU_N_TARGET_SITES,
                        "rest": rest, "n_train": n_tr, "n_aux": n_aux,
                        "n_cal": n_cal, "min_cal_clusters": MIN_CAL_CLUSTERS,
                        "cal_ok": bool(n_cal >= MIN_CAL_CLUSTERS),
                        "min_total_sites": EICU_MIN_TOTAL_SITES,
                        "total_sites_ok": bool(n_sites >= EICU_MIN_TOTAL_SITES)}

    invalid = []
    if not split_projection["total_sites_ok"]:
        invalid.append(f"site_split will raise too-few-sites: {n_sites} < "
                       f"{EICU_MIN_TOTAL_SITES}")
    if not split_projection["cal_ok"]:
        invalid.append(f"site_split will raise too-few-cal-clusters: projected "
                       f"cal {n_cal} < MIN_CAL_CLUSTERS {MIN_CAL_CLUSTERS}")
    for col, d in categorical_drift.items():
        if d["exceeds_cap"]:
            invalid.append(f"build_raw(strict_levels=True) will raise "
                           f"categorical-level-drift on {col!r}")
    for label, block in (("apacheApsVar", aps), ("apachePredVar", apv)):
        if any(e["n_other_negative"] and e["n"]
               and (e["n_other_negative"] / e["n"]) > EICU_MAX_UNPARSEABLE_SHARE
               for e in block["sentinels"].values()):
            invalid.append(f"build_raw will raise unexpected-negative-sentinel "
                           f"on {label}")
    if unparseable_over:
        invalid.append(f"build_raw will raise unrecognised-null-token on "
                       f"{sorted(unparseable_over)[:6]!r} (E-15)")
    for label, block in (("apacheApsVar", aps), ("apachePredVar", apv)):
        n_t = block["n_rows"]
        k_t = block["n_key_unparseable"]
        if n_t and (k_t / n_t) > EICU_MAX_UNPARSEABLE_SHARE:
            invalid.append(
                f"build_raw will raise unparseable-join-key on {label} "
                f"({k_t} of {n_t} patientunitstayid tokens fail integer "
                f"parse; E-21)")
    if len(selected) >= EICU_MIN_OUTCOME_STRATUM:
        for tag in ("aps_present", "apv_present"):
            e = outcome_missingness[tag]
            if e["n_present"] < EICU_MIN_OUTCOME_STRATUM:
                invalid.append(
                    f"build_raw(arm='primary') will raise "
                    f"apache-coverage-collapse on {tag} (n_present "
                    f"{e['n_present']} < {EICU_MIN_OUTCOME_STRATUM} with "
                    f"{len(selected)} cohort stays -- the E-9 gate is "
                    f"unevaluable; E-21)")
    if sel["unknown_status"]:
        invalid.append(f"build_raw will raise unknown-outcome-level on "
                       f"{sorted(sel['unknown_status'])!r} (E-16)")
    for tag in ("aps_present", "apv_present"):
        e = outcome_missingness[tag]
        if (e["gate_applies"] and e["prevalence_ratio"] is not None
                and e["prevalence_ratio"] > EICU_MAX_OUTCOME_PREVALENCE_RATIO):
            invalid.append(
                f"build_raw(arm='primary') will raise "
                f"outcome-informative-missingness on {tag} "
                f"(absent:present prevalence ratio {e['prevalence_ratio']} > "
                f"{EICU_MAX_OUTCOME_PREVALENCE_RATIO}); the declared remedy is "
                f"arm='apache-linked', NOT a widened cap (E-9)")
    if not selected:
        invalid.append("build_raw will raise empty-cohort")
    if expect_reference:
        invalid.extend(f"{m['what']} does not match the released extract "
                       f"({m['got']} != {m['expected']})" for m in mismatches)

    reference_check = {"expect_reference": bool(expect_reference),
                       "ok": not mismatches, "mismatches": mismatches,
                       "split_projection": split_projection,
                       "invalid_conditions": invalid}
    if mismatches and expect_reference:
        raise _err("preflight",
                   "extract does not match the released eICU-CRD v2.0 "
                   "reference counts; a wrong download, v2.0.1, or a re-zip "
                   "parses cleanly and produces numbers for a DIFFERENT dataset",
                   mismatches, reason="reference-row-count-mismatch")
    if mismatches:
        warnings.append(
            f"[MEASURE] T-6: {len(mismatches)} reference mismatch(es) "
            f"(expect_reference=False, so this is a report, not an abort): "
            f"{mismatches!r}")
    if invalid:
        warnings.append(f"[INVALID] the run would abort: {invalid!r}")

    out = {
        "data_dir": str(data_dir),
        "tables": tables,
        "patient": patient_block,
        "cross_site_patients": sel["cross"],
        "site_stay_counts": site_stay_counts,
        "apache": {"apacheApsVar": {"n_rows": aps["n_rows"],
                                    "n_distinct_stays": aps["n_distinct_stays"],
                                    "rows_per_stay_hist": aps["rows_per_stay_hist"],
                                    "n_stays_gt1_row": aps["n_stays_gt1_row"]},
                   "apachePredVar": {"n_rows": apv["n_rows"],
                                     "n_distinct_stays": apv["n_distinct_stays"],
                                     "rows_per_stay_hist": apv["rows_per_stay_hist"],
                                     "n_stays_gt1_row": apv["n_stays_gt1_row"]},
                   "apachePatientResult": {"n_rows": res_rows,
                                           "n_distinct_stays": len(res_per_stay),
                                           "rows_per_stay_hist": dict(sorted(res_hist.items())),
                                           "n_stays_gt1_row": res_gt1}},
        "apache_versions": {"value_counts": dict(version_counts),
                            "version_x_pred_unavailable": version_pred,
                            "preference": list(EICU_APACHE_VERSION_PREFERENCE)},
        "sentinels": {"patient": patient_sent,
                      "apacheApsVar": aps["sentinels"],
                      "apachePredVar": apv["sentinels"]},
        "sentinel_site_dispersion": {"patient": pat_dispersion,
                                     "apacheApsVar": aps["dispersion"],
                                     "apachePredVar": apv["dispersion"]},
        "apache_coverage_by_site": {"apacheApsVar": aps_cov,
                                    "apachePredVar": apv_cov,
                                    "apachePatientResult": res_cov},
        "hospital": hospital,
        "categorical_drift": categorical_drift,
        "outcome_stratified_missingness": outcome_missingness,
        "apache_absent_los": apache_absent_los,
        "unparseable_tokens": {"apacheApsVar": aps["null_tokens"],
                               "apachePredVar": apv["null_tokens"],
                               "over_cap": unparseable_over,
                               "cap": EICU_MAX_UNPARSEABLE_SHARE},
        "join_key_unparseable": {
            t: {"n_rows": b["n_rows"],
                "n_key_unparseable": b["n_key_unparseable"]}
            for t, b in (("apacheApsVar", aps), ("apachePredVar", apv))},
        "attrition": attrition,
        "fio2_convention": {"apacheApsVar": aps["fio2"],
                            "apachePredVar": apv["fio2"]},
        "temperature_convention": {"apacheApsVar": aps["temperature"],
                                   "apachePredVar": apv["temperature"]},
        "ordinal_value_sets": ordinal_value_sets,
        "reference_check": reference_check,
        "predictions": [dict(p) for p in EICU_PREDICTIONS],
        "warnings": warnings,
    }
    if verbose:
        print(f"[eicu] preflight: {len(selected)} primary-cohort stays over "
              f"{n_sites} sites; projected cal={n_cal} "
              f"(MIN_CAL_CLUSTERS={MIN_CAL_CLUSTERS}); "
              f"{len(warnings)} warning(s), {len(invalid)} blocking condition(s)",
              file=sys.stderr)
    return out
