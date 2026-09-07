"""Coverage of the BBSE uncertainty box at the design's own auxiliary-site counts.

The label-shift mode's guarantee rests on a Bonferroni box over four
estimated parameters: the head's confusion rates c0 and c1 and the source
prevalence pi_s, each from a percentile cluster bootstrap over the auxiliary
sites, and the target predicted-positive rate q, from an exact
Clopper-Pearson interval when one site is declared. The three bootstraps are
asymptotic. The manuscript discloses a design-time probe that measured their
joint miscoverage at about twice the nominal budget, but the probe's
configuration, seeds and numbers were never put on the record, and the
pointer to them was circular. This file is that probe, re-run so the record
exists.

The head is held fixed: one 208-site cohort is drawn and split on a stream
of its own, the head fitted once, and its population confusion rates
computed in closed form. Under the class-conditional Gaussian generator the
head's decision logit is Gaussian within each class, so c_y = Phi(m_y / s)
with m_y the class-conditional mean logit and s its standard deviation; a
Monte-Carlo check on 200,000 records per class must agree to 0.004 or the
probe refuses to run. The population source prevalence and the population
target prevalence at the registered shift are integrals of the sigmoid over
the site random effect, taken by Gauss-Hermite quadrature.

Each fit then draws a fresh auxiliary cohort of n_aux sites and one declared
target site at the registered shift. The target site's random effect is drawn
in the open, so its true prevalence pi_t is known exactly, and the site is
generated with that prevalence and no further effect. fit_bbse runs exactly
as the pipeline runs it, seeded from the target bytes. Coverage is scored
parameter by parameter against the truths above, jointly over the three
bootstrap parameters and over all four, and for the propagated odds-ratio
interval against two truths: the declared site's odds ratio (what the box was
fitted to) and the population's (what a fresh pool at the shift realises).
The decline rate and its reasons, the interval widths and the point estimate
travel with them.

The implied certificate level follows the panel's decomposition. The
certificate spends delta_bet = 0.025 on the betting test and delta_conf =
0.025 on the box; if the box misses more often than its budget, the
guarantee's level is 1 minus (measured box miss plus delta_bet), and the
manuscript should say so rather than print 0.95. Two versions are reported:
the measured miss rate of the four-parameter box, and the panel's own sum
(three-parameter miss plus the q share plus delta_bet). Both come with the
exact interval of a 400-fit estimate, because part of any shortfall here is
resolution: each percentile endpoint sits at the 0.3125% tail of 2,000
resamples, about six draws, and BBSE_BOOT is a frozen constant this file
reads and never changes.

Run: python -m experiments.probe_bbse_coverage [--fits 400]
        [--n-aux 36,42,74] [--out DIR]

Writes BBSE_probe.csv and BBSE_probe.json into experiments/out-bbse-probe/.
The JSON carries a _run block (UTC, git sha; the probe reads no frozen file).

Refs: SPEC "shift.py"; METHODS 5 (the disclosure); fix-pass plan WP2; panel
action item 19.
"""

import argparse
import dataclasses
import os
import sys
import time

import numpy as np
from scipy.stats import norm

from certgate.constants import (BBSE_BONFERRONI, BBSE_BOOT, BBSE_DELTA_BET,
                                BBSE_DELTA_CONF, DELTA, PI_CLIP)
from certgate.data import SimConfig, draw_cohort, split_sites
from certgate.model import fit_head, _sigmoid
from certgate.pipeline import _bbse_seed_rng
from certgate.shift import fit_bbse
from experiments.run_synthetic import (ANCHOR_SITES, SHIFT_BASE, _rng,
                                       _rate_ci95, _write_csv)
from experiments.derive_fixpass_numbers import (EXP_DIR, assert_not_frozen,
                                                run_block)
from experiments.run_eicu import _write_json

