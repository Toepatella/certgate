"""The E9 certificates scored against their named estimands in closed form.

Status: POST-HOC (2026-10-29). A read-only replay of two released E9 arms;
nothing frozen is regenerated and no certified quantity descends from this
file. Audits FNR-1, FNR-5, FNR-6 (verdicts "e9-narrative" and
"estimand-equivalence", 2026-10).

Why a closed form exists. On the synthetic generator (certgate/data.py) the
class-conditional feature law is the same at every site, x | y ~ N(mu_y, I),
and only the site's prevalence moves. A fitted head's decision logit
z = intercept + a . (x - mu_head), a = coef / sd, is therefore Gaussian
within each class, with mean m_y = intercept + a . (mu_y - mu_head) and sd
s = ||a||. A record answers at tau when |z| >= L = logit(tau) and is wrong
when y = 1 with z < 0 or y = 0 with z >= 0, so per class

    e1 = Phi((-L - m1) / s)     a1 = e1 + Phibar((L - m1) / s)
    e0 = Phibar((L - m0) / s)   a0 = e0 + Phi((-L - m0) / s)

are the answered-and-wrong and answered probabilities. Site sizes are drawn
independently of the site effect, so the site weights cancel from every
ratio-of-expectations estimand below and each reduces to these four numbers.

(a) Arm A, single declared site (experiments/out/E9_bbse_frontier.csv,
target_mode single-site-cp; 44 certificates over 40 draws). The single-site
BBSE box takes an exact Clopper-Pearson interval for the declared site's own
predicted-positive probability, so the certificate names R_M reweighted to
that site's LATENT prevalence pi_t* = sigmoid(logit 0.22 + u_t), with
rho* = odds(pi_t*) / odds(pi_s) and pi_s = E_u sigmoid(logit 0.095 + u), the
source mix the cluster bootstrap estimates. The named estimand is exactly

    R(pi_t*) = [pi_t* e1 + (1 - pi_t*) e0] / [pi_t* a1 + (1 - pi_t*) a0]

at the deployed tau. u_t is read from a deep copy of the draw's generator
taken just before the target site is drawn: draw_cohort(cfg, 1, ...) spends
one normal on the size and one on u_t, in that order, and the copy's size
must equal the target pool's record count. The released out-e9a-rescore/
column rm_rescored reweights the fresh pool to the declared pool's REALISED
prevalence instead, a plug-in proxy; both are reported side by side, with
R at the realised prevalence and at the population target prevalence
(0.23126) beside them, and whether the frozen box covers rho* and the
population parameter rho_pop = 2.601345 (out-bbse-probe truth).

(b) Arm B, the false-negative frontier (experiments/out/E9_fnr.csv, the
shipped atom, and experiments/out-e9b-positives/, the positives-normalised
atom; 600 draws, 2,428 certificates). Both estimands equal the head's
answered false-negative rate among positives on this generator,
FNR(tau) = e1 / a1 = p_fn / p_ap (audit FNR-5), so every issued certificate
is scored at its deployed tau, the event Ville's inequality bounds --
certifying while FNR(tau*) exceeds the budget -- is counted directly, and
for every draw the curve over TAU_GRID says whether 0.4 is below the
estimand at some grid threshold.

Self-check (refuse to write). Before anything is written:
  - arm A: each replayed draw rebuilds its E9_bbse_frontier.csv rows exactly
    as run_E9 does (pipeline in bbse mode, then the fresh pool) and must
    equal the frozen CSV cell for cell at every alpha -- certified flag,
    tau, coverage, decline reason, rho_lo and rho_hi to the last digit, box
    width, rm_fresh, rm_exceed; each certified row must also reproduce
    out-e9a-rescore/E9a_rescore.csv's pi_target, pi_eval, pi_source and
    rm_rescored to six decimals, and the three rows rescore_e9a pins as
    exceeding must replay to its four;
  - arm B: run_e9b_positives.run_draw replays both arms' walks on every
    draw and must equal out-e9b-positives/E9b_fnr_positives.csv cell for
    cell, the shipped arm also out/E9_fnr.csv; the head scored here is
    re-fitted on the same stream and must reproduce each row's fresh-pool
    values (true_fnr_at_lowest_tau under both normalisations and every
    certificate's fnr_fresh) exactly;
  - the closed form against Monte Carlo: for every arm-A certificate and
    for the six positives-atom certificates at b = 0.4, MC_RECORDS
    simulated records per class must agree with the closed form to MC_TOL;
  - the population parameters must equal out-bbse-probe/BBSE_probe.json's
    truth (pi_s, pi_pop_target, rho_pop) to six decimals.
Any mismatch raises SystemExit and nothing is written.

Seeding. Every replay runs on the replayed experiment's own stream:
_rng(9, 0, n_idx, m_idx, r) for arm A (m_idx = 0, single-site-cp) and
_rng(9, 1, n_idx, r) for arm B, both from the protocol SEED. The Monte
Carlo checks draw from the same parts with MC_STREAM_TAG appended,
_rng(9, 0, n_idx, 0, r, 99) and _rng(9, 1, n_idx, r, 99), a longer entropy
list than any stream the experiment itself uses.

Inputs (read only, sha256 in the JSON's _run block):
experiments/out/E9_bbse_frontier.csv, experiments/out/E9_fnr.csv,
experiments/out-e9a-rescore/E9a_rescore.csv,
experiments/out-e9b-positives/E9b_fnr_positives.csv,
experiments/out-bbse-probe/BBSE_probe.json.

Run: python -m experiments.rescore_e9_exact [--out DIR]

Writes E9_exact.csv (one row per certificate: arm A's 44, arm B's 2,428)
and E9_exact.json (summaries, the flagged rows, the per-draw arm-B curves,
the self-check block, _run) into experiments/out-e9-exact/. About 25
minutes, almost all of it the arm-B walk replay.
"""

