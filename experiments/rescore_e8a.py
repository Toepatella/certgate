"""Rescore the comparator suite against the exact site-population R_M.

POST-HOC (2026-10-29). Nothing this file writes is a certified quantity, and
the released comparator arm (experiments/out/E8_comparators.csv, arm A of the
eighth experiment) is unchanged: it is read, never opened for writing.

Why. The released arm scores every certificate on one fresh 200-site pool
(Section 3.9's metric): a certificate counts as exceeding when the pool's
influence-weighted R_M is above alpha. That pool carries its own sampling
noise in R_M (sd about 0.0015 at this operating point), and the asymptotic
defaults -- the Student-t bound and the site bootstrap -- deploy thresholds
whose risk sits close to alpha, where symmetric noise carries more of them
across the budget than back under it. The fresh-pool rate therefore mixes the
bound's own miss with the pool's. The certificate names a parameter, and this
generator makes it computable, so this file scores each certificate against
it as well. Both scorings are reported side by side; the second is a second
estimand for the same certificates, not a correction of the first.

The parameter. The atom is Z_c = (g_c / (M n_c)) sum_i ans_i (err_i - alpha)
+ alpha with g_c = min(n_c, M), and E[Z] <= alpha exactly when
R_M = E[g a e] / E[g a] <= alpha. draw_cohort draws the site size n_c
independently of the site effect u_c, so E[g_c P(. | u_c)] = E[g] E_u[P(. | u)]
and the influence weights cancel:

    R_M = E_u[P_u(ans & err)] / E_u[P_u(ans)].

Both probabilities are linear in the site prevalence pi_u, so only its mean
pibar = E[sigmoid(logit 0.095 + 0.5 Z)] enters, taken by Gauss-Hermite
quadrature (probe_bbse_coverage.population_prevalence; 0.1036567). The head's
logit L = b + w.x, with w = coef / sd and b = intercept - w.mu_head, is
Gaussian within each class because x | y ~ N(mu_y, I): mean m_y = b + w.mu_y,
sd s = ||w||. With l = logit(tau) > 0 the head answers when |L| >= l and errs
when the sign of L disagrees with y, so

    R_M = [pibar Phi((-l - m1)/s) + (1 - pibar) Phi((m0 - l)/s)]
          / [pibar (Phi((m1 - l)/s) + Phi((-l - m1)/s))
             + (1 - pibar) (Phi((m0 - l)/s) + Phi((-l - m0)/s))].

What runs.
  1. Replay. Every arm-A draw is replayed on its frozen stream:
     _rng(8, 0, n_idx, r) -> _draw_split -> the 200-site eval pool with the
     prefix e8av{n_idx}_{r}, then the five walks of run_E8 in its own order,
     alpha = 0.05 before 0.10, so the site bootstrap consumes
     boot_rng = _rng(8, 0, n_idx, r, 1) exactly as E8 did. Every one of the
     12,000 frozen rows must replay its certified flag; every certified row
     (6,056) its deployed tau exactly, its coverage to four decimals, its
     rm_fresh to six and its rm_exceed flag. The pooled fresh-pool counts are
     pinned (Student-t 61, site bootstrap 59 of 1,200 at alpha = 0.05; zero
     elsewhere). Any miss aborts with nothing written.
  2. Rescore. Each certified row is scored against the closed form above.
     The pooled population counts are pinned too (Student-t 46, site
     bootstrap 45 of 1,200 at alpha = 0.05; zero elsewhere), so a drift in
     either the replay or the closed form refuses to write.
  3. Truth check. The closed form is checked against direct simulation at
     the pinned near-alpha row (60 sites, draw 199, Student-t, alpha = 0.05,
     tau 0.61) and at the certified Student-t and bootstrap rows at
     alpha = 0.05 whose population R_M sits closest to alpha: a record-level
     Monte Carlo (u -> y -> x | y, 20M records per row) and a fresh
     4,000-site draw_cohort pool scored by _rm_on_pool, each within five
     standard errors, or nothing is written. The truth-check streams are
     _rng(8, 90, k), an index family no experiment uses.

Run: python -m experiments.rescore_e8a [--out DIR]       (about 20 min)

Writes E8a_rescore.csv (one row per certified frozen row) and E8a_rescore.json
(pooled and per-site-count counts under both scorings with exact
Clopper-Pearson intervals, the concordance table with its exact McNemar test,
the fresh-minus-population residual, pibar, the self-check, _run with the
sha256 of the frozen input) into experiments/out-e8a-rescore/.

Refs: SPEC "E8" arm A; audit 2026-10 nominal-exceedance (Fix B).
"""

