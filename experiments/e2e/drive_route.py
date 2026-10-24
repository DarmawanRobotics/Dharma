"""
End-to-end check on the real nodes: drive a route of `ros2 launch robot_bringup sim.launch.py`.

Run it next to the launch (same ROS domain, workspace sourced):

    ros2 launch robot_bringup sim.launch.py scenario:=person_crossing params_file:=<file>
    python3 experiments/e2e/drive_route.py --scenario person_crossing

It waits until localization is up, loads the site's route (navigation/load_path), starts
navigation and records the true pose (sim/ground_truth), navigation/status, control/status
and sim/collision until the goal, a final state or the timeout. Written to
results/e2e_sim.csv: completion, time, stops, smallest clearance to the scenario's obstacles
and to the walls, largest distance from the route, protective field states seen.
"""

import argparse
from collections import Counter
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import common  # noqa: F401  (puts the stack on sys.path)
from common.metrics import box_clearance, write_rows
from common.worlds import robot, sim_file
from geometry_msgs.msg import PoseStamped
import numpy as np
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
from std_srvs.srv import Trigger

from dharma_interfaces.msg import ControlStatus, LocalizationStatus, NavigationStatus
from dharma_interfaces.srv import LoadPath
from dharma_sim.core.scenario import load_scenario
from dharma_sim.core.world import World
from dharma_utils.io import read_route
from dharma_utils.math import Pose2D, yaw_from_quat
from dharma_utils.ros import LATCHED

FIELD = {v: k[6:].lower() for k, v in vars(ControlStatus).items() if k.startswith('FIELD_')}
DONE = (NavigationStatus.GOAL_REACHED, NavigationStatus.FAILED, NavigationStatus.OFF_PATH)


class Recorder(Node):
    """Collects what the run does."""

    def __init__(self):
        super().__init__('e2e_drive_route')
        self.truth: list[tuple[float, Pose2D]] = []
        self.first: float | None = None  # first ground truth stamp: the scenario clock starts
        self.nav: list[int] = []
        self.fields: Counter = Counter()
        self.localized = False
        self.collided = False
        self.create_subscription(PoseStamped, 'sim/ground_truth', self.on_truth, 50)
        self.create_subscription(NavigationStatus, 'navigation/status', self.on_nav, LATCHED)
        self.create_subscription(ControlStatus, 'control/status', self.on_control, LATCHED)
        self.create_subscription(LocalizationStatus, 'localization/status', self.on_loc, LATCHED)
        self.create_subscription(Bool, 'sim/collision', self.on_collision, LATCHED)

    def on_truth(self, msg: PoseStamped):
        """Keep the true pose with its stamp."""
        p, q = msg.pose.position, msg.pose.orientation
        stamp = msg.header.stamp.sec + 1e-9 * msg.header.stamp.nanosec
        self.first = stamp if self.first is None else self.first
        self.truth.append((stamp, Pose2D(p.x, p.y, yaw_from_quat((q.x, q.y, q.z, q.w)))))

    def on_nav(self, msg: NavigationStatus):
        """Keep the follower states."""
        self.nav.append(int(msg.state))

    def on_control(self, msg: ControlStatus):
        """Count the protective field states."""
        self.fields[FIELD.get(int(msg.field), str(msg.field))] += 1

    def on_loc(self, msg: LocalizationStatus):
        """Note when localization is up."""
        self.localized = msg.state != LocalizationStatus.NONE

    def on_collision(self, msg: Bool):
        """Latch a collision of the simulated body."""
        self.collided = self.collided or bool(msg.data)

    def call(self, srv_type, name: str, request, timeout: float = 10.0):
        """Call a service and return the response (None on timeout)."""
        client = self.create_client(srv_type, name)
        if not client.wait_for_service(timeout_sec=timeout):
            return None
        future = client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=timeout)
        return future.result()


def spin_until(node: Recorder, condition, timeout: float) -> bool:
    """Spin until condition() or timeout (s); return condition()."""
    end = time.monotonic() + timeout
    while time.monotonic() < end and not condition():
        rclpy.spin_once(node, timeout_sec=0.05)
    return condition()


