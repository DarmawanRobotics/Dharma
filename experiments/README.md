# Dharma evaluation experiments

The experiments behind Section VI of the paper (`docs/paper/sections/evaluation.tex`). E1-E5
close the loop over the **pure cores** of the stack at the node rates, without ROS; one
end-to-end check drives the real nodes of `robot_bringup sim.launch.py`.

| Experiment           | Script               | Measures                                                                                                                                                    | Seeds x conditions                     | Runtime (2 CPUs) |
| -------------------- | -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------- | ---------------- |
| E1 stopping distance | `e1_stopping.py`     | distance from the first scan that shows a person to standstill, smallest clearance, reaction time, against D(v); field `human_speed` 0.5 m/s and 0          | 20 x 4 speeds x 2 human speeds         | 15 s             |
| E2 blind LiDAR       | `e2_blind.py`        | AUTO: time to the first zero command and distance to standstill; REMOTE: creep speed of the fastest body point; v0.2 and the v0.1 baseline                  | 20 x 3 failures x 2 modes x 2 versions | 40 s             |
| E3 localization      | `e3_localization.py` | ATE, largest position error, heading RMSE, rejected inliers and outliers of hard replacement (v0.1), the EKF with tags, the EKF with tags and scan matching | 20 runs x 3 estimators (same inputs)   | 8 min            |
| E4 path shift        | `e4_path_shift.py`   | completion, time, stops, smallest clearance to people, largest offset from the route; path shift, reactive avoidance, none                                  | 20 x 3 modes x 2 layouts               | 8 min            |
| E5 back-up           | `e5_backup.py`       | completion, time, distance backed up, time BLOCKED, smallest clearance to a person behind and to the walls; no back-up, back-up free, back-up with a person | 20 x 3 conditions                      | 2 min            |
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
the measured twist, the 360° safety scan and the output of the reactive avoidance policy on the
front scan, which the bringup always runs (its emergency stop holds the follower in every
avoidance mode). The policy (`POLICIES.create(..., robot=)`) looks around the direction of
travel of navigation's last command (backward while reversing on a 360° scan), as
`obstacle_avoidance_node` does with `control/nav_cmd_vel`. E5 sets `front.fov_deg: 360` and
`inspection.reverse_distance_m: 1.0`. The phases of the periodic tasks are drawn from the seed.
Messages arrive when they are published; processing time is not modelled. Package defaults are
used everywhere (the robot profile of `src/robot_bringup/config/robot.yaml`); the health speed
scale and the planner's replanning are not in the loop, and localization is the true pose
except in E3.

Baselines (clearly not stack code):

- `common/perception.py` `PerceptionV01`: a cloud with fewer than 100 raw points gives an
  all-zero safety scan, and nothing is published while no cloud arrives (no watchdog;
  `PerceptionV02` publishes every sector BLOCKED after `input.timeout_sec` without a usable
  cloud, as `lidar_sector_node` does).
- `common/mux.py` `MuxV01`: the v0.2 arbitration and envelope with the v0.1 field. Sector
  centres below `range_max` are obstacle points, a point at the robot (a BLOCKED or zero range)
  is skipped, NaN sectors are free, a scan older than 0.5 s (receive time) stops AUTO, and the
  field is off in REMOTE (the v0.1 default).
- `common/baseline.py` `HardReplace`: every usable tag replaces map->odom with the one that puts
  the robot on the tag's map->base (flattened to x, y, yaw), unless map->odom would move by more
  than 0.5 m or 15 deg (v0.1 `max_correction_m` / `max_correction_deg`); no uncertainty is kept.

Tag detections are simulated in `common/tags.py`: a tag is detected when it lies in the
camera's field of view, faces the camera, is not hidden by a wall or pillar and is closer than
`max_range`. A detection gets the noise the localization assumes (dharma_localization
`TagNoise`: position sigma1 d^2 / cos(view angle) per axis, heading sigma_psi1 d / cos(view
angle) about the vertical); with `outlier_rate` (5 %) it is an outlier instead, a heading error
of 5-25 deg and a 0.1-0.4 m position error, like the pose ambiguity of a small planar tag.

## Protocols