import argparse
import os
import sys
import time

import numpy as np
from scipy.stats import binomtest, norm

from certgate.certify import (certification_rng, fixed_sequence_walk,
                              influence_atoms, walk_order)
from certgate.constants import (ALPHA_LADDER, DELTA, M_INFLUENCE,
                                MODE_BASELINE, TAU_GRID)
from certgate.data import SimConfig, draw_cohort
from certgate.model import _sigmoid
from experiments.comparators import (hoeffding_ucb, mpeb_ucb,
                                     site_bootstrap_ucb, t_ucb)
from experiments.run_synthetic import (E1_EVAL_SITES, E8_BOOT, E8_COMPARATORS,
                                       FULL_SWEEP, _bound_walk, _draw_split,
                                       _rescore, _rm_on_pool, _rng, _write_csv)
from experiments.derive_fixpass_numbers import (EXP_DIR, assert_not_frozen,
                                                run_block, _read_csv)
from experiments.probe_bbse_coverage import population_prevalence
from experiments.run_eicu import _write_json

OUT_DIR = os.path.join(EXP_DIR, "out-e8a-rescore")
FROZEN = os.path.join(EXP_DIR, "out", "E8_comparators.csv")
R_DRAWS = 200

# Every released output directory, the released post-hoc sidecars included.
# derive_fixpass_numbers.FROZEN_DIRS covers every entry here.
FROZEN_DIRS_ALL = ("out", "out-panel", "out-sens", "out-subgroups",
                   "out-faithfulness", "out-rev2", "out-timing",
                   "out-settled", "out-derived", "out-e9a-rescore",
                   "out-e9b-positives", "out-bbse-probe")

PIBAR_PIN = (0.1036567, 7)
N_FROZEN_ROWS = 12_000
N_CERTIFIED_ROWS = 6_056
# (method, alpha) -> exceeding certificates, pooled over the six site counts.
# Fresh pool: what the frozen CSV says. Population: what the audit's two
# independent replays found. A miss on either refuses to write.
PINNED_FRESH = {("t", 0.05): 61, ("site_boot", 0.05): 59}
PINNED_POPULATION = {("t", 0.05): 46, ("site_boot", 0.05): 45}
# The near-alpha row the audit's Monte Carlo pinned: closed form 0.049944.
MC_PIN_ROW = dict(n_sites=60, draw=199, alpha=0.05, method="t", tau=0.61,
                  rm_population_6dp=0.049944)
MC_STREAM = (8, 90)                 # sidecar-only index family
MC_RECORDS = 20_000_000
MC_CHUNK = 2_000_000
MC_NEAREST = 8                      # near-alpha rows checked besides the pin
MC_POOL_SITES = 4_000
MC_Z_TOL = 5.0
NEAR_BAND = 0.003

POST_HOC = ("[MEASURE] POST-HOC (2026-10-29): replay of the released E8 "
            "comparator arm and rescoring of every certified row against the "
            "closed-form site-population R_M; the frozen CSV is unchanged "
            "and no certified quantity descends from this file. The "
            "population scoring is a second estimand for the same "
            "certificates, not a correction of the first.")

ESTIMAND_NOTE = (
    "rm_fresh is the released Section 3.9 metric: the certificate's "
    "influence-weighted R_M on one fresh 200-site pool, which carries that "
    "pool's sampling noise. rm_population is the parameter the certificate "
    "names, E[g a e] / E[g a] over the site population, in closed form: site "
    "size is drawn independently of the site effect, so the influence "
    "weights cancel and R_M = E_u[P_u(ans & err)] / E_u[P_u(ans)], linear in "
    "the site prevalence, evaluated at pibar = E[sigmoid(logit 0.095 + "
    "0.5 Z)] with the head's logit Gaussian within each class. An exceedance "
    "is R_M > alpha under either scoring.")

FIELDS = ["n_sites", "draw", "alpha", "method", "tau", "coverage",
          "rm_fresh", "rm_population", "rm_fresh_minus_population",
          "rm_exceed_fresh", "rm_exceed_population"]


# ------------------------------------------------------------ write guard

