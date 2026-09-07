"""The synthetic validation harness.

Runs the nine experiments E1-E9 deterministically, all seeded from
constants.SEED. Writes one CSV per experiment, PNG figures, and a summary.md
into the output directory.
Figures use the matplotlib Agg backend -- no seaborn, no interactive display.

CLI:

    python -m experiments.run_synthetic [--quick] [--only E1,E4] [--out DIR]

--quick is R=10 draws over the cluster sweep {60, 208, 400} -- a fast smoke of
every experiment, and E1-quick must show zero hard violations. The full grid is
R=200 over {60, 100, 150, 208, 300, 400} and takes about 42 minutes on
the baseline machine (a 14-core laptop CPU, no GPU; measured 2026-09-06).

Refs: METHODS 8; SPEC section "Experiments".
"""

import argparse
import collections
import csv
import datetime
import hashlib
import json
import os
import re

import matplotlib
matplotlib.use("Agg")                       # headless: no interactive display
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import binomtest

from certgate.constants import (SEED, ALPHA_LADDER, DELTA, M_INFLUENCE,
                                MIN_CAL_CLUSTERS, SPLIT_FRACTIONS, TAU_GRID,
                                MODE_BASELINE)
from certgate.certify import (influence_atoms, walk_order,
                              fixed_sequence_walk, certification_rng)
from certgate.data import SimConfig, draw_cohort, split_sites
from certgate.model import fit_head
from certgate.pipeline import run_certgate
from certgate.explain import (global_importance, local_attribution,
                              abstention_explanation, cohort_abstention_profile,
                              composition, counterfactual_to_answer)
from certgate.harness import hard_violation, exceedance_reference, SIZE_BINS
from certgate.report import provenance
from certgate import reliability as rp
import dataclasses

from sklearn.ensemble import HistGradientBoostingClassifier

from experiments.comparators import (hoeffding_ucb, mpeb_ucb,
                                     site_bootstrap_ucb, t_ucb)

# One generator for everything: every experiment runs the documented
# SimConfig() defaults. The only experiment-local generator parameters are the
# shift or tilt each experiment is about, declared here and pinned by
# tests/test_constants.py. An undeclared one makes the headline numbers
# irreproducible from the stated setup.
# Ref: audit V7.
QUICK_SWEEP = (60, 208, 400)
FULL_SWEEP = (60, 100, 150, 208, 300, 400)
ANCHOR_SITES = 208
SHIFT_BASE = 0.22                           # label shift 0.095 -> 0.22
CONCEPT_INTERCEPT = 2.0                     # E3 tilt, verified below
E1_SU_SWEEP = (0.5, 1.0, 2.0)               # E1 heterogeneity sensitivity (audit V1)
E1_EVAL_SITES = 200                         # fresh sites for the aggregate R_M metric
E2_SHIFT_SWEEP = (0.095, 0.13, 0.16, 0.19, 0.22)   # magnitude sweep; 0.22 = anchor,
                                            # 0.095 = the null-shift arm (panel S2-6/S2-7)
E7_RECORD_SAMPLE = 2000                     # record-as-unit subsample of S_cal / S_aux
E7_SU_ARM = (0.5, 2.0)                      # heterogeneity arms for the comparator
# revision-2 (SPEC "E8"; design probes in PHASE0-PROBES.md, in git history)
E8_COMPARATORS = ("wsr", "hoeffding", "mpeb", "t", "site_boot")
E8_BOOT = 1000                              # site-bootstrap resamples (arm A)
E8_NOISE_SWEEP = (0.01, 0.02, 0.03, 0.035, 0.04)   # aleatoric label-flip floor (arm B)
E8_NOISE_R = 300                            # draws per eta (exceedance resolution)
E8_HEAD_ARMS = ("gbm", "degraded")          # alternative heads (arm C)
E8_GBM_MAX_ITER = 200
E8_DEGRADED_ZERO_FEATURES = 2               # informative features denied to the head
# revision-2 (SPEC "E9"; frozen from the P0.2/P0.3 pilots in PHASE0-PROBES.md,
# in git history)
E9_SOURCE_SWEEP = (208, 600, 900, 1200)     # BBSE power frontier source-site counts
E9_TARGET_MODES = ("single-site-cp", "k40-boot")
E9_TARGET_K = 40                            # declared target sites, bootstrap mode
E9_R = 50                                   # draws per (source count, target mode)
E9_FNR_LADDER = (0.4, 0.5, 0.55, 0.6)       # FNR budgets; 0.4 = negative control
E9_FNR_SWEEP = (208, 400, 600)              # site counts for the FNR frontier
E9_FNR_R = 200
EXPERIMENTS = ("E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9")


# ------------------------------------------------------------------ helpers

def _rng(*parts):
    """Deterministic Generator seeded from the protocol SEED and index parts."""
    return np.random.default_rng(np.random.SeedSequence([SEED, *parts]))


def _rate(k, n):
    """Conditional rate over n certified draws.

    Returns None (JSON null) when n == 0. A 0.0 there would conflate "no
    certificates issued" with "zero violations".
    """
    return round(k / n, 4) if n else None


def _rate_ci95(k, n):
    """Exact Clopper-Pearson 95% interval for the rate _rate(k, n) reports.

    Uses binomtest.proportion_ci rather than a beta.ppf construction. It
    carries the k == 0 and k == n boundary conventions itself, and that is
    where a hand-rolled version picks up an off-by-one in the shape parameters.
    Returns None when n == 0, mirroring _rate's null convention -- an interval
    over no draws is undefined, never [0, 1].

    Refs: METHODS 9; SPEC 3.9 scoring rule.
    """
    if not n:
        return None
    ci = binomtest(int(k), int(n)).proportion_ci(confidence_level=0.95,
                                                 method="exact")
    return [round(float(ci.low), 4), round(float(ci.high), 4)]


def _write_csv(path, rows, fieldnames):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fieldnames})


def _row_for(report, alpha):
    for r in report["certified"]:
        if r["alpha"] == alpha:
            return r
    return None


def _cert_eval(head, report, alpha, target_x, target_y):
    """Evaluate one certified row against the oracle target pool (harness)."""
    row = _row_for(report, alpha)
    out = dict(certified=False, tau=None, coverage=0.0, n_answered=0,
               answered_err_rate=float("nan"), hard=False, exceed=False,
               deploy_mode=None, decline_reason=None)
    if row is None or row["status"] != "certified":
        if row is not None:
            out["decline_reason"] = json.dumps(row.get("reasons", {}))
        elif report.get("reason"):
            # Fully-gated report (insufficient-clusters, pool-too-small):
            # keep the structural gate reason attributable in the CSV.
            out["decline_reason"] = report["reason"]
        return out
    tau = row["tau"]
    ans = head.score(target_x) >= tau
    err = head.predict(target_x) != target_y
    err_ans = err[ans]
    n_ans = int(ans.sum())
    rate = float(err_ans.mean()) if n_ans else float("nan")
    out.update(certified=True, tau=float(tau), coverage=float(ans.mean()),
               n_answered=n_ans, answered_err_rate=rate,
               hard=bool(hard_violation(err_ans, alpha)),
               exceed=bool(n_ans > 0 and rate > alpha),
               deploy_mode=row["deploy_mode"])
    return out


def _draw_split(cfg, n_sites, rng):
    coh = draw_cohort(cfg, n_sites, rng)
    train, aux, cal = split_sites(coh, rng)
    return train, aux, cal, fit_head(train)


def _rm_on_pool(head, pool, tau, M=M_INFLUENCE):
    """Influence-weighted answered-set risk R_M on a fresh multi-site pool.

    This is the quantity the certificate actually bounds:

        R_M = sum_c g_c a_c e_c / sum_c g_c a_c
            = sum_c (g_c/n_c) err_ans_c / sum_c (g_c/n_c) ans_c

    with g_c = min(n_c, M). Returns NaN when nothing answers.

    Refs: METHODS 3; audit V1.
    """
    score = head.score(pool.x)
    err = head.predict(pool.x) != pool.y
    ans = score >= tau
    n_sites = pool.n_sites
    sizes = pool.site_sizes.astype(float)
    g_over_n = np.where(sizes > 0,
                        np.minimum(sizes, M)
                        / np.maximum(sizes, 1.0), 0.0)
    num_c = np.bincount(pool.site_id, weights=(ans & err).astype(float),
                        minlength=n_sites)
    den_c = np.bincount(pool.site_id, weights=ans.astype(float),
                        minlength=n_sites)
    num = float((g_over_n * num_c).sum())
    den = float((g_over_n * den_c).sum())
    return (num / den) if den > 0 else float("nan")


def _per_site_exceed_frac(head, pool, tau, alpha):
    """Fraction of answering sites whose own answered error exceeds alpha.

    A dispersion diagnostic, with no delta target attached. Under between-site
    heterogeneity it rises while the certified aggregate R_M stays within
    budget. It measures what the certificate deliberately does not bound
    (audit V1).
    """
    score = head.score(pool.x)
    err = head.predict(pool.x) != pool.y
    ans = score >= tau
    n_sites = pool.n_sites
    num_c = np.bincount(pool.site_id, weights=(ans & err).astype(float),
                        minlength=n_sites)
    den_c = np.bincount(pool.site_id, weights=ans.astype(float),
                        minlength=n_sites)
    answering = den_c > 0
    if not answering.any():
        return float("nan")
    rates = num_c[answering] / den_c[answering]
    return float((rates > alpha).mean())


def _plot(vals):
    """None -> NaN for matplotlib: a missing rate plots as a gap, never 0."""
    return [np.nan if v is None else v for v in vals]


def _alpha_bar(ax, xs, vals, none_fontsize, val_fontsize):
    """Label one per-alpha bar series on ax.

    A None value means the rung never certified: no bar, and the text says
    so. A true 0.0 bar has zero height -- label it or it reads as absence.
    """
    for x, v in zip(xs, vals):
        if v is None:
            ax.text(x, 0.03, "no certificates", ha="center", va="bottom",
                    rotation=90, fontsize=none_fontsize, color="dimgray",
                    transform=ax.get_xaxis_transform())
        else:
            ax.text(x, v, f"{v:.3f}", ha="center", va="bottom",
                    fontsize=val_fontsize)


def _rescore(head, evalp, dep, alpha, risk=_rm_on_pool, risk_key="rm_fresh",
             exceed_key="rm_exceed", tau=None):
    """Rescore one certified rung against a fresh eval pool.

    dep is the deployed TAU_GRID index; E9 arm A passes tau directly instead,
    because the pipeline row carries the deployed tau but not its index.
    Returns the fields the callers row.update() with: tau at 4 dp, coverage
    at 4 dp, the fresh risk at 6 dp and its exceed flag, keyed by
    risk_key/exceed_key (E9 arm B's FNR walk renames both).
    """
    tau = float(TAU_GRID[dep]) if tau is None else float(tau)
    rm = risk(head, evalp, tau)
    return {
        "tau": round(tau, 4),
        "coverage": round(float((head.score(evalp.x) >= tau).mean()), 4),
        risk_key: round(rm, 6),
        exceed_key: bool(rm > alpha),
    }


