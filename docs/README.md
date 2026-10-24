# Dharma documentation

| Folder                 |                                                                                                                                                                      |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [wiki/](wiki/)         | the GitHub wiki pages: getting started, a new product, robot profile, mapping, navigation, safety, tuning, troubleshooting ([publish](wiki/README.md))               |
| [manual/](manual/)     | the technical manual (LaTeX): architecture, every subsystem with its models and parameters, safety case, interfaces, development, traceability of every fixed defect |
| [paper/](paper/)       | the paper describing Dharma's methods and evaluation (LaTeX, IEEE conference format)                                                                                 |
| [diagrams/](diagrams/) | draw.io sources, exported to `pdf/` (manual, paper) and `svg/` (wiki, READMEs)                                                                                       |

## Wiki

Start at [wiki/Home.md](wiki/Home.md): [Getting Started](wiki/Getting-Started.md) ·
[Architecture](wiki/Architecture.md) · [Robot Profile](wiki/Robot-Profile.md) ·
[Topics and Services](wiki/Topics-and-Services.md) · [Safety](wiki/Safety.md) ·
[Localization](wiki/Localization.md) · [Mapping and Sites](wiki/Mapping-and-Sites.md) ·
[Navigation](wiki/Navigation.md) · [Health](wiki/Health.md) ·
[Simulation](wiki/Simulation.md) · [Tuning](wiki/Tuning.md) ·
[New Product from Template](wiki/New-Product-from-Template.md) ·
[Contributing](wiki/Contributing.md) · [Troubleshooting](wiki/Troubleshooting.md) ·
[FAQ](wiki/FAQ.md). The pages link to each other by wiki page name, so the links work once
published to the GitHub wiki.

## Manual

`manual/dharma_manual.tex` with one file per chapter in `manual/chapters/`. The parameter and
interface tables in `manual/generated/` come from the code: `make reference SRC=<dir with the
dharma_* checkouts>` regenerates them (`manual/tools/reference.py`). `manual/tools/brake_test.py`
measures a robot's braking limits (chapter 3).

## Diagrams

| Diagram            |                                                                          |
| ------------------ | ------------------------------------------------------------------------ |
| `layers`           | the layers with the safety column, on dharma_utils and interfaces        |
| `dataflow`         | the nodes and the main topics between them                               |
| `tf_tree`          | `map -> odom -> camera_init -> body -> base_link` and who publishes what |
| `repos`            | the repository dependency graph                                          |
| `safety_pipeline`  | sources, arbitration, envelope, protective field, e-stop and re-arm      |
| `follower_fsm`     | the path follower's states and transitions                               |
| `localization_ekf` | predict, gated updates and the `map -> odom` publication                 |
| `ci`               | lint and the Humble / Jazzy build and test matrix                        |

## Build

```bash
make -C docs              # diagrams (when draw.io is installed), then the manual and the paper
make -C docs diagrams     # diagrams/*.drawio -> diagrams/pdf (cropped) and diagrams/svg
make -C docs manual       # build/manual/dharma_manual.pdf
make -C docs paper        # build/paper/dharma.pdf
make -C docs clean        # remove build/ (the exported diagrams are committed and kept)
```

Needs a LaTeX installation with latexmk and IEEEtran; draw.io (`drawio`, headless through
`xvfb-run`) only to re-export the diagrams. Each package documents its own nodes, topics and
parameters in its README. `scripts/init_project.py` removes the manual, the paper, the diagram
sources and the wiki from a product made from the template and replaces this index
(`--keep-docs` keeps them).
