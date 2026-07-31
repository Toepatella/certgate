"""SPEC "Tests" for the end-to-end pipeline.

In-distribution certification and coverage; the exact decline partition; the
site-disjointness gate; run-to-run determinism of the certified tiers; the
record-carrying cluster gate (empty sites do not count); the target-pool floor;
and a complete provenance block.
"""
import json

import numpy as np
import pytest

from certgate.data import SimConfig, draw_cohort, split_sites
from certgate.validate import Cohort, CohortError
from certgate.pipeline import run_certgate
from certgate.constants import (ALPHA_LADDER, DELTA, BBSE_DELTA_BET,
                                M_INFLUENCE, TAU_GRID)


@pytest.fixture(scope="module")
def in_dist():
    cfg = SimConfig()
    rng = np.random.default_rng(20260721)
    coh = draw_cohort(cfg, 208, rng)
    train, aux, cal = split_sites(coh, rng)
    tgt = draw_cohort(cfg, 1, rng, site_label_prefix="tgt")
    return dict(train=train, aux=aux, cal=cal, tgt=tgt)


def _row(report, alpha):
    return next(r for r in report["certified"] if r["alpha"] == alpha)


def test_end_to_end_certifies_with_coverage(in_dist):
    tr, ax, ca, tg = (in_dist[k] for k in ("train", "aux", "cal", "tgt"))
    rep = run_certgate(tr, ax, ca, tg.x, target_label="t0",
                       oracle_target_y=tg.y)
    row = _row(rep, 0.10)
    assert row["status"] == "certified"
    assert row["coverage"] > 0.5
    # decline partition sums to the target pool size exactly.
    assert sum(rep["decline_partition"].values()) == tg.n
    # guarantee text carries the load-bearing clauses (audit V1: the estimand
    # is the site-population average, with the mandatory dispersion clause;
    # the exact string is frozen in test_report.py).
    stmt = row["statement"]
    assert "averaged over the population of sites" in stmt
    assert "NOT any individual site's answered error rate" in stmt
    assert "does not measure or bound" in stmt
    assert "NOT a bound" in stmt
    assert "OUT OF SCOPE" in stmt
    assert "at this target site" not in stmt          # the V1 defect, retired


def test_overlapping_cal_train_raises(in_dist):
    tr, ax, tg = in_dist["train"], in_dist["aux"], in_dist["tgt"]
    with pytest.raises(CohortError):
        run_certgate(tr, ax, tr, tg.x)          # cal == train -> label overlap


def test_two_runs_byte_identical_certified_tiers(in_dist):
    tr, ax, ca, tg = (in_dist[k] for k in ("train", "aux", "cal", "tgt"))
    r1 = run_certgate(tr, ax, ca, tg.x, target_label="det")
    r2 = run_certgate(tr, ax, ca, tg.x, target_label="det")
    dump = lambda r: json.dumps(r["certified"], sort_keys=True, default=str)
    assert dump(r1) == dump(r2)


def test_insufficient_clusters_counts_carrying_only(in_dist):
    """45 record-carrying sites + 20 empty sites: the gate counts carrying
    only, so 45 < MIN_CAL_CLUSTERS declines even though n_sites == 65."""
    cfg = SimConfig()
    rng = np.random.default_rng(4)
    sub = draw_cohort(cfg, 45, rng, site_label_prefix="carry")
    labels = sub.site_labels + tuple(f"empty-{i}" for i in range(20))
    cal_gappy = Cohort(x=sub.x, y=sub.y, site_id=sub.site_id,
                       site_labels=labels)
    assert cal_gappy.n_sites == 65
    assert int((cal_gappy.site_sizes > 0).sum()) == 45
    tr = draw_cohort(cfg, 12, rng, site_label_prefix="TR")
    ax = draw_cohort(cfg, 12, rng, site_label_prefix="AX")
    tg = in_dist["tgt"]
    rep = run_certgate(tr, ax, cal_gappy, tg.x, target_label="clust")
    assert rep["reason"] == "insufficient-clusters"
    assert rep["diagnostic"]["n_cal_carrying"] == 45
    assert sum(rep["decline_partition"].values()) == tg.n


def test_pool_too_small(in_dist):
    tr, ax, ca, tg = (in_dist[k] for k in ("train", "aux", "cal", "tgt"))
    rep = run_certgate(tr, ax, ca, tg.x[:5], target_label="small")
    assert rep["reason"] == "pool-too-small"
    assert sum(rep["decline_partition"].values()) == 5
    assert rep["decline_partition"]["pool-too-small"] == 5