def _rollup(certs, n_draws, fields, none_certify=False, risk_key="rm_fresh",
            exceed_key="rm_exceed", coverage_empty=None):
    """Aggregate certified rows into one summary cell.

    fields names the emitted keys in emit order, so every caller keeps its
    exact key set and dict order in the byte-compared summary blocks.
    none_certify=True reports certify_rate as None (the caller's cell had no
    draws at all); coverage_empty is what mean_coverage reports over zero
    certificates. The hard and exceed counts are computed once per call.
    """
    n_c = len(certs)
    k_hard = k_exc = None
    out = {}
    for f in fields:
        if f == "certify_rate":
            out[f] = None if none_certify else round(n_c / n_draws, 4)
        elif f == "n_certified":
            out[f] = n_c
        elif f in ("hard_violation_rate", "hard_violation_rate_ci95",
                   "hard_violation_rate_diag",
                   "hard_violation_rate_diag_ci95"):
            if k_hard is None:
                k_hard = sum(x["hard"] for x in certs)
            out[f] = (_rate_ci95(k_hard, n_c) if f.endswith("_ci95")
                      else _rate(k_hard, n_c))
        elif f in ("exceedance_rate", "exceedance_rate_diag"):
            out[f] = _rate(sum(x["exceed"] for x in certs), n_c)
        elif f in (exceed_key + "_rate", exceed_key + "_rate_ci95"):
            if k_exc is None:
                k_exc = sum(bool(x.get(exceed_key)) for x in certs)
            out[f] = (_rate_ci95(k_exc, n_c) if f.endswith("_ci95")
                      else _rate(k_exc, n_c))
        elif f == "mean_" + risk_key:
            out[f] = (round(float(np.mean([x[risk_key] for x in certs])), 4)
                      if certs else None)
        elif f == "mean_tau":
            out[f] = (round(float(np.mean([x["tau"] for x in certs])), 4)
                      if certs else None)
        elif f == "mean_coverage":
            out[f] = (round(float(np.mean([x["coverage"] for x in certs])), 4)
                      if certs else coverage_empty)
        elif f == "mean_per_site_exceed_frac":
            out[f] = (round(float(np.mean([x["per_site_exceed_frac"]
                                           for x in certs])), 4)
                      if certs else None)
        else:
            raise KeyError(f"_rollup: unknown field {f!r}")
    return out


# ------------------------------------------------------------------ E1

def run_E1(out, quick):
    """E1 validity.

    The conformance metric is the aggregate quantity the test actually
    certifies. Per draw, the certified tau is applied to a fresh
    E1_EVAL_SITES-site pool and R_M is computed there. Conformance is the
    fraction of certified draws with R_M > alpha, and it targets <= DELTA.

    The single-fresh-site hard-violation rate is kept, but only as a per-site
    dispersion diagnostic with no delta target. The certificate does not bound
    individual sites, and the E1_SU_SWEEP arm shows that per-site rate rising
    with heterogeneity while the certified aggregate stays within budget.

    Refs: audit V1.
    """
    R = 10 if quick else 200
    rows = []
    for su_idx, s_u in enumerate(E1_SU_SWEEP):
        cfg = SimConfig(s_u=s_u)
        for r in range(R):
            rng = _rng(1, su_idx, r)
            train, aux, cal, head = _draw_split(cfg, ANCHOR_SITES, rng)
            tgt = draw_cohort(cfg, 1, rng, site_label_prefix=f"e1t{su_idx}_{r}",
                              require_both_classes=False)
            rep = run_certgate(train, aux, cal, tgt.x,
                               target_label=f"E1-{su_idx}-{r}",
                               oracle_target_y=tgt.y)
            evalp = draw_cohort(cfg, E1_EVAL_SITES, rng,
                                site_label_prefix=f"e1v{su_idx}_{r}")
            for alpha in ALPHA_LADDER:
                ev = _cert_eval(head, rep, alpha, tgt.x, tgt.y)
                if ev["certified"]:
                    rm = _rm_on_pool(head, evalp, ev["tau"])
                    disp = _per_site_exceed_frac(head, evalp, ev["tau"], alpha)
                    ev.update(rm_fresh=round(rm, 6),
                              rm_exceed=bool(rm > alpha),
                              per_site_exceed_frac=round(disp, 4))
                else:
                    ev.update(rm_fresh=None, rm_exceed=None,
                              per_site_exceed_frac=None)
                rows.append(dict(s_u=s_u, draw=r, n_sites=ANCHOR_SITES,
                                 alpha=alpha, **ev))
    _write_csv(os.path.join(out, "E1_validity.csv"), rows,
               ["s_u", "draw", "n_sites", "alpha", "certified", "tau",
                "coverage", "n_answered", "answered_err_rate", "hard",
                "exceed", "rm_fresh", "rm_exceed", "per_site_exceed_frac",
                "deploy_mode", "decline_reason"])

    def _arm(sub, R_arm):
        """Per-alpha summary for one s_u arm.

        Key order: CONFORMANCE first (the certified aggregate, target <=
        DELTA), then the per-site dispersion DIAGNOSTICS (no delta target).
        """
        arm = {}
        for alpha in ALPHA_LADDER:
            certs = [x for x in sub if x["alpha"] == alpha and x["certified"]]
            arm[alpha] = _rollup(
                certs, R_arm,
                ("certify_rate", "n_certified", "rm_exceed_rate_ci95",
                 "rm_exceed_rate", "mean_rm_fresh",
                 "hard_violation_rate_diag_ci95", "hard_violation_rate_diag",
                 "exceedance_rate_diag", "mean_per_site_exceed_frac",
                 "mean_coverage"),
                coverage_empty=0.0)
        return arm

    base_rows = [x for x in rows if x["s_u"] == E1_SU_SWEEP[0]]
    summary = {"R": R, "eval_sites": E1_EVAL_SITES,
               "conformance_metric": (
                   "rm_exceed_rate: fraction of certified draws whose "
                   "influence-weighted answered risk R_M on a fresh "
                   f"{E1_EVAL_SITES}-site pool exceeds alpha (target <= "
                   f"DELTA={DELTA}). hard_violation_rate_diag is a PER-SITE "
                   "DISPERSION DIAGNOSTIC with no delta target -- the "
                   "certificate bounds the site-population average, not "
                   "individual sites (audit V1)."),
               "s_u_protocol": E1_SU_SWEEP[0]}
    summary.update(_arm(base_rows, R))
    summary["total_rm_exceed"] = int(sum(
        bool(x["rm_exceed"]) for x in base_rows if x["certified"]))

    # s_u sensitivity arm (audit V1): aggregate stays within budget while the
    # per-site dispersion rises with heterogeneity.
    sens = []
    for s_u in E1_SU_SWEEP:
        sub = [x for x in rows if x["s_u"] == s_u]
        arm = _arm(sub, R)
        sens.append(dict(
            s_u=s_u,
            certify_rate=arm[0.10]["certify_rate"],
            rm_exceed_rate=arm[0.10]["rm_exceed_rate"],
            mean_rm_fresh=arm[0.10]["mean_rm_fresh"],
            hard_violation_rate_diag=arm[0.10]["hard_violation_rate_diag"],
            mean_per_site_exceed_frac=arm[0.10]["mean_per_site_exceed_frac"]))
    summary["su_sensitivity"] = sens

    # exceedance vs binomial reference by answered-set size bin
    # (alpha=0.10, protocol s_u only)
    bins = []
    certs10 = [x for x in base_rows if x["alpha"] == 0.10 and x["certified"]]
    for lo, hi in SIZE_BINS:
        grp = [x for x in certs10 if lo <= x["n_answered"] < hi]
        # Empty bins report None (JSON null), never NaN -- NaN is an invalid
        # JSON token. Same rule as E6's rollup below.
        if grp:
            obs = round(float(np.mean([x["exceed"] for x in grp])), 4)
            ref = round(float(np.mean([exceedance_reference(x["n_answered"], 0.10)
                                       for x in grp])), 4)
        else:
            obs = ref = None
        bins.append(dict(size_bin=f"[{lo},{hi})", n=len(grp),
                         observed_exceedance=obs, binomial_reference=ref))
    summary["exceedance_by_size"] = bins

    # figure: aggregate conformance per alpha + exceedance-by-size + s_u arm
    fig, ax = plt.subplots(1, 3, figsize=(16, 4))
    alphas = list(ALPHA_LADDER)
    rm_bars = [summary[a]["rm_exceed_rate"] for a in alphas]
    xpos = np.arange(len(alphas))   # numeric x: a nan bar must not eat its tick
    ax[0].bar(xpos, _plot(rm_bars), color="#4477aa")
    ax[0].set_xticks(xpos); ax[0].set_xticklabels([str(a) for a in alphas])
    ax[0].set_xlim(-0.6, len(alphas) - 0.4)   # autoscale ignores the nan bars
    real = [v for v in rm_bars if v is not None]
    ax[0].set_ylim(0.0, max(real + [DELTA]) * 1.3)
    _alpha_bar(ax[0], range(len(rm_bars)), rm_bars, 8, 7)
    ax[0].axhline(DELTA, color="crimson", ls="--", label=f"DELTA={DELTA}")
    ax[0].set_title("Certified-aggregate R_M exceed rate")
    ax[0].set_xlabel("alpha"); ax[0].set_ylabel("rate"); ax[0].legend()
    labels = [b["size_bin"] for b in bins]
    ax[1].plot(labels, _plot([b["observed_exceedance"] for b in bins]), "o-",
               label="observed")
    ax[1].plot(labels, _plot([b["binomial_reference"] for b in bins]), "s--",
               label="binomial ref")
    ax[1].set_title("Exceedance vs reference (alpha=0.10)")
    ax[1].set_xlabel("answered-set size bin"); ax[1].set_ylabel("exceedance")
    ax[1].legend()
    su_vals = [s["s_u"] for s in sens]
    ax[2].plot(su_vals, _plot([s["rm_exceed_rate"] for s in sens]), "o-",
               label="aggregate R_M exceed (certified)")
    ax[2].plot(su_vals, _plot([s["hard_violation_rate_diag"] for s in sens]),
               "s--", label="per-site hard rate (diagnostic)")
    ax[2].axhline(DELTA, color="crimson", ls=":", label=f"DELTA={DELTA}")
    ax[2].set_title("Heterogeneity: aggregate vs per-site (alpha=0.10)")
    ax[2].set_xlabel("s_u (site random-effect sd)"); ax[2].set_ylabel("rate")
    ax[2].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(out, "E1_validity.png"),
                                    dpi=110); plt.close(fig)
    summary["_headline"] = (
        f"total_rm_exceed={summary['total_rm_exceed']}, "
        f"a=0.10 certify={summary[0.10]['certify_rate']} "
        f"rm_exceed={summary[0.10]['rm_exceed_rate']} "
        f"per_site_diag={summary[0.10]['hard_violation_rate_diag']} "
        f"coverage={summary[0.10]['mean_coverage']}")
    return summary


# ------------------------------------------------------------------ E2

