"""SPEC section "Experiments": the synthetic validation harness (METHODS 8).

Runs E1-E6 fully seeded from ``constants.SEED`` and deterministically; writes a
CSV per experiment, PNG figures (matplotlib Agg -- no seaborn, no interactive
display), and a ``summary.md`` into the output directory.

CLI::

    python -m experiments.run_synthetic [--quick] [--only E1,E4] [--out DIR]

``--quick``: R=10 draws, cluster sweep {60, 208, 400}. Full: R=200, sweep
{60, 100, 150, 208, 300, 400}. The full grid targets < ~30 min; --quick is a
fast smoke of every experiment (E1-quick must show zero hard violations).
"""

import argparse
import collections
import csv
import datetime
import json
import os
import re

import matplotlib
matplotlib.use("Agg")                       # headless: no interactive display
import matplotlib.pyplot as plt
import numpy as np

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
                              composition)
from certgate.harness import hard_violation, exceedance_reference, SIZE_BINS
from certgate.report import provenance

# ONE generator (audit V7): every experiment runs the documented SimConfig()
# defaults; the only experiment-local generator parameters are the shift/tilt
# each experiment is ABOUT, declared here and pinned by tests/test_constants.py.
# (The old undeclared SHIFT_SEP=1.8 made the E2/E3 headline numbers
# non-reproducible from the stated setup.)
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
EXPERIMENTS = ("E1", "E2", "E3", "E4", "E5", "E6", "E7")


# ------------------------------------------------------------------ helpers

def _rng(*parts):
    """Deterministic Generator seeded from the protocol SEED and index parts."""
    return np.random.default_rng(np.random.SeedSequence([SEED, *parts]))


def _rate(k, n):
    """Conditional rate over n certified draws; None (JSON null) when n == 0 --
    0.0 would conflate "no certificates issued" with "zero violations"."""
    return round(k / n, 4) if n else None


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
            # fully-gated report (insufficient-clusters / pool-too-small):
            # keep the structural gate reason attributable in the CSV
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


def _rm_on_pool(head, pool, tau):
    """Influence-weighted answered-set risk R_M on a fresh multi-site pool
    (METHODS 3) -- the quantity the certificate actually bounds (audit V1):
    R_M = sum_c g_c a_c e_c / sum_c g_c a_c = sum_c (g_c/n_c) err_ans_c /
    sum_c (g_c/n_c) ans_c with g_c = min(n_c, M). NaN when nothing answers."""
    score = head.score(pool.x)
    err = head.predict(pool.x) != pool.y
    ans = score >= tau
    n_sites = pool.n_sites
    sizes = pool.site_sizes.astype(float)
    g_over_n = np.where(sizes > 0,
                        np.minimum(sizes, M_INFLUENCE)
                        / np.maximum(sizes, 1.0), 0.0)
    num_c = np.bincount(pool.site_id, weights=(ans & err).astype(float),
                        minlength=n_sites)
    den_c = np.bincount(pool.site_id, weights=ans.astype(float),
                        minlength=n_sites)
    num = float((g_over_n * num_c).sum())
    den = float((g_over_n * den_c).sum())
    return (num / den) if den > 0 else float("nan")


def _per_site_exceed_frac(head, pool, tau, alpha):
    """DISPERSION DIAGNOSTIC (audit V1 -- no delta target attached): fraction
    of the pool's answering sites whose own answered error exceeds alpha. Under
    between-site heterogeneity this rises while the certified aggregate R_M
    stays within budget; it measures what the certificate deliberately does not
    bound."""
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


# ------------------------------------------------------------------ E1

