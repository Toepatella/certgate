"""Worked real-data example: from a CSV-like dataset to a CertGate certificate.

This script is the glue a practitioner writes when a real multi-site clinical
dataset arrives. It is deliberately end-to-end and heavily commented:

  1. Write a small synthetic dataset to a temporary CSV, then read it back with
     the *stdlib* ``csv`` module -- NO pandas (CertGate adds no dependencies;
     see requirements.txt) -- so the genuine from-a-file path is exercised.
  2. Split sites into train / aux / cal BY SITE (never by record -- see the loud
     comment in ``_split_by_site``).
  3. Build each split's Cohort with ``from_raw`` (coerce labels + densify site
     ids + run the loud input contract).
  4. Run ``run_certgate`` WITHOUT oracle labels and print what the report holds:
     certified rungs, the guarantee statement, the decline partition, and an
     abstention explanation for one declined deployment case.
  5. Show what an honest decline looks like (structural refusal with a reason
     code) and note what degrades gracefully when oracle labels are absent.

Run it directly:  ``python examples/real_data_example.py``
It is deterministic (everything seeds from ``certgate.constants.SEED``).
"""
import csv
import os
import sys
import tempfile

import numpy as np

# Run directly, this script puts examples/ -- not the repo root -- on sys.path,
# so ``import certgate`` would fail. Add the repo root. This is module-level
# (never inside a function), which respects the repo's top-level-imports invariant.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from certgate.constants import SEED, SPLIT_FRACTIONS
from certgate.data import SimConfig, draw_cohort
from certgate.validate import from_raw
from certgate.model import fit_head
from certgate.explain import abstention_explanation
from certgate.pipeline import run_certgate
from certgate.report import render_text

POSITIVE = "case"        # outcome-column string that means y=1
NEGATIVE = "control"     # the single other observed value -> y=0


# --------------------------------------------------------------------------- #
# CSV write / read (stdlib csv only -- no pandas)                             #
# --------------------------------------------------------------------------- #
def _write_labeled_csv(path, cohort):
    """Historical multi-site data WITH outcomes -> a CSV a hospital might export.

    Columns: ``site, outcome, x0..x{d-1}``; one row per patient record. This is
    the shape of data you already have labels for (the calibration sites).
    """
    d = cohort.d
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["site", "outcome"] + [f"x{j}" for j in range(d)])
        for i in range(cohort.n):
            label = cohort.site_labels[cohort.site_id[i]]
            outcome = POSITIVE if cohort.y[i] else NEGATIVE
            w.writerow([label, outcome] + [f"{v:.6f}" for v in cohort.x[i]])


def _write_features_only_csv(path, cohort):
    """A NEW deployment batch: site id + features, NO outcome column.

    In real deployment the outcomes do not exist yet -- these are patients whose
    risk we are about to gate. Certification never needs their labels. The SITE
    column, however, must travel with the batch: a multi-site deployment pool
    passes it to ``run_certgate`` as ``target_site_id`` so the per-site target
    disjointness gate and BBSE's cluster-correct q interval both see it.
    """
    d = cohort.d
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["site"] + [f"x{j}" for j in range(d)])
        for i in range(cohort.n):
            label = cohort.site_labels[cohort.site_id[i]]
            w.writerow([label] + [f"{v:.6f}" for v in cohort.x[i]])


def _read_labeled_csv(path):
    """Read the historical CSV back with the stdlib csv module (no pandas)."""
    sites, outcomes, feats = [], [], []
    with open(path, newline="") as fh:
        r = csv.reader(fh)
        header = next(r)
        i_site = header.index("site")
        i_out = header.index("outcome")
        xcols = [k for k, name in enumerate(header) if name.startswith("x")]
        for row in r:
            sites.append(row[i_site])
            outcomes.append(row[i_out])
            feats.append([float(row[k]) for k in xcols])
    return sites, outcomes, feats


def _read_features_only_csv(path):
    """Read the deployment CSV back -> ((n, d) float matrix, per-record site ids)."""
    with open(path, newline="") as fh:
        r = csv.reader(fh)
        header = next(r)
        i_site = header.index("site")
        xcols = [k for k, name in enumerate(header) if name.startswith("x")]
        sites, rows = [], []
        for row in r:
            sites.append(row[i_site])
            rows.append([float(row[k]) for k in xcols])
    return np.asarray(rows, dtype=np.float64), sites