def measure(node: Recorder, scenario: str, route_xy: np.ndarray) -> dict:
    """Return the metrics of the recorded run."""
    world = World.from_yaml(str(sim_file('config/worlds/mall_loop.yaml')))
    scen = load_scenario(str(sim_file(f'config/scenarios/{scenario}.yaml'))) if scenario else None
    t = np.array([s for s, _ in node.truth])
    poses = [p for _, p in node.truth]
    xy = np.array([(p.x, p.y) for p in poses])
    fp = robot().footprint
    start = node.first
    people = [box_clearance(fp, p, scen.circles_at(s - start)) if scen else np.inf
              for s, p in zip(t, poses, strict=True)]  # fmt: skip
    walls = [box_clearance(fp, p, _wall_points(world)) for p in poses[::10]]
    speed = np.hypot(*np.diff(xy, axis=0).T) / np.maximum(np.diff(t), 1e-3)
    offset = [float(np.min(np.hypot(*(route_xy - q).T))) for q in xy[::10]]
    moved = np.flatnonzero(speed > 0.05)
    t0 = t[moved[0]] if len(moved) else t[0]
    return {
        'completed': NavigationStatus.GOAL_REACHED in node.nav,
        'time_sec': float(t[-1] - t0),
        'distance_m': float(np.sum(np.hypot(*np.diff(xy, axis=0).T))),
        'stops': _stops(speed),
        'min_clearance_obstacles_m': float(np.min(people)),
        'min_clearance_walls_m': float(np.min(walls)),
        'max_offset_m': float(np.max(offset)),
        'collided': node.collided,
        'fields': ' '.join(f'{k}:{v}' for k, v in sorted(node.fields.items())),
        'final_state': node.nav[-1] if node.nav else -1,
    }


def _wall_points(world: World) -> np.ndarray:
    """Return the walls as small circles every 5 cm (for the clearance) plus the pillars."""
    pts = []
    for x0, y0, x1, y1, _ in world.segments:
        n = int(np.hypot(x1 - x0, y1 - y0) / 0.05) + 1
        pts += [(x, y, 0.0, 1.0) for x, y in zip(np.linspace(x0, x1, n), np.linspace(y0, y1, n),
                                                 strict=True)]  # fmt: skip
    return np.vstack([np.array(pts), world.circles])


def _stops(speed: np.ndarray) -> int:
    smooth = np.convolve(speed, np.ones(10) / 10.0, mode='same')
    stops, moving = 0, False
    for v in smooth:
        if v > 0.15:
            moving = True
        elif v < 0.05 and moving:
            stops, moving = stops + 1, False
    return stops


def main():
    """Drive the route and write results/e2e_sim.csv."""
    parser = argparse.ArgumentParser(description='drive the sim route on the real nodes')
    parser.add_argument('--scenario', default='person_crossing')
    parser.add_argument('--route', default='mall_loop/routes/mall_loop.csv')
    parser.add_argument('--timeout', type=float, default=300.0)
    args = parser.parse_args()
    rclpy.init()
    node = Recorder()
    if not spin_until(node, lambda: node.localized, 90.0):
        raise SystemExit('localization did not come up')
    loaded = node.call(LoadPath, 'navigation/load_path', LoadPath.Request(path=args.route))
    if loaded is None or not loaded.success:
        raise SystemExit(f'load_path failed: {loaded.message if loaded else "no service"}')
    spin_until(node, lambda: False, 2.0)
    started = node.call(Trigger, 'navigation/start', Trigger.Request())
    if started is None or not started.success:
        raise SystemExit(f'start failed: {started.message if started else "no service"}')
    node.truth.clear()
    spin_until(node, lambda: bool(node.nav) and node.nav[-1] in DONE, args.timeout)
    route = read_route(str(sim_file('config/routes/mall_loop.csv')))
    route_xy = np.array([(p.x, p.y) for p in route])
    row = {'scenario': args.scenario, **measure(node, args.scenario, route_xy)}
    write_rows('e2e_sim', [row])
    sys.stdout.write(f'{row}\n')
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
