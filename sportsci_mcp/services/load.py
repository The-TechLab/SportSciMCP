from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any


def _norm_col(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def parse_session_csv(file_path: str, format_hint: str = "auto") -> dict[str, Any]:
    path = Path(file_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row")
        rows = list(reader)
    cols = {_norm_col(c): c for c in reader.fieldnames}

    def pick(*names: str) -> str | None:
        for n in names:
            if n in cols:
                return cols[n]
        return None

    date_c = pick("date", "session_date", "day")
    athlete_c = pick("athlete", "athlete_id", "player", "player_id", "name")
    srpe_c = pick("srpe", "s_rpe", "session_rpe", "rpe")
    duration_c = pick("duration", "duration_min", "minutes", "session_duration")
    distance_c = pick("distance", "distance_m", "total_distance")
    load_c = pick("load", "session_load", "training_load")

    sessions: list[dict[str, Any]] = []
    for row in rows:
        session: dict[str, Any] = {"raw": {k: row.get(v, "") for k, v in cols.items()}}
        if date_c:
            session["date"] = row.get(date_c, "")
        if athlete_c:
            session["athlete_id"] = row.get(athlete_c, "")
        if srpe_c:
            try:
                session["srpe"] = float(row.get(srpe_c) or 0)
            except ValueError:
                session["srpe"] = None
        if duration_c:
            try:
                session["duration_min"] = float(row.get(duration_c) or 0)
            except ValueError:
                session["duration_min"] = None
        if distance_c:
            try:
                session["distance"] = float(row.get(distance_c) or 0)
            except ValueError:
                session["distance"] = None
        if load_c:
            try:
                session["load"] = float(row.get(load_c) or 0)
            except ValueError:
                session["load"] = None
        elif session.get("srpe") is not None and session.get("duration_min"):
            session["load"] = session["srpe"] * session["duration_min"]
        sessions.append(session)

    athletes = sorted({s.get("athlete_id") for s in sessions if s.get("athlete_id")})
    return {
        "file": str(path),
        "format_hint": format_hint,
        "row_count": len(sessions),
        "columns_detected": list(cols.keys()),
        "athletes": athletes,
        "sessions": sessions,
    }


def calc_training_load(
    sessions: list[dict[str, Any]] | None = None,
    *,
    csv_path: str | None = None,
    acute_days: int = 7,
    chronic_days: int = 28,
) -> dict[str, Any]:
    if csv_path:
        parsed = parse_session_csv(csv_path)
        sessions = parsed["sessions"]
    if not sessions:
        raise ValueError("Provide sessions list or csv_path")

    by_athlete: dict[str, list[tuple[datetime | None, float]]] = {}
    for s in sessions:
        aid = str(s.get("athlete_id") or "default")
        load = s.get("load")
        if load is None:
            continue
        dt = None
        raw_date = s.get("date")
        if raw_date:
            for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
                try:
                    dt = datetime.strptime(str(raw_date)[:10], fmt)
                    break
                except ValueError:
                    continue
        by_athlete.setdefault(aid, []).append((dt, float(load)))

    results: dict[str, Any] = {}
    flags: list[dict[str, Any]] = []
    for athlete, points in by_athlete.items():
        loads = [p[1] for p in points]
        acute = sum(loads[-acute_days:]) / min(len(loads), acute_days) if loads else 0
        chronic = sum(loads[-chronic_days:]) / min(len(loads), chronic_days) if loads else 0
        acwr = round(acute / chronic, 2) if chronic > 0 else None
        entry = {
            "session_count": len(loads),
            "total_load": round(sum(loads), 1),
            "mean_load": round(sum(loads) / len(loads), 1) if loads else 0,
            "acute_load": round(acute, 1),
            "chronic_load": round(chronic, 1),
            "acwr": acwr,
        }
        results[athlete] = entry
        if acwr is not None and acwr > 1.5:
            flags.append(
                {
                    "athlete_id": athlete,
                    "flag": "acwr_spike",
                    "acwr": acwr,
                    "message": "ACWR > 1.5 — review training progression",
                }
            )

    return {
        "acute_days": acute_days,
        "chronic_days": chronic_days,
        "by_athlete": results,
        "flags": flags,
    }
