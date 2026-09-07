"""The false-negative frontier under a second, positives-normalised atom.

The released frontier (experiments/out/E9_fnr.csv, arm B of the ninth
experiment) certifies the influence-weighted false-negative rate among
answered positives on the unmodified atom: influence_atoms with weights = y
and the site weight g_c = min(n_c, 100) inherited from R_M. Against a measured
truth near 0.45, no budget below 0.55 issues at realistic site counts. The
panel asked whether that price belongs to the estimand or to its
normalisation: a site's positives are a tenth of its records, so the
inherited weight divides each site's false negatives by ten times more
records than carry them, and the margin the walk must certify shrinks with
it.

This file runs the frozen arm again, row for row, and beside it a second arm
on the same draws: the same influence_atoms, restricted to each site's
positive records, with the site weight taken on the positive count,
g_c^+ = min(n_c^+, M^+) and M^+ = 10. Both estimands are reported for every
certificate, each scored on the same fresh pool under its own normalisation
and under the other's. The shipped arm must reproduce the frozen CSV cell for
cell before the positives arm is written at all.

Why the positives-normalised atom is valid, engaging the SPEC's stated
objection ("Outcome-weighted atoms", the paragraph beginning "Validity"). The
SPEC keeps g_c on the full site size because "renormalizing by per-site
answered positives would make the weight outcome-dependent and void the
outcome-independence requirement on g_c". The atom here does not renormalise
by answered positives. Its weight is a function of the site's positive COUNT
n_c^+: fixed by the site's labels before any threshold is chosen, the same at
every rung of the tau grid, and never a function of the head's errors or of
which records answer. What the requirement protects is that the certified
quantity be one fixed functional of the site distribution that the
certificate can name; a threshold-dependent weight would make the estimand
move with tau. n_c^+ is tau-independent, so the estimand is fixed:
FNR_M^+ = E[g_c^+ fn_c / n_c^+] / E[g_c^+ ap_c / n_c^+], with fn_c the
answered false negatives and ap_c the answered positives at site c, a
ratio-of-expectations over the site draw exactly parallel to R_M. Under
Assumption 1 the sites are exchangeable draws, so (n_c^+, the positives'
scores and errors) are i.i.d. across sites and the per-site atoms
Z_c = b + (g_c^+ / (M^+ n_c^+)) sum_{i in c, y_i = 1} ans_i (err_i - b) are
i.i.d. and bounded: the inner sum lies in [-b n_c^+, (1 - b) n_c^+], the
prefactor scales it into [-b, 1 - b], and the shift lands in [0, 1]. A site
with no positives, or none answered, enters as the neutral atom Z_c = b, as
record-less sites do for R_M. The sign identity E[Z] <= b iff FNR_M^+ <= b
holds exactly as it does for the shipped atom. What changes is the estimand
-- sites now count by their positives, capped at ten, rather than by their
records capped at a hundred -- and the manuscript reports both, because a
certificate is a statement about one named estimand and the choice between
them is a modelling decision, not a free lunch.

--quick runs 20 draws per site count. The full run is E9_FNR_R = 200 draws
at 208, 400 and 600 sites, the frozen grid.

Run: python -m experiments.run_e9b_positives [--quick] [--out DIR]

Writes E9b_fnr_positives.csv, .json and .png into
experiments/out-e9b-positives/. The PNG is the certify-rate-versus-budget
frontier for both arms, drawn in the style of E9_frontiers.png. The JSON
carries a _run block (UTC, git sha, sha256 of the frozen input).

Refs: SPEC "Outcome-weighted atoms"; fix-pass plan WP2; panel action item 5.
"""

import argparse
import os
import sys
import time

import matplotlib
matplotlib.use("Agg")                       # headless: no interactive display
import matplotlib.pyplot as plt
import numpy as np

from certgate.constants import DELTA, M_INFLUENCE, TAU_GRID
from certgate.certify import influence_atoms, walk_order, fixed_sequence_walk
from certgate.data import SimConfig, draw_cohort
from experiments.run_synthetic import (E1_EVAL_SITES, E9_FNR_LADDER,
                                       E9_FNR_SWEEP, E9_FNR_R, _rng,
                                       _draw_split, _e9_fnr_rng, _fnr_on_pool,
                                       _rescore, _rollup, _rate_ci95,
                                       _write_csv)
