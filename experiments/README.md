# Dharma evaluation experiments

The experiments behind Section VI of the paper (`docs/paper/sections/evaluation.tex`). E1-E4
close the loop over the **pure cores** of the stack at the node rates, without ROS; one
end-to-end check drives the real nodes of `robot_bringup sim.launch.py`.

| Experiment           | Script               | Measures                                                                                                                                                    | Seeds x conditions                     | Runtime (2 CPUs) |
| -------------------- | -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------- | ---------------- |
| E1 stopping distance | `e1_stopping.py`     | distance from the first scan that shows a person to standstill, smallest clearance, reaction time, against D(v)                                             | 20 x 4 speeds                          | 10 s             |
| E2 blind LiDAR       | `e2_blind.py`        | AUTO: time to the first zero command and distance to standstill; REMOTE: creep speed of the fastest body point; v0.2 and the v0.1 baseline                  | 20 x 3 failures x 2 modes x 2 versions | 40 s             |
| E3 localization      | `e3_localization.py` | ATE, largest position error, heading RMSE, rejected inliers and outliers of hard replacement (v0.1), the EKF with tags, the EKF with tags and scan matching | 20 runs x 3 estimators (same inputs)   | 7 min            |
| E4 path shift        | `e4_path_shift.py`   | completion, time, stops, smallest clearance to people, largest offset from the route; path shift, reactive avoidance, none                                  | 20 x 3 modes x 2 layouts               | 10 min           |
| End to end           | `e2e/run.sh`         | the mall_loop route with two standing people on the real nodes                                                                                              | 1 run                                  | 2 min            |

## Run

The cores are imported from the package checkouts: `common/stack.py` puts them on `sys.path`,
searching `$DHARMA_SRC`, `src/dharma/` (`vcs import src < dharma.repos`) and the directory
next to the hub. Python 3.10+, numpy, scipy, PyYAML; matplotlib for the figures, pytest for the
tests. No ROS is needed for E1-E4.

```bash
python3 experiments/run_all.py               # every experiment, 20 seeds, 2 processes
python3 experiments/run_all.py --seeds 2 e1  # one experiment, seeds 1-2
python3 experiments/run_all.py --report      # only the tables and figures from results/
python3 -m pytest experiments/test           # smoke tests, one seed (about 1 min)
make -C docs paper                           # the paper with the regenerated tables
```

`run_all.py` writes `results/<experiment>.csv` (one row per run, every seed), then
`report.py` writes `docs/paper/tables/e*.tex` (the tables), `docs/paper/tables/results.tex`
(the numbers quoted in the text) and `docs/paper/figures/e3_error.pdf`. Every run is
deterministic per seed: a rerun reproduces the committed CSVs exactly.

## Rig

`common/rig.py` advances one clock in 10 ms ticks: dharma_sim's `Simulation` (body with the
profile's acceleration limits, Mid-360 ray casting, drifting odometry, sensor and command
latency, collisions) at 100 Hz; LiDAR, dharma_perception's `SectorPipeline` and the node's
watchdog at 10 Hz; a driver (dharma_navigation's `Follower` with the avoidance policy, or a
constant command stream) at 20 Hz; dharma_control's `Arbiter` and `Gate` (envelope and
protective field) for every command and its watchdog at 50 Hz. The phases of the periodic
tasks are drawn from the seed. Messages arrive when they are published; processing time is
not modelled. Package defaults are used everywhere (the robot profile of
`src/robot_bringup/config/robot.yaml`); the health speed scale and the planner's replanning are
not in the loop, and localization is the true pose except in E3.

Baselines (clearly not stack code): `common/perception.py` `PerceptionV01` and
`common/mux.py` `MuxV01` (v0.1: a blind cloud gives an all-zero safety scan, which the v0.1
field skips as free; no perception watchdog; field off in REMOTE), `common/baseline.py`
`HardReplace` (v0.1: every tag replaces map->odom unless map->odom moves by more than
0.5 m / 15 deg). Tag detections are simulated in `common/tags.py` with the noise model the
localization assumes plus 5 % outliers.

