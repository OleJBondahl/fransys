"""Typst string literals: the one place engineer-authored text becomes Typst source (spec P6)."""


def literal(text: str) -> str:
    """`text` as a Typst string literal, backslash and quote escaped, never as markup."""
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def description_par(text: str) -> str:
    """A paragraph line for `text`, `""` when it is empty (a strip's description, author-0013)."""
    return f"#par(text({literal(text)}))\n" if text else ""
