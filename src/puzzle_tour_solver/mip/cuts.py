"""
A set of cuts for the MIP to separate, i.e., prohibit, subtours. A lot can be separated
similar to the Dantzig TSP formulation, but we can also have intersecting cycles that
are not connected. These need a more complicated cut.

You can also create further cuts. Their application order is specified in a list in
the MIP model.

Dominik Krupke, Braunschweig, 2023
"""

import abc
import typing
import networkx as nx
import gurobipy as gp
from .instance import CoverageGraph, Coverage, Vertex, Edge
from .variables import VariableMap, VariableAssignment


class CuttingPlanes(abc.ABC):
    def __init__(self, graph: CoverageGraph, vars: VariableMap):
        self.graph = graph
        self.vars = vars

    @abc.abstractmethod
    def cut(
        self, sol: VariableAssignment, add_to_model: typing.Callable[[gp.LinExpr], None]
    ) -> int:
        pass

    @abc.abstractmethod
    def get_stats(self) -> typing.Dict:
        pass


class ConnectSeparateComponents(CuttingPlanes):
    """
    This cut connects non-intersecting components by an efficient cut, similar to
    Dantzig's formulation for TSP.
    """

    def __init__(self, graph: CoverageGraph, vars: VariableMap):
        super().__init__(graph, vars)
        self.num_cuts = 0

    def _prohibit_component(
        self,
        sol: VariableAssignment,
        component: typing.Iterable[Vertex],
        add_to_model: typing.Callable[[gp.LinExpr], None],
    ) -> int:
        n = 0
        expr = gp.LinExpr()
        for v in component:
            for uvw in self.graph.coverages(v):
                expr += self.vars[uvw]
                n += sol[uvw]
        add_to_model(expr <= n - 1)
        return 1

    def cut(
        self, sol: VariableAssignment, add_to_model: typing.Callable[[gp.LinExpr], None]
    ) -> int:
        graph = nx.Graph()
        graph.add_edges_from(sol.used_edges())
        components = list(nx.connected_components(graph))
        if len(components) <= 1:
            return 0
        mandatory = set(self.graph.mandatory())
        n = 0
        for component in components:
            component = set(component)
            component_has_mandatory_elements = bool(component.intersection(mandatory))
            component_misses_mandatory_elements = bool(mandatory.difference(component))
            if component_has_mandatory_elements and component_misses_mandatory_elements:
                add_to_model(
                    sum(self.vars[uvw] for uvw in self.graph.leaving(component)) >= 1
                )
                n += 1
            elif not component_has_mandatory_elements:
                # useless component that should be prohibited.
                n += self._prohibit_component(sol, component, add_to_model)
        assert n > 0, "Disconnected components should add at least one cut"
        self.num_cuts += n
        return n

    def get_stats(self) -> typing.Dict:
        return {"num_connect_separate_components_cuts": self.num_cuts}


class ConnectIntersectingComponents(CuttingPlanes):
    """
    This cut connects intersecting but disconnected components. It is an expensive cut
    that should only be used for exactly this scenario.
    """

    def __init__(self, graph: CoverageGraph, vars: VariableMap):
        super().__init__(graph, vars)
        self.num_cuts = 0

    def _get_mandatory_full_coverage(
        self, cycle: typing.List[Coverage]
    ) -> typing.Optional[Coverage]:
        """
        Precondition: There is only one per vertex!
        """
        for uvw in cycle:
            if uvw.full:
                return uvw
        return None

    def _get_vertices_of_component(
        self, cycle: typing.List[Coverage]
    ) -> typing.Set[Vertex]:
        vertices = set()
        for uvw in cycle:
            vertices.add(uvw.v)
        return vertices

    def _get_edges_of_component(self, cycle: typing.List[Coverage]) -> typing.Set[Edge]:
        edges = set()
        for uvw in cycle:
            for e in uvw.edges():
                edges.add(e)
        return edges

    def _prohibit_cycle(
        self,
        cycle: typing.List[Coverage],
        add_to_model: typing.Callable[[gp.LinExpr], None],
    ):
        add_to_model(sum(self.vars[uvw] for uvw in cycle) <= len(cycle) - 1)
        return 1

    def _get_sum_of_leaving_coverages(self, sol, cycle, reference_coverage):
        edges: typing.Set[Edge] = self._get_edges_of_component(cycle)
        sum_of_leaving_coverages = gp.LinExpr()
        for v in self._get_vertices_of_component(cycle):
            if v == reference_coverage.v:
                continue  # this case is handled in the next loop
            for uvw in self.graph.coverages(v):
                if all(uvw.edges()[i] not in edges for i in (0, 1)):
                    continue  # one edge has to be on the current path
                if all(uvw.edges()[i] in edges for i in (0, 1)):
                    continue  # one edge has to leave the current path
                assert sol[uvw] == 0, "Should not be used, otherwise it is in cycle"
                sum_of_leaving_coverages += self.vars[uvw]
        for uvw in self.graph.coverages(reference_coverage.v):
            if uvw != reference_coverage and uvw.full:
                assert sol[uvw] == 0
                sum_of_leaving_coverages += self.vars[uvw]
        return sum_of_leaving_coverages

    def cut(
        self, sol: VariableAssignment, add_to_model: typing.Callable[[gp.LinExpr], None]
    ) -> int:
        n = 0
        cycles = sol.cycles()
        if len(cycles) == 1:
            return 0
        for cycle in cycles:
            reference_coverage = self._get_mandatory_full_coverage(cycle)
            if reference_coverage is None:
                n += self._prohibit_cycle(cycle, add_to_model)
                continue
            if sum(1 for uvw in cycle if uvw.full) == len(list(self.graph.mandatory())):
                continue  # no need to add constraint. All full coverages in cycle.
            expr = self._get_sum_of_leaving_coverages(sol, cycle, reference_coverage)
            add_to_model(expr >= 1)
            n += 1
        assert n > 0, "at least one cut always can and needs to be added."
        self.num_cuts += n
        return n

    def get_stats(self) -> typing.Dict:
        return {"num_connect_intersecting_components_cuts": self.num_cuts}
