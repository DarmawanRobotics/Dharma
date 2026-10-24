# Dharma evaluation experiments

The experiments behind Section VI of the paper (`docs/paper/sections/evaluation.tex`). E1-E5
close the loop over the **pure cores** of the stack at the node rates, without ROS; one
end-to-end check drives the real nodes of `robot_bringup sim.launch.py`.

| Experiment           | Script               | Measures                                                                                                                                                    | Seeds x conditions                     | Runtime (2 CPUs) |
| -------------------- | -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------- | ---------------- |
| E1 stopping distance | `e1_stopping.py`     | distance from the first scan that shows a person to standstill, smallest clearance, reaction time, against D(v); field `human_speed` 0.5 m/s and 0          | 20 x 4 speeds x 2 human speeds         | 15 s             |
| E2 blind LiDAR       | `e2_blind.py`        | AUTO: time to the first zero command and distance to standstill; REMOTE: creep speed of the fastest body point; v0.2 and the v0.1 baseline                  | 20 x 3 failures x 2 modes x 2 versions | 40 s             |
| E3 localization      | `e3_localization.py` | ATE, largest position error, heading RMSE, rejected inliers and outliers of hard replacement (v0.1), the EKF with tags, the EKF with tags and scan matching | 20 runs x 3 estimators (same inputs)   | 7 min            |
| E4 path shift        | `e4_path_shift.py`   | completion, time, stops, smallest clearance to people, largest offset from the route; path shift, reactive avoidance, none                                  | 20 x 3 modes x 2 layouts               | 10 min           |
| E5 back-up           | `e5_backup.py`       | completion, time, distance backed up, time BLOCKED, smallest clearance to a person behind and to the walls; no back-up, back-up free, back-up with a person | 20 x 3 conditions                      | 1 min            |
| End to end           | `e2e/run.sh`         | the mall_loop route with two standing people on the real nodes                                                                                              | 1 run                                  | 2 min            |

## Run

The cores are imported from the package checkouts: `common/stack.py` puts them on `sys.path`,
searching `$DHARMA_SRC`, `src/dharma/` (`vcs import src < dharma.repos`) and the directory
next to the hub. Python 3.8+, numpy, scipy, PyYAML; matplotlib for the figures, pytest for the
tests. No ROS is needed for E1-E5.

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
protective field, `field.human_speed` 0.5 m/s as in the bringup) for every command and its
watchdog at 50 Hz. The follower reads the mux state every tick as from `control/status`
(e-stop, REMOTE, navigation armed: a disarmed follower streams neutral commands, which arm it),
the measured twist, and the avoidance policy (`POLICIES.create(..., robot=)`) looks around the
direction of travel of navigation's last command, as `obstacle_avoidance_node` does with
`control/nav_cmd_vel`. E5 sets `front.fov_deg: 360` and `inspection.reverse_distance_m: 1.0`. The phases of the periodic
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
loads and starts the route and writes `results/e2e_sim.csv`. `sim_params.yaml` only pins the
route loader to `/tmp/dharma_sim/sites` (a run without it loads the route too). The committed
CSV holds the run quoted in the paper, made after the navigation and control fixes (Jazzy,
workspace with every package at main). Before the fixes the same setup completed in 78.6 s
(2 stops) and an earlier run stayed BLOCKED at the second person (the path-shift deadlock).
The start of a run can still race the follower's localization pause
(`start failed: cannot start while localization holds`); the runs are not deterministic.

## Findings and fixes

