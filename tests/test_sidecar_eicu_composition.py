"""The post-hoc eICU composition/margin sidecar, on the MOCK corpus only.

experiments/eicu_composition_margin.py replays the released eICU primary arm
from the restricted extract; it is run by the DUA holder, never here. These
tests drive it end to end on a small schema-faithful mock (150 hospitals,
2,400 stays: about two seconds to generate, under a second per replicate),
against a reference run built from run_eicu's own builders on that mock.
They check that the output is aggregate-only, that every refusal path
(tampered certificate, tampered pooled cell, foreign extract, frozen
directory, record-level payload) writes nothing, that the exact margin equals
a direct per-site atom computation, and that the two composition formulas
are the ones the audit names. The real extract is never opened.

The CERTGATE_EICU=1 arm builds the reference with run_eicu.main itself
(--quick, two replicates; ~20 s) instead of the in-test builder.

Ref: audit 2026-10 BBSE-1 (contract C1), CORE-3.
"""
from __future__ import annotations

import json
import os
import shutil

import numpy as np
import pytest

from certgate.constants import ALPHA_LADDER, M_INFLUENCE, PI_CLIP, TAU_GRID
from certgate.data import SimConfig, draw_cohort, split_sites
from certgate.explain import composition
from certgate.model import fit_head
from certgate.pipeline import _feasibility
from certgate.report import provenance
from experiments import eicu_composition_margin as sc
from experiments import eicu_etl as etl
from experiments import eicu_mock as mock
from experiments import run_eicu as re_

from _eicu_helpers import _run_eicu

MOCK_SITES, MOCK_STAYS = 150, 2400      # >= EICU_MOCK_MIN_TOTAL_SITES; 51 cal
N_REPLICATES = 2
POOLED_FIELDS = ["replicate", "arm", "alpha", "certified", "tau", "tau_idx",
                 "coverage", "n_answered", "n_cal_carrying"]


# ----------------------------------------------------------------- helpers --

def build_reference(data_dir, ref_dir, replicates=N_REPLICATES):
    """The released pooled-arm artifacts the sidecar reproduces, built here.

    Independent of the sidecar's own replay: the cohorts come from the test
    suite's _run_eicu driver, and each artifact is assembled with the same
    run_eicu builders run_certification uses (_strip_report, _bbse_block,
    _eval_rung, the composition row, _write_json/_write_table, and
    report.provenance with run_eicu._data_sha). On this mock no rung
    certifies, so composition_three_way is empty, as run_certification
    leaves it.
    """
    os.makedirs(ref_dir, exist_ok=True)
    pooled, comp_rows, bbse_rows, cert, names = [], [], [], None, None
    for r in range(replicates):
        rep, ctx = _run_eicu(data_dir, replicate=r)
        names = ctx["names"]
        head = fit_head(ctx["train"])
        target, cal = ctx["target"], ctx["cal"]
        n_carrying = int((cal.site_sizes > 0).sum())
        for alpha in ALPHA_LADDER:
            ev = re_._eval_rung(head, rep, alpha, target.x, target.y)
            pooled.append(dict(replicate=r, arm="primary", alpha=alpha,
                               certified=ev["certified"], tau=ev["tau"],
                               tau_idx=ev["tau_idx"], coverage=ev["coverage"],
                               n_answered=ev["n_answered"],
                               n_cal_carrying=n_carrying))
        bb = re_._bbse_block(rep)
        bb["replicate"] = r
        bbse_rows.append(bb)
        comp = rep["diagnostic"].get("composition")
        op = rep.get("operative")
        if comp and op is not None:
            comp_rows.append(dict(
                replicate=r, alpha=op["alpha"],
                tau=round(float(op["tau"]), 6),
                predicted_positive_fraction=comp["predicted_class"][
                    "positive_fraction"],
                bbse_implied_positive_fraction=(comp.get("bbse_true_class")
                                                or {}).get(
                                                    "positive_fraction"),
                oracle_positive_fraction=comp["oracle_true_class"][
                    "positive_fraction"]))
        if r == 0:
            cert = re_._strip_report(rep, names)
    re_._write_json(os.path.join(ref_dir, "EICU_certificate.json"), cert,
                    "EICU_certificate.json")
    re_._write_json(os.path.join(ref_dir, "EICU_diagnostics.json"),
                    dict(arm="primary", replicates=replicates,
                         composition_three_way=comp_rows, bbse=bbse_rows),
                    "EICU_diagnostics.json")
    re_._write_table(os.path.join(ref_dir, "EICU_pooled.csv"), pooled,
                     POOLED_FIELDS, "EICU_pooled.csv")
    re_._write_json(os.path.join(ref_dir, "EICU_provenance.json"),
                    provenance(mode="FULL", arm="primary",
                               replicates=replicates,
                               data_sha=re_._data_sha(data_dir)),
                    "EICU_provenance.json")
    return ref_dir


