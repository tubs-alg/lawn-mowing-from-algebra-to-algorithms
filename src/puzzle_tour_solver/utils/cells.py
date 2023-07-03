from dataclasses import dataclass
from typing import List

from shapely import Polygon

from .point import Point


@dataclass
class Path:
    points: List[Point]
    length: float

    def __invert__(self):
        return Path(points=self.points[::-1], length=self.length)


@dataclass
class CellCoverage:
    path: Path
    f: int
    n1: int
    n2: int
    cost: float


@dataclass
class Cell:
    index: int
    i: int
    j: int
    bounds: list
    needs_coverage: bool
    connection_points: dict
    coverages: list
    center: Point

    def shapely_polygon(self):
        return Polygon([(p.x, p.y) for p in self.bounds])
