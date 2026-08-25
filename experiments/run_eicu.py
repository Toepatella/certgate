"""The eICU-CRD v2.0 certification runner: two modes behind one CLI.

PREFLIGHT profiles an extract and writes the a-priori predictions. It builds no
features and certifies nothing. The pre-registration ordering is the whole
point: the predictions must exist on disk before any certificate does.

CERTIFICATION builds the cohorts through certgate.validate.from_raw, asserts
site-disjointness, then drives certgate.pipeline.run_certgate over both
target-pool arms. Those arms are 24 single-hospital pools (K == 1) and one
pooled multi-site pool (K == 24), repeated for each of --replicates independent
by-site re-splits.

Compliance is enforced in code, not in a comment. assert_aggregate_only sits on
every write, because the PhysioNet Credentialed Health Data License 1.5.0 and
DUA 1.5.0 restrict derived record-level artifacts and experiments/out/ is a
tracked directory. Nothing keyed by patientunitstayid or uniquepid ever reaches
the output directory.

CLI:

    python -m experiments.run_eicu --data DIR [--preflight] [--out experiments/out]
            [--arm primary|apache-complete] [--replicates N] [--quick]
            [--no-reference-check]

--data is required in both modes. --preflight short-circuits after the profile.
--replicates defaults to 1; the validity-replication arm is --replicates 20
(= eicu_etl.EICU_SPLIT_REPLICATES). --quick caps replicates at 2 and skips
figures.

Deliberate deviations from the run_synthetic house conventions:

  * _rm_on_pool and _per_site_exceed_frac are imported from run_synthetic,
    never re-implemented. They are the exact quantities the paper's synthetic
    numbers use, and a private copy would let the real-data numbers drift from
    the synthetic ones silently.
  * eICU tables are written ASCII-strict (_write_table). eICU categorical
    literals may carry non-ASCII, and a crash beats a mojibake cell.
  * The summary is EICU-SUMMARY.md and NEVER summary.md.
    run_synthetic._existing_summary_blocks matches ^## (E\\d) -- a single digit
    -- so an ## EICU section placed there would be unparseable and silently
    clobbered by the next partial --only rerun.
  * Structural outcomes are read from report["reason"] and row["status"], never
    from exception-or-not. run_certgate returns a gated report
    (insufficient-clusters, pool-too-small) rather than raising, so code that
    only catches exceptions reads a gated run as a successful certification of
    nothing.

Refs: SPEC "Real-data protocol (eICU-CRD v2.0)"; threat T-12.
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
from certgate.explain import (cohort_abstention_profile,
                              gaussian_conditional_shapley_matrix)
from certgate import reliability as rp
from experiments import eicu_etl as etl
from experiments.run_synthetic import (_rm_on_pool, _per_site_exceed_frac,
                                       _write_csv, _rate)

# _write_csv is imported because the SPEC's import surface names it. The eICU
# tables deliberately do not use it -- see _write_table, where locale-default
# encoding would write a mojibake cell instead of crashing.
# Do not let an F401 autofix strip it. tests/test_eicu_path.py pins the identity
# run_eicu._write_csv is run_synthetic._write_csv.

EICU_OUT_PREFIX = "EICU"
EICU_MAX_OUTPUT_LEN = 512        # > 208 sites, < any record-level array
EICU_FORBIDDEN_OUT_KEYS = ("stay_id", "patient_id", "admission_id", "site_raw",
                           "y_raw", "answered_mask", "x", "site_id",
                           "comparator_predicted_mortality", "split_idx")
# This tuple is APPEND-ONLY. A new section goes last so that no section written
# before it moves, which is what keeps every EICU-SUMMARY.md already on disk --
# experiments/out/ and out-sens/ included -- parseable and preserved.
# _write_summary emits only the names listed here (else: continue), so a block
# added to _certification_blocks without this edit is dropped with no error.
EICU_SUMMARY_SECTIONS = ("EICU-PREFLIGHT", "EICU-PREDICTIONS",
                         "EICU-POOLED", "EICU-PERSITE", "EICU-COMPARATOR",
                         "EICU-RELIABILITY", "EICU-SUBGROUPS",
                         "EICU-FAITHFULNESS")

# Post-hoc subgroup descriptives. They carry no pre-registration claim: the
# dimensions and age bands were chosen after the extract was read.
# The label below travels in two places -- a leading post_hoc column on every
# EICU_subgroups.csv row, and the post_hoc field of the EICU-SUBGROUPS summary
# block. The cell floor reuses the frozen eicu_etl.EICU_MIN_OUTCOME_STRATUM,
# adding no new threshold constant.
# One marginal dimension at a time, never crossed, never per-hospital x
# subgroup.
# Ref: SPEC pin amendment, revision-2 item 3b; panel item S2-36; A5/A6
# discipline.
EICU_SUBGROUP_DIMS = ("age_band", "gender", "ethnicity",
                      "hospitaladmitsource", "unittype")
EICU_SUBGROUP_AGE_BANDS = ((18, 45), (45, 65), (65, 75), (75, 200))
EICU_SUBGROUP_LABEL = ("[MEASURE] POST-HOC SUBGROUP DESCRIPTIVES (2026-08-20): "
                       "computed after the extract was read; certifies "
                       "nothing, settles no registered prediction or failure "
                       "criterion, and no certified quantity descends from "
                       "it. Rates in cells below the frozen "
                       "EICU_MIN_OUTCOME_STRATUM record floor are suppressed "
                       "as null, never 0.0.")

# Post-hoc attribution value-function contrast. The deployed attributions are
# interventional Shapley values (explain.py). This block measures how far the
# conditional values -- the Gaussian value function of Aas et al. 2021 -- move
# the abstention-driver reading on the top k drivers.
# The driver set uses the same rule and depth as abstention_gap_ranking, so the
# cross-check below covers every feature in the sub-game, and the covariance
# comes from S_train only.
# Same A6 discipline as the subgroups block: labeled in two places, certifies
# nothing, consumes no _rng draw.
# Ref: SPEC pin amendment, 2026-08-21 venue-fit pass; decision-letter item 9 /
# S1-12; audit V20.
EICU_FAITHFULNESS_TOP_K = 10     # 2^10 coalitions, enumerated exactly
EICU_FAITHFULNESS_LABEL = (
    "[MEASURE] POST-HOC ATTRIBUTION VALUE-FUNCTION CONTRAST (2026-08-21): "
    "computed after the extract was read; certifies nothing, settles no "
    "registered prediction or failure criterion, and no certified quantity "
    "descends from it. Interventional (deployed) vs Gaussian-conditional "
    "Shapley values on the top-k abstention drivers; the Gaussian conditional is "
    "an APPROXIMATION for binary and __missing indicator features.")

# Executable forms of the pre-declared failure criteria. They are literals here
# rather than prose in a paper, so a run cannot quietly skip an alarm registered
# against it before the data arrived.
# Ref: EICU-PROTOCOL section 10.
EICU_FB_MIN_COVERAGE = 0.20      # F-B: a certificate at 5% coverage is a decline in a hat
EICU_FD_COVERAGE_ALARM = 0.90    # F-D leg 3: alpha=0.05 + coverage > this ...
EICU_FD_RM_ALARM = 0.01          # ... + fresh-pool R_M under this = LEAK ALARM
EICU_FE_MIN_SITES = 200          # F-E: below this the estimand's population moved

# F-D legs 1 and 2. Both depend on neither alpha nor coverage, and both are
# computed every replicate on the real extract rather than only inside pytest.
# They exist because a single-leg F-D conditioned on alpha == ALPHA_LADDER[0],
# coverage > 0.90 and R_M < 0.01 let a leak certifying alpha = 0.10 at coverage
# 0.86 pass underneath it, demonstrated in-harness with outcome-correlated
# APACHE-row absence.
# Ref: audit E-10 (2026-07-31).
EICU_LEAK_AUC_CEILING = 0.90      # APACHE-IVa, a purpose-built day-1 score, reaches
                                  # ~0.87 on eICU hospital mortality. A 161-column
                                  # logistic head that beats it from the same inputs
                                  # is a leak before it is a result
EICU_LEAK_ABLATION_MAX_DROP = 0.05
                                  # most AUC the 49 missingness/presence columns may
                                  # cost when ablated. Measured on the mock: clean
                                  # -0.016, outcome-correlated absence +0.082 at
                                  # p=0.30 and +0.248 at p=0.75
EICU_COVERAGE_BANDS = (0.0, 0.2, 0.5, 0.8, 1.0)   # APACHE per-site coverage bands
EICU_TOP_GAP_FEATURES = 10       # abstention_gap_ranking depth (settles P4)
# apachePredVar treatment/intervention flags whose measurement timing relative
# to the outcome cannot be cited to a source. activetx encodes active treatment
# versus comfort measures -- a decision made during the stay and adjacent to
# death by definition.
# They stay on the allowlist only as long as outcome_screen clears them. Their
# univariate AUC goes to EICU_diagnostics.json every run, so the question is
# answered from the data rather than from a DDL comment.
# Ref: audit E-19 (2026-07-31).
EICU_TIMING_UNVERIFIED = ("activetx", "thrombolytics", "graftcount",
                          "electivesurgery", "ventday1", "oobventday1",
                          "oobintubday1", "ima", "midur")
EICU_PALETTE = ("#4477aa", "#cc6677", "#ee8866", "#228833", "#aa3377",
                "#66ccee")

_SUMMARY_BLOCK_RE = re.compile(r"^## (EICU-[A-Z]+)[^\n]*\n(```json\n.*?\n```)",
                               re.S | re.M)


# ------------------------------------------------------- compliance gate ---

def assert_aggregate_only(obj, where) -> None:
    """Recursively refuse record-level data on the way out.

    Raises EicuError (reason=record-level-output) if obj carries any
    EICU_FORBIDDEN_OUT_KEYS key, or any list/tuple/ndarray longer than
    EICU_MAX_OUTPUT_LEN. Every write in this module goes through it.

    The length cap catches a per-record array smuggled into a payload. It is
    applied to each CSV row rather than to a row list, because the number of
    rows is itself an aggregate quantity -- replicates x hospitals x rungs
    legitimately exceeds 512 at --replicates 20. Any single cell carrying 512+
    values is a record-level array by construction.

    Refs: SPEC "Real-data protocol"; threat T-17."""
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

    numpy scalars and arrays become python. Tuples and sets become lists, with
    sets sorted -- an unsorted set would make the artifact non-deterministic
    across interpreter runs. Non-finite floats become None, so every artifact is
    strict json: None for uncomputable, never 0.0 and never NaN.
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


def _write_json(path, payload, where, *, per_item_keys=()):
    """Gate then write one JSON artifact (indent=2, deterministic key order).

    per_item_keys names top-level keys whose value is a list of aggregate items,
    one per replicate say. Those lists are gated item by item rather than as one
    sequence, for the reason assert_aggregate_only gives for CSV rows: the
    number of items is itself aggregate, while a single item carrying 512+
    values is record-level by construction. The key still appears in the gated
    envelope under a placeholder, so it is still checked against
    EICU_FORBIDDEN_OUT_KEYS; only the length cap is relaxed, and only for the
    named keys.

    Each item must be a dict. The per-item gate is a no-op on scalars, so a flat
    float list under a named key would otherwise slip through ungated.
    """
    ready = _json_ready(payload)
    if per_item_keys and isinstance(ready, dict):
        envelope = {
            k: (f"<{len(v)} items gated individually>"
                if k in per_item_keys and isinstance(v, list) else v)
            for k, v in ready.items()}
        assert_aggregate_only(envelope, where)
        for key in per_item_keys:
            items = ready.get(key)
            if isinstance(items, list):
                for i, item in enumerate(items):
                    # Only a dict -- one aggregate payload per replicate -- is a
                    # sanctioned item shape; see the docstring for why.
                    if not isinstance(item, dict):
                        raise etl.EicuError(
                            f"run_eicu._write_json: {where}.{key}[{i}] is a "
                            f"{type(item).__name__}, not a dict -- per_item_keys "
                            f"items must each be one aggregate payload "
                            f"(reason=record-level-output)")
                    assert_aggregate_only(item, f"{where}.{key}[{i}]")
    else:
        assert_aggregate_only(ready, where)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(ready, fh, indent=2)
        fh.write("\n")


def _write_table(path, rows, fieldnames, where):
    """Write one eICU CSV, ASCII-strict and gated row by row.

    A deliberate deviation from run_synthetic._write_csv, which uses the locale
    default (cp1252 on this host). eICU categorical literals may carry
    non-ASCII, and cp1252 would encode them into a cell that reads back as
    mojibake instead of failing. All eICU cell content is ASCII by construction
    -- site labels, numbers, reason tags, and categorical levels never reach a
    cell -- so a non-ASCII cell means the protocol was violated upstream.

    Cells are validated before the file is opened, so the failure names the
    offending column instead of raising mid-stream on a truncated table.
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
    """Render one CSV cell: None -> empty, numpy scalar -> python.

    A non-finite float is empty too, never the literal nan token a reader would
    parse as a number. Empty keeps the empty-bin discipline across the trip.
    """
    if v is None:
        return ""
    if isinstance(v, np.generic):
        v = v.item()
    if isinstance(v, float) and not np.isfinite(v):
        return ""
    return v                    # bools render True/False, as every house CSV does


