"""SPEC "Tests": the hostile-extract fixture, end to end (fixture audit 2026-07-25).

`experiments/synth_fixture.py --signal` emits a 10-table gzip-CSV corpus with
every documented structural wart AND a latent-severity outcome;
`experiments/fixture_etl.py` turns it into finite features + raw site labels;
`from_raw` -> `run_certgate` must reach an HONEST outcome on it: either a
certificate whose oracle-checked answered error respects alpha, or a decline.
The smoke test keeps the default suite fast; the full-scale arm (20800
sessions / 208 heavy-tailed sites — the pilot-trial configuration) runs only
when CERTGATE_FIXTURE=1.
"""
import json
import os

import numpy as np
import pytest

from certgate.constants import ALPHA_LADDER
from certgate.harness import hard_violation
from certgate.model import fit_head
from certgate.pipeline import run_certgate
from certgate.report import render_text
from certgate.validate import from_raw
from experiments.synth_fixture import Config, generate
from experiments import fixture_etl as etl

FIXTURE_TABLES = ["site", "entity_session", "measurement"]


def _run_fixture(tmp_path, sessions, sites, rate, site_sigma):
    """Generate -> ETL -> cohorts -> run_certgate. Returns (report, ctx)."""
    out = str(tmp_path / "fixture")
    generate(Config(sessions=sessions, sites=sites, rate_scale=rate,
                    tables=FIXTURE_TABLES, out=out, signal=True,
                    site_sigma=site_sigma, seed=20260725))
    x, names, meta = etl.build_matrix(out, verbose=False)
    states = set(meta["close_state"])
    assert states <= {"state_a", "state_b"}      # signal mode: outcome complete
    y_raw = ["case" if s == "state_a" else "control"
             for s in meta["close_state"]]
    idx, _ = etl.site_split(meta["site_raw"])

    def cohort(key, strict=True):
        sel = idx[key]
        return from_raw(x[sel], [y_raw[i] for i in sel], "case",
                        [meta["site_raw"][i] for i in sel],
                        require_both_classes=strict)

    train, aux, cal = cohort("train"), cohort("aux"), cohort("cal")
    target = cohort("target", strict=False)
    tgt_sites = [meta["site_raw"][i] for i in idx["target"]]
    rep = run_certgate(train, aux, cal, target.x, target_label="fixture-pool",
                       target_site_id=tgt_sites, oracle_target_y=target.y)
    return rep, dict(train=train, target=target, tgt_sites=tgt_sites)


def _assert_honest(rep, ctx):
    """The only acceptable outcomes: a valid certificate, or a decline."""
    parts = rep["decline_partition"]
    assert sum(parts.values()) == ctx["target"].n
    assert "[partition]" in render_text(rep)     # renders without KeyError
    op = rep["operative"]
    if op is None:
        assert not rep["answered_mask"].any()
        return "declined"
    head = fit_head(ctx["train"])                # deterministic: same head
    err = head.predict(ctx["target"].x) != ctx["target"].y
    ans = rep["answered_mask"]
    # the certificate's own alpha must not be hard-violated by the oracle
    assert not hard_violation(err[ans], op["alpha"])
    return "certified"


def test_fixture_smoke_end_to_end(tmp_path):
    """Small-scale (~seconds): the hostile corpus travels the whole real-data
    path and lands on an honest outcome. Uniform site sizes keep the
    50-carrying-cluster gate deterministically satisfied at this scale."""
    rep, ctx = _run_fixture(tmp_path, sessions=5000, sites=150, rate=0.05,
                            site_sigma=0.0)
    outcome = _assert_honest(rep, ctx)
    assert outcome in ("certified", "declined")
    # every rung reported, every row a certified/declined dict
    assert [r["alpha"] for r in rep["certified"]] == [a for a in ALPHA_LADDER]
    # provenance binds the target site identity (fixture passes target_site_id)
    assert "target_site_id" in rep["provenance"]["input_hashes"]
    assert rep["diagnostic"]["target_site_id_supplied"] is True
    # the ETL's documented int() trap fired and was handled, not crashed on
    assert ctx["target"].x.dtype == np.float64


@pytest.mark.skipif(os.environ.get("CERTGATE_FIXTURE") != "1",
                    reason="full-scale fixture arm; set CERTGATE_FIXTURE=1")
def test_fixture_full_scale_certifies_honestly(tmp_path):
    """Pilot-trial configuration (20800 sessions / 208 heavy-tailed sites,
    ~20 s): certification is plausible here, and if issued must survive the
    oracle; a decline is equally acceptable — the assertion is honesty."""
    rep, ctx = _run_fixture(tmp_path, sessions=20800, sites=208, rate=0.1,
                            site_sigma=1.1)
    outcome = _assert_honest(rep, ctx)
    bd = rep["diagnostic"]["bbse"]
    assert bd["n_target_sites"] in (None, len(set(ctx["tgt_sites"])))
    # report round-trips to JSON with the stable shapes
    ser = json.dumps({k: v for k, v in rep["diagnostic"].items()
                      if k != "abstention_profile" and k != "composition"},
                     default=str)
    assert json.loads(ser)["feasibility"].keys() == {"0.05", "0.1"}
    assert outcome in ("certified", "declined")
