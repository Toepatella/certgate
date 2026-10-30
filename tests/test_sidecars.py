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

The 2026-10 mathematical audit adds regressions beside them: the derivation
reads the comparator columns from the file that carries them and rounds only
its outputs; Table S7's medians are of exact count ratios; the settlement's
P2, P3, P4 and P6 read what the protocol registered; and the numbers the
corrected manuscript text quotes from the BBSE probe, E5 and E9a are read
back from the released files. Every runner refuses its own released
directory on a bare re-run, and every sidecar's write guard refuses every
experiments/out*/ directory but its own.

Refs: fix-pass plan WP2; audit 2026-10.
"""
import copy
import csv
import json
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
                os.path.join(dfn.EXP_DIR, "out-derived", "fixpass_numbers.json"),
                str(tmp_path / "EICU-SUMMARY.md")):
        with pytest.raises(SystemExit):
            dfn.assert_not_frozen(bad)
    # the re-emitted run and the released post-hoc sidecars, each runner's
    # own default directory among them
    for name in ("out-rev2", "out-timing", "out-settled", "out-e9a-rescore",
                 "out-e9b-positives", "out-bbse-probe"):
        with pytest.raises(SystemExit, match="frozen-output-dir"):
            dfn.assert_not_frozen(os.path.join(dfn.EXP_DIR, name, "x.json"))
    dfn.assert_not_frozen(str(tmp_path / "fine.json"))     # no raise
    dfn.assert_not_frozen(os.path.join(dfn.EXP_DIR, "out-derived-r2", "x.json"))
    assert dfn.OUT_PATH == os.path.join(dfn.EXP_DIR, "out-derived-r2",
                                        "fixpass_numbers.json")


def _released(*parts):
    """A released artifact under experiments/, read only."""
    path = os.path.join(dfn.EXP_DIR, *parts)
    return dfn._read_json(path) if path.endswith(".json") else dfn._read_csv(path)


def test_derive_reads_rev2_comparator_columns():
    """The seven columns appended on 2026-09-04 live in EICU_comparator.csv,
    and their alpha = 0.10 means are Supplementary Table S11's (audit 2026-10
    EICU-2: the first emission read EICU_pooled.csv and found none)."""
    doc = dfn.derive()
    cols = doc["rev2"]["comparator_new_columns"]
    assert set(cols) == set(dfn.REV2_COMPARATOR_COLUMNS) == {
        "head_auc_pool", "head_brier_pool", "head_auc_answered",
        "head_brier_answered", "apache_iva_auc_pool", "apache_iva_brier_pool",
        "n_apache_available_pool"}
    assert "pooled_new_columns" not in doc["rev2"]
    assert all(v["n"] == 20 for v in cols.values())
    means = {k: v["mean"] for k, v in cols.items()}
    assert means["head_auc_pool"] == 0.8593
    assert means["head_brier_pool"] == 0.0616
    assert means["apache_iva_auc_pool"] == 0.8601
    assert means["apache_iva_brier_pool"] == 0.063
    assert means["head_auc_answered"] == 0.8098
    assert means["head_brier_answered"] == 0.0428
    assert round(means["n_apache_available_pool"]) == 15839
    assert "experiments/out-rev2/EICU_comparator.csv" in doc["_run"]["inputs"]


def test_rev2_sections_refuses_comparator_without_appended_columns(tmp_path):
    """A comparator file without the appended columns is an error, never
    a silent 'no new columns found'."""
    p = tmp_path / "EICU_comparator.csv"
    with open(p, "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows([["replicate", "alpha", "n_answered"],
                                  ["0", "0.1", "10"]])
    with pytest.raises(SystemExit, match="rev2-columns-missing"):
        dfn._rev2_sections({"rev2_comparator": str(p),
                            "rev2_faithfulness": str(tmp_path / "absent.csv")})


def test_derive_rounds_only_outputs():
    """No ratio is taken on an intermediate already rounded for display.

    odds(1362/15169) / odds(pi_s) at the certificate's full-precision pi_s
    is 0.98359; from pi_s first rounded to 0.0912 it was 0.983. The age
    gradient is 3.876 on unrounded means (3.89 from the 4-dp ones), and the
    rev2 Spearman mean is 16/33 = 0.48485 (0.4849 from 4-dp correlations).
    """
    doc = dfn.derive()
    bt = doc["three_way_composition"]["bbse_transfer"]
    assert bt["true_odds_ratio_vs_pi_s"] == 0.984
    assert bt["pool_prevalence_observed"] == 0.0898
    assert bt["expected_q_at_observed_prevalence"] == 0.0365
    assert doc["fairness"]["age_gradients"]["answered_err_ratio"] == 3.88
    assert doc["rev2"]["faithfulness_spearman"]["mean"] == 0.4848


def test_derive_sens_decline_reasons_are_counts():
    """decline_reasons counts each reason; it used to set every count to 1."""
    sens = _released("out-sens", "EICU_pooled.csv")
    att = _released("out-sens", "EICU_attrition.csv")
    assert dfn.sens_section(sens, att)["decline_reasons"] == {
        "baseline:failsafe|bbse:failsafe": 1}
    sens = copy.deepcopy(sens)
    row = next(r for r in sens if r["alpha"] == "0.1" and r["certified"] == "True")
    row.update(certified="False", decline_reason="baseline:failsafe|bbse:failsafe")
    assert dfn.sens_section(sens, att)["decline_reasons"] == {
        "baseline:failsafe|bbse:failsafe": 2}


def test_e1_note_says_table_s4_replays_every_draw():
    """Table S4 replays all 200 draws; only its self-check is restricted to
    the 194 baseline-deploying ones (audit 2026-10 synthetic-5)."""
    note = dfn.derive()["e1"]["note"]
    assert "replays all of these draws" in note
    assert "excluded from Table S4" not in note


def test_confusion_table_summary_rounds_exact_ratios_once():
    """Table S7: min/median/max are the exact count ratios' statistics,
    rounded once. Medians of the rows' 4-dp rates flipped two declined-set
    cells (specificity 0.842, PPV 0.5882); audit 2026-10 reliability-1."""
    from decimal import Decimal, ROUND_HALF_EVEN
    from fractions import Fraction
    from experiments import panel_confusion_tables as pct

    ratios = dict(
        sensitivity=lambda r: (r["tp"], r["tp"] + r["fn"]),
        specificity=lambda r: (r["tn"], r["tn"] + r["fp"]),
        ppv=lambda r: (r["tp"], r["tp"] + r["fp"]),
        npv=lambda r: (r["tn"], r["tn"] + r["fn"]),
        fnr=lambda r: (r["fn"], r["tp"] + r["fn"]),
        error=lambda r: (r["fp"] + r["fn"], r["records"]),
        fn_share_of_errors=lambda r: (r["fn"], r["fp"] + r["fn"]))

    def q4(v):
        return float((Decimal(v.numerator) / Decimal(v.denominator))
                     .quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN))

    with open(pct.PANEL_PATH, encoding="utf-8") as fh:
        doc = pct.derive(json.load(fh))
    for scope, rows in doc["per_replicate"].items():
        for metric, ratio in ratios.items():
            exact = sorted(Fraction(*ratio(r)) for r in rows if ratio(r)[1])
            k = len(exact)
            med = (exact[k // 2] if k % 2
                   else (exact[k // 2 - 1] + exact[k // 2]) / 2)
            assert doc["summary"][scope][metric] == dict(
                min=q4(exact[0]), median=q4(med), max=q4(exact[-1])), (
                scope, metric)
    assert doc["summary"]["declined"]["specificity"]["median"] == 0.8421
    assert doc["summary"]["declined"]["ppv"]["median"] == 0.5883


def test_table_s8_means_round_once_from_released_counts():
    """Three Table S8 cells, recomputed from the released subgroup counts and
    rounded once: the released 4-dp rates' means put each 0.0001 lower
    (audit 2026-10, Table S8 double rounding)."""
    rows = _released("out-subgroups", "EICU_subgroups.csv")

    def cells(dim, level):
        return [r for r in rows if r["dim"] == dim and r["level"] == level]

    def coverage_mean(dim, level):
        return round(float(np.mean([
            int(float(r["n_answered"])) / int(float(r["n"]))
            for r in cells(dim, level) if r["coverage"] not in ("", None)])), 4)

    assert coverage_mean("hospitaladmitsource", "Acute Care/Floor") == 0.8582
    assert coverage_mean("hospitaladmitsource", "Other Hospital") == 0.8054
    errs = []
    for r in cells("age_band", "18-44"):
        if r["status"] != "ok" or r["answered_err_rate"] in ("", None):
            continue
        na, rate = int(float(r["n_answered"])), float(r["answered_err_rate"])
        k = [j for j in range(na + 1) if round(j / na, 4) == rate]
        assert len(k) == 1                  # the integer error count is unique
        errs.append(k[0] / na)
    assert round(float(np.mean(errs)), 4) == 0.0194


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
    with pytest.raises(SystemExit):
        sp.main(["--out", os.path.join(dfn.EXP_DIR, "out-derived")])


def _no_compute(name):
    """Stand-in for a runner's compute step: reaching it means the runner's
    write guard let a frozen target through, so fail before anything is
    computed or written."""
    def boom(*_a, **_k):
        raise AssertionError(f"{name} reached its compute step: the released "
                             f"default output directory was not refused")
    return boom


@pytest.mark.parametrize("name, compute, released", [
    ("settle_predictions", "settle", "out-settled"),
    ("rescore_e9a", "rescore", "out-e9a-rescore"),
    ("probe_bbse_coverage", "run", "out-bbse-probe"),
    ("run_e9b_positives", "run", "out-e9b-positives"),
])
def test_runner_refuses_its_released_directory(monkeypatch, name, compute,
                                               released):
    """A bare re-run never overwrites the runner's own released sidecar.

    Each runner's default --out is the directory its release went to; the
    write guard refuses it, so a re-run needs --out <new dir>, and so does an
    explicit --out naming it. The compute step is stubbed to fail, so a
    regression fails here without touching the released files."""
    import importlib
    module = importlib.import_module(f"experiments.{name}")
    monkeypatch.setattr(module, compute, _no_compute(name))
    with pytest.raises(SystemExit):
        module.main([])
    with pytest.raises(SystemExit):
        module.main(["--out", os.path.join(dfn.EXP_DIR, released)])


def test_every_sidecar_guard_refuses_every_other_output_dir():
    """Every experiments/out*/ directory is released and frozen to every
    sidecar but its own.

    Each guard is checked against the directories on disk, not against the
    module's own list, so a directory left off a list fails here."""
    import glob
    from experiments import rescore_e6_composition as e6c
    from experiments import rescore_e8a as e8a
    from experiments import rescore_e9_exact as ex
    from experiments import eicu_composition_margin as sc
    dirs = sorted(d for d in glob.glob(os.path.join(dfn.EXP_DIR, "out*"))
                  if os.path.isdir(d))
    assert len(dirs) >= 17
    norm = lambda p: os.path.normcase(os.path.abspath(p))   # noqa: E731
    for guard, own in ((dfn.assert_not_frozen, dfn.OUT_DIR),
                       (e6c.assert_writable, e6c.OUT_DIR),
                       (e8a.assert_writable, e8a.OUT_DIR),
                       (ex._assert_writable, ex.OUT_DIR),
                       (sc.assert_writable, sc.OUT_DIR)):
        guard(os.path.join(own, "x.json"))                  # its own: no raise
        for d in dirs:
            if norm(d) == norm(own):
                continue
            with pytest.raises(SystemExit, match="frozen"):
                guard(os.path.join(d, "x.json"))


