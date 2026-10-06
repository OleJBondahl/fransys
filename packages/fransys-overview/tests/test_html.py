import json
import re
from html.parser import HTMLParser
from typing import override

import pytest
from fransys_overview import html
from fransys_overview._app import APP_JS
from fransys_overview._template import TEMPLATE, fill
from fransys_overview._vendor_cytoscape import CYTOSCAPE_MIN_JS
from fransys_overview.html import _json_escape

from fransys_model.derive import overview_graph
from fransys_model.kernel.ids import parse_id, render_id

_NETWORK_ATTRIBUTES = {"src", "href", "srcset", "action", "poster", "data", "ping", "formaction"}
_EMBEDDING_TAGS = {"link", "img", "iframe", "object", "embed", "source", "audio", "video", "base"}
_FORBIDDEN_IN_THE_APP = [
    "Math.random",
    "Date",
    "performance.",
    "fetch(",
    "XMLHttpRequest",
    "WebSocket",
    "localStorage",
    "sessionStorage",
    "eval(",
    "new Function",
    "innerHTML",
    "outerHTML",
    "document.write",
    "insertAdjacentHTML",
    "navigator",
    "http",
]


class _Page(HTMLParser):
    """The tags, the script elements and the title of a page, as `html.parser` reads it."""

    def __init__(self, page):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.scripts = []
        self.title = ""
        self._script = None
        self._in_title = False
        self.feed(page)
        self.close()

    @override
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        if tag == "script":
            self._script = (dict(attrs), [])
        self._in_title = tag == "title"

    @override
    def handle_endtag(self, tag):
        if tag == "script" and self._script is not None:
            attrs, parts = self._script
            self.scripts.append((attrs, "".join(parts)))
            self._script = None
        self._in_title = False

    @override
    def handle_data(self, data):
        if self._script is not None:
            self._script[1].append(data)
        elif self._in_title:
            self.title += data


def _network_problems(page):
    """What in `page` could reach the network; the vendored text and the licence are set aside."""
    parsed = _Page(page)
    found = [f"<{tag}>" for tag, _ in parsed.tags if tag in _EMBEDDING_TAGS]
    for tag, attrs in parsed.tags:
        for name, value in attrs.items():
            if name in _NETWORK_ATTRIBUTES:
                found.append(f"<{tag} {name}>")
            if re.match(r"\s*(https?:)?//", value or ""):
                found.append(f"<{tag} {name}={value!r}>")
    rest = page.replace(CYTOSCAPE_MIN_JS, "")
    found.extend(text for text in ("http", "://", "@import", "url(") if text in rest)
    return found


def _data_block(page):
    (block,) = [text for attrs, text in _Page(page).scripts if attrs.get("id") == "overview-data"]
    return block


def _expected(model):
    """What the rows say, in the plain form of the data block."""
    graph = overview_graph(model)
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


def test_the_page_is_one_document_with_three_scripts(demo_cabinet):
    page = html(demo_cabinet)
    parsed = _Page(page)
    assert page.startswith("<!DOCTYPE html>\n<html lang=")
    assert page.endswith("</html>\n")
    assert parsed.title == "System overview"
    assert [attrs for attrs, _ in parsed.scripts] == [
        {},
        {"type": "application/json", "id": "overview-data"},
        {},
    ]
    ids = [attrs.get("id") for _, attrs in parsed.tags]
    for wanted in ("cy", "detail", "search", "reset", "legend"):
        assert ids.count(wanted) == 1


def test_the_page_reaches_no_network(demo_cabinet):
    page = html(demo_cabinet)
    assert page.count(CYTOSCAPE_MIN_JS) == 1
    assert _network_problems(page) == []


@pytest.mark.parametrize(
    "spoiler",
    [
        '<script src="https://cdn.example/x.js"></script>',
        '<link rel="stylesheet" href="style.css">',
        '<img src="//example.org/x.png">',
        "<style>@import 'x.css';</style>",
        "<style>a { background: url(x.png); }</style>",
        "<p>see http://example.org</p>",
    ],
)
def test_the_network_check_can_fail(demo_cabinet, spoiler):
    page = html(demo_cabinet).replace("<body>", "<body>" + spoiler)
    assert _network_problems(page) != []


def test_the_data_block_is_the_rows(demo_cabinet):
    block = _data_block(html(demo_cabinet))
    assert json.loads(block) == _expected(demo_cabinet)


def test_the_demo_plant_covers_what_the_page_shows(demo_cabinet):
    data = json.loads(_data_block(html(demo_cabinet)))
    assert 20 <= len(data["nodes"]) <= 40
    assert {link["kind"] for link in data["links"]} == {"wire", "cable", "mate"}
    assert {node["location"] for node in data["nodes"]} == {None, "+C1", "+F2"}
    assert any(not node["installed"] for node in data["nodes"])
    assert any(node["parent"] is not None for node in data["nodes"])
    assert any(link["count"] > 1 for link in data["links"])
    assert {link["via"] for link in data["links"] if link["kind"] == "cable"} == {"-W1", "-W2"}
    assert data["signals"]


