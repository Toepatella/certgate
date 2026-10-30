"""The instruments that produce the paper's numbers.

What gets pinned here:
  - _rm_on_pool, E1's conformance instrument after the audit-V1 rescoring,
    and on this generator its M-invariance in population
  - _rate's None-vs-0.0 distinction, which keeps zero-certificate cells honest,
    and the conditional (per-certified-draw) reading of rm_exceed_rate
  - the summary writer's preserved blocks, which must survive partial reruns
  - the documented seed-stream aliasing of E2's sweep and E5's replication
  - the panel readings the paper's tables rest on

Refs: verification N2; audit 2026-10 (ids at each test).
"""
import os

import numpy as np

from certgate.validate import Cohort
from certgate.model import Head
from experiments.run_synthetic import (_rm_on_pool, _per_site_exceed_frac,
                                       _rate, _existing_summary_blocks,
                                       _write_summary)


def _two_site_pool():
    """A two-site toy pool with hand-computable answered errors.

      - site A: 50 records, 10 answered errors, 40 answered correct
      - site B: 400 records (above M=100), all answered, 8 errors

    The head is the identity on d=1, so x engineers the scores.
    """
    # x: sign gives prediction; |logit| gives score; all answered at tau=0.55
    xs, ys = [], []
    xs += [+1.0] * 10 + [-1.0] * 40          # A: 10 predicted-pos on y=False
    ys += [False] * 50                        #    -> 10 errors
    xs += [+1.0] * 8 + [-1.0] * 392           # B: 8 errors
    ys += [False] * 400
    x = np.array(xs, dtype=np.float64).reshape(-1, 1)
    y = np.array(ys, dtype=bool)
    sid = np.array([0] * 50 + [1] * 400, dtype=np.int64)
    return Cohort(x=x, y=y, site_id=sid, site_labels=("A", "B"))


def test_rm_on_pool_matches_closed_form_and_is_not_the_record_mean():
    """R_M against hand arithmetic, and against the record mean it is not.

        R_M = sum_c (g_c/n_c) err_c / sum_c (g_c/n_c) ans_c, g_c = min(n_c, M)

    Site A has g/n = 50/50 = 1, site B has g/n = 100/400 = 0.25. So
    R_M = (1*10 + 0.25*8) / (1*50 + 0.25*400) = 12/150 = 0.08.

    The unweighted record mean is 18/450 = 0.04, half of R_M. Substituting it
    is the aggregate-vs-record confusion audit V1 corrects.
    """
    head = Head(coef=np.array([1.0]), intercept=0.0, mu=np.zeros(1),
                sd=np.ones(1))
    pool = _two_site_pool()
    rm = _rm_on_pool(head, pool, 0.55)
    assert abs(rm - 0.08) < 1e-12
    record_mean = 18 / 450
    assert abs(rm - record_mean) > 0.03            # distinct estimands
    # nothing answered -> NaN, never 0.0
    assert np.isnan(_rm_on_pool(head, pool, 1.01))


def test_per_site_exceed_frac_closed_form():
    """One of the two answering sites exceeds alpha.

    Site A risk is 10/50 = 0.20, above alpha = 0.10. Site B risk is
    8/400 = 0.02.
    """
    head = Head(coef=np.array([1.0]), intercept=0.0, mu=np.zeros(1),
                sd=np.ones(1))
    pool = _two_site_pool()
    assert _per_site_exceed_frac(head, pool, 0.55, 0.10) == 0.5
    assert np.isnan(_per_site_exceed_frac(head, pool, 1.01, 0.10))
    # 10/50 == alpha is not an exceedance (audit GAP-unreviewed-tests-2)
    assert _per_site_exceed_frac(head, pool, 0.55, 0.20) == 0.0
    # a third, fully declined site (x = 0 -> score 0.5 < 0.55) leaves the
    # denominator at the answering sites
    xs = np.vstack([pool.x, np.zeros((50, 1))])
    p3 = Cohort(x=xs, y=np.concatenate([pool.y, np.zeros(50, bool)]),
                site_id=np.concatenate([pool.site_id,
                                        np.full(50, 2, np.int64)]),
                site_labels=("A", "B", "C"))
    assert _per_site_exceed_frac(head, p3, 0.55, 0.10) == 0.5


def test_rate_none_vs_zero():
    """_rate(0, 0) is None, never 0.0.

    None means no certificates were issued; 0.0 would mean zero violations.
    That distinction keeps E2's zero-certificate BBSE cell honest.
    """
    assert _rate(0, 0) is None
    assert _rate(0, 10) == 0.0
    assert _rate(3, 10) == 0.3


