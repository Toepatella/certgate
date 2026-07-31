"""SPEC section "explain.py": attributions, abstention explanations, composition.

For the linear head the additive attributions ``phi_j = coef_j * z_j`` (in
standardized space) are exact INTERVENTIONAL Shapley values with the S_train
feature-mean baseline (the Linear SHAP result) -- ``sum(phi) + intercept ==
logit`` to machine precision, no sampling (METHODS section 6). The value
function must be named (audit V20): under correlated features the CONDITIONAL
Shapley values differ from these, and the efficiency identity does not
distinguish the two (both decompositions satisfy it). Abstentions are explained
against the answering bar ``L* = log(tau*/(1-tau*))``: answering requires
``|logit| >= L*``, so the margin-to-answer is ``L* - |logit|`` and is ``> 0``
exactly for declined cases.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:                      # annotation only
    from certgate.model import Head


def _sigmoid_scalar(z: float) -> float:
    if z >= 0:
        return float(1.0 / (1.0 + np.exp(-z)))
    ez = np.exp(z)
    return float(ez / (1.0 + ez))


def _standardize(head: "Head", x_row) -> np.ndarray:
    x_row = np.asarray(x_row, dtype=np.float64)
    return (x_row - head.mu) / head.sd


def global_importance(head: "Head") -> np.ndarray:
    """Standardized-space coefficients -- direction and strength per feature (SPEC explain.py).

    The head's ``coef`` already lives in standardized space, so it IS the global
    importance vector (METHODS section 6, "standardized coefficients").
    """
    return np.asarray(head.coef, dtype=np.float64)


def local_attribution(head: "Head", x_row) -> dict:
    """Exact additive attributions for one case (SPEC explain.py).

    Returns ``base`` (intercept), ``phi`` (``coef_j * z_j``), ``logit`` and
    ``p1``, with ``sum(phi) + base == logit`` exact by construction.
    ``phi`` are the INTERVENTIONAL Shapley values of the linear logit with the
    S_train feature-mean baseline (Linear SHAP; audit V20) -- exact for that
    value function, and distinct from conditional Shapley values whenever
    features are correlated.
    """
    z = _standardize(head, x_row)
    phi = head.coef * z
    base = float(head.intercept)
    logit = base + float(phi.sum())
    return {"base": base, "phi": phi, "logit": logit, "p1": _sigmoid_scalar(logit)}


def abstention_explanation(head: "Head", x_row, tau_star) -> dict:
    """Explain why a case is answered or declined at threshold ``tau_star`` (SPEC explain.py).

    ``L* = log(tau*/(1-tau*))``; answering requires ``|logit| >= L*``. Reports the
    signed margin-to-answer (``> 0`` iff declined) and each feature's signed
    contribution toward (or away from) the decided-class confidence.
    """
    attr = local_attribution(head, x_row)
    logit = attr["logit"]
    l_star = float(np.log(tau_star / (1.0 - tau_star)))
    margin_to_answer = l_star - abs(logit)
    direction = 1.0 if logit >= 0 else -1.0
    toward_confidence = attr["phi"] * direction     # >0 builds confidence, <0 erodes it
    return {
        "tau_star": float(tau_star),
        "L_star": l_star,
        "logit": logit,
        "abs_logit": abs(logit),
        "margin_to_answer": margin_to_answer,
        "declined": bool(margin_to_answer > 0),
        "phi": attr["phi"],
        "toward_confidence": toward_confidence,
        "p1": attr["p1"],
    }


def cohort_abstention_profile(head: "Head", x, answered_mask) -> dict:
    """Mean ``|phi_j|`` for answered vs declined populations + gap ranking (SPEC explain.py).

    Identifies systematic abstention drivers: features whose typical magnitude of
    contribution differs most between answered and declined cases.
    """
    x = np.asarray(x, dtype=np.float64)
    answered_mask = np.asarray(answered_mask, dtype=bool)
    z = (x - head.mu) / head.sd
    abs_phi = np.abs(z * head.coef)                 # (n, d)
    declined_mask = ~answered_mask
    d = head.coef.shape[0]
    mean_ans = abs_phi[answered_mask].mean(axis=0) if answered_mask.any() else np.full(d, np.nan)
    mean_dec = abs_phi[declined_mask].mean(axis=0) if declined_mask.any() else np.full(d, np.nan)
    gap = mean_ans - mean_dec
    # when either population is empty the gap is undefined: the ranking is
    # EMPTY, never argsort of all-NaN -- which returns the identity permutation
    # and fabricates feature 0 as the top abstention driver (audit V22).
    if np.isnan(gap).all():
        gap_ranking = np.array([], dtype=np.int64)
    else:
        gap_ranking = np.argsort(-np.abs(gap))
    return {
        "mean_abs_phi_answered": mean_ans,
        "mean_abs_phi_declined": mean_dec,
        "gap": gap,
        "gap_ranking": gap_ranking,
        "n_answered": int(answered_mask.sum()),
        "n_declined": int(declined_mask.sum()),
    }


def composition(head: "Head", target_x, answered_mask, rho_point=None, oracle_y=None) -> dict:
    """Answered-set class composition, reported up to three tagged ways (SPEC explain.py; audit F25).

    ``predicted_class`` (estimated): fraction the head calls positive.
    ``bbse_true_class`` (estimated, label-shift-tagged, only if ``rho_point`` given):
    the label-shift-corrected true-positive fraction, obtained by re-weighting the
    source posterior odds by ``rho`` per record.
    ``oracle_true_class`` (diagnostic, only if ``oracle_y`` given): the realized
    true-positive fraction from oracle labels -- reveals whether a certificate was
    earned by answering only easy negatives.
    """
    target_x = np.asarray(target_x, dtype=np.float64)
    answered_mask = np.asarray(answered_mask, dtype=bool)
    n_ans = int(answered_mask.sum())
    pred = head.predict(target_x)

    pred_pos = int((np.asarray(pred, dtype=bool) & answered_mask).sum())
    out = {
        "predicted_class": {
            "tag": "estimated",
            "positive_fraction": (pred_pos / n_ans) if n_ans else float("nan"),
            "n_positive": pred_pos,
            "n_answered": n_ans,
        }
    }

    if rho_point is not None:
        p_s = np.asarray(head.predict_proba(target_x), dtype=np.float64)
        odds_s = p_s / np.clip(1.0 - p_s, 1e-12, None)
        odds_t = float(rho_point) * odds_s
        p_t = odds_t / (1.0 + odds_t)
        out["bbse_true_class"] = {
            "tag": "estimated (label-shift assumption)",
            "positive_fraction": float(p_t[answered_mask].mean()) if n_ans else float("nan"),
            "expected_n_positive": float(p_t[answered_mask].sum()) if n_ans else float("nan"),
            "rho": float(rho_point),
            "n_answered": n_ans,
        }

    if oracle_y is not None:
        oracle_y = np.asarray(oracle_y, dtype=bool)
        opos = int((oracle_y & answered_mask).sum())
        out["oracle_true_class"] = {
            "tag": "diagnostic (oracle)",
            "positive_fraction": (opos / n_ans) if n_ans else float("nan"),
            "n_positive": opos,
            "n_answered": n_ans,
        }

    return out