OUT_DIR = os.path.join(EXP_DIR, "out-bbse-probe")
N_AUX_SWEEP = (36, 42, 74)                  # eICU S_aux at 190/207 sites; 208 x 0.2; eICU S_cal
N_FITS = 400
STREAM_HEAD = (9, 2)                        # arm index 2 of the E9 family: unused by run_synthetic
STREAM_FIT = (9, 2, 1)
MC_RECORDS = 200_000
MC_TOL = 0.004
LVL = BBSE_DELTA_CONF / BBSE_BONFERRONI     # per-parameter two-sided level, 0.00625
NOMINAL = dict(per_parameter=1.0 - LVL,
               joint_three_bootstrap=1.0 - 3 * LVL,
               joint_four=1.0 - BBSE_DELTA_CONF,
               certificate=1.0 - DELTA)
PARAMS = ("c0", "c1", "pi_s", "q")
CLIP_BOUND_RHO = 100.0                      # rho_hi beyond this: the PI_CLIP corner bound it

POST_HOC = ("[MEASURE] POST-HOC (2026-09-04): coverage probe of the BBSE "
            "uncertainty box with the head held fixed; a diagnostic of the "
            "asymptotic bootstrap intervals at the design's own site counts. "
            "No certified quantity descends from it and BBSE_BOOT is read, "
            "never changed.")


def _logit(p):
    return np.log(p / (1.0 - p))


def _odds(p):
    return p / (1.0 - p)


def _expect_over_site_effect(f, s_u, n_nodes=200):
    """E[f(u)] for u ~ N(0, s_u^2), by probabilists' Gauss-Hermite."""
    x, w = np.polynomial.hermite_e.hermegauss(n_nodes)
    return float((w * f(s_u * x)).sum() / np.sqrt(2.0 * np.pi))


def population_prevalence(base, s_u):
    """The record-pooled prevalence over i.i.d. sites: E_u sigmoid(logit(base) + u).

    Site sizes are independent of the random effect, so the pooled positive
    share converges to this, which is the estimand of BBSE's pi_s.
    """
    return _expect_over_site_effect(lambda u: _sigmoid(_logit(base) + u), s_u)


def head_confusion_rates(head, cfg):
    """(c0, c1) = (P(yhat=1 | y=0), P(yhat=1 | y=1)) for a fixed head.

    x | y ~ N(mu_y, I), so the decision logit intercept + a . (x - mu_head)
    with a = coef / sd is Gaussian with mean m_y = intercept + a . (mu_y -
    mu_head) and sd ||a||; yhat = 1 iff the logit is >= 0.
    """
    a = head.coef / head.sd
    s = float(np.linalg.norm(a))
    m0 = float(head.intercept + a @ (cfg.mu(0) - head.mu))
    m1 = float(head.intercept + a @ (cfg.mu(1) - head.mu))
    return float(norm.cdf(m0 / s)), float(norm.cdf(m1 / s))


def _mc_confusion_rates(head, cfg, rng, n=MC_RECORDS):
    out = []
    for y in (0, 1):
        x = rng.normal(0.0, 1.0, (n, cfg.d)) + cfg.mu(y)
        out.append(float(head.predict(x).mean()))
    return tuple(out)


def fixed_head(cfg=None):
    """One 208-site cohort on the probe's own stream; the head fitted once."""
    cfg = cfg or SimConfig()
    rng = _rng(*STREAM_HEAD)
    coh = draw_cohort(cfg, ANCHOR_SITES, rng)
    train, _, _ = split_sites(coh, rng)
    head = fit_head(train)
    c0, c1 = head_confusion_rates(head, cfg)
    mc0, mc1 = _mc_confusion_rates(head, cfg, _rng(*STREAM_HEAD, 99))
    if abs(c0 - mc0) > MC_TOL or abs(c1 - mc1) > MC_TOL:
        raise SystemExit(
            f"probe_bbse_coverage: closed-form confusion rates ({c0:.4f}, "
            f"{c1:.4f}) disagree with Monte Carlo ({mc0:.4f}, {mc1:.4f}) "
            f"beyond {MC_TOL}; refusing to score coverage against them "
            f"(reason=truth-check-failed)")
    truth = dict(c0=c0, c1=c1, c0_mc=mc0, c1_mc=mc1,
                 pi_s=population_prevalence(cfg.base_rate, cfg.s_u),
                 pi_pop_target=population_prevalence(SHIFT_BASE, cfg.s_u),
                 head_train_sites=train.n_sites, head_train_records=train.n)
    truth["rho_pop"] = _odds(truth["pi_pop_target"]) / _odds(truth["pi_s"])
    return head, truth