def _e2_arm(cfg, base, R, seed_parts, prefix, label_suffix):
    """One magnitude arm of E2.

    seed_parts prefixes the per-draw stream. That keeps the 0.22 anchor on its
    original _rng(2, r) stream, so its published numbers stay byte-exact while
    sweep arms live on distinct streams.
    """
    rows = []
    for r in range(R):
        rng = _rng(*seed_parts, r)
        train, aux, cal, head = _draw_split(cfg, ANCHOR_SITES, rng)
        tgt = draw_cohort(cfg, 1, rng, label_base_rate=base,
                          site_label_prefix=f"{prefix}{r}",
                          require_both_classes=False)
        rep_b = run_certgate(train, aux, cal, tgt.x,
                             target_label=f"E2b{label_suffix}-{r}",
                             oracle_target_y=tgt.y, modes=("baseline",))
        rep_s = run_certgate(train, aux, cal, tgt.x,
                             target_label=f"E2s{label_suffix}-{r}",
                             oracle_target_y=tgt.y, modes=("bbse",))
        bd = rep_s["diagnostic"]["bbse"]     # stable key set (fixture audit)
        # Aggregate-estimand rescoring: a fresh label-shifted eval pool, drawn
        # after the streams above so every anchor number stays byte-exact.
        # Ref: draft-sync flag 2026-07-30.
        evalp = draw_cohort(cfg, E1_EVAL_SITES, rng, label_base_rate=base,
                            site_label_prefix=f"{prefix}v{r}")

        def _rm_fields(ev, alpha):
            if not ev["certified"]:
                return dict(rm_fresh=None, rm_exceed=None)
            rm = _rm_on_pool(head, evalp, ev["tau"])
            return dict(rm_fresh=round(rm, 6), rm_exceed=bool(rm > alpha))

        for alpha in ALPHA_LADDER:
            eb = _cert_eval(head, rep_b, alpha, tgt.x, tgt.y)
            es = _cert_eval(head, rep_s, alpha, tgt.x, tgt.y)
            eb.update(_rm_fields(eb, alpha))
            es.update(_rm_fields(es, alpha))
            srow = _row_for(rep_s, alpha)
            reason = None if srow["status"] == "certified" else \
                srow.get("reasons", {}).get("bbse")
            common = dict(draw=r, alpha=alpha, target_base=base)
            rows.append(dict(**common, mode="baseline", bbse_reason=None,
                             bbse_rho_lo=None, bbse_rho_hi=None,
                             bbse_gap_lo=None, bbse_q_target=None, **eb))
            rows.append(dict(**common, mode="bbse", bbse_reason=reason,
                             bbse_rho_lo=bd.get("rho_lo"),
                             bbse_rho_hi=bd.get("rho_hi"),
                             bbse_gap_lo=bd.get("gap_lo"),
                             bbse_q_target=bd.get("q_target"), **es))
    return rows


