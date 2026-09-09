"""
Vehicular mobility model (Section 3.1).

Nodes move according to a random waypoint model with velocity
v_i ~ Uniform(5, 30) m/s. Path loss follows
    p_ij(t) = min(1, p0 * (d_ij(t)/d0)^alpha),
alpha=3.5, p0=0.05, d0=50m (see core/channel_models.PathLossModel).

An optional SUMO trace loader is provided for users who have real SUMO
FCD-export XML traces (`--mobility-trace path/to/fcd.xml`); if SUMO/its
trace files aren't available, `RandomWaypointMobility` below is a
self-contained substitute requiring no external simulator, and is what
`run_sim.py` uses by default.
"""
from __future__ import annotations
import numpy as np


class RandomWaypointMobility:
    def __init__(self, area_size: float = 1000.0, v_low: float = 5.0,
                 v_high: float = 30.0, rng: np.random.Generator | None = None):
        self.area_size = area_size
        self.v_low, self.v_high = v_low, v_high
        self.rng = rng or np.random.default_rng()
        self.positions: dict[int, np.ndarray] = {}
        self.targets: dict[int, np.ndarray] = {}
        self.speeds: dict[int, float] = {}

    def _random_point(self) -> np.ndarray:
        return self.rng.uniform(0, self.area_size, size=2)

    def add_node(self, node_id: int) -> None:
        self.positions[node_id] = self._random_point()
        self.targets[node_id] = self._random_point()
        self.speeds[node_id] = float(self.rng.uniform(self.v_low, self.v_high))

    def remove_node(self, node_id: int) -> None:
        self.positions.pop(node_id, None)
        self.targets.pop(node_id, None)
        self.speeds.pop(node_id, None)

    def step(self, dt: float = 1.0) -> dict[int, np.ndarray]:
        for nid, pos in self.positions.items():
            target = self.targets[nid]
            direction = target - pos
            dist = np.linalg.norm(direction)
            if dist < 1e-6:
                self.targets[nid] = self._random_point()
                self.speeds[nid] = float(self.rng.uniform(self.v_low, self.v_high))
                continue
            step_dist = self.speeds[nid] * dt
            if step_dist >= dist:
                self.positions[nid] = target
            else:
                self.positions[nid] = pos + direction / dist * step_dist
        return {nid: pos.copy() for nid, pos in self.positions.items()}

    def velocities(self) -> dict[int, float]:
        return dict(self.speeds)

    def pairwise_distance(self, a: int, b: int) -> float:
        return float(np.linalg.norm(self.positions[a] - self.positions[b]))


def load_sumo_fcd_trace(path: str):
    """
    Optional loader for real SUMO floating-car-data (FCD) XML traces, for
    users who have access to SUMO and want to replace RandomWaypointMobility
    with recorded traces. Requires `sumolib`/`xml.etree` and a real .xml
    export from `sumo --fcd-output`; not needed to run the default sim.
    """
    import xml.etree.ElementTree as ET
    tree = ET.parse(path)
    root = tree.getroot()
    trace: dict[float, dict[str, tuple[float, float]]] = {}
    for timestep in root.findall('timestep'):
        t = float(timestep.get('time'))
        frame = {}
        for veh in timestep.findall('vehicle'):
            frame[veh.get('id')] = (float(veh.get('x')), float(veh.get('y')))
        trace[t] = frame
    return trace
