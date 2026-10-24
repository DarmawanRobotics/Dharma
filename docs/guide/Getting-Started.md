# Getting Started

Run the whole stack on the simulator in a few minutes, then on a robot.

## 1. Get the workspace

The [Dharma hub](https://github.com/DarmawanRobotics/Dharma) is the workspace: `dharma.repos`
lists every stack repository, `external.repos` the Livox driver and FAST-LIO.

**Dev container** (Linux or macOS, no local ROS needed):

```bash
git clone https://github.com/DarmawanRobotics/Dharma.git && cd Dharma
scripts/dev.sh up        # imports the stack into src/, builds the image, starts the container
scripts/dev.sh build     # colcon build (Humble; --distro foxy or --distro jazzy)
scripts/dev.sh test      # colcon test + test-result
scripts/dev.sh shell     # a shell with ROS and the workspace sourced
scripts/dev.sh vnc       # desktop: vnc://localhost:5901 or http://localhost:6080/vnc.html
```

Foxy, Humble and Jazzy run side by side (`--distro foxy`: ports 5903 / 6082, `--distro jazzy`:
5902 / 6081) with separate build, install and log volumes. VS Code: _Reopen in Container_.

**Natively** (Ubuntu 20.04 + Foxy, 22.04 + Humble or 24.04 + Jazzy, also on the robot computer):

```bash
scripts/setup.sh check      # what is installed, what is missing
scripts/setup.sh install    # tools, repos, Livox SDK, rosdep, build
source install/setup.bash
```

## 2. Run on the simulator

```bash
ros2 launch robot_bringup sim.launch.py rviz:=true
```

This starts [dharma_sim](Simulation.md) (a kinematic robot with a simulated Mid-360 and drifting
odometry in a small mall) and the whole stack with odometry `external`. The simulator publishes
`/initialpose` while the robot is not localized, so localization starts by itself.

In RViz, the **Mission** panel drives the robot:

1. use _2D Goal Pose_ to fill in a goal, then **Go** (`planner/go_to`);
2. watch `navigation/status` and the planned path; press **E-STOP** on the **Safety** panel at
   any time, **Release**, then **Resume** on the Mission panel.

The same from a terminal:

```bash
ros2 service call /planner/go_to dharma_interfaces/srv/GoTo "{x: 4.5, y: 3.0, yaw: 3.14}"
ros2 topic echo /navigation/status
ros2 service call /control/estop/engage std_srvs/srv/Trigger
```

Add people with a scenario (`scenario:=person_crossing`) or by hand:

```bash
ros2 topic pub --once /sim/obstacles geometry_msgs/msg/PoseArray "{poses: [{position: {x: 2.0, y: -3.0}}]}"
```

## 3. On a robot

1. Make a product from the template and fill in the robot profile:
   [New Product from Template](New-Product-from-Template.md), [Robot Profile](Robot-Profile.md).
2. Measure the braking limits ([Robot Profile](Robot-Profile.md#measure-the-braking-limits)).
3. Map the site, record its tags, teach routes: [Mapping and Sites](Mapping-and-Sites.md).
4. `ros2 launch robot_bringup robot.launch.py site:=<site>`.

Keep a hardware e-stop at hand: Dharma's safety layer is a software channel, see
[Safety](Safety.md).