def run_E2(out, quick):
    R = 10 if quick else 200
    cfg = SimConfig()                       # documented generator (audit V7)
    # anchor magnitude, full R, original seed streams (numbers byte-exact)
    rows = _e2_arm(cfg, SHIFT_BASE, R, (2,), "e2t", "")
    # magnitude sweep (panel S2-6/S2-7) at R//2 on distinct streams; the
    # 0.095 point is the null-shift arm (BBSE behaviour when nothing is wrong)
    R_sweep = max(2, R // 2)
    for m_idx, base in enumerate(E2_SHIFT_SWEEP):
        if base == SHIFT_BASE:
            continue
        rows += _e2_arm(cfg, base, R_sweep, (2, 100 + m_idx), f"e2m{m_idx}_",
                        f"m{m_idx}")
    _write_csv(os.path.join(out, "E2_label_shift.csv"), rows,
               ["draw", "alpha", "mode", "target_base", "certified", "tau",
                "coverage", "n_answered", "answered_err_rate", "hard",
                "exceed", "rm_fresh", "rm_exceed", "decline_reason",
                "deploy_mode", "bbse_reason", "bbse_rho_lo", "bbse_rho_hi",
                "bbse_gap_lo", "bbse_q_target"])

    def _mode_stats(sub, n_draws):
        certs = [x for x in sub if x["certified"]]
        n_c = len(certs)
        out = _rollup(certs, n_draws,
                      ("certify_rate", "n_certified", "hard_violation_rate",
                       "hard_violation_rate_ci95", "exceedance_rate",
                       "rm_exceed_rate", "rm_exceed_rate_ci95"))
        out.update(
            joint_certify_and_hard_rate=round(
                sum(1 for x in certs if x["hard"]) / n_draws, 4),
            decline_rate=round((len(sub) - n_c) / len(sub), 4) if sub else 0.0)
        return out

    anchor = [x for x in rows if x["target_base"] == SHIFT_BASE]
    summary = {"R": R, "target_base_rate": SHIFT_BASE, "sep": SimConfig().sep,
               "R_sweep": R_sweep}
    for mode in ("baseline", "bbse"):
        summary[mode] = {}
        for alpha in ALPHA_LADDER:
            sub = [x for x in anchor
                   if x["mode"] == mode and x["alpha"] == alpha]
            summary[mode][alpha] = _mode_stats(sub, R)
    sweep = []
    for base in E2_SHIFT_SWEEP:
        n_draws = R if base == SHIFT_BASE else R_sweep
        entry = dict(target_base=base, R=n_draws)
        for mode in ("baseline", "bbse"):
            sub = [x for x in rows if x["target_base"] == base
                   and x["mode"] == mode and x["alpha"] == 0.10]
            entry[mode] = _mode_stats(sub, n_draws)
        sweep.append(entry)
    summary["shift_sweep_alpha0.10"] = sweep

    fig, ax = plt.subplots(1, 2, figsize=(12, 4))
    alphas = list(ALPHA_LADDER)
    width = 0.35
    xpos = np.arange(len(alphas))
    for mode, dx, color in (("baseline", -width / 2, "#cc6677"),
                            ("bbse", width / 2, "#4477aa")):
        vals = [summary[mode][a]["hard_violation_rate"] for a in alphas]
        ax[0].bar(xpos + dx, _plot(vals), width, label=mode, color=color)
        _alpha_bar(ax[0], xpos + dx, vals, 7, 6)
    ax[0].axhline(DELTA, color="black", ls="--", label=f"DELTA={DELTA}")
    ax[0].set_xticks(xpos); ax[0].set_xticklabels([str(a) for a in alphas])
    ax[0].set_xlim(-0.6, len(alphas) - 0.4)   # autoscale ignores the nan bars
    real = [summary[m][a]["hard_violation_rate"]
            for m in ("baseline", "bbse") for a in alphas
            if summary[m][a]["hard_violation_rate"] is not None]
    ax[0].set_ylim(0.0, max(real + [DELTA]) * 1.3)
    ax[0].set_title(f"Hard-violation rate at shift -> {SHIFT_BASE}")
    ax[0].set_xlabel("alpha"); ax[0].set_ylabel("hard-violation rate")
    ax[0].legend()
    bb = summary["bbse"][0.10]            # computed, not copied: stays correct
    ax[0].text(0.02, 0.98,                # under --quick's smaller R
               f"BBSE at this shift: declined {R - bb['n_certified']}/{R}, "
               f"certify-and-violate {bb['joint_certify_and_hard_rate']:.3f}",
               transform=ax[0].transAxes, ha="left", va="top", fontsize=7,
               color="#4477aa")
    bases = [e["target_base"] for e in sweep]
    ax[1].plot(bases, _plot([e["baseline"]["hard_violation_rate"]
                             for e in sweep]), "o-", color="#cc6677",
               label="baseline hard-viol")
    ax[1].plot(bases, [e["baseline"]["certify_rate"] for e in sweep], "o--",
               color="#cc6677", alpha=0.5, label="baseline certify")
    ax[1].plot(bases, [e["bbse"]["certify_rate"] for e in sweep], "s--",
               color="#4477aa", label="bbse certify")
    ax[1].plot(bases, [e["bbse"]["joint_certify_and_hard_rate"]
                       for e in sweep], "s-", color="#4477aa",
               label="bbse certify-and-violate")
    ax[1].axhline(DELTA, color="black", ls=":", label=f"DELTA={DELTA}")
    ax[1].axvline(E2_SHIFT_SWEEP[0], color="grey", ls=":", lw=1,
                  label="null shift (source rate)")
    ax[1].set_title("Magnitude sweep (alpha=0.10)")
    ax[1].set_xlabel("target base rate (source 0.095)")
    ax[1].set_ylabel("rate"); ax[1].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(os.path.join(out, "E2_label_shift.png"),
                                    dpi=110); plt.close(fig)
    b, s = summary["baseline"][0.10], summary["bbse"][0.10]
    summary["_headline"] = (
        f"baseline a=0.10 hard_viol={b['hard_violation_rate']} "
        f"exceed={b['exceedance_rate']}; bbse decline_rate="
        f"{s['decline_rate']} hard_viol={s['hard_violation_rate']}")
    return summary


# ------------------------------------------------------------------ E3

def run_E3(out, quick):
    R = 10 if quick else 200
    cfg = SimConfig()                       # documented generator (audit V7)
    rows = []
    verified_risk = []
    for r in range(R):
        rng = _rng(3, r)
        train, aux, cal, head = _draw_split(cfg, ANCHOR_SITES, rng)
        tgt = draw_cohort(cfg, 1, rng, concept_intercept=CONCEPT_INTERCEPT,
                          site_label_prefix=f"e3t{r}",
                          require_both_classes=False)
        rep = run_certgate(train, aux, cal, tgt.x, target_label=f"E3-{r}",
                           oracle_target_y=tgt.y)
        # Aggregate-estimand rescoring: a fresh concept-tilted eval pool, drawn
        # after the streams above so the anchor numbers stay byte-exact.
        # Ref: draft-sync flag 2026-07-30.
        evalp = draw_cohort(cfg, E1_EVAL_SITES, rng,
                            concept_intercept=CONCEPT_INTERCEPT,
                            site_label_prefix=f"e3v{r}")
        for alpha in ALPHA_LADDER:
            ev = _cert_eval(head, rep, alpha, tgt.x, tgt.y)
            if ev["certified"]:
                rm = _rm_on_pool(head, evalp, ev["tau"])
                ev.update(rm_fresh=round(rm, 6), rm_exceed=bool(rm > alpha))
            else:
                ev.update(rm_fresh=None, rm_exceed=None)
            if alpha == 0.10 and ev["certified"]:
                verified_risk.append(ev["answered_err_rate"])
            rows.append(dict(draw=r, alpha=alpha, **ev))
    # Construction check: the tilt must push answered risk above alpha, and
    # that is enforced, not merely reported. A de-poisoned tilt aborts before
    # anything is written. A negative control that fails verification must
    # never emit passing-looking violation rates.
    # Ref: SPEC E3; REVIEW-FABLE D3 (in git history).
    verified = (float(np.mean(verified_risk)) if verified_risk
                else float("nan"))
    poisonous = bool(verified > 0.10)
    if not poisonous:
        raise RuntimeError(
            f"E3: concept tilt failed poison verification -- mean answered "
            f"risk {verified} at alpha=0.10 does not exceed alpha=0.10 "
            f"(concept_intercept={CONCEPT_INTERCEPT}, R={R}); refusing to "
            f"report negative-control violation rates "
            f"(reason=e3-control-not-poisonous)")

    _write_csv(os.path.join(out, "E3_concept_shift.csv"), rows,
               ["draw", "alpha", "certified", "tau", "coverage", "n_answered",
                "answered_err_rate", "hard", "exceed", "rm_fresh",
                "rm_exceed", "deploy_mode", "decline_reason"])

    summary = {"R": R, "concept_intercept": CONCEPT_INTERCEPT,
               "sep": SimConfig().sep,
               "verified_mean_answered_risk_alpha0.10": round(verified, 4),
               "tilt_pushes_risk_above_alpha": poisonous}
    for alpha in ALPHA_LADDER:
        certs = [x for x in rows if x["alpha"] == alpha and x["certified"]]
        summary[alpha] = _rollup(
            certs, R,
            ("certify_rate", "n_certified", "hard_violation_rate",
             "hard_violation_rate_ci95", "exceedance_rate",
             "rm_exceed_rate", "rm_exceed_rate_ci95"))

    fig, ax = plt.subplots(figsize=(7, 4))
    alphas = list(ALPHA_LADDER)
    hv_bars = [summary[a]["hard_violation_rate"] for a in alphas]
    xpos = np.arange(len(alphas))   # numeric x: a nan bar must not eat its tick
    ax.bar(xpos, _plot(hv_bars), color="#ee8866")
    ax.set_xticks(xpos); ax.set_xticklabels([str(a) for a in alphas])
    ax.set_xlim(-0.6, len(alphas) - 0.4)      # autoscale ignores the nan bars
    real = [v for v in hv_bars if v is not None]
    ax.set_ylim(0.0, max(real + [DELTA]) * 1.15)
    _alpha_bar(ax, range(len(hv_bars)), hv_bars, 8, 8)
    ax.axhline(DELTA, color="black", ls="--", label=f"DELTA={DELTA}")
    ax.set_title("Concept-shift negative control (should FAIL)")
    ax.set_xlabel("alpha"); ax.set_ylabel("hard-violation rate"); ax.legend()
    fig.tight_layout(); fig.savefig(os.path.join(out, "E3_concept_shift.png"),
                                    dpi=110); plt.close(fig)
    summary["_headline"] = (
        f"verified_risk={summary['verified_mean_answered_risk_alpha0.10']} "
        f">alpha={summary['tilt_pushes_risk_above_alpha']}; "
        f"a=0.10 hard_viol={summary[0.10]['hard_violation_rate']}")
    return summary


# ------------------------------------------------------------------ E4

def run_E4(out, quick):
    R = 10 if quick else 200
    sweep = QUICK_SWEEP if quick else FULL_SWEEP
    cfg = SimConfig()
    rows = []
    for n_sites in sweep:
        for r in range(R):
            rng = _rng(4, n_sites, r)
            train, aux, cal, head = _draw_split(cfg, n_sites, rng)
            tgt = draw_cohort(cfg, 1, rng, site_label_prefix=f"e4t{n_sites}_{r}",
                              require_both_classes=False)
            rep = run_certgate(train, aux, cal, tgt.x,
                               target_label=f"E4-{n_sites}-{r}",
                               oracle_target_y=tgt.y)
            for alpha in ALPHA_LADDER:
                ev = _cert_eval(head, rep, alpha, tgt.x, tgt.y)
                rows.append(dict(n_sites=n_sites, draw=r, alpha=alpha, **ev))
    _write_csv(os.path.join(out, "E4_site_sweep.csv"), rows,
               ["n_sites", "draw", "alpha", "certified", "tau", "coverage",
                "n_answered", "answered_err_rate", "hard", "decline_reason"])

    summary = {"R": R, "sweep": list(sweep)}
    grid = {}
    for alpha in ALPHA_LADDER:
        grid[alpha] = []
        for n_sites in sweep:
            sub = [x for x in rows
                   if x["alpha"] == alpha and x["n_sites"] == n_sites]
            certs = [x for x in sub if x["certified"]]
            grid[alpha].append(dict(
                n_sites=n_sites,
                **_rollup(certs, R, ("certify_rate", "mean_coverage"),
                          coverage_empty=0.0)))
    summary["grid"] = grid

    # Cluster counts whose calibration share falls under the 50-carrying-
    # cluster floor are structurally gated (reason=insufficient-clusters).
    # They sample the gate, not the WSR information floor — annotate.
    gate_min_sites = int(np.ceil(MIN_CAL_CLUSTERS / SPLIT_FRACTIONS[2]))
    summary["gate_limited_n_sites"] = [n for n in sweep if n < gate_min_sites]
    summary["gate_note"] = (
        f"points with n_sites < {gate_min_sites} are declined by the "
        f"{MIN_CAL_CLUSTERS}-record-carrying-cluster gate, not the betting "
        f"test's information floor")

    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    for alpha in ALPHA_LADDER:
        g = grid[alpha]
        ax[0].plot([d["n_sites"] for d in g], [d["certify_rate"] for d in g],
                   "o-", label=f"alpha={alpha}")
        ax[1].plot([d["n_sites"] for d in g], [d["mean_coverage"] for d in g],
                   "o-", label=f"alpha={alpha}")
    ax[0].axvspan(min(sweep), min(gate_min_sites, max(sweep)), alpha=0.12,
                  color="grey",
                  label=f"< {MIN_CAL_CLUSTERS}-cluster gate")
    ax[0].axvline(ANCHOR_SITES, color="grey", ls=":", lw=1,
                  label=f"operating point ({ANCHOR_SITES} sites)")
    ax[1].axvline(ANCHOR_SITES, color="grey", ls=":", lw=1)
    ax[0].set_title("Certify rate vs cluster count")
    ax[0].set_xlabel("n_sites"); ax[0].set_ylabel("certify rate"); ax[0].legend()
    ax[1].set_title("Mean coverage vs cluster count")
    ax[1].set_xlabel("n_sites"); ax[1].set_ylabel("coverage"); ax[1].legend()
    fig.tight_layout(); fig.savefig(os.path.join(out, "E4_site_sweep.png"),
                                    dpi=110); plt.close(fig)
    g = {a: [d['certify_rate'] for d in summary['grid'][a]]
         for a in ALPHA_LADDER}
    summary["_headline"] = (f"certify-rate-by-nsites {summary['sweep']}: "
                            f"0.05={g[0.05]} 0.10={g[0.10]}")
    return summary


# ------------------------------------------------------------------ E5

def run_E5(out, quick):
    cfg = SimConfig()
    rng = _rng(5)
    train, aux, cal, head = _draw_split(cfg, ANCHOR_SITES, rng)
    tgt = draw_cohort(cfg, 1, rng, site_label_prefix="e5t",
                      require_both_classes=False)
    rep = run_certgate(train, aux, cal, tgt.x, target_label="E5",
                       oracle_target_y=tgt.y)
    op = rep["operative"]
    tau_star = op["tau"] if op else 0.8
    score = head.score(tgt.x)
    answered = score >= tau_star

    # representative cases: strongest answer, deepest decline, nearest threshold
    idx_ans = int(np.argmax(score))
    idx_dec = int(np.argmin(score))
    idx_near = int(np.argmin(np.abs(score - tau_star)))
    cases = {}
    for name, i in (("answered", idx_ans), ("declined", idx_dec),
                    ("near_threshold", idx_near)):
        attr = local_attribution(head, tgt.x[i])
        absn = abstention_explanation(head, tgt.x[i], tau_star)
        cases[name] = dict(
            index=i, score=float(score[i]),
            logit=float(attr["logit"]), p1=float(attr["p1"]),
            phi=[float(v) for v in attr["phi"]],
            margin_to_answer=float(absn["margin_to_answer"]),
            declined=bool(absn["declined"]))
    profile = cohort_abstention_profile(head, tgt.x, answered)
    gimp = global_importance(head)

    # ---- Replication arm. The single-draw case study above has n_declined ~ 2,
    # ---- which supports no cohort-level claim. So: R fresh draws on the
    # ---- distinct stream _rng(5, r), each giving an abstention profile at its
    # ---- own deployed tau; the case-study stream _rng(5) stays byte-exact.
    # ---- A null result — no stable single driver — is expected here, because
    # ---- features 0-3 share one signal direction with equal loadings.
    # ---- Ref: panel S1-4.
    R = 10 if quick else 200
    gaps, top_feats = [], []
    pooled_declined = pooled_targets = draws_certified = 0
    # ---- Functionally-grounded counterfactual evaluation: top-ranked
    # ---- single-feature delta vs an equal-|dz| most-favorable move on a
    # ---- uniformly random feature. Both are judged by the deployed rule,
    # ---- score >= tau. It runs on stream _rng(5, r, 1), so the case-study
    # ---- (_rng(5)) and replication (_rng(5, r)) draws stay byte-exact.
    # ---- Ref: R3-09 protocol (2026-07-31).
    cf_cases = cf_top_flips = cf_rand_flips = cf_unflippable = 0
    for r in range(R):
        rng_r = _rng(5, r)
        train_r, aux_r, cal_r, head_r = _draw_split(cfg, ANCHOR_SITES, rng_r)
        tgt_r = draw_cohort(cfg, 1, rng_r, site_label_prefix=f"e5r{r}",
                            require_both_classes=False)
        rep_r = run_certgate(train_r, aux_r, cal_r, tgt_r.x,
                             target_label=f"E5r-{r}")
        if rep_r["operative"] is None:
            continue
        draws_certified += 1
        prof_r = cohort_abstention_profile(head_r, tgt_r.x,
                                           rep_r["answered_mask"])
        pooled_declined += prof_r["n_declined"]
        pooled_targets += tgt_r.n
        if prof_r["n_declined"] > 0 and prof_r["n_answered"] > 0:
            gaps.append(prof_r["gap"])
            top_feats.append(int(prof_r["gap_ranking"][0]))
        tau_r = rep_r["operative"]["tau"]
        rng_cf = _rng(5, r, 1)
        for i in np.flatnonzero(~rep_r["answered_mask"]):
            cf = counterfactual_to_answer(head_r, tgt_r.x[i], tau_r)
            if not cf["flip_verified"] or not len(cf["single_feature_ranking"]):
                cf_unflippable += 1
                continue
            cf_cases += 1
            jt = int(cf["single_feature_ranking"][0])
            x_top = tgt_r.x[i].copy()
            x_top[jt] += cf["single_feature_delta_x"][jt]
            if float(head_r.score(x_top.reshape(1, -1))[0]) >= tau_r:
                cf_top_flips += 1
            budget = abs(float(cf["single_feature_delta_z"][jt]))
            jr = int(rng_cf.integers(0, tgt_r.x.shape[1]))
            s = cf["direction"]
            dz = budget if s * head_r.coef[jr] >= 0 else -budget
            x_rnd = tgt_r.x[i].copy()
            x_rnd[jr] += dz * head_r.sd[jr]
            if float(head_r.score(x_rnd.reshape(1, -1))[0]) >= tau_r:
                cf_rand_flips += 1
    counterfactual_eval = dict(
        n_declined_evaluated=int(cf_cases),
        n_unflippable=int(cf_unflippable),
        top_feature_flip_rate=_rate(cf_top_flips, cf_cases),
        random_feature_flip_rate=_rate(cf_rand_flips, cf_cases),
        protocol=("top-ranked single-feature counterfactual delta vs an "
                  "equal-|delta_z| most-favorable move on a uniformly random "
                  "feature; both judged by the deployed rule score >= tau "
                  "(R3-09 functionally-grounded)"))
    if gaps:
        gmat = np.vstack(gaps)
        gap_mean = gmat.mean(axis=0)
        gap_ci = 1.96 * gmat.std(axis=0, ddof=1) / np.sqrt(len(gmat)) \
            if len(gmat) > 1 else np.full(gmat.shape[1], np.nan)
        cnt = collections.Counter(top_feats)
        top_mode, top_n = cnt.most_common(1)[0]
        replication = dict(
            R=R, draws_certified=draws_certified,
            draws_with_declines=len(gaps),
            pooled_declined=int(pooled_declined),
            pooled_decline_rate=round(pooled_declined / pooled_targets, 4)
            if pooled_targets else None,
            gap_mean=[round(float(v), 4) for v in gap_mean],
            gap_ci95=[None if np.isnan(v) else round(float(v), 4)
                      for v in gap_ci],
            top_gap_feature_counts={str(k): int(v)
                                    for k, v in sorted(cnt.items())},
            top_gap_feature_mode=int(top_mode),
            top_gap_stability=round(top_n / len(gaps), 4),
            stable_driver=bool(top_n / len(gaps) >= 0.5),
            counterfactual_eval=counterfactual_eval)
    else:
        replication = dict(R=R, draws_certified=draws_certified,
                           draws_with_declines=0, pooled_declined=0,
                           stable_driver=False,
                           counterfactual_eval=counterfactual_eval)

    def _clean(vals):
        """Map NaN to None -- NaN is an invalid JSON token (audit V22)."""
        return [None if np.isnan(v) else float(v) for v in vals]

    payload = dict(
        tau_star=float(tau_star),
        global_importance=[float(v) for v in gimp],
        cases=cases,
        abstention_profile=dict(
            mean_abs_phi_answered=_clean(profile["mean_abs_phi_answered"]),
            mean_abs_phi_declined=_clean(profile["mean_abs_phi_declined"]),
            gap=_clean(profile["gap"]),
            gap_ranking=[int(v) for v in profile["gap_ranking"]],
            n_answered=profile["n_answered"], n_declined=profile["n_declined"]),
        replication=replication)
    with open(os.path.join(out, "E5_explain.json"), "w") as fh:
        json.dump(payload, fh, indent=2)

    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    feat = np.arange(len(gimp))
    ax[0].bar(feat, gimp, color="#228833")
    ax[0].set_title("Global importance (standardized coefs)")
    ax[0].set_xlabel("feature"); ax[0].set_ylabel("coef")
    if gaps:
        ax[1].bar(feat, replication["gap_mean"], color="#aa3377",
                  yerr=[0.0 if v is None else v
                        for v in replication["gap_ci95"]], capsize=3)
        ax[1].set_title(
            "Answered-vs-declined mean |attribution| gap\n"
            f"(mean +/- 95% CI over {len(gaps)} draws)")
    else:
        ax[1].bar(feat, profile["gap"], color="#aa3377")
        ax[1].set_title("Answered-vs-declined |phi| gap (single draw)")
    ax[1].set_xlabel("feature"); ax[1].set_ylabel("mean |phi| gap")
    fig.tight_layout(); fig.savefig(os.path.join(out, "E5_explain.png"),
                                    dpi=110); plt.close(fig)
    # An empty ranking (all answered or all declined) reports None, never a
    # fabricated feature index (audit V22).
    top_gap = (int(profile["gap_ranking"][0])
               if len(profile["gap_ranking"]) else None)
    res = dict(tau_star=round(float(tau_star), 4),
               n_answered=profile["n_answered"],
               n_declined=profile["n_declined"],
               top_gap_feature=top_gap,
               replication=replication)
    res["_headline"] = (
        f"tau*={res['tau_star']} answered={res['n_answered']} "
        f"declined={res['n_declined']} top_gap_feat={res['top_gap_feature']}")
    return res


# ------------------------------------------------------------------ E6

def run_E6(out, quick):
    cfg = SimConfig()
    rng = _rng(6)
    train, aux, cal, head = _draw_split(cfg, ANCHOR_SITES, rng)
    tgt = draw_cohort(cfg, 40, rng, site_label_prefix="e6t")   # multi-site pool
    # Per-record raw site labels. These feed the BBSE q_t cluster bootstrap
    # and the target-disjointness assertion (audits V2, V9).
    tgt_sites = np.array(tgt.site_labels, dtype=object)[tgt.site_id]
    rep = run_certgate(train, aux, cal, tgt.x, target_label="E6",
                       target_site_id=tgt_sites, oracle_target_y=tgt.y)
    op = rep["operative"]
    tau_star = op["tau"] if op else 0.8
    score = head.score(tgt.x)
    err = head.predict(tgt.x) != tgt.y
    answered = score >= tau_star

    rows = []
    for s in range(tgt.n_sites):
        m = tgt.site_id == s
        a = m & answered
        n_ans = int(a.sum())
        rows.append(dict(
            site=tgt.site_labels[s], size=int(m.sum()),
            coverage=round(float(a.sum() / max(m.sum(), 1)), 4),
            answered_err=round(float(err[a].mean()) if n_ans else float("nan"),
                               4),
            n_answered=n_ans))
    _write_csv(os.path.join(out, "E6_fairness.csv"), rows,
               ["site", "size", "coverage", "answered_err", "n_answered"])

    # Per-size-bin fairness rollup. Empty bins report None (JSON null, blank
    # CSV cell), never NaN -- which reads as an error in a paper table.
    bin_rows = []
    for lo, hi in SIZE_BINS:
        grp = [r for r in rows if lo <= r["size"] < hi]
        errs = [r["answered_err"] for r in grp
                if not np.isnan(r["answered_err"])]
        cov = round(float(np.mean([r["coverage"] for r in grp])), 4) if grp else None
        aerr = round(float(np.mean(errs)), 4) if errs else None
        bin_rows.append(dict(size_bin=f"[{lo},{hi})", n_sites=len(grp),
                             mean_coverage=cov, mean_answered_err=aerr))

    # The BBSE-implied view is an estimated quantity, present whenever the fit
    # held. It is never gated on which mode won deployment (verification N5).
    rho = rep["diagnostic"]["bbse"].get("rho_point")
    comp = composition(head, tgt.x, answered, rho_point=rho, oracle_y=tgt.y)
    comp_json = {k: {kk: (float(vv) if isinstance(vv, (int, float)) else vv)
                     for kk, vv in v.items()} for k, v in comp.items()}

    # Post-hoc reliability panel, added 2026-08-01 after E1-E7 were published.
    # It is descriptive: no certified quantity changes, and it consumes no
    # _rng(6) draw. The panel self-seeds from a sha256 of its own input bytes,
    # so E6's generator sequence is untouched, and so is
    # experiments/panel_s2_tables.py:e6_arm, which replays it.
    # `answered` is passed in so panel_from_head cross-checks it against
    # head.score >= tau_star, and the panel computes p = head.predict_proba(x)
    # itself. That is what makes the score/predict_proba conflation
    # unreachable. E6 has no reference scorer, so p_ref stays None and
    # brier.reference is an explicit null.
    panel = rp.panel_from_head(head, tgt.x, tgt.y, tgt.site_id, tau_star,
                               answered_mask=answered,
                               n_boot=(200 if quick else rp.N_BOOT))
    hl = rp.panel_headline(panel)
    _write_csv(os.path.join(out, "E6_reliability.csv"),
               rp.panel_reliability_rows(panel),
               list(rp.PANEL_RELIABILITY_FIELDS))
    # allow_nan=False enforces the no-NaN rule at the write boundary, rather
    # than trusting the emit pass to have got it right.
    with open(os.path.join(out, "E6_reliability.json"), "w") as fh:
        json.dump({"post_hoc": rp.E6_POST_HOC_NOTE, **panel}, fh, indent=2,
                  allow_nan=False)
    _e6_reliability_figure(out, panel)

    with open(os.path.join(out, "E6_composition.json"), "w") as fh:
        json.dump(dict(size_bins=bin_rows, composition=comp_json), fh, indent=2)

    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    labels = [b["size_bin"] for b in bin_rows]
    xpos = np.arange(len(labels))   # numeric x: a nan bar must not eat its tick
    heights = [b["mean_answered_err"] if b["mean_answered_err"] is not None
               else np.nan for b in bin_rows]           # empty bins -> no bar
    ax[0].bar(xpos, heights, color="#66ccee")
    ax[0].set_xticks(xpos); ax[0].set_xticklabels(labels)
    ax[0].axhline(op["alpha"] if op else 0.10, color="crimson", ls="--",
                  label="alpha")
    ax[0].set_title("Mean answered error by site-size bin")
    ax[0].set_xlabel("site-size bin"); ax[0].set_ylabel("answered error")
    ax[0].legend()
    covs = [b["mean_coverage"] if b["mean_coverage"] is not None else np.nan
            for b in bin_rows]                          # empty bins -> no bar
    ax[1].bar(xpos, covs, color="#66ccee")
    ax[1].set_xticks(xpos); ax[1].set_xticklabels(labels)
    ax[1].set_ylim(0.0, 1.0)
    ax[1].set_title("Mean per-site coverage by site-size bin")
    ax[1].set_xlabel("site-size bin"); ax[1].set_ylabel("coverage")
    fig.tight_layout(); fig.savefig(os.path.join(out, "E6_fairness.png"),
                                    dpi=110); plt.close(fig)
    res = dict(tau_star=round(float(tau_star), 4),
               size_bins=bin_rows,
               predicted_positive_fraction=round(
                   comp["predicted_class"]["positive_fraction"], 4),
               # The marker travels with the numbers. summary.md is what the
               # paper is written from, and the copy in E6_reliability.json
               # never reaches that reader. So these three keys must not land
               # in a published-grid block without saying they came after
               # E1-E7 and are descriptive only. Synthetic-side counterpart of
               # POST_HOC_LABEL travelling into EICU-SUMMARY.md.
               panel_post_hoc=rp.E6_POST_HOC_NOTE,
               # Post-hoc panel headline, never re-rounded. The panel rounds
               # once at emit time (rp.ROUND_DP = 6); a second pass here would
               # make the last decimal irreproducible. So these carry 6 dp
               # while E6's own keys carry 4 -- that asymmetry is the
               # round-once invariant, not an inconsistency.
               panel_ece_answered=hl["ece_answered"],
               panel_calibration_slope_answered=hl[
                   "calibration_slope_answered"],
               panel_skill_margin_answered_minus_all=hl[
                   "skill_margin_answered_minus_all"])
    res["_headline"] = (
        f"tau*={res['tau_star']} "
        f"pred_pos_frac={res['predicted_positive_fraction']} "
        f"skill_margin={res['panel_skill_margin_answered_minus_all']}")
    return res


def _e6_reliability_figure(out, panel):
    """Post-hoc panel figure: reliability curve left, skill margin right.

    The right panel shows the constant-majority skill margin by scope. Both use
    the same Paul-Tol hex set and dpi=110 as every other figure here.

    The empty-bin, ci_status and clamped-half-width rules live in exactly one
    place, rp.panel_reliability_series. run_eicu's panel figure reads the same
    contract, so the two cannot drift.
    """
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11, 4))
    axL.plot([0, 1], [0, 1], color="black", ls="--", lw=1, label="identity")
    for scope, colour in zip(rp.PANEL_CURVE_SCOPES, ("#4477aa", "#cc6677")):
        xs, ys, lo, hi = rp.panel_reliability_series(panel, scope)
        if xs:
            axL.errorbar(xs, ys, yerr=[lo, hi], marker="o", color=colour,
                         capsize=3, label=f"{scope} (n={len(xs)} bins)")
    axL.set_title("Reliability curve (POST-HOC panel)")
    axL.set_xlabel("mean predicted P(y=1)"); axL.set_ylabel("observed rate")
    axL.legend(fontsize=8)

    scopes = ("answered", "declined", "all")
    margins = [panel["skill"][s]["skill_margin"] for s in scopes]
    axR.bar(scopes, _plot(margins), color="#66ccee")
    axR.axhline(0.0, color="black", lw=1)
    axR.set_title("Skill margin vs constant-majority baseline")
    axR.set_ylabel("constant error - model error")
    fig.tight_layout(); fig.savefig(os.path.join(out, "E6_reliability.png"),
                                    dpi=rp.FIG_DPI); plt.close(fig)


