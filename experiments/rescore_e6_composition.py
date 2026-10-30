"""Re-derive E6's BBSE-implied answered-set composition against the head's own prior.

POST-HOC (2026-10-29). The released E6 composition
(experiments/out/E6_composition.json, Supplementary Table S9, Section 4.7)
reports a BBSE-implied true-positive fraction of the answered set, 0.0858
(2,170.87 expected positives). It was computed by multiplying every record's
head posterior odds by BBSE's rho_point = odds(pi_t) / odds(pi_source), where
pi_source is the record-pooled S_aux prevalence the fit divides out. The
logistic head is fit on S_train with an unpenalized intercept, so its odds
carry the S_train prevalence pi_train, not pi_source. The label-shift prior
correction (Saerens, Latinne and Decaestecker 2002) therefore multiplies by
odds(pi_t) / odds(pi_train) = rho_point * odds(pi_source) / odds(pi_train),
with pi_source clipped exactly as rho_box_interval clips it. The released
multiplier is exact only when pi_train equals pi_source; in E6 they are
0.1024 and 0.1153 (audit 2026-10 BBSE-1, verdicts composition-prior#L1#0 and
composition-prior#L2#0).

This file replays E6 in memory exactly as run_E6 does it -- _rng(6),
_draw_split on ANCHOR_SITES, the 40-site e6t target pool, run_certgate with
target_site_id and oracle_target_y, tau* from the operative rung -- and
recomputes the composition both ways. run_certgate and fit_head draw nothing
from the _rng(6) stream (the BBSE bootstrap seeds from the target bytes, the
walks from certification_rng), so the replay reproduces the released target
pool byte for byte.

Refuse-to-write self-check. Before anything is written, the replay must
reproduce, with exact float equality, every value of the released
composition block it builds on: rho_point; the predicted-class
positive_fraction, n_positive and n_answered; the oracle-class
positive_fraction, n_positive and n_answered; and the released
bbse_true_class positive_fraction and expected_n_positive under the released
rho-only multiplier. The corrected values must then match the ones the two
verdicts derived independently (to the decimals they quote). Any difference
aborts with nothing written.

Nothing here is a certified quantity: the BBSE-implied view is an estimated,
label-shift-tagged diagnostic, and no certificate, tier, rho_point, walk
order or guarantee string moves. The eICU counterpart cannot be corrected
from released artifacts (pi_train for the published split is not recorded)
and is not attempted here.

Inputs: experiments/out/E6_composition.json (read only; its sha256 goes into
the _run block). The replay itself reads no file.

Run: python -m experiments.rescore_e6_composition [--out DIR]

Writes E6_composition_corrected.json into experiments/out-e6-composition/
(the README.md beside it is hand-written). Takes seconds to half a minute
(one E6 head fit and one run_certgate call).

Refs: SPEC "explain.py" composition; audit F25; audit 2026-10 BBSE-1.
"""

import argparse
import json
import os
import sys
import time

import numpy as np

from certgate.constants import PI_CLIP
from certgate.data import SimConfig, draw_cohort
from certgate.explain import composition
from certgate.pipeline import run_certgate
from experiments.run_synthetic import ANCHOR_SITES, _draw_split, _rng
from experiments.derive_fixpass_numbers import (EXP_DIR, assert_not_frozen,
                                                run_block, _read_json)
from experiments.run_eicu import _write_json

OUT_DIR = os.path.join(EXP_DIR, "out-e6-composition")
OUT_NAME = "E6_composition_corrected.json"
FROZEN = os.path.join(EXP_DIR, "out", "E6_composition.json")

# Every released output directory. derive_fixpass_numbers.assert_not_frozen
# covers every entry here; the list is kept so this sidecar names them itself.
FROZEN_DIRS = ("out", "out-panel", "out-sens", "out-subgroups",
               "out-faithfulness", "out-rev2", "out-timing", "out-settled",
               "out-derived", "out-e9a-rescore", "out-e9b-positives",
               "out-bbse-probe")