import argparse
import copy
import os
import sys
import time

import numpy as np
from scipy.stats import norm

from certgate.constants import ALPHA_LADDER, TAU_GRID
from certgate.data import SimConfig, draw_cohort, split_sites
from certgate.model import fit_head, _sigmoid
from certgate.pipeline import run_certgate
from experiments import run_e9b_positives as e9b
from experiments.derive_fixpass_numbers import (EXP_DIR, assert_not_frozen,
                                                run_block, _read_csv,
                                                _read_json)
from experiments.probe_bbse_coverage import population_prevalence
from experiments.rescore_e9a import EXCEEDING_ROWS, _rm_reweighted
from experiments.run_eicu import _write_json
from experiments.run_synthetic import (E1_EVAL_SITES, E9_FNR_LADDER,
                                       E9_FNR_R, E9_FNR_SWEEP,
                                       E9_SOURCE_SWEEP, E9_TARGET_MODES,
                                       SHIFT_BASE, _draw_split, _fnr_on_pool,
                                       _rescore, _rng, _row_for, _write_csv)

OUT_DIR = os.path.join(EXP_DIR, "out-e9-exact")
FROZEN_A = os.path.join(EXP_DIR, "out", "E9_bbse_frontier.csv")
FROZEN_B = os.path.join(EXP_DIR, "out", "E9_fnr.csv")
RELEASED_A = os.path.join(EXP_DIR, "out-e9a-rescore", "E9a_rescore.csv")
RELEASED_B = os.path.join(EXP_DIR, "out-e9b-positives",
                          "E9b_fnr_positives.csv")
PROBE_JSON = os.path.join(EXP_DIR, "out-bbse-probe", "BBSE_probe.json")
INPUTS = (FROZEN_A, FROZEN_B, RELEASED_A, RELEASED_B, PROBE_JSON)

# Every released output directory, the earlier post-hoc sidecars included.
# derive_fixpass_numbers.FROZEN_DIRS covers every entry here except
# out-derived-r2, a released sidecar this file reads and must never write into.
RELEASED_DIRS = ("out", "out-panel", "out-sens", "out-subgroups",
                 "out-faithfulness", "out-rev2", "out-timing", "out-settled",
                 "out-derived", "out-derived-r2", "out-e9a-rescore",
                 "out-e9b-positives", "out-bbse-probe")

SINGLE_SITE = "single-site-cp"
M_IDX_SINGLE = E9_TARGET_MODES.index(SINGLE_SITE)
FROZEN_A_FIELDS = ("certified", "tau", "coverage", "decline_reason", "rho_lo",
                   "rho_hi", "box_width", "rm_fresh", "rm_exceed")
RELEASED_A_6DP = ("pi_target", "pi_eval", "pi_source", "rm_fresh_replayed",
                  "rm_rescored")
B_FIELDS = tuple(f for f in e9b.FIELDS if f != "arm")
FNR_CONTROL = 0.4                           # the E9_FNR_LADDER rung audited
MC_RECORDS = 1_000_000                      # simulated records per class
MC_TOL = 0.003
MC_STREAM_TAG = 99

POST_HOC = ("[MEASURE] POST-HOC (2026-10-29): closed-form named estimands "
            "for the released E9 certificates, on the generator's "
            "site-invariant P(x|y); a read-only replay that reproduces the "
            "released rows before scoring them. Nothing frozen moves and no "
            "certified quantity descends from this file.")

ESTIMAND_NOTE = (
    "arm A: R(pi) = [pi e1 + (1-pi) e0] / [pi a1 + (1-pi) a0] from the "
    "head's class-conditional answered-and-wrong (e_y) and answered (a_y) "
    "probabilities at the deployed tau; r_named_exact at the declared site's "
    "latent prevalence pi_latent = sigmoid(logit 0.22 + u_t), the estimand a "
    "single-site certificate names; r_at_realised at the declared pool's "
    "realised prevalence (what released rm_rescored estimates on the fresh "
    "pool); r_at_population at the population target prevalence 0.23126 "
    "(what released rm_fresh estimates). rho_star = odds(pi_latent) / "
    "odds(pi_s), pi_s = 0.103657. arm B: fnr_exact = e1 / a1 = p_fn / p_ap, "
    "the value of both FNR_M and FNR_M^+ on this generator.")


# ----------------------------------------------------------------- helpers