def direct_atom_margin(score, err, site_id, n_sites, alpha, M=M_INFLUENCE):
    """max_tau mean_c (g_c/M) a_c (alpha - e_c), one site at a time.

    alpha - Z_c = (g_c/M) a_c (alpha - e_c) with g_c = min(n_c, M), a_c the
    site's answered fraction and e_c its answered error; a site that answers
    nothing (or carries no record) contributes 0. The mean runs over all
    n_sites columns, as influence_atoms lays them out.
    """
    best = -np.inf
    for tau in TAU_GRID:
        ans = score >= tau
        tot = 0.0
        for c in range(n_sites):
            in_c = site_id == c
            n_c = int(in_c.sum())
            k = int((in_c & ans).sum())
            if n_c == 0 or k == 0:
                continue
            e_c = float(err[in_c & ans].mean())
            tot += min(n_c, M) / M * (k / n_c) * (alpha - e_c)
        best = max(best, tot / n_sites)
    return best


def _walk(obj, path="$"):
    """Yield (path, key, value) over a JSON tree."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield path, k, v
            yield from _walk(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk(v, f"{path}[{i}]")


def _main(data, ref, out, replicates=N_REPLICATES):
    return sc.main(["--data", data, "--reference", ref, "--out", out,
                    "--replicates", str(replicates), "--quiet"])


# ---------------------------------------------------------------- fixtures --

@pytest.fixture(scope="module")
def corpus(tmp_path_factory):
    base = tmp_path_factory.mktemp("eicu_sidecar")
    data = str(base / "corpus")
    mock.generate(mock.MockConfig(stays=MOCK_STAYS, sites=MOCK_SITES,
                                  out=data))
    ref = build_reference(data, str(base / "reference"))
    out = str(base / "out")
    doc = _main(data, ref, out)
    return dict(base=base, data=data, ref=ref, out=out, doc=doc)


@pytest.fixture(scope="module")
def replay0(corpus):
    x_raw, _, meta = etl.build_raw(corpus["data"], strict_levels=True,
                                   verbose=False)
    site_raw = [str(s) for s in meta["site_raw"]]
    return sc.replay_replicate(0, x_raw, etl.labels(meta), site_raw)


def _tampered(corpus, tmp_path, fname, edit):
    ref = str(tmp_path / "ref")
    shutil.copytree(corpus["ref"], ref)
    path = os.path.join(ref, fname)
    if fname.endswith(".json"):
        with open(path, encoding="utf-8") as fh:
            obj = json.load(fh)
        edit(obj)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(obj, fh)
    else:
        with open(path, encoding="ascii", newline="") as fh:
            text = fh.read()
        with open(path, "w", encoding="ascii", newline="") as fh:
            fh.write(edit(text))
    return ref


# ------------------------------------------------------------------- tests --

def test_end_to_end_writes_aggregate_only_post_hoc_artifacts(corpus):
    out = corpus["out"]
    assert sorted(os.listdir(out)) == sorted(
        [sc.JSON_NAME, sc.COMPOSITION_CSV, sc.MARGIN_CSV, sc.README_NAME])

    with open(os.path.join(out, sc.README_NAME), encoding="utf-8") as fh:
        readme = fh.read()
    assert "Status: POST-HOC (2026-10-29)" in readme.splitlines()[2]
    assert "Nothing in this directory is a certified quantity" in readme
    assert "python -m experiments.eicu_composition_margin --data" in readme

    with open(os.path.join(out, sc.JSON_NAME), encoding="utf-8") as fh:
        doc = json.load(fh)
    run = doc["_run"]
    assert set(run) == {"utc", "git_sha", "inputs"}
    assert len(run["inputs"]) == 4
    assert all(len(h) == 64 for h in run["inputs"].values())
    assert doc["extract"]["data_sha"] == re_._data_sha(corpus["data"])
    assert set(doc["extract"]["tables_sha256"]) == {
        f"{t}.csv.gz" for t in mock.EICU_MOCK_TABLES}
    assert doc["post_hoc"].startswith("[MEASURE] POST-HOC (2026-10-29)")
    assert doc["self_check"]["replicates_vs_diagnostics_and_pooled"] == dict(
        replicates_checked=N_REPLICATES, mismatches=0)
    assert all(v["equal"] for v in
               doc["self_check"]["replicate0_vs_certificate"].values())
    assert len(doc["replicates"]) == N_REPLICATES
    assert set(doc["replicates"][0]["margins"]) == {"0.05", "0.1"}

    # aggregate-only: no forbidden key, no long sequence, anywhere
    for path, key, value in _walk(doc):
        assert key not in re_.EICU_FORBIDDEN_OUT_KEYS, f"{path}.{key}"
        if isinstance(value, list):
            assert len(value) <= re_.EICU_MAX_OUTPUT_LEN, f"{path}.{key}"
    for item in doc["replicates"]:
        re_.assert_aggregate_only(item, "replicate")
    for name in (sc.COMPOSITION_CSV, sc.MARGIN_CSV):
        rows = sc._read_csv(os.path.join(out, name))
        for row in rows:
            re_.assert_aggregate_only(row, name)
            assert set(row) <= set(sc.COMPOSITION_FIELDS) | set(
                sc.MARGIN_FIELDS)
    margin_rows = sc._read_csv(os.path.join(out, sc.MARGIN_CSV))
    assert len(margin_rows) == N_REPLICATES * len(ALPHA_LADDER)


def test_emitted_margin_equals_a_direct_atom_computation(corpus, replay0):
    """The JSON's replicate-0 margin is the per-site atom margin, exactly."""
    head, aux = replay0["head"], replay0["aux"]
    score = head.score(aux.x)
    err = head.predict(aux.x) != aux.y
    rec = corpus["doc"]["replicates"][0]
    for alpha in ALPHA_LADDER:
        m = rec["margins"][str(float(alpha))]
        direct = direct_atom_margin(score, err, aux.site_id, aux.n_sites,
                                    alpha)
        assert m["margin_atom"] == pytest.approx(direct, abs=1e-12)
        # the released proxy and floor beside it are the pipeline's own
        n_carrying = int((replay0["cal"].site_sizes > 0).sum())
        proxy = _feasibility(head, aux, alpha, n_carrying)
        assert m["margin_proxy"] == proxy["margin"]
        assert m["floor"] == proxy["floor"]
        assert m["ratio_atom"] == pytest.approx(direct / proxy["floor"],
                                                abs=1e-12)


