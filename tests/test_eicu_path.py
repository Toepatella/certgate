"""SPEC "Real-data protocol": the eICU mock corpus, end to end.

`experiments/eicu_mock.py` emits a schema-faithful, byte-deterministic gzip-CSV
corpus carrying every documented eICU-CRD v2.0 wart (dual `-1`/`''` sentinels,
the HIPAA `'> 89'` age token, negative admit offsets whose EARLIEST stay has
the HIGHEST one, multi-row `apachePatientResult` across `'IV'`/`'IVa'`,
site-correlated APACHE coverage, heavy-tailed hospital sizes, duplicate stay
ids, cross-hospital `uniquepid`, a BOM, embedded newlines, mixed `fio2` and
temperature units); `experiments/eicu_etl.py` turns it into a finite float64
feature matrix, raw two-valued outcome strings and raw hospital site labels;
`from_raw` -> `run_certgate` must reach an HONEST outcome on it -- a certificate
whose oracle-checked answered risk respects its own alpha, or a decline.
Certification is never asserted; honesty is.

The load-bearing tests here are the LEAK KILLERS (T-1, failure criterion F-D).
A leak in this path produces a spectacular and entirely fake result, so the
denylist is proved three ways: structurally (allowlist and denylist disjoint
and jointly exhaustive over every DDL column of the five source tables),
by name (`assert_no_leak_columns` over the 36-entry denylist, and it must RAISE
when a leak is reintroduced), and behaviourally (a head fit on the shipped
matrix cannot approach the discrimination a reintroduced label column trivially
attains).

The always-on arm keeps the default suite fast; the full-scale arm (208
hospitals / 200,859 stays -- the real eICU scale) runs only when
CERTGATE_EICU=1.
"""
from __future__ import annotations

import ast
import csv
import gzip
import hashlib
import io
import json
import math
import os
import pathlib
import random
import shutil
from collections import Counter

import numpy as np
import pytest
from sklearn.metrics import roc_auc_score

from certgate.constants import ALPHA_LADDER, MIN_CAL_CLUSTERS, SPLIT_FRACTIONS
from certgate.harness import hard_violation
from certgate.model import fit_head
from certgate.pipeline import run_certgate
from certgate.report import render_text
from certgate.validate import (Cohort, assert_site_disjoint, densify_sites,
                               from_raw, normalized_label)
from experiments import eicu_etl as etl
from experiments import eicu_mock as mock
from experiments import run_eicu
from experiments import run_synthetic

# ---------------------------------------------------------------------------
# Sizes for the auxiliary corpora. The canonical small arm is the mock's own
# default (180 hospitals / 9000 stays -> 63 carrying calibration sites, so
# certification is REACHABLE and a decline is equally legitimate). The tiny
# byte-determinism corpus deliberately runs signal=False, the one configuration
# in which `generate` admits fewer than EICU_MIN_TOTAL_SITES sites.
TINY_SITES, TINY_STAYS = 60, 900
DRIFT_STAYS = 2400

# F-D, the unfalsifiable-success failure: a good result is a leak alarm. The
# mock's outcome is driven by a latent severity at the frozen slope
# EICU_MOCK_SIGNAL_B = 0.85, whose Bayes-optimal AUC is Phi(0.85/sqrt(2)) =
# 0.726; the shipped clean corpus measures 0.597. The ceiling is therefore set
# from that stated Bayes-optimal value plus a margin -- NOT 25 points above it.
#
# 2026-07-31 audit, E-10: the old ceiling was 0.98, so a probe whose own
# comment computed the honest ceiling as ~0.73 could only detect a leak of
# near-label strength -- which is exactly what its single positive control
# injected. A leak-planted corpus measuring 0.835 passed it. 0.80 leaves ~0.07
# of headroom over the Bayes-optimal value for finite-sample noise and still
# refuses anything a latent-severity model at B = 0.85 cannot produce.
LEAK_AUC_CEILING = 0.80

# The subtle positive control: outcome-correlated APACHE-row absence at this
# rate. Nothing else about the corpus changes. At p = 0.30 the shipped small
# corpus measures head AUC 0.671 (BELOW the ceiling above -- which is why the
# AUC leg alone is not enough), missingness-ablation drop +0.082, and an
# absent:present outcome prevalence ratio of 3.86.
LEAK_ABSENCE_RATE = 0.30

# Generous on purpose: the load-bearing assertion is the pandas/pyarrow refusal
# (audit F16), and this set only has to keep a genuinely new third-party import
# from passing unnoticed.
_STDLIB_OK = {
    "__future__", "abc", "argparse", "array", "ast", "bisect", "collections",
    "contextlib", "copy", "csv", "dataclasses", "datetime", "decimal", "enum",
    "functools", "glob", "gzip", "hashlib", "heapq", "importlib", "inspect",
    "io", "itertools", "json", "logging", "math", "numbers", "operator", "os",
    "pathlib", "platform", "pprint", "random", "re", "shutil", "statistics",
    "string", "struct", "sys", "tempfile", "textwrap", "time", "typing",
    "unicodedata", "warnings", "zlib",
}

PREFLIGHT_KEYS = {
    "data_dir", "tables", "patient", "cross_site_patients", "site_stay_counts",
    "apache", "apache_versions", "sentinels", "sentinel_site_dispersion",
    "apache_coverage_by_site", "hospital", "categorical_drift", "attrition",
    "fio2_convention", "temperature_convention", "ordinal_value_sets",
    "reference_check", "predictions", "warnings",
    # 2026-07-31 audit: the three screens the old preflight had nowhere.
    "outcome_stratified_missingness",   # E-9  outcome-informative absence
    "apache_absent_los",                # E-9  site channel vs outcome channel
    "unparseable_tokens",               # E-15 a NULL token that is not ''
    # 2026-07-31 arrival-day audit (A5): the join-key format profile, so the
    # unparseable-join-key / apache-coverage-collapse raises are projected.
    "join_key_unparseable",             # E-21 an unlinked child table
}

# E-17: the casing verdict is DECIDABLE, so it is pinned PER TABLE for both
# mock header modes rather than accepted as "one of the three".
HEADER_CASE_EXPECTED = {"camel": "camel", "lower": "lower"}

MANIFEST_KEYS = {
    "seed", "stays_requested", "stays_written", "admissions", "sites",
    "site_size_sigma", "base_rate", "header_case", "signal", "warts", "drift",
    "row_counts", "apache_site_coverage_bands", "sites_with_zero_result_rows",
}

# Every leak the protocol names (§A.7). Asserted by NAME so that deleting a
# denylist row cannot pass silently.
KNOWN_LEAKS = (
    "diedinhospital", "actualhospitalmortality", "actualicumortality",
    "hospitaldischargestatus", "hospitaldischargelocation",
    "unitdischargestatus", "unitdischargelocation", "hospitaldischargeoffset",
    "unitdischargeoffset", "dischargeweight", "actualiculos",
    "actualhospitallos", "unabridgedunitlos", "unabridgedhosplos",
    "actualventdays", "unabridgedactualventdays", "saps3today",
    "saps3yesterday", "var03hspxlos", "dischargelocation",
    "hospitaldischargetime24", "unitdischargetime24", "hospitalid", "wardid",
    "hospitaldischargeyear", "predictedhospitalmortality", "apachescore",
    "acutephysiologyscore",
)

# The `patient` source columns that DO contribute features (§A.5.1/§A.5.2).
# `hospitaladmitoffset` is the source of the `pre_icu_hours` feature -- the one
# allowlisted column whose feature name differs from its column name.
ALLOW_PATIENT = frozenset({
    "age", "admissionheight", "admissionweight", "hospitaladmitoffset",
    "gender", "ethnicity", "hospitaladmitsource", "unitadmitsource",
    "unittype", "unitstaytype",
})

# Deny-by-default's third bucket: columns that are neither features nor leaks
# -- surrogate/natural keys, admission-time timestamps that carry no outcome
# information and are not modelled, the APACHE version tag, and the
# site-CONSTANT `hospital` covariates read only as diagnostic strata (§A.6).
# Pinned per table so that a new column in the schema, or a column silently
# promoted into the allowlist, fails the exhaustiveness test.
NEITHER = {
    "patient": frozenset({
        "patientunitstayid", "patienthealthsystemstayid",
        "hospitaladmittime24", "unitadmittime24", "uniquepid"}),
    "hospital": frozenset({"numbedscategory", "teachingstatus", "region"}),
    "apacheApsVar": frozenset({"apacheapsvarid", "patientunitstayid"}),
    "apachePredVar": frozenset({
        "apachepredvarid", "patientunitstayid", "sicuday", "saps3day1",
        "gender", "teachtype", "region", "bedcount", "admitsource", "meds",
        "verbal", "motor", "eyes", "age", "admitdiagnosis", "managementsystem",
        "pao2", "fio2", "creatinine", "visitnumber", "amilocation", "day1meds",
        "day1verbal", "day1motor", "day1eyes", "day1pao2", "day1fio2"}),
    "apachePatientResult": frozenset({
        "apachepatientresultsid", "patientunitstayid", "apacheversion",
        "preopmi", "preopcardiaccath", "ptcawithin24h"}),
}


# ------------------------------------------------------------------ helpers --

def _gz_hashes(data_dir) -> dict:
    """sha256 of every `.csv.gz` in a corpus directory, keyed by filename."""
    out = {}
    for p in sorted(pathlib.Path(data_dir).iterdir()):
        if p.name.endswith(".csv.gz"):
            out[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def _int_leaf_sum(obj) -> int:
    """Sum of every integer leaf in a nested counter structure.

    The ETL's counter dicts (`sentinel_counts`, `dedup_counts`, ...) are frozen
    by NAME but not by internal shape; summing the leaves asserts "this channel
    fired" without pinning a nesting the contract leaves open.
    """
    if isinstance(obj, bool):
        return 0
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, dict):
        return sum(_int_leaf_sum(v) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return sum(_int_leaf_sum(v) for v in obj)
    return 0


def _schema_columns(table) -> list:
    """Lowercased DDL column names for one source table, in DDL order."""
    return [str(c).lower() for c, _ in mock.EICU_MOCK_SCHEMA[table]]


def _deny_bare() -> set:
    """Denylisted column names with any `table.` qualifier stripped."""
    return {str(c).split(".")[-1].lower() for c, _ in etl.EICU_LEAK_DENYLIST}


# ---- minimal hand-built corpora: one planted trap per corpus, no mock -------
#
# The mock plants every wart at a RATE; these corpora plant one exactly, so a
# regression in a single documented trap goes red on its own line rather than
# perturbing an aggregate. Column names and DDL order come from
# EICU_MOCK_SCHEMA, so the two writers cannot drift apart.

_PATIENT_ROW = dict(
    patientunitstayid="1", patienthealthsystemstayid="1", gender="Male",
    age="55", ethnicity="Caucasian", hospitalid="1", wardid="10",
    apacheadmissiondx="Sepsis", admissionheight="170.0",
    hospitaladmittime24="10:00:00", hospitaladmitoffset="-120",
    hospitaladmitsource="Emergency Department", hospitaldischargeyear="2014",
    hospitaldischargetime24="18:00:00", hospitaldischargeoffset="4320",
    hospitaldischargelocation="Home", hospitaldischargestatus="Alive",
    unittype="MICU", unitadmittime24="10:00:00",
    unitadmitsource="Emergency Department", unitvisitnumber="1",
    unitstaytype="admit", admissionweight="80.0", dischargeweight="81.0",
    unitdischargetime24="12:00:00", unitdischargeoffset="1440",
    unitdischargelocation="Floor", unitdischargestatus="Alive",
    uniquepid="001-0001")

_APS_VALUES = dict(
    intubated="0", vent="0", dialysis="0", eyes="4", motor="6", verbal="5",
    meds="0", urine="1500", wbc="9.5", temperature="37.0",
    respiratoryrate="18", sodium="140", heartrate="88", meanbp="75",
    ph="7.38", hematocrit="35.0", creatinine="1.0", albumin="3.4",
    pao2="90", pco2="40", bun="18", glucose="110", bilirubin="0.8",
    fio2="0.35")

_APV_VALUES = dict(
    graftcount="0", thrombolytics="0", aids="0", hepaticfailure="0",
    lymphoma="0", metastaticcancer="0", leukemia="0", immunosuppression="0",
    cirrhosis="0", electivesurgery="0", activetx="1", readmit="0", ima="0",
    midur="0", ventday1="0", oobventday1="0", oobintubday1="0", diabetes="0",
    ejectfx="55")


def _patient(stay, **over):
    row = dict(_PATIENT_ROW)
    row["patientunitstayid"] = str(stay)
    row["patienthealthsystemstayid"] = str(stay)
    row["uniquepid"] = f"001-{int(stay):04d}"
    row.update({k: str(v) for k, v in over.items()})
    return row


def _aps(stay, sid, fill=None, **over):
    row = dict(_APS_VALUES) if fill is None else {k: fill for k in _APS_VALUES}
    row.update({k: str(v) for k, v in over.items()})
    row["apacheapsvarid"] = str(sid)
    row["patientunitstayid"] = str(stay)
    return row


def _apv(stay, sid, fill=None, **over):
    row = dict(_APV_VALUES) if fill is None else {k: fill for k in _APV_VALUES}
    row.update({k: str(v) for k, v in over.items()})
    row["apachepredvarid"] = str(sid)
    row["patientunitstayid"] = str(stay)
    return row


def _result(stay, sid, version, pred):
    return dict(apachepatientresultsid=str(sid), patientunitstayid=str(stay),
                apacheversion=version, predictedhospitalmortality=str(pred),
                actualhospitalmortality="ALIVE", predictedicumortality="0.05",
                actualicumortality="ALIVE", acutephysiologyscore="40",
                apachescore="55", physicianspeciality="critical care medicine",
                physicianinterventioncategory="", predictediculos="2.0",
                actualiculos="1.9", predictedhospitallos="6.0",
                actualhospitallos="5.5", preopmi="-1", preopcardiaccath="-1",
                ptcawithin24h="-1", unabridgedunitlos="1.9",
                unabridgedhosplos="5.5", actualventdays="0.0",
                predventdays="0.0", unabridgedactualventdays="0.0")


def _hospital(hid):
    return dict(hospitalid=str(hid), numbedscategory="250-499",
                teachingstatus="t", region="Midwest")


def _write_corpus(dst, rows_by_table) -> str:
    """Write a five-table gzip-CSV corpus with DDL column names and order.

    Byte-determinism discipline mirrors `synth_fixture.TableWriter`
    (`GzipFile(filename="", mtime=0, fileobj=...)` + `TextIOWrapper(newline="")`)
    so a planted corpus is reproducible too; `csv.writer` owns the line endings.
    """
    os.makedirs(dst, exist_ok=True)
    for table in mock.EICU_MOCK_TABLES:
        cols = [str(c) for c, _ in mock.EICU_MOCK_SCHEMA[table]]
        with open(os.path.join(dst, f"{table}.csv.gz"), "wb") as raw:
            gz = gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0)
            fh = io.TextIOWrapper(gz, encoding="utf-8", newline="")
            w = csv.writer(fh, quoting=csv.QUOTE_MINIMAL)
            w.writerow(cols)
            for r in rows_by_table.get(table, ()):
                w.writerow([str(r.get(c.lower(), "")) for c in cols])
            fh.close()
    return dst