def _assert_writable(path):
    """Refuse any write into a released or another sidecar's directory."""
    assert_not_frozen(path, own="out-e9-exact")
    target = os.path.normcase(os.path.abspath(path))
    for name in RELEASED_DIRS:
        frozen = os.path.normcase(os.path.join(EXP_DIR, name))
        if target == frozen or target.startswith(frozen + os.sep):
            raise SystemExit(
                f"refusing to write {path}: experiments/{name}/ is a released "
                f"output directory; this sidecar writes only to its own "
                f"(reason=frozen-output-dir)")


def _odds(p):
    return p / (1.0 - p)


def _logit(p):
    return np.log(p / (1.0 - p))


def _cell(v):
    """A value as csv.DictWriter rendered it in the released CSVs."""
    return "" if v is None else str(v)


def _snap(tau):
    """The deployed TAU_GRID index for a tau printed at 4 dp."""
    return int(np.argmin(np.abs(TAU_GRID - float(tau))))


def _r6(v):
    return None if v is None else round(float(v), 6)


def class_rates(head, cfg, taus):
    """(e0, a0, e1, a1) at each tau, in closed form for a fixed head.

    e_y = P(answered and wrong | y), a_y = P(answered | y) at the site-free
    class-conditional law x | y ~ N(mu_y, I) (see the module docstring).
    """
    a = head.coef / head.sd
    s = float(np.linalg.norm(a))
    m0 = float(head.intercept + a @ (cfg.mu(0) - head.mu))
    m1 = float(head.intercept + a @ (cfg.mu(1) - head.mu))
    L = _logit(np.asarray(taus, dtype=np.float64))
    e1 = norm.cdf((-L - m1) / s)
    a1 = e1 + norm.sf((L - m1) / s)
    e0 = norm.sf((L - m0) / s)
    a0 = e0 + norm.cdf((-L - m0) / s)
    return e0, a0, e1, a1


def positive_logit_mean(head, cfg):
    """m1, the head's mean decision logit on positives; FNR(tau) falls in
    tau exactly when m1 > 0 (inverse-Mills argument, audit FNR-1)."""
    a = head.coef / head.sd
    return float(head.intercept + a @ (cfg.mu(1) - head.mu))


def answered_risk(rates, pi):
    """R(pi), the answered error at class prevalence pi."""
    e0, a0, e1, a1 = rates
    return (pi * e1 + (1.0 - pi) * e0) / (pi * a1 + (1.0 - pi) * a0)


def fnr_exact(rates):
    """FNR(tau) = p_fn / p_ap, both estimands' value on this generator."""
    _, _, e1, a1 = rates
    return e1 / a1


def mc_class_rates(head, cfg, tau, rng, n=MC_RECORDS):
    """Monte-Carlo twin of class_rates at one tau: n records per class."""
    out = []
    for y in (0, 1):
        xs = rng.normal(0.0, 1.0, (n, cfg.d)) + cfg.mu(y)
        ans = head.score(xs) >= tau
        err = head.predict(xs) != bool(y)
        out += [float((ans & err).mean()), float(ans.mean())]
    e0, a0, e1, a1 = out
    return e0, a0, e1, a1


def population_parameters(cfg):
    pi_s = population_prevalence(cfg.base_rate, cfg.s_u)
    pi_t = population_prevalence(SHIFT_BASE, cfg.s_u)
    return dict(pi_s=pi_s, pi_pop_target=pi_t,
                rho_pop=_odds(pi_t) / _odds(pi_s))


# ------------------------------------------------------------------ arm A

def replay_a(n_idx, r, cfg=None):
    """One single-site arm-A draw, call for call as run_E9 runs it.

    Returns the head, the declared target, the fresh pool, the target's
    site effect u_t (from a copy of the stream taken before the target is
    drawn) and the rows run_E9 writes for this draw, one per alpha.
    """
    cfg = cfg or SimConfig()
    n_sites = E9_SOURCE_SWEEP[n_idx]
    rng = _rng(9, 0, n_idx, M_IDX_SINGLE, r)
    coh = draw_cohort(cfg, n_sites, rng)
    train, aux, cal = split_sites(coh, rng)
    head = fit_head(train)
    peek = copy.deepcopy(rng)
    size = int(np.clip(np.exp(peek.normal(cfg.size_mu, cfg.size_sigma, 1)),
                       cfg.size_lo, cfg.size_hi).astype(int)[0])
    u_t = float(peek.normal(0.0, cfg.s_u, 1)[0])
    tgt = draw_cohort(cfg, 1, rng, label_base_rate=SHIFT_BASE,
                      site_label_prefix=f"e9t{n_idx}_{r}",
                      require_both_classes=False)
    if tgt.n != size:
        raise SystemExit(
            f"rescore_e9_exact: arm A draw ({n_sites}, {r}): the stream copy "
            f"gives a target of {size} records, the replay {tgt.n}; u_t is "
            f"not the target's own effect; nothing written "
            f"(reason=stream-copy-mismatch)")
    rep = run_certgate(train, aux, cal, tgt.x,
                       target_label=f"E9a-{n_sites}-{SINGLE_SITE}-{r}",
                       target_site_id=None, oracle_target_y=tgt.y,
                       modes=("bbse",))
    bd = rep["diagnostic"]["bbse"]
    evalp = draw_cohort(cfg, E1_EVAL_SITES, rng, label_base_rate=SHIFT_BASE,
                        site_label_prefix=f"e9v{n_idx}_{r}")
    lo, hi = bd.get("rho_lo"), bd.get("rho_hi")
    width = (round(float(hi) - float(lo), 4)
             if lo is not None and hi is not None else None)
    rows = []
    for alpha in ALPHA_LADDER:
        row = _row_for(rep, alpha)
        certified = row is not None and row["status"] == "certified"
        out = dict(n_source_sites=n_sites, target_mode=SINGLE_SITE, draw=r,
                   alpha=alpha, certified=certified, tau=None, coverage=None,
                   decline_reason=None, rho_lo=lo, rho_hi=hi,
                   box_width=width, rm_fresh=None, rm_exceed=None,
                   tau_deployed=None)
        if certified:
            out.update(_rescore(head, evalp, None, alpha, tau=row["tau"]))
            out["tau_deployed"] = float(row["tau"])
        elif row is not None:
            out["decline_reason"] = row.get("reasons", {}).get("bbse")
        else:
            out["decline_reason"] = rep.get("reason")
        rows.append(out)
    return dict(n_sites=n_sites, draw=r, head=head, tgt=tgt, evalp=evalp,
                u_t=u_t, pi_source=float(coh.y.mean()), rows=rows)


