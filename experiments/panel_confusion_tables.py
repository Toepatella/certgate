"""Read-only derivation of the eICU answered/declined confusion tables.

Everything here is derived from the released 20-replicate reliability panel
experiments/out/EICU_reliability_panel.json. The restricted extract is never
touched and no pipeline is re-run. This file writes nothing: results go to
stdout as JSON, exactly like experiments/panel_s2_tables.py.

The panel's skill block computes model_error_rate at DECISION_THRESHOLD = 0.5,
which coincides with the head's own hard-label rule. So on every scope
(answered / declined / all):

    errors = model_error_rate * n            # = FP + FN
    TP = (n_predicted_positive + n_observed_positive - errors) / 2
    FP = n_predicted_positive - TP
    FN = n_observed_positive - TP
    TN = n - TP - FP - FN

model_error_rate is rounded once at emit time (6 dp), so the worst-case
reconstruction error in errors is 5e-7 * n, under 0.01 record at these pool
sizes. Every derived count must land within INT_TOL of an integer, or this
script refuses to emit anything at all.

Post-hoc status: every number below descends from the panel, so the panel's
post-hoc label governs this table too. The label is re-emitted verbatim as the
first key of the output. No certified quantity is touched, and none of the
protocol's predictions or failure criteria are settled.

There are no bootstrap intervals here. The panel does not bootstrap a
sensitivity statistic, and NOTES[1] of the panel forbids differencing marginal
interval endpoints, so this table reports exact counts and point rates only.

Run: python -m experiments.panel_confusion_tables [path-to-panel-json]

Refs: revision-2 item 3a; panel item S2-28 (eICU half).
"""

import json
import os
import sys

import numpy as np

from experiments.panel_s2_tables import _op_chars as _s2_op_chars

OUT = os.path.join(os.path.dirname(__file__), "out")
PANEL_PATH = os.path.join(OUT, "EICU_reliability_panel.json")
SCOPES = ("answered", "declined", "all")
INT_TOL = 0.05           # reconstruction slack; true worst case is ~0.01
# Replicate-0 answered-scope 2x2, verified by hand against the panel's
# composition and skill blocks. If the derivation ever stops reproducing it,
# nothing else here is trustworthy.
SELF_CHECK = dict(replicate=0, scope="answered", tp=57, fp=6, fn=537, tn=12364)


def _reconstruct(comp, skill):
    """(tp, fp, fn, tn) from one scope's composition + skill blocks."""
    n = comp["n"]
    if n == 0:
        return dict(tp=0, fp=0, fn=0, tn=0)
    npp = comp["n_predicted_positive"]
    nop = comp["n_observed_positive"]
    errors_f = skill["model_error_rate"] * n
    errors = round(errors_f)
    if abs(errors_f - errors) > INT_TOL:
        raise AssertionError(
            f"panel_confusion_tables: errors={errors_f} not within {INT_TOL} "
            f"of an integer (reason=derivation-not-exact)")
    tp_f = (npp + nop - errors) / 2.0
    tp = round(tp_f)
    if abs(tp_f - tp) > INT_TOL:
        raise AssertionError(
            f"panel_confusion_tables: tp={tp_f} not within {INT_TOL} of an "
            f"integer (reason=derivation-not-exact)")
    fp, fn = npp - tp, nop - tp
    tn = n - tp - fp - fn
    if min(tp, fp, fn, tn) < 0:
        raise AssertionError(
            f"panel_confusion_tables: negative cell in ({tp},{fp},{fn},{tn}) "
            f"(reason=derivation-inconsistent)")
    return dict(tp=tp, fp=fp, fn=fn, tn=tn)


def _op_chars(c, skill):
    """panel_s2_tables' Table 7 row with fnr, plus the panel's own
    constant-rule reference carried through."""
    row = _s2_op_chars(c, fnr=True)
    row["constant_predictor_error_rate"] = skill.get(
        "constant_predictor_error_rate")
    return row


def _agg(rows, key):
    vals = [row[key] for row in rows if row[key] is not None]
    if not vals:
        return None
    return dict(min=round(float(np.min(vals)), 4),
                median=round(float(np.median(vals)), 4),
                max=round(float(np.max(vals)), 4))


def derive(panel_doc):
    per_scope = {s: [] for s in SCOPES}
    for panel in panel_doc["panels"]:
        for scope in SCOPES:
            c = _reconstruct(panel["composition"][scope], panel["skill"][scope])
            row = dict(replicate=panel["replicate"],
                       **_op_chars(c, panel["skill"][scope]))
            per_scope[scope].append(row)

    # Hard self-check against the hand-verified replicate-0 cell counts.
    chk = next(row for row in per_scope[SELF_CHECK["scope"]]
               if row["replicate"] == SELF_CHECK["replicate"])
    for k in ("tp", "fp", "fn", "tn"):
        if chk[k] != SELF_CHECK[k]:
            raise AssertionError(
                f"panel_confusion_tables: replicate-0 {k}={chk[k]} != "
                f"verified {SELF_CHECK[k]} (reason=self-check-failed)")

    metrics = ("sensitivity", "specificity", "ppv", "npv", "fnr", "error",
               "fn_share_of_errors")
    return dict(
        post_hoc=panel_doc["post_hoc"],
        derived_from="EICU_reliability_panel.json",
        replicates=panel_doc["replicates"],
        note=("Counts reconstructed exactly from the panel's composition and "
              "skill blocks at the panel's own 0.5 decision threshold; no "
              "bootstrap intervals exist for these derived rates."),
        self_check=dict(**SELF_CHECK, status="passed"),
        summary={s: {m: _agg(per_scope[s], m) for m in metrics}
                 for s in SCOPES},
        per_replicate=per_scope)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    path = argv[0] if argv else PANEL_PATH
    with open(path, encoding="utf-8") as fh:
        panel_doc = json.load(fh)
    print(json.dumps(derive(panel_doc), indent=2))


if __name__ == "__main__":
    main()
