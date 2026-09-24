"""CSV adapter preserves sessions, missingness and source provenance."""
import csv
import hashlib
from collections import Counter
from pathlib import Path
from .schema import CHANNELS, Record, sanitize, timestamp

def read_session(path: Path, engine="public-example-unknown-engine"):
    rows, issues = [], Counter()
    previous = None
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)):
            raise ValueError("Duplicate CSV headers")
        required = {"Timestamp"} | {c[1] for c in CHANNELS}
        if not required <= set(headers):
            raise ValueError(f"Missing or unsupported units/headers: {sorted(required-set(headers))}")
        for line, row in enumerate(reader, 2):
            try:
                dt = timestamp(row["Timestamp"], csv_utc=True)
            except (ValueError, TypeError):
                issues["invalid_timestamp_rows"] += 1
                continue
            if previous is not None and dt <= previous:
                issues["duplicate_or_reversed_rows"] += 1
                continue
            if previous is not None and (dt-previous).total_seconds() > 1.5:
                issues["gaps"] += 1
            previous = dt
            values = {}
            for _, header, name, unit, _, _ in CHANNELS:
                raw = row.get(header)
                try:
                    val = float(raw)
                    val *= 100 if "[hPa]" in header else 100000 if "[bar]" in header else 1
                except (ValueError, TypeError):
                    val = raw
                values[name] = val
            values, quality = sanitize(values)
            issues.update(q for q in quality.values() if q != "valid")
            rows.append(Record(dt, Path(path).stem, engine, values, quality))
    return rows, {"file": Path(path).name, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                  "rows": len(rows), "issues": dict(issues)}

def load_directory(path: Path):
    sessions, audits = [], []
    for file in sorted(Path(path).glob("*.csv")):
        records, audit = read_session(file)
        if records:
            sessions.append(records)
        audits.append(audit)
    if not sessions:
        raise ValueError("No usable CSV sessions")
    return sessions, audits

def split_sessions(sessions):
    """Merge overlapping time intervals BEFORE chronological group splitting.

    Prevents overlapping ECU recordings/copies from leaking across train/test.
    Conservative: all engines on the same day also stay in a single group.
    """
    groups = []
    for session in sorted(sessions, key=lambda s: s[0].time):
        start, end = session[0].time.date(), session[-1].time.date()
        if groups and start <= groups[-1]["end"]:
            groups[-1]["sessions"].append(session)
            groups[-1]["end"] = max(end, groups[-1]["end"])
        else:
            groups.append({"start": start, "end": end, "sessions": [session]})
    if len(groups) < 3:
        raise ValueError("Need >=3 disjoint day/overlap groups for train/calibration/test")
    n_train = max(1, min(len(groups)-2, int(len(groups)*.6)))
    n_cal = max(1, int(len(groups)*.2))
    sections = (groups[:n_train], groups[n_train:n_train+n_cal], groups[n_train+n_cal:])
    split = {name: [s for g in part for s in g["sessions"]]
             for name, part in zip(("train", "calibration", "test"), sections)}
    manifest = {name: [{"session": s[0].session, "start": s[0].time.isoformat(),
                        "end": s[-1].time.isoformat(), "rows": len(s)} for s in chunk]
                for name, chunk in split.items()}
    return split, manifest