# --------------------------------------------------------------- helpers ---

def _say(verbose, msg, err=False):
    """Console line with the literal `[eicu] ` prefix (SPEC "Real-data protocol")."""
    if verbose or err:
        print(f"[eicu] {msg}", file=(sys.stderr if err else sys.stdout))


def _alpha_key(alpha):
    """Rung key as a string, "0.05" or "0.1", matching diagnostic["feasibility"].

    A float dict key survives json.dump only by silent stringification, and
    str(0.10) is "0.1"."""
    return str(float(alpha))


def _site_sort_key(label):
    """Deterministic, readable ordering for hosp-<int> labels.

    Sorts by the numeric suffix when it parses, else by the raw string. Never
    hash order."""
    text = str(label)
    if text.startswith(etl.EICU_SITE_PREFIX):
        tail = text[len(etl.EICU_SITE_PREFIX):]
        if tail.lstrip("+-").isdigit():
            return (0, int(tail), "")
    return (1, 0, text)


def _row_for(report, alpha):
    """The certified-tier row for one rung, or None on a gated report."""
    for r in report["certified"]:
        if r["alpha"] == alpha:
            return r
    return None


def _reasons_text(reasons):
    """{mode: reason} -> a compact ASCII cell, ordered by mode name."""
    if not reasons:
        return None
    return "|".join(f"{m}:{r or 'declined'}" for m, r in sorted(reasons.items()))


def _noncontributing_text(mode_outcomes):
    """Why a mode did not back the deployed threshold, on a certified row.

    On real data a silent BBSE non-contribution is the interesting signal. A
    certified row whose BBSE arm declined must still say so, or prediction P3
    is unsettleable from the released tables.

    Refs: report.py _combine_alpha's mode_outcomes; fixture audit 2026-07-25."""
    if not mode_outcomes:
        return None
    parts = [f"{m}:{o}" for m, o in sorted(mode_outcomes.items())
             if o != "covering"]
    return "|".join(parts) if parts else None


def _eval_rung(head, report, alpha, pool_x, pool_y):
    """Score one rung of one report against the oracle labels of its pool.

    The eICU analogue of run_synthetic._cert_eval, plus the fields the eICU
    tables carry: tau_idx, deploy_mode, modes, and the non-contributing-mode
    text. Structural gates are read from report["reason"] and rung outcomes
    from row["status"] -- a tier == "certified" row can still be
    status == "declined"."""
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


# Identity binding, not a re-implementation: the ETL's tie-averaged
# Mann-Whitney AUC, bound by name so a clone cannot drift from it.
# tests/test_eicu_path.py asserts that identity.
# Ref: SPEC module DAG note.
_auc = etl._rank_auc


