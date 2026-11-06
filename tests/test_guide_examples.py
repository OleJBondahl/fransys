"""Every ```python``` block of the consumer guide's twelve pages actually runs.

Deliberately not built once: each page gets its own fresh namespace so that a page's blocks
can build on each other (a later block reuses an earlier one's imports and variables) while
"""

import importlib
import re
import sys
from importlib.resources import files
from typing import Any

import fransys as fr
from _expected_codes import expect_codes
from first_party_imports import first_party_violations

# The fixed twelve guide pages, by filename stem; `AGENTS.md` is not one of
# them. Parametrize id is the page name itself (e.g. `test_...[build]`), not a discovered
# file path: a page that does not exist yet, and a missing page surfaces as a normal,
# uncaught `FileNotFoundError` at its own test id.
GUIDE_PAGES = (
    "index",
    "parts",
    "authoring",
    "series",
    "drawn-ledger",
    "detail",
    "harnesses",
    "units",
    "build",
    "documents",
    "reading",
    "layout-numbers",
    "reading-rows",
    "reading-records",
    "keywords",
    "keywords-design",
    "keywords-handles",
    "keywords-output",
    "settings",
    "moving-to-0.22",
    "moving-to-0.20",
    "moving-to-0.19",
    "moving-to-0.16-and-0.17",
    "moving-to-0.15",
    "moving-to-0.14",
    "findings",
    "findings-validators",
    "findings-build",
    "findings-release",
    "findings-render",
    "findings-pdf",
    "findings-kicad",
    "findings-parts",
    "examples",
    "moving-to-0.6",
    "kicad",
    "moving-to-fransys",
    "drawing",
    "readability",
    "overview",
)

_FENCE = re.compile(r"```python\n(.*?)```", re.DOTALL)


def _python_blocks(markdown: str) -> list[str]:
    """Every ```python fenced code block of `markdown`, its own text, in document order."""
    blocks: list[str] = [str(block) for block in _FENCE.findall(markdown)]
    return blocks


def _page_blocks(page: str) -> list[str]:
    """`page`'s python blocks, read through the installed package (a `FileNotFoundError`
    propagates uncaught for a page that does not exist yet)."""
    text = files("fransys").joinpath("guide", f"{page}.md").read_text(encoding="utf-8")
    return _python_blocks(text)


def run_blocks(page: str, blocks: list[str]) -> None:
    """Run `blocks` in one namespace; leave `sys.path`, `sys.modules` and the finder cache as found.

    The import caches are invalidated before each block: a block that creates a package in the
    working directory within the finder's cached directory mtime tick would not find it.
    """
    path, modules, finders = list(sys.path), set(sys.modules), set(sys.path_importer_cache)
    namespace: dict[Any, Any] = {}
    try:
        for block in blocks:
            importlib.invalidate_caches()
            exec(compile(block, f"<{page}.md>", "exec"), namespace, namespace)  # noqa: S102 (the page's own runnable block)
    finally:
        sys.path[:] = path
        for name in set(sys.modules) - modules:
            del sys.modules[name]
        for entry in set(sys.path_importer_cache) - finders:
            del sys.path_importer_cache[entry]


def test_guide_page_blocks_run(page, tmp_path, monkeypatch):
    blocks = _page_blocks(page)
    page_dir = tmp_path / page
    page_dir.mkdir()
    monkeypatch.chdir(page_dir)
    built: list[Any] = []
    real = fr.build

    def spy(*args: Any, **kwargs: Any) -> Any:
        built.append(real(*args, **kwargs))
        return built[-1]

    monkeypatch.setattr(fr, "build", spy)
    run_blocks(page, blocks)
    if page == "reading":  # its first build, the branch-current example, shows the finding by design (R1741 Q1, R1712)
        expect_codes(built[0], "RATING_CURRENT_BELOW_BRANCH")


def test_a_block_creating_a_package_in_the_cached_tick_still_imports_it(tmp_path, monkeypatch):
    """UNDO: drop `importlib.invalidate_caches()` from `run_blocks`; block 2 cannot import."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "dont_write_bytecode", True)  # a __pycache__ would move the mtime
    first = "import sys\nsys.path.insert(0, '.')\nopen('one_mod.py', 'w').write('X = 1')\nimport one_mod\n"
    # Block 2 sets the directory's mtime back to what block 1's import cached: the same tick.
    second = (
        "import os\nstamp = os.stat('.').st_mtime_ns\n"
        "os.mkdir('two_pkg')\nopen('two_pkg/__init__.py', 'w').write('Y = 2')\n"
        "os.utime('.', ns=(stamp, stamp))\nimport two_pkg\nassert two_pkg.Y == 2\n"
    )
    run_blocks("tick", [first, second])


def test_run_blocks_restores_sys_path_and_modules(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    importlib.invalidate_caches()  # run_blocks drops stale finder entries; compare like with like
    before = list(sys.path), set(sys.modules), set(sys.path_importer_cache)
    block = "import sys\nsys.path.insert(0, '.')\nopen('gone_mod.py', 'w').write('')\nimport gone_mod\n"
    run_blocks("restore", [block])
    assert (list(sys.path), set(sys.modules), set(sys.path_importer_cache)) == before


def test_guide_page_imports_only_fransys(page):
    blocks = _page_blocks(page)
    violations: dict[int, set[str]] = {}
    for index, block in enumerate(blocks):
        found = first_party_violations(block)
        if found:
            violations[index] = found
    assert violations == {}


def pytest_generate_tests(metafunc):
    if "page" in metafunc.fixturenames:
        metafunc.parametrize("page", GUIDE_PAGES, ids=GUIDE_PAGES)


# The twelve pages plus AGENTS.md (not one of the twelve): the guide folder's whole,
# fixed file list. Only meaningful once every guide file exists, which is why this
# assertion is not staged disabled inside an earlier commit: written here, at the point
# in this order's own sequence where all twelve are first committed together.
_EXPECTED_GUIDE_FILES = frozenset({f"{page}.md" for page in GUIDE_PAGES} | {"AGENTS.md"})


def test_all_twelve_guide_pages_and_agents_exist():
    """The installed package's `guide/` folder holds exactly twelve pages and `AGENTS.md`,
    no more and no fewer -- a page renamed, dropped or left over from a probe is caught here.
    """
    guide_dir = files("fransys").joinpath("guide")
    found = {entry.name for entry in guide_dir.iterdir() if entry.name.endswith(".md")}
    missing = _EXPECTED_GUIDE_FILES - found
    extra = found - _EXPECTED_GUIDE_FILES
    assert not missing, f"guide/ is missing: {sorted(missing)}"
    assert not extra, f"guide/ has unexpected files: {sorted(extra)}"
