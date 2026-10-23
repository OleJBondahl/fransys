"""`AGENTS.md`'s own text names the resource-loading mechanism it tells an agent to use to
find the guide. This proves that mechanism actually works: it extracts the exact
expression `AGENTS.md` gives (a plain, non-`python`-labeled fence) and executes it, rather
than checking a hand-copied duplicate string against it. A test that only string-matched
would still pass if the named call could never actually load anything.
"""

import importlib.resources
import re
import subprocess
import sys

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


def _route_block(text: str) -> str:
    (block,) = [body for lang, body in _FENCE.findall(text) if lang == "markdown"]
    return block


def test_agents_md_holds_a_paste_able_route_block():
    """H2: one `markdown` fence of at most 5 lines names the site for the installed version,
    `help KEY` and the installed guide as the offline fallback; the page links Type checking."""
    text = _agents_md_text()
    block = _route_block(text)
    assert len(block.splitlines()) <= 5
    assert f"{SITE_URL}X.Y.Z/llms.txt" in block
    assert 'importlib.metadata.version("fransys")' in block
    assert "python -m fransys help KEY" in block
    assert "Offline only" in block
    assert 'importlib.resources.files("fransys")' in block
    assert "](keywords.md#type-checking)" in text
    keywords = importlib.resources.files("fransys").joinpath("guide", "keywords.md")
    assert "\n## Type checking\n" in keywords.read_text(encoding="utf-8")


def test_the_block_help_command_runs():
    """H2: the `help KEY` line of the pasted block, with `write` for KEY, works as written."""
    (line,) = [ln for ln in _route_block(_agents_md_text()).splitlines() if "help KEY" in ln]
    command = re.search(r"`(python -m fransys help KEY)`", line)
    assert command is not None
    argv = command.group(1).replace("KEY", "write").split()
    argv[0] = sys.executable
    run = subprocess.run(argv, capture_output=True, text=True, check=False)  # noqa: S603 -- the block's own command
    assert run.returncode == 0
    assert run.stdout.startswith("fr.write(")


def test_the_index_tells_the_consumer_to_paste_the_block():
    index = importlib.resources.files("fransys").joinpath("guide", "index.md")
    text = index.read_text(encoding="utf-8")
    assert "[AGENTS.md](AGENTS.md)" in text
    assert "`CLAUDE.md`" in text