def _covers(ci, value):
    return None if ci is None else bool(ci[0] <= value <= ci[1])


def probe_fit(head, truth, n_aux, rep, cfg=None):
    """One fit: fresh S_aux of n_aux sites, one declared target site."""
    cfg = cfg or SimConfig()
    rng = _rng(*STREAM_FIT, n_aux, rep)
    aux = draw_cohort(cfg, n_aux, rng, site_label_prefix=f"bp{n_aux}_{rep}a")
    u_t = float(rng.normal(0.0, cfg.s_u))
    pi_t = float(_sigmoid(_logit(SHIFT_BASE) + u_t))
    cfg0 = dataclasses.replace(cfg, s_u=0.0)     # the effect is already in pi_t
    tgt = draw_cohort(cfg0, 1, rng, label_base_rate=pi_t,
                      site_label_prefix=f"bp{n_aux}_{rep}t",
                      require_both_classes=False)
    fit = fit_bbse(head, aux, tgt.x, _bbse_seed_rng(tgt.x, None),
                   target_site_id=None)
    d = fit.diagnostics
    q_true = truth["c0"] * (1.0 - pi_t) + truth["c1"] * pi_t
    rho_site = _odds(pi_t) / _odds(truth["pi_s"])
    cis = dict(c0=d["c0_ci"], c1=d["c1_ci"], pi_s=d["pi_s_ci"], q=d["q_ci"])
    values = dict(c0=truth["c0"], c1=truth["c1"], pi_s=truth["pi_s"],
                  q=q_true)
    cov = {p: _covers(cis[p], values[p]) for p in PARAMS}
    box_exists = all(cis[p] is not None for p in PARAMS)
    joint3 = (all(cov[p] for p in ("c0", "c1", "pi_s")) if box_exists
              else None)
    joint4 = all(cov.values()) if box_exists else None
    row = dict(n_aux=n_aux, rep=rep, n_target=tgt.n,
               n_target_positive=int(tgt.y.sum()),
               declined=bool(fit.declined), reason=fit.reason or None,
               box_exists=box_exists, pi_t_site=round(pi_t, 6),
               q_true=round(q_true, 6), rho_site=round(rho_site, 6),
               q_hat=(None if d["q_target"] is None
                      else round(float(d["q_target"]), 6)),
               gap_lo=(None if d["gap_lo"] is None
                       else round(float(d["gap_lo"]), 6)),
               n_boot=d["n_boot"], n_attempts=d["n_attempts"])
    for p in PARAMS:
        ci = cis[p]
        row[f"{p}_lo"] = None if ci is None else round(float(ci[0]), 6)
        row[f"{p}_hi"] = None if ci is None else round(float(ci[1]), 6)
        row[f"covers_{p}"] = cov[p]
    row.update(covers_joint3=joint3, covers_joint4=joint4)
    if fit.declined:
        row.update(rho_lo=None, rho_hi=None, rho_point=None, box_width=None,
                   covers_rho_site=None, covers_rho_pop=None)
    else:
        row.update(rho_lo=round(fit.rho_lo, 6), rho_hi=round(fit.rho_hi, 6),
                   rho_point=round(fit.rho_point, 6),
                   box_width=round(fit.rho_hi - fit.rho_lo, 6),
                   covers_rho_site=bool(fit.rho_lo <= rho_site <= fit.rho_hi),
                   covers_rho_pop=bool(fit.rho_lo <= truth["rho_pop"]
                                       <= fit.rho_hi))
    return row


def _rate(rows, key):
    vals = [r[key] for r in rows if r[key] is not None]
    k, n = sum(vals), len(vals)
    return dict(k=int(k), n=n, rate=(round(k / n, 4) if n else None),
                ci95=_rate_ci95(k, n), miss=(round(1.0 - k / n, 4) if n
                                              else None),
                miss_ci95=(None if not n else
                           [round(1.0 - c, 4) for c in
                            reversed(_rate_ci95(k, n))]))


