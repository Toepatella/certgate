"""Rescore the label-shift power frontier against the declared target's own prevalence.

The released power frontier (experiments/out/E9_bbse_frontier.csv, arm A of
the ninth experiment) scores every BBSE certificate against a fresh 200-site
pool drawn at the population shift, and finds the single-declared-site path
exceeding its budget in 2 of 20 certificates at 1,200 source sites. That
scoring asks a question the certificate never answered. Under label shift the
mode certifies for the DECLARED target's prevalence -- the one site whose
predicted-positive rate went into the uncertainty box -- and a single site
carries its own random effect on the log-odds base rate, so its prevalence is
not the population's. Scoring it against the population pool compares two
estimands.

This file replays every draw with a certified rung on its frozen stream
(_rng(9, 0, n_idx, m_idx, r) -> cohort -> split -> head -> declared target ->
fresh eval pool; run_certgate and fit_head consume nothing from that stream,
so the replay reproduces the frozen pool byte for byte). It checks that the
replayed R_M matches the frozen rm_fresh to four decimals on every certified
row, refusing to emit anything if one differs, and then rescores each
certificate on the same fresh pool reweighted by class to the declared
target's own oracle prevalence. Both scores are reported side by side. The
frozen CSV is never opened for writing.

The reweighting: with pi_t the declared pool's prevalence and pi_e the fresh
pool's, every fresh positive carries weight pi_t / pi_e and every negative
(1 - pi_t) / (1 - pi_e), inside the same influence-weighted ratio that
_rm_on_pool computes. When pi_t equals pi_e the two scores coincide exactly,
and the test suite pins that. The declared pool's odds ratio against the
source is also checked against the frozen [rho_lo, rho_hi], beside the
population's, so the reader can see which of the two the box was covering.

--rho-point re-runs the pipeline in bbse mode on the replayed draws to
recover the box's point estimate and the prevalence it implies, neither of
which is in the frozen CSV. It costs one BBSE fit per draw and changes
nothing above; the recovered box is compared with the frozen one as a second
self-check.

Run: python -m experiments.rescore_e9a [--rho-point] [--out DIR]

Writes E9a_rescore.csv and E9a_rescore.json into experiments/out-e9a-rescore/.
The JSON carries a _run block (UTC, git sha, sha256 of the frozen input).

Refs: SPEC "E9" arm A; fix-pass plan WP2; panel action item 4.
"""

import argparse
import os
import sys
import time

import numpy as np

from certgate.constants import M_INFLUENCE
from certgate.data import SimConfig, draw_cohort, split_sites
from certgate.model import fit_head
from certgate.pipeline import run_certgate
from experiments.run_synthetic import (E1_EVAL_SITES, E9_SOURCE_SWEEP,
                                       E9_TARGET_MODES, E9_TARGET_K,
                                       SHIFT_BASE, _rng, _rm_on_pool,
                                       _rate_ci95, _write_csv)
from experiments.derive_fixpass_numbers import (EXP_DIR, assert_not_frozen,
                                                run_block, _read_csv)
from experiments.run_eicu import _write_json

OUT_DIR = os.path.join(EXP_DIR, "out-e9a-rescore")
FROZEN = os.path.join(EXP_DIR, "out", "E9_bbse_frontier.csv")
SELF_CHECK_DP = 4
# The three rows the frozen arm flags as exceeding, at the four decimals the
# fix-pass plan pins. If the replay stops reproducing them, nothing is written.
EXCEEDING_ROWS = {
    (1200, "single-site-cp", 29, 0.05): 0.0580,
    (1200, "single-site-cp", 29, 0.10): 0.1068,
    (1200, "single-site-cp", 48, 0.10): 0.1089,
}

POST_HOC = ("[MEASURE] POST-HOC (2026-09-04): replay and rescoring of the "
            "released label-shift power frontier; the frozen CSV is "
            "unchanged and no certified quantity descends from this file. "
            "The rescored column is a second estimand for the same "
            "certificates, not a correction of the first.")