def test_atom_margin_separates_from_the_proxy_when_sites_are_capped():
    """With sites above M the record-pooled proxy is not the atom margin.

    On the mock every site is below M = 100, where the two coincide
    algebraically; a 208-site synthetic cohort has capped sites, and there
    the sidecar's atom margin still equals the direct computation while the
    proxy moves away from it (audit CORE-3).
    """
    rng = np.random.default_rng(123)
    coh = draw_cohort(SimConfig(), 208, rng)
    train, aux, _ = split_sites(coh, rng)
    assert int(aux.site_sizes.max()) > M_INFLUENCE
    head = fit_head(train)
    score = head.score(aux.x)
    err = head.predict(aux.x) != aux.y
    for alpha in ALPHA_LADDER:
        got = sc.atom_margin(score, err, aux, alpha)
        direct = direct_atom_margin(score, err, aux.site_id, aux.n_sites,
                                    alpha)
        assert got["margin_atom"] == pytest.approx(direct, abs=1e-12)
        assert got["margin_atom_answered"] == pytest.approx(direct,
                                                            abs=1e-12)
        proxy = _feasibility(head, aux, alpha, 83)["margin"]
        assert abs(proxy - got["margin_atom"]) > 1e-4


def test_composition_formulas_are_the_released_and_the_corrected_ones(
        replay0):
    """Released: odds x rho alone. Corrected: odds x odds(pi_t)/odds(pi_train).

    The mock's BBSE fit declines, so the formulas are pinned on its cohorts
    with a stated (rho, pi_s) and a non-empty answered set.
    """
    head, target, train = (replay0["head"], replay0["target"],
                           replay0["train"])
    mask = head.score(target.x) >= TAU_GRID[0]
    assert mask.any()
    rho, pi_s = 0.6683906350656348, 0.09115001606167684
    pi_train = float(np.mean(train.y))

    rel, rel_n = sc.released_bbse_fraction(head, target.x, mask, rho)
    p = head.predict_proba(target.x)
    o = rho * p / np.clip(1.0 - p, 1e-12, None)
    assert rel == float((o / (1.0 + o))[mask].mean())
    assert rel_n == pytest.approx(rel * int(mask.sum()), rel=1e-12)

    cor = sc.corrected_bbse_block(head, target.x, mask, rho, pi_s, pi_train)
    assert cor == composition(head, target.x, mask, rho, pi_source=pi_s,
                              pi_train=pi_train)["bbse_true_class"]
    odds = lambda q: q / (1.0 - q)                          # noqa: E731
    pi_t = rho * odds(pi_s) / (1.0 + rho * odds(pi_s))
    assert cor["odds_multiplier"] == pytest.approx(
        odds(pi_t) / odds(pi_train), rel=1e-12)
    o_c = cor["odds_multiplier"] * p / np.clip(1.0 - p, 1e-12, None)
    assert cor["positive_fraction"] == pytest.approx(
        float((o_c / (1.0 + o_c))[mask].mean()), rel=1e-12)
    # with the S_train prior equal to the S_aux prior the two coincide
    same = sc.corrected_bbse_block(head, target.x, mask, rho, pi_s,
                                   float(np.clip(pi_s, PI_CLIP,
                                                 1.0 - PI_CLIP)))
    assert same["positive_fraction"] == pytest.approx(rel, rel=1e-12)
    assert pi_train != pi_s and cor["positive_fraction"] != pytest.approx(
        rel, rel=1e-6)


