"""ETL: hostile synthetic relational extract -> CertGate cohorts (SPEC Tests,
fixture audit 2026-07-25).

Reads a `synth_fixture` output directory's {entity_session,measurement}.csv.gz
with the csv module (NEVER line-based tools: fields carry embedded
newlines/commas/quotes), builds a finite float64 feature matrix with explicit
missing-indicator columns, and partitions BY SITE (the unit of statistical
independence). The feature matrix deliberately NEVER includes close_state —
in --signal mode that column IS the outcome.

Stdlib + numpy only.
"""
from __future__ import annotations

import csv
import gzip
import sys
from collections import defaultdict

import numpy as np

SPLIT_RNG_SEED = 20260721
N_TARGET_SITES = 12

CAT_ATTR_CATEGORY = ("cat_a", "cat_b", "cat_u", "")
CAT_SESSION_KIND = ("kind_admit", "kind_readmit", "kind_transfer", "kind_stepdown")
CAT_CHANNEL_TYPE = ("chan_alpha", "chan_beta", "chan_gamma", "chan_delta",
                    "chan_epsilon")
CAT_ATTR_CLASS = ("cls_1", "cls_2", "cls_3", "cls_4", "cls_5", "cls_other", "")

csv.field_size_limit(10 ** 7)


# ---------------------------------------------------------------- readers ---

def _read_table(data_dir, name):
    """Yield dict rows from a gzipped CSV. csv.reader with newline='' is the
    ONLY safe read: the generator embeds newlines/commas/quotes in text fields."""
    path = f"{data_dir}/{name}.csv.gz"
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        r = csv.reader(fh)
        header = next(r)
        for row in r:
            yield dict(zip(header, row))


def _maybe_float(s):
    """'' / whitespace / junk -> None; else float. Never raises."""
    if s is None:
        return None
    t = s.strip()
    if not t:
        return None
    try:
        return float(t)
    except ValueError:
        return None


def _attr_band(s):
    """The documented int() trap: '' is missing, '> 89' is a ceiling token.

    A naive int(row['attr_band']) raises on ~7.3% of rows here (578 '> 89'
    + 80 ''), which is exactly what the generator advertises.
    """
    t = (s or "").strip()
    if not t:
        return None
    if t == "> 89":
        return 90.0
    return float(int(t))          # int() first: asserts the residue is integral


# ------------------------------------------------------- measurement agg ---

def measurement_aggregates(data_dir):
    """Per-session (n_rows, n_parseable, sum_parseable, n_empty_value_num)."""
    n_rows = defaultdict(int)
    n_parse = defaultdict(int)
    sum_parse = defaultdict(float)
    n_empty = defaultdict(int)
    total = 0
    for d in _read_table(data_dir, "measurement"):
        sid = d["session_id"].strip()
        total += 1
        n_rows[sid] += 1
        raw = d["value_num"]
        v = _maybe_float(raw)
        if v is None:
            if not raw.strip():
                n_empty[sid] += 1
        else:
            n_parse[sid] += 1
            sum_parse[sid] += v
    return dict(n_rows=n_rows, n_parse=n_parse, sum_parse=sum_parse,
                n_empty=n_empty, total_rows=total)


# ------------------------------------------------------------- features ----

FEATURE_NAMES = (
    ["entry_metric_a", "entry_metric_a__missing",
     "entry_metric_b", "entry_metric_b__missing",
     "exit_metric_b", "exit_metric_b__missing",
     "attr_band", "attr_band__missing",
     "close_offset", "outer_open_offset", "outer_close_offset"]
    + [f"attr_category={v or 'EMPTY'}" for v in CAT_ATTR_CATEGORY]
    + [f"session_kind={v}" for v in CAT_SESSION_KIND]
    + [f"channel_type={v}" for v in CAT_CHANNEL_TYPE]
    + [f"attr_class={v or 'EMPTY'}" for v in CAT_ATTR_CLASS]
    + ["meas_n_rows", "meas_n_parseable", "meas_mean_value", "meas_n_empty"]
)


