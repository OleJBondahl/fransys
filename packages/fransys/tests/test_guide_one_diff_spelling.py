"""The guide teaches `fr.diff` alone for the change list, not `derive.baseline.diff` (O13)."""

from importlib.resources import files

_GUIDE = files("fransys") / "guide"


def _pages() -> dict[str, str]:
    return {
        p.name: p.read_text(encoding="utf-8") for p in _GUIDE.iterdir() if p.name.endswith(".md")
    }


def test_no_page_teaches_the_derive_baseline_diff() -> None:
    assert [n for n, text in _pages().items() if "baseline.diff" in text] == []


def test_the_build_page_teaches_sk_diff() -> None:
    assert "`fr.diff(result, into" in _pages()["build.md"]