def check_a(rep, frozen, released):
    """Mismatches of one replayed arm-A draw against the released files."""
    bad = []
    for row in rep["rows"]:
        key = (row["n_source_sites"], row["draw"], float(row["alpha"]))
        fr = frozen.get(key)
        if fr is None:
            bad.append(dict(row=key, reason="not in E9_bbse_frontier.csv"))
            continue
        for f in FROZEN_A_FIELDS:
            if _cell(row[f]) != fr[f]:
                bad.append(dict(row=key, field=f, frozen=fr[f],
                                replayed=_cell(row[f])))
        if not row["certified"]:
            continue
        rel = released.get(key)
        if rel is None:
            bad.append(dict(row=key, reason="not in E9a_rescore.csv"))
            continue
        tau = row["tau_deployed"]
        pi_t = float(rep["tgt"].y.mean())
        mine = dict(pi_target=pi_t, pi_eval=float(rep["evalp"].y.mean()),
                    pi_source=rep["pi_source"], rm_fresh_replayed=row["rm_fresh"],
                    rm_rescored=_rm_reweighted(rep["head"], rep["evalp"], tau,
                                               pi_t))
        for f in RELEASED_A_6DP:
            if round(float(mine[f]), 6) != float(rel[f]):
                bad.append(dict(row=key, field=f, released=rel[f],
                                replayed=round(float(mine[f]), 6)))
        if float(rel["tau"]) != row["tau"]:
            bad.append(dict(row=key, field="tau", released=rel["tau"],
                            replayed=row["tau"]))
    return bad


def score_a(rep, pop, cfg=None, mc=True):
    """Closed-form named estimand for each certified row of one draw."""
    cfg = cfg or SimConfig()
    head, tgt = rep["head"], rep["tgt"]
    pi_lat = float(_sigmoid(_logit(SHIFT_BASE) + rep["u_t"]))
    pi_real = float(tgt.y.mean())
    rho_star = _odds(pi_lat) / _odds(pop["pi_s"])
    n_idx = E9_SOURCE_SWEEP.index(rep["n_sites"])
    mc_rng = _rng(9, 0, n_idx, M_IDX_SINGLE, rep["draw"], MC_STREAM_TAG)
    out = []
    for row in rep["rows"]:
        if not row["certified"]:
            continue
        tau, alpha = row["tau_deployed"], float(row["alpha"])
        rates = class_rates(head, cfg, np.array([tau]))
        r_named = float(answered_risk(rates, pi_lat)[0])
        r_mc = None
        if mc:
            r_mc = float(answered_risk(mc_class_rates(head, cfg, tau, mc_rng),
                                       pi_lat))
        lo, hi = float(row["rho_lo"]), float(row["rho_hi"])
        out.append(dict(
            arm="A-single-site", n_sites=rep["n_sites"], draw=rep["draw"],
            budget=alpha, tau=row["tau"],
            released_fresh=row["rm_fresh"],
            released_fresh_exceeds=bool(row["rm_exceed"]),
            released_proxy=_r6(_rm_reweighted(head, rep["evalp"], tau,
                                              pi_real)),
            exact_named_estimand=_r6(r_named),
            exact_exceeds=bool(r_named > alpha),
            exact_slack=_r6(alpha - r_named),
            mc_named_estimand=_r6(r_mc),
            u_t=_r6(rep["u_t"]), pi_latent=_r6(pi_lat),
            pi_realised=_r6(pi_real), n_target_records=int(tgt.n),
            exact_at_realised_prevalence=_r6(answered_risk(rates,
                                                           pi_real)[0]),
            exact_at_population_prevalence=_r6(answered_risk(
                rates, pop["pi_pop_target"])[0]),
            rho_star=_r6(rho_star), rho_lo=_r6(lo), rho_hi=_r6(hi),
            box_covers_rho_star=bool(lo <= rho_star <= hi),
            box_covers_rho_pop_parameter=bool(lo <= pop["rho_pop"] <= hi)))
    return out


