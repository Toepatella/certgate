#!/usr/bin/env python3
"""
Synthetic dataset generator (the hostile-extract FIXTURE — SPEC.md Tests:
`test_fixture_integration.py`; consumed via `experiments/fixture_etl.py`).

Produces a multi-table, domain-neutral relational dataset that mirrors the
*structure* of a well-known public multi-site longitudinal research corpus:
a root entity table, two high-volume irregular time-series tables, a
measurement/result table, and several sparse event-log tables, all keyed on a
single session identifier.

The point is fidelity of SHAPE, not of content. Every awkward property that
tends to break real pipelines is reproduced deliberately:

  * time is stored as SIGNED INTEGER MINUTES relative to each session's start,
    never as an absolute timestamp -- and offsets go negative for events that
    precede the session, and can exceed the session's own close offset
  * wall-clock-of-day is a VARCHAR(8) "HH:MM:SS" string, decoupled from offsets
  * one ordinal attribute is stored as TEXT with a non-numeric ceiling token
    ("> 89"), so naive int() casts blow up
  * booleans are text ("True"/"False"/"Yes"/"No"/""), inconsistently per column
  * an entire table stores numeric-looking values as VARCHAR, including junk
  * NOT NULL columns still contain empty strings
  * wide signal tables are mostly null -- each row carries a few populated
    channels out of sixteen
  * hierarchical taxonomy strings are pipe-delimited paths of varying depth
  * row counts per session are heavy-tailed (log-normal), so a handful of
    sessions carry a disproportionate share of all rows
  * sessions per SITE are heavy-tailed too (log-normal site weights,
    --site-size-sigma, default 1.1 -- the source corpus's hospital sizes span
    tens to thousands of stays; 0 restores the old uniform assignment exactly)
  * duplicate and near-duplicate rows exist (near-duplicates differ only in
    their surrogate id -- the double-charted-event pattern)
  * a small fraction of text fields embed commas, quotes and newlines

Output: one gzipped CSV per table, plus a manifest and optional SQL DDL.

Loading note: NOT NULL text columns deliberately contain empty strings, and
csv.QUOTE_MINIMAL emits an empty field UNQUOTED -- which PostgreSQL's
COPY ... (FORMAT csv) reads as NULL. Loading into the emitted DDL therefore
needs FORCE_NOT_NULL on ledger.node_value_text, flow.item_name and
tag.tag_path. That is the wart working as intended, not a bug.

Usage
-----
    python generate_synthetic_dataset.py --sessions 500 --out ./data
    python generate_synthetic_dataset.py --sessions 20000 --seed 7 --emit-ddl
    python generate_synthetic_dataset.py --sessions 100 --tables entity_session,measurement

Stdlib only. Memory is flat regardless of scale: rows stream to disk per
session rather than accumulating in lists. Every table draws from its own
(seed, table, session)-derived RNG stream, so a --tables subset run is a
byte-identical projection of the full run at the same seed, and the gzip
header carries mtime=0 so identical runs are byte-identical on disk.

--signal (default OFF)
plants a LATENT SEVERITY FACTOR: each session draws a hidden z ~ N(0,1); the
entry metrics, the attr_band ordinal and the measurement values become noisy
views of z, and close_state becomes a real outcome ('state_a' = event) drawn
from P(event) = sigmoid(SIGNAL_INTERCEPT + SIGNAL_B*z + u_site) with a
per-site random effect u_site ~ N(0, SIGNAL_U_SD^2). Prevalence lands near
10% with between-site heterogeneity -- the regime a multi-site clinical
corpus actually presents -- while every structural wart stays in place.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import gzip
import io
import json
import math
import os
import random
import sys
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# Schema definition
# --------------------------------------------------------------------------
# Column order here is the column order in the emitted CSV. Types are carried
# alongside so --emit-ddl can produce a matching CREATE TABLE.

SCHEMA: dict[str, list[tuple[str, str]]] = {
    "site": [
        ("site_id", "INT NOT NULL"),
        ("capacity_band", "VARCHAR(32)"),
        ("tier_flag", "BOOLEAN"),
        ("region", "VARCHAR(64)"),
    ],
    "entity_session": [
        ("session_id", "INT"),
        ("account_id", "INT"),
        ("attr_category", "VARCHAR(25)"),
        ("attr_band", "VARCHAR(10)"),
        ("attr_class", "VARCHAR(50)"),
        ("site_id", "INT"),
        ("zone_id", "INT"),
        ("entry_code", "VARCHAR(1000)"),
        ("entry_metric_a", "NUMERIC(10,2)"),
        ("outer_open_time24", "VARCHAR(8)"),
        ("outer_open_offset", "INT"),
        ("outer_open_source", "VARCHAR(30)"),
        ("outer_close_year", "SMALLINT"),
        ("outer_close_time24", "VARCHAR(8)"),
        ("outer_close_offset", "INT"),
        ("outer_close_target", "VARCHAR(100)"),
        ("outer_close_state", "VARCHAR(10)"),
        ("channel_type", "VARCHAR(50)"),
        ("open_time24", "VARCHAR(8)"),
        ("open_source", "VARCHAR(100)"),
        ("session_index", "INT"),
        ("session_kind", "VARCHAR(15)"),
        ("entry_metric_b", "NUMERIC(10,2)"),
        ("exit_metric_b", "NUMERIC(10,2)"),
        ("close_time24", "VARCHAR(8)"),
        ("close_offset", "INT"),
        ("close_target", "VARCHAR(100)"),
        ("close_state", "VARCHAR(10)"),
        ("subject_key", "VARCHAR(10)"),
    ],
    "signal_periodic": [
        ("record_id", "BIGINT"),
        ("session_id", "INT"),
        ("offset_min", "INT"),
        ("sig_num_1", "NUMERIC(11,4)"),
        ("sig_int_01", "INT"),
        ("sig_int_02", "INT"),
        ("sig_int_03", "INT"),
        ("sig_int_04", "INT"),
        ("sig_int_05", "INT"),
        ("sig_int_06", "INT"),
        ("sig_int_07", "INT"),
        ("sig_int_08", "INT"),
        ("sig_int_09", "INT"),
        ("sig_int_10", "INT"),
        ("sig_int_11", "INT"),
        ("sig_int_12", "INT"),
        ("sig_dbl_1", "DOUBLE PRECISION"),
        ("sig_dbl_2", "DOUBLE PRECISION"),
        ("sig_dbl_3", "DOUBLE PRECISION"),
    ],
    "signal_aperiodic": [
        ("record_id", "INT NOT NULL"),
        ("session_id", "INT NOT NULL"),
        ("offset_min", "INT NOT NULL"),
        ("ap_dbl_01", "DOUBLE PRECISION"),
        ("ap_dbl_02", "DOUBLE PRECISION"),
        ("ap_dbl_03", "DOUBLE PRECISION"),
        ("ap_dbl_04", "DOUBLE PRECISION"),
        ("ap_dbl_05", "DOUBLE PRECISION"),
        ("ap_dbl_06", "DOUBLE PRECISION"),
        ("ap_dbl_07", "DOUBLE PRECISION"),
        ("ap_dbl_08", "DOUBLE PRECISION"),
        ("ap_dbl_09", "DOUBLE PRECISION"),
        ("ap_dbl_10", "DOUBLE PRECISION"),
    ],
    "measurement": [
        ("measurement_id", "INT NOT NULL"),
        ("session_id", "INT NOT NULL"),
        ("offset_min", "INT NOT NULL"),
        ("group_id", "NUMERIC(3,0) NOT NULL"),
        ("metric_name", "VARCHAR(256)"),
        ("value_num", "NUMERIC(11,4)"),
        ("value_text", "VARCHAR(255)"),
        ("unit_canonical", "VARCHAR(255)"),
        ("unit_reported", "VARCHAR(255)"),
        ("revised_offset_min", "INT"),
    ],
    "tag": [
        ("tag_id", "INT NOT NULL"),
        ("session_id", "INT NOT NULL"),
        ("active_at_close", "VARCHAR(64)"),
        ("offset_min", "INT NOT NULL"),
        ("tag_path", "VARCHAR(200) NOT NULL"),
        ("code_ref", "VARCHAR(100)"),
        ("priority", "VARCHAR(10) NOT NULL"),
    ],
    "action": [
        ("action_id", "INT"),
        ("session_id", "INT"),
        ("offset_min", "INT"),
        ("action_path", "VARCHAR(200)"),
        ("active_at_close", "VARCHAR(10)"),
    ],
    "dispatch": [
        ("dispatch_id", "INT NOT NULL"),
        ("session_id", "INT NOT NULL"),
        ("order_offset_min", "INT NOT NULL"),
        ("start_offset_min", "INT NOT NULL"),
        ("flag_composite", "VARCHAR(6) NOT NULL"),
        ("flag_cancelled", "VARCHAR(6) NOT NULL"),
        ("item_name", "VARCHAR(220)"),
        ("item_code", "INT"),
        ("quantity", "VARCHAR(60)"),
        ("channel", "VARCHAR(120)"),
        ("cadence", "VARCHAR(255)"),
        ("flag_priming", "VARCHAR(120) NOT NULL"),
        ("flag_conditional", "VARCHAR(6) NOT NULL"),
        ("stop_offset_min", "INT NOT NULL"),
        ("group_code", "INT NOT NULL"),
    ],
    "flow": [
        ("flow_id", "INT NOT NULL"),
        ("session_id", "INT NOT NULL"),
        ("offset_min", "INT NOT NULL"),
        ("item_name", "VARCHAR(255) NOT NULL"),
        ("rate_reported", "VARCHAR(255)"),
        ("rate_normalized", "VARCHAR(255)"),
        ("amount", "VARCHAR(255)"),
        ("volume", "VARCHAR(255)"),
        ("ref_scalar", "VARCHAR(255)"),
    ],
    "ledger": [
        ("ledger_id", "INT NOT NULL"),
        ("session_id", "INT NOT NULL"),
        ("offset_min", "INT NOT NULL"),
        ("total_in", "NUMERIC(12,4)"),
        ("total_out", "NUMERIC(12,4)"),
        ("total_aux", "NUMERIC(12,4)"),
        ("total_net", "NUMERIC(12,4)"),
        ("entry_offset_min", "INT NOT NULL"),
        ("node_path", "VARCHAR(500)"),
        ("node_label", "VARCHAR(255)"),
        ("node_value_num", "NUMERIC(12,4) NOT NULL"),
        ("node_value_text", "VARCHAR(255) NOT NULL"),
    ],
}

TABLE_ORDER = list(SCHEMA.keys())

# Approximate rows-per-session for the event tables, loosely proportioned after
# the source corpus. Tune freely -- these are means of a heavy-tailed draw, not
# fixed counts. signal_periodic is NOT listed: it derives from session duration.
EVENT_RATES: dict[str, float] = {
    "signal_aperiodic": 125.0,
    "measurement": 195.0,
    "tag": 13.0,
    "action": 18.0,
    "dispatch": 36.0,
    "flow": 24.0,
    "ledger": 62.0,
}

# --------------------------------------------------------------------------
# Vocabularies -- deliberately opaque tokens, no semantics anywhere
# --------------------------------------------------------------------------

CAPACITY_BANDS = ["<100", "100 - 249", "250 - 499", ">= 500", ""]
REGIONS = ["region_n", "region_s", "region_e", "region_w", ""]
CATEGORIES = ["cat_a", "cat_b", "cat_u", ""]
CLASSES = ["cls_1", "cls_2", "cls_3", "cls_4", "cls_5", "cls_other", ""]
CHANNEL_TYPES = ["chan_alpha", "chan_beta", "chan_gamma", "chan_delta", "chan_epsilon"]
SESSION_KINDS = ["kind_admit", "kind_readmit", "kind_transfer", "kind_stepdown"]
SOURCES = ["src_01", "src_02", "src_03", "src_04", "src_05", "src_direct", ""]
TARGETS = ["dst_01", "dst_02", "dst_03", "dst_04", "dst_home", "dst_other", ""]
STATES = ["state_a", "state_b", ""]
PRIORITIES = ["primary", "major", "other"]
UNITS_CANONICAL = ["u/l", "mg/dl", "%", "ratio", "count/uL", "index", ""]
# The per-column boolean inconsistency the docstring promises: tag,
# dispatch.flag_composite/flag_priming and site.tier_flag speak True/False;
# action and dispatch.flag_cancelled/flag_conditional speak Yes/No.
BOOL_TF = ["True", "False"]
BOOL_YN = ["Yes", "No"]

# Pipe-delimited taxonomy roots, mirroring the source corpus's hierarchical
# path strings. Depth varies from 2 to 5 segments.
TAXONOMY_ROOTS = ["grp_a", "grp_b", "grp_c", "grp_d", "grp_e", "grp_f"]

# --signal mode: latent-severity outcome model (see module docstring).
# Intercept chosen so E[P(event)] over z and u_site lands near 10%.
SIGNAL_INTERCEPT = -3.7
SIGNAL_B = 2.0            # log-odds per unit latent severity z
SIGNAL_U_SD = 0.5         # per-site random effect sd on the log-odds
# Feature loadings: how strongly each observable leaks the latent z.
SIGNAL_LOAD = {
    "entry_metric_a": -6.0,   # on top of gauss(170, 12)
    "entry_metric_b": 16.0,   # on top of gauss(85, 26)
    "exit_metric_b": 10.0,    # on top of gauss(87, 27)
    "attr_band": 7.0,         # on top of gauss(64, 17), clamps/traps intact
    "measurement_mu": 0.45,   # on the lognormal's log-mean (2.0, sigma 1.0)
}

# A fraction of text values are deliberately hostile to CSV parsers.
NASTY_TEXT = [
    'value, with comma',
    'value "with quotes"',
    "value 'single'",
    "value\nwith newline",
    "  leading and trailing  ",
    "",
]


@dataclass
class Config:
    sessions: int = 500
    seed: int = 20260725
    out: str = "./data"
    sites: int = 0            # 0 -> derived from session count
    compresslevel: int = 6
    rate_scale: float = 1.0   # global multiplier on EVENT_RATES
    sample_interval: int = 5  # minutes between signal_periodic rows
    dirty: float = 0.02       # fraction of text fields that get hostile values
    dup_rate: float = 0.001   # fraction of event rows emitted twice
    tables: list[str] = field(default_factory=lambda: list(TABLE_ORDER))
    emit_ddl: bool = False
    signal: bool = False      # plant a latent-severity outcome (docstring)
    site_sigma: float = 1.1   # lognormal sd of site weights; 0 = uniform (old)


# --------------------------------------------------------------------------
# Value helpers
# --------------------------------------------------------------------------

def num(value, dp: int):
    """Fixed-point render; None becomes an empty field (a NULL in CSV terms)."""
    if value is None:
        return ""
    return f"{value:.{dp}f}"


def integer(value):
    return "" if value is None else str(int(value))


def maybe(rng: random.Random, p_present: float, producer):
    """Return producer() with probability p_present, else None."""
    return producer() if rng.random() < p_present else None


def hhmmss(rng: random.Random) -> str:
    """Wall-clock-of-day as text, intentionally unlinked from the offsets."""
    return f"{rng.randrange(24):02d}:{rng.randrange(60):02d}:{rng.randrange(60):02d}"


def ordinal_band(rng: random.Random, shift: float = 0.0) -> str:
    """
    Ordinal attribute stored as TEXT. Roughly 6% of rows carry the ceiling
    token '> 89' and ~1% are blank, so int(row['attr_band']) raises on real
    data. This is the single most common parsing trap in the source corpus.
    ``shift`` moves the numeric branch's mean (used by --signal); 0.0 leaves
    the draw byte-identical to the unshifted form.
    """
    r = rng.random()
    if r < 0.01:
        return ""
    if r < 0.07:
        return "> 89"
    return str(int(min(89, max(16, rng.gauss(64 + shift, 17)))))


def taxonomy_path(rng: random.Random, min_depth: int = 2, max_depth: int = 5) -> str:
    depth = rng.randint(min_depth, max_depth)
    segs = [rng.choice(TAXONOMY_ROOTS)]
    for level in range(1, depth):
        segs.append(f"n{level}_{rng.randrange(1, 40)}")
    return "|".join(segs)


def dirty_text(rng: random.Random, clean: str, cfg: Config) -> str:
    """Occasionally swap in a value engineered to break a naive CSV reader."""
    if rng.random() < cfg.dirty:
        return rng.choice(NASTY_TEXT)
    return clean


def numeric_looking_text(rng: random.Random) -> str:
    """
    The `flow` table stores every numeric-looking value as free text, and the
    real column contents are a mess: plain numbers, numbers with units,
    ranges, comparators, and outright junk. Reproduced faithfully.
    """
    r = rng.random()
    if r < 0.55:
        return f"{rng.uniform(0, 500):.2f}"
    if r < 0.70:
        return str(rng.randrange(0, 1000))
    if r < 0.78:
        return f"{rng.uniform(0, 50):.1f} q/hr"
    if r < 0.84:
        return f"<{rng.randrange(1, 10)}"
    if r < 0.89:
        return f"{rng.randrange(1, 20)}-{rng.randrange(20, 60)}"
    if r < 0.93:
        return "OFF"
    if r < 0.96:
        return "N/A"
    if r < 0.98:
        return ""
    return "  "


def heavy_tail_count(rng: random.Random, mean: float) -> int:
    """
    Log-normal draw with the requested arithmetic mean. Produces the long right
    tail the source corpus has -- most sessions are small, a few are enormous.
    """
    if mean <= 0:
        return 0
    sigma = 1.1
    mu = math.log(mean) - (sigma ** 2) / 2.0
    return max(0, int(rng.lognormvariate(mu, sigma)))


# --------------------------------------------------------------------------
# Writer
# --------------------------------------------------------------------------

class TableWriter:
    """Streaming gzip CSV writer for one table. Counts rows as it goes."""

    def __init__(self, path: str, columns: list[str], compresslevel: int):
        self.path = path
        self.columns = columns
        self.rows = 0
        # mtime=0 and no embedded filename: the gzip HEADER is constant, so
        # "same seed + same args = byte-identical output" holds for the .gz
        # files themselves, not just their decompressed content. (gzip.open
        # stamps wall-clock mtime into header bytes 4:8, which silently broke
        # byte-level reproducibility checks.)
        self._raw = open(path, "wb")
        gz = gzip.GzipFile(filename="", mode="wb", fileobj=self._raw,
                           compresslevel=compresslevel, mtime=0)
        self._fh = io.TextIOWrapper(gz, encoding="utf-8", newline="")
        self._w = csv.writer(self._fh, quoting=csv.QUOTE_MINIMAL)
        self._w.writerow(columns)

    def write(self, row: list) -> None:
        self._w.writerow(row)
        self.rows += 1

    def close(self) -> None:
        self._fh.close()      # flushes TextIOWrapper and closes the GzipFile
        self._raw.close()     # GzipFile(fileobj=...) never closes the fileobj


class NullWriter:
    """Stands in for a table the caller excluded via --tables."""

    rows = 0

    def write(self, row) -> None:  # noqa: D102
        pass

    def close(self) -> None:  # noqa: D102
        pass


# --------------------------------------------------------------------------
# Per-table row builders
# --------------------------------------------------------------------------

def build_sites(rng: random.Random, n_sites: int):
    for site_id in range(1, n_sites + 1):
        yield [
            site_id,
            rng.choice(CAPACITY_BANDS),
            rng.choice(BOOL_TF) if rng.random() < 0.95 else "",
            rng.choice(REGIONS),
        ]


_CLOSE_STATE_IDX = [c for c, _ in SCHEMA["entity_session"]].index("close_state")


def build_session_row(rng: random.Random, cfg: Config, s: dict) -> list:
    duration = s["duration"]
    sig = s.get("signal")
    z = sig["z"] if sig else 0.0          # z == 0.0 -> draws byte-identical
    open_offset = -rng.randrange(0, 4 * 24 * 60)          # negative by design
    close_offset = duration + rng.randrange(0, 6 * 24 * 60)
    row = [
        s["session_id"],
        s["account_id"],
        rng.choice(CATEGORIES),
        ordinal_band(rng, SIGNAL_LOAD["attr_band"] * z),
        rng.choice(CLASSES),
        s["site_id"],
        s["zone_id"],
        dirty_text(rng, taxonomy_path(rng, 2, 4), cfg),
        num(maybe(rng, 0.88, lambda: rng.gauss(
            170 + SIGNAL_LOAD["entry_metric_a"] * z, 12)), 2),
        hhmmss(rng),
        open_offset,
        rng.choice(SOURCES),
        rng.choice([2014, 2015]),
        hhmmss(rng),
        close_offset,
        rng.choice(TARGETS),
        rng.choice(STATES),
        s["channel_type"],
        hhmmss(rng),
        rng.choice(SOURCES),
        s["session_index"],
        rng.choice(SESSION_KINDS),
        num(maybe(rng, 0.92, lambda: max(30.0, rng.gauss(
            85 + SIGNAL_LOAD["entry_metric_b"] * z, 26))), 2),
        num(maybe(rng, 0.35, lambda: max(30.0, rng.gauss(
            87 + SIGNAL_LOAD["exit_metric_b"] * z, 27))), 2),
        hhmmss(rng),
        duration,
        rng.choice(TARGETS),
        rng.choice(STATES),
        s["subject_key"],
    ]
    if sig is not None:
        # close_state becomes the OUTCOME: 'state_a' = event. The random
        # draw above is kept so the rng stream is position-identical; only
        # the emitted value is overridden.
        row[_CLOSE_STATE_IDX] = "state_a" if sig["y"] else "state_b"
    return row


def build_signal_periodic(rng: random.Random, cfg: Config, s: dict, next_id):
    """
    Regularly sampled wide table: one row per sample_interval minutes, but each
    row populates only a few of its sixteen channels. This is where most of the
    volume lives -- and where sparse-wide handling gets tested.
    """
    duration = s["duration"]
    n = max(1, duration // cfg.sample_interval)
    # Each session subscribes to a stable subset of channels.
    n_active = rng.randint(2, 7)
    active = set(rng.sample(range(16), n_active))
    baselines = {i: rng.uniform(20, 140) for i in active}

    offset = rng.randrange(0, cfg.sample_interval)
    for _ in range(n):
        vals: list = [None] * 16
        for i in active:
            if rng.random() < 0.90:            # gaps even in active channels
                baselines[i] += rng.gauss(0, 1.5)
                vals[i] = baselines[i]
        row = [
            next_id(),
            s["session_id"],
            offset,
            num(vals[0], 4),
        ]
        row += [integer(None if vals[i] is None else round(vals[i])) for i in range(1, 13)]
        row += [
            "" if vals[i] is None else repr(round(vals[i], 6))
            for i in range(13, 16)
        ]
        yield row
        offset += cfg.sample_interval


def build_signal_aperiodic(rng: random.Random, cfg: Config, s: dict, count, next_id):
    for _ in range(count):
        vals = [
            maybe(rng, 0.30, lambda: rng.uniform(0.5, 200.0))
            for _ in range(10)
        ]
        yield [
            next_id(),
            s["session_id"],
            event_offset(rng, s),
        ] + ["" if v is None else f"{v:.6f}" for v in vals]


def build_measurement(rng: random.Random, cfg: Config, s: dict, count, next_id):
    sig = s.get("signal")
    mu = 2.0 + (SIGNAL_LOAD["measurement_mu"] * sig["z"] if sig else 0.0)
    for _ in range(count):
        offset = event_offset(rng, s)
        numeric = rng.random() < 0.82
        value = rng.lognormvariate(mu, 1.0) if numeric else None
        yield [
            next_id(),
            s["session_id"],
            offset,
            rng.randrange(1, 8),
            dirty_text(rng, f"metric_{rng.randrange(1, 160):03d}", cfg),
            num(value, 4),
            "" if numeric else rng.choice(["low", "high", "indeterminate", "-", ""]),
            rng.choice(UNITS_CANONICAL),
            rng.choice(UNITS_CANONICAL),
            integer(maybe(rng, 0.15, lambda: offset + rng.randrange(1, 600))),
        ]


def build_tag(rng: random.Random, cfg: Config, s: dict, count, next_id):
    for _ in range(count):
        yield [
            next_id(),
            s["session_id"],
            rng.choice(BOOL_TF),
            event_offset(rng, s),
            dirty_text(rng, taxonomy_path(rng, 3, 5), cfg),
            f"{rng.randrange(100, 999)}.{rng.randrange(0, 99):02d}" if rng.random() < 0.8 else "",
            rng.choice(PRIORITIES),
        ]


def build_action(rng: random.Random, cfg: Config, s: dict, count, next_id):
    for _ in range(count):
        yield [
            next_id(),
            s["session_id"],
            event_offset(rng, s),
            dirty_text(rng, taxonomy_path(rng, 3, 5), cfg),
            rng.choice(BOOL_YN),          # Yes/No here, True/False in `tag`
        ]


def build_dispatch(rng: random.Random, cfg: Config, s: dict, count, next_id):
    for _ in range(count):
        order_off = event_offset(rng, s)
        start_off = order_off + rng.randrange(0, 240)
        yield [
            next_id(),
            s["session_id"],
            order_off,
            start_off,
            rng.choice(BOOL_TF),          # flag_composite: True/False
            rng.choice(BOOL_YN),          # flag_cancelled: Yes/No
            dirty_text(rng, f"item_{rng.randrange(1, 900):04d}", cfg),
            integer(maybe(rng, 0.85, lambda: rng.randrange(1000, 40000))),
            f"{rng.randrange(1, 500)} unit" if rng.random() < 0.9 else "",
            rng.choice(["ch_01", "ch_02", "ch_03", "ch_04", ""]),
            rng.choice(["once", "q6", "q8", "q12", "daily", "prn", ""]),
            rng.choice(BOOL_TF),          # flag_priming: True/False
            rng.choice(BOOL_YN),          # flag_conditional: Yes/No
            start_off + rng.randrange(60, 20000),
            rng.randrange(0, 90),
        ]


def build_flow(rng: random.Random, cfg: Config, s: dict, count, next_id):
    """Every value column is VARCHAR here, junk included. Deliberate."""
    for _ in range(count):
        yield [
            next_id(),
            s["session_id"],
            event_offset(rng, s),
            dirty_text(rng, f"item_{rng.randrange(1, 300):04d}", cfg),
            numeric_looking_text(rng),
            numeric_looking_text(rng),
            numeric_looking_text(rng),
            numeric_looking_text(rng),
            numeric_looking_text(rng),
        ]


def build_ledger(rng: random.Random, cfg: Config, s: dict, count, next_id):
    for _ in range(count):
        offset = event_offset(rng, s)
        t_in = rng.uniform(0, 4000)
        t_out = rng.uniform(0, 4000)
        t_aux = rng.uniform(0, 500) if rng.random() < 0.1 else 0.0
        yield [
            next_id(),
            s["session_id"],
            offset,
            num(t_in, 4),
            num(t_out, 4),
            num(t_aux, 4),
            num(t_in - t_out - t_aux, 4),
            offset - rng.randrange(0, 120),
            dirty_text(rng, taxonomy_path(rng, 3, 5), cfg),
            f"label_{rng.randrange(1, 200):03d}",
            num(rng.uniform(0, 1500), 4),
            # NOT NULL, yet frequently empty -- exactly as in the source
            "" if rng.random() < 0.7 else f"note_{rng.randrange(1, 50)}",
        ]


def event_offset(rng: random.Random, s: dict) -> int:
    """
    Event time in signed minutes from session start. ~4% land before the
    session opens and ~2% after it closes, which is what the real corpus does
    and what naive `0 <= offset <= duration` filters silently drop.
    """
    r = rng.random()
    if r < 0.04:
        return -rng.randrange(1, 3000)
    if r < 0.06:
        return s["duration"] + rng.randrange(1, 2000)
    return rng.randrange(0, max(1, s["duration"]))


BUILDERS = {
    "signal_aperiodic": build_signal_aperiodic,
    "measurement": build_measurement,
    "tag": build_tag,
    "action": build_action,
    "dispatch": build_dispatch,
    "flow": build_flow,
    "ledger": build_ledger,
}


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------

def plan_sessions(rng: random.Random, cfg: Config, n_sites: int):
    """
    Build the entity hierarchy: subject -> account -> session.

    Mirrors the source corpus's three-level identity structure, where roughly
    1.44 sessions exist per subject. Yields session dicts lazily so memory
    stays flat at any scale.
    """
    session_id = 141_168      # ids start in a plausible band, not at 1
    account_id = 210_000
    subject_ordinal = 0
    emitted = 0

    # Heavy-tailed site sizes (--site-size-sigma > 0): each site gets a
    # lognormal weight from a DEDICATED stream, and subjects pick a site with
    # probability proportional to it -- hospital totals then span tens to
    # thousands of sessions, like the source corpus. sigma == 0 keeps the old
    # uniform randint path byte-for-byte.
    site_cum, site_tot = None, 0.0
    if cfg.site_sigma > 0:
        wrng = random.Random(f"{cfg.seed}:site-weights")
        site_cum = []
        for _ in range(n_sites):
            site_tot += wrng.lognormvariate(0.0, cfg.site_sigma)
            site_cum.append(site_tot)

    while emitted < cfg.sessions:
        subject_ordinal += 1
        # Derived from the ordinal, not random, so subjects never collide.
        subject_key = f"{(subject_ordinal // 100000) % 1000:03d}-{subject_ordinal % 100000}"
        if site_cum is not None:
            site_id = bisect.bisect_left(site_cum, rng.random() * site_tot) + 1
        else:
            site_id = rng.randint(1, n_sites)

        n_accounts = 1 if rng.random() < 0.90 else 2
        for _ in range(n_accounts):
            account_id += rng.randrange(1, 40)
            # Most accounts hold one session; a tail hold several.
            n_sessions = 1
            r = rng.random()
            if r > 0.78:
                n_sessions = 2
            if r > 0.95:
                n_sessions = rng.randint(3, 6)

            for idx in range(1, n_sessions + 1):
                if emitted >= cfg.sessions:
                    return
                session_id += rng.randrange(1, 30)
                # Duration is log-normal: median ~1.6 days, long right tail.
                duration = max(10, int(rng.lognormvariate(math.log(2300), 0.95)))
                sig = None
                if cfg.signal:
                    # Dedicated streams: the latent draw never perturbs the
                    # plan stream, so --signal changes VALUES, not structure
                    # (same sessions, sites, durations as the unsignalled run).
                    srng = random.Random(f"{cfg.seed}:signal:{session_id}")
                    u_c = random.Random(
                        f"{cfg.seed}:signal-site:{site_id}").gauss(0.0, SIGNAL_U_SD)
                    z = srng.gauss(0.0, 1.0)
                    logit_p = SIGNAL_INTERCEPT + SIGNAL_B * z + u_c
                    p = 1.0 / (1.0 + math.exp(-logit_p))
                    sig = {"z": z, "y": srng.random() < p}
                yield {
                    "session_id": session_id,
                    "account_id": account_id,
                    "subject_key": subject_key,
                    "site_id": site_id,
                    "zone_id": site_id * 100 + rng.randrange(1, 9),
                    "session_index": idx,
                    "channel_type": rng.choice(CHANNEL_TYPES),
                    "duration": duration,
                    "signal": sig,
                }
                emitted += 1


def make_counter(start: int = 1):
    box = [start]

    def nxt() -> int:
        v = box[0]
        box[0] += 1
        return v

    return nxt


def table_rng(seed: int, table: str, session_id) -> random.Random:
    """Deterministic, INDEPENDENT stream per (table, session).

    Every table's per-session content is a function of (seed, table,
    session_id) alone, so excluding tables via --tables can no longer shift
    any other table's draws: a subset run is a byte-identical projection of
    the full run at the same seed. (Previously one shared stream meant a
    --tables run produced entirely different data than the full run.)
    """
    return random.Random(f"{seed}:{table}:{session_id}")


def generate(cfg: Config) -> dict:
    # Separate streams for the plan and the site table; per-(table, session)
    # streams for everything else (see table_rng) -- the plan always runs in
    # full, so which tables are selected can never change what the plan draws.
    rng_plan = random.Random(f"{cfg.seed}:plan")
    os.makedirs(cfg.out, exist_ok=True)

    n_sites = cfg.sites or max(3, min(208, cfg.sessions // 400 + 3))

    writers: dict[str, TableWriter | NullWriter] = {}
    for name, cols in SCHEMA.items():
        if name in cfg.tables:
            writers[name] = TableWriter(
                os.path.join(cfg.out, f"{name}.csv.gz"),
                [c for c, _ in cols],
                cfg.compresslevel,
            )
        else:
            writers[name] = NullWriter()

    counters = {name: make_counter(1) for name in SCHEMA}

    try:
        for row in build_sites(random.Random(f"{cfg.seed}:site"), n_sites):
            writers["site"].write(row)

        done = 0
        for s in plan_sessions(rng_plan, cfg, n_sites):
            sid = s["session_id"]
            writers["entity_session"].write(build_session_row(
                table_rng(cfg.seed, "entity_session", sid), cfg, s))

            if isinstance(writers["signal_periodic"], TableWriter):
                for row in build_signal_periodic(
                    table_rng(cfg.seed, "signal_periodic", sid),
                    cfg, s, counters["signal_periodic"]
                ):
                    writers["signal_periodic"].write(row)

            for name, rate in EVENT_RATES.items():
                w = writers[name]
                if not isinstance(w, TableWriter):
                    continue
                rt = table_rng(cfg.seed, name, sid)
                count = heavy_tail_count(rt, rate * cfg.rate_scale)
                for row in BUILDERS[name](rt, cfg, s, count, counters[name]):
                    w.write(row)
                    r_dup = rt.random()
                    if r_dup < cfg.dup_rate / 2.0:
                        w.write(row)                  # exact duplicate, id too
                    elif r_dup < cfg.dup_rate:
                        # near-duplicate: same content, fresh surrogate id --
                        # the double-charted-event pattern real corpora have
                        w.write([counters[name]()] + row[1:])

            done += 1
            if done % 250 == 0:
                print(f"  ... {done}/{cfg.sessions} sessions", file=sys.stderr)
    finally:
        for w in writers.values():
            w.close()

    manifest = {
        "seed": cfg.seed,
        "sessions_requested": cfg.sessions,
        "sites": n_sites,
        "site_size_sigma": cfg.site_sigma,
        "sample_interval_min": cfg.sample_interval,
        "rate_scale": cfg.rate_scale,
        "row_counts": {
            name: w.rows for name, w in writers.items() if isinstance(w, TableWriter)
        },
    }
    with open(os.path.join(cfg.out, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)

    if cfg.emit_ddl:
        with open(os.path.join(cfg.out, "schema.sql"), "w") as fh:
            for name, cols in SCHEMA.items():
                fh.write(f"DROP TABLE IF EXISTS {name} CASCADE;\n")
                fh.write(f"CREATE TABLE {name}\n(\n")
                body = ",\n".join(f"    {c} {t}" for c, t in cols)
                fh.write(body + "\n);\n\n")

    return manifest


def parse_args(argv=None) -> Config:
    p = argparse.ArgumentParser(
        description="Generate a synthetic multi-table dataset with realistic structural warts."
    )
    p.add_argument("--sessions", type=int, default=500,
                   help="number of rows in entity_session (default 500)")
    p.add_argument("--seed", type=int, default=20260725,
                   help="RNG seed; same seed + same args = byte-identical output")
    p.add_argument("--out", default="./data", help="output directory")
    p.add_argument("--sites", type=int, default=0,
                   help="number of sites; 0 derives one from --sessions")
    p.add_argument("--compresslevel", type=int, default=6, choices=range(0, 10))
    p.add_argument("--rate-scale", type=float, default=1.0,
                   help="multiplier on event rows per session (0.1 for a fast smoke test)")
    p.add_argument("--sample-interval", type=int, default=5,
                   help="minutes between signal_periodic samples")
    p.add_argument("--dirty", type=float, default=0.02,
                   help="fraction of text fields given parser-hostile values")
    p.add_argument("--dup-rate", type=float, default=0.001,
                   help="fraction of event rows duplicated (half exact copies "
                        "including the id, half near-duplicates that differ "
                        "only in their surrogate id)")
    p.add_argument("--tables", default="",
                   help="comma-separated subset of tables to emit (default: "
                        "all); selected tables are byte-identical to the same "
                        "tables of a full run at the same seed")
    p.add_argument("--emit-ddl", action="store_true",
                   help="also write schema.sql")
    p.add_argument("--site-size-sigma", type=float, default=1.1,
                   help="lognormal sd of per-site weights: session counts per "
                        "site become heavy-tailed like the source corpus's "
                        "hospital sizes (default 1.1); 0 restores the old "
                        "uniform site assignment exactly")
    p.add_argument("--signal", action="store_true",
                   help="plant a latent-severity outcome: close_state becomes "
                        "a real event driven by a hidden z that also shifts "
                        "entry metrics, attr_band and measurement values "
                        "(~10%% prevalence, per-site random effects); OFF by "
                        "default and structure-preserving (same sessions, "
                        "sites and durations as an unsignalled run)")
    a = p.parse_args(argv)

    tables = [t.strip() for t in a.tables.split(",") if t.strip()] or list(TABLE_ORDER)
    unknown = set(tables) - set(TABLE_ORDER)
    if unknown:
        p.error(f"unknown table(s): {', '.join(sorted(unknown))}. "
                f"Valid: {', '.join(TABLE_ORDER)}")

    return Config(
        sessions=a.sessions,
        seed=a.seed,
        out=a.out,
        sites=a.sites,
        compresslevel=a.compresslevel,
        rate_scale=a.rate_scale,
        sample_interval=a.sample_interval,
        dirty=a.dirty,
        dup_rate=a.dup_rate,
        tables=tables,
        emit_ddl=a.emit_ddl,
        signal=a.signal,
        site_sigma=a.site_size_sigma,
    )


def main(argv=None) -> int:
    cfg = parse_args(argv)
    print(f"Generating {cfg.sessions} sessions into {cfg.out} (seed={cfg.seed})",
          file=sys.stderr)
    manifest = generate(cfg)
    print("\nRow counts:", file=sys.stderr)
    width = max(len(k) for k in manifest["row_counts"])
    for name, count in manifest["row_counts"].items():
        print(f"  {name.ljust(width)}  {count:>12,}", file=sys.stderr)
    print(f"\nWrote {cfg.out}/manifest.json", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