def test_settle_p3_rule_reads_per_site_pools_and_both_rungs():
    """P3's falsification rule sees all 25 pools at either rung (audit
    2026-10 EICU-12). EICU_per_site.csv has no modes column: on a certified
    row the reason cell names the modes that did not back the deployed tau,
    and BBSE certified-not-covering also fires the rule."""
    pooled = _released("out", "EICU_pooled.csv")
    per_site = _released("out", "EICU_per_site.csv")
    clauses, verdict, extra = sp.settle_p3(pooled, per_site)
    assert verdict == "confirmed" and clauses[2]["met"]
    share3 = extra["per_replicate"][3]["bbse_declined_share"]
    for alpha, reason, fires in (("0.1", "baseline:failsafe", True),
                                 ("0.05", "baseline:failsafe", True),
                                 ("0.1", "", False)):
        ps = copy.deepcopy(per_site)
        row = next(r for r in ps if r["replicate"] == "3"
                   and r["alpha"] == alpha and r["reason"] != "pool-too-small")
        row.update(certified="True", reason=reason)
        clauses, verdict, extra = sp.settle_p3(pooled, ps)
        assert clauses[2]["met"] is (not fires)
        assert verdict == ("falsified" if fires else "confirmed")
        if fires:
            assert clauses[2]["observed"] == "1 pools over 20 re-splits"
        elif alpha == "0.1":
            # a certified row with both modes covering is not a BBSE decline
            new = extra["per_replicate"][3]["bbse_declined_share"]
            assert round(share3 - new, 4) == round(1 / 25, 4)
    pl = copy.deepcopy(pooled)
    row = next(r for r in pl if r["replicate"] == "4" and r["alpha"] == "0.05")
    row.update(certified="True", modes="bbse", deploy_mode="bbse",
               decline_reason="baseline:failsafe")
    assert sp.settle_p3(pl, per_site)[1] == "falsified"
    pl = copy.deepcopy(pooled)
    row = next(r for r in pl if r["replicate"] == "5" and r["alpha"] == "0.1")
    assert row["certified"] == "True" and row["modes"] == "baseline"
    row.update(decline_reason="bbse:certified-not-covering")
    clauses, verdict, extra = sp.settle_p3(pl, per_site)
    assert verdict == "falsified" and not clauses[2]["met"]
    assert "certified-not-covering" not in extra["per_replicate"][5]["reasons"]


