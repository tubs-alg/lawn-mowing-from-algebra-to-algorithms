"""
A number of classes to model and work with an instance.
An instance is a graph where each vertex has multiple options for passing or coverage.

Dominik Krupke, Braunschweig, 2023
"""
import itertools
import typing
from collections import defaultdict

from puzzle_tour_solver.generators.grid.square_grid import SquareGrid
from puzzle_tour_solver.utils.cells import CellCoverage


class Vertex:
    """
    A vertex in the grid.
    """

    def __init__(self, idx: int, x: float, y: float):
        """
        To be created by the instance.
        """
        self.idx = idx
        self.x = x
        self.y = y
        self.is_mandatory = False
        self.meta = dict()

    def __eq__(self, other):
        return self.idx == other.idx

    def __int__(self):
        return self.idx

    def __lt__(self, other):
        return self.idx < other.idx

    def __le__(self, other):
        return self.idx <= other.idx

    def __hash__(self):
        return self.idx

    def __repr__(self):
        if self.is_mandatory:
            return f"({round(self.x, 2)}, {round(self.y, 2)})[#{self.idx}!]"
        return f"({round(self.x, 2)}, {round(self.y, 2)})[#{self.idx}]"


class Edge:
    def __init__(self, v: Vertex, w: Vertex):
        self.v = min(v, w)
        self.w = max(v, w)

    def __len__(self):
        return 2

    def __getitem__(self, item):
        if item == 0:
            return self.v
        if item == 1:
            return self.w
        raise IndexError()

    def __hash__(self):
        return hash((self.v, self.w))

    def __eq__(self, other):
        return self.v == other.v and self.w == other.w


class Coverage:
    """
    Represents the coverage of a vertex/field.
    Only with full=True it is a true coverage.
    Otherwise, it is just passing through (with a potentially cheaper tour).
    """

    def __init__(self, u: Vertex, v: Vertex, w: Vertex, full: bool):
        self.u = min(u, w)  # exit/entry
        self.v = v  # the central vertex
        self.w = max(u, w)  # exit/entry
        self.full = full

    def is_u(self) -> bool:
        return self.u == self.w

    def __hash__(self):
        return hash((self.u, self.v, self.w, self.full))

    def uvw(self) -> typing.Tuple[Vertex, Vertex, Vertex]:
        return (self.u, self.v, self.w)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Coverage):
            return False
        return self.uvw() == other.uvw() and self.full == other.full

    def other(self, u: Vertex) -> Vertex:
        if u == self.u:
            return self.w
        else:
            return self.u

    def __repr__(self) -> str:
        if self.full:
            return f"({self.u} <- {self.v} -> {self.w} [full])"
        return f"({self.u} <- {self.v} -> {self.w})"

    def __contains__(self, item):
        return item in self.uvw()

    def edges(self) -> typing.Tuple[Edge, Edge]:
        return (Edge(self.u, self.v), Edge(self.v, self.w))

    def are_connected(self, uvw: "Coverage") -> bool:
        assert isinstance(uvw, Coverage)
        return self.v in uvw and self.v != uvw.v and uvw.v in self and uvw.v != self.v


