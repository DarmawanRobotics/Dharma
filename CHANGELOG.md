# Changelog

All notable changes to the Dharma template. Format: [Keep a Changelog](https://keepachangelog.com),
versions follow [SemVer](https://semver.org).

## [Unreleased]

### Added

- Docking and charging: dharma_navigation's `docking_node` in the bringup (centre on the dock
  tag, walk in, sit, start charging, undock); `config/stack.yaml` has its hook placeholders for
  the robot driver, `config/sim.yaml` points them at dharma_sim's dock station, so
  `docking/dock` works on the simulator (mall_loop: `charging_dock` on the west wall).
- Bringup argument `fiducials_detector` (`apriltag` | `aruco`): ArUco markers through
  dharma_perception's `aruco_detector_node`, same TF frames.

### Changed

- Documentation as plain Markdown in the repository: the GitHub wiki pages moved to `docs/guide/`
  with relative links and the diagram SVGs, so they render on GitHub (also in a private
  repository); the MkDocs site, its Pages workflow and `make -C docs site` are removed.
- The technical manual and the paper are committed as PDFs in `docs/pdf/` (`make -C docs pdf`).

### Added

- Foxy support next to Humble and Jazzy: dev container (`dev-foxy`, ports 5903 / 6082 on
  localhost, `.devcontainer/foxy/`), `scripts/dev.sh --distro foxy`, `scripts/setup.sh` on
  Ubuntu 20.04 (distribution from `/opt/ros` or the Ubuntu release; loguru from pip there).
- CI: Foxy in the stack build matrix (frozen image: fresh ROS apt key, end-of-life rosdep
  data, loguru from pip); scripts and experiments jobs on Python 3.8.
- Bringup: a launch warning for `/**` parameters besides `robot.*` (Foxy applies a node's own
  section after `/**`).
- Experiments: E5, backing up after the inspection at a stop point that faces a wall (360° scan,
  `inspection.reverse_distance_m` 1 m; no back-up, free, a person behind); E1 also with
  `field.human_speed` 0 (the braking model alone).

### Changed

- Python 3.8: `from __future__ import annotations` everywhere, ruff `target-version = "py38"`
  (`tooling/`), no 3.9+ runtime features in the experiments and tools,
  `dharma_utils.math.default_rng` instead of `np.random.default_rng`.
- Experiments: avoidance policies get the robot profile (dharma_navigation main).
- Experiments rerun on dharma_navigation #11 and dharma_perception #12: the follower reads the
  mux state (armed handshake) and the measured twist, avoidance looks around the direction of
  travel; results, tables, figure and the paper's evaluation, abstract and conclusion updated;
  the README's findings table became "Findings and fixes" with before / after numbers.
- Experiments rerun on dharma_navigation #13 (swept-footprint guard, `pass_margin`, rejoin
  planner, corner-aware corridor, reactive defaults): the rig's follower gets the sector centres
  (`ScanInput.centres`) as `path_follower_node` builds it; E1, E3, E4, E5 rerun (E1 and E2
  reproduce their CSVs; E3 changed with the follower's laps); results, tables, figure, README
  findings and open items, and the paper's evaluation, abstract and conclusion updated.
- Docs: Foxy | Humble | Jazzy in the README, guide, manual, paper and CI diagram.

### Fixed

- Bringup: package launches see only their explicit arguments on Foxy too (no
  `GroupAction(forwarding=False)` there: the scope unsets the bringup's arguments).
- `test_init_project` registers the module before running it (dataclasses with postponed
  annotations).

## [0.2.0] - 2026-10-23

The hub of the stack and the template a robot product is generated from.

### Added

- `dharma.repos` (every Dharma repository) and `external.repos` (livox_ros_driver2, FAST-LIO,
  optional Leg-KILO).
- Dev containers for Humble and Jazzy (`docker/`, `compose.yaml`, `.devcontainer/`): XFCE over
  VNC / noVNC on localhost, Livox-SDK2, the rosdep keys of every package, pre-commit and ruff;
  separate build/install/log volumes per distro.
- `scripts/dev.sh` (up, shell, build, test, vnc, down, clean, import; `--distro`),
  `scripts/setup.sh` (check / install ros, tools, repos, livox, rosdep, build, service),
  `scripts/start_tmux.sh` (one window per subsystem from `scripts/tmux/*.yaml`),
  `scripts/init_project.py` (template -> product), `scripts/sync_tooling.sh`.
- `tooling/`: the canonical ruff, clang-format, editorconfig, prettier, pre-commit and
  per-repository CI files.
- `robot_bringup` placeholder package: the robot profile (`config/robot.yaml`), stack overrides
  (`config/stack.yaml`, `config/sim.yaml`), `robot.launch.py` (the whole stack, optional robot
  driver) and `sim.launch.py` (the same stack on dharma_sim); the composition in one module
  (`stack.py`), every include in its own launch scope; the robot profile validated at launch;
  the started nodes handed to the health monitor.
- CI: pre-commit lint, script tests, the whole stack built on Humble and Jazzy with same-branch
  dependencies, robot_bringup tests.
- README, CONTRIBUTING, pull request template, docs index.
