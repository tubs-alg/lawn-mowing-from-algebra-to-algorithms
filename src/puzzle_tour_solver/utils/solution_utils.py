import typing

from puzzle_tour_solver.mip.instance import Coverage, CoverageGraph


def get_path_form_solution(solution: typing.List[Coverage], graph: CoverageGraph) -> \
        typing.List[typing.Tuple[float, float]]:
    """
    Converts a given solution to a complete path.
    """
    path = []
    for i, uvw in enumerate(solution):
        n = solution[(i + 1) % len(solution)]
        if uvw.w == n.v:
            path += [(p.x, p.y) for p in graph.path_map[uvw].points]
        else:
            path += [(p.x, p.y) for p in (~graph.path_map[uvw]).points]
    return path