def test_p4_matcher_is_the_registered_set():
    """aps_present, apv_present and the 43 aps_/apv_ __missing siblings; not
    the four patient-table missingness flags (audit 2026-10 EICU-12)."""
    from experiments import eicu_etl
    hit = [f for f in eicu_etl.FEATURE_NAMES if dfn.is_apache_absence(f)]
    assert len(hit) == 45
    assert {"aps_present", "apv_present"} <= set(hit)
    assert all(f in ("aps_present", "apv_present") or (
        f.startswith(("aps_", "apv_")) and f.endswith("__missing")) for f in hit)
    for f in ("age__missing", "admissionheight__missing",
              "admissionweight__missing", "pre_icu_hours__missing"):
        assert f in eicu_etl.FEATURE_NAMES and not dfn.is_apache_absence(f)
    for f in ("aps_heartrate__missing", "apv_electivesurgery__missing"):
        assert dfn.is_apache_absence(f)
    diag = copy.deepcopy(_released("out", "EICU_diagnostics.json"))
    blk = diag["abstention_gap_ranking"]["replicate0_alpha0.1"]
    blk["ranking"][2] = dict(blk["ranking"][2],
                             feature="admissionweight__missing", gap=-0.5)
    per = sp.settle_p4(diag)[2]["per_replicate"]
    assert per[0]["hits"] == [] or all(
        h["feature"] != "admissionweight__missing" for h in per[0]["hits"])
    p4 = dfn.p4_signed_section(diag)
    assert all(h["feature"] != "admissionweight__missing"
               for e in p4["exceptions"] for h in e["hits"])