def _row_of(meta, stay) -> int:
    """Matrix row index carrying a given `patientunitstayid` (order-free)."""
    hit = np.flatnonzero(np.asarray(meta["stay_id"]) == int(stay))
    assert hit.size == 1, f"stay {stay} appears {hit.size} times, expected 1"
    return int(hit[0])


def _col_of(names, feature) -> int:
    return list(names).index(feature)


def _attrition(meta_or_pf) -> dict:
    """Attrition ledger as {step: n_stays}, order asserted separately."""
    return {e["step"]: e["n_stays"] for e in meta_or_pf["attrition"]}


# ------------------------------------------------------ end-to-end driver ----

def _run_eicu(data_dir, replicate=0):
    """generate-already-done -> ETL -> cohorts -> run_certgate. (rep, ctx)."""
    x_raw, names, meta = etl.build_raw(data_dir, verbose=False)
    idx, sets = etl.site_split(meta["site_raw"], replicate=replicate)
    x, fill = etl.impute(x_raw, idx["train"])
    y_raw = etl.labels(meta)
    site_raw = list(meta["site_raw"])

    def cohort(key, strict=True):
        sel = idx[key]
        return from_raw(x[sel], [y_raw[i] for i in sel],
                        etl.EICU_POSITIVE_LABEL,
                        [site_raw[i] for i in sel],
                        require_both_classes=strict)

    train, aux, cal = cohort("train"), cohort("aux"), cohort("cal")
    target = cohort("target", strict=False)
    # records never cross a boundary; the assertion runs BEFORE every certification
    assert_site_disjoint(train=train, aux=aux, cal=cal)
    tgt_sites = [site_raw[i] for i in idx["target"]]
    rep = run_certgate(train, aux, cal, target.x,
                       target_label=etl.EICU_POOLED_TARGET_LABEL,
                       target_site_id=tgt_sites, oracle_target_y=target.y)
    ctx = dict(train=train, aux=aux, cal=cal, target=target,
               tgt_sites=tgt_sites, meta=meta, names=names, x=x, x_raw=x_raw,
               fill=fill, idx=idx, sets=sets, y_raw=y_raw, site_raw=site_raw,
               y_bool=np.asarray([v == etl.EICU_POSITIVE_LABEL
                                  for v in y_raw], dtype=bool))
    return rep, ctx


def _assert_honest(rep, ctx):
    """The only acceptable outcomes: a valid certificate, or a decline."""
    parts = rep["decline_partition"]
    assert sum(parts.values()) == ctx["target"].n
    assert "[partition]" in render_text(rep)      # renders without KeyError
    op = rep["operative"]
    if op is None:
        assert not rep["answered_mask"].any()
        return "declined"
    head = fit_head(ctx["train"])                 # deterministic: same head
    err = head.predict(ctx["target"].x) != ctx["target"].y
    ans = rep["answered_mask"]
    # the certificate's own alpha must not be hard-violated by the oracle
    assert not hard_violation(err[ans], op["alpha"])
    return "certified"


# ----------------------------------------------------------------- fixtures --

@pytest.fixture(scope="module")
def mock_small(tmp_path_factory):
    """The canonical small corpus, generated ONCE (never into the repo)."""
    out = str(tmp_path_factory.mktemp("eicu_small") / "corpus")
    manifest = mock.generate(mock.MockConfig(out=out))
    return dict(dir=out, manifest=manifest)


@pytest.fixture(scope="module")
def mock_tiny(tmp_path_factory):
    """Two byte-identical runs plus a `--tables` projection, same seed.

    signal=False is the one configuration in which `generate` admits fewer than
    EICU_MIN_TOTAL_SITES sites, so the determinism arm stays cheap.
    """
    base = tmp_path_factory.mktemp("eicu_tiny")
    cfgs = {}
    for key, tables in (("a", None), ("b", None),
                        ("subset", ["patient", "hospital"])):
        out = str(base / key)
        kw = dict(stays=TINY_STAYS, sites=TINY_SITES, signal=False, out=out)
        if tables is not None:
            kw["tables"] = tables
        mock.generate(mock.MockConfig(**kw))
        cfgs[key] = out
    return cfgs


def _plant_outcome_correlated_absence(src, dst, rate, seed=7):
    """Copy a corpus, deleting APACHE rows for a fraction of DECEDENTS.

    This is the mechanism of the 2026-07-31 critical finding (E-9) in its
    purest form: "the day-1 window did not close because the stay ended".
    NOTHING else about the corpus changes -- same features, same labels, same
    hospitals, same coverage band structure -- so anything the pipeline sees
    downstream is attributable to this channel alone. The resulting APACHE
    coverage stays indistinguishable from the released extract's
    171177/200859 = 0.852, which is why coverage cannot be the screen.
    """
    os.makedirs(dst, exist_ok=True)
    rng = random.Random(seed)
    doomed = set()
    for row in etl.read_table(src, "patient"):
        if (row["hospitaldischargestatus"] or "").strip() == "Expired":
            sid = etl._maybe_int(row["patientunitstayid"])
            if sid is not None and rng.random() < rate:
                doomed.add(sid)
    for table in mock.EICU_MOCK_TABLES:
        sp = etl._resolve_table_path(src, table)
        dp = os.path.join(dst, f"{table}.csv.gz")
        if table not in ("apacheApsVar", "apachePredVar"):
            shutil.copyfile(sp, dp)
            continue
        with open(dp, "wb") as raw:
            gz = gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0)
            fh = io.TextIOWrapper(gz, encoding="utf-8", newline="")
            w = csv.writer(fh, quoting=csv.QUOTE_MINIMAL)
            with gzip.open(sp, "rt", encoding="utf-8-sig", newline="") as f:
                r = csv.reader(f)
                header = next(r)
                w.writerow(header)
                j = [h.strip().lower() for h in header].index("patientunitstayid")
                for row in r:
                    if not row:
                        continue
                    sid = etl._maybe_int(row[j]) if j < len(row) else None
                    if sid in doomed:
                        continue
                    w.writerow(row)
            fh.close()
    assert doomed, "the leak fixture planted nothing"
    return dst


@pytest.fixture(scope="module")
def mock_leak(tmp_path_factory, mock_small):
    """Outcome-correlated APACHE-row absence at LEAK_ABSENCE_RATE (E-9)."""
    out = str(tmp_path_factory.mktemp("eicu_leak") / "corpus")
    return _plant_outcome_correlated_absence(mock_small["dir"], out,
                                             LEAK_ABSENCE_RATE)


def _plant_column_level_absence(src, dst, rate, seed=11):
    """Copy a corpus, BLANKING every allowlisted APS cell for some decedents.

    The row is KEPT, so `aps_present` stays 1 for every stay and the whole-row
    prevalence-ratio abort structurally cannot see this. What moves is the 24
    `aps_*__missing` siblings. The mechanism is realistic -- a panel that stops
    being drawn once a patient is dying -- and it is the case that proves the
    F-D ablation leg has power the ratio gate does not: the two gates cover
    different halves of the same channel.
    """
    os.makedirs(dst, exist_ok=True)
    rng = random.Random(seed)
    doomed = set()
    for row in etl.read_table(src, "patient"):
        if (row["hospitaldischargestatus"] or "").strip() == "Expired":
            sid = etl._maybe_int(row["patientunitstayid"])
            if sid is not None and rng.random() < rate:
                doomed.add(sid)
    for table in mock.EICU_MOCK_TABLES:
        sp = etl._resolve_table_path(src, table)
        dp = os.path.join(dst, f"{table}.csv.gz")
        if table != "apacheApsVar":
            shutil.copyfile(sp, dp)
            continue
        with open(dp, "wb") as raw:
            gz = gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0)
            fh = io.TextIOWrapper(gz, encoding="utf-8", newline="")
            w = csv.writer(fh, quoting=csv.QUOTE_MINIMAL)
            with gzip.open(sp, "rt", encoding="utf-8-sig", newline="") as f:
                r = csv.reader(f)
                header = next(r)
                w.writerow(header)
                low = [h.strip().lower() for h in header]
                j = low.index("patientunitstayid")
                blank = [low.index(c) for c in etl.EICU_APS_NUMERIC]
                for row in r:
                    if not row:
                        continue
                    sid = etl._maybe_int(row[j]) if j < len(row) else None
                    if sid in doomed:
                        row = list(row) + [""] * max(0, len(low) - len(row))
                        for b in blank:
                            row[b] = ""
                    w.writerow(row)
            fh.close()
    assert doomed, "the column-level leak fixture planted nothing"
    return dst


@pytest.fixture(scope="module")
def mock_leak_subcap(tmp_path_factory, mock_small):
    """A COLUMN-level leak: the rows survive, only the cells go missing.

    `build_raw` succeeds on this corpus -- the presence flags are untouched, so
    the prevalence-ratio abort cannot fire -- and the only thing left to catch
    it is the missingness-ablation leg of F-D, the leg the old alpha- and
    coverage-conditioned F-D did not have.
    """
    out = str(tmp_path_factory.mktemp("eicu_leak_sub") / "corpus")
    # Calibrated: head AUC 0.705 (BELOW EICU_LEAK_AUC_CEILING = 0.90, so the
    # discrimination leg is silent), ablation drop +0.106 (over the 0.05 cap),
    # whole-row presence ratio 1.11 (unchanged from the clean corpus).
    return _plant_column_level_absence(mock_small["dir"], out, 0.35)


@pytest.fixture(scope="module")
def mock_drift(tmp_path_factory):
    """A corpus whose categorical drift is pushed PAST EICU_MAX_OTHER_SHARE."""
    out = str(tmp_path_factory.mktemp("eicu_drift") / "corpus")
    mock.generate(mock.MockConfig(stays=DRIFT_STAYS,
                                  sites=mock.EICU_MOCK_SMALL_SITES,
                                  drift=True, out=out))
    return out


