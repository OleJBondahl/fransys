"""The first-party import scan of a consumer script, shared by the guide tests."""

from import_walk import top_level_imports

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
    return top_level_imports(source) & _FIRST_PARTY_NOT_FRANSYS