## End-to-end check

Build the stack in a workspace (see the bringup README), source ROS, then:

```bash
experiments/e2e/run.sh <workspace> [runs]   # launch, drive, stop; one row per run
```

Each run starts `ros2 launch robot_bringup sim.launch.py params_file:=experiments/e2e/sim_params.yaml`
and `e2e/drive_route.py`, which places two standing people on the mall route (`sim/obstacles`),
loads and starts the route and writes `results/e2e_sim.csv`. `sim_params.yaml` points the route
loader at `/tmp/dharma_sim/sites`: the bringup does not pass `sites_dir` to navigation, so
without it `navigation/load_path` refuses the simulator's route. The committed CSV holds the run
quoted in the paper; an earlier run of the same setup stayed BLOCKED at the second person (the
path-shift deadlock below), and the start of a run can race the follower's localization pause
(`start failed: cannot start while localization holds`); the runs are not deterministic.

## Findings

Results that contradict the design or show defects of the stack (reproduce with the seed):

| Where                                                                   | Symptom                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | Reproduce                                                             |
| ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| dharma_navigation `core/shift/path_shift.py`                            | The speed limit uses the free distance at the measured lateral position too; a robot that stops within `stop_margin` (0.4 m) of a person before it reached its offset gets speed 0, which also stops the sideways slide: BLOCKED for good (E4 `on_route` seeds 3, 7).                                                                                                                                                                                                                 | `e4_path_shift.run('path_shift', 3)`                                  |
| dharma_navigation `core/shift/path_shift.py`, `core/follower/phases.py` | While the robot stands, `offset` keeps sliding toward a target on the other side of a crossing person; the off-path check compares the lateral position with that offset and ends the run OFF_PATH (seed 16).                                                                                                                                                                                                                                                                         | `e4_path_shift.run('path_shift', 16)`                                 |
| dharma_navigation follower + dharma_control mux                         | Stall detection uses the commanded speed: a robot held by the mux (field STOP, or navigation disarmed) is reported FOLLOWING forever, so the planner's replanning on BLOCKED never starts (E4 `beside_route`, `off` seeds 1 and 11, `reactive` seeds 1, 6, 11; a follower started less than `nav_timeout_sec` after the mux never moves). The mux corridor (`field.lateral_margin` 0.10 m) is wider than the follower guard's (0.05 m), so the follower plans passes the mux refuses. | `e4_path_shift.run('off', 1, 'beside_route')`                         |
| dharma_navigation `core/avoidance/vfh.py`                               | The gap heading is the gap edge plus half `min_gap_width_deg`, independent of the body width and distance: −14° past a person 1 m ahead is still a collision course; the guard stops the robot, the emergency cone holds it, reactive avoidance never passes a person on the route (0/20) and behaves like no avoidance.                                                                                                                                                              | `e4_path_shift.run('reactive', 1)`                                    |
| dharma_control field, dharma_navigation guard                           | Both check the robot's own motion against a static scan; a person walking at 0.2 m/s brushed the stopped robot (E4 `beside_route` seed 15, clearance −0.005 m). ISO/TS 15066 speed and separation monitoring includes the speed of the person.                                                                                                                                                                                                                                        | `e4_path_shift.run('path_shift', 15, 'beside_route')`                 |
| robot_bringup `stack.py`                                                | `sites_dir` is not passed to navigation: `navigation/load_path` of the simulator's route is refused (`/root/dharma/map/...: No such file`); `e2e/sim_params.yaml` works around it.                                                                                                                                                                                                                                                                                                    | `ros2 launch robot_bringup sim.launch.py` then `navigation/load_path` |
| dharma_localization gate                                                | 20 % of the simulated tag outliers (5-25 deg, 0.1-0.4 m) passed the chi-square gate; the EKF error stayed at 0.07 m ATE.                                                                                                                                                                                                                                                                                                                                                              | `e3_localization.run(1)`                                              |
