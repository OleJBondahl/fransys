"""`AGENTS.md`'s own text names the resource-loading mechanism it tells an agent to use to
find the guide. This proves that mechanism actually works: it extracts the exact
expression `AGENTS.md` gives (a plain, non-`python`-labeled fence) and executes it, rather
than checking a hand-copied duplicate string against it. A test that only string-matched
would still pass if the named call could never actually load anything.
"""

import importlib.resources
import re

from fransys_model.derive.docs_site import SITE_URL

_FENCE = re.compile(r"```(\w*)\n(.*?)\n```", re.DOTALL)


def _agents_md_text() -> str:
    return (
        importlib.resources.files("fransys")
        .joinpath("guide", "AGENTS.md")
        .read_text(encoding="utf-8")
    )


def _mechanism_expression(text: str) -> str:
    """The one fenced snippet of `text` that is not language-tagged `python` (`AGENTS.md`'s
    mechanism fence is deliberately plain prose, not a runnable python
    block, so it stays out of `test_guide_examples.py`'s block scan)."""
    fences = [body for lang, body in _FENCE.findall(text) if lang == ""]
    assert len(fences) == 1, f"expected exactly one plain fence, found {len(fences)}"
    return fences[0].strip()


def test_agents_md_has_no_python_fence():
    assert "```python" not in _agents_md_text()


def test_agents_md_mechanism_actually_loads_the_guide():
    """Extract the folder-finding expression `AGENTS.md` names, then execute it (not a
    second, independently-written copy of it) to load `index.md` through it for real."""
    expression = _mechanism_expression(_agents_md_text())
    call = expression + '.joinpath("index.md").read_text(encoding="utf-8")'
    # Scoped to just `importlib` (so `importlib.resources...`, exactly as named, resolves);
    # no other builtins, since the extracted call needs none.
    result = eval(call, {"__builtins__": {}, "importlib": importlib}, {})  # noqa: S307
    assert result.startswith("# Fransys")


def test_agents_md_points_at_index_and_part_file_contract():
    text = _agents_md_text()
    assert "index.md" in text
    assert f"{SITE_URL}X.Y.Z/contracts/part-file/index.md" in text


def test_agents_md_holds_a_paste_able_route_block():
    """D7: one `markdown` fence names the site, the version source, llms.txt, the Markdown
    form and the offline-only rule, and the page links the Type checking section."""
    text = _agents_md_text()
    (block,) = [body for lang, body in _FENCE.findall(text) if lang == "markdown"]
    assert f"{SITE_URL}X.Y.Z/llms.txt" in block
    assert "llms-full.txt" in block
    assert 'importlib.metadata.version("fransys")' in block
    assert "plus `index.md`" in block
    assert "offline fallback" in block
    assert "](keywords.md#type-checking)" in text
    keywords = importlib.resources.files("fransys").joinpath("guide", "keywords.md")
    assert "\n## Type checking\n" in keywords.read_text(encoding="utf-8")
