"""The eICU ETL boundary: ingest gates, feature contract, leak proofs.

read_table decode/truncation and null-token gates, join keys, _select_cohort,
preflight, build_raw's planted traps, S_train-only impute, the three-way
leak-denylist proof, the EicuError vocabulary, and the AST import rules.
Split from test_eicu_path.py on 2026-08-25; the tests are relocated verbatim.
"""
from __future__ import annotations

import ast
import csv
import gzip
import io
import json
import math
import os
import pathlib
import random
import shutil

import numpy as np
import pytest
from sklearn.metrics import roc_auc_score

from certgate.constants import MIN_CAL_CLUSTERS, SPLIT_FRACTIONS
from certgate.model import fit_head
from certgate.validate import Cohort, densify_sites, from_raw, normalized_label
from experiments import eicu_etl as etl
from experiments import eicu_mock as mock
from experiments import run_eicu

from _eicu_helpers import (ALLOW_PATIENT, DRIFT_STAYS, HEADER_CASE_EXPECTED,
                           KNOWN_LEAKS, LEAK_ABSENCE_RATE, LEAK_AUC_CEILING,
                           NEITHER, PREFLIGHT_KEYS, TINY_SITES, TINY_STAYS,
                           _STDLIB_OK, _aps, _apv, _attrition, _col_of,
                           _deny_bare, _hospital, _int_leaf_sum, _patient,
                           _result, _row_of, _schema_columns, _write_corpus,
                           mock_small, pipeline_small)


def _plant_outcome_correlated_absence(src, dst, rate, seed=7):
    """Copy a corpus, deleting APACHE rows for a fraction of decedents.

    This is the E-9 mechanism in its purest form: the day-1 window did not
    close because the stay ended. Nothing else changes -- same features,
    labels, hospitals and coverage bands -- so whatever the pipeline sees
    downstream comes from this channel alone.

    The resulting APACHE coverage stays indistinguishable from the released
    extract's 171177/200859 = 0.852, which is why coverage cannot be the
    screen.

    Refs: audit E-9, the 2026-07-31 critical finding.
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
    """Copy a corpus, blanking every allowlisted APS cell for some decedents.

    The row is kept, so aps_present stays 1 for every stay and the whole-row
    prevalence-ratio abort cannot see this; what moves is the 24
    aps_*__missing siblings. The mechanism is realistic -- a panel stops being
    drawn once a patient is dying -- and it proves the F-D ablation leg has
    power the ratio gate does not.
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
    """A column-level leak: the rows survive, only the cells go missing.

    build_raw succeeds on this corpus, because the presence flags are untouched
    and the prevalence-ratio abort cannot fire. The only thing left to catch it
    is the missingness-ablation leg of F-D.
    """
    out = str(tmp_path_factory.mktemp("eicu_leak_sub") / "corpus")
    # Calibrated: head AUC 0.705, below EICU_LEAK_AUC_CEILING = 0.90, so the
    # discrimination leg stays silent. Ablation drop +0.106, over the 0.05 cap.
    # Whole-row presence ratio 1.11, unchanged from the clean corpus.
    return _plant_column_level_absence(mock_small["dir"], out, 0.35)


@pytest.fixture(scope="module")
def mock_drift(tmp_path_factory):
    """A corpus whose categorical drift is pushed past EICU_MAX_OTHER_SHARE."""
    out = str(tmp_path_factory.mktemp("eicu_drift") / "corpus")
    mock.generate(mock.MockConfig(stays=DRIFT_STAYS,
                                  sites=mock.EICU_MOCK_SMALL_SITES,
                                  drift=True, out=out))
    return out


@pytest.fixture(scope="module")
def planted(tmp_path_factory):
    """Sentinel corpus: clean, all -1, all empty string, no APACHE row."""
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
    """Dedup corpus: IV/IVa preference, duplicate ids, a '-1' probability."""
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


# ==================================================== 4-5. feature contract ===

def test_feature_name_list_matches_the_pinned_width():
    names = list(etl.FEATURE_NAMES)
    assert len(names) == etl.EICU_N_FEATURES == 161
    assert len(set(names)) == len(names), "duplicate feature name"
    # every __missing sibling sits immediately after its parent, so a column
    # and its indicator can never be reordered apart
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


def test_rank_auc_matches_the_sklearn_reference_implementation():
    """_rank_auc agrees with sklearn's roc_auc_score.

    It is hand-rolled because the enclave rule pins eicu_etl to numpy plus
    certgate, and the AUC it produces is a published number: the APACHE-IVa
    comparison. Tie handling is the whole risk, so the cases below are
    weighted towards ties.

    Refs: audit F16.
    """
    rng = np.random.default_rng(11)
    cases = {
        "continuous": (rng.normal(size=400), rng.random(400) < 0.3),
        "heavy_ties": (rng.integers(0, 3, 400).astype(float),
                       rng.random(400) < 0.4),
        "all_tied": (np.full(200, 2.0), rng.random(200) < 0.5),
        "binary_scores": ((rng.random(300) < 0.5).astype(float),
                          rng.random(300) < 0.25),
        "perfectly_separated": (np.arange(100, dtype=float),
                                np.arange(100) >= 50),
    }
    for name, (v, y) in cases.items():
        ours = etl._rank_auc(v, y)
        assert ours == pytest.approx(float(roc_auc_score(y, v)), abs=1e-12), name
    # the absent-class contract sklearn cannot express: None, never a number
    assert etl._rank_auc(np.arange(10.0), np.zeros(10, dtype=bool)) is None
    assert etl._rank_auc(np.arange(10.0), np.ones(10, dtype=bool)) is None


