"""run_eicu's certification path and its post-hoc side-cars.

The end-to-end honest-outcome smoke, the reliability-panel wiring and RP-8
guards, summary sections, faithfulness, assert_aggregate_only, the house-
helper identity pins, and the explain_dashboard_eicu cross-check guards.
Split from test_eicu_path.py on 2026-08-25; the tests are relocated verbatim.
"""
from __future__ import annotations

import csv
import json
import os
from collections import Counter

import numpy as np
import pytest

from certgate import reliability as rp
from certgate.constants import ALPHA_LADDER, SEED
from certgate.harness import hard_violation
from certgate.model import fit_head
from certgate.pipeline import run_certgate
from certgate.report import render_text
from examples import explain_dashboard_eicu as dash_eicu
from experiments import eicu_etl as etl
from experiments import panel_s2_tables
from experiments import run_eicu
from experiments import run_synthetic

from _eicu_helpers import _assert_honest, mock_small, pipeline_small


# ============================================ 18-21. the certification path ===

def test_smoke_end_to_end_reaches_an_honest_outcome(pipeline_small):
    """The whole path on the pooled target arm, plus one per-hospital pool.

    The pooled arm holds 24 hospitals; the per-hospital pool has K == 1.
    Certification is never asserted. The assertion is that whatever is issued
    survives the oracle.
    """
    rep, ctx = pipeline_small["rep"], pipeline_small
    outcome = _assert_honest(rep, ctx)
    assert outcome in ("certified", "declined")
    assert rep["reason"] is None                   # the pooled arm is not gated
    assert [r["alpha"] for r in rep["certified"]] == list(ALPHA_LADDER)
    assert all(r["status"] in ("certified", "declined") for r in rep["certified"])

    # target identity is validated and bound, K = 24 >= BBSE_MIN_TARGET_SITES
    assert "target_site_id" in rep["provenance"]["input_hashes"]
    assert "target_site_labels" in rep["provenance"]["input_hashes"]
    assert rep["diagnostic"]["target_site_id_supplied"] is True
    assert len(set(ctx["tgt_sites"])) == etl.EICU_N_TARGET_SITES
    assert ctx["target"].x.dtype == np.float64
    assert np.isfinite(ctx["target"].x).all()

    # ---- per-hospital arm: target_site_id supplied even though K == 1 ----
    site, _n = Counter(ctx["tgt_sites"]).most_common(1)[0]
    rows = np.array([i for i in ctx["idx"]["target"]
                     if ctx["site_raw"][i] == site], dtype=int)
    rep1 = run_certgate(ctx["train"], ctx["aux"], ctx["cal"], ctx["x"][rows],
                        target_label=site,
                        target_site_id=[ctx["site_raw"][i] for i in rows],
                        oracle_target_y=ctx["y_bool"][rows])
    assert rep1["reason"] in (None, "pool-too-small")
    assert sum(rep1["decline_partition"].values()) == len(rows)
    assert rep1["diagnostic"]["target_site_id_supplied"] is True
    assert "[partition]" in render_text(rep1)
    if rep1["operative"] is not None:
        head = fit_head(ctx["train"])
        err = head.predict(ctx["x"][rows]) != ctx["y_bool"][rows]
        assert not hard_violation(err[rep1["answered_mask"]],
                                  rep1["operative"]["alpha"])


def test_the_honesty_assertion_fires_on_a_bad_certificate(pipeline_small):
    """The honesty check must not be dead code.

    At the mock's frozen signal strength both arms decline, so the certified
    branch of _assert_honest -- the oracle hard_violation gate this whole file
    exists to reach -- would never execute. It is therefore driven both ways
    against the real head and held-out pool: a certificate answering exactly
    the head's mistakes must be rejected, one answering only correct records
    accepted.
    """
    ctx = pipeline_small
    head = fit_head(ctx["train"])
    err = head.predict(ctx["target"].x) != ctx["target"].y
    n = ctx["target"].n
    assert int(err.sum()) >= 10, "need a non-trivial error set to violate with"

    def _rep(answered):
        k = int(answered.sum())
        return dict(
            target_label="synthetic-probe", reason=None, certified=[],
            operative=dict(alpha=0.10, tau=0.9, tau_idx=0,
                           deploy_mode="baseline", modes=["baseline"]),
            estimated=None,
            diagnostic=dict(coverage=k / n, n_cal_carrying=63),
            decline_partition={"answered": k, "below_tau": n - k, "failsafe": 0,
                               "pool-too-small": 0, "insufficient-clusters": 0},
            answered_mask=answered, provenance={})

    with pytest.raises(AssertionError):
        _assert_honest(_rep(err), ctx)               # answers only its mistakes
    assert _assert_honest(_rep(~err), ctx) == "certified"


@pytest.fixture(scope="module")
def mock_certified_run(tmp_path_factory, mock_small):
    """One quick run_certification on the always-on corpus, run once.

    This is the only always-on test that drives the runner rather than the
    pipeline, so it is the only place the post-hoc panel's wiring into run_eicu
    is exercised: gated writers, summary section, figure skip, label plumbing.
    quick=True skips the figures, which keeps the cost in the seconds.
    """
    out = str(tmp_path_factory.mktemp("eicu_panel_run") / "out")
    payload = run_eicu.run_certification(mock_small["dir"], out,
                                         replicates=1, quick=True,
                                         verbose=False)
    return dict(out=out, payload=payload)


