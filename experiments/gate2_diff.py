"""Gate 2 of the fix pass: the re-run computed exactly what the frozen run did.

The 2026-09-04 fix pass added diagnostics to the eICU runner -- the sub-24 h
stay counts, the head's and APACHE-IVa's whole-pool scores, the per-hospital
75+ share, the coefficient rank of the top abstention driver, a sixth
subgroup dimension -- and it made every one of them APPENDED: a new column
after the frozen columns, a new key after the frozen keys, new subgroup rows
after the frozen rows of each replicate. The certified path was not meant to
move by a byte. This script is the proof rather than the promise.

It projects a fresh 20-replicate run (experiments/out-rev2/ by default) onto
the columns and keys of the frozen release run (experiments/out/), stripping
the appended material and the `_run` stamps, and requires byte-identity for
the tables and value-identity for the JSON documents. The frozen sidecars are
covered too: the five old subgroup dimensions against out-subgroups/, the
replicate-0 value-function rows against out-faithfulness/, and the preflight
document from the timing run against the released preflight on its old keys.

Any delta on an old column or key is a failure and the exit code says so. It
is not this script's job to explain such a delta away, and it never edits
anything it compares: the frozen directories are read only, and the one file
it writes -- a small JSON report carrying a `_run` stamp -- goes to the
current working directory by default (or to --report), never into a frozen
directory, and an existing report is not overwritten without --force.

Aggregate-only by construction: it reads aggregate artifacts and writes file
names, hashes and verdicts. The extract is never opened.

Run: python -m experiments.gate2_diff [--new experiments/out-rev2]
        [--old experiments/out] [--old-subgroups experiments/out-subgroups]
        [--old-faithfulness experiments/out-faithfulness]
        [--new-preflight experiments/out-timing]
        [--report GATE2-REPORT.json] [--force]

Refs: the fix-pass plan, WP3 and Verification; SPEC PIN AMENDMENT 2026-09-04.
"""

import argparse
import csv
import datetime
import hashlib
import io
import json
import os
import subprocess
import sys

from experiments.run_eicu import _write_json

EXP_DIR = os.path.dirname(os.path.abspath(__file__))
# Directories this script may read and must never write into.
FROZEN_DIRS = ("out", "out-panel", "out-sens", "out-subgroups",
               "out-faithfulness")

# The frozen run's tables that carry no appended column: bytes must match.
BYTE_IDENTICAL_CSV = ("EICU_pooled.csv", "EICU_attrition.csv",
                      "EICU_reliability.csv")
# Tables that gained appended columns: projected onto the old header first.
PROJECTED_CSV = ("EICU_comparator.csv", "EICU_per_site.csv")
# JSON documents with no appended key: whole-document value identity.
FULL_JSON = ("EICU_certificate.json", "EICU_reliability_panel.json")
# JSON documents that gained appended keys: projected onto the old key tree.
PROJECTED_JSON = ("EICU_diagnostics.json",)
# Keys that name the invocation or the wall clock rather than a computed
# quantity, as dotted paths. They are reported with both values, never
# compared, and never silently dropped either. provenance.timestamp_utc is the
# certificate's own `_run` stamp: certgate.report.provenance writes it on every
# call.
INVOCATION_KEYS = {"EICU_preflight.json": ("data_dir",),
                   "EICU_certificate.json": ("provenance.timestamp_utc",)}

_MISSING = object()


# ------------------------------------------------------------------ helpers --

def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_sha():
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True,
                              cwd=os.path.dirname(EXP_DIR)).stdout.strip()
    except Exception:                       # not a checkout, or no git
        return None


def _rel(path):
    return os.path.relpath(path, os.path.dirname(EXP_DIR)).replace(os.sep, "/")


def _run_block(paths):
    """The provenance stamp every fix-pass sidecar carries as its _run key."""
    return dict(
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat(
            timespec="seconds"),
        git_sha=_git_sha(),
        inputs={_rel(p): _sha256(p) for p in paths})


def _assert_not_frozen(path):
    """Refuse a report path that would land inside a frozen directory."""
    target = os.path.normcase(os.path.abspath(path))
    for name in FROZEN_DIRS:
        frozen = os.path.normcase(os.path.join(EXP_DIR, name))
        if target == frozen or target.startswith(frozen + os.sep):
            raise SystemExit(
                f"gate2_diff: refusing to write {path}: experiments/{name}/ is "
                f"frozen (byte-identical by gate) (reason=frozen-output-dir)")


