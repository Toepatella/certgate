"""The E8a rescoring sidecar (POST-HOC, 2026-10-29): fast regressions.

The full replay of all 1,200 arm-A draws and its pooled pins (Student-t
61 -> 46, site bootstrap 59 -> 45 of 1,200 at alpha = 0.05) live in
experiments/rescore_e8a.py's own refuse-to-write self-check; it takes minutes.
Pinned here, in seconds:
  - pibar, the population-mean site prevalence, by quadrature
  - one frozen draw replays its certified rows exactly (tau, rm_fresh 6 dp)
  - the closed-form population R_M agrees with a record-level Monte Carlo
    and with a fresh draw_cohort pool at the audit's near-alpha row
  - the sidecar refuses every released output directory
  - the released sidecar JSON, when present, carries the pinned counts

Refs: audit 2026-10 nominal-exceedance (Fix B).
"""
import json
import os

import numpy as np
import pytest

from certgate.constants import TAU_GRID
from certgate.data import SimConfig, draw_cohort
from experiments import rescore_e8a as e8a
from experiments.probe_bbse_coverage import population_prevalence
from experiments.run_synthetic import _rng


@pytest.fixture(scope="module")
def near_alpha_draw():
    """Draws (60 sites, r=0) and (60 sites, r=199), replayed once."""
    rows, check, heads = e8a.rescore(draws=[(0, 0), (0, 199)], log=None)
    return rows, check, heads


def _row(rows, draw, alpha, method):
    return next(x for x in rows if x["draw"] == draw and x["alpha"] == alpha
                and x["method"] == method)


def test_pibar_is_the_quadrature_prevalence():
    pi = e8a.pibar()
    assert round(pi, 6) == 0.103657
    assert round(pi, 7) == e8a.PIBAR_PIN[0]
    assert pi == population_prevalence(0.095, 0.5)


def test_replays_frozen_draw_exactly(near_alpha_draw):
    rows, check, _ = near_alpha_draw
    assert check["mismatches"] == 0 and check["frozen_rows_compared"] == 20
    t, b = _row(rows, 0, 0.05, "t"), _row(rows, 0, 0.05, "site_boot")
    assert (t["tau"], t["rm_fresh"]) == (0.71, 0.04142)
    assert (b["tau"], b["rm_fresh"]) == (0.69, 0.043508)


def test_near_alpha_row_flips_under_population_scoring(near_alpha_draw):
    rows, _, _ = near_alpha_draw
    x = _row(rows, 199, 0.05, "t")
    assert x["tau"] == 0.61 and x["rm_fresh"] == 0.053018
    assert round(x["rm_population"], 6) == 0.049944
    assert x["rm_exceed_fresh"] and not x["rm_exceed_population"]


def test_closed_form_matches_record_monte_carlo(near_alpha_draw):
    _, _, heads = near_alpha_draw
    head = heads[(0, 199)]
    tau = float(TAU_GRID[np.argmin(np.abs(TAU_GRID - 0.61))])
    cf = e8a.population_rm(head, tau)
    mc, se = e8a.mc_population_rm(head, tau, _rng(*e8a.MC_STREAM, 2, 0),
                                  n_records=2_000_000)
    assert abs(mc - cf) <= 5 * se


def test_closed_form_matches_generator_pool(near_alpha_draw):
    """The influence weights cancel: draw_cohort + _rm_on_pool agree."""
    _, _, heads = near_alpha_draw
    head = heads[(0, 0)]
    pool = draw_cohort(SimConfig(), 1000, _rng(*e8a.MC_STREAM, 3, 0),
                       site_label_prefix="e8atest")
    for tau in (0.61, 0.71, 0.85):
        tg = float(TAU_GRID[np.argmin(np.abs(TAU_GRID - tau))])
        cf = e8a.population_rm(head, tg)
        gp, se = e8a.pool_rm_se(head, pool, tg)
        assert abs(gp - cf) <= 5 * se


def test_refuses_released_output_directories(tmp_path):
    for name in e8a.FROZEN_DIRS_ALL:
        with pytest.raises(SystemExit):
            e8a.assert_writable(os.path.join(e8a.EXP_DIR, name,
                                             "E8a_rescore.json"))
    e8a.assert_writable(os.path.join(e8a.OUT_DIR, "E8a_rescore.json"))
    e8a.assert_writable(str(tmp_path / "E8a_rescore.json"))


def test_released_sidecar_carries_pinned_counts():
    path = os.path.join(e8a.OUT_DIR, "E8a_rescore.json")
    assert os.path.exists(path), path
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    assert doc["self_check"]["certified_rows_reproduced"] == 6056
    assert doc["self_check"]["mismatches"] == 0
    for (method, alpha), k in e8a.PINNED_FRESH.items():
        assert doc["counts"][f"{method}|{alpha}"]["pooled"]["fresh"]["k"] == k
    for (method, alpha), k in e8a.PINNED_POPULATION.items():
        cell = doc["counts"][f"{method}|{alpha}"]["pooled"]
        assert cell["population"]["k"] == k and cell["n_certified"] == 1200
    for key in ("wsr|0.05", "wsr|0.1", "mpeb|0.05", "mpeb|0.1",
                "hoeffding|0.05", "hoeffding|0.1"):
        cell = doc["counts"][key]["pooled"]
        assert cell["fresh"]["k"] == 0 and cell["population"]["k"] == 0
