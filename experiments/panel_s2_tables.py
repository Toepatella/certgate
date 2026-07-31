"""Read-only analysis behind draft.md Tables 6 and 7 (panel items S2-13, S2-28).

Two things the main grid does not emit:

  * **Table 6 — influence-cap sensitivity.** Replays E1's ``s_u=0.5`` arm in
    baseline mode at each candidate ``M``, re-deriving BOTH the ``S_aux`` walk
    order and the calibration walk, and rescores each certificate against
    ``R_M`` AT THAT SAME ``M`` on the same fresh 200-site evaluation pool. Each
    M certifies its own estimand, so the table compares procedures, not one
    quantity. Self-checks against the recorded ``E1_validity.csv``: at M=100 the
    replay must reproduce every baseline-deploying draw's tau exactly.

  * **Table 7 — answered/declined operating characteristics.** Confusion counts,
    sensitivity, specificity, PPV and NPV for the answered and declined sets of
    E1 (pooled over its 200 fresh evaluation pools) and E6 (its single 40-site
    deployment), plus the always-negative comparator error rate that Section 3.1
    and Section 4.2 weigh alpha against.

Also emitted: the Section 3.3 cap facts (share of sites above M, share of
records above their site's cap, min g_c/n_c), the record-level-vs-R_M gap for
E1 and E6, and the record-carrying-but-silent (neutral atom) counts.

Determinism: every draw is reseeded from ``constants.SEED`` through the same
rule ``run_synthetic._rng`` uses, so this file reproduces the grid's cohorts
without re-running it. It reads ``experiments/out/E1_validity.csv`` and WRITES
NOTHING -- results go to stdout as JSON.

Run: ``python -m experiments.panel_s2_tables [R]``   (default R = 200)

NOTE (open item): these numbers are not yet folded into ``run_synthetic.py``'s
CSV/summary writers, so ``python -m experiments.run_synthetic`` alone does not
regenerate Tables 6 and 7. Appendix A.3's one-command claim covers Tables 1-4
and Figures 1-7 only until that wiring lands.
"""

import csv
import json
import os
import sys

import numpy as np

from certgate.certify import (certification_rng, fixed_sequence_walk,
                              influence_atoms, walk_order)
from certgate.constants import (ALPHA_LADDER, DELTA, M_INFLUENCE,
                                MODE_BASELINE, SEED, TAU_GRID)
from certgate.data import SimConfig, draw_cohort, split_sites
from certgate.model import fit_head
from certgate.pipeline import run_certgate

OUT = os.path.join(os.path.dirname(__file__), "out")
ANCHOR_SITES = 208
E1_EVAL_SITES = 200
# 5000 is the generator's upper size clip: g_c = n_c for EVERY site, i.e. the
# record-proportional estimand. M is also the atom normaliser, so raising it
# shrinks every atom toward alpha -- which is why the certificate dies there.
M_SWEEP = (25, 50, 100, 200, 500, 1000, 5000)


def _rng(*parts):
    """Same seeding rule as ``run_synthetic._rng``."""
    return np.random.default_rng(np.random.SeedSequence([SEED, *parts]))


def _confusion(y, yhat):
    y, yhat = np.asarray(y, bool), np.asarray(yhat, bool)
    return dict(tp=int((y & yhat).sum()), fp=int((~y & yhat).sum()),
                fn=int((y & ~yhat).sum()), tn=int((~y & ~yhat).sum()))


def _op_chars(c):
    """Operating characteristics from confusion counts (Table 7 row)."""
    tp, fp, fn, tn = c["tp"], c["fp"], c["fn"], c["tn"]
    n = tp + fp + fn + tn
    r = lambda num, den: (round(num / den, 4) if den else None)   # noqa: E731
    return dict(
        records=n, **c,
        positive_fraction=r(tp + fn, n), error=r(fp + fn, n),
        sensitivity=r(tp, tp + fn), specificity=r(tn, tn + fp),
        ppv=r(tp, tp + fp), npv=r(tn, tn + fn),
        fn_share_of_errors=r(fn, fp + fn))


def _always_negative_error(*sets):
    """Error rate of a constant always-negative rule, which answers EVERYTHING.

    The comparator alpha is weighed against (Sections 3.1, 4.2), so it must be
    taken over the WHOLE pool -- answered plus declined -- not over the answered
    subset, whose prevalence the gate has already altered.
    """
    pos = sum(s["tp"] + s["fn"] for s in sets)
    n = sum(s["records"] for s in sets)
    return round(pos / n, 4) if n else None


def _rm(head, pool, tau, M):
    """Influence-weighted answered risk at cap ``M`` (Section 3.3)."""
    ans = head.score(pool.x) >= tau
    err = head.predict(pool.x) != pool.y
    sizes = pool.site_sizes.astype(float)
    g_over_n = np.where(sizes > 0,
                        np.minimum(sizes, M) / np.maximum(sizes, 1.0), 0.0)
    num = np.bincount(pool.site_id, weights=(ans & err).astype(float),
                      minlength=pool.n_sites)
    den = np.bincount(pool.site_id, weights=ans.astype(float),
                      minlength=pool.n_sites)
    a, b = float((g_over_n * num).sum()), float((g_over_n * den).sum())
    return (a / b) if b > 0 else float("nan")


