"""Where a consumer reads the Fransys documentation: the site, a version's path, a finding's row.

The site is the official documentation (decision 0105, DOCS-FOR-AGENTS). Every pointer to it, in
a docstring, a guide banner or a finding, is built here.
"""

__all__ = ["OFFLINE_NOTE", "SITE_URL", "finding_url", "version_url"]

SITE_URL = "https://olejbondahl.github.io/fransys/"

OFFLINE_NOTE = (
    f"> Offline copy. Read the official docs for your version at {SITE_URL}X.Y.Z/ "
    f"(X.Y.Z is `fransys.__version__`), or {SITE_URL}X.Y.Z/llms.txt. Use this copy only offline."
)


def version_url(version: str) -> str:
    """The site root of one release, `SITE_URL` plus `<version>/`."""
    return f"{SITE_URL}{version}/"


def finding_url(version: str, see: str) -> str:
    """The URL of a finding code's row on that release's findings page, from `CodeInfo.see`.

    `see` is `<page>#<anchor>`, as `CodeInfo.see` gives it.
    """
    page, _, anchor = see.partition("#")
    return f"{version_url(version)}guide/{page}/#{anchor}"
