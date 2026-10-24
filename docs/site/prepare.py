#!/usr/bin/env python3
"""
Assemble the MkDocs sources of the documentation site from the wiki pages (single source).

    python3 docs/site/prepare.py               # docs/build/site-src, PDFs from docs/build
    python3 docs/site/prepare.py --skip-pdfs   # no LaTeX build: link the published PDFs

Copies docs/wiki/*.md (not _Sidebar.md and README.md) and the site-only pages of
docs/site/pages/ into the build directory and rewrites the wiki links for MkDocs:
[Safety](Safety) -> Safety.md, [x](Page#anchor) -> Page.md#anchor, Home -> index.md. The
images/<name>.svg references get the exports of docs/diagrams/svg/ and the downloads the PDFs
built by `make -C docs paper manual`. `<!-- include: Page#section -->` in a site page inserts
a section of a wiki page (`intro`: the text before its first `##` heading). Python 3.8.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import shutil
import sys
from typing import Iterable

DOCS = Path(__file__).resolve().parent.parent
SITE_URL = 'https://darmawanrobotics.github.io/Dharma/'
NOT_PAGES = frozenset({'_Sidebar.md', 'README.md'})
HOME = 'Home'
IMAGES = 'images/'
# published path -> source below docs/ (make -C docs paper manual)
PDFS = (
    ('pdf/dharma_manual.pdf', 'build/manual/dharma_manual.pdf'),
    ('pdf/dharma_paper.pdf', 'build/paper/dharma.pdf'),
)
LINK_RE = re.compile(r'(!?\[(?:[^\]\\]|\\.)*\])\(([^)\s]+)((?:\s+"[^"]*")?)\)')
INCLUDE_RE = re.compile(r'^<!-- include: ([A-Za-z0-9-]+)#([a-z0-9-]+) -->$', re.MULTILINE)
FENCE_RE = re.compile(r'^\s*(`{3,}|~{3,})')
CODE_SPAN_RE = re.compile(r'(`+)(?:.+?)\1')
SCHEME_RE = re.compile(r'^[a-zA-Z][a-zA-Z0-9+.-]*:')


class PrepareError(RuntimeError):
    """The sources do not make a site (a missing diagram, PDF or included section)."""


def page_file(name: str) -> str:
    """Return the site file of a wiki page name: Home -> index.md, Safety -> Safety.md."""
    return 'index.md' if name == HOME else name + '.md'


def wiki_pages(wiki: Path) -> dict[str, Path]:
    """Return the wiki pages by page name (Safety -> docs/wiki/Safety.md)."""
    return {p.stem: p for p in sorted(wiki.glob('*.md')) if p.name not in NOT_PAGES}


def rewrite_target(target: str, pages: Iterable[str]) -> str:
    """Return a link target for MkDocs: wiki page names become files, anything else stays."""
    if SCHEME_RE.match(target) or target.startswith(('/', '#')):
        return target
    name, sep, anchor = target.partition('#')
    if name in pages:
        return page_file(name) + sep + anchor
    return target


def _outside_code_spans(line: str, fn) -> str:
    """Apply fn to the parts of a line that are not inline code."""
    out, pos = [], 0
    for m in CODE_SPAN_RE.finditer(line):
        out += [fn(line[pos : m.start()]), m.group(0)]
        pos = m.end()
    out.append(fn(line[pos:]))
    return ''.join(out)


def rewrite_links(text: str, pages: Iterable[str]) -> tuple[str, set[str]]:
    """Return the text with rewritten links and the images/*.svg names it references.

    Fenced code blocks and inline code are left alone.
    """
    names = set(pages)
    images: set[str] = set()

    def link(m: re.Match) -> str:
        target = m.group(2)
        if target.startswith(IMAGES):
            images.add(target[len(IMAGES) :])
            return m.group(0)
        return f'{m.group(1)}({rewrite_target(target, names)}{m.group(3)})'

    def part(chunk: str) -> str:
        return LINK_RE.sub(link, chunk)

    out, fence = [], ''
    for line in text.splitlines(keepends=True):
        m = FENCE_RE.match(line)
        if fence:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence):
                fence = ''
            out.append(line)
        elif m:
            fence = m.group(1)
            out.append(line)
        else:
            out.append(_outside_code_spans(line, part))
    return ''.join(out), images


def slug(heading: str) -> str:
    """Return the GitHub anchor of a heading text (lower case, punctuation dropped)."""
    text = re.sub(r'[^\w\- ]', '', heading.strip().lower())
    return text.replace(' ', '-')


def section(text: str, name: str) -> str:
    """Return a `## ` section of a page (with its heading) or `intro`, the text before it.

    The page title (`# `) is not part of the intro.
    """
    lines = text.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.startswith('## ')]
    if name == 'intro':
        body = lines[: starts[0] if starts else len(lines)]
        body = [line for line in body if not line.startswith('# ')]
        return ''.join(body).strip('\n') + '\n'
    for k, i in enumerate(starts):
        if slug(lines[i][3:]) == name:
            end = starts[k + 1] if k + 1 < len(starts) else len(lines)
            return ''.join(lines[i:end]).strip('\n') + '\n'
    raise PrepareError(f'no section {name!r}')


def expand_includes(text: str, wiki: Path) -> str:
    """Replace every `<!-- include: Page#section -->` line by that section of the wiki page."""

    def include(m: re.Match) -> str:
        path = wiki / (m.group(1) + '.md')
        if not path.is_file():
            raise PrepareError(f'include of a missing wiki page: {m.group(1)}')
        try:
            return section(path.read_text(encoding='utf-8'), m.group(2)).rstrip('\n')
        except PrepareError as e:
            raise PrepareError(f'{m.group(1)}: {e}') from None

    return INCLUDE_RE.sub(include, text)


def _site_page(path: Path, docs: Path, pages: dict[str, Path], skip_pdfs: bool) -> str:
    """Return a page of docs/site/pages with its includes expanded."""
    text = expand_includes(path.read_text(encoding='utf-8'), docs / 'wiki')
    if skip_pdfs:
        for dest, _ in PDFS:
            text = text.replace(f']({dest})', f']({SITE_URL}{dest})')
    return text


def collect(docs: Path = DOCS, skip_pdfs: bool = False) -> dict[str, str | Path]:
    """Return the site sources: published path -> rewritten text or file to copy.

    Raises PrepareError for a referenced diagram that has no export, a missing PDF (unless
    skip_pdfs: then the downloads link the published site) or a bad include.
    """
    pages = wiki_pages(docs / 'wiki')
    if not pages:
        raise PrepareError(f'no wiki pages in {docs / "wiki"}')
    missing = [src for _, src in PDFS if not (docs / src).is_file()]
    if missing and not skip_pdfs:
        raise PrepareError(
            f'missing {", ".join(missing)}: `make -C docs paper manual` or --skip-pdfs'
        )
    texts = {page_file(n): p.read_text(encoding='utf-8') for n, p in pages.items() if n != HOME}
    files: dict[str, str | Path] = {}
    site = docs / 'site' / 'pages'
    for path in sorted(p for p in site.rglob('*') if p.is_file()):
        rel = path.relative_to(site).as_posix()
        if path.suffix == '.md':
            texts[rel] = _site_page(path, docs, pages, skip_pdfs)
        else:
            files[rel] = path
    images: set[str] = set()
    for rel, text in texts.items():
        files[rel], used = rewrite_links(text, pages)
        images |= used
    for name in sorted(images):
        svg = docs / 'diagrams' / 'svg' / name
        if not svg.is_file():
            raise PrepareError(
                f'{IMAGES}{name}: no export in docs/diagrams/svg (make -C docs diagrams)'
            )
        files[IMAGES + name] = svg
    if not skip_pdfs:
        files.update((dest, docs / src) for dest, src in PDFS)
    return files


def build(out: Path, docs: Path = DOCS, skip_pdfs: bool = False) -> list[str]:
    """Write the site sources of a docs/ tree to out (emptied first); return the paths."""
    files = collect(docs, skip_pdfs)
    if out.exists():
        shutil.rmtree(out)
    for rel, content in files.items():
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, Path):
            shutil.copyfile(content, out / rel)
        else:
            (out / rel).write_text(content, encoding='utf-8')
    return sorted(files)


def main(argv: list[str] | None = None) -> int:
    """Run the command line."""
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0].strip())
    parser.add_argument('--docs', type=Path, default=DOCS, help='the docs/ directory')
    parser.add_argument('--out', type=Path, help='default: <docs>/build/site-src')
    parser.add_argument('--skip-pdfs', action='store_true', help='link the published PDFs')
    args = parser.parse_args(argv)
    try:
        out = args.out or args.docs / 'build' / 'site-src'
        written = build(out, args.docs, skip_pdfs=args.skip_pdfs)
    except PrepareError as e:
        sys.stderr.write(f'prepare: {e}\n')
        return 1
    sys.stdout.write(f'prepare: {len(written)} files in {out}\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
