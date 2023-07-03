"""
Tools for performing some basic local optimization.

Dominik Krupke, Braunschweig, 2023
"""

import typing
from collections import defaultdict

from .coverages_to_cycle import coverages_to_cycle
from .instance import CoverageGraph, Coverage, Vertex


class LocalOptimizer:

    def relative_cost(self, graph: CoverageGraph, u: Vertex, v: Vertex, w: Vertex) \
            -> float:
        """
        Return the relative cost of using uvw with full coverage.
        """
        return graph.cost(Coverage(u, v, w, full=True)) - graph.cost(
            Coverage(u, v, w, full=False))

    def optimize_tile(self, graph: CoverageGraph, tile: Vertex,
                      coverages: typing.List[Coverage]) -> \
            typing.List[Coverage]:
        """
        Return a list of coverage where the full coverage has been assigned to
        the cheapest option.
        """
        if not all(uvw.v == tile for uvw in coverages):
            raise ValueError("Coverage not for tile")
        if not tile.is_mandatory:
            # trivial case with no full coverages
            return [Coverage(uvw.u, uvw.v, uvw.w, full=False) for uvw in coverages]
        # find the cheapest best coverage
        best_full = min(range(len(coverages)),
                        key=lambda i: self.relative_cost(graph, coverages[i].u,
                                                         coverages[i].v, coverages[i].w))
        return [Coverage(uvw.u, uvw.v, uvw.w, full=(i == best_full))
                for i, uvw in enumerate(coverages)]

    def __call__(self, graph: CoverageGraph, solution: typing.List[Coverage]) \
            -> typing.List[Coverage]:
        """
        Perform a local optimization on the solution.
        """
        coverages_per_tile = defaultdict(list)
        for uvw in solution:
            coverages_per_tile[uvw.v].append(uvw)
        improved_solution = sum((self.optimize_tile(graph, v, covs)
                                 for v, covs in coverages_per_tile.items()), start=[])
        improved_solution = coverages_to_cycle(improved_solution)  # sort to cycle
        return improved_solution