def _missingness_columns(feature_names):
    """Indices of the 49 missingness/presence columns, and of the rest.

    The 49 are the 43 __missing siblings, age__missing and friends, and the two
    presence flags. E-9 identified this channel as jointly site- and
    outcome-informative: the day-1 APACHE window does not close for a stay that
    ends because the patient died, so whole-row absence is a partial outcome
    proxy with no column name. Ablating them is the leak probe with the power
    the AUC ceiling alone lacks."""
    miss = [j for j, n in enumerate(feature_names)
            if n.endswith("__missing") or n in ("aps_present", "apv_present")]
    keep = [j for j in range(len(feature_names)) if j not in set(miss)]
    return miss, keep


def _leak_probe(train, cal, feature_names):
    """The alpha- and coverage-independent leak alarm (F-D legs 1 and 2, E-10).

    Fits the head on train and scores it out of sample on the site-disjoint
    calibration split. Then refits with the missingness/presence block ablated
    and reports the AUC that costs. Both numbers reach EICU_pooled.csv and
    EICU_diagnostics.json, so the check exists on the real extract, where the
    mock's Bayes-optimal ceiling does not apply and only a runtime number can
    bound it."""
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
    """Derive the EICU-PREFLIGHT and EICU-PREDICTIONS sections (threat T-18).

    The predictions block is written in preflight mode, before any certificate
    exists. A pre-registration that could be edited after the data landed is not
    a pre-registration."""
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
    """Profile an extract and write the pre-registration, certifying nothing.

    etl.preflight streams all five tables and returns an aggregate-only profile.
    This wrapper gates it, writes EICU_preflight.json and the EICU-PREFLIGHT and
    EICU-PREDICTIONS sections of EICU-SUMMARY.md, then returns the preflight
    dict unchanged -- its key set is frozen by the ETL contract.

    reference_check=True turns a row-count, site-count or patient-count mismatch
    against EICU_REFERENCE_* into an EicuError
    (reason=reference-row-count-mismatch). Pass it for the real extract; drop it
    with --no-reference-check for the mock corpus. That raise is the
    pre-declared protocol failure F-C: the run stops and writes no numbers."""
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

    The full five-table check belongs to preflight. Here the ledger's first step
    already carries the raw patient row count and hospital count, so a wrong
    download or a v2.0.1 extract is visible for free. It is reported, never
    raised: run_certification's signature has no off-switch, and the mock corpus
    legitimately fails it."""
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
    """Attrition ledger rows in the frozen step order (SPEC EICU_ATTRITION_STEPS)."""
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
    """Per-site APACHE coverage and missingness, from the contracted arrays.

    Those arrays are site_raw, aps_present and apv_present. They are read here
    rather than from meta['site_meta'], so the per-site table and the dispersion
    diagnostic come from one code path. Site-informative missingness is the
    covariate-shift channel CertGate v2 scope-cut (threat T-3): it must be
    measured, never imputed away."""
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
    """Per-site mean share of NaN across the imputable feature columns.

    Its dispersion across hospitals is the site-informative-missingness
    diagnostic the protocol registers as threat T-3. Measured on the raw matrix,
    before impute erases the evidence."""
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
    """Site counts per APACHE-coverage band, plus the zero-coverage count.

    Those zero-coverage hospitals are what an APACHE filter would delete
    (threat T-4)."""
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
    """Site-constant hospital covariates, read from the hospital table.

    SPEC A.6: the hospital table contributes no features. numbedscategory,
    teachingstatus and region are site-constant, so under a site-as-unit design
    their coefficients would be identified from ~75 between-site observations
    rather than ~60k records. They are also the cleanest site proxies available.

    They are read here as strata for the per-site diagnostic table only, through
    the ETL's own contracted reader. No second CSV parser, no undeclared
    dependency, and the values never touch x. Missing or unreadable strata
    degrade to None cells plus a warning, because a diagnostic must not abort a
    certification run."""
    out = {}
    reader = getattr(etl, "read_table", None)
    if reader is None:                   # explicit, so a real AttributeError
        warnings.append(                 # from inside the reader still surfaces
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
    """The three site-constant covariates for one site, or None cells.

    The hospital table is the source of record. meta['site_meta'] is consulted
    second, in case a future ETL carries them there. Nothing is guessed: a site
    with no row in either yields empty cells and increments the miss count, so
    an all-empty stratum column shows up in the diagnostics rather than reading
    as silently blank."""
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
    """Top abstention drivers at tau (settles prediction P4).

    Computed with explain.cohort_abstention_profile at every certified rung, not
    only the operative one the report happens to carry. An empty answered or
    declined population yields an empty ranking, never an argsort of an all-NaN
    gap -- that fabricated feature 0 as the top driver (audit V22)."""
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
    """The BBSE outcome for one report, including why it declined.

    diagnostic["bbse"] is None wholesale on a gated exit, and otherwise carries
    the stable key set. So every key is indexable, and None means "not computed"
    rather than KeyError (audit V25)."""
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
    """Certificate-level projection of one report, with arrays stripped.

    answered_mask is replaced by its .sum() (threat T-17). The key itself does
    not survive -- it is in EICU_FORBIDDEN_OUT_KEYS -- so the count is emitted
    as n_answered and the compliance gate stays a gate, not a special case."""
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
    """from_raw for the four splits, then the site-disjointness assertion.

    require_both_classes=False is used for the target pool only. A single
    held-out hospital may legitimately be all-Alive at ~9% prevalence, and that
    opt-in is the sole sanctioned relaxation. Labels flow as raw two-valued
    strings so coerce_labels owns the two-value contract; a hand-built bool
    array would bypass it."""
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

    predictedhospitalmortality is a VARCHAR holding a probability. The ETL has
    already run it through float() -- a string comparison is threat T-9 -- and
    mapped -1 to NaN. Coverage of that column is site-correlated, so the
    comparator is scored on the answered records that carry it, and the
    subset-matched CertGate error is reported beside it rather than compared
    across different denominators."""
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
    """Failure criteria F-A..F-E, evaluated in code (EICU-PROTOCOL section 10).

    They were registered before the data arrived, so they are computed here
    rather than argued after the fact. F-A is deliberately written as a
    bound-shaped observation: 20 replicates cannot resolve a delta = 0.05 rate,
    and they share one hospital population, so they are not independent draws of
    the calibration site population."""
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
    # E-10: the two legs that depend on neither alpha nor coverage. One row per
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