@pytest.fixture(scope="module")
def pipeline_small(mock_small):
    """The full always-on path: ETL -> split -> impute -> cohorts -> certgate.

    Built ONCE: re-reading the extract per test is a build error, not a style
    preference (T-16)."""
    rep, ctx = _run_eicu(mock_small["dir"])
    return dict(rep=rep, **ctx)


@pytest.fixture(scope="module")
def planted(tmp_path_factory):
    """Sentinel corpus: one clean stay, one all-`-1`, one all-`''`, one with no
    APACHE row at all."""
    dst = str(tmp_path_factory.mktemp("eicu_planted") / "corpus")
    return _write_corpus(dst, {
        "patient": [_patient(1), _patient(2), _patient(3), _patient(4)],
        "hospital": [_hospital(1)],
        "apacheApsVar": [_aps(1, 11), _aps(2, 12, fill="-1"),
                         _aps(3, 13, fill="")],
        "apachePredVar": [_apv(1, 21), _apv(2, 22, fill="-1"),
                          _apv(3, 23, fill="")],
        "apachePatientResult": [_result(1, 31, "IVa", "0.15")],
    })


@pytest.fixture(scope="module")
def planted_dedup(tmp_path_factory):
    """Dedup corpus: IV/IVa version preference, duplicate surrogate ids in both
    `apachePatientResult` and `apacheApsVar`, and a `'-1'` STRING probability."""
    dst = str(tmp_path_factory.mktemp("eicu_dedup") / "corpus")
    return _write_corpus(dst, {
        "patient": [_patient(s) for s in (1, 2, 3, 4, 5)],
        "hospital": [_hospital(1)],
        # stay 1 carries a duplicate APS row: min(apacheapsvarid) wins, so the
        # matrix must take heartrate 88, never the 200 on the higher id
        "apacheApsVar": [_aps(1, 11), _aps(1, 99, heartrate="200")],
        "apachePredVar": [_apv(1, 21)],
        "apachePatientResult": [
            _result(1, 10, "IV", "0.11"), _result(1, 11, "IVa", "0.22"),
            _result(2, 20, "IV", "0.33"),
            _result(3, 30, "IVa", "0.44"), _result(3, 29, "IVa", "0.55"),
            _result(4, 40, "IVa", "-1"),
        ],
    })


# =============================================================== 1-3. mock ===

def test_mock_is_byte_deterministic(mock_tiny):
    """Two runs at the same seed are byte-identical per `.csv.gz` -- the gzip
    header is frozen (`filename=""`, `mtime=0`) and every RNG stream is derived
    from the seed, so a corpus is a reproducible input, not a snapshot."""
    ha, hb = _gz_hashes(mock_tiny["a"]), _gz_hashes(mock_tiny["b"])
    assert ha, "no .csv.gz files written"
    assert ha == hb


def test_mock_table_subset_is_a_byte_identical_projection(mock_tiny):
    """`--tables patient,hospital` is a PROJECTION of the full run, not a
    different draw: the plan always runs in full and id counters are per table,
    so a subset can be regenerated without re-deriving the whole corpus."""
    full, sub = _gz_hashes(mock_tiny["a"]), _gz_hashes(mock_tiny["subset"])
    assert set(sub) == {"patient.csv.gz", "hospital.csv.gz"}
    for name, digest in sub.items():
        assert digest == full[name], f"{name} is not a byte-identical projection"


def test_mock_manifest_has_the_frozen_key_set(mock_small):
    m = mock_small["manifest"]
    assert set(m) == MANIFEST_KEYS
    assert m["seed"] == mock.EICU_MOCK_SEED
    assert m["sites"] == mock.EICU_MOCK_SMALL_SITES
    assert m["stays_requested"] == mock.EICU_MOCK_SMALL_STAYS
    assert m["signal"] is True and m["drift"] is False
    assert set(m["row_counts"]) == set(mock.EICU_MOCK_TABLES)
    json.dumps(m)                                  # manifest.json round-trips


def test_mock_level_tuples_match_the_etl_tuples():
    """The sanctioned stdlib-only duplication is PINNED: `eicu_mock` may not
    import numpy (and therefore may not import `eicu_etl`), so its level tuples
    are copies -- copies that must never drift from the protocol's."""
    for suffix in ("GENDER", "ETHNICITY", "ADMITSOURCE", "UNITTYPE",
                   "UNITSTAYTYPE"):
        assert (getattr(mock, f"EICU_MOCK_LEVELS_{suffix}")
                == getattr(etl, f"EICU_LEVELS_{suffix}")), suffix


def test_mock_cli_parses_and_rejects_unknown_values():
    cfg = mock.parse_args([])
    assert cfg.seed == mock.EICU_MOCK_SEED
    assert cfg.sites == mock.EICU_MOCK_SMALL_SITES
    assert cfg.stays == mock.EICU_MOCK_SMALL_STAYS
    assert cfg.signal is True and cfg.warts is True
    assert cfg.header_case in mock.EICU_MOCK_HEADER_CASES
    assert mock.parse_args(["--tables", "patient,hospital"]).tables == \
        ["patient", "hospital"]
    with pytest.raises(SystemExit):
        mock.parse_args(["--tables", "patient,notATable"])
    with pytest.raises(SystemExit):
        mock.parse_args(["--header-case", "sNaKe"])


# ==================================================== 4-5. feature contract ===

def test_feature_name_list_matches_the_pinned_width():
    names = etl.feature_names()
    assert names == list(etl.FEATURE_NAMES)
    assert len(names) == etl.EICU_N_FEATURES == 161
    assert len(set(names)) == len(names), "duplicate feature name"
    # every __missing sibling is IMMEDIATELY adjacent to its parent, so a
    # column and its indicator can never be reordered apart
    for i, nm in enumerate(names):
        if nm.endswith("__missing"):
            assert i > 0 and names[i - 1] == nm[: -len("__missing")], nm
    # the block arithmetic of §A.5.8
    assert len(etl.EICU_PATIENT_NUMERIC) == 4
    assert len(etl.EICU_APS_NUMERIC) == 24
    assert len(etl.EICU_APV_NUMERIC) == 19
    assert names[-2:] == ["aps_present", "apv_present"]
    assert "age_masked" in names
    assert "age_masked__missing" not in names      # an indicator is never NaN
    assert sum(1 for n in names if n.startswith("aps_")) == 24 * 2 + 1
    assert sum(1 for n in names if n.startswith("apv_")) == 19 * 2 + 1


def test_leak_denylist_excludes_every_known_leak_from_features():
    """T-1. Every documented leak is on the denylist AND absent from the
    feature names in every form the ETL could have emitted it."""
    assert len(etl.EICU_LEAK_DENYLIST) == 36
    bare = _deny_bare()
    names = etl.feature_names()
    for col in KNOWN_LEAKS:
        assert col in bare, f"{col} is not on EICU_LEAK_DENYLIST"
        for form in (col, f"aps_{col}", f"apv_{col}", f"{col}__missing",
                     f"aps_{col}__missing", f"apv_{col}__missing"):
            assert form not in names, f"leak {form} reached FEATURE_NAMES"
        assert not any(n.startswith(f"{col}=") for n in names), col
    etl.assert_no_leak_columns(names)              # the shipped list is clean


def test_assert_no_leak_columns_raises_when_a_leak_is_reintroduced():
    """The denylist is only worth what its enforcement is worth: adding a leak
    back in ANY of the sanctioned spellings must raise, not warn."""
    names = etl.feature_names()
    for reintroduced in ("diedinhospital", "apv_diedinhospital",
                         "apv_diedinhospital__missing",
                         "actualhospitalmortality", "hospitalid",
                         "hospitalid=420", "aps_apachescore"):
        with pytest.raises(etl.EicuError, match="leak-column-in-features"):
            etl.assert_no_leak_columns(names + [reintroduced])


def test_allowlist_and_denylist_are_disjoint_and_jointly_exhaustive():
    """Deny by DEFAULT, proved structurally.

    Every DDL column of the five source tables lands in exactly one of three
    buckets -- allowlisted feature source, denylisted, or a pinned
    neither-bucket of keys/timestamps/site-constant strata. A column moved from
    the denylist into the allowlist collides; a column quietly dropped from the
    denylist becomes unclassified. Both fail here, which is the point: the
    allowlist cannot grow by accident.
    """
    deny = _deny_bare()
    allow = {"patient": ALLOW_PATIENT,
             "hospital": frozenset(),
             "apacheApsVar": frozenset(etl.EICU_APS_NUMERIC),
             "apachePredVar": frozenset(etl.EICU_APV_NUMERIC),
             "apachePatientResult": frozenset()}
    # the allowlist's own names agree with the ETL's numeric tuples
    assert {"age", "admissionheight", "admissionweight"} <= \
        set(etl.EICU_PATIENT_NUMERIC)
    assert "pre_icu_hours" in etl.EICU_PATIENT_NUMERIC   # <- hospitaladmitoffset

    unclassified = {}
    for table in mock.EICU_MOCK_TABLES:
        cols = set(_schema_columns(table))
        a, n = allow[table], NEITHER[table]
        d = cols & deny
        assert not (a & d), f"{table}: allowlisted AND denylisted: {sorted(a & d)}"
        assert not (a & n), f"{table}: allowlisted AND in the neither-bucket"
        assert not (d & n), f"{table}: denylisted AND in the neither-bucket"
        assert a <= cols, f"{table}: allowlist names not in the DDL: {sorted(a - cols)}"
        assert n <= cols, f"{table}: neither-bucket names not in the DDL"
        rest = cols - a - d - n
        if rest:
            unclassified[table] = sorted(rest)
    assert not unclassified, (
        f"columns classified neither as features, leaks, nor keys: "
        f"{unclassified} -- deny by default means every column has a verdict")
    # `apachePatientResult` and `hospital` contribute NO features (§A.6): the
    # first has 8.65% zero-coverage hospitals, the second is site-CONSTANT.
    assert not allow["apachePatientResult"] and not allow["hospital"]


def test_no_leak_reaches_the_matrix_via_implausible_discrimination(
        pipeline_small):
    """T-1/F-D behaviourally: a leak announces itself as implausible AUC.

    The ceiling is set from the mock's own STATED Bayes-optimal AUC (0.726 at
    EICU_MOCK_SIGNAL_B = 0.85) plus a margin. The 2026-07-31 audit (E-10) found
    it at 0.98 -- 25 points above the value the constant's own comment computed
    -- so the probe could only see a leak of near-label strength, which is
    exactly what its single positive control injected.
    """
    train, cal = pipeline_small["train"], pipeline_small["cal"]
    head = fit_head(train)
    auc = roc_auc_score(cal.y, head.predict_proba(cal.x))
    assert 0.0 <= auc <= LEAK_AUC_CEILING, (
        f"out-of-sample AUC {auc:.4f} exceeds the leak ceiling "
        f"{LEAK_AUC_CEILING} -- re-audit EICU_LEAK_DENYLIST and the "
        f"first-stay/dedup logic before reporting any number (F-D)")

    # positive control: the probe has the power to see a leak of this kind
    leak_train = Cohort(x=np.column_stack([train.x, train.y.astype(np.float64)]),
                        y=train.y, site_id=train.site_id,
                        site_labels=train.site_labels)
    leak_head = fit_head(leak_train)
    leak_auc = roc_auc_score(
        cal.y, leak_head.predict_proba(
            np.column_stack([cal.x, cal.y.astype(np.float64)])))
    assert leak_auc > 0.95, (
        "the AUC probe cannot detect an outcome column and is therefore not a "
        "leak test")
    assert auc < leak_auc


def test_leak_auc_ceiling_sits_just_above_the_mocks_bayes_optimal_auc():
    """E-10: the ceiling must be DERIVED from the mock's own outcome model.

    Phi(B/sqrt(2)) is the AUC a score recovering the latent severity PERFECTLY
    attains, so it is the honest upper bound for anything the mock can produce.
    A ceiling far above it makes the probe decorative; a ceiling below it makes
    the suite flaky. Pinning the relation here is what stops the 0.98 the audit
    found from coming back.
    """
    bayes = 0.5 * (1.0 + math.erf(mock.EICU_MOCK_SIGNAL_B / 2.0))
    assert bayes == pytest.approx(0.7264, abs=5e-4)
    assert bayes < LEAK_AUC_CEILING <= bayes + 0.08
    assert LEAK_AUC_CEILING == 0.80          # literal pin, per audit F13


