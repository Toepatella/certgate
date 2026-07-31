"""SPEC section "Real-data protocol (eICU-CRD v2.0)": the certification runner.

Two modes, one CLI. PREFLIGHT profiles an extract and writes the a-priori
predictions WITHOUT building features and WITHOUT certifying anything -- the
pre-registration ordering is the whole point, so the predictions must exist on
disk before any certificate does. The CERTIFICATION run builds the cohorts
through ``certgate.validate.from_raw``, asserts site-disjointness, and drives
``certgate.pipeline.run_certgate`` over BOTH target-pool arms -- 24
single-hospital pools (K == 1) and one pooled multi-site pool (K == 24) -- for
each of ``--replicates`` independent by-site re-splits.

Compliance is enforced in CODE, not in a comment: ``assert_aggregate_only``
sits on every write (PhysioNet Credentialed Health Data License 1.5.0 + DUA
1.5.0 restrict derived record-level artifacts, and ``experiments/out/`` is a
TRACKED directory). Nothing keyed by ``patientunitstayid`` or ``uniquepid``
ever reaches the output directory.

CLI::

    python -m experiments.run_eicu --data DIR [--preflight] [--out experiments/out]
            [--arm primary|apache-complete] [--replicates N] [--quick]
            [--no-reference-check]

``--data`` is required in both modes. ``--preflight`` short-circuits after the
profile. ``--replicates`` defaults to 1; the validity-replication arm is
``--replicates 20`` (= ``eicu_etl.EICU_SPLIT_REPLICATES``). ``--quick`` caps
replicates at 2 and skips figures.

Deliberate deviations from the ``run_synthetic`` house conventions, each argued:

  * ``_rm_on_pool`` and ``_per_site_exceed_frac`` are IMPORTED from
    ``run_synthetic``, never re-implemented. They are the exact quantities the
    paper's synthetic numbers are computed with; a private copy would let the
    real-data numbers drift from the synthetic ones silently.
  * eICU tables are written ASCII-STRICT (``_write_table``). eICU categorical
    literals may carry non-ASCII; a crash is correct and a mojibake cell is not.
  * The summary is ``EICU-SUMMARY.md`` and NEVER ``summary.md``:
    ``run_synthetic._existing_summary_blocks`` matches ``^## (E\\d)`` -- a
    SINGLE digit -- so an ``## EICU`` section placed there would be
    unparseable and silently clobbered by the next partial ``--only`` rerun.
  * Structural outcomes are read from ``report["reason"]`` / ``row["status"]``,
    never from exception-or-not: ``run_certgate`` RETURNS a gated report
    (``insufficient-clusters``, ``pool-too-small``) rather than raising, and
    code that only catches exceptions reads a gated run as a successful
    certification of nothing (threat T-12).
"""

import argparse
import csv
import datetime
import hashlib
import json
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")                       # headless: no interactive display
import matplotlib.pyplot as plt
import numpy as np

from certgate.constants import (SEED, ALPHA_LADDER, DELTA, M_INFLUENCE,
                                MIN_ANSWERABLE, MIN_CAL_CLUSTERS)
from certgate.validate import (from_raw, assert_site_disjoint, Cohort,
                               CohortError)
from certgate.model import fit_head
from certgate.harness import hard_violation
from certgate.pipeline import run_certgate
from certgate.report import render_text, provenance
from certgate.explain import cohort_abstention_profile
from experiments import eicu_etl as etl
from experiments.run_synthetic import (_rm_on_pool, _per_site_exceed_frac,
                                       _write_csv, _rate)

# ``_write_csv`` is bound here because the SPEC's import surface names it; the
# eICU tables deliberately do NOT use it (see ``_write_table``: locale-default
# encoding would write a mojibake cell where a crash is the correct outcome).
_HOUSE_CSV_WRITER = _write_csv

EICU_OUT_PREFIX = "EICU"
EICU_MAX_OUTPUT_LEN = 512        # > 208 sites, < any record-level array
EICU_FORBIDDEN_OUT_KEYS = ("stay_id", "patient_id", "admission_id", "site_raw",
                           "y_raw", "answered_mask", "x", "site_id",
                           "comparator_predicted_mortality", "split_idx")
EICU_SUMMARY_SECTIONS = ("EICU-PREFLIGHT", "EICU-PREDICTIONS",
                         "EICU-POOLED", "EICU-PERSITE", "EICU-COMPARATOR")

# Executable forms of the pre-declared failure criteria (EICU-PROTOCOL section
# 10). They are literals HERE rather than prose in a paper so that a run
# cannot quietly skip the alarm registered against it before the data arrived.
EICU_FB_MIN_COVERAGE = 0.20      # F-B: a certificate at 5% coverage is a decline in a hat
EICU_FD_COVERAGE_ALARM = 0.90    # F-D leg 3: alpha=0.05 + coverage > this ...
EICU_FD_RM_ALARM = 0.01          # ... + fresh-pool R_M under this = LEAK ALARM
EICU_FE_MIN_SITES = 200          # F-E: below this the estimand's population moved

# F-D legs 1 and 2 (2026-07-31 audit, E-10). The old F-D was conditioned on
# alpha == ALPHA_LADDER[0] AND coverage > 0.90 AND R_M < 0.01, so a leak that
# certified alpha = 0.10 at coverage 0.86 passed underneath it -- demonstrated
# in-harness with outcome-correlated APACHE-row absence. These two legs depend
# on NEITHER alpha NOR coverage, and both are computed every replicate on the
# real extract rather than only inside pytest.
EICU_LEAK_AUC_CEILING = 0.90      # APACHE-IVa, a purpose-built day-1 score, reaches
                                  # ~0.87 on hospital mortality in eICU; a 161-column
                                  # logistic head that beats this FROM THE SAME INPUTS
                                  # is a leak before it is a result
EICU_LEAK_ABLATION_MAX_DROP = 0.05
                                  # ablating the 49 missingness/presence columns must
                                  # not cost more than this much AUC. Measured on the
                                  # mock: clean -0.016, outcome-correlated absence at
                                  # p=0.30 +0.082, at p=0.75 +0.248
EICU_COVERAGE_BANDS = (0.0, 0.2, 0.5, 0.8, 1.0)   # APACHE per-site coverage bands
EICU_TOP_GAP_FEATURES = 10       # abstention_gap_ranking depth (settles P4)
# apachePredVar treatment/intervention flags whose measurement TIMING relative
# to the outcome cannot be cited to a source (2026-07-31 audit, E-19).
# `activetx` encodes active treatment versus comfort measures -- a decision made
# DURING the stay and adjacent to death by definition. They stay on the
# allowlist ONLY as long as `outcome_screen` clears them, and their univariate
# AUC is written to EICU_diagnostics.json every run so the question is answered
# from data rather than from a DDL comment.
EICU_TIMING_UNVERIFIED = ("activetx", "thrombolytics", "graftcount",
                          "electivesurgery", "ventday1", "oobventday1",
                          "oobintubday1", "ima", "midur")
EICU_PALETTE = ("#4477aa", "#cc6677", "#ee8866", "#228833", "#aa3377",
                "#66ccee")

_SUMMARY_BLOCK_RE = re.compile(r"^## (EICU-[A-Z]+)[^\n]*\n(```json\n.*?\n```)",
                               re.S | re.M)


# ------------------------------------------------------- compliance gate ---

def assert_aggregate_only(obj, where) -> None:
    """Recursively refuse record-level data on the way OUT (SPEC "Real-data
    protocol"; threat T-17).

    Raises ``EicuError`` (``reason=record-level-output``) if ``obj`` contains
    any ``EICU_FORBIDDEN_OUT_KEYS`` key, or any list/tuple/ndarray longer than
    ``EICU_MAX_OUTPUT_LEN``. EVERY write in this module goes through it.

    The length cap exists to catch a per-RECORD array smuggled into a payload;
    it is applied to each CSV ROW rather than to a row LIST, because the number
    of rows is itself an aggregate quantity (replicates x hospitals x rungs
    legitimately exceeds 512 at ``--replicates 20``) while any single cell that
    carries 512+ values is a record-level array by construction.
    """
    stack = [(obj, str(where))]
    while stack:
        node, path = stack.pop()
        if isinstance(node, dict):
            for k, v in node.items():
                key = str(k)
                if key in EICU_FORBIDDEN_OUT_KEYS:
                    raise etl.EicuError(
                        f"run_eicu.assert_aggregate_only: {path} carries the "
                        f"record-level key {key!r}, which the DUA forbids in a "
                        f"derived artifact (reason=record-level-output)")
                stack.append((v, f"{path}.{key}"))
        elif isinstance(node, np.ndarray):
            if int(node.size) > EICU_MAX_OUTPUT_LEN:
                raise etl.EicuError(
                    f"run_eicu.assert_aggregate_only: {path} is an array of "
                    f"{node.size} values, over the aggregate cap "
                    f"{EICU_MAX_OUTPUT_LEN} -- record-level data must never "
                    f"reach the output directory "
                    f"(reason=record-level-output)")
        elif isinstance(node, (list, tuple, set, frozenset)):
            if len(node) > EICU_MAX_OUTPUT_LEN:
                raise etl.EicuError(
                    f"run_eicu.assert_aggregate_only: {path} is a sequence of "
                    f"{len(node)} values, over the aggregate cap "
                    f"{EICU_MAX_OUTPUT_LEN} -- record-level data must never "
                    f"reach the output directory "
                    f"(reason=record-level-output)")
            for i, v in enumerate(node):
                stack.append((v, f"{path}[{i}]"))


def _json_ready(obj):
    """JSON-serialisable projection of a payload (SPEC report.py's V25 rule).

    numpy scalars/arrays become python; tuples and sets become lists (sets
    SORTED -- an unsorted set would make the artifact non-deterministic across
    interpreter runs); non-finite floats become ``None``, so every artifact is
    STRICT json. ``None`` for uncomputable, never ``0.0`` and never ``NaN``.
    """
    if isinstance(obj, dict):
        return {(k if isinstance(k, str) else str(k)): _json_ready(v)
                for k, v in obj.items()}
    if isinstance(obj, np.ndarray):
        return [_json_ready(v) for v in obj.tolist()]
    if isinstance(obj, (set, frozenset)):
        return [_json_ready(v) for v in sorted(obj, key=str)]
    if isinstance(obj, (list, tuple)):
        return [_json_ready(v) for v in obj]
    if isinstance(obj, np.generic):
        return _json_ready(obj.item())
    if isinstance(obj, float):
        return obj if np.isfinite(obj) else None
    return obj


