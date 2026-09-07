# experiments/out-timing/ -- POST-HOC preflight re-run (timing and LOS window)

POST-HOC. Written on 2026-09-05 during the post-hoc revision pass, after the eICU-CRD v2.0
extract had been read and after the release run in `experiments/out/` was
frozen. Nothing here is part of the pre-extract protocol freeze; nothing here
certifies anything. The released preflight stays where it is; this directory
exists for two numbers the release run did not record.

What produced it, exactly:

    python -m experiments.run_eicu --data eicu-extract --preflight --out experiments/out-timing

  - `EICU_preflight.json` -- the same preflight profile as
    `experiments/out/EICU_preflight.json`, plus the keys appended by the fix
    pass under `apache_absent_los`: `n_lt_24h` / `frac_lt_24h` on each existing
    LOS stratum and a `los_window` block (whole selected cohort and its deaths)
    counting the stays whose ICU stay ended before the hour-24 prediction time.
    `experiments/gate2_diff.py` projects this file onto the released file's
    keys and requires identity; the only key it does not compare is the
    `data_dir` invocation string (`./eicu-extract` then, `eicu-extract` now).
  - `EICU-SUMMARY.md`, `EICU_provenance.json` -- the runner writes both in a
    `finally:` block on every invocation; that is why `--out` is now required
    and why this run has its own directory.

Wall-clock for the compute statement (Appendix A.3): 48.7 s on an Intel Core
Ultra 7 165U (14 logical cores, 31.5 GB RAM, Windows 11, CPU only; Python
3.13.3, numpy 2.5.0, scipy 1.18.0, scikit-learn 1.9.0), including the
reference-fingerprint check against the released row counts, which passed.

Aggregate-only, like every eICU artifact in this repository:
`run_eicu.assert_aggregate_only` gated every write. `unitdischargeoffset` is
a denylisted feature; it was read here as a diagnostic and reduced to counts
and quantiles, never to a per-stay value.
