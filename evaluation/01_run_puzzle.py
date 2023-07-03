import argparse
import os
import time
import socket
from pathlib import Path

import slurminade
import hashlib
from aemeasure import MeasurementSeries, Database, read_as_pandas_table
from shapely import LineString
from shapely.geometry import Polygon

from puzzle_tour_solver.tsp.tsp_with_coverage import TSPWithCoverageSolver

# hack for gurobi licence on alg workstations. TODO: Find a nicer way

if socket.gethostname().startswith("alg"):
    os.environ["GRB_LICENSE_FILE"] = os.path.join(
        Path.home(), ".gurobi", socket.gethostname(), "gurobi.lic"
    )

# Import algorithms. Using PATH-hack, because evaluation is no library.

from puzzle_tour_solver.mip import (
    CoverageGraph,
    LocalOptimizer, LnsOptimizer, Model,
)
from puzzle_tour_solver.utils.parser_utils import read_cgal_polygon
from puzzle_tour_solver.utils.solution_utils import get_path_form_solution
from puzzle_tour_solver.generators.coverages.square import SquareCoverage
from puzzle_tour_solver.generators.grid.optimal_grid import SquareGridOptimizer

instances_paths = []

# your supervisor will tell you the necessary configuration.
slurminade.update_default_configuration(
    partition="alg",
    constraint="alggen03",
    mail_user="perk@ibr.cs.tu-bs.de",
    mail_type="FAIL",
)
slurminade.set_dispatch_limit(200)


def unique_hash(data):
    m = hashlib.md5()
    m.update(str(data).encode())
    return str(m.hexdigest())


@slurminade.slurmify()
def optimize_instances(
        result_folder: str, instances_path: str, side_length, grid_optimize_tries,
        timelimit_tsp, timelimit_lns,
        timelimit_mip
):
    print("Solving", instances_path)

    if not os.path.isfile(instances_path):
        raise ValueError(f"Given path is not valid {instances_path}")

    with MeasurementSeries(result_folder) as ms:
        instance_id = unique_hash(instances_path)
        with ms.measurement() as m:
            try:
                polygon = read_cgal_polygon(file_name=instances_path)

                grid_optimizer_start = time.perf_counter()
                grid = SquareGridOptimizer(
                    side_length=side_length, polygon=polygon, tries=grid_optimize_tries
                ).optimize()
                m["grid_optimizer_runtime"] = time.perf_counter() - grid_optimizer_start
                m["grid_properties"] = grid.grid_properties

                coverage_calculator_start = time.perf_counter()
                coverage_generator = SquareCoverage(
                    radius=side_length / 2, square_grid=grid
                )
                coverage_generator.compute_coverages()
                m["coverage_calculator_runtime"] = (
                        time.perf_counter() - coverage_calculator_start
                )

                graph = CoverageGraph.from_grid(grid)
                assert graph.check()

                local_opt = LocalOptimizer()

                tsp_start = time.perf_counter()
                tsp_with_cov = TSPWithCoverageSolver()
                tsp_with_cov_sol = tsp_with_cov.solve(graph,
                                                      grid=grid,
                                                      timelimit=timelimit_tsp)
                initial_sol = tsp_with_cov_sol.coverages

                # m["tsp_original_tour"] = [(v.x, v.y) for v in tsp_with_cov_sol.tsp_tour]
                m["tsp_path_grid_graph"] = [(cov.v.x, cov.v.y) for cov in initial_sol]
                m["tsp_path_grid_graph"].append(m["tsp_path_grid_graph"][0])

                m["tsp_obj_grid_graph"] = LineString(m["tsp_path_grid_graph"]).length
                m["tsp_path_before_optimization"] = get_path_form_solution(initial_sol, graph)

                initial_sol = local_opt(graph, initial_sol)

                m["tsp_path"] = get_path_form_solution(initial_sol, graph)
                m["tsp_obj"] = graph.obj(initial_sol)
                m["tsp_runtime"] = time.perf_counter() - tsp_start

                lns_start = time.perf_counter()
                # Continue optimization with LNS for a near optimal solution
                lns = LnsOptimizer(graph, initial_sol)
                is_optimal = lns.optimize(
                    iterations=100000,
                    iteration_timelimit=5,
                    timelimit=timelimit_lns
                )

                current_sol = lns.current_solution

                m["lns_path_before_optimization"] = get_path_form_solution(current_sol, graph)

                current_sol = local_opt(graph, current_sol)

                m["lns_path"] = get_path_form_solution(current_sol, graph)
                m["lns_obj"] = graph.obj(current_sol)
                m["lns_runtime"] = time.perf_counter() - lns_start
                m["lns_is_optimal"] = is_optimal

                # Further improvement and lower bounds via MIP
                mip_start = time.perf_counter()
                model = Model(graph, current_sol)
                ub, lb = model.optimize(timelimit=timelimit_mip)
                assert lb <= ub, "Lower bound should be <= upper bound by definition."

                sol = model.extract_solution()
                m["mip_path_before_optimization"] = get_path_form_solution(sol, graph)
                sol = local_opt(graph, sol)
                m["mip_path"] = get_path_form_solution(sol, graph)
                m["mip_obj"] = graph.obj(sol)
                m["mip_runtime"] = time.perf_counter() - mip_start

                m["lb"] = lb
                m["ub"] = ub
                m["side_length"] = side_length
                m["grid_optimize_tries"] = grid_optimize_tries
                m["instance_id"] = instance_id
                m["instance"] = os.path.basename(instances_path)
                m["polygon"] = polygon.wkt
                m["timelimit_lns"] = timelimit_lns
                m["timelimit_mip"] = timelimit_mip
                m["timelimit_tsp"] = timelimit_tsp
                m["instance_path"] = instances_path
                # m["stats"] = stats

            except Exception as e:
                print(e)
                raise


@slurminade.slurmify(mail_type="ALL")
def compress(result_folder):
    Database(result_folder).compress()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--side-length", type=float, default=1)
    parser.add_argument("--grid-optimize-tries", type=int, default=10)
    parser.add_argument("--timelimit-lns", type=int, default=300)
    parser.add_argument("--timelimit-tsp", type=int, default=300)
    parser.add_argument("--timelimit-mip", type=int, default=300)

    parser.add_argument("--instances-path", "-d", required=True)
    parser.add_argument("--out-dir", "-o", required=True)

    args = parser.parse_args()

    current_results = read_as_pandas_table(args.out_dir)

    with slurminade.Batch(max_size=10) as batch:
        for instance in os.listdir(args.instances_path):
            instance_path = os.path.join(args.instances_path, instance)

            if (
                    len(current_results) > 0
                    and len(
                current_results[
                    current_results["instance_id"] == unique_hash(instance_path)
                ]
            )
                    > 0
            ):
                continue

            optimize_instances.distribute(
                args.out_dir,
                instance_path,
                args.side_length,
                args.grid_optimize_tries,
                args.timelimit_tsp,
                args.timelimit_lns,
                args.timelimit_mip,
            )
            print("Added", instance_path)
        jids = batch.flush()
        compress.wait_for(jids).distribute(args.out_dir)