def _write_json(path, payload, where):
    """Gate then write one JSON artifact (indent=2, deterministic key order)."""
    ready = _json_ready(payload)
    assert_aggregate_only(ready, where)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(ready, fh, indent=2)
        fh.write("\n")


def _write_table(path, rows, fieldnames, where):
    """Write one eICU CSV, ASCII-STRICT and gated row by row.

    Deliberate deviation from ``run_synthetic._write_csv`` (which uses the
    locale default, cp1252 on this host): eICU categorical literals may carry
    non-ASCII, and cp1252 would encode them into a cell that reads back as
    mojibake instead of failing. All eICU cell content is ASCII by construction
    (site labels, numbers, reason tags; categorical levels never reach a cell),
    so a non-ASCII cell means the protocol was violated upstream. The cells are
    validated BEFORE the file is opened, so the failure names the offending
    column instead of raising mid-stream and leaving a truncated table.
    """
    for i, row in enumerate(rows):
        assert_aggregate_only(row, f"{where}[{i}]")
        for k in fieldnames:
            v = row.get(k)
            if isinstance(v, str) and not v.isascii():
                raise etl.EicuError(
                    f"run_eicu._write_table: {where} row {i} column {k!r} "
                    f"carries non-ASCII content {v!r} -- eICU cells are ASCII "
                    f"by construction, so this is an upstream protocol "
                    f"violation, not an encoding preference "
                    f"(reason=non-ascii-output)")
    with open(path, "w", newline="", encoding="ascii") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow({k: _csv_cell(row.get(k)) for k in fieldnames})


def _csv_cell(v):
    """One CSV cell. ``None`` -> empty (the empty-bin discipline survives the
    round trip); numpy scalars -> python; non-finite floats -> empty, never the
    literal ``nan`` token that a downstream reader would parse as a number."""
    if v is None:
        return ""
    if isinstance(v, np.generic):
        v = v.item()
    if isinstance(v, float) and not np.isfinite(v):
        return ""
    return v                    # bools render True/False, as every house CSV does


# --------------------------------------------------------------- helpers ---

def _say(verbose, msg, err=False):
    """Console line with the literal ``[eicu] `` prefix (SPEC "Real-data protocol")."""
    if verbose or err:
        print(f"[eicu] {msg}", file=(sys.stderr if err else sys.stdout))


def _alpha_key(alpha):
    """Rung key as a STRING (``"0.05"`` / ``"0.1"``), matching
    ``diagnostic["feasibility"]``: a float dict key survives ``json.dump`` only
    by silent stringification, and ``str(0.10)`` is ``"0.1"``."""
    return str(float(alpha))


def _site_sort_key(label):
    """Deterministic, human-readable ordering for ``hosp-<int>`` labels: the
    numeric suffix when it parses, else the raw string (never hash order)."""
    text = str(label)
    if text.startswith(etl.EICU_SITE_PREFIX):
        tail = text[len(etl.EICU_SITE_PREFIX):]
        if tail.lstrip("+-").isdigit():
            return (0, int(tail), "")
    return (1, 0, text)


def _row_for(report, alpha):
    """The certified-tier row for one rung, or ``None`` on a gated report."""
    for r in report["certified"]:
        if r["alpha"] == alpha:
            return r
    return None


def _reasons_text(reasons):
    """``{mode: reason}`` -> a compact ASCII cell, deterministic by mode name."""
    if not reasons:
        return None
    return "|".join(f"{m}:{r or 'declined'}" for m, r in sorted(reasons.items()))


def _noncontributing_text(mode_outcomes):
    """Why a mode did NOT back the deployed threshold, on a CERTIFIED row.

    On real data a silent BBSE non-contribution is the interesting signal
    (report.py ``_combine_alpha``'s ``mode_outcomes``, fixture audit
    2026-07-25): a certified row whose BBSE arm declined must still say so, or
    prediction P3 is unsettleable from the released tables.
    """
    if not mode_outcomes:
        return None
    parts = [f"{m}:{o}" for m, o in sorted(mode_outcomes.items())
             if o != "covering"]
    return "|".join(parts) if parts else None


def _eval_rung(head, report, alpha, pool_x, pool_y):
    """Score one rung of one report against the ORACLE labels of its pool.

    The eICU analogue of ``run_synthetic._cert_eval``, extended with the fields
    the eICU tables carry (``tau_idx``, ``deploy_mode``, ``modes``, and the
    non-contributing-mode text). Structural gates are read from
    ``report["reason"]`` and rung outcomes from ``row["status"]`` -- a
    ``tier == "certified"`` row can still be ``status == "declined"``.
    """
    out = dict(certified=False, tau=None, tau_idx=None, deploy_mode=None,
               modes=None, coverage=None, n_answered=0, answered_err_rate=None,
               hard=False, decline_reason=report.get("reason"))
    row = _row_for(report, alpha)
    if row is None:                      # gated exit: reason already carried
        return out
    if row["status"] != "certified":
        out["decline_reason"] = _reasons_text(row.get("reasons", {}))
        return out
    tau = float(row["tau"])
    n_pool = int(np.asarray(pool_x).shape[0])
    ans = head.score(pool_x) >= tau
    err = head.predict(pool_x) != pool_y
    n_ans = int(ans.sum())
    out.update(certified=True, tau=round(tau, 6), tau_idx=int(row["tau_idx"]),
               deploy_mode=row["deploy_mode"], modes="|".join(row["modes"]),
               coverage=_rate(n_ans, n_pool), n_answered=n_ans,
               answered_err_rate=_rate(int(err[ans].sum()), n_ans),
               hard=bool(hard_violation(err[ans], alpha)),
               decline_reason=_noncontributing_text(row.get("mode_outcomes")))
    return out


