"""
Defining a container for the MIP variables and for their assignments.
Having a separate container for the variables is a good practice, as it allows to
easily make the MIP LNS-compatible (by just returning constants for the fixed variables).

The assignment container allows to provide semantic access to the assignment (directly
reconstructing graphs etc from the variables) and potentially cache those.

Dominik Krupke, Braunschweig, 2023
"""

import gurobipy as gp
import typing
import networkx as nx
from gurobipy import GRB

from .coverages_to_cycle import coverages_to_cycle
from .instance import CoverageGraph, Coverage, Edge


class VariableAssignment:
    def __init__(self, graph: CoverageGraph, values: typing.Dict[Coverage, int]):
        self.graph = graph
        self._values = values

    def __getitem__(self, item: Coverage) -> int:
        return round(self._values.get(item, 0))

    def used_coverages(self, duplicates: bool = False) -> typing.Iterable[Coverage]:
        """
        Return all coverages used in the current solution.
        If you want repetitive coverages, set duplicates=True
        """
        for uvw, x in self._values.items():
            for _ in range(round(x)):
                yield uvw
                if not duplicates:
                    continue

    def used_edges(self) -> typing.Iterable[Edge]:
        """
        Return all edges used in the current solution.
        """
        edges = set()
        for uvw in self.used_coverages():
            for edge in uvw.edges():
                if edge not in edges:
                    yield edge
                    edges.add(edge)

    def components(self) -> typing.List[typing.Dict[Coverage, int]]:
        components = []
        g = nx.Graph()
        for uvw in self.used_coverages(duplicates=False):
            for e in uvw.edges():
                g.add_edge(uvw, e)
        for comp in nx.connected_components(g):
            comp = list(comp)  # TODO: Clean up
            assert comp
            covs = [uvw for uvw in comp if isinstance(uvw, Coverage)]
            assert covs
            components.append({uvw: round(self[uvw]) for uvw in covs})
            assert all(x > 0 for x in components[-1].values())
        assert all(len(comp) > 0 for comp in components)
        if not components:
            raise ValueError("No components")
        return components

    def cycles(self) -> typing.List[typing.List[Coverage]]:
        return [
            coverages_to_cycle(sum((x * [uvw] for uvw, x in comp.items()), start=[]))
            for comp in self.components()
        ]


class VariableMap:
    """
    The  variable map saves the variables for the  model.
    It can also be used to query the used variables in the current solution.
    """

    def __init__(
        self,
        graph: CoverageGraph,
        model: gp.Model,
        fixed: typing.Optional[typing.Dict[Coverage, int]] = None,
    ):
        self.graph = graph
        self.fixed = fixed if fixed is not None else dict()
        self._vars_full = model.addVars(
            [uvw for uvw in graph.coverages() if uvw.full and uvw not in self.fixed],
            vtype=GRB.BINARY,
        )
        self._vars_justpassing = model.addVars(
            [
                uvw
                for uvw in graph.coverages()
                if not uvw.full and uvw not in self.fixed
            ],
            lb=0,
            # ub=2,
            vtype=GRB.INTEGER,
        )

    def __getitem__(
        self, item: Coverage
    ) -> typing.Union[int, float, gp.Var, gp.LinExpr]:
        if item in self.fixed:
            return self.fixed[item]
        if item.full:
            return self._vars_full[item]
        else:
            return self._vars_justpassing[item]

    def get_current_value(self, uvw: Coverage, model: typing.Optional[gp.Model] = None):
        if uvw in self.fixed:
            return self[uvw]
        elif model:
            return model.cbGetSolution(self[uvw])
        else:
            return self[uvw].X

    def get_assignment(self, model: typing.Optional[gp.Model] = None):
        values = dict()
        for uvw in self.graph.coverages():
            x = self.get_current_value(uvw, model)
            if x > 0:
                values[uvw] = x
        return VariableAssignment(self.graph, values)

    def is_true_var(self, uvw: Coverage):
        return uvw in self._vars_full or uvw in self._vars_justpassing

    def all_real_vars(self) -> typing.Iterable[typing.Tuple[Coverage, gp.Var]]:
        yield from self._vars_full.items()
        yield from self._vars_justpassing.items()
