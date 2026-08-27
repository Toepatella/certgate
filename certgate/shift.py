"""Label-shift (BBSE) assumption mode.

Black-box shift estimation puts a cluster-robust confidence box on
(c0, c1, pi_source, q_target). That box propagates to an odds-ratio interval
[rho_lo, rho_hi], and certification tests the worst case over the interval.

The budget splits two ways: the bet spends BBSE_DELTA_BET, the box spends
BBSE_DELTA_CONF. A union bound puts them back together as 1 - delta.

Ported from the audited v1 fit_a2/certify_a2
(../xAI-projtect-v1/testbed/modes.py), plus four pieces of SPEC hardening:

  - bootstrap top-up-or-decline;
  - decline when the q_t range leaves the box;
  - deterministic per-endpoint permutation streams, replacing v1's single
    shared stream;
  - a confidence share for q_t itself.

That last one is not cosmetic. The target predicted-positive rate is a noisy
estimate, not an observed constant; treating it as exact issued false
certificates at up to 3x delta under pure label shift, where a control with
q_t effectively exact issued none.

Declines, never fallbacks:

  bbse-empty-target -> bbse-target-clustering -> bbse-degenerate-bootstrap
  -> bbse-ill-conditioned -> bbse-misspecified

Runtime dependencies are constants, certify and scipy only. Cohort and Head are
duck-typed at runtime and imported for type hints under TYPE_CHECKING only.

Refs: SPEC "shift.py"; METHODS 5; audits F40/B-8, F41/B-9, V2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
from scipy.stats import beta as _beta_dist

from .constants import (ALPHA_LADDER, BBSE_DELTA_CONF, BBSE_DELTA_BET,
                        BBSE_BONFERRONI, BBSE_GAP_FLOOR, BBSE_BOOT,
                        BBSE_BOOT_MAX_ATTEMPTS, BBSE_MIN_TARGET_SITES,
                        PI_CLIP, M_INFLUENCE, TAU_GRID, MODE_BBSE)
from .certify import (influence_atoms, walk_order, wsr_reject,
                      certification_rng)

if TYPE_CHECKING:                      # type hints only -- never imported at runtime
    from .validate import Cohort
    from .model import Head


@dataclass
class BBSEFit:
    """Frozen label-shift correction, a function of (head, S_aux, target pool).

    q_target is an estimate of the target population predicted-positive rate
    and carries sampling error, so it gets its own confidence share in the box.

    Scale-invariance lets record weights be (1, rho), with rho the
    target/source odds ratio of the positive class. walk_orders maps each alpha
    to its S_aux-derived fixed sequence.

    Refs: METHODS 5; audit V2.
    """
    declined: bool
    reason: str
    rho_lo: float
    rho_hi: float
    rho_point: float
    diagnostics: dict
    walk_orders: dict = field(default_factory=dict)


_DIAG_KEYS = ("n_target", "n_target_sites", "min_target_sites", "q_target",
              "q_ci", "c0", "c1", "pi_s", "c0_ci", "c1_ci", "pi_s_ci",
              "gap_lo", "n_boot", "n_attempts", "rho_lo", "rho_hi",
              "rho_point")


def bbse_diagnostics(**known) -> dict:
    """Diagnostics dict with a stable key set.

    Every BBSEFit.diagnostics carries the same keys -- a full fit, every
    decline path, and the pipeline's not-run placeholder alike. Keys a branch
    did not compute are None, so a consumer indexing any key gets None rather
    than KeyError.

    Unknown keys are rejected loudly so the set cannot drift silently.

    Refs: SPEC "shift.py"; audit V25 (fixture audit 2026-07-25).
    """
    unknown = set(known) - set(_DIAG_KEYS)
    if unknown:
        raise ValueError(
            f"bbse_diagnostics: unknown keys {sorted(unknown)} -- the stable "
            f"key set is {list(_DIAG_KEYS)}")
    d = {k: None for k in _DIAG_KEYS}
    d.update(known)
    return d


def _decline(reason: str, diag: dict) -> BBSEFit:
    """A declined fit: NaN odds-ratio interval, empty walk orders."""
    nan = float("nan")
    return BBSEFit(True, reason, nan, nan, nan, diag)


def _q_interval(pred, target_site_id, lvl, rng):
    """Two-sided level-lvl interval for the target predicted-positive rate q.

    Passing target_site_id as None, or as one distinct site, is the caller
    declaring the pool is a single site. That branch is exact Clopper-Pearson
    on the record count -- finite-sample valid for records iid within one site.
    A multi-site pool must supply target_site_id, or the interval under-covers.

    With at least BBSE_MIN_TARGET_SITES sites the interval is a percentile
    cluster bootstrap over target sites, BBSE_BOOT resamples. Every resample is
    valid, because q needs no both-classes constraint. It is asymptotic, like
    the S_aux box.

    Pools of 2..BBSE_MIN_TARGET_SITES-1 sites decline upstream in fit_bbse and
    never reach here.

    Refs: audit V2; verification F1.
    """
    pred = np.asarray(pred, dtype=bool)
    n = int(pred.shape[0])
    k = int(pred.sum())
    uniq = dense = None
    if target_site_id is not None:
        sid = np.asarray(target_site_id)
        uniq, dense = np.unique(sid, return_inverse=True)
    n_sites = 1 if uniq is None else int(len(uniq))
    if n_sites <= 1:
        q_lo = float(_beta_dist.ppf(lvl / 2.0, k, n - k + 1)) if k > 0 else 0.0
        q_hi = (float(_beta_dist.ppf(1.0 - lvl / 2.0, k + 1, n - k))
                if k < n else 1.0)
        return q_lo, q_hi, n_sites
    k_s = np.bincount(dense, weights=pred.astype(float), minlength=n_sites)
    n_s = np.bincount(dense, minlength=n_sites).astype(float)
    draws = np.empty(BBSE_BOOT)
    for b in range(BBSE_BOOT):
        idx = rng.integers(0, n_sites, n_sites)
        draws[b] = k_s[idx].sum() / n_s[idx].sum()   # n_s >= 1 per site: safe
    q_lo = float(np.quantile(draws, lvl / 2.0))
    q_hi = float(np.quantile(draws, 1.0 - lvl / 2.0))
    return q_lo, q_hi, n_sites


def _site_stats(head: "Head", cohort: "Cohort") -> np.ndarray:
    """Per-site sufficient statistics, stacked as (4, n_sites).

    Rows are n, pos, pred1&pos, pred1&neg, built with bincount. y is bool by
    the Cohort contract.
    """
    yhat = head.predict(cohort.x)
    n_sites = cohort.n_sites
    n = np.bincount(cohort.site_id, minlength=n_sites).astype(float)
    pos = np.bincount(cohort.site_id, weights=cohort.y.astype(float),
                      minlength=n_sites)
    p1p = np.bincount(cohort.site_id,
                      weights=(yhat & cohort.y).astype(float),
                      minlength=n_sites)
    p1n = np.bincount(cohort.site_id,
                      weights=(yhat & ~cohort.y).astype(float),
                      minlength=n_sites)
    return np.stack([n, pos, p1p, p1n])          # (4, n_sites)


def rho_box_interval(q_lo, q_hi, q_point, lo, hi, point):
    """Worst-case odds-ratio interval over the (q, c0, c1, pi_s) box.

    Returns that interval plus the point estimate, evaluated at the box's 16
    corners.

    Corners suffice. On the gated region (c1 - c0 >= BBSE_GAP_FLOOR > 0),
    pi_t = (q - c0)/(c1 - c0) is monotone in each coordinate, rho is monotone
    in pi_t and pi_s, and the clip preserves monotonicity. So the extremes over
    the 4-D box are attained at corners.

    The clip costs precision, not coverage: the unclipped odds ratio stays
    covered whenever the true pi_t lies in [PI_CLIP, 1-PI_CLIP]. Outside that
    range the exposure is bounded at the PI_CLIP odds scale, about 1e-4 in an
    affine-in-rho statistic. Misspecification declines before it gets there.

    Refs: SPEC "shift.py"; audits V2, F41/B-9; verification F2-bbse.
    """
    def rho_of(q, c0, c1, pi_s):
        pi_t = np.clip((q - c0) / (c1 - c0), PI_CLIP, 1.0 - PI_CLIP)
        pi_s = np.clip(pi_s, PI_CLIP, 1.0 - PI_CLIP)
        return (pi_t / (1.0 - pi_t)) / (pi_s / (1.0 - pi_s))

    corners = [rho_of(q, c0, c1, ps)
               for q in (q_lo, q_hi)
               for c0 in (lo[0], hi[0])
               for c1 in (lo[1], hi[1])
               for ps in (lo[2], hi[2])]               # 16 box corners
    return (float(min(corners)), float(max(corners)),
            float(rho_of(q_point, *point)))


def fit_bbse(head: "Head", aux: "Cohort", target_x, rng,
             target_site_id=None, *, score_aux=None, err_aux=None) -> BBSEFit:
    """Fit the BBSE confidence box and propagate it to an odds-ratio interval.

    The box is fit on S_aux plus the target pool; the interval is the worst
    case over that box.

    The bootstrap draws site-index resamples until BBSE_BOOT valid ones are
    collected, valid meaning the pooled resample holds a positive and a
    negative. If BBSE_BOOT_MAX_ATTEMPTS run out first it declines
    bbse-degenerate-bootstrap, never a quantile over a reduced count.

    q_t is an estimate of the target population predicted-positive rate, so it
    gets its own confidence share at BBSE_DELTA_CONF / BBSE_BONFERRONI. That
    share is exact Clopper-Pearson for a single-site pool (target_site_id None
    or one distinct value), and a cluster bootstrap over target sites
    otherwise -- see _q_interval.

    Decline order:

      - bbse-empty-target;
      - bbse-target-clustering;
      - bbse-degenerate-bootstrap;
      - bbse-ill-conditioned, when the worst-case confusion gap
        lo_c1 - hi_c0 < BBSE_GAP_FLOOR;
      - bbse-misspecified, unless the whole q interval sits inside the box
        range [lo_c0, hi_c1].

    That last test is written as not (...), which is NaN-safe: a non-finite q
    declines instead of flowing through.

    Refs: SPEC "shift.py"; METHODS 5; audits F40/B-8, F41/B-9 (widened by V2),
    V2, V14; verification F1.
    """
    stats = _site_stats(head, aux)
    n_sites = stats.shape[1]
    n_target = int(np.asarray(target_x).shape[0])
    if n_target == 0:
        return _decline("bbse-empty-target", bbse_diagnostics(n_target=0))
    # q cluster-bootstrap floor. A percentile bootstrap over 2..K-1 target
    # sites cannot approach nominal coverage: measured rho-miss up to 46% at
    # K=2 against a nominal 2.5%, and certify-and-violate at 3.4x delta where
    # the bet has power. Decline rather than pretend.
    # Ref: verification F1.
    if target_site_id is not None:
        sid = np.asarray(target_site_id)
        if sid.ndim != 1 or sid.shape[0] != n_target:
            raise ValueError(
                "fit_bbse: target_site_id must be 1-D and aligned with "
                "target_x (reason=bad-target-site-id)")
        n_ts = int(len(np.unique(sid)))
        if 2 <= n_ts < BBSE_MIN_TARGET_SITES:
            return _decline("bbse-target-clustering", bbse_diagnostics(
                n_target=n_target, n_target_sites=n_ts,
                min_target_sites=BBSE_MIN_TARGET_SITES))
    pred_t = head.predict(target_x)
    q_t = float(np.asarray(pred_t, dtype=float).mean())

    def params(cols):
        s = stats[:, cols].sum(axis=1)
        n_, pos, p1p, p1n = s
        neg = n_ - pos
        if pos < 1 or neg < 1:
            return None
        return p1n / neg, p1p / pos, pos / n_          # c0, c1, pi_s

    point = params(np.arange(n_sites))

    # Bootstrap: top-up-or-decline (never quantile over a reduced draw count).
    valid = []
    n_attempts = 0
    while len(valid) < BBSE_BOOT and n_attempts < BBSE_BOOT_MAX_ATTEMPTS:
        b = params(rng.integers(0, n_sites, n_sites))
        n_attempts += 1
        if b is not None:
            valid.append(b)
    if point is None or len(valid) < BBSE_BOOT:
        return _decline("bbse-degenerate-bootstrap", bbse_diagnostics(
            n_target=n_target, q_target=q_t,
            n_boot=len(valid), n_attempts=n_attempts))

    boots = np.array(valid)                            # (BBSE_BOOT, 3)
    lvl = BBSE_DELTA_CONF / BBSE_BONFERRONI            # Bonferroni over 4 params
    lo = np.quantile(boots, lvl / 2.0, axis=0)
    hi = np.quantile(boots, 1.0 - lvl / 2.0, axis=0)
    q_lo, q_hi, n_target_sites = _q_interval(pred_t, target_site_id, lvl, rng)

    diag = bbse_diagnostics(
        q_target=q_t, q_ci=(q_lo, q_hi),
        n_target=n_target, n_target_sites=n_target_sites,
        c0=float(point[0]), c1=float(point[1]),
        pi_s=float(point[2]),
        c0_ci=(float(lo[0]), float(hi[0])),
        c1_ci=(float(lo[1]), float(hi[1])),
        pi_s_ci=(float(lo[2]), float(hi[2])),
        gap_lo=float(lo[1] - hi[0]),
        n_boot=len(valid), n_attempts=n_attempts)

    if lo[1] - hi[0] < BBSE_GAP_FLOOR:                 # worst-case c1 - c0
        return _decline("bbse-ill-conditioned", diag)

    if not (lo[0] <= q_lo and q_hi <= hi[1]):          # q interval in box range
        return _decline("bbse-misspecified", diag)

    rho_lo, rho_hi, rho_point = rho_box_interval(q_lo, q_hi, q_t, lo, hi,
                                                 point)
    diag.update(rho_lo=rho_lo, rho_hi=rho_hi, rho_point=rho_point)

    # Walk orders from point-rho-weighted S_aux atoms. These are
    # S_cal-independent, so in-sample flattery here costs power, never
    # validity.
    if score_aux is None:
        score_aux = head.score(aux.x)
    if err_aux is None:
        err_aux = head.predict(aux.x) != aux.y
    w_pt = np.where(aux.y, rho_point, 1.0)
    wmax_pt = max(1.0, rho_point)
    orders = {}
    for alpha in ALPHA_LADDER:
        atoms = influence_atoms(score_aux, err_aux, aux.site_id, n_sites,
                                TAU_GRID, alpha, M_INFLUENCE,
                                weights=w_pt, wmax=wmax_pt)
        orders[alpha] = walk_order(atoms)

    return BBSEFit(False, "", rho_lo, rho_hi, rho_point, diag, orders)


def certify_bbse(head: "Head", fit: BBSEFit, cal: "Cohort", alpha, *,
                 score=None, err=None) -> dict:
    """BBSE certification for one alpha rung.

    A declined fit passes straight through. Otherwise this is a dual-endpoint
    fixed-sequence walk at BBSE_DELTA_BET: a threshold passes only if the
    betting test rejects on both the rho_lo and the rho_hi atom sets.

    Returns exactly the four keys the pipeline reads: certified, tau_idx, tau,
    reason. Diagnostics live on the BBSEFit the caller already holds. score
    and err are optional precomputed head.score(cal.x) and
    head.predict(cal.x) != cal.y; run_certgate passes them in so the frozen
    head scores each cohort once.

    Why two endpoints are enough. Under the per-endpoint normalization
    wmax=max(1,rho) the atom mean is piecewise in rho, with a kink at 1, so an
    interior maximum is possible. But the statistic is scale-invariant, so
    sign(E[Z]-alpha) = sign(A + rho*B) with (A, B) free of rho -- affine in
    rho. So the certifiable set {rho: E[Z] <= alpha} is convex: certifying both
    endpoints covers every interior rho, and a violating rho inside the box
    forces a violating endpoint, whose level-BBSE_DELTA_BET test controls false
    certification.

    The per-endpoint permutation streams are certification_rng(alpha,
    MODE_BBSE, "lo") and the same with "hi". Both are deterministic,
    order-independent, and carry no target identifier. The fit itself stays
    legitimately target-dependent through the q_t interval, which is why the
    shared-event clause is claimed for baseline mode only.

    Refs: SPEC "shift.py"; METHODS 5; audit V3.
    """
    if fit.declined:
        return dict(certified=[], tau_idx=None, tau=None, reason=fit.reason)

    n_cal_sites = cal.n_sites
    if score is None:
        score = head.score(cal.x)
    if err is None:
        err = head.predict(cal.x) != cal.y
    atom_sets = []
    for rho in (fit.rho_lo, fit.rho_hi):
        w = np.where(cal.y, rho, 1.0)
        atom_sets.append(influence_atoms(score, err, cal.site_id, n_cal_sites,
                                         TAU_GRID, alpha, M_INFLUENCE,
                                         weights=w, wmax=max(1.0, rho)))
    endpoint_rngs = (
        certification_rng(alpha, MODE_BBSE, "lo"),
        certification_rng(alpha, MODE_BBSE, "hi"),
    )

    certified = []
    for t in fit.walk_orders[alpha]:
        ok = all(wsr_reject(atoms[t], alpha, BBSE_DELTA_BET, rng=r)
                 for atoms, r in zip(atom_sets, endpoint_rngs))
        if ok:
            certified.append(int(t))
        else:
            break

    if not certified:
        return dict(certified=[], tau_idx=None, tau=None, reason="failsafe")

    deployed = min(certified, key=lambda t: TAU_GRID[t])
    return dict(certified=certified, tau_idx=deployed,
                tau=float(TAU_GRID[deployed]), reason=None)
