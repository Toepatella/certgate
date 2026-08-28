"""The eICU mock-corpus generator, on its own terms.

Byte-determinism and the --tables projection, the frozen manifest key set,
generator honesty against the ETL's level tuples, and the CERTGATE_EICU /
CERTGATE_EICU_LARGE gated arms at the generator's frozen sizes.
Split from test_eicu_path.py on 2026-08-25; the tests are relocated verbatim.
"""
from __future__ import annotations

import json
import os

import pytest

from certgate.constants import MIN_CAL_CLUSTERS
from experiments import eicu_etl as etl
from experiments import eicu_mock as mock

from _eicu_helpers import (MANIFEST_KEYS, TINY_SITES, TINY_STAYS,
                           _assert_honest, _gz_hashes, _run_eicu, mock_small)


@pytest.fixture(scope="module")
def mock_tiny(tmp_path_factory):
    """Two byte-identical runs plus a --tables projection, same seed.

    signal=False is the one configuration in which generate admits fewer than
    EICU_MIN_TOTAL_SITES sites, so the determinism arm stays cheap.
    """
    base = tmp_path_factory.mktemp("eicu_tiny")
    cfgs = {}
    for key, tables in (("a", None), ("b", None),
                        ("subset", ["patient", "hospital"])):
        out = str(base / key)
        kw = dict(stays=TINY_STAYS, sites=TINY_SITES, signal=False, out=out)
        if tables is not None:
            kw["tables"] = tables
        mock.generate(mock.MockConfig(**kw))
        cfgs[key] = out
    return cfgs


# =============================================================== 1-3. mock ===

def test_mock_is_byte_deterministic(mock_tiny):
    """Two runs at the same seed give byte-identical .csv.gz files.

    The gzip header is frozen and every stream derives from the seed, so a
    corpus is a reproducible input, not a snapshot.
    """
    ha, hb = _gz_hashes(mock_tiny["a"]), _gz_hashes(mock_tiny["b"])
    assert ha, "no .csv.gz files written"
    assert ha == hb


def test_mock_table_subset_is_a_byte_identical_projection(mock_tiny):
    """--tables patient,hospital is a projection, not a different draw.

    The plan always runs in full and id counters are per table, so a subset
    regenerates without re-deriving the whole corpus.
    """
    full, sub = _gz_hashes(mock_tiny["a"]), _gz_hashes(mock_tiny["subset"])
    assert set(sub) == {"patient.csv.gz", "hospital.csv.gz"}
    for name, digest in sub.items():
        assert digest == full[name], f"{name} is not a byte-identical projection"


def test_mock_manifest_has_the_frozen_key_set(mock_small):
    m = mock_small["manifest"]
    assert set(m) == MANIFEST_KEYS
    assert m["signal"] is True and m["drift"] is False
    assert set(m["row_counts"]) == set(mock.EICU_MOCK_TABLES)
    json.dumps(m)                                  # manifest.json round-trips


def test_mock_level_tuples_match_the_etl_tuples():
    """eicu_mock cannot import eicu_etl, so its level tuples are pinned."""
    for suffix in ("GENDER", "ETHNICITY", "ADMITSOURCE", "UNITTYPE",
                   "UNITSTAYTYPE"):
        assert (getattr(mock, f"EICU_MOCK_LEVELS_{suffix}")
                == getattr(etl, f"EICU_LEVELS_{suffix}")), suffix


def test_mock_cli_parses_the_tables_list():
    assert mock.parse_args(["--tables", "patient,hospital"]).tables == \
        ["patient", "hospital"]


# ================================================ 22. full-scale (env-gated) ==

@pytest.mark.skipif(os.environ.get("CERTGATE_EICU") != "1",
                    reason="full-scale eICU mock arm; set CERTGATE_EICU=1")
def test_full_scale_mock_reaches_an_honest_outcome(tmp_path):
    """The real eICU scale: 208 hospitals, 200,859 unit stays, ~35 MB of gzip.

    Holding out 24 hospitals leaves 73/36/75, so MIN_CAL_CLUSTERS = 50 has 50%
    headroom. Certification is plausible here and, if issued, must survive the
    oracle. A decline is equally acceptable.
    """
    out = str(tmp_path / "eicu_full")
    manifest = mock.generate(mock.MockConfig(stays=mock.EICU_MOCK_FULL_STAYS,
                                             sites=mock.EICU_MOCK_FULL_SITES,
                                             out=out))
    assert manifest["sites"] == mock.EICU_MOCK_FULL_SITES == 208
    assert manifest["stays_requested"] == mock.EICU_MOCK_FULL_STAYS == 200859

    rep, ctx = _run_eicu(out)
    outcome = _assert_honest(rep, ctx)
    assert outcome in ("certified", "declined")
    assert rep["diagnostic"]["n_cal_carrying"] >= MIN_CAL_CLUSTERS
    assert len(ctx["sets"]["cal"]) == 75           # 208 - 24 = 184 -> 73/36/75

    # the report round-trips to JSON with the stable shapes: str(0.10) is "0.1"
    ser = json.dumps({k: v for k, v in rep["diagnostic"].items()
                      if k not in ("abstention_profile", "composition")},
                     default=str)
    assert json.loads(ser)["feasibility"].keys() == {"0.05", "0.1"}

    bd = rep["diagnostic"]["bbse"]
    assert bd is None or bd["n_target_sites"] in (None,
                                                  etl.EICU_N_TARGET_SITES)


@pytest.mark.skipif(os.environ.get("CERTGATE_EICU_LARGE") != "1",
                    reason="large-site eICU mock arm; set CERTGATE_EICU_LARGE=1")
def test_large_mock_reaches_the_certified_branch():
    """margin_floor scales as 1/n_carrying (E-20).

    So the mock's frozen-size decline does not generalise to any corpus size.
    The oracle margin 0.0354 meets a floor that falls with the calibration
    cluster count, crossing at n_carrying = 77, about 217 hospitals. At 900
    hospitals the mock certifies alpha = 0.10, EICU_MOCK_SIGNAL_B untouched.

    This arm exercises the certified branch before the extract lands:
    _eval_rung's path, _abstention_ranking (which settles P4), _rm_on_pool and
    _per_site_exceed_frac. It still asserts honesty only.
    """
    import tempfile
    from certgate.certify import margin_floor
    from certgate.constants import DELTA

    # the arithmetic the claim rests on
    assert margin_floor(63, DELTA, 0.10) > 0.0354     # small arm  -> declines
    assert margin_floor(75, DELTA, 0.10) > 0.0354     # full arm   -> declines
    assert margin_floor(77, DELTA, 0.10) < 0.0354     # crossing point

    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "eicu_large")
        mock.generate(mock.MockConfig(stays=90000, sites=900, out=out))
        rep, ctx = _run_eicu(out)
        outcome = _assert_honest(rep, ctx)
        assert outcome in ("certified", "declined")
        assert rep["diagnostic"]["n_cal_carrying"] > 77, (
            "this arm is pointless unless it clears the crossing point")
