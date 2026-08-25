"""Read-only rendering of the eICU abstention-driver figure (main Figure 3).

Everything here is derived from the released 20-replicate diagnostics artifact
experiments/out/EICU_diagnostics.json. The key is abstention_gap_ranking: the
per-replicate top-10 answered-vs-declined attribution gap run_eicu already
emits at the operative rung. The restricted extract is never touched and no
pipeline is re-run, exactly like panel_confusion_tables.py.

The one write is the PNG the draft calls out. The counts the draft quotes are
recomputed here and printed to stdout as JSON, so the text can be checked
against the artifact and not against a prose copy:

  - GCS motor is the top driver on 20/20 re-splits
  - FiO2 is in the top three on 13
  - the day-1 intubation flag is in the top three on 10

Aggregate-only by construction: ten features x twenty replicates of a cohort
mean, no record ever present. The feature glossary maps allowlisted eICU
column names to the clinical reading a figure needs; it is display only.

Run: python -m experiments.fig_eicu_abstention_drivers [diagnostics-json] [out-png]

Refs: draft section 4.11; venue-fit pass 2026-08-21.
"""

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt        # noqa: E402
import numpy as np                     # noqa: E402

DIAG_DEFAULT = os.path.join("experiments", "out", "EICU_diagnostics.json")
PNG_DEFAULT = os.path.join("experiments", "out", "EICU_abstention_drivers.png")
TOP_N_FEATURES = 10                    # the depth run_eicu emits (EICU_TOP_GAP_FEATURES)
TOP_K_MEMBERSHIP = 3                   # "top three" in the draft

# display glossary: allowlisted eICU column -> clinical reading (figure only)
GLOSSARY = {
    "aps_motor": "GCS motor score",
    "aps_eyes": "GCS eye opening",
    "aps_verbal": "GCS verbal score",
    "aps_fio2": "FiO$_2$ (day 1)",
    "aps_pao2": "PaO$_2$ (day 1)",
    "aps_pco2": "PaCO$_2$ (day 1)",
    "aps_ph": "arterial pH (day 1)",
    "aps_intubated": "intubated (APS day 1)",
    "apv_oobintubday1": "intubated out of OR, day 1",
    "apv_oobventday1": "ventilated out of OR, day 1",
    "aps_temperature": "temperature (day 1)",
    "aps_heartrate": "heart rate (day 1)",
    "aps_heartrate__missing": "heart rate missing",
    "aps_meanbp": "mean BP (day 1)",
    "aps_respiratoryrate": "respiratory rate (day 1)",
    "aps_sodium": "sodium (day 1)",
    "aps_creatinine": "creatinine (day 1)",
    "aps_bun": "BUN (day 1)",
    "aps_glucose": "glucose (day 1)",
    "aps_albumin": "albumin (day 1)",
    "aps_bilirubin": "bilirubin (day 1)",
    "aps_hematocrit": "hematocrit (day 1)",
    "aps_wbc": "white cell count (day 1)",
    "aps_urine": "urine output (day 1)",
    "age": "age",
    "unitstaytype=stepdown/other": "unit stay type: step-down / other",
}


def _label(name):
    return GLOSSARY.get(name, name.replace("_", " "))


def load_rankings(path):
    doc = json.load(open(path, encoding="utf-8"))
    block = doc["abstention_gap_ranking"]
    keys = sorted(block, key=lambda k: int(k.split("replicate")[1].split("_")[0]))
    return [(k, block[k]["ranking"]) for k in keys]


def counts(rankings):
    top1, topk, gaps = {}, {}, {}
    for _, ranking in rankings:
        names = [r["feature"] for r in ranking]
        top1[names[0]] = top1.get(names[0], 0) + 1
        for n in names[:TOP_K_MEMBERSHIP]:
            topk[n] = topk.get(n, 0) + 1
        for r in ranking:
            gaps.setdefault(r["feature"], []).append(r["gap"])
    return top1, topk, gaps