Results that contradicted the design or showed defects of the stack, the fix and the numbers of
this rig before and after it (20 seeds unless a seed is given; reproduce with the seed). The
"before" numbers are the committed results of the previous run (dharma_navigation at #10).

| Symptom                                                                                                                                                                                                                                          | Fix                                                                                                                                                                                                                          | Before → after                                                                                                                                                                                                                                                                         | Reproduce                                                             |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| Path shift: a robot that stopped within `stop_margin` of a person before it reached its offset got speed 0, which also stopped the sideways slide: BLOCKED for good                                                                              | dharma_navigation #11: the slide toward the committed offset goes on while forward is held, guarded on the 360° scan                                                                                                         | E4 `on_route` seeds 3, 7: BLOCKED → goal in 82.1 s and 73.9 s                                                                                                                                                                                                                          | `e4_path_shift.run('path_shift', 3)`                                  |
| Path shift: while the robot stood, the offset slid toward a target beyond a crossing person; the off-path check compared with that offset: OFF_PATH                                                                                              | dharma_navigation #11: committed offset at most `max_lead` (0.25 m) ahead of the robot, the off-path check uses it                                                                                                           | E4 `on_route` seed 16: OFF_PATH → goal in 73.8 s; path shift on the route 17/20 → 20/20                                                                                                                                                                                                | `e4_path_shift.run('path_shift', 16)`                                 |
| Follower: stall detection used the commanded speed, so a robot held by the mux (field STOP, disarmed) was FOLLOWING forever and the planner never replanned; a follower started right after the mux never moved; guard margin 0.05 m, mux 0.10 m | dharma_navigation #11: BLOCKED from the measured pose (`stall_distance` 0.1 m for `blocked_timeout_sec` 10 s), neutral commands while `control/status` says disarmed, `safety.lateral_margin` 0.10 m checked against the mux | E4 `beside_route`, `off` seeds 1, 11 and `reactive` 1, 6, 11: FOLLOWING until the 150 s limit → BLOCKED after standing 10 s                                                                                                                                                            | `e4_path_shift.run('off', 1, 'beside_route')`                         |
| Field and guard checked the robot's motion against a static scan; a person walking at 0.2 m/s brushed the stopped robot                                                                                                                          | dharma_navigation #11: ISO/TS 15066 separation, protective distance D(v) + v_h (t_r + v/a), `field.human_speed` / `safety.human_speed` 0.5 m/s                                                                               | E4 `beside_route` seed 15: clearance −0.005 m (contact) → 0.29 m; E4 contacts 1 → 0, smallest clearance of path shift beside the route contact → 0.19 m; E1 at 0.8 m/s: 0.68 → 0.56 m to standstill, clearance 0.16 → 0.23 m (E1 with `human_speed` 0 reproduces the old rows exactly) | `e4_path_shift.run('path_shift', 15, 'beside_route')`                 |
| VFH aimed at the gap edge plus half `min_gap_width_deg`, independent of the body width: a collision course                                                                                                                                       | dharma_navigation #11: headings within asin((w/2 + `body_margin`) / d) of an obstacle are blocked                                                                                                                            | E4 `on_route` seed 1: heading −14° into the person → −36° clear of it; reactive avoidance still passes 0/20 (open, below)                                                                                                                                                              | `e4_path_shift.run('reactive', 1)`                                    |
| robot_bringup: `sites_dir` was not passed to the route loader, `navigation/load_path` refused the simulator's route                                                                                                                              | hub bringup (#1): `sites_dir` of the launch goes to `path_loader_node`                                                                                                                                                       | a run without `sim_params.yaml` loads the route (301 points)                                                                                                                                                                                                                           | `ros2 launch robot_bringup sim.launch.py` then `navigation/load_path` |

Open:

| Where                                       | Symptom                                                                                                                                                                                                                                                                                                                                                                                                                                                                | Reproduce                                                                                                                                       |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| dharma_navigation guard, reactive avoidance | Reactive avoidance still never passes a person on the route (0/20, smallest clearance 0.35 → 0.53 m): VFH now picks a clear heading (about −36°), but the guard checks the diagonal motion with the bounding box of the footprint rotated to it plus `stop_margin` 0.3 m and the separation term, and holds the robot about 0.3 m short (BLOCKED, the planner would replan)                                                                                            | `e4_path_shift.run('reactive', 1)`                                                                                                              |
| dharma_navigation guard                     | The guard is now more cautious than the mux: with `lateral_margin` 0.10 m on the sector-edge points it refuses passes with about 0.1 m beside the body that the old 0.05 m allowed. E4 `beside_route` without path shift: reactive 13/20 → 8/20, none 13/20 → 7/20 (reactive seeds 3, 8, 12, 13, 19, none also 10: BLOCKED at the person beside the route; seeds 3 and 8 complete with `safety.lateral_margin` 0.05 m and still block with 0.10 m and `human_speed` 0) | `e4_path_shift.run('off', 3, 'beside_route')`                                                                                                   |
| dharma_navigation back-up rejoin            | After backing up 1 m from a stop that faces a wall 0.9 m beside the route, the rejoin walks diagonally to the waypoint 1 m past the stop; the guard (rotated bounding box, 0.3 m stop margin, separation) holds it 0.23 m short and the follower stays BLOCKED until `join.timeout_sec` (60 s) gives up: E5 free 20/20 done but 43.7 s BLOCKED, with a person behind 9/20 held                                                                                         | `e5_backup.run('free', 1)`                                                                                                                      |
| dharma_navigation `core/shift/corridor.py`  | Points beyond a route corner on its outer side are projected onto the corner with their perpendicular offset: a stop point at a corner (route east to a stop facing a wall 0.8 m ahead, then north) stops the robot `stop_margin` short of the corner, 1.2 m from the wall (BLOCKED); avoidance `off` reaches the stop. E5 avoids it with a straight route                                                                                                             | open room with the east wall at x = 5.5, route east along y = 0 from x = 0 to a stop at (4.7, 0), yaw 0, then north: the robot holds at x = 3.9 |
| dharma_localization gate                    | 20 % of the simulated tag outliers (5-25 deg, 0.1-0.4 m) passed the chi-square gate (now 20 % of 135); the EKF error stayed at 0.075 m ATE                                                                                                                                                                                                                                                                                                                             | `e3_localization.run(1)`                                                                                                                        |