def test_p4_counts_one_ranking_per_replicate():
    """run_eicu writes one ranking per certified rung; P4 reads the operative
    rung's, one per re-split, and its majority is of the twenty."""
    diag = copy.deepcopy(_released("out", "EICU_diagnostics.json"))
    block = diag["abstention_gap_ranking"]
    for key in list(block):
        block[key.replace("alpha0.1", "alpha0.05")] = copy.deepcopy(block[key])
    assert len(block) == 40
    per = sp.settle_p4(diag)[2]["per_replicate"]
    assert [d["replicate"] for d in per] == list(range(20))
    assert dfn.p4_signed_section(diag)["n_replicates"] == 20
    base = sp.settle_p4(_released("out", "EICU_diagnostics.json"))
    hits_before = {d["replicate"] for d in base[2]["per_replicate"]
                   if d["unsigned_hit"]}
    for rep in range(6):
        for alpha in ("0.1", "0.05"):
            rk = block[f"replicate{rep}_alpha{alpha}"]["ranking"]
            rk[0] = dict(rk[0], feature="aps_present")
    clauses, verdict, _ = sp.settle_p4(diag)
    k = len(hits_before | set(range(6)))
    assert clauses[0]["observed"] == f"{k} of 20 re-splits"
    assert verdict == "falsified"
    # a ranking planted only at the strictest rung is the one read
    diag = copy.deepcopy(_released("out", "EICU_diagnostics.json"))
    blk = copy.deepcopy(diag["abstention_gap_ranking"]["replicate3_alpha0.1"])
    blk["ranking"][0] = dict(blk["ranking"][0], feature="aps_present", gap=-0.5)
    diag["abstention_gap_ranking"]["replicate3_alpha0.05"] = blk
    per = sp.settle_p4(diag)[2]["per_replicate"]
    assert [d["replicate"] for d in per] == list(range(20))
    assert per[3]["top3"][0]["feature"] == "aps_present"
    assert dfn.p4_signed_section(diag)["n_replicates"] == 20