# --------------------------------------------------------------------------- #
# Split BY SITE (never by record)                                            #
# --------------------------------------------------------------------------- #
def _split_by_site(sites, outcomes, feats, rng):
    """Partition WHOLE SITES into train / aux / cal by ``SPLIT_FRACTIONS``.

    *** Split BY SITE, never by record. ***  The site (hospital) is the unit of
    statistical independence -- that is the whole point of CertGate. Two reasons
    this matters, both loud:
      - ``run_certgate`` ASSERTS site-disjointness at entry (``assert_site_disjoint``)
        across train/aux/cal, and additionally rejects a ``target_label`` (or, when
        supplied, ``target_site_id`` labels) naming any train/aux/cal site (audit
        V9) -- the TARGET must be a genuinely new site too, and for a multi-site
        deployment pool you should pass ``target_site_id`` so this is checked
        per site (it also gives BBSE its cluster-correct q_t interval). This
        example's deployment pool spans 12 sites and passes it below.
      - Even if it somehow slipped through, a record-level split would silently
        break the finite-sample guarantee (leakage across the calibration draw).
    So we assign each SITE LABEL to exactly one split, then route every record by
    its site.
    """
    unique_sites = sorted(set(sites))                 # deterministic base order
    perm = rng.permutation(len(unique_sites))
    f_train, f_aux, _ = SPLIT_FRACTIONS
    n_train = int(round(f_train * len(unique_sites)))
    n_aux = int(round(f_aux * len(unique_sites)))
    assign = {}
    for rank, idx in enumerate(perm):
        site = unique_sites[idx]
        if rank < n_train:
            assign[site] = "train"
        elif rank < n_train + n_aux:
            assign[site] = "aux"
        else:
            assign[site] = "cal"
    buckets = {k: {"x": [], "y": [], "sites": []}
               for k in ("train", "aux", "cal")}
    for site, out, xrow in zip(sites, outcomes, feats):
        b = buckets[assign[site]]
        b["x"].append(xrow)
        b["y"].append(out)
        b["sites"].append(site)
    return buckets


def _build_cohorts(buckets):
    """Turn each raw split into a Cohort via the from_raw loader contract.

    ``from_raw`` does the whole raw -> Cohort job: ``coerce_labels`` maps the
    "case"/"control" strings to strict bool (positive_label="case"),
    ``densify_sites`` maps the raw string site ids to dense 0..K-1, and
    ``make_cohort`` runs the loud input checks. Fitting cohorts keep the strict
    ``require_both_classes=True`` default (single-class data breaks the head fit).

    WARNING -- missing-label sentinels are NOT auto-detected. ``coerce_labels``
    rejects ONLY NaN / None. Domain sentinels like ``-1``, ``9``, ``"NA"`` or
    ``""`` are treated as ordinary label values (and a third distinct value trips
    the ">2 distinct labels" error). Clean sentinels out of the outcome column
    BEFORE calling ``from_raw``.
    """
    cohorts = {}
    for name, b in buckets.items():
        cohorts[name] = from_raw(np.asarray(b["x"], dtype=np.float64),
                                 np.asarray(b["y"]),      # string dtype -> bool
                                 POSITIVE, b["sites"])
    return cohorts


