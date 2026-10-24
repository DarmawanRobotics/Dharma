from __future__ import annotations

import importlib.util
from pathlib import Path
import re

import pytest

SITE = Path(__file__).resolve().parent.parent
DOCS = SITE.parent
spec = importlib.util.spec_from_file_location('prepare', SITE / 'prepare.py')
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)

PAGES = {'Home', 'Safety', 'Robot-Profile', 'Getting-Started'}


def rewrite(text: str) -> str:
    return prepare.rewrite_links(text, PAGES)[0]


def test_page_links_become_files():
    assert rewrite('see [Safety](Safety).') == 'see [Safety](Safety.md).'
    assert rewrite('[a](Getting-Started) [b](Safety)') == '[a](Getting-Started.md) [b](Safety.md)'


def test_anchor_is_kept():
    text = '[limits](Robot-Profile#measure-the-braking-limits)'
    assert rewrite(text) == '[limits](Robot-Profile.md#measure-the-braking-limits)'


def test_home_is_the_landing_page():
    assert rewrite('**[Home](Home)**') == '**[Home](index.md)**'


def test_title_is_kept():
    assert rewrite('[s](Safety "The safety page")') == '[s](Safety.md "The safety page")'


@pytest.mark.parametrize(
    'text',
    [
        '[r](https://github.com/DarmawanRobotics/Dharma)',
        '[a](#tf-latency-diagnosis-in-ten-minutes)',
        '[x](/abs/path)',
        '[m](mailto:someone@example.com)',
        '[u](Unknown-Page)',
        '[f](Safety.md)',
    ],
)
def test_other_targets_are_unchanged(text):
    assert rewrite(text) == text


def test_images_are_collected_and_kept():
    text, images = prepare.rewrite_links('![Layers](images/layers.svg)\n', PAGES)
    assert text == '![Layers](images/layers.svg)\n'
    assert images == {'layers.svg'}


def test_inline_code_is_not_rewritten():
    text = 'links use `[Safety](Safety)`, like [Safety](Safety)'
    assert rewrite(text) == 'links use `[Safety](Safety)`, like [Safety](Safety.md)'


def test_fenced_code_is_not_rewritten():
    text = '```bash\n[Safety](Safety)\n````\n[Safety](Safety)\n'
    assert rewrite(text) == '```bash\n[Safety](Safety)\n````\n[Safety](Safety.md)\n'
    longer = '````\n```\n[Safety](Safety)\n````\n'
    assert rewrite(longer) == longer
    tilde = '~~~\n[Safety](Safety)\n~~~\n'
    assert rewrite(tilde) == tilde


def test_slug_matches_github():
    assert prepare.slug('Measure the braking limits\n') == 'measure-the-braking-limits'
    assert prepare.slug('TF latency: diagnosis in ten minutes') == (
        'tf-latency-diagnosis-in-ten-minutes'
    )
    assert prepare.slug('map -> odom') == 'map---odom'


PAGE = (
    '# Title\n\nIntro text.\n\n![d](images/d.svg)\n\n## Start here\n\nA\n\n## Repositories\n\nB\n'
)


def test_section_intro_and_named():
    assert prepare.section(PAGE, 'intro') == 'Intro text.\n\n![d](images/d.svg)\n'
    assert prepare.section(PAGE, 'start-here') == '## Start here\n\nA\n'
    assert prepare.section(PAGE, 'repositories') == '## Repositories\n\nB\n'
    with pytest.raises(prepare.PrepareError):
        prepare.section(PAGE, 'nothing')


@pytest.fixture
def tree(tmp_path):
    """A docs/ tree: two wiki pages, a sidebar, a README, site pages, exports and a PDF."""
    wiki = tmp_path / 'wiki'
    wiki.mkdir()
    (wiki / 'Home.md').write_text('# Home\n\nSee [Safety](Safety).\n\n## More\n\nM\n')
    (wiki / 'Safety.md').write_text('# Safety\n\n![p](images/p.svg)\n\n[Home](Home)\n')
    (wiki / '_Sidebar.md').write_text('- [Safety](Safety)\n')
    (wiki / 'README.md').write_text('not a page\n')
    pages = tmp_path / 'site' / 'pages'
    (pages / 'assets').mkdir(parents=True)
    (pages / 'index.md').write_text('# Site\n\n<!-- include: Home#intro -->\n\n[d](pdf/d.pdf)\n')
    (pages / 'assets' / 'x.css').write_text('a {}\n')
    svg = tmp_path / 'diagrams' / 'svg'
    svg.mkdir(parents=True)
    (svg / 'p.svg').write_text('<svg/>')
    (svg / 'unused.svg').write_text('<svg/>')
    (tmp_path / 'build').mkdir()
    (tmp_path / 'build' / 'd.pdf').write_bytes(b'%PDF')
    return tmp_path


