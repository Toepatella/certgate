"""The post-hoc E6 composition sidecar (audit 2026-10 BBSE-1).

Fast checks only; the full E6 replay and its exact-equality self-check live
inside experiments/rescore_e6_composition.py itself. Pinned here:
  - the sidecar refuses every frozen output directory and accepts its own
  - the released formula is head odds times rho alone, and the corrected
    multiplier reduces to rho exactly when pi_train equals pi_source
  - the self-check refuses on any single-field difference from the frozen
    block, and the verdict check refuses a corrected value off the verdicts
  - the emitted JSON (when present) carries the frozen numbers verbatim as
    the released view and the verdicts' numbers as the corrected one
"""
import copy
import json
import os

import numpy as np
import pytest

from experiments import rescore_e6_composition as e6c
from experiments.derive_fixpass_numbers import EXP_DIR


class _StubHead:
    def __init__(self, p):
        self._p = np.asarray(p, dtype=np.float64)

    def predict_proba(self, x):
        return self._p


def _frozen():
    with open(e6c.FROZEN, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.mark.parametrize("name", e6c.FROZEN_DIRS)
def test_refuses_every_frozen_dir(name):
    with pytest.raises(SystemExit, match="frozen"):
        e6c.assert_writable(os.path.join(EXP_DIR, name, e6c.OUT_NAME))


def test_accepts_its_own_dir():
    e6c.assert_writable(os.path.join(e6c.OUT_DIR, e6c.OUT_NAME))


def test_released_view_is_rho_times_head_odds():
    head = _StubHead([0.5, 0.2, 0.9])
    answered = np.array([True, True, False])
    v = e6c.released_view(head, np.zeros((3, 1)), answered, 2.0)
    # odds 1 -> 2 (p 2/3); odds 0.25 -> 0.5 (p 1/3)
    assert v["positive_fraction"] == pytest.approx(0.5, abs=1e-15)
    assert v["expected_n_positive"] == pytest.approx(1.0, abs=1e-15)
    assert v["n_answered"] == 2 and v["odds_multiplier"] == 2.0


def test_corrected_multiplier_is_target_to_training_odds_ratio():
    pi_t, pi_s, pi_tr = 0.0975, 0.1153, 0.1024
    rho = e6c._odds(pi_t) / e6c._odds(pi_s)
    m = e6c.corrected_multiplier(rho, pi_s, pi_tr)
    assert m == pytest.approx(e6c._odds(pi_t) / e6c._odds(pi_tr), rel=1e-13)
    # equal priors: the released and corrected multipliers coincide
    assert e6c.corrected_multiplier(rho, pi_s, pi_s) == pytest.approx(
        rho, rel=1e-14)


def _passing_inputs():
    comp = _frozen()["composition"]
    fb = comp["bbse_true_class"]
    released = dict(positive_fraction=fb["positive_fraction"],
                    expected_n_positive=fb["expected_n_positive"],
                    n_answered=int(fb["n_answered"]))
    replayed = copy.deepcopy(comp)
    return released, replayed, fb["rho"], comp


def test_self_check_passes_on_frozen_values():
    released, replayed, rho, comp = _passing_inputs()
    fields = e6c.self_check(released, replayed, rho, comp)
    assert len(fields) == 10


@pytest.mark.parametrize("where,key", [
    ("released", "positive_fraction"),
    ("released", "expected_n_positive"),
    ("rho", None),
    ("predicted_class", "n_positive"),
    ("predicted_class", "positive_fraction"),
    ("oracle_true_class", "n_positive"),
    ("oracle_true_class", "positive_fraction"),
])
def test_self_check_refuses_any_difference(where, key):
    released, replayed, rho, comp = _passing_inputs()
    if where == "released":
        released[key] = np.nextafter(released[key], np.inf)
    elif where == "rho":
        rho = np.nextafter(rho, np.inf)
    else:
        replayed[where][key] = replayed[where][key] + 1
    with pytest.raises(SystemExit, match="replay-mismatch"):
        e6c.self_check(released, replayed, rho, comp)


def test_verdict_check():
    good = {k: v for k, (v, _dp) in e6c.VERDICT_EXPECTED.items()}
    e6c.check_verdict(good)
    bad = dict(good, positive_fraction=0.0857576903)
    with pytest.raises(SystemExit, match="verdict-mismatch"):
        e6c.check_verdict(bad)


OUT_JSON = os.path.join(e6c.OUT_DIR, e6c.OUT_NAME)


def test_emitted_json_matches_frozen_and_verdicts():
    assert os.path.exists(OUT_JSON), OUT_JSON
    with open(OUT_JSON, encoding="utf-8") as fh:
        doc = json.load(fh)
    frozen = _frozen()["composition"]
    rel = doc["bbse_true_class"]["released"]
    for k in ("positive_fraction", "expected_n_positive", "rho"):
        assert rel[k] == frozen["bbse_true_class"][k]
    assert doc["oracle_true_class"]["n_positive"] == \
        frozen["oracle_true_class"]["n_positive"]
    assert doc["oracle_true_class"]["positive_fraction"] == \
        frozen["oracle_true_class"]["positive_fraction"]
    cor = doc["bbse_true_class"]["corrected"]
    for k, (v, dp) in e6c.VERDICT_EXPECTED.items():
        assert round(cor[k], dp) == v
    assert doc["self_check"]["mismatches"] == 0
    assert "experiments/out/E6_composition.json" in doc["_run"]["inputs"]
    with open(os.path.join(e6c.OUT_DIR, "README.md"), encoding="utf-8") as fh:
        assert "Status: POST-HOC (2026-10-29)" in fh.read()
