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
exactly for declined cases. Declined cases additionally carry an exact
contrastive artifact (``counterfactual_to_answer``): the closed-form minimal
move -- whole-vector or single-feature -- that would make the case answerable,
a score-space recourse statement, never a clinical recommendation.
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


# Headroom added to the flip target in logit space. A delta landing EXACTLY on
# |logit| = L* is DECLINED by the deployed float64 rule ``head.score(x) >= tau``
# on a measurable fraction of cases: sigmoid(log(tau/(1-tau))) < tau in float64
# for 6 of the 23 frozen TAU_GRID thresholds (1 ULP each), summation-order noise
# between the attribution sum and Head.logit's BLAS dot reaches ~3e-14, and the
# raw-space round trip adds ~1e-12 (adversarial verification 2026-07-31: exact
# landings failed the deployed rule on 18.2% of fixture-head declines). 1e-9
# dominates every measured shortfall; realized confidence moves by < 3e-10.
_EPS_ANSWER_LOGIT = 1e-9


def counterfactual_to_answer(head: "Head", x_row, tau_star) -> dict:
    """Minimal counterfactuals into the answer region (SPEC explain.py).

    The head is linear in standardized space, so "what is the smallest change
    that would make this case answerable?" has a closed-form answer. For a
    declined case with margin ``m = L* - |logit| > 0`` on its current side
    ``s = sign(logit)`` (tie at 0 -> +1):

    - minimal standardized-L2 move: direction ``s*coef``, exact minimal
      distance ``m/||coef||_2`` (no move of smaller norm flips, in any
      direction: Cauchy-Schwarz);
    - single-feature counterfactual: ``delta_z_j = s*m/coef_j`` (raw units
      ``delta_x_j = sd_j * delta_z_j``), ``inf`` where ``coef_j == 0``.

    The REPORTED distances are those exact minima; the RETURNED delta vectors
    are computed from ``m + _EPS_ANSWER_LOGIT`` so the flip holds under the
    DEPLOYED answering rule ``head.score(x_cf) >= tau_star`` in float64 -- an
    exact landing on the bar provably does not (see ``_EPS_ANSWER_LOGIT``).
    ``flip_verified`` re-evaluates that deployed rule with no tolerance.
    ``confidence_at_flip`` is the realized ``head.score`` at the flipped
    point -- the WEAKEST answerable answer, within ~3e-10 above ``tau_star``
    -- and ``answered_class_on_flip`` the current side's predicted class;
    both are None unless the case was declined and the flip verified.

    These are SCORE-SPACE recourse statements about the gate, never causal or
    clinically achievable actions: features are not independently manipulable
    (a missingness indicator cannot "move 0.4"), and the artifact answers
    "what would the gate need", not "what should the clinician do". Answered
    cases return zero deltas, distance 0 and an EMPTY ranking (never the
    argsort-of-degenerate identity permutation -- audit V22 pattern); an
    all-zero head cannot flip (distance ``inf``, ``flip_verified`` False).
    """
    attr = local_attribution(head, x_row)
    logit = attr["logit"]
    l_star = float(np.log(tau_star / (1.0 - tau_star)))
    margin = l_star - abs(logit)
    declined = bool(margin > 0)
    m = max(margin, 0.0)
    m_eff = m + _EPS_ANSWER_LOGIT if declined else 0.0
    s = 1.0 if logit >= 0 else -1.0
    coef = np.asarray(head.coef, dtype=np.float64)
    sd = np.asarray(head.sd, dtype=np.float64)
    coef_norm2 = float(coef @ coef)

    if coef_norm2 > 0.0:
        delta_z_min = (s * m_eff / coef_norm2) * coef
        l2_distance_z = m / float(np.sqrt(coef_norm2))
        opposite_z = (l_star + abs(logit)) / float(np.sqrt(coef_norm2))
    else:
        delta_z_min = np.zeros_like(coef)
        l2_distance_z = float("inf") if declined else 0.0
        opposite_z = float("inf")

    if declined:
        with np.errstate(divide="ignore"):
            single_z = np.where(coef != 0.0, s * m_eff / coef, np.inf)
        finite = np.isfinite(single_z)
        order = np.argsort(np.abs(np.where(finite, single_z, np.inf)),
                           kind="stable")
        ranking = order[finite[order]]
    else:
        single_z = np.zeros_like(coef)
        ranking = np.array([], dtype=np.int64)
    single_x = sd * single_z
    delta_x_min = sd * delta_z_min

    # the DEPLOYED rule, exactly as pipeline.py compares it -- no tolerance
    x_cf = np.asarray(x_row, dtype=np.float64) + delta_x_min
    score_cf = float(head.score(x_cf.reshape(1, -1))[0])
    flip_verified = bool(score_cf >= tau_star)
    flipped = declined and flip_verified

    return {
        "tau_star": float(tau_star),
        "L_star": l_star,
        "logit": logit,
        "margin_to_answer": margin,
        "declined": declined,
        "direction": s,
        "delta_z_min_l2": delta_z_min,
        "delta_x_min_l2": delta_x_min,
        "l2_distance_z": l2_distance_z,
        "single_feature_delta_z": single_z,
        "single_feature_delta_x": single_x,
        "single_feature_ranking": ranking,
        "opposite_side_distance_z": opposite_z,
        "answered_class_on_flip": bool(s > 0) if flipped else None,
        "confidence_at_flip": score_cf if flipped else None,
        "flip_verified": flip_verified,
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