# ------------------------------------------------------------------ E7

def _e7_walk(score_cal, err_cal, sid_cal, n_cal, score_aux, err_aux, sid_aux,
             n_aux, alpha, m_cap, rng):
    """One fixed-sequence walk at full DELTA: S_aux-ordered, S_cal-tested."""
    order = walk_order(influence_atoms(score_aux, err_aux, sid_aux, n_aux,
                                       TAU_GRID, alpha, m_cap))
    atoms = influence_atoms(score_cal, err_cal, sid_cal, n_cal, TAU_GRID,
                            alpha, m_cap)
    return fixed_sequence_walk(atoms, order, alpha, DELTA, TAU_GRID, rng=rng)


def run_E7(out, quick):
    """Record-as-unit comparator.

    Certifies the same calibration data two ways: the site-unit walk the paper
    deploys, and a record-as-unit walk -- influence_atoms over an
    E7_RECORD_SAMPLE-record subsample with per-record ids and M=1.

    That second walk is the plain record-level betting certifier of the
    Geifman–El-Yaniv lineage. It treats within-site-correlated records as
    independent draws, which is exactly the anti-conservatism the site-as-unit
    design exists to prevent.

    Both units are then scored at their own deployed taus against the
    influence-weighted R_M of one shared fresh E1_EVAL_SITES-site pool.

    Refs: panel S1-13.
    """
    R = 10 if quick else 200
    rows = []
    for su_idx, s_u in enumerate(E7_SU_ARM):
        cfg = SimConfig(s_u=s_u)
        for r in range(R):
            rng = _rng(7, su_idx, r)
            train, aux, cal, head = _draw_split(cfg, ANCHOR_SITES, rng)
            evalp = draw_cohort(cfg, E1_EVAL_SITES, rng,
                                site_label_prefix=f"e7v{su_idx}_{r}")
            sc_cal = head.score(cal.x)
            er_cal = head.predict(cal.x) != cal.y
            sc_aux = head.score(aux.x)
            er_aux = head.predict(aux.x) != aux.y
            rr = _rng(7, su_idx, r, 1)
            ic = rr.choice(cal.n, E7_RECORD_SAMPLE, replace=False)
            ia = rr.choice(aux.n, E7_RECORD_SAMPLE, replace=False)
            rec_ids = np.arange(E7_RECORD_SAMPLE)
            for alpha in ALPHA_LADDER:
                _, dep_site = _e7_walk(
                    sc_cal, er_cal, cal.site_id, cal.n_sites,
                    sc_aux, er_aux, aux.site_id, aux.n_sites,
                    alpha, M_INFLUENCE,
                    certification_rng(alpha, MODE_BASELINE))
                _, dep_rec = _e7_walk(
                    sc_cal[ic], er_cal[ic], rec_ids, E7_RECORD_SAMPLE,
                    sc_aux[ia], er_aux[ia], rec_ids, E7_RECORD_SAMPLE,
                    alpha, 1,
                    certification_rng(alpha, MODE_BASELINE, "e7-record"))
                for unit, dep in (("site", dep_site), ("record", dep_rec)):
                    if dep is None:
                        rows.append(dict(s_u=s_u, draw=r, alpha=alpha,
                                         unit=unit, certified=False, tau=None,
                                         coverage=None, rm_fresh=None,
                                         rm_exceed=None))
                        continue
                    rows.append(dict(s_u=s_u, draw=r, alpha=alpha, unit=unit,
                                     certified=True,
                                     **_rescore(head, evalp, dep, alpha)))
    _write_csv(os.path.join(out, "E7_comparator.csv"), rows,
               ["s_u", "draw", "alpha", "unit", "certified", "tau",
                "coverage", "rm_fresh", "rm_exceed"])

    summary = {"R": R, "record_sample": E7_RECORD_SAMPLE,
               "comparator": ("record unit = per-record atoms with M=1 on an "
                              f"{E7_RECORD_SAMPLE}-record subsample — the "
                              "plain record-level betting certifier, which "
                              "treats within-site-correlated records as "
                              "independent"),
               "arms": {}}
    for s_u in E7_SU_ARM:
        arm = {}
        for alpha in ALPHA_LADDER:
            per = {}
            for unit in ("site", "record"):
                sub = [x for x in rows if x["s_u"] == s_u
                       and x["alpha"] == alpha and x["unit"] == unit]
                certs = [x for x in sub if x["certified"]]
                per[unit] = _rollup(certs, R,
                                    ("certify_rate", "rm_exceed_rate",
                                     "mean_rm_fresh", "mean_tau"))
            arm[alpha] = per
        summary["arms"][s_u] = arm

    fig, ax = plt.subplots(1, len(ALPHA_LADDER), figsize=(12, 4))
    width = 0.2
    xpos = np.arange(len(E7_SU_ARM))
    for k, alpha in enumerate(ALPHA_LADDER):
        a = ax[k]
        for j, (unit, color) in enumerate((("site", "#4477aa"),
                                           ("record", "#cc6677"))):
            cert = [summary["arms"][s][alpha][unit]["certify_rate"]
                    for s in E7_SU_ARM]
            exc = [summary["arms"][s][alpha][unit]["rm_exceed_rate"]
                   for s in E7_SU_ARM]
            a.bar(xpos + (2 * j - 1.5) * width, cert, width,
                  label=f"{unit} certify", color=color, alpha=0.45)
            a.bar(xpos + (2 * j - 0.5) * width, _plot(exc), width,
                  label=f"{unit} R_M-exceed", color=color)
        a.axhline(DELTA, color="black", ls="--", label=f"DELTA={DELTA}")
        a.set_xticks(xpos)
        a.set_xticklabels([f"s_u={s}" for s in E7_SU_ARM])
        a.set_title(f"Site vs record unit (alpha={alpha})")
        a.set_ylabel("rate"); a.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(os.path.join(out, "E7_comparator.png"),
                                    dpi=110); plt.close(fig)
    arm0 = summary["arms"][E7_SU_ARM[0]]
    summary["_headline"] = (
        f"a=0.05 record certify={arm0[0.05]['record']['certify_rate']} "
        f"exceed={arm0[0.05]['record']['rm_exceed_rate']} vs site "
        f"certify={arm0[0.05]['site']['certify_rate']}; "
        f"a=0.10 record exceed={arm0[0.10]['record']['rm_exceed_rate']}")
    return summary


