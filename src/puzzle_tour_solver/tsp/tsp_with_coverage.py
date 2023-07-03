import typing
from dataclasses import dataclass

from concorde.tsp import TSPSolver

from puzzle_tour_solver.mip.instance import CoverageGraph, Coverage
from puzzle_tour_solver.generators.grid.square_grid import SquareGrid
from puzzle_tour_solver.mip import Vertex, is_feasible_solution
from puzzle_tour_solver.mip.heuristic import get_graph_approx
import networkx as nx

from puzzle_tour_solver.utils.solution_utils import get_path_form_solution


class TSPWithCoverageSolver:
    SCALING_FACTOR = 1e2

    @dataclass
    class Solution:
        ub: float
        is_optimal: bool
        tour: typing.List[typing.Tuple[float, float]]
        tsp_tour: typing.List[Vertex]
        coverages: typing.List[Coverage]

    def solve(self, graph: CoverageGraph, grid: SquareGrid, timelimit: int = 300):
        assert graph.check()
        cells_that_need_coverage = [cell for cell in grid.all_cells if cell.needs_coverage]
        xes = [cell.center.x * TSPWithCoverageSolver.SCALING_FACTOR for cell in cells_that_need_coverage]
        yes = [cell.center.y * TSPWithCoverageSolver.SCALING_FACTOR for cell in cells_that_need_coverage]

        solver = TSPSolver.from_data(xes, yes, norm="MAN_2D")
        tour = solver.solve(time_bound=timelimit)

        is_optimal = tour.success
        if not tour.found_tour:
            raise RuntimeError("Could not find feasible TSP tour!")

        # Convert tour to graph vertices
        tour = [graph.vertex_map[cells_that_need_coverage[i].index] for i in tour.tour]

        if tour[0] != tour[-1]:  # close tour
            tour.append(tour[0])

        extended_tour: typing.List[Vertex] = [tour[0]]
        g = get_graph_approx(graph)
        for v in tour[1:]:
            u = extended_tour[-1]
            if graph.are_neighbored(u, v):
                extended_tour.append(v)
            else:
                path = nx.shortest_path(g, u, v, weight="weight")
                extended_tour += path[1:]

        covered_vertices = set()
        extended_tour.append(extended_tour[1])
        solution = []
        for i in range(1, len(extended_tour) - 1):
            u = extended_tour[i - 1]
            v = extended_tour[i]
            w = extended_tour[i + 1]
            assert u != v and v != w
            if v.is_mandatory and v not in covered_vertices:
                solution.append(Coverage(u, v, w, True))
                covered_vertices.add(v)
            else:
                solution.append(Coverage(u, v, w, False))

        assert is_feasible_solution(solution)

        ub = sum(graph.cost(uvw) for uvw in solution)

        tour = get_path_form_solution(solution, graph)
        return TSPWithCoverageSolver.Solution(ub=ub,
                                              tour=tour,
                                              tsp_tour=extended_tour,
                                              is_optimal=is_optimal,
                                              coverages=solution)