def test_the_block_is_written_the_documented_way(demo_cabinet):
    block = _data_block(html(demo_cabinet))
    assert block == json.dumps(
        json.loads(block), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    assert block.isascii()


def test_ids_are_the_models_own_serialised_ids(demo_cabinet):
    data = json.loads(_data_block(html(demo_cabinet)))
    for node in data["nodes"]:
        assert parse_id(node["id"]).kind == "item"
        assert render_id(parse_id(node["id"])) == node["id"]
    ids = {node["id"] for node in data["nodes"]}
    assert all(link["a"] in ids and link["b"] in ids for link in data["links"])


def test_an_unnumbered_item_is_labelled_by_its_description(demo_cabinet):
    nodes = json.loads(_data_block(html(demo_cabinet)))["nodes"]
    assert [node["label"] for node in nodes if node["label"] == "Spare relay"] == ["Spare relay"]
    assert "-K1" in [node["label"] for node in nodes]


AWKWARD = '</script><script>alert(1)</script> & &amp; <b>"x"</b> \u00fc\u65e5\u672c'


def _awkward_plant(plant):
    """Every string of the data block holds text that could end or start a script."""
    first = plant.item("x", AWKWARD, mpn=AWKWARD, description=AWKWARD)
    second = plant.item("y", None, description=AWKWARD)
    cable = plant.item("w", AWKWARD, mpn="SIM-CABLE")
    plant.place(first, AWKWARD)
    plant.wire((first, AWKWARD), (second, AWKWARD), "wire")
    plant.core(cable, (first, "1"), (second, "1"), "core")
    return plant.freeze()


def test_text_that_could_end_a_script_is_safe_and_comes_back_exactly(plant):
    model = _awkward_plant(plant)
    page = html(model)
    block = _data_block(page)
    assert not set("<>&") & set(block)
    assert block.isascii()
    assert json.loads(block) == _expected(model)
    data = json.loads(block)
    assert {node["label"] for node in data["nodes"]} == {AWKWARD, "-" + AWKWARD}
    assert AWKWARD in {node["location"] for node in data["nodes"]}
    assert AWKWARD in {node["mpn"] for node in data["nodes"]}
    assert AWKWARD in {port["marking"] for signal in data["signals"] for port in signal}
    assert "-" + AWKWARD in {link["via"] for link in data["links"]}
    assert page.lower().count("</script") == 3
    assert len(_Page(page).scripts) == 3


def test_the_escape_is_a_json_escape_not_an_entity(plant):
    model = _awkward_plant(plant)
    block = _data_block(html(model))
    backslash = chr(92)
    assert backslash + "u003c" in block
    assert backslash + "u003e" in block
    assert backslash + "u0026" in block
    assert "&lt;" not in block


def test_token_looking_text_in_the_data_survives(plant):
    plant.item("t", "@@APP@@", description="@@DATA@@ @@TITLE@@ @@NOPE@@")
    model = plant.freeze()
    page = html(model)
    assert json.loads(_data_block(page))["nodes"][0]["label"] == "-@@APP@@"
    assert page.count(APP_JS) == 1


def test_an_empty_model_is_a_valid_page_with_empty_lists(plant):
    page = html(plant.freeze())
    assert json.loads(_data_block(page)) == {"links": [], "nodes": [], "signals": []}
    assert _Page(page).title == "System overview"
    assert _network_problems(page) == []


def test_the_same_model_gives_the_same_bytes(demo_cabinet):
    assert html(demo_cabinet) == html(demo_cabinet)


@pytest.mark.parametrize("seed", range(6))
def test_insertion_order_does_not_change_the_bytes(demo_plant, seed):
    assert html(demo_plant.freeze(seed)) == html(demo_plant.freeze())


def test_the_page_has_no_date_time_or_user(demo_cabinet):
    rest = html(demo_cabinet).replace(CYTOSCAPE_MIN_JS, "")
    assert not re.search(r"\b(19|20)\d\d-\d\d-\d\d\b", rest)
    assert not re.search(r"\b\d\d:\d\d(:\d\d)?\b", rest)


def test_the_template_has_exactly_the_four_tokens():
    assert set(re.findall(r"@@([A-Z]+)@@", TEMPLATE)) == {"TITLE", "CYTOSCAPE", "DATA", "APP"}


def test_fill_replaces_every_token_in_one_pass():
    assert fill("<@@A@@ @@B@@ @@A@@>", {"A": "@@B@@", "B": "x"}) == "<@@B@@ x @@B@@>"


def test_fill_refuses_a_token_with_no_value():
    with pytest.raises(ValueError, match=r"no value for \['B', 'C'\]"):
        fill("@@A@@ @@B@@ @@C@@", {"A": "1"})


def test_fill_refuses_a_value_with_no_token():
    with pytest.raises(ValueError, match=r"no token for \['B', 'C'\]"):
        fill("@@A@@", {"A": "1", "B": "2", "C": "3"})


def test_json_escape_is_a_backslash_u_and_four_hex_digits():
    assert _json_escape("<") == "\\u003c"
    assert _json_escape("Z") == "\\u005a"


def test_the_page_script_is_pure_and_offline():
    for text in _FORBIDDEN_IN_THE_APP:
        assert text not in APP_JS, text
    for wanted in ("overview-data", "Escape", "textContent", "'preset'", "cytoscape("):
        assert wanted in APP_JS, wanted
    assert APP_JS.isascii()


def test_the_forbidden_word_check_can_fail():
    assert any(text in "const t = Math.random();" for text in _FORBIDDEN_IN_THE_APP)
