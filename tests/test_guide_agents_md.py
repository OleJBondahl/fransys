"""`AGENTS.md`'s own text names the resource-loading mechanism it tells an agent to use to
find the guide (CG5). This proves that mechanism actually works: it extracts the exact
expression `AGENTS.md` gives (a plain, non-`python`-labeled fence) and executes it, rather
than checking a hand-copied duplicate string against it. A test that only string-matched
would still pass if the named call could never actually load anything.
"""

import importlib.resources
import re

_FENCE = re.compile(r"```(\w*)\n(.*?)\n```", re.DOTALL)


def _agents_md_text() -> str:
    return (
        importlib.resources.files("fransys")
        .joinpath("guide", "AGENTS.md")
        .read_text(encoding="utf-8")
    )


def _mechanism_expression(text: str) -> str:
    """The one fenced snippet of `text` that is not language-tagged `python` (CG5:
    `AGENTS.md`'s mechanism fence is deliberately plain prose, not a runnable python
    block, so it stays out of `test_guide_examples.py`'s block scan)."""
    fences = [body for lang, body in _FENCE.findall(text) if lang != "python"]
    assert len(fences) == 1, f"expected exactly one non-python fence, found {len(fences)}"
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
    assert "docs/contracts/part-file.md" in text