def _reliability_figure(out, panel_payloads, verbose):
    """The post-hoc panel figure; its title carries the label.

    A real-extract figure must carry that label on its face, not only in the
    JSON beside it.

    The empty-bin, ci_status and clamped-half-width rules are not restated here.
    They live once in rp.panel_reliability_series and rp.panel_ci_halfwidths,
    which run_synthetic's E6 figure reads too. That matters beyond tidiness: an
    unclamped half-width makes matplotlib raise, and this function runs inside
    run_certification before the summary is written, so a descriptive figure
    would take a 20-replicate certified run down with it."""
    if not panel_payloads:
        # A previous run into the same --out may have left its own panel figure
        # here. With zero panels this run, that stale PNG would sit beside an
        # EICU-SUMMARY.md reporting n_panels: 0 and read as current output.
        # Remove it rather than leave last run's curves in place.
        stale = os.path.join(out, f"{EICU_OUT_PREFIX}_reliability_panel.png")
        if os.path.exists(stale):
            os.remove(stale)
            _say(verbose, f"removed stale {EICU_OUT_PREFIX}"
                          f"_reliability_panel.png (no panels this run)")
        return
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(12, 4))
    # The joined curve is the lowest-numbered replicate present, named on the
    # axis title. Under RP-8 replicate 0's panel can be skipped, and a
    # hard-coded "replicate 0" label would then claim another replicate's curve.
    base = min(panel_payloads, key=lambda p: p["replicate"])
    axL.plot([0.0, 1.0], [0.0, 1.0], "k--", lw=1, label="identity")
    for scope, colour in zip(rp.PANEL_CURVE_SCOPES,
                             (EICU_PALETTE[0], EICU_PALETTE[1])):
        labelled = False
        for payload in panel_payloads:
            xs, ys, _lo, _hi = rp.panel_reliability_series(payload, scope)
            if not xs:
                continue
            # The legend entry goes to the first payload that actually plots
            # this scope, not to base. Under RP-8 base is merely whichever
            # replicate survived. If it answered nothing -- every answered bin
            # empty, a shape the runner really produces when no rung certifies
            # -- a base-only label would leave the scope as unlabelled scattered
            # dots with no key. label=None is matplotlib's "omit from legend".
            label = None if labelled else scope
            labelled = True
            if payload is base:
                axL.plot(xs, ys, "o-", color=colour, label=label)
            else:
                axL.plot(xs, ys, ".", color=colour, alpha=0.4, ms=5,
                         label=label)
    axL.set_title(f"reliability curve (replicate {base['replicate']} joined; "
                  f"others scattered)")
    axL.set_xlabel("mean predicted P(death)")
    axL.set_ylabel("observed positive rate")
    axL.legend(fontsize=8)

    labels, values, los, his = [], [], [], []
    for payload in panel_payloads:
        ref = (payload["brier"] or {}).get("reference")
        if ref is None or ref.get("brier_difference") is None:
            continue
        labels.append(str(payload["replicate"]))
        values.append(float(ref["brier_difference"]))
        # Clamped via the shared helper. brier_difference is a paired
        # ratio-of-sums over 24 sites, and its percentile interval need not
        # straddle the full-sample point estimate. A raw subtraction goes
        # negative there, and matplotlib raises rather than warns, which would
        # abort this run before EICU-SUMMARY.md is written.
        d_lo, d_hi = rp.panel_ci_halfwidths(
            values[-1], (ref.get("ci") or {}).get("brier_difference"),
            ref.get("ci_status"))
        los.append(d_lo)
        his.append(d_hi)
    if values:
        axR.errorbar(labels, values, yerr=[los, his], fmt="o",
                     color=EICU_PALETTE[5], capsize=3)
        axR.axhline(0.0, color="black", lw=1)
    else:
        axR.text(0.5, 0.5, "no reference-matched Brier", ha="center",
                 va="center", color="dimgray", transform=axR.transAxes)
    axR.set_title("paired Brier difference, APACHE-IVa minus head\n"
                  "(denominator-matched, answered set)", fontsize=10)
    axR.set_xlabel("replicate")
    axR.set_ylabel("brier_difference")
    fig.suptitle("POST-HOC (2026-08-01) selective reliability panel -- "
                 "descriptive; certifies nothing", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(out,
                             f"{EICU_OUT_PREFIX}_reliability_panel.png"),
                dpi=rp.FIG_DPI)
    plt.close(fig)
    _say(verbose, f"wrote {EICU_OUT_PREFIX}_reliability_panel.png")


def _figures(out, pooled_rows, per_site_rows, panel_payloads, verbose):
    """Three figures: matplotlib Agg, house palette, no seaborn.

    The third is the post-hoc panel figure (SPEC Experiments)."""
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
    _reliability_figure(out, panel_payloads, verbose)


def _pooled_summary(pooled_rows, *, arm, replicates, n_records, n_sites,
                    site_counts, warnings):
    """The EICU-POOLED payload: per-rung rollup plus the pre-declared verdicts."""
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
        for x in rows:                    # why a mode did not contribute (P3)
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
    """The EICU-PERSITE payload.

    Carries the between-hospital dispersion the certificate deliberately does
    not bound (audit V1), plus the pool-too-small count that settles P5."""
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


def _panel_ci_statuses(node, sink):
    """Collect every ci_status emitted anywhere in a panel payload.

    A degenerate-resamples or truncated-resamples event is invisible in a
    headline scalar: the value is still there, only its interval is gone. So the
    summary counts the whole vocabulary, not the point estimates alone."""
    stack = [node]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            status = item.get("ci_status")
            if isinstance(status, str):
                sink[status] = sink.get(status, 0) + 1
            stack.extend(item.values())
        elif isinstance(item, (list, tuple)):
            stack.extend(item)