def test_tampered_certificate_refuses_at_replicate_zero(corpus, tmp_path):
    def edit(cert):
        cert["diagnostic"]["n_cal_carrying"] += 1
    ref = _tampered(corpus, tmp_path, "EICU_certificate.json", edit)
    out = str(tmp_path / "out")
    with pytest.raises(SystemExit, match="reason=self-check-failed"):
        _main(corpus["data"], ref, out)
    assert not os.path.exists(out)


def test_tampered_bbse_prior_refuses_at_replicate_zero(corpus, tmp_path):
    def edit(cert):
        cert["diagnostic"]["bbse"]["pi_s"] += 1e-12
    ref = _tampered(corpus, tmp_path, "EICU_certificate.json", edit)
    out = str(tmp_path / "out")
    with pytest.raises(SystemExit, match="bbse.pi_s.*reason=self-check-failed"):
        _main(corpus["data"], ref, out)
    assert not os.path.exists(out)


def test_tampered_pooled_cell_refuses_after_the_replay(corpus, tmp_path):
    def edit(text):
        lines = text.splitlines(keepends=True)
        head = lines[0].rstrip("\r\n").split(",")
        j = head.index("n_cal_carrying")
        for i, line in enumerate(lines[1:], start=1):
            cells = line.rstrip("\r\n").split(",")
            if cells[0] == "1":                    # replicate 1 only
                cells[j] = str(int(cells[j]) + 1)
                lines[i] = ",".join(cells) + "\r\n"
                break
        return "".join(lines)
    ref = _tampered(corpus, tmp_path, "EICU_pooled.csv", edit)
    out = str(tmp_path / "out")
    with pytest.raises(SystemExit, match="reason=replay-mismatch"):
        _main(corpus["data"], ref, out)
    assert not os.path.exists(out)


