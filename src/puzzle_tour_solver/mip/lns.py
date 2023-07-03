"""
A simple LNS algorithm based on the MIP and automatic neighborhood size adaption based
on whether the previous iteration was successful.

This algorithm should yield good, nearly optimal results for many instances but is
not maximally optimized, especially for larger instances with relatively small
neighborhoods as fixed variables are just replaced by constants. Especially, the cuts
are still computed on the full instance, which may be inefficient.

Dominik Krupke, Braunschweig, 2023
"""
import random
import typing
import math
import networkx as nx

from .instance import CoverageGraph, Coverage, Vertex
from .model import Model
from ..utils.timer import Timer


class LnsOptimizer:
    def __init__(self, graph: CoverageGraph, initial_solution: typing.List[Coverage]):
        self.graph = graph
        self.current_solution = initial_solution

    def optimize_neighborhood(
        self, fixed_vertices: typing.Set[Vertex], timelimit: float
    ):
        if timelimit <= 0:
            return None, None
        mip = Model(self.graph, self.current_solution, fixed_part=fixed_vertices)
        lb, ub = mip.optimize(timelimit=timelimit)
        if ub is None:
            print("WARNING: No upper bound in LNS. This should not happen.")
            return lb, ub
        solution = mip.extract_solution()
        if self.graph.obj(solution) < self.graph.obj(self.current_solution):
            self.current_solution = solution
        return lb, ub

    def optimize_around(self, vertex: Vertex, num_free: int, timelimit: float):
        g = nx.Graph()
        for e in self.graph.edges():
            g.add_edge(e.v, e.w)
        bfs = [vertex] + [
            v for u, v in nx.bfs_edges(g, source=vertex, depth_limit=num_free)
        ]
        fixed = set(g.nodes) - set(bfs[:num_free])
        return self.optimize_neighborhood(fixed, timelimit)

    def random_optimization_step(self, nbrhood_size: int, timelimit: float):
        v = random.choice(self.current_solution).v
        return self.optimize_around(v, nbrhood_size, timelimit)

    def optimize(
        self,
        iterations: int = 50,
        iteration_timelimit: float = 5.0,
        timelimit: float = 60.0,
    ) -> bool:
        """
        Optimize the problem for a number of iterations, where each iteration
        has a timelimit. You can use it multiple times.

        Returns, whether the solution was optimal in the end.
        """
        opt_timer = Timer(timelimit)
        n = 10
        for i in range(iterations):
            if opt_timer.is_out_of_time():
                return False
            print(f"LNS iteration={i}, size={n}.")
            iter_timer = Timer(min(iteration_timelimit, opt_timer.remaining()))
            lb, ub = self.random_optimization_step(n, iter_timer.remaining())
            if n >= len(self.graph.vertices) and ub is not None and lb == ub:
                return True  # optimal solution found
            if ub is not None and lb == ub:
                n = math.ceil(n * 1.25)
            else:
                n = math.floor(n / 1.25)
        return False
