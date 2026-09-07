"""The fix-pass sidecars: read-only derivations and post-hoc replays.

Four things get pinned here:
  - derive_fixpass_numbers reproduces its pinned values from the released
    files, and refuses to write into a frozen output directory
  - settle_predictions scores the seven registered predictions 3 confirmed /
    1 partly / 3 falsified with P7 the partly one, and refuses frozen paths
  - rescore_e9a replays one certified frozen row to four decimals, and its
    class reweighting is the identity at the pool's own prevalence
  - probe_bbse_coverage's closed-form truths agree with Monte Carlo, and a
    three-fit smoke run writes what it says it writes

Refs: fix-pass plan WP2.
"""
import os

import numpy as np
import pytest

from certgate.validate import Cohort
from certgate.model import Head
from experiments import derive_fixpass_numbers as dfn
from experiments import settle_predictions as sp
from experiments import rescore_e9a as e9a
from experiments import probe_bbse_coverage as probe
from experiments.run_synthetic import _rm_on_pool


# ------------------------------------------------------------- derivation

def test_derive_pins_reproduce_from_released_files():
    """Every pinned value derives from the released artifacts.

    The pins are the text-to-artifact guard: a manuscript number that stops
    reproducing fails here before it fails in front of a referee.
    """
    doc = dfn.derive()
    assert doc["pins"], "no pins were checked"
    assert all(v["status"] for v in doc["pins"].values())
    assert doc["published_split"]["n_predicted_positive_answered"] == 63
    assert doc["fairness"]["cells_over_alpha"]["n"] == 8
    assert doc["fairness"]["cells_status_ok"] == 570
    assert doc["e1"]["baseline_deploying_draws_alpha0.10"] == 194
    assert round(doc["head_auc_s_cal"]["mean"], 4) == 0.8618
    assert doc["_run"]["inputs"]                    # sha256 of every input


def test_derive_refuses_frozen_targets(tmp_path):
    """Nothing under a frozen output directory, and never EICU-SUMMARY.md."""
    for bad in (os.path.join(dfn.EXP_DIR, "out", "x.json"),
                os.path.join(dfn.EXP_DIR, "out-panel", "x.json"),
                os.path.join(dfn.EXP_DIR, "out-sens", "sub", "x.csv"),
                str(tmp_path / "EICU-SUMMARY.md")):
        with pytest.raises(SystemExit):
            dfn.assert_not_frozen(bad)
    dfn.assert_not_frozen(str(tmp_path / "fine.json"))     # no raise
    dfn.assert_not_frozen(os.path.join(dfn.EXP_DIR, "out-derived", "x.json"))


# ------------------------------------------------------------- settlement

def test_settle_tally_and_p7_partly():
    doc = sp.settle()
    assert doc["tally"] == dict(confirmed=3, partly=1, falsified=3)
    by = {p["id"]: p for p in doc["predictions"]}
    assert by["P7"]["verdict"] == "partly"
    # size clause holds, the 208-site clause fails by one, the APACHE
    # linkage clause holds
    assert [c["met"] for c in by["P7"]["clauses"]] == [True, False, True]
    assert {by[k]["verdict"] for k in ("P1", "P3", "P6")} == {"confirmed"}
    assert {by[k]["verdict"] for k in ("P2", "P4", "P5")} == {"falsified"}
    # P3's modal-reason clause is disclosed, not hidden
    assert any(not c["met"] for c in by["P3"]["clauses"])
    assert "3 confirmed / 1 partly / 3 falsified" in doc["headline"]


def test_settle_refuses_frozen_out_dir():
    with pytest.raises(SystemExit):
        sp.main(["--out", os.path.join(dfn.EXP_DIR, "out")])
    with pytest.raises(SystemExit):
        sp.main(["--out", os.path.join(dfn.EXP_DIR, "out-panel")])


# --------------------------------------------------------------- E9 arm A

def test_e9a_replays_one_600_site_certified_row_to_4dp():
    """One 600-site single-declared-site draw replays its frozen rm_fresh."""
    frozen = dfn._read_csv(e9a.FROZEN)
    certified = e9a._frozen_certified(frozen)
    key = min(k for k in certified if k[0] == 1 and k[1] == 0)   # 600 sites
    rows, check = e9a.rescore(draws=[key], log=None)
    assert check["mismatches"] == 0
    assert check["rows_checked"] == len(certified[key]) >= 1
    for r in rows:
        assert r["self_check_4dp"]
        assert round(r["rm_fresh_replayed"], 4) == round(r["rm_fresh_frozen"], 4)
        assert r["coverage_replayed"] == r["coverage_frozen"]


