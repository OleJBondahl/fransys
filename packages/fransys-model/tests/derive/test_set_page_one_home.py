"""`set_page_text` is the only writer of the `<set>.<page>` pair in `fransys_model` (T11)."""

import ast
from pathlib import Path

import fransys_model

_SRC = Path(fransys_model.__file__).parent
_HOME = "derive/sheet_forms.py"


def _dotted_page_writers() -> list[str]:
    """Every f-string that glues a `*page*` or `*number*` value to another with a literal `.`."""
    found: list[str] = []
    for path in sorted(_SRC.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.JoinedStr):
                continue
            parts = node.values
            found.extend(
                f"{path.relative_to(_SRC)}:{node.lineno}"
                for left, dot, right in zip(parts, parts[1:], parts[2:], strict=False)
                if isinstance(left, ast.FormattedValue)
                and isinstance(right, ast.FormattedValue)
                and isinstance(dot, ast.Constant)
                and dot.value == "."
                and any(w in ast.unparse(right.value) for w in ("page", "number"))
            )
    return found


def test_set_page_text_is_the_only_writer_of_the_set_page_pair() -> None:
    """No f-string but `set_page_text`'s glues a set number to a page number with a dot."""
    writers = _dotted_page_writers()
    assert [w.split(":")[0] for w in writers] == [
        _HOME
    ]  # the scan sees the home, so a second shows