from experiments.derive_fixpass_numbers import (EXP_DIR, assert_not_frozen,
                                                run_block, _read_csv)
from experiments.run_eicu import _write_json

OUT_DIR = os.path.join(EXP_DIR, "out-e9b-positives")
FROZEN = os.path.join(EXP_DIR, "out", "E9_fnr.csv")
E9B_POS_M = 10                              # M^+: cap on the positive count
ARMS = ("shipped", "positives")
FROZEN_FIELDS = ("certified", "tau", "coverage", "fnr_fresh", "fnr_exceed",
                 "true_fnr_at_lowest_tau")

POST_HOC = ("[MEASURE] POST-HOC (2026-09-04): a second, positives-normalised "
            "estimand run beside the released false-negative frontier on the "
            "same draws; the frozen CSV is unchanged and reproduced row for "
            "row before this arm is written. An experimental secondary "
            "certificate, never the deployed report.")

ESTIMAND_NOTE = (
    "shipped: influence_atoms with weights = y and g_c = min(n_c, 100) on the "
    "full site size, the atom the paper ships (SPEC 'Outcome-weighted "
    "atoms'). positives: the same influence_atoms on each site's positive "
    "records with g_c^+ = min(n_c^+, 10) on the positive count. The two "
    "certify different estimands, FNR_M (sites weighted by records, cap 100) "
    "and FNR_M^+ (sites weighted by positives, cap 10); each certificate is "
    "scored on the fresh pool under both. n_c^+ is a function of the site's "
    "labels alone: tau-independent, error-independent, fixed before any "
    "threshold is chosen, so the estimand is one named functional of the "
    "site distribution and the atoms stay i.i.d. and in [0, 1] under "
    "Assumption 1.")


def _positives_atoms(score, err, site_id, n_sites, y, budget, M=E9B_POS_M):
    """Positives-normalised FNR atoms, shape (n_tau, n_sites).

    The frozen influence_atoms on the y == 1 records only: bincount of the
    restricted site ids gives n_c^+, so g/(M n) inside the library becomes
    g_c^+ / (M^+ n_c^+) with no library change. Among positives err is the
    false-negative indicator, so the sign identity E[Z] <= b iff
    FNR_M^+ <= b holds exactly as for the shipped atom.
    """
    pos = np.asarray(y, dtype=bool)
    return influence_atoms(np.asarray(score)[pos], np.asarray(err)[pos],
                           np.asarray(site_id)[pos], n_sites, TAU_GRID,
                           budget, M)


def _fnr_pos_on_pool(head, pool, tau, M=E9B_POS_M):
    """Positives-normalised false-negative rate on a fresh pool.

    FNR_M^+ = sum_c (g_c^+/n_c^+) fn_c / sum_c (g_c^+/n_c^+) ap_c with
    g_c^+ = min(n_c^+, M) on the site's positive count. The twin of
    _fnr_on_pool. Returns NaN when no positives answer.
    """
    score = head.score(pool.x)
    err = head.predict(pool.x) != pool.y
    ans = score >= tau
    pos = np.asarray(pool.y, dtype=bool)
    n_pos = np.bincount(pool.site_id, weights=pos.astype(float),
                        minlength=pool.n_sites)
    g_over_n = np.where(n_pos > 0,
                        np.minimum(n_pos, M) / np.maximum(n_pos, 1.0), 0.0)
    num_c = np.bincount(pool.site_id, weights=(ans & err & pos).astype(float),
                        minlength=pool.n_sites)
    den_c = np.bincount(pool.site_id, weights=(ans & pos).astype(float),
                        minlength=pool.n_sites)
    num = float((g_over_n * num_c).sum())
    den = float((g_over_n * den_c).sum())
    return (num / den) if den > 0 else float("nan")


def _cell(v):
    """Render a value the way the frozen CSV's DictWriter did."""
    return "" if v is None else str(v)


