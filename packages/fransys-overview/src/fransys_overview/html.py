"""Interactive system overview HTML (spec section 6)."""

import json
from html import escape
from typing import TYPE_CHECKING

from fransys_model.derive import overview_graph
from fransys_model.kernel import render_id

from ._app import APP_JS
from ._template import TEMPLATE, fill
from ._vendor_cytoscape import CYTOSCAPE_MIN_JS

if TYPE_CHECKING:
    from fransys_model.derive import OverviewGraph
    from fransys_model.kernel import Model

# The rows carry no project name, and nothing is looked up, so the title is this.
TITLE = "System overview"


def _json_escape(char: str) -> str:
    """`char` as a JSON escape: a backslash, `u` and four hex digits, which `json.loads` reads."""
    return chr(92) + "u" + f"{ord(char):04x}"


# A data block inside a `<script>` element is raw text: `</script>` ends it, and `&lt;` is not
# decoded. So the three characters are written as JSON escapes, inside the JSON strings.
_SCRIPT_SAFE = {char: _json_escape(char) for char in "<>&"}


def _data(graph: OverviewGraph) -> dict[str, object]:
    """The rows as the plain data the page script reads; ids are the model's own `render_id`."""
    return {
        "nodes": [
            {
                "id": render_id(node.item),
                "installed": node.installed,
                "label": node.designation if node.designation is not None else node.description,
                "location": node.location_label,
                "mpn": node.mpn,
                "parent": None if node.parent is None else render_id(node.parent),
            }
            for node in graph.nodes
        ],
        "links": [
            {
                "a": render_id(link.a),
                "b": render_id(link.b),
                "count": link.count,
                "kind": link.kind.value,
                "via": link.via_designation,
            }
            for link in graph.links
        ],
        "signals": [
            [{"item": render_id(port.item), "marking": port.marking} for port in signal.ports]
            for signal in graph.signals
        ],
    }


def _data_block(graph: OverviewGraph) -> str:
    """The JSON of `_data`, safe inside a `<script>` element."""
    text = json.dumps(_data(graph), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    for char, escaped in _SCRIPT_SAFE.items():
        text = text.replace(char, escaped)
    return text


def html(model: Model) -> str:
    """Render the whole model as one self-contained, interactive overview page.

    Formats `fransys_model.derive.overview_graph` and nothing else. Library, script and data
    are inline, so the page needs no network; the browser lays it out, and the bytes do not
    depend on that layout. Pure.

    Args:
        model: A frozen model.

    Returns:
        The overview page as HTML text. Same model digest, same bytes.
    """
    values = {
        "TITLE": escape(TITLE),
        "CYTOSCAPE": CYTOSCAPE_MIN_JS,
        "DATA": _data_block(overview_graph(model)),
        "APP": APP_JS,
    }
    return fill(TEMPLATE, values)
