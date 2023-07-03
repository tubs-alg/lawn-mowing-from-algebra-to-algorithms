from collections import defaultdict

import numpy as np
from shapely import Polygon
from math import ceil

from puzzle_tour_solver.utils.cells import Cell
from puzzle_tour_solver.utils.point import Point


class Grid:
    def __init__(self):
        self._map = defaultdict(dict)

    def __setitem__(self, pos, value: Cell):
        x, y = pos
        self._map[x][y] = value

    def __getitem__(self, pos) -> Cell:
        x, y = pos
        return self._map[x][y]

    def contains(self, x, y):
        return x in self._map and y in self._map[x]

    def values(self):
        for x in self._map:
            for y in self._map[x]:
                yield self[x, y]

    def __len__(self):
        return sum(len(self._map[x]) for x in self._map)


class SquareGrid:
    def __init__(self, polygon: Polygon, side_length: float, min_x=None, min_y=None):
        self._polygon = polygon

        self._min_x, self._min_y, self._max_x, self._max_y = self._polygon.bounds

        if min_x is not None:
            if min_x > self._min_x:
                raise ValueError("We can not start inside the polygon")
            else:
                self._min_x = min_x

        if min_y is not None:
            if min_y > self._min_y:
                raise ValueError("We can not start inside the polygon")
            else:
                self._min_y = min_y

        self._side_length = side_length

        self._nx = ceil((self._max_x - self._min_x) / self._side_length)
        self._ny = ceil((self._max_y - self._min_y) / self._side_length)

        self._coverage_cells = Grid()
        self._phantom_cells = Grid()

        self._initialize()

    @property
    def grid_properties(self):
        return {
            "side_length": self._side_length,
            "min_x": self._min_x,
            "min_y": self._min_y,
            "max_x": self._max_x,
            "max_y": self._max_y,
            "n_inside_cells": len(self._coverage_cells),
            "n_phantom_cells": len(self._phantom_cells),
        }

    @property
    def inside_cells(self):
        return self._coverage_cells

    @property
    def phantom_cells(self):
        return self._phantom_cells

    @property
    def all_cells(self):
        return list(self._coverage_cells.values()) + list(self._phantom_cells.values())

    def _generate_connection_points(self, i: int, j: int, square_bounds):
        """
        Generating the connection points for the paths, i.e. middlepoints of all four sides.
        :param i: x index
        :param j: y index
        :return:
        """
        connection_points = dict()

        if i > 0:
            connection_points[(i - 1, j)] = square_bounds[0] + Point(
                0, 0.5 * self._side_length
            )

        if i < self._nx - 1:
            connection_points[(i + 1, j)] = square_bounds[1] + Point(
                0, 0.5 * self._side_length
            )

        if j > 0:
            connection_points[(i, j - 1)] = square_bounds[0] + Point(
                0.5 * self._side_length, 0
            )

        if j < self._ny - 1:
            connection_points[(i, j + 1)] = square_bounds[3] + Point(
                0.5 * self._side_length, 0
            )

        return connection_points

    def _generate_cell_bounds(self, i: int, j: int):
        """
        BOTTOM_LEFT = 0
        BOTTOM_RIGHT = 1
        TOP_RIGHT = 2
        TOP_LEFT = 3
        :param i:
        :param j:
        :return: bl br tr tl
        """
        return [
            Point(
                self._min_x + i * self._side_length, self._min_y + j * self._side_length
            ),
            Point(
                self._min_x + i * self._side_length + self._side_length,
                self._min_y + j * self._side_length,
            ),
            Point(
                self._min_x + i * self._side_length + self._side_length,
                self._min_y + j * self._side_length + self._side_length,
            ),
            Point(
                self._min_x + i * self._side_length,
                self._min_y + j * self._side_length + self._side_length,
            ),
        ]

    def _initialize(self):
        for i in range(self._nx):
            for j in range(self._ny):
                cell_bounds = self._generate_cell_bounds(i, j)
                cell_polygon = Polygon(p.to_shapely() for p in cell_bounds)

                assert np.isclose(cell_polygon.area, self._side_length**2)

                cell = Cell(
                    i=i,
                    j=j,
                    bounds=cell_bounds,
                    needs_coverage=self._polygon.intersection(cell_polygon).area > 1e-6,
                    connection_points=self._generate_connection_points(
                        i, j, cell_bounds
                    ),
                    index=i + j * self._nx,
                    coverages=list(),
                    center=cell_polygon.centroid,
                )

                if cell.needs_coverage:
                    self._coverage_cells[i, j] = cell
                else:
                    self._phantom_cells[i, j] = cell

        assert all(
            self._coverage_cells[i, j].needs_coverage
            for i in range(self._nx)
            for j in range(self._ny)
            if self._coverage_cells.contains(i, j)
        )
        assert all(
            (self._coverage_cells[x, y].i == x and self._coverage_cells[x, y].j == y)
            if self._coverage_cells.contains(x, y)
            else (self._phantom_cells[x, y].i == x and self._phantom_cells[x, y].j == y)
            for x in range(self._nx)
            for y in range(self._ny)
        )

        for i in range(self._nx):
            for j in range(self._ny):
                if self._coverage_cells.contains(i, j):
                    f = self._coverage_cells[i, j]  # type: Cell
                    phantom_cell = Cell(
                        index=self._nx * self._ny + i + j * self._nx,
                        i=f.i,
                        j=f.j,
                        bounds=f.bounds,
                        needs_coverage=False,
                        connection_points=f.connection_points,
                        coverages=list(),
                        center=f.center,
                    )

                    self._phantom_cells[i, j] = phantom_cell