def build_matrix(data_dir, verbose=True):
    """Return (x, feature_names, meta) where meta carries per-row raw fields.

    Missing numerics are mean-imputed and every imputed column gets a 0/1
    indicator sibling, so no NaN ever reaches make_cohort (which rejects
    non-finite x loudly).
    """
    agg = measurement_aggregates(data_dir)
    rows = []
    for d in _read_table(data_dir, "entity_session"):
        rows.append(d)
    n = len(rows)

    raw_num = {k: np.full(n, np.nan) for k in
               ("entry_metric_a", "entry_metric_b", "exit_metric_b", "attr_band")}
    hard = {k: np.zeros(n) for k in
            ("close_offset", "outer_open_offset", "outer_close_offset")}
    meas = {k: np.zeros(n) for k in
            ("n_rows", "n_parse", "mean", "n_empty")}
    meas["mean"][:] = np.nan
    band_trap_hits = 0

    site_raw, kinds, classes, states, sess_ids = [], [], [], [], []
    for i, d in enumerate(rows):
        for k in ("entry_metric_a", "entry_metric_b", "exit_metric_b"):
            v = _maybe_float(d[k])
            if v is not None:
                raw_num[k][i] = v
        try:
            b = _attr_band(d["attr_band"])
        except ValueError:                       # would-be int() blow-up
            band_trap_hits += 1
            b = None
        if b is not None:
            raw_num["attr_band"][i] = b
        for k in hard:
            v = _maybe_float(d[k])
            if v is None:                        # NOT NULL columns can still be ''
                raise ValueError(f"row {i}: {k} empty/unparseable: {d[k]!r}")
            hard[k][i] = v
        sid = d["session_id"].strip()
        meas["n_rows"][i] = agg["n_rows"].get(sid, 0)
        meas["n_parse"][i] = agg["n_parse"].get(sid, 0)
        meas["n_empty"][i] = agg["n_empty"].get(sid, 0)
        np_ = agg["n_parse"].get(sid, 0)
        if np_ > 0:
            meas["mean"][i] = agg["sum_parse"][sid] / np_
        site_raw.append("site_" + d["site_id"].strip())
        kinds.append(d["session_kind"])
        classes.append(d["attr_class"])
        states.append(d["close_state"])
        sess_ids.append(sid)

    cols, missing_counts = [], {}
    for k in ("entry_metric_a", "entry_metric_b", "exit_metric_b", "attr_band"):
        v = raw_num[k]
        miss = ~np.isfinite(v)
        missing_counts[k] = int(miss.sum())
        mean = float(np.nanmean(v)) if np.isfinite(v).any() else 0.0
        filled = np.where(miss, mean, v)
        cols.append(filled)
        cols.append(miss.astype(np.float64))
    for k in ("close_offset", "outer_open_offset", "outer_close_offset"):
        cols.append(hard[k])

    def onehot(values, cats):
        for c in cats:
            cols.append(np.array([1.0 if v == c else 0.0 for v in values]))

    onehot([d["attr_category"] for d in rows], CAT_ATTR_CATEGORY)
    onehot(kinds, CAT_SESSION_KIND)
    onehot([d["channel_type"] for d in rows], CAT_CHANNEL_TYPE)
    onehot(classes, CAT_ATTR_CLASS)

    cols.append(meas["n_rows"])
    cols.append(meas["n_parse"])
    mmiss = ~np.isfinite(meas["mean"])
    missing_counts["meas_mean_value"] = int(mmiss.sum())
    mmean = float(np.nanmean(meas["mean"])) if np.isfinite(meas["mean"]).any() else 0.0
    cols.append(np.where(mmiss, mmean, meas["mean"]))
    cols.append(meas["n_empty"])

    x = np.column_stack(cols).astype(np.float64)
    assert x.shape == (n, len(FEATURE_NAMES)), (x.shape, len(FEATURE_NAMES))
    assert np.isfinite(x).all(), "feature matrix must be finite"

    meta = dict(site_raw=site_raw, session_kind=kinds, attr_class=classes,
                close_state=states, session_id=sess_ids,
                missing_counts=missing_counts,
                band_trap_hits=band_trap_hits,
                measurement_rows=agg["total_rows"],
                sessions_without_measurements=int((meas["n_rows"] == 0).sum()))
    if verbose:
        print(f"[etl] {n} sessions x {x.shape[1]} features; "
              f"missing={missing_counts}; "
              f"sessions w/o measurements={meta['sessions_without_measurements']}",
              file=sys.stderr)
    return x, list(FEATURE_NAMES), meta


# --------------------------------------------------------------- labels ----

def labels_common(meta):
    """~25% prevalence: 'case' iff session_kind == 'kind_readmit'."""
    return ["case" if k == "kind_readmit" else "control"
            for k in meta["session_kind"]]


def labels_rare(meta):
    """~5% prevalence: 'case' iff attr_class == 'cls_5' AND close_state == 'state_a'."""
    return ["case" if (c == "cls_5" and s == "state_a") else "control"
            for c, s in zip(meta["attr_class"], meta["close_state"])]


# ---------------------------------------------------------------- split ----

def site_split(site_raw):
    """Deterministic BY-SITE partition. Records never cross a split boundary."""
    uniq = sorted(set(site_raw))
    rng = np.random.default_rng(SPLIT_RNG_SEED)
    perm = rng.permutation(len(uniq))
    shuffled = [uniq[i] for i in perm]
    target_sites = set(shuffled[:N_TARGET_SITES])
    rest = shuffled[N_TARGET_SITES:]
    n_rest = len(rest)
    n_tr = int(n_rest * 0.40)
    n_aux = int(n_rest * 0.20)
    train_sites = set(rest[:n_tr])
    aux_sites = set(rest[n_tr:n_tr + n_aux])
    cal_sites = set(rest[n_tr + n_aux:])
    assert not (train_sites & aux_sites & cal_sites)
    assert len(train_sites | aux_sites | cal_sites | target_sites) == len(uniq)
    idx = {k: [] for k in ("train", "aux", "cal", "target")}
    for i, s in enumerate(site_raw):
        if s in target_sites:
            idx["target"].append(i)
        elif s in train_sites:
            idx["train"].append(i)
        elif s in aux_sites:
            idx["aux"].append(i)
        else:
            idx["cal"].append(i)
    sets = dict(train=train_sites, aux=aux_sites, cal=cal_sites,
                target=target_sites)
    return {k: np.asarray(v, dtype=int) for k, v in idx.items()}, sets