def test_provenance_block_present_with_all_keys(in_dist):
    tr, ax, ca, tg = (in_dist[k] for k in ("train", "aux", "cal", "tgt"))
    rep = run_certgate(tr, ax, ca, tg.x, target_label="prov")
    prov = rep["provenance"]
    assert set(prov) >= {"python", "packages", "seed", "input_hashes",
                         "meta", "timestamp_utc"}
    assert set(prov["packages"]) == {"numpy", "scipy", "scikit-learn"}
    # audit V11: every array the certificate depends on is hashed -- x, y AND
    # the site partition of all three cohorts, plus the target.
    assert set(prov["input_hashes"]) == {
        "train_x", "train_y", "train_site_id",
        "aux_x", "aux_y", "aux_site_id",
        "cal_x", "cal_y", "cal_site_id", "target_x"}
    assert prov["seed"] == 20260721


def test_provenance_binds_label_content_and_shape(in_dist):
    """audit V11 / V6 #9: flipping one calibration label must change the
    recorded hashes -- two runs that certify differently must never share a
    provenance block. The digest also binds shape, so a reshaped matrix is
    not provenance-identical."""
    tr, ax, ca, tg = (in_dist[k] for k in ("train", "aux", "cal", "tgt"))
    rep1 = run_certgate(tr, ax, ca, tg.x, target_label="bind",
                        modes=("baseline",))
    y_flip = ca.y.copy()
    y_flip[:int(0.35 * len(y_flip))] = ~y_flip[:int(0.35 * len(y_flip))]
    ca_flip = Cohort(x=ca.x, y=y_flip, site_id=ca.site_id,
                     site_labels=ca.site_labels)
    rep2 = run_certgate(tr, ax, ca_flip, tg.x, target_label="bind",
                        modes=("baseline",))
    h1, h2 = rep1["provenance"]["input_hashes"], rep2["provenance"]["input_hashes"]
    assert h1["cal_y"] != h2["cal_y"]              # content is bound
    assert h1["cal_x"] == h2["cal_x"]              # untouched arrays agree
    # shape binding: a transposed matrix hashes differently even though its
    # raw bytes are identical
    from certgate.report import provenance
    a = np.arange(6, dtype=np.float64).reshape(2, 3)
    pa = provenance(m=a)["input_hashes"]["m"]
    pb = provenance(m=np.ascontiguousarray(a.reshape(3, 2)))["input_hashes"]["m"]
    assert pa != pb


def test_baseline_reports_are_target_label_invariant(in_dist):
    """audit V3 / V6 #12-adjacent: baseline atoms are target-independent, so
    the certified tier, operative rung and answered mask must be byte-identical
    across spellings of the target label. Fails on the old label-seeded
    permutation, under which the deployed threshold moved with a respelling."""
    tr, ax, ca, tg = (in_dist[k] for k in ("train", "aux", "cal", "tgt"))
    reps = [run_certgate(tr, ax, ca, tg.x, target_label=lbl,
                         modes=("baseline",))
            for lbl in ("tgt-0042", "TGT-0042", "st marys")]
    dump = lambda r: json.dumps(r["certified"], sort_keys=True, default=str)
    assert dump(reps[0]) == dump(reps[1]) == dump(reps[2])
    assert reps[0]["operative"] == reps[1]["operative"] == reps[2]["operative"]
    for r in reps[1:]:
        assert np.array_equal(reps[0]["answered_mask"], r["answered_mask"])