def summarise_cell(rows):
    fitted = [r for r in rows if not r["declined"]]
    boxed = [r for r in rows if r["box_exists"]]
    reasons = {}
    for r in rows:
        if r["declined"]:
            reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
    cov_boxed = {p: _rate(boxed, f"covers_{p}") for p in PARAMS}
    cov_boxed["joint_three_bootstrap"] = _rate(boxed, "covers_joint3")
    cov_boxed["joint_four"] = _rate(boxed, "covers_joint4")
    cov_fit = {p: _rate(fitted, f"covers_{p}") for p in PARAMS}
    cov_fit["joint_three_bootstrap"] = _rate(fitted, "covers_joint3")
    cov_fit["joint_four"] = _rate(fitted, "covers_joint4")
    cov_fit["rho_declared_site"] = _rate(fitted, "covers_rho_site")
    cov_fit["rho_population"] = _rate(fitted, "covers_rho_pop")
    widths = [r["box_width"] for r in fitted]
    # A rho_hi in the hundreds or beyond means the q interval reached the
    # box's c1 edge and the pi_t clip at 1 - PI_CLIP bound the corner: the
    # interval is then wide rather than wrong, and the mean width follows it.
    clip_bound = sum(1 for r in fitted if r["rho_hi"] > CLIP_BOUND_RHO)
    miss4 = cov_fit["joint_four"]["miss"]
    miss3 = cov_fit["joint_three_bootstrap"]["miss"]
    miss4_hi = (cov_fit["joint_four"]["miss_ci95"] or [None, None])[1]
    implied = None
    if miss4 is not None:
        implied = dict(
            measured_four_parameter=round(1.0 - (miss4 + BBSE_DELTA_BET), 4),
            panel_decomposition_three_plus_q_share=round(
                1.0 - (miss3 + LVL + BBSE_DELTA_BET), 4),
            conservative_ci_upper=round(1.0 - (miss4_hi + BBSE_DELTA_BET), 4),
            formula=("1 - (box miss + delta_bet); the panel's version "
                     "replaces the four-parameter miss by the three-bootstrap "
                     "miss plus the q share delta_conf/4"))
    return dict(
        n_fits=len(rows), n_fitted=len(fitted), n_with_box=len(boxed),
        decline=dict(k=len(rows) - len(fitted), n=len(rows),
                     rate=round((len(rows) - len(fitted)) / len(rows), 4),
                     reasons=reasons),
        coverage_among_fits_with_a_box=cov_boxed,
        coverage_among_certifiable_fits=cov_fit,
        box_width_rho=(dict(mean=round(float(np.mean(widths)), 4),
                            median=round(float(np.median(widths)), 4),
                            min=round(float(np.min(widths)), 4),
                            max=round(float(np.max(widths)), 4),
                            n_clip_bound=clip_bound,
                            mean_excluding_clip_bound=round(float(np.mean(
                                [w for w, r in zip(widths, fitted)
                                 if r["rho_hi"] <= CLIP_BOUND_RHO])), 4)
                            if clip_bound < len(widths) else None)
                       if widths else None),
        mean_rho_point=(round(float(np.mean([r["rho_point"]
                                             for r in fitted])), 4)
                        if fitted else None),
        mean_pi_t_site=round(float(np.mean([r["pi_t_site"] for r in rows])),
                             4),
        implied_certificate_level=implied)