def _toy_pool():
    """Two sites of four records; the head is the identity on d=1.

    x = +/-3 gives a score of ~0.95, so everything answers at tau = 0.55.
    Site A: y = [T, T, F, F], predictions [T, F, T, F] -> one FN, one FP.
    Site B: y = [T, F, F, F], predictions [T, T, F, F] -> one FP.
    Pool prevalence 3/8; unweighted R_M = 3/8 with g/n = 1 on both sites.
    """
    x = np.array([+3, -3, +3, -3, +3, +3, -3, -3], dtype=np.float64)
    y = np.array([True, True, False, False, True, False, False, False])
    sid = np.array([0, 0, 0, 0, 1, 1, 1, 1], dtype=np.int64)
    pool = Cohort(x=x.reshape(-1, 1), y=y, site_id=sid,
                  site_labels=("A", "B"))
    head = Head(coef=np.array([1.0]), intercept=0.0, mu=np.zeros(1),
                sd=np.ones(1))
    return head, pool


def test_e9a_rescoring_is_identity_at_matched_prevalence():
    head, pool = _toy_pool()
    rm = _rm_on_pool(head, pool, 0.55)
    assert np.isclose(rm, 3 / 8)
    pi_e = float(pool.y.mean())
    assert np.isclose(e9a._rm_reweighted(head, pool, 0.55, pi_e), rm)


def test_e9a_rescoring_closed_form_at_another_prevalence():
    """Reweight the toy pool from 3/8 to 1/2.

    Positives carry 4/3, negatives 4/5. Site A numerator 4/3 + 4/5, site A
    denominator 2*(4/3) + 2*(4/5); site B numerator 4/5, denominator
    4/3 + 3*(4/5). R = (4/3 + 8/5) / 8.
    """
    head, pool = _toy_pool()
    got = e9a._rm_reweighted(head, pool, 0.55, 0.5)
    assert np.isclose(got, (4 / 3 + 8 / 5) / 8)
    assert not np.isclose(got, 3 / 8)


# ------------------------------------------------------------ BBSE probe

def test_probe_truths_closed_form():
    """Site-effect integrals and the head's confusion rates."""
    assert np.isclose(probe.population_prevalence(0.095, 0.0), 0.095)
    # a symmetric effect on the log-odds raises a below-half prevalence
    assert probe.population_prevalence(0.095, 0.5) > 0.095
    head, truth = probe.fixed_head()                # Monte-Carlo agreement
    assert abs(truth["c0"] - truth["c0_mc"]) <= probe.MC_TOL
    assert abs(truth["c1"] - truth["c1_mc"]) <= probe.MC_TOL
    assert 0.0 < truth["c0"] < truth["c1"] < 1.0
    assert truth["rho_pop"] > 1.0                   # the shift raises the odds


def test_probe_smoke_three_fits(tmp_path):
    doc = probe.main(["--fits", "3", "--n-aux", "36", "--out", str(tmp_path)])
    assert (tmp_path / "BBSE_probe.csv").exists()
    assert (tmp_path / "BBSE_probe.json").exists()
    cell = doc["cells"]["36"]
    assert cell["n_fits"] == 3
    assert cell["n_fitted"] + cell["decline"]["k"] == 3
    assert doc["nominal"]["joint_four"] == 0.975
    assert doc["nominal"]["per_parameter"] == 1 - 0.025 / 4
    cov = cell["coverage_among_fits_with_a_box"]
    for p in ("c0", "c1", "pi_s", "q"):
        assert cov[p]["n"] <= 3


# ---------------------------------------------------------------- gate 2

def test_gate2_report_path_is_freeze_protected(tmp_path):
    """The gate-2 report never lands in a frozen directory and never overwrites.

    The report used to default into the re-run directory, so a bare re-run of
    the gate could replace the shipped report in place. It now goes to the
    working directory or --report, refuses any frozen directory outright, and
    refuses an existing file unless --force is passed.
    """
    from experiments import gate2_diff as g2

    for bad in (os.path.join(g2.EXP_DIR, "out", "GATE2-REPORT.json"),
                os.path.join(g2.EXP_DIR, "out-panel", "x.json"),
                os.path.join(g2.EXP_DIR, "out-sens", "sub", "x.json")):
        with pytest.raises(SystemExit, match="frozen-output-dir"):
            g2.main(["--report", bad])

    shipped = os.path.join(g2.EXP_DIR, "out-rev2", "GATE2-REPORT.json")
    assert os.path.exists(shipped), "the shipped gate-2 report is released"
    with pytest.raises(SystemExit, match="report-exists"):
        g2.main(["--report", shipped])

    report = tmp_path / "GATE2-REPORT.json"
    assert g2.main(["--report", str(report)]) == 0
    first = report.read_bytes()
    with pytest.raises(SystemExit, match="report-exists"):
        g2.main(["--report", str(report)])
    assert report.read_bytes() == first
    assert g2.main(["--report", str(report), "--force"]) == 0