def assert_writable(path):
    """Refuse any write into a released or another sidecar's directory."""
    assert_not_frozen(path, own="out-e8a-rescore")
    target = os.path.normcase(os.path.abspath(path))
    for name in FROZEN_DIRS_ALL:
        frozen = os.path.normcase(os.path.join(EXP_DIR, name))
        if target == frozen or target.startswith(frozen + os.sep):
            raise SystemExit(
                f"refusing to write {path}: experiments/{name}/ is a released "
                f"output directory; this sidecar writes to its own "
                f"(reason=frozen-output-dir)")


# ------------------------------------------------------------ closed form

def pibar(cfg=None):
    """Population-mean site prevalence E[sigmoid(logit base + s_u Z)]."""
    cfg = cfg or SimConfig()
    return population_prevalence(cfg.base_rate, cfg.s_u)


def head_logit_moments(head, cfg=None):
    """(m0, m1, s): the head logit's class-conditional means and its sd.

    L = intercept + ((x - mu_head) / sd) . coef = b + w.x with w = coef / sd;
    x | y ~ N(mu_y, I) makes L | y ~ N(b + w.mu_y, ||w||^2).
    """
    cfg = cfg or SimConfig()
    w = np.asarray(head.coef, dtype=float) / np.asarray(head.sd, dtype=float)
    b = float(head.intercept - w @ np.asarray(head.mu, dtype=float))
    return (b + float(w @ cfg.mu(0)), b + float(w @ cfg.mu(1)),
            float(np.linalg.norm(w)))


def population_rm(head, tau, cfg=None, pi=None):
    """Closed-form site-population R_M of a head answering at score >= tau.

    The head answers when max(p, 1 - p) >= tau, i.e. |L| >= logit(tau), and
    errs when L < 0 on a positive or L >= 0 on a negative.
    """
    cfg = cfg or SimConfig()
    pi = pibar(cfg) if pi is None else pi
    m0, m1, s = head_logit_moments(head, cfg)
    l_thr = float(np.log(tau / (1.0 - tau)))
    ae1 = norm.cdf((-l_thr - m1) / s)          # answered and wrong | y = 1
    ae0 = norm.cdf((m0 - l_thr) / s)           # answered and wrong | y = 0
    a1 = norm.cdf((m1 - l_thr) / s) + ae1      # answered | y = 1
    a0 = ae0 + norm.cdf((-l_thr - m0) / s)     # answered | y = 0
    num = pi * ae1 + (1.0 - pi) * ae0
    den = pi * a1 + (1.0 - pi) * a0
    return float(num / den) if den > 0 else float("nan")


# ------------------------------------------------------------ truth checks

def mc_population_rm(head, tau, rng, n_records=MC_RECORDS, chunk=MC_CHUNK,
                     cfg=None):
    """Record-level Monte Carlo of the population R_M: u -> y -> x | y.

    Each record carries its own site effect, so the ratio of answered-error
    to answered counts converges to E_u[P_u(ans & err)] / E_u[P_u(ans)],
    the estimand the closed form evaluates. Returns (estimate, se) with the
    ratio's binomial standard error.
    """
    cfg = cfg or SimConfig()
    mu0, mu1 = cfg.mu(0), cfg.mu(1)
    base_logit = float(np.log(cfg.base_rate / (1.0 - cfg.base_rate)))
    num = den = 0
    left = int(n_records)
    while left > 0:
        k = min(chunk, left)
        left -= k
        u = rng.normal(0.0, cfg.s_u, k)
        y = rng.random(k) < _sigmoid(base_logit + u)
        x = rng.normal(0.0, 1.0, (k, cfg.d)) + np.where(y[:, None], mu1, mu0)
        ans = head.score(x) >= tau
        err = head.predict(x) != y
        num += int((ans & err).sum())
        den += int(ans.sum())
    r = num / den
    return r, float(np.sqrt(r * (1.0 - r) / den))


def pool_rm_se(head, pool, tau, M=M_INFLUENCE):
    """_rm_on_pool on a draw_cohort pool, with its delta-method site SE."""
    r = _rm_on_pool(head, pool, tau, M)
    ans = head.score(pool.x) >= tau
    err = head.predict(pool.x) != pool.y
    sizes = pool.site_sizes.astype(float)
    g_over_n = np.where(sizes > 0,
                        np.minimum(sizes, M) / np.maximum(sizes, 1.0), 0.0)
    num_c = g_over_n * np.bincount(pool.site_id, weights=(ans & err) * 1.0,
                                   minlength=pool.n_sites)
    den_c = g_over_n * np.bincount(pool.site_id, weights=ans * 1.0,
                                   minlength=pool.n_sites)
    k = pool.n_sites
    resid = num_c - r * den_c
    se = np.sqrt(k / (k - 1) * float((resid ** 2).sum())) / float(den_c.sum())
    return r, float(se)