def _reliability_summary(panel_payloads, *, arm, replicates, pooled_rows):
    """The EICU-RELIABILITY payload: the post-hoc panel, rolled up.

    Descriptive only. Nothing here is certified and nothing settles a frozen
    prediction. The block leads with rp.POST_HOC_LABEL because a separate
    summary section inherits no label from the run warnings.

    Distributions across replicates go through _summary_stats, where the median
    is p50. An undefined statistic is None, never 0.0.

    consistency is reported, never raised. The panel's DECISION_THRESHOLD = 0.5
    is Head.predict's own rule, so skill.answered.model_error_rate and the
    pooled row's answered_err_rate at the operative rung are the same quantity.

    They are not the same number, because they round differently: _rate gives
    the pooled row 4 dp and the emit pass gives the panel 6. A gap up to 5e-05
    is arithmetic, not a finding -- measured on the real extract at 1.5e-05,
    from 0.041885 against a pooled 0.0419. A gap materially above that is a lead
    to chase, still never a crash mid-run."""
    out = {
        "post_hoc": rp.POST_HOC_LABEL,
        "arm": arm,
        "replicates": int(replicates),
        "n_panels": len(panel_payloads),
        "scope": ("pooled target arm only (K = "
                  f"{etl.EICU_N_TARGET_SITES} hospitals >= "
                  f"MIN_SITES_FOR_CI = {rp.MIN_SITES_FOR_CI}); the "
                  "per-hospital arm is K = 1, where every interval would be "
                  "floor-suppressed at 24x the cost"),
        "settings": {"schema_version": rp.SCHEMA_VERSION,
                     "seed": rp.PANEL_SEED,
                     "n_boot": rp.N_BOOT,
                     "ci_level": rp.CI_LEVEL,
                     "bin_edges": list(rp.DEFAULT_BIN_EDGES),
                     "decision_threshold": rp.DECISION_THRESHOLD,
                     "bootstrap_unit": "site"},
        "brier_difference_note": (
            "brier.reference.brier_difference is a SINGLE paired statistic "
            "from ONE resample stream (reference minus primary on the "
            "IDENTICAL availability mask). It must never be reconstructed by "
            "differencing brier.primary_answered, whose denominator is the "
            "wider answered set (panel notes[4])."),
        "skill_margin_note": (
            "skill_margin = constant-majority baseline error rate MINUS model "
            "error rate. At single-digit prevalence a low answered error rate "
            "is also what a constant always-negative rule achieves, so the "
            "margin -- not the error rate -- is what says whether the gate "
            "earned its answered set or merely selected an easy one."),
        # RP-9: the panel's own disclosures travel inside each payload of
        # EICU_reliability_panel.json, one copy per replicate. EICU-SUMMARY.md
        # is the human-facing artifact, and a reader of it would otherwise get
        # the numbers without the estimand text that governs them. notes[1]
        # matters most -- marginal intervals, never difference two endpoints --
        # since this block prints brier_reference, brier_primary_matched and
        # brier_difference side by side.
        "notes": list(rp.NOTES),
        # The replicates are re-splits of one hospital population on one
        # extract, so the _summary_stats spread below is split-to-split
        # variation, not sampling uncertainty. _failure_criteria states the same
        # non-independence for F-A. Saying it in one place only would let a
        # p10-p90 band beside the panel's own bootstrap intervals read as a
        # second uncertainty quantification.
        "replicate_spread_note": (
            "sd / p10 / p50 / p90 below are taken ACROSS REPLICATES, which are "
            "re-splits of ONE hospital population on ONE extract and are "
            "therefore NOT independent draws. That spread is split-to-split "
            "variation, not sampling uncertainty. The cluster-bootstrap `ci` "
            "fields are the only intervals here with a coverage claim."),
    }
    if not panel_payloads:
        # Two paths reach n_panels == 0 and the count alone does not separate
        # them, so the note below must name both. Either every panel was skipped
        # under RP-8 -- the case a real extract actually meets -- or the arm ran
        # no replicates at all, reachable only by calling this helper directly
        # (run_certification refuses replicates < 1 with reason=bad-replicates).
        out["note"] = (
            f"no panel was produced (replicates = {int(replicates)}). With "
            "replicates >= 1 this means EVERY replicate's panel was SKIPPED "
            "under RP-8 -- a DESCRIPTIVE layer may never abort the certified "
            "run, so a PanelError is swallowed, recorded and that replicate's "
            "panel dropped; the reason for each is in the run warnings "
            "(EICU_diagnostics.json and the EICU-POOLED block) tagged "
            "'[MEASURE] RP-8', and on stderr. The other way to land here is an "
            "arm that ran no replicates at all, reachable only by calling this "
            "helper directly (run_certification refuses replicates < 1 with "
            "reason=bad-replicates). No certified quantity is affected either "
            "way.")
        return out

    heads = [rp.panel_headline(p) for p in panel_payloads]
    refs = [(p["brier"] or {}).get("reference") for p in panel_payloads]

    def _pick(seq, key):
        return [None if d is None else d.get(key) for d in seq]

    out["n_sites"] = _summary_stats([p["counts"]["n_sites"]
                                     for p in panel_payloads])
    out["coverage"] = _summary_stats(_pick(heads, "coverage"))
    out["ece_answered"] = _summary_stats(_pick(heads, "ece_answered"))
    out["ece_declined"] = _summary_stats(_pick(heads, "ece_declined"))
    out["calibration_slope_answered"] = _summary_stats(
        _pick(heads, "calibration_slope_answered"))
    status_counts = {}
    for h in heads:
        s = h["calibration_status_answered"]
        status_counts[s] = status_counts.get(s, 0) + 1
    out["calibration_status_answered_counts"] = status_counts
    out["fit_statuses"] = list(rp.FIT_STATUSES)
    out["brier_answered"] = _summary_stats(_pick(heads, "brier_answered"))
    out["brier_reference"] = _summary_stats(_pick(refs, "brier_reference"))
    out["brier_primary_matched"] = _summary_stats(
        _pick(refs, "brier_primary_matched"))
    out["brier_difference"] = _summary_stats(_pick(refs, "brier_difference"))
    out["brier_available_share"] = _summary_stats(
        _pick(refs, "available_share"))
    # This key is named for what it holds: the whole three-name interval dict
    # from the shared reference stream -- brier_reference,
    # brier_primary_matched and brier_difference. Naming it
    # brier_difference_ci_... would invite a reader to take the first nested
    # interval for the paired-difference one, the confusion notes[4] and
    # brier_difference_note exist to prevent. The paired interval is the
    # brier_difference member inside.
    # Keyed by the payload's own replicate field, never by position. Under RP-8
    # a skipped replicate-0 panel drops out of panel_payloads, and refs[0] would
    # then publish another replicate's interval under this name.
    ref0 = next((ref for p, ref in zip(panel_payloads, refs)
                 if p["replicate"] == 0), None)
    out["brier_reference_ci_replicate0"] = (
        None if ref0 is None else ref0.get("ci"))
    out["skill_margin_answered"] = _summary_stats(
        _pick(heads, "skill_margin_answered"))
    out["skill_margin_all"] = _summary_stats(
        [p["skill"]["all"]["skill_margin"] for p in panel_payloads])
    out["skill_contrast_answered_minus_all"] = _summary_stats(
        _pick(heads, "skill_margin_answered_minus_all"))
    out["skill_contrast_answered_minus_declined"] = _summary_stats(
        [p["skill"]["contrast"]["answered_minus_declined"]
         for p in panel_payloads])

    ci_status_counts = {}
    for p in panel_payloads:
        for key in ("reliability", "calibration", "ece", "brier", "skill",
                    "composition"):
            _panel_ci_statuses(p.get(key), ci_status_counts)
    out["ci_status_counts"] = ci_status_counts
    out["ci_statuses"] = list(rp.CI_STATUSES)

    gaps = []
    for p in panel_payloads:
        alpha = p.get("operative_alpha")
        if alpha is None:
            continue
        panel_err = p["skill"]["answered"]["model_error_rate"]
        for row in pooled_rows:
            if (row["replicate"] == p["replicate"] and row["alpha"] == alpha
                    and row["answered_err_rate"] is not None
                    and panel_err is not None):
                gaps.append(abs(float(panel_err)
                                - float(row["answered_err_rate"])))
    out["consistency"] = {
        "max_abs_gap_panel_vs_pooled_answered_err": (
            round(max(gaps), 6) if gaps else None),
        "n_compared": len(gaps),
        "note": ("panel skill.answered.model_error_rate vs the pooled row's "
                 "answered_err_rate at the OPERATIVE rung. The panel's "
                 "DECISION_THRESHOLD = 0.5 is Head.predict's own rule, so the "
                 "two are the SAME quantity and the gap is pure rounding: the "
                 "pooled row goes through _rate (4 dp) and the panel through "
                 "the emit pass (6 dp), so anything up to 5e-05 is expected "
                 "and is NOT a finding. A gap materially above that means the "
                 "two are no longer measuring the same thing. REPORTED, never "
                 "raised -- on real data this is a lead to chase, not a crash "
                 "mid-run.")}
    return out


def _subgroup_masks(x, feature_names):
    """Marginal subgroup masks from the allowlisted columns (SPEC rev-2 3b).

    One-hot equality for the categorical dimensions. Age is banded only on rows
    whose age__missing sibling is 0, because imputed ages carry the S_train mean
    and must not be banded."""
    idx = {n: i for i, n in enumerate(feature_names)}
    masks = {}
    age = x[:, idx["age"]]
    miss = (x[:, idx["age__missing"]] == 1.0 if "age__missing" in idx
            else np.zeros(len(x), dtype=bool))
    bands = {}
    for lo, hi in EICU_SUBGROUP_AGE_BANDS:
        label = f"{lo}-{hi - 1}" if hi < 200 else f"{lo}+"
        bands[label] = (~miss) & (age >= lo) & (age < hi)
    masks["age_band"] = bands
    for dim in EICU_SUBGROUP_DIMS[1:]:
        prefix = dim + "="
        levels = {}
        for name, col in idx.items():
            if name.startswith(prefix):
                levels[name[len(prefix):] or "EMPTY"] = x[:, col] == 1.0
        masks[dim] = levels
    return masks


def _subgroup_rows(head, target, feature_names, tau, replicate, arm):
    """Post-hoc per-replicate subgroup descriptives, pooled arm only.

    Computed at the deployed operative tau. A whole cell below the frozen floor
    emits null rates with status suppressed-below-floor; an answered or declined
    scope below the floor emits null for that scope's rates while the cell stays
    ok. Null means suppressed-or-undefined, never 0.0 (panel NOTES[6])."""
    floor = etl.EICU_MIN_OUTCOME_STRATUM
    rows = []
    if tau is not None:
        ans = head.score(target.x) >= tau
        err = head.predict(target.x) != target.y
    for dim in EICU_SUBGROUP_DIMS:
        levels = _subgroup_masks(target.x, feature_names)[dim]
        for level in sorted(levels):
            m = levels[level]
            n = int(m.sum())
            row = dict(post_hoc=EICU_SUBGROUP_LABEL, replicate=replicate,
                       arm=arm, dim=dim, level=level, n=n, n_answered=None,
                       coverage=None, answered_err_rate=None,
                       answered_pos_rate=None, declined_err_rate=None,
                       declined_pos_rate=None, status="ok")
            if tau is None:
                row["status"] = "no-certificate"
            elif n < floor:
                row["status"] = "suppressed-below-floor"
            else:
                a, d = m & ans, m & ~ans
                na, nd = int(a.sum()), int(d.sum())
                row["n_answered"] = na
                row["coverage"] = round(na / n, 4)
                if na >= floor:
                    row["answered_err_rate"] = round(float(err[a].mean()), 4)
                    row["answered_pos_rate"] = round(
                        float(target.y[a].mean()), 4)
                if nd >= floor:
                    row["declined_err_rate"] = round(float(err[d].mean()), 4)
                    row["declined_pos_rate"] = round(
                        float(target.y[d].mean()), 4)
            rows.append(row)
    return rows


