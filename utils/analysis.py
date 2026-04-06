# utils/analysis.py
from __future__ import annotations
import pandas as pd
from datetime import date


def _gap_status(gap: int) -> str:
    if gap < 0:   return "🔴 Overlap"
    if gap == 0:  return "🟠 Back-to-Back"
    if gap <= 7:  return "🟡 Tight Gap"
    return "🟢 OK"


def gap_analysis(df: pd.DataFrame, player_name: str) -> pd.DataFrame:
    pdata = (
        df[df["player_name"] == player_name]
        .sort_values("start_date")
        .reset_index(drop=True)
    )
    if pdata.empty:
        return pdata
    gaps, statuses = [], []
    for i in range(len(pdata)):
        if i == 0:
            gaps.append(None); statuses.append("—")
        else:
            gap = (pdata.loc[i,"start_date"] - pdata.loc[i-1,"end_date"]).days
            gaps.append(gap); statuses.append(_gap_status(gap))
    pdata["gap_days"]   = gaps
    pdata["gap_status"] = statuses
    return pdata


def player_workload(
    df: pd.DataFrame,
    player_name: str,
    ref_date: pd.Timestamp | None = None,
) -> tuple[int, str]:
    if ref_date is None:
        ref_date = pd.Timestamp(date.today())
    window_start = ref_date - pd.Timedelta(days=30)
    pdata  = df[df["player_name"] == player_name]
    recent = pdata[
        (pdata["start_date"] >= window_start) | (pdata["end_date"] >= window_start)
    ]
    count = len(recent)
    level = "Low" if count == 0 else ("Medium" if count <= 2 else "High")
    return count, level


def workload_badge_class(level: str) -> str:
    return {"Low":"badge-green","Medium":"badge-yellow","High":"badge-red"}.get(level,"badge-blue")