# ------------------------------------------------------------ replay

def replay_draw(n_idx, r, cfg=None, n_boot=E8_BOOT):
    """Replay one E8 arm-A draw, call for call, on its frozen streams.

    Returns (head, evalp, rows) with one row per (alpha, method) in run_E8's
    order, carrying the deployed TAU_GRID index (dep) or None.
    """
    cfg = cfg or SimConfig()
    n_sites = FULL_SWEEP[n_idx]
    rng = _rng(8, 0, n_idx, r)
    _train, aux, cal, head = _draw_split(cfg, n_sites, rng)
    evalp = draw_cohort(cfg, E1_EVAL_SITES, rng,
                        site_label_prefix=f"e8av{n_idx}_{r}")
    sc_cal, er_cal = head.score(cal.x), head.predict(cal.x) != cal.y
    sc_aux, er_aux = head.score(aux.x), head.predict(aux.x) != aux.y
    boot_rng = _rng(8, 0, n_idx, r, 1)
    ucbs = {
        "hoeffding": hoeffding_ucb,
        "mpeb": mpeb_ucb,
        "t": t_ucb,
        "site_boot": lambda z, d: site_bootstrap_ucb(z, d, n_boot, boot_rng),
    }
    rows = []
    for alpha in ALPHA_LADDER:                   # 0.05 before 0.10, as E8
        a_aux = influence_atoms(sc_aux, er_aux, aux.site_id, aux.n_sites,
                                TAU_GRID, alpha, M_INFLUENCE)
        a_cal = influence_atoms(sc_cal, er_cal, cal.site_id, cal.n_sites,
                                TAU_GRID, alpha, M_INFLUENCE)
        order = walk_order(a_aux)
        for method in E8_COMPARATORS:
            if method == "wsr":
                _, dep = fixed_sequence_walk(
                    a_cal, order, alpha, DELTA, TAU_GRID,
                    rng=certification_rng(alpha, MODE_BASELINE, "e8-comp"))
            else:
                _, dep = _bound_walk(a_cal, order, alpha, DELTA, TAU_GRID,
                                     ucbs[method])
            rows.append(dict(n_sites=n_sites, draw=r, alpha=alpha,
                             method=method, dep=dep))
    return head, evalp, rows


def _frozen_index(frozen_rows):
    return {(int(x["n_sites"]), int(x["draw"]), float(x["alpha"]),
             x["method"]): x for x in frozen_rows}


