"""Certified-gate statistical core (SPEC section "certify.py", METHODS 3-4).

The math is ported verbatim from the audited v1 reference
(``../testbed/certify.py``, which survived adversarial review); the SPEC's
constants and the loud-rejection hardening (isfinite guards on scores and
weights, sha256-only seed rule) override v1 where they differ.

Contents:
  - influence_atoms   linearized per-site atoms Z_c in [0, 1] (METHODS 3)
  - wsr_reject        one-sided Waudby-Smith-Ramdas betting test (METHODS 4)
  - margin_floor      information-theoretic feasibility floor
  - walk_order        S_aux-ordered fixed sequence (most conservative first)
  - fixed_sequence_walk   learn-then-test threshold walk at full delta
  - certification_rng deterministic, unchoosable permutation stream
"""

import hashlib

import numpy as np

from .constants import (SEED, ALPHA_LADDER, WSR_LAMBDA_CAP, WSR_VAR_FLOOR,
                        WSR_MU0, WSR_S2_0)


def influence_atoms(score, err, site_id, n_sites, tau_grid, alpha, M,
                    weights=None, wmax=1.0):
    """Per-site atoms ``Z_c`` in [0, 1], shape ``(n_tau, n_sites)`` (METHODS 3).

    ``Z_c = (g_c / (M*n_c)) * sum_{i in c} ans_i*(err_i - alpha) + alpha`` with
    the data-independent influence weight ``g_c = min(n_c, M)``; ``E[Z] <= alpha
    <=> R_M <= alpha``. Sites with zero answered-eligible records enter as
    NEUTRAL atoms ``Z_c = alpha`` (never dropped -- dropping would redefine the
    cluster population post hoc; a neutral atom dilutes power, never validity).

    Weighted mode (label-shift correction): per-record contributions scale by
    ``w_i / wmax`` with ``w_i`` in ``[0, wmax]``; the certified statistic is
    scale-invariant in ``w`` so the normalization only keeps atoms in range.

    Hardening (SPEC): non-finite scores raise loudly (audit F36); the NaN-bypass
    on weights is closed -- weights must be finite and within ``[0, wmax]``
    (audit F08).
    """
    score = np.asarray(score, dtype=float)
    if not np.isfinite(score).all():
        raise ValueError(
            "influence_atoms: score contains non-finite values "
            "(reason=nonfinite-score)")
    sizes = np.bincount(site_id, minlength=n_sites).astype(float)
    # empty (screened-out) sites -> zero influence -> neutral atom == alpha
    g_over_Mn = np.where(sizes > 0,
                         np.minimum(sizes, M) / (M * np.maximum(sizes, 1.0)),
                         0.0)
    base = np.where(err, 1.0 - alpha, -alpha)
    if weights is not None:
        w = np.asarray(weights, dtype=float)
        if (not np.isfinite(w).all()) or w.min() < 0.0 or w.max() > wmax + 1e-12:
            raise ValueError(
                "influence_atoms: weights must be finite and in [0, wmax] "
                "(reason=bad-weights)")
        base = base * (w / wmax)
    out = np.empty((len(tau_grid), n_sites))
    for t, tau in enumerate(tau_grid):
        ans = score >= tau
        s = np.bincount(site_id, weights=base * ans, minlength=n_sites)
        out[t] = g_over_Mn * s + alpha
    return out


def wsr_reject(z, alpha, delta, rng=None):
    """One-sided WSR betting test of ``H0: E[Z] >= alpha`` (METHODS 4).

    CERTIFY (return True) iff the wealth process ``K_t = prod (1 + lam_s
    (alpha - Z_s))`` sup-crosses ``1/delta`` -- Ville's inequality gives
    finite-sample level ``delta``. ``lam_t`` is predictable and variance
    adaptive with the audited cap ``WSR_LAMBDA_CAP/(1-alpha)``, variance floor
    ``WSR_VAR_FLOOR``, running ``(mu, s2)`` initialized ``(WSR_MU0, WSR_S2_0)``.
    ``rng`` supplies the prespecified permutation (SPEC seed rule).
    """
    z = np.asarray(z, dtype=float)
    if rng is not None:
        z = rng.permutation(z)
    n = len(z)
    log_inv_delta = np.log(1.0 / delta)
    log_wealth = 0.0
    mu, s2, cnt = WSR_MU0, WSR_S2_0, 1.0
    lam_cap = WSR_LAMBDA_CAP / (1.0 - alpha)
    for t in range(n):
        lam = min(np.sqrt(2.0 * log_inv_delta / (max(s2, WSR_VAR_FLOOR) * n)),
                  lam_cap)
        log_wealth += np.log(max(1.0 + lam * (alpha - z[t]), 1e-300))
        if log_wealth >= log_inv_delta:
            return True                       # sup-crossing: Ville covers it
        cnt += 1.0
        mu += (z[t] - mu) / cnt
        s2 += ((z[t] - mu) ** 2 - s2) / cnt
    return False


def margin_floor(n, delta, alpha):
    """Information-theoretic feasibility floor (METHODS 4): no valid level-delta
    test of a [0,1]-bounded mean certifies with margin below
    ``ln(1/delta) * (1 - alpha) / n``. Reported as a diagnostic, never a gate."""
    return np.log(1.0 / delta) * (1.0 - alpha) / n


def walk_order(atoms_aux):
    """Fixed-sequence order from S_aux atoms (METHODS 4): ascending mean atom,
    i.e. most-conservative (largest estimated certification margin) first.
    Data-independent of S_cal, so it spends no multiplicity budget."""
    return np.argsort(atoms_aux.mean(axis=1))


def fixed_sequence_walk(atoms, order, alpha, delta, tau_grid, rng=None):
    """Learn-then-test threshold walk (METHODS 4). Tests thresholds in the
    prespecified ``order`` at full ``delta``, stopping at the first failure;
    returns ``(certified tau-index list, deployed index or None)`` with
    deployed = maximum-coverage (lowest tau) in the certified prefix."""
    certified = []
    for t in order:
        if wsr_reject(atoms[t], alpha, delta, rng=rng):
            certified.append(int(t))
        else:
            break
    if not certified:
        return [], None
    deployed = min(certified, key=lambda t: tau_grid[t])
    return certified, deployed


def certification_rng(alpha, mode_idx, stream=""):
    """Prespecified, unchoosable permutation stream (SPEC seed rule; METHODS 4).

    sha256-ONLY (audit B-10): the stream discriminator is hashed and its first
    eight bytes spread across two 32-bit SeedSequence entries. There is no
    ``int()`` fast path, so no numeric aliasing and no ``OverflowError`` on odd
    inputs (audit F43/F57). Deterministic in the frozen inputs and run identity.

    The TARGET LABEL is deliberately NOT part of the seed (audit V3): baseline
    atoms are target-independent, so a label-seeded permutation gave every
    target a separately randomized test of identical calibration data -- the
    deployed threshold moved with the spelling of a free-text identifier and
    the shared-1-delta-event clause printed on the certificate was false.
    ``stream`` distinguishes only the BBSE endpoint walks (``"lo"`` / ``"hi"``);
    the baseline walk passes the default ``""``.
    """
    h = hashlib.sha256(str(stream).encode()).digest()
    return np.random.default_rng(np.random.SeedSequence(
        [SEED, ALPHA_LADDER.index(alpha), mode_idx,
         int.from_bytes(h[:4], "big"), int.from_bytes(h[4:8], "big")]))
