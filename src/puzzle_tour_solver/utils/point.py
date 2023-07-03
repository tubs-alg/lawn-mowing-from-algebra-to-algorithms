import numpy as np
import typing
from shapely.geometry import Point as ShapelyPoint


class Point:
    """
    A simple point_vertex data structure that should be compatible with most others.
    """

    def __init__(self, *args, **kwargs):
        if args:
            if len(args) == 1:
                self._x = args[0][0]
                self._y = args[0][1]
            elif len(args) == 2:
                self._x = args[0]
                self._y = args[1]
            else:
                raise ValueError(f"Don't know how to create a point from {args}")
        elif kwargs:
            self._x = kwargs["x"]
            self._y = kwargs["y"]
        self._x = float(self._x)
        self._y = float(self._y)
        assert isinstance(self._x, float)
        assert isinstance(self._y, float)

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    def __len__(self):
        return 2

    def __getitem__(self, item):
        if item == 0 or item == "x":
            return self.x
        elif item == 1 or item == "y":
            return self.y

        raise KeyError("Bad access.", item)

    def to_np(self):
        return np.array([self.x, self.y])

    def to_shapely(self):
        return ShapelyPoint(self.x, self.y)

    def __add__(self, other):
        a = self.to_np() + other.to_np()
        return Point(a)

    def __mul__(self, other):
        a = other * self.to_np()
        return Point(a)

    def __sub__(self, p2):
        return Point(self.x - p2.i, self.y - p2.j)

    def __hash__(self):
        return hash((self.x, self.y))

    def __lt__(self, other):
        return hash(self) < hash(other)

    def __str__(self):
        return f"({self.x}, {self.y})"

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __rmul__(self, other):
        return self * other


class PointVertex:
    """
    Representing a point vertex in an embedded graph.
    The primary difference to a point is that it has a unique id used for hashing and
    comparison. This allows it to change its position without invalidating dictionaries
    and such.
    """

    def __init__(self, *args, **kwargs):
        self.point = Point(*args, **kwargs)

    @property
    def x(self):
        return self.point.x

    @property
    def y(self):
        return self.point.y

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return id(self) == id(other)

    def __lt__(self, other):
        return hash(self) < hash(other)

    def __getitem__(self, item):
        if item == 0 or item == "x":
            return self.x
        elif item == 1 or item == "y":
            return self.y
        raise KeyError("Bad access.")

    def __str__(self):
        return f"PointVertex[{id(self)}]@({self.x}, {self.y})"

    def __repr__(self):
        return str(self)


def distance(
    p0: typing.Union[Point, PointVertex], p1: typing.Union[Point, PointVertex]
):
    """
    Returns the euclidean distance between two points.
    """
    return np.math.sqrt((p0.x - p1.x) ** 2 + (p0.y - p1.y) ** 2)