def test_outcome_correlated_apache_absence_is_caught_before_any_certificate(
        mock_leak):
    """THE critical finding (E-9), as a regression test.

    APACHE day-1 rows do not exist for a stay that ends BECAUSE THE PATIENT
    DIED before the window closes, so `aps_present` / `apv_present` and the 43
    `__missing` siblings are a partial OUTCOME proxy with no column name --
    invisible to the 36-entry denylist, to the `-1` gate, to the drift gate,
    and to the old alpha- and coverage-conditioned F-D.

    `mock_leak` plants exactly that mechanism at LEAK_ABSENCE_RATE and changes
    nothing else. Three assertions, in the order the pipeline meets them:
    preflight MEASURES it, `build_raw` ABORTS on it, and the declared
    `apache-linked` arm is the escape that pays the immortal-time cost.
    """
    # 1. preflight measures it and names the raise build_raw will make
    pf = etl.preflight(mock_leak, verbose=False)
    osm = pf["outcome_stratified_missingness"]["aps_present"]
    assert osm["gate_applies"]
    assert osm["prevalence_ratio"] > etl.EICU_MAX_OUTCOME_PREVALENCE_RATIO
    assert any("outcome-informative-missingness" in c
               for c in pf["reference_check"]["invalid_conditions"])
    assert any("E-9" in w for w in pf["warnings"])
    # the ledger's own prevalence collapse, which n_stays alone cannot show
    ledger = {e["step"]: e for e in pf["attrition"]}
    assert (ledger["apache-aps-linked"]["prevalence"]
            < ledger["primary-cohort"]["prevalence"])
    # ... and the LOS diagnostic that separates the site channel from the
    # outcome channel: absent stays are short because they ENDED
    los = pf["apache_absent_los"]
    assert los["aps_absent"]["n"] > 0 and los["aps_present"]["n"] > 0

    # 2. build_raw refuses to produce a matrix at all
    with pytest.raises(etl.EicuError,
                       match="outcome-informative-missingness"):
        etl.build_raw(mock_leak, verbose=False)

    # 3. the declared escape works and makes the flags information-free
    x, names, meta = etl.build_raw(mock_leak, arm="apache-linked",
                                   verbose=False)
    j = _col_of(names, "aps_present")
    k = _col_of(names, "apv_present")
    assert (x[:, j] == 1.0).all() and (x[:, k] == 1.0).all()
    assert meta["arm"] == "apache-linked"
    # strictly fewer stays than the primary cohort: that is the immortal-time
    # cost, paid explicitly instead of taken silently
    assert 0 < meta["n"] < _attrition(pf)["primary-cohort"]
    # and the flags no longer separate the outcome, because they are constant
    om = meta["outcome_missingness"]["aps_present"]
    assert om["n_absent"] == 0 and not om["gate_applies"]


def test_the_leak_probe_fires_on_a_subtle_leak_not_only_on_the_label(
        mock_leak_subcap, mock_small):
    """E-10: the runtime alarm has power against a REALISTIC leak.

    `mock_leak_subcap` plants outcome-correlated missingness at the CELL level:
    the `apacheApsVar` rows survive, so `aps_present` stays 1 everywhere and
    the whole-row prevalence-ratio abort structurally cannot fire. `build_raw`
    succeeds, and the only thing left is the ablation leg of F-D -- the leg the
    old alpha- and coverage-conditioned F-D did not have. The two gates cover
    different halves of the same channel, and this is the half that needs the
    runtime probe.
    """
    def probe(data_dir):
        x_raw, names, meta = etl.build_raw(data_dir, verbose=False)
        idx, _sets = etl.site_split(meta["site_raw"], replicate=0)
        x, _fill = etl.impute(x_raw, idx["train"])
        y_raw, site_raw = etl.labels(meta), list(meta["site_raw"])

        def coh(key):
            sel = idx[key]
            return from_raw(x[sel], [y_raw[i] for i in sel],
                            etl.EICU_POSITIVE_LABEL,
                            [site_raw[i] for i in sel])
        out, _head = run_eicu._leak_probe(coh("train"), coh("cal"), names)
        return out

    clean = probe(mock_small["dir"])
    leaked = probe(mock_leak_subcap)

    assert clean["n_ablated_columns"] == 49
    assert not clean["auc_alarm"] and not clean["ablation_alarm"], clean
    assert clean["ablation_drop"] <= 0.02      # honest: the block adds nothing

    # the leak is real, and it is NOT visible to the AUC ceiling alone
    assert leaked["head_auc_oos"] > clean["head_auc_oos"]
    assert leaked["head_auc_oos"] <= run_eicu.EICU_LEAK_AUC_CEILING
    assert not leaked["auc_alarm"]
    # ... nor to the whole-row prevalence-ratio abort, which is why build_raw
    # let this corpus through at all
    _x, _n, lmeta = etl.build_raw(mock_leak_subcap, verbose=False)
    assert (lmeta["outcome_missingness"]["aps_present"]["prevalence_ratio"]
            <= etl.EICU_MAX_OUTCOME_PREVALENCE_RATIO)
    # ... the ablation leg is what sees it
    assert leaked["ablation_drop"] > run_eicu.EICU_LEAK_ABLATION_MAX_DROP
    assert leaked["ablation_alarm"], leaked


def test_outcome_screen_covers_every_feature_and_names_the_timing_suspects(
        pipeline_small):
    """E-19: "is this column post-hoc?" is answered from DATA, not DDL comments.

    The denylist applies a "timing relative to outcome unverified" standard to
    two `apachePatientResult` columns; nine `apachePredVar` treatment flags
    (`activetx` above all -- active treatment versus comfort measures is decided
    DURING the stay) had no timing verification at all, and nothing in the
    preflight could settle it. `outcome_screen` does.
    """
    ctx = pipeline_small
    screen = etl.outcome_screen(ctx["x_raw"], ctx["meta"], names=ctx["names"])
    assert set(screen["features"]) == set(ctx["names"])
    assert screen["n_features"] == etl.EICU_N_FEATURES
    assert 0.0 < screen["base_prevalence"] < 1.0
    for name, e in screen["features"].items():
        assert e["kind"] in ("binary", "continuous", "degenerate"), name
        assert e["auc"] is None or 0.0 <= e["auc"] <= 1.0

    # every named timing suspect is screened, and on the CLEAN corpus none of
    # them is anywhere near the review band
    for col in run_eicu.EICU_TIMING_UNVERIFIED:
        e = screen["features"][f"apv_{col}"]
        assert e["auc"] is not None, col
        assert abs(e["auc"] - 0.5) <= (etl.EICU_FEATURE_AUC_REVIEW - 0.5), (
            f"apv_{col} univariate AUC {e['auc']} is past the pre-registered "
            f"review band; its measurement TIMING must be re-audited before "
            f"any number is reported (E-19)")
    assert not screen["flagged"]

    # ... and the screen HAS power: an injected outcome column is flagged
    y = ctx["y_bool"].astype(np.float64)
    x2 = np.column_stack([ctx["x_raw"], y])
    screen2 = etl.outcome_screen(x2, ctx["meta"],
                                 names=list(ctx["names"]) + ["__leak__"])
    assert [d["feature"] for d in screen2["flagged"]] == ["__leak__"]


# ========================================================== 6-7. preflight ===

def test_preflight_profiles_without_certifying(mock_small):
    """The mandatory non-certifying pass: it profiles, it writes the a-priori
    predictions, and it builds no features and issues no certificate."""
    pf = etl.preflight(mock_small["dir"], verbose=False)
    assert set(pf) == PREFLIGHT_KEYS
    assert "certified" not in pf and "operative" not in pf

    assert set(pf["tables"]) == set(etl.EICU_TABLES)
    for t, entry in pf["tables"].items():
        assert set(entry) == {"path", "rows", "header", "header_raw",
                              "header_case_as_read", "n_names_with_uppercase",
                              "reference_rows", "rows_match_reference"}
        # E-17: the verdict is DECIDABLE and pinned, not merely "one of three"
        assert entry["header_case_as_read"] == HEADER_CASE_EXPECTED["camel"]
        assert len(entry["header_raw"]) == len(entry["header"])
        assert entry["reference_rows"] == etl.EICU_REFERENCE_ROW_COUNTS[t]
        assert entry["rows_match_reference"] is False    # mock, not the extract

    man = mock_small["manifest"]
    assert pf["patient"]["n_rows"] == pf["tables"]["patient"]["rows"]
    assert pf["patient"]["n_rows"] == man["stays_written"]
    assert pf["patient"]["n_hospitals"] == man["sites"]
    # E-13: identity counts are RAW (S0); cohort counts are named separately
    assert pf["patient"]["n_hospitals_cohort"] <= pf["patient"]["n_hospitals"]
    assert pf["patient"]["n_uniquepid_cohort"] <= pf["patient"]["n_uniquepid"]
    assert set(pf["patient"]["hospitaldischargestatus"]) <= {"Alive",
                                                             "Expired", ""}

    # the ledger is frozen in ORDER, and records n_sites and n_positive as
    # well as n_stays -- E-9: n_stays alone cannot show a prevalence collapse
    assert [e["step"] for e in pf["attrition"]] == list(etl.EICU_ATTRITION_STEPS)
    for e in pf["attrition"]:
        assert set(e) == {"step", "n_stays", "n_sites", "n_positive",
                          "prevalence"}
        assert 0 <= e["n_positive"] <= e["n_stays"]
    att = _attrition(pf)
    assert att["raw-unit-stays"] >= att["outcome-known"] >= att["adult"] \
        >= att["first-stay"] == att["primary-cohort"]

    # The mandated site-informative-missingness diagnostic (T-3): CertGate v2
    # scope-cut covariate-shift mode, so this must be SURFACED per site and
    # never imputed away. Asserted as a superset -- the five mandated fields
    # must be present and well-formed; measuring MORE of what the SPEC wants
    # measured is not a regression.
    assert set(pf["sentinel_site_dispersion"]) >= {"apacheApsVar",
                                                   "apachePredVar"}
    mandated = {"mean_site_minus_one_rate", "sd_site_minus_one_rate",
                "p10", "p50", "p90"}
    for table in ("apacheApsVar", "apachePredVar"):
        per_col = pf["sentinel_site_dispersion"][table]
        assert set(per_col) == set(etl.EICU_APS_NUMERIC if table == "apacheApsVar"
                                   else etl.EICU_APV_NUMERIC)
        for col, stats in per_col.items():
            assert mandated <= set(stats), f"{table}.{col} lost {mandated - set(stats)}"
            for field in mandated:
                assert 0.0 <= float(stats[field]) <= 1.0, (table, col, field)
        # the mock modulates the -1 rate PER SITE (wart W3), so the dispersion
        # this diagnostic exists to expose must be non-zero somewhere
        assert any(s["sd_site_minus_one_rate"] > 0.0 for s in per_col.values())

    # aggregate-only, JSON-serialisable, and it names the pre-registration
    run_eicu.assert_aggregate_only(pf, "preflight")
    round_tripped = json.loads(json.dumps(pf))
    assert set(round_tripped) == PREFLIGHT_KEYS
    preds = json.dumps(pf["predictions"])
    for pid in ("P1", "P2", "P3", "P4", "P5", "P6", "P7"):
        assert pid in preds
    assert isinstance(pf["warnings"], list)


def test_preflight_reference_check_raises_on_the_mock(mock_small):
    """T-6: the wrong download must not silently produce numbers of a different
    dataset. The mock is not the extract, so `expect_reference=True` refuses."""
    with pytest.raises(etl.EicuError, match="reference-row-count-mismatch"):
        etl.preflight(mock_small["dir"], expect_reference=True, verbose=False)


def test_missing_table_and_missing_column_are_loud(tmp_path):
    empty = str(tmp_path / "empty")
    os.makedirs(empty, exist_ok=True)
    with pytest.raises(etl.EicuError, match="missing-table"):
        list(etl.read_table(empty, "patient"))
    with pytest.raises(etl.EicuError, match="missing-column"):
        etl.require_columns(["patientunitstayid", "age"], "patient",
                            ["patientunitstayid", "hospitaldischargestatus"])


# ================================================ 8-13. the planted traps ====

