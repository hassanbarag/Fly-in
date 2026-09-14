from typing import Optional

from models import Zone, Connection


class Graph:
    """Represents the full network of zones and connections."""

    def __init__(self) -> None:
        self.zones: dict[str, Zone] = {}
        self.connections: list[Connection] = []
        self.adjacency: dict[str, list[Connection]] = {}
        self.start_zone: Optional[Zone] = None
        self.end_zone: Optional[Zone] = None

    def add_zone(
        self,
        zone: Zone,
        is_start: bool = False,
        is_end: bool = False,
    ) -> None:
        """Add a zone to the graph."""

        if zone.name in self.zones:
            raise ValueError(f"Duplicate zone name: '{zone.name}'.")

        self.zones[zone.name] = zone
        self.adjacency[zone.name] = []

        if is_start:
            if self.start_zone is not None:
                raise ValueError("A start zone is already defined.")
            self.start_zone = zone

        if is_end:
            if self.end_zone is not None:
                raise ValueError("An end zone is already defined.")
            self.end_zone = zone

    def add_connection(self, connection: Connection) -> None:
        """Add a connection to the graph."""

        if connection.zone_a.name not in self.zones:
            raise ValueError(
                f"Uknown zone '{connection.zone_a.name}' in connection."
            )
        if connection.zone_b.name not in self.zones:
            raise ValueError(
                f"Unknow zone '{connection.zone_b.name}' in connection."
            )

        for existing in self.connections:
            if existing.key() == connection.key():
                raise ValueError(
                    f"Duplicate connection: "
                    f"'{connection.zone_a.name}-{connection.zone_b.name}'."
                )

        self.connections.append(connection)
        self.adjacency[connection.zone_a.name].append(connection)
        self.adjacency[connection.zone_b.name].append(connection)

    def get_zone(self, name: str) -> Zone:
        """Returns the zone with the given name."""

        if name not in self.zones:
            raise ValueError(f"Uknown zone: '{name}'.")
        return self.zones[name]

    def get_neighbors(self, zone_name: str) -> list[Connection]:
        """Return all connection leaving the given zone."""

        if zone_name not in self.adjacency:
            raise ValueError(f"Uknown zone: '{zone_name}'.")
        return self.adjacency[zone_name]

    def validate_complete(self) -> None:
        """Check that poth a start zone and an end zone have been defined."""

        if self.start_zone is None:
            raise ValueError("No start zone (start_hub) was defined.")
        if self.end_zone is None:
            raise ValueError("No end zone (end_hub) was defined.")
