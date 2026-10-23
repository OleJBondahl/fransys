"""`set_page_text` is the only writer of the `<set>.<page>` pair in `fransys_model` (T11)."""

import ast
from pathlib import Path

import fransys_model

_SRC = Path(fransys_model.__file__).parent


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


def test_no_f_string_glues_a_set_number_to_a_page_number_with_a_typed_dot() -> None:
    """`set_page_text` reads the `[reference]` set_sep, so no site types the dot (B2a, C2.1)."""
    assert _dotted_page_writers() == []
