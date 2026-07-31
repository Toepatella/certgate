"""SPEC section "model.py": logistic head with internal guarded standardization.

The head stores the training standardization ``(mu, sd)`` and standardizes RAW
``x`` internally on every call -- callers pass raw features to ``logit`` /
``predict_proba`` / ``predict`` / ``score``. Standardization uses a
relative-tolerance guard on ``sd`` (audit F06), so a near-constant column is
divided by 1.0 rather than by a numerically-zero standard deviation.

The score only ranks; certificate validity never depends on the head's quality
or calibration (METHODS section 6).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from sklearn.linear_model import LogisticRegression

from certgate.constants import HEAD_C, HEAD_MAX_ITER, SD_REL_TOL

if TYPE_CHECKING:                      # annotation only -- keeps model runtime-free of validate
    from certgate.validate import Cohort


def _sigmoid(z):
    z = np.asarray(z, dtype=np.float64)
    with np.errstate(over="ignore"):
        return np.where(z >= 0, 1.0 / (1.0 + np.exp(-z)), np.exp(z) / (1.0 + np.exp(z)))


@dataclass
class Head:
    """Fitted logistic head (SPEC model.py). ``sd`` is already the guarded ``sd_safe``."""

    coef: np.ndarray        # (d,) standardized-space coefficients
    intercept: float
    mu: np.ndarray          # (d,) training feature means
    sd: np.ndarray          # (d,) guarded training standard deviations

    def logit(self, x):
        """Decision logit on RAW ``x`` (standardized internally with stored mu/sd)."""
        x = np.asarray(x, dtype=np.float64)
        z = (x - self.mu) / self.sd
        return self.intercept + z @ self.coef

    def predict_proba(self, x):
        """P(y=1 | x) on RAW ``x``."""
        return _sigmoid(self.logit(x))

    def predict(self, x):
        """Hard label (p1 >= 0.5) on RAW ``x``."""
        return self.predict_proba(x) >= 0.5

    def score(self, x):
        """Selective-prediction confidence score max(p1, 1-p1) in [0.5, 1] on RAW ``x``."""
        p1 = self.predict_proba(x)
        return np.maximum(p1, 1.0 - p1)


def fit_head(train: "Cohort") -> Head:
    """Fit the L2 logistic head on standardized training features (SPEC model.py).

    ``mu, sd`` come from ``train``; the guarded ``sd_safe`` replaces any column
    whose ``sd`` fails the relative tolerance ``SD_REL_TOL * max(1, |mu|)`` with
    1.0 (audit F06). sklearn ``LogisticRegression(C=HEAD_C, max_iter=HEAD_MAX_ITER)``
    is fit on the standardized ``z``; the returned Head standardizes raw ``x`` the
    same way.
    """
    x = np.asarray(train.x, dtype=np.float64)
    mu = x.mean(axis=0)
    sd = x.std(axis=0)
    sd_safe = np.where(sd > SD_REL_TOL * np.maximum(1.0, np.abs(mu)), sd, 1.0)
    z = (x - mu) / sd_safe
    clf = LogisticRegression(C=HEAD_C, max_iter=HEAD_MAX_ITER)
    clf.fit(z, np.asarray(train.y))
    coef = clf.coef_.ravel().astype(np.float64)
    intercept = float(clf.intercept_[0])
    return Head(coef=coef, intercept=intercept, mu=mu, sd=sd_safe)
