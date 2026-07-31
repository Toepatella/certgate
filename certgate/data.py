"""SPEC section "data.py": simplified synthetic multi-site generator + site splits.

Ports the exact-shift semantics of ``../testbed/generator.py`` (METHODS section 7)
but drops the covariate-delta, missingness/availability, and oracle latent/site
machinery -- a Cohort holds only ``x, y, site_id, site_labels``.

Generative model (chosen so each shift is EXACT, not approximate):
  Site c:   size n_c ~ clipped LogNormal(size_mu, size_sigma);
            random effect u_c ~ N(0, s_u^2) on the log-odds base rate;
            pi_c = sigmoid(logit(base) + u_c).
  Record:   class-conditional Gaussians x | y ~ N(mu_y, I_d), symmetric means
            mu_1 = +sep/2 * v, mu_0 = -sep/2 * v (v unit) -- Bayes-exact logistic
            posterior logit P(y=1 | x, c) = logit(pi_c) + sep * (v . x).

Shift paths:
  label shift    class-conditional path with a shifted site-level base rate
                 (P(x|y) invariant -- the BBSE assumption, exactly).
  concept shift  marginal-then-posterior path: draw the site mixture, then tilt
                 the posterior logit by concept_intercept + concept_slope . x
                 (neither exchangeability nor label shift holds).
Label shift composing with concept tilt is the unidentifiable regime and raises
``ValueError`` by design.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from certgate.constants import SPLIT_FRACTIONS
from certgate.validate import Cohort, CohortError, make_cohort


def _sigmoid(z):
    z = np.asarray(z, dtype=np.float64)
    with np.errstate(over="ignore"):
        return np.where(z >= 0, 1.0 / (1.0 + np.exp(-z)), np.exp(z) / (1.0 + np.exp(z)))


def _logit(p):
    p = np.asarray(p, dtype=np.float64)
    return np.log(p / (1.0 - p))


@dataclass
class SimConfig:
    """Frozen generator parameters (SPEC data.py). Defaults match METHODS section 1."""

    d: int = 8
    sep: float = 2.2
    base_rate: float = 0.095
    s_u: float = 0.5
    size_mu: float = 6.0
    size_sigma: float = 1.1
    size_lo: int = 20
    size_hi: int = 5000

    def direction(self) -> np.ndarray:
        """Unit signal direction v = normalized ones on the first ``d//2`` dims."""
        v = np.zeros(self.d)
        v[: max(1, self.d // 2)] = 1.0
        return v / np.linalg.norm(v)

    def mu(self, y) -> np.ndarray:
        """Class-conditional mean mu_y = (+/- sep/2) * v."""
        return (0.5 if y else -0.5) * self.sep * self.direction()

    def posterior_logit(self, x, pi_site) -> np.ndarray:
        """Bayes-exact source posterior logit P(y=1 | x, site)."""
        w = self.sep * self.direction()
        return _logit(pi_site) + x @ w


def draw_cohort(cfg: SimConfig, n_sites: int, rng, *, label_base_rate=None,
                concept_intercept: float = 0.0, concept_slope=None,
                site_label_prefix: str = "s",
                require_both_classes: bool = True) -> Cohort:
    """Draw a multi-site Cohort (SPEC data.py).

    Class-conditional exact path when there is no concept tilt (pure label shift
    when ``label_base_rate`` is set); marginal-then-posterior path for concept
    tilt (``../testbed/generator.py`` lines 130-159 semantics). Composing a
    ``label_base_rate`` with a concept tilt raises ``ValueError`` -- the
    unidentifiable regime. Site labels ``f"{prefix}-{i:04d}"`` guarantee
    disjointness across distinct prefixes.
    """
    concept = (concept_intercept != 0.0) or (concept_slope is not None)
    if label_base_rate is not None and concept:
        raise ValueError(
            "label_base_rate composes only with the class-conditional (label-shift) path; "
            "combined label + concept shift is the unidentifiable regime by design")

    sizes = np.clip(
        np.exp(rng.normal(cfg.size_mu, cfg.size_sigma, n_sites)),
        cfg.size_lo, cfg.size_hi).astype(int)
    u = rng.normal(0.0, cfg.s_u, n_sites)
    n = int(sizes.sum())
    site_id = np.repeat(np.arange(n_sites), sizes)
    u_rec = u[site_id]

    base = cfg.base_rate if label_base_rate is None else label_base_rate
    pi_site_rec = _sigmoid(_logit(base) + u_rec)

    if not concept:
        # class-conditional path: exact for source AND pure label shift.
        y = rng.random(n) < pi_site_rec
        x = rng.normal(0.0, 1.0, (n, cfg.d)) + np.where(y[:, None], cfg.mu(1), cfg.mu(0))
    else:
        # marginal-then-posterior path: site mixture then posterior tilt.
        mix = rng.random(n) < pi_site_rec
        x = rng.normal(0.0, 1.0, (n, cfg.d)) + np.where(mix[:, None], cfg.mu(1), cfg.mu(0))
        lg = cfg.posterior_logit(x, pi_site_rec) + concept_intercept
        if concept_slope is not None:
            lg = lg + x @ np.asarray(concept_slope, dtype=np.float64)
        y = rng.random(n) < _sigmoid(lg)

    labels = tuple(f"{site_label_prefix}-{i:04d}" for i in range(n_sites))
    return make_cohort(x, y.astype(bool), site_id, site_labels=labels,
                       expect_features=cfg.d,
                       require_both_classes=require_both_classes)


def subset_sites(cohort: Cohort, keep_dense_ids) -> Cohort:
    """Keep only the named sites, renumbering densely and carrying labels (SPEC data.py)."""
    keep = np.unique(np.asarray(keep_dense_ids, dtype=np.int64))    # sorted, unique
    if keep.size and (keep.min() < 0 or keep.max() >= cohort.n_sites):
        raise CohortError("subset_sites: keep id out of range 0..n_sites-1")
    keep_mask = np.zeros(cohort.n_sites, dtype=bool)
    keep_mask[keep] = True
    rec_mask = keep_mask[cohort.site_id]
    remap = np.full(cohort.n_sites, -1, dtype=np.int64)
    remap[keep] = np.arange(keep.size)
    new_site_id = remap[cohort.site_id[rec_mask]]
    new_labels = tuple(cohort.site_labels[i] for i in keep.tolist())
    return make_cohort(cohort.x[rec_mask], cohort.y[rec_mask], new_site_id, site_labels=new_labels)


def split_sites(cohort: Cohort, rng) -> tuple[Cohort, Cohort, Cohort]:
    """Partition sites into ``(train, aux, cal)`` by ``SPLIT_FRACTIONS``, site-disjoint.

    Implements the METHODS section 2 discipline: a random permutation of sites is
    cut 40/20/40; the calibration cohort takes the remainder so every site is
    assigned exactly once.
    """
    n_sites = cohort.n_sites
    perm = rng.permutation(n_sites)
    f_train, f_aux, _ = SPLIT_FRACTIONS
    n_train = int(round(f_train * n_sites))
    n_aux = int(round(f_aux * n_sites))
    train_ids = perm[:n_train]
    aux_ids = perm[n_train:n_train + n_aux]
    cal_ids = perm[n_train + n_aux:]
    return (subset_sites(cohort, train_ids),
            subset_sites(cohort, aux_ids),
            subset_sites(cohort, cal_ids))