# The values both verdicts derived independently for the corrected view
# (value, decimals compared). If the replay lands elsewhere, nothing is written.
VERDICT_EXPECTED = {
    "positive_fraction": (0.0913101048, 10),
    "expected_n_positive": (2311.424, 3),
    "odds_multiplier": (0.9475924166, 10),
    "pi_train": (0.1023781383, 10),
    "pi_source": (0.1152509772, 10),
}

POST_HOC = ("[MEASURE] POST-HOC (2026-10-29): in-memory replay of E6 and a "
            "re-derivation of its BBSE-implied answered-set composition "
            "against the head's S_train prior (audit 2026-10 BBSE-1). "
            "experiments/out/E6_composition.json is unchanged and keeps the "
            "rho-only multiplier. The BBSE-implied view is an estimated, "
            "label-shift-tagged diagnostic; no certified quantity descends "
            "from this file.")

FORMULA_NOTE = (
    "released: odds_t = rho_point * odds_head, with rho_point = "
    "odds(pi_t)/odds(clip(pi_source)) and pi_source the record-pooled S_aux "
    "prevalence. corrected: odds_t = odds_multiplier * odds_head, with "
    "odds_multiplier = rho_point * odds(clip(pi_source))/odds(pi_train) = "
    "odds(pi_t)/odds(pi_train) and pi_train = train.y.mean(), the S_train "
    "prevalence the logistic head's odds carry. clip is to "
    "[PI_CLIP, 1 - PI_CLIP], as rho_box_interval clips it. Both views "
    "average p_t = odds_t/(1 + odds_t) over the answered records.")


def _odds(p):
    return p / (1.0 - p)


def assert_writable(path):
    """Refuse any write into a released or another sidecar's directory."""
    assert_not_frozen(path, own="out-e6-composition")
    target = os.path.normcase(os.path.abspath(path))
    for name in FROZEN_DIRS:
        frozen = os.path.normcase(os.path.join(EXP_DIR, name))
        if target == frozen or target.startswith(frozen + os.sep):
            raise SystemExit(
                f"refusing to write {path}: experiments/{name}/ is frozen; "
                f"this sidecar writes to experiments/out-e6-composition/ "
                f"(reason=frozen-output-dir)")


def released_view(head, target_x, answered, rho_point):
    """The released BBSE-implied view: head odds times rho_point, per record.

    Kept verbatim from certgate/explain.py composition() as of c27e798, the
    code that wrote experiments/out/E6_composition.json, so the self-check
    can reproduce the frozen numbers bit for bit.
    """
    n_ans = int(answered.sum())
    p_s = np.asarray(head.predict_proba(target_x), dtype=np.float64)
    odds_s = p_s / np.clip(1.0 - p_s, 1e-12, None)
    odds_t = float(rho_point) * odds_s
    p_t = odds_t / (1.0 + odds_t)
    return dict(
        positive_fraction=(float(p_t[answered].mean()) if n_ans
                           else float("nan")),
        expected_n_positive=(float(p_t[answered].sum()) if n_ans
                             else float("nan")),
        odds_multiplier=float(rho_point),
        rho=float(rho_point),
        n_answered=n_ans)


def corrected_multiplier(rho_point, pi_source, pi_train):
    """rho_point * odds(clip(pi_source)) / odds(pi_train), as composition() forms it."""
    ps = float(np.clip(float(pi_source), PI_CLIP, 1.0 - PI_CLIP))
    return float(rho_point) * (ps / (1.0 - ps)) / (pi_train / (1.0 - pi_train))


def replay():
    """Replay E6 call for call (run_synthetic.run_E6) and return its pieces."""
    cfg = SimConfig()
    rng = _rng(6)
    train, aux, cal, head = _draw_split(cfg, ANCHOR_SITES, rng)
    tgt = draw_cohort(cfg, 40, rng, site_label_prefix="e6t")
    tgt_sites = np.array(tgt.site_labels, dtype=object)[tgt.site_id]
    rep = run_certgate(train, aux, cal, tgt.x, target_label="E6",
                       target_site_id=tgt_sites, oracle_target_y=tgt.y)
    op = rep["operative"]
    tau_star = op["tau"] if op else 0.8
    answered = head.score(tgt.x) >= tau_star
    bb = rep["diagnostic"]["bbse"]
    return dict(head=head, train=train, tgt=tgt, answered=answered,
                tau_star=float(tau_star), bbse=bb)


