# out-derived-r2/ -- POST-HOC, read-only derivation (corrected re-derivation)

**Status: POST-HOC (2026-10-29).** Nothing here is a certified quantity. This
directory holds one file, `fixpass_numbers.json`. It comes from the same
read-only derivation as `experiments/out-derived/fixpass_numbers.json`, which
stays frozen as released (run stamp 2026-09-07T01:29:07Z). The inputs are the
same released artifacts under `experiments/out/`, `out-panel/`, `out-sens/`,
`out-subgroups/` and `out-faithfulness/`, the four post-hoc sidecars
(`out-e9a-rescore/`, `out-e9b-positives/`, `out-bbse-probe/`, `out-settled/`)
and lane C's re-emitted eICU run (`out-rev2/`). The derivation is now run by
the corrected `experiments/derive_fixpass_numbers.py` (audit 2026-10, EICU-2,
EICU-12, synthetic-5). No number quoted in the manuscript changes. For the
three ratios below the manuscript quotes 0.98, 3.9-fold and 0.48, and those
hold either way.

Produced by `experiments/derive_fixpass_numbers.py`:

    python -m experiments.derive_fixpass_numbers

That default output is this directory. The script refuses to write into
`out-derived/` and the other frozen directories.

## What differs from out-derived/fixpass_numbers.json

The two files were diffed field by field, with `_run` compared separately.
These are the only differences.

Values:

  - `rev2.pooled_new_columns` read "no new columns found". It is removed and
    replaced by `rev2.comparator_new_columns`. The script looked for the seven
    columns appended on 2026-09-04 in `out-rev2/EICU_pooled.csv`, but
    `run_eicu` writes them only to `out-rev2/EICU_comparator.csv`. The
    re-emitted pooled file is byte-identical to the released one, so the
    columns could never be found there. The columns are now summarised over
    that file's 20 alpha = 0.10 rows (mean / sd / min / max):
      - head AUC on the pool: 0.8593 / 0.0062 / 0.8429 / 0.8707
      - head Brier on the pool: 0.0616 / 0.0036 / 0.0561 / 0.0693
      - head AUC on the answered set: 0.8098 / 0.0145 / 0.7649 / 0.8326
      - head Brier on the answered set: 0.0428 / 0.0053 / 0.0328 / 0.0503
      - APACHE-IVa AUC on the pool: 0.8601 / 0.0067 / 0.8480 / 0.8711
      - APACHE-IVa Brier on the pool: 0.0630 / 0.0031 / 0.0584 / 0.0687
      - n_apache_available_pool: mean 15,838.95

    These figures are the held-out-pool rows and the answered-set head rows of
    Supplementary Table S11, and Table 2's 0.859, 0.860 and 0.810. A comparator
    file that lacks the columns now stops the derivation, where before it
    printed a fallback string.
  - `three_way_composition.bbse_transfer.true_odds_ratio_vs_pi_s` is
    0.983 -> 0.984. The old value used pi_s already rounded for display to
    0.0912. It is now computed from the certificate's unrounded c0, c1 and pi_s
    and the panel's integer pool counts (1362/15169), which gives 0.98359.
    `pool_prevalence_observed` (0.0898) and
    `expected_q_at_observed_prevalence` (0.0365) do not move.
  - `fairness.age_gradients.answered_err_ratio` is 3.89 -> 3.88. The old value
    divided the 4-dp age-band display means. The unrounded means give
    0.074985 / 0.019345 = 3.876. `deferral_ratio` stays 4.86.
  - `rev2.faithfulness_spearman.mean` is 0.4849 -> 0.4848. The old value
    averaged per-replicate Spearman correlations already rounded to 4 dp. The
    exact mean of the 20 rank correlations is 16/33 = 0.4848485. sd 0.2041,
    min 0.1273 and max 0.8667 do not move. `faithfulness_by_replicate` keeps
    its 4-dp values.

Descriptive strings:

  - `head_auc_s_cal.note` now names `rev2.comparator_new_columns`
    (`out-rev2/EICU_comparator.csv`) as the place where the pool and
    answered-set AUC and Brier live.
  - `e1.note` now says that the influence-cap sweep (Table S4) replays every
    draw in baseline mode. The six draws that deployed a BBSE threshold enter
    the sweep at their baseline-walk threshold, and only its threshold
    self-check is restricted to the baseline-deploying draws. The old note
    said those six were excluded from Table S4.
  - `p4_signed.rule` now describes the registered P4 set as
    "aps_*__missing / apv_*__missing sibling" instead of "*__missing sibling".
    The script's matcher was tightened to match, and it counts one ranking per
    re-split, at the operative rung. All `p4_signed` counts are unchanged.

Provenance:

  - `sidecars.settled.run` is 2026-09-05T16:33:18+00:00 -> 2026-09-07T01:29:12+00:00.
    The released derivation was written five seconds before the settled
    sidecar's final write, so it folded in an earlier write with the same
    headline. It now carries the stamp of the committed
    `out-settled/EICU-PREDICTIONS-SETTLED.json`.
  - In `_run.inputs`, `out-rev2/EICU_comparator.csv` is hashed in place of
    `out-rev2/EICU_pooled.csv`. The hash of
    `out-settled/EICU-PREDICTIONS-SETTLED.json` now matches the committed file
    (398073b2...). `_run.utc` and `_run.git_sha` are this run's. The sha is
    the branch tip (c27e798) at emission time, with the corrected script
    still uncommitted in the working tree.

Every other derived value, including the seven pins, the composition, the
calibration, the published-split confusion counts, the fairness cells, the E9
blocks and the exact intervals, is equal to the released file.

## Pins

Seven values are pinned inside the script: composition mean 0.0524, head AUC
on S_cal 0.8618, 63 positive calls on the published split, 8 fairness cells
over budget, 570 fairness cells with status ok, Spearman 0.636 for replicate 0
and 194 baseline-mode E1 draws. If any of them stops reproducing, nothing is
written.
All seven reproduced on this emission. The JSON's `_run` block records the UTC
time, the git sha and the sha256 of every input read. No pipeline is re-run
and the restricted extract is never touched.