ESTIMAND_NOTE = (
    "rm_fresh scores each certificate on a fresh 200-site pool at the "
    "population shift (target base rate 0.22 with site random effects). "
    "rm_rescored scores the same certificate on the same pool reweighted by "
    "class to the declared target pool's own oracle prevalence pi_target, "
    "which is what the BBSE box was fitted to. pi_eval is the fresh pool's "
    "prevalence; pi_source the source cohort's. rho_site = "
    "odds(pi_target)/odds(pi_source) is the odds ratio the certificate "
    "declared; rho_pop = odds(pi_eval)/odds(pi_source) the one the fresh pool "
    "realises.")


def _odds(p):
    return p / (1.0 - p)


def _rm_reweighted(head, pool, tau, pi_target, M=M_INFLUENCE):
    """R_M on a pool reweighted by class to prevalence pi_target.

    Same influence-weighted ratio as _rm_on_pool, with each record carrying
    the class weight that moves the pool's prevalence from pi_e to pi_target:
    pi_target / pi_e on positives, (1 - pi_target) / (1 - pi_e) on negatives.
    At pi_target == pi_e every weight is 1 and this equals _rm_on_pool.
    Returns NaN when nothing answers or the pool is single-class.
    """
    score = head.score(pool.x)
    err = head.predict(pool.x) != pool.y
    ans = score >= tau
    pi_e = float(pool.y.mean())
    if not 0.0 < pi_e < 1.0:
        return float("nan")
    w = np.where(pool.y, pi_target / pi_e, (1.0 - pi_target) / (1.0 - pi_e))
    sizes = pool.site_sizes.astype(float)
    g_over_n = np.where(sizes > 0,
                        np.minimum(sizes, M) / np.maximum(sizes, 1.0), 0.0)
    num_c = np.bincount(pool.site_id, weights=w * (ans & err),
                        minlength=pool.n_sites)
    den_c = np.bincount(pool.site_id, weights=w * ans, minlength=pool.n_sites)
    num = float((g_over_n * num_c).sum())
    den = float((g_over_n * den_c).sum())
    return (num / den) if den > 0 else float("nan")


def replay_draw(n_idx, m_idx, r, cfg=None):
    """Replay one arm-A draw on its frozen stream.

    Mirrors run_E9 arm A call for call: cohort, split, head, declared target,
    then the fresh eval pool -- in that order, on _rng(9, 0, n_idx, m_idx, r).
    The pipeline call that sits between target and eval pool in run_E9 draws
    nothing from this stream (its BBSE bootstrap seeds from the target bytes,
    its walks from certification_rng), so it is left out here and run only
    under --rho-point, after the pool is drawn.
    """
    cfg = cfg or SimConfig()
    n_sites = E9_SOURCE_SWEEP[n_idx]
    mode = E9_TARGET_MODES[m_idx]
    rng = _rng(9, 0, n_idx, m_idx, r)
    coh = draw_cohort(cfg, n_sites, rng)
    train, aux, cal = split_sites(coh, rng)
    head = fit_head(train)
    if mode == "single-site-cp":
        tgt = draw_cohort(cfg, 1, rng, label_base_rate=SHIFT_BASE,
                          site_label_prefix=f"e9t{n_idx}_{r}",
                          require_both_classes=False)
        tgt_sites = None
    else:
        tgt = draw_cohort(cfg, E9_TARGET_K, rng, label_base_rate=SHIFT_BASE,
                          site_label_prefix=f"e9k{n_idx}_{r}")
        tgt_sites = np.array(tgt.site_labels, dtype=object)[tgt.site_id]
    evalp = draw_cohort(cfg, E1_EVAL_SITES, rng, label_base_rate=SHIFT_BASE,
                        site_label_prefix=f"e9v{n_idx}_{r}")
    return dict(n_sites=n_sites, mode=mode, draw=r, head=head, train=train,
                aux=aux, cal=cal, tgt=tgt, tgt_sites=tgt_sites, evalp=evalp,
                pi_source=float(coh.y.mean()))