def _read_csv(path):
    with open(path, encoding="ascii", newline="") as fh:
        rows = list(csv.reader(fh))
    return rows[0], rows[1:]


def _serialize_csv(header, rows):
    """Re-serialize the way run_eicu._write_table does, so bytes can match."""
    buf = io.StringIO(newline="")
    w = csv.writer(buf)
    w.writerow(header)
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode("ascii")


def _first_line_delta(a, b):
    la, lb = a.splitlines(), b.splitlines()
    for i, (x, y) in enumerate(zip(la, lb)):
        if x != y:
            return dict(line=i + 1, old=x.decode("ascii", "replace")[:200],
                        new=y.decode("ascii", "replace")[:200])
    if len(la) != len(lb):
        return dict(line=min(len(la), len(lb)) + 1,
                    old=f"<{len(la)} lines>", new=f"<{len(lb)} lines>")
    return None


def _load_json(path):
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    if isinstance(doc, dict):
        doc.pop("_run", None)
    return doc


def _pop_path(doc, dotted):
    """Remove and return doc[a][b]... for a dotted path; None when absent."""
    node = doc
    parts = dotted.split(".")
    for k in parts[:-1]:
        if not isinstance(node, dict) or k not in node:
            return None
        node = node[k]
    if isinstance(node, dict):
        return node.pop(parts[-1], None)
    return None


def _project(new, old):
    """new projected onto old's key tree; appended keys vanish, missing ones
    become a sentinel so the comparison names them."""
    if isinstance(old, dict):
        if not isinstance(new, dict):
            return new
        return {k: _project(new.get(k, _MISSING), v) for k, v in old.items()}
    if isinstance(old, list) and isinstance(new, list) and len(new) == len(old):
        return [_project(n, o) for n, o in zip(new, old)]
    return new


def _appended_keys(new, old, path=""):
    """Keys present in new and absent from old, anywhere in the tree."""
    found = []
    if isinstance(old, dict) and isinstance(new, dict):
        for k in new:
            if k not in old:
                found.append(f"{path}.{k}" if path else k)
            else:
                found.extend(_appended_keys(new[k], old[k],
                                            f"{path}.{k}" if path else k))
    elif (isinstance(old, list) and isinstance(new, list)
          and len(old) == len(new)):
        for i, (n, o) in enumerate(zip(new, old)):
            found.extend(_appended_keys(n, o, f"{path}[{i}]"))
    return found


def _json_deltas(a, b, path="", sink=None, cap=12):
    """First `cap` paths where a and b differ in value."""
    sink = [] if sink is None else sink
    if len(sink) >= cap:
        return sink
    if a is _MISSING or b is _MISSING:
        sink.append(dict(path=path or "<root>",
                         old=("<missing>" if a is _MISSING else repr(a)[:120]),
                         new=("<missing>" if b is _MISSING else repr(b)[:120])))
    elif isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            _json_deltas(a.get(k, _MISSING), b.get(k, _MISSING),
                         f"{path}.{k}" if path else k, sink, cap)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            _json_deltas(x, y, f"{path}[{i}]", sink, cap)
    elif a != b:
        sink.append(dict(path=path or "<root>", old=repr(a)[:120],
                         new=repr(b)[:120]))
    return sink


def _canon(doc):
    # the missing-key sentinel renders as a string no artifact carries, so a
    # key the new run dropped still compares unequal to the old value
    return json.dumps(doc, sort_keys=True, separators=(",", ":"),
                      default=lambda o: "<missing-in-new-run>")


# ------------------------------------------------------------- the checks ----

def _check_bytes(name, old_path, new_path):
    if not os.path.exists(new_path):
        return dict(artifact=name, kind="byte-identical", status="MISSING")
    a, b = open(old_path, "rb").read(), open(new_path, "rb").read()
    if a == b:
        return dict(artifact=name, kind="byte-identical", status="ok",
                    n_bytes=len(a))
    return dict(artifact=name, kind="byte-identical", status="DIFF",
                first_delta=_first_line_delta(a, b))


