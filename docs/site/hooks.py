"""MkDocs hooks of the documentation site (mkdocs.yml: hooks)."""

from __future__ import annotations

from urllib.parse import urljoin


def on_page_context(context, page, config, nav):
    """Point the edit link of a site-only page at its real source.

    The wiki pages are edited in docs/wiki/ (edit_uri). A page from docs/site/pages/ names its
    source relative to docs/wiki/ in its front matter (`source: ../site/pages/index.md`).
    """
    source = page.meta.get('source')
    if source and page.edit_url and page.edit_url.endswith(page.file.src_uri):
        wiki = page.edit_url[: -len(page.file.src_uri)]
        page.edit_url = urljoin(wiki, source)
    return context