def test_leak_denylist_excludes_every_known_leak_from_features():
    """Every documented leak is denylisted and out of the features (T-1)."""
    assert len(etl.EICU_LEAK_DENYLIST) == 36
    bare = _deny_bare()
    names = list(etl.FEATURE_NAMES)
    for col in KNOWN_LEAKS:
        assert col in bare, f"{col} is not on EICU_LEAK_DENYLIST"
        for form in (col, f"aps_{col}", f"apv_{col}", f"{col}__missing",
                     f"aps_{col}__missing", f"apv_{col}__missing"):
            assert form not in names, f"leak {form} reached FEATURE_NAMES"
        assert not any(n.startswith(f"{col}=") for n in names), col
    etl.assert_no_leak_columns(names)              # the shipped list is clean


def test_assert_no_leak_columns_raises_when_a_leak_is_reintroduced():
    """Reintroducing a leak in any sanctioned spelling must raise, not warn."""
    names = list(etl.FEATURE_NAMES)
    for reintroduced in ("diedinhospital", "apv_diedinhospital",
                         "apv_diedinhospital__missing",
                         "actualhospitalmortality", "hospitalid",
                         "hospitalid=420", "aps_apachescore"):
        with pytest.raises(etl.EicuError, match="leak-column-in-features"):
            etl.assert_no_leak_columns(names + [reintroduced])