class CoverageGraph:
    def __init__(self):
        self.vertices = []
        self.coordinates = set()
        self._costs = dict()
        self._neighbors = defaultdict(list)

        self.vertex_map = dict()
        self.path_map = dict()

    @classmethod
    def from_grid(cls, square_grid: SquareGrid):
        graph = cls()

        for cell in square_grid.all_cells:
            graph.vertex_map[cell.index] = graph.get_or_create_vertex(
                cell.center.x, cell.center.y, cell.needs_coverage
            )

        for cell in square_grid.all_cells:
            for cov in cell.coverages:  # type: CellCoverage
                cost = cov.cost
                uvw = Coverage(
                    graph.vertex_map[cov.n1],
                    graph.vertex_map[cov.f],
                    graph.vertex_map[cov.n2],
                    cell.needs_coverage,
                )
                graph.set_cost(uvw, cost)
                if graph.vertex_map[cov.n1] == uvw.u:
                    graph.path_map[uvw] = cov.path
                else:
                    assert graph.vertex_map[cov.n1] == uvw.w
                    graph.path_map[uvw] = ~cov.path  # invert path

        return graph

    def neighbors(self, v: Vertex) -> typing.List[Vertex]:
        return [self.vertices[i] for i in self._neighbors[v.idx]]

    def are_neighbored(self, v: Vertex, w: Vertex) -> bool:
        return w in self.neighbors(v)

    def get_or_create_vertex(self, x: float, y: float, mandatory=False):
        v = next((v for v in self.vertices if v.x == x and v.y == y), None)
        if v is None:
            v = Vertex(len(self.vertices), x, y)
            v.is_mandatory = mandatory
            self.vertices.append(v)
            return v
        else:
            v.is_mandatory = mandatory or v.is_mandatory
        return v

    def coverages(self, v: typing.Optional[Vertex] = None) -> typing.Iterable[Coverage]:
        if v is None:
            for v in self.vertices:
                yield from self.coverages(v)
        else:
            for n in self.neighbors(v):
                if v.is_mandatory:
                    yield Coverage(n, v, n, True)
                # This would never be used by an optimal solution, but necessary for
                # some heuristic initial solutions.
                yield Coverage(n, v, n, False)
            for n0, n1 in itertools.combinations(self.neighbors(v), 2):
                if v.is_mandatory:
                    yield Coverage(n0, v, n1, True)
                yield Coverage(n0, v, n1, False)

    def set_cost(self, uvw: Coverage, cost: float):
        self._add_edge(uvw.u, uvw.v)
        self._add_edge(uvw.v, uvw.w)
        self._costs[uvw] = cost

    def leaving(self, vertices: typing.Iterable[Vertex]) -> typing.Iterable[Coverage]:
        vertices = set(vertices)
        for v in vertices:
            for coverage in self.coverages(v):
                if any(w not in vertices for w in coverage.uvw()):
                    yield coverage

    def _add_edge(self, v: Vertex, w: Vertex):
        v_nbrs = self.neighbors(v)
        if w not in v_nbrs:
            self._neighbors[v.idx].append(w.idx)
            self._neighbors[w.idx].append(v.idx)

    def cost(self, uvw: Coverage):
        if uvw.is_u() and not uvw.full:
            if uvw not in self._costs:
                return 0.0
        return self._costs[uvw]

    def obj(self, coverages: typing.Iterable[Coverage]) -> float:
        return sum(self.cost(uvw) for uvw in coverages)

    def edges(self) -> typing.Iterable[Edge]:
        for v in self.vertices:
            for n in self.neighbors(v):
                if v.idx < n.idx:
                    yield Edge(v, n)

    def mandatory(self) -> typing.Iterable[Vertex]:
        for v in self.vertices:
            if v.is_mandatory:
                yield v

    def check(self):
        for coverage in self.coverages():
            self.cost(coverage)
        return True


def is_in_line(uvw0: Coverage, uvw1: Coverage, uvw2: Coverage):
    if not uvw0.are_connected(uvw1) or not uvw1.are_connected(uvw2):
        return False
    return (uvw0.v == uvw1.u and uvw1.w == uvw2.v) or (
        uvw0.v == uvw1.w and uvw1.u == uvw2.v
    )


def is_feasible_solution(coverages: typing.List[Coverage]):
    coverages = list(coverages)  # copy
    assert all(isinstance(c, Coverage) for c in coverages)
    if len(coverages) < 2:
        return False
    if len(coverages) == 2:
        return coverages[0].are_connected(coverages[1]) and all(
            c.is_u() for c in coverages
        )
    coverages += [coverages[0], coverages[1]]
    return all(
        is_in_line(coverages[i - 2], coverages[i - 1], coverages[i])
        for i in range(2, len(coverages))
    )
