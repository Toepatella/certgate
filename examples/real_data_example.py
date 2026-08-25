"""Worked example: from a CSV-like dataset to a CertGate certificate.

This is the glue a practitioner writes when real multi-site clinical data
arrives. It runs end to end:

  1. Write a small synthetic dataset to a temporary CSV, then read it back with
     the stdlib csv module -- no pandas, so the genuine from-a-file path gets
     exercised.
  2. Split sites into train / aux / cal by site, never by record.
  3. Build each split's Cohort with from_raw.
  4. Run run_certgate without oracle labels and print the report: certified
     rungs, guarantee statement, decline partition, and one abstention
     explanation.
  5. Show what an honest decline looks like.

Run it directly:  python examples/real_data_example.py
Deterministic: everything seeds from certgate.constants.SEED.
"""
import csv
import os
import sys
import tempfile

import numpy as np

# Run directly, this script puts examples/ on sys.path rather than the repo
# root, so `import certgate` would fail. Add the repo root. Module level, never
# inside a function -- that is the repo's top-level-imports invariant.
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
    """Historical multi-site data with outcomes, as a hospital might export it.

    Columns: site, outcome, x0..x{d-1}; one row per patient record. This is the
    shape of data you already have labels for -- the calibration sites.
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
    """A new deployment batch: site id + features, no outcome column.

    In real deployment the outcomes do not exist yet. These are the patients
    whose risk we are about to gate, and certification never needs their labels.

    The site column must still travel with the batch. A multi-site pool hands it
    to run_certgate as target_site_id, which feeds both the per-site target
    disjointness gate and BBSE's cluster-correct q interval.
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
    """Partition whole sites into train / aux / cal by SPLIT_FRACTIONS.

    Split by site, NEVER by record. The site (hospital) is the unit of
    statistical independence, which is the whole point of CertGate.

      - run_certgate asserts site-disjointness (assert_site_disjoint) across
        train/aux/cal, and rejects a target naming any train/aux/cal site -- the
        target must be a genuinely new site too. For a multi-site pool, pass
        target_site_id so the check runs per site; it also gives BBSE its
        cluster-correct q_t interval. This example's pool spans 12 sites.
      - Even if that slipped through, a record-level split would silently break
        the finite-sample guarantee by leaking across the calibration draw.

    Refs: audit V9 (target-site rejection).
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

    from_raw does the whole raw -> Cohort job: coerce_labels maps the
    "case"/"control" strings to strict bool (positive_label="case"),
    densify_sites maps raw site ids to dense 0..K-1, and make_cohort runs the
    loud input checks. Fitting cohorts keep require_both_classes=True, since
    single-class data breaks the head fit.

    Missing-label sentinels are NOT auto-detected. coerce_labels rejects only
    NaN and None; domain sentinels like -1, 9, "NA" or "" count as ordinary
    label values, and a third distinct value trips the ">2 distinct labels"
    error. Clean them out of the outcome column before calling from_raw.
    """
    cohorts = {}
    for name, b in buckets.items():
        cohorts[name] = from_raw(np.asarray(b["x"], dtype=np.float64),
                                 np.asarray(b["y"]),      # string dtype -> bool
                                 POSITIVE, b["sites"])
    return cohorts


def main():
    rng = np.random.default_rng(SEED)                 # deterministic throughout

    # The documented 208-site generator (SimConfig defaults). 40% of 208 is
    # about 83 calibration sites, clearing the 50-record-carrying floor, and
    # this exact draw is the split tests/test_pipeline.py pins as certifying
    # alpha=0.10. The temp CSV is ~35 MB, the price of realistic site sizes:
    # feasibility rides on both cluster count and per-site atom noise.
    cfg = SimConfig()
    historical = draw_cohort(cfg, 208, rng)
    # The deployment batch is a multi-site pool of 12 new sites. Twelve is above
    # BBSE_MIN_TARGET_SITES=10, so BBSE's q interval takes the cluster-bootstrap
    # path instead of declining. Only features matter here, so
    # require_both_classes=False -- a real batch may legitimately be all one
    # class. It draws from its own rng stream, so the pool's shape can never
    # reshuffle the historical split above.
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

    # ---- run the gate without oracle labels ----
    # Certification NEVER needs target labels. It certifies the answered-set
    # error rate from the calibration draw. Without oracle labels the report
    # only omits the diagnostic oracle composition; every certified or
    # estimated number still fires.
    # target_site_id carries the pool's per-record raw site labels, so the
    # pipeline can assert every target site is disjoint from train/aux/cal, and
    # BBSE's q_t interval becomes a cluster bootstrap over the 12 target sites
    # instead of a single-site Clopper-Pearson interval.
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
            # mode_outcomes records why the other mode did not contribute. On
            # real data, BBSE silently not contributing is the interesting
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
    # Re-fit the head on train to explain a specific case. fit_head is
    # deterministic, so this is the same head run_certgate fit internally.
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
    # A structural refusal issues no certificate. Every target record lands in
    # one gate bucket, tagged with a reason code. The two structural reasons:
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