def load_a():
    """(frozen, released) single-site rows keyed (n_sites, draw, alpha)."""
    frozen = {(int(f["n_source_sites"]), int(f["draw"]), float(f["alpha"])): f
              for f in _read_csv(FROZEN_A) if f["target_mode"] == SINGLE_SITE}
    released = {(int(f["n_source_sites"]), int(f["draw"]), float(f["alpha"])):
                f for f in _read_csv(RELEASED_A)
                if f["target_mode"] == SINGLE_SITE}
    return frozen, released


def run_a(log=print, draws=None, mc=True):
    """Replay, check and score every single-site arm-A draw that certified."""
    cfg = SimConfig()
    pop = population_parameters(cfg)
    frozen, released = load_a()
    keys = sorted({(E9_SOURCE_SWEEP.index(k[0]), k[1])
                   for k, f in frozen.items() if f["certified"] == "True"})
    if draws is not None:
        keys = sorted(draws)
    rows, bad, mc_bad = [], [], []
    t0 = time.perf_counter()
    for i, (n_idx, r) in enumerate(keys):
        rep = replay_a(n_idx, r, cfg)
        bad += check_a(rep, frozen, released)
        scored = score_a(rep, pop, cfg, mc=mc)
        for x in scored:
            if mc and abs(x["mc_named_estimand"]
                          - x["exact_named_estimand"]) > MC_TOL:
                mc_bad.append(x)
        rows += scored
        if log and (i % 10 == 9 or i == len(keys) - 1):
            log(f"[certgate] e9 exact arm A: {i + 1}/{len(keys)} draws "
                f"({time.perf_counter() - t0:.0f} s)")
    if bad:
        raise SystemExit(
            f"rescore_e9_exact: arm A replay differs from the released rows "
            f"on {len(bad)} cells, e.g. {bad[:3]}; nothing written "
            f"(reason=replay-mismatch)")
    if mc_bad:
        raise SystemExit(
            f"rescore_e9_exact: arm A closed form disagrees with Monte Carlo "
            f"beyond {MC_TOL} on {len(mc_bad)} rows, e.g. {mc_bad[:2]}; "
            f"nothing written (reason=truth-check-failed)")
    if draws is None:
        n_cert = sum(f["certified"] == "True" for f in frozen.values())
        if len(rows) != n_cert:
            raise SystemExit(
                f"rescore_e9_exact: scored {len(rows)} arm-A certificates, "
                f"the frozen CSV holds {n_cert}; nothing written "
                f"(reason=replay-mismatch)")
        for (n, mode, d, alpha), expected in EXCEEDING_ROWS.items():
            got = next(x for x in rows if x["n_sites"] == n and x["draw"] == d
                       and x["budget"] == alpha)
            if mode != SINGLE_SITE or round(got["released_fresh"], 4) \
                    != expected:
                raise SystemExit(
                    f"rescore_e9_exact: pinned exceeding row "
                    f"{(n, mode, d, alpha)} replayed {got['released_fresh']}, "
                    f"expected {expected}; nothing written "
                    f"(reason=self-check-failed)")
    check = dict(draws_replayed=len(keys), certificates=len(rows),
                 frozen_cells_compared=len(keys) * len(ALPHA_LADDER)
                 * len(FROZEN_A_FIELDS),
                 mismatches=0, mc_checked=len(rows) if mc else 0,
                 mc_max_abs_diff=(round(max(abs(x["mc_named_estimand"]
                                                - x["exact_named_estimand"])
                                            for x in rows), 6)
                                  if mc and rows else None),
                 wall_clock_s=round(time.perf_counter() - t0, 1))
    return rows, check


def summarise_a(rows):
    cells = {}
    for n in E9_SOURCE_SWEEP:
        for alpha in ALPHA_LADDER:
            sub = [x for x in rows if x["n_sites"] == n
                   and x["budget"] == alpha]
            if not sub:
                continue
            cells[f"{n}|{alpha}"] = dict(
                n_certified=len(sub),
                exact_exceeds=sum(x["exact_exceeds"] for x in sub),
                released_fresh_exceeds=sum(x["released_fresh_exceeds"]
                                           for x in sub),
                released_proxy_exceeds=sum(x["released_proxy"] > alpha
                                           for x in sub),
                box_covers_rho_star=sum(x["box_covers_rho_star"]
                                        for x in sub),
                box_covers_rho_pop_parameter=sum(
                    x["box_covers_rho_pop_parameter"] for x in sub),
                max_exact_named_estimand=max(x["exact_named_estimand"]
                                             for x in sub))
    flagged = [dict((k, x[k]) for k in (
        "n_sites", "draw", "budget", "tau", "released_fresh", "released_proxy",
        "exact_named_estimand", "exact_exceeds", "mc_named_estimand",
        "pi_latent", "pi_realised", "n_target_records",
        "exact_at_realised_prevalence", "exact_at_population_prevalence",
        "rho_star", "rho_lo", "rho_hi", "box_covers_rho_star"))
        for x in rows if x["released_fresh_exceeds"]]
    return dict(
        certificates=len(rows),
        draws=len({(x["n_sites"], x["draw"]) for x in rows}),
        exact_exceeds=sum(x["exact_exceeds"] for x in rows),
        min_exact_slack=min(x["exact_slack"] for x in rows),
        box_covers_rho_star=sum(x["box_covers_rho_star"] for x in rows),
        box_covers_rho_pop_parameter=sum(x["box_covers_rho_pop_parameter"]
                                         for x in rows),
        released_fresh_exceeds=sum(x["released_fresh_exceeds"] for x in rows),
        released_proxy_exceeds=sum(x["released_proxy"] > x["budget"]
                                   for x in rows),
        cells=cells, released_exceeding_rows=flagged)


