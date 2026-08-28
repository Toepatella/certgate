"""Shared apparatus for the eICU test files (test_eicu_mock/_etl/_run).

Frozen key sets, the planted-trap row builders and corpus writer, the
ETL -> run_certgate driver with its honesty assertion, and the fixtures
more than one file uses (mock_small, pipeline_small).
Split from test_eicu_path.py on 2026-08-25; the code is relocated verbatim.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import os
import pathlib

import numpy as np
import pytest

from certgate.harness import hard_violation
from certgate.model import fit_head
from certgate.pipeline import run_certgate
from certgate.report import render_text
from certgate.validate import assert_site_disjoint, from_raw
from experiments import eicu_etl as etl
from experiments import eicu_mock as mock


# ---------------------------------------------------------------------------
# Sizes for the auxiliary corpora. The canonical small arm is the mock's own
# default: 180 hospitals / 9000 stays -> 63 carrying calibration sites, so
# certification is reachable and a decline is equally legitimate. The tiny
# byte-determinism corpus runs signal=False, the one configuration in which
# generate admits fewer than EICU_MIN_TOTAL_SITES sites.
TINY_SITES, TINY_STAYS = 60, 900
DRIFT_STAYS = 2400

# F-D, the unfalsifiable-success failure: too good a result is a leak alarm.
# The mock's outcome comes from a latent severity at the frozen slope
# EICU_MOCK_SIGNAL_B = 0.85, so its Bayes-optimal AUC is Phi(0.85/sqrt(2)) =
# 0.726 and the shipped clean corpus measures 0.597.
#
# The ceiling is therefore derived from that Bayes-optimal value plus a margin.
# 0.80 leaves ~0.07 of headroom for finite-sample noise and still refuses
# anything a latent-severity model at B = 0.85 cannot produce. A ceiling far
# above it -- the audit found 0.98 -- detects only a leak of near-label
# strength, and let a leak-planted corpus measuring 0.835 through.
# Ref: audit E-10 (2026-07-31).
LEAK_AUC_CEILING = 0.80

# The subtle positive control: outcome-correlated APACHE-row absence at this
# rate, with nothing else about the corpus changed. At p = 0.30 the shipped
# small corpus measures head AUC 0.671, missingness-ablation drop +0.082, and
# an absent:present outcome prevalence ratio of 3.86. That AUC sits below the
# ceiling above, which is why the AUC leg alone is not enough.
LEAK_ABSENCE_RATE = 0.30

# Generous on purpose. The load-bearing assertion is the pandas/pyarrow
# refusal; this set only has to keep a genuinely new third-party import from
# passing unnoticed. Ref: audit F16.
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
    # Three screens the 2026-07-31 audit added.
    "outcome_stratified_missingness",   # E-9  outcome-informative absence
    "apache_absent_los",                # E-9  site channel vs outcome channel
    "unparseable_tokens",               # E-15 a NULL token that is not ''
    # The join-key format profile, so preflight projects the
    # unparseable-join-key and apache-coverage-collapse raises.
    # Ref: arrival-day audit, amendment A5 (2026-07-31).
    "join_key_unparseable",             # E-21 an unlinked child table
}

# The casing verdict is decidable, so it is pinned per table for both mock
# header modes rather than accepted as "one of the three". Ref: audit E-17.
HEADER_CASE_EXPECTED = {"camel": "camel", "lower": "lower"}

MANIFEST_KEYS = {
    "seed", "stays_requested", "stays_written", "admissions", "sites",
    "site_size_sigma", "base_rate", "header_case", "signal", "warts", "drift",
    "row_counts", "apache_site_coverage_bands", "sites_with_zero_result_rows",
}

# Every leak the protocol names (§A.7). Asserted by name, so deleting a
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

# The patient source columns that do contribute features (§A.5.1/§A.5.2).
# hospitaladmitoffset is the source of the pre_icu_hours feature -- the one
# allowlisted column whose feature name differs from its column name.
ALLOW_PATIENT = frozenset({
    "age", "admissionheight", "admissionweight", "hospitaladmitoffset",
    "gender", "ethnicity", "hospitaladmitsource", "unitadmitsource",
    "unittype", "unitstaytype",
})

# Deny-by-default's third bucket: columns that are neither features nor leaks.
#   - surrogate and natural keys
#   - admission-time timestamps, which carry no outcome information and are
#     not modelled
#   - the APACHE version tag
#   - the site-constant hospital covariates, read only as diagnostic strata
# Pinned per table, so a new schema column -- or a column quietly promoted into
# the allowlist -- fails the exhaustiveness test. Ref: protocol §A.6.
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
    """sha256 of every .csv.gz in a corpus directory, keyed by filename."""
    out = {}
    for p in sorted(pathlib.Path(data_dir).iterdir()):
        if p.name.endswith(".csv.gz"):
            out[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def _int_leaf_sum(obj) -> int:
    """Sum of every integer leaf in a nested counter structure.

    The ETL's counter dicts (sentinel_counts, dedup_counts, ...) are frozen by
    name but not by internal shape. Summing the leaves asserts "this channel
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
# The mock plants every wart at a rate; these corpora plant exactly one. A
# regression in a single documented trap then goes red on its own line rather
# than perturbing an aggregate. Column names and DDL order come from
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

    Byte-determinism mirrors synth_fixture.TableWriter: a GzipFile with
    filename="" and mtime=0, wrapped in TextIOWrapper(newline=""), so a planted
    corpus is reproducible too. csv.writer owns the line endings.
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
    """Matrix row index carrying a given patientunitstayid, order-free."""
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
    """ETL -> cohorts -> run_certgate on a built corpus, as (rep, ctx)."""
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
    # records never cross a boundary; this runs before every certification
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
    """The canonical small corpus, generated once and never into the repo."""
    out = str(tmp_path_factory.mktemp("eicu_small") / "corpus")
    manifest = mock.generate(mock.MockConfig(out=out))
    return dict(dir=out, manifest=manifest)


@pytest.fixture(scope="module")
def pipeline_small(mock_small):
    """The full always-on path: ETL -> split -> impute -> cohorts -> certgate.

    Built once. Re-reading the extract per test is a build error, not a style
    preference (T-16).
    """
    rep, ctx = _run_eicu(mock_small["dir"])
    return dict(rep=rep, **ctx)
