"""Suppression check, a scan of `src` comments: only `# noqa: PLR2004` may remain.

Fails on a bare `# noqa` and on any noqa code other than PLR2004. The core takes source text so
the can-fail tests feed it tmp_path source; the real check runs on the package.
"""

import io
import re
import tokenize
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PACKAGE_ROOT / "src" / "fransys_layout"

ALLOWED_CODES = frozenset({"PLR2004"})
NOQA = re.compile(
    r"#\s*noqa\b(?::\s*(?P<codes>[A-Za-z0-9]+(?:\s*,\s*[A-Za-z0-9]+)*))?", re.IGNORECASE
)


def suppressions(source: str) -> list[tuple[int, str]]:
    """(line, what) of each bare `# noqa` and each noqa code outside ALLOWED_CODES."""
    found = []
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        match = NOQA.search(tok.string) if tok.type == tokenize.COMMENT else None
        if match is None:
            continue
        if match["codes"] is None:
            found.append((tok.start[0], "bare noqa"))
            continue
        codes = [c.strip().upper() for c in match["codes"].split(",")]
        found += [(tok.start[0], code) for code in codes if code not in ALLOWED_CODES]
    return found


def scan(src_root: Path) -> list[str]:
    """One `path:line: what` per forbidden suppression under `src_root`."""
    out = []
    for path in sorted(src_root.rglob("*.py")):
        rel = path.relative_to(src_root).as_posix()
        hits = suppressions(path.read_text(encoding="utf-8"))
        out += [f"{rel}:{line}: {what}" for line, what in hits]
    return out


def _write(tmp_path: Path, source: str) -> list[str]:
    (tmp_path / "mod.py").write_text(source, encoding="utf-8")
    return scan(tmp_path)


def test_forbidden_code_flagged(tmp_path):
    hits = _write(tmp_path, "def f(a): ...  # noqa: PLR0913\n")
    assert hits == ["mod.py:1: PLR0913"]


def test_mixed_codes_flag_only_the_forbidden(tmp_path):
    hits = _write(tmp_path, "x = 1  # noqa: PLR2004, C901 reason\n")
    assert hits == ["mod.py:1: C901"]


def test_bare_noqa_flagged(tmp_path):
    hits = _write(tmp_path, "import os\nx = 1  # noqa\n")
    assert hits == ["mod.py:2: bare noqa"]


def test_plr2004_alone_passes(tmp_path):
    assert _write(tmp_path, "x = 1 > 3  # noqa: PLR2004 a rule constant\n") == []


def test_noqa_text_in_a_string_passes(tmp_path):
    assert _write(tmp_path, "s = '# noqa: PLR0913'\n") == []


def test_package_has_no_forbidden_suppression():
    assert scan(SRC_ROOT) == []
