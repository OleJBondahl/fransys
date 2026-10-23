"""`python -m fransys help KEY` for a finding code, and the close names offered for a miss."""

import difflib

import fransys
from fransys._codes import BY_CODE
from fransys_model.derive.docs_site import version_url


def lookup_code(key: str) -> str | None:
    """The printed row of finding code `key`, read from `BY_CODE`, or None if it is no code."""
    info = BY_CODE.get(key)
    if info is None:
        return None
    severities = ", ".join(s.name for s in info.severities)
    return "\n".join(
        [
            f"{info.code}: {severities}",
            f"stage: {info.stage}",
            f"who acts: {info.who}",
            f"cause: {info.cause}",
            f"fix: {info.fix}",
            f"guide: {info.page}.md",
            f"site: {version_url(fransys.__version__)}guide/{info.page}.md",
        ]
    )


def suggest(key: str) -> tuple[str, ...]:
    """Up to five public names or codes close to `key`, best match first."""
    bare = key.removeprefix("fr.")
    pool = {*fransys.__all__, *BY_CODE}
    return tuple(difflib.get_close_matches(bare, pool, n=5, cutoff=0.6))