def rescore(draws=None, frozen_path=FROZEN, log=print, cfg=None):
    """Replay, self-check and rescore.

    draws restricts the replay to a list of (n_idx, r) keys (the tests replay
    one); the pooled pins are then skipped. Returns (rows, check, heads),
    rows holding one dict per certified row, heads {(n_idx, r): head}.
    Raises SystemExit, writing nothing, on any mismatch.
    """
    cfg = cfg or SimConfig()
    pi = pibar(cfg)
    if round(pi, PIBAR_PIN[1]) != PIBAR_PIN[0]:
        raise SystemExit(f"rescore_e8a: pibar {pi!r} != {PIBAR_PIN[0]} to "
                         f"{PIBAR_PIN[1]} dp; nothing written "
                         f"(reason=self-check-failed)")
    frozen = _frozen_index(_read_csv(frozen_path))
    keys = ([(i, r) for i in range(len(FULL_SWEEP)) for r in range(R_DRAWS)]
            if draws is None else list(draws))
    rows, heads, mismatches = [], {}, []
    n_compared = 0
    t0 = time.perf_counter()
    for i, (n_idx, r) in enumerate(keys):
        head, evalp, rep = replay_draw(n_idx, r, cfg)
        heads[(n_idx, r)] = head
        for x in rep:
            fr = frozen[(x["n_sites"], x["draw"], x["alpha"], x["method"])]
            n_compared += 1
            certified = x["dep"] is not None
            if certified != (fr["certified"] == "True"):
                mismatches.append(dict(row=fr, replayed_dep=x["dep"]))
                continue
            if not certified:
                continue
            sc = _rescore(head, evalp, x["dep"], x["alpha"])
            tau = float(TAU_GRID[x["dep"]])
            ok = (sc["tau"] == float(fr["tau"])
                  and sc["coverage"] == round(float(fr["coverage"]), 4)
                  and sc["rm_fresh"] == round(float(fr["rm_fresh"]), 6)
                  and sc["rm_exceed"] == (fr["rm_exceed"] == "True"))
            if not ok:
                mismatches.append(dict(row=fr, replayed=sc))
                continue
            rm_pop = population_rm(head, tau, cfg, pi)
            rows.append(dict(
                n_sites=x["n_sites"], draw=r, alpha=x["alpha"],
                method=x["method"], tau=sc["tau"], coverage=sc["coverage"],
                rm_fresh=sc["rm_fresh"], rm_population=round(rm_pop, 8),
                rm_fresh_minus_population=round(sc["rm_fresh"] - rm_pop, 8),
                rm_exceed_fresh=sc["rm_exceed"],
                rm_exceed_population=bool(rm_pop > x["alpha"]),
                _tau_grid=tau, _n_idx=n_idx))
        if log and (i % 50 == 49 or i == len(keys) - 1):
            log(f"[certgate] e8a replay: {i + 1}/{len(keys)} draws "
                f"({time.perf_counter() - t0:.0f} s)")
    if mismatches:
        raise SystemExit(
            f"rescore_e8a: {len(mismatches)} frozen rows did not replay "
            f"(tau exact, coverage 4 dp, rm_fresh 6 dp, flags): "
            f"{mismatches[:3]} -- the frozen stream and the replay have "
            f"diverged; nothing written (reason=replay-mismatch)")
    check = dict(draws_replayed=len(keys), frozen_rows_compared=n_compared,
                 certified_rows_reproduced=len(rows), mismatches=0,
                 criteria="certified flag on every row; on every certified "
                          "row tau exactly, coverage to 4 dp, rm_fresh to "
                          "6 dp, rm_exceed flag")
    if draws is None:
        _check_pins(rows, n_compared)
        check.update(pinned_fresh=_pin_doc(PINNED_FRESH),
                     pinned_population=_pin_doc(PINNED_POPULATION),
                     pibar_pin=PIBAR_PIN[0])
    check["replay_wall_clock_s"] = round(time.perf_counter() - t0, 1)
    return rows, check, heads


def _pin_doc(pins):
    return {f"{m}|{a}": k for (m, a), k in pins.items()}


def _count(rows, method, alpha, key):
    return sum(1 for x in rows if x["method"] == method
               and x["alpha"] == alpha and x[key])


def _check_pins(rows, n_compared):
    problems = []
    if n_compared != N_FROZEN_ROWS:
        problems.append(f"compared {n_compared} rows, expected "
                        f"{N_FROZEN_ROWS}")
    if len(rows) != N_CERTIFIED_ROWS:
        problems.append(f"{len(rows)} certified rows, expected "
                        f"{N_CERTIFIED_ROWS}")
    for method in E8_COMPARATORS:
        for alpha in ALPHA_LADDER:
            for key, pins in (("rm_exceed_fresh", PINNED_FRESH),
                              ("rm_exceed_population", PINNED_POPULATION)):
                want = pins.get((method, alpha), 0)
                got = _count(rows, method, alpha, key)
                if got != want:
                    problems.append(f"{method} a={alpha} {key}: {got} != "
                                    f"{want}")
    if problems:
        raise SystemExit(f"rescore_e8a: pinned counts did not reproduce: "
                         f"{problems}; nothing written "
                         f"(reason=self-check-failed)")