def _frozen_certified(frozen_rows):
    """{(n_idx, m_idx, draw): [certified rows]} from the frozen CSV."""
    draws = {}
    for row in frozen_rows:
        if row["certified"] != "True":
            continue
        key = (E9_SOURCE_SWEEP.index(int(row["n_source_sites"])),
               E9_TARGET_MODES.index(row["target_mode"]), int(row["draw"]))
        draws.setdefault(key, []).append(row)
    return draws


def rescore(rho_point=False, draws=None, frozen_path=FROZEN, log=print):
    """Replay, self-check and rescore every certified frozen row.

    draws restricts the replay to a subset of (n_idx, m_idx, draw) keys (the
    test suite replays one). Returns (rows, summary).
    """
    frozen = _read_csv(frozen_path)
    certified = _frozen_certified(frozen)
    keys = sorted(certified) if draws is None else sorted(draws)
    rows, mismatches = [], []
    t0 = time.perf_counter()
    for i, key in enumerate(keys):
        n_idx, m_idx, r = key
        rep = replay_draw(n_idx, m_idx, r)
        head, tgt, evalp = rep["head"], rep["tgt"], rep["evalp"]
        pi_t, pi_e, pi_s = (float(tgt.y.mean()), float(evalp.y.mean()),
                            rep["pi_source"])
        bbse = None
        if rho_point:
            report = run_certgate(rep["train"], rep["aux"], rep["cal"], tgt.x,
                                  target_label=f"E9a-{rep['n_sites']}-"
                                               f"{rep['mode']}-{r}",
                                  target_site_id=rep["tgt_sites"],
                                  oracle_target_y=tgt.y, modes=("bbse",))
            bbse = report["diagnostic"]["bbse"]
        for fr in certified[key]:
            alpha = float(fr["alpha"])
            tau = float(fr["tau"])
            rm_frozen = float(fr["rm_fresh"])
            rm_replayed = round(_rm_on_pool(head, evalp, tau), 6)
            cov_replayed = round(float((head.score(evalp.x) >= tau).mean()), 4)
            ok = (round(rm_replayed, SELF_CHECK_DP)
                  == round(rm_frozen, SELF_CHECK_DP)
                  and cov_replayed == round(float(fr["coverage"]), 4))
            if not ok:
                mismatches.append(dict(key=key, alpha=alpha,
                                       frozen=rm_frozen, replayed=rm_replayed,
                                       coverage_frozen=fr["coverage"],
                                       coverage_replayed=cov_replayed))
            rm_res = _rm_reweighted(head, evalp, tau, pi_t)
            rho_lo, rho_hi = float(fr["rho_lo"]), float(fr["rho_hi"])
            rho_site = _odds(pi_t) / _odds(pi_s)
            rho_pop = _odds(pi_e) / _odds(pi_s)
            row = dict(
                n_source_sites=rep["n_sites"], target_mode=rep["mode"],
                draw=r, alpha=alpha, tau=round(tau, 4),
                coverage_frozen=float(fr["coverage"]),
                coverage_replayed=cov_replayed,
                rm_fresh_frozen=rm_frozen, rm_fresh_replayed=rm_replayed,
                self_check_4dp=ok,
                rm_exceed_frozen=fr["rm_exceed"] == "True",
                pi_target=round(pi_t, 6), pi_eval=round(pi_e, 6),
                pi_source=round(pi_s, 6),
                rm_rescored=round(rm_res, 6),
                rm_rescored_exceed=bool(rm_res > alpha),
                rho_lo=round(rho_lo, 6), rho_hi=round(rho_hi, 6),
                rho_site=round(rho_site, 6), rho_pop=round(rho_pop, 6),
                box_covers_rho_site=bool(rho_lo <= rho_site <= rho_hi),
                box_covers_rho_pop=bool(rho_lo <= rho_pop <= rho_hi),
                rho_point=None, pi_t_implied=None, q_target=None,
                box_matches_frozen_6dp=None)
            if bbse is not None:
                q, c0, c1 = bbse["q_target"], bbse["c0"], bbse["c1"]
                row.update(
                    rho_point=round(float(bbse["rho_point"]), 6),
                    pi_t_implied=round((q - c0) / (c1 - c0), 6),
                    q_target=round(float(q), 6),
                    box_matches_frozen_6dp=bool(
                        round(float(bbse["rho_lo"]), 6) == round(rho_lo, 6)
                        and round(float(bbse["rho_hi"]), 6)
                        == round(rho_hi, 6)))
            rows.append(row)
        if log and (i % 10 == 9 or i == len(keys) - 1):
            log(f"[certgate] e9a rescore: {i + 1}/{len(keys)} draws "
                f"({time.perf_counter() - t0:.0f} s)")
    if mismatches:
        raise SystemExit(
            f"rescore_e9a: {len(mismatches)} certified rows did not replay to "
            f"{SELF_CHECK_DP} dp: {mismatches[:3]} -- the frozen stream and "
            f"the replay have diverged; nothing written "
            f"(reason=replay-mismatch)")
    if draws is None:
        for (n, mode, d, alpha), expected in EXCEEDING_ROWS.items():
            got = next(x for x in rows if x["n_source_sites"] == n
                       and x["target_mode"] == mode and x["draw"] == d
                       and x["alpha"] == alpha)
            if round(got["rm_fresh_replayed"], 4) != expected:
                raise SystemExit(
                    f"rescore_e9a: exceeding row {(n, mode, d, alpha)} "
                    f"replayed {got['rm_fresh_replayed']}, expected "
                    f"{expected} to 4 dp; nothing written "
                    f"(reason=self-check-failed)")
    return rows, dict(draws_replayed=len(keys), rows_checked=len(rows),
                      mismatches=0, wall_clock_s=round(
                          time.perf_counter() - t0, 1))


