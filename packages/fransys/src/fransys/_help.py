"""`python -m fransys help KEY`: one key, a public name or a finding code (AGENT-HELP H1)."""

from fransys._help_codes import lookup_code, suggest
from fransys._help_names import names_text, resolve


def help_text(key: str) -> tuple[str, int]:
    """The text to print for `key` and the exit code: 0 if found, 1 if not."""
    found = resolve(key)
    if found is not None:
        return names_text(found), 0
    code = lookup_code(key)
    if code is not None:
        return code, 0
    lines = [f"no such name or code: {key}"]
    close = suggest(key)
    if close:
        lines.append(f"did you mean: {', '.join(close)}")
    return "\n".join(lines), 1
