"""Logistic head that standardizes its own inputs.

The head stores the training standardization (mu, sd) and applies it on every
call, so callers always pass RAW features to logit / predict_proba / predict /
score. A relative-tolerance guard on sd divides a near-constant column by 1.0
rather than by a numerically-zero standard deviation.

The score only ranks. Certificate validity never depends on how good or how
well-calibrated the head is.

Refs: SPEC "model.py"; METHODS 6; audit F06.
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
    """A fitted logistic head. sd is already the guarded sd_safe."""

    coef: np.ndarray        # (d,) standardized-space coefficients
    intercept: float
    mu: np.ndarray          # (d,) training feature means
    sd: np.ndarray          # (d,) guarded training standard deviations

    def logit(self, x):
        """Decision logit on RAW x, standardized internally with the stored mu/sd."""
        x = np.asarray(x, dtype=np.float64)
        z = (x - self.mu) / self.sd
        return self.intercept + z @ self.coef

    def predict_proba(self, x):
        """P(y=1 | x) on RAW x."""
        return _sigmoid(self.logit(x))

    def predict(self, x):
        """Hard label (p1 >= 0.5) on RAW x."""
        return self.predict_proba(x) >= 0.5

    def score(self, x):
        """Selective-prediction confidence, max(p1, 1-p1) in [0.5, 1], on RAW x."""
        p1 = self.predict_proba(x)
        return np.maximum(p1, 1.0 - p1)


def fit_head(train: "Cohort") -> Head:
    """Fit the L2 logistic head on standardized training features.

    mu and sd come from train. The guarded sd_safe replaces sd with 1.0 for any
    column that fails the relative tolerance SD_REL_TOL * max(1, |mu|).

    sklearn's LogisticRegression(C=HEAD_C, max_iter=HEAD_MAX_ITER) is fit on
    the standardized z, and the returned Head standardizes raw x the same way.

    Refs: SPEC "model.py"; audit F06.
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