def _recorded_e1():
    """Certified alpha=0.10, s_u=0.5 rows of the released E1 artifact."""
    with open(os.path.join(OUT, "E1_validity.csv")) as fh:
        return {int(r["draw"]): r for r in csv.DictReader(fh)
                if r["s_u"] == "0.5" and r["alpha"] in ("0.1", "0.10")
                and r["certified"] == "True"}


def e1_arm(R):
    """Table 6 + E1's half of Table 7, from one replay of the s_u=0.5 arm."""
    recorded = _recorded_e1()
    cfg = SimConfig(s_u=0.5)
    acc = {(M, a): dict(n=0, tau=[], cov=[], rm=[], exceed=0)
           for M in M_SWEEP for a in ALPHA_LADDER}
    capped = {M: [] for M in M_SWEEP}
    ans_c = dict(tp=0, fp=0, fn=0, tn=0)
    dec_c = dict(tp=0, fp=0, fn=0, tn=0)
    rec_err, rm_dep, neutral, zero_cov = [], [], [], []
    check = dict(compared=0, tau_mismatches=0)

    for r in range(R):
        rng = _rng(1, 0, r)
        coh = draw_cohort(cfg, ANCHOR_SITES, rng)
        train, aux, cal = split_sites(coh, rng)
        head = fit_head(train)
        # advance the stream exactly as run_E1 does (single-site target pool)
        draw_cohort(cfg, 1, rng, site_label_prefix=f"e1t0_{r}",
                    require_both_classes=False)
        ev = draw_cohort(cfg, E1_EVAL_SITES, rng, site_label_prefix=f"e1v0_{r}")

        s_aux, e_aux = head.score(aux.x), head.predict(aux.x) != aux.y
        s_cal, e_cal = head.score(cal.x), head.predict(cal.x) != cal.y
        cal_sizes = cal.site_sizes.astype(float)

        for M in M_SWEEP:
            capped[M].append(float(np.maximum(cal_sizes - M, 0).sum()
                                   / cal_sizes.sum()))
            for alpha in ALPHA_LADDER:
                a_aux = influence_atoms(s_aux, e_aux, aux.site_id, aux.n_sites,
                                        TAU_GRID, alpha, M)
                a_cal = influence_atoms(s_cal, e_cal, cal.site_id, cal.n_sites,
                                        TAU_GRID, alpha, M)
                _, dep = fixed_sequence_walk(
                    a_cal, walk_order(a_aux), alpha, DELTA, TAU_GRID,
                    rng=certification_rng(alpha, MODE_BASELINE))
                if dep is None:
                    continue
                tau = float(TAU_GRID[dep])
                rm = _rm(head, ev, tau, M)
                k = acc[(M, alpha)]
                k["n"] += 1
                k["tau"].append(tau)
                k["cov"].append(float((head.score(ev.x) >= tau).mean()))
                k["rm"].append(rm)
                k["exceed"] += int(rm > alpha)
                if M == 100 and alpha == 0.10 and r in recorded:
                    # the OR-combination deploys max tau across modes, so only
                    # baseline-deploying draws are comparable to a baseline replay
                    if recorded[r]["deploy_mode"] == "baseline":
                        check["compared"] += 1
                        check["tau_mismatches"] += int(
                            abs(tau - float(recorded[r]["tau"])) > 1e-9)

        # Table 7 + Section 3.3/4.2 diagnostics at the DEPLOYED (recorded) tau
        if r in recorded:
            tau = float(recorded[r]["tau"])
            s_ev, yh = head.score(ev.x), head.predict(ev.x)
            a = s_ev >= tau
            for tgt, mask in ((ans_c, a), (dec_c, ~a)):
                for k2, v in _confusion(ev.y[mask], yh[mask]).items():
                    tgt[k2] += v
            rec_err.append(float((yh[a] != ev.y[a]).mean()))
            rm_dep.append(_rm(head, ev, tau, M_INFLUENCE))
            a_by_site = np.bincount(cal.site_id,
                                    weights=(s_cal >= tau).astype(float),
                                    minlength=cal.n_sites)
            neutral.append(int(((cal_sizes > 0) & (a_by_site == 0)).sum()))
            ev_sizes = ev.site_sizes.astype(float)
            ev_ans = np.bincount(ev.site_id, weights=a.astype(float),
                                 minlength=ev.n_sites)
            zero_cov.append(int(((ev_sizes > 0) & (ev_ans == 0)).sum()))

    def _summ(k, R_):
        if not k["n"]:
            return dict(certify_rate=0.0, n_certified=0)
        return dict(certify_rate=round(k["n"] / R_, 4), n_certified=k["n"],
                    mean_tau=round(float(np.mean(k["tau"])), 4),
                    mean_coverage=round(float(np.mean(k["cov"])), 4),
                    mean_rm=round(float(np.mean(k["rm"])), 4),
                    rm_exceed_rate=round(k["exceed"] / k["n"], 4))

    # HARD self-check, not a printed diagnostic: if the replay does not
    # reproduce the released artifact's certified thresholds, nothing below is
    # trustworthy and no table should be emitted.
    if check["compared"] == 0 or check["tau_mismatches"]:
        raise AssertionError(
            f"panel_s2_tables: replay does not reproduce E1_validity.csv -- "
            f"{check['tau_mismatches']} tau mismatch(es) over "
            f"{check['compared']} baseline-deploying draws "
            f"(reason=replay-mismatch)")

    cov = np.array([float(recorded[r]["coverage"]) for r in sorted(recorded)])
    ans_o, dec_o = _op_chars(ans_c), _op_chars(dec_c)
    return dict(
        R=R,
        self_check=check,
        always_negative_error=_always_negative_error(ans_o, dec_o),
        decline_rate_records=round(dec_o["records"]
                                   / (ans_o["records"] + dec_o["records"]), 4),
        declined_share_of_all_positives=round(
            (dec_o["tp"] + dec_o["fn"])
            / (ans_o["tp"] + ans_o["fn"] + dec_o["tp"] + dec_o["fn"]), 4),
        table6={f"M={M}": dict(
            records_above_cap=round(float(np.mean(capped[M])), 4),
            **{f"alpha={a}": _summ(acc[(M, a)], R) for a in ALPHA_LADDER})
            for M in M_SWEEP},
        table7_answered=ans_o,
        table7_declined=dec_o,
        target_pool_coverage=dict(mean=round(float(cov.mean()), 4),
                                  min=round(float(cov.min()), 4)),
        record_vs_rm=dict(
            record_level_answered_error=round(float(np.mean(rec_err)), 4),
            rm=round(float(np.mean(rm_dep)), 4),
            gap=round(float(np.mean(np.array(rm_dep) - np.array(rec_err))), 4)),
        neutral_atoms=dict(max_record_carrying_silent_cal_sites=int(max(neutral)),
                           max_zero_coverage_eval_sites=int(max(zero_cov))))