def test_minus_one_sentinel_never_reaches_the_matrix(planted):
    """T-2. `-1` is the UNDOCUMENTED APACHE sentinel: it is a plausible finite
    number, so it passes every downstream gate and silently poisons the head.
    The all-`-1` stay must arrive as ALL-missing, and no `-1` may survive."""
    x_raw, names, meta = etl.build_raw(planted, verbose=False)
    r1, r2 = _row_of(meta, 1), _row_of(meta, 2)
    aps_cols = [i for i, n in enumerate(names)
                if n.startswith("aps_") and not n.endswith("__missing")
                and n != "aps_present"]
    apv_cols = [i for i, n in enumerate(names)
                if n.startswith("apv_") and not n.endswith("__missing")
                and n != "apv_present"]
    assert len(aps_cols) == 24 and len(apv_cols) == 19

    for col in aps_cols + apv_cols:
        assert np.isnan(x_raw[r2, col]), names[col]
        assert x_raw[r2, _col_of(names, names[col] + "__missing")] == 1.0
        assert np.isfinite(x_raw[r1, col]), names[col]
        assert x_raw[r1, _col_of(names, names[col] + "__missing")] == 0.0

    # presence is ROW presence, not VALUE presence: the all-(-1) stay carried a
    # row, so the flag stays 1.0 while all 43 siblings flip together
    assert x_raw[r2, _col_of(names, "aps_present")] == 1.0
    assert x_raw[r2, _col_of(names, "apv_present")] == 1.0

    x, fill = etl.impute(x_raw, np.array([r1], dtype=int))
    hr = _col_of(names, "aps_heartrate")
    assert x[r2, hr] == x[r1, hr] == 88.0          # imputed from S_train only
    assert not (x[:, aps_cols + apv_cols] == -1.0).any()
    assert np.isfinite(x).all()
    assert np.isnan(x_raw[r2, hr]), "impute must not mutate x_raw"

    # a column entirely NaN within fit_idx falls back, counted
    x_fb, fill_fb = etl.impute(x_raw, np.array([r2], dtype=int))
    assert x_fb[r2, hr] == etl.EICU_IMPUTE_FALLBACK == 0.0
    assert fill_fb["aps_heartrate"] == etl.EICU_IMPUTE_FALLBACK
    assert _int_leaf_sum(meta["sentinel_counts"]) > 0
    assert fill != fill_fb


def test_empty_string_is_a_second_missing_channel(planted):
    """The documented SQL NULL (the MIT-LCP loader is `NULL ''`) and the
    undocumented `-1` are INDEPENDENT channels; handling only one leaves the
    other in the matrix."""
    x_raw, names, meta = etl.build_raw(planted, verbose=False)
    r2, r3 = _row_of(meta, 2), _row_of(meta, 3)
    block = [i for i, n in enumerate(names)
             if (n.startswith("aps_") or n.startswith("apv_"))
             and not n.endswith("__missing")
             and n not in ("aps_present", "apv_present")]
    assert np.isnan(x_raw[r3, block]).all()
    assert (x_raw[r3, [_col_of(names, names[i] + "__missing") for i in block]]
            == 1.0).all()
    # identical treatment to the -1 channel
    assert np.array_equal(x_raw[r2, block], x_raw[r3, block], equal_nan=True)
    assert x_raw[r3, _col_of(names, "aps_present")] == 1.0


def test_absent_apache_row_clears_the_presence_flag(planted):
    """T-3: whole-row APACHE absence is site-correlated. It is named by one
    explicit column rather than smeared across 43 `__missing` siblings, so the
    abstention explanations can point at it (prediction P4)."""
    x_raw, names, meta = etl.build_raw(planted, verbose=False)
    r4 = _row_of(meta, 4)
    assert x_raw[r4, _col_of(names, "aps_present")] == 0.0
    assert x_raw[r4, _col_of(names, "apv_present")] == 0.0
    assert np.isnan(x_raw[r4, _col_of(names, "aps_heartrate")])
    assert x_raw[r4, _col_of(names, "aps_heartrate__missing")] == 1.0
    assert not np.asarray(meta["aps_present"])[r4]
    assert not np.asarray(meta["apv_present"])[r4]
    assert np.asarray(meta["aps_present"]).dtype == bool


def test_unexpected_negative_sentinel_aborts(tmp_path):
    """T-2's other half. Every allowlisted column has non-negative
    physiological support, so negative mass that is NOT exactly `-1.0` is an
    UNRECOGNISED sentinel: it must abort, not flow, and not be absorbed by the
    `value < 0 => missing` rule the histogram has not yet justified."""
    dst = _write_corpus(str(tmp_path / "negsentinel"), {
        "patient": [_patient(1), _patient(2)],
        "hospital": [_hospital(1)],
        "apacheApsVar": [_aps(1, 11), _aps(2, 12, wbc="-7")],
        "apachePredVar": [_apv(1, 21), _apv(2, 22)],
        "apachePatientResult": [],
    })
    with pytest.raises(etl.EicuError, match="unexpected-negative-sentinel"):
        etl.build_raw(dst, verbose=False)


def test_age_over_89_is_kept_and_flagged(tmp_path):
    """The HIPAA ceiling token. Dropping `'> 89'` (the common benchmark's
    `max_age=89`) removes a mortality-enriched stratum whose SHARE VARIES BY
    HOSPITAL -- a site-correlated exclusion. It is kept at 90.0 with an
    explicit indicator so the ceiling is visible to the head and to Shapley."""
    dst = _write_corpus(str(tmp_path / "age"), {
        "patient": [_patient(1, age=etl.EICU_AGE_MASK_TOKEN), _patient(2, age="45"),
                    _patient(3, age=""), _patient(4, age="17"),
                    _patient(5, age="not-a-number")],
        "hospital": [_hospital(1)],
        "apacheApsVar": [], "apachePredVar": [], "apachePatientResult": [],
    })
    x_raw, names, meta = etl.build_raw(dst, verbose=False)
    assert meta["n"] == 2                          # blank, under-18 and junk drop
    assert sorted(int(s) for s in meta["stay_id"]) == [1, 2]

    r1, r2 = _row_of(meta, 1), _row_of(meta, 2)
    assert x_raw[r1, _col_of(names, "age")] == etl.EICU_AGE_MASK_VALUE == 90.0
    assert x_raw[r1, _col_of(names, "age_masked")] == 1.0
    assert x_raw[r1, _col_of(names, "age__missing")] == 0.0
    assert x_raw[r2, _col_of(names, "age")] == 45.0
    assert x_raw[r2, _col_of(names, "age_masked")] == 0.0

    att = _attrition(meta)
    assert [e["step"] for e in meta["attrition"]] == list(etl.EICU_ATTRITION_STEPS)
    assert att["raw-unit-stays"] == 5
    assert att["outcome-known"] == 5
    assert att["adult"] == 2
    assert att["primary-cohort"] == 2


def test_blank_discharge_status_is_dropped_never_imputed(tmp_path):
    """~0.87% of stays have NO usable outcome. MIT-LCP's own `icustay_detail`
    uses `ELSE NULL`; a coerced blank would fabricate ~1750 survivors."""
    dst = _write_corpus(str(tmp_path / "status"), {
        "patient": [_patient(1, hospitaldischargestatus="Alive"),
                    _patient(2, hospitaldischargestatus="Expired"),
                    _patient(3, hospitaldischargestatus="")],
        "hospital": [_hospital(1)],
        "apacheApsVar": [], "apachePredVar": [], "apachePatientResult": [],
    })
    _, _, meta = etl.build_raw(dst, verbose=False)
    assert meta["n"] == 2
    assert sorted(etl.labels(meta)) == [etl.EICU_NEGATIVE_LABEL,
                                        etl.EICU_POSITIVE_LABEL]
    att = _attrition(meta)
    assert att["raw-unit-stays"] == 3 and att["outcome-known"] == 2
    assert _int_leaf_sum(meta["drop_counts"]) >= 1


def test_a_third_outcome_level_raises(tmp_path):
    """A value outside {'Alive','Expired',''} is a schema surprise, not a
    survivor: it must raise rather than be silently coerced to negative."""
    dst = _write_corpus(str(tmp_path / "badstatus"), {
        "patient": [_patient(1), _patient(2, hospitaldischargestatus="Transferred")],
        "hospital": [_hospital(1)],
        "apacheApsVar": [], "apachePredVar": [], "apachePatientResult": [],
    })
    with pytest.raises(etl.EicuError, match="unknown-outcome-level"):
        etl.build_raw(dst, verbose=False)


def test_first_stay_rule_picks_the_highest_hospitaladmitoffset(tmp_path):
    """S4's sign trap: `hospitaladmitoffset` is NEGATIVE minutes, so the
    EARLIEST stay has the HIGHEST (least negative) offset. `min` here silently
    selects the LAST ICU stay of an admission -- a post-hoc selection."""
    dst = _write_corpus(str(tmp_path / "firststay"), {
        "patient": [
            # tie on unitvisitnumber -> max offset wins (-14 beats -22)
            _patient(1001, patienthealthsystemstayid=100, unitvisitnumber=1,
                     hospitaladmitoffset=-14),
            _patient(1002, patienthealthsystemstayid=100, unitvisitnumber=1,
                     hospitaladmitoffset=-22),
            # unitvisitnumber is the PRIMARY key: 1 beats 2 despite the offset
            _patient(2001, patienthealthsystemstayid=200, unitvisitnumber=2,
                     hospitaladmitoffset=-10),
            _patient(2002, patienthealthsystemstayid=200, unitvisitnumber=1,
                     hospitaladmitoffset=-500),
            # exact tie -> min patientunitstayid, for determinism
            _patient(3001, patienthealthsystemstayid=300, unitvisitnumber=1,
                     hospitaladmitoffset=-30),
            _patient(3002, patienthealthsystemstayid=300, unitvisitnumber=1,
                     hospitaladmitoffset=-30),
        ],
        "hospital": [_hospital(1)],
        "apacheApsVar": [], "apachePredVar": [], "apachePatientResult": [],
    })
    x_raw, names, meta = etl.build_raw(dst, verbose=False)
    assert sorted(int(s) for s in meta["stay_id"]) == [1001, 2002, 3001]
    att = _attrition(meta)
    assert att["adult"] == 6 and att["first-stay"] == 3
    # the offset survives ONLY as a windowed pre-ICU duration, sign corrected
    assert x_raw[_row_of(meta, 1001), _col_of(names, "pre_icu_hours")] == \
        pytest.approx(14.0 / 60.0)
    assert len(set(int(a) for a in np.asarray(meta["admission_id"]))) == 3


def test_apache_result_dedup_is_version_preferred_and_counted(planted_dedup):
    """T-8/T-9. `apachePatientResult` carries one row per apacheVersion (297,064
    rows over 171,177 stays, which is not 2x), and
    `predictedhospitalmortality` is a VARCHAR holding a probability: compared
    as a string, `'-1' > '0'`. `float()` first, always."""
    _, _, meta = etl.build_raw(planted_dedup, verbose=False)
    pred = np.asarray(meta["comparator_predicted_mortality"], dtype=np.float64)
    ver = list(meta["comparator_apache_version"])

    assert pred[_row_of(meta, 1)] == pytest.approx(0.22)   # IVa beats IV
    assert ver[_row_of(meta, 1)] == "IVa"
    assert pred[_row_of(meta, 2)] == pytest.approx(0.33)   # IV only
    assert ver[_row_of(meta, 2)] == "IV"
    assert pred[_row_of(meta, 3)] == pytest.approx(0.55)   # min surrogate id
    assert np.isnan(pred[_row_of(meta, 4)])                # the '-1' STRING
    assert np.isnan(pred[_row_of(meta, 5)])                # no row at all
    assert not (pred == -1.0).any()
    assert etl.EICU_APACHE_VERSION_PREFERENCE == ("IVa", "IV")
    assert _int_leaf_sum(meta["dedup_counts"]) >= 1         # reported, not silent


def test_duplicate_apache_rows_keep_the_minimum_surrogate_id(planted_dedup):
    """`apacheApsVar` does not declare `patientunitstayid` unique. The tie-break
    is explicit and the count is REPORTED -- never a silent drop."""
    x_raw, names, meta = etl.build_raw(planted_dedup, verbose=False)
    assert x_raw[_row_of(meta, 1), _col_of(names, "aps_heartrate")] == 88.0
    assert _int_leaf_sum(meta["dedup_counts"]) > 0


def test_categorical_level_drift_raises(mock_drift, pipeline_small):
    """T-7. A level tuple frozen without seeing the data can be wrong. Unlisted
    values fall to OTHER and are COUNTED; past the 5% cap the run stops, and
    the fix is a visible SPEC + constants diff, not a drift bucket the head
    quietly learns."""
    with pytest.raises(etl.EicuError, match="categorical-level-drift"):
        etl.build_raw(mock_drift, strict_levels=True, verbose=False)
    _, _, meta = etl.build_raw(mock_drift, strict_levels=False, verbose=False)
    shares = meta["categorical_other_shares"]
    assert max(shares.values()) > etl.EICU_MAX_OTHER_SHARE == 0.05

    # the canonical corpus exercises the OTHER bucket WITHOUT tripping the gate
    # (wart W16), so the cap is tested from both sides
    ok = pipeline_small["meta"]["categorical_other_shares"]
    assert set(ok) == set(shares)
    assert all(0.0 <= s <= etl.EICU_MAX_OTHER_SHARE for s in ok.values())
    assert _int_leaf_sum(pipeline_small["meta"]["categorical_other_counts"]) > 0


