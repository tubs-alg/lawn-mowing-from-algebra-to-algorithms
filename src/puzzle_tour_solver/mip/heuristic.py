"""
Simple 2-Opt heuristic to quickly obtain an okay-ish solution.

Dominik Krupke, Braunschweig, 2023
"""


import random
import typing
import networkx as nx

from .instance import Vertex, CoverageGraph, Coverage, is_feasible_solution
from ..utils.timer import Timer


def dist(v: Vertex, w: Vertex):
    return abs(v.x - w.x) + abs(v.y - w.y)


class DistMatrix:
    def __init__(self, instance: typing.List[Vertex]):
        self._dists = [
            [dist(p0, p1) for p1 in instance] for i, p0 in enumerate(instance)
        ]

    def dist(self, i: int, j: int):
        if i == j:
            return 0.0
        return self._dists[i][j]


class TwoOptOptimizer:
    def __init__(self, instance: typing.List[Vertex]):
        self.instance = instance
        self._dist_matrix = DistMatrix(instance)

    def _diff(self, tour, i, j):
        i_ = i - 1 % len(tour)
        j_ = j - 1 % len(tour)
        prev_cost = self._dist_matrix.dist(tour[i_], tour[i]) + self._dist_matrix.dist(
            tour[j_], tour[j]
        )
        changed_cost = self._dist_matrix.dist(
            tour[i_], tour[j_]
        ) + self._dist_matrix.dist(tour[i], tour[j])
        return changed_cost - prev_cost

    def optimization_step(self, tour):
        changed = False
        for j in range(len(tour)):
            for i in range(j):
                if self._diff(tour, i, j) < 0:
                    tour = tour[:i] + tour[i:j][::-1] + tour[j:]
                    changed = True
        return tour, changed

    def optimize(self, tour=None, timelimit: float = 90):
        if not tour:
            tour = list(range(len(self.instance)))
            random.shuffle(tour)
        improved = True
        timelimit_watcher = Timer(timelimit)
        try:
            while improved:
                tour, improved = self.optimization_step(tour)
                timelimit_watcher.check()
        except TimeoutError:
            print("Terminated by timeout.")
        return [self.instance[i] for i in tour]


def get_graph_approx(instance: CoverageGraph):
    g = nx.Graph()
    g.add_nodes_from(instance.vertices)
    for v in instance.vertices:
        for w in instance.neighbors(v):
            assert v != w
            g.add_edge(v, w, weight=dist(v, w))
    return g


def compute_heuristic_solution(
    instance: CoverageGraph, timelimit: float
) -> typing.List[Coverage]:
    vertices = list(instance.mandatory())
    assert (
        len(vertices) >= 2
    ), "With less than two mandatory vertices, the optimization is useless."
    tour = TwoOptOptimizer(vertices).optimize(timelimit=timelimit)
    if tour[0] != tour[-1]:  # close tour
        tour.append(tour[0])
    extended_tour: typing.List[Vertex] = [tour[0]]
    g = get_graph_approx(instance)
    for v in tour[1:]:
        u = extended_tour[-1]
        if instance.are_neighbored(u, v):
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
    obj = sum(instance.cost(uvw) for uvw in solution)
    print("Initial solution with objective:", obj)
    return solution
