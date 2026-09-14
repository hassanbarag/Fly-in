*This project has been created as part of the 42 curriculum by <hassamoh>.*

# Fly-in — Autonomous Drone Fleet Routing Simulation

## Description

**Fly-in** is a turn-based simulation engine that routes a fleet of autonomous
drones from a central base (`start_hub`) to a target delivery location
(`end_hub`), across a network of zones with varying movement costs, capacity
constraints, and access restrictions.

The goal is to move **all drones** from start to end in the **fewest possible
simulation turns**, while respecting:

- **Zone occupancy limits** (`max_drones`)
- **Connection (link) capacity limits** (`max_link_capacity`)
- **Zone-specific movement costs** (`normal`, `priority` = 1 turn,
  `restricted` = 2 turns, `blocked` = inaccessible)
- **Conflict-free, deterministic scheduling** — no two drones can violate a
  capacity constraint on the same turn
- **Distribution of drones across multiple distinct paths**, rather than
  funnelling every drone through a single route

The project is entirely **object-oriented**, fully **type-safe** (`mypy`),
`flake8`-compliant, and implements its own graph and pathfinding logic from
scratch — no `networkx`, `graphlib`, or similar graph libraries are used.

## Features

- **Custom text-based parser** for the network definition format, with
  precise, line-numbered error messages for malformed input
- **Graph representation** built entirely from scratch (adjacency lists,
  zone/connection lookups, duplicate and integrity validation)
- **Dijkstra's algorithm** for single-source shortest-cost pathfinding
- **Yen's k-shortest-paths algorithm** built on top of Dijkstra, to compute
  several distinct loopless routes so drones can be spread across the
  network instead of bottlenecking on one path
- **Turn-based simulation engine** that:
  - Releases zone capacity from drones leaving a zone before granting it to
    drones arriving, within the same turn
  - Resolves conflicts deterministically (by drone ID) when multiple drones
    compete for the same limited resource
  - Handles multi-turn transits through `restricted` zones correctly (a
    drone committed to a 2-turn crossing cannot be interrupted)
  - Detects unresolvable deadlocks via a safety turn-limit
- **Visual representation** via a `pygame` window: the network is drawn to
  scale from each zone's coordinates, drones are rendered as custom sprite
  images, and movement between turns is animated with smooth interpolation
  rather than instant jumps

## Instructions

### Requirements

- Python 3.10+
- `pygame` 

### Installation

```bash
make install
```

This installs all dependencies It only needs
to be run once (or again after adding a new dependency).

### Running the simulation

```bash
make run
```
By default this runs the `network.txt`

Or directly, without `make`:

```bash
python3 main.py network.txt
```

The program prints each turn's drone movements to the terminal as they
happen, and opens a `pygame` window animating the same moves visually.
Closing the window, or pressing `Ctrl+C` in the terminal, exits cleanly at
any point.

### Other Makefile targets

| Command           | Description                                              |
|-------------------|-----------------------------------------------------------|
| `make debug`      | Runs the simulation inside Python's `pdb` debugger        |
| `make clean`      | Removes `__pycache__` and `.mypy_cache` directories       |
| `make lint`       | Runs `flake8` and `mypy` with the required flags          |
| `make lint-strict`| Runs `flake8` and `mypy --strict` for stricter checking   |

### Network file format

See `maps/` The format is documented in full in the
project subject; in short:

```
nb_drones: <positive integer>
start_hub: <name> <x> <y> [metadata]
end_hub: <name> <x> <y> [metadata]
hub: <name> <x> <y> [zone=normal|restricted|priority|blocked color=<word> max_drones=<n>]
connection: <zone1>-<zone2> [max_link_capacity=<n>]
```

## Example Input & Expected Output

Given the following network file (`maps/easy/02_simple_fork.txt`):

```
# Easy Level 2: Simple fork with two paths
nb_drones: 4

start_hub: start 0 0 [color=green]
hub: junction 1 0 [color=yellow max_drones=2]
hub: path_a 2 1 [color=blue]
hub: path_b 2 -1 [color=blue]
end_hub: goal 3 0 [color=red]

connection: start-junction [max_link_capacity=2]
connection: junction-path_a
connection: junction-path_b
connection: path_a-goal
connection: path_b-goal
```

Running:

```bash
python3 main.py maps/easy/02_simple_fork.txt
```

Produces the following terminal output:

```
Turn 1: D1-junction D2-junction
Turn 2: D1-path_a D2-path_b D3-junction D4-junction
Turn 3: D1-goal D2-goal D3-path_a D4-path_b
Turn 4: D3-goal D4-goal
```