# ================================================= 14-17. splits and labels ===

def test_site_split_is_by_site_disjoint_and_deterministic(pipeline_small):
    sets, idx = pipeline_small["sets"], pipeline_small["idx"]
    site_raw = pipeline_small["site_raw"]
    assert set(sets) == {"train", "aux", "cal", "target"}
    keys = ("train", "aux", "cal", "target")
    for i, a in enumerate(keys):                   # PAIRWISE, not a triple
        for b in keys[i + 1:]:
            assert not (sets[a] & sets[b]), f"{a} and {b} share sites"
    uniq = set(site_raw)
    assert set().union(*sets.values()) == uniq
    assert len(sets["target"]) == etl.EICU_N_TARGET_SITES == 24

    # records inherit their hospital's assignment; none crosses a boundary
    for key in keys:
        assert {site_raw[i] for i in idx[key]} <= sets[key]
    assert sum(len(idx[k]) for k in keys) == len(site_raw)
    assert np.asarray(idx["train"]).dtype.kind == "i"

    again, again_sets = etl.site_split(site_raw, replicate=0)
    assert again_sets == sets
    for key in keys:
        assert np.array_equal(again[key], idx[key])
    _, other = etl.site_split(site_raw, replicate=1)
    assert other != sets                           # an INDEPENDENT re-split


def test_site_split_refuses_a_population_it_cannot_calibrate():
    few = [f"{etl.EICU_SITE_PREFIX}{i}" for i in range(etl.EICU_MIN_TOTAL_SITES - 1)]
    with pytest.raises(etl.EicuError, match="too-few-sites"):
        etl.site_split(few, replicate=0)
    assert etl.EICU_MIN_TOTAL_SITES == 149


def test_split_leaves_at_least_min_cal_clusters(pipeline_small):
    """The site arithmetic, worked: 180 mock hospitals - 24 held out = 156;
    40/20/40 gives 62/31/63, and EICU_MOCK_MIN_STAYS_PER_SITE = 12 makes all 63
    RECORD-CARRYING, so the MIN_CAL_CLUSTERS = 50 gate is deterministically
    satisfied and certification is reachable."""
    sets, cal = pipeline_small["sets"], pipeline_small["cal"]
    uniq = len(set(pipeline_small["site_raw"]))
    assert uniq == mock.EICU_MOCK_SMALL_SITES == 180
    rest = uniq - etl.EICU_N_TARGET_SITES
    n_tr = int(rest * SPLIT_FRACTIONS[0])
    n_aux = int(rest * SPLIT_FRACTIONS[1])
    assert (len(sets["train"]), len(sets["aux"])) == (n_tr, n_aux) == (62, 31)
    assert len(sets["cal"]) == rest - n_tr - n_aux == 63
    assert int((cal.site_sizes > 0).sum()) >= MIN_CAL_CLUSTERS
    assert pipeline_small["rep"]["diagnostic"]["n_cal_carrying"] >= \
        MIN_CAL_CLUSTERS


def test_impute_means_come_from_train_only(pipeline_small):
    """The transductive leak no downstream gate catches: pooled-matrix means
    would carry the TARGET pool's covariate distribution into the training
    features. Perturbing the target pool must leave the fills untouched."""
    x_raw, idx, fill = (pipeline_small["x_raw"], pipeline_small["idx"],
                        pipeline_small["fill"])
    perturbed = x_raw.copy()
    tgt = idx["target"]
    block = perturbed[tgt]
    perturbed[tgt] = np.where(np.isnan(block), np.nan, block + 1000.0)
    x_p, fill2 = etl.impute(perturbed, idx["train"])
    assert fill2 == fill
    # asserted on the MATRIX too, so the check does not rest on the internal
    # shape of the fill record: the fitting rows come out identical
    assert np.array_equal(x_p[idx["train"]], pipeline_small["x"][idx["train"]])

    # and moving the fit set DOES move the imputed values -- the test has teeth
    x_c, _ = etl.impute(x_raw, idx["cal"])
    assert not np.array_equal(x_c, pipeline_small["x"])
    with pytest.raises(etl.EicuError, match="impute-fit-empty"):
        etl.impute(x_raw, np.array([], dtype=int))


def test_labels_flow_through_coerce_labels_not_a_bool_array(pipeline_small):
    """`coerce_labels` owns the two-value contract; the ETL never hand-builds a
    bool array. `require_both_classes=False` is the TARGET-pool-only opt-in."""
    y_raw = pipeline_small["y_raw"]
    assert isinstance(y_raw, list)
    assert all(isinstance(v, str) for v in y_raw)
    assert set(y_raw) <= {etl.EICU_POSITIVE_LABEL, etl.EICU_NEGATIVE_LABEL}
    assert etl.EICU_POSITIVE_LABEL == "Expired"
    assert etl.EICU_LABEL_COLUMN == "hospitaldischargestatus"
    assert etl.EICU_POSITIVE_LABEL in set(y_raw)

    target = pipeline_small["target"]
    assert target.y.dtype == bool
    assert target.x.dtype == np.float64


def test_hospitalid_survives_densify_sites_without_collision(pipeline_small):
    """Site identity is emitted as ONE canonical spelling per hospital
    (`hosp-{int(hospitalid)}`), so `densify_sites`' cosmetic-collision raise --
    which exists because a hospital split into two 'independent' clusters buys
    certification strength the honest clustering refuses -- cannot fire on our
    own output. `hospitalid`/`wardid` never enter x."""
    site_raw = pipeline_small["site_raw"]
    dense, labels = densify_sites(site_raw)        # must not raise
    assert len(labels) == len(set(site_raw)) == 180
    assert all(s.startswith(etl.EICU_SITE_PREFIX) for s in labels)
    assert all(s[len(etl.EICU_SITE_PREFIX):].lstrip("-").isdigit()
               for s in labels)
    assert len({normalized_label(s) for s in labels}) == len(labels)
    assert int(dense.max()) == len(labels) - 1
    # the pooled label cannot collide with any hospital label
    assert normalized_label(etl.EICU_POOLED_TARGET_LABEL) not in \
        {normalized_label(s) for s in labels}


def test_etl_output_is_deterministic_and_build_matrix_agrees(
        mock_small, pipeline_small):
    """Identical inputs -> byte-identical features. `build_matrix` is a
    convenience wrapper over build_raw -> site_split -> impute and must not
    diverge from the explicit path the runner uses."""
    x1, n1, m1 = etl.build_matrix(mock_small["dir"], verbose=False)
    x2, n2, m2 = etl.build_matrix(mock_small["dir"], verbose=False)
    assert np.array_equal(x1, x2)
    assert n1 == n2 == etl.feature_names()
    assert list(m1["site_raw"]) == list(m2["site_raw"])
    assert m1["impute_fill"] == m2["impute_fill"]
    assert np.array_equal(np.asarray(m1["stay_id"]), np.asarray(m2["stay_id"]))
    assert set(m1["split_sites"]) == {"train", "aux", "cal", "target"}

    assert np.array_equal(x1, pipeline_small["x"])
    assert m1["impute_fill"] == pipeline_small["fill"]
    assert list(m1["site_raw"]) == pipeline_small["site_raw"]


# ============================================ 18-21. the certification path ===

def test_smoke_end_to_end_reaches_an_honest_outcome(pipeline_small):
    """The whole path on the pooled 24-hospital target arm, plus one
    per-hospital (K == 1) pool. Certification is NEVER asserted; the assertion
    is that whatever is issued survives the oracle."""
    rep, ctx = pipeline_small["rep"], pipeline_small
    outcome = _assert_honest(rep, ctx)
    assert outcome in ("certified", "declined")
    assert rep["reason"] is None                   # the pooled arm is not gated
    assert [r["alpha"] for r in rep["certified"]] == list(ALPHA_LADDER)
    assert all(r["status"] in ("certified", "declined") for r in rep["certified"])

    # target identity is validated and bound, K = 24 >= BBSE_MIN_TARGET_SITES
    assert "target_site_id" in rep["provenance"]["input_hashes"]
    assert "target_site_labels" in rep["provenance"]["input_hashes"]
    assert rep["diagnostic"]["target_site_id_supplied"] is True
    assert len(set(ctx["tgt_sites"])) == etl.EICU_N_TARGET_SITES
    assert ctx["target"].x.dtype == np.float64
    assert np.isfinite(ctx["target"].x).all()

    # ---- per-hospital arm: target_site_id SUPPLIED even though K == 1 ----
    site, _n = Counter(ctx["tgt_sites"]).most_common(1)[0]
    rows = np.array([i for i in ctx["idx"]["target"]
                     if ctx["site_raw"][i] == site], dtype=int)
    rep1 = run_certgate(ctx["train"], ctx["aux"], ctx["cal"], ctx["x"][rows],
                        target_label=site,
                        target_site_id=[ctx["site_raw"][i] for i in rows],
                        oracle_target_y=ctx["y_bool"][rows])
    assert rep1["reason"] in (None, "pool-too-small")
    assert sum(rep1["decline_partition"].values()) == len(rows)
    assert rep1["diagnostic"]["target_site_id_supplied"] is True
    assert "[partition]" in render_text(rep1)
    if rep1["operative"] is not None:
        head = fit_head(ctx["train"])
        err = head.predict(ctx["x"][rows]) != ctx["y_bool"][rows]
        assert not hard_violation(err[rep1["answered_mask"]],
                                  rep1["operative"]["alpha"])


def test_the_honesty_assertion_fires_on_a_bad_certificate(pipeline_small):
    """The honesty check must not be dead code.

    At the mock's frozen signal strength both arms currently DECLINE (a
    legitimate outcome the contract explicitly refuses to assert against), so
    the certified branch of `_assert_honest` -- the oracle `hard_violation`
    gate, the assertion this whole file exists to make -- would otherwise never
    execute. Here it is driven both ways against the real head and the real
    held-out pool: a certificate that answers exactly the records the head gets
    WRONG must be rejected, and one that answers only correct records accepted.
    """
    ctx = pipeline_small
    head = fit_head(ctx["train"])
    err = head.predict(ctx["target"].x) != ctx["target"].y
    n = ctx["target"].n
    assert int(err.sum()) >= 10, "need a non-trivial error set to violate with"

    def _rep(answered):
        k = int(answered.sum())
        return dict(
            target_label="synthetic-probe", reason=None, certified=[],
            operative=dict(alpha=0.10, tau=0.9, tau_idx=0,
                           deploy_mode="baseline", modes=["baseline"]),
            estimated=None,
            diagnostic=dict(coverage=k / n, n_cal_carrying=63),
            decline_partition={"answered": k, "below_tau": n - k, "failsafe": 0,
                               "pool-too-small": 0, "insufficient-clusters": 0},
            answered_mask=answered, provenance={})

    with pytest.raises(AssertionError):
        _assert_honest(_rep(err), ctx)               # answers only its mistakes
    assert _assert_honest(_rep(~err), ctx) == "certified"


def test_run_eicu_refuses_record_level_output():
    """T-17. PhysioNet's DUA restricts derived record-level artifacts and
    `experiments/out/` is a TRACKED directory, so every write goes through the
    refusal -- including the arrays a naive `json.dump` of a report would emit."""
    for payload in (
        {"stay_id": [1, 2, 3]},
        {"summary": {"per_site": {"site_raw": ["hosp-1"]}}},
        {"answered_mask": [True, False]},
        {"comparator_predicted_mortality": [0.1]},
        {"split_idx": {"train": [0]}},
        {"rows": list(range(run_eicu.EICU_MAX_OUTPUT_LEN + 1))},
        {"rows": np.zeros(run_eicu.EICU_MAX_OUTPUT_LEN + 1)},
    ):
        with pytest.raises(etl.EicuError, match="record-level-output"):
            run_eicu.assert_aggregate_only(payload, "test")

    assert run_eicu.EICU_MAX_OUTPUT_LEN == 512     # > 208 sites, < any record array
    # an aggregate payload of the shape the runner actually writes passes
    run_eicu.assert_aggregate_only(
        {"alpha": 0.1, "coverage": 0.72, "per_site": [{"site": "hosp-1",
                                                       "n_answered": 40}],
         "attrition": [{"step": s, "n_stays": 1, "n_sites": 1}
                       for s in etl.EICU_ATTRITION_STEPS]}, "test")


