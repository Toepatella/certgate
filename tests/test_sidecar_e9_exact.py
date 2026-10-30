"""The E9 closed-form estimand sidecar (experiments/rescore_e9_exact.py).

What gets pinned here, in a few seconds (the full 640-draw replay stays in
the script's own refuse-to-write self-check):
  - the closed-form class rates against simulated records on a hand-built
    head, and the identities R(1) = FNR and R(pi) constant when the two
    classes' logits are mirror images
  - the sidecar refuses every released output directory
  - one arm-A draw (1,200 sites, draw 48) replays its frozen rows cell for
    cell (the unrounded rho_lo/rho_hi to 1e-12 relative: a Linux replay moves
    their last bits) and names 0.0792 at the declared site's latent
    prevalence, against the released proxy 0.058612
  - one arm-B draw (600 sites, draw 80) replays both arms' released rows and
    scores the 0.400108 fresh-pool certificate at 0.3902
  - the released out-e9-exact/ files carry the verdict numbers

Refs: audits FNR-1, FNR-5, FNR-6 (2026-10).
"""
import json
import os

import numpy as np
import pytest

from certgate.data import SimConfig
from certgate.model import Head
from experiments import rescore_e9_exact as ex
from experiments.derive_fixpass_numbers import EXP_DIR, _read_csv


def _mirror_head(cfg, k=1.3):
    """A head whose logit is k * sep * (v . x): class means +/- k sep^2 / 2,
    sd k sep, so the two classes are mirror images about zero."""
    return Head(coef=k * cfg.sep * cfg.direction(), intercept=0.0,
                mu=np.zeros(cfg.d), sd=np.ones(cfg.d))


def test_closed_form_rates_match_simulation_and_identities():
    cfg = SimConfig()
    head = _mirror_head(cfg)
    taus = np.array([0.55, 0.75, 0.91])
    rates = ex.class_rates(head, cfg, taus)
    e0, a0, e1, a1 = rates
    # mirror-image classes: equal error and answer rates, so R(pi) is flat
    assert np.allclose(e0, e1) and np.allclose(a0, a1)
    for pi in (0.05, 0.3, 0.9):
        assert np.allclose(ex.answered_risk(rates, pi), ex.fnr_exact(rates))
    assert np.allclose(ex.answered_risk(rates, 1.0), ex.fnr_exact(rates))
    rng = np.random.default_rng(20261029)
    for i, tau in enumerate(taus):
        mc = ex.mc_class_rates(head, cfg, tau, rng, n=200_000)
        assert np.allclose(mc, [r[i] for r in rates], atol=0.004)
    # FNR falls in tau exactly when the positives' mean logit is positive
    assert ex.positive_logit_mean(head, cfg) > 0
    assert np.all(np.diff(ex.fnr_exact(rates)) < 0)


def test_refuses_every_released_directory():
    for name in ex.RELEASED_DIRS:
        with pytest.raises(SystemExit):
            ex._assert_writable(os.path.join(EXP_DIR, name, "E9_exact.json"))
    ex._assert_writable(os.path.join(ex.OUT_DIR, "E9_exact.json"))


def test_arm_a_draw48_replays_and_names_the_latent_estimand():
    frozen, released = ex.load_a()
    rep = ex.replay_a(3, 48)
    assert ex.check_a(rep, frozen, released) == []
    # the values a Linux CI replay of this draw gave (about 6 ulps off the
    # Windows release) pass; a real change does not, and other cells stay exact
    assert ex._same_cell("rho_lo", 0.29164722290741557, "0.2916472229074152")
    assert ex._same_cell("rho_hi", 1.65402541301774, "1.6540254130177414")
    assert not ex._same_cell("rho_hi", 1.6540254130177414 * (1 + 1e-9),
                             "1.6540254130177414")
    assert not ex._same_cell("tau", 0.5500000000000001, "0.55")
    pop = ex.population_parameters(SimConfig())
    rows = {x["budget"]: x for x in ex.score_a(rep, pop, mc=False)}
    assert sorted(rows) == [0.05, 0.1]
    r = rows[0.1]
    assert r["tau"] == 0.55 and r["n_target_records"] == 712
    assert abs(r["pi_latent"] - 0.1564) < 5e-4
    assert r["pi_realised"] == 0.115169
    assert abs(r["exact_named_estimand"] - 0.0792) < 5e-4
    assert not r["exact_exceeds"]
    assert r["released_proxy"] == 0.058612 and r["released_fresh"] == 0.108856
    assert abs(r["exact_at_population_prevalence"] - 0.1104) < 5e-4
    assert abs(r["rho_star"] - 1.6027) < 5e-4 and r["box_covers_rho_star"]


def test_arm_b_draw_600_80_scores_the_pool_excursion():
    released, frozen = ex.load_b()
    rep = ex.replay_b(2, 80)
    assert ex.check_b(rep, released, frozen) == []
    draw, certs = ex.score_b(rep, mc=False)
    assert draw["strictly_decreasing"] and draw["below_control_at_some_tau"]
    c = next(x for x in certs if x["arm"] == "B-positives"
             and x["budget"] == 0.4)
    assert c["tau"] == 0.91 and c["released_fresh"] == 0.400108
    assert c["released_fresh_exceeds"] and not c["exact_exceeds"]
    assert abs(c["exact_named_estimand"] - 0.3902) < 5e-4


def _release():
    path = os.path.join(ex.OUT_DIR, "E9_exact.json")
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    return doc, _read_csv(os.path.join(ex.OUT_DIR, "E9_exact.csv"))


def test_released_sidecar_carries_the_verdict_numbers():
    doc, rows = _release()
    assert set(doc["_run"]["inputs"]) == {
        "experiments/out/E9_bbse_frontier.csv", "experiments/out/E9_fnr.csv",
        "experiments/out-e9a-rescore/E9a_rescore.csv",
        "experiments/out-e9b-positives/E9b_fnr_positives.csv",
        "experiments/out-bbse-probe/BBSE_probe.json"}
    sc = doc["self_check"]
    assert sc["arm_a"]["mismatches"] == 0 and sc["arm_b"]["mismatches"] == 0
    assert sc["arm_a"]["draws_replayed"] == 40
    assert sc["arm_b"]["draws_replayed"] == 600
    assert doc["population"]["rho_pop"] == 2.601345
    a, b = doc["arm_a"], doc["arm_b"]
    # arm A: 44 single-site certificates, all within budget and covered
    assert (a["certificates"], a["exact_exceeds"],
            a["box_covers_rho_star"]) == (44, 0, 44)
    flagged = {(x["draw"], x["budget"]): x["exact_named_estimand"]
               for x in a["released_exceeding_rows"]}
    assert sorted(flagged) == [(29, 0.05), (29, 0.1), (48, 0.1)]
    for key, want in {(29, 0.05): 0.0163, (29, 0.1): 0.0398,
                      (48, 0.1): 0.0792}.items():
        assert abs(flagged[key] - want) < 5e-4
    assert a["cells"]["1200|0.1"]["box_covers_rho_pop_parameter"] == 16
    # arm B: 2,428 certificates, none over budget on the exact estimand
    assert (b["certificates"], b["exact_exceeds"]) == (2428, 0)
    ctl = b["positives_certificates_at_control"]
    assert len(ctl) == 6
    assert all(0.355 < x["exact_named_estimand"] < 0.393 for x in ctl)
    assert b["certify_and_estimand_exceeds_at_control"] == dict(
        positives=0, shipped=0, draws=600)
    assert b["below_control_at_some_tau"] == 529
    assert b["strictly_decreasing"] == 599
    assert len(rows) == 44 + 2428
