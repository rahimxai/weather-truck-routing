from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum

LonLat = tuple[float, float]


class Level(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @property
    def label(self):
        return self.name.replace("_", " ").title()


@dataclass(frozen=True)
class Weather:
    wind_mph: float
    gust_mph: float
    rain_in_hr: float
    snow_in_hr: float


@dataclass(frozen=True)
class Risk:
    level: Level
    reason: str
    wind: Level
    rain: Level
    snow: Level


@dataclass(frozen=True)
class Route:
    id: str
    geometry: list[LonLat]
    distance_mi: float
    duration_s: float
    # (mile, seconds after departure) pairs from the router, used for ETAs.
    profile: list[tuple[float, float]]


@dataclass(frozen=True)
class Checkpoint:
    mile: float
    lon: float
    lat: float
    eta: datetime
    covered_mi: float
    weather: Weather | None = None
    risk: Risk | None = None


@dataclass(frozen=True)
class RouteSummary:
    miles_by_level: dict[Level, float]
    avg_risk: float


@dataclass(frozen=True)
class ScoredRoute:
    route: Route
    checkpoints: list[Checkpoint]
    summary: RouteSummary


@dataclass(frozen=True)
class Recommendation:
    ranked: list[ScoredRoute]
    explanation: str
    warnings: list[str] = field(default_factory=list)

    @property
    def best(self):
        return self.ranked[0]
