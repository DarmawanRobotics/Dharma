# Dharma documentation

| Folder                 |                                                                                                             |
| ---------------------- | ----------------------------------------------------------------------------------------------------------- |
| [wiki/](wiki/)         | how-to pages: install, bring up a new robot, map a site, tune, diagnose                                     |
| [manual/](manual/)     | the technical manual (LaTeX): architecture, every subsystem, configuration, safety, interfaces, development |
| [paper/](paper/)       | the paper describing Dharma's methods and evaluation (LaTeX, IEEE format)                                   |
| [diagrams/](diagrams/) | draw.io sources, exported to `pdf/` (manual, paper) and `svg/` (wiki, READMEs)                              |

`make -C docs` builds the diagrams and the PDFs (`make diagrams`, `make manual`, `make paper`,
`make clean`); it needs draw.io and a LaTeX installation with latexmk.

Each package documents its own nodes, topics and parameters in its README. Products made from
this template keep only this index (`scripts/init_project.py`; `--keep-docs` keeps the rest).
