"""Every place a consumer meets Fransys points at the official site (DOCS-FOR-AGENTS D6).

The `fransys` module docstring, the package metadata and the top of every page of the wheel's
guide name the site, the versioned path and `llms.txt`.
"""

import importlib.metadata
import importlib.resources
import tomllib
from pathlib import Path

import fransys as fr

from fransys_model.derive.docs_site import OFFLINE_NOTE, SITE_URL, version_url

ROOT = Path(__file__).resolve().parents[1]
GUIDE = Path(str(importlib.resources.files("fransys").joinpath("guide")))


def test_the_module_docstring_names_the_site_the_version_path_and_llms_txt() -> None:
    doc = fr.__doc__ or ""
    assert SITE_URL in doc
    assert version_url(fr.__version__) in doc
    assert f"{version_url(fr.__version__)}llms.txt" in doc


def test_every_guide_page_opens_with_the_offline_banner_naming_the_site() -> None:
    pages = sorted(GUIDE.glob("*.md"))
    assert len(pages) > 30
    for page in pages:
        lines = page.read_text(encoding="utf-8").splitlines()
        assert lines[0].startswith("# "), page.name
        assert lines[2] == OFFLINE_NOTE, page.name
    index = (GUIDE / "index.md").read_text(encoding="utf-8")
    assert f"{SITE_URL}X.Y.Z/" in index
    assert f"{SITE_URL}X.Y.Z/llms.txt" in index


def test_the_package_metadata_has_a_documentation_url() -> None:
    project = tomllib.loads((ROOT / "packages/fransys/pyproject.toml").read_text("utf-8"))[
        "project"
    ]
    assert project["urls"]["Documentation"] == SITE_URL
    assert importlib.metadata.metadata("fransys").get_all("Project-URL") is not None


def test_the_site_config_and_the_one_site_url_agree() -> None:
    config = (ROOT / "website" / "mkdocs.yml").read_text(encoding="utf-8")
    assert f"site_url: {SITE_URL}\n" in config


def test_the_package_summary_names_the_site() -> None:
    summary = importlib.metadata.metadata("fransys")["Summary"]
    assert SITE_URL + "latest/" in summary
    assert "llms.txt" in summary
