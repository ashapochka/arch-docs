"""Plane geometry for diagram layout: shapes, connection ports, polylines."""

import itertools
import math
from dataclasses import dataclass
from typing import Literal, NamedTuple

type Point = tuple[float, float]
type Side = Literal["top", "bottom", "left", "right"]


class Port(NamedTuple):
    """A connection point: absolute position plus draw.io's fractional position."""

    x: float
    y: float
    fx: float
    fy: float


@dataclass(frozen=True)
class Shape:
    """Axis-aligned bounding box of a placed shape, addressed by its key."""

    key: str
    x: float
    y: float
    w: float
    h: float

    @property
    def cx(self) -> float:
        """Horizontal centre (a lifeline's x position)."""
        return self.x + self.w / 2

    def port(self, side: Side, f: float = 0.5) -> Port:
        """Return the point on `side` at fraction `f` along it.

        `f` runs left to right on top/bottom and top to bottom on left/right;
        0.5 is the middle. `fx`/`fy` are the same point as fractions of the
        shape (0..1), which is how draw.io stores exit/entry points.

        Raises:
            ValueError: if `f` is outside 0..1.
        """
        if not 0 <= f <= 1:
            raise ValueError(f"port fraction must be in 0..1, got {f}")
        fx, fy = {
            "top": (f, 0.0),
            "bottom": (f, 1.0),
            "left": (0.0, f),
            "right": (1.0, f),
        }[side]
        return Port(self.x + fx * self.w, self.y + fy * self.h, fx, fy)


def point_along(points: list[Point], t: float) -> Point:
    """Return the point at fraction `t` (0..1) of a polyline's total length.

    t=0 is the first point, t=1 the last. A polyline of zero length returns
    its first point.

    Raises:
        ValueError: if fewer than two points are given, or `t` is outside 0..1.
    """
    if len(points) < 2:
        raise ValueError(f"a polyline needs at least two points, got {len(points)}")
    if not 0 <= t <= 1:
        raise ValueError(f"t must be in 0..1, got {t}")
    segments = [math.dist(a, b) for a, b in itertools.pairwise(points)]
    remaining = sum(segments) * t
    for (a, b), length in zip(itertools.pairwise(points), segments, strict=True):
        if remaining <= length:
            r = remaining / length if length else 0.0
            return a[0] + (b[0] - a[0]) * r, a[1] + (b[1] - a[1]) * r
        remaining -= length
    return points[-1]  # float rounding left a sliver past the last segment