def _check_projected_csv(name, old_path, new_path, *, row_filter=None,
                         kind="projected-columns"):
    """Project the new table onto the old header (and optionally onto a row
    subset), then require the projection to equal the old table when both are
    re-serialized the same way -- so the line terminator on disk (CRLF on a
    Windows checkout, LF on Linux) plays no part; values, header and row order
    are what is compared."""
    if not os.path.exists(new_path):
        return dict(artifact=name, kind=kind, status="MISSING")
    old_header, old_rows = _read_csv(old_path)
    new_header, new_rows = _read_csv(new_path)
    out = dict(artifact=name, kind=kind, n_rows_old=len(old_rows),
               n_rows_new=len(new_rows))
    if new_header[:len(old_header)] != old_header:
        out.update(status="DIFF",
                   detail="the old columns do not lead the new header",
                   old_header=old_header, new_header=new_header)
        return out
    out["appended_columns"] = new_header[len(old_header):]
    idx = [new_header.index(c) for c in old_header]
    kept = [r for r in new_rows if row_filter is None
            or row_filter(dict(zip(new_header, r)))]
    out["n_rows_compared"] = len(kept)
    out["n_rows_appended"] = len(new_rows) - len(kept)
    projected = _serialize_csv(old_header, [[r[i] for i in idx] for r in kept])
    old_bytes = _serialize_csv(old_header, old_rows)
    if projected == old_bytes:
        out["status"] = "ok"
    else:
        out["status"] = "DIFF"
        out["first_delta"] = _first_line_delta(old_bytes, projected)
    return out


def _check_json(name, old_path, new_path, *, project, invocation_keys=()):
    if not os.path.exists(new_path):
        return dict(artifact=name, kind="json", status="MISSING")
    old, new = _load_json(old_path), _load_json(new_path)
    out = dict(artifact=name,
               kind=("projected-keys" if project else "full-document"))
    noted = {}
    for k in invocation_keys:
        if isinstance(old, dict) and isinstance(new, dict):
            noted[k] = dict(old=_pop_path(old, k), new=_pop_path(new, k))
    if noted:
        out["invocation_keys_not_compared"] = noted
    if project:
        out["appended_keys"] = _appended_keys(new, old)
        new = _project(new, old)
    if _canon(old) == _canon(new):
        out["status"] = "ok"
    else:
        out["status"] = "DIFF"
        out["deltas"] = _json_deltas(old, new)
    return out


def run_gate(new, old, old_subgroups, old_faithfulness, new_preflight):
    results = []
    for name in BYTE_IDENTICAL_CSV:
        results.append(_check_bytes(name, os.path.join(old, name),
                                    os.path.join(new, name)))
    for name in PROJECTED_CSV:
        results.append(_check_projected_csv(name, os.path.join(old, name),
                                            os.path.join(new, name)))
    for name in FULL_JSON:
        results.append(_check_json(name, os.path.join(old, name),
                                   os.path.join(new, name), project=False,
                                   invocation_keys=INVOCATION_KEYS.get(name,
                                                                       ())))
    for name in PROJECTED_JSON:
        results.append(_check_json(name, os.path.join(old, name),
                                   os.path.join(new, name), project=True))
    results.append(_check_json(
        "EICU_preflight.json", os.path.join(old, "EICU_preflight.json"),
        os.path.join(new_preflight, "EICU_preflight.json"), project=True,
        invocation_keys=INVOCATION_KEYS["EICU_preflight.json"]))

    # the sixth subgroup dimension is appended per replicate; the old five
    # dims, in the old order, must be the old file
    old_sub = os.path.join(old_subgroups, "EICU_subgroups.csv")
    _h, old_rows = _read_csv(old_sub)
    old_dims = {r[_h.index("dim")] for r in old_rows}
    res = _check_projected_csv(
        "EICU_subgroups.csv", old_sub, os.path.join(new, "EICU_subgroups.csv"),
        row_filter=lambda r: r["dim"] in old_dims,
        kind="projected-rows (old dims)")
    res["old_dims"] = sorted(old_dims)
    if res["status"] == "ok" and os.path.exists(
            os.path.join(new, "EICU_subgroups.csv")):
        nh, nrows = _read_csv(os.path.join(new, "EICU_subgroups.csv"))
        res["appended_dims"] = sorted(
            {r[nh.index("dim")] for r in nrows} - old_dims)
    results.append(res)

    # the value-function contrast was frozen from one replicate; the fresh
    # run's rows for that replicate must be those rows
    old_f = os.path.join(old_faithfulness, "EICU_faithfulness.csv")
    fh, frows = _read_csv(old_f)
    old_reps = {r[fh.index("replicate")] for r in frows}
    res = _check_projected_csv(
        "EICU_faithfulness.csv", old_f,
        os.path.join(new, "EICU_faithfulness.csv"),
        row_filter=lambda r: r["replicate"] in old_reps,
        kind="projected-rows (old replicates)")
    res["old_replicates"] = sorted(old_reps)
    results.append(res)
    return results


