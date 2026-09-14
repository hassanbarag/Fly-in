from models import Zone, Connection
from graph import Graph

VALID_ZONE_TYPES = ("normal", "blocked", "restricted", "priority")


class Parser:
    """Parsers a network definition file into a Graph object."""

    def __init__(self, filepath: str) -> None:
        """Initialize the parser with the path to the input file."""

        self.filepath = filepath
        self.graph = Graph()
        self.nb_drones: int = 0
        self._nb_drones_set: bool = False

    def parse(self) -> tuple[Graph, int]:
        """Parse the input file and return the
        resulting graph and drone count."""
        with open(self.filepath, "r", encoding="utf-8") as file:
            first_content_line = True
            for line_number, row_line in enumerate(file, start=1):
                line = row_line.strip()

                if line == "" or line.startswith("#"):
                    continue

                if first_content_line and not line.startswith("nb_drones:"):
                    raise ValueError(
                        f"Line {line_number}: the first line must define "
                        f"'nb_drones', found '{line}' instead."
                    )
                first_content_line = False

                self._parse_line(line, line_number)

        if not self._nb_drones_set:
            raise ValueError("Missing 'nb drones' declaration in the file.")

        self.graph.validate_complete()
        return self.graph, self.nb_drones

    def _parse_line(self, line: str, line_number: int) -> None:
        """Dispatch a single line to the correct parsinng method."""

        if line.startswith("nb_drones:"):
            self._parse_nb_drones(line, line_number)
        elif line.startswith("start_hub:"):
            self._parse_zone_line(
                line, line_number, is_start=True, is_end=False
            )
        elif line.startswith("end_hub:"):
            self._parse_zone_line(
                line, line_number, is_start=False, is_end=True
            )
        elif line.startswith("hub:"):
            self._parse_zone_line(
                line, line_number, is_start=False, is_end=False
            )
        elif line.startswith("connection:"):
            self._parse_connection_line(line, line_number)
        else:
            raise ValueError(
                f"Line {line_number}: unrecognized line format: '{line}'."
            )

    def _parse_nb_drones(self, line: str, line_number: int) -> None:
        """Parse the 'nb_drones: <n>' line."""

        if self._nb_drones_set:
            raise ValueError(
                f"Line {line_number}: 'nb_drones' is defined more than once."
            )

        _, _, value = line.partition(":")
        value = value.strip()

        if not value.isdigit() or int(value) <= 0:
            raise ValueError(
                f"Line {line_number}: 'nb_drones' must be a positive integer,"
                f"got '{value}'."
            )

        self.nb_drones = int(value)
        self._nb_drones_set = True

    def _parse_zone_line(
        self,
        line: str,
        line_number: int,
        is_start: bool,
        is_end:  bool,
    ) -> None:
        """Parse a zone definition line (start_hub / end_hub / hub)."""

        _, _, rest = line.partition(":")
        rest = rest.strip()

        if "[" in rest:
            body, _, bracket_part = rest.partition("[")
            rest = body.strip()
            if not bracket_part.endswith("]"):
                raise ValueError(
                    f"Line {line_number}: malformed metadata block "
                    f"(missing closing ']')."
                )

            metadata_str = bracket_part[:-1].strip()

        tokens = rest.split()
        if len(tokens) != 3:
            raise ValueError(
                f"Line {line_number}: expected '<name> <x> <y>', "
                f"got '{rest}'."
            )

        name, x_str, y_str = tokens
        if "-" in name:
            raise ValueError(
                f"Line {line_number}: zone name '{name}' cannot contain '-'."
            )
        if not x_str.lstrip("-").isdigit() or not y_str.lstrip("-").isdigit():
            raise ValueError(
                f"Line {line_number}: coordinates must be integers, "
                f"got '{x_str}', '{y_str}'."
            )

        metadata = self._parse_metadata(metadata_str, line_number)

        zone_type = metadata.get("zone", "normal")
        color = metadata.get("color")
        max_drones_str = metadata.get("max_drones", "1")

        if zone_type not in VALID_ZONE_TYPES:
            raise ValueError(
                f"Line {line_number}: invalid zone type '{zone_type}'."
                f"Must be one of {VALID_ZONE_TYPES}."
            )

        if not max_drones_str.isdigit() or int(max_drones_str) < 1:
            raise ValueError(
                f"Line {line_number}: max_drones must be a positive integer, "
                f"got '{max_drones_str}'."
            )

        max_drones = int(max_drones_str)
        if is_start or is_end:
            max_drones = 1

        zone = Zone(
            name=name,
            x=int(x_str),
            y=int(y_str),
            zone_type=zone_type,
            color=color,
            max_drones=max_drones,
        )
        self.graph.add_zone(zone, is_start=is_start, is_end=is_end)

    def _parse_connection_line(self, line: str, line_number: int) -> None:
        """Parse a 'connection: a-b [metadata]' line."""

        _, _, rest = line.partition(":")
        rest = rest.strip()

        metadata_str = ""

        if "[" in rest:
            body, _, bracket_part = rest.partition("[")
            rest = body.strip()
            if not bracket_part.endswith("]"):
                raise ValueError(
                    f"Line {line_number}: malformed metadata block "
                    f"(missing closing ']')."
                )
            metadata_str = bracket_part[:-1].strip()

        if "-" not in rest:
            raise ValueError(
                f"Line {line_number}: "
                f"expected '<zone1>-<zone2>', got '{rest}'."
            )

        zone_a_name, _, zone_b_name = rest.partition("-")
        zone_a_name = zone_a_name.strip()
        zone_b_name = zone_b_name.strip()

        zone_a = self.graph.get_zone(zone_a_name)
        zone_b = self.graph.get_zone(zone_b_name)

        metadata = self._parse_metadata(metadata_str, line_number)
        capacity_str = metadata.get("max_link_capacity", "1")

        if not capacity_str.isdigit() or int(capacity_str) < 1:
            raise ValueError(
                f"Line {line_number}: max_link_capacity must be a positive "
                f"integer, got '{capacity_str}'."
            )

        connection = Connection(
            zone_a, zone_b, max_link_capacity=int(capacity_str)
        )
        self.graph.add_connection(connection)

    def _parse_metadata(
        self, metadata_str: str, line_number: int
    ) -> dict[str, str]:
        """Parse a metadata block like 'zone=restricted color=red'."""

        metadata: dict[str, str] = {}
        if metadata_str == "":
            return metadata

        for token in metadata_str.split():
            if "=" not in token:
                raise ValueError(
                    f"Line {line_number} invalid metadata token '{token}', "
                    f"expected 'key=value'."
                )
            key, _, value = token.partition("=")
            metadata[key.strip()] = value.strip()

        return metadata
