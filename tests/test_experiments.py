"""verification N2: the instruments that produce the paper's numbers.

``_rm_on_pool`` is E1's conformance instrument after the audit-V1 rescoring;
``_rate``'s None-vs-0.0 distinction keeps zero-certificate cells honest; the
summary writer's preserved blocks must survive partial reruns.
"""
import numpy as np

from certgate.validate import Cohort
from certgate.model import Head
from experiments.run_synthetic import (_rm_on_pool, _per_site_exceed_frac,
                                       _rate, _existing_summary_blocks,
                                       _write_summary)


def _two_site_pool():
    """Site A: 50 records, 10 answered errors, 40 answered correct.
    Site B: 400 records (> M=100), all answered, 8 errors.
    Head = identity on d=1; scores engineered via x."""
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
    """R_M = sum_c (g_c/n_c) err_c / sum_c (g_c/n_c) ans_c with g_c=min(n_c,M).
    Site A: g/n = 50/50 = 1 -> weight 1 per record share; site B: g/n =
    100/400 = 0.25. R_M = (1*10 + 0.25*8) / (1*50 + 0.25*400) = 12/150 = 0.08.
    The unweighted record mean is 18/450 = 0.04 -- HALF of R_M; a mutation
    substituting it (the exact aggregate-vs-record confusion V1 corrects)
    fails here."""
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
    """Site A risk 10/50 = 0.20 > alpha=0.10; site B risk 8/400 = 0.02 -> 1/2
    answering sites exceed."""
    head = Head(coef=np.array([1.0]), intercept=0.0, mu=np.zeros(1),
                sd=np.ones(1))
    pool = _two_site_pool()
    assert _per_site_exceed_frac(head, pool, 0.55, 0.10) == 0.5
    assert np.isnan(_per_site_exceed_frac(head, pool, 1.01, 0.10))


def test_rate_none_vs_zero():
    """_rate(0, 0) is None (no certificates issued), never 0.0 (zero
    violations) -- the distinction that keeps E2's zero-certificate BBSE cell
    honest."""
    assert _rate(0, 0) is None
    assert _rate(0, 10) == 0.0
    assert _rate(3, 10) == 0.3


def test_summary_preserved_blocks_survive_two_partial_runs(tmp_path):
    """audit V26: preserved sections must survive a SECOND partial run (the
    header regex must tolerate the '(preserved...)' suffix), and fresh blocks
    carry their own run stamps."""
    out = str(tmp_path)
    _write_summary(out, {"E2": {"R": 5, "x": 1}}, quick=True)
    blocks1 = _existing_summary_blocks(f"{out}/summary.md")
    assert set(blocks1) == {"E2"}
    # run 2: recompute only E3 -> E2 preserved
    _write_summary(out, {"E3": {"R": 5, "y": 2}}, quick=True)
    blocks2 = _existing_summary_blocks(f"{out}/summary.md")
    assert set(blocks2) == {"E2", "E3"}
    assert blocks2["E2"] == blocks1["E2"]          # byte-identical carry
    # run 3: recompute only E1 -> E2 must STILL survive (second-generation
    # preservation through the suffixed header)
    _write_summary(out, {"E1": {"R": 5, "z": 3}}, quick=True)
    blocks3 = _existing_summary_blocks(f"{out}/summary.md")
    assert set(blocks3) == {"E1", "E2", "E3"}
    assert blocks3["E2"] == blocks1["E2"]
    with open(f"{out}/summary.md", encoding="utf-8") as fh:
        text = fh.read()
    assert "(preserved from an earlier run)" in text
    assert '"_run"' in text                        # fresh blocks are stamped