def summarise(rows, check, frozen_rows, rho_point):
    """Per-cell frozen vs rescored exceedance, plus the exceeding rows."""
    R = {}
    for fr in frozen_rows:
        k = (int(fr["n_source_sites"]), fr["target_mode"], float(fr["alpha"]))
        R[k] = R.get(k, 0) + 1
    cells = {}
    for (n, mode, alpha), n_draws in sorted(R.items()):
        sub = [x for x in rows if x["n_source_sites"] == n
               and x["target_mode"] == mode and x["alpha"] == alpha]
        n_c = len(sub)
        k_frozen = sum(x["rm_exceed_frozen"] for x in sub)
        k_res = sum(x["rm_rescored_exceed"] for x in sub)
        cells[f"{n}|{mode}|{alpha}"] = dict(
            R=n_draws, n_certified=n_c,
            certify_rate=round(n_c / n_draws, 4),
            rm_exceed_frozen=dict(k=k_frozen, n=n_c,
                                  rate=(round(k_frozen / n_c, 4) if n_c
                                        else None),
                                  ci95=_rate_ci95(k_frozen, n_c)),
            rm_exceed_rescored=dict(k=k_res, n=n_c,
                                    rate=(round(k_res / n_c, 4) if n_c
                                          else None),
                                    ci95=_rate_ci95(k_res, n_c)),
            mean_rm_fresh=(round(float(np.mean(
                [x["rm_fresh_replayed"] for x in sub])), 4) if n_c else None),
            mean_rm_rescored=(round(float(np.mean(
                [x["rm_rescored"] for x in sub])), 4) if n_c else None),
            mean_pi_target=(round(float(np.mean(
                [x["pi_target"] for x in sub])), 4) if n_c else None),
            mean_pi_eval=(round(float(np.mean(
                [x["pi_eval"] for x in sub])), 4) if n_c else None),
            box_covers_rho_site=(round(float(np.mean(
                [x["box_covers_rho_site"] for x in sub])), 4) if n_c
                else None),
            box_covers_rho_pop=(round(float(np.mean(
                [x["box_covers_rho_pop"] for x in sub])), 4) if n_c
                else None))
    exceeding = [dict(n_source_sites=x["n_source_sites"],
                      target_mode=x["target_mode"], draw=x["draw"],
                      alpha=x["alpha"], tau=x["tau"],
                      rm_fresh=x["rm_fresh_replayed"],
                      rm_rescored=x["rm_rescored"],
                      rm_rescored_exceed=x["rm_rescored_exceed"],
                      pi_target=x["pi_target"], pi_eval=x["pi_eval"],
                      rho_site=x["rho_site"], rho_pop=x["rho_pop"],
                      rho_box=[x["rho_lo"], x["rho_hi"]],
                      box_covers_rho_site=x["box_covers_rho_site"],
                      box_covers_rho_pop=x["box_covers_rho_pop"])
                 for x in rows if x["rm_exceed_frozen"]]
    single = cells.get("1200|single-site-cp|0.1", {})
    headline = (
        f"single-site 1200 a=0.10: frozen rm_exceed "
        f"{single.get('rm_exceed_frozen', {}).get('k')} of "
        f"{single.get('n_certified')} (CI "
        f"{single.get('rm_exceed_frozen', {}).get('ci95')}); rescored to the "
        f"declared site's prevalence "
        f"{single.get('rm_exceed_rescored', {}).get('k')} of "
        f"{single.get('n_certified')}; all {len(rows)} certified rows "
        f"replayed to {SELF_CHECK_DP} dp")
    out = dict(post_hoc=POST_HOC, estimand=ESTIMAND_NOTE, headline=headline,
               self_check=dict(**check, exceeding_rows_pinned={
                   f"{k[0]}|{k[1]}|{k[2]}|{k[3]}": v
                   for k, v in EXCEEDING_ROWS.items()}),
               population_odds_ratio=round(_odds(SHIFT_BASE)
                                           / _odds(SimConfig().base_rate), 4),
               cells=cells, exceeding_rows=exceeding,
               rho_point_run=bool(rho_point))
    if rho_point:
        with_pt = [x for x in rows if x["rho_point"] is not None]
        out["rho_point"] = dict(
            rows=len(with_pt),
            box_matches_frozen_6dp=all(x["box_matches_frozen_6dp"]
                                       for x in with_pt),
            mean_abs_pi_t_implied_minus_pi_target=round(float(np.mean(
                [abs(x["pi_t_implied"] - x["pi_target"]) for x in with_pt])),
                4) if with_pt else None,
            mean_abs_pi_t_implied_minus_pi_eval=round(float(np.mean(
                [abs(x["pi_t_implied"] - x["pi_eval"]) for x in with_pt])),
                4) if with_pt else None)
    return out


