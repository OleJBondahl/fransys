"""`d.detail` holds the four detail calls, and their old names on `d` raise (author-0042, A2)."""

import re
from importlib.resources import files

import fransys as fr
import pytest
from fransys.colours import BK

_MOVED = ("wire", "net", "busbar", "rail_bond")
# The digest of this design built with d.wire, d.net, d.busbar and d.rail_bond at main 8650e4af9.
# The digest covers the demo part library, so it moved with the library, never with the move:
# 54c87f08d (main f6f5720e4), 60889bbd4 (DEMO-LAMP-24 rating, parts-0022) and 7597e12be (demo
# motor and relay coil draw, model-0232). At the batch merge of each of the last two, the merged
# tree with that change's part files set back gave the digest from before it (API-BATCH), and
# COIL-FAN-PINS's `plc-do-16ch.toml` (layout-0208 R1), checked the same way.
# SCHEMA_VERSION 19 to 20 (model-0256) moved it too.
_DIGEST_BEFORE_THE_MOVE = "2e734886cc5d3d361c32e1d1ee12d2bce67f80a41a5a585c70b627424898b7c0"


def test_each_moved_call_builds_the_model_it_built_on_d():
    d = fr.design("demo_parts", place="CAB")
    d.location("CAB", "Cabinet")
    strip = d.terminal_strip("X1", "DEMO-TB-2.5", 6)
    k1 = d.device("K1", "DEMO-CTR-3P-24")
    t = [strip[i] for i in range(1, 7)]
    d.detail.busbar(t[0], t[1])
    d.detail.rail_bond(t[2], t[3])
    d.detail.net("BUS", t[4], t[5])
    d.detail.wire(k1.main["1"], t[0].outer, wire=(BK, 1.5), label="W1")
    assert fr.build(d).model.digest == _DIGEST_BEFORE_THE_MOVE


@pytest.mark.parametrize("name", _MOVED)
def test_a_moved_name_on_d_raises_naming_its_new_home(name):
    d = fr.design("demo_parts")
    with pytest.raises(fr.AuthorError, match=rf"d\.{name} moved to d\.detail\.{name} in 0\.19\.0"):
        getattr(d, name)
    assert not hasattr(d, name)
    assert not hasattr(fr.Design, name)
    assert callable(getattr(d.detail, name))


def test_the_moved_wire_error_names_its_core_path():
    with pytest.raises(
        fr.AuthorError,
        match=(
            r"d\.wire moved to d\.detail\.wire in 0\.19\.0; "
            r"a current path is d\.series\(\.\.\.\): see moving-to"
        ),
    ):
        fr.design("demo_parts").wire  # noqa: B018 -- the lookup itself raises
    assert isinstance(fr.design("demo_parts").detail, fr.Detail)


@pytest.mark.parametrize("name", ["net", "busbar", "rail_bond"])
def test_the_other_moved_errors_name_no_core_path(name):
    with pytest.raises(fr.AuthorError) as raised:
        getattr(fr.design("demo_parts"), name)
    assert re.fullmatch(
        rf"d\.{name} moved to d\.detail\.{name} in 0\.19\.0: see moving-to-0\.19#[\w-]+",
        str(raised.value),
    )


def _slug(heading: str) -> str:
    """A markdown heading's anchor: lower case, words joined by `-`, other marks dropped."""
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def anchors(page: str) -> set[str]:
    text = files("fransys").joinpath("guide", page).read_text(encoding="utf-8")
    return {_slug(line.lstrip("#")) for line in text.splitlines() if line.startswith("#")}


def test_the_moved_name_error_points_to_a_section_of_the_moving_to_page():
    """A10: the raise names `moving-to-0.19#<anchor>`, and the page has that heading."""
    with pytest.raises(fr.AuthorError) as raised:
        fr.design("demo_parts").busbar  # noqa: B018 -- the lookup itself raises
    found = re.search(r"see (moving-to-[\d.]+)#([\w-]+)", str(raised.value))
    assert found, raised.value
    page, anchor = found.groups()
    assert anchor in anchors(f"{page}.md")
    assert "the-detail-calls" in anchors("moving-to-0.19.md")
    assert "the-detail-calls" not in anchors("moving-to-0.15.md")
