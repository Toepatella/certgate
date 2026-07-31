"""verification N1: the V21/V16 fixes need tests that would go red on revert.

``_bootstrap_estimate``'s top-up-or-decline discipline, the NaN-not-0.0 empty
answered set, ``_feasibility``'s None-not-inf sentinels, and ``render_text``'s
n_boot surfacing were all silently revertible at 110/110 green.
"""
import json

import numpy as np

from certgate.data import SimConfig, draw_cohort, split_sites
from certgate.model import fit_head, Head
from certgate.report import _bootstrap_estimate, render_text
from certgate.pipeline import _feasibility, run_certgate


def _head_cal():
    cfg = SimConfig()
    rng = np.random.default_rng(31)
    coh = draw_cohort(cfg, 60, rng)
    train, _, cal = split_sites(coh, rng)
    return fit_head(train), cal


def test_bootstrap_estimate_tops_up_to_full_count():
    """Resamples with zero answered mass are topped up, never dropped: with a
    reachable tau the draw count must be EXACTLY n_boot (a drop-only loop
    yields fewer whenever any resample has zero answered mass)."""
    head, cal = _head_cal()
    est = _bootstrap_estimate(head, cal, 0.55, n_boot=200)
    assert est["n_boot"] == 200
    assert est["n_attempts"] >= 200
    assert np.isfinite(est["point"])
    assert np.isfinite(est["ci95"]).all()


def test_bootstrap_estimate_declines_on_topup_shortfall():
    """The top-up-or-decline discipline itself (audit V21 / verification N1):
    when fewer than n_boot valid resamples arrive within the attempt budget,
    the CI must be NaN -- never a quantile over the reduced count. Budget
    pinched via the max_attempts parameter so the shortfall regime is
    deterministically reachable; a revert to 'quantile whatever arrived'
    produces a finite CI here and fails."""
    head, cal = _head_cal()
    est = _bootstrap_estimate(head, cal, 0.55, n_boot=200, max_attempts=10)
    assert 0 < est["n_boot"] < 200                 # some arrived, not enough
    assert np.isnan(est["ci95"]).all()             # declined, not reduced
    assert np.isfinite(est["point"])               # the point is still real


def test_bootstrap_estimate_empty_answered_set_is_nan_not_zero():
    """audit V21: a tau answering nothing must yield NaN, never 0.0 -- zero
    risk and no evidence are different claims."""
    head, cal = _head_cal()
    est = _bootstrap_estimate(head, cal, 1.01)     # nothing answers
    assert np.isnan(est["point"])
    assert np.isnan(est["ci95"]).all()
    assert est["n_boot"] == 0


def test_feasibility_reports_none_not_inf_when_no_coverage():
    """audit V16: a head answering nothing at any tau must report margin/ratio
    as None (JSON null), never -inf (invalid strict JSON, reads as a very bad
    but real margin)."""
    _, cal = _head_cal()
    flat = Head(coef=np.zeros(cal.d), intercept=0.0, mu=np.zeros(cal.d),
                sd=np.ones(cal.d))                 # score == 0.5 < every tau
    feas = _feasibility(flat, cal, 0.10, n_carrying=50)
    assert feas["margin"] is None and feas["ratio"] is None
    json.dumps(feas, allow_nan=False)              # strict-JSON serialisable


def test_render_text_surfaces_n_boot_and_handles_gated_reports():
    """render_text must show the estimated tier's n_boot (audit V21) and must
    not crash on a gated report (audit V25)."""
    cfg = SimConfig()
    rng = np.random.default_rng(20260721)
    coh = draw_cohort(cfg, 208, rng)
    train, aux, cal = split_sites(coh, rng)
    tgt = draw_cohort(cfg, 1, rng, site_label_prefix="rt")
    rep = run_certgate(train, aux, cal, tgt.x, target_label="render")
    text = render_text(rep)
    assert "n_boot=" in text
    # fixture audit 2026-07-25: the partition line includes the ANSWERED
    # count, so its label must not read as a decline count
    assert "[partition]" in text
    assert "[declines]" not in text
    gated = run_certgate(train, aux, cal, tgt.x[:5], target_label="gated")
    assert "[gate]" in render_text(gated)          # no KeyError on gated path