# ------------------------------------------------------------------ E8

class _FnHead:
    """Duck-typed head for E8 arm C.

    Everything downstream of scoring needs only .score and .predict, following
    the reliability-panel precedent. Never fed to explain.py, which requires
    the linear Head.
    """

    def __init__(self, score, predict):
        self.score, self.predict = score, predict


def _zero_prefix(x, k):
    """Copy x with its first k feature columns zeroed (the degraded head)."""
    xz = x.copy()
    xz[:, :k] = 0.0
    return xz


def _bound_walk(atoms, order, alpha, delta, tau_grid, ucb):
    """Comparator fixed-sequence walk (SPEC E8 arm A).

    Same order and stop-at-first-failure semantics as
    certify.fixed_sequence_walk, with ucb(atoms[t], delta) <= alpha in place of
    the betting test. The library walk stays untouched -- no injection point,
    so the delta-accounting spy keeps working.
    """
    certified = []
    for t in order:
        if ucb(atoms[t], delta) <= alpha:
            certified.append(int(t))
        else:
            break
    if not certified:
        return [], None
    return certified, min(certified, key=lambda t: tau_grid[t])


def _flip_labels(cohorts, eta, rng):
    """E8 arm B aleatoric floor: symmetric label flips at rate eta.

    Flips come from one stream over the cohorts in a fixed order, and are
    applied to train, aux, cal and the eval pool alike. Exchangeability
    (Assumption 1) therefore holds by construction. This floor is irreducible
    error that no threshold can screen away.
    """
    for c in cohorts:
        flip = rng.random(len(c.y)) < eta
        c.y[flip] = ~c.y[flip]


