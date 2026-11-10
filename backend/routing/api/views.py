from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..adapters import tomtom
from ..services.heatmap import corridor_heatmap
from ..services.plan import plan_trip
from .serializers import (
    HeatmapRequestSerializer,
    PlanRequestSerializer,
    heatmap_payload,
    plan_payload,
)


@api_view(["GET", "HEAD"])
def health(request):
    # Report whether the key is set, never the key itself.
    return Response({"status": "ok", "tomtom_key": bool(settings.TOMTOM_API_KEY)})


@api_view(["GET"])
def geocode(request):
    q = request.query_params.get("q", "").strip()
    if len(q) < 2:
        return Response([])
    return Response(tomtom.geocode(q[:100]))


@api_view(["POST"])
def plan(request):
    req = PlanRequestSerializer(data=request.data)
    req.is_valid(raise_exception=True)
    d = req.validated_data
    rec, warnings = plan_trip(
        origin=(d["origin"]["lon"], d["origin"]["lat"]),
        dest=(d["destination"]["lon"], d["destination"]["lat"]),
        departure=d["departure"],
        load_lb=d["load_lb"],
        interval_mi=d["interval_mi"],
        scenario=d["scenario"],
    )
    return Response(plan_payload(rec, warnings, d["scenario"]))


@api_view(["POST"])
def heatmap(request):
    req = HeatmapRequestSerializer(data=request.data)
    req.is_valid(raise_exception=True)
    d = req.validated_data
    cells, size, frames = corridor_heatmap(
        d["routes"], d["departure"], d["load_lb"], scenario=d["scenario"]
    )
    return Response(heatmap_payload(cells, size, d["departure"], frames, d["scenario"]))
