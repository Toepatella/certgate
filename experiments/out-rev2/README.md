# experiments/out-rev2/ -- POST-HOC 20-replicate re-run (post-hoc diagnostics)

POST-HOC. Written on 2026-09-05 during the post-hoc revision pass, after the eICU-CRD v2.0
extract had been read and after the release run in `experiments/out/` was
frozen. Nothing here is part of the pre-extract protocol freeze; nothing here
re-certifies anything. The released run stays where it is and remains the
run the paper's certified numbers cite. This directory exists because the
post-hoc pass appended diagnostics the release run did not record, and the only
honest way to obtain them was to run the whole protocol again with the
appended code and prove that the certified path did not move.

What produced it, exactly:

    python -m experiments.run_eicu --data eicu-extract --replicates 20 --out experiments/out-rev2

The runner's reference-fingerprint check (`reference_check=True`) compared the
extract's row counts and data_sha against the frozen provenance and passed.
Seed 20260721, primary arm, 164,322 stays over 207 hospitals, the same
train / aux / calibration / target draws as the release run.

What is appended, and where (everything before it is the frozen material):

  - `EICU_comparator.csv` -- seven columns after the frozen ones:
    `head_auc_pool`, `head_brier_pool`, `head_auc_answered`,
    `head_brier_answered`, `apache_iva_auc_pool`, `apache_iva_brier_pool`,
    `n_apache_available_pool` (the pool is every held-out stay of the
    replicate; the answered set is the certified subset).
  - `EICU_per_site.csv` -- one column after the frozen ones: `share_75plus`
    (share of the hospital pool aged 75 or older). The Spearman correlation
    of that share with the per-pool answered error rate is a scalar in the
    `EICU-PERSITE` block of `EICU-SUMMARY.md`.
  - `EICU_subgroups.csv` -- a sixth dimension, `aps_present`
    (levels `present` / `absent`), appended after the `unittype` rows of
    each replicate (SPEC PIN AMENDMENT 2026-09-04).
  - `EICU_diagnostics.json` -- two keys after the frozen ones:
    `los_under_24h` (per-replicate counts of stays whose ICU stay ended
    before the hour-24 prediction time, split answered / declined and
    deaths) and `top_driver_coef_rank` (the rank of the top abstention
    driver in the head's |coefficient| ordering over the 161 features).
  - `EICU-SUMMARY.md` -- the `EICU-POOLED` block gains a `los_under_24h`
    scalar block; `EICU-COMPARATOR` and `EICU-PERSITE` gain the means of
    the columns above.
  - `EICU_faithfulness.csv` -- all 20 replicates (the frozen
    `experiments/out-faithfulness/` file holds replicate 0 only; its rows
    are reproduced here byte-for-byte).
  - `GATE2-REPORT.json` -- written by `python -m experiments.gate2_diff`,
    which projected this directory onto the frozen columns and keys of
    `experiments/out/`, `experiments/out-subgroups/` and
    `experiments/out-faithfulness/` and found 11 of 11 artifacts identical
    (byte-identical tables, value-identical JSON documents). To re-run the
    gate use the flag form, `python -m experiments.gate2_diff --new
    experiments/out-rev2 --old experiments/out` (the script takes no
    positionals; without `--report` it writes `GATE2-REPORT.json` to the
    current working directory, never into this directory, and it refuses to
    overwrite an existing report without `--force`).

Wall-clock for the compute statement (Appendix A.3): 1,767.7 s (29.5 min)
on an Intel Core Ultra 7 165U (14 logical cores, 31.5 GB RAM, Windows 11,
CPU only; Python 3.13.3, numpy 2.5.0, scipy 1.18.0, scikit-learn 1.9.0),
measured as the subprocess wall clock around the command line above,
including the reference-fingerprint check.

Aggregate-only, like every eICU artifact in this repository:
`run_eicu.assert_aggregate_only` gated every write. The per-stay length of
stay used for the sub-24 h counts is a diagnostic side array on the cohort
object (never a feature column, never written, never keyed by stay id);
`unitdischargeoffset` remains a denylisted feature.