# ------------------------------------------------------------------ arm B

def replay_b(n_idx, r, cfg=None):
    """One arm-B draw: both arms' released rows plus the head they score.

    run_e9b_positives.run_draw replays the walks on _rng(9, 1, n_idx, r);
    the head and fresh pool are re-drawn here on a fresh copy of the same
    stream so the closed form can be taken from the head.
    """
    cfg = cfg or SimConfig()
    n_sites = E9_FNR_SWEEP[n_idx]
    shipped, positives = e9b.run_draw(n_idx, r, cfg)
    rng = _rng(9, 1, n_idx, r)
    _, _, cal, head = _draw_split(cfg, n_sites, rng)
    evalp = draw_cohort(cfg, E1_EVAL_SITES, rng,
                        site_label_prefix=f"e9fv{n_idx}_{r}")
    return dict(n_sites=n_sites, draw=r, head=head, evalp=evalp,
                n_cal=cal.n_sites,
                rows={"shipped": shipped, "positives": positives})


def check_b(rep, released, frozen):
    """Mismatches of one replayed arm-B draw against the released files."""
    bad = []
    fresh = {"shipped": _fnr_on_pool, "positives": e9b._fnr_pos_on_pool}
    lowest = float(TAU_GRID[0])
    for arm, arm_rows in rep["rows"].items():
        own_truth = round(fresh[arm](rep["head"], rep["evalp"], lowest), 6)
        for x in arm_rows:
            key = (arm, x["n_sites"], x["draw"], x["fnr_budget"])
            rel = released.get(key)
            if rel is None:
                bad.append(dict(row=key, reason="not in E9b_fnr_positives"))
                continue
            for f in B_FIELDS:
                if _cell(x[f]) != rel[f]:
                    bad.append(dict(row=key, field=f, released=rel[f],
                                    replayed=_cell(x[f])))
            if own_truth != x["true_fnr_at_lowest_tau"]:
                bad.append(dict(row=key, field="head-refit truth",
                                replayed=own_truth))
            if x["certified"]:
                v = round(fresh[arm](rep["head"], rep["evalp"], x["tau"]), 6)
                if v != x["fnr_fresh"]:
                    bad.append(dict(row=key, field="head-refit fnr_fresh",
                                    replayed=v))
    bad += e9b._check_shipped(rep["rows"]["shipped"], frozen)
    return bad


def score_b(rep, cfg=None, mc=True):
    """The draw's exact FNR curve and every certificate scored on it."""
    cfg = cfg or SimConfig()
    head = rep["head"]
    curve = fnr_exact(class_rates(head, cfg, TAU_GRID))
    below = curve < FNR_CONTROL
    n_idx = E9_FNR_SWEEP.index(rep["n_sites"])
    draw = dict(n_sites=rep["n_sites"], draw=rep["draw"],
                m_pos_logit=_r6(positive_logit_mean(head, cfg)),
                fnr_exact_tau_lowest=_r6(curve[0]),
                fnr_exact_tau_highest=_r6(curve[-1]),
                strictly_decreasing=bool(np.all(np.diff(curve) < 0)),
                below_control_at_some_tau=bool(below.any()),
                first_tau_below_control=(round(float(TAU_GRID[
                    int(np.argmax(below))]), 4) if below.any() else None))
    certs = []
    for arm, arm_rows in rep["rows"].items():
        for x in arm_rows:
            if not x["certified"]:
                continue
            k = _snap(x["tau"])
            b = float(x["fnr_budget"])
            v = float(curve[k])
            mc_v = None
            if mc and arm == "positives" and b == FNR_CONTROL:
                e0, a0, e1, a1 = mc_class_rates(
                    head, cfg, float(TAU_GRID[k]),
                    _rng(9, 1, n_idx, rep["draw"], MC_STREAM_TAG))
                mc_v = e1 / a1
            certs.append(dict(
                arm=f"B-{arm}", n_sites=rep["n_sites"], draw=rep["draw"],
                budget=b, tau=x["tau"], released_fresh=x["fnr_fresh"],
                released_fresh_exceeds=bool(x["fnr_exceed"]),
                exact_named_estimand=_r6(v), exact_exceeds=bool(v > b),
                exact_slack=_r6(b - v), mc_named_estimand=_r6(mc_v),
                exact_at_lowest_tau=_r6(curve[0])))
    return draw, certs


