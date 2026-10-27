import pygame

from graph import Graph
from models import Zone

ZONE_COLORS: dict[str, tuple[int, int, int]] = {
    "normal": (96, 165, 250),
    "restricted": (248, 113, 113),
    "priority": (250, 204, 21),
    "blocked": (107, 114, 128),
}

NAMED_COLORS = {
    "red": (248, 113, 113),
    "blue": (96, 165, 250),
    "green": (74, 222, 128),
    "yellow": (250, 204, 21),
    "orange": (251, 146, 60),
    "purple": (192, 132, 252),
    "gray": (107, 114, 128),
    "grey": (107, 114, 128),
    "cyan": (34, 211, 238),
    "pink": (244, 114, 182),
    "white": (255, 255, 255),
    "black": (30, 30, 30),
}

START_END_COLOR = (74, 222, 128)
CONNECTION_COLOR = (63, 63, 70)
LABEL_COLOR = (229, 231, 235)
ZONE_RADIUS = 20
MARGIN = 60


class Visualizer:
    """Renders the drone network and animates drone movements using pygame."""

    def __init__(
        self,
        graph: Graph,
        drone_image_path: str = "assets/drone.png",
        background_image_path: str = "assets/background.png",
        window_size: tuple[int, int] = (1200, 650),
        drone_size: tuple[int, int] = (60, 60),
        lerp_steps: int = 30,  # A ●──● B "A ilaa B waxaan rabaa 30 tallaabo."
        fps: int = 20,
    ) -> None:
        """Initialize the visualizer."""

        self.graph = graph
        self.drone_image_path = drone_image_path
        self.background_image_path = background_image_path
        self.window_width, self.window_height = window_size
        self.drone_size = drone_size
        self.lerp_steps = lerp_steps
        self.fps = fps

        self.screen: pygame.surface.Surface | None = None
        self.drone_image: pygame.surface.Surface | None = None
        self.background_image: pygame.surface.Surface | None = None
        self.zone_positions: dict[str, tuple[float, float]] = {}

        if graph.start_zone is None or graph.end_zone is None:
            raise ValueError("Graph must have start_zone and end_zone.")
        self.start_zone: Zone = graph.start_zone
        self.end_zone: Zone = graph.end_zone

    def play(self, output_lines: list[str], nb_drones: int) -> None:
        """Run the full animation for a completed simulation."""

        self._init_pygame()
        self._load_images()
        self._compute_zone_positions()
        static_layer = self._render_static_layer()

        drone_ids = [f"D{i + 1}" for i in range(nb_drones)]
        start_pos = self.zone_positions[self.start_zone.name]
        positions: dict[str, tuple[float, float]] = {
            drone_id: start_pos for drone_id in drone_ids
        }

        clock = pygame.time.Clock()
        running = True

        total_turns = len(output_lines)

        for turn_number, line in enumerate(output_lines, start=1):
            if not running:
                break

            print(f"Turn {turn_number}: {line}")

            moves = self._parse_turn_line(line)
            targets = dict(positions)
            for drone_id, destination_name in moves.items():
                targets[drone_id] = self._resolve_position(destination_name)

            running = self._animate_turn(
                static_layer,
                positions, targets,
                clock, turn_number,
                total_turns
            )
            positions = targets

        if running:
            self._wait_for_close()
        else:
            pygame.quit()

    def _init_pygame(self) -> None:
        """Initialize pygame and create the display window."""

        pygame.init()
        self.screen = pygame.display.set_mode(
            (self.window_width, self.window_height)
        )
        pygame.display.set_caption("Fly-in - Drone Network Simulation")

    def _load_images(self) -> None:
        """Load and scale the drone and background images from disk."""

        background = pygame.image.load(self.background_image_path).convert()
        self.background_image = pygame.transform.scale(
            background, (self.window_width, self.window_height)
        )

        drone = pygame.image.load(self.drone_image_path).convert_alpha()
        self.drone_image = pygame.transform.scale(drone, self.drone_size)

    def _compute_zone_positions(self) -> None:
        """Convert each zone's (x, y) coordinates int pixel postions."""

        xs = [zone.x for zone in self.graph.zones.values()]
        ys = [zone.y for zone in self.graph.zones.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(max_x - min_x, 1)
        span_y = max(max_y - min_y, 1)

        for zone in self.graph.zones.values():
            px = MARGIN + (zone.x - min_x) / span_x * (
                self.window_width - 4 * MARGIN
            )
            py = MARGIN + (max_y - zone.y) / span_y * (
                self.window_height - 4 * MARGIN
            )
            self.zone_positions[zone.name] = (px, py)

    def _zone_color(self, zone_name: str) -> tuple[int, int, int]:
        """Return the RGB color for a zone base on its type."""

        if zone_name in (self.start_zone.name, self.end_zone.name):
            return START_END_COLOR

        zone = self.graph.get_zone(zone_name)
        if zone.color is not None:
            return NAMED_COLORS.get(
                zone.color.lower(), ZONE_COLORS[zone.zone_type]
            )
        return ZONE_COLORS[zone.zone_type]

    def _render_static_layer(self) -> pygame.Surface:
        """Pre-render the background,
        connections, and zones onto one surface."""

        assert self.background_image is not None
        surface = pygame.Surface(
            (self.window_width, self.window_height)
        )
        surface.blit(self.background_image, (0, 0))

        for connection in self.graph.connections:
            pos_a = self.zone_positions[connection.zone_a.name]
            pos_b = self.zone_positions[connection.zone_b.name]
            pygame.draw.line(surface, CONNECTION_COLOR, pos_a, pos_b, 10)

        font = pygame.font.Font(None, 18)
        for zone in self.graph.zones.values():
            pos = self.zone_positions[zone.name]
            color = self._zone_color(zone.name)
            pygame.draw.circle(
                surface, color, (int(pos[0]), int(pos[1])), ZONE_RADIUS
            )

            label = font.render(zone.name, True, LABEL_COLOR)
            label_rect = label.get_rect(center=(pos[0], pos[1] + 42))
            surface.blit(label, label_rect)

        return surface

    def _draw_drone(self, position: tuple[float, float]) -> None:
        """Drow the drone image centered at a given pixel position."""

        assert self.drone_image is not None
        assert self.screen is not None
        rect = self.drone_image.get_rect(
            center=(int(position[0]), int(position[1]))
        )
        self.screen.blit(self.drone_image, rect)

    def _lerp(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        t: float,
    ) -> tuple[float, float]:
        """Linearly interpolate between two positions."""

        x = start[0] + t * (end[0] - start[0])
        y = start[1] + t * (end[1] - start[1])
        return (x, y)

    def _animate_turn(
        self,
        static_layer: pygame.Surface,
        positions: dict[str, tuple[float, float]],
        targets: dict[str, tuple[float, float]],
        clock: pygame.time.Clock,
        turn_number: int,
        total_turns: int,
    ) -> bool:
        """Animate all drones moving
        from their current positions to targets."""

        assert self.screen is not None
        font = pygame.font.Font(None, 40)

        for step in range(1, self.lerp_steps + 1):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False

            t = step / self.lerp_steps
            self.screen.blit(static_layer, (0, 0))

            for drone_id, start_pos in positions.items():
                end_pos = targets[drone_id]
                current_pos = self._lerp(start_pos, end_pos, t)
                self._draw_drone(current_pos)

            hud_txt = font.render(
                f"Turn: {turn_number}/{total_turns}", True, (229, 231, 235)
            )

            self.screen.blit(hud_txt, (16, 16))

            pygame.display.flip()
            clock.tick(self.fps)

        return True

    def _parse_turn_line(self, line: str) -> dict[str, str]:
        """Parse one line of Simulator
        output into drone-to-destination moves."""

        moves: dict[str, str] = {}
        if line.strip() == "":
            return moves

        for token in line.split():
            drone_id, _, destination = token.partition("-")
            moves[drone_id] = destination
        return moves

    def _resolve_position(self, name: str) -> tuple[float, float]:
        """Resolve a destination name to a pixel position."""

        if name in self.graph.zones:
            return self.zone_positions[name]

        zone_a_name, zone_b_name = name.split("-")

        pos_a = self.zone_positions[zone_a_name]
        pos_b = self.zone_positions[zone_b_name]
        return (
            (pos_a[0] + pos_b[0]) / 2,
            (pos_a[1] + pos_b[1]) / 2,
        )

    def _wait_for_close(self) -> None:
        """Keep the window open after the simulation ends, untill closed."""
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    waiting = False
        pygame.quit()
