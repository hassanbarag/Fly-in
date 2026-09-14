import heapq

from models import Zone
from graph import Graph
from models import Connection


class Pathfinder:
    """Compute the cheapest path between two zones
    using Dijkstra's algorithm"""

    def __init__(self, graph: Graph) -> None:
        """Initialize the pathfinder with a graph to search over."""

        self.graph = graph

    def shortest_path(self, start_name: str, end_name: str) -> list[Zone]:
        """Find the cheapest path between two zone."""

        path = self._dijkstra_excluding(
            start_name, end_name, set(), set()
        )
        if path is None:
            raise ValueError(
                f"No path found from '{start_name}' to '{end_name}'."
            )
        return path

    def k_shortest_paths(
        self, start_name: str, end_name: str, k: int
    ) -> list[list[Zone]]:
        """Find up to k distinct loopless paths,
        cheapest first (yen's algorithm)."""

        first_path = self._dijkstra_excluding(
            start_name, end_name, set(), set()
        )
        if first_path is None:
            raise ValueError(
                f"No path found from '{start_name}' to '{end_name}'."
            )

        found_paths: list[list[Zone]] = [first_path]
        candidates: list[tuple[int, list[Zone]]] = []

        for _ in range(1, k):
            previous_path = found_paths[-1]
            for i in range(len(previous_path) - 1):
                spur_node = previous_path[i]
                root_path = previous_path[: i + 1]
                root_names = [zone.name for zone in root_path]

                excluded_connections: set[frozenset] = set()
                for path in found_paths:
                    if (
                        [z.name for z in path[: i + 1]] == root_names
                        and len(path) > i + 1
                    ):
                        conn = self._connection_between(
                            path[i].name, path[i + 1].name
                        )
                        if conn is not None:
                            excluded_connections.add(conn.key())

                excluded_zone = {zone.name for zone in root_path[: -1]}

                spur_path = self._dijkstra_excluding(
                    spur_node.name, end_name,
                    excluded_zone, excluded_connections
                )

                if spur_path is not None:
                    total_path = root_path[: -1] + spur_path
                    total_names = [zone.name for zone in total_path]

                    already_known = any(
                        [z.name for z in p] == total_names
                        for p in found_paths
                    ) or any(
                        [z.name for z in p] == total_names
                        for _, p in candidates
                    )
                    if not already_known:
                        cost = self._path_cost(total_path)
                        candidates.append((cost, total_path))

            if not candidates:
                break

            candidates.sort(key=lambda item: item[0])
            _, best_path = candidates.pop(0)
            found_paths.append(best_path)

        return found_paths

    def _dijkstra_excluding(
        self,
        start_name: str,
        end_name: str,
        excluded_zones: set,
        excluded_connections: set,
    ) -> list[Zone] | None:
        """Run Dijkstra's algorithm while
        ignoring certain zones/connections."""

        distances: dict[str, int] = {start_name: 0}
        previous: dict[str, str] = {}
        visited: set[str] = set()
        queue: list[tuple[int, str]] = [(0, start_name)]

        while queue:
            current_dist, current_name = heapq.heappop(queue)

            if current_name in visited:
                continue
            visited.add(current_name)

            if current_name == end_name:
                break

            for connection in self.graph.get_neighbors(current_name):
                if connection.key() in excluded_connections:
                    continue

                neighbor = connection.other_side(current_name)

                if neighbor.name in excluded_zones or neighbor.is_blocked():
                    continue

                move_cost = neighbor.movement_cost()
                if move_cost is None:
                    continue

                new_dist = current_dist + move_cost
                if (
                    neighbor.name not in distances
                    or new_dist < distances[neighbor.name]
                ):
                    distances[neighbor.name] = new_dist
                    previous[neighbor.name] = current_name
                    heapq.heappush(queue, (new_dist, neighbor.name))

        if end_name not in distances:
            return None

        return self._reconstruct_path(previous, start_name, end_name)

    def _reconstruct_path(
        self,
        previous: dict[str, str],
        start_name: str,
        end_name: str,
    ) -> list[Zone]:
        """Rebuild the path from the
        previous-node map produced by Dijkstra."""

        path_names = [end_name]
        while path_names[-1] != start_name:
            path_names.append(previous[path_names[-1]])
        path_names.reverse()

        return [self.graph.get_zone(name) for name in path_names]

    def _connection_between(
        self, zone_a_name: str, zone_b_name: str
    ) -> Connection | None:
        """Find th connection linking two adjacent zones if any."""

        for connection in self.graph.get_neighbors(zone_a_name):
            if connection.involves(zone_b_name):
                return connection

        return None

    def _path_cost(self, path: list[Zone]) -> int:
        """Compute the total movement cost of a path"""

        total = 0
        for zone in path[1:]:
            cost = zone.movement_cost()

            if cost is None:
                continue

            total += cost
        return total