def run(n_aux_sweep=N_AUX_SWEEP, n_fits=N_FITS, log=print):
    t0 = time.perf_counter()
    head, truth = fixed_head()
    rows = []
    for n_aux in n_aux_sweep:
        for rep in range(n_fits):
            rows.append(probe_fit(head, truth, n_aux, rep))
        if log:
            log(f"[certgate] bbse probe: n_aux={n_aux} done "
                f"({time.perf_counter() - t0:.0f} s)")
    cells = {str(n): summarise_cell([r for r in rows if r["n_aux"] == n])
             for n in n_aux_sweep}
    pooled = summarise_cell(rows)
    mc_note = (f"each percentile endpoint sits at the {LVL / 2:.5f} tail of "
               f"BBSE_BOOT = {BBSE_BOOT} resamples, i.e. about "
               f"{BBSE_BOOT * LVL / 2:.2f} tail draws; part of any shortfall "
               f"below the nominal {NOMINAL['per_parameter']:.5f} per "
               f"parameter is Monte-Carlo resolution of that quantile, and "
               f"a larger BBSE_BOOT is a frozen-constant change deferred to "
               f"after submission")
    parts = []
    for n in n_aux_sweep:
        c = cells[str(n)]["coverage_among_certifiable_fits"]
        lvl = cells[str(n)]["implied_certificate_level"]
        parts.append(
            f"n_aux={n}: decline {cells[str(n)]['decline']['rate']}, "
            f"box4 miss {c['joint_four']['miss']} "
            f"(box3 {c['joint_three_bootstrap']['miss']}), rho covers site "
            f"{c['rho_declared_site']['rate']} / pop "
            f"{c['rho_population']['rate']}, implied level "
            f"{lvl['measured_four_parameter'] if lvl else None}")
    headline = "; ".join(parts)
    doc = dict(post_hoc=POST_HOC, headline=headline,
               config=dict(n_aux_sweep=list(n_aux_sweep), fits_per_n_aux=n_fits,
                           target="one declared site at the registered "
                                  f"shift (base rate {SHIFT_BASE}), its "
                                  "random effect drawn in the open",
                           head_stream=list(STREAM_HEAD),
                           fit_stream_prefix=list(STREAM_FIT),
                           bbse_boot=BBSE_BOOT, bonferroni=BBSE_BONFERRONI,
                           per_parameter_level=LVL,
                           delta_conf=BBSE_DELTA_CONF,
                           delta_bet=BBSE_DELTA_BET),
               truth={k: (round(v, 6) if isinstance(v, float) else v)
                      for k, v in truth.items()},
               nominal=NOMINAL, cells=cells, pooled_over_n_aux=pooled,
               clip=dict(pi_clip=PI_CLIP, rho_hi_clip_bound_above=CLIP_BOUND_RHO,
                         note="the pi_t clip costs width, not coverage: the "
                              "unclipped odds ratio stays covered whenever the "
                              "true pi_t lies inside [PI_CLIP, 1 - PI_CLIP]"),
               monte_carlo_resolution=mc_note,
               wall_clock_s=round(time.perf_counter() - t0, 1))
    return rows, doc


FIELDS = (["n_aux", "rep", "n_target", "n_target_positive", "declined",
           "reason", "box_exists", "pi_t_site", "q_true", "rho_site", "q_hat",
           "gap_lo", "n_boot", "n_attempts"]
          + [f"{p}_{s}" for p in PARAMS for s in ("lo", "hi")]
          + [f"covers_{p}" for p in PARAMS]
          + ["covers_joint3", "covers_joint4", "rho_lo", "rho_hi",
             "rho_point", "box_width", "covers_rho_site", "covers_rho_pop"])


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="coverage probe of the BBSE box, head held fixed")
    ap.add_argument("--fits", type=int, default=N_FITS)
    ap.add_argument("--n-aux", default=",".join(map(str, N_AUX_SWEEP)))
    ap.add_argument("--out", default=OUT_DIR)
    args = ap.parse_args(argv)
    sweep = tuple(int(s) for s in args.n_aux.split(",") if s.strip())
    csv_path = os.path.join(args.out, "BBSE_probe.csv")
    json_path = os.path.join(args.out, "BBSE_probe.json")
    for p in (csv_path, json_path):
        assert_not_frozen(p)
    rows, doc = run(sweep, args.fits)
    os.makedirs(args.out, exist_ok=True)
    _write_csv(csv_path, rows, FIELDS)
    _write_json(json_path, {"_run": run_block([]), **doc},
                "probe_bbse_coverage")
    print(f"[certgate] {doc['headline']}")
    print(f"[certgate] wrote {csv_path} and {json_path} "
          f"({doc['wall_clock_s']} s)", file=sys.stderr)
    return doc


if __name__ == "__main__":
    main()