def e6_arm():
    """E6's half of Table 7, plus its R_M-vs-record gap (Section 4.7)."""
    cfg = SimConfig()
    rng = _rng(6)
    coh = draw_cohort(cfg, ANCHOR_SITES, rng)
    train, aux, cal = split_sites(coh, rng)
    head = fit_head(train)
    tgt = draw_cohort(cfg, 40, rng, site_label_prefix="e6t")
    tgt_sites = np.array(tgt.site_labels, dtype=object)[tgt.site_id]
    rep = run_certgate(train, aux, cal, tgt.x, target_label="E6",
                       target_site_id=tgt_sites, oracle_target_y=tgt.y)
    op = rep["operative"]
    tau = float(op["tau"])
    a = head.score(tgt.x) >= tau
    yh = head.predict(tgt.x)
    sizes = tgt.site_sizes.astype(float)
    ans_by_site = np.bincount(tgt.site_id, weights=a.astype(float),
                              minlength=tgt.n_sites)
    ans_o = _op_chars(_confusion(tgt.y[a], yh[a]))
    dec_o = _op_chars(_confusion(tgt.y[~a], yh[~a]))
    return dict(
        alpha=op["alpha"], tau=round(tau, 4), deploy_mode=op["deploy_mode"],
        always_negative_error=_always_negative_error(ans_o, dec_o),
        table7_answered=ans_o,
        table7_declined=dec_o,
        record_vs_rm=dict(
            record_level_answered_error=round(float((yh[a] != tgt.y[a]).mean()), 4),
            rm=round(_rm(head, tgt, tau, M_INFLUENCE), 4)),
        zero_coverage_sites=int(((sizes > 0) & (ans_by_site == 0)).sum()),
        n_sites=int(tgt.n_sites))


def cap_facts(n_reps=400):
    """Section 3.3's cap arithmetic, over the generator's own size draw."""
    cfg = SimConfig()
    rng = np.random.default_rng(SEED)
    sizes = np.concatenate([draw_cohort(cfg, ANCHOR_SITES, rng).site_sizes
                            .astype(float) for _ in range(n_reps)])
    return dict(
        sites=len(sizes),
        share_sites_above_M=round(float((sizes > M_INFLUENCE).mean()), 4),
        share_records_above_own_cap=round(
            float(np.maximum(sizes - M_INFLUENCE, 0).sum() / sizes.sum()), 4),
        min_g_over_n=round(float((np.minimum(sizes, M_INFLUENCE)
                                  / sizes).min()), 4),
        median_site_size=float(np.median(sizes)))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    R = int(argv[0]) if argv else 200
    print(json.dumps(dict(cap_facts=cap_facts(), E1=e1_arm(R), E6=e6_arm()),
                     indent=2))


if __name__ == "__main__":
    main()