def run_E1(out, quick):
    """E1 validity, rescored per audit V1.

    The CONFORMANCE metric is the aggregate quantity the test actually
    certifies: per draw, the certified tau is applied to a fresh
    ``E1_EVAL_SITES``-site pool and the influence-weighted answered risk R_M is
    computed on it; conformance = fraction of certified draws with R_M > alpha
    (target <= DELTA). The single-fresh-site hard-violation rate is RETAINED
    but is a PER-SITE DISPERSION DIAGNOSTIC with no delta target: the
    certificate deliberately does not bound individual sites, and the
    ``E1_SU_SWEEP`` arm shows the per-site rate rising with heterogeneity while
    the certified aggregate stays within budget.
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
        """Per-alpha summary for one s_u arm."""
        arm = {}
        for alpha in ALPHA_LADDER:
            certs = [x for x in sub if x["alpha"] == alpha and x["certified"]]
            n_c = len(certs)
            arm[alpha] = dict(
                certify_rate=round(n_c / R_arm, 4),
                n_certified=n_c,
                # CONFORMANCE (target <= DELTA): the certified aggregate.
                rm_exceed_rate=_rate(sum(bool(x["rm_exceed"]) for x in certs),
                                     n_c),
                mean_rm_fresh=round(float(np.mean([x["rm_fresh"]
                                                   for x in certs])), 4)
                if certs else None,
                # DIAGNOSTICS (no delta target): per-site dispersion.
                hard_violation_rate_diag=_rate(sum(x["hard"] for x in certs),
                                               n_c),
                exceedance_rate_diag=_rate(sum(x["exceed"] for x in certs),
                                           n_c),
                mean_per_site_exceed_frac=round(
                    float(np.mean([x["per_site_exceed_frac"] for x in certs])),
                    4) if certs else None,
                mean_coverage=round(float(np.mean([x["coverage"]
                                                   for x in certs]))
                                    if certs else 0.0, 4))
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
        # empty bins report None (-> JSON null), never NaN: NaN is an invalid
        # JSON token that breaks downstream parsers (uniform with E6's rollup)
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
    ax[0].bar([str(a) for a in alphas],
              [np.nan if v is None else v for v in rm_bars],
              color="#4477aa")
    for i, v in enumerate(rm_bars):
        if v is None:                     # rung never certified: no bar, say so
            ax[0].text(i, DELTA * 0.05, "no certificates", ha="center",
                       va="bottom", rotation=90, fontsize=8, color="dimgray")
    ax[0].axhline(DELTA, color="crimson", ls="--", label=f"DELTA={DELTA}")
    ax[0].set_title("E1 certified-aggregate R_M exceed rate")
    ax[0].set_xlabel("alpha"); ax[0].set_ylabel("rate"); ax[0].legend()
    labels = [b["size_bin"] for b in bins]
    _pnum = lambda v: np.nan if v is None else v      # empty bin -> gap in line
    ax[1].plot(labels, [_pnum(b["observed_exceedance"]) for b in bins], "o-",
               label="observed")
    ax[1].plot(labels, [_pnum(b["binomial_reference"]) for b in bins], "s--",
               label="binomial ref")
    ax[1].set_title("E1 exceedance vs reference (alpha=0.10)")
    ax[1].set_xlabel("answered-set size bin"); ax[1].set_ylabel("exceedance")
    ax[1].legend()
    su_vals = [s["s_u"] for s in sens]
    ax[2].plot(su_vals, [_pnum(s["rm_exceed_rate"]) for s in sens], "o-",
               label="aggregate R_M exceed (certified)")
    ax[2].plot(su_vals, [_pnum(s["hard_violation_rate_diag"]) for s in sens],
               "s--", label="per-site hard rate (diagnostic)")
    ax[2].axhline(DELTA, color="crimson", ls=":", label=f"DELTA={DELTA}")
    ax[2].set_title("E1 heterogeneity: aggregate vs per-site (alpha=0.10)")
    ax[2].set_xlabel("s_u (site random-effect sd)"); ax[2].set_ylabel("rate")
    ax[2].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(out, "E1_validity.png"),
                                    dpi=110); plt.close(fig)
    return summary


# ------------------------------------------------------------------ E2

def _e2_arm(cfg, base, R, seed_parts, prefix, label_suffix):
    """One magnitude arm of E2. ``seed_parts`` prefixes the per-draw stream, so
    the 0.22 anchor keeps its original ``_rng(2, r)`` stream (and its published
    numbers) byte-identical while sweep arms live on distinct streams."""
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
        # aggregate-estimand rescoring (draft-sync flag 2026-07-30): a fresh
        # label-shifted eval pool, drawn AFTER the streams above so every
        # anchor number stays byte-identical
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
    # anchor magnitude, full R, ORIGINAL seed streams (numbers byte-identical)
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
        return dict(
            certify_rate=round(n_c / n_draws, 4),
            n_certified=n_c,
            hard_violation_rate=_rate(sum(x["hard"] for x in certs), n_c),
            exceedance_rate=_rate(sum(x["exceed"] for x in certs), n_c),
            rm_exceed_rate=_rate(sum(bool(x.get("rm_exceed"))
                                     for x in certs), n_c),
            joint_certify_and_hard_rate=round(
                sum(1 for x in certs if x["hard"]) / n_draws, 4),
            decline_rate=round((len(sub) - n_c) / len(sub), 4) if sub else 0.0)

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
        ax[0].bar(xpos + dx, [np.nan if v is None else v for v in vals],
                  width, label=mode, color=color)
        for i, v in enumerate(vals):
            if v is None:                 # rung never certified: no bar, say so
                ax[0].text(xpos[i] + dx, DELTA * 0.05, "no certificates",
                           ha="center", va="bottom", rotation=90, fontsize=7,
                           color="dimgray")
    ax[0].axhline(DELTA, color="black", ls="--", label=f"DELTA={DELTA}")
    ax[0].set_xticks(xpos); ax[0].set_xticklabels([str(a) for a in alphas])
    ax[0].set_title(f"E2 hard-violation rate at shift -> {SHIFT_BASE}")
    ax[0].set_xlabel("alpha"); ax[0].set_ylabel("hard-violation rate")
    ax[0].legend()
    bases = [e["target_base"] for e in sweep]
    _p = lambda v: np.nan if v is None else v
    ax[1].plot(bases, [_p(e["baseline"]["hard_violation_rate"])
                       for e in sweep], "o-", color="#cc6677",
               label="baseline hard-viol")
    ax[1].plot(bases, [e["baseline"]["certify_rate"] for e in sweep], "o--",
               color="#cc6677", alpha=0.5, label="baseline certify")
    ax[1].plot(bases, [e["bbse"]["certify_rate"] for e in sweep], "s--",
               color="#4477aa", label="bbse certify")
    ax[1].plot(bases, [e["bbse"]["joint_certify_and_hard_rate"]
                       for e in sweep], "s-", color="#4477aa",
               label="bbse certify-and-violate")
    ax[1].axhline(DELTA, color="black", ls=":", label=f"DELTA={DELTA}")
    ax[1].set_title("E2 magnitude sweep (alpha=0.10)")
    ax[1].set_xlabel("target base rate (source 0.095)")
    ax[1].set_ylabel("rate"); ax[1].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(os.path.join(out, "E2_label_shift.png"),
                                    dpi=110); plt.close(fig)
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
        # aggregate-estimand rescoring (draft-sync flag 2026-07-30): a fresh
        # concept-tilted eval pool, drawn AFTER the streams above so the
        # anchor numbers stay byte-identical
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
    # construction check: the tilt is verified to push answered risk > alpha.
    # ENFORCED, not just reported (SPEC E3; REVIEW-FABLE D3): a de-poisoned
    # tilt aborts before anything is written -- a negative control that fails
    # verification must never emit passing-looking violation rates.
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
        n_c = len(certs)
        summary[alpha] = dict(
            certify_rate=round(n_c / R, 4),
            n_certified=n_c,
            hard_violation_rate=_rate(sum(x["hard"] for x in certs), n_c),
            exceedance_rate=_rate(sum(x["exceed"] for x in certs), n_c),
            rm_exceed_rate=_rate(sum(bool(x.get("rm_exceed"))
                                     for x in certs), n_c))

    fig, ax = plt.subplots(figsize=(7, 4))
    alphas = list(ALPHA_LADDER)
    hv_bars = [summary[a]["hard_violation_rate"] for a in alphas]
    ax.bar([str(a) for a in alphas],
           [np.nan if v is None else v for v in hv_bars], color="#ee8866")
    for i, v in enumerate(hv_bars):
        if v is None:                     # rung never certified: no bar, say so
            ax.text(i, DELTA * 0.05, "no certificates", ha="center",
                    va="bottom", rotation=90, fontsize=8, color="dimgray")
    ax.axhline(DELTA, color="black", ls="--", label=f"DELTA={DELTA}")
    ax.set_title("E3 concept-shift negative control (certificate should FAIL)")
    ax.set_xlabel("alpha"); ax.set_ylabel("hard-violation rate"); ax.legend()
    fig.tight_layout(); fig.savefig(os.path.join(out, "E3_concept_shift.png"),
                                    dpi=110); plt.close(fig)
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
                certify_rate=round(len(certs) / R, 4),
                mean_coverage=round(float(np.mean([x["coverage"]
                                                   for x in certs]))
                                    if certs else 0.0, 4)))
    summary["grid"] = grid

    # cluster counts whose calibration share falls under the 50-carrying-
    # cluster floor are structurally gated (reason=insufficient-clusters),
    # so they sample the gate, not the WSR information floor — annotate.
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
    ax[0].set_title("E4 certify rate vs cluster count")
    ax[0].set_xlabel("n_sites"); ax[0].set_ylabel("certify rate"); ax[0].legend()
    ax[1].set_title("E4 mean coverage vs cluster count")
    ax[1].set_xlabel("n_sites"); ax[1].set_ylabel("coverage"); ax[1].legend()
    fig.tight_layout(); fig.savefig(os.path.join(out, "E4_site_sweep.png"),
                                    dpi=110); plt.close(fig)
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

    # ---- replication arm (panel S1-4): the single-draw case study above is
    # ---- n_declined ~ 2, which supports NO cohort-level claim. R fresh draws
    # ---- on the DISTINCT stream _rng(5, r) (the case-study stream _rng(5)
    # ---- stays byte-identical); per draw, the abstention profile at that
    # ---- draw's deployed tau. A null result — no stable single driver — is
    # ---- the expected outcome for this generator (features 0-3 share one
    # ---- signal direction with equal loadings) and is reported as such.
    R = 10 if quick else 200
    gaps, top_feats = [], []
    pooled_declined = pooled_targets = draws_certified = 0
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
            stable_driver=bool(top_n / len(gaps) >= 0.5))
    else:
        replication = dict(R=R, draws_certified=draws_certified,
                           draws_with_declines=0, pooled_declined=0,
                           stable_driver=False)

    def _clean(vals):
        """NaN -> None: NaN is an invalid JSON token and the harness forbids
        emitting it (audit V22)."""
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
    ax[0].set_title("E5 global importance (standardized coefs)")
    ax[0].set_xlabel("feature"); ax[0].set_ylabel("coef")
    if gaps:
        ax[1].bar(feat, replication["gap_mean"], color="#aa3377",
                  yerr=[0.0 if v is None else v
                        for v in replication["gap_ci95"]], capsize=3)
        ax[1].set_title(
            f"E5 answered-vs-declined |phi| gap "
            f"(mean +/- 95% CI over {len(gaps)} draws)")
    else:
        ax[1].bar(feat, profile["gap"], color="#aa3377")
        ax[1].set_title("E5 answered-vs-declined |phi| gap (single draw)")
    ax[1].set_xlabel("feature"); ax[1].set_ylabel("mean |phi| gap")
    fig.tight_layout(); fig.savefig(os.path.join(out, "E5_explain.png"),
                                    dpi=110); plt.close(fig)
    # an empty ranking (all answered or all declined) reports None, never a
    # fabricated feature index (audit V22)
    top_gap = (int(profile["gap_ranking"][0])
               if len(profile["gap_ranking"]) else None)
    return dict(tau_star=round(float(tau_star), 4),
                n_answered=profile["n_answered"],
                n_declined=profile["n_declined"],
                top_gap_feature=top_gap,
                replication=replication)


# ------------------------------------------------------------------ E6

def run_E6(out, quick):
    cfg = SimConfig()
    rng = _rng(6)
    train, aux, cal, head = _draw_split(cfg, ANCHOR_SITES, rng)
    tgt = draw_cohort(cfg, 40, rng, site_label_prefix="e6t")   # multi-site pool
    # per-record raw site labels: feeds the BBSE q_t cluster bootstrap and the
    # target-disjointness assertion (audit V2/V9)
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

    # per-size-bin fairness rollup. Empty bins report None (-> JSON null /
    # blank CSV cell), never NaN: NaN is an invalid JSON token that breaks
    # downstream parsers and reads as an error in a paper table.
    bin_rows = []
    for lo, hi in SIZE_BINS:
        grp = [r for r in rows if lo <= r["size"] < hi]
        errs = [r["answered_err"] for r in grp
                if not np.isnan(r["answered_err"])]
        cov = round(float(np.mean([r["coverage"] for r in grp])), 4) if grp else None
        aerr = round(float(np.mean(errs)), 4) if errs else None
        bin_rows.append(dict(size_bin=f"[{lo},{hi})", n_sites=len(grp),
                             mean_coverage=cov, mean_answered_err=aerr))

    # the BBSE-implied view is an estimated quantity, present whenever the fit
    # held -- NOT gated on which mode won deployment (verification N5)
    rho = rep["diagnostic"]["bbse"].get("rho_point")
    comp = composition(head, tgt.x, answered, rho_point=rho, oracle_y=tgt.y)
    comp_json = {k: {kk: (float(vv) if isinstance(vv, (int, float)) else vv)
                     for kk, vv in v.items()} for k, v in comp.items()}
    with open(os.path.join(out, "E6_composition.json"), "w") as fh:
        json.dump(dict(size_bins=bin_rows, composition=comp_json), fh, indent=2)

    fig, ax = plt.subplots(figsize=(7, 4))
    labels = [b["size_bin"] for b in bin_rows]
    heights = [b["mean_answered_err"] if b["mean_answered_err"] is not None
               else np.nan for b in bin_rows]           # empty bins -> no bar
    ax.bar(labels, heights, color="#66ccee")
    ax.axhline(tau_and_alpha(op), color="crimson", ls="--", label="alpha")
    ax.set_title("E6 mean answered error by site-size bin")
    ax.set_xlabel("site-size bin"); ax.set_ylabel("answered error"); ax.legend()
    fig.tight_layout(); fig.savefig(os.path.join(out, "E6_fairness.png"),
                                    dpi=110); plt.close(fig)
    return dict(tau_star=round(float(tau_star), 4),
                size_bins=bin_rows,
                predicted_positive_fraction=round(
                    comp["predicted_class"]["positive_fraction"], 4))


def tau_and_alpha(op):
    return op["alpha"] if op else 0.10


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
    """Record-as-unit comparator (panel S1-13).

    Certify the SAME calibration data two ways: (i) the site-unit walk the
    paper deploys, and (ii) a record-as-unit walk — ``influence_atoms`` over an
    ``E7_RECORD_SAMPLE``-record subsample with per-record ids and M=1, i.e. the
    plain record-level betting certifier of the Geifman–El-Yaniv lineage. The
    record certifier treats within-site-correlated records as independent
    draws, which is exactly the anti-conservatism the site-as-unit design
    exists to prevent; both units are then scored at their own deployed taus
    against the influence-weighted R_M of one shared fresh
    ``E1_EVAL_SITES``-site pool.
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
                    tau = float(TAU_GRID[dep])
                    rm = _rm_on_pool(head, evalp, tau)
                    cov = float((head.score(evalp.x) >= tau).mean())
                    rows.append(dict(s_u=s_u, draw=r, alpha=alpha, unit=unit,
                                     certified=True, tau=round(tau, 4),
                                     coverage=round(cov, 4),
                                     rm_fresh=round(rm, 6),
                                     rm_exceed=bool(rm > alpha)))
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
                per[unit] = dict(
                    certify_rate=round(len(certs) / R, 4),
                    rm_exceed_rate=_rate(
                        sum(bool(x["rm_exceed"]) for x in certs), len(certs)),
                    mean_rm_fresh=round(float(np.mean(
                        [x["rm_fresh"] for x in certs])), 4) if certs else None,
                    mean_tau=round(float(np.mean(
                        [x["tau"] for x in certs])), 4) if certs else None)
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
            a.bar(xpos + (2 * j - 0.5) * width,
                  [np.nan if v is None else v for v in exc], width,
                  label=f"{unit} R_M-exceed", color=color)
        a.axhline(DELTA, color="black", ls="--", label=f"DELTA={DELTA}")
        a.set_xticks(xpos)
        a.set_xticklabels([f"s_u={s}" for s in E7_SU_ARM])
        a.set_title(f"E7 site vs record unit (alpha={alpha})")
        a.set_ylabel("rate"); a.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(os.path.join(out, "E7_comparator.png"),
                                    dpi=110); plt.close(fig)
    return summary