def _subgroup_summary(rows, *, arm):
    """EICU-SUBGROUPS block: pooled over replicates, one entry per level.

    Suppression is counted arithmetically, mirroring EICU-RELIABILITY's
    n_panels shortfall discipline."""
    out = {"post_hoc": EICU_SUBGROUP_LABEL, "arm": arm,
           "floor": etl.EICU_MIN_OUTCOME_STRATUM,
           "dims": {}, "n_cells_suppressed_whole": sum(
               1 for r in rows if r["status"] == "suppressed-below-floor")}
    for dim in EICU_SUBGROUP_DIMS:
        levels = {}
        for level in sorted({r["level"] for r in rows if r["dim"] == dim}):
            sub = [r for r in rows if r["dim"] == dim and r["level"] == level]
            cov = [r["coverage"] for r in sub if r["coverage"] is not None]
            aerr = [r["answered_err_rate"] for r in sub
                    if r["answered_err_rate"] is not None]
            apos = [r["answered_pos_rate"] for r in sub
                    if r["answered_pos_rate"] is not None]
            levels[level] = dict(
                n_mean=round(float(np.mean([r["n"] for r in sub])), 1),
                n_replicates=len(sub),
                coverage_mean=round(float(np.mean(cov)), 4) if cov else None,
                coverage_min=round(float(np.min(cov)), 4) if cov else None,
                answered_err_mean=round(float(np.mean(aerr)), 4)
                if aerr else None,
                answered_pos_mean=round(float(np.mean(apos)), 4)
                if apos else None,
                n_answered_rates_suppressed=sum(
                    1 for r in sub if r["status"] == "ok"
                    and r["answered_err_rate"] is None))
        out["dims"][dim] = levels
    return out


def _spearman(a, b):
    """Spearman rank correlation by hand (numpy only; ties average-ranked)."""
    def rank(v):
        v = np.asarray(v, dtype=np.float64)
        order = np.argsort(v, kind="mergesort")
        r = np.empty(len(v))
        r[order] = np.arange(len(v), dtype=np.float64)
        for val in np.unique(v):          # average ranks over ties
            m = v == val
            r[m] = r[m].mean()
        return r
    ra, rb = rank(a), rank(b)
    ra -= ra.mean()
    rb -= rb.mean()
    den = float(np.sqrt((ra ** 2).sum() * (rb ** 2).sum()))
    return round(float((ra * rb).sum() / den), 6) if den > 0 else None


def _faithfulness_rows(head, train, target, feature_names, tau, replicate, arm,
                       k=EICU_FAITHFULNESS_TOP_K):
    """Post-hoc per-replicate value-function contrast, pooled arm only.

    Computed at the deployed operative tau. One row per selected feature carries
    mean |phi| on the answered and declined sets, the answered-minus-declined
    gap under both value functions, and the feature's driver rank under each.
    Returns (rows, scalars); rows are empty when no rung certified or either
    population is empty, because no ranking is fabricated (audit V22)."""
    if tau is None:
        return [], dict(status="no-certificate", replicate=replicate)
    coef = np.asarray(head.coef, dtype=np.float64)
    ans = head.score(target.x) >= float(tau)
    if not ans.any() or ans.all():
        return [], dict(status="empty-population", replicate=replicate)
    # the sub-game is the emitted driver set: same rule and depth as
    # _abstention_ranking (cohort_abstention_profile's gap_ranking[:k])
    sel = np.asarray(cohort_abstention_profile(head, target.x, ans)
                     ["gap_ranking"], dtype=int)[:int(k)]
    z_train = ((np.asarray(train.x, dtype=np.float64) - head.mu)
               / head.sd)[:, sel]
    cov = z_train.T @ z_train / z_train.shape[0]
    z = ((np.asarray(target.x, dtype=np.float64) - head.mu) / head.sd)[:, sel]
    phi_int = z * coef[sel]
    phi_cond = z @ gaussian_conditional_shapley_matrix(coef[sel], cov).T
    out = {}
    for name, phi in (("int", phi_int), ("cond", phi_cond)):
        m_ans = np.abs(phi[ans]).mean(axis=0)
        m_dec = np.abs(phi[~ans]).mean(axis=0)
        gap = m_ans - m_dec
        rank = np.empty(len(sel), dtype=int)
        rank[np.argsort(-np.abs(gap), kind="mergesort")] = \
            np.arange(1, len(sel) + 1)
        out[name] = (m_ans, m_dec, gap, rank)
    rows = []
    for i, j in enumerate(sel.tolist()):
        rows.append(dict(
            post_hoc=EICU_FAITHFULNESS_LABEL, replicate=replicate, arm=arm,
            feature=feature_names[j], coef=round(float(coef[j]), 6),
            mean_abs_phi_answered_int=round(float(out["int"][0][i]), 6),
            mean_abs_phi_declined_int=round(float(out["int"][1][i]), 6),
            gap_int=round(float(out["int"][2][i]), 6),
            rank_int=int(out["int"][3][i]),
            mean_abs_phi_answered_cond=round(float(out["cond"][0][i]), 6),
            mean_abs_phi_declined_cond=round(float(out["cond"][1][i]), 6),
            gap_cond=round(float(out["cond"][2][i]), 6),
            rank_cond=int(out["cond"][3][i])))
    corr = np.corrcoef(z_train, rowvar=False)
    off = np.abs(corr - np.diag(np.diag(corr)))
    scalars = dict(
        status="ok", replicate=replicate, k=int(len(sel)),
        n_coalitions=int(1 << len(sel)), n_answered=int(ans.sum()),
        n_declined=int((~ans).sum()),
        top_driver_int=feature_names[
            sel[int(np.argmax(np.abs(out["int"][2])))]],
        top_driver_cond=feature_names[
            sel[int(np.argmax(np.abs(out["cond"][2])))]],
        spearman_abs_gap_int_vs_cond=_spearman(np.abs(out["int"][2]),
                                               np.abs(out["cond"][2])),
        max_abs_offdiag_corr_train=round(float(off.max()), 6),
        max_abs_offdiag_corr_pair=[
            feature_names[sel[int(i)]]
            for i in np.unravel_index(int(np.argmax(off)), off.shape)],
        corr_train=[[round(float(v), 4) for v in row] for row in corr],
        max_abs_rel_gap_change=round(float(np.max(
            np.abs(out["cond"][2] - out["int"][2])
            / np.maximum(np.abs(out["int"][2]), 1e-12))), 6))
    return rows, scalars


def _faithfulness_summary(rows, scalars, abstention, *, arm):
    """EICU-FAITHFULNESS block: per-replicate scalars and per-feature means.

    Also cross-checks the recomputed interventional gaps against the
    abstention_gap_ranking already in EICU_diagnostics.json. Same head, same tau,
    same populations, so any difference beyond rounding is a wiring defect."""
    out = {"post_hoc": EICU_FAITHFULNESS_LABEL, "arm": arm,
           "k": EICU_FAITHFULNESS_TOP_K, "replicates": scalars,
           "n_replicates_ok": sum(1 for sc in scalars
                                  if sc.get("status") == "ok"),
           "features": {}}
    diffs = []
    for r in rows:
        key = f"replicate{r['replicate']}_alpha0.1"
        for item in (abstention.get(key) or {}).get("ranking", []):
            if item["feature"] == r["feature"] and item["gap"] is not None:
                diffs.append(abs(item["gap"] - r["gap_int"]))
    out["max_abs_diff_vs_abstention_ranking"] = (
        round(max(diffs), 6) if diffs else None)
    out["n_cross_checked"] = len(diffs)
    for name in sorted({r["feature"] for r in rows}):
        sub = [r for r in rows if r["feature"] == name]
        out["features"][name] = dict(
            n_replicates=len(sub),
            coef_mean=round(float(np.mean([r["coef"] for r in sub])), 6),
            gap_int_mean=round(float(np.mean([r["gap_int"] for r in sub])), 6),
            gap_cond_mean=round(float(np.mean([r["gap_cond"] for r in sub])),
                                6),
            rank_int_median=float(np.median([r["rank_int"] for r in sub])),
            rank_cond_median=float(np.median([r["rank_cond"] for r in sub])),
            n_top1_int=sum(1 for r in sub if r["rank_int"] == 1),
            n_top1_cond=sum(1 for r in sub if r["rank_cond"] == 1))
    return out


