# Dharma

Dharma is a robot-agnostic ROS 2 autonomy stack (Humble and Jazzy) for legged and wheeled
service robots in public spaces: LiDAR-inertial odometry, fiducial localization, occupancy
mapping with sites, path planning and following, a safety mux with a protective field, health
monitoring, RViz panels and a simulator. Nothing in it is specific to one robot: geometry,
limits and frames come from one [robot profile](Robot-Profile). A product (a tour guide, an
inspection robot) is a repository made from the [template](New-Product-from-Template).

![Layered architecture](images/layers.svg)

## Start here

| I want to                        | Read                                                                                   |
| -------------------------------- | -------------------------------------------------------------------------------------- |
| run the stack on the simulator   | [Getting Started](Getting-Started)                                                     |
| understand how the parts fit     | [Architecture](Architecture), [Topics and Services](Topics-and-Services)               |
| bring Dharma up on a new robot   | [New Product from Template](New-Product-from-Template), [Robot Profile](Robot-Profile) |
| map a site and teach routes      | [Mapping and Sites](Mapping-and-Sites), [Localization](Localization)                   |
| drive to goals and follow routes | [Navigation](Navigation)                                                               |
| know what keeps the robot safe   | [Safety](Safety)                                                                       |
| tune or diagnose a robot         | [Tuning](Tuning), [Health](Health), [Troubleshooting](Troubleshooting)                 |
| test without hardware            | [Simulation](Simulation)                                                               |
| change or extend a package       | [Contributing](Contributing)                                                           |
| quick answers                    | [FAQ](FAQ)                                                                             |

## Repositories

One repository per part, all at version 0.2.0:

| Repository                                                                     |                                                                                     |
| ------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------- |
| [Dharma](https://github.com/DarmawanRobotics/Dharma)                           | hub and template: `dharma.repos`, dev container, scripts, `robot_bringup`, the docs |
| [dharma_utils](https://github.com/DarmawanRobotics/dharma_utils)               | math, typed configuration, robot profile, braking model, `DharmaNode`, test helpers |
| [dharma_interfaces](https://github.com/DarmawanRobotics/dharma_interfaces)     | typed status messages, sector scans, waypoints, services                            |
| [dharma_odometry](https://github.com/DarmawanRobotics/dharma_odometry)         | FAST-LIO / Leg-KILO behind a still-start gate, odometry monitor                     |
| [dharma_localization](https://github.com/DarmawanRobotics/dharma_localization) | gravity-aligned bridge, fiducial-anchored EKF over `map -> odom`, scan matching     |
| [dharma_perception](https://github.com/DarmawanRobotics/dharma_perception)     | front and 360° sector scans, fail-safe when blind; AprilTag throttle                |
| [dharma_mapping](https://github.com/DarmawanRobotics/dharma_mapping)           | occupancy grids per site, crash-safe maps, route recorder                           |
| [dharma_navigation](https://github.com/DarmawanRobotics/dharma_navigation)     | planner, route loader, path follower, avoidance; `dharma_control`: the safety mux   |
| [dharma_health](https://github.com/DarmawanRobotics/dharma_health)             | one typed health signal with a speed scale, diagnostics                             |
| [dharma_rviz](https://github.com/DarmawanRobotics/dharma_rviz)                 | RViz panels: mission, safety, status, tuning, tags                                  |
| [dharma_sim](https://github.com/DarmawanRobotics/dharma_sim)                   | software-in-the-loop robot with drift, latency and seeded scenarios                 |

## Documents

- **Technical manual** (architecture, models, every parameter and interface, safety case,
  traceability of every fixed defect): `docs/manual` in the hub, built with
  `make -C docs manual` into `docs/build/manual/dharma_manual.pdf`.
- **Paper** (methods and evaluation): `docs/paper`, `make -C docs paper`.
- **Diagrams**: `docs/diagrams` (draw.io sources, PDF and SVG exports).
- Each package README lists its nodes, topics and parameters.