def run_E8(out, quick):
    """Certificate stress and comparator suite.

    Three arms:

      - A: four alternative one-sided bounds, walked on the same atoms and in
        the same order as the WSR betting test (review weakness 1). The
        two-sided reading is pre-committed in SPEC.
      - B: the label-noise stress frontier (weakness 4). Certify rate must
        collapse before exceedance appears as the aleatoric floor rises.
      - C: alternative heads (S2-26/S2-27). Validity is head-agnostic; quality
        is priced as coverage.

    Refs: revision-2; SPEC "E8".
    """
    R = 10 if quick else 200
    noise_R = 6 if quick else E8_NOISE_R
    sweep = QUICK_SWEEP if quick else FULL_SWEEP
    n_boot = 200 if quick else E8_BOOT

    # ---- arm A: comparator bounds on identical atoms --------------------
    rows_a = []
    for n_idx, n_sites in enumerate(sweep):
        cfg = SimConfig()
        for r in range(R):
            rng = _rng(8, 0, n_idx, r)
            train, aux, cal, head = _draw_split(cfg, n_sites, rng)
            evalp = draw_cohort(cfg, E1_EVAL_SITES, rng,
                                site_label_prefix=f"e8av{n_idx}_{r}")
            sc_cal, er_cal = head.score(cal.x), head.predict(cal.x) != cal.y
            sc_aux, er_aux = head.score(aux.x), head.predict(aux.x) != aux.y
            boot_rng = _rng(8, 0, n_idx, r, 1)
            ucbs = {
                "hoeffding": hoeffding_ucb,
                "mpeb": mpeb_ucb,
                "t": t_ucb,
                "site_boot": lambda z, d: site_bootstrap_ucb(
                    z, d, n_boot, boot_rng),
            }
            for alpha in ALPHA_LADDER:
                a_aux = influence_atoms(sc_aux, er_aux, aux.site_id,
                                        aux.n_sites, TAU_GRID, alpha,
                                        M_INFLUENCE)
                a_cal = influence_atoms(sc_cal, er_cal, cal.site_id,
                                        cal.n_sites, TAU_GRID, alpha,
                                        M_INFLUENCE)
                order = walk_order(a_aux)
                for method in E8_COMPARATORS:
                    if method == "wsr":
                        _, dep = fixed_sequence_walk(
                            a_cal, order, alpha, DELTA, TAU_GRID,
                            rng=certification_rng(alpha, MODE_BASELINE,
                                                  "e8-comp"))
                    else:
                        _, dep = _bound_walk(a_cal, order, alpha, DELTA,
                                             TAU_GRID, ucbs[method])
                    row = dict(n_sites=n_sites, draw=r, alpha=alpha,
                               method=method, certified=dep is not None,
                               tau=None, coverage=None, rm_fresh=None,
                               rm_exceed=None)
                    if dep is not None:
                        row.update(_rescore(head, evalp, dep, alpha))
                    rows_a.append(row)
    _write_csv(os.path.join(out, "E8_comparators.csv"), rows_a,
               ["n_sites", "draw", "alpha", "method", "certified", "tau",
                "coverage", "rm_fresh", "rm_exceed"])

    # ---- arm B: label-noise stress frontier -----------------------------
    rows_b = []
    for e_idx, eta in enumerate(E8_NOISE_SWEEP):
        cfg = SimConfig()
        for r in range(noise_R):
            rng = _rng(8, 1, e_idx, r)
            coh = draw_cohort(cfg, ANCHOR_SITES, rng)
            train, aux, cal = split_sites(coh, rng)
            evalp = draw_cohort(cfg, E1_EVAL_SITES, rng,
                                site_label_prefix=f"e8nv{e_idx}_{r}")
            _flip_labels((train, aux, cal, evalp), eta,
                         _rng(8, 1, e_idx, r, 1))
            head = fit_head(train)
            sc_cal, er_cal = head.score(cal.x), head.predict(cal.x) != cal.y
            sc_aux, er_aux = head.score(aux.x), head.predict(aux.x) != aux.y
            risk_floor = _rm_on_pool(head, evalp, float(TAU_GRID[0]))
            for alpha in ALPHA_LADDER:
                a_aux = influence_atoms(sc_aux, er_aux, aux.site_id,
                                        aux.n_sites, TAU_GRID, alpha,
                                        M_INFLUENCE)
                a_cal = influence_atoms(sc_cal, er_cal, cal.site_id,
                                        cal.n_sites, TAU_GRID, alpha,
                                        M_INFLUENCE)
                _, dep = fixed_sequence_walk(
                    a_cal, walk_order(a_aux), alpha, DELTA, TAU_GRID,
                    rng=certification_rng(alpha, MODE_BASELINE, "e8-noise"))
                row = dict(eta=eta, draw=r, alpha=alpha,
                           certified=dep is not None, tau=None, coverage=None,
                           rm_fresh=None, rm_exceed=None,
                           risk_at_lowest_tau=round(risk_floor, 6))
                if dep is not None:
                    row.update(_rescore(head, evalp, dep, alpha))
                rows_b.append(row)
    _write_csv(os.path.join(out, "E8_noise.csv"), rows_b,
               ["eta", "draw", "alpha", "certified", "tau", "coverage",
                "rm_fresh", "rm_exceed", "risk_at_lowest_tau"])

    # ---- arm C: alternative heads ---------------------------------------
    rows_c = []
    for h_idx, head_name in enumerate(E8_HEAD_ARMS):
        cfg = SimConfig()
        for r in range(R):
            rng = _rng(8, 2, h_idx, r)
            train, aux, cal, lin_head = _draw_split(cfg, ANCHOR_SITES, rng)
            evalp = draw_cohort(cfg, E1_EVAL_SITES, rng,
                                site_label_prefix=f"e8hv{h_idx}_{r}")
            if head_name == "gbm":
                seed = int(_rng(8, 2, h_idx, r, 1).integers(2 ** 31))
                clf = HistGradientBoostingClassifier(
                    max_iter=E8_GBM_MAX_ITER, random_state=seed)
                clf.fit(train.x, train.y)

                def _sc(x, clf=clf):
                    p = clf.predict_proba(x)[:, 1]
                    return np.maximum(p, 1.0 - p)

                def _pr(x, clf=clf):
                    return clf.predict_proba(x)[:, 1] >= 0.5

                alt = _FnHead(_sc, _pr)
            else:                                      # "degraded"
                dhead = fit_head(dataclasses.replace(
                    train,
                    x=_zero_prefix(train.x, E8_DEGRADED_ZERO_FEATURES)))

                def _sc(x, h=dhead):
                    return h.score(_zero_prefix(x, E8_DEGRADED_ZERO_FEATURES))

                def _pr(x, h=dhead):
                    return h.predict(_zero_prefix(x,
                                                  E8_DEGRADED_ZERO_FEATURES))

                alt = _FnHead(_sc, _pr)
            heads = {head_name: alt}
            if h_idx == 0:
                # same-draws linear reference, once (the gbm arm's draws)
                heads["linear"] = lin_head
            for name, hd in heads.items():
                sc_cal, er_cal = hd.score(cal.x), hd.predict(cal.x) != cal.y
                sc_aux, er_aux = hd.score(aux.x), hd.predict(aux.x) != aux.y
                for alpha in ALPHA_LADDER:
                    a_aux = influence_atoms(sc_aux, er_aux, aux.site_id,
                                            aux.n_sites, TAU_GRID, alpha,
                                            M_INFLUENCE)
                    a_cal = influence_atoms(sc_cal, er_cal, cal.site_id,
                                            cal.n_sites, TAU_GRID, alpha,
                                            M_INFLUENCE)
                    walk_rng = (certification_rng(alpha, MODE_BASELINE)
                                if name == "linear" else
                                certification_rng(alpha, MODE_BASELINE,
                                                  f"e8-head-{name}"))
                    _, dep = fixed_sequence_walk(
                        a_cal, walk_order(a_aux), alpha, DELTA, TAU_GRID,
                        rng=walk_rng)
                    row = dict(head=name, draw=r, alpha=alpha,
                               certified=dep is not None, tau=None,
                               coverage=None, rm_fresh=None, rm_exceed=None)
                    if dep is not None:
                        row.update(_rescore(hd, evalp, dep, alpha))
                    rows_c.append(row)
    _write_csv(os.path.join(out, "E8_heads.csv"), rows_c,
               ["head", "draw", "alpha", "certified", "tau", "coverage",
                "rm_fresh", "rm_exceed"])

    # ---- summary ---------------------------------------------------------
    def _agg(rows, key_field, key):
        sub = [x for x in rows if x[key_field] == key]
        out_by_alpha = {}
        for alpha in ALPHA_LADDER:
            s = [x for x in sub if x["alpha"] == alpha]
            certs = [x for x in s if x["certified"]]
            out_by_alpha[alpha] = _rollup(
                certs, len(s),
                ("certify_rate", "rm_exceed_rate", "mean_tau",
                 "mean_coverage", "mean_rm_fresh"),
                none_certify=not s)
        return out_by_alpha

    comp = {}
    for method in E8_COMPARATORS:
        per = _agg(rows_a, "method", method)
        for alpha in ALPHA_LADDER:
            per[alpha]["certify_by_nsites"] = [
                round(sum(1 for x in rows_a
                          if x["method"] == method and x["alpha"] == alpha
                          and x["n_sites"] == n and x["certified"]) / R, 4)
                for n in sweep]
        comp[method] = per
    noise = {}
    for eta in E8_NOISE_SWEEP:
        per = _agg(rows_b, "eta", eta)
        sub = [x for x in rows_b if x["eta"] == eta and x["alpha"] == 0.10]
        per["mean_risk_at_lowest_tau"] = round(float(np.mean(
            [x["risk_at_lowest_tau"] for x in sub])), 4) if sub else None
        noise[eta] = per
    heads_summary = {name: _agg(rows_c, "head", name)
                     for name in ("linear",) + E8_HEAD_ARMS}

    summary = {
        "R": R, "noise_R": noise_R, "sweep": list(sweep), "n_boot": n_boot,
        "comparators": comp,
        "noise": noise,
        "heads": heads_summary,
        "explain_supported": {"linear": True, "gbm": False,
                              "degraded": False},
        "notes": ("arm A: identical atoms and walk order across all five "
                  "certifiers; two-sided reading pre-committed in SPEC. "
                  "arm B: flips applied to every cohort alike, so "
                  "exchangeability holds by construction. arm C: linear "
                  "reference rows come from the gbm arm's draws; "
                  "temperature miscalibration is analytically a no-op for "
                  "the gate (monotone score transform) and is not simulated. "
                  "explain_supported=False for the degraded head marks the "
                  "deployed explanation path, not linear-algebra "
                  "feasibility."),
    }

    # ---- figure ----------------------------------------------------------
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    colors = {"wsr": "#4477aa", "hoeffding": "#cc6677", "mpeb": "#228833",
              "t": "#ccbb44", "site_boot": "#aa3377"}
    a = axes[0]
    for method in E8_COMPARATORS:
        a.plot(sweep, comp[method][0.10]["certify_by_nsites"], "-o",
               color=colors[method], label=method, ms=3)
        a.plot(sweep, comp[method][0.05]["certify_by_nsites"], "--o",
               color=colors[method], ms=3, alpha=0.5)
    a.set_xlabel("n_sites")
    a.set_ylabel("certify rate")
    a.set_title("Comparator frontiers (solid a=0.10, dashed a=0.05)")
    a.legend(fontsize=7)
    a = axes[1]
    etas = list(E8_NOISE_SWEEP)
    a.plot(etas, [noise[e][0.10]["certify_rate"] for e in etas], "-o",
           color="#4477aa", label="certify rate (a=0.10)")
    exc = [noise[e][0.10]["rm_exceed_rate"] for e in etas]
    a.plot(etas, _plot(exc), "-s", color="#cc6677", label="R_M-exceed rate")
    a.axhline(DELTA, color="black", ls="--", lw=0.8, label=f"DELTA={DELTA}")
    a.set_xlabel("label-noise rate eta")
    a.set_title("Stress frontier")
    a.legend(fontsize=7)
    a = axes[2]
    names = ("linear",) + E8_HEAD_ARMS
    xpos = np.arange(len(names))
    cov = [heads_summary[n][0.10]["mean_coverage"] for n in names]
    cert = [heads_summary[n][0.10]["certify_rate"] for n in names]
    a.bar(xpos - 0.15, _plot(cert), 0.3, color="#4477aa",
          label="certify rate")
    a.bar(xpos + 0.15, _plot(cov), 0.3, color="#66ccee", label="coverage")
    a.set_xticks(xpos)
    a.set_xticklabels(names)
    a.set_title("Heads (a=0.10)")
    a.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "E8_suite.png"), dpi=110)
    plt.close(fig)
    h_wsr = comp["wsr"][0.10]
    h_mpe = comp["mpeb"][0.10]
    h_noise = {e: v[0.10]["certify_rate"] for e, v in noise.items()}
    h_deg = heads_summary["degraded"][0.10]
    summary["_headline"] = (
        f"comp a=0.10 wsr={h_wsr['certify_by_nsites']} "
        f"mpeb={h_mpe['certify_by_nsites']}; noise certify={h_noise}; "
        f"degraded cov={h_deg['mean_coverage']} "
        f"exceed={h_deg['rm_exceed_rate']}")
    return summary


# ------------------------------------------------------------------ E9

def _e9_fnr_rng(budget, stream=""):
    """Permutation stream for the experimental FNR walks.

    Mirrors certify.certification_rng's sha256-only construction, but indexes
    E9_FNR_LADDER and carries a leading 9 discriminator, so it can never alias
    a certification stream. The frozen library function and ALPHA_LADDER stay
    untouched (SPEC "Outcome-weighted atoms").
    """
    h = hashlib.sha256(str(stream).encode()).digest()
    return np.random.default_rng(np.random.SeedSequence(
        [SEED, 9, E9_FNR_LADDER.index(budget),
         int.from_bytes(h[:4], "big"), int.from_bytes(h[4:8], "big")]))


def _fnr_on_pool(head, pool, tau):
    """Influence-weighted false-negative rate among answered positives.

    On a fresh pool, FNR_M = sum_c (g_c/n_c) fn_c / sum_c (g_c/n_c) ap_c with
    g_c = min(n_c, M). Returns NaN when no positives answer.

    Refs: SPEC "Outcome-weighted atoms".
    """
    score = head.score(pool.x)
    err = head.predict(pool.x) != pool.y
    ans = score >= tau
    sizes = pool.site_sizes.astype(float)
    g_over_n = np.where(sizes > 0,
                        np.minimum(sizes, M_INFLUENCE)
                        / np.maximum(sizes, 1.0), 0.0)
    num_c = np.bincount(pool.site_id,
                        weights=(ans & err & pool.y).astype(float),
                        minlength=pool.n_sites)
    den_c = np.bincount(pool.site_id, weights=(ans & pool.y).astype(float),
                        minlength=pool.n_sites)
    num = float((g_over_n * num_c).sum())
    den = float((g_over_n * den_c).sum())
    return (num / den) if den > 0 else float("nan")