def render(rankings, png):
    n_rep = len(rankings)
    top1, topk, gaps = counts(rankings)
    # left panel: features ordered by how often they appear in the emitted
    # top-10, then by mean gap. The gap is answered-minus-declined mean |phi|,
    # so a negative value means the feature pulls harder on declined cases.
    order = sorted(gaps, key=lambda f: (-len(gaps[f]), np.mean(gaps[f])))[:TOP_N_FEATURES]
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.6),
                           gridspec_kw={"width_ratios": [1.35, 1.0]})
    y = np.arange(len(order))[::-1]
    for yi, f in zip(y, order):
        v = np.asarray(gaps[f], dtype=np.float64)
        ax[0].scatter(v, np.full(v.shape, yi), s=14, color="tab:blue",
                      alpha=0.45, zorder=2)
        ax[0].plot([v.min(), v.max()], [yi, yi], color="tab:blue", lw=1,
                   alpha=0.5, zorder=1)
        ax[0].scatter([v.mean()], [yi], s=46, color="black", marker="D",
                      zorder=3)
        ax[0].text(1.01, yi, f"{len(v)}/{n_rep}", va="center", fontsize=7.5,
                   color="dimgray", transform=ax[0].get_yaxis_transform())
    ax[0].axvline(0.0, color="gray", lw=0.8, ls="--")
    ax[0].set_yticks(y)
    ax[0].set_yticklabels([_label(f) for f in order], fontsize=8.5)
    ax[0].set_xlabel("answered minus declined mean |attribution| (logit units)")
    ax[0].set_title(f"Where the gate abstains: attribution gap, {n_rep} "
                    f"re-splits (n/{n_rep} = re-splits in the emitted top ten)",
                    fontsize=9.5)
    ax[0].grid(axis="x", lw=0.3, alpha=0.5)
    # right panel: top-3 membership per re-split, for every feature that ever
    # enters the top three. A presence grid, so the 20/20 reads off directly.
    members = sorted(topk, key=lambda f: (-topk[f], np.mean(gaps[f])))
    grid = np.zeros((len(members), n_rep))
    for j, (_, ranking) in enumerate(rankings):
        names = [r["feature"] for r in ranking[:TOP_K_MEMBERSHIP]]
        for i, f in enumerate(members):
            if f in names:
                grid[i, j] = TOP_K_MEMBERSHIP - names.index(f)   # 3 = rank 1
    ax[1].imshow(grid, aspect="auto", cmap="Blues", vmin=0,
                 vmax=TOP_K_MEMBERSHIP)
    ax[1].set_yticks(range(len(members)))
    ax[1].set_yticklabels([f"{_label(f)}  ({topk[f]}/{n_rep})"
                           for f in members], fontsize=8.5)
    ax[1].set_xticks(range(0, n_rep, 5))
    ax[1].set_xticklabels([str(i) for i in range(0, n_rep, 5)], fontsize=8)
    ax[1].set_xlabel("by-site re-split")
    ax[1].set_title("Top-three abstention driver per re-split\n"
                    "(darkest = rank 1)", fontsize=10)
    for i in range(len(members)):
        for j in range(n_rep):
            if grid[i, j] > 0:
                ax[1].text(j, i, str(int(TOP_K_MEMBERSHIP - grid[i, j] + 1)),
                           ha="center", va="center", fontsize=6.5,
                           color="white" if grid[i, j] >= 2 else "black")
    fig.tight_layout()
    fig.savefig(png, dpi=110)
    plt.close(fig)
    return order, members


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    diag = argv[0] if argv else DIAG_DEFAULT
    png = argv[1] if len(argv) > 1 else PNG_DEFAULT
    rankings = load_rankings(diag)
    order, members = render(rankings, png)
    top1, topk, gaps = counts(rankings)
    out = {
        "source": diag, "png": png, "n_replicates": len(rankings),
        "top1_counts": dict(sorted(top1.items(), key=lambda kv: -kv[1])),
        "top3_counts": dict(sorted(topk.items(), key=lambda kv: -kv[1])),
        "mean_gap_by_feature": {f: round(float(np.mean(gaps[f])), 6)
                                for f in order},
        "n_in_top10_by_feature": {f: len(gaps[f]) for f in order},
        "figure_rows_left": [_label(f) for f in order],
        "figure_rows_right": [_label(f) for f in members],
    }
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return out


if __name__ == "__main__":
    main()
