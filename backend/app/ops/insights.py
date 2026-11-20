"""Auswertungen fuer den Betreiber (rein funktional): Spiele je Tag, Spitzenzeiten, Spieldauer, Abbruchquote.

Eingabe sind anonyme Zaehlereignisse (``{"at": Unix-Zeit, "duration": Sekunden|None, "humans": Zahl}``) und die
Tisch-Statistik aus ``community.stats``. Tageszeiten werden in deutscher Zeit (MEZ/MESZ) ausgewiesen; die Umstellung
wird selbst berechnet, damit weder ``tzdata`` noch ``zoneinfo`` im Container noetig sind.
"""
from __future__ import annotations

import statistics
from datetime import datetime, timedelta, timezone

DAY = 86400
WEEKDAYS = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")
MAX_GAME_SECONDS = 2 * 3600       # laenger gilt ein Spiel als unterbrochen (Pause) und zaehlt nicht in die Dauer
ENDED_AFTER = 3600                # Tisch ohne Aktion seit einer Stunde gilt als beendet (Basis der Abbruchquote)


def _last_sunday(year: int, month: int) -> datetime:
    day = datetime(year, month, 31 if month in (3, 10) else 30, 1, 0, tzinfo=timezone.utc)
    return day - timedelta(days=(day.weekday() + 1) % 7)


def berlin_offset_hours(epoch: float) -> int:
    """1 (MEZ) oder 2 (MESZ): Sommerzeit von letztem Maisonntag-Maerz 01:00 UTC bis letztem Sonntag im Oktober 01:00 UTC."""
    moment = datetime.fromtimestamp(epoch, timezone.utc)
    start, end = _last_sunday(moment.year, 3), _last_sunday(moment.year, 10)
    return 2 if start <= moment < end else 1


def berlin(epoch: float) -> datetime:
    return datetime.fromtimestamp(epoch, timezone.utc).replace(tzinfo=None) + timedelta(hours=berlin_offset_hours(epoch))


def _minutes(values: list[float]) -> dict:
    if not values:
        return {"count": 0, "avg": 0.0, "median": 0.0, "p90": 0.0}
    ordered = sorted(values)
    p90 = ordered[min(len(ordered) - 1, int(len(ordered) * 0.9))]
    return {"count": len(values), "avg": round(sum(values) / len(values) / 60, 1),
            "median": round(statistics.median(values) / 60, 1), "p90": round(p90 / 60, 1)}


def summarize_insights(events: list[dict], logs: list[dict], now: float, days: int = 30) -> dict:
    recent = [e for e in events if now - e["at"] <= days * DAY]
    today = berlin(now).date()
    per_day = {(today - timedelta(days=back)).isoformat(): 0 for back in range(days - 1, -1, -1)}
    by_hour, by_weekday = [0] * 24, [0] * 7
    for e in recent:
        local = berlin(e["at"])
        key = local.date().isoformat()
        if key in per_day:
            per_day[key] += 1
        by_hour[local.hour] += 1
        by_weekday[local.weekday()] += 1
    peak_hour = max(range(24), key=lambda h: (by_hour[h], -h)) if any(by_hour) else None
    peak_day = max(range(7), key=lambda d: (by_weekday[d], -d)) if any(by_weekday) else None
    durations = [e["duration"] for e in recent if e.get("duration") and 0 < e["duration"] <= MAX_GAME_SECONDS]
    together = [e["duration"] for e in recent
                if e.get("duration") and 0 < e["duration"] <= MAX_GAME_SECONDS and e.get("humans", 0) >= 2]
    ended = [l for l in logs if l.get("startedAt") and now - l["lastActivityAt"] >= ENDED_AFTER]
    never_finished = sum(1 for l in ended if l["games"] == 0)
    rounds = sum(l["rounds"] for l in ended)
    finished_rounds = sum(min(l.get("roundsFinished", 0), l["rounds"]) for l in ended)
    return {
        "days": days,
        "gamesInPeriod": len(recent),
        "gamesTotal": len(events),
        "since": min((e["at"] for e in events), default=None),
        "perDay": [{"date": d, "games": n} for d, n in per_day.items()],
        "byHour": by_hour,
        "byWeekday": [{"label": WEEKDAYS[i], "games": n} for i, n in enumerate(by_weekday)],
        "peak": {"hour": peak_hour, "weekday": None if peak_day is None else WEEKDAYS[peak_day]},
        "duration": _minutes(durations),
        "durationWithHumans": _minutes(together),
        "abort": {
            "tablesEnded": len(ended),
            "neverFinishedAGame": never_finished,
            "neverFinishedRate": round(never_finished / len(ended), 3) if ended else None,
            "rounds": rounds,
            "roundsAborted": max(0, rounds - finished_rounds),
            "roundsAbortedRate": round(max(0, rounds - finished_rounds) / rounds, 3) if rounds else None,
        },
    }