# ------------------------------------------------------------------ driver

_RUNNERS = {"E1": run_E1, "E2": run_E2, "E3": run_E3, "E4": run_E4,
            "E5": run_E5, "E6": run_E6, "E7": run_E7}


def _existing_summary_blocks(path):
    """Parse an existing summary.md into {experiment: rendered ```json block```}
    so a partial (--only) run can preserve the sections it did not recompute
    instead of clobbering them to a subset. The header pattern tolerates a
    "(preserved ...)" suffix so preserved sections survive a second partial
    run (audit V26)."""
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
    """Write summary.md. Every fresh block is stamped with its own run mode and
    UTC timestamp, and preserved sections are visibly marked in the header --
    a FULL header above a QUICK-computed block was indistinguishable before
    (audit V26)."""
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
                print(f"[certgate] {name} done: "
                      f"{_headline(name, results[name])}")
    finally:
        # an aborted run (e.g. E3's poison-verification gate) must never leave
        # fresh CSVs beside a silently stale summary (audit V26)
        _write_summary(args.out, results, args.quick)
        # run-level provenance beside the artifacts (panel S2-24): package
        # versions, python, protocol seed, what ran and in which mode
        with open(os.path.join(args.out, "provenance.json"), "w") as fh:
            json.dump(provenance(selected=",".join(selected),
                                 quick=bool(args.quick)), fh, indent=2)
        print(f"[certgate] wrote CSVs, PNGs, summary.md and provenance.json "
              f"to {args.out}")
    return results


