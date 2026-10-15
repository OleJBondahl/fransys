"""The built site: banner on every page, a Markdown copy of each, the llms files, search."""

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

build_site = importlib.import_module("build_site")

BANNER = "Beta: the API may change between minor versions until 1.0.0."


def test_config_and_override_carry_the_banner():
    """Runs without Zensical: the config holds the text, the override template prints it."""
    assert f'announce: "{BANNER}"' in (ROOT / "website" / "mkdocs.yml").read_text(encoding="utf-8")
    override = (ROOT / "website" / "overrides" / "main.html").read_text(encoding="utf-8")
    assert "config.extra.announce" in override


@pytest.fixture(scope="module")
def built_root(tmp_path_factory):
    """One real Zensical build of the site from a one-clone example folder (a few seconds)."""
    importlib.import_module(
        "zensical"
    )  # a missing `site` dependency group fails here, naming zensical
    work = tmp_path_factory.mktemp("site")
    examples = work / "examples"
    (examples / "out" / "all").mkdir(parents=True)
    (examples / "README.md").write_text("# Examples\n\nDemo.\n", encoding="utf-8")
    (examples / "out" / "all" / "demo-bom.csv").write_text("a,b\n", encoding="utf-8")
    state = work / "state"
    state.mkdir()
    paths = {
        "STATE": state,
        "SRC": state / "site-src",
        "OUT": state / "site",
        "SNIPPETS": state / "snippets",
    }
    with pytest.MonkeyPatch.context() as patch:
        for name, value in paths.items():
            patch.setattr(build_site, name, value)
        build_site.stage(examples)
        build_site.build()
    return state / "site"


@pytest.fixture(scope="module")
def built_site(built_root):
    """The `<X.Y.Z>/` folder of the built site."""
    return built_root / build_site.fr.__version__


def test_every_built_page_has_the_banner(built_site):
    """Each HTML page under the built site holds the banner text exactly."""
    pages = sorted(built_site.rglob("*.html"))
    assert pages
    missing = [str(p.relative_to(built_site)) for p in pages if BANNER not in p.read_text("utf-8")]
    assert not missing


def test_every_page_has_a_markdown_copy_and_links_it(built_site):
    """D2: each HTML page but 404 has `index.md` beside it and a link to it."""
    for page in sorted(built_site.rglob("index.html")):
        copy = page.with_name("index.md")
        assert copy.is_file(), page
        assert copy.read_text("utf-8").startswith("#"), copy
        assert 'rel="alternate" type="text/markdown"' in page.read_text("utf-8"), page
        assert "Markdown copy of this page" in page.read_text("utf-8"), page


def test_the_llms_files_and_the_search_index_are_published(built_site):
    """D3, D4: llms.txt names the version first; llms-full.txt holds the guide; search.json."""
    version = build_site.fr.__version__
    assert (built_site / "llms.txt").read_text("utf-8").splitlines()[0] == f"# Fransys {version}"
    full = (built_site / "llms-full.txt").read_text("utf-8")
    assert full.splitlines()[0] == f"# Fransys {version}"
    assert "# Finding codes: PDF" in full
    assert (built_site / "search.json").stat().st_size > 0


def test_the_layout_keeps_the_version_beside_latest_and_a_root_that_goes_to_latest(built_root):
    """D1: `<X.Y.Z>/` and `latest/` hold the same pages, the footer names the version, the root
    page redirects to `latest/` and the root llms.txt names the versioned form."""
    version = build_site.fr.__version__
    assert sorted(p.name for p in built_root.iterdir()) == [
        version,
        "index.html",
        "latest",
        "llms.txt",
    ]
    for name in (version, "latest"):
        page = (built_root / name / "guide" / "index.html").read_text("utf-8")
        assert f"Fransys {version} documentation" in page
    assert "url=latest/" in (built_root / "index.html").read_text("utf-8")
    root = (built_root / "llms.txt").read_text("utf-8")
    assert f"{version}/llms.txt" in root
    assert "<X.Y.Z>/llms.txt" in root


def test_a_dev_version_has_no_site_path(monkeypatch, tmp_path):
    """No silent fallback: a version that is not X.Y.Z stops the layout, naming it."""
    monkeypatch.setattr(build_site.fr, "__version__", "0.19.5.dev1")
    monkeypatch.setattr(build_site, "OUT", tmp_path / "out")
    with pytest.raises(SystemExit, match=r"0\.19\.5\.dev1"):
        build_site.lay_out(tmp_path)


def test_every_finding_row_url_lands_on_an_anchor_of_the_built_findings_page(built_site):
    """D6: the `see:` URL of each registered code names a row anchor that exists on that page."""
    from fransys import _codes

    missing = []
    for info in _codes.BY_CODE.values():
        page = (built_site / "guide" / info.page / "index.html").read_text("utf-8")
        if f'id="{info.code.lower()}"' not in page:
            missing.append(info.code)
    assert not missing
