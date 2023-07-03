# The Lawn Mowing Problem: From Algebra to Algorithms
This repository contains the code for a solver to the lawn mowing problem.
Given some polygon, preferably a polyomino, 
we realize a tour of the dual grid with locally optimal
puzzle pieces: a limited set of locally good trajectories 
that mow each visited pixel, which are merged at
transition points on the pixel boundaries.
Making use of the puzzle pieces, we can now approach the LMP in three steps,
as follows.

* A: Find a cheap roundtrip on the dual grid graph.
* B: Carry out the individual pixel transitions based on the above
puzzle pieces as building blocks to ensure coverage of all pixels.
* C: Perform post-processing on the resulting tour.

In principle, we can approach **A**
by considering an integer program (IP); however, solving this IP
becomes too costly for larger instances, so
we use a more scalable approach: **A** Find 
a good TSP solution on the dual grid graph; **B** insert puzzle pieces;
**C** use turn-minimizing 
methods, including Large Neighborhood Search (LNS)
and iterative solution of IP subproblems.

### Setup
You can install the package with `pip`.
```
pip install .
```

This will also download and build Concorde (and its dependency QSOpt) and then 
build PyConcorde. While this may take a few minutes, downloading Concorde 
only happens the first time the install script is run. Please note that this package
requires Gurobi to run. **Please make sure you have an active license.**

You can test if everything was set up correctly by 
installing `pytest` (e.g. `pip install pytest`) and running

```
pytest
```


### Project Structure

The relevant source code can be found in `src`. Instances are located in the `instances` folder. 
All of the evaluation scripts
that are needed to generate the plots from our paper can be found in `evaluation`. 
The code to execute our experiments are in `evaluation/00_run_tsp.py` for TSP
on a small grid and in `evaluation/01_run_puzzle.py` for the puzzle solver. Note that
you need to install [slurminade](https://github.com/d-krupke/slurminade)
and [aemearue](https://github.com/d-krupke/aemeasure) to run the scripts.
The `02_data_preprocessing` notebook performs some preprocessing on the results and
saves a compressed version in `evaluation/03_clean_data.json.zip`. All other
notebooks use that file for further evaluation. The file 
`evaluation/external/alenex_2023.json.zip` contains relevant data from [1] that we 
need for comparison.
Descriptions of the plots and goals can be found within each notebook. 

### Example

The following example contains code to execute the puzzle solver. Please see the
relevant script in `evaluation` for further details.

```python
from puzzle_tour_solver.mip import (
    CoverageGraph,
    LocalOptimizer, LnsOptimizer, Model,
)
from puzzle_tour_solver.utils.parser_utils import read_cgal_polygon
from puzzle_tour_solver.utils.solution_utils import get_path_form_solution
from puzzle_tour_solver.generators.coverages.square import SquareCoverage
from puzzle_tour_solver.generators.grid.optimal_grid import SquareGridOptimizer
from puzzle_tour_solver.tsp.tsp_with_coverage import TSPWithCoverageSolver

instance_path = "xxx"
side_length = 1
grid_optimize_tries = 10

timelimit_tsp = 100
timelimit_lns = 100
timelimit_mip = 100

# Reading the polygon
polygon = read_cgal_polygon(file_name=instance_path)

# Finding the best grid for the polygon
grid = SquareGridOptimizer(
    side_length=side_length, polygon=polygon, tries=grid_optimize_tries
).optimize()

# Compute the "coverages" / trajectories for the tiles in the polygon.
coverage_generator = SquareCoverage(
    radius=side_length / 2, square_grid=grid
)
coverage_generator.compute_coverages()

# Initialize the local optimizer that will be used throughout this run.
local_opt = LocalOptimizer()

# Generate the dual grid graph
graph = CoverageGraph.from_grid(grid)
assert graph.check()

# Execute a TSP on the dual grid graph and replace adjacent visits with an appropriate tile
tsp_with_cov = TSPWithCoverageSolver()
tsp_with_cov_sol = tsp_with_cov.solve(graph,
                                      grid=grid,
                                      timelimit=timelimit_tsp)
initial_sol = tsp_with_cov_sol.coverages

# Do some local optimization to improve the current solution
initial_sol = local_opt(graph, initial_sol)

# Use LNS to further optimize our current solution
lns = LnsOptimizer(graph, initial_sol)
is_optimal = lns.optimize(
    iterations=100000,
    iteration_timelimit=5,
    timelimit=timelimit_lns
)
current_sol = lns.current_solution

# Do some local optimization to improve the current solution
current_sol = local_opt(graph, current_sol)

# Further improvement and lower bounds via MIP
model = Model(graph, current_sol)
ub, lb = model.optimize(timelimit=timelimit_mip)
sol = model.extract_solution()
sol = local_opt(graph, sol)

# Retrieve the path and objective value.
path = get_path_form_solution(sol, graph)
obj = graph.obj(sol)
```

### References
[1] Fekete, Sándor P., et al. "[A Closer Cut: Computing Near-Optimal Lawn Mowing Tours.](https://epubs.siam.org/doi/pdf/10.1137/1.9781611977561.ch1)" 2023 Proceedings of the Symposium on Algorithm Engineering and Experiments (ALENEX). Society for Industrial and Applied Mathematics, 2023.