def run_draw(n_idx, r, cfg=None):
    """Both arms on one frozen arm-B draw, _rng(9, 1, n_idx, r).

    The shipped rows are built exactly as run_E9 builds them, so they can be
    compared cell for cell with the frozen CSV. Returns (shipped_rows,
    positives_rows), each one row per budget.
    """
    cfg = cfg or SimConfig()
    n_sites = E9_FNR_SWEEP[n_idx]
    rng = _rng(9, 1, n_idx, r)
    train, aux, cal, head = _draw_split(cfg, n_sites, rng)
    evalp = draw_cohort(cfg, E1_EVAL_SITES, rng,
                        site_label_prefix=f"e9fv{n_idx}_{r}")
    sc_cal, er_cal = head.score(cal.x), head.predict(cal.x) != cal.y
    sc_aux, er_aux = head.score(aux.x), head.predict(aux.x) != aux.y
    w_cal = cal.y.astype(float)
    w_aux = aux.y.astype(float)
    true_fnr = _fnr_on_pool(head, evalp, float(TAU_GRID[0]))
    true_fnr_pos = _fnr_pos_on_pool(head, evalp, float(TAU_GRID[0]))
    shipped, positives = [], []
    for budget in E9_FNR_LADDER:
        # ---- shipped arm, call for call as run_E9 ----------------------
        a_aux = influence_atoms(sc_aux, er_aux, aux.site_id, aux.n_sites,
                                TAU_GRID, budget, M_INFLUENCE, weights=w_aux,
                                wmax=1.0)
        a_cal = influence_atoms(sc_cal, er_cal, cal.site_id, cal.n_sites,
                                TAU_GRID, budget, M_INFLUENCE, weights=w_cal,
                                wmax=1.0)
        _, dep = fixed_sequence_walk(a_cal, walk_order(a_aux), budget, DELTA,
                                     TAU_GRID, rng=_e9_fnr_rng(budget,
                                                               "e9-fnr"))
        row = dict(n_sites=n_sites, draw=r, fnr_budget=budget,
                   certified=dep is not None, tau=None, coverage=None,
                   fnr_fresh=None, fnr_exceed=None,
                   true_fnr_at_lowest_tau=round(true_fnr, 6))
        if dep is not None:
            row.update(_rescore(head, evalp, dep, budget, risk=_fnr_on_pool,
                                risk_key="fnr_fresh", exceed_key="fnr_exceed"))
        shipped.append(row)
        # ---- positives arm: same draw, positives-normalised atoms -------
        p_aux = _positives_atoms(sc_aux, er_aux, aux.site_id, aux.n_sites,
                                 aux.y, budget)
        p_cal = _positives_atoms(sc_cal, er_cal, cal.site_id, cal.n_sites,
                                 cal.y, budget)
        _, dep_p = fixed_sequence_walk(p_cal, walk_order(p_aux), budget,
                                       DELTA, TAU_GRID,
                                       rng=_e9_fnr_rng(budget, "e9-fnr-pos"))
        prow = dict(n_sites=n_sites, draw=r, fnr_budget=budget,
                    certified=dep_p is not None, tau=None, coverage=None,
                    fnr_fresh=None, fnr_exceed=None,
                    true_fnr_at_lowest_tau=round(true_fnr_pos, 6))
        if dep_p is not None:
            prow.update(_rescore(head, evalp, dep_p, budget,
                                 risk=_fnr_pos_on_pool, risk_key="fnr_fresh",
                                 exceed_key="fnr_exceed"))
        positives.append(prow)
    # cross-scoring: each certificate under the other estimand too
    for row, other in ((shipped, _fnr_pos_on_pool),
                       (positives, _fnr_on_pool)):
        for x in row:
            if x["certified"]:
                v = other(head, evalp, x["tau"])
                x["fnr_fresh_other"] = round(v, 6)
                x["fnr_exceed_other"] = bool(v > x["fnr_budget"])
            else:
                x["fnr_fresh_other"] = None
                x["fnr_exceed_other"] = None
    return shipped, positives


def _check_shipped(shipped, frozen_rows):
    """Cell-for-cell comparison of the shipped rows with the frozen CSV."""
    frozen = {(int(f["n_sites"]), int(f["draw"]), float(f["fnr_budget"])): f
              for f in frozen_rows}
    mismatches = []
    for x in shipped:
        f = frozen.get((x["n_sites"], x["draw"], x["fnr_budget"]))
        if f is None:
            mismatches.append(dict(row=(x["n_sites"], x["draw"],
                                        x["fnr_budget"]),
                                   reason="not in frozen CSV"))
            continue
        for k in FROZEN_FIELDS:
            if _cell(x[k]) != f[k]:
                mismatches.append(dict(row=(x["n_sites"], x["draw"],
                                            x["fnr_budget"]), field=k,
                                       frozen=f[k], replayed=_cell(x[k])))
    return mismatches


