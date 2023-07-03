import argparse
import os
import time
import socket
from pathlib import Path

import slurminade
import hashlib
from aemeasure import MeasurementSeries, Database, read_as_pandas_table
from shapely.geometry import Polygon, LineString
from math import sqrt

# hack for gurobi licence on alg workstations. TODO: Find a nicer way

if socket.gethostname().startswith("alg"):
    os.environ["GRB_LICENSE_FILE"] = os.path.join(
        Path.home(), ".gurobi", socket.gethostname(), "gurobi.lic"
    )

# Import algorithms. Using PATH-hack, because evaluation is no library.

from puzzle_tour_solver.tsp.tsp_solver import TSPGridSolver
from puzzle_tour_solver.utils.parser_utils import read_cgal_polygon
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
    result_folder: str, instances_path: str, side_length, grid_optimize_tries, timelimit
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

                solver = TSPGridSolver()

                mip_start = time.perf_counter()
                tour = solver.solve(grid=grid, timelimit=timelimit)
                if tour[0] != tour[-1]:  # close tour
                    tour.append(tour[0])

                m["mip_runtime"] = time.perf_counter() - mip_start
                m["ub"] = LineString(tour).length
                m["path"] = tour

                m["side_length"] = side_length
                m["grid_optimize_tries"] = grid_optimize_tries
                m["instance_id"] = instance_id
                m["instance"] = os.path.basename(instances_path)
                m["polygon"] = polygon.wkt
                m["timelimit"] = timelimit
                m["instance_path"] = instances_path

            except Exception as e:
                print(e)
                raise


@slurminade.slurmify(mail_type="ALL")
def compress(result_folder):
    Database(result_folder).compress()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--timelimit", type=int, default=300)
    parser.add_argument("--side-length", type=float, default=1)
    parser.add_argument("--grid-optimize-tries", type=int, default=10)
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
                args.side_length * sqrt(2) * 0.5,
                args.grid_optimize_tries,
                args.timelimit,
            )
            print("Added", instance_path)
        jids = batch.flush()
        compress.wait_for(jids).distribute(args.out_dir)