def test_mock_run_writes_the_reliability_panel(mock_certified_run):
    """The post-hoc panel reaches disk, gated and labelled.

    Added 2026-08-01, after the extract was read. The mock declines every rung
    by arithmetic, so this also exercises the tau_star=None, all-False-mask
    branch on the runner. That branch is a legal shape, not a crash: every
    answered statistic is None carrying undefined-point, and the artifact is
    still strict JSON.
    """
    out = mock_certified_run["out"]

    raw = open(os.path.join(out, "EICU_reliability_panel.json"),
               encoding="utf-8").read()
    # nan and Infinity are not valid JSON. A reader would either choke or, in
    # Python, silently produce a float no downstream tool can print.
    assert "NaN" not in raw and "Infinity" not in raw
    doc = json.loads(raw, parse_constant=_reject_json_constant)
    assert "POST-HOC" in doc["post_hoc"]
    assert doc["post_hoc"] == rp.POST_HOC_LABEL
    assert len(doc["panels"]) == 1
    panel = doc["panels"][0]

    # the panel carries the sandbox's own root seed, never certgate's.
    # Re-pointing it at constants.SEED would silently discard the external
    # verification that is the whole reason to port rather than re-derive.
    assert panel["settings"]["seed"] == rp.PANEL_SEED == 20260731
    assert panel["settings"]["seed"] != SEED
    assert panel["schema_version"] == "srp/1"
    assert panel["generated_utc"] is None            # no wall clock, ever
    assert panel["counts"]["n_sites"] == etl.EICU_N_TARGET_SITES
    assert panel["operative_alpha"] is None          # the mock certifies nothing
    assert panel["counts"]["n_answered"] == 0
    for block in (panel["ece"]["answered"],
                  panel["calibration"]["answered"],
                  panel["brier"]["primary_answered"],
                  panel["skill"]["contrast"]):
        assert block["ci"] is None
        assert block["ci_status"] in rp.CI_STATUSES
    # the declined scope is fully populated at K = 24 >= MIN_SITES_FOR_CI
    assert panel["ece"]["declined"]["ece"] is not None
    assert panel["skill"]["all"]["ci_status"] == "ok"

    rows = list(csv.DictReader(open(os.path.join(out, "EICU_reliability.csv"),
                                    encoding="ascii")))
    assert len(rows) == 2 * (len(rp.DEFAULT_BIN_EDGES) - 1)      # 14 per replicate
    assert list(rows[0]) == (["post_hoc", "replicate", "arm"]
                             + list(rp.PANEL_RELIABILITY_FIELDS))
    assert {r["scope"] for r in rows} == {"answered", "declined"}
    assert all(r["ci_status"] in rp.CI_STATUSES for r in rows)
    # RP-9: the CSV is the panel artifact most easily detached from the
    # directory that explains it, so the label rides on every row rather than
    # being inherited from a neighbouring file.
    assert all(r["post_hoc"] == rp.POST_HOC_LABEL for r in rows)

    text = open(os.path.join(out, "EICU-SUMMARY.md"), encoding="utf-8").read()
    assert "## EICU-RELIABILITY" in text
    # EICU_SUMMARY_SECTIONS is APPEND-ONLY. A new section goes last so that no
    # section written before it moves, which is what keeps every
    # EICU-SUMMARY.md already on disk parseable. The panel sits at index 5 and
    # the subgroups section after it.
    assert run_eicu.EICU_SUMMARY_SECTIONS.index("EICU-RELIABILITY") == 5
    assert run_eicu.EICU_SUMMARY_SECTIONS.index("EICU-SUBGROUPS") == 6
    # the value-function contrast is appended after the subgroups, again last
    assert "EICU-FAITHFULNESS" == run_eicu.EICU_SUMMARY_SECTIONS[-1]
    block = mock_certified_run["payload"]["reliability"]
    assert block["post_hoc"] == rp.POST_HOC_LABEL
    assert block["n_panels"] == 1
    # RP-9: the estimand disclosures travel with the numbers into the
    # human-facing summary. notes[1] governs exactly the arrangement the block
    # prints: brier_reference, brier_primary_matched and brier_difference side
    # by side.
    assert block["notes"] == list(rp.NOTES)
    assert "MARGINAL" in block["notes"][1]
    assert "not independent" in block["replicate_spread_note"] or \
        "NOT independent" in block["replicate_spread_note"]
    # the key names the whole three-name interval dict it holds; the paired
    # interval is the brier_difference member inside it
    assert "brier_difference_ci_replicate0" not in block
    assert "brier_reference_ci_replicate0" in block
    assert block["ci_status_counts"]                  # the vocabulary is counted
    assert set(block["ci_status_counts"]) <= set(rp.CI_STATUSES)
    assert set(block["calibration_status_answered_counts"]) <= set(
        rp.FIT_STATUSES)
    # the label reaches the run warnings too, hence EICU_diagnostics.json and
    # the EICU-POOLED block: a separate JSON file inherits nothing.
    diag = json.load(open(os.path.join(out, "EICU_diagnostics.json"),
                          encoding="utf-8"))
    assert rp.POST_HOC_LABEL in diag["warnings"]
    # quick=True skips every figure, the panel's included
    assert not os.path.exists(os.path.join(out,
                                           "EICU_reliability_panel.png"))

    # nothing forbidden, nothing record-length, at any depth
    run_eicu.assert_aggregate_only(run_eicu._json_ready(doc),
                                   "EICU_reliability_panel.json")
    _assert_no_forbidden_key(doc)


def test_mock_run_writes_the_faithfulness_block(mock_certified_run):
    """The post-hoc value-function contrast reaches disk, gated and labelled.

    The always-on mock declines every rung, so this exercises the tau=None
    branch on the runner. No rows are fabricated, the CSV is header-only, and
    the summary block still carries the label and a no-certificate status per
    replicate.
    """
    out = mock_certified_run["out"]
    block = mock_certified_run["payload"]["faithfulness"]
    assert block["post_hoc"] == run_eicu.EICU_FAITHFULNESS_LABEL
    assert block["k"] == run_eicu.EICU_FAITHFULNESS_TOP_K
    assert block["n_replicates_ok"] == 0
    assert [sc["status"] for sc in block["replicates"]] == ["no-certificate"]
    assert block["features"] == {}
    assert block["max_abs_diff_vs_abstention_ranking"] is None
    rows = list(csv.DictReader(open(os.path.join(out, "EICU_faithfulness.csv"),
                                    encoding="ascii")))
    assert rows == []
    text = open(os.path.join(out, "EICU-SUMMARY.md"), encoding="utf-8").read()
    assert "## EICU-FAITHFULNESS" in text
    run_eicu.assert_aggregate_only(run_eicu._json_ready(block),
                                   "EICU-FAITHFULNESS")
    _assert_no_forbidden_key(block)