def test_settle_p6_scores_the_registered_mean():
    """P6 registers the mean coverage at the operative rung, not a majority
    of re-splits inside the interval (audit 2026-10 EICU-12)."""
    pooled = _released("out", "EICU_pooled.csv")

    def with_cov(values):
        rows = copy.deepcopy(pooled)
        op = sorted((r for r in rows if r["alpha"] == "0.1"),
                    key=lambda r: int(r["replicate"]))
        for r, v in zip(op, values):
            r["coverage"] = v
        return rows

    # majority outside, mean inside
    assert sp.settle_p6(with_cov(["0.97"] * 10 + ["0.90"] * 10))[1] == "confirmed"
    # majority inside, mean outside
    assert sp.settle_p6(with_cov(["0.61"] * 11 + ["0.20"] * 9))[1] == "falsified"
    assert sp.settle_p6(with_cov(["0.94"] * 11 + ["0.99"] * 9))[1] == "falsified"
    # a re-split certified at alpha = 0.05 enters at that, its operative, rung
    rows = copy.deepcopy(pooled)
    for r in rows:
        if r["alpha"] == "0.05" and int(r["replicate"]) < 12:
            r.update(certified="True", coverage="0.30")
    clauses, verdict, extra = sp.settle_p6(rows)
    assert verdict == "falsified"
    assert extra["per_replicate"][:12] == [0.3] * 12


def test_settle_p2_tolerates_an_uncertified_resplit():
    """An uncertified re-split has no deployed tau and a blank cell; it meets
    neither clause and the majority stays of the twenty (audit 2026-10
    EICU-12: out-sens replicate 7 used to crash the settlement)."""
    sens = _released("out-sens", "EICU_pooled.csv")
    assert any(r["alpha"] == "0.1" and r["certified"] != "True" for r in sens)
    clauses, _, extra = sp.settle_p2(sens)
    assert all("of 20 re-splits" in c["observed"] for c in clauses)
    assert len(extra["per_replicate"]) == 20
    pooled = copy.deepcopy(_released("out", "EICU_pooled.csv"))
    before = sp.settle_p2(pooled)
    row = next(r for r in pooled if r["replicate"] == "7" and r["alpha"] == "0.1")
    was_dir = float(row["per_site_exceed_frac"]) > 0.02
    row.update(certified="False", per_site_exceed_frac="")
    clauses, verdict, extra = sp.settle_p2(pooled)
    k_before = int(before[0][0]["observed"].split()[0])
    assert clauses[0]["observed"].startswith(
        f"{k_before - was_dir} of 20 re-splits")
    assert extra["per_replicate"][7] is None
    row = next(r for r in pooled if r["replicate"] == "0" and r["alpha"] == "0.1")
    row.update(certified="False", per_site_exceed_frac="")
    assert sp.settle_p2(pooled)[0][0]["observed"].endswith(
        "published split none")


def test_p2_registered_basis_vs_settling_statistic():
    """P2's registered 0.02 / 0.10 are E1's single-fresh-site hard-violation
    rates, not per_site_exceed_frac, the field P2 is settled on (audit
    2026-10 EICU-3). Every number the erratum quotes is read back here."""
    from experiments.run_synthetic import _existing_summary_blocks
    block = _existing_summary_blocks(
        os.path.join(dfn.EXP_DIR, "out", "summary.md"))["E1"]
    e1 = json.loads(block.split("\n", 1)[1].rsplit("\n", 1)[0])
    su = {s["s_u"]: s for s in e1["su_sensitivity"]}
    assert [su[k]["hard_violation_rate_diag"] for k in (0.5, 1.0, 2.0)] == [
        0.02, 0.1, 0.095]
    assert [su[k]["mean_per_site_exceed_frac"] for k in (0.5, 1.0, 2.0)] == [
        0.055, 0.1285, 0.1634]
    rows = _released("out", "E1_validity.csv")

    def arm(s_u):
        c = [r for r in rows if r["s_u"] == s_u and r["alpha"] == "0.1"
             and r["certified"] == "True"]
        hard = sum(r["hard"] == "True" for r in c) / len(c)
        frac = float(np.mean([float(r["per_site_exceed_frac"]) for r in c]))
        return round(hard, 4), round(frac, 4)

    assert arm("0.5") == (0.02, 0.055)
    assert arm("2.0") == (0.095, 0.1634)
    p2 = {p["id"]: p for p in sp.settle()["predictions"]}["P2"]
    vals = p2["per_replicate"]
    assert p2["verdict"] == "falsified"
    assert [c["met"] for c in p2["clauses"]] == [True, False]
    assert (sum(v > 0.02 for v in vals), sum(0.05 <= v <= 0.30 for v in vals),
            sum(v < 0.055 for v in vals)) == (11, 2, 18)
    mean = float(np.mean(vals))
    assert round(mean, 4) == 0.0271 and 0.02 < mean < 0.055
    dep = [r for r in _released("out", "EICU_per_site.csv")
           if r["alpha"] == "0.1" and r["certified"] == "True"]
    assert (len(dep), sum(r["hard"] == "True" for r in dep)) == (477, 7)


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