def truth_check(rows, heads, cfg=None, n_records=MC_RECORDS,
                pool_sites=MC_POOL_SITES, n_nearest=MC_NEAREST, log=print):
    """Closed form against record-level MC and a fresh generator pool.

    Checks the pinned row and the n_nearest certified Student-t / bootstrap
    rows at alpha = 0.05 whose population R_M sits closest to alpha (one per
    distinct head and tau). Raises SystemExit if either simulation disagrees
    by more than MC_Z_TOL standard errors.
    """
    cfg = cfg or SimConfig()
    pin = next(x for x in rows
               if x["n_sites"] == MC_PIN_ROW["n_sites"]
               and x["draw"] == MC_PIN_ROW["draw"]
               and x["alpha"] == MC_PIN_ROW["alpha"]
               and x["method"] == MC_PIN_ROW["method"])
    if (pin["tau"] != MC_PIN_ROW["tau"]
            or round(pin["rm_population"], 6)
            != MC_PIN_ROW["rm_population_6dp"]):
        raise SystemExit(f"rescore_e8a: pinned near-alpha row {pin} does not "
                         f"reproduce {MC_PIN_ROW}; nothing written "
                         f"(reason=self-check-failed)")
    picks, seen = [pin], {(pin["_n_idx"], pin["draw"], pin["tau"])}
    near = sorted((x for x in rows if x["alpha"] == 0.05
                   and x["method"] in ("t", "site_boot")),
                  key=lambda x: abs(x["rm_population"] - x["alpha"]))
    for x in near:
        k = (x["_n_idx"], x["draw"], x["tau"])
        if k not in seen:
            seen.add(k)
            picks.append(x)
        if len(picks) > n_nearest:
            break
    pool = draw_cohort(cfg, pool_sites, _rng(*MC_STREAM, 0),
                       site_label_prefix="e8amc")
    out, bad = [], []
    for j, x in enumerate(picks):
        head = heads[(x["_n_idx"], x["draw"])]
        cf = population_rm(head, x["_tau_grid"], cfg)
        mc, mc_se = mc_population_rm(head, x["_tau_grid"],
                                     _rng(*MC_STREAM, 1, j), n_records,
                                     cfg=cfg)
        gp, gp_se = pool_rm_se(head, pool, x["_tau_grid"])
        z_mc, z_gp = (mc - cf) / mc_se, (gp - cf) / gp_se
        rec = dict(n_sites=x["n_sites"], draw=x["draw"], alpha=x["alpha"],
                   method=x["method"], tau=x["tau"],
                   rm_population=round(cf, 8),
                   record_mc=round(mc, 8), record_mc_se=round(mc_se, 8),
                   record_mc_z=round(z_mc, 3),
                   generator_pool=round(gp, 8),
                   generator_pool_se=round(gp_se, 8),
                   generator_pool_z=round(z_gp, 3),
                   rm_fresh=x["rm_fresh"])
        out.append(rec)
        if abs(z_mc) > MC_Z_TOL or abs(z_gp) > MC_Z_TOL:
            bad.append(rec)
        if log:
            log(f"[certgate] e8a truth check {j + 1}/{len(picks)}: closed "
                f"{cf:.6f} record-MC {mc:.6f} (z {z_mc:+.2f}) pool {gp:.6f} "
                f"(z {z_gp:+.2f})")
    if bad:
        raise SystemExit(f"rescore_e8a: closed-form R_M disagrees with "
                         f"simulation beyond {MC_Z_TOL} SE: {bad}; nothing "
                         f"written (reason=truth-check-failed)")
    return dict(records_per_row=int(n_records), pool_sites=int(pool_sites),
                pool_records=int(len(pool.y)), z_tolerance=MC_Z_TOL,
                streams=f"record MC _rng{MC_STREAM + (1, 'j')}; generator "
                        f"pool _rng{MC_STREAM + (0,)}",
                rows=out)


# ------------------------------------------------------------ summary

def exact_ci(k, n, dp=6):
    """Exact Clopper-Pearson 95% interval, or None over no draws."""
    if not n:
        return None
    ci = binomtest(int(k), int(n)).proportion_ci(confidence_level=0.95,
                                                 method="exact")
    return [round(float(ci.low), dp), round(float(ci.high), dp)]


def _cell(sub, n_draws):
    n_c = len(sub)
    kf = sum(x["rm_exceed_fresh"] for x in sub)
    kp = sum(x["rm_exceed_population"] for x in sub)
    both = sum(x["rm_exceed_fresh"] and x["rm_exceed_population"]
               for x in sub)
    f_only, p_only = kf - both, kp - both
    disc = f_only + p_only
    return dict(
        draws=n_draws, n_certified=n_c,
        fresh=dict(k=kf, n=n_c, rate=round(kf / n_c, 4) if n_c else None,
                   ci95=exact_ci(kf, n_c)),
        population=dict(k=kp, n=n_c, rate=round(kp / n_c, 4) if n_c else None,
                        ci95=exact_ci(kp, n_c)),
        exceed_both=both, fresh_only=f_only, population_only=p_only,
        mcnemar_exact_p=(round(float(binomtest(f_only, disc, 0.5).pvalue), 4)
                         if disc else None),
        max_rm_population=(round(max(x["rm_population"] for x in sub), 6)
                           if n_c else None))


