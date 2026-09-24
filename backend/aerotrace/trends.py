"""Session-level trend summaries; never convert trend slopes into remaining life."""
from datetime import datetime
import statistics

def trend_summary(session_summaries):
    output = {}
    for regime in ("idle", "loaded"):
        by_day = {}
        for s in session_summaries:
            value = s["median_score_by_regime"].get(regime)
            if value is not None:
                by_day.setdefault(s["date"], []).append(value)
        points = sorted((datetime.fromisoformat(d).toordinal(), statistics.median(v)) for d, v in by_day.items())
        # Theil-Sen slope needs multiple independent dates. Overlap copies cannot increase N.
        if len(points) < 3:
            output[regime] = {"status": "insufficient_history", "distinct_days": len(points), "slope_per_day": None}
        else:
            slopes = [(y2-y1)/(x2-x1) for i, (x1, y1) in enumerate(points) for x2, y2 in points[i+1:]]
            output[regime] = {"status": "descriptive_only", "distinct_days": len(points),
                              "slope_per_day": statistics.median(slopes),
                              "warning": "Operating mix and model drift can change this score; not a physical wear rate"}
    return {"regimes": output, "rul_hours": None, "failure_probability": None,
            "reason": "Trend is not a validated degradation or survival model"}