def test_faithfulness_rows_on_a_certified_head():
    """The block on a head that does certify, the synthetic fixture.

    It emits k rows per replicate under both value functions, the
    interventional gap reproduces cohort_abstention_profile exactly, and under
    an identity covariance the two value functions coincide.
    """
    from certgate.data import SimConfig, draw_cohort, split_sites
    from certgate.model import fit_head
    from certgate.explain import cohort_abstention_profile
    rng = np.random.default_rng(5)
    coh = draw_cohort(SimConfig(), 40, rng)
    train, _, _ = split_sites(coh, rng)
    head = fit_head(train)
    target = draw_cohort(SimConfig(), 6, rng, site_label_prefix="t")
    names = [f"f{j}" for j in range(head.coef.shape[0])]
    tau = 0.75
    rows, sc = run_eicu._faithfulness_rows(head, train, target, names, tau,
                                           0, "primary", k=8)
    assert sc["status"] == "ok" and len(rows) == 8
    prof = cohort_abstention_profile(head, target.x,
                                     head.score(target.x) >= tau)
    for r in rows:
        j = names.index(r["feature"])
        assert abs(r["gap_int"] - float(prof["gap"][j])) < 1e-6
    assert {r["rank_int"] for r in rows} == set(range(1, 9))
    assert {r["rank_cond"] for r in rows} == set(range(1, 9))
    assert sc["top_driver_int"] == names[int(prof["gap_ranking"][0])]
    assert sc["n_answered"] + sc["n_declined"] == target.n
    for r in rows:
        run_eicu.assert_aggregate_only(r, "faithfulness-row")


def _reject_json_constant(token):
    raise AssertionError(f"non-finite JSON constant {token!r} in the panel")


def _assert_no_forbidden_key(node):
    """Recursive: no forbidden key may hide under a nested block."""
    stack = [node]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            for k, v in item.items():
                assert k not in run_eicu.EICU_FORBIDDEN_OUT_KEYS, k
                stack.append(v)
        elif isinstance(item, (list, tuple)):
            assert len(item) <= run_eicu.EICU_MAX_OUTPUT_LEN
            stack.extend(item)