def _closed_form_answered_risk(head, cfg, tau, pi):
    """The head's population answered error on one site at prevalence pi.

    x | y ~ N(mu_y, I), so the decision logit is Gaussian within each class
    with mean intercept + a . (mu_y - mu_head) and sd ||a||, a = coef / sd.
    A record is answered when |logit| >= logit(tau) and wrong when y = 0 with
    logit >= 0 or y = 1 with logit < 0. One site carries no influence cap.
    """
    from scipy.stats import norm
    a = head.coef / head.sd
    s = float(np.linalg.norm(a))
    lt = float(np.log(tau / (1.0 - tau)))
    m0, m1 = (float(head.intercept + a @ (cfg.mu(y) - head.mu)) for y in (0, 1))
    a0 = norm.sf((lt - m0) / s) + norm.cdf((-lt - m0) / s)
    a1 = norm.sf((lt - m1) / s) + norm.cdf((-lt - m1) / s)
    e0, e1 = norm.sf((lt - m0) / s), norm.cdf((-lt - m1) / s)
    return (pi * e1 + (1 - pi) * e0) / (pi * a1 + (1 - pi) * a0)


def test_e9a_rescore_is_a_proxy_for_the_latent_prevalence_estimand():
    """The three frozen-exceeding single-site rows (1,200 sites, draws 29 and
    48), replayed to the declared site's latent prevalence.

    rescore_e9a reweights to the declared pool's REALISED prevalence, a
    proxy; the estimand a single-site certificate names sits at the site's
    latent prevalence sigmoid(logit 0.22 + u). In closed form there the
    three rows score 0.0163, 0.0398 and 0.0792, each within its alpha, and
    draw 48's proxy (0.0586) understates its own (audit 2026-10 FNR-6).
    """
    from certgate.data import SimConfig, draw_cohort, split_sites
    from certgate.model import fit_head, _sigmoid
    from experiments.run_synthetic import SHIFT_BASE, _rng

    frozen = {(int(r["draw"]), r["alpha"]): r for r in dfn._read_csv(
        os.path.join(dfn.EXP_DIR, "out-e9a-rescore", "E9a_rescore.csv"))
        if r["n_source_sites"] == "1200" and r["target_mode"] == "single-site-cp"
        and r["rm_exceed_frozen"] == "True"}
    assert sorted(frozen) == [(29, "0.05"), (29, "0.1"), (48, "0.1")]
    cfg = SimConfig()
    pi_bar = probe.population_prevalence(cfg.base_rate, cfg.s_u)
    expect = {(29, "0.05"): 0.0163, (29, "0.1"): 0.0398, (48, "0.1"): 0.0792}
    for draw in (29, 48):
        rng = _rng(9, 0, 3, 0, draw)          # e9a.replay_draw(3, 0, draw)
        coh = draw_cohort(cfg, 1200, rng)
        train, _, _ = split_sites(coh, rng)
        head = fit_head(train)
        peek = copy.deepcopy(rng)             # the declared site's own draws
        size = int(np.clip(np.exp(peek.normal(cfg.size_mu, cfg.size_sigma, 1)),
                           cfg.size_lo, cfg.size_hi)[0])
        u = float(peek.normal(0.0, cfg.s_u, 1)[0])
        tgt = draw_cohort(cfg, 1, rng, label_base_rate=SHIFT_BASE,
                          site_label_prefix=f"e9t3_{draw}",
                          require_both_classes=False)
        assert tgt.n == size
        latent = float(_sigmoid(np.log(SHIFT_BASE / (1 - SHIFT_BASE)) + u))
        for (d, alpha), row in frozen.items():
            if d != draw:
                continue
            assert round(float(tgt.y.mean()), 6) == float(row["pi_target"])
            r_lat = _closed_form_answered_risk(head, cfg, float(row["tau"]),
                                               latent)
            assert abs(r_lat - expect[(d, alpha)]) < 1e-3
            assert r_lat <= float(alpha)
        if draw == 48:
            assert tgt.n == 712
            assert abs(latent - 0.1564) < 5e-4
            rho_star = probe._odds(latent) / probe._odds(pi_bar)
            assert abs(rho_star - 1.6027) < 5e-4
            row = frozen[(48, "0.1")]
            assert float(row["rho_lo"]) <= rho_star <= float(row["rho_hi"])
            r_lat = _closed_form_answered_risk(head, cfg, 0.55, latent)
            r_real = _closed_form_answered_risk(head, cfg, 0.55,
                                                float(tgt.y.mean()))
            r_pop = _closed_form_answered_risk(
                head, cfg, 0.55, probe.population_prevalence(SHIFT_BASE, cfg.s_u))
            assert abs(r_real - 0.0622) < 5e-4
            assert abs(r_pop - 0.1104) < 5e-4 and r_pop > 0.10
            assert float(row["rm_rescored"]) == 0.058612
            assert r_lat - float(row["rm_rescored"]) > 0.015


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
    # the population prevalences the corrected text quotes for the base-rate
    # shift and the s_u sweep (audit 2026-10 synthetic-11, PAPER1-19)
    assert round(probe.population_prevalence(0.095, 0.5), 4) == 0.1037
    assert round(probe.population_prevalence(0.22, 0.5), 4) == 0.2313
    assert round(probe.population_prevalence(0.095, 1.0), 4) == 0.1281
    assert round(probe.population_prevalence(0.095, 2.0), 4) == 0.1973