**E1 stopping distance** (`e1_stopping.py`). AUTO, a constant command stream at the follower
rate (20 Hz) through the mux. Once the robot cruises at v, a person (circle r = 0.25 m, 1.7 m
high) appears on its axis D(v) + m in front of the front edge (m = `field.margin`): the nearest
appearance from which the model still promises a stop with the margin. Measured: the distance
from the first safety scan that shows the person to standstill, the smallest clearance of the
footprint and the reaction time (appearance to the first braking of the body, against the
model's t_r). Twice: with the field's default `human_speed` (0.5 m/s, ISO/TS 15066 separation:
the field also keeps the distance a person walking toward the robot covers until it stands) and
with `human_speed` 0 (the braking model alone).

**E2 blind LiDAR** (`e2_blind.py`). The robot drives straight at 0.5 m/s (AUTO: a command
stream at 20 Hz; REMOTE: the operator source, re-armed by neutral commands first). After 5 s
(plus a seeded phase) the LiDAR fails for 4 s: silent (no cloud at all, a dharma_sim dropout),
empty (clouds without points) or sparse (50 points per cloud, below the 100 of the blindness
check). Measured: AUTO, the time from the failure to the first zero command of the mux and the
distance to standstill; REMOTE, the speed of the fastest point of the body once settled (1.5 s
after the failure to its end).

**E3 localization** (`e3_localization.py`). The follower drives three laps of dharma_sim's
mall_loop route (true pose, full rig) with the odometry drift of the drift scenario; four tags
hang at the corridor ends. Every run feeds the same odometry, detections (5 Hz, 5 % outliers)
and scans to hard replacement by every tag (v0.1, `common/baseline.py`), the gated EKF of
dharma_localization with tags, and the EKF with tags and scan matching (1 Hz) on the site map
dharma_sim draws from the world (the map the stack gets in simulation). Errors are sampled at
10 Hz against the true pose.

**E4 path shift** (`e4_path_shift.py`). The follower drives a 20 m route along the centre of a
3 m corridor (full rig: perception, follower, avoidance node, mux with its protective field);
reactive avoidance is the VFH policy of the bringup. Per seed a person stands on the route at
5-6.5 m, one beside it at 10-11.5 m, one walks the same way at 0.2 m/s from 13-14 m (once the
robot passes 9 m) and one crosses at 17-18 m at 0.6 m/s (once the robot is 3 m before) and
leaves. Layout `beside_route` puts both standing people 0.6-0.9 m beside the route, on opposite
sides. Measured: the smallest clearance between the footprint and a person, the time to the goal
(150 s limit), stops (below 0.05 m/s after above 0.15 m/s, before the goal) and the largest
distance from the route.

**E5 back-up** (`e5_backup.py`). The follower drives a 5.5 m route north, 0.9 m from the east
wall of a room (full rig: 360° front and safety scans, path shift, the mux). Its stop point in
the middle faces the wall (yaw 0, 0.5 m between the front edge and the wall) for a 5 s dwell.
Conditions: none (no back-up, `inspection.reverse_distance_m` 0: the robot turns in place and
goes on), free (backs up 1 m, then rejoins the route 1 m past the stop) and person (the same
while a person who stepped in during the dwell stands 0.5-1.5 m behind the rear edge). Nothing
gives up on BLOCKED (a loaded route has no replanning: the follower waits, a join gives up after
`join.timeout_sec`). Measured: completion and time (120 s limit), how far the robot backed up,
how long it reported BLOCKED, the smallest clearance to the person and to the walls after the
dwell.

## End-to-end check

Build the stack in a workspace (see the bringup README), source ROS, then:

```bash
experiments/e2e/run.sh <workspace> [runs]   # launch, drive, stop; one row per run
```

Each run starts `ros2 launch robot_bringup sim.launch.py params_file:=experiments/e2e/sim_params.yaml`
and `e2e/drive_route.py`. It waits until localization is up, places two standing people on the mall
route (`sim/obstacles`, the simulator's default radius 0.25 m and height 1.7 m), loads the site's
route (`navigation/load_path`), starts navigation and records the true pose (`sim/ground_truth`),
`navigation/status`, `control/status` and `sim/collision` until the goal, a final state or the
timeout. `results/e2e_sim.csv` gets completion, time, stops, the smallest clearance to the people
and to the walls, the largest distance from the route and the protective field states seen.
`sim_params.yaml` only pins the route loader to `/tmp/dharma_sim/sites` (a run without it loads the
route too). The committed CSV holds the run quoted in the paper, made after the first navigation
and control fixes (Jazzy, workspace with every package at main then: dharma_navigation #11; not
rerun on #13). Before the fixes the same setup completed in 78.6 s (2 stops) and an earlier run
stayed BLOCKED at the second person (the path-shift deadlock). The start of a run can still race
the follower's localization pause (`start failed: cannot start while localization holds`); the runs
are not deterministic.

## Findings and fixes

Results that contradicted the design or showed defects of the stack, the fix and the numbers of
this rig before and after it (20 seeds unless a seed is given; reproduce with the seed). The
"before" numbers are the committed results of the previous run: dharma_navigation at #10 for
the #11 rows, the #11 results for the #13 rows (round 2: E1 and E2 reproduce their CSVs
exactly, E3 changed because the follower drives its laps).

| Symptom                                                                                                                                                                                                                                          | Fix                                                                                                                                                                                                                                                                                                                                                                                                | Before → after                                                                                                                                                                                                                                                                         | Reproduce                                                             |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| Path shift: a robot that stopped within `stop_margin` of a person before it reached its offset got speed 0, which also stopped the sideways slide: BLOCKED for good                                                                              | dharma_navigation #11: the slide toward the committed offset goes on while forward is held, guarded on the 360° scan                                                                                                                                                                                                                                                                               | E4 `on_route` seeds 3, 7: BLOCKED → goal in 82.1 s and 73.9 s                                                                                                                                                                                                                          | `e4_path_shift.run('path_shift', 3)`                                  |
| Path shift: while the robot stood, the offset slid toward a target beyond a crossing person; the off-path check compared with that offset: OFF_PATH                                                                                              | dharma_navigation #11: committed offset at most `max_lead` (0.25 m) ahead of the robot, the off-path check uses it                                                                                                                                                                                                                                                                                 | E4 `on_route` seed 16: OFF_PATH → goal in 73.8 s; path shift on the route 17/20 → 20/20                                                                                                                                                                                                | `e4_path_shift.run('path_shift', 16)`                                 |
| Follower: stall detection used the commanded speed, so a robot held by the mux (field STOP, disarmed) was FOLLOWING forever and the planner never replanned; a follower started right after the mux never moved; guard margin 0.05 m, mux 0.10 m | dharma_navigation #11: BLOCKED from the measured pose (`stall_distance` 0.1 m for `blocked_timeout_sec` 10 s), neutral commands while `control/status` says disarmed, `safety.lateral_margin` 0.10 m checked against the mux                                                                                                                                                                       | E4 `beside_route`, `off` seeds 1, 11 and `reactive` 1, 6, 11: FOLLOWING until the 150 s limit → BLOCKED after standing 10 s                                                                                                                                                            | `e4_path_shift.run('off', 1, 'beside_route')`                         |
| Field and guard checked the robot's motion against a static scan; a person walking at 0.2 m/s brushed the stopped robot                                                                                                                          | dharma_navigation #11: ISO/TS 15066 separation, protective distance D(v) + v_h (t_r + v/a), `field.human_speed` / `safety.human_speed` 0.5 m/s                                                                                                                                                                                                                                                     | E4 `beside_route` seed 15: clearance −0.005 m (contact) → 0.29 m; E4 contacts 1 → 0, smallest clearance of path shift beside the route contact → 0.19 m; E1 at 0.8 m/s: 0.68 → 0.56 m to standstill, clearance 0.16 → 0.23 m (E1 with `human_speed` 0 reproduces the old rows exactly) | `e4_path_shift.run('path_shift', 15, 'beside_route')`                 |
| VFH aimed at the gap edge plus half `min_gap_width_deg`, independent of the body width: a collision course                                                                                                                                       | dharma_navigation #11: headings within asin((w/2 + `body_margin`) / d) of an obstacle are blocked                                                                                                                                                                                                                                                                                                  | E4 `on_route` seed 1: heading −14° into the person → −36° clear of it; reactive avoidance still passes 0/20 (open, below)                                                                                                                                                              | `e4_path_shift.run('reactive', 1)`                                    |
| robot_bringup: `sites_dir` was not passed to the route loader, `navigation/load_path` refused the simulator's route                                                                                                                              | hub bringup (#1): `sites_dir` of the launch goes to `path_loader_node`                                                                                                                                                                                                                                                                                                                             | a run without `sim_params.yaml` loads the route (301 points)                                                                                                                                                                                                                           | `ros2 launch robot_bringup sim.launch.py` then `navigation/load_path` |
| Guard: the footprint's bounding box rotated to a diagonal command on the sector-edge points, plus `stop_margin` for every point, held diagonal passes and people about 0.1 m beside the body that the mux lets pass                              | dharma_navigation #13: the footprint at its own orientation swept along the command, widened by `lateral_margin` once (`core/sweep.py`, shared with the mux field), on the sector centres the mux sees (`ScanInput.centres`, built in `common/navigation.py` as `path_follower_node` does); a point passed within `lateral_margin` is held only `pass_margin` (0.15 m, the field's `margin`) short | E4 `beside_route` none 7/20 → 13/20 (seeds 3, 8, 10, 12, 13, 19 now pass; smallest clearance 0.18 → 0.12 m), reactive 8/20 → 20/20 (0.15 → 0.20 m); path shift on the route 73.3 ± 2.6 s, 3.0 stops → 70.5 ± 4.7 s, 1.3 stops (seed 16 overtakes the walking person: 52.8 s, 0.18 m)   | `e4_path_shift.run('off', 3, 'beside_route')`                         |
| Back-up rejoin: after backing up 1 m from a stop that faces a wall, the rejoin walked diagonally to the waypoint 1 m past the stop; the guard held it 0.23 m short and the follower stood BLOCKED until `join.timeout_sec` (60 s)                | dharma_navigation #13: the rejoin aims at the first route point whose straight approach is clear (`core/follower/rejoin.py`), turning onto the route heading first                                                                                                                                                                                                                                 | E5 free: 91.4 s with 43.7 s BLOCKED → 41.2 s, 0 s BLOCKED; with a person behind: 9/20 held, 51.0 ± 28.0 s → 0/20 held, 35.4 ± 4.1 s; smallest clearance to that person 0.43 → 0.38 m, to the walls 0.41 m (unchanged)                                                                  | `e5_backup.run('free', 1)`                                            |
| Path shift moved the robot off the empty mall loop (no people): with dharma_navigation #11 a lap was 0.59 m shorter with path shift than with avoidance `off` (seed 2, one lap: 28.005 vs 28.595 m)                                              | dharma_navigation #13; of its changes only the path-shift ones remain once the guard, the controller's heading and the avoidance defaults are swapped back (each leaves the lap at 28.595 m), most likely the corner-aware corridor                                                                                                                                                                | the lap with path shift equals the lap with `off` (28.595 m); E3 three laps 84.3 → 86.1 m, ATE hard replacement 0.443 → 0.408 m, EKF with tags 0.075 → 0.078 m, with scan matching 0.028 → 0.029 m                                                                                     | `e3_localization.run(2, laps=1)`                                      |

Open:

| Where                                            | Symptom                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | Reproduce                                                                                                                                      |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| dharma_navigation VFH, reactive avoidance        | Reactive avoidance still never passes a person on the route (0/20). The guard no longer holds the VFH heading (largest offset 0.05 → 0.17 m), but after a sidestep of 0.02-0.17 m VFH finds no run of free headings `min_gap_width_deg` (20°) wide within `max_heading_offset_deg` (60°), returns `velocity_scale` 0 with heading 0 (smoothed: the offset decays), and the robot stands 0.53-0.73 m from the person (BLOCKED, the planner would replan). The old shared distances do not change it (seeds 1-3 BLOCKED with `safe_distance` 1.0 m or `body_margin` 0.10 m) | `e4_path_shift.run('reactive', 1)`                                                                                                             |
| dharma_navigation guard and mux field, by design | Without path shift 7/20 runs beside the route stay BLOCKED (seeds 1, 4, 5, 6, 7, 11, 16): there the true gap between the body and the person is 0.07-0.12 m; the runs that pass have at least 0.123 m. The guard and the field use the same point model (a sector's nearest range at its centre angle, `lateral_margin` 0.10 m), which can place a person up to half a sector closer to the swept body than it is; path shift passes all of them                                                                                                                          | `e4_path_shift.run('off', 1, 'beside_route')`                                                                                                  |
| dharma_navigation `core/shift/corridor.py`       | A stop point at a route corner (route east to a stop facing a wall 0.8 m ahead, then north) held the robot `stop_margin` short of the corner, 1.2 m from the wall. #13 keeps a point's distance to an outer corner (its unit test); no experiment here covers the case yet (E5 uses a straight route)                                                                                                                                                                                                                                                                     | open room with the east wall at x = 5.5, route east along y = 0 from x = 0 to a stop at (4.7, 0), yaw 0, then north: the robot held at x = 3.9 |
| dharma_localization gate                         | 21 % of the simulated tag outliers (5-25 deg, 0.1-0.4 m) passed the chi-square gate (21 % of 125 after #13, 20 % of 135 before); the EKF error stayed at 0.078 m ATE (0.075 m before)                                                                                                                                                                                                                                                                                                                                                                                     | `e3_localization.run(1)`                                                                                                                       |