def _auc(scores, y):
    """Rank (Mann-Whitney) AUC with tie-averaged ranks; ``None`` when either
    class is absent. Deterministic (``mergesort``) and dependency-free -- the
    eICU path may not reach for a sklearn metric it does not otherwise need."""
    s = np.asarray(scores, dtype=np.float64)
    y = np.asarray(y, dtype=bool)
    n = int(s.shape[0])
    n1 = int(y.sum())
    n0 = n - n1
    if n1 == 0 or n0 == 0:
        return None
    order = np.argsort(s, kind="mergesort")
    s_sorted = s[order]
    ranks = np.empty(n, dtype=np.float64)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and s_sorted[j + 1] == s_sorted[i]:
            j += 1
        ranks[order[i:j + 1]] = 0.5 * (i + j) + 1.0
        i = j + 1
    return float((ranks[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def _missingness_columns(feature_names):
    """Indices of the 49 MISSINGNESS/PRESENCE columns (43 ``__missing``
    siblings + ``age__missing`` etc. + the two presence flags), and the rest.

    These are the channel E-9 identified as jointly site- AND
    outcome-informative: the day-1 APACHE window does not close for a stay that
    ends because the patient died, so whole-row absence is a partial outcome
    proxy with no column name. Ablating them is the leak probe with the power
    the AUC ceiling alone does not have.
    """
    miss = [j for j, n in enumerate(feature_names)
            if n.endswith("__missing") or n in ("aps_present", "apv_present")]
    keep = [j for j in range(len(feature_names)) if j not in set(miss)]
    return miss, keep


def _leak_probe(train, cal, feature_names):
    """The alpha- and coverage-INDEPENDENT leak alarm (F-D legs 1 and 2, E-10).

    Fits the head on ``train`` and scores it OUT OF SAMPLE on the site-disjoint
    calibration split, then refits with the missingness/presence block ablated
    and reports the AUC it costs. Both numbers reach ``EICU_pooled.csv`` and
    ``EICU_diagnostics.json``, so the check exists on the real extract, where
    the mock's Bayes-optimal ceiling does not apply and only a runtime number
    can bound it.
    """
    out = dict(head_auc_oos=None, head_auc_ablated=None, ablation_drop=None,
               auc_ceiling=EICU_LEAK_AUC_CEILING,
               ablation_max_drop=EICU_LEAK_ABLATION_MAX_DROP,
               auc_alarm=False, ablation_alarm=False)
    miss, keep = _missingness_columns(feature_names)
    head = fit_head(train)
    auc = _auc(head.predict_proba(cal.x), cal.y)
    if auc is None:                       # one class only: probe cannot speak
        return out, head
    out["head_auc_oos"] = round(float(auc), 6)
    out["auc_alarm"] = bool(auc > EICU_LEAK_AUC_CEILING)
    if keep:
        sub = Cohort(x=np.ascontiguousarray(train.x[:, keep]), y=train.y,
                     site_id=train.site_id, site_labels=train.site_labels)
        auc_ab = _auc(fit_head(sub).predict_proba(
            np.ascontiguousarray(cal.x[:, keep])), cal.y)
        if auc_ab is not None:
            out["head_auc_ablated"] = round(float(auc_ab), 6)
            drop = float(auc) - float(auc_ab)
            out["ablation_drop"] = round(drop, 6)
            out["ablation_alarm"] = bool(drop > EICU_LEAK_ABLATION_MAX_DROP)
    out["n_ablated_columns"] = len(miss)
    return out, head


def _summary_stats(values):
    """Aggregate-only distribution summary (never the values themselves)."""
    v = np.asarray([x for x in values if x is not None and np.isfinite(x)],
                   dtype=np.float64)
    if v.size == 0:
        return dict(n=0, mean=None, sd=None, p10=None, p50=None, p90=None,
                    min=None, max=None)
    q10, q50, q90 = (float(x) for x in np.quantile(v, [0.10, 0.50, 0.90]))
    return dict(n=int(v.size), mean=round(float(v.mean()), 6),
                sd=round(float(v.std(ddof=0)), 6), p10=round(q10, 6),
                p50=round(q50, 6), p90=round(q90, 6),
                min=round(float(v.min()), 6), max=round(float(v.max()), 6))


# -------------------------------------------------------------- preflight ---

def _preflight_blocks(pf):
    """Derive the EICU-PREFLIGHT + EICU-PREDICTIONS summary sections.

    The predictions block is written IN PREFLIGHT MODE, before any certificate
    exists (threat T-18): a pre-registration that could be edited after the
    data landed is not a pre-registration.
    """
    if not pf:
        return {}
    tables = pf.get("tables") or {}
    patient = pf.get("patient") or {}
    attrition = pf.get("attrition") or []
    by_step = {d.get("step"): d for d in attrition}
    drift = pf.get("categorical_drift") or {}
    preflight_block = {
        "data_dir_basename": os.path.basename(str(pf.get("data_dir", ""))),
        "tables": {t: {"rows": v.get("rows"),
                       "reference_rows": v.get("reference_rows"),
                       "rows_match_reference": v.get("rows_match_reference"),
                       "header_case_as_read": v.get("header_case_as_read")}
                   for t, v in tables.items()},
        "n_hospitals": patient.get("n_hospitals"),
        "n_uniquepid": patient.get("n_uniquepid"),
        "n_healthsystemstays": patient.get("n_healthsystemstays"),
        "attrition": attrition,
        "site_selection": {
            "n_sites_primary_cohort":
                (by_step.get("primary-cohort") or {}).get("n_sites"),
            "n_sites_apache_result_linked":
                (by_step.get("apache-result-linked") or {}).get("n_sites"),
            "note": ("apache-result-linked vs primary-cohort is the headline "
                     "site-selection statistic (threat T-4): restricting to "
                     "APACHE-covered stays MOVES the site population the "
                     "certificate's site-population-average estimand refers "
                     "to. The primary arm never applies it."),
        },
        "categorical_drift": {c: {"other_share": d.get("other_share"),
                                  "exceeds_cap": d.get("exceeds_cap")}
                              for c, d in drift.items()},
        "cross_site_patients": pf.get("cross_site_patients"),
        "reference_check": pf.get("reference_check"),
        "sentinel_site_dispersion_reported": bool(
            pf.get("sentinel_site_dispersion")),
        "warnings": pf.get("warnings") or [],
        "certifies_nothing": True,
    }
    return {"EICU-PREFLIGHT": preflight_block,
            "EICU-PREDICTIONS": {"registered_before_any_certificate": True,
                                 "predictions": pf.get("predictions")}}


def run_preflight(data_dir, out, *, reference_check=True, verbose=True) -> dict:
    """Profile an extract and write the pre-registration -- certifying NOTHING.

    ``etl.preflight`` streams all five tables and returns an AGGREGATE-ONLY
    profile; this wrapper gates it, writes ``EICU_preflight.json`` and the
    ``EICU-PREFLIGHT`` / ``EICU-PREDICTIONS`` sections of ``EICU-SUMMARY.md``,
    and returns the preflight dict UNCHANGED (its key set is frozen by the ETL
    contract, so nothing is added to it here).

    ``reference_check=True`` turns a row-count / site-count / patient-count
    mismatch against ``EICU_REFERENCE_*`` into an ``EicuError``
    (``reason=reference-row-count-mismatch``) -- pass it for the real extract,
    drop it (``--no-reference-check``) for the mock corpus. That raise is a
    pre-declared PROTOCOL failure (F-C): the run stops and writes no numbers.
    """
    os.makedirs(out, exist_ok=True)
    _say(verbose, f"preflight on {data_dir} "
                  f"(reference_check={bool(reference_check)}) -- profiling "
                  f"only, no features and no certificates")
    pf = etl.preflight(data_dir, expect_reference=bool(reference_check),
                       verbose=verbose)
    assert_aggregate_only(_json_ready(pf), "preflight")
    _write_json(os.path.join(out, f"{EICU_OUT_PREFIX}_preflight.json"), pf,
                "EICU_preflight.json")
    for w in (pf.get("warnings") or []):
        _say(verbose, str(w), err=True)          # the ETL tags its own warnings
    _write_summary(out, _preflight_blocks(pf),
                   mode="PREFLIGHT", replicates=0, arm=None,
                   data_sha=_data_sha(data_dir))
    _say(verbose, f"preflight wrote {EICU_OUT_PREFIX}_preflight.json and the "
                  f"EICU-PREFLIGHT / EICU-PREDICTIONS sections to {out}")
    return pf


# ---------------------------------------------------------- certification ---

def _reference_check(meta):
    """Cheap extract-identity check from the attrition ledger (threat T-6).

    The full five-table check belongs to ``preflight``; here the ledger's first
    step already carries the raw ``patient`` row count and hospital count, so
    a wrong download or a v2.0.1 extract is visible for free. It is REPORTED,
    not raised: ``run_certification``'s signature has no off-switch, and the
    mock corpus legitimately fails it.
    """
    ledger = {d.get("step"): d for d in (meta.get("attrition") or [])}
    raw = ledger.get("raw-unit-stays") or {}
    n_stays, n_sites = raw.get("n_stays"), raw.get("n_sites")
    matches = (n_stays == etl.EICU_REFERENCE_UNIT_STAYS
               and n_sites == etl.EICU_REFERENCE_SITES)
    return dict(n_raw_stays=n_stays, n_raw_sites=n_sites,
                expected_stays=etl.EICU_REFERENCE_UNIT_STAYS,
                expected_sites=etl.EICU_REFERENCE_SITES,
                matches_reference=bool(matches),
                note=("a mismatch means this is NOT eICU-CRD v2.0 as released "
                      "(wrong download, a re-zip, or the mock corpus); "
                      "preflight --no-reference-check is the mock path, and "
                      "expect_reference=True is where the mismatch RAISES"))


def _attrition_rows(meta, arm, warnings):
    """Attrition ledger rows in the FROZEN step order (SPEC ``EICU_ATTRITION_STEPS``)."""
    ledger = {d.get("step"): d for d in (meta.get("attrition") or [])}
    rows = []
    for step in etl.EICU_ATTRITION_STEPS:
        d = ledger.get(step)
        if d is None:
            warnings.append(f"attrition ledger is missing the frozen step "
                            f"{step!r}")
            continue
        # E-9: n_positive/prevalence per step. A ledger that records only
        # n_stays cannot show the prevalence collapse at apache-aps-linked,
        # which is the signature of outcome-correlated APACHE absence.
        rows.append(dict(step=step, n_stays=d.get("n_stays"),
                         n_sites=d.get("n_sites"),
                         n_positive=d.get("n_positive"),
                         prevalence=(None if d.get("prevalence") is None
                                     else round(float(d["prevalence"]), 6)),
                         arm=arm))
    for step in ledger:
        if step not in etl.EICU_ATTRITION_STEPS:
            warnings.append(f"attrition ledger carries the unfrozen step "
                            f"{step!r}")
    return rows


def _site_coverage(meta):
    """Per-site APACHE coverage and per-site missingness, from the CONTRACTED
    arrays only (``site_raw``, ``aps_present``, ``apv_present``).

    Computed here rather than read from ``meta['site_meta']`` so the numbers in
    the per-site table and the numbers in the dispersion diagnostic come from
    one code path. Site-informative missingness is the covariate-shift channel
    CertGate v2 scope-cut (threat T-3): it must be MEASURED, never imputed away.
    """
    site_raw = np.asarray([str(s) for s in meta["site_raw"]])
    aps = np.asarray(meta["aps_present"], dtype=bool)
    apv = np.asarray(meta["apv_present"], dtype=bool)
    labels, inv = np.unique(site_raw, return_inverse=True)
    n = np.bincount(inv, minlength=labels.size).astype(np.float64)
    a = np.bincount(inv, weights=aps.astype(np.float64), minlength=labels.size)
    v = np.bincount(inv, weights=apv.astype(np.float64), minlength=labels.size)
    denom = np.maximum(n, 1.0)
    return {str(lab): dict(n_stays=int(n[i]),
                           aps_coverage=round(float(a[i] / denom[i]), 6),
                           apv_coverage=round(float(v[i] / denom[i]), 6))
            for i, lab in enumerate(labels.tolist())}


def _site_missing_share(x_raw, meta):
    """Per-site mean share of NaN across the IMPUTABLE feature columns.

    The dispersion of this quantity across hospitals is the site-informative
    -missingness diagnostic the protocol registers as threat T-3; it is
    measured on the RAW matrix, before ``impute`` erases the evidence.
    """
    cols = np.asarray(meta.get("imputable_cols") or [], dtype=int)
    site_raw = np.asarray([str(s) for s in meta["site_raw"]])
    labels, inv = np.unique(site_raw, return_inverse=True)
    if cols.size == 0:
        return {str(lab): 0.0 for lab in labels.tolist()}
    per_record = np.isnan(x_raw[:, cols]).mean(axis=1)
    n = np.bincount(inv, minlength=labels.size).astype(np.float64)
    s = np.bincount(inv, weights=per_record, minlength=labels.size)
    denom = np.maximum(n, 1.0)
    return {str(lab): round(float(s[i] / denom[i]), 6)
            for i, lab in enumerate(labels.tolist())}


def _coverage_bands(coverage_by_site, key):
    """Site counts per APACHE-coverage band + the zero-coverage hospital count
    (threat T-4: those hospitals are what an APACHE filter would delete)."""
    vals = np.asarray([d[key] for d in coverage_by_site.values()],
                      dtype=np.float64)
    bands = []
    edges = EICU_COVERAGE_BANDS
    for lo, hi in zip(edges[:-1], edges[1:]):
        sel = (vals > lo) & (vals <= hi) if lo > 0.0 else (vals <= hi)
        bands.append(dict(band=f"({lo},{hi}]" if lo > 0.0 else f"[0,{hi}]",
                          n_sites=int(sel.sum())))
    return dict(bands=bands, n_sites=int(vals.size),
                n_sites_zero=int((vals <= 0.0).sum()),
                n_sites_below_20pct=int((vals < 0.2).sum()),
                summary=_summary_stats(vals.tolist()))


def _hospital_strata(data_dir, warnings):
    """Site-constant hospital covariates, read from the ``hospital`` table.

    SPEC A.6: ``hospital`` contributes NO FEATURES. ``numbedscategory`` /
    ``teachingstatus`` / ``region`` are site-CONSTANT, so under a site-as-unit
    design their coefficients would be identified from ~75 between-site
    observations rather than ~60k records, and they are the cleanest available
    site proxies. They are read HERE, as strata for the per-site diagnostic
    table only, through the ETL's own contracted reader -- no second CSV
    parser, no undeclared dependency, and the values never touch ``x``.

    Missing or unreadable strata degrade to ``None`` cells plus a warning: they
    are diagnostic, and a diagnostic must not abort a certification run.
    """
    out = {}
    reader = getattr(etl, "read_table", None)
    if reader is None:                   # explicit, so a genuine AttributeError
        warnings.append(                 # raised INSIDE the reader still surfaces
            "eicu_etl exposes no read_table; the per-site hospital strata "
            "(numbedscategory/teachingstatus/region) are reported empty")
        return out
    try:
        for row in reader(data_dir, "hospital"):
            raw = (row.get("hospitalid") or "").strip()
            try:
                key = f"{etl.EICU_SITE_PREFIX}{int(raw)}"
            except (TypeError, ValueError):
                continue
            out[key] = dict(
                numbedscategory=(row.get("numbedscategory") or "").strip()
                or None,
                teachingstatus=(row.get("teachingstatus") or "").strip()
                or None,
                region=(row.get("region") or "").strip() or None)
    except (etl.EicuError, OSError) as e:
        warnings.append(f"hospital strata unavailable for the per-site table "
                        f"({e}); numbedscategory/teachingstatus/region are "
                        f"reported empty rather than guessed at")
    return out


def _site_stratum(meta, site, hospital_strata):
    """The three site-constant covariates for one site, or ``None`` cells.

    The ``hospital`` table is the source of record; ``meta['site_meta']`` is
    consulted second in case a future ETL carries them there. Nothing is
    guessed: a site with no row in either yields empty cells and increments the
    miss count, so an all-empty stratum column is VISIBLE in the diagnostics
    rather than silently blank.
    """
    rec = hospital_strata.get(site)
    if rec is None:
        sm = meta.get("site_meta") or {}
        cand = sm.get(site)
        if isinstance(cand, dict) and any(
                k in cand for k in ("numbedscategory", "teachingstatus",
                                    "region")):
            rec = cand
    if not isinstance(rec, dict):
        return dict(numbedscategory=None, teachingstatus=None, region=None,
                    found=False)
    return dict(numbedscategory=rec.get("numbedscategory"),
                teachingstatus=rec.get("teachingstatus"),
                region=rec.get("region"), found=True)


def _abstention_ranking(head, target_x, tau, feature_names,
                        top=EICU_TOP_GAP_FEATURES):
    """Top abstention drivers at ``tau`` (settles prediction P4).

    Computed with ``explain.cohort_abstention_profile`` at EVERY certified
    rung, not only the operative one the report happens to carry. An empty
    answered or declined population yields an EMPTY ranking, never argsort of
    an all-NaN gap (audit V22 -- that fabricated feature 0 as the top driver).
    """
    ans = head.score(target_x) >= float(tau)
    prof = cohort_abstention_profile(head, target_x, ans)
    order = np.asarray(prof["gap_ranking"], dtype=int).ravel()
    gap = np.asarray(prof["gap"], dtype=np.float64)
    m_ans = np.asarray(prof["mean_abs_phi_answered"], dtype=np.float64)
    m_dec = np.asarray(prof["mean_abs_phi_declined"], dtype=np.float64)
    out = []
    for j in order[:int(top)].tolist():
        out.append(dict(feature=feature_names[j],
                        gap=None if not np.isfinite(gap[j])
                        else round(float(gap[j]), 6),
                        mean_abs_phi_answered=None
                        if not np.isfinite(m_ans[j])
                        else round(float(m_ans[j]), 6),
                        mean_abs_phi_declined=None
                        if not np.isfinite(m_dec[j])
                        else round(float(m_dec[j]), 6)))
    return dict(n_answered=int(prof["n_answered"]),
                n_declined=int(prof["n_declined"]), ranking=out)


def _bbse_block(report):
    """The BBSE outcome for one report, INCLUDING why it declined.

    ``diagnostic["bbse"]`` is ``None`` wholesale on a gated exit and otherwise
    carries the stable key set, so every key is indexable and ``None`` means
    "not computed" rather than KeyError (audit V25).
    """
    d = (report.get("diagnostic") or {}).get("bbse")
    if not d:
        return dict(fitted=False, reason=None, n_target_sites=None,
                    q_target=None, q_ci=None, gap_lo=None, rho_lo=None,
                    rho_hi=None, rho_point=None, n_boot=None)
    return dict(fitted=True, reason=None, n_target_sites=d.get("n_target_sites"),
                q_target=d.get("q_target"), q_ci=d.get("q_ci"),
                gap_lo=d.get("gap_lo"), rho_lo=d.get("rho_lo"),
                rho_hi=d.get("rho_hi"), rho_point=d.get("rho_point"),
                n_boot=d.get("n_boot"))


def _strip_report(report, feature_names):
    """Certificate-level projection of one report: arrays stripped,
    ``answered_mask`` replaced by its ``.sum()`` (threat T-17).

    The key ``answered_mask`` itself does not survive -- it is in
    ``EICU_FORBIDDEN_OUT_KEYS``, so the count is emitted as ``n_answered`` and
    the compliance gate stays a gate rather than a special case.
    """
    diag = dict(report.get("diagnostic") or {})
    prof = diag.get("abstention_profile")
    if prof:
        order = np.asarray(prof["gap_ranking"], dtype=int).ravel()
        gap = np.asarray(prof["gap"], dtype=np.float64)
        diag["abstention_profile"] = dict(
            n_answered=int(prof["n_answered"]),
            n_declined=int(prof["n_declined"]),
            gap_ranking=[dict(feature=feature_names[j],
                              gap=None if not np.isfinite(gap[j])
                              else round(float(gap[j]), 6))
                         for j in order[:EICU_TOP_GAP_FEATURES].tolist()])
    mask = report.get("answered_mask")
    return dict(target_label=report.get("target_label"),
                reason=report.get("reason"),
                certified=report.get("certified"),
                operative=report.get("operative"),
                estimated=report.get("estimated"),
                diagnostic=diag,
                decline_partition=report.get("decline_partition"),
                n_answered=int(np.asarray(mask).sum()) if mask is not None
                else None,
                provenance=report.get("provenance"))


def _build_cohorts(x, y_raw, site_raw, idx, arm, replicate):
    """``from_raw`` for the four splits, then the site-disjointness assertion.

    ``require_both_classes=False`` is used for the TARGET pool ONLY: a single
    held-out hospital may legitimately be all-``Alive`` at ~9% prevalence, and
    that opt-in is the sole sanctioned relaxation. Labels flow as RAW
    two-valued strings so ``coerce_labels`` owns the two-value contract -- a
    hand-built bool array would bypass it.
    """
    cohorts = {}
    for split in ("train", "aux", "cal", "target"):
        sel = np.asarray(idx[split], dtype=int)
        if sel.size == 0:
            raise etl.EicuError(
                f"run_eicu._build_cohorts: split {split!r} is empty at "
                f"arm={arm} replicate={replicate} (reason=empty-cohort)")
        try:
            cohorts[split] = from_raw(
                x[sel], [y_raw[i] for i in sel.tolist()],
                etl.EICU_POSITIVE_LABEL,
                [site_raw[i] for i in sel.tolist()],
                require_both_classes=(split != "target"))
        except CohortError as e:
            raise CohortError(
                f"run_eicu._build_cohorts: split {split!r} (arm={arm}, "
                f"replicate={replicate}) failed the Cohort contract: {e}"
            ) from e
    assert_site_disjoint(train=cohorts["train"], aux=cohorts["aux"],
                         cal=cohorts["cal"])
    return cohorts


def _comparator_row(head, report, alpha, target, comparator_p, replicate):
    """APACHE-IVa comparator on the answered set (aggregate rates only).

    ``predictedhospitalmortality`` is a VARCHAR holding a probability: the ETL
    has already run it through ``float()`` (a string comparison is threat T-9)
    and mapped ``-1`` to NaN. Coverage of that column is SITE-correlated, so
    the comparator is scored on the answered records that carry it, and the
    subset-matched CertGate error is reported beside it in the summary rather
    than compared across different denominators.
    """
    row = dict(replicate=replicate, alpha=alpha, n_answered=0,
               certgate_answered_err=None, apache_iva_brier_answered=None,
               apache_iva_auc_answered=None, n_apache_available=0)
    cert = _row_for(report, alpha)
    if cert is None or cert["status"] != "certified":
        return row, None
    tau = float(cert["tau"])
    ans = head.score(target.x) >= tau
    err = head.predict(target.x) != target.y
    n_ans = int(ans.sum())
    row["n_answered"] = n_ans
    row["certgate_answered_err"] = _rate(int(err[ans].sum()), n_ans)
    p = np.asarray(comparator_p, dtype=np.float64)
    avail = ans & np.isfinite(p)
    n_avail = int(avail.sum())
    row["n_apache_available"] = n_avail
    subset_err = None
    if n_avail:
        y_sub = np.asarray(target.y, dtype=bool)[avail]
        p_sub = p[avail]
        row["apache_iva_brier_answered"] = round(
            float(np.mean((p_sub - y_sub.astype(np.float64)) ** 2)), 6)
        auc = _auc(p_sub, y_sub)
        row["apache_iva_auc_answered"] = (None if auc is None
                                          else round(auc, 6))
        subset_err = _rate(int(err[avail].sum()), n_avail)
    return row, subset_err


def _failure_criteria(pooled_rows, site_counts, n_replicates):
    """The pre-declared failure criteria F-A..F-E, evaluated in code.

    Registered BEFORE the data arrived (EICU-PROTOCOL section 10), so they are
    computed here rather than argued after the fact. F-A is deliberately
    written as a BOUND-SHAPED observation: 20 replicates cannot resolve a
    delta = 0.05 rate, and they share one hospital population, so they are not
    independent draws of the calibration site population.
    """
    ops = {}
    for row in pooled_rows:
        if not row["certified"]:
            continue
        r = row["replicate"]
        if r not in ops or row["alpha"] < ops[r]["alpha"]:
            ops[r] = row
    n_cert = len(ops)
    n_exceed = sum(1 for row in ops.values() if row.get("rm_exceed"))
    exceed_rate = _rate(n_exceed, n_cert)
    covs = [row["coverage"] for row in ops.values()
            if row["coverage"] is not None]
    mean_cov = round(float(np.mean(covs)), 4) if covs else None

    strict = ALPHA_LADDER[0]
    fd_hits = [row for row in pooled_rows
               if row["certified"] and row["alpha"] == strict
               and (row["coverage"] or 0.0) > EICU_FD_COVERAGE_ALARM
               and row.get("rm_fresh") is not None
               and row["rm_fresh"] < EICU_FD_RM_ALARM]
    # E-10: the two legs that depend on NEITHER alpha NOR coverage. One row per
    # (replicate, alpha) carries the same replicate-level probe, so dedupe.
    by_rep = {row["replicate"]: row for row in pooled_rows}
    auc_hits = [r for r, row in sorted(by_rep.items())
                if row.get("head_auc_oos") is not None
                and row["head_auc_oos"] > EICU_LEAK_AUC_CEILING]
    abl_hits = [r for r, row in sorted(by_rep.items())
                if row.get("ablation_drop") is not None
                and row["ablation_drop"] > EICU_LEAK_ABLATION_MAX_DROP]
    aucs = [row["head_auc_oos"] for row in by_rep.values()
            if row.get("head_auc_oos") is not None]
    drops = [row["ablation_drop"] for row in by_rep.values()
             if row.get("ablation_drop") is not None]
    n_primary_sites = site_counts.get("primary-cohort")

    return {
        "F-A": dict(
            fired=bool(exceed_rate is not None and exceed_rate > DELTA),
            n_replicates=n_replicates, n_certified_replicates=n_cert,
            n_rm_exceed=n_exceed, rm_exceed_rate=exceed_rate, target=DELTA,
            note=("BOUND-SHAPED OBSERVATION, never 'validity confirmed': "
                  f"{n_replicates} replicates cannot resolve a delta={DELTA} "
                  "rate, and the replicates share ONE hospital population, so "
                  "they are not independent draws of the calibration site "
                  "population.")),
        "F-B": dict(
            fired=bool(n_cert == 0 or (mean_cov is not None
                                       and mean_cov < EICU_FB_MIN_COVERAGE)),
            n_certified_replicates=n_cert, mean_operative_coverage=mean_cov,
            min_coverage=EICU_FB_MIN_COVERAGE,
            note=("feasibility failure: no rung certifies on the pooled arm, "
                  "or the operative rung answers fewer than a fifth of cases "
                  "-- a certificate at 5% coverage is a decline wearing a hat.")),
        "F-C": dict(
            fired=False,
            checked=["leak-denylist (assert_no_leak_columns)",
                     "feature width == EICU_N_FEATURES",
                     "categorical drift gate (build_raw strict_levels=True)",
                     "finite x after impute (etl.impute)",
                     "assert_site_disjoint(train, aux, cal)",
                     "assert_aggregate_only on every write"],
            note=("protocol failure aborts the run and writes no certificate; "
                  "reaching this payload means every gate above passed.")),
        "F-D": dict(
            fired=bool(fd_hits or auc_hits or abl_hits),
            legs=dict(
                discrimination=dict(
                    fired=bool(auc_hits), n_hits=len(auc_hits),
                    ceiling=EICU_LEAK_AUC_CEILING,
                    max_head_auc_oos=max(aucs) if aucs else None,
                    what=("the head's OWN out-of-sample AUC on the "
                          "site-disjoint calibration split. APACHE-IVa, a "
                          "purpose-built day-1 score, reaches ~0.87 on this "
                          "outcome; a 161-column logistic head that beats the "
                          "ceiling FROM THE SAME INPUTS is a leak before it is "
                          "a result.")),
                missingness_ablation=dict(
                    fired=bool(abl_hits), n_hits=len(abl_hits),
                    max_drop=EICU_LEAK_ABLATION_MAX_DROP,
                    observed_max_drop=max(drops) if drops else None,
                    what=("AUC lost by ablating the 49 missingness/presence "
                          "columns. APACHE day-1 rows do not exist for a stay "
                          "that ends because the patient died, so whole-row "
                          "absence is a partial OUTCOME proxy with no column "
                          "name -- invisible to a name denylist. Measured on "
                          "the mock: clean -0.016; outcome-correlated absence "
                          "at p=0.30 +0.082; at p=0.75 +0.248.")),
                unfalsifiable_success=dict(
                    fired=bool(fd_hits), n_hits=len(fd_hits), alpha=strict,
                    coverage_alarm=EICU_FD_COVERAGE_ALARM,
                    rm_alarm=EICU_FD_RM_ALARM,
                    what=("the original leg: alpha=0.05 certifying at 208 "
                          "hospitals with coverage > 0.90 and near-zero "
                          "fresh-pool R_M contradicts E4's frontier."))),
            n_hits=len(fd_hits) + len(auc_hits) + len(abl_hits),
            note=("the UNFALSIFIABLE-SUCCESS failure, in THREE legs. The first "
                  "two depend on NEITHER alpha NOR coverage: the old "
                  "single-leg form was demonstrated to pass underneath an "
                  "outcome-correlated-missingness leak that certified "
                  "alpha=0.10 at coverage 0.86 (2026-07-31 audit, E-10). If "
                  "ANY leg fires the run is FAILED until the denylist, the "
                  "first-stay/dedup logic and the APACHE presence channel are "
                  "re-audited; it is never reported as a headline. Prediction "
                  "P4 (presence flags in the top-3 abstention drivers) is the "
                  "LEAK'S SIGNATURE, so P4 is settled as confirmed only when "
                  "every leg here is clear.")),
        "F-E": dict(
            fired=bool(n_primary_sites is not None
                       and n_primary_sites < EICU_FE_MIN_SITES),
            n_sites_primary_cohort=n_primary_sites,
            min_sites=EICU_FE_MIN_SITES,
            note=("REPORTING obligation, not an abort: below this the "
                  "certificate's site-population-average estimand refers to "
                  "'hospitals that survived our filters', not 'US hospitals in "
                  "eICU', and every guarantee sentence must be re-scoped to "
                  "the surviving population BY NAME.")),
    }


def _figures(out, pooled_rows, per_site_rows, verbose):
    """Two figures, matplotlib Agg, house palette, no seaborn (SPEC Experiments)."""
    alphas = list(ALPHA_LADDER)
    fig, ax = plt.subplots(1, 3, figsize=(16, 4))
    cert_rate, mean_cov = [], []
    for a in alphas:
        rows = [r for r in pooled_rows if r["alpha"] == a]
        certs = [r for r in rows if r["certified"]]
        cert_rate.append(_rate(len(certs), len(rows)))
        cov = [r["coverage"] for r in certs if r["coverage"] is not None]
        mean_cov.append(round(float(np.mean(cov)), 4) if cov else None)
    _num = lambda v: np.nan if v is None else v
    ax[0].bar([str(a) for a in alphas], [_num(v) for v in cert_rate],
              color=EICU_PALETTE[0], label="certify rate")
    ax[0].plot([str(a) for a in alphas], [_num(v) for v in mean_cov], "o--",
               color=EICU_PALETTE[1], label="mean coverage")
    for i, v in enumerate(cert_rate):
        if not v:
            ax[0].text(i, 0.02, "no certificates", ha="center", va="bottom",
                       rotation=90, fontsize=8, color="dimgray")
    ax[0].set_title("eICU pooled arm: certification and coverage")
    ax[0].set_xlabel("alpha"); ax[0].set_ylabel("rate"); ax[0].legend(fontsize=8)

    for k, a in enumerate(alphas):
        certs = [r for r in pooled_rows if r["alpha"] == a and r["certified"]]
        xs = [r["replicate"] for r in certs]
        ys = [_num(r["rm_fresh"]) for r in certs]
        ax[1].plot(xs, ys, "o", color=EICU_PALETTE[k % len(EICU_PALETTE)],
                   label=f"R_M alpha={a}")
        ax[1].axhline(a, color="crimson", ls="--" if k == 0 else ":",
                      label=f"alpha={a}")
    ax[1].set_title("eICU held-out pool: influence-weighted answered risk")
    ax[1].set_xlabel("replicate"); ax[1].set_ylabel("R_M")
    ax[1].legend(fontsize=7)

    for k, a in enumerate(alphas):
        certs = [r for r in pooled_rows if r["alpha"] == a and r["certified"]]
        ax[2].plot([r["replicate"] for r in certs],
                   [_num(r["per_site_exceed_frac"]) for r in certs], "s-",
                   color=EICU_PALETTE[k % len(EICU_PALETTE)],
                   label=f"alpha={a}")
    ax[2].set_title("eICU per-site dispersion (NOT bounded by the certificate)")
    ax[2].set_xlabel("replicate")
    ax[2].set_ylabel("fraction of answering sites over alpha")
    ax[2].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(out, f"{EICU_OUT_PREFIX}_pooled.png"), dpi=110)
    plt.close(fig)

    fig, ax = plt.subplots(1, 2, figsize=(12, 4))
    op_alpha = None
    for a in alphas:
        if any(r["certified"] and r["alpha"] == a for r in per_site_rows):
            op_alpha = a
            break
    sub = [r for r in per_site_rows
           if r["alpha"] == op_alpha and r["certified"]] if op_alpha else []
    if sub:
        sizes = [r["n_target"] for r in sub]
        errs = [_num(r["answered_err_rate"]) for r in sub]
        covs = [_num(r["coverage"]) for r in sub]
        ax[0].scatter(sizes, errs, color=EICU_PALETTE[0], s=18)
        ax[0].axhline(op_alpha, color="crimson", ls="--",
                      label=f"alpha={op_alpha}")
        ax[0].set_xscale("log")
        ax[0].legend(fontsize=8)
        ax[1].scatter(sizes, covs, color=EICU_PALETTE[3], s=18)
        ax[1].set_xscale("log")
    else:
        for a_ in ax:
            a_.text(0.5, 0.5, "no per-hospital certificates", ha="center",
                    va="center", color="dimgray", transform=a_.transAxes)
    ax[0].set_title("eICU per-hospital answered error at the operative rung")
    ax[0].set_xlabel("hospital pool size (records)")
    ax[0].set_ylabel("answered error rate")
    ax[1].set_title("eICU per-hospital coverage")
    ax[1].set_xlabel("hospital pool size (records)")
    ax[1].set_ylabel("coverage")
    fig.tight_layout()
    fig.savefig(os.path.join(out, f"{EICU_OUT_PREFIX}_per_site.png"), dpi=110)
    plt.close(fig)
    _say(verbose, f"wrote {EICU_OUT_PREFIX}_pooled.png and "
                  f"{EICU_OUT_PREFIX}_per_site.png")


def _pooled_summary(pooled_rows, *, arm, replicates, n_records, n_sites,
                    site_counts, warnings):
    """The EICU-POOLED payload: per-rung rollup + the pre-declared verdicts."""
    out = {"arm": arm, "replicates": replicates, "n_records": n_records,
           "n_sites": n_sites,
           "estimand": (
               f"the M={M_INFLUENCE} influence-weighted answered-set risk "
               "averaged over the SITE POPULATION the calibration hospitals "
               "were drawn from -- NOT any individual hospital's answered "
               "error rate (audit V1). per_site_exceed_frac measures what the "
               "certificate deliberately does not bound."),
           "rm_fresh_means": (
               "R_M on the HELD-OUT 24-hospital target pool of this replicate "
               "-- hospitals that entered no fitting and no calibration split. "
               "It is not a second independent draw from the site population: "
               "the replicates share ONE hospital population, which is exactly "
               "why F-A is written as a bound-shaped observation."),
           "rungs": {}}
    for alpha in ALPHA_LADDER:
        rows = [x for x in pooled_rows if x["alpha"] == alpha]
        certs = [x for x in rows if x["certified"]]
        rm = [x["rm_fresh"] for x in certs if x["rm_fresh"] is not None]
        disp = [x["per_site_exceed_frac"] for x in certs
                if x["per_site_exceed_frac"] is not None]
        cov = [x["coverage"] for x in certs if x["coverage"] is not None]
        taus = [x["tau"] for x in certs if x["tau"] is not None]
        reasons = {}
        for x in rows:                    # WHY a mode did not contribute (P3)
            if x["decline_reason"]:
                reasons[x["decline_reason"]] = \
                    reasons.get(x["decline_reason"], 0) + 1
        out["rungs"][_alpha_key(alpha)] = dict(
            certify_rate=_rate(len(certs), len(rows)),
            n_certified=len(certs), n_replicates=len(rows),
            mean_tau=round(float(np.mean(taus)), 4) if taus else None,
            mean_coverage=round(float(np.mean(cov)), 4) if cov else None,
            mean_rm_fresh=round(float(np.mean(rm)), 4) if rm else None,
            rm_exceed_rate=_rate(sum(1 for x in certs if x["rm_exceed"]),
                                 len(certs)),
            hard_violation_rate_diag=_rate(sum(1 for x in certs if x["hard"]),
                                           len(certs)),
            mean_per_site_exceed_frac=round(float(np.mean(disp)), 4)
            if disp else None,
            deploy_modes=sorted({x["deploy_mode"] for x in certs
                                 if x["deploy_mode"]}),
            mode_non_contribution=reasons)
    out["failure_criteria"] = _failure_criteria(pooled_rows, site_counts,
                                                replicates)
    out["site_selection"] = {
        "n_sites_primary_cohort": site_counts.get("primary-cohort"),
        "n_sites_apache_result_linked": site_counts.get("apache-result-linked"),
        "n_sites_apache_complete_arm": site_counts.get("apache-complete-arm"),
        "note": ("apache-result-linked vs primary-cohort is the site-selection "
                 "statistic (threat T-4). The primary arm MEASURES it and "
                 "never applies it: restricting the cohort would move the site "
                 "population the estimand refers to.")}
    out["warnings"] = warnings
    return out


def _per_site_summary(per_site_rows, *, arm):
    """The EICU-PERSITE payload: the between-hospital DISPERSION the
    certificate deliberately does not bound (audit V1), plus the
    ``pool-too-small`` count that settles prediction P5."""
    pools = {(x["replicate"], x["site"]) for x in per_site_rows}
    too_small = {(x["replicate"], x["site"]) for x in per_site_rows
                 if x["reason"] == "pool-too-small"}
    out = {"arm": arm, "n_pools": len(pools),
           "n_pool_too_small": len(too_small),
           "min_answerable": MIN_ANSWERABLE,
           "reason_column": (
               "EICU_per_site.csv 'reason' carries, in order of precedence: "
               "the STRUCTURAL gate ('pool-too-small' / "
               "'insufficient-clusters'), else the rung's per-mode decline "
               "reasons, else -- on a CERTIFIED row -- the modes that did not "
               "back the deployed threshold ('bbse:<reason>'). Read it "
               "together with 'certified': a certified row carrying a reason "
               "is the BBSE non-contribution signal (P3), not a decline."),
           "rungs": {}}
    for alpha in ALPHA_LADDER:
        rows = [x for x in per_site_rows if x["alpha"] == alpha]
        certs = [x for x in rows if x["certified"]]
        errs = [x["answered_err_rate"] for x in certs
                if x["answered_err_rate"] is not None]
        cov = [x["coverage"] for x in certs if x["coverage"] is not None]
        out["rungs"][_alpha_key(alpha)] = dict(
            n_pools=len(rows), n_certified=len(certs),
            certify_rate=_rate(len(certs), len(rows)),
            mean_coverage=round(float(np.mean(cov)), 4) if cov else None,
            answered_err=_summary_stats(errs),
            hard_violation_rate_diag=_rate(sum(1 for x in certs if x["hard"]),
                                           len(certs)),
            note=("per-hospital hard-violation is a DISPERSION diagnostic with "
                  "NO delta target: the certificate bounds the site-population "
                  "average, not individual hospitals (audit V1)."))
    return out


def _comparator_summary(comparator_rows, *, arm):
    """The EICU-COMPARATOR payload: APACHE-IVa on the answered set."""
    out = {"arm": arm, "rungs": {}}
    for alpha in ALPHA_LADDER:
        rows = [x for x in comparator_rows if x["alpha"] == alpha
                and x["n_answered"] > 0]
        brier = [x["apache_iva_brier_answered"] for x in rows
                 if x["apache_iva_brier_answered"] is not None]
        auc = [x["apache_iva_auc_answered"] for x in rows
               if x["apache_iva_auc_answered"] is not None]
        cg = [x["certgate_answered_err"] for x in rows
              if x["certgate_answered_err"] is not None]
        sub = [x["_certgate_err_on_apache_subset"] for x in rows
               if x["_certgate_err_on_apache_subset"] is not None]
        avail = [x["n_apache_available"] for x in rows]
        ans = [x["n_answered"] for x in rows]
        out["rungs"][_alpha_key(alpha)] = dict(
            n_certified_replicates=len(rows),
            mean_certgate_answered_err=round(float(np.mean(cg)), 4)
            if cg else None,
            mean_certgate_answered_err_on_apache_subset=round(
                float(np.mean(sub)), 4) if sub else None,
            mean_apache_iva_brier=round(float(np.mean(brier)), 4)
            if brier else None,
            mean_apache_iva_auc=round(float(np.mean(auc)), 4) if auc else None,
            apache_available_share=_rate(int(np.sum(avail)), int(np.sum(ans)))
            if ans else None,
            note=("the APACHE-IVa columns are scored on the answered records "
                  "that CARRY a comparator value; that coverage is "
                  "site-correlated, so the subset-matched CertGate error is "
                  "reported beside them rather than compared across different "
                  "denominators."))
    return out


def _certification_blocks(payload):
    """Derive the EICU-POOLED / EICU-PERSITE / EICU-COMPARATOR sections."""
    if not payload:
        return {}
    return {"EICU-POOLED": payload.get("pooled"),
            "EICU-PERSITE": payload.get("per_site"),
            "EICU-COMPARATOR": payload.get("comparator")}


def run_certification(data_dir, out, *, arm="primary", replicates=1,
                      quick=False, verbose=True) -> dict:
    """Full certification run over ``replicates`` independent by-site re-splits.

    Per replicate, on ONE ``build_raw`` (re-reading a 200k-row extract 20 times
    is a build error, not a style preference -- threat T-16):

      1. ``etl.site_split(site_raw, replicate=r)``          (records never cross)
      2. ``etl.impute(x_raw, idx['train'])``                (S_train ONLY: pooled
         means would let the target pool's covariates into the training
         features -- a transductive leak no downstream gate catches)
      3. cohorts via ``from_raw``; ``require_both_classes=False`` for TARGET only
      4. ``assert_site_disjoint(train, aux, cal)``
      5. POOLED arm: one ``run_certgate`` over all 24 held-out hospitals,
         ``target_site_id`` supplied (K = 24 >= BBSE_MIN_TARGET_SITES, so q_t
         takes the cluster bootstrap)
      6. PER-HOSPITAL arm: one ``run_certgate`` per held-out hospital,
         ``target_site_id`` supplied even at K == 1 -- statistically the same
         exact Clopper-Pearson q_t path ``None`` takes, plus full id
         validation, record-level disjointness against train/aux/cal, and
         provenance binding of the dense array and its canonical labels
      7. oracle scoring: ``_rm_on_pool`` + ``_per_site_exceed_frac`` +
         ``hard_violation`` at the deployed tau against the held-out pool
      8. APACHE-IVa comparator on the answered set (aggregate rates only)

    ``quick=True`` caps replicates at 2 and skips figures. Returns the summary
    payload; every artifact it writes has passed ``assert_aggregate_only``.
    """
    if arm not in etl.EICU_ARMS:
        raise etl.EicuError(
            f"run_eicu.run_certification: arm must be one of {etl.EICU_ARMS}, "
            f"got {arm!r} (reason=unknown-arm)")
    replicates = int(replicates)
    if replicates < 1:
        # run_eicu's OWN reason tags (record-level-output, non-ascii-output,
        # bad-replicates) sit beside eicu_etl's closed set; a truthful tag
        # beats reusing a neighbouring module's tag that names the wrong fault.
        raise etl.EicuError(
            f"run_eicu.run_certification: replicates must be >= 1, got "
            f"{replicates} (reason=bad-replicates)")
    if quick:
        replicates = min(replicates, 2)
    os.makedirs(out, exist_ok=True)
    warnings = []

    # ---- one streaming build, then the loud protocol gates (F-C) ----------
    x_raw, feature_names, meta = etl.build_raw(data_dir, arm=arm,
                                               strict_levels=True,
                                               verbose=verbose)
    etl.assert_no_leak_columns(feature_names)          # a TEST, not a comment
    if (len(feature_names) != etl.EICU_N_FEATURES
            or int(x_raw.shape[1]) != etl.EICU_N_FEATURES):
        raise etl.EicuError(
            f"run_eicu.run_certification: feature width "
            f"{int(x_raw.shape[1])} / name count {len(feature_names)} != "
            f"EICU_N_FEATURES={etl.EICU_N_FEATURES} "
            f"(reason=feature-width-mismatch)")
    n_records = int(x_raw.shape[0])
    if n_records == 0:
        raise etl.EicuError(
            f"run_eicu.run_certification: arm {arm!r} produced an empty cohort "
            f"(reason=empty-cohort)")

    ref = _reference_check(meta)
    if not ref["matches_reference"]:
        warnings.append(
            f"extract does not match the eICU-CRD v2.0 reference "
            f"({ref['n_raw_stays']} stays / {ref['n_raw_sites']} hospitals vs "
            f"{ref['expected_stays']} / {ref['expected_sites']}) -- every "
            f"number below describes THIS extract, not the released dataset")
        _say(verbose, f"[MEASURE] {warnings[-1]}", err=True)

    y_raw = list(etl.labels(meta))
    site_raw = [str(s) for s in meta["site_raw"]]
    comparator = np.asarray(meta["comparator_predicted_mortality"],
                            dtype=np.float64)
    attrition_rows = _attrition_rows(meta, arm, warnings)
    site_counts = {d["step"]: d["n_sites"] for d in attrition_rows}
    coverage_by_site = _site_coverage(meta)
    missing_by_site = _site_missing_share(x_raw, meta)
    hospital_strata = _hospital_strata(data_dir, warnings)

    # E-19: every allowlisted feature screened against the outcome BEFORE any
    # certificate. The denylist applies a "timing relative to outcome
    # unverified" standard to two apachePatientResult columns; nine
    # apachePredVar treatment flags (activetx above all) had no timing
    # verification at all, and the DDL cannot settle it on a dataset whose
    # sentinel convention the DDL already gets wrong. So it is settled from the
    # data. Run on the RAW matrix -- the only place missingness is still visible.
    screen = etl.outcome_screen(x_raw, meta, names=feature_names)
    screen_block = {"base_prevalence": screen["base_prevalence"],
                    "review_auc": screen["review_auc"],
                    "n_features": screen["n_features"],
                    "flagged": screen["flagged"][:EICU_TOP_GAP_FEATURES],
                    "n_flagged": len(screen["flagged"]),
                    "outcome_missingness": screen["outcome_missingness"],
                    "timing_unverified": list(EICU_TIMING_UNVERIFIED),
                    "timing_unverified_auc": {
                        c: screen["features"].get(f"apv_{c}", {}).get("auc")
                        for c in EICU_TIMING_UNVERIFIED}}
    if screen["flagged"]:
        warnings.append(
            f"E-19: {len(screen['flagged'])} allowlisted feature(s) exceed the "
            f"pre-registered univariate review band "
            f"|AUC-0.5| > {etl.EICU_FEATURE_AUC_REVIEW - 0.5}: "
            f"{[(d['feature'], d['auc']) for d in screen['flagged'][:6]]!r} -- "
            f"each must be re-audited for measurement TIMING before any number "
            f"is reported")
        _say(verbose, f"[MEASURE] {warnings[-1]}", err=True)

    _say(verbose, f"arm={arm}: {n_records} records x {len(feature_names)} "
                  f"features over {len(coverage_by_site)} hospitals; "
                  f"{replicates} replicate(s), seed={SEED}")

    pooled_rows, per_site_rows, comparator_rows = [], [], []
    composition_rows, bbse_rows, abstention = [], [], {}
    leak_rows = []
    certificate = None
    impute_fill = {}
    sites_without_strata = set()          # DISTINCT sites, not site x replicate

    for r in range(replicates):
        idx, sets = etl.site_split(site_raw, replicate=r)
        # PAIRWISE disjointness of the returned label sets, re-asserted at the
        # runner boundary. assert_site_disjoint below covers train/aux/cal and
        # run_certgate covers the target -- this catches a split that is wrong
        # BEFORE a head is fit on it, and covers the target pair explicitly (a
        # triple-intersection assert is strictly weaker; SPEC A.8).
        for a, b in (("train", "aux"), ("train", "cal"), ("aux", "cal"),
                     ("train", "target"), ("aux", "target"), ("cal", "target")):
            shared = sorted(set(sets[a]) & set(sets[b]))
            if shared:
                raise CohortError(
                    f"run_eicu.run_certification: site_split(replicate={r}) "
                    f"returned splits {a!r} and {b!r} sharing sites "
                    f"{shared[:8]!r} -- records must never cross a split "
                    f"boundary")
        x, fill = etl.impute(x_raw, idx["train"], verbose=False)
        if r == 0:
            impute_fill = dict(fill)
        cohorts = _build_cohorts(x, y_raw, site_raw, idx, arm, r)
        train, aux, cal = cohorts["train"], cohorts["aux"], cohorts["cal"]
        target = cohorts["target"]
        # F-D legs 1 and 2 (E-10): the leak alarm runs BEFORE any certificate,
        # every replicate, and depends on neither alpha nor coverage.
        leak, head = _leak_probe(train, cal, feature_names)
        leak["replicate"] = r
        leak_rows.append(leak)
        if leak["auc_alarm"] or leak["ablation_alarm"]:
            _say(True, f"F-D LEAK ALARM at replicate {r}: out-of-sample head "
                       f"AUC {leak['head_auc_oos']} (ceiling "
                       f"{EICU_LEAK_AUC_CEILING}), missingness-ablation drop "
                       f"{leak['ablation_drop']} (cap "
                       f"{EICU_LEAK_ABLATION_MAX_DROP}) -- re-audit the "
                       f"denylist, the first-stay/dedup logic and the APACHE "
                       f"presence channel before reporting ANY number",
                 err=True)
        t_idx = np.asarray(idx["target"], dtype=int)
        t_sites = [site_raw[i] for i in t_idx.tolist()]
        t_sites_arr = np.asarray(t_sites)
        n_carrying = int((cal.site_sizes > 0).sum())
        _say(verbose, f"replicate {r}: train {train.n_sites} / aux "
                      f"{aux.n_sites} / cal {cal.n_sites} sites "
                      f"({n_carrying} record-carrying, floor "
                      f"{MIN_CAL_CLUSTERS}); target {target.n_sites} hospitals,"
                      f" {target.n} records")

        # ---- arm 2: pooled multi-site pool (K == 24) ----------------------
        rep_pooled = run_certgate(train, aux, cal, target.x,
                                  target_label=etl.EICU_POOLED_TARGET_LABEL,
                                  target_site_id=t_sites,
                                  oracle_target_y=target.y)
        for alpha in ALPHA_LADDER:
            ev = _eval_rung(head, rep_pooled, alpha, target.x, target.y)
            rm = disp = None
            if ev["certified"]:
                rm = _rm_on_pool(head, target, ev["tau"])
                disp = _per_site_exceed_frac(head, target, ev["tau"], alpha)
            pooled_rows.append(dict(
                replicate=r, arm=arm, alpha=alpha,
                certified=ev["certified"], tau=ev["tau"],
                tau_idx=ev["tau_idx"], deploy_mode=ev["deploy_mode"],
                modes=ev["modes"], coverage=ev["coverage"],
                n_target=int(target.n), n_answered=ev["n_answered"],
                answered_err_rate=ev["answered_err_rate"],
                rm_fresh=(None if rm is None or not np.isfinite(rm)
                          else round(float(rm), 6)),
                rm_exceed=(None if rm is None or not np.isfinite(rm)
                           else bool(rm > alpha)),
                per_site_exceed_frac=(None if disp is None
                                      or not np.isfinite(disp)
                                      else round(float(disp), 4)),
                hard=ev["hard"], n_cal_carrying=n_carrying,
                head_auc_oos=leak["head_auc_oos"],
                head_auc_ablated=leak["head_auc_ablated"],
                ablation_drop=leak["ablation_drop"],
                leak_alarm=bool(leak["auc_alarm"] or leak["ablation_alarm"]),
                decline_reason=ev["decline_reason"]))
            if ev["certified"]:
                abstention[f"replicate{r}_alpha{_alpha_key(alpha)}"] = \
                    _abstention_ranking(head, target.x, ev["tau"],
                                        feature_names)
            crow, subset_err = _comparator_row(head, rep_pooled, alpha, target,
                                               comparator[t_idx], r)
            crow["_certgate_err_on_apache_subset"] = subset_err
            comparator_rows.append(crow)

        bb = _bbse_block(rep_pooled)
        bb["replicate"] = r
        bb["mode_outcomes"] = {
            _alpha_key(row["alpha"]): (row.get("mode_outcomes")
                                       or row.get("reasons"))
            for row in rep_pooled["certified"]}
        bbse_rows.append(bb)

        comp = (rep_pooled.get("diagnostic") or {}).get("composition")
        op = rep_pooled.get("operative")
        if comp and op is not None:
            composition_rows.append(dict(
                replicate=r, alpha=op["alpha"], tau=round(float(op["tau"]), 6),
                predicted_positive_fraction=(comp.get("predicted_class") or {})
                .get("positive_fraction"),
                bbse_implied_positive_fraction=(comp.get("bbse_true_class")
                                                or {}).get("positive_fraction"),
                oracle_positive_fraction=(comp.get("oracle_true_class") or {})
                .get("positive_fraction")))

        if r == 0:
            certificate = _strip_report(rep_pooled, feature_names)
            _say(verbose, "replicate 0 pooled certificate:\n"
                 + render_text(rep_pooled))

        # ---- arm 1: per-hospital single-site pools (K == 1) ---------------
        for site in sorted(set(t_sites), key=_site_sort_key):
            pos = np.flatnonzero(t_sites_arr == site)
            x_h = target.x[pos]
            y_h = target.y[pos]
            rep_h = run_certgate(train, aux, cal, x_h, target_label=site,
                                 target_site_id=[site] * int(pos.size),
                                 oracle_target_y=y_h)
            strat = _site_stratum(meta, site, hospital_strata)
            if not strat["found"]:
                sites_without_strata.add(site)
            cov = coverage_by_site.get(site, {})
            for alpha in ALPHA_LADDER:
                ev = _eval_rung(head, rep_h, alpha, x_h, y_h)
                per_site_rows.append(dict(
                    replicate=r, arm=arm, site=site, alpha=alpha,
                    n_target=int(pos.size),
                    reason=(rep_h.get("reason")
                            or ev["decline_reason"] or None),
                    certified=ev["certified"], tau=ev["tau"],
                    coverage=ev["coverage"], n_answered=ev["n_answered"],
                    answered_err_rate=ev["answered_err_rate"],
                    hard=ev["hard"],
                    numbedscategory=strat["numbedscategory"],
                    teachingstatus=strat["teachingstatus"],
                    region=strat["region"],
                    aps_coverage=cov.get("aps_coverage"),
                    apv_coverage=cov.get("apv_coverage")))

    # ---- tables ----------------------------------------------------------
    _write_table(os.path.join(out, f"{EICU_OUT_PREFIX}_attrition.csv"),
                 attrition_rows,
                 ["step", "n_stays", "n_sites", "n_positive", "prevalence",
                  "arm"], "EICU_attrition.csv")
    _write_table(os.path.join(out, f"{EICU_OUT_PREFIX}_pooled.csv"),
                 pooled_rows,
                 ["replicate", "arm", "alpha", "certified", "tau", "tau_idx",
                  "deploy_mode", "modes", "coverage", "n_target", "n_answered",
                  "answered_err_rate", "rm_fresh", "rm_exceed",
                  "per_site_exceed_frac", "hard", "n_cal_carrying",
                  "head_auc_oos", "head_auc_ablated", "ablation_drop",
                  "leak_alarm", "decline_reason"], "EICU_pooled.csv")
    _write_table(os.path.join(out, f"{EICU_OUT_PREFIX}_per_site.csv"),
                 per_site_rows,
                 ["replicate", "arm", "site", "alpha", "n_target", "reason",
                  "certified", "tau", "coverage", "n_answered",
                  "answered_err_rate", "hard", "numbedscategory",
                  "teachingstatus", "region", "aps_coverage", "apv_coverage"],
                 "EICU_per_site.csv")
    _write_table(os.path.join(out, f"{EICU_OUT_PREFIX}_comparator.csv"),
                 comparator_rows,
                 ["replicate", "alpha", "n_answered", "certgate_answered_err",
                  "apache_iva_brier_answered", "apache_iva_auc_answered",
                  "n_apache_available"], "EICU_comparator.csv")

    # ---- diagnostics + certificate ---------------------------------------
    aps_vals = [d["aps_coverage"] for d in coverage_by_site.values()]
    apv_vals = [d["apv_coverage"] for d in coverage_by_site.values()]
    diagnostics = {
        "arm": arm, "replicates": replicates,
        "n_records": n_records, "n_sites": len(coverage_by_site),
        "reference_check": ref,
        "site_missingness_dispersion": dict(
            _summary_stats(list(missing_by_site.values())),
            what=("per-hospital mean share of NaN across the imputable "
                  "feature columns, measured on the RAW matrix before "
                  "imputation erases it. Site-informative missingness is a "
                  "covariate-shift channel CertGate v2 scope-cut (threat "
                  "T-3): it is MEASURED here, never imputed away.")),
        "apache_coverage_by_site": {
            "aps": _coverage_bands(coverage_by_site, "aps_coverage"),
            "apv": _coverage_bands(coverage_by_site, "apv_coverage")},
        "categorical_drift": {
            "other_shares": meta.get("categorical_other_shares"),
            "cap": etl.EICU_MAX_OTHER_SHARE,
            "note": ("build_raw ran with strict_levels=True, so a share over "
                     "the cap would have RAISED categorical-level-drift "
                     "before any certificate existed.")},
        # E-9/E-10/E-19: the outcome-informative half of the missingness
        # channel, the runtime leak alarm, and the per-feature timing screen.
        # These three exist because absence has no column name and so is
        # invisible to EICU_LEAK_DENYLIST.
        "outcome_missingness": meta.get("outcome_missingness"),
        "leak_probe": leak_rows,
        "outcome_screen": screen_block,
        "attrition_prevalence": [
            {k: d.get(k) for k in ("step", "n_stays", "n_positive",
                                   "prevalence")}
            for d in (meta.get("attrition") or [])],
        "sentinel_counts": meta.get("sentinel_counts"),
        "unit_conversions": meta.get("unit_conversions"),
        "unparseable_tokens": meta.get("unparseable_tokens"),
        "window_clipped_counts": meta.get("window_clipped_counts"),
        "dedup_counts": meta.get("dedup_counts"),
        "drop_counts": meta.get("drop_counts"),
        "cross_site_patients": meta.get("cross_site_patients"),
        "impute_fill_replicate0": impute_fill,
        "abstention_gap_ranking": abstention,
        "composition_three_way": composition_rows,
        "bbse": bbse_rows,
        "n_target_sites_without_hospital_strata": len(sites_without_strata),
        "n_hospital_strata_rows": len(hospital_strata),
        "warnings": warnings,
    }
    _write_json(os.path.join(out, f"{EICU_OUT_PREFIX}_diagnostics.json"),
                diagnostics, "EICU_diagnostics.json")
    if certificate is not None:
        _write_json(os.path.join(out, f"{EICU_OUT_PREFIX}_certificate.json"),
                    certificate, "EICU_certificate.json")

    if not quick:
        _figures(out, pooled_rows, per_site_rows, verbose)

    # ---- summary payload --------------------------------------------------
    payload = {
        "pooled": _pooled_summary(pooled_rows, arm=arm, replicates=replicates,
                                  n_records=n_records,
                                  n_sites=len(coverage_by_site),
                                  site_counts=site_counts, warnings=warnings),
        "per_site": _per_site_summary(per_site_rows, arm=arm),
        "comparator": _comparator_summary(comparator_rows, arm=arm)}
    _write_summary(out, _certification_blocks(payload), mode=(
        "QUICK" if quick else "FULL"), replicates=replicates, arm=arm,
        data_sha=_data_sha(data_dir))

    fc = payload["pooled"]["failure_criteria"]
    for name in ("F-A", "F-B", "F-D", "F-E"):
        if fc[name]["fired"]:
            _say(True, f"PRE-DECLARED FAILURE {name} FIRED: {fc[name]['note']}",
                 err=True)
    _say(verbose, f"wrote CSVs, diagnostics, certificate and "
                  f"EICU-SUMMARY.md to {out}")
    return payload


# ------------------------------------------------------- summary + driver ---

def _existing_summary_blocks(path):
    """Parse an existing ``EICU-SUMMARY.md`` into {section: rendered json block}.

    The eICU path owns its own parser and its own file: ``run_synthetic``'s
    regex is ``^## (E\\d)``, a SINGLE digit, so an ``## EICU-...`` section
    placed in ``summary.md`` would be unparseable there and silently clobbered
    on the next partial rerun. The header pattern tolerates a "(preserved ...)"
    suffix so a preserved section survives a second partial run (audit V26).
    """
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    return {m.group(1): m.group(2)
            for m in _SUMMARY_BLOCK_RE.finditer(text)}


def _write_summary(out, blocks, *, mode, replicates, arm, data_sha):
    """Write ``EICU-SUMMARY.md``: fresh sections stamped, others preserved.

    Same discipline as ``run_synthetic._write_summary`` (audit V26): every
    fresh block carries its own ``_run`` stamp and preserved sections are
    VISIBLY marked, so a FULL header can never sit above a QUICK-computed
    block.
    """
    path = os.path.join(out, f"{EICU_OUT_PREFIX}-SUMMARY.md")
    preserved = _existing_summary_blocks(path)
    stamp = dict(mode=mode,
                 utc=datetime.datetime.now(
                     datetime.timezone.utc).isoformat(timespec="seconds"),
                 replicates=int(replicates), arm=arm, data_sha=data_sha)
    lines = ["# CertGate eICU-CRD v2.0 -- real-data summary",
             "",
             f"- mode: {mode} (per-block stamps are authoritative; preserved "
             f"sections are marked)",
             f"- seed: {SEED}",
             f"- alpha ladder: {ALPHA_LADDER}, delta: {DELTA}",
             "- estimand: site-population average, NOT a per-hospital "
             "guarantee (audit V1)",
             "- the extract itself is NOT redistributable; every artifact here "
             "is aggregate-only (PhysioNet DUA 1.5.0)",
             ""]
    for name in EICU_SUMMARY_SECTIONS:
        payload = blocks.get(name)
        if payload is not None:
            ready = _json_ready({"_run": stamp, **payload})
            assert_aggregate_only(ready, f"EICU-SUMMARY.md::{name}")
            block = "```json\n" + json.dumps(ready, indent=2) + "\n```"
            lines.append(f"## {name}")
        elif name in preserved:
            block = preserved[name]
            lines.append(f"## {name} (preserved from an earlier run)")
        else:
            continue
        lines.append(block)
        lines.append("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def _data_sha(data_dir):
    """Identity of an extract WITHOUT reading it: sha256 over the sorted
    ``name:size`` listing of its gzip tables. Cheap on a 3 GB directory, and it
    distinguishes v2.0 from a re-zip or the mock corpus; no record-level byte
    enters the digest or the artifact."""
    h = hashlib.sha256()
    try:
        names = sorted(os.listdir(data_dir))
    except OSError:
        return None
    for name in names:
        if not name.lower().endswith(".csv.gz"):
            continue
        path = os.path.join(data_dir, name)
        try:
            size = os.path.getsize(path)
        except OSError:                                  # pragma: no cover
            continue
        h.update(f"{name.lower()}:{size}\n".encode())
    return h.hexdigest()


def main(argv=None) -> dict:
    """CLI entry point (SPEC "Real-data protocol").

    The summary and the provenance block are written in a ``finally:`` block so
    an aborted run never leaves fresh CSVs beside a silently stale summary
    (audit V26): on an abort the fresh-block set is empty, every prior section
    is re-emitted marked "(preserved from an earlier run)", and the failure is
    visible rather than papered over.
    """
    ap = argparse.ArgumentParser(
        description="CertGate eICU-CRD v2.0 certification run")
    ap.add_argument("--data", required=True,
                    help="directory holding the gzipped eICU CSV tables "
                         "(gitignored; never committed or redistributed)")
    ap.add_argument("--preflight", action="store_true",
                    help="profile the extract and write the a-priori "
                         "predictions; build no features and certify nothing")
    ap.add_argument("--out", default=os.path.join("experiments", "out"),
                    help="output directory (aggregate artifacts only)")
    ap.add_argument("--arm", default=etl.EICU_ARMS[0],
                    choices=list(etl.EICU_ARMS),
                    help="cohort arm; apache-linked (day-1 window complete, "
                         "immortal-time-selected) and apache-complete "
                         "(additionally comparator-available) are declared "
                         "SENSITIVITY arms and never the headline")
    ap.add_argument("--replicates", type=int, default=1,
                    help=f"independent by-site re-splits; the validity arm is "
                         f"{etl.EICU_SPLIT_REPLICATES}")
    ap.add_argument("--quick", action="store_true",
                    help="cap replicates at 2 and skip figures")
    ap.add_argument("--no-reference-check", dest="reference_check",
                    action="store_false",
                    help="preflight only: do not require the extract to match "
                         "EICU_REFERENCE_ROW_COUNTS (the mock-corpus path)")
    args = ap.parse_args(argv)
    if args.replicates < 1:
        ap.error(f"--replicates must be >= 1, got {args.replicates}")

    os.makedirs(args.out, exist_ok=True)
    mode = "PREFLIGHT" if args.preflight else (
        "QUICK" if args.quick else "FULL")
    _say(True, f"{mode} run -> {args.out} (seed={SEED}); arm={args.arm}, "
               f"replicates={args.replicates}")
    result = None
    try:
        if args.preflight:
            result = run_preflight(args.data, args.out,
                                   reference_check=args.reference_check)
        else:
            result = run_certification(args.data, args.out, arm=args.arm,
                                       replicates=args.replicates,
                                       quick=args.quick)
    finally:
        blocks = (_preflight_blocks(result) if args.preflight
                  else _certification_blocks(result))
        _write_summary(args.out, blocks, mode=mode,
                       replicates=(0 if args.preflight else args.replicates),
                       arm=(None if args.preflight else args.arm),
                       data_sha=_data_sha(args.data))
        _write_json(os.path.join(args.out,
                                 f"{EICU_OUT_PREFIX}_provenance.json"),
                    provenance(mode=mode, arm=args.arm,
                               replicates=int(args.replicates),
                               quick=bool(args.quick),
                               preflight=bool(args.preflight),
                               data_sha=_data_sha(args.data),
                               protocol="EICU-PROTOCOL.md",
                               n_features=int(etl.EICU_N_FEATURES)),
                    "EICU_provenance.json")
        _say(True, f"wrote {EICU_OUT_PREFIX}-SUMMARY.md and "
                   f"{EICU_OUT_PREFIX}_provenance.json to {args.out}")
    return result


if __name__ == "__main__":
    main()