def test_delta_accounting_spy(in_dist, monkeypatch):
    """audit V6 #2/#3: record every delta actually handed to wsr_reject.
    The baseline path must spend exactly {DELTA}; the BBSE walk exactly
    {BBSE_DELTA_BET}. A mutation spending delta=0.5, or the full DELTA on the
    BBSE bet, fails here."""
    import certgate.certify as certify_mod
    import certgate.shift as shift_mod
    from certgate.model import Head
    from certgate.shift import certify_bbse, BBSEFit

    seen = {"certify": set(), "shift": set()}
    real = certify_mod.wsr_reject

    def spy_certify(z, alpha, delta, rng=None):
        seen["certify"].add(delta)
        return real(z, alpha, delta, rng=rng)

    def spy_shift(z, alpha, delta, rng=None):
        seen["shift"].add(delta)
        return real(z, alpha, delta, rng=rng)

    monkeypatch.setattr(certify_mod, "wsr_reject", spy_certify)
    monkeypatch.setattr(shift_mod, "wsr_reject", spy_shift)

    tr, ax, ca, tg = (in_dist[k] for k in ("train", "aux", "cal", "tgt"))
    run_certgate(tr, ax, ca, tg.x, target_label="spy", modes=("baseline",))
    assert seen["certify"] == {DELTA}

    # drive the BBSE walk deterministically (a fit decline must not let the
    # call-site check silently pass)
    head = Head(coef=np.array([1.0]), intercept=0.0, mu=np.zeros(1),
                sd=np.ones(1))
    n_sites = 60
    x = np.tile(np.array([-0.5] * 95 + [0.5] * 5, dtype=np.float64),
                n_sites).reshape(-1, 1)
    y = np.zeros(60 * 100, dtype=bool)
    sid = np.repeat(np.arange(n_sites, dtype=np.int64), 100)
    cal_flat = Cohort(x=x, y=y, site_id=sid,
                      site_labels=tuple(f"f{s}" for s in range(n_sites)))
    fit = BBSEFit(declined=False, reason="", rho_lo=1.0, rho_hi=1.0,
                  rho_point=1.0, diagnostics={},
                  walk_orders={a: np.array([0]) for a in ALPHA_LADDER})
    certify_bbse(head, fit, cal_flat, 0.10)
    assert seen["shift"] == {BBSE_DELTA_BET}


def test_walk_order_is_aux_derived(in_dist, monkeypatch):
    """audit V6 #5: the order handed to fixed_sequence_walk must equal the
    S_aux-derived walk_order recomputed independently. A mutation deriving the
    order from S_cal -- selection on the testing data, the reason S_aux
    exists -- fails here."""
    import certgate.pipeline as pl
    from certgate.model import fit_head
    from certgate.certify import influence_atoms, walk_order

    recorded = {}
    real = pl.fixed_sequence_walk

    def spy(atoms, order, alpha, delta, tau_grid, rng=None):
        recorded[alpha] = np.array(order, copy=True)
        return real(atoms, order, alpha, delta, tau_grid, rng=rng)

    monkeypatch.setattr(pl, "fixed_sequence_walk", spy)
    tr, ax, ca, tg = (in_dist[k] for k in ("train", "aux", "cal", "tgt"))
    run_certgate(tr, ax, ca, tg.x, target_label="order", modes=("baseline",))
    head = fit_head(tr)                       # deterministic: same head
    score_aux = head.score(ax.x)
    err_aux = head.predict(ax.x) != ax.y
    for alpha in ALPHA_LADDER:
        expected = walk_order(influence_atoms(score_aux, err_aux, ax.site_id,
                                              ax.n_sites, TAU_GRID, alpha,
                                              M_INFLUENCE))
        assert np.array_equal(recorded[alpha], expected)


def test_unknown_or_empty_modes_raise(in_dist):
    """audit V23: a misspelled mode must never yield an all-declined report
    indistinguishable from a statistical decline."""
    tr, ax, ca, tg = (in_dist[k] for k in ("train", "aux", "cal", "tgt"))
    with pytest.raises(ValueError, match="unknown-mode"):
        run_certgate(tr, ax, ca, tg.x, modes=("bsse",))
    with pytest.raises(ValueError, match="unknown-mode"):
        run_certgate(tr, ax, ca, tg.x, modes=())


def test_single_class_fitting_cohort_raises(in_dist):
    """audit V18: the require_both_classes=False relaxation is sanctioned for
    TARGET pools only; an all-negative calibration cohort must be refused at
    the boundary where roles are known."""
    tr, ax, ca, tg = (in_dist[k] for k in ("train", "aux", "cal", "tgt"))
    ca_neg = Cohort(x=ca.x, y=np.zeros(ca.n, dtype=bool), site_id=ca.site_id,
                    site_labels=ca.site_labels)
    with pytest.raises(CohortError, match="single-class"):
        run_certgate(tr, ax, ca_neg, tg.x)


