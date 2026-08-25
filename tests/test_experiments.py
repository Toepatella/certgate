"""The instruments that produce the paper's numbers.

Three things get pinned here:
  - _rm_on_pool, E1's conformance instrument after the audit-V1 rescoring
  - _rate's None-vs-0.0 distinction, which keeps zero-certificate cells honest
  - the summary writer's preserved blocks, which must survive partial reruns

Refs: verification N2.
"""
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