def test_allowlist_and_denylist_are_disjoint_and_jointly_exhaustive():
    """Deny by default, proved structurally.

    Every DDL column of the five source tables lands in exactly one of three
    buckets: allowlisted feature source, denylisted, or the pinned
    neither-bucket of keys, timestamps and site-constant strata. A column moved
    into the allowlist collides, and one quietly dropped from the denylist
    becomes unclassified, so the allowlist cannot grow by accident.
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
    # apachePatientResult and hospital contribute no features (§A.6): the first
    # has 8.65% zero-coverage hospitals, the second is site-constant.
    assert not allow["apachePatientResult"] and not allow["hospital"]


def test_no_leak_reaches_the_matrix_via_implausible_discrimination(
        pipeline_small):
    """A leak announces itself as implausible AUC.

    The ceiling is derived from the mock's own Bayes-optimal AUC; the
    arithmetic is on LEAK_AUC_CEILING above. The positive control below proves
    the probe has the power to see the leak it is looking for.

    Refs: threat T-1; failure criterion F-D; audit E-10.
    """
    train, cal = pipeline_small["train"], pipeline_small["cal"]
    head = fit_head(train)
    auc = roc_auc_score(cal.y, head.predict_proba(cal.x))
    assert 0.0 <= auc <= LEAK_AUC_CEILING, (
        f"out-of-sample AUC {auc:.4f} exceeds the leak ceiling "
        f"{LEAK_AUC_CEILING} -- re-audit EICU_LEAK_DENYLIST and the "
        f"first-stay/dedup logic before reporting any number (F-D)")

    # positive control: an outcome column must be visible to the probe
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
    """The ceiling must be derived from the mock's own outcome model.

    Phi(B/sqrt(2)) is the AUC a score that recovers the latent severity
    perfectly attains, the honest upper bound for anything the mock can
    produce. A ceiling far above it makes the probe decorative; one below it
    makes the suite flaky (audit E-10).
    """
    bayes = 0.5 * (1.0 + math.erf(mock.EICU_MOCK_SIGNAL_B / 2.0))
    assert bayes == pytest.approx(0.7264, abs=5e-4)
    assert bayes < LEAK_AUC_CEILING <= bayes + 0.08
    assert LEAK_AUC_CEILING == 0.80          # literal pin, per audit F13


def test_outcome_correlated_apache_absence_is_caught_before_any_certificate(
        mock_leak):
    """The E-9 critical finding, as a regression test.

    APACHE day-1 rows do not exist for a stay that ends because the patient
    died before the window closes. So aps_present, apv_present and the 43
    __missing siblings are an outcome proxy with no column name, invisible to
    the denylist, the -1 gate and the drift gate alike.

    mock_leak plants that mechanism and changes nothing else. Three assertions
    follow, in pipeline order: preflight measures it, build_raw aborts on it,
    and the apache-linked arm is the escape that pays the immortal-time cost.

    Refs: audit E-9; failure criterion F-D.
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
    # outcome channel: absent stays are short because they ended
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
    """The runtime alarm has power against a realistic leak.

    mock_leak_subcap plants outcome-correlated missingness at the cell level.
    The apacheApsVar rows survive, so aps_present stays 1 everywhere, the
    whole-row prevalence-ratio abort cannot fire, and build_raw succeeds. Only
    the ablation leg of F-D is left, and it is what sees this (audit E-10).
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

    # the leak is real, and the AUC ceiling alone cannot see it
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
    """Post-hoc timing is settled from data, not from DDL comments.

    The denylist applies a "timing relative to outcome unverified" standard to
    two apachePatientResult columns, but nine apachePredVar treatment flags had
    no timing verification at all. activetx is the worst: active treatment
    versus comfort measures is decided during the stay. Nothing in preflight
    could settle that; outcome_screen does (audit E-19).
    """
    ctx = pipeline_small
    screen = etl.outcome_screen(ctx["x_raw"], ctx["meta"], names=ctx["names"])
    assert set(screen["features"]) == set(ctx["names"])
    assert screen["n_features"] == etl.EICU_N_FEATURES
    assert 0.0 < screen["base_prevalence"] < 1.0
    for name, e in screen["features"].items():
        assert e["kind"] in ("binary", "continuous", "degenerate"), name
        assert e["auc"] is None or 0.0 <= e["auc"] <= 1.0

    # every named timing suspect is screened, and on the clean corpus none of
    # them is anywhere near the review band
    for col in run_eicu.EICU_TIMING_UNVERIFIED:
        e = screen["features"][f"apv_{col}"]
        assert e["auc"] is not None, col
        assert abs(e["auc"] - 0.5) <= (etl.EICU_FEATURE_AUC_REVIEW - 0.5), (
            f"apv_{col} univariate AUC {e['auc']} is past the pre-registered "
            f"review band; its measurement TIMING must be re-audited before "
            f"any number is reported (E-19)")
    assert not screen["flagged"]

    # ... and the screen has power: an injected outcome column is flagged
    y = ctx["y_bool"].astype(np.float64)
    x2 = np.column_stack([ctx["x_raw"], y])
    screen2 = etl.outcome_screen(x2, ctx["meta"],
                                 names=list(ctx["names"]) + ["__leak__"])
    assert [d["feature"] for d in screen2["flagged"]] == ["__leak__"]


# ========================================================== 6-7. preflight ===

def test_preflight_profiles_without_certifying(mock_small):
    """The mandatory pass: it profiles; it builds and certifies nothing."""
    pf = etl.preflight(mock_small["dir"], verbose=False)
    assert set(pf) == PREFLIGHT_KEYS
    assert "certified" not in pf and "operative" not in pf

    assert set(pf["tables"]) == set(etl.EICU_TABLES)
    for t, entry in pf["tables"].items():
        assert set(entry) == {"path", "rows", "header", "header_raw",
                              "header_case_as_read", "n_names_with_uppercase",
                              "reference_rows", "rows_match_reference"}
        # E-17: the verdict is decidable and pinned, not merely "one of three"
        assert entry["header_case_as_read"] == HEADER_CASE_EXPECTED["camel"]
        assert len(entry["header_raw"]) == len(entry["header"])
        assert entry["reference_rows"] == etl.EICU_REFERENCE_ROW_COUNTS[t]
        assert entry["rows_match_reference"] is False    # mock, not the extract

    man = mock_small["manifest"]
    assert pf["patient"]["n_rows"] == pf["tables"]["patient"]["rows"]
    assert pf["patient"]["n_rows"] == man["stays_written"]
    assert pf["patient"]["n_hospitals"] == man["sites"]
    # E-13: identity counts are raw (S0); cohort counts are named separately
    assert pf["patient"]["n_hospitals_cohort"] <= pf["patient"]["n_hospitals"]
    assert pf["patient"]["n_uniquepid_cohort"] <= pf["patient"]["n_uniquepid"]
    assert set(pf["patient"]["hospitaldischargestatus"]) <= {"Alive",
                                                             "Expired", ""}

    # the ledger is frozen in order, and records n_sites and n_positive as well
    # as n_stays: n_stays alone cannot show a prevalence collapse (E-9)
    assert [e["step"] for e in pf["attrition"]] == list(etl.EICU_ATTRITION_STEPS)
    for e in pf["attrition"]:
        assert set(e) == {"step", "n_stays", "n_sites", "n_positive",
                          "prevalence"}
        assert 0 <= e["n_positive"] <= e["n_stays"]
    att = _attrition(pf)
    assert att["raw-unit-stays"] >= att["outcome-known"] >= att["adult"] \
        >= att["first-stay"] == att["primary-cohort"]

    # The mandated site-informative-missingness diagnostic (T-3). CertGate v2
    # scope-cut covariate-shift mode, so this must be surfaced per site and
    # never imputed away. Asserted as a superset: the five mandated fields must
    # be present and well-formed, and measuring more of what the SPEC wants
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
        # the mock modulates the -1 rate per site (wart W3), so the dispersion
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
    """The mock is not the extract, so expect_reference=True refuses (T-6)."""
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
    """-1 is the undocumented APACHE sentinel (T-2).

    It is a plausible finite number, so it passes every downstream gate and
    silently poisons the head. The all -1 stay must arrive as all-missing, and
    no -1 may survive.
    """
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

    # presence is row presence, not value presence: the all-(-1) stay carried a
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
    """Handling the -1 sentinel alone leaves the SQL NULL '' in the matrix."""
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
    """Whole-row APACHE absence is site-correlated (T-3).

    It is named by one explicit column rather than smeared across 43 __missing
    siblings, so the abstention explanations can point at it (prediction P4).
    """
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
    """T-2's other half: an unrecognised negative sentinel aborts.

    Every allowlisted column has non-negative physiological support, so
    negative mass that is not exactly -1.0 is unrecognised. It must abort --
    never flow, and never be absorbed by a "value < 0 means missing" rule the
    histogram has not yet justified.
    """
    dst = _write_corpus(str(tmp_path / "negsentinel"), {
        "patient": [_patient(1), _patient(2)],
        "hospital": [_hospital(1)],
        "apacheApsVar": [_aps(1, 11), _aps(2, 12, wbc="-7")],
        "apachePredVar": [_apv(1, 21), _apv(2, 22)],
        "apachePatientResult": [],
    })
    with pytest.raises(etl.EicuError, match="unexpected-negative-sentinel"):
        etl.build_raw(dst, verbose=False)


def test_sub_threshold_negative_sentinel_flows_as_missing(tmp_path):
    """Amendment A6: sub-threshold negative mass warns instead of aborting.

    Negative-not-(-1) mass below EICU_MAX_UNPARSEABLE_SHARE maps to missing and
    warns. The released extract carries exactly one such cell in ~4.1M:
    one cohort stay carried a large negative urine value (identifier and raw value withheld).

    Those cells always became NaN and the raise was only a look-at-this gate,
    so no computed number changes. Above the threshold the abort must still
    fire, which the test above pins at a 1-in-2 rate.

    Refs: EICU-PROTOCOL amendment A6, post-hoc, logged data-seen.
    """
    n = 200                                    # 1/200 = 0.005 < 0.01
    rows = {"patient": [], "hospital": [_hospital(1)],
            "apacheApsVar": [], "apachePredVar": [],
            "apachePatientResult": []}
    for i in range(1, n + 1):
        rows["patient"].append(_patient(
            i, hospitaldischargestatus="Expired" if i % 7 == 0 else "Alive"))
        over = {"urine": "-4321.5"} if i == 3 else {}
        rows["apacheApsVar"].append(_aps(i, i, **over))
        rows["apachePredVar"].append(_apv(i, i))
    dst = _write_corpus(str(tmp_path / "subthreshold"), rows)

    x_raw, names, meta = etl.build_raw(dst, verbose=False)
    assert x_raw.shape[0] == n
    assert meta["sentinel_counts"]["aps_urine"]["other_negative"] == 1
    assert any("A6" in w for w in meta["warnings"]), (
        "a post-hoc relaxation must announce itself in the warnings")
    # the offending cell is missing, never a finite negative
    r = _row_of(meta, 3)
    assert np.isnan(x_raw[r, _col_of(names, "aps_urine")])
    assert x_raw[r, _col_of(names, "aps_urine__missing")] == 1.0
    # and no finite negative urine survives anywhere
    col = x_raw[:, _col_of(names, "aps_urine")]
    assert not np.any(col[np.isfinite(col)] < 0.0)

    pf = etl.preflight(dst, verbose=False)
    assert not any("unexpected-negative-sentinel" in c
                   for c in pf["reference_check"]["invalid_conditions"])
    assert any("A6" in w for w in pf["warnings"])


def test_age_over_89_is_kept_and_flagged(tmp_path):
    """The HIPAA age-ceiling token is kept, not dropped.

    Dropping '> 89' -- the common benchmark's max_age=89 -- removes a
    mortality-enriched stratum whose share varies by hospital, so it is a
    site-correlated exclusion. It is kept at 90.0 with an explicit indicator,
    which leaves the ceiling visible to the head and to Shapley.
    """
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
    """~0.87% of stays have no usable outcome, and they are dropped.

    MIT-LCP's own icustay_detail uses ELSE NULL, and a coerced blank would
    fabricate ~1750 survivors.
    """
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
    """A value outside {'Alive', 'Expired', ''} must raise, not be coerced."""
    dst = _write_corpus(str(tmp_path / "badstatus"), {
        "patient": [_patient(1), _patient(2, hospitaldischargestatus="Transferred")],
        "hospital": [_hospital(1)],
        "apacheApsVar": [], "apachePredVar": [], "apachePatientResult": [],
    })
    with pytest.raises(etl.EicuError, match="unknown-outcome-level"):
        etl.build_raw(dst, verbose=False)


def test_first_stay_rule_picks_the_highest_hospitaladmitoffset(tmp_path):
    """S4's sign trap: hospitaladmitoffset is negative minutes.

    The earliest stay therefore has the highest, least negative, offset. Using
    min here silently selects the last ICU stay of an admission, which is a
    post-hoc selection.
    """
    dst = _write_corpus(str(tmp_path / "firststay"), {
        "patient": [
            # tie on unitvisitnumber -> max offset wins (-14 beats -22)
            _patient(1001, patienthealthsystemstayid=100, unitvisitnumber=1,
                     hospitaladmitoffset=-14),
            _patient(1002, patienthealthsystemstayid=100, unitvisitnumber=1,
                     hospitaladmitoffset=-22),
            # unitvisitnumber is the primary key: 1 beats 2 despite the offset
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
    # the offset survives only as a windowed pre-ICU duration, sign corrected
    assert x_raw[_row_of(meta, 1001), _col_of(names, "pre_icu_hours")] == \
        pytest.approx(14.0 / 60.0)
    assert len(set(int(a) for a in np.asarray(meta["admission_id"]))) == 3


def test_apache_result_dedup_is_version_preferred_and_counted(planted_dedup):
    """apachePatientResult carries one row per apacheVersion (T-8, T-9).

    That is 297,064 rows over 171,177 stays, which is not 2x. And
    predictedhospitalmortality is a VARCHAR holding a probability, so compared
    as a string '-1' > '0'. Call float() first, always.
    """
    _, _, meta = etl.build_raw(planted_dedup, verbose=False)
    pred = np.asarray(meta["comparator_predicted_mortality"], dtype=np.float64)
    ver = list(meta["comparator_apache_version"])

    assert pred[_row_of(meta, 1)] == pytest.approx(0.22)   # IVa beats IV
    assert ver[_row_of(meta, 1)] == "IVa"
    assert pred[_row_of(meta, 2)] == pytest.approx(0.33)   # IV only
    assert ver[_row_of(meta, 2)] == "IV"
    assert pred[_row_of(meta, 3)] == pytest.approx(0.55)   # min surrogate id
    assert np.isnan(pred[_row_of(meta, 4)])                # the '-1' string
    assert np.isnan(pred[_row_of(meta, 5)])                # no row at all
    assert not (pred == -1.0).any()
    assert etl.EICU_APACHE_VERSION_PREFERENCE == ("IVa", "IV")
    assert _int_leaf_sum(meta["dedup_counts"]) >= 1         # reported, not silent


def test_duplicate_apache_rows_keep_the_minimum_surrogate_id(planted_dedup):
    """Duplicate APS rows: the minimum surrogate id wins, and it is counted."""
    x_raw, names, meta = etl.build_raw(planted_dedup, verbose=False)
    assert x_raw[_row_of(meta, 1), _col_of(names, "aps_heartrate")] == 88.0
    assert _int_leaf_sum(meta["dedup_counts"]) > 0


def test_categorical_level_drift_raises(mock_drift, pipeline_small):
    """A level tuple frozen without seeing the data can be wrong (T-7).

    Unlisted values fall to the OTHER bucket and are counted. Past the 5% cap
    the run stops, and the fix is a visible SPEC plus constants diff -- never a
    drift bucket the head quietly learns.
    """
    with pytest.raises(etl.EicuError, match="categorical-level-drift"):
        etl.build_raw(mock_drift, strict_levels=True, verbose=False)
    _, _, meta = etl.build_raw(mock_drift, strict_levels=False, verbose=False)
    shares = meta["categorical_other_shares"]
    assert max(shares.values()) > etl.EICU_MAX_OTHER_SHARE == 0.05

    # the canonical corpus exercises the OTHER bucket without tripping the gate
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
    for i, a in enumerate(keys):                   # pairwise, not a triple
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
    assert other != sets                           # an independent re-split


def test_site_split_refuses_a_population_it_cannot_calibrate():
    few = [f"{etl.EICU_SITE_PREFIX}{i}" for i in range(etl.EICU_MIN_TOTAL_SITES - 1)]
    with pytest.raises(etl.EicuError, match="too-few-sites"):
        etl.site_split(few, replicate=0)
    assert etl.EICU_MIN_TOTAL_SITES == 149


def test_split_leaves_at_least_min_cal_clusters(pipeline_small):
    """The site arithmetic, worked.

    180 mock hospitals minus 24 held out leaves 156, and 40/20/40 gives
    62/31/63. EICU_MOCK_MIN_STAYS_PER_SITE = 12 makes all 63 record-carrying,
    so MIN_CAL_CLUSTERS = 50 is satisfied and certification is reachable.
    """
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
    """The transductive leak no downstream gate catches.

    Pooled-matrix means would carry the target pool's covariate distribution
    into the training features, so perturbing the target pool must leave the
    fills untouched.
    """
    x_raw, idx, fill = (pipeline_small["x_raw"], pipeline_small["idx"],
                        pipeline_small["fill"])
    perturbed = x_raw.copy()
    tgt = idx["target"]
    block = perturbed[tgt]
    perturbed[tgt] = np.where(np.isnan(block), np.nan, block + 1000.0)
    x_p, fill2 = etl.impute(perturbed, idx["train"])
    assert fill2 == fill
    # asserted on the matrix too, so the check does not rest on the internal
    # shape of the fill record: the fitting rows come out identical
    assert np.array_equal(x_p[idx["train"]], pipeline_small["x"][idx["train"]])

    # and moving the fit set does move the imputed values -- the test has teeth
    x_c, _ = etl.impute(x_raw, idx["cal"])
    assert not np.array_equal(x_c, pipeline_small["x"])
    with pytest.raises(etl.EicuError, match="impute-fit-empty"):
        etl.impute(x_raw, np.array([], dtype=int))


def test_labels_flow_through_coerce_labels_not_a_bool_array(pipeline_small):
    """coerce_labels owns the two-value contract, never a hand-built array.

    require_both_classes=False is the target-pool-only opt-in.
    """
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
    """Site identity has one canonical spelling per hospital.

    It is always hosp-{int(hospitalid)}, so densify_sites' cosmetic-collision
    raise cannot fire on our own output. That raise exists because a hospital
    split into two "independent" clusters buys certification strength the
    honest clustering refuses. hospitalid and wardid never enter x.
    """
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
    """Identical inputs give byte-identical features.

    build_matrix wraps build_raw -> site_split -> impute, and must not diverge
    from the explicit path the runner uses.
    """
    x1, n1, m1 = etl.build_matrix(mock_small["dir"], verbose=False)
    x2, n2, m2 = etl.build_matrix(mock_small["dir"], verbose=False)
    assert np.array_equal(x1, x2)
    assert n1 == n2 == list(etl.FEATURE_NAMES)
    assert list(m1["site_raw"]) == list(m2["site_raw"])
    assert m1["impute_fill"] == m2["impute_fill"]
    assert np.array_equal(np.asarray(m1["stay_id"]), np.asarray(m2["stay_id"]))
    assert set(m1["split_sites"]) == {"train", "aux", "cal", "target"}

    assert np.array_equal(x1, pipeline_small["x"])
    assert m1["impute_fill"] == pipeline_small["fill"]
    assert list(m1["site_raw"]) == pipeline_small["site_raw"]


def test_out_of_range_comparator_probability_is_mapped_to_missing(tmp_path):
    """A comparator probability outside [0, 1] maps to missing (RP-8).

    predictedhospitalmortality is a VARCHAR(50) holding a probability, and only
    the exact -1 sentinel used to map to missing. A stray finite cell outside
    [0, 1] then reached two consumers that disagreed: _comparator_row scored it
    silently, while the panel's validate_inputs rejects it -- after the
    replicate's certification work, so a descriptive layer could take the
    certificate down. The released extract carries no such cell, 0 of 297,064
    rows, so this one is planted.
    """
    n = 40
    rows = {"patient": [], "hospital": [_hospital(1)], "apacheApsVar": [],
            "apachePredVar": [], "apachePatientResult": []}
    for i in range(1, n + 1):
        rows["patient"].append(_patient(
            i, hospitaldischargestatus="Expired" if i % 5 == 0 else "Alive"))
        rows["apacheApsVar"].append(_aps(i, i))
        rows["apachePredVar"].append(_apv(i, i))
        pred = "1.4" if i == 3 else ("-1" if i == 4 else "0.25")
        rows["apachePatientResult"].append(
            _result(i, 1000 + i, "IVa", pred))
    dst = _write_corpus(str(tmp_path / "oorcomp"), rows)

    _, _, meta = etl.build_raw(dst, verbose=False)
    assert meta["comparator_out_of_range"] == 1
    assert any("RP-8" in w for w in meta["warnings"]), (
        "a value-dependent map must announce itself, exactly as A6 does")

    comp = meta["comparator_predicted_mortality"]
    r_bad = _row_of(meta, 3)
    r_sentinel = _row_of(meta, 4)
    r_ok = _row_of(meta, 5)
    assert np.isnan(comp[r_bad])            # 1.4 -> missing, like -1
    assert np.isnan(comp[r_sentinel])
    assert comp[r_ok] == 0.25
    # no finite cell outside [0, 1] survives anywhere, which is precisely the
    # precondition reliability.validate_inputs enforces on p_ref
    fin = comp[np.isfinite(comp)]
    assert fin.size and np.all((fin >= 0.0) & (fin <= 1.0))

    # one definition of "comparator available": the mapped cell is absent from
    # the apache-complete arm too, so the comparator scoring and the panel's
    # p_ref agree instead of disagreeing silently.
    complete_step = [s for s in meta["attrition"]
                     if s["step"] == "apache-complete-arm"][0]
    assert complete_step["n_stays"] == int(np.isfinite(comp).sum())


def test_etl_imports_no_undeclared_dependency():
    """The ETL declares every dependency it uses (audit F16).

    pandas and pyarrow are installed here and are not in requirements.txt.
    eicu_etl is stdlib plus numpy only, eicu_mock is stdlib only, and every
    import sits at module top level for the enclave requirement.
    """
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
    """patientunitstayid is the primary key of patient (E-11).

    Unguarded, a duplicate collapses silently and inconsistently: scan A keeps
    the last row's label and hospital, scan B keeps the first row's features,
    and the record carries one patient's covariates under another's outcome.
    The collapse is also mis-accounted as a first-stay drop, and dedup_counts
    stays empty, because patient has no dedup path.
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
    # assert_site_disjoint and site_split, which compare labels only
    d2 = _write_corpus(str(tmp_path / "dup_site"), {
        "patient": [_patient(1, hospitalid=1, age=30),
                    _patient(1, hospitalid=2, age=80),
                    _patient(2, hospitalid=1)],
        "hospital": [_hospital(1), _hospital(2)]})
    with pytest.raises(etl.EicuError, match="duplicate-stay-id"):
        etl.build_raw(d2, verbose=False)