def main():
    rng = np.random.default_rng(SEED)                 # deterministic throughout

    # The documented 208-site generator (SimConfig defaults): 40% of 208 ~ 83
    # calibration sites clears the 50-record-carrying floor comfortably, and
    # this exact draw reproduces the split tests/test_pipeline.py pins as
    # certifying alpha=0.10. The temp CSV is ~35 MB -- the price of realistic
    # site sizes (the certificate's feasibility rides on BOTH cluster count
    # and per-site atom noise).
    cfg = SimConfig()
    historical = draw_cohort(cfg, 208, rng)
    # The deployment batch is a MULTI-SITE pool of NEW sites (12 of them --
    # comfortably above BBSE_MIN_TARGET_SITES=10, so BBSE's q interval takes
    # the cluster-bootstrap path instead of declining). Features only matter
    # here, so require_both_classes=False (a real batch may legitimately be
    # all one class). Drawn from its OWN rng stream so the deployment pool's
    # shape can never reshuffle the historical split above.
    deployment = draw_cohort(cfg, 12, np.random.default_rng(SEED + 1),
                             site_label_prefix="deploy",
                             require_both_classes=False)

    tmpdir = tempfile.mkdtemp(prefix="certgate_example_")
    hist_csv = os.path.join(tmpdir, "historical_labeled.csv")
    deploy_csv = os.path.join(tmpdir, "deployment_features_only.csv")
    _write_labeled_csv(hist_csv, historical)
    _write_features_only_csv(deploy_csv, deployment)
    print(f"[io] wrote historical CSV  -> {hist_csv}")
    print(f"[io] wrote deployment CSV  -> {deploy_csv}")

    # ---- read back from file (stdlib csv), split by site, build cohorts ----
    sites, outcomes, feats = _read_labeled_csv(hist_csv)
    buckets = _split_by_site(sites, outcomes, feats, rng)
    cohorts = _build_cohorts(buckets)
    target_x, target_sites = _read_features_only_csv(deploy_csv)
    for name in ("train", "aux", "cal"):
        c = cohorts[name]
        print(f"[data] {name:5s}: {c.n:6d} records over {c.n_sites:3d} sites")
    print(f"[data] target (deployment): {target_x.shape[0]} records, "
          f"{target_x.shape[1]} features, "
          f"{len(set(target_sites))} sites")

    # ---- run the gate WITHOUT oracle labels ----
    # Certification NEVER needs target labels; it certifies the answered-set error
    # RATE from the calibration draw. What degrades gracefully when oracle labels
    # are absent: only the DIAGNOSTIC oracle composition (the realized true-positive
    # fraction among answered cases) is omitted from the report -- every load-bearing
    # certified/estimated number still fires.
    # target_site_id carries the pool's per-record raw site labels: the
    # pipeline asserts every target site is disjoint from train/aux/cal, and
    # BBSE's q_t interval becomes a cluster bootstrap over the 12 target
    # sites rather than a single-site Clopper-Pearson interval.
    rep = run_certgate(cohorts["train"], cohorts["aux"], cohorts["cal"],
                       target_x, target_label="deploy-pool",
                       target_site_id=target_sites)

    print("\n" + "=" * 72)
    print("CERTIFIED RUNGS")
    print("=" * 72)
    for row in rep["certified"]:
        if row["status"] == "certified":
            print(f"  alpha={row['alpha']:.2f}: CERTIFIED  tau={row['tau']:.3f}  "
                  f"deploy_mode={row['deploy_mode']}  modes={row['modes']}  "
                  f"coverage={row['coverage']:.3f}")
            # mode_outcomes records why the OTHER mode did not contribute --
            # on real data BBSE silently not contributing is the interesting
            # signal (e.g. 'failsafe' vs 'bbse-ill-conditioned').
            print(f"              per-mode outcomes: {row['mode_outcomes']}")
        else:
            print(f"  alpha={row['alpha']:.2f}: declined  reasons={row['reasons']}")

    op = rep["operative"]
    if op is not None:
        stmt = next(r["statement"] for r in rep["certified"]
                    if r["status"] == "certified" and r["alpha"] == op["alpha"])
        print(f"\nGUARANTEE STATEMENT (operative rung alpha={op['alpha']:.2f}, "
              f"tau={op['tau']:.3f}):")
        print("  " + stmt)

    print(f"\nDECLINE PARTITION (sums to n_target="
          f"{sum(rep['decline_partition'].values())}):")
    for k, v in rep["decline_partition"].items():
        print(f"  {k}: {v}")

    # ---- abstention explanation for one declined deployment case ----
    # Re-fit the head on train to explain a specific case. fit_head is deterministic,
    # so this is the SAME head run_certgate fit internally.
    head = fit_head(cohorts["train"])
    declined = np.where(~rep["answered_mask"])[0]
    if op is not None and declined.size:
        idx = int(declined[0])
        expl = abstention_explanation(head, target_x[idx], op["tau"])
        print(f"\nABSTENTION EXPLANATION for declined deployment case #{idx}:")
        print(f"  answering bar L*={expl['L_star']:.3f};  |logit|="
              f"{expl['abs_logit']:.3f};  margin_to_answer="
              f"{expl['margin_to_answer']:.3f}  (>0 => declined)")
        order = np.argsort(-np.abs(expl["phi"]))
        print("  top feature contributions toward the decided-class confidence:")
        for j in order[:3]:
            print(f"    x{int(j)}: phi={expl['phi'][j]:+.3f}  "
                  f"toward_confidence={expl['toward_confidence'][j]:+.3f}")
    elif op is not None:
        print("\n(No declined deployment case in this batch -- coverage was 100%.)")

    # ---- what an honest decline looks like ----
    # A structural refusal issues NO certificate and puts every target record in a
    # single gate bucket, tagged with a reason code. Two structural reasons:
    #   * "pool-too-small"        -- target pool below MIN_ANSWERABLE
    #   * "insufficient-clusters" -- fewer than 50 record-carrying calibration sites
    print("\n" + "=" * 72)
    print("HONEST DECLINE (structural refusal, no certificate issued)")
    print("=" * 72)
    tiny = target_x[:5]                               # 5 < MIN_ANSWERABLE (=10)
    rep_small = run_certgate(cohorts["train"], cohorts["aux"], cohorts["cal"],
                             tiny, target_label="tiny-batch")
    print(f"  5-record target -> reason={rep_small['reason']!r}, "
          f"partition={rep_small['decline_partition']}")

    print("\n" + render_text(rep))

    # ---- tidy up the throwaway temp files ----
    for p in (hist_csv, deploy_csv):
        os.remove(p)
    os.rmdir(tmpdir)
    print(f"\n[io] cleaned up temp dir {tmpdir}")


if __name__ == "__main__":
    main()