def test_rm_helpers_are_the_synthetic_ones():
    """The real-data numbers must be computed by the SAME functions as the
    paper's synthetic ones; a re-implementation would let them drift silently."""
    assert run_eicu._rm_on_pool is run_synthetic._rm_on_pool
    assert run_eicu._per_site_exceed_frac is run_synthetic._per_site_exceed_frac
    assert run_eicu._rate is run_synthetic._rate
    assert run_eicu._write_csv is run_synthetic._write_csv


def test_etl_imports_no_undeclared_dependency():
    """Audit F16. `pandas` and `pyarrow` are installed in this environment and
    are NOT in requirements.txt; `eicu_etl` is stdlib + numpy only and
    `eicu_mock` is stdlib only. Imports are also checked to be at MODULE TOP
    LEVEL (the enclave/reproducibility requirement)."""
    allowed = {
        "experiments.eicu_etl": {"numpy", "certgate"},
        "experiments.eicu_mock": set(),
    }
    for modname, extra in allowed.items():
        mod = etl if modname.endswith("eicu_etl") else mock
        src = pathlib.Path(mod.__file__).read_text(encoding="utf-8")
        tree = ast.parse(src)
        roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                roots.add((node.module or "").split(".")[0])
        assert "pandas" not in roots, f"{modname} imports pandas (audit F16)"
        assert "pyarrow" not in roots, f"{modname} imports pyarrow (audit F16)"
        third_party = roots - _STDLIB_OK
        assert third_party <= extra, \
            f"{modname} imports undeclared {sorted(third_party - extra)}"

    for mod in (etl, mock, run_eicu):
        tree = ast.parse(pathlib.Path(mod.__file__).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef)):
                for child in ast.walk(node):
                    assert not isinstance(child, (ast.Import, ast.ImportFrom)), \
                        (f"{mod.__name__}.{node.name} imports inside a "
                         f"function/class; all third-party imports must be at "
                         f"module top level")


# ============================ 2026-07-31 ingest-audit boundary regressions ===

def test_duplicate_patientunitstayid_raises(tmp_path):
    """E-11: `patientunitstayid` is the PRIMARY KEY of `patient`.

    Before the fix a duplicate collapsed SILENTLY and INCONSISTENTLY: scan A's
    `stay_meta[stay_id] = ...` kept the LAST row's label and hospital while
    scan B's `if stay_id in row_of: continue` kept the FIRST row's features, so
    a record carried one patient's covariates under another row's outcome --
    and the collapse was mis-accounted as a first-stay drop. `dedup_counts` was
    empty, because `patient` has no dedup path.
    """
    d = _write_corpus(str(tmp_path / "dup"), {
        "patient": [_patient(1, age=30, hospitaldischargestatus="Alive"),
                    _patient(1, age=80, hospitaldischargestatus="Expired"),
                    _patient(2, age=60)],
        "hospital": [_hospital(1)]})
    with pytest.raises(etl.EicuError, match="duplicate-stay-id"):
        etl.build_raw(d, verbose=False)
    with pytest.raises(etl.EicuError, match="duplicate-stay-id"):
        etl._select_cohort(d)

    # the site variant is equally fatal and equally invisible to
    # assert_site_disjoint / site_split, which compare LABELS only
    d2 = _write_corpus(str(tmp_path / "dup_site"), {
        "patient": [_patient(1, hospitalid=1, age=30),
                    _patient(1, hospitalid=2, age=80),
                    _patient(2, hospitalid=1)],
        "hospital": [_hospital(1), _hospital(2)]})
    with pytest.raises(etl.EicuError, match="duplicate-stay-id"):
        etl.build_raw(d2, verbose=False)


def test_a_null_token_that_is_not_empty_string_raises(tmp_path):
    """E-15: the opposite direction of the `-1` gate, which had no guard.

    A Postgres text-format re-export writes `\\N` for NULL. Every allowlisted
    APACHE numeric then parses as `unparseable`, all 43 parents become 100%
    NaN, all 43 `__missing` siblings become the constant 1.0,
    `model.SD_REL_TOL` zeroes 86 of 161 coefficients -- and before the fix
    `build_raw` SUCCEEDED, with an empty `warnings` list, so a certificate was
    issued about a model that had seen no physiology at all.
    """
    rows = {"patient": [], "hospital": [_hospital(1)],
            "apacheApsVar": [], "apachePredVar": []}
    for i in range(1, 61):
        rows["patient"].append(_patient(
            i, hospitaldischargestatus="Expired" if i % 7 == 0 else "Alive"))
        rows["apacheApsVar"].append(_aps(i, i, fill="\\N"))
        rows["apachePredVar"].append(_apv(i, i, fill="\\N"))
    d = _write_corpus(str(tmp_path / "nulltoken"), rows)

    with pytest.raises(etl.EicuError, match="unrecognised-null-token") as ei:
        etl.build_raw(d, verbose=False)
    assert "\\\\N" in str(ei.value) or "\\N" in str(ei.value), (
        "the message must NAME the offending token, not just count it -- a "
        "count cannot tell the operator their NULL token is wrong")

    # preflight reports it rather than raising, and names the raise to come
    pf = etl.preflight(d, verbose=False)
    assert pf["unparseable_tokens"]["over_cap"]
    assert any("E-15" in w for w in pf["warnings"])
    assert any("unrecognised-null-token" in c
               for c in pf["reference_check"]["invalid_conditions"])


def test_null_token_in_patient_numeric_aborts(tmp_path):
    """E-22: the E-15 gate covers the PATIENT numerics, not only aps_/apv_.

    Before the fix `\\N` in `admissionweight` flowed silently: the column went
    constant at the imputation fallback with `sentinel_counts` recording 100%
    unparseable and the warnings list unchanged -- and the same token in
    `hospitaladmitoffset` (the SS4 first-stay tie-breaker) silently changed
    WHICH stays entered the cohort, with no trace in the attrition ledger
    (2026-07-31 arrival-day audit).
    """
    rows = {"patient": [], "hospital": [_hospital(1)],
            "apacheApsVar": [], "apachePredVar": [],
            "apachePatientResult": []}
    for i in range(1, 61):
        rows["patient"].append(_patient(
            i, admissionweight="\\N",
            hospitaldischargestatus="Expired" if i % 7 == 0 else "Alive"))
    d = _write_corpus(str(tmp_path / "patientnull"), rows)

    with pytest.raises(etl.EicuError, match="unrecognised-null-token") as ei:
        etl.build_raw(d, verbose=False)
    assert "admissionweight" in str(ei.value)
    assert "\\\\N" in str(ei.value) or "\\N" in str(ei.value)

    pf = etl.preflight(d, verbose=False)
    assert "patient.admissionweight" in pf["unparseable_tokens"]["over_cap"]
    assert any("unrecognised-null-token" in c
               for c in pf["reference_check"]["invalid_conditions"])


def test_float_join_keys_abort_not_unlink(tmp_path):
    """E-21 leg 1: a join-key FORMAT artifact raises, never silently unlinks.

    A pandas int64 -> float64 `to_csv` round-trip writes `patientunitstayid`
    as '141258.0' (scientific notation is the same trap). `_maybe_int` returns
    None, the row is skipped UNREAD, and before the fix every aps_* column
    collapsed to the imputation fallback with zero warnings, the E-15 gate
    blind (no cell was ever read) and the E-9 gate `gate_applies=false` -- the
    exact end state `unrecognised-null-token`'s own message warns about,
    reached through a door with no gate on it (2026-07-31 arrival-day audit).
    """
    rows = {"patient": [_patient(i) for i in range(1, 5)],
            "hospital": [_hospital(1)],
            "apacheApsVar": [_aps(i, i) for i in range(1, 5)],
            "apachePredVar": [_apv(i, i) for i in range(1, 5)],
            "apachePatientResult": []}
    for r in rows["apacheApsVar"]:
        r["patientunitstayid"] += ".0"
    d = _write_corpus(str(tmp_path / "floatkeys"), rows)

    with pytest.raises(etl.EicuError, match="unparseable-join-key") as ei:
        etl.build_raw(d, verbose=False)
    assert "apacheApsVar" in str(ei.value), "the message must name the table"
    assert "1.0" in str(ei.value), "the message must name the offending token"

    pf = etl.preflight(d, verbose=False)
    assert any("unparseable-join-key" in c
               for c in pf["reference_check"]["invalid_conditions"])


def test_apache_coverage_collapse_on_broken_join(tmp_path):
    """E-21 leg 2: an UNLINKED APACHE block aborts once the cohort can carry E-9.

    Keys shifted so nothing joins while every ROW COUNT stays intact -- the
    route `EICU_REFERENCE_ROW_COUNTS` cannot see by construction. Before the
    fix this certified with 89/161 constant columns and a warnings list
    SHORTER than the clean corpus's. The same corpus with the keys pointing
    home must build: the gate is keyed on the JOIN, not the scale.
    """
    n = etl.EICU_MIN_OUTCOME_STRATUM + 20
    stays = range(1, n + 1)
    rows = {"patient": [_patient(
                i, hospitaldischargestatus="Expired" if i % 7 == 0 else "Alive")
                for i in stays],
            "hospital": [_hospital(1)],
            "apacheApsVar": [_aps(9000000 + i, i) for i in stays],
            "apachePredVar": [_apv(9000000 + i, i) for i in stays],
            "apachePatientResult": []}
    d = _write_corpus(str(tmp_path / "brokenjoin"), rows)

    with pytest.raises(etl.EicuError, match="apache-coverage-collapse") as ei:
        etl.build_raw(d, verbose=False)
    assert "aps_present" in str(ei.value)

    pf = etl.preflight(d, verbose=False)
    assert any("apache-coverage-collapse" in c
               for c in pf["reference_check"]["invalid_conditions"])

    # negative control: identical scale, keys pointing home -> builds
    rows["apacheApsVar"] = [_aps(i, i) for i in stays]
    rows["apachePredVar"] = [_apv(i, i) for i in stays]
    d2 = _write_corpus(str(tmp_path / "linkedjoin"), rows)
    x_raw, _names, meta = etl.build_raw(d2, verbose=False)
    assert x_raw.shape[0] == n


def test_apache_coverage_collapse_on_header_only_table(tmp_path):
    """E-21 leg 2, second route: a header-only child table aborts at scale.

    The tiny single-trap corpora above (`planted`, the age/status corpora)
    legitimately ship empty APACHE tables and MUST keep building -- the gate
    arms only at n_cohort >= EICU_MIN_OUTCOME_STRATUM, the exact scale at
    which E-9 is supposed to be evaluable and total absence would otherwise
    bypass it.
    """
    n = etl.EICU_MIN_OUTCOME_STRATUM + 20
    rows = {"patient": [_patient(
                i, hospitaldischargestatus="Expired" if i % 7 == 0 else "Alive")
                for i in range(1, n + 1)],
            "hospital": [_hospital(1)],
            "apacheApsVar": [], "apachePredVar": [],
            "apachePatientResult": []}
    d = _write_corpus(str(tmp_path / "headeronly"), rows)

    with pytest.raises(etl.EicuError, match="apache-coverage-collapse"):
        etl.build_raw(d, verbose=False)

    # the apache-linked escape is NOT the remedy here: with zero linked stays
    # that arm has an empty cohort, and the honest failure is empty-cohort
    with pytest.raises(etl.EicuError, match="empty-cohort"):
        etl.build_raw(d, arm="apache-linked", verbose=False)