def _certification_blocks(payload):
    """Derive the six certification sections of EICU-SUMMARY.md, named below."""
    if not payload:
        return {}
    return {"EICU-POOLED": payload.get("pooled"),
            "EICU-PERSITE": payload.get("per_site"),
            "EICU-COMPARATOR": payload.get("comparator"),
            "EICU-RELIABILITY": payload.get("reliability"),
            "EICU-SUBGROUPS": payload.get("subgroups"),
            "EICU-FAITHFULNESS": payload.get("faithfulness")}


def run_certification(data_dir, out, *, arm="primary", replicates=1,
                      quick=False, verbose=True) -> dict:
    """Full certification run over `replicates` independent by-site re-splits.

    Everything below runs per replicate on ONE build_raw: re-reading a 200k-row
    extract 20 times is a build error, not a style preference (threat T-16).

      1. etl.site_split(site_raw, replicate=r) -- records never cross a split.
      2. etl.impute(x_raw, idx['train']) on S_train only. Pooled means would let
         the target pool's covariates into the training features, a
         transductive leak no downstream gate catches.
      3. Cohorts via from_raw, with require_both_classes=False for target only.
      4. assert_site_disjoint(train, aux, cal).
      5. Pooled arm: one run_certgate over all 24 held-out hospitals, with
         target_site_id supplied. K = 24 >= BBSE_MIN_TARGET_SITES, so q_t takes
         the cluster bootstrap.
      6. Per-hospital arm: one run_certgate per held-out hospital, with
         target_site_id supplied even at K == 1. That is statistically the same
         exact Clopper-Pearson q_t path None takes, plus full id validation,
         record-level disjointness against train/aux/cal, and provenance
         binding of the dense array and its canonical labels.
      7. Oracle scoring at the deployed tau against the held-out pool:
         _rm_on_pool, _per_site_exceed_frac and hard_violation.
      8. APACHE-IVa comparator on the answered set, aggregate rates only.
      9. Post-hoc selective reliability panel on the pooled arm only, via
         rp.panel_from_head so the caller never constructs p. It is
         descriptive: it alters no certified quantity, settles no frozen
         prediction, and everything it writes carries rp.POST_HOC_LABEL.

    quick=True caps replicates at 2 and skips figures. Returns the summary
    payload; every artifact written has passed assert_aggregate_only.
    """
    if arm not in etl.EICU_ARMS:
        raise etl.EicuError(
            f"run_eicu.run_certification: arm must be one of {etl.EICU_ARMS}, "
            f"got {arm!r} (reason=unknown-arm)")
    replicates = int(replicates)
    if replicates < 1:
        # run_eicu has its own reason tags -- record-level-output,
        # non-ascii-output, bad-replicates -- beside eicu_etl's closed set. A
        # truthful tag beats reusing a neighbour's tag for the wrong fault.
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
    etl.assert_no_leak_columns(feature_names)          # a test, not a comment
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

    y_raw = etl.labels(meta)
    site_raw = [str(s) for s in meta["site_raw"]]
    comparator = np.asarray(meta["comparator_predicted_mortality"],
                            dtype=np.float64)
    attrition_rows = _attrition_rows(meta, arm, warnings)
    site_counts = {d["step"]: d["n_sites"] for d in attrition_rows}
    coverage_by_site = _site_coverage(meta)
    missing_by_site = _site_missing_share(x_raw, meta)
    hospital_strata = _hospital_strata(data_dir, warnings)

    # E-19: every allowlisted feature is screened against the outcome before any
    # certificate exists. The denylist applies a "timing relative to outcome
    # unverified" standard to two apachePatientResult columns, but nine
    # apachePredVar treatment flags -- activetx above all -- had no timing
    # verification at all.
    # The DDL cannot settle that on a dataset whose sentinel convention the DDL
    # already gets wrong, so it is settled from the data. Run on the raw matrix,
    # the only place missingness is still visible.
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
    # Post-hoc selective reliability panel, pooled arm only. The label is a
    # hand-appended string and a separate JSON file inherits nothing, so it
    # travels in five places:
    #   - here, reaching diagnostics["warnings"] and the EICU-POOLED block
    #   - the top of EICU_reliability_panel.json
    #   - the EICU-RELIABILITY summary block
    #   - the face of the figure
    #   - a leading post_hoc column on every EICU_reliability.csv row
    panel_payloads, panel_curve_rows = [], []
    subgroup_rows = []
    faith_rows, faith_scalars = [], []
    warnings.append(rp.POST_HOC_LABEL)
    certificate = None
    impute_fill = {}
    sites_without_strata = set()          # distinct sites, not site x replicate

    for r in range(replicates):
        idx, sets = etl.site_split(site_raw, replicate=r)
        # Pairwise disjointness of the returned label sets, re-asserted at the
        # runner boundary. assert_site_disjoint below covers train/aux/cal and
        # run_certgate covers the target. This catches a wrong split before a
        # head is fit on it, and covers the target pair explicitly -- a
        # triple-intersection assert is strictly weaker (SPEC A.8).
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
        # F-D legs 1 and 2 (E-10): the leak alarm runs before any certificate,
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

        # ---- post-hoc reliability panel, pooled arm only -------------------
        # Pooled arm only: K = 24 >= rp.MIN_SITES_FOR_CI = 10, while the
        # per-hospital arm is K = 1, where every interval would be
        # floor-suppressed at 24x the cost. One panel per replicate, not per
        # rung, so it sits after the alpha loop. Descriptive: it alters no
        # certified quantity and every number carries rp.POST_HOC_LABEL.
        #
        # Three input decisions, each closing a trap:
        #   - `p` is never built here. panel_from_head computes
        #     head.predict_proba(x) (the binned quantity) and
        #     head.score(x) >= tau (the gate) itself. Feeding score as p would
        #     pass validation silently and produce a meaningless panel.
        #   - the mask is the one the operative rung deployed, and the tau
        #     passed for the cross-check is the raw op["tau"], not _eval_rung's
        #     6 dp rounding, which would disagree at the boundary
        #     (deployed-mask-mismatch). With no certified rung op_pooled is
        #     None: tau_star=None is legal, the all-False mask is used as given,
        #     and every answered statistic emits None with 'undefined-point'.
        #   - sites are target.site_id, dense int64 by the Cohort contract,
        #     never the raw string labels. A silent remap would change which
        #     records move together under the cluster bootstrap.
        #
        # RP-8: the whole call is guarded. validate_inputs is deliberately
        # intolerant and runs after every certification call for this replicate
        # but before any artifact is written, so an unmodelled input would
        # otherwise take the certificate down with it. A descriptive layer must
        # never do that. That is why the catch is `except Exception` and not
        # `except rp.PanelError`: the principle is who survives the crash, not
        # the exception's type.
        # The swallow is not silent. The reason goes to warnings -- hence
        # EICU_diagnostics.json and the EICU-POOLED block -- and to stderr,
        # non-PanelError types are called out as wiring defects, and
        # EICU-RELIABILITY.n_panels < replicates records the shortfall
        # arithmetically. run_E6 deliberately does not wrap: on synthetic data
        # a panel exception is a wiring bug and must be loud.
        op_pooled = rep_pooled.get("operative")
        try:
            panel = rp.panel_from_head(
                head, target.x, target.y, target.site_id,
                (float(op_pooled["tau"]) if op_pooled else None),
                answered_mask=rep_pooled["answered_mask"],
                p_ref=comparator[t_idx])      # APACHE-IVa; NaN = absent
        except Exception as exc:
            # A length-mismatched mask raises a bare numpy broadcast ValueError
            # from the gate cross-check, and a head without predict_proba
            # raises AttributeError. Neither is a PanelError, and either would
            # take the certified run down from inside the descriptive layer.
            # Only PanelError is an expected rejection. Anything else is named
            # as a wiring defect but still costs only the diagnostic.
            kind = ("" if isinstance(exc, rp.PanelError) else
                    f" [UNEXPECTED {type(exc).__name__} -- a panel-wiring "
                    f"defect, not a data rejection; investigate]")
            msg = (f"[MEASURE] RP-8: the POST-HOC reliability panel was SKIPPED "
                   f"for replicate {r} -- {exc}.{kind} The panel is "
                   f"descriptive; the certificate for this replicate is "
                   f"unaffected")
            warnings.append(msg)
            _say(True, msg, err=True)
        else:
            panel_payloads.append({
                "replicate": r, "arm": arm,
                "operative_alpha": (float(op_pooled["alpha"]) if op_pooled
                                    else None),
                **panel})
            for row in rp.panel_reliability_rows(panel):
                panel_curve_rows.append({"replicate": r, "arm": arm,
                                         "post_hoc": rp.POST_HOC_LABEL, **row})

        # ---- post-hoc subgroup descriptives (revision-2 item 3b) ----------
        # Pooled arm only, at the deployed operative tau, marginal dimensions
        # only. Descends entirely from data seen after the freeze: labeled,
        # floor-suppressed, certifies nothing.
        subgroup_rows.extend(_subgroup_rows(
            head, target, feature_names,
            (float(op_pooled["tau"]) if op_pooled else None), r, arm))

        # ---- post-hoc attribution value-function contrast ------------------
        # Pooled arm, deployed operative tau, covariance from S_train only.
        # Descriptive: no _rng draw, every number labeled.
        fr, fs = _faithfulness_rows(
            head, train, target, feature_names,
            (float(op_pooled["tau"]) if op_pooled else None), r, arm)
        faith_rows.extend(fr)
        faith_scalars.append(fs)

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

    # ---- post-hoc panel artifacts, through the gated writers --------------
    # The panel is aggregate-only by construction -- the longest sequence
    # anywhere is the 8-element bin_edges echo -- but construction does not
    # exempt the writer, so both go through assert_aggregate_only.
    #
    # `panels` is gated per payload (per_item_keys), the way _write_table gates
    # CSV rows: it holds one aggregate payload per replicate, so its length is a
    # replicate count, not a record-level array. Gated as one sequence it
    # tripped EICU_MAX_OUTPUT_LEN at --replicates 600 and aborted the run on a
    # purely descriptive artifact, after every certification arm was paid for.
    #
    # That covers the panel only. EICU_diagnostics.json above carries
    # per-replicate lists of the same shape (bbse, composition_three_way), is
    # written first, and is still gated whole -- so at that scale it aborts
    # there instead. Named here rather than left to look covered.
    _write_json(os.path.join(out,
                             f"{EICU_OUT_PREFIX}_reliability_panel.json"),
                {"post_hoc": rp.POST_HOC_LABEL,
                 "arm": arm, "replicates": int(replicates),
                 "scope": ("pooled target arm only (K = "
                           f"{etl.EICU_N_TARGET_SITES} hospitals); the "
                           "per-hospital arm is K = 1 and every interval "
                           "would be floor-suppressed"),
                 "panels": panel_payloads},
                "EICU_reliability_panel.json", per_item_keys=("panels",))
    # The leading post_hoc column is deliberate (RP-9). This CSV carries
    # real-extract per-bin observed rates and is the panel artifact most easily
    # detached from the directory that explains it, and a per-row column is the
    # only carrier that survives that. The repetition is the cost of the A6
    # discipline, not an oversight.
    _write_table(os.path.join(out, f"{EICU_OUT_PREFIX}_reliability.csv"),
                 panel_curve_rows,
                 ["post_hoc", "replicate", "arm"]
                 + list(rp.PANEL_RELIABILITY_FIELDS),
                 "EICU_reliability.csv")
    # Post-hoc subgroup rows: same leading-label discipline as the panel CSV
    # above (RP-9).
    _write_table(os.path.join(out, f"{EICU_OUT_PREFIX}_subgroups.csv"),
                 subgroup_rows,
                 ["post_hoc", "replicate", "arm", "dim", "level", "n",
                  "n_answered", "coverage", "answered_err_rate",
                  "answered_pos_rate", "declined_err_rate",
                  "declined_pos_rate", "status"], "EICU_subgroups.csv")
    _write_table(os.path.join(out, f"{EICU_OUT_PREFIX}_faithfulness.csv"),
                 faith_rows,
                 ["post_hoc", "replicate", "arm", "feature", "coef",
                  "mean_abs_phi_answered_int", "mean_abs_phi_declined_int",
                  "gap_int", "rank_int", "mean_abs_phi_answered_cond",
                  "mean_abs_phi_declined_cond", "gap_cond", "rank_cond"],
                 "EICU_faithfulness.csv")

    if not quick:
        _figures(out, pooled_rows, per_site_rows, panel_payloads, verbose)

    # ---- summary payload --------------------------------------------------
    payload = {
        "pooled": _pooled_summary(pooled_rows, arm=arm, replicates=replicates,
                                  n_records=n_records,
                                  n_sites=len(coverage_by_site),
                                  site_counts=site_counts, warnings=warnings),
        "per_site": _per_site_summary(per_site_rows, arm=arm),
        "comparator": _comparator_summary(comparator_rows, arm=arm),
        "reliability": _reliability_summary(panel_payloads, arm=arm,
                                            replicates=replicates,
                                            pooled_rows=pooled_rows),
        "subgroups": _subgroup_summary(subgroup_rows, arm=arm),
        "faithfulness": _faithfulness_summary(faith_rows, faith_scalars,
                                              abstention, arm=arm)}
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
    """Parse an existing EICU-SUMMARY.md into {section: rendered json block}.

    The eICU path owns its own parser and its own file. run_synthetic's regex is
    ^## (E\\d) -- a single digit -- so an ## EICU-... section placed in
    summary.md would be unparseable there and silently clobbered on the next
    partial rerun. The header pattern tolerates a "(preserved ...)" suffix, so a
    preserved section survives a second partial run (audit V26)."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    return {m.group(1): m.group(2)
            for m in _SUMMARY_BLOCK_RE.finditer(text)}


def _write_summary(out, blocks, *, mode, replicates, arm, data_sha):
    """Write EICU-SUMMARY.md: fresh sections stamped, others preserved.

    Same discipline as run_synthetic._write_summary (audit V26). Every fresh
    block carries its own _run stamp, and preserved sections are visibly marked,
    so a FULL header can never sit above a QUICK-computed block."""
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
    """Identity of an extract without reading it.

    sha256 over the sorted name:size listing of its gzip tables. Cheap on a 3 GB
    directory, and it tells v2.0 from a re-zip or the mock corpus. No
    record-level byte enters the digest or the artifact."""
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

    The summary and the provenance block are written in a finally: block, so an
    aborted run never leaves fresh CSVs beside a silently stale summary. On an
    abort the fresh-block set is empty, every prior section is re-emitted marked
    "(preserved from an earlier run)", and the failure is visible rather than
    papered over (audit V26)."""
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
                               n_features=int(etl.EICU_N_FEATURES),
                               # POST-HOC panel provenance: its own schema, its
                               # own frozen bins, its own root seed. The
                               # sandbox's seed is what keeps the port
                               # byte-exact, so rp.PANEL_SEED != SEED by design.
                               panel_schema=rp.SCHEMA_VERSION,
                               panel_seed=rp.PANEL_SEED,
                               panel_n_boot=rp.N_BOOT,
                               panel_bin_edges=list(rp.DEFAULT_BIN_EDGES),
                               panel_post_hoc=True),
                    "EICU_provenance.json")
        _say(True, f"wrote {EICU_OUT_PREFIX}-SUMMARY.md and "
                   f"{EICU_OUT_PREFIX}_provenance.json to {args.out}")
    return result


if __name__ == "__main__":
    main()
