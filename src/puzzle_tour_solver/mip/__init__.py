"""
This module provides code for finding an (optimal) tour through a grid where each
vertex can be covered by different paths. The code is very generic and can be easily
used for many instances, even those that are highly irregular.

An important concept is a `Coverage` that is defined by a cell v (represented by a
vertex), and the two neighbored cells u,w from which we enter/leave. A `full` coverage
actually is a path that covers v and ends at the gates to u resp. w. Other coverages just
need to go from u to w. All combinations for u and w must be defined.

Usage by first converting the problem to a CoverageGraph and then just calling `optimize`.
There is some hope to solve instances with less than 1000 vertices. For less than 100
vertices there is a good chance.

Dominik Krupke, Braunschweig, 2023
"""

import typing

from .heuristic import compute_heuristic_solution
from .instance import CoverageGraph, Coverage, Vertex, Edge, is_feasible_solution
from .lns import LnsOptimizer
from .model import Model
from .local_optimization import LocalOptimizer
from ..generators.grid.square_grid import SquareGrid
from ..tsp.tsp_with_coverage import TSPWithCoverageSolver
from ..utils.timer import Timer


def optimize(
        instance: CoverageGraph, timelimit: float, initial_heuristic="2-opt", grid: SquareGrid = None
) -> typing.Tuple[float, float, typing.List[Coverage]]:
    """
    Compute a tour using 2OPt, LNS, and MIP.
    return Lower Bound, Upper Bound, Cycle of Coverages.
    """
    timer = Timer(timelimit)
    if initial_heuristic == "2-opt":
        # Initial Solution via 2-Opt
        initial_sol = compute_heuristic_solution(instance, timelimit / 3)
    else:
        tsp_with_cov = TSPWithCoverageSolver()
        initial_sol = tsp_with_cov.solve(instance, grid=grid, timelimit=int(timelimit / 3)).coverages
    print(
        f"[{int(timer.time())}s] Found initial solution of"
        f" value {instance.obj(initial_sol)}."
    )
    local_opt = LocalOptimizer()
    initial_sol = local_opt(instance, initial_sol)
    print(f"[{int(timer.time())}s] After local optimization: {instance.obj(initial_sol)}")
    if timer.is_out_of_time():
        print("Out of time.")
        return 0, instance.obj(initial_sol), initial_sol
    # Continue optimization with LNS for a near optimal solution
    lns = LnsOptimizer(instance, initial_sol)
    if lns.optimize(
            iterations=1000, iteration_timelimit=5, timelimit=timer.remaining() / 3
    ):
        print(f"[{int(timer.time())}s]  LNS found optimal solution.")
    print(
        f"[{int(timer.time())}s]  LNS found solution of"
        f" value {instance.obj(lns.current_solution)}."
    )
    current_sol = local_opt(instance, lns.current_solution)
    print(f"[{int(timer.time())}s] After local optimization: {instance.obj(current_sol)}")
    # Further improvement and lower bounds via MIP
    model = Model(instance, current_sol)
    if timer.is_out_of_time():
        print("Out of time.")
        return 0, instance.obj(current_sol), current_sol
    ub, lb = model.optimize(timelimit=timer.remaining())
    assert lb <= ub, "Lower bound should be <= upper bound by definition."
    print(
        f"[{int(timer.time())}s]  MIP found solution of value {ub} with lower bound {lb}."
    )
    sol = model.extract_solution()
    sol = local_opt(instance, sol)
    print(f"[{int(timer.time())}s] After local optimization: {instance.obj(sol)}")
    return lb, ub, sol
