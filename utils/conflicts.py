# utils/conflicts.py
# ──────────────────────────────────────────────────────────────
#  Conflict Detection Engine
#  Priority order (per product spec):
#    1. Event Conflicts  — do the dates clash?
#    2. Player Conflicts — is a player double-booked?
#    3. Team Conflicts   — is a team double-booked?
# ──────────────────────────────────────────────────────────────

from __future__ import annotations
import pandas as pd


def _overlaps(s1, e1, s2, e2) -> bool:
    return s1 <= e2 and e1 >= s2


# ── 1. Event date overlaps (HIGHEST PRIORITY) ─────────────────

def detect_event_overlaps(events_df: pd.DataFrame) -> list[dict]:
    """Any two events in the same gender+category bracket that share dates."""
    conflicts: list[dict] = []
    if events_df.empty:
        return conflicts

    df = events_df.copy()
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["end_date"]   = pd.to_datetime(df["end_date"])
    rows = df.reset_index(drop=True)

    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            r1, r2 = rows.iloc[i], rows.iloc[j]
            if _overlaps(r1["start_date"], r1["end_date"],
                         r2["start_date"], r2["end_date"]):
                conflicts.append({
                    "Event A":    r1["event_name"],
                    "Category A": r1.get("category",""),
                    "Gender A":   r1.get("gender",""),
                    "Format A":   r1["format"],
                    "Start A":    r1["start_date"].date(),
                    "End A":      r1["end_date"].date(),
                    "Event B":    r2["event_name"],
                    "Category B": r2.get("category",""),
                    "Gender B":   r2.get("gender",""),
                    "Format B":   r2["format"],
                    "Start B":    r2["start_date"].date(),
                    "End B":      r2["end_date"].date(),
                })
    return conflicts


# ── 2. Player conflicts ───────────────────────────────────────

def detect_player_conflicts(df: pd.DataFrame) -> list[dict]:
    conflicts: list[dict] = []
    if df.empty:
        return conflicts

    for player in df["player_name"].unique():
        rows = df[df["player_name"] == player].reset_index(drop=True)
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                r1, r2 = rows.iloc[i], rows.iloc[j]
                if _overlaps(r1["start_date"], r1["end_date"],
                             r2["start_date"], r2["end_date"]):
                    conflicts.append({
                        "Player":  player,
                        "Event A": r1["event_name"],
                        "Team A":  r1["team"],
                        "Start A": r1["start_date"].date(),
                        "End A":   r1["end_date"].date(),
                        "Event B": r2["event_name"],
                        "Team B":  r2["team"],
                        "Start B": r2["start_date"].date(),
                        "End B":   r2["end_date"].date(),
                    })
    return conflicts


# ── 3. Team conflicts ─────────────────────────────────────────

def detect_team_conflicts(df: pd.DataFrame) -> list[dict]:
    conflicts: list[dict] = []
    if df.empty:
        return conflicts

    for team in df["team"].unique():
        rows = (
            df[df["team"] == team]
            .drop_duplicates("event_name")
            .reset_index(drop=True)
        )
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                r1, r2 = rows.iloc[i], rows.iloc[j]
                if _overlaps(r1["start_date"], r1["end_date"],
                             r2["start_date"], r2["end_date"]):
                    conflicts.append({
                        "Team":    team,
                        "Event A": r1["event_name"],
                        "Start A": r1["start_date"].date(),
                        "End A":   r1["end_date"].date(),
                        "Event B": r2["event_name"],
                        "Start B": r2["start_date"].date(),
                        "End B":   r2["end_date"].date(),
                    })
    return conflicts


# ── Conflict summary for a single event ──────────────────────

def conflicts_for_event(
    event_name: str,
    events_df: pd.DataFrame,
    squad_df: pd.DataFrame,
) -> dict:
    """
    Return all conflict types touching a specific event.
    Used by the search/calendar detail view.
    """
    ev_conflicts = [
        c for c in detect_event_overlaps(events_df)
        if c["Event A"] == event_name or c["Event B"] == event_name
    ]
    pl_conflicts = [
        c for c in detect_player_conflicts(squad_df)
        if c["Event A"] == event_name or c["Event B"] == event_name
    ]
    tm_conflicts = [
        c for c in detect_team_conflicts(squad_df)
        if c["Event A"] == event_name or c["Event B"] == event_name
    ]
    return {
        "event":  ev_conflicts,
        "player": pl_conflicts,
        "team":   tm_conflicts,
    }