def test_panel_gate_is_the_deployed_mask_not_a_rounded_tau(pipeline_small):
    """The certified branch of the eICU panel call, unreachable on the mock.

    Two things are pinned:

      - panel_from_head derives the mask from head.score(x) >= tau itself, so
        a driver never constructs p and the predict_proba / score conflation
        is structurally unreachable.
      - a mask re-derived from a tau rounded to 6 dp, which is what _eval_rung
        stores, is rejected when it disagrees with the deployed one.
    """
    ctx = pipeline_small
    head = fit_head(ctx["train"])
    target = ctx["target"]
    scores = head.score(target.x)
    # an actual score value, so nudging tau up by one ulp is guaranteed to drop
    # at least that record out of the answered set
    tau = float(np.sort(scores)[scores.size // 3])

    panel = rp.panel_from_head(head, target.x, target.y, target.site_id, tau,
                               n_boot=32)
    assert panel["counts"]["n_answered"] == int((scores >= tau).sum())
    assert panel["counts"]["n_answered"] > 0

    # the same call with the deployed mask supplied is identical, not merely close
    same = rp.panel_from_head(head, target.x, target.y, target.site_id, tau,
                              answered_mask=(scores >= tau), n_boot=32)
    assert same == panel

    # a mask built at a tau that rounds to a different set is refused
    bad = scores >= float(np.nextafter(tau, 1.0))
    assert not np.array_equal(bad, scores >= tau)
    with pytest.raises(rp.PanelError, match="deployed-mask-mismatch"):
        rp.panel_from_head(head, target.x, target.y, target.site_id, tau,
                           answered_mask=bad, n_boot=32)


def _panel_for_figure(*, answered_share, with_reference):
    """A small real panel payload, shaped as run_certification builds one."""
    rng = np.random.default_rng(11)
    n_sites, per_site = 24, 40
    n = n_sites * per_site
    p = rng.uniform(0.0, 1.0, n)
    y = rng.uniform(0.0, 1.0, n) < p
    site_id = np.repeat(np.arange(n_sites), per_site)
    answered = rng.uniform(0.0, 1.0, n) < answered_share
    p_ref = (np.clip(p + rng.normal(0.0, 0.1, n), 0.0, 1.0)
             if with_reference else None)
    panel = rp.selective_reliability_panel(p, answered, site_id, y, p_ref,
                                           n_boot=24)
    return {"replicate": 0, "arm": "primary", "operative_alpha": 0.10, **panel}


def test_reliability_figure_renders_including_the_degenerate_shape(tmp_path):
    """_reliability_figure, driven directly on both shapes it can meet.

    The always-on mock arm runs quick=True and skips every figure, so a crash
    here would abort a 20-replicate real run after all the certification work
    was done. The shapes are an ordinary panel with a reference scorer, and the
    degenerate all-declined panel with reference None. The second takes the
    no-reference-matched-Brier and empty-answered-curve branches together.
    """
    normal = _panel_for_figure(answered_share=0.6, with_reference=True)
    degenerate = _panel_for_figure(answered_share=0.0, with_reference=False)
    assert degenerate["brier"]["reference"] is None
    assert degenerate["counts"]["n_answered"] == 0

    for name, payloads in (("normal", [normal]),
                           ("degenerate", [degenerate]),
                           ("mixed", [normal, degenerate])):
        out = str(tmp_path / name)
        os.makedirs(out, exist_ok=True)
        run_eicu._reliability_figure(out, payloads, verbose=False)
        png = os.path.join(out, "EICU_reliability_panel.png")
        assert os.path.exists(png) and os.path.getsize(png) > 0, name

    # and an empty accumulator (every replicate's panel skipped) is a no-op,
    # never an exception on panel_payloads[0]
    out = str(tmp_path / "empty")
    os.makedirs(out, exist_ok=True)
    run_eicu._reliability_figure(out, [], verbose=False)
    assert not os.path.exists(os.path.join(out,
                                           "EICU_reliability_panel.png"))


def test_reliability_figure_survives_a_point_outside_its_own_interval(tmp_path):
    """A percentile interval that does not straddle its own point estimate.

    site_bootstrap_ci quantiles the resampling distribution and promises no
    such straddle, and for the paired brier_difference over 24 sites the point
    can land outside. A raw point - ci['lo'] then goes negative and matplotlib
    raises rather than warning -- inside _figures, which run_certification
    calls before the summary payload exists, so a descriptive figure takes the
    whole run's summary down with it. _panel_for_figure cannot reach the shape,
    so it is planted here rather than waited for.
    """
    # the clamp itself, at the one place it is defined
    assert rp.panel_ci_halfwidths(0.001, {"lo": 0.004, "hi": 0.009}) == (0.0,
                                                                         0.008)
    assert rp.panel_ci_halfwidths(0.5, {"lo": 0.4, "hi": 0.6}) == (
        pytest.approx(0.1), pytest.approx(0.1))
    assert rp.panel_ci_halfwidths(0.5, None) == (0.0, 0.0)
    # a non-'ok' status carries no interval, and never a zero-width one
    assert rp.panel_ci_halfwidths(0.5, {"lo": 0.4, "hi": 0.6},
                                  "degenerate-resamples") == (0.0, 0.0)

    payload = _panel_for_figure(answered_share=0.6, with_reference=True)

    ref = payload["brier"]["reference"]
    assert ref is not None and ref["ci"] is not None
    point = float(ref["brier_difference"])
    # push both endpoints above the point: lo > point is the negative-yerr case
    ref["ci"]["brier_difference"] = {"lo": point + 0.01, "hi": point + 0.02}

    planted = 0
    for scope in rp.PANEL_CURVE_SCOPES:
        for rec in payload["reliability"][scope]:
            if rec["ci_status"] == "ok" and rec["observed"] is not None:
                rec["ci"] = {"lo": rec["observed"] + 0.05,
                             "hi": rec["observed"] + 0.10}
                planted += 1
                break
    assert planted, "no 'ok' bin to plant the inverted interval in"

    # the series contract clamps rather than emitting a negative half-width
    for scope in rp.PANEL_CURVE_SCOPES:
        _xs, _ys, lo, hi = rp.panel_reliability_series(payload, scope)
        assert all(v >= 0.0 for v in lo), scope
        assert all(v >= 0.0 for v in hi), scope

    out = str(tmp_path / "inverted")
    os.makedirs(out, exist_ok=True)
    run_eicu._reliability_figure(out, [payload], verbose=False)
    png = os.path.join(out, "EICU_reliability_panel.png")
    assert os.path.exists(png) and os.path.getsize(png) > 0


def test_reliability_curve_legend_names_every_plotted_scope(tmp_path,
                                                            monkeypatch):
    """The legend entry belongs to the first payload that plots a scope.

    It does not belong to base. Under RP-8 base is merely whichever replicate
    survived, and if that one answered nothing its answered curve is empty. A
    base-only label then leaves every later replicate's answered points as
    unlabelled scattered dots with no key.
    """
    base = _panel_for_figure(answered_share=0.0, with_reference=False)
    later = dict(_panel_for_figure(answered_share=0.6, with_reference=True),
                 replicate=1)
    assert base["replicate"] == 0 and base["counts"]["n_answered"] == 0

    seen = {}
    real_close = run_eicu.plt.close

    def _capture(fig):
        legend = fig.axes[0].get_legend()
        seen["labels"] = [t.get_text() for t in legend.get_texts()]
        real_close(fig)

    monkeypatch.setattr(run_eicu.plt, "close", _capture)
    out = str(tmp_path / "legend")
    os.makedirs(out, exist_ok=True)
    run_eicu._reliability_figure(out, [base, later], verbose=False)

    assert set(seen["labels"]) == {"identity", "answered", "declined"}


def test_a_panel_error_costs_a_diagnostic_and_never_the_certificate(
        tmp_path, monkeypatch, capsys, mock_small):
    """RP-8, the guard itself: the catch around the panel call.

    That wrapper bounds the blast radius of every failure channel we cannot
    name. It sits after every certification call for the replicate and before
    any artifact is written, so losing it trades a whole 20-replicate run for
    a missing diagnostic.

    The failure is planted at run_eicu.rp.panel_from_head, the single entry
    point SPEC names. Four things are asserted, (a) to (d) below; the first is
    the whole point, that the run returns rather than propagating.
    """
    calls = []

    def _boom(*args, **kwargs):
        calls.append(len(calls))
        raise rp.PanelError("planted-panel-failure (RP-8 regression probe)")

    monkeypatch.setattr(run_eicu.rp, "panel_from_head", _boom)

    out = str(tmp_path / "rp8")
    # quick=False on purpose: the always-on panel test runs quick=True and so
    # never reaches _figures, which is exactly where an empty accumulator would
    # strand a 20-replicate run after all the certification work was done.
    payload = run_eicu.run_certification(mock_small["dir"], out,
                                         replicates=1, quick=False,
                                         verbose=False)
    assert calls == [0], "the planted failure must be reached exactly once"

    # (a) the certified run completed and its own artifacts are all there
    for name in ("EICU_pooled.csv", "EICU_per_site.csv",
                 "EICU_diagnostics.json", "EICU_certificate.json",
                 "EICU-SUMMARY.md", "EICU_pooled.png", "EICU_per_site.png"):
        assert os.path.exists(os.path.join(out, name)), name
    assert payload["pooled"]["replicates"] == 1
    for alpha in ALPHA_LADDER:
        # every rung was still evaluated for the replicate whose panel died
        assert payload["pooled"]["rungs"][str(float(alpha))][
            "n_replicates"] == 1

    # (b) the swallow is not silent: warnings and stderr, naming the replicate
    diag = json.load(open(os.path.join(out, "EICU_diagnostics.json"),
                          encoding="utf-8"))
    skips = [w for w in diag["warnings"] if "[MEASURE] RP-8" in w]
    assert len(skips) == 1, diag["warnings"]
    assert "SKIPPED for replicate 0" in skips[0]
    assert "planted-panel-failure" in skips[0]
    assert "unaffected" in skips[0]
    assert skips == [w for w in payload["pooled"]["warnings"]
                     if "[MEASURE] RP-8" in w]
    assert "[MEASURE] RP-8" in capsys.readouterr().err
    # the POST-HOC label still rides along: the label is unconditional, the
    # panel is not
    assert rp.POST_HOC_LABEL in diag["warnings"]

    # (c) the shortfall is arithmetic (SPEC RP-8: n_panels < replicates), the
    # no-panel note is true of the case that produced it, and the summary still
    # parses with every certification section present and in frozen order
    block = payload["reliability"]
    assert block["n_panels"] == 0 < block["replicates"] == 1
    assert block["post_hoc"] == rp.POST_HOC_LABEL
    # one replicate ran here, and was certified; only its panel is missing. The
    # note must cover the case that produced it and point at the warnings that
    # explain it, rather than claiming the arm ran zero replicates.
    note = " ".join(block["note"].split())
    assert "replicates = 1" in note
    assert "EVERY replicate's panel was SKIPPED under RP-8" in note
    assert "[MEASURE] RP-8" in note
    for key in ("ece_answered", "brier_difference", "consistency"):
        assert key not in block, f"{key} claims a statistic no panel produced"

    path = os.path.join(out, "EICU-SUMMARY.md")
    sections = run_eicu._existing_summary_blocks(path)
    expected = [s for s in run_eicu.EICU_SUMMARY_SECTIONS
                if s in run_eicu._certification_blocks(payload)]
    assert list(sections) == expected == ["EICU-POOLED", "EICU-PERSITE",
                                          "EICU-COMPARATOR",
                                          "EICU-RELIABILITY",
                                          "EICU-SUBGROUPS",
                                          "EICU-FAITHFULNESS"]
    for name, rendered in sections.items():
        body = json.loads(rendered.strip().removeprefix("```json")
                          .removesuffix("```"))
        assert body["_run"]["replicates"] == 1, name
    assert json.loads(sections["EICU-RELIABILITY"].strip()
                      .removeprefix("```json").removesuffix("```"))[
        "n_panels"] == 0

    # (d) nothing claims a panel that never ran. The two panel artifacts are
    # still written but empty: their absence would read as "never wired in"
    # rather than "skipped, here is why". The figure is not written at all,
    # since its title would name a replicate whose curve does not exist
    # (quick=False, so its siblings are written).
    doc = json.loads(open(os.path.join(out, "EICU_reliability_panel.json"),
                          encoding="utf-8").read(),
                     parse_constant=_reject_json_constant)
    assert doc["panels"] == []
    assert doc["post_hoc"] == rp.POST_HOC_LABEL
    csv_path = os.path.join(out, "EICU_reliability.csv")
    rows = list(csv.DictReader(open(csv_path, encoding="ascii")))
    assert rows == []
    assert list(csv.reader(open(csv_path, encoding="ascii")))[0] == (
        ["post_hoc", "replicate", "arm"] + list(rp.PANEL_RELIABILITY_FIELDS))
    assert not os.path.exists(os.path.join(out,
                                           "EICU_reliability_panel.png"))


def test_run_eicu_refuses_record_level_output():
    """Every write goes through the record-level refusal (T-17).

    The PhysioNet DUA restricts derived record-level artifacts and
    experiments/out/ is tracked. The refusal covers the arrays a naive
    json.dump of a report would emit.
    """
    for payload in (
        {"stay_id": [1, 2, 3]},
        {"summary": {"per_site": {"site_raw": ["hosp-1"]}}},
        {"answered_mask": [True, False]},
        {"comparator_predicted_mortality": [0.1]},
        {"split_idx": {"train": [0]}},
        {"rows": list(range(run_eicu.EICU_MAX_OUTPUT_LEN + 1))},
        {"rows": np.zeros(run_eicu.EICU_MAX_OUTPUT_LEN + 1)},
    ):
        with pytest.raises(etl.EicuError, match="record-level-output"):
            run_eicu.assert_aggregate_only(payload, "test")

    assert run_eicu.EICU_MAX_OUTPUT_LEN == 512     # > 208 sites, < any record array
    # an aggregate payload of the shape the runner actually writes passes
    run_eicu.assert_aggregate_only(
        {"alpha": 0.1, "coverage": 0.72, "per_site": [{"site": "hosp-1",
                                                       "n_answered": 40}],
         "attrition": [{"step": s, "n_stays": 1, "n_sites": 1}
                       for s in etl.EICU_ATTRITION_STEPS]}, "test")


def test_rm_helpers_are_the_synthetic_ones():
    """Real-data numbers use the same helpers as the paper's synthetic ones."""
    assert run_eicu._rm_on_pool is run_synthetic._rm_on_pool
    assert run_eicu._per_site_exceed_frac is run_synthetic._per_site_exceed_frac
    assert run_eicu._rate is run_synthetic._rate
    assert run_eicu._write_csv is run_synthetic._write_csv
    assert run_eicu._row_for is run_synthetic._row_for
    # the rank AUC was a byte-equivalent clone of the ETL's, the one house
    # helper that had escaped this net
    assert run_eicu._auc is etl._rank_auc
    # the Table 6/7 replay scores its certificates with the same estimand
    assert panel_s2_tables._rm_on_pool is run_synthetic._rm_on_pool


# ---------------------------------------------------------------------------
# 2026-08-10 hardening -- audit fixes around the panel wiring and the eICU
# dashboard driver. SPEC, amended the same day: a descriptive layer may never
# abort the certified run.
# ---------------------------------------------------------------------------

def test_a_non_panel_error_also_costs_only_the_diagnostic(
        tmp_path, monkeypatch, mock_small):
    """RP-8 is about who survives the crash, not the exception's type.

    Two panel escapes are not PanelError: a length-mismatched mask raises a
    bare numpy broadcast ValueError, and a duck-typed head without
    predict_proba raises AttributeError. The broadened catch must swallow
    either, keep the certificate, and name the unexpected type as a wiring
    defect rather than a data rejection.
    """
    def _boom(*args, **kwargs):
        raise ValueError("planted-non-panel-failure (broadcast-shape probe)")

    monkeypatch.setattr(run_eicu.rp, "panel_from_head", _boom)
    out = str(tmp_path / "rp8b")
    payload = run_eicu.run_certification(mock_small["dir"], out,
                                         replicates=1, quick=True,
                                         verbose=False)
    skips = [w for w in payload["pooled"]["warnings"]
             if "[MEASURE] RP-8" in w]
    assert len(skips) == 1, payload["pooled"]["warnings"]
    assert "planted-non-panel-failure" in skips[0]
    assert "UNEXPECTED ValueError" in skips[0]
    assert "wiring defect" in skips[0]
    # and a PanelError stays an expected rejection, with no wiring-defect
    # callout; pinned by test_a_panel_error_costs_a_diagnostic_and_never_the_
    # certificate, whose message assertions would fail on the [UNEXPECTED tag


def test_per_item_keys_items_must_be_dicts(tmp_path):
    """Per-item keys must hold dicts, one aggregate payload each.

    The gate is a no-op on scalars, so a flat float list under the named key --
    the record-level shape it exists to stop -- escapes ungated: 600 floats
    pass where 513 would abort any other key.
    """
    good = {"post_hoc": rp.POST_HOC_LABEL,
            "panels": [{"replicate": 0, "ece": 0.1}]}
    path = str(tmp_path / "good.json")
    run_eicu._write_json(path, good, "test.good", per_item_keys=("panels",))
    with open(path, encoding="utf-8") as fh:
        assert json.load(fh)["panels"][0]["replicate"] == 0

    flat = {"post_hoc": rp.POST_HOC_LABEL,
            "panels": [float(i) for i in range(600)]}
    with pytest.raises(etl.EicuError,
                       match="must each be one aggregate payload"):
        run_eicu._write_json(str(tmp_path / "flat.json"), flat,
                             "test.flat", per_item_keys=("panels",))

    # an ndarray is flattened to a plain list by _json_ready first, so it is
    # the same smuggle in a different wrapper
    arr = {"panels": np.arange(600, dtype=float)}
    with pytest.raises(etl.EicuError,
                       match="must each be one aggregate payload"):
        run_eicu._write_json(str(tmp_path / "arr.json"), arr,
                             "test.arr", per_item_keys=("panels",))


def test_an_empty_panel_run_removes_a_stale_reliability_png(tmp_path):
    """A run that produced no panel clears the previous run's figure.

    A stale PNG left beside an EICU-SUMMARY.md reporting n_panels: 0 reads as
    current output. Reachable by re-running into the same --out under RP-8.
    """
    out = str(tmp_path)
    png = os.path.join(out, "EICU_reliability_panel.png")
    with open(png, "wb") as fh:
        fh.write(b"stale bytes from a previous run")
    run_eicu._reliability_figure(out, [], verbose=False)
    assert not os.path.exists(png)
    # and the no-op stays a no-op when there was nothing stale
    run_eicu._reliability_figure(out, [], verbose=False)
    assert not os.path.exists(png)


class _CalStub:
    n_sites = 74


def test_dashboard_cross_check_refuses_an_uncomparable_certificate(tmp_path):
    """A comparison that cannot be made is a failed cross-check.

    Guarding every comparison on "want is not None" opens a vacuous-success
    hole. A released certificate carrying none of the six fields -- operative
    null, from a run that certified no rung -- skips them all and still returns
    the "all match" banner string.
    """
    row = {"alpha": 0.1, "tau": 0.85, "tau_idx": 15, "deploy_mode": "baseline"}
    ref_path = str(tmp_path / "EICU_certificate.json")

    with open(ref_path, "w", encoding="utf-8") as fh:
        json.dump({"operative": None, "diagnostic": None}, fh)
    with pytest.raises(SystemExit, match="does not carry"):
        dash_eicu._cross_check(row, _CalStub(), 0.855, ref_path)

    # a fully-populated matching reference still returns the confirmation
    with open(ref_path, "w", encoding="utf-8") as fh:
        json.dump({"operative": {"alpha": 0.1, "tau": 0.85, "tau_idx": 15,
                                 "deploy_mode": "baseline"},
                   "diagnostic": {"coverage": 0.855, "n_cal": 74}}, fh)
    msg = dash_eicu._cross_check(row, _CalStub(), 0.855, ref_path)
    assert msg.startswith("alpha, tau, tau_idx")

    # a missing file stays the labelled-unverified path, never a false pass
    msg2 = dash_eicu._cross_check(row, _CalStub(), 0.855,
                                  str(tmp_path / "absent.json"))
    assert msg2.startswith(dash_eicu._UNVERIFIED)


def test_dashboard_answered_risk_never_prints_nan():
    """The banner never prints a literal 'nan (95% CI nan-nan)'.

    report._bootstrap_estimate emits NaN for an empty answered set, and a
    (NaN, NaN) ci95 when the top-up declines (audit V21).
    """
    nan = float("nan")
    assert dash_eicu._answered_risk(
        {"estimated": {"point": nan, "ci95": (nan, nan)}}) is None
    assert dash_eicu._answered_risk(
        {"estimated": {"point": 0.0387, "ci95": (0.0356, nan)}}) is None
    assert dash_eicu._answered_risk({}) is None
    assert dash_eicu._answered_risk(
        {"estimated": {"point": 0.0387, "ci95": (0.0356, 0.0422)}}
    ) == "0.0387 (95% CI 0.0356-0.0422)"


def test_dashboard_out_guard_refuses_the_sidecar_output_dirs(tmp_path):
    """The out guard covers the tracked sidecar directories too.

    Checking for "out" alone misses out-panel/ and out-sens/, which .gitignore
    declares tracked by design and where a record-level page must never land.
    """
    for d in ("out", "out-panel", "out-sens"):
        bad = os.path.join(str(tmp_path), d, "explain_dashboard_eicu.html")
        with pytest.raises(SystemExit, match="record-level-output"):
            dash_eicu._check_out_path(bad)
    ok = os.path.join(str(tmp_path), "pages",
                      "explain_dashboard_eicu_v2.html")
    assert dash_eicu._check_out_path(ok) == os.path.abspath(ok)


# ================================= 2026-09-04 fix pass: appended diagnostics ===
# Everything below was added after the extract was read, on the subgroups
# precedent: new keys and columns are APPENDED, the certified path computes
# what it computed before, and experiments/gate2_diff.py proves it on the
# frozen artifacts. These tests pin the shape -- every new value a scalar or
# None, through the aggregate gate -- not any number.

def _is_scalar_or_none(v):
    return v is None or isinstance(v, (bool, int, float, str))


def test_mock_run_appends_the_sub_24h_and_coef_rank_diagnostics(
        mock_certified_run):
    """EICU_diagnostics.json and the EICU-POOLED block carry the new blocks.

    The always-on mock declines every rung, so the answered / declined halves
    are None and the coefficient-rank block is empty; both are legal shapes
    and both must still be scalar-only and strict JSON."""
    out = mock_certified_run["out"]
    diag = json.load(open(os.path.join(out, "EICU_diagnostics.json"),
                          encoding="utf-8"))
    # the frozen keys are all still there, in front of the appended ones
    frozen = ["arm", "replicates", "n_records", "n_sites", "reference_check",
              "abstention_gap_ranking", "composition_three_way", "bbse",
              "n_target_sites_without_hospital_strata",
              "n_hospital_strata_rows", "warnings"]
    keys = list(diag)
    assert all(k in keys for k in frozen)
    assert keys.index("los_under_24h") > keys.index("warnings")
    assert keys.index("top_driver_coef_rank") > keys.index("los_under_24h")

    los = diag["los_under_24h"]
    assert isinstance(los, list) and len(los) == 1
    row = los[0]
    for k in ("replicate", "operative_alpha", "n_pool", "n_deaths_pool",
              "n_los_unavailable_pool", "n_lt_24h_pool",
              "n_deaths_lt_24h_pool", "n_answered", "n_declined",
              "n_lt_24h_answered", "n_lt_24h_declined",
              "n_deaths_lt_24h_declined"):
        assert k in row and _is_scalar_or_none(row[k]), k
    assert 0 <= row["n_lt_24h_pool"] <= row["n_pool"]
    assert 0 <= row["n_deaths_lt_24h_pool"] <= min(row["n_lt_24h_pool"],
                                                    row["n_deaths_pool"])
    assert row["operative_alpha"] is None          # the mock certifies nothing
    assert row["n_answered"] is None and row["n_lt_24h_declined"] is None

    rank = diag["top_driver_coef_rank"]
    assert rank["by_rung"] == {}                   # no certified rung, no rank
    assert rank["summary"] == dict(n=0, mode=None, min=None, max=None)
    assert "abstention_gap_ranking[0]" in rank["what"]

    pooled = mock_certified_run["payload"]["pooled"]
    block = pooled["los_under_24h"]
    assert block["threshold"] == run_eicu.EICU_LOS_WINDOW_HOURS == 24.0
    assert block["n_replicates"] == 1
    for k, v in block.items():
        assert _is_scalar_or_none(v), k
    assert block["mean_frac_lt_24h_pool"] is not None
    assert block["mean_frac_lt_24h_of_answered"] is None
    # the appended block sits after the frozen keys of the POOLED payload
    assert list(pooled).index("los_under_24h") > list(pooled).index("warnings")
    text = open(os.path.join(out, "EICU-SUMMARY.md"), encoding="utf-8").read()
    assert "los_under_24h" in text
    run_eicu.assert_aggregate_only(run_eicu._json_ready(diag),
                                   "EICU_diagnostics.json")
    _assert_no_forbidden_key(diag)


def test_mock_run_appends_the_comparator_and_per_site_columns(
        mock_certified_run):
    """The two CSVs gain APPENDED columns; the frozen columns lead unchanged."""
    out = mock_certified_run["out"]
    with open(os.path.join(out, "EICU_comparator.csv"), encoding="ascii") as fh:
        rows = list(csv.DictReader(fh))
        header = list(rows[0]) if rows else None
    frozen = ["replicate", "alpha", "n_answered", "certgate_answered_err",
              "apache_iva_brier_answered", "apache_iva_auc_answered",
              "n_apache_available"]
    appended = ["head_auc_pool", "head_brier_pool", "head_auc_answered",
                "head_brier_answered", "apache_iva_auc_pool",
                "apache_iva_brier_pool", "n_apache_available_pool"]
    assert header == frozen + appended
    assert len(rows) == len(ALPHA_LADDER)
    for r in rows:
        # whole-pool scores exist whether or not the rung certified
        assert 0.0 <= float(r["head_auc_pool"]) <= 1.0
        assert 0.0 <= float(r["head_brier_pool"]) <= 1.0
        assert int(r["n_apache_available_pool"]) >= int(r["n_apache_available"])
        # answered-set scores are empty on a declined rung, never 0.0
        assert r["head_auc_answered"] == "" and r["head_brier_answered"] == ""
        if int(r["n_apache_available_pool"]):
            assert 0.0 <= float(r["apache_iva_brier_pool"]) <= 1.0
    comp = mock_certified_run["payload"]["comparator"]
    for rung in comp["rungs"].values():
        for k in ("mean_head_auc_pool", "mean_head_brier_pool",
                  "mean_head_auc_answered", "mean_head_brier_answered",
                  "mean_apache_iva_auc_pool", "mean_apache_iva_brier_pool",
                  "apache_available_share_pool", "n_rows_pool"):
            assert k in rung and _is_scalar_or_none(rung[k]), k
        assert rung["mean_head_auc_pool"] is not None
        assert rung["mean_head_auc_answered"] is None
        assert "EVERY held-out stay" in rung["pool_note"]

    with open(os.path.join(out, "EICU_per_site.csv"), encoding="ascii") as fh:
        rows = list(csv.DictReader(fh))
    assert list(rows[0])[-1] == "share_75plus"
    assert list(rows[0])[:17] == [
        "replicate", "arm", "site", "alpha", "n_target", "reason",
        "certified", "tau", "coverage", "n_answered", "answered_err_rate",
        "hard", "numbedscategory", "teachingstatus", "region", "aps_coverage",
        "apv_coverage"]
    shares = [float(r["share_75plus"]) for r in rows if r["share_75plus"]]
    assert shares and all(0.0 <= s <= 1.0 for s in shares)
    per_site = mock_certified_run["payload"]["per_site"]
    for rung in per_site["rungs"].values():
        assert "share_75plus_vs_answered_err_spearman" in rung
        assert _is_scalar_or_none(rung["share_75plus_vs_answered_err_spearman"])
        assert isinstance(rung["n_pools_in_spearman"], int)
        assert "not" in rung["share_75plus_note"]      # non-independence stated


def test_mock_run_appends_the_aps_present_subgroup_dimension(
        mock_certified_run):
    """aps_present is the sixth, LAST dimension: its rows follow the unittype
    rows in every replicate, so a projection onto the five old dims is the
    old file."""
    out = mock_certified_run["out"]
    with open(os.path.join(out, "EICU_subgroups.csv"), encoding="ascii") as fh:
        rows = list(csv.DictReader(fh))
    dims_in_order = []
    for r in rows:
        if not dims_in_order or dims_in_order[-1] != r["dim"]:
            dims_in_order.append(r["dim"])
    assert dims_in_order == list(run_eicu.EICU_SUBGROUP_DIMS)
    assert run_eicu.EICU_SUBGROUP_DIMS[-1] == "aps_present"
    aps = [r for r in rows if r["dim"] == "aps_present"]
    assert sorted(r["level"] for r in aps) == ["absent", "present"]
    assert sum(int(r["n"]) for r in aps) == sum(
        int(r["n"]) for r in rows if r["dim"] == "gender")   # one partition each
    block = mock_certified_run["payload"]["subgroups"]
    assert set(block["dims"]["aps_present"]) == {"absent", "present"}
    note = block["dim_notes"]["aps_present"]
    assert "APACHE-ineligible admission types" in note
    assert "early discharge" not in note
    assert note == run_eicu.EICU_SUBGROUP_DIM_NOTES["aps_present"]


def test_subgroup_masks_read_the_presence_column_not_a_one_hot_prefix():
    names = ["age", "age__missing", "aps_present", "gender=Female",
             "gender=Male"]
    x = np.array([[70.0, 0, 1.0, 1, 0],
                  [80.0, 0, 0.0, 0, 1],
                  [40.0, 1, 1.0, 1, 0]])
    masks = run_eicu._subgroup_masks(x, names)
    assert masks["aps_present"]["present"].tolist() == [True, False, True]
    assert masks["aps_present"]["absent"].tolist() == [False, True, False]
    # every level of the new dim is a partition of the rows
    assert (masks["aps_present"]["present"]
            | masks["aps_present"]["absent"]).all()


def test_los_under_24h_row_counts_add_up():
    los = np.array([3.0, 30.0, np.nan, 12.0, 48.0, -2.0])
    y = np.array([True, False, True, True, False, False])
    ans = np.array([True, True, False, False, True, True])
    row = run_eicu._los_under_24h_row(los, y, ans, 3, 0.10)
    assert row == dict(replicate=3, operative_alpha=0.10, n_pool=6,
                       n_deaths_pool=3, n_los_unavailable_pool=1,
                       n_lt_24h_pool=3, n_deaths_lt_24h_pool=2,
                       n_answered=4, n_declined=2, n_lt_24h_answered=2,
                       n_lt_24h_declined=1, n_deaths_lt_24h_declined=1)
    # no certified rung: the pool counts stand, the halves are None
    row = run_eicu._los_under_24h_row(los, y, None, 0, None)
    assert row["n_lt_24h_pool"] == 3 and row["n_answered"] is None
    for v in row.values():
        assert _is_scalar_or_none(v)
    run_eicu.assert_aggregate_only(row, "los-row")


def test_share_75plus_excludes_imputed_ages():
    names = ["age", "age__missing", "aps_present"]
    x = np.array([[80.0, 0, 1], [60.0, 0, 1], [75.0, 0, 0], [63.2, 1, 0]])
    assert run_eicu._share_75plus(x, names) == round(2 / 3, 4)
    x_all_missing = np.array([[63.2, 1, 0], [63.2, 1, 1]])
    assert run_eicu._share_75plus(x_all_missing, names) is None


def test_top_driver_coef_rank_is_the_position_in_the_abs_coef_order():
    """On a head that certifies (the synthetic fixture) the rank is 1-based,
    consistent with argsort on |coef|, and the block's mode is well defined."""
    from certgate.data import SimConfig, draw_cohort, split_sites
    rng = np.random.default_rng(11)
    coh = draw_cohort(SimConfig(), 40, rng)
    train, _, _ = split_sites(coh, rng)
    head = fit_head(train)
    target = draw_cohort(SimConfig(), 6, rng, site_label_prefix="t")
    names = [f"f{j}" for j in range(head.coef.shape[0])]
    ranking = run_eicu._abstention_ranking(head, target.x, 0.75, names)
    entry = run_eicu._top_driver_coef_rank(head, names, ranking["ranking"])
    j = names.index(ranking["ranking"][0]["feature"])
    order = np.argsort(-np.abs(np.asarray(head.coef)), kind="mergesort")
    assert entry["abs_coef_rank"] == int(np.flatnonzero(order == j)[0]) + 1
    assert 1 <= entry["abs_coef_rank"] <= entry["n_features"] == len(names)
    assert entry["feature"] == names[j]
    assert entry["coef"] == round(float(head.coef[j]), 6)
    block = run_eicu._coef_rank_block({"r0_a0.1": entry,
                                       "r1_a0.1": dict(entry, abs_coef_rank=2),
                                       "r2_a0.1": dict(entry, abs_coef_rank=2)})
    assert block["summary"] == dict(n=3, mode=2,
                                    min=min(entry["abs_coef_rank"], 2),
                                    max=max(entry["abs_coef_rank"], 2))
    empty = run_eicu._top_driver_coef_rank(head, names, [])
    assert empty["abs_coef_rank"] is None and empty["n_features"] == len(names)


def test_run_eicu_cli_requires_out(tmp_path):
    """--out has no default any more: the old default was experiments/out/,
    the frozen release directory, and the summary + provenance are written in
    a finally: block even on --preflight. A forgotten flag must fail loudly
    before anything is opened."""
    with pytest.raises(SystemExit) as info:
        run_eicu.main(["--data", str(tmp_path), "--preflight"])
    assert info.value.code == 2                      # argparse usage error
    assert not any(p.name.startswith("EICU") for p in tmp_path.iterdir())


def test_dashboard_out_guard_refuses_any_out_prefixed_directory(tmp_path):
    """The guard is a prefix rule since 2026-09-04: a fixed list went stale
    (out-subgroups/, out-faithfulness/, out-rev2/, out-timing/)."""
    for d in ("out-subgroups", "out-faithfulness", "out-rev2", "out-timing",
              os.path.join("out-rev2", "nested")):
        bad = os.path.join(str(tmp_path), d, "explain_dashboard_eicu.html")
        with pytest.raises(SystemExit, match="record-level-output"):
            dash_eicu._check_out_path(bad)
    ok = os.path.join(str(tmp_path), "pages", "explain_dashboard_eicu.html")
    assert dash_eicu._check_out_path(ok) == os.path.abspath(ok)
