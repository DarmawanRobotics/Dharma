# Wiki sources

The pages of the [Dharma GitHub wiki](https://github.com/DarmawanRobotics/Dharma/wiki), kept
here so they are reviewed and versioned with the code. `Home.md` is the start page,
`_Sidebar.md` the navigation; links between pages use the page name without `.md`
(`[Safety](Safety)`). Diagrams are referenced as `images/<name>.svg` and copied from
`docs/diagrams/svg/` when publishing. This README is not a wiki page.

The same pages are the [documentation site](https://darmawanrobotics.github.io/Dharma/): `docs/site/prepare.py` turns them into MkDocs
sources (wiki links to page files, diagrams from `docs/diagrams/svg/`) and
`.github/workflows/docs.yml` deploys it from `main`. Write the pages for the wiki; the site follows
without changes ([docs/README.md](../README.md#site)).

## Publish

The wiki is a separate git repository. Create the first page once in the GitHub web interface
(this creates the repository), then from the hub root:

```bash
git clone https://github.com/DarmawanRobotics/Dharma.wiki.git /tmp/dharma-wiki
rsync -a --delete --exclude .git --exclude README.md docs/wiki/ /tmp/dharma-wiki/
mkdir -p /tmp/dharma-wiki/images && cp docs/diagrams/svg/*.svg /tmp/dharma-wiki/images/
cd /tmp/dharma-wiki
git add -A && git commit -m "docs: update the wiki" && git push
```

`--delete` removes pages that were deleted here; edit the pages here, not in the web interface,
or the next publish overwrites the change.

## Check before publishing

```bash
pre-commit run prettier --files docs/wiki/*.md     # formatting
grep -o '](images/[a-z_]*\.svg)' docs/wiki/*.md | sed 's/.*images\///;s/)//' | sort -u \
  | while read -r f; do [ -f "docs/diagrams/svg/$f" ] || echo "missing diagram: $f"; done
```

After a diagram change, `make -C docs diagrams` regenerates the SVG exports.
