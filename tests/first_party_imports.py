"""The first-party import scan of a consumer script, shared by the guide tests."""

import ast

# Every first-party import name besides `fransys` itself (a consumer script imports nothing else).
_FIRST_PARTY_NOT_FRANSYS = frozenset(
    {
        "fransys_model",
        "symdef",
        "electrical_symbols",
        "fransys_parts",
        "fransys_author",
        "fransys_layout",
        "fransys_render",
        "fransys_reports",
        "fransys_pdf",
        "fransys_kicad",
        "fransys_wago",
        "fransys_overview",
    }
)


def first_party_violations(source: str) -> set[str]:
    """First-party top-level packages `source` imports besides `fransys` itself."""
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported.add(node.module.split(".")[0])
    return imported & _FIRST_PARTY_NOT_FRANSYS
