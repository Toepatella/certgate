"""The explanation page over a MOCK corpus: the eICU pipeline, no eICU record.

examples/explain_dashboard.html is the synthetic demonstration, and
explain_dashboard_eicu.py renders the same page over the credentialed extract,
which nobody outside the data-use agreement can open. This module sits between
the two. It generates the schema-faithful eICU mock (experiments/eicu_mock.py)
in a temporary directory, walks the path the eICU driver walks -- ETL, by-site
split, train-only imputation, fit_head, run_certgate over the pooled held-out
hospitals -- and renders the page with the real eICU column names (aps_motor,
apv_oobintubday1, unitstaytype=stepdown/other), so a reader sees what the eICU
page looks like without a single record from the eICU corpus.

The corpus size is not the mock's default. margin_floor scales as 1/n_carrying,
and at the mock's frozen 180- and 208-hospital sizes the gate declines every
rung by design (EICU-PROTOCOL.md step 4 and the calibration note on
EICU_MOCK_SIGNAL_LOAD). The floor crosses the mock's oracle margin at about 217
hospitals, so the page is built at 900 hospitals / 90,000 stays -- the size the
CERTGATE_EICU_LARGE arm of tests/test_eicu_mock.py uses -- where alpha = 0.10
certifies with every pre-registered constant untouched.

Every number on the page is a property of the mock, and the page says so three
times: a banner reading "MOCK CORPUS -- synthetic, no eICU record" is inserted
at the top of the body, the cohort label repeats it, and the certificate block
carries a `corpus` field. Nothing here reads the extract, experiments/out, or
any released certificate; a mock has nothing to be cross-checked against.

The output is examples/explain_dashboard_mock.html, a committed deliverable. Its
basename must NOT match the gitignored explain_dashboard_eicu*.html pattern --
that pattern exists for record-level pages built from the extract -- and the
module refuses one that would, so the two kinds of page can never be confused
by filename.

Run:  python -m examples.explain_dashboard_mock
      python -m examples.explain_dashboard_mock --sites 900 --stays 90000 \\
          --out examples/explain_dashboard_mock.html

Refs: draft section 3.8 (the two-register explanation page); the fix pass of
2026-09-04 (a reviewer could not see the eICU page and had only the synthetic
demonstration to judge the register by).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import subprocess
import sys
import tempfile

import numpy as np

from certgate.constants import DELTA
from certgate.model import fit_head
from certgate.pipeline import run_certgate
from certgate.validate import assert_site_disjoint, from_raw
from examples.explain_dashboard import build_dashboard
from experiments import eicu_etl as etl
from experiments import eicu_mock as mock

# The size at which the mock certifies alpha = 0.10 (see the module docstring
# and test_large_mock_reaches_the_certified_branch in tests/test_eicu_mock.py).
MOCK_SITES = 900
MOCK_STAYS = 90000

# The banner text, verbatim. tests/test_eicu_mock.py asserts it is on the page.
MOCK_BANNER = "MOCK CORPUS — synthetic, no eICU record"

_HERE = os.path.dirname(os.path.abspath(__file__))
_OUT_DEFAULT = os.path.join(_HERE, "explain_dashboard_mock.html")
# .gitignore denies these for record-level pages; a mock page must not hide
# behind them, and must not be mistaken for one.
_FORBIDDEN_PREFIXES = ("explain_dashboard_eicu",)
_FORBIDDEN_SUFFIXES = ("_eicu_dashboard.html", "-eicu-dashboard.html")


def _fail(msg):
    raise SystemExit("explain_dashboard_mock: " + msg)


def _check_out_path(out):
    base = os.path.basename(out)
    if not base.endswith(".html"):
        _fail(f"refusing to write {out!r}: the output is an html page")
    if (base.startswith(_FORBIDDEN_PREFIXES) or base.endswith(_FORBIDDEN_SUFFIXES)):
        _fail(f"refusing to write {out!r}: that basename matches the gitignored "
              "pattern reserved for record-level pages built from the eICU "
              "extract. A mock page is a committed deliverable and must not "
              "be filed as one of those (reason=basename-collision)")
    return os.path.abspath(out)


def _git_sha():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, check=True,
                              cwd=_HERE).stdout.strip()
    except Exception:            # noqa: BLE001 -- provenance, never a failure
        return "unknown"


def _cohorts(x, y_raw, site_raw, idx):
    """from_raw for the four splits, then the site-disjointness assertion.

    require_both_classes is relaxed for the target pool only, exactly as
    run_eicu._build_cohorts does it: a single held-out hospital may be
    all-Alive at 9% prevalence, and that is the one sanctioned relaxation.
    """
    out = {}
    for split in ("train", "aux", "cal", "target"):
        sel = np.asarray(idx[split], dtype=int)
        if sel.size == 0:
            _fail(f"split {split!r} is empty (reason=empty-cohort)")
        out[split] = from_raw(x[sel], [y_raw[i] for i in sel.tolist()],
                              etl.EICU_POSITIVE_LABEL,
                              [site_raw[i] for i in sel.tolist()],
                              require_both_classes=(split != "target"))
    assert_site_disjoint(train=out["train"], aux=out["aux"], cal=out["cal"])
    return out


def certify(corpus_dir, *, replicate=0, verbose=True):
    """ETL -> split -> impute -> cohorts -> fit_head -> run_certgate.

    The same sequence explain_dashboard_eicu.build runs over the extract, on a
    built mock corpus. Returns everything the renderer needs in one dict.
    """
    x_raw, feature_names, meta = etl.build_raw(corpus_dir, verbose=verbose)
    etl.assert_no_leak_columns(feature_names)
    y_raw = etl.labels(meta)
    site_raw = [str(s) for s in meta["site_raw"]]
    idx, _sets = etl.site_split(site_raw, replicate=replicate)
    x, _fill = etl.impute(x_raw, idx["train"], verbose=False)
    cohorts = _cohorts(x, y_raw, site_raw, idx)
    head = fit_head(cohorts["train"])
    t_sites = [site_raw[i] for i in idx["target"]]
    report = run_certgate(cohorts["train"], cohorts["aux"], cohorts["cal"],
                          cohorts["target"].x,
                          target_label=etl.EICU_POOLED_TARGET_LABEL,
                          target_site_id=t_sites,
                          oracle_target_y=cohorts["target"].y)
    return dict(head=head, report=report, cohorts=cohorts,
                feature_names=list(feature_names), t_sites=t_sites,
                n_records=int(x_raw.shape[0]), n_sites=len(set(site_raw)),
                replicate=replicate)


def _banner_html(detail):
    return ('<div id="mockbanner" role="note" style="background:#7a1f1f;'
            'color:#fff;font:600 15px/1.45 system-ui,-apple-system,Segoe UI,'
            'sans-serif;padding:10px 18px;text-align:center;letter-spacing:'
            '.01em">' + MOCK_BANNER + ' · ' + detail +
            ' · every number on this page describes the mock</div>')


def render(res, out, *, corpus_note, provenance_comment, allow_declined=False,
           verbose=True):
    """Write the page for one certify() result. Returns the written path."""
    out = _check_out_path(out)
    say = (lambda m: print(m, flush=True)) if verbose else (lambda m: None)
    head, report, cohorts = res["head"], res["report"], res["cohorts"]
    train, aux, cal = cohorts["train"], cohorts["aux"], cohorts["cal"]
    target = cohorts["target"]
    op = report.get("operative")
    if op is None and not allow_declined:
        _fail("the mock declined every rung at this corpus size, so there is "
              "no certified operating point to display. Build at >= "
              f"{MOCK_SITES} hospitals, or pass --allow-declined for an "
              "explicitly uncertified demonstration page "
              "(reason=no-operative-rung)")
    if op is None:
        # An uncertified page: build_dashboard shows its own uncertified
        # banner when certificate is None. The threshold is the pool-median
        # score, and the cohort label says that is all it is.
        tau = float(np.median(head.score(target.x)))
        certificate = None
        status = ("no rung certified at this size; demonstration threshold = "
                  "pool-median score")
    else:
        # TAU_GRID values come back as binary floats (0.8300000000000001); the
        # banner prints bare key = value pairs, so round to the grid's precision.
        tau = round(float(op["tau"]), 6)
        certificate = {
            "certified": True,
            "alpha": float(op["alpha"]),
            "delta": float(DELTA),
            "tau": tau,
            "mode": op["deploy_mode"],
            "n_cal_hospitals": int(cal.n_sites),
            "corpus": f"{MOCK_BANNER} ({corpus_note})",
            "verification": ("not cross-checked: a synthetic corpus has no "
                             "released certificate to be compared against"),
        }
        status = f"alpha = {float(op['alpha'])} certified"
    coverage = float((head.score(target.x) >= tau).mean())
    say(f"[dashboard-mock] {status}; tau = {tau:.4f}; coverage on the pooled "
        f"held-out hospitals {coverage:.4f}")

    label = (f"{MOCK_BANNER}: {corpus_note}, replicate {res['replicate']}; "
             f"{status}")
    provenance = dict(
        pool=f"{target.n_sites} held-out mock hospitals",
        cohort_total=res["n_records"], cohort_sites=res["n_sites"],
        replicate=res["replicate"],
        splits=f"{train.n_sites} train / {aux.n_sites} aux / "
               f"{cal.n_sites} calibration")
    path = build_dashboard(head, target.x, tau_star=tau, out_path=out,
                           feature_names=res["feature_names"],
                           oracle_y=target.y, cohort_label=label,
                           certificate=certificate, site_ids=res["t_sites"],
                           include_outcomes=True, provenance=provenance)

    # The banner goes in above everything else on the page, after the one
    # <body> tag build_dashboard writes; the provenance comment sits beside it.
    with open(path, encoding="utf-8", newline="") as fh:
        html = fh.read()
    body_open = html.find("<body")
    if body_open < 0 or html.count("<body") != 1:
        _fail("build_dashboard wrote a page without exactly one <body> tag")
    cut = html.index(">", body_open) + 1
    html = (html[:cut] + "\n" + provenance_comment + "\n"
            + _banner_html(corpus_note) + html[cut:])
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html)
    say(f"[dashboard-mock] wrote {path}")
    return path


def build(out=_OUT_DEFAULT, *, sites=MOCK_SITES, stays=MOCK_STAYS,
          seed=mock.EICU_MOCK_SEED, corpus_dir=None, replicate=0,
          allow_declined=False, verbose=True):
    """Generate (or reuse) a mock corpus, certify it and render the page.

    corpus_dir: an existing mock corpus to reuse instead of generating one in
    a temporary directory; the tests pass their module-scoped small corpus.
    Returns the written path.
    """
    out = _check_out_path(out)
    say = (lambda m: print(m, flush=True)) if verbose else (lambda m: None)

    def _go(corpus, manifest):
        note = (f"{manifest.get('sites', sites)} mock hospitals, "
                f"{manifest.get('stays_written', stays):,} stays, "
                f"seed {manifest.get('seed', seed)}")
        stamp = {
            "utc": _dt.datetime.now(_dt.timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ"),
            "git_sha": _git_sha(),
            "generator": "experiments/eicu_mock.py",
            "sites": manifest.get("sites", sites),
            "stays_written": manifest.get("stays_written", stays),
            "seed": manifest.get("seed", seed),
            "row_counts": manifest.get("row_counts"),
        }
        comment = ("<!-- examples/explain_dashboard_mock.py -- MOCK CORPUS, "
                   "no eICU record. " + json.dumps(stamp, sort_keys=True)
                   + " -->")
        res = certify(corpus, replicate=replicate, verbose=verbose)
        return render(res, out, corpus_note=note, provenance_comment=comment,
                      allow_declined=allow_declined, verbose=verbose)

    if corpus_dir is not None:
        manifest = {}
        mpath = os.path.join(corpus_dir, "manifest.json")
        if os.path.exists(mpath):
            with open(mpath, encoding="utf-8") as fh:
                manifest = json.load(fh)
        return _go(corpus_dir, manifest)

    with tempfile.TemporaryDirectory(prefix="eicu_mock_page_") as tmp:
        corpus = os.path.join(tmp, "eicu-mock")
        say(f"[dashboard-mock] generating the mock corpus: {sites} hospitals, "
            f"{stays} stays, seed {seed} -> {corpus}")
        manifest = mock.generate(mock.MockConfig(stays=stays, sites=sites,
                                                 seed=seed, out=corpus))
        return _go(corpus, manifest)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sites", type=int, default=MOCK_SITES)
    ap.add_argument("--stays", type=int, default=MOCK_STAYS)
    ap.add_argument("--seed", type=int, default=mock.EICU_MOCK_SEED)
    ap.add_argument("--corpus", default=None,
                    help="reuse an existing mock corpus directory instead of "
                         "generating one")
    ap.add_argument("--replicate", type=int, default=0)
    ap.add_argument("--out", default=_OUT_DEFAULT)
    ap.add_argument("--allow-declined", action="store_true",
                    help="render an explicitly uncertified page when the "
                         "gate declines every rung")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    build(args.out, sites=args.sites, stays=args.stays, seed=args.seed,
          corpus_dir=args.corpus, replicate=args.replicate,
          allow_declined=args.allow_declined, verbose=not args.quiet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