def _probe_release():
    with open(os.path.join(dfn.EXP_DIR, "out-bbse-probe", "BBSE_probe.json"),
              encoding="utf-8") as fh:
        doc = json.load(fh)
    rows = dfn._read_csv(os.path.join(dfn.EXP_DIR, "out-bbse-probe",
                                      "BBSE_probe.csv"))
    return doc, rows


def test_probe_release_level_reads_from_rho_coverage():
    """The union bound consumes only rho* in [rho_lo, rho_hi]; box coverage is
    sufficient, not necessary. The released probe covered the declared
    site's odds ratio in every certifiable fit, so in its regime the level is
    at least 0.97, against the 0.93 box-route plug-in (audit 2026-10
    PROBE-1, BBSE-5). Never round the rho route up: 1 - (0.0032 + 0.025)."""
    doc, rows = _probe_release()
    pooled = doc["pooled_over_n_aux"]
    rho = pooled["coverage_among_certifiable_fits"]["rho_declared_site"]
    assert rho["k"] == rho["n"] == 1163
    assert rho["miss_ci95"] == [0.0, 0.0032]
    rho_route = 1 - (rho["miss_ci95"][1] + probe.BBSE_DELTA_BET)
    assert round(rho_route, 3) == 0.972
    implied = pooled["implied_certificate_level"]
    assert implied["measured_four_parameter"] == 0.9277
    assert implied["conservative_ci_upper"] == 0.9139
    assert rho_route >= 0.97 > 0.95 > implied["measured_four_parameter"]
    for n_aux, cell in doc["cells"].items():
        c = cell["coverage_among_certifiable_fits"]["rho_declared_site"]
        assert c["k"] == c["n"], n_aux
        assert 1 - (c["miss_ci95"][1] + probe.BBSE_DELTA_BET) >= 0.965, n_aux
    certifiable = [r for r in rows if r["declined"] == "False"]
    box_missed = [r for r in certifiable if r["covers_joint4"] == "False"]
    assert len(box_missed) == 55
    assert all(r["covers_rho_site"] == "True" for r in box_missed)


def test_probe_joint_miss_is_sum_of_parameter_misses():
    """Only the Clopper-Pearson q covers at its nominal 0.99375; the three
    bootstrap intervals miss above their 0.00625 pooled over the 1,200 boxed
    fits, and among certifiable fits no fit missed two parameters, so the
    four-parameter miss is exactly the sum 13 + 20 + 18 + 4 = 55 (audit
    2026-10 PROBE-2)."""
    from scipy.stats import binomtest
    _, rows = _probe_release()
    cols = [f"covers_{p}" for p in probe.PARAMS]
    certifiable = [r for r in rows if r["declined"] == "False"]
    for r in certifiable:
        n_miss = sum(r[c] == "False" for c in cols)
        assert n_miss <= 1
        assert (r["covers_joint4"] == "False") is (n_miss == 1)
    per_param = [sum(r[c] == "False" for r in certifiable) for c in cols]
    assert per_param == [13, 20, 18, 4]
    assert sum(r["covers_joint4"] == "False" for r in certifiable) == 55
    boxed = [r for r in rows if r["box_exists"] == "True"]
    assert len(boxed) == 1200
    misses = [sum(r[c] == "False" for r in boxed) for c in cols]
    assert misses == [15, 21, 21, 5]
    for k in misses[:3]:                    # c0, c1, pi_s
        assert binomtest(k, len(boxed)).proportion_ci().low > 0.00625


