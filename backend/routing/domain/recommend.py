from .models import Level, Recommendation, RouteSummary, ScoredRoute

NO_TRAVEL_WARNING = "Every route crosses No Travel conditions. Consider a later departure."
RISK_LEVELS = (Level.NO_TRAVEL, Level.SEVERE, Level.HIGH)


def summarize(cps, total_mi):
    miles = dict.fromkeys(Level, 0.0)
    for cp in cps:
        miles[cp.risk.level] += cp.covered_mi
    # Distance-weighted mean of the level scores (Low 0 ... No Travel 4).
    avg = sum(level * mi for level, mi in miles.items()) / total_mi if total_mi else 0.0
    return RouteSummary(miles_by_level=miles, avg_risk=avg)


def score(route, cps):
    return ScoredRoute(route=route, checkpoints=cps, summary=summarize(cps, route.distance_mi))


def sort_key(sr):
    # No Travel goes first (not in the spec's list, but clearly the worst outcome).
    # Rounding keeps float noise from deciding the winner.
    miles = sr.summary.miles_by_level
    return (
        round(miles[Level.NO_TRAVEL], 1),
        round(miles[Level.SEVERE], 1),
        round(miles[Level.HIGH], 1),
        round(sr.summary.avg_risk, 2),
        sr.route.duration_s,
    )


def recommend(scored):
    """Rank routes safest first and explain why the winner won."""
    ranked = sorted(scored, key=sort_key)  # stable, so exact ties keep router order
    best = ranked[0]
    warnings = []
    # Any No Travel checkpoint counts here, even one too short to survive rounding.
    if any(cp.risk.level == Level.NO_TRAVEL for cp in best.checkpoints):
        warnings.append(NO_TRAVEL_WARNING)
    return Recommendation(ranked=ranked, explanation=explain(ranked), warnings=warnings)


def explain(ranked):
    best = ranked[0]
    if len(ranked) == 1:
        return f"Route {best.route.id} is the only route found."

    text = versus(best, ranked[1])
    # The runner-up may not be the quick option the driver is weighing up,
    # so also say what the fastest route would cost.
    fastest = min(ranked, key=lambda sr: sr.route.duration_s)
    if fastest is not best and fastest is not ranked[1]:
        text += " " + faster_but(fastest, best)
    return text


def versus(best, other):
    name, vs = f"Route {best.route.id}", f"Route {other.route.id}"
    a, b = sort_key(best), sort_key(other)
    time = time_note(best.route.duration_s - other.route.duration_s)

    for i, level in enumerate(RISK_LEVELS):
        if a[i] != b[i]:
            return f"{name}: {a[i]:g} {level.label} miles vs {b[i]:g} on {vs}; {time}."
    if a[3] != b[3]:
        return (
            f"{name}: same Severe and High miles as {vs}, "
            f"lower average risk ({a[3]:.2f} vs {b[3]:.2f}); {time}."
        )
    if a[4] != b[4]:
        return f"{name}: same risk as {vs}; {time}."
    return f"{name} and {vs} tie on risk and travel time."


def faster_but(fast, best):
    """Why a quicker route lost: the first risk key where it's worse."""
    a, b = sort_key(fast), sort_key(best)
    lead = f"Route {fast.route.id} is {time_note(fast.route.duration_s - best.route.duration_s)}"
    for i, level in enumerate(RISK_LEVELS):
        if a[i] > b[i]:
            return f"{lead} but has {a[i]:g} {level.label} miles."
    return f"{lead} but riskier overall (average {a[3]:.2f} vs {b[3]:.2f})."


def time_note(diff_s):
    if diff_s == 0:
        return "same travel time"
    word = "longer" if diff_s > 0 else "faster"
    mins = round(abs(diff_s) / 60)
    if mins == 0:
        return f"slightly {word}"
    return f"{fmt_duration(mins)} {word}"


def fmt_duration(mins):
    if mins < 60:
        return f"{mins} min"
    return f"{mins // 60} h {mins % 60:02d} min"