def self_check(released, replayed_comp, rho_point, frozen_comp):
    """Exact-equality check of the replay against the frozen composition block.

    released: released_view() on the replay; replayed_comp: composition() on
    the replay; frozen_comp: the "composition" object of the frozen JSON.
    Returns the list of checked fields; raises SystemExit on any difference.
    """
    fb = frozen_comp["bbse_true_class"]
    fp = frozen_comp["predicted_class"]
    fo = frozen_comp["oracle_true_class"]
    rp_, ro = replayed_comp["predicted_class"], replayed_comp["oracle_true_class"]
    pairs = {
        "bbse_true_class.rho": (float(rho_point), fb["rho"]),
        "bbse_true_class.positive_fraction (released formula)":
            (released["positive_fraction"], fb["positive_fraction"]),
        "bbse_true_class.expected_n_positive (released formula)":
            (released["expected_n_positive"], fb["expected_n_positive"]),
        "bbse_true_class.n_answered":
            (float(released["n_answered"]), fb["n_answered"]),
        "predicted_class.positive_fraction":
            (float(rp_["positive_fraction"]), fp["positive_fraction"]),
        "predicted_class.n_positive":
            (float(rp_["n_positive"]), fp["n_positive"]),
        "predicted_class.n_answered":
            (float(rp_["n_answered"]), fp["n_answered"]),
        "oracle_true_class.positive_fraction":
            (float(ro["positive_fraction"]), fo["positive_fraction"]),
        "oracle_true_class.n_positive":
            (float(ro["n_positive"]), fo["n_positive"]),
        "oracle_true_class.n_answered":
            (float(ro["n_answered"]), fo["n_answered"]),
    }
    bad = {k: dict(replayed=a, frozen=b) for k, (a, b) in pairs.items()
           if a != b}
    if bad:
        raise SystemExit(
            f"rescore_e6_composition: the replay does not reproduce the "
            f"frozen E6 composition exactly: {bad}; nothing written "
            f"(reason=replay-mismatch)")
    return sorted(pairs)


def check_verdict(corrected):
    """The corrected view must land on the verdicts' values; else refuse."""
    bad = {k: dict(got=corrected[k], expected=v)
           for k, (v, dp) in VERDICT_EXPECTED.items()
           if round(float(corrected[k]), dp) != v}
    if bad:
        raise SystemExit(
            f"rescore_e6_composition: the corrected view departs from the "
            f"verdicts' expected values: {bad}; nothing written "
            f"(reason=verdict-mismatch)")