def test_read_boundary_failures_are_typed_and_name_the_table(tmp_path,
                                                             mock_small):
    """E-14: every boundary rejection is a TYPED error with a reason tag.

    A non-UTF-8 byte used to escape as a bare `UnicodeDecodeError` whose
    "position N" is a decode-BUFFER offset, and a partial unzip of the
    multi-GB download as a bare `EOFError`. Neither names the table or the
    path, so on a five-table extract the operator cannot tell which file
    failed.
    """
    # 1. undecodable: one latin-1 byte inside a text field
    bad = str(tmp_path / "undecodable")
    os.makedirs(bad, exist_ok=True)
    for table in mock.EICU_MOCK_TABLES:
        src = etl._resolve_table_path(mock_small["dir"], table)
        dst = os.path.join(bad, f"{table}.csv.gz")
        if table != "patient":
            shutil.copyfile(src, dst)
            continue
        with gzip.open(src, "rb") as f:
            raw = f.read()
        marker = b"Sepsis"
        raw = (raw.replace(marker, b"Sepsi\xe9s", 1) if marker in raw
               else raw + b"\n\xe9\n")
        with open(dst, "wb") as fh:
            gz = gzip.GzipFile(filename="", mode="wb", fileobj=fh, mtime=0)
            gz.write(raw)
            gz.close()
    with pytest.raises(etl.EicuError, match="undecodable-table") as ei:
        list(etl.read_table(bad, "patient"))
    assert "'patient'" in str(ei.value) and "patient.csv.gz" in str(ei.value)

    # 2. truncated: a partial unzip of the download
    trunc = str(tmp_path / "truncated")
    os.makedirs(trunc, exist_ok=True)
    for table in mock.EICU_MOCK_TABLES:
        src = etl._resolve_table_path(mock_small["dir"], table)
        dst = os.path.join(trunc, f"{table}.csv.gz")
        blob = pathlib.Path(src).read_bytes()
        pathlib.Path(dst).write_bytes(
            blob[: len(blob) // 2] if table == "patient" else blob)
    with pytest.raises(etl.EicuError, match="truncated-table") as ei:
        list(etl.read_table(trunc, "patient"))
    assert "'patient'" in str(ei.value)

    # both tags are in the module's CLOSED reason-tag vocabulary
    for tag in ("undecodable-table", "truncated-table"):
        assert tag in etl.EicuError.__doc__


def test_preflight_profiles_through_an_unknown_outcome_level(tmp_path,
                                                             mock_small):
    """E-16: preflight must not be aborted by the drift it exists to report.

    One row of 9000 re-cased to 'EXPIRED' (a plausible re-export) used to raise
    `unknown-outcome-level` from inside `_select_cohort`'s row loop, discarding
    every value count already accumulated -- so the operator got the token but
    no count, no site distribution, no attrition ledger, no sentinel
    histograms, and no `EICU_preflight.json` at all. `build_raw`'s raise is
    unchanged.
    """
    d = str(tmp_path / "thirdlevel")
    os.makedirs(d, exist_ok=True)
    for table in mock.EICU_MOCK_TABLES:
        src = etl._resolve_table_path(mock_small["dir"], table)
        dst = os.path.join(d, f"{table}.csv.gz")
        if table != "patient":
            shutil.copyfile(src, dst)
            continue
        with open(dst, "wb") as raw:
            gz = gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0)
            fh = io.TextIOWrapper(gz, encoding="utf-8", newline="")
            w = csv.writer(fh, quoting=csv.QUOTE_MINIMAL)
            with gzip.open(src, "rt", encoding="utf-8-sig", newline="") as f:
                r = csv.reader(f)
                header = next(r)
                w.writerow(header)
                j = [h.strip().lower() for h in header].index(
                    etl.EICU_LABEL_COLUMN)
                done = False
                for row in r:
                    if not row:
                        continue
                    if not done and row[j].strip() == "Expired":
                        row = list(row)
                        row[j] = "EXPIRED"
                        done = True
                    w.writerow(row)
            fh.close()
            assert done

    # preflight COMPLETES and reports the token, its count, and the raise
    pf = etl.preflight(d, verbose=False)
    assert set(pf) == PREFLIGHT_KEYS
    assert pf["patient"]["hospitaldischargestatus"].get("EXPIRED") == 1
    assert any("E-16" in w for w in pf["warnings"])
    assert any("unknown-outcome-level" in c
               for c in pf["reference_check"]["invalid_conditions"])
    assert pf["attrition"][0]["n_stays"] > 0        # the ledger survived

    # build_raw still refuses, and the message names the function that raised
    with pytest.raises(etl.EicuError, match="unknown-outcome-level") as ei:
        etl.build_raw(d, verbose=False)
    assert "eicu_etl._select_cohort" in str(ei.value)


def test_reference_check_passes_when_the_constants_match_the_corpus(
        monkeypatch, mock_small):
    """E-13: the mandatory first command must not abort on a CORRECT extract.

    `n_uniquepid` was counted POST-filter (after the S1-S4 drops) and compared
    against EICU_REFERENCE_PATIENTS = 139367, the dataset's PRE-filter
    published total. On the real extract ~1751 stays carry a blank outcome and
    at 1.44 stays/patient most of those patients lose every stay, so the
    computed count lands ~1.7% low and `preflight(expect_reference=True)` --
    the documented arrival-day command -- aborts, writing NO artifact at all.
    The old suite could not see this: its only reference test asserts a RAISE,
    so a spurious mismatch and a genuine one were indistinguishable.

    Here every reference constant is re-pinned to the mock's own TRUE
    whole-table values, so the only thing that can disagree is the estimator.
    """
    d = mock_small["dir"]
    rows = {t: sum(1 for _ in etl.read_table(d, t)) for t in etl.EICU_TABLES}
    uids, sites = set(), set()
    for row in etl.read_table(d, "patient"):
        uids.add((row["uniquepid"] or "").strip())
        sites.add(etl._maybe_int(row["hospitalid"]))
    sites.discard(None)

    monkeypatch.setattr(etl, "EICU_REFERENCE_ROW_COUNTS", rows)
    monkeypatch.setattr(etl, "EICU_REFERENCE_SITES", len(sites))
    monkeypatch.setattr(etl, "EICU_REFERENCE_PATIENTS", len(uids))
    monkeypatch.setattr(etl, "EICU_REFERENCE_UNIT_STAYS", rows["patient"])

    pf = etl.preflight(d, expect_reference=True, verbose=False)   # must NOT raise
    assert pf["reference_check"]["ok"] is True
    assert pf["reference_check"]["mismatches"] == []
    # the identity counts are the RAW ones; the cohort counts are separate and
    # are ALLOWED to be smaller -- that is the distinction the fix introduced
    assert pf["patient"]["n_uniquepid"] == len(uids)
    assert pf["patient"]["n_hospitals"] == len(sites)
    assert pf["patient"]["n_uniquepid_cohort"] < pf["patient"]["n_uniquepid"]


def test_header_case_verdict_is_pinned_per_table_for_both_mock_modes(
        tmp_path_factory, mock_small):
    """E-17: a fully camelCase header must not read as 'mixed'.

    The old rule required EVERY name to carry an upper-case character, so
    single-token names (`age`, `gender`, `ph`, `urine`, `region`) forced
    'mixed' on four of the five tables -- and 'mixed' reads as "some columns
    were re-cased and some were not", a materially different diagnosis in
    exactly the direction T-6 exists to detect. The old test accepted any of
    the three values, so it could not see the wrong answer.
    """
    camel = etl.preflight(mock_small["dir"], verbose=False)
    for t in etl.EICU_TABLES:
        entry = camel["tables"][t]
        assert entry["header_case_as_read"] == "camel", t
        assert entry["n_names_with_uppercase"] > 0

    low = str(tmp_path_factory.mktemp("eicu_lower") / "corpus")
    mock.generate(mock.MockConfig(stays=TINY_STAYS, sites=TINY_SITES,
                                  signal=False, header_case="lower", out=low))
    pf = etl.preflight(low, verbose=False)
    for t in etl.EICU_TABLES:
        entry = pf["tables"][t]
        assert entry["header_case_as_read"] == "lower", t
        assert entry["n_names_with_uppercase"] == 0

    # and a genuine re-export (separators + case) reads as 'mixed'
    assert etl._header_case(["patientUnitStayId", "hospital_id"]) == "mixed"
    assert etl._header_case(["patientunitstayid", "hospitalid"]) == "lower"


def test_room_air_fio2_is_an_observation_not_a_missing_value(tmp_path):
    """E-18: the fio2 windows are lower-CLOSED.

    `fio2 == 0.21` (equivalently `21`) is ROOM AIR -- the modal value of a
    ventilation-linked column. The frozen windows were lower-OPEN, so it was
    discarded as missing and the loss was buried in a `unit_conversions`
    counter. Ventilation status is site-correlated, so that converted the
    commonest valid value into exactly the informative-missingness channel this
    protocol undertakes to guard.
    """
    rows = {"patient": [], "hospital": [_hospital(1)],
            "apacheApsVar": [], "apachePredVar": []}
    for i, f in enumerate(("0.21", "21", "0.35", "50", "1.0", "100"), start=1):
        rows["patient"].append(_patient(
            i, hospitaldischargestatus="Expired" if i == 1 else "Alive"))
        rows["apacheApsVar"].append(_aps(i, i, fio2=f))
        rows["apachePredVar"].append(_apv(i, i))
    d = _write_corpus(str(tmp_path / "roomair"), rows)
    x, names, meta = etl.build_raw(d, verbose=False)
    j = _col_of(names, "aps_fio2")
    jm = _col_of(names, "aps_fio2__missing")
    for stay, want in ((1, 0.21), (2, 0.21), (3, 0.35), (4, 0.50),
                       (5, 1.0), (6, 1.0)):
        r = _row_of(meta, stay)
        assert x[r, jm] == 0.0, f"stay {stay} fio2 dropped as missing"
        assert x[r, j] == pytest.approx(want), stay
    # the room-air conversions are COUNTED, so the decision stays visible
    conv = meta["unit_conversions"]
    assert conv.get("aps_fio2:room-air-fraction") == 1
    assert conv.get("aps_fio2:room-air-percent") == 1
    assert not any(k.endswith(":at-window-floor") for k in conv)


# ================================================ 22. full-scale (env-gated) ==

@pytest.mark.skipif(os.environ.get("CERTGATE_EICU") != "1",
                    reason="full-scale eICU mock arm; set CERTGATE_EICU=1")
def test_full_scale_mock_reaches_an_honest_outcome(tmp_path):
    """The real eICU scale: 208 hospitals / 200,859 unit stays (~35 MB of
    gzip), 24 held out -> 73/36/75 with MIN_CAL_CLUSTERS = 50 and 50%
    headroom. Certification is plausible here and, if issued, must survive the
    oracle; a decline is equally acceptable."""
    out = str(tmp_path / "eicu_full")
    manifest = mock.generate(mock.MockConfig(stays=mock.EICU_MOCK_FULL_STAYS,
                                             sites=mock.EICU_MOCK_FULL_SITES,
                                             out=out))
    assert manifest["sites"] == mock.EICU_MOCK_FULL_SITES == 208
    assert manifest["stays_requested"] == mock.EICU_MOCK_FULL_STAYS == 200859

    rep, ctx = _run_eicu(out)
    outcome = _assert_honest(rep, ctx)
    assert outcome in ("certified", "declined")
    assert rep["diagnostic"]["n_cal_carrying"] >= MIN_CAL_CLUSTERS
    assert len(ctx["sets"]["cal"]) == 75           # 208 - 24 = 184 -> 73/36/75

    # the report round-trips to JSON with the stable shapes: str(0.10) is "0.1"
    ser = json.dumps({k: v for k, v in rep["diagnostic"].items()
                      if k not in ("abstention_profile", "composition")},
                     default=str)
    assert json.loads(ser)["feasibility"].keys() == {"0.05", "0.1"}

    bd = rep["diagnostic"]["bbse"]
    assert bd is None or bd["n_target_sites"] in (None,
                                                  etl.EICU_N_TARGET_SITES)


@pytest.mark.skipif(os.environ.get("CERTGATE_EICU_LARGE") != "1",
                    reason="large-site eICU mock arm; set CERTGATE_EICU_LARGE=1")
def test_large_mock_reaches_the_certified_branch():
    """E-20: `margin_floor` scales as 1/n_carrying, so the frozen-size decline
    does NOT generalise to "any corpus size".

    The claim that the mock "declines every rung BY ARITHMETIC, at any corpus
    size" was propagated into SPEC.md, EICU-PROTOCOL.md (twice, including the
    operator checklist), CLAUDE.md and the comment on the frozen pin. It is
    false: the oracle margin 0.0354 is compared against a floor that FALLS with
    the calibration cluster count, and the crossing point is n_carrying = 77
    (~217 hospitals). At 900 hospitals the mock certifies alpha = 0.10 with
    EICU_MOCK_SIGNAL_B untouched.

    This arm exists so the certified branch -- `_eval_rung`'s certified path,
    `_abstention_ranking` (which settles P4), `_rm_on_pool` /
    `_per_site_exceed_frac` -- is exercised before the extract lands, and so
    that the corrected claim stays checkable. It still asserts HONESTY, never
    that certification happens.
    """
    import tempfile
    from certgate.certify import margin_floor
    from certgate.constants import DELTA

    # the arithmetic the corrected claim rests on
    assert margin_floor(63, DELTA, 0.10) > 0.0354     # small arm  -> declines
    assert margin_floor(75, DELTA, 0.10) > 0.0354     # full arm   -> declines
    assert margin_floor(77, DELTA, 0.10) < 0.0354     # crossing point

    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "eicu_large")
        mock.generate(mock.MockConfig(stays=90000, sites=900, out=out))
        rep, ctx = _run_eicu(out)
        outcome = _assert_honest(rep, ctx)
        assert outcome in ("certified", "declined")
        assert rep["diagnostic"]["n_cal_carrying"] > 77, (
            "this arm is pointless unless it clears the crossing point")