def _print_report(results):
    width = max(len(r["artifact"]) for r in results)
    for r in results:
        line = f"  {r['status']:<8}{r['artifact']:<{width + 2}}{r['kind']}"
        extras = []
        if r.get("appended_columns"):
            extras.append(f"appended columns: {r['appended_columns']}")
        if r.get("appended_dims"):
            extras.append(f"appended dims: {r['appended_dims']}")
        if r.get("appended_keys"):
            extras.append(f"{len(r['appended_keys'])} appended key path(s)")
        if r.get("n_rows_compared") is not None:
            extras.append(f"{r['n_rows_compared']} rows compared, "
                          f"{r['n_rows_appended']} appended")
        if r.get("invocation_keys_not_compared"):
            extras.append(f"not compared: {r['invocation_keys_not_compared']}")
        print(line)
        for e in extras:
            print(f"{'':10}{e}")
        if r["status"] == "DIFF":
            for k in ("first_delta", "deltas", "detail"):
                if r.get(k) is not None:
                    print(f"{'':10}{k}: {json.dumps(r[k])[:600]}")
    bad = [r["artifact"] for r in results if r["status"] != "ok"]
    print()
    if bad:
        print(f"GATE 2 FAILED: {len(bad)} artifact(s) differ on frozen "
              f"columns/keys: {bad}")
    else:
        print(f"GATE 2 PASSED: {len(results)} artifact(s) identical on every "
              f"frozen column and key")
    return not bad


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Gate 2 of the fix pass: project the fresh eICU run onto "
                    "the frozen run's columns and keys and require identity")
    ap.add_argument("--new", default=os.path.join(EXP_DIR, "out-rev2"))
    ap.add_argument("--old", default=os.path.join(EXP_DIR, "out"))
    ap.add_argument("--old-subgroups",
                    default=os.path.join(EXP_DIR, "out-subgroups"))
    ap.add_argument("--old-faithfulness",
                    default=os.path.join(EXP_DIR, "out-faithfulness"))
    ap.add_argument("--new-preflight",
                    default=os.path.join(EXP_DIR, "out-timing"))
    ap.add_argument("--report", default=None,
                    help="JSON report path (default: GATE2-REPORT.json in the "
                         "current working directory; never inside a frozen "
                         "directory; an existing file is not overwritten "
                         "without --force)")
    ap.add_argument("--force", action="store_true",
                    help="overwrite an existing report file")
    args = ap.parse_args(argv)
    report = args.report or os.path.join(os.getcwd(), "GATE2-REPORT.json")
    _assert_not_frozen(report)
    if os.path.exists(report) and not args.force:
        raise SystemExit(
            f"gate2_diff: refusing to overwrite existing {report}; pass "
            f"--force or another --report path (reason=report-exists)")

    print(f"gate 2: {_rel(args.new)} (+ {_rel(args.new_preflight)}) projected "
          f"onto {_rel(args.old)}, {_rel(args.old_subgroups)}, "
          f"{_rel(args.old_faithfulness)}")
    results = run_gate(args.new, args.old, args.old_subgroups,
                       args.old_faithfulness, args.new_preflight)
    passed = _print_report(results)

    inputs = []
    for r in results:
        for d in (args.old, args.new, args.old_subgroups,
                  args.old_faithfulness, args.new_preflight):
            p = os.path.join(d, r["artifact"])
            if os.path.exists(p) and p not in inputs:
                inputs.append(p)
    payload = {"_run": _run_block(inputs),
               "gate": "fix-pass gate 2 (2026-09-04)",
               "passed": passed,
               "new": _rel(args.new), "new_preflight": _rel(args.new_preflight),
               "old": _rel(args.old), "old_subgroups": _rel(args.old_subgroups),
               "old_faithfulness": _rel(args.old_faithfulness),
               "results": results}
    _write_json(report, payload, "GATE2-REPORT.json",
                per_item_keys=("results",))
    print(f"report -> {_rel(report)}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