def run_E9(out, quick):
    """Power frontiers.

    Two arms:

      - A: the BBSE label-shift power frontier -- source-site count crossed
        with declared target mode at the anchor shift, running the standard
        pipeline in bbse mode only (review weakness 3). The
        single-site-declaration exceedance question is pre-declared in SPEC.
      - B: the outcome-weighted FNR frontier on unmodified atoms (weakness 2).
        The claim is a frontier and a price, never a tight FNR guarantee.

    Refs: revision-2; SPEC "E9".
    """
    R = 3 if quick else E9_R
    fnr_R = 10 if quick else E9_FNR_R

    # ---- arm A: BBSE power frontier -------------------------------------
    rows_a = []
    for n_idx, n_sites in enumerate(E9_SOURCE_SWEEP):
        for m_idx, mode in enumerate(E9_TARGET_MODES):
            cfg = SimConfig()
            for r in range(R):
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
                    tgt = draw_cohort(cfg, E9_TARGET_K, rng,
                                      label_base_rate=SHIFT_BASE,
                                      site_label_prefix=f"e9k{n_idx}_{r}")
                    tgt_sites = np.array(tgt.site_labels,
                                         dtype=object)[tgt.site_id]
                rep = run_certgate(train, aux, cal, tgt.x,
                                   target_label=f"E9a-{n_sites}-{mode}-{r}",
                                   target_site_id=tgt_sites,
                                   oracle_target_y=tgt.y, modes=("bbse",))
                bd = rep["diagnostic"]["bbse"]
                evalp = draw_cohort(cfg, E1_EVAL_SITES, rng,
                                    label_base_rate=SHIFT_BASE,
                                    site_label_prefix=f"e9v{n_idx}_{r}")
                lo, hi = bd.get("rho_lo"), bd.get("rho_hi")
                width = (round(float(hi) - float(lo), 4)
                         if lo is not None and hi is not None else None)
                for alpha in ALPHA_LADDER:
                    row = _row_for(rep, alpha)
                    certified = row is not None and row["status"] == "certified"
                    out_row = dict(n_source_sites=n_sites, target_mode=mode,
                                   draw=r, alpha=alpha, certified=certified,
                                   tau=None, coverage=None,
                                   decline_reason=None, rho_lo=lo, rho_hi=hi,
                                   box_width=width, rm_fresh=None,
                                   rm_exceed=None)
                    if certified:
                        out_row.update(_rescore(head, evalp, None, alpha,
                                                tau=row["tau"]))
                    elif row is not None:
                        out_row["decline_reason"] = \
                            row.get("reasons", {}).get("bbse")
                    else:
                        out_row["decline_reason"] = rep.get("reason")
                    rows_a.append(out_row)
    _write_csv(os.path.join(out, "E9_bbse_frontier.csv"), rows_a,
               ["n_source_sites", "target_mode", "draw", "alpha", "certified",
                "tau", "coverage", "decline_reason", "rho_lo", "rho_hi",
                "box_width", "rm_fresh", "rm_exceed"])

    # ---- arm B: FNR frontier on outcome-weighted atoms ------------------
    rows_b = []
    for n_idx, n_sites in enumerate(E9_FNR_SWEEP):
        cfg = SimConfig()
        for r in range(fnr_R):
            rng = _rng(9, 1, n_idx, r)
            train, aux, cal, head = _draw_split(cfg, n_sites, rng)
            evalp = draw_cohort(cfg, E1_EVAL_SITES, rng,
                                site_label_prefix=f"e9fv{n_idx}_{r}")
            sc_cal, er_cal = head.score(cal.x), head.predict(cal.x) != cal.y
            sc_aux, er_aux = head.score(aux.x), head.predict(aux.x) != aux.y
            w_cal = cal.y.astype(float)
            w_aux = aux.y.astype(float)
            true_fnr = _fnr_on_pool(head, evalp, float(TAU_GRID[0]))
            for budget in E9_FNR_LADDER:
                a_aux = influence_atoms(sc_aux, er_aux, aux.site_id,
                                        aux.n_sites, TAU_GRID, budget,
                                        M_INFLUENCE, weights=w_aux, wmax=1.0)
                a_cal = influence_atoms(sc_cal, er_cal, cal.site_id,
                                        cal.n_sites, TAU_GRID, budget,
                                        M_INFLUENCE, weights=w_cal, wmax=1.0)
                _, dep = fixed_sequence_walk(
                    a_cal, walk_order(a_aux), budget, DELTA, TAU_GRID,
                    rng=_e9_fnr_rng(budget, "e9-fnr"))
                row = dict(n_sites=n_sites, draw=r, fnr_budget=budget,
                           certified=dep is not None, tau=None, coverage=None,
                           fnr_fresh=None, fnr_exceed=None,
                           true_fnr_at_lowest_tau=round(true_fnr, 6))
                if dep is not None:
                    row.update(_rescore(head, evalp, dep, budget,
                                        risk=_fnr_on_pool,
                                        risk_key="fnr_fresh",
                                        exceed_key="fnr_exceed"))
                rows_b.append(row)
    _write_csv(os.path.join(out, "E9_fnr.csv"), rows_b,
               ["n_sites", "draw", "fnr_budget", "certified", "tau",
                "coverage", "fnr_fresh", "fnr_exceed",
                "true_fnr_at_lowest_tau"])

    # ---- summary ---------------------------------------------------------
    frontier = {}
    for n_sites in E9_SOURCE_SWEEP:
        for mode in E9_TARGET_MODES:
            sub = [x for x in rows_a if x["n_source_sites"] == n_sites
                   and x["target_mode"] == mode and x["alpha"] == 0.10]
            certs = [x for x in sub if x["certified"]]
            reasons = {}
            for x in sub:
                if not x["certified"]:
                    key = x["decline_reason"] or "unknown"
                    reasons[key] = reasons.get(key, 0) + 1
            widths = [x["box_width"] for x in sub
                      if x["box_width"] is not None]
            agg = _rollup(certs, R,
                          ("certify_rate", "mean_tau", "rm_exceed_rate"),
                          none_certify=not sub)
            frontier[f"{n_sites}|{mode}"] = dict(
                certify_rate=agg["certify_rate"],
                decline_reasons=reasons,
                median_box_width=round(float(np.median(widths)), 4)
                if widths else None,
                mean_tau=agg["mean_tau"],
                rm_exceed_rate=agg["rm_exceed_rate"])
    fnr = {}
    for budget in E9_FNR_LADDER:
        per = {}
        for n_sites in E9_FNR_SWEEP:
            sub = [x for x in rows_b if x["fnr_budget"] == budget
                   and x["n_sites"] == n_sites]
            certs = [x for x in sub if x["certified"]]
            per[n_sites] = _rollup(
                certs, fnr_R,
                ("certify_rate", "mean_tau", "mean_fnr_fresh",
                 "fnr_exceed_rate"),
                none_certify=not sub, risk_key="fnr_fresh",
                exceed_key="fnr_exceed")
        fnr[budget] = per
    truth = [x["true_fnr_at_lowest_tau"] for x in rows_b
             if x["fnr_budget"] == E9_FNR_LADDER[0]]
    summary = {
        "R": R, "fnr_R": fnr_R,
        "anchor_shift": SHIFT_BASE,
        "bbse_frontier": frontier,
        "fnr_frontier": fnr,
        "true_fnr_at_lowest_tau_mean": round(float(np.mean(truth)), 4)
        if truth else None,
        "notes": ("arm A: pipeline in bbse mode only; certificates rescored "
                  "on a fresh same-shift pool (E2's aggregate-estimand "
                  "precedent); the single-site-declaration exceedance rate "
                  "is a pre-declared question (SPEC E9). arm B: experimental "
                  "secondary certificate on unmodified influence_atoms with "
                  "weights=y; a frontier and a price, never a tight FNR "
                  "guarantee; 0.4 is the built-in always-refuses negative "
                  "control."),
    }

    # ---- figure ----------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    a = axes[0]
    for mode, color in (("single-site-cp", "#cc6677"), ("k40-boot", "#4477aa")):
        a.plot(E9_SOURCE_SWEEP,
               [frontier[f"{n}|{mode}"]["certify_rate"]
                for n in E9_SOURCE_SWEEP], "-o", color=color, label=mode, ms=4)
    a.set_xlabel("declared source sites")
    a.set_ylabel("BBSE certify rate (a=0.10)")
    a.set_title("Label-shift power frontier")
    a.legend(fontsize=8)
    a = axes[1]
    for n_sites, color in zip(E9_FNR_SWEEP, ("#cc6677", "#4477aa", "#228833")):
        a.plot(E9_FNR_LADDER,
               [fnr[b][n_sites]["certify_rate"] for b in E9_FNR_LADDER],
               "-o", color=color, label=f"{n_sites} sites", ms=4)
    a.set_xlabel("FNR budget")
    a.set_ylabel("certify rate")
    a.set_title("FNR frontier (outcome-weighted atoms)")
    a.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "E9_frontiers.png"), dpi=110)
    plt.close(fig)
    hl_fr = {k: v["certify_rate"] for k, v in frontier.items()
             if k.endswith("k40-boot")}
    hl_f5, hl_f55 = fnr[0.5], fnr[0.55]
    summary["_headline"] = (
        f"bbse k40 certify={hl_fr}; fnr b=0.5 by sites="
        f"{[hl_f5[n]['certify_rate'] for n in E9_FNR_SWEEP]} "
        f"b=0.55={[hl_f55[n]['certify_rate'] for n in E9_FNR_SWEEP]} "
        f"(truth~{summary['true_fnr_at_lowest_tau_mean']})")
    return summary


# ------------------------------------------------------------------ driver

_RUNNERS = {"E1": run_E1, "E2": run_E2, "E3": run_E3, "E4": run_E4,
            "E5": run_E5, "E6": run_E6, "E7": run_E7, "E8": run_E8,
            "E9": run_E9}


def _existing_summary_blocks(path):
    """Parse an existing summary.md into {experiment: rendered json block}.

    A partial (--only) run uses this to preserve the sections it did not
    recompute, instead of clobbering summary.md down to a subset. The header
    pattern tolerates a "(preserved ...)" suffix, so preserved sections survive
    a second partial run (audit V26).
    """
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    blocks = {}
    for m in re.finditer(r"^## (E\d)[^\n]*\n(```json\n.*?\n```)",
                         text, re.S | re.M):
        blocks[m.group(1)] = m.group(2)
    return blocks


def _write_summary(out, results, quick):
    """Write summary.md.

    Every fresh block is stamped with its own run mode and UTC timestamp, and
    preserved sections are marked in the header. Without those marks a "FULL"
    header could sit above a quick-computed block, with nothing to tell them
    apart (audit V26).
    """
    path = os.path.join(out, "summary.md")
    # preserve prior sections for experiments not recomputed in this run
    preserved = _existing_summary_blocks(path)
    lines = ["# CertGate synthetic experiments -- summary",
             "",
             f"- mode: {'QUICK' if quick else 'FULL'} (per-block stamps are "
             f"authoritative; preserved sections are marked)",
             f"- seed: {SEED}",
             f"- alpha ladder: {ALPHA_LADDER}, delta: {DELTA}",
             ""]
    stamp = dict(mode="QUICK" if quick else "FULL",
                 utc=datetime.datetime.now(
                     datetime.timezone.utc).isoformat(timespec="seconds"))
    for name in EXPERIMENTS:
        if name in results:
            payload = {"_run": stamp, **results[name]}
            block = "```json\n" + json.dumps(payload, indent=2) + "\n```"
            lines.append(f"## {name}")
        elif name in preserved:
            block = preserved[name]                 # keep the earlier section
            lines.append(f"## {name} (preserved from an earlier run)")
        else:
            continue
        lines.append(block)
        lines.append("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def main(argv=None):
    ap = argparse.ArgumentParser(description="CertGate synthetic experiments")
    ap.add_argument("--quick", action="store_true",
                    help="R=10, sweep {60,208,400}")
    ap.add_argument("--only", default=None,
                    help="comma-separated subset, e.g. E1,E4")
    ap.add_argument("--out", default=os.path.join("experiments", "out"),
                    help="output directory")
    args = ap.parse_args(argv)

    selected = EXPERIMENTS if args.only is None else tuple(
        s.strip().upper() for s in args.only.split(",") if s.strip())
    unknown = [s for s in selected if s not in _RUNNERS]
    if unknown:
        ap.error(f"unknown experiment(s): {unknown}; choose from {EXPERIMENTS}")

    os.makedirs(args.out, exist_ok=True)
    print(f"[certgate] {'QUICK' if args.quick else 'FULL'} run -> {args.out} "
          f"(seed={SEED}); experiments: {', '.join(selected)}")
    results = {}
    try:
        for name in EXPERIMENTS:
            if name in selected:
                results[name] = _RUNNERS[name](args.out, args.quick)
                # pop: the digest is CLI-only and must never reach summary.md
                print(f"[certgate] {name} done: "
                      f"{results[name].pop('_headline')}")
    finally:
        # An aborted run (e.g. E3's poison-verification gate) must never leave
        # fresh CSVs beside a silently stale summary (audit V26).
        _write_summary(args.out, results, args.quick)
        # Run-level provenance beside the artifacts (panel S2-24): package
        # versions, python, protocol seed, what ran and in which mode.
        with open(os.path.join(args.out, "provenance.json"), "w") as fh:
            json.dump(provenance(selected=",".join(selected),
                                 quick=bool(args.quick)), fh, indent=2)
        print(f"[certgate] wrote CSVs, PNGs, summary.md and provenance.json "
              f"to {args.out}")
    return results


if __name__ == "__main__":
    main()
