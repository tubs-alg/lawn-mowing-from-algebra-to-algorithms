"""
The MIP model uses variables for the different ways of passing a vertex. This file
provides code to obtain an actual cycle of those. This requires an algorithm similar
to eulerian tour (but slightly more complicated).

Dominik Krupke, Braunschweig, 2023
"""

import typing

from .instance import is_feasible_solution, Coverage, Vertex


class SolutionConverter:
    def __init__(self):
        pass

    def _extract_coverage(
        self, coverage: typing.Dict[Coverage, int], u: Vertex, v: Vertex
    ) -> Coverage:
        for uvw, x in coverage.items():
            if x > 0 and uvw.v == v and (uvw.u == u or uvw.w == u):
                if x == 1:
                    coverage.pop(uvw)
                    return uvw
                else:
                    coverage[uvw] = x - 1
                    return uvw
        raise KeyError("Could not find matching entry.")

    def _extract_cycle(
        self, coverage: typing.Dict[Coverage, int], u: Vertex, v: Vertex
    ) -> typing.List[Coverage]:
        """
        u: Direction we are coming from.
        v: The vertex we are currently at.
        """
        start = (u, v)
        try:
            cycle = [self._extract_coverage(coverage, u, v)]
        except KeyError:
            return []
        u, v = v, cycle[-1].other(u)
        cycle.append(self._extract_coverage(coverage, u, v))
        u, v = v, cycle[-1].other(u)
        while (u, v) != start:
            cycle.append(self._extract_coverage(coverage, u, v))
            u, v = v, cycle[-1].other(u)
        if not is_feasible_solution(cycle):
            print(cycle)
        assert is_feasible_solution(cycle), "Should be a feasible cycle."
        return cycle

    def _random_used_arc(
        self, coverages: typing.Dict[Coverage, int]
    ) -> typing.Tuple[Vertex, Vertex]:
        for uvw, x in coverages.items():
            if x > 0:
                return uvw.u, uvw.v
        raise ValueError("No coverages")

    def extract_cycle_from_dict(
        self, coverages: typing.Dict[Coverage, int]
    ) -> typing.List[Coverage]:
        u, v = self._random_used_arc(coverages)
        cycle = self._extract_cycle(coverages, u, v)
        i = 0
        while i < len(cycle):
            u = cycle[i - 1 % len(cycle)]
            v = cycle[i]
            subcycle = self._extract_cycle(coverages, u.v, v.v)
            if subcycle:
                cycle = cycle[:i] + subcycle + cycle[i:]
            else:
                i += 1
        assert is_feasible_solution(cycle), "Should be a feasible cycle."
        return cycle

    def convert_from_list_to_dict(
        self, coverages: typing.List[Coverage]
    ) -> typing.Dict[Coverage, int]:
        sol = dict()
        for uvw in coverages:
            sol[uvw] = sol.get(uvw, 0) + 1
        return sol

    def convert_from_list_to_cycle(self, coverages: typing.List[Coverage]):
        return self.extract_cycle_from_dict(self.convert_from_list_to_dict(coverages))


def coverages_to_cycle(coverages: typing.List[Coverage]):
    return SolutionConverter().convert_from_list_to_cycle(coverages)
