"""The V21/V16 fixes need tests that would go red on revert.

Four things were silently revertible at 110/110 green:
  - _bootstrap_estimate's top-up-or-decline discipline
  - the NaN-not-0.0 empty answered set
  - _feasibility's None-not-inf sentinels
  - render_text's n_boot surfacing

Refs: verification N1.
"""
import json

import numpy as np

from certgate.constants import M_INFLUENCE
from certgate.data import SimConfig, draw_cohort, split_sites
from certgate.model import fit_head, Head
from certgate.report import _bootstrap_estimate, _rm_vs_unweighted, render_text
from certgate.pipeline import _feasibility, run_certgate
from certgate.validate import Cohort


def _head_cal():
    cfg = SimConfig()
    rng = np.random.default_rng(31)
    coh = draw_cohort(cfg, 60, rng)
    train, _, cal = split_sites(coh, rng)
    return fit_head(train), cal


def test_bootstrap_estimate_tops_up_to_full_count():
    """Resamples with zero answered mass are topped up, never dropped.

    With a reachable tau the draw count must be exactly n_boot. A drop-only
    loop yields fewer whenever any resample has zero answered mass.
    """
    head, cal = _head_cal()
    est = _bootstrap_estimate(head, cal, 0.55, n_boot=200)
    assert est["n_boot"] == 200
    assert est["n_attempts"] >= 200
    assert np.isfinite(est["point"])
    assert np.isfinite(est["ci95"]).all()


def test_bootstrap_estimate_declines_on_topup_shortfall():
    """The top-up-or-decline discipline itself.

    When fewer than n_boot valid resamples arrive within the attempt budget,
    the CI must be NaN, never a quantile over the reduced count.

    max_attempts pinches the budget so the shortfall regime is
    deterministically reachable. A revert to 'quantile whatever arrived'
    produces a finite CI here and fails.

    Refs: audit V21; verification N1.
    """
    head, cal = _head_cal()
    est = _bootstrap_estimate(head, cal, 0.55, n_boot=200, max_attempts=10)
    assert 0 < est["n_boot"] < 200                 # some arrived, not enough
    assert np.isnan(est["ci95"]).all()             # declined, not reduced
    assert np.isfinite(est["point"])               # the point is still real


def test_bootstrap_estimate_empty_answered_set_is_nan_not_zero():
    """A tau answering nothing yields NaN, never 0.0 (audit V21).

    Zero risk and no evidence are different claims.
    """
    head, cal = _head_cal()
    est = _bootstrap_estimate(head, cal, 1.01)     # nothing answers
    assert np.isnan(est["point"])
    assert np.isnan(est["ci95"]).all()
    assert est["n_boot"] == 0


def test_feasibility_reports_none_not_inf_when_no_coverage():
    """A head answering nothing reports margin and ratio as None (audit V16).

    None serializes as JSON null. -inf is invalid strict JSON, and reads as a
    very bad but real margin.
    """
    _, cal = _head_cal()
    flat = Head(coef=np.zeros(cal.d), intercept=0.0, mu=np.zeros(cal.d),
                sd=np.ones(cal.d))                 # score == 0.5 < every tau
    feas = _feasibility(flat, cal, 0.10, n_carrying=50)
    assert feas["margin"] is None and feas["ratio"] is None
    json.dumps(feas, allow_nan=False)              # strict-JSON serialisable


def test_render_text_surfaces_n_boot_and_handles_gated_reports():
    """render_text shows the estimated tier's n_boot (audit V21).

    It must also not crash on a gated report (audit V25).
    """
    cfg = SimConfig()
    rng = np.random.default_rng(20260721)
    coh = draw_cohort(cfg, 208, rng)
    train, aux, cal = split_sites(coh, rng)
    tgt = draw_cohort(cfg, 1, rng, site_label_prefix="rt")
    rep = run_certgate(train, aux, cal, tgt.x, target_label="render")
    text = render_text(rep)
    assert "n_boot=" in text
    # the estimated tier names its estimand (audit 2026-10 CORE-5)
    assert "[estimated] record-pooled answered-set risk on S_cal" in text
    # the partition line includes the answered count, so its label must not
    # read as a decline count (fixture audit 2026-07-25)
    assert "[partition]" in text
    assert "[declines]" not in text
    gated = run_certgate(train, aux, cal, tgt.x[:5], target_label="gated")
    assert "[gate]" in render_text(gated)          # no KeyError on gated path


def test_estimated_point_is_record_pooled_not_rm():
    """The estimated tier is the record-pooled answered risk, not R_M.

    Every answered S_cal record counts once, with no influence cap. R_M,
    whose S_cal plug-in is rm_vs_unweighted's r_m, caps each site at M and
    differs whenever some calibration site exceeds M.

    Ref: audit 2026-10 CORE-5.
    """
    head, cal = _head_cal()
    tau = 0.55
    score = head.score(cal.x)
    ans = score >= tau
    err = head.predict(cal.x) != cal.y
    assert (cal.site_sizes > M_INFLUENCE).any()
    est = _bootstrap_estimate(head, cal, tau)
    rm = _rm_vs_unweighted(head, cal, tau)
    assert est["point"] == float(err[ans].sum() / ans.sum())
    assert est["point"] == rm["unweighted_risk"]
    sizes = cal.site_sizes.astype(np.float64)
    g = np.minimum(sizes, M_INFLUENCE)
    a_c = np.bincount(cal.site_id, weights=ans, minlength=cal.n_sites)
    e_c = np.bincount(cal.site_id, weights=ans & err, minlength=cal.n_sites)
    keep = sizes > 0
    want = float((g[keep] * e_c[keep] / sizes[keep]).sum()
                 / (g[keep] * a_c[keep] / sizes[keep]).sum())
    assert abs(rm["r_m"] - want) < 1e-12
    assert rm["r_m"] != est["point"]


def test_rm_gap_isolates_the_influence_cap_under_bbse_weights():
    """Both sides of the R_M gap carry the deploy-mode class weights.

    With every site at or below M the influence weights are all 1, so the gap
    must be exactly 0 under any class weights. The old plain record mean
    folded the BBSE class reweighting into the gap (about +0.054 here).
    Baseline values stay bitwise those of the plain record mean.

    Ref: audit 2026-10 CORE-9.
    """
    rng = np.random.default_rng(5)
    n_sites, per_site = 40, 60
    assert per_site <= M_INFLUENCE
    site_id = np.repeat(np.arange(n_sites, dtype=np.int64), per_site)
    x = rng.normal(size=(site_id.size, 3))
    y = (1.5 * x[:, 0] - x[:, 1] + rng.normal(size=site_id.size)) > 1.0
    cal = Cohort(x=x, y=y, site_id=site_id,
                 site_labels=tuple(f"s{i}" for i in range(n_sites)))
    head = Head(coef=np.array([1.2, -0.8, 0.3]), intercept=-1.0,
                mu=np.zeros(3), sd=np.ones(3))
    tau = 0.6
    w = np.where(cal.y, 2.5, 1.0)
    rm_w = _rm_vs_unweighted(head, cal, tau, weights=w)
    assert rm_w["gap"] == 0.0
    # same ratio, summed in a different order (bincount per site first)
    assert abs(rm_w["unweighted_risk"] - _bootstrap_estimate(
        head, cal, tau, weights=w)["point"]) < 1e-15
    ans = head.score(cal.x) >= tau
    err = head.predict(cal.x) != cal.y
    assert _rm_vs_unweighted(head, cal, tau)["unweighted_risk"] == \
        float(err[ans].mean())
