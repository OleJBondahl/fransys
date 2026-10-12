"""Typst string literals: the one place engineer-authored text becomes Typst source."""


def literal(text: str) -> str:
    """`text` as a Typst string literal, backslash and quote escaped, never as markup."""
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def description_par(text: str) -> str:
    """A sticky paragraph for `text`, `""` when empty: it stays with its table (author-0013, L7)."""
    return f"#block(sticky: true, par(text({literal(text)})))\n" if text else ""
