"""Label-shift (BBSE) assumption mode (SPEC section "shift.py", METHODS 5).

Black-box shift estimation with a cluster-robust confidence box on
``(c0, c1, pi_source, q_target)`` propagated to an odds-ratio interval
``[rho_lo, rho_hi]``; certification tests the worst case over that interval at
``BBSE_DELTA_BET`` while the box spends ``BBSE_DELTA_CONF``, restoring
``1 - delta`` by union bound. Ported from the audited v1 ``fit_a2/certify_a2``
(``../testbed/modes.py``) with the SPEC hardening: bootstrap top-up-or-decline
(audit F40/B-8), q_t range decline (audit F41/B-9), deterministic per-endpoint
permutation streams (supersedes v1's shared-stream pattern), and -- audit V2 --
a confidence share for ``q_t`` itself: the target predicted-positive rate is a
noisy estimate of the target population rate, not an observed constant, and
treating it as exact issued false certificates at up to 3x delta under pure
label shift (isolated by control: with ``q_t`` effectively exact the same code
issued zero false certificates).

Declines (never fallbacks): ``bbse-empty-target`` ->
``bbse-target-clustering`` -> ``bbse-degenerate-bootstrap`` ->
``bbse-ill-conditioned`` -> ``bbse-misspecified``.

Runtime dependencies are ``constants``, ``certify`` and scipy only; ``Cohort``
and ``Head`` are duck-typed at runtime and imported for type hints solely under
``TYPE_CHECKING`` (validate/model are authored in parallel).
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
    """Frozen label-shift correction (METHODS 5). A function of
    ``(head, S_aux, target pool)`` only. ``q_target`` is an ESTIMATE of the
    target population predicted-positive rate carrying sampling error, and it
    receives its own confidence share in the box (audit V2). Scale-invariance
    lets record weights be ``(1, rho)`` with ``rho`` the target/source odds
    ratio of the positive class. ``walk_orders`` maps each alpha to its
    S_aux-derived fixed sequence."""
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
    """Stable-key diagnostics dict (SPEC shift.py; fixture audit 2026-07-25 —
    audit-V25's stable-key discipline extended to the bbse sub-dict).

    Every ``BBSEFit.diagnostics`` — full fit, every decline path, and the
    pipeline's not-run placeholder — carries the SAME key set, with ``None``
    for whatever that branch did not compute: a consumer indexing any key gets
    ``None``, never ``KeyError``. Unknown keys are rejected loudly so the set
    cannot drift silently.
    """
    unknown = set(known) - set(_DIAG_KEYS)
    if unknown:
        raise ValueError(
            f"bbse_diagnostics: unknown keys {sorted(unknown)} -- the stable "
            f"key set is {list(_DIAG_KEYS)}")
    d = {k: None for k in _DIAG_KEYS}
    d.update(known)
    return d


def _q_interval(pred, target_site_id, lvl, rng):
    """Two-sided level-``lvl`` confidence interval for the target population
    predicted-positive rate ``q`` (audit V2).

    ``target_site_id is None`` (or one distinct site) is the caller DECLARING
    the pool is a single site: exact Clopper-Pearson on the record count --
    finite-sample, valid for records iid within one site. A multi-site pool
    with unknown clustering under-covers here and MUST supply
    ``target_site_id``. With >= BBSE_MIN_TARGET_SITES sites: percentile
    cluster bootstrap over target sites (``BBSE_BOOT`` resamples; every
    resample is valid -- ``q`` needs no both-classes constraint; asymptotic
    like the S_aux box). 2..BBSE_MIN_TARGET_SITES-1 sites decline upstream in
    ``fit_bbse`` (verification F1) and never reach this function.
    """
    pred = np.asarray(pred, dtype=bool)
    n = int(pred.shape[0])
    k = int(pred.sum())
    uniq = dense = None
    if target_site_id is not None:
        sid = np.asarray(target_site_id)
        if sid.ndim != 1 or sid.shape[0] != n:
            raise ValueError(
                "fit_bbse: target_site_id must be 1-D and aligned with "
                "target_x (reason=bad-target-site-id)")
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
    """Per-site sufficient statistics ``(n, pos, pred1&pos, pred1&neg)`` stacked
    as ``(4, n_sites)`` via bincount (y is bool by the Cohort contract)."""
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
    """Worst-case odds-ratio interval over the 16 corners of the
    ``(q, c0, c1, pi_s)`` box, plus the point estimate (SPEC shift.py;
    audit V2).

    Corner coverage of the box interior: ``pi_t = (q - c0)/(c1 - c0)`` is
    monotone in each coordinate on the gated region (``c1 - c0 >=
    BBSE_GAP_FLOOR > 0``), rho is monotone in ``pi_t`` and ``pi_s``, and the
    clip preserves monotonicity -- so the extremes over the 4-D box are
    attained at corners. Clip effect (precision, verification F2-bbse):
    coverage of the unclipped odds ratio holds whenever the true ``pi_t`` lies
    in ``[PI_CLIP, 1-PI_CLIP]``; outside that range the exposure is bounded at
    the PI_CLIP odds scale (~1e-4 shift in an affine-in-rho statistic).
    Misspecification declines first (audit F41/B-9).
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
             target_site_id=None) -> BBSEFit:
    """Fit the BBSE confidence box on S_aux + the target pool and propagate it
    to a worst-case odds-ratio interval (SPEC section "shift.py", METHODS 5).

    Bootstrap draws site-index resamples until ``BBSE_BOOT`` VALID ones are
    collected (valid iff the pooled resample has >=1 positive and >=1 negative)
    or ``BBSE_BOOT_MAX_ATTEMPTS`` are exhausted -- in which case decline
    ``bbse-degenerate-bootstrap`` (never quantile over a silently reduced count;
    audit F40/B-8).

    ``q_t`` (audit V2): the target predicted-positive rate is an ESTIMATE of
    the target population rate and gets its own confidence share at level
    ``BBSE_DELTA_CONF / BBSE_BONFERRONI`` -- exact Clopper-Pearson for a
    single-site pool (``target_site_id`` None or one distinct value), a
    cluster bootstrap over target sites otherwise (see ``_q_interval``).

    Decline order: ``bbse-empty-target`` (audit V14) ->
    ``bbse-target-clustering`` (verification F1) ->
    ``bbse-degenerate-bootstrap`` -> ``bbse-ill-conditioned`` when the
    worst-case confusion gap ``lo_c1 - hi_c0 < BBSE_GAP_FLOOR`` ->
    ``bbse-misspecified`` unless the WHOLE q interval sits inside the box
    range ``[lo_c0, hi_c1]`` (audit F41/B-9, widened by V2; the ``not (...)``
    form is NaN-safe, so a non-finite q declines instead of flowing through).
    """
    stats = _site_stats(head, aux)
    n_sites = stats.shape[1]
    n_target = int(np.asarray(target_x).shape[0])
    if n_target == 0:
        return BBSEFit(True, "bbse-empty-target",
                       float("nan"), float("nan"), float("nan"),
                       bbse_diagnostics(n_target=0))
    # q cluster-bootstrap floor (verification F1): a percentile bootstrap over
    # 2..K-1 target sites cannot approach nominal coverage (measured rho-miss
    # up to 46% at K=2 against nominal 2.5%, certify-and-violate at 3.4x delta
    # where the bet has power) -- decline rather than pretend.
    if target_site_id is not None:
        sid = np.asarray(target_site_id)
        if sid.ndim != 1 or sid.shape[0] != n_target:
            raise ValueError(
                "fit_bbse: target_site_id must be 1-D and aligned with "
                "target_x (reason=bad-target-site-id)")
        n_ts = int(len(np.unique(sid)))
        if 2 <= n_ts < BBSE_MIN_TARGET_SITES:
            return BBSEFit(True, "bbse-target-clustering",
                           float("nan"), float("nan"), float("nan"),
                           bbse_diagnostics(
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
        return BBSEFit(True, "bbse-degenerate-bootstrap",
                       float("nan"), float("nan"), float("nan"),
                       bbse_diagnostics(n_target=n_target, q_target=q_t,
                                        n_boot=len(valid),
                                        n_attempts=n_attempts))

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
        return BBSEFit(True, "bbse-ill-conditioned",
                       float("nan"), float("nan"), float("nan"), diag)

    if not (lo[0] <= q_lo and q_hi <= hi[1]):          # q interval in box range
        return BBSEFit(True, "bbse-misspecified",
                       float("nan"), float("nan"), float("nan"), diag)

    rho_lo, rho_hi, rho_point = rho_box_interval(q_lo, q_hi, q_t, lo, hi,
                                                 point)
    diag.update(rho_lo=rho_lo, rho_hi=rho_hi, rho_point=rho_point)

    # walk orders from point-rho-weighted S_aux atoms (S_cal-independent;
    # in-sample flattery here affects power only, never validity)
    score_aux = head.score(aux.x)
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


def certify_bbse(head: "Head", fit: BBSEFit, cal: "Cohort", alpha) -> dict:
    """BBSE certification for one alpha rung (SPEC section "shift.py",
    METHODS 5). Decline passthrough when the fit declined; otherwise a
    dual-endpoint fixed-sequence walk at ``BBSE_DELTA_BET`` where each threshold
    passes only if the betting test rejects at BOTH ``rho_lo`` and ``rho_hi``
    atom sets. Soundness: under the per-endpoint normalization
    ``wmax=max(1,rho)`` the atom mean is piecewise in ``rho`` (kink at 1; an
    interior max is possible), but the statistic is scale-invariant, so
    ``sign(E[Z]-alpha) = sign(A + rho*B)`` with ``(A, B)`` rho-free -- affine
    in ``rho``. The certifiable set ``{rho: E[Z] <= alpha}`` is thus convex:
    certifying both endpoints covers every interior ``rho``, and a violating
    ``rho`` in the box forces a violating endpoint whose level-``BBSE_DELTA_BET``
    test controls false certification.

    Per-endpoint permutation streams are ``certification_rng(alpha, MODE_BBSE,
    "lo")`` and ``"hi"`` -- deterministic, order-independent, and free of any
    target identifier (audit V3; the fit itself remains legitimately
    target-dependent through the q_t interval, which is why the shared-event
    clause is claimed for baseline mode only).
    """
    n_cal_sites = cal.n_sites
    n_carrying = int((cal.site_sizes > 0).sum())
    if fit.declined:
        return dict(alpha=alpha, tau=None, tau_idx=None, certified=[],
                    reason=fit.reason, n_cal=n_cal_sites,
                    n_cal_carrying=n_carrying, diagnostics=fit.diagnostics)

    score = head.score(cal.x)
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
        return dict(alpha=alpha, tau=None, tau_idx=None, certified=[],
                    reason="failsafe", n_cal=n_cal_sites,
                    n_cal_carrying=n_carrying, diagnostics=fit.diagnostics)

    deployed = min(certified, key=lambda t: TAU_GRID[t])
    return dict(alpha=alpha, tau=float(TAU_GRID[deployed]), tau_idx=deployed,
                certified=certified, reason=None, n_cal=n_cal_sites,
                n_cal_carrying=n_carrying, diagnostics=fit.diagnostics)