FIELDS = ["n_source_sites", "target_mode", "draw", "alpha", "tau",
          "coverage_frozen", "coverage_replayed", "rm_fresh_frozen",
          "rm_fresh_replayed", "self_check_4dp", "rm_exceed_frozen",
          "pi_target", "pi_eval", "pi_source", "rm_rescored",
          "rm_rescored_exceed", "rho_lo", "rho_hi", "rho_site", "rho_pop",
          "box_covers_rho_site", "box_covers_rho_pop", "rho_point",
          "pi_t_implied", "q_target", "box_matches_frozen_6dp"]


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="replay and rescore the E9 arm-A certificates")
    ap.add_argument("--rho-point", action="store_true",
                    help="also re-run the BBSE fit to recover rho_point")
    ap.add_argument("--out", default=OUT_DIR)
    args = ap.parse_args(argv)
    csv_path = os.path.join(args.out, "E9a_rescore.csv")
    json_path = os.path.join(args.out, "E9a_rescore.json")
    for p in (csv_path, json_path):
        assert_not_frozen(p)
    t0 = time.perf_counter()
    rows, check = rescore(rho_point=args.rho_point)
    frozen = _read_csv(FROZEN)
    doc = summarise(rows, check, frozen, args.rho_point)
    doc["wall_clock_s"] = round(time.perf_counter() - t0, 1)
    os.makedirs(args.out, exist_ok=True)
    _write_csv(csv_path, rows, FIELDS)
    _write_json(json_path, {"_run": run_block([FROZEN]), **doc},
                "rescore_e9a", per_item_keys=("exceeding_rows",))
    print(f"[certgate] {doc['headline']}")
    print(f"[certgate] wrote {csv_path} and {json_path} "
          f"({doc['wall_clock_s']} s)", file=sys.stderr)
    return doc


if __name__ == "__main__":
    main()