def test_summary_preserved_blocks_survive_two_partial_runs(tmp_path):
    """Preserved sections survive a second partial run (audit V26).

    The header regex must tolerate the '(preserved...)' suffix. Fresh blocks
    carry their own run stamps.
    """
    out = str(tmp_path)
    _write_summary(out, {"E2": {"R": 5, "x": 1}}, quick=True)
    blocks1 = _existing_summary_blocks(f"{out}/summary.md")
    assert set(blocks1) == {"E2"}
    # run 2: recompute only E3 -> E2 preserved
    _write_summary(out, {"E3": {"R": 5, "y": 2}}, quick=True)
    blocks2 = _existing_summary_blocks(f"{out}/summary.md")
    assert set(blocks2) == {"E2", "E3"}
    assert blocks2["E2"] == blocks1["E2"]          # byte-identical carry
    # run 3: recompute only E1 -> E2 must still survive, a second generation
    # of preservation through the suffixed header
    _write_summary(out, {"E1": {"R": 5, "z": 3}}, quick=True)
    blocks3 = _existing_summary_blocks(f"{out}/summary.md")
    assert set(blocks3) == {"E1", "E2", "E3"}
    assert blocks3["E2"] == blocks1["E2"]
    with open(f"{out}/summary.md", encoding="utf-8") as fh:
        text = fh.read()
    assert "(preserved from an earlier run)" in text
    assert '"_run"' in text                        # fresh blocks are stamped


def test_e8_bound_walk_mirrors_fixed_sequence_semantics():
    """The comparator walk shares the library walk's contract exactly.

    Test in order, stop at the first failure, deploy the lowest-tau certified
    index. An empty prefix deploys None.

    Refs: SPEC E8 arm A.
    """
    from experiments.run_synthetic import _bound_walk
    atoms = np.array([[0.02], [0.04], [0.5], [0.03]])
    tau_grid = np.array([0.9, 0.8, 0.7, 0.6])
    ucb = lambda z, d: float(z.mean())          # noqa: E731
    certified, dep = _bound_walk(atoms, np.array([0, 1, 2, 3]),
                                 0.05, 0.05, tau_grid, ucb)
    assert certified == [0, 1]                   # stops at atoms[2] = 0.5
    assert dep == 1                              # min tau among certified
    certified, dep = _bound_walk(atoms, np.array([2, 0, 1]),
                                 0.05, 0.05, tau_grid, ucb)
    assert certified == [] and dep is None
    # min tau among the certified, not the last certified
    # (audit GAP-unreviewed-tests-2)
    certified, dep = _bound_walk(atoms, np.array([1, 0, 2]),
                                 0.05, 0.05, tau_grid, ucb)
    assert list(certified) == [1, 0] and dep == 1
    a2 = atoms.copy()
    a2[3] = [0.05]
    certified, dep = _bound_walk(a2, np.array([3, 2]), 0.05, 0.05,
                                 tau_grid, ucb)
    assert list(certified) == [3] and dep == 3      # ucb == alpha certifies


def test_e8_flip_labels_rate_and_determinism():
    from types import SimpleNamespace
    from experiments.run_synthetic import _flip_labels, _rng
    y1 = np.zeros(20000, dtype=bool)
    y2 = np.zeros(20000, dtype=bool)
    _flip_labels((SimpleNamespace(y=y1),), 0.03, _rng(9999, 0))
    _flip_labels((SimpleNamespace(y=y2),), 0.03, _rng(9999, 0))
    assert (y1 == y2).all()                      # deterministic
    assert abs(y1.mean() - 0.03) < 0.005         # rate ~ eta
    y3 = np.zeros(20000, dtype=bool)
    _flip_labels((SimpleNamespace(y=y3),), 0.03, _rng(9999, 1))
    assert (y1 != y3).any()                      # stream-sensitive


def test_e9_fnr_rng_deterministic_and_ladder_indexed():
    """The FNR permutation stream mirrors certification_rng's sha256 build.

    It indexes E9_FNR_LADDER, and the leading-9 discriminator keeps it from
    ever aliasing a certification stream.

    Refs: SPEC "Outcome-weighted atoms".
    """
    from experiments.run_synthetic import _e9_fnr_rng
    a = _e9_fnr_rng(0.5, "e9-fnr").integers(0, 2 ** 31, 4)
    b = _e9_fnr_rng(0.5, "e9-fnr").integers(0, 2 ** 31, 4)
    c = _e9_fnr_rng(0.55, "e9-fnr").integers(0, 2 ** 31, 4)
    d = _e9_fnr_rng(0.5, "other").integers(0, 2 ** 31, 4)
    assert (a == b).all()
    assert not (a == c).all()
    assert not (a == d).all()
    import pytest as _pytest
    with _pytest.raises(ValueError):
        _e9_fnr_rng(0.10)                        # off the FNR ladder, loudly