def run(quick=False, log=print):
    fnr_R = 20 if quick else E9_FNR_R
    frozen = _read_csv(FROZEN)
    t0 = time.perf_counter()
    rows = []
    shipped_all = []
    for n_idx, n_sites in enumerate(E9_FNR_SWEEP):
        for r in range(fnr_R):
            shipped, positives = run_draw(n_idx, r)
            shipped_all += shipped
            for arm, arm_rows in (("shipped", shipped),
                                  ("positives", positives)):
                for x in arm_rows:
                    rows.append(dict(arm=arm, **x))
        if log:
            log(f"[certgate] e9b positives: {n_sites} sites done "
                f"({time.perf_counter() - t0:.0f} s)")
    mismatches = _check_shipped(shipped_all, frozen)
    if mismatches:
        raise SystemExit(
            f"run_e9b_positives: the shipped arm did not reproduce the frozen "
            f"E9_fnr.csv on {len(mismatches)} cells, e.g. {mismatches[:3]}; "
            f"the positives arm is not trusted and nothing is written "
            f"(reason=shipped-arm-mismatch)")
    check = dict(shipped_rows_compared=len(shipped_all), mismatches=0,
                 frozen_rows=len(frozen), fnr_R=fnr_R, quick=bool(quick),
                 wall_clock_s=round(time.perf_counter() - t0, 1))
    return rows, check


def summarise(rows, check):
    fnr_R = check["fnr_R"]
    frontier = {arm: {} for arm in ARMS}
    for arm in ARMS:
        for budget in E9_FNR_LADDER:
            per = {}
            for n_sites in E9_FNR_SWEEP:
                sub = [x for x in rows if x["arm"] == arm
                       and x["fnr_budget"] == budget
                       and x["n_sites"] == n_sites]
                certs = [x for x in sub if x["certified"]]
                cell = _rollup(certs, fnr_R,
                               ("certify_rate", "mean_tau", "mean_fnr_fresh",
                                "fnr_exceed_rate"),
                               none_certify=not sub, risk_key="fnr_fresh",
                               exceed_key="fnr_exceed")
                k = sum(bool(x["fnr_exceed"]) for x in certs)
                k_o = sum(bool(x["fnr_exceed_other"]) for x in certs)
                cell["n_certified"] = len(certs)
                cell["certify_rate_ci95"] = _rate_ci95(len(certs), len(sub))
                cell["fnr_exceed_rate_ci95"] = _rate_ci95(k, len(certs))
                cell["fnr_exceed_rate_other_estimand"] = (
                    round(k_o / len(certs), 4) if certs else None)
                cell["mean_fnr_fresh_other_estimand"] = (
                    round(float(np.mean([x["fnr_fresh_other"]
                                         for x in certs])), 4)
                    if certs else None)
                per[str(n_sites)] = cell
            frontier[arm][str(budget)] = per
    truth = {}
    for arm in ARMS:
        truth[arm] = {}
        for n_sites in E9_FNR_SWEEP:
            vals = [x["true_fnr_at_lowest_tau"] for x in rows
                    if x["arm"] == arm and x["n_sites"] == n_sites
                    and x["fnr_budget"] == E9_FNR_LADDER[0]]
            truth[arm][str(n_sites)] = round(float(np.mean(vals)), 4)
        truth[arm]["all"] = round(float(np.mean(
            [x["true_fnr_at_lowest_tau"] for x in rows if x["arm"] == arm
             and x["fnr_budget"] == E9_FNR_LADDER[0]])), 4)
    total_exceed = {arm: sum(bool(x["fnr_exceed"]) for x in rows
                             if x["arm"] == arm and x["certified"])
                    for arm in ARMS}
    total_exceed_other = {arm: sum(bool(x["fnr_exceed_other"]) for x in rows
                                   if x["arm"] == arm and x["certified"])
                          for arm in ARMS}
    s5, p5 = frontier["shipped"]["0.5"], frontier["positives"]["0.5"]
    s55, p55 = frontier["shipped"]["0.55"], frontier["positives"]["0.55"]
    headline = (
        f"certify rate at b=0.5 by sites {list(E9_FNR_SWEEP)}: shipped "
        f"{[s5[str(n)]['certify_rate'] for n in E9_FNR_SWEEP]} vs positives "
        f"{[p5[str(n)]['certify_rate'] for n in E9_FNR_SWEEP]}; b=0.55: "
        f"shipped {[s55[str(n)]['certify_rate'] for n in E9_FNR_SWEEP]} vs "
        f"positives {[p55[str(n)]['certify_rate'] for n in E9_FNR_SWEEP]}; "
        f"fresh-pool exceedances under own estimand "
        f"{total_exceed}, under the other {total_exceed_other}; truth "
        f"shipped {truth['shipped']['all']} positives "
        f"{truth['positives']['all']}")
    return dict(post_hoc=POST_HOC, estimand=ESTIMAND_NOTE, headline=headline,
                shipped_row_check=check, M_positives=E9B_POS_M,
                M_shipped=M_INFLUENCE, fnr_R=fnr_R, ladder=list(E9_FNR_LADDER),
                sweep=list(E9_FNR_SWEEP), fnr_frontier=frontier,
                true_fnr_at_lowest_tau_mean=truth,
                total_fresh_exceedances_own_estimand=total_exceed,
                total_fresh_exceedances_other_estimand=total_exceed_other)