def test_malformed_oracle_labels_raise(in_dist):
    """audit V19: oracle_target_y was the one input with no validation --
    a length-1 array broadcast to a fabricated composition and a float
    probability array coerced to all-True."""
    tr, ax, ca, tg = (in_dist[k] for k in ("train", "aux", "cal", "tgt"))
    with pytest.raises(ValueError, match="bad-oracle-labels"):
        run_certgate(tr, ax, ca, tg.x, oracle_target_y=np.array([True]))
    with pytest.raises(ValueError, match="bad-oracle-labels"):
        run_certgate(tr, ax, ca, tg.x,
                     oracle_target_y=np.full(tg.n, 0.3))


def test_target_overlapping_calibration_raises(in_dist):
    """audit V9: a target named as (or containing) a calibration site gets a
    threshold selected partly on itself -- must be refused."""
    tr, ax, ca, tg = (in_dist[k] for k in ("train", "aux", "cal", "tgt"))
    with pytest.raises(CohortError, match="site-disjoint"):
        run_certgate(tr, ax, ca, tg.x, target_label=ca.site_labels[0])
    sid = np.array([ca.site_labels[0]] * tg.n, dtype=object)
    with pytest.raises(CohortError, match="site-disjoint"):
        run_certgate(tr, ax, ca, tg.x, target_label="fresh",
                     target_site_id=sid)


def test_gated_report_has_stable_diagnostic_keys(in_dist):
    """audit V25: gated exits must emit the same diagnostic key set as full
    reports (None where uncomputable), so consumers never KeyError."""
    tr, ax, ca, tg = (in_dist[k] for k in ("train", "aux", "cal", "tgt"))
    rep = run_certgate(tr, ax, ca, tg.x[:5], target_label="gate-keys")
    d = rep["diagnostic"]
    for key in ("composition", "abstention_profile", "rm_vs_unweighted",
                "bbse", "capped_influence_share"):
        assert key in d
    assert d["composition"] is None
    assert isinstance(d["capped_influence_share"], float)  # computable: computed


def test_nonfinite_target_raises(in_dist):
    tr, ax, ca, tg = (in_dist[k] for k in ("train", "aux", "cal", "tgt"))
    bad = tg.x.copy()
    bad[0, 0] = np.nan
    with pytest.raises(ValueError, match="nonfinite-features"):
        run_certgate(tr, ax, ca, bad)


def test_target_gates_use_canonical_normal_form(in_dist):
    """verification F2: the V9 gates must compare identity under the same
    normal form densify_sites uses -- 's-0000 ' (trailing space) and 'S-0000'
    (case variant) name calibration sites and must be refused."""
    tr, ax, ca, tg = (in_dist[k] for k in ("train", "aux", "cal", "tgt"))
    a_cal_site = ca.site_labels[0]
    for spelling in (a_cal_site + " ", a_cal_site.upper()):
        with pytest.raises(CohortError, match="site-disjoint"):
            run_certgate(tr, ax, ca, tg.x, target_label=spelling)


def test_misaligned_target_site_id_raises_on_every_path(in_dist):
    """verification N3/F4: a target_site_id shorter than the pool must be a
    typed boundary error under BOTH mode sets -- previously silent on the
    baseline path, where a partial column could satisfy the V9 gate."""
    tr, ax, ca, tg = (in_dist[k] for k in ("train", "aux", "cal", "tgt"))
    short = np.array(["z0", "z1"], dtype=object)
    for modes in (("baseline",), ("bbse",), ("baseline", "bbse")):
        with pytest.raises(CohortError, match="bad-target-site-id"):
            run_certgate(tr, ax, ca, tg.x, target_label="mis",
                         target_site_id=short, modes=modes)


def test_bbse_fit_is_target_label_free_and_data_seeded():
    """verification G-2: the BBSE bootstrap seed derives from the target DATA,
    never the label -- byte-identical pools must get byte-identical fits under
    any respelling, and a changed pool must change the stream."""
    from certgate.pipeline import _bbse_seed_rng
    x1 = np.arange(24, dtype=np.float64).reshape(6, 4)
    s1 = np.arange(6, dtype=np.int64) % 2
    a = _bbse_seed_rng(x1, s1).standard_normal(8)
    b = _bbse_seed_rng(x1.copy(), s1.copy()).standard_normal(8)
    assert np.allclose(a, b)                       # data-identical -> identical
    x2 = x1.copy(); x2[0, 0] += 1e-9
    assert not np.allclose(a, _bbse_seed_rng(x2, s1).standard_normal(8))
    s2 = s1.copy(); s2[0] = 1 - s2[0]
    assert not np.allclose(a, _bbse_seed_rng(x1, s2).standard_normal(8))
    assert np.allclose(_bbse_seed_rng(x1).standard_normal(8),
                       _bbse_seed_rng(x1, None).standard_normal(8))


