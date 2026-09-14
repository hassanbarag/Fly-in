from collections import defaultdict

from models import Zone, Connection, Drone
from graph import Graph
from pathfinder import Pathfinder


MAX_TURNS_SAFETY_LIMIT = 10_000
MAX_DISTINCT_PATHS = 8  # cap on how many alternate routes we compute


class Simulator:
    """Runs the turn-based simulation of drones moving through the network."""

    def __init__(
        self, graph: Graph, nb_drones:  int, pathfinder: Pathfinder,
    ) -> None:
        """Initialize the simulator"""

        if graph.start_zone is None or graph.end_zone is None:
            raise ValueError("Graph must have start_zone and end_zone.")

        self.graph = graph
        self.start_zone: Zone = graph.start_zone
        self.end_zone: Zone = graph.end_zone
        self.drones = [
            Drone(f"D{i + 1}", graph.start_zone) for i in range(nb_drones)
        ]

        k = min(nb_drones, MAX_DISTINCT_PATHS)
        available_paths = pathfinder.k_shortest_paths(
            graph.start_zone.name, graph.end_zone.name, k,
        )

        self.paths: dict[str, list[Zone]] = {}
        self.path_index: dict[str, int] = {}
        for i, drone in enumerate(self.drones):
            assigned_path = available_paths[i % len(available_paths)]
            self.paths[drone.drone_id] = assigned_path
            self.path_index[drone.drone_id] = 0

        self.zone_occupancy: dict[str, int] = {name: 0 for name in graph.zones}
        self.link_occupancy: dict[frozenset, int] = {}
        self.turn = 0
        self.turn_history: list[dict] = []

    def run(self) -> list[str]:
        """Run the simulation untill all drones reach th end zone."""

        output_lines: list[str] = []

        while not all(drone.delivered for drone in self.drones):
            self.turn += 1
            if self.turn > MAX_TURNS_SAFETY_LIMIT:
                raise RuntimeError(
                    "Simulation exceeded the maximum turn limit "
                    "(possible deadlock)."
                )

            moves = self._run_one_turn()
            output_lines.append(" ".join(moves))

        return output_lines

    def _run_one_turn(self) -> list[str]:
        """Advance the simulation by one turn."""

        moves: list[str] = []
        just_arrived: set[str] = set()

        # Phase 0: advance drones already in multi-turn transit.
        for drone in self.drones:
            if drone.is_in_transit():
                arrived = drone.advance_transit()
                if arrived:
                    self.path_index[drone.drone_id] += 1
                    moves.append(
                        f"{drone.drone_id}-{drone.require_current_zone().name}"
                    )
                    just_arrived.add(drone.drone_id)
                    if drone.require_current_zone().name == self.end_zone.name:
                        drone.mark_delivered()

        active_drones = [
            drone
            for drone in self.drones
            if not drone.delivered
            and not drone.is_in_transit()
            and drone.drone_id not in just_arrived
        ]

        # Phase 1: release capacity for zones about to be left.
        working_zone_occ = dict(self.zone_occupancy)
        release_counts: dict[str, int] = defaultdict(int)
        for drone in active_drones:
            release_counts[drone.require_current_zone().name] += 1
        for zone_name, count in release_counts.items():
            if zone_name not in (
                self.start_zone.name, self.end_zone.name
            ):
                working_zone_occ[zone_name] -= count

        # Phase 2: commit moves in deterministic order (by drone_id).
        working_link_occ: dict[frozenset, int] = defaultdict(int)
        for drone in sorted(active_drones, key=lambda d: d.drone_id):
            moved = self._try_move_drone(
                drone, working_zone_occ, working_link_occ, moves
            )
            if not moved:
                zone_name = drone.require_current_zone().name
                if zone_name not in (
                    self.start_zone.name, self.end_zone.name
                ):
                    working_zone_occ[zone_name] += 1

        link_snapshot = {}
        for connection in self.graph.connections:
            link_snapshot[connection] = (
                working_link_occ.get(connection.key(), 0)
            )
        self.turn_history.append({
            "zones": dict(working_zone_occ),
            "links": link_snapshot,
        })

        self.zone_occupancy = working_zone_occ
        return moves

    def _try_move_drone(
        self,
        drone: Drone,
        working_zone_occ: dict[str, int],
        working_link_occ: dict[frozenset, int],
        moves: list[str],
    ) -> bool:
        """Attempt to move a single drone into its next path zone"""

        index = self.path_index[drone.drone_id]
        path = self.paths[drone.drone_id]
        next_zone = path[index + 1]
        connection = self._find_connection(
            drone.require_current_zone().name, next_zone.name)

        is_special = next_zone.name in (
            self.start_zone.name,
            self.end_zone.name,
        )
        zone_available = is_special or (
            working_zone_occ.get(next_zone.name, 0) < next_zone.max_drones
        )
        link_available = (
            working_link_occ[connection.key()] < connection.max_link_capacity
        )

        if not (zone_available and link_available):
            return False

        working_link_occ[connection.key()] += 1
        cost = next_zone.movement_cost()

        if cost is None:
            raise ValueError(
                f"Zone '{next_zone.name}' is blocked and cannot be entered."
            )

        if cost == 1:
            working_zone_occ[next_zone.name] = (
                working_zone_occ.get(next_zone.name, 0) + 1
            )
            drone.move_to(next_zone)
            self.path_index[drone.drone_id] += 1
            moves.append(f"{drone.drone_id}-{next_zone.name}")
            if next_zone.name == self.end_zone.name:
                drone.mark_delivered()
        else:
            if not is_special:
                working_zone_occ[next_zone.name] = (
                    working_zone_occ.get(next_zone.name, 0) + 1
                )
            drone.start_transit(connection, next_zone, cost - 1)
            connection_name = "-".join(
                sorted((connection.zone_a.name, connection.zone_b.name))
            )
            moves.append(f"{drone.drone_id}-{connection_name}")

        return True

    def _find_connection(
        self, zone_a_name: str, zone_b_name: str
    ) -> Connection:
        """find the connection linking two adjacent zones."""

        for connection in self.graph.get_neighbors(zone_a_name):
            if connection.involves(zone_b_name):
                return connection
        raise ValueError(
            f"No connection found between '{zone_a_name}' and '{zone_b_name}'."
        )
