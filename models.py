from typing import Optional


VALID_ZONE_TYPES = ("normal", "blocked", "restricted", "priority")

MOVEMENT_COSTS = {
    "normal": 1,
    "restricted": 2,
    "priority": 1,
    "blocked": None,  # blocked zones cannot be entered
}


class Zone:
    """Represents a zone (hub) in the drone network."""

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        zone_type: str = "normal",
        color: Optional[str] = None,
        max_drones: int = 1,
    ) -> None:
        if zone_type not in VALID_ZONE_TYPES:
            raise ValueError(
                f"Invalid zone type '{zone_type}' for zone '{name}'. "
                f"Must be one of {VALID_ZONE_TYPES}."
            )
        if max_drones < 1:
            raise ValueError(
                f"max_drones must be a positive integer for zone '{name}', "
                f"got {max_drones}."
            )

        self.name = name
        self.x = x
        self.y = y
        self.zone_type = zone_type
        self.color = color
        self.max_drones = max_drones

    def movement_cost(self) -> Optional[int]:
        """Returns the turn cost to move into this zone."""
        return MOVEMENT_COSTS[self.zone_type]

    def is_blocked(self) -> bool:
        """Check whether this zone is inaccessible."""
        return self.zone_type == "blocked"

    def has_capacity(self, current_occupants: int) -> bool:
        """Check if the zone can accept one more drone."""
        return current_occupants < self.max_drones


class Connection:
    """Represents a bidirectional connection (edge) between two zones."""

    def __init__(
        self,
        zone_a: Zone,
        zone_b: Zone,
        max_link_capacity: int = 1,
    ) -> None:
        if max_link_capacity < 1:
            raise ValueError(
                f"max_link_capacity must be a positive integer for "
                f"connection '{zone_a.name}-{zone_b.name}', "
                f"got {max_link_capacity}."
            )
        if zone_a.name == zone_b.name:
            raise ValueError(
                f"A zone cannot be connected to itself: '{zone_a.name}'."
            )

        self.zone_a = zone_a
        self.zone_b = zone_b
        self.max_link_capacity = max_link_capacity

    def key(self) -> frozenset:
        """Returns a direction-independent identifier for this connection."""
        return frozenset({self.zone_a.name, self.zone_b.name})

    def involves(self, zone_name: str) -> bool:
        """Check whether this connection touches the given zone."""
        return zone_name in (self.zone_a.name, self.zone_b.name)

    def other_side(self, zone_name: str) -> Zone:
        """Returns the zone on the other end of the connection."""
        if zone_name == self.zone_a.name:
            return self.zone_b
        if zone_name == self.zone_b.name:
            return self.zone_a
        raise ValueError(
            f"Zone '{zone_name}' is not part of this connection."
        )


class Drone:
    """Represents a single drone moving through the network."""

    def __init__(self, drone_id: str, start_zone: Zone) -> None:
        if not drone_id:
            raise ValueError("drone_id cannot be empty.")

        self.drone_id = drone_id
        self.current_zone: Optional[Zone] = start_zone
        self.delivered = False
        self.history: list[str] = []

        # Used when the drone is crossing a multi-turn connection
        # (e.g. toward a restricted zone).
        self.in_transit_connection: Optional[Connection] = None
        self.transit_destination: Optional[Zone] = None
        self.transit_remaining: int = 0

    def is_in_transit(self) -> bool:
        """Check whether the drone is currently crossing a connection."""
        return self.in_transit_connection is not None

    def start_transit(
        self,
        connection: Connection,
        destination: Zone,
        turns: int,
    ) -> None:
        """Start a multi-turn move toward a restricted zone."""
        if self.is_in_transit():
            raise ValueError(
                f"Drone '{self.drone_id}' is already in transit."
            )

        # Drone-ku ma joogaa isla meesh uu u socdo?
        if self.current_zone == destination:
            raise ValueError(
                f"Drone '{self.drone_id}'"
                f"is already in zone '{destination.name}'"
            )

        # Destination-ku ma ka mid yahay connection-kan?
        if destination not in (connection.zone_a, connection.zone_b):
            raise ValueError(
                f"Drone '{destination.name}'"
                f"is not connected by this connection."
            )

        # Drone-ku ma ka bilaabanayaa connection-kan?
        if self.current_zone not in (connection.zone_a, connection.zone_b):
            raise ValueError(
                f"Drone '{self.drone_id}'"
                f"is not at one end of this connection."
            )

        if turns < 1:
            raise ValueError("Turns must be at least 1.")

        # Bilow safarka
        self.current_zone = None
        self.in_transit_connection = connection
        self.transit_destination = destination
        self.transit_remaining = turns
        self.history.append(
            f"{self.drone_id} started moving to {destination.name}"
        )

    def require_current_zone(self) -> Zone:
        """Return the drone's current zone (must not be in transit)."""
        if self.current_zone is None:
            raise ValueError(f"Drone '{self.drone_id}' is in transit.")
        return self.current_zone

    def move_to(self, zone: Zone) -> None:
        """Move the drone directly into a new zone (single-turn move)."""

        self.history.append(f"{self.drone_id}-{zone.name}")
        if zone.zone_type == "blocked":
            raise ValueError(
                f"Drone '{self.drone_id}' cannot move into a blocked zone."
            )
        self.current_zone = zone

    def advance_transit(self) -> bool:
        """Advance the drone by one turn while in transit."""

        if not self.is_in_transit():
            raise ValueError(
                f"Drone '{self.drone_id}' is not currently in transit."
            )

        self.transit_remaining -= 1

        if self.transit_remaining <= 0:
            destination = self.transit_destination

            if destination is None:
                raise ValueError("Transit destination is missing.")

            self.current_zone = destination
            self.in_transit_connection = None
            self.transit_destination = None
            self.history.append(f"{self.drone_id}-{destination.name}")
            return True
        return False

    def mark_delivered(self) -> None:
        """Mark the drone as having reached the end zone."""
        self.delivered = True
