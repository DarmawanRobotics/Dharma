# Changelog

All notable changes to the Dharma template. Format: [Keep a Changelog](https://keepachangelog.com),
versions follow [SemVer](https://semver.org).

## [Unreleased]

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
