"""Every built site page carries the Beta banner, which comes from `website/mkdocs.yml` (PM9)."""

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
def built_site(tmp_path_factory):
    """One real Zensical build of the site from a one-clone example folder (a few seconds)."""
    pytest.importorskip("zensical", reason="the `site` dependency group is not installed")
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


def test_every_built_page_has_the_banner(built_site):
    """Each HTML page under the built site holds the banner text exactly."""
    pages = sorted(built_site.rglob("*.html"))
    assert pages
    missing = [str(p.relative_to(built_site)) for p in pages if BANNER not in p.read_text("utf-8")]
    assert not missing