def test_a_null_token_that_is_not_empty_string_raises(tmp_path):
    """The opposite direction of the -1 gate (E-15).

    A Postgres text-format re-export writes \\N for NULL. Every allowlisted
    APACHE numeric then parses as unparseable: all 43 parents go 100% NaN, all
    43 __missing siblings go constant at 1.0, and model.SD_REL_TOL zeroes 86 of
    161 coefficients. Unguarded, build_raw succeeds with an empty warnings
    list, so a certificate gets issued about a model that saw no physiology.
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
    """The E-15 gate covers the patient numerics too, not only aps_ and apv_.

    Unguarded, \\N in admissionweight flows silently: the column goes constant
    at the imputation fallback and the warnings list is unchanged. The same
    token in hospitaladmitoffset, the SS4 first-stay tie-breaker, changes which
    stays enter the cohort with no trace in the attrition ledger.

    Refs: audit E-22, arrival-day audit (2026-07-31).
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
    """E-21 leg 1: a join-key format artifact raises, never silently unlinks.

    A pandas int64 -> float64 to_csv round-trip writes patientunitstayid as
    '141258.0'; scientific notation is the same trap. _maybe_int returns None
    and the row is skipped unread. Every aps_ column then collapses to the
    imputation fallback with the E-15 gate blind (no cell was ever read) and
    the E-9 gate reporting gate_applies=false -- the end state
    unrecognised-null-token warns about, through a door with no gate on it.

    Refs: arrival-day audit (2026-07-31).
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
    """E-21 leg 2: an unlinked APACHE block aborts once E-9 is evaluable.

    The keys are shifted so nothing joins while every row count stays intact,
    the route EICU_REFERENCE_ROW_COUNTS cannot see by construction. Unguarded,
    this certifies with 89 of 161 columns constant and a warnings list shorter
    than the clean corpus's. The same corpus with the keys pointing home must
    build: the gate is keyed on the join, not the scale.
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

    The tiny single-trap corpora above ship empty APACHE tables legitimately
    and must keep building, so the gate arms only at
    n_cohort >= EICU_MIN_OUTCOME_STRATUM -- the scale at which E-9 becomes
    evaluable and total absence would otherwise bypass it.
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

    # the apache-linked escape is not the remedy here: with zero linked stays
    # that arm has an empty cohort, and the honest failure is empty-cohort
    with pytest.raises(etl.EicuError, match="empty-cohort"):
        etl.build_raw(d, arm="apache-linked", verbose=False)