Each line represents one simulation turn. Each entry shows a drone and
the zone it moved to during that turn. Drones that do not move are omitted.
The simulation automatically distributes drones between the two available
paths (path_a and path_b) while respecting zone and connection capacity
limits. A pygame window also displays the same movements in real time.

## Algorithm Choices & Implementation Strategy

**Why Dijkstra instead of BFS:** zones have different movement costs
(`restricted` zones cost 2 turns instead of 1), so a plain breadth-first
search — which only minimizes the number of hops — does not necessarily
find the cheapest route. Dijkstra's algorithm, using a binary heap
(`heapq`) as its priority queue, correctly accounts for these weighted
costs in `O((V + E) log V)` time.

**Why Yen's algorithm for multiple paths:** the subject requires
distributing drones across multiple paths rather than funnelling all of
them through a single shortest route. Yen's algorithm repeatedly re-runs a
constrained version of Dijkstra (excluding zones/connections already used
by previously found routes) to discover the next-cheapest *distinct*
loopless path. This lets the simulator hand out drones round-robin across
several valid routes, significantly reducing congestion on any single
bottleneck zone or connection — while still fully respecting the original
capacity model already validated on a single path.

**Turn scheduling (avoiding conflicts and deadlocks):** each simulation
turn is processed in two phases. First, capacity is released for zones that
drones are about to leave, since the subject specifies that departing
drones free up their zone within the same turn they leave it. Second,
drones are processed in a fixed, deterministic order (sorted by drone ID),
so that when several drones compete for the same zone or connection
capacity, the outcome is always reproducible — never randomized. Drones
that cannot move this turn simply wait and retry the following turn. A
hard turn-count safety limit guards against unresolved deadlocks causing an
infinite loop.

**Complexity:** pathfinding is `O((V + E) log V)` per path computed (up to
a capped number of alternate paths, `MAX_DISTINCT_PATHS = 8`, since
computing more distinct routes than there are drones brings no benefit).
The simulation loop itself is `O(D)` per turn, where `D` is the number of
active drones, since each drone's move is resolved independently against
pre-computed occupancy dictionaries rather than recomputing the graph.
Paths are computed once per drone at startup and cached for the entire run,
not recalculated turn-by-turn.

## Visual Representation

The simulation is rendered live using `pygame`:

- Each zone is drawn as a colored circle at a position scaled from its
  `(x, y)` coordinates, colored according to its type (`normal`,
  `restricted`, `priority`, `blocked`, or start/end).
- Connections are drawn as lines between zones.
- The static layer (background, zones, connections) is pre-rendered once
  per run and cached, rather than redrawn from scratch every frame.
- Each drone is rendered using a custom sprite image, and its movement
  between two zones each turn is animated using linear interpolation
  (`lerp`) across a fixed number of frames, producing smooth, continuous
  motion rather than instant teleporting between zones — making it much
  easier to visually follow congestion, waiting, and path distribution as
  they happen.
- A live turn counter (`Turn: x/y`) is displayed on screen, and the
  corresponding text output is printed to the terminal in sync with the
  animation, so both views stay aligned.

This makes it possible to visually confirm, at a glance, that drones are
being distributed across distinct paths, that capacity limits are being
respected (drones visibly waiting rather than overlapping a full zone), and
that restricted-zone transits correctly take two turns.

## Resources

- *Introduction to Algorithms* (CLRS) — Dijkstra's algorithm reference
- Yen, J. Y. (1971). *"Finding the K Shortest Loopless Paths in a Network."*
  Management Science — original description of the k-shortest-paths method
  adapted here
- [Python `heapq` documentation](https://docs.python.org/3/library/heapq.html)
- [Pygame documentation](https://www.pygame.org/docs/)
- [PEP 257 – Docstring Conventions](https://peps.python.org/pep-0257/)

### AI usage

AI assistance (Claude) was used throughout this project as a learning and
design aid, in line with the curriculum's AI usage guidelines:

- **Concept explanations**: understanding graph theory fundamentals,
  Dijkstra's algorithm, and Yen's k-shortest-paths algorithm before any
  code was written.
- **Design review**: discussing class responsibilities and module
  boundaries (e.g. why `Zone`/`Connection` are separate from `Graph`
  logic) before implementation.

- **Pygame guidance**: explaining `pygame` concepts (the game loop, image
  loading/scaling, linear interpolation for animation) that were then
  implemented and tested independently.

All source code in this repository was written and typed by hand by the
author(s) listed above, with the understanding and ability to explain any
part of it during peer evaluation.
