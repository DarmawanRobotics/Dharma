---
layout: home

hero:
  name: Dharma
  text: Autonomy for service robots
  tagline: >-
    A robot-agnostic ROS 2 stack for legged and wheeled robots in public spaces. One robot
    profile, typed parameters, a safety mux with a protective field, and a simulator to test it
    all without hardware. Foxy, Humble and Jazzy.
  image:
    src: /logo.svg
    alt: Dharma
  actions:
    - theme: brand
      text: Get started
      link: /guide/getting-started
    - theme: alt
      text: Architecture
      link: /guide/architecture
    - theme: alt
      text: New product
      link: /guide/new-product

features:
  - icon: 🧭
    title: Odometry and localization
    details: >-
      FAST-LIO or Leg-KILO behind a still-start gate, and a fiducial-anchored EKF over
      map → odom that rejects corrections that disagree.
    link: /subsystems/localization
    linkText: Localization
  - icon: 🗺️
    title: Sites and maps
    details: >-
      Occupancy grids per site, saved crash-safe, with their AprilTags and the routes taught on
      them.
    link: /subsystems/mapping-and-sites
    linkText: Mapping and sites
  - icon: 🛣️
    title: Planning and following
    details: >-
      go_to on the map, route following with stop points and inspections, path shift around
      obstacles, docking onto a charger.
    link: /subsystems/navigation
    linkText: Navigation
  - icon: 🛡️
    title: One mux, one field
    details: >-
      Only the control mux drives the robot: e-stop, modes, sources and a protective field
      sized from the measured braking.
    link: /subsystems/safety
    linkText: Safety
  - icon: 🩺
    title: Health you can act on
    details: >-
      One typed health signal with a speed scale; stamps, TF delays and the clock diagnosed, not
      just topic rates.
    link: /subsystems/health
    linkText: Health
  - icon: 🧪
    title: Simulator in the loop
    details: >-
      A kinematic robot with a simulated Mid-360, drift and latency runs the whole stack in CI on
      every change.
    link: /subsystems/simulation
    linkText: Simulation
---

## Documents

<div class="docs-cards">

[**Technical manual** · PDF<br><span>Architecture, every subsystem with its models and parameters, safety case, interfaces, traceability.</span>](/files/dharma_manual.pdf)

[**Paper** · PDF<br><span>Dharma's methods and evaluation, IEEE conference format.</span>](/files/dharma_paper.pdf)

[**Troubleshooting**<br><span>TF latency, time synchronisation, localization, the follower's states.</span>](/operate/troubleshooting)

</div>

## Products on Dharma

| Product                                                    | Robot               | What it does                                             |
| ---------------------------------------------------------- | ------------------- | -------------------------------------------------------- |
| [Pashupati](https://darmawanrobotics.github.io/Pashupati/) | ZSBot Genisom L1W   | mall patrol with AI inspection, the NETRA command center |
| [Molly](https://darmawanrobotics.github.io/Molly/)         | Deep Robotics Lite3 | tour guide: tours, speech, gestures, a visitor dashboard |