def test_fnr_on_pool_closed_form():
    """FNR_M on a two-site toy pool, checked against hand arithmetic."""
    from types import SimpleNamespace
    from experiments.run_synthetic import _fnr_on_pool

    class _H:
        def score(self, x):
            return x[:, 0]

        def predict(self, x):
            return x[:, 1] >= 0.5

    # site 0: 3 records (2 answered positives, 1 FN); site 1: 2 records
    # (1 answered positive, 0 FN). Equal g/n weights -> FNR = weighted mean.
    x = np.array([[0.9, 0.0], [0.9, 1.0], [0.1, 1.0],
                  [0.9, 1.0], [0.9, 0.0]])
    y = np.array([True, True, True, True, False])
    pool = SimpleNamespace(x=x, y=y, site_id=np.array([0, 0, 0, 1, 1]),
                           n_sites=2, site_sizes=np.array([3, 2]))
    got = _fnr_on_pool(_H(), pool, 0.5)
    # site 0: fn=1 (rec0: answered, pred neg, y pos), ap=2 -> g/n = min(3,M)/3 = 1
    # site 1: fn=0, ap=1 -> g/n = 1
    # FNR_M = (1*1 + 1*0) / (1*2 + 1*1) = 1/3
    assert np.isclose(got, 1.0 / 3.0)
    # a second pool where site 1 sits above the cap (audit
    # GAP-unreviewed-tests-2): site 1 has 200 records, two answered
    # positives, both false negatives, g/n = 100/200
    x1 = np.vstack([x[:3], np.tile([0.9, 0.0], (200, 1))])
    y1 = np.array([True, True, True] + [True] * 2 + [False] * 198)
    pool1 = SimpleNamespace(x=x1, y=y1,
                            site_id=np.array([0] * 3 + [1] * 200),
                            n_sites=2, site_sizes=np.array([3, 200]))
    # FNR_M = (1 + 0.5*2) / (2 + 0.5*2) = 2/3; record-pooled would be 3/4
    assert np.isclose(_fnr_on_pool(_H(), pool1, 0.5), 2.0 / 3.0)


def test_eicu_subgroup_rows_masks_floor_and_no_certificate():
    """_subgroup_rows on a synthetic stand-in cohort.

    Covers one-hot masks, age__missing exclusion, whole-cell and per-scope
    floor suppression (null never zero), and the no-certificate path.

    Refs: revision-2 item 3b.
    """
    from types import SimpleNamespace
    from experiments.run_eicu import _subgroup_rows

    rng = np.random.default_rng(0)
    n = 700
    feature_names = ["age", "age__missing", "gender=Female", "gender=Male",
                     "ethnicity=Caucasian", "ethnicity=Other/Unknown",
                     "hospitaladmitsource=Emergency Department",
                     "unittype=MICU"]
    x = np.zeros((n, len(feature_names)))
    x[:, 0] = rng.uniform(20, 90, n)
    x[:5, 1] = 1.0                                  # 5 imputed ages
    female = rng.random(n) < 0.55
    x[:, 2] = female
    x[:, 3] = ~female
    x[:, 4] = 1.0                                   # everyone Caucasian
    x[:, 6] = 1.0
    x[:, 7] = 1.0
    y = rng.random(n) < 0.1
    pool = SimpleNamespace(x=x, y=y)

    class _H:
        def score(self, x):
            return np.full(len(x), 0.9)             # everything answered

        def predict(self, x):
            return np.zeros(len(x), dtype=bool)     # always-negative

    rows = _subgroup_rows(_H(), pool, feature_names, 0.8, 3, "primary")
    by = {(r["dim"], r["level"]): r for r in rows}
    # everyone answered -> coverage 1.0 where unsuppressed
    cauc = by[("ethnicity", "Caucasian")]
    assert cauc["status"] == "ok" and cauc["coverage"] == 1.0
    # always-negative head -> answered error == positive rate
    assert cauc["answered_err_rate"] == cauc["answered_pos_rate"]
    # declined scope is empty -> its rates suppressed as None, never 0.0
    assert cauc["declined_err_rate"] is None
    # the empty Other/Unknown level is a whole-cell suppression
    other = by[("ethnicity", "Other/Unknown")]
    assert other["status"] == "suppressed-below-floor"
    assert other["answered_err_rate"] is None
    # age bands exclude the 5 imputed rows
    assert sum(r["n"] for r in rows if r["dim"] == "age_band") == n - 5
    # no-certificate path: everything null, status marked
    rows_nc = _subgroup_rows(_H(), pool, feature_names, None, 0, "primary")
    assert all(r["status"] == "no-certificate" and r["coverage"] is None
               for r in rows_nc)


