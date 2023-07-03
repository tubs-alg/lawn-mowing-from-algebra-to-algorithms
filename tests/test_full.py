import itertools

import networkx as nx

from puzzle_tour_solver.generators.grid.optimal_grid import SquareGridOptimizer
from puzzle_tour_solver.generators.coverages.square import SquareCoverage
from puzzle_tour_solver.mip import (
    Vertex,
    CoverageGraph,
    Coverage,
    is_feasible_solution,
)
from puzzle_tour_solver.tsp.tsp_solver import TSPGridSolver
from puzzle_tour_solver.tsp.tsp_with_coverage import TSPWithCoverageSolver
from puzzle_tour_solver.utils.parser_utils import read_cgal_polygon
from math import sqrt
from shapely import Polygon, LineString
import numpy as np

from puzzle_tour_solver.utils.solution_utils import get_path_form_solution

from puzzle_tour_solver.mip import optimize


def test_full_u():
    def dist(v: Vertex, w: Vertex):
        return abs(v.x - w.x) + abs(v.y - w.y)

    graph = CoverageGraph()
    g = nx.Graph()
    g.add_nodes_from(
        [graph.get_or_create_vertex(x, y, True) for x in [0, 1, 2] for y in [0, 1, 2]]
    )
    for v, w in itertools.combinations(g.nodes, 2):
        if dist(v, w) == 1:
            g.add_edge(v, w)
    for v in g.nodes:
        for n0, n1 in itertools.combinations_with_replacement(g.neighbors(v), 2):
            graph.set_cost(Coverage(n0, v, n1, True), 1.2)
            graph.set_cost(Coverage(n0, v, n1, False), 1.0)

    lb, ub, solution = optimize(graph, 120)
    assert is_feasible_solution(solution)


def test_tsp():
    polygon = read_cgal_polygon(file_name="instances/small/srpg_iso0000039.poly")

    grid = SquareGridOptimizer(side_length=sqrt(2), polygon=polygon, tries=5).optimize()

    solver = TSPGridSolver()
    tour = solver.solve(grid=grid, timelimit=60)

    if tour[0] != tour[-1]:
        tour.append(tour[0])
    linestring = LineString(tour)

    assert np.isclose(linestring.length, 64.225396, atol=1e-2), f"{linestring.length}"
    assert len(tour) - 1 == len(grid.inside_cells)


def test_tsp_with_holes():
    polygon = read_cgal_polygon(file_name="instances/srpg_iso_aligned_mc_small/srpg_iso_aligned_mc0000088.poly")

    grid = SquareGridOptimizer(side_length=sqrt(2),
                               polygon=polygon,
                               tries=5).optimize()
#
    solver = TSPGridSolver()
    tour = solver.solve(grid=grid, timelimit=60)

    if tour[0] != tour[-1]:
        tour.append(tour[0])
    linestring = LineString(tour)
    assert np.isclose(linestring.length, 166.048773, atol=1e-2), f"{linestring.length}"
    assert len(tour) - 1 == len(grid.inside_cells)


def test_parse_instance():
    polygon = read_cgal_polygon(file_name="instances/small/srpg_iso0000059.poly")

    # For some reason the files are named n-1
    assert len(list(polygon.boundary.coords[:-1])) - 1 == 59
    assert np.isclose(polygon.area, 87.37, rtol=1e-2)

    polygon = read_cgal_polygon(file_name="instances/srpg_iso_aligned_mc_small/srpg_iso_aligned_mc0000088.poly")
    # For some reason the files are named n-1
    assert len(list(polygon.exterior.coords[:-1])) + len(list(polygon.interiors[0].coords[:-1])) - 2 == 88


def test_coverage_path_with_holes():
    side_length = 1
    polygon = read_cgal_polygon(file_name="instances/srpg_iso_aligned_mc_small/srpg_iso_aligned_mc0000088.poly")

    grid = SquareGridOptimizer(
        side_length=side_length, polygon=polygon, tries=5
    ).optimize()

    coverage_generator = SquareCoverage(radius=side_length / 2, square_grid=grid)
    coverage_generator.compute_coverages()

    assert int(polygon.area) == len(grid.inside_cells)
    graph = CoverageGraph.from_grid(grid)
    assert graph.check()

    lb, ub, solution = optimize(graph, 60)
    assert is_feasible_solution(solution)

    path = get_path_form_solution(solution, graph)
    assert np.isclose(LineString(path).length, ub)


def test_coverage_path():
    side_length = 1
    polygon = read_cgal_polygon(file_name="instances/small/srpg_iso0000039.poly")

    grid = SquareGridOptimizer(
        side_length=side_length, polygon=polygon, tries=5
    ).optimize()

    coverage_generator = SquareCoverage(radius=side_length / 2, square_grid=grid)
    coverage_generator.compute_coverages()

    graph = CoverageGraph.from_grid(grid)
    assert graph.check()

    lb, ub, solution = optimize(graph, 60)
    assert is_feasible_solution(solution)
    path = get_path_form_solution(solution, graph)

    assert np.isclose(LineString(path).length, ub)


def test_tsp_with_coverage():
    side_length = 1
    polygon = read_cgal_polygon(file_name="instances/small/srpg_iso0000039.poly")

    grid = SquareGridOptimizer(
        side_length=side_length, polygon=polygon, tries=5
    ).optimize()

    coverage_generator = SquareCoverage(radius=side_length / 2, square_grid=grid)
    coverage_generator.compute_coverages()

    graph = CoverageGraph.from_grid(grid)
    assert graph.check()

    solver = TSPWithCoverageSolver()

    path = solver.solve(graph, grid, timelimit=30).tour

    assert np.isclose(LineString(path).length, 98.27535)
