import sys
import pygame
from parser import Parser
from pathfinder import Pathfinder
from simulator import Simulator
from visualizer import Visualizer


def _print_capacity_info(simulator: Simulator, turn_index: int) -> None:
    snapshot = simulator.turn_history[turn_index]
    zone_parts = []
    for zone_name, count, in snapshot["zones"].items():
        zone = simulator.graph.get_zone(zone_name)
        zone_parts.append(
            f"Zone {zone_name}: {count}/ max drones {zone.max_drones}"
        )

    link_parts = []
    for connection, count in snapshot["links"].items():
        name = f"{connection.zone_a.name}-{connection.zone_b.name}"
        link_parts.append(
            f"Connection {name}:"
            f"{count}/ capacity use {connection.max_link_capacity}"
        )

    print(", ".join(zone_parts + link_parts))


def main() -> None:
    """Parse the input file, run the simulation, and display the result."""

    args = sys.argv[1:]
    capacity_info = "--capacity-info" in args
    filtered_args = [arg for arg in args if arg != "--capacity-info"]

    if len(filtered_args) != 1:
        print(f"Usage: python3 {sys.argv[0]} [--capacity-info] <network_file>")
        sys.exit(1)

    filepath = filtered_args[0]
    """if len(sys.argv) != 2:
        print(f"Usage: python3 {sys.argv[0]} <network_file>")
        sys.exit(1)"""

    """filepath = sys.argv[1]"""

    try:
        parser = Parser(filepath)
        graph, nb_drones = parser.parse()
    except (ValueError, FileNotFoundError, OSError) as error:
        print(f"Error while parsing '{filepath}': {error}")
        sys.exit(1)

    try:
        pathfinder = Pathfinder(graph)
        simulator = Simulator(graph, nb_drones, pathfinder)
        output_lines = simulator.run()
    except (ValueError, RuntimeError) as error:
        print(f"Error during simulation: {error}")
        sys.exit(1)

    for turn_index, line in enumerate(output_lines):
        if capacity_info:
            _print_capacity_info(simulator, turn_index)

    try:
        visualizer = Visualizer(graph)
        visualizer.play(output_lines, nb_drones)
    except (FileNotFoundError, OSError) as error:
        print(
            f"Warning: could not launch visualizer ({error}). "
            f"Text output above is still valid."
        )

    except KeyboardInterrupt:
        print("\nVisualization interrupted by user. Exiting cleanly.")
        pygame.quit()

    print(f"\nSimulation complete in {len(output_lines)} turns.")


if __name__ == "__main__":
    main()
