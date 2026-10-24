"""An occupancy grid of a simulator world (the map scan matching runs against in E3)."""

import numpy as np

from dharma_sim.core.world import World
from dharma_utils.grid import GridSpec


def rasterize(world: World, resolution: float = 0.05, pad: float = 1.0):
    """Return (occupied bool grid with rows = y, GridSpec) of the walls and pillars."""
    seg, circ = world.segments, world.circles
    xs = np.concatenate([seg[:, 0], seg[:, 2], circ[:, 0] - circ[:, 2], circ[:, 0] + circ[:, 2]])
    ys = np.concatenate([seg[:, 1], seg[:, 3], circ[:, 1] - circ[:, 2], circ[:, 1] + circ[:, 2]])
    x0, y0 = xs.min() - pad, ys.min() - pad
    width = int(np.ceil((xs.max() + pad - x0) / resolution))
    height = int(np.ceil((ys.max() + pad - y0) / resolution))
    spec = GridSpec(resolution, float(x0), float(y0), width, height)
    occupied = np.zeros((height, width), dtype=bool)
    for x_a, y_a, x_b, y_b, _ in seg:
        n = int(np.ceil(np.hypot(x_b - x_a, y_b - y_a) / (0.25 * resolution))) + 1
        line = np.column_stack((np.linspace(x_a, x_b, n), np.linspace(y_a, y_b, n)))
        _mark(occupied, spec, line)
    centers = spec.centers(np.indices((width, height)).reshape(2, -1).T)
    for cx, cy, r, _ in circ:
        near = np.hypot(centers[:, 0] - cx, centers[:, 1] - cy) <= r + 0.5 * resolution
        _mark(occupied, spec, centers[near])
    return occupied, spec


def _mark(occupied: np.ndarray, spec: GridSpec, xy: np.ndarray):
    cells = spec.cells(xy)
    cells = cells[spec.inside(cells)]
    occupied[cells[:, 1], cells[:, 0]] = True
