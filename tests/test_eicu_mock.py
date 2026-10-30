"""The eICU mock-corpus generator, on its own terms.

Byte-determinism and the --tables projection, the frozen manifest key set,
generator honesty against the ETL's level tuples, the CERTGATE_EICU /
CERTGATE_EICU_LARGE gated arms at the generator's frozen sizes, and the
mock-corpus explanation page (examples/explain_dashboard_mock.py).
Split from test_eicu_path.py on 2026-08-25; the tests are relocated verbatim.
"""
from __future__ import annotations

import json
import os
import pathlib

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
    headroom. At B = 0.85 this size declines every rung (measured); the
    assertion is honesty only, so a certificate would also pass provided it
    survives the oracle.
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
    The floor is in atom units: it meets the oracle's record-unit margin 0.0354
    times the calibration hospitals' mean min(n_c,100)/100. At this corpus's
    size distribution (mean 0.568) that crossing is about 134 calibration
    clusters; the 900-hospital, 90,000-stay mock yields 351 and certifies
    alpha = 0.10 (measured), EICU_MOCK_SIGNAL_B untouched.
    Ref: audit 2026-10 GAP-eicu-mock-math-1.

    This arm exercises the certified branch before the extract lands:
    _eval_rung's path, _abstention_ranking (which settles P4), _rm_on_pool and
    _per_site_exceed_frac. It still asserts honesty only.
    """
    import tempfile
    from certgate.certify import margin_floor
    from certgate.constants import DELTA

    # the arithmetic the claim rests on
    assert margin_floor(63, DELTA, 0.10) > 0.0354     # record-unit floor arithmetic only
    assert margin_floor(75, DELTA, 0.10) > 0.0354     # record-unit floor arithmetic only
    assert margin_floor(77, DELTA, 0.10) < 0.0354     # record-unit floor arithmetic only
    # the atom-unit crossing: record-unit margin times the mean atom weight
    assert min(n for n in range(50, 400)
               if margin_floor(n, DELTA, 0.10) < 0.5679 * 0.035434) == 134

    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "eicu_large")
        mock.generate(mock.MockConfig(stays=90000, sites=900, out=out))
        rep, ctx = _run_eicu(out)
        outcome = _assert_honest(rep, ctx)
        assert outcome in ("certified", "declined")
        assert rep["diagnostic"]["n_cal_carrying"] > 134, (
            "this arm is pointless unless it clears the atom-unit crossing "
            "(about 134 calibration clusters at this size)")


# ============================================= mock-corpus explanation page ==

def test_mock_dashboard_page_names_features_and_declares_itself(mock_small,
                                                                tmp_path):
    """The committed mock page: eICU column names, a banner, a parseable payload.

    The small corpus declines every rung at the frozen seed, so the page is built with
    allow_declined=True and shows the uncertified banner; the full-size
    committed page (900 hospitals) is built by the module's CLI. What is
    pinned here is the contract the page makes regardless of outcome: the
    payload names the real eICU features (not "feature 0"), the MOCK CORPUS
    banner is on the page, the cohort label repeats it, and the `const DATA =`
    line parses as JSON the way tests/test_reliability_panel.py reads it.
    """
    from examples import explain_dashboard_mock as page

    out = tmp_path / "explain_dashboard_mock.html"
    path = page.build(str(out), corpus_dir=mock_small["dir"],
                      allow_declined=True, verbose=False)
    html = pathlib.Path(path).read_text(encoding="utf-8")
    assert page.MOCK_BANNER in html
    assert html.count('id="mockbanner"') == 1
    assert "no eICU record" in html

    prefix = "const DATA = "
    line = next(l for l in html.splitlines() if l.startswith(prefix))
    payload = json.loads(line[len(prefix):].rstrip(";"))
    names = payload["raw_names"]
    assert "aps_motor" in names and "age" in names
    assert any(n.startswith("unitstaytype=") for n in names)
    assert not any(n.startswith("feature ") for n in names)
    assert payload["cohort_label"].startswith(page.MOCK_BANNER)
    assert payload["provenance"]["pool"].endswith("held-out mock hospitals")

    # the basename guard: a mock page must never be filed as a record-level
    # eICU page, whose pattern .gitignore denies
    with pytest.raises(SystemExit, match="basename-collision"):
        page.build(str(tmp_path / "explain_dashboard_eicu_mock.html"),
                   corpus_dir=mock_small["dir"], allow_declined=True,
                   verbose=False)


def test_committed_mock_dashboard_page_ships():
    """The page the manuscript cites is in the tree and declares itself.

    Section 4.11 and the Code availability statement point the reader at
    examples/explain_dashboard_mock.html; this pins that the file ships,
    carries the MOCK CORPUS banner once, and says it holds no eICU record.
    """
    from examples import explain_dashboard_mock as page

    root = pathlib.Path(__file__).resolve().parents[1]
    html_path = root / "examples" / "explain_dashboard_mock.html"
    assert html_path.exists(), "examples/explain_dashboard_mock.html is cited"
    html = html_path.read_text(encoding="utf-8")
    assert page.MOCK_BANNER in html
    assert html.count('id="mockbanner"') == 1
    assert "no eICU record" in html


# ======================== audit 2026-10: the mock page's certificate block ===

def _render_stub_certificate(monkeypatch, tmp_path):
    """Render the mock page from a stub certified report; capture what
    build_dashboard receives instead of drawing the page."""
    from types import SimpleNamespace

    import numpy as np

    from certgate.constants import TAU_GRID
    from certgate.model import Head
    from examples import explain_dashboard_mock as page

    captured = {}

    def _fake_build_dashboard(head, x, *, tau_star, out_path, **kw):
        captured.update(tau_star=tau_star, **kw)
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write("<html><body></body></html>")
        return out_path

    monkeypatch.setattr(page, "build_dashboard", _fake_build_dashboard)
    head = Head(coef=np.array([1.0]), intercept=0.0, mu=np.array([0.0]),
                sd=np.array([1.0]))
    x = np.array([[1.585627263740381], [3.0], [0.1]])
    cohort = SimpleNamespace(n_sites=3, n=3, x=x,
                             y=np.array([True, True, False]))
    res = dict(head=head,
               report={"operative": dict(alpha=0.1, tau=float(TAU_GRID[14]),
                                         tau_idx=14, deploy_mode="baseline",
                                         modes=["baseline"])},
               cohorts=dict(train=cohort, aux=cohort, cal=cohort,
                            target=cohort),
               feature_names=["f0"], t_sites=["h1", "h2", "h3"],
               n_records=3, n_sites=12, replicate=0)
    page.render(res, str(tmp_path / "explain_dashboard_mock.html"),
                corpus_note="stub", provenance_comment="<!-- stub -->",
                verbose=False)
    return captured


def test_mock_page_deploys_the_unrounded_certified_tau(monkeypatch, tmp_path):
    """The page gates on the deployed double; only the banner copy is rounded.

    Ref: audit 2026-10 GAP-example-builders-1, explain-13 (contract C4).
    """
    from certgate.constants import TAU_GRID

    captured = _render_stub_certificate(monkeypatch, tmp_path)
    assert captured["tau_star"] == float(TAU_GRID[14])     # 0.8300000000000001
    cert = captured["certificate"]
    assert cert["tau"] == 0.83 and cert["tau_idx"] == 14


def test_mock_page_banner_carries_selected_claim_joint_level(monkeypatch,
                                                             tmp_path):
    """delta is per rung; the displayed rung was selected from the ladder, so
    the page states the joint level 1 - len(ALPHA_LADDER)*delta and the tagged
    assumption. Ref: audit 2026-10 GAP-example-builders-4,
    GAP-estimand-wording-all-surfaces-6.
    """
    cert = _render_stub_certificate(monkeypatch, tmp_path)["certificate"]
    assert cert["joint_confidence_over_ladder"] == 0.9
    assert cert["delta"] == 0.05
    assert cert["tagged_assumption"] == "exchangeability"
    assert cert["deploy_mode"] == "baseline" and "mode" not in cert


def _committed_mock_payload():
    root = pathlib.Path(__file__).resolve().parents[1]
    html = (root / "examples" / "explain_dashboard_mock.html").read_text(
        encoding="utf-8")
    prefix = "const DATA = "
    line = next(l for l in html.splitlines() if l.startswith(prefix))
    return html, json.loads(line[len(prefix):].rstrip(";"))


def test_committed_mock_dashboard_certificate_states_joint_level():
    """The committed page carries the joint level, the tagged assumption and
    the influence-weighted estimand wording. Ref: audit 2026-10
    GAP-estimand-wording-all-surfaces-3, -6."""
    html, payload = _committed_mock_payload()
    cert = payload["certificate"]
    assert cert["joint_confidence_over_ladder"] == 0.9
    assert cert["tagged_assumption"] == "exchangeability"
    assert "mode" not in cert
    assert "jointly" in html
    assert "influence-weighted" in html