def test_read_boundary_failures_are_typed_and_name_the_table(tmp_path,
                                                             mock_small):
    """Every boundary rejection is a typed error with a reason tag (E-14).

    Untyped, a non-UTF-8 byte escapes as a bare UnicodeDecodeError whose
    "position N" is a decode-buffer offset, and a partial unzip of the multi-GB
    download as a bare EOFError. Neither names the table or the path, so the
    operator cannot tell which of five files failed.
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

    # both tags are in the module's closed reason-tag vocabulary
    for tag in ("undecodable-table", "truncated-table"):
        assert tag in etl.EicuError.__doc__


def test_preflight_profiles_through_an_unknown_outcome_level(tmp_path,
                                                             mock_small):
    """Preflight must not be aborted by the drift it exists to report (E-16).

    One row of 9000 re-cased to 'EXPIRED' is a plausible re-export. Raising
    unknown-outcome-level from inside _select_cohort's row loop discards every
    value count already accumulated, so the operator gets the token but no
    count, no site distribution, no ledger and no EICU_preflight.json at all.
    build_raw's own raise is unchanged.
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

    # preflight completes and reports the token, its count, and the raise
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
    """The mandatory first command must not abort on a correct extract (E-13).

    Counting n_uniquepid post-filter and comparing it against
    EICU_REFERENCE_PATIENTS = 139367, the pre-filter published total, lands
    ~1.7% low: ~1751 stays carry a blank outcome, and at 1.44 stays per patient
    most of those lose every stay. preflight(expect_reference=True) then aborts
    and writes no artifact. Here the constants are re-pinned to the mock's own
    whole-table values, so only the estimator can disagree.
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

    pf = etl.preflight(d, expect_reference=True, verbose=False)   # must not raise
    assert pf["reference_check"]["ok"] is True
    assert pf["reference_check"]["mismatches"] == []
    # the identity counts are the raw ones; the cohort counts are separate and
    # are allowed to be smaller, which is the distinction that matters here
    assert pf["patient"]["n_uniquepid"] == len(uids)
    assert pf["patient"]["n_hospitals"] == len(sites)
    assert pf["patient"]["n_uniquepid_cohort"] < pf["patient"]["n_uniquepid"]


def test_header_case_verdict_is_pinned_per_table_for_both_mock_modes(
        tmp_path_factory, mock_small):
    """A fully camelCase header must not read as 'mixed' (E-17).

    Requiring every name to carry an upper-case character forces 'mixed' on
    four of the five tables, because of single-token names like age, gender and
    urine. But 'mixed' reads as "some columns were re-cased and some were not",
    a materially different diagnosis, in exactly the direction T-6 exists to
    detect. So the verdict is pinned per table.
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
    """The fio2 windows are lower-closed (E-18).

    fio2 == 0.21, equivalently 21, is room air: the modal value of a
    ventilation-linked column. A lower-open window discards it as missing and
    buries the loss in a unit_conversions counter. Ventilation status is
    site-correlated, so that turns the commonest valid value into exactly the
    informative-missingness channel this protocol undertakes to guard.
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
    # the room-air conversions are counted, so the decision stays visible
    conv = meta["unit_conversions"]
    assert conv.get("aps_fio2:room-air-fraction") == 1
    assert conv.get("aps_fio2:room-air-percent") == 1
    assert not any(k.endswith(":at-window-floor") for k in conv)


# ================================= 2026-09-04 fix pass: the LOS diagnostic ===
# unitdischargeoffset stays on the denylist. It is read twice as a diagnostic
# -- into preflight counts and into a row-aligned side array on the cohort
# object -- and never becomes a column, an artifact, or a stay-keyed record.

def test_preflight_los_window_counts_stays_and_deaths_before_hour_24(
        mock_small):
    pf = etl.preflight(mock_small["dir"], verbose=False)
    assert set(pf) == PREFLIGHT_KEYS                 # no new top-level key
    los = pf["apache_absent_los"]
    # the old strata keep their frozen keys and gain the two appended counts
    for tag in ("aps_absent", "aps_present", "aps_absent_positive"):
        block = los[tag]
        assert list(block)[:7] == ["n", "min", "q1", "median", "q3", "max",
                                   "mean"]
        assert list(block)[7:] == ["n_lt_24h", "frac_lt_24h"]
        assert 0 <= block["n_lt_24h"] <= block["n"]
        if block["n"]:
            assert abs(block["frac_lt_24h"] - block["n_lt_24h"] / block["n"]) < 1e-6
        else:
            assert block["frac_lt_24h"] is None
    win = los["los_window"]
    assert win["threshold_hours"] == etl.EICU_LOS_WINDOW_HOURS == 24.0
    assert set(win) == {"threshold_hours", "what", "cohort", "deaths",
                        "n_negative_offset_cohort"}
    cohort, deaths = win["cohort"], win["deaths"]
    # the whole cohort is the union of the two APACHE strata
    assert cohort["n"] == los["aps_absent"]["n"] + los["aps_present"]["n"]
    assert cohort["n"] + los["n_los_unavailable"] == \
        _attrition(pf)["primary-cohort"]
    assert deaths["n"] <= cohort["n"]
    assert deaths["n_lt_24h"] <= cohort["n_lt_24h"]
    assert los["aps_absent_positive"]["n"] <= deaths["n"]
    assert isinstance(win["n_negative_offset_cohort"], int)
    # every value is a scalar: the block is aggregate by shape
    for block in (cohort, deaths):
        assert all(v is None or isinstance(v, (int, float)) for v in block.values())
    run_eicu.assert_aggregate_only(run_eicu._json_ready(los), "apache_absent_los")


def test_build_raw_carries_a_diagnostic_los_side_array_never_a_column(
        pipeline_small):
    meta, names, x_raw = (pipeline_small["meta"], pipeline_small["names"],
                          pipeline_small["x_raw"])
    los = meta["los_hours"]
    assert isinstance(los, np.ndarray) and los.dtype == np.float64
    assert los.shape == (meta["n"],) == (x_raw.shape[0],)
    assert "los_hours" not in names and "unitdischargeoffset" not in names
    assert names == list(etl.FEATURE_NAMES)          # the feature contract holds
    assert len(names) == etl.EICU_N_FEATURES
    finite = np.isfinite(los)
    assert finite.any()
    # the mock's stays end: some inside the first day, some after
    assert (los[finite] < etl.EICU_LOS_WINDOW_HOURS).any()
    assert (los[finite] >= etl.EICU_LOS_WINDOW_HOURS).any()
    # the array is row-aligned with y: the deaths' LOS is a subset by mask
    y = pipeline_small["y_bool"]
    assert y.shape == los.shape
    # and the aggregate gate refuses it whole, before the DUA has to
    if los.size > run_eicu.EICU_MAX_OUTPUT_LEN:
        with pytest.raises(etl.EicuError, match="record-level-output"):
            run_eicu.assert_aggregate_only({"los_hours": los}, "leak-probe")


def test_build_raw_subsets_the_los_side_array_with_the_arm(mock_small):
    """The apache-linked arm keeps fewer stays; the side array follows."""
    x_p, _n, meta_p = etl.build_raw(mock_small["dir"], verbose=False)
    x_l, _n, meta_l = etl.build_raw(mock_small["dir"], arm="apache-linked",
                                    verbose=False)
    assert meta_p["los_hours"].shape == (x_p.shape[0],)
    assert meta_l["los_hours"].shape == (x_l.shape[0],)
    assert x_l.shape[0] < x_p.shape[0]
    # the linked arm keeps the stays with BOTH day-1 rows; the side array is
    # exactly those stays' values, in order
    keep = (np.asarray(meta_p["aps_present"], dtype=bool)
            & np.asarray(meta_p["apv_present"], dtype=bool))
    np.testing.assert_array_equal(meta_l["los_hours"],
                                  meta_p["los_hours"][keep])
