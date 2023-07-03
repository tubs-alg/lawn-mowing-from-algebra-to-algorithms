"""
A mixed integer programming model for the problem. Allows to fix variables in order to
be easily used for an LNS. Without fixing variables, it potentially computes a provably
optimal solution.

This file primarily only contains the base model and some interface. The variables are
defined in `variables.py` and the subtour elimination constraints in `cuts.py`.

Dominik Krupke, Braunschweig, 2023
"""
import gurobipy as gp
import typing
from gurobipy import GRB

from .cuts import (
    CuttingPlanes,
    ConnectSeparateComponents,
    ConnectIntersectingComponents,
)
from .instance import CoverageGraph, Coverage, Vertex
from .variables import VariableMap


class Model:
    def __init__(
        self,
        graph: CoverageGraph,
        initial_solution: typing.Optional[typing.List[Coverage]] = None,
        fixed_part: typing.Optional[typing.Set[Vertex]] = None,
    ):
        self.model = gp.Model()
        fixed_vars = {}
        if fixed_part is not None:
            if initial_solution is None:
                raise ValueError(
                    "Fixing is only possible with a feasible initial solution."
                )
            sol = self._initial_solution_to_dict(initial_solution)
            fixed_vars = {uvw: x for uvw, x in sol.items() if uvw.v in fixed_part}
        self.vmap = VariableMap(graph, self.model, fixed=fixed_vars)
        self.graph = graph
        self.add_objective()
        self.enforce_coverage()
        self.enforce_flow()
        self.stats = {}
        self._cuts: typing.List[CuttingPlanes] = [
            ConnectSeparateComponents(graph, self.vmap),
            ConnectIntersectingComponents(graph, self.vmap),
        ]
        if initial_solution:
            self._add_initial_solution(initial_solution)

    def _initial_solution_to_dict(self, initial_solution: typing.List[Coverage]):
        sol = dict()
        for uvw in initial_solution:
            sol[uvw] = sol.get(uvw, 0) + 1
        return sol

    def _add_initial_solution(self, initial_solution: typing.List[Coverage]):
        sol = self._initial_solution_to_dict(initial_solution)
        self.model.NumStart = 1
        self.model.update()
        self.model.params.StartNumber = 0
        for uvw, var in self.vmap.all_real_vars():
            var.Start = sol.get(uvw, 0)

    def add_objective(self):
        def c(uvw: Coverage):
            return self.graph.cost(uvw)

        obj = gp.quicksum(c(uvw) * self.vmap[uvw] for uvw in self.graph.coverages())
        self.model.setObjective(obj, GRB.MINIMIZE)

    def enforce_coverage(self):
        for v in self.graph.mandatory():
            cov_sum = gp.quicksum(
                self.vmap[uvw] for uvw in self.graph.coverages(v) if uvw.full
            )
            self.model.addConstr(cov_sum == 1, f"{v} needs to be covered.")

    def enforce_flow(self):
        for v, w in self.graph.edges():

            def f(uvw: Coverage):
                return 2 * self.vmap[uvw] if uvw.is_u() else 1 * self.vmap[uvw]

            self.model.addConstr(
                sum(f(uvw) for uvw in self.graph.coverages(v) if w in uvw)
                == sum(f(vwu) for vwu in self.graph.coverages(w) if v in vwu),
                f"{v}->{w} == {w}->{v}",
            )

    def optimize(self, timelimit=900):
        def callback(model, where):
            if where == GRB.Callback.MIPSOL:
                sol = self.vmap.get_assignment(model)
                for cuts in self._cuts:
                    if cuts.cut(sol, lambda expr: model.cbLazy(expr)) > 0:
                        return

        self.model.Params.TimeLimit = timelimit
        self.model.Params.lazyConstraints = 1
        self.model.optimize(callback)
        for cuts in self._cuts:
            self.stats.update(cuts.get_stats())
        if self.model.SolCount > 0:
            return self.model.ObjVal, self.model.ObjBound
        return None, self.model.ObjBound

    def extract_solution(self) -> typing.List[Coverage]:
        cycles = self.vmap.get_assignment().cycles()
        assert len(cycles) == 1
        return cycles[0]