def _residual(sub):
    d = np.array([x["rm_fresh_minus_population"] for x in sub])
    if len(d) < 2:
        return None
    return dict(n=int(len(d)), mean=round(float(d.mean()), 6),
                sd=round(float(d.std(ddof=1)), 6))


def summarise(rows, check, truth):
    sweep = list(FULL_SWEEP)
    counts = {}
    for method in E8_COMPARATORS:
        for alpha in ALPHA_LADDER:
            sub = [x for x in rows if x["method"] == method
                   and x["alpha"] == alpha]
            per = {str(n): _cell([x for x in sub if x["n_sites"] == n],
                                 R_DRAWS) for n in sweep}
            counts[f"{method}|{alpha}"] = dict(
                pooled=_cell(sub, R_DRAWS * len(sweep)), per_site_count=per)
    near = {}
    for method in ("t", "site_boot"):
        sub = [x for x in rows if x["method"] == method and x["alpha"] == 0.05]
        near[method] = dict(
            band=NEAR_BAND,
            population_below=sum(0.05 - NEAR_BAND <= x["rm_population"] < 0.05
                                 for x in sub),
            population_above=sum(0.05 <= x["rm_population"]
                                 < 0.05 + NEAR_BAND for x in sub),
            max_abs_gap_discordant=(round(max(
                (abs(x["rm_population"] - 0.05) for x in sub
                 if x["rm_exceed_fresh"] != x["rm_exceed_population"]),
                default=0.0), 6)))
    residual = dict(
        all_certified_rows=_residual(rows),
        per_site_count={str(n): _residual([x for x in rows
                                           if x["n_sites"] == n])
                        for n in sweep})
    t5, b5 = counts["t|0.05"]["pooled"], counts["site_boot|0.05"]["pooled"]
    headline = (
        f"a=0.05 pooled over {len(sweep)} site counts: Student-t "
        f"{t5['fresh']['k']}/{t5['n_certified']} on the fresh pool -> "
        f"{t5['population']['k']}/{t5['n_certified']} against the population "
        f"R_M (CI {t5['population']['ci95']}); site bootstrap "
        f"{b5['fresh']['k']} -> {b5['population']['k']} (CI "
        f"{b5['population']['ci95']}); WSR, MP-EB and Hoeffding 0 under both; "
        f"all {check['certified_rows_reproduced']} certified rows replayed "
        f"(tau exact, rm_fresh 6 dp)")
    return dict(post_hoc=POST_HOC, estimand=ESTIMAND_NOTE, headline=headline,
                pibar=round(pibar(), 8),
                closed_form=("R_M = [pibar Phi((-l-m1)/s) + (1-pibar) "
                             "Phi((m0-l)/s)] / [pibar (Phi((m1-l)/s) + "
                             "Phi((-l-m1)/s)) + (1-pibar) (Phi((m0-l)/s) + "
                             "Phi((-l-m0)/s))], l = logit(tau), w = coef/sd, "
                             "b = intercept - w.mu_head, m_y = b + w.mu_y, "
                             "s = ||w||"),
                self_check=check, truth_check=truth, counts=counts,
                near_alpha=near, fresh_minus_population=residual)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="replay the E8 arm-A comparators and rescore them "
                    "against the closed-form population R_M (post-hoc)")
    ap.add_argument("--out", default=OUT_DIR)
    args = ap.parse_args(argv)
    csv_path = os.path.join(args.out, "E8a_rescore.csv")
    json_path = os.path.join(args.out, "E8a_rescore.json")
    for p in (csv_path, json_path):
        assert_writable(p)
    t0 = time.perf_counter()
    rows, check, heads = rescore()
    truth = truth_check(rows, heads)
    doc = summarise(rows, check, truth)
    doc["wall_clock_s"] = round(time.perf_counter() - t0, 1)
    os.makedirs(args.out, exist_ok=True)
    _write_csv(csv_path, rows, FIELDS)
    _write_json(json_path, {"_run": run_block([FROZEN]), **doc},
                "rescore_e8a")
    print(f"[certgate] {doc['headline']}")
    print(f"[certgate] wrote {csv_path} and {json_path} "
          f"({doc['wall_clock_s']} s)", file=sys.stderr)
    return doc


if __name__ == "__main__":
    main()