def _headline(name, res):
    """One-line human-readable digest of an experiment result (for the CLI tail)."""
    if name == "E1":
        return (f"total_rm_exceed={res['total_rm_exceed']}, "
                f"a=0.10 certify={res[0.10]['certify_rate']} "
                f"rm_exceed={res[0.10]['rm_exceed_rate']} "
                f"per_site_diag={res[0.10]['hard_violation_rate_diag']} "
                f"coverage={res[0.10]['mean_coverage']}")
    if name == "E2":
        b, s = res["baseline"][0.10], res["bbse"][0.10]
        return (f"baseline a=0.10 hard_viol={b['hard_violation_rate']} "
                f"exceed={b['exceedance_rate']}; bbse decline_rate="
                f"{s['decline_rate']} hard_viol={s['hard_violation_rate']}")
    if name == "E3":
        return (f"verified_risk={res['verified_mean_answered_risk_alpha0.10']} "
                f">alpha={res['tilt_pushes_risk_above_alpha']}; "
                f"a=0.10 hard_viol={res[0.10]['hard_violation_rate']}")
    if name == "E4":
        g = {a: [d['certify_rate'] for d in res['grid'][a]] for a in ALPHA_LADDER}
        return f"certify-rate-by-nsites {res['sweep']}: 0.05={g[0.05]} 0.10={g[0.10]}"
    if name == "E5":
        return (f"tau*={res['tau_star']} answered={res['n_answered']} "
                f"declined={res['n_declined']} top_gap_feat={res['top_gap_feature']}")
    if name == "E6":
        return (f"tau*={res['tau_star']} "
                f"pred_pos_frac={res['predicted_positive_fraction']}")
    if name == "E7":
        a = res["arms"][E7_SU_ARM[0]]
        return (f"a=0.05 record certify={a[0.05]['record']['certify_rate']} "
                f"exceed={a[0.05]['record']['rm_exceed_rate']} vs site "
                f"certify={a[0.05]['site']['certify_rate']}; "
                f"a=0.10 record exceed={a[0.10]['record']['rm_exceed_rate']}")
    return ""


if __name__ == "__main__":
    main()
