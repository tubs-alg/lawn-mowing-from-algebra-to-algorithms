from typing import List

import numpy as np
from shapely import LineString

from puzzle_tour_solver.generators.grid.square_grid import SquareGrid
from puzzle_tour_solver.utils.cells import Path, Cell, CellCoverage
from puzzle_tour_solver.utils.point import Point
import itertools as it


class SquareCoverage:
    def __init__(self, radius: float, square_grid: SquareGrid):
        self._grid = square_grid
        self._radius = radius

    @property
    def path_bottom_to_right(self):
        """
        This path was precomputed with Mathematica and is used as a base for constructing all other paths.
        Note that all paths are representing transformation of the entering connection point.
        :return:
        """
        return Path(
            [
                Point(0, 0),
                Point((0.7071067812 - 1) * self._radius, 1.292893219 * self._radius),
                Point(self._radius, self._radius),
            ],
            2.651308592 * self._radius,
        )

    @property
    def path_bottom_to_bottom(self):
        """
        This path was precomputed with Mathematica and is used as a base for constructing all other paths.
        Note that all paths are representing transformation of the entering connection point.
        :return:
        """
        return Path(
            [
                Point(0, 0),
                Point(-0.234920168 * self._radius, 1.356064560 * self._radius),
                Point(0.234920168 * self._radius, 1.356064560 * self._radius),
                Point(0, 0),
            ],
            3.222365414 * self._radius,
        )

    @property
    def path_bottom_to_top(self):
        """
        Obviously the optimal path.
        Note that all paths are representing transformation of the entering connection point.
        :return:
        """
        return Path([Point(0, 0), Point(0, 2 * self._radius)], 2 * self._radius)

    @staticmethod
    def rotate_90_clockwise(input_path: Path):
        new_path_points = [Point(p.y, -p.x) for p in input_path.points]
        return Path(points=new_path_points, length=input_path.length)

    @staticmethod
    def flip_y(input_path: Path):
        new_path_points = [Point(-p.x, p.y) for p in input_path.points]
        return Path(points=new_path_points, length=input_path.length)

    @staticmethod
    def flip_x(input_path: Path):
        new_path_points = [Point(p.x, -p.y) for p in input_path.points]
        return Path(points=new_path_points, length=input_path.length)

    def _construct_coverage_path(self, n1: Cell, f: Cell, n2: Cell) -> Path:
        connect_n1 = f.connection_points[(n1.i, n1.j)]

        # Define the three path types
        if n1.i == n2.i and n1.j == n2.j:
            if n1.i < f.i:  # Left Left
                base_path = self.rotate_90_clockwise(self.path_bottom_to_bottom)
            elif n1.j < f.j:
                base_path = self.path_bottom_to_bottom
            elif n1.i > f.i:
                base_path = self.flip_y(
                    self.rotate_90_clockwise(self.path_bottom_to_bottom)
                )
            else:
                base_path = self.flip_x(self.path_bottom_to_bottom)
        elif n1.i == n2.i or n1.j == n2.j:
            # straight
            if n1.i < n2.i:
                base_path = self.rotate_90_clockwise(self.path_bottom_to_top)
            elif n1.i > n2.i:
                base_path = self.flip_y(
                    self.rotate_90_clockwise(self.path_bottom_to_top)
                )
            elif n1.j < n2.j:
                base_path = self.path_bottom_to_top
            else:
                base_path = self.flip_x(self.path_bottom_to_top)
        else:
            # turn
            if n1.i < f.i:  # entry left
                if n2.j < f.j:  # exit bottom
                    base_path = self.rotate_90_clockwise(self.path_bottom_to_right)
                else:  # exit top
                    base_path = self.rotate_90_clockwise(
                        self.flip_y(self.path_bottom_to_right)
                    )
            elif n1.i > f.i:  # entry right
                if n2.j < f.j:  # exit bottom
                    base_path = self.rotate_90_clockwise(
                        self.flip_x(self.path_bottom_to_right)
                    )
                else:  # exit top
                    base_path = self.rotate_90_clockwise(
                        self.flip_y(self.flip_x(self.path_bottom_to_right))
                    )
            elif n1.j < f.j:  # entry bottom
                if n2.i < f.i:  # exit left
                    base_path = self.flip_y(self.path_bottom_to_right)
                else:  # exit right
                    base_path = self.path_bottom_to_right
            else:  # entry top
                if n2.i < f.i:  # exit left
                    base_path = self.flip_x(self.flip_y(self.path_bottom_to_right))
                else:  # exit right
                    base_path = self.flip_x(self.path_bottom_to_right)

        assert base_path is not None
        path = Path(list(base_path.points), base_path.length)
        # Tranformation to the correct position
        path.points = [p + connect_n1 for p in path.points]

        return path

    def _get_neighbors(self, x, y) -> List[Cell]:
        neighbor_indices = [(x - 1, y), (x + 1, y), (x, y + 1), (x, y - 1)]
        return [
            self._grid.inside_cells[i, j]
            for i, j in neighbor_indices
            if self._grid.inside_cells.contains(i, j)
        ] + [
            self._grid.phantom_cells[i, j]
            for i, j in neighbor_indices
            if self._grid.phantom_cells.contains(i, j)
        ]

    def compute_coverages(self):
        for f in self._grid.all_cells:
            x, y = f.i, f.j

            for n1, n2 in it.product(self._get_neighbors(x, y), repeat=2):
                connect_n1 = f.connection_points[(n1.i, n1.j)]
                connect_n2 = f.connection_points[(n2.i, n2.j)]

                if n1.index > n2.index:
                    continue

                if f.needs_coverage:
                    path = self._construct_coverage_path(n1, f, n2)
                else:
                    line_string = LineString(
                        [(connect_n1.x, connect_n1.y), (connect_n2.x, connect_n2.y)]
                    )
                    path = Path([connect_n1, connect_n2], line_string.length)

                assert np.allclose(path.points[0].to_np(), connect_n1.to_np())
                assert np.allclose(path.points[-1].to_np(), connect_n2.to_np())

                f.coverages.append(
                    CellCoverage(
                        path=path, f=f.index, n1=n1.index, n2=n2.index, cost=path.length
                    )
                )
