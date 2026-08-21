"""Rebuild the eICU explain dashboard from the credentialed extract.

``examples/explain_dashboard.py`` renders the SYNTHETIC demo, which is a
committed deliverable. This module renders the same page over one replicate of
the real eICU-CRD v2.0 cohort, and that output is a different kind of object:
it embeds every displayed case's raw feature vector so the page can recompute
the head's arithmetic offline, which makes it a DERIVED RECORD-LEVEL artifact
under PhysioNet DUA 1.5.0. It is denied by ``.gitignore``
(``explain_dashboard_eicu*.html``), it must never be committed or shared, and
this module refuses to write anywhere that pattern does not cover.

Why a committed driver instead of an ad-hoc script: the page shows a
certificate, and a certificate that cannot be traced to the run which issued it
is decoration. The pipeline below is the same one ``run_eicu.run_certification``
walks for replicate 0 -- the same ``site_split``, the same S_train-only
``impute``, the same ``_build_cohorts``, the same ``fit_head`` on S_train, the
same ``run_certgate`` over the pooled 24-hospital target -- and it then
CROSS-CHECKS the rung it is about to display against the released
``experiments/out/EICU_certificate.json``, aborting on any disagreement in
alpha, tau, tau_idx, deploy mode, coverage or calibration-site count. A page
whose numbers have drifted from the published certificate is worse than no
page.

The OUTCOME of that check rides in the certificate banner as ``verification``,
so a page that skipped it (``--no-cross-check``, a missing released
certificate, or an ``--alpha`` rung the released certificate does not record)
is never byte-identical to one that passed it.

This module writes ONE html file. It never touches ``experiments/out``, never
re-runs the certification arms, and computes no new certified quantity: the
certificate it renders is read off the report, not re-derived.

Run:  python -m examples.explain_dashboard_eicu --data ./eicu-extract
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

from certgate.constants import DELTA
from certgate.model import fit_head
from certgate.pipeline import run_certgate
from examples.explain_dashboard import build_dashboard
from experiments import eicu_etl as etl
from experiments.run_eicu import _build_cohorts, _row_for

# The DUA guard. ``.gitignore`` denies ``explain_dashboard_eicu*.html``; an
# --out that escapes that pattern would put record-level data on a tracked
# path, and a gitignore miss is unrecoverable once pushed. Checked on the
# BASENAME, so no directory argument can talk its way past it.
_OUT_PREFIX = "explain_dashboard_eicu"
_OUT_SUFFIX = ".html"

# A6 (the one post-hoc amendment, logged data-seen=YES) relaxed the
# unexpected-negative-sentinel abort. It moved no computed number, but every
# figure built from this extract carries the label rather than leaving a reader
# to discover the amendment elsewhere.
_A6 = "post-hoc amendment A6 applies"

# The prefix every not-cross-checked verification string carries. It is what
# puts the gap ON THE PAGE (the certificate banner prints every key it is
# given) rather than only on a stderr line that scrolls away, and it is what
# `build` tests to decide whether to also warn on stderr.
_UNVERIFIED = "NOT CROSS-CHECKED --"


def _fail(msg):
    raise SystemExit("explain_dashboard_eicu: " + msg)


def _check_out_path(out):
    base = os.path.basename(out)
    if not (base.startswith(_OUT_PREFIX) and base.endswith(_OUT_SUFFIX)):
        _fail(
            f"refusing to write {out!r}: a dashboard built from the eICU "
            f"extract embeds RECORD-LEVEL data, so its filename must match the "
            f"gitignored pattern {_OUT_PREFIX}*{_OUT_SUFFIX} "
            f"(reason=record-level-output)")
    out = os.path.abspath(out)
    # "out" alone missed the tracked sidecar output dirs (out-panel/,
    # out-sens/), which .gitignore's own note declares tracked-by-design --
    # exactly where a record-level page must never land.
    for d in ("out", "out-panel", "out-sens"):
        if os.path.sep + d + os.path.sep in out + os.path.sep:
            _fail(f"refusing to write {out!r}: this module never writes into "
                  f"an experiment output directory "
                  f"(reason=record-level-output)")
    return out


def _operative(report, alpha=None):
    """The rung to display: the requested alpha, else the strictest certified.

    ``run_certgate`` already reports the operative rung; re-deriving it here
    would be a second opinion on a selection the certificate has made, so the
    report's own choice is preferred and ``--alpha`` only ever narrows it.
    """
    if alpha is None:
        op = report.get("operative")
        if not op:
            _fail("this replicate certified NO rung of the ladder, so there is "
                  "no operating point to display. The page is only built for a "
                  "certified deployment (reason=no-operative-rung)")
        alpha = float(op["alpha"])
    row = _row_for(report, alpha)
    if row is None or row.get("status") != "certified":
        _fail(f"alpha={alpha} is not certified on this replicate "
              f"(status={None if row is None else row.get('status')!r}) "
              f"(reason=no-operative-rung)")
    return row


def _answered_risk(report):
    """The estimated answered-set risk, formatted as the page displays it.

    NOTE THE POOL. ``report['estimated']`` is ``report._bootstrap_estimate``
    over **S_cal**, so this number's denominator is the CALIBRATION hospitals,
    not the held-out pool the rest of the page is about. Every other banner
    field (alpha, tau, mode, n_cal_hospitals) is a property of the certificate
    itself; this is the only one carrying a different pool, and the banner
    renders bare ``key = value`` pairs -- so the KEY it is filed under is the
    only place that pool can be named.

    It is also bootstrapped at the OPERATIVE tau only, so ``build`` suppresses
    it whenever ``--alpha`` selects a different rung.
    """
    est = report.get("estimated") or {}
    point, ci = est.get("point"), est.get("ci95")
    if point is None or not ci:
        return None
    # report._bootstrap_estimate emits NaN for an empty answered set and a
    # (NaN, NaN) ci95 when the bootstrap top-up declines (audit V21); without
    # this guard the banner would print the literal "nan (95% CI nan-nan)".
    if not (math.isfinite(point) and all(math.isfinite(c) for c in ci)):
        return None
    return f"{point:.4f} (95% CI {ci[0]:.4f}-{ci[1]:.4f})"


def _cross_check(row, cal, coverage, ref_path):
    """Abort unless the rung matches the released certificate.

    Compared against the certificate the paper cites, not against a constant
    written here: a literal would drift silently the first time the released
    run changed, which is the failure this check exists to catch.

    Returns the VERIFICATION STRING the page carries in its certificate banner
    -- either the confirmation or an ``_UNVERIFIED``-prefixed reason. It is a
    return value rather than a stderr line because stderr scrolls away and the
    html is the artifact that gets opened, mailed and shown: a page whose
    numbers were never checked against the published run must not be
    indistinguishable from one that was.
    """
    if not os.path.exists(ref_path):
        return (f"{_UNVERIFIED} no released certificate at {ref_path}, so this "
                f"rung was not compared against the published run")
    with open(ref_path, encoding="utf-8") as fh:
        ref = json.load(fh)
    ref_op = ref.get("operative") or {}
    ref_diag = ref.get("diagnostic") or {}
    bad, missing = [], []
    for name, got, want in (
            ("alpha", float(row["alpha"]), ref_op.get("alpha")),
            ("tau", float(row["tau"]), ref_op.get("tau")),
            ("tau_idx", int(row["tau_idx"]), ref_op.get("tau_idx")),
            ("deploy_mode", row["deploy_mode"], ref_op.get("deploy_mode")),
            ("coverage", round(coverage, 6),
             None if ref_diag.get("coverage") is None
             else round(float(ref_diag["coverage"]), 6)),
            ("n_cal", int(cal.n_sites), ref_diag.get("n_cal"))):
        if want is None:
            # A field the released certificate does not carry was previously
            # SKIPPED -- and the unconditional "all match" string below then
            # asserted six-field agreement over zero comparisons (a released
            # run that certified no rung has operative: null, silently
            # skipping four of the six). A comparison that cannot be made is
            # a failed cross-check, not a passed one.
            missing.append(name)
        elif got != want:
            bad.append(f"{name}: this run {got!r} vs released {want!r}")
    if missing:
        _fail("the released certificate "
              f"({ref_path}) does not carry: {', '.join(missing)} -- the "
              "cross-check cannot be completed, and a page claiming agreement "
              "it never verified is worse than no page. Re-run the "
              "certification, or pass --no-cross-check if you know why "
              "(reason=certificate-mismatch)")
    if bad:
        _fail("this run DISAGREES with the released certificate "
              f"({ref_path}):\n  " + "\n  ".join(bad) +
              "\nThe page would display a certificate the published run did "
              "not issue. Re-run the certification, or pass "
              "--no-cross-check if you know why they differ "
              "(reason=certificate-mismatch)")
    return (f"alpha, tau, tau_idx, mode, coverage and calibration-site count "
            f"all match the released certificate ({os.path.basename(ref_path)})")


def build(data_dir, out, *, arm="primary", replicate=0, alpha=None,
          cross_check=True, verbose=True):
    """Render one replicate's held-out pool. Returns the written path."""
    out = _check_out_path(out)
    say = (lambda m: print(m, flush=True)) if verbose else (lambda m: None)

    x_raw, feature_names, meta = etl.build_raw(data_dir, arm=arm,
                                               strict_levels=True,
                                               verbose=verbose)
    etl.assert_no_leak_columns(feature_names)
    y_raw = etl.labels(meta)
    site_raw = [str(s) for s in meta["site_raw"]]
    n_records, n_sites = int(x_raw.shape[0]), len(set(site_raw))
    say(f"[dashboard-eicu] cohort {n_records} stays over {n_sites} hospitals, "
        f"{len(feature_names)} features (arm={arm})")

    idx, _sets = etl.site_split(site_raw, replicate=replicate)
    x, _fill = etl.impute(x_raw, idx["train"], verbose=False)
    cohorts = _build_cohorts(x, y_raw, site_raw, idx, arm, replicate)
    train, aux, cal = cohorts["train"], cohorts["aux"], cohorts["cal"]
    target = cohorts["target"]
    t_sites = [site_raw[i] for i in idx["target"]]
    say(f"[dashboard-eicu] replicate {replicate}: {train.n_sites} train / "
        f"{aux.n_sites} aux / {cal.n_sites} calibration; target "
        f"{target.n_sites} hospitals, {target.n} records")

    head = fit_head(train)
    report = run_certgate(train, aux, cal, target.x,
                          target_label=etl.EICU_POOLED_TARGET_LABEL,
                          target_site_id=t_sites, oracle_target_y=target.y)
    row = _operative(report, alpha)
    tau = float(row["tau"])
    coverage = float((head.score(target.x) >= tau).mean())
    say(f"[dashboard-eicu] operative alpha={row['alpha']} tau={tau} "
        f"mode={row['deploy_mode']} coverage={coverage:.4f}")

    # The released certificate records the OPERATIVE rung only, so there is
    # nothing there to compare a --alpha-selected rung against. Saying so is
    # the fix: comparing anyway reported every field as a disagreement and told
    # the operator to re-run the certification, when nothing had drifted and
    # they had simply asked for a different rung.
    op_alpha = (None if not report.get("operative")
                else float(report["operative"]["alpha"]))
    off_operative = (alpha is not None and op_alpha is not None
                     and float(alpha) != op_alpha)
    if not cross_check:
        verification = (f"{_UNVERIFIED} --no-cross-check was passed, so these "
                        f"numbers were not compared against the published run")
    elif off_operative:
        verification = (
            f"{_UNVERIFIED} --alpha selected the {row['alpha']} rung while "
            f"this replicate's operative rung is {op_alpha}; the released "
            f"certificate records only the operative rung, so there is nothing "
            f"to compare this one against")
    else:
        ref_path = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "experiments", "out",
            "EICU_certificate.json")
        verification = _cross_check(row, cal, coverage, ref_path)
    if verification.startswith(_UNVERIFIED):
        print("[MEASURE] " + verification, file=sys.stderr, flush=True)
    else:
        say("[dashboard-eicu] cross-check OK: " + verification)

    certificate = {
        "certified": True,
        "alpha": float(row["alpha"]),
        "delta": float(DELTA),
        "tau": tau,
        "mode": row["deploy_mode"],
        "n_cal_hospitals": int(cal.n_sites),
        # KEYED BY ITS POOL, not merely documented. This is the S_cal estimate
        # (see _answered_risk), and the banner prints bare `key = value` pairs
        # beside a provenance box reading "N held-out hospitals" -- under the
        # bare name `answered_risk` a reader takes it for the error rate on the
        # pool being browsed, which has a different denominator.
        #
        # SUPPRESSED off-operative, and that is not optional. report["estimated"]
        # is bootstrapped ONCE, at the OPERATIVE tau (report.py: the
        # `_bootstrap_estimate(head, cal, operative["tau"], ...)` call), so it
        # does not describe an --alpha-selected rung. Printing it beside this
        # row's `tau` would put an error estimate from a DIFFERENT threshold two
        # keys away from the threshold it is read against, in one banner line.
        "answered_risk_on_calibration_sites": (
            _answered_risk(report) if not off_operative else
            "not shown: report['estimated'] is bootstrapped at the operative "
            "rung only and does not describe this rung"),
        # Carried ON THE PAGE so an unverified page is never byte-identical to
        # a cross-checked one.
        "verification": verification,
    }
    provenance = dict(
        pool=f"{target.n_sites} held-out hospitals",
        cohort_total=n_records, cohort_sites=n_sites, replicate=replicate,
        splits=f"{train.n_sites} train / {aux.n_sites} aux / "
               f"{cal.n_sites} calibration")
    label = (f"eICU-CRD v2.0 held-out hospitals, replicate {replicate}"
             + (f", arm {arm}" if arm != "primary" else "") + f" ({_A6})")

    path = build_dashboard(head, target.x, tau_star=tau, out_path=out,
                           feature_names=feature_names, oracle_y=target.y,
                           cohort_label=label, certificate=certificate,
                           site_ids=t_sites, include_outcomes=True,
                           provenance=provenance)
    say(f"[dashboard-eicu] wrote {path}")
    say("[dashboard-eicu] RESTRICTED: this file embeds record-level eICU data. "
        "It is gitignored -- never commit, never redistribute (DUA 1.5.0).")
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True,
                    help="extract directory (the five eICU *.csv.gz tables)")
    ap.add_argument("--out", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        _OUT_PREFIX + _OUT_SUFFIX),
        help="output html (basename must match %s*%s)" % (_OUT_PREFIX,
                                                          _OUT_SUFFIX))
    ap.add_argument("--arm", default="primary", choices=sorted(etl.EICU_ARMS))
    ap.add_argument("--replicate", type=int, default=0)
    ap.add_argument("--alpha", type=float, default=None,
                    help="display this rung instead of the operative one; the "
                         "released certificate records only the operative "
                         "rung, so an off-operative rung is reported as NOT "
                         "CROSS-CHECKED on the page rather than compared")
    ap.add_argument("--no-cross-check", action="store_true",
                    help="skip the check against the released certificate")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    build(args.data, args.out, arm=args.arm, replicate=args.replicate,
          alpha=args.alpha, cross_check=not args.no_cross_check,
          verbose=not args.quiet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