def figure(doc, path):
    """Certify rate vs FNR budget at each site count, one panel per arm.

    Same Paul-Tol hex set, markers and dpi as E9_frontiers.png's right panel,
    so Figure S10 reads as a continuation of Figure 5. The dotted vertical is
    each arm's mean truth at the lowest threshold.
    """
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    titles = dict(shipped=f"Shipped atom: g_c = min(n_c, {M_INFLUENCE})",
                  positives=f"Positives-normalised atom: g_c+ = "
                            f"min(n_c+, {E9B_POS_M})")
    for a, arm in zip(axes, ARMS):
        fr = doc["fnr_frontier"][arm]
        for n_sites, color in zip(E9_FNR_SWEEP,
                                  ("#cc6677", "#4477aa", "#228833")):
            a.plot(E9_FNR_LADDER,
                   [fr[str(b)][str(n_sites)]["certify_rate"]
                    for b in E9_FNR_LADDER],
                   "-o", color=color, label=f"{n_sites} sites", ms=4)
        a.axvline(doc["true_fnr_at_lowest_tau_mean"][arm]["all"],
                  color="grey", ls=":", lw=1,
                  label="mean truth at lowest tau")
        a.set_xlabel("FNR budget")
        a.set_title(titles[arm], fontsize=10)
        a.set_ylim(-0.03, 1.03)
        a.legend(fontsize=8)
    axes[0].set_ylabel(f"certify rate (R = {doc['fnr_R']})")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


FIELDS = ["arm", "n_sites", "draw", "fnr_budget", "certified", "tau",
          "coverage", "fnr_fresh", "fnr_exceed", "fnr_fresh_other",
          "fnr_exceed_other", "true_fnr_at_lowest_tau"]


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="the FNR frontier under the shipped and the "
                    "positives-normalised atom")
    ap.add_argument("--quick", action="store_true",
                    help="20 draws per site count")
    ap.add_argument("--out", default=OUT_DIR)
    args = ap.parse_args(argv)
    paths = {ext: os.path.join(args.out, f"E9b_fnr_positives.{ext}")
             for ext in ("csv", "json", "png")}
    for p in paths.values():
        assert_not_frozen(p)
    t0 = time.perf_counter()
    rows, check = run(quick=args.quick)
    doc = summarise(rows, check)
    doc["wall_clock_s"] = round(time.perf_counter() - t0, 1)
    os.makedirs(args.out, exist_ok=True)
    _write_csv(paths["csv"], rows, FIELDS)
    _write_json(paths["json"], {"_run": run_block([FROZEN]), **doc},
                "run_e9b_positives")
    figure(doc, paths["png"])
    print(f"[certgate] {doc['headline']}")
    print(f"[certgate] wrote {', '.join(paths.values())} "
          f"({doc['wall_clock_s']} s)", file=sys.stderr)
    return doc


if __name__ == "__main__":
    main()