def test_rm_exceed_rate_is_conditional_on_certified_draws():
    """rm_exceed_rate is k over the certified draws, not over all draws.

    The betting test bounds the joint certify-and-exceed probability, which
    is rm_exceed_rate x certify_rate; the conditional rate is never below it.

    Refs: audit synthetic-2.
    """
    from experiments.run_synthetic import _rollup
    out = _rollup([{"rm_exceed": True}, {"rm_exceed": False}], 50,
                  ("certify_rate", "rm_exceed_rate"))
    assert out == {"certify_rate": 0.04, "rm_exceed_rate": 0.5}
    assert out["rm_exceed_rate"] * out["certify_rate"] == 1 / 50


def test_rm_population_value_is_m_invariant_on_generator():
    """The generator draws site size independently of the site random effect,
    so R_M takes one population value at every M: on a large pool the seven
    Table S4 weightings agree up to sampling noise. A negative control that
    couples size and prevalence moves R_M with M.

    Refs: audit synthetic-6.
    """
    from certgate.constants import SEED
    from certgate.data import SimConfig, draw_cohort, subset_sites
    from experiments.panel_s2_tables import M_SWEEP
    from experiments.run_synthetic import _draw_split, _rng
    cfg = SimConfig()
    _, _, _, head = _draw_split(cfg, 208, _rng(9, 1, 0, 0))
    pool = draw_cohort(cfg, 1500, np.random.default_rng([SEED, 3]),
                       site_label_prefix="inv")
    for tau in (0.55, 0.75):
        base = _rm_on_pool(head, pool, tau, 100)
        for M in M_SWEEP:
            assert abs(_rm_on_pool(head, pool, tau, M) - base) < 0.003
    sizes = pool.site_sizes
    prev = (np.bincount(pool.site_id, weights=pool.y.astype(float))
            / sizes)
    keep = np.where((sizes > np.median(sizes))
                    == (prev > np.median(prev)))[0]
    coupled = subset_sites(pool, keep)
    for tau in (0.55, 0.75):
        assert abs(_rm_on_pool(head, coupled, tau, 25)
                   - _rm_on_pool(head, coupled, tau, 5000)) > 0.006


def test_cap_share_closed_form():
    """89.6% of sites exceed M = 100 under the generator's size law:
    n_c = floor(clip(exp(N(6, 1.1^2)), 20, 5000)) > 100 iff the normal draw
    is at least log(101). cap_facts emits the closed form beside its
    simulated share.

    Refs: audit synthetic-10.
    """
    from scipy.stats import norm
    from certgate.constants import M_INFLUENCE
    from certgate.data import SimConfig
    from experiments.panel_s2_tables import cap_facts
    cfg = SimConfig()
    exact = float(norm.sf((np.log(M_INFLUENCE + 1) - cfg.size_mu)
                          / cfg.size_sigma))
    assert round(exact, 3) == 0.896
    facts = cap_facts(n_reps=10)
    assert facts["share_sites_above_M_exact"] == round(exact, 4)
    se = np.sqrt(exact * (1.0 - exact) / facts["sites"])
    assert abs(facts["share_sites_above_M"] - exact) < 4 * se


def test_table_s4_rows_count_bbse_deploying_draws(monkeypatch):
    """Table S4 replays every validity-grid draw; deploy_mode gates only the
    tau self-check (paper Table S4 caption, SI A.3).

    Refs: audits synthetic-5, PAPER1-4, PAPER2-1.
    """
    from experiments import panel_s2_tables as P
    rec = {r: dict(v) for r, v in P._recorded_e1().items() if r < 2}
    rec[1]["deploy_mode"] = "bbse"      # as if draw 1 had deployed a BBSE tau
    monkeypatch.setattr(P, "_recorded_e1", lambda: rec)
    out = P.e1_arm(2)
    assert out["self_check"] == dict(compared=1, tau_mismatches=0)
    assert out["table6"]["M=100"]["alpha=0.1"]["n_certified"] == 2


def test_seed_streams_alias_at_trailing_zero():
    """numpy's SeedSequence zero-pads entropy shorter than four words, so a
    trailing zero index aliases the shorter stream: E5's replication draw 0
    is the case-study stream _rng(5), and draw 0 of each E2 sweep arm m is
    the anchor's _rng(2, 100 + m). The comments in run_synthetic document
    this; the released numbers are unchanged by it.

    Refs: audits GAP-seed-stream-aliasing-1, GAP-seed-stream-aliasing-2.
    """
    from certgate.constants import SEED

    def pool(*parts):
        return np.random.SeedSequence([SEED, *parts]).pool

    assert np.array_equal(pool(5, 0), pool(5))
    assert not np.array_equal(pool(5, 1), pool(5))
    for m in range(4):
        assert np.array_equal(pool(2, 100 + m, 0), pool(2, 100 + m))
        assert not np.array_equal(pool(2, 100 + m, 1), pool(2, 100 + m))