def run(tree, monkeypatch, **kwargs):
    monkeypatch.setattr(prepare, 'PDFS', (('pdf/d.pdf', 'build/d.pdf'),))
    out = tree / 'out'
    return out, set(prepare.build(out, tree, **kwargs))


def test_build_writes_the_site_sources(tree, monkeypatch):
    out, files = run(tree, monkeypatch)
    assert files == {'Safety.md', 'index.md', 'assets/x.css', 'images/p.svg', 'pdf/d.pdf'}
    assert (
        out / 'Safety.md'
    ).read_text() == '# Safety\n\n![p](images/p.svg)\n\n[Home](index.md)\n'
    index = (out / 'index.md').read_text()
    assert index == '# Site\n\nSee [Safety](Safety.md).\n\n[d](pdf/d.pdf)\n'
    assert (out / 'pdf' / 'd.pdf').read_bytes() == b'%PDF'
    assert not (out / '_Sidebar.md').exists()
    assert not (out / 'README.md').exists()
    assert not (out / 'images' / 'unused.svg').exists()


def test_build_empties_the_output(tree, monkeypatch):
    (tree / 'out').mkdir()
    (tree / 'out' / 'Stale.md').write_text('old')
    out, _ = run(tree, monkeypatch)
    assert not (out / 'Stale.md').exists()


def test_missing_diagram_fails(tree, monkeypatch):
    (tree / 'diagrams' / 'svg' / 'p.svg').unlink()
    with pytest.raises(prepare.PrepareError, match=r'images/p\.svg'):
        run(tree, monkeypatch)


def test_missing_pdf_fails_unless_skipped(tree, monkeypatch):
    (tree / 'build' / 'd.pdf').unlink()
    with pytest.raises(prepare.PrepareError, match='--skip-pdfs'):
        run(tree, monkeypatch)
    out, files = run(tree, monkeypatch, skip_pdfs=True)
    assert 'pdf/d.pdf' not in files
    assert f'[d]({prepare.SITE_URL}pdf/d.pdf)' in (out / 'index.md').read_text()


def test_bad_include_fails(tree, monkeypatch):
    index = tree / 'site' / 'pages' / 'index.md'
    index.write_text('<!-- include: Missing#intro -->\n')
    with pytest.raises(prepare.PrepareError, match='Missing'):
        run(tree, monkeypatch)
    index.write_text('<!-- include: Home#nothing -->\n')
    with pytest.raises(prepare.PrepareError, match='nothing'):
        run(tree, monkeypatch)


def test_main(tree, monkeypatch, capsys):
    monkeypatch.setattr(prepare, 'PDFS', (('pdf/d.pdf', 'build/d.pdf'),))
    assert prepare.main(['--docs', str(tree)]) == 0
    assert (tree / 'build' / 'site-src' / 'Safety.md').is_file()
    assert 'prepare: 5 files' in capsys.readouterr().out
    assert prepare.main(['--docs', str(tree / 'nothing'), '--out', str(tree / 'o')]) == 1
    assert 'no wiki pages' in capsys.readouterr().err


def test_the_real_docs(tmp_path):
    """Every wiki page and diagram reference of the repository makes a site."""
    out = tmp_path / 'site-src'
    files = prepare.build(out, skip_pdfs=True)
    wiki = {p.name for p in (DOCS / 'wiki').glob('*.md')} - prepare.NOT_PAGES - {'Home.md'}
    assert wiki <= set(files)
    assert {'index.md', 'downloads.md'} <= set(files)
    for path in out.glob('*.md'):
        text = path.read_text(encoding='utf-8')
        assert '<!-- include:' not in text
        for target in re.findall(r'\]\(([A-Z][A-Za-z-]+)(?:#[^)]*)?\)', text):
            pytest.fail(f'{path.name}: wiki link {target} not rewritten')


def test_mkdocs_nav_lists_every_page():
    """mkdocs.yml names every page prepare writes (strict builds also warn on omissions)."""
    config = (SITE / 'mkdocs.yml').read_text(encoding='utf-8')
    nav = set(re.findall(r'^\s+- (?:[^:\n]+: )?([A-Za-z-]+\.md)$', config, re.MULTILINE))
    wiki = {p.name for p in (DOCS / 'wiki').glob('*.md')} - prepare.NOT_PAGES - {'Home.md'}
    assert wiki | {'index.md', 'downloads.md'} == nav