def test_foreign_extract_refuses_before_any_replay(corpus, tmp_path):
    def edit(prov):
        assert prov["meta"]["data_sha"] == re_._data_sha(corpus["data"])
        prov["meta"]["data_sha"] = "0" * 64
    ref = _tampered(corpus, tmp_path, "EICU_provenance.json", edit)
    out = str(tmp_path / "out")
    with pytest.raises(SystemExit, match="reason=extract-mismatch"):
        _main(corpus["data"], ref, out)
    assert not os.path.exists(out)


def test_replicates_beyond_the_release_refuse(corpus, tmp_path):
    with pytest.raises(SystemExit, match="reason=bad-replicates"):
        _main(corpus["data"], corpus["ref"], str(tmp_path / "out"),
              replicates=N_REPLICATES + 1)


@pytest.mark.parametrize("frozen", ["out", "out-panel", "out-derived",
                                    "out-rev2", "out-settled",
                                    "out-e9a-rescore", "out-bbse-probe"])
def test_frozen_directories_are_refused_before_anything_runs(frozen,
                                                             tmp_path):
    out = os.path.join(sc.EXP_DIR, frozen)
    with pytest.raises(SystemExit, match="reason=frozen-output-dir"):
        sc.main(["--data", str(tmp_path / "no-such-extract"), "--out", out])


def test_record_level_payload_is_refused_and_nothing_is_written(corpus,
                                                                tmp_path):
    def fresh():
        return json.loads(json.dumps(re_._json_ready(corpus["doc"])))
    doc = fresh()
    doc["replicates"][0]["site_id"] = [0, 1]
    out = str(tmp_path / "out")
    with pytest.raises(etl.EicuError, match="reason=record-level-output"):
        sc.write_outputs(out, doc, [], [], [])
    doc = fresh()
    doc["replicates"][1]["margins"]["0.1"]["per_tau"] = list(range(600))
    with pytest.raises(etl.EicuError, match="reason=record-level-output"):
        sc.write_outputs(out, doc, [], [], [])
    assert not os.path.exists(out)


def test_default_output_directory_is_the_named_sidecar():
    assert os.path.basename(sc.OUT_DIR) == "out-eicu-composition"
    assert os.path.normcase(sc.REFERENCE_DIR) == os.path.normcase(
        os.path.join(sc.EXP_DIR, "out"))


@pytest.mark.skipif(os.environ.get("CERTGATE_EICU") != "1",
                    reason="genuine run_eicu reference arm; set CERTGATE_EICU=1")
def test_reproduces_a_genuine_run_eicu_release(corpus, tmp_path):
    """The reference is run_eicu.main's own output on the same mock."""
    ref = str(tmp_path / "run_eicu_out")
    re_.main(["--data", corpus["data"], "--out", ref, "--replicates",
              str(N_REPLICATES), "--quick"])
    out = str(tmp_path / "out")
    doc = _main(corpus["data"], ref, out)
    assert doc["self_check"]["replicates_vs_diagnostics_and_pooled"][
        "mismatches"] == 0
    for a, b in zip(doc["replicates"], corpus["doc"]["replicates"]):
        assert a["margins"] == b["margins"]
        assert a["composition"] == b["composition"]