def load_b():
    """(released rows keyed (arm, n_sites, draw, budget), frozen rows)."""
    released = {(f["arm"], int(f["n_sites"]), int(f["draw"]),
                 float(f["fnr_budget"])): f for f in _read_csv(RELEASED_B)}
    return released, _read_csv(FROZEN_B)


def run_b(log=print, draws=None, mc=True):
    """Replay, check and score every arm-B draw (600 by default)."""
    cfg = SimConfig()
    released, frozen = load_b()
    keys = ([(n_idx, r) for n_idx in range(len(E9_FNR_SWEEP))
             for r in range(E9_FNR_R)] if draws is None else sorted(draws))
    draw_rows, certs, bad, mc_bad = [], [], [], []
    t0 = time.perf_counter()
    for i, (n_idx, r) in enumerate(keys):
        rep = replay_b(n_idx, r, cfg)
        bad += check_b(rep, released, frozen)
        d, c = score_b(rep, cfg, mc=mc)
        draw_rows.append(d)
        certs += c
        mc_bad += [x for x in c if x["mc_named_estimand"] is not None
                   and abs(x["mc_named_estimand"]
                           - x["exact_named_estimand"]) > MC_TOL]
        if log and (i % 50 == 49 or i == len(keys) - 1):
            log(f"[certgate] e9 exact arm B: {i + 1}/{len(keys)} draws "
                f"({time.perf_counter() - t0:.0f} s)")
    if bad:
        raise SystemExit(
            f"rescore_e9_exact: arm B replay differs from the released rows "
            f"on {len(bad)} cells, e.g. {bad[:3]}; nothing written "
            f"(reason=replay-mismatch)")
    if mc_bad:
        raise SystemExit(
            f"rescore_e9_exact: arm B closed form disagrees with Monte Carlo "
            f"beyond {MC_TOL} on {len(mc_bad)} rows, e.g. {mc_bad[:2]}; "
            f"nothing written (reason=truth-check-failed)")
    if draws is None:
        n_cert = sum(f["certified"] == "True" for f in released.values())
        if len(certs) != n_cert or len(draw_rows) * 2 * len(E9_FNR_LADDER) \
                != len(released):
            raise SystemExit(
                f"rescore_e9_exact: scored {len(certs)} arm-B certificates "
                f"over {len(draw_rows)} draws against {n_cert} released; "
                f"nothing written (reason=replay-mismatch)")
    mc_rows = [x for x in certs if x["mc_named_estimand"] is not None]
    check = dict(draws_replayed=len(keys), certificates=len(certs),
                 released_cells_compared=len(keys) * 2 * len(E9_FNR_LADDER)
                 * len(B_FIELDS), mismatches=0, mc_checked=len(mc_rows),
                 mc_max_abs_diff=(round(max(abs(x["mc_named_estimand"]
                                                - x["exact_named_estimand"])
                                            for x in mc_rows), 6)
                                  if mc_rows else None),
                 wall_clock_s=round(time.perf_counter() - t0, 1))
    return draw_rows, certs, check


def summarise_b(draw_rows, certs):
    per_n = {}
    for n in E9_FNR_SWEEP:
        sub = [d for d in draw_rows if d["n_sites"] == n]
        if not sub:
            continue
        per_n[str(n)] = dict(
            draws=len(sub),
            mean_fnr_exact_tau_lowest=round(float(np.mean(
                [d["fnr_exact_tau_lowest"] for d in sub])), 4),
            mean_fnr_exact_tau_highest=round(float(np.mean(
                [d["fnr_exact_tau_highest"] for d in sub])), 4),
            below_control_at_some_tau=sum(d["below_control_at_some_tau"]
                                          for d in sub),
            strictly_decreasing=sum(d["strictly_decreasing"] for d in sub))
    first = [d["first_tau_below_control"] for d in draw_rows
             if d["first_tau_below_control"] is not None]
    by_cell = {}
    for arm in ("B-shipped", "B-positives"):
        for b in E9_FNR_LADDER:
            sub = [x for x in certs if x["arm"] == arm and x["budget"] == b]
            by_cell[f"{arm}|{b}"] = dict(
                n_certified=len(sub),
                exact_exceeds=sum(x["exact_exceeds"] for x in sub),
                released_fresh_exceeds=sum(x["released_fresh_exceeds"]
                                           for x in sub),
                max_exact_named_estimand=(max(x["exact_named_estimand"]
                                              for x in sub) if sub else None),
                min_exact_slack=(min(x["exact_slack"] for x in sub)
                                 if sub else None))
    control = [dict((k, x[k]) for k in (
        "n_sites", "draw", "budget", "tau", "released_fresh",
        "released_fresh_exceeds", "exact_named_estimand", "exact_exceeds",
        "mc_named_estimand", "exact_at_lowest_tau"))
        for x in certs if x["arm"] == "B-positives"
        and x["budget"] == FNR_CONTROL]
    nonmono = [dict(n_sites=d["n_sites"], draw=d["draw"],
                    m_pos_logit=d["m_pos_logit"])
               for d in draw_rows if not d["strictly_decreasing"]]
    return dict(
        draws=len(draw_rows), certificates=len(certs),
        exact_exceeds=sum(x["exact_exceeds"] for x in certs),
        min_exact_slack=(min(x["exact_slack"] for x in certs)
                         if certs else None),
        released_fresh_exceeds=sum(x["released_fresh_exceeds"]
                                   for x in certs),
        mean_fnr_exact_tau_lowest=round(float(np.mean(
            [d["fnr_exact_tau_lowest"] for d in draw_rows])), 4),
        below_control_at_some_tau=sum(d["below_control_at_some_tau"]
                                      for d in draw_rows),
        never_below_control=sum(not d["below_control_at_some_tau"]
                                for d in draw_rows),
        strictly_decreasing=sum(d["strictly_decreasing"] for d in draw_rows),
        not_strictly_decreasing=nonmono,
        first_tau_below_control=(dict(
            min=min(first), median=round(float(np.median(first)), 4),
            max=max(first)) if first else None),
        by_site_count=per_n, by_cell=by_cell,
        positives_certificates_at_control=control,
        certify_and_estimand_exceeds_at_control=dict(
            positives=sum(x["exact_exceeds"] for x in control),
            shipped=sum(x["exact_exceeds"] for x in certs
                        if x["arm"] == "B-shipped"
                        and x["budget"] == FNR_CONTROL),
            draws=len(draw_rows)))