def test_provenance_binds_run_configuration(in_dist):
    """verification N8: two runs whose certified tiers can differ (different
    modes / alphas) must not share a byte-identical provenance record."""
    tr, ax, ca, tg = (in_dist[k] for k in ("train", "aux", "cal", "tgt"))
    r1 = run_certgate(tr, ax, ca, tg.x, target_label="cfg",
                      modes=("baseline",))
    r2 = run_certgate(tr, ax, ca, tg.x, target_label="cfg",
                      modes=("baseline",), alphas=(0.10,))
    m1, m2 = r1["provenance"]["meta"], r2["provenance"]["meta"]
    assert m1["modes"] == ["baseline"] and m1["alphas"] == [0.05, 0.1]
    assert m2["alphas"] == [0.1]
    assert m1 != m2


def test_composition_three_way_whenever_bbse_fit_holds(in_dist):
    """verification N5: the BBSE-implied composition view is an estimated
    quantity, not part of the certificate -- it must appear whenever the fit
    did not decline, even when baseline wins deployment."""
    tr, ax, ca, tg = (in_dist[k] for k in ("train", "aux", "cal", "tgt"))
    rep = run_certgate(tr, ax, ca, tg.x, target_label="3way",
                       oracle_target_y=tg.y)
    comp = rep["diagnostic"]["composition"]
    bbse_diag = rep["diagnostic"]["bbse"]
    # stable-key diagnostics: rho_point is ALWAYS present now, None until the
    # fit reaches the rho stage (fixture audit 2026-07-25)
    if bbse_diag.get("rho_point") is not None:     # fit reached the rho stage
        assert "bbse_true_class" in comp
    assert rep["diagnostic"]["target_site_id_supplied"] is False


def test_target_x_cohort_rejected(in_dist):
    """fixture audit 2026-07-25: passing the target Cohort itself -- the
    natural mistake, since the other three positional arguments ARE Cohorts --
    must be a typed boundary error telling the caller to pass target.x, never
    a raw numpy float()-conversion TypeError from deep inside asarray."""
    tr, ax, ca, tg = (in_dist[k] for k in ("train", "aux", "cal", "tgt"))
    with pytest.raises(ValueError, match="target-is-cohort"):
        run_certgate(tr, ax, ca, tg)
    # and any other non-numeric target_x is the typed not-numeric reason
    with pytest.raises(ValueError, match="target-not-numeric"):
        run_certgate(tr, ax, ca, [["a", "b"], ["c", "d"]])


def test_feasibility_keys_are_strings_and_json_stable(in_dist):
    """fixture audit 2026-07-25: feasibility is keyed by str(alpha), so a
    saved report JSON-round-trips without json.dump silently stringifying
    float keys out from under a consumer."""
    tr, ax, ca, tg = (in_dist[k] for k in ("train", "aux", "cal", "tgt"))
    rep = run_certgate(tr, ax, ca, tg.x, target_label="feas")
    feas = rep["diagnostic"]["feasibility"]
    assert set(feas) == {"0.05", "0.1"}
    assert json.loads(json.dumps(feas)) == feas    # keys survive round-trip


def test_bbse_diagnostics_stable_keys_across_mode_sets(in_dist):
    """fixture audit 2026-07-25: diagnostic['bbse'] carries the same stable
    key set whether BBSE ran (full fit) or not (the not-run placeholder) --
    a consumer indexing any key gets None, never KeyError."""
    from certgate.shift import bbse_diagnostics
    keys = set(bbse_diagnostics())
    tr, ax, ca, tg = (in_dist[k] for k in ("train", "aux", "cal", "tgt"))
    rep_full = run_certgate(tr, ax, ca, tg.x, target_label="dk-full")
    rep_base = run_certgate(tr, ax, ca, tg.x, target_label="dk-base",
                            modes=("baseline",))
    assert set(rep_full["diagnostic"]["bbse"]) == keys
    assert set(rep_base["diagnostic"]["bbse"]) == keys
    # not-run placeholder: every value is None
    assert all(v is None for v in rep_base["diagnostic"]["bbse"].values())
