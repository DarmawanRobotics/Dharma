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
| End to end           | `e2e/drive_route.py` | the mall_loop route on the real nodes with the person_crossing scenario                                                                                     | 1 run                                  | 3 min            |

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

Build the stack in a workspace (see `docs/` and the bringup README), then in two shells:

```bash
ros2 launch robot_bringup sim.launch.py scenario:=person_crossing params_file:=<file>
python3 experiments/e2e/drive_route.py --scenario person_crossing
```

`<file>` sets `path_loader_node: ros__parameters: sites_dir: /tmp/dharma_sim/sites` (the
bringup does not pass `sites_dir` to navigation, so without it `navigation/load_path` refuses
the simulator's route). The script writes `results/e2e_sim.csv`.
