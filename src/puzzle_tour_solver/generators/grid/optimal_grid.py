import typing
from shapely import Polygon

from puzzle_tour_solver.generators.grid.square_grid import SquareGrid


class SquareGridOptimizer:
    def __init__(self, polygon: Polygon, side_length: float, tries=10):
        self._polygon = polygon
        self._side_length = side_length
        self._tries = tries

    def optimize(self):
        min_x, min_y, _, _ = self._polygon.bounds
        grids: typing.List[SquareGrid] = list()

        grids.append(SquareGrid(
                        polygon=self._polygon,
                        side_length=self._side_length
                    ))

        for xi in range(0, self._tries):
            for yi in range(0, self._tries):
                grids.append(
                    SquareGrid(
                        polygon=self._polygon,
                        side_length=self._side_length,
                        min_x=min_x - (xi / self._tries) * self._side_length,
                        min_y=min_y - (yi / self._tries) * self._side_length,
                    )
                )

        print("Generated", len(grids), "grids")

        return min(grids, key=lambda grid: len(grid.inside_cells))