def test_probe_clip_bound_reads_the_box_not_a_rho_hi_threshold():
    """The pi_t clip sets rho_hi only when a box corner passes 1 - PI_CLIP.

    A largest corner pi_t of 0.895 gives rho_hi near 105 with the clip idle;
    q_hi past c1_lo gives rho_hi = (1 - PI_CLIP)/PI_CLIP / odds(pi_s_lo).
    Read against the flag, the released CSV holds the 2, 2 and 2 clip-bound
    fits and the mean widths the module docstring quotes for the released
    run (audit 2026-10 PROBE-3).
    """
    from certgate.constants import PI_CLIP
    from certgate.shift import rho_box_interval

    lo = np.array([0.015, 0.4852, 0.075])
    hi = np.array([0.019, 0.55, 0.13])
    point = (0.017, 0.52, 0.10)
    box = dict(c0_ci=(lo[0], hi[0]), c1_ci=(lo[1], hi[1]))
    _, rho_hi, _ = rho_box_interval(0.40, 0.4357, 0.42, lo, hi, point)
    assert rho_hi > 100
    assert not probe._rho_hi_clip_bound(dict(box, q_ci=(0.40, 0.4357)))
    _, rho_hi, _ = rho_box_interval(0.45, 0.49, 0.47, lo, hi, point)
    assert probe._rho_hi_clip_bound(dict(box, q_ci=(0.45, 0.49)))
    assert np.isclose(rho_hi, (1 - PI_CLIP) / PI_CLIP / (0.075 / 0.925))

    _, rows = _probe_release()
    fitted = [r for r in rows if r["declined"] == "False"]
    flag = [probe._rho_hi_clip_bound(
        {f"{p}_ci": (float(r[f"{p}_lo"]), float(r[f"{p}_hi"]))
         for p in ("q", "c0", "c1")}) for r in fitted]
    expect = {"36": (2, 8.2248), "42": (2, 7.538), "74": (2, 8.5153),
              None: (6, 8.0908)}
    for n_aux, (k, mean) in expect.items():
        sel = [(r, f) for r, f in zip(fitted, flag)
               if n_aux is None or r["n_aux"] == n_aux]
        assert sum(f for _, f in sel) == k
        assert round(float(np.mean([float(r["box_width"])
                                    for r, f in sel if not f])), 4) == mean


# ------------------------------------------------------------- E5 chance

def _expected_max_share(n, k=4):
    """E[max cell count] / n for Multinomial(n; 1/k each), exactly.

    f_j(s) counts the sequences of length s over j cells with every cell at
    most m: f_j(s) = sum_i C(s, i) f_{j-1}(s - i), i <= m. Then
    E[max] = sum_m P(max > m) = sum_m (1 - f_k(n) / k^n)."""
    from fractions import Fraction
    from math import comb
    total = 0
    for m in range(n):
        if m * k < n:                       # some cell must exceed m
            total += 1
            continue
        f = [1 if s <= m else 0 for s in range(n + 1)]
        for _ in range(k - 1):
            f = [sum(comb(s, i) * f[s - i] for i in range(min(s, m) + 1))
                 for s in range(n + 1)]
        tail = 1 - Fraction(f[n], k ** n)
        if tail == 0:
            break
        total += tail
    return float(total / n)


def test_e5_modal_share_chance_reference():
    """The modal top-gap share 0.274 sits below 0.288, the expected share of
    the most frequent of four equally likely features over 186 draws; 0.25
    is the per-feature share, not the modal one (audit 2026-10 synthetic-9).
    """
    rep = _released("out", "E5_explain.json")["replication"]
    n = rep["draws_with_declines"]
    assert n == 186 == sum(rep["top_gap_feature_counts"].values())
    e_max = _expected_max_share(n)
    assert round(e_max, 3) == 0.288
    assert rep["top_gap_stability"] == 0.2742 <= e_max


def test_e5_chance_reference_in_paper_text():
    """The manuscript quotes the modal-share reference, not 0.25."""
    with open(os.path.join(dfn.REPO_DIR, "paper", "draft.md"),
              encoding="utf-8") as fh:
        text = fh.read()
    phrase = "0.288 expected for the most frequent of four equally likely features"
    assert text.count(phrase) == 2
    assert "0.25 chance level" not in text and "vs 0.25 chance" not in text


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
