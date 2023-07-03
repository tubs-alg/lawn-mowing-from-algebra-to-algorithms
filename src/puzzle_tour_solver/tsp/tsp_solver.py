from concorde.tsp import TSPSolver

from puzzle_tour_solver.generators.grid.square_grid import SquareGrid


class TSPGridSolver:
    # This scaling factor will be applied to any instance and ensure that Concorde outputs the optimal tour
    SCALING_FACTOR = 1e3

    def __init__(self, norm: str = "EUC_2D"):
        self._norm = norm

    def solve(self, grid: SquareGrid, timelimit: int = 300):
        print("USING PRECISION", TSPGridSolver.SCALING_FACTOR)
        all_cells = grid.all_cells

        print("Received", len(all_cells), "cells")

        xes = list()
        yes = list()

        for cell in all_cells:
            if cell.needs_coverage:
                xes.append(cell.center.x)
                yes.append(cell.center.y)

        solver = TSPSolver.from_data(
            [x * TSPGridSolver.SCALING_FACTOR for x in xes],
            [y * TSPGridSolver.SCALING_FACTOR for y in yes],
            norm=self._norm,
        )  # EUC_2D rounds to the nearest integer (thus the scaling)

        tour = solver.solve(time_bound=timelimit)

        if tour.success or tour.found_tour:
            return [(xes[i], yes[i]) for i in tour.tour]

        return None
