"""Interactive system overview HTML."""

import json
from html import escape
from typing import TYPE_CHECKING

from ._app import APP_JS
from ._data import page_data
from ._template import TEMPLATE, fill
from ._vendor_cytoscape import CYTOSCAPE_MIN_JS

if TYPE_CHECKING:
    from fransys_model.derive.baseline import ListingDiff
    from fransys_model.kernel import Finding, Model

# The rows carry no project name, and nothing is looked up, so the title is this.
TITLE = "System overview"


def _json_escape(char: str) -> str:
    """`char` as a JSON escape: a backslash, `u` and four hex digits, which `json.loads` reads."""
    return chr(92) + "u" + f"{ord(char):04x}"


# A data block inside a `<script>` element is raw text: `</script>` ends it, and `&lt;` is not
# decoded. So the three characters are written as JSON escapes, inside the JSON strings.
_SCRIPT_SAFE = {char: _json_escape(char) for char in "<>&"}


def _data_block(model: Model, findings: tuple[Finding, ...], changes: ListingDiff | None) -> str:
    """The JSON of `page_data`, safe inside a `<script>` element."""
    text = json.dumps(
        page_data(model, findings, changes),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    for char, escaped in _SCRIPT_SAFE.items():
        text = text.replace(char, escaped)
    return text


def html(
    model: Model, *, findings: tuple[Finding, ...] = (), changes: ListingDiff | None = None
) -> str:
    """Render the system overview as one self-contained, interactive page.

    Draws the views `fransys_model.derive.overview_view_rows` gives at the positions of the
    `layout.overview_*` records, so `model` is the one `lay_out_overview` returns; none gives no
    views. Library, script and data are inline: no network, no layout. Pure.

    Args:
        model: A frozen model with its overview records.
        findings: The findings of the same build; the Findings switch badges what they name.
        changes: The `ListingDiff` from the last release, or `None`. The Changes switch marks
            what it adds or changes, lists what it removes, and offers "Changes only".

    Returns:
        The overview page as HTML text. Same model digest, same bytes.
    """
    values = {
        "TITLE": escape(TITLE),
        "CYTOSCAPE": CYTOSCAPE_MIN_JS,
        "DATA": _data_block(model, findings, changes),
        "APP": APP_JS,
    }
    return fill(TEMPLATE, values)