# ----------------------------------------------------------------- driver

CSV_FIELDS = ["arm", "n_sites", "draw", "budget", "tau", "released_fresh",
              "released_fresh_exceeds", "released_proxy",
              "exact_named_estimand", "exact_exceeds", "exact_slack",
              "mc_named_estimand", "exact_at_lowest_tau", "u_t", "pi_latent",
              "pi_realised", "n_target_records",
              "exact_at_realised_prevalence",
              "exact_at_population_prevalence", "rho_star", "rho_lo",
              "rho_hi", "box_covers_rho_star",
              "box_covers_rho_pop_parameter"]


def check_population(pop):
    truth = _read_json(PROBE_JSON)["truth"]
    for k in ("pi_s", "pi_pop_target", "rho_pop"):
        if round(pop[k], 6) != truth[k]:
            raise SystemExit(
                f"rescore_e9_exact: population {k} {pop[k]:.6f} differs from "
                f"BBSE_probe.json's {truth[k]}; nothing written "
                f"(reason=self-check-failed)")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="score the E9 certificates against their named "
                    "estimands in closed form")
    ap.add_argument("--out", default=OUT_DIR)
    args = ap.parse_args(argv)
    csv_path = os.path.join(args.out, "E9_exact.csv")
    json_path = os.path.join(args.out, "E9_exact.json")
    for p in (csv_path, json_path):
        _assert_writable(p)
    t0 = time.perf_counter()
    pop = population_parameters(SimConfig())
    check_population(pop)
    rows_a, check_a_ = run_a()
    draws_b, certs_b, check_b_ = run_b()
    doc = dict(
        post_hoc=POST_HOC, estimand=ESTIMAND_NOTE,
        population=dict((k, round(v, 6)) for k, v in pop.items()),
        self_check=dict(arm_a=check_a_, arm_b=check_b_,
                        population_matches_bbse_probe=True,
                        mc_records_per_class=MC_RECORDS, mc_tol=MC_TOL),
        arm_a=summarise_a(rows_a), arm_b=summarise_b(draws_b, certs_b))
    a, b = doc["arm_a"], doc["arm_b"]
    ctl = b["positives_certificates_at_control"]
    doc["headline"] = (
        f"arm A: {a['certificates']} single-site certificates, named "
        f"estimand over budget in {a['exact_exceeds']}, box covers rho* in "
        f"{a['box_covers_rho_star']}; released-exceeding rows "
        f"{[x['exact_named_estimand'] for x in a['released_exceeding_rows']]}"
        f" (proxy {[x['released_proxy'] for x in a['released_exceeding_rows']]}"
        f"). arm B: {b['certificates']} certificates, exact FNR over budget in "
        f"{b['exact_exceeds']}; b=0.4 positives certificates "
        f"{[x['exact_named_estimand'] for x in ctl]}; exact FNR < 0.4 at some "
        f"grid tau in {b['below_control_at_some_tau']} of {b['draws']} draws")
    doc["wall_clock_s"] = round(time.perf_counter() - t0, 1)
    os.makedirs(args.out, exist_ok=True)
    _write_csv(csv_path, rows_a + certs_b, CSV_FIELDS)
    _write_json(json_path, {"_run": run_block(list(INPUTS)), **doc,
                            "arm_b_draws": draws_b},
                "rescore_e9_exact", per_item_keys=("arm_b_draws",))
    print(f"[certgate] {doc['headline']}")
    print(f"[certgate] wrote {csv_path} and {json_path} "
          f"({doc['wall_clock_s']} s)", file=sys.stderr)
    return doc


if __name__ == "__main__":
    main()
