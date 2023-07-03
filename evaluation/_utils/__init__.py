from aemeasure import read_as_pandas_table
import os
import pandas as pd
import shapely.wkt
import collections
import numpy as np
import re


def instance_types(instance_name):
    return re.search(r"([a-z|\_]+)[0-9]+\.poly", instance_name).group(1).rstrip("_mc")


def instance_types_simplified(instance_name):
    instance_type = instance_types(instance_name)
    if "aligned" in instance_type:
        return "Polyominoes"
    elif not "octa" in instance_type:
        return "Orthogonal Polygons"
    else:
        return "Octagonal Polygons"


def unify_instances(solutions):
    common_instance_set = set(solutions[0]["instance_path"])

    for sol in solutions:
        common_instance_set = common_instance_set.intersection(set(sol["instance_path"]))
        print([f"{item}: {count}" for item, count in collections.Counter(sol["instance_path"]).items() if count > 1])

    return [
        sol[sol["instance_path"].isin(common_instance_set)] for sol in solutions
    ]


def load_directory(directory):
    solutions = list()
    for d in os.listdir(directory):
        full_path = os.path.join(directory, d)
        if os.path.isdir(full_path):
            print("Adding", full_path)
            solutions.append(read_as_pandas_table(full_path))

    return pd.concat(solutions, ignore_index=True)

def add_important_fields(results):
    results["instance_type"] = results["instance"].apply(instance_types)
    results["instance_type_simplified"] = results["instance"].apply(instance_types_simplified)
    results["polygon_area"] = results["polygon_shapely"].apply(lambda x: x.area)
    results["convex_hull_area"] = results["polygon_shapely"].apply(lambda x: x.convex_hull.area)
    results["relative_area"] = results["convex_hull_area"] / (np.pi * 0.25)  # r = 0.5
    results["relative_area_nearest_500"] = results["relative_area"].apply(lambda x: 5 * round(x / 5, -2))
    results["relative_area_nearest_100"] = results["relative_area"].apply(lambda x: round(x, -2))
    results["relative_area_nearest_50"] = results["relative_area"].apply(lambda x: 5 * round(x / 5, -1))
    results["relative_area_nearest_250"] = results["relative_area"].apply(lambda x: 2.5 * round(x / 2.5, -2))


def load_old_results():
    turncost_solutions = load_directory("turncost_improved")
    tsp_solutions = load_directory("tsp")
    tsp_coverage_solutions = load_directory("tsp_coverage")

    turncost_solutions["solver"] = "tsp_with_turncost"
    tsp_solutions["solver"] = "tsp"
    tsp_coverage_solutions["solver"] = "tsp_cov"

    results = pd.concat(unify_instances([turncost_solutions, tsp_solutions, tsp_coverage_solutions]), ignore_index=True)
    results["polygon"] = results["polygon"].apply(lambda x: shapely.wkt.loads(x))

    add_important_fields(results)

    results = results[results["relative_area"] <= 1000]  # Talk about this value

    return results


def load_turncost_results():
    turncost_solutions = load_directory("turncost")
    turncost_solutions_tsp_start = load_directory("turncost_improved")

    turncost_solutions["solver"] = "tsp_with_turncost"
    turncost_solutions_tsp_start["solver"] = "tsp_with_turncost_tsp_start"

    results = pd.concat(unify_instances([turncost_solutions, turncost_solutions_tsp_start]), ignore_index=True)
    results["polygon"] = results["polygon"].apply(lambda x: shapely.wkt.loads(x))

    add_important_fields(results)

    results = results[results["relative_area"] <= 1000]  # Talk about this value

    return results

def load_results(with_tsp=False):
    solutions = load_directory("results/complete/")
    if with_tsp:
        tsp_solutions = load_directory("results/tsp/")
        small_tsp_obj = [None] * len(solutions)
        small_tsp_path = [None] * len(solutions)
        small_tsp_runtime = [None] * len(solutions)

        for i, sol in tsp_solutions.iterrows():
            original_solutions = solutions[solutions['instance_path'] == sol["instance_path"]]
            if len(original_solutions) == 0:
                continue
            assert len(original_solutions) == 1
            index = int(original_solutions.index.values.astype(int)[0])
            small_tsp_obj[index] = sol["ub"]
            small_tsp_path[index] = sol["path"]
            small_tsp_runtime[index] = sol["mip_runtime"]

        solutions["small_tsp_obj"] = small_tsp_obj
        solutions["small_tsp_runtime"] = small_tsp_runtime
        solutions["small_tsp_path"] = small_tsp_path
        assert (solutions["small_tsp_obj"] > 0).all()
    results = solutions
    results["polygon_shapely"] = results["polygon"].apply(lambda x: shapely.wkt.loads(x))
    add_important_fields(results)
    results = results[results["relative_area"] <= 1000]  # Talk about this value
    return results