def derive(frozen_path=FROZEN, log=print):
    """Replay, self-check and build the sidecar document (nothing written)."""
    frozen = _read_json(frozen_path)
    t0 = time.perf_counter()
    r = replay()
    head, tgt, answered, bb = r["head"], r["tgt"], r["answered"], r["bbse"]
    rho = bb.get("rho_point")
    if rho is None:
        raise SystemExit("rescore_e6_composition: the replayed BBSE fit "
                         "declined; the frozen file has a rho_point "
                         "(reason=replay-mismatch)")
    pi_train = float(np.mean(r["train"].y))
    comp = composition(head, tgt.x, answered, rho_point=rho, oracle_y=tgt.y,
                       pi_source=bb.get("pi_s"), pi_train=pi_train)
    rel = released_view(head, tgt.x, answered, rho)
    checked = self_check(rel, comp, rho, frozen["composition"])

    cb = comp["bbse_true_class"]
    mult = corrected_multiplier(rho, bb["pi_s"], pi_train)
    if mult != cb["odds_multiplier"]:
        raise SystemExit("rescore_e6_composition: the odds multiplier differs "
                         "from composition()'s (reason=self-check-failed)")
    pi_source = cb["pi_source"]
    # pi_t implied by rho_point against the clipped source prevalence.
    o_t = float(rho) * _odds(pi_source)
    pi_t_implied = o_t / (1.0 + o_t)
    corrected = dict(
        tag=cb["tag"],
        positive_fraction=cb["positive_fraction"],
        expected_n_positive=cb["expected_n_positive"],
        odds_multiplier=cb["odds_multiplier"],
        rho=cb["rho"], pi_train=cb["pi_train"], pi_source=pi_source,
        n_answered=cb["n_answered"])
    check_verdict(corrected)
    fb = frozen["composition"]["bbse_true_class"]
    released = dict(
        tag=fb["tag"],
        positive_fraction=fb["positive_fraction"],
        expected_n_positive=fb["expected_n_positive"],
        odds_multiplier=rel["odds_multiplier"],
        rho=fb["rho"], pi_train=pi_train, pi_source=pi_source,
        n_answered=fb["n_answered"],
        note=("the released multiplier is rho alone, i.e. the head's odds "
              "were treated as carrying pi_source; pi_train and pi_source "
              "are recorded here for comparison, they are not keys of the "
              "frozen file"))
    oracle = dict(comp["oracle_true_class"])
    o_frac = oracle["positive_fraction"]
    doc = dict(
        post_hoc=POST_HOC,
        formula=FORMULA_NOTE,
        headline=(
            f"E6 BBSE-implied true-class fraction: released "
            f"{released['positive_fraction']:.10f} "
            f"({released['expected_n_positive']:.3f} expected), corrected "
            f"{corrected['positive_fraction']:.10f} "
            f"({corrected['expected_n_positive']:.3f} expected, multiplier "
            f"{corrected['odds_multiplier']:.10f}); oracle "
            f"{o_frac:.10f} ({oracle['n_positive']} of "
            f"{oracle['n_answered']})"),
        bbse_true_class=dict(released=released, corrected=corrected),
        oracle_true_class=oracle,
        predicted_class=dict(comp["predicted_class"]),
        relative_error_vs_oracle=dict(
            released=(released["positive_fraction"] - o_frac) / o_frac,
            corrected=(corrected["positive_fraction"] - o_frac) / o_frac),
        bbse_fit=dict(rho_point=float(rho), pi_s_unclipped=float(bb["pi_s"]),
                      pi_t_implied=pi_t_implied,
                      q_target=float(bb["q_target"]), c0=float(bb["c0"]),
                      c1=float(bb["c1"]), rho_lo=float(bb["rho_lo"]),
                      rho_hi=float(bb["rho_hi"])),
        replay=dict(stream="_rng(6)", anchor_sites=ANCHOR_SITES,
                    target_sites=40, target_prefix="e6t",
                    tau_star=r["tau_star"],
                    pi_train_definition="train.y.mean()",
                    n_train=int(len(r["train"].y)),
                    n_train_positive=int(np.sum(r["train"].y))),
        self_check=dict(
            exact_equality_with=os.path.relpath(
                frozen_path, os.path.dirname(EXP_DIR)).replace(os.sep, "/"),
            fields=checked, mismatches=0,
            verdict_expected={k: v for k, (v, _dp)
                              in VERDICT_EXPECTED.items()}),
        not_moved=("no certificate, certified tier, estimated tier, "
                   "rho_point, rho box, walk order or guarantee string; the "
                   "predicted-class and oracle views are unchanged"),
        wall_clock_s=round(time.perf_counter() - t0, 1))
    if log:
        log(f"[certgate] e6 composition: {doc['headline']}")
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="re-derive E6's BBSE-implied composition (post-hoc)")
    ap.add_argument("--out", default=OUT_DIR)
    args = ap.parse_args(argv)
    path = os.path.join(args.out, OUT_NAME)
    assert_writable(path)
    doc = derive()
    os.makedirs(args.out, exist_ok=True)
    _write_json(path, {"_run": run_block([FROZEN]), **doc},
                "rescore_e6_composition")
    print(f"[certgate] wrote {path} ({doc['wall_clock_s']} s)",
          file=sys.stderr)
    return doc


if __name__ == "__main__":
    main()
