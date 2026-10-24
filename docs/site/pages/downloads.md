---
source: ../site/pages/downloads.md
---

# Downloads

Both documents are built from their LaTeX sources in `docs/` with every change to `main` that
publishes this site, so they always match the documentation here.

<div class="grid" markdown>

<div class="card" markdown>

:material-book-open-page-variant-outline:{ .lg .middle } **Technical manual**

---

Architecture, every subsystem with its models and parameters, the interfaces, the safety case,
the development guide and the traceability of every fixed defect.

[:material-download: dharma_manual.pdf](pdf/dharma_manual.pdf){ .md-button .md-button--primary }

</div>

<div class="card" markdown>

:material-file-document-outline:{ .lg .middle } **Paper**

---

_Dharma: A Robot-Agnostic, Safety-Layered ROS 2 Autonomy Stack for Service Robots in Crowded
Public Spaces_: the methods and their evaluation, in the IEEE conference format.

[:material-download: dharma_paper.pdf](pdf/dharma_paper.pdf){ .md-button .md-button--primary }

</div>

</div>

## Build them yourself

```bash
make -C docs paper manual DRAWIO=nodrawio   # docs/build/paper/dharma.pdf, docs/build/manual/dharma_manual.pdf
```

The build needs LaTeX with latexmk and IEEEtran (Ubuntu: `texlive-latex-extra`,
`texlive-fonts-recommended`, `texlive-publishers`, `latexmk`). The diagrams are committed as PDF
exports, so draw.io is only needed to change them.
