"""Every link marker stores a facing, and it is the side its port leaves its symbol (layout-0205).

The PDF links read the box from the stored facing (NV2); render drew it from the port's geometry
until now. Checked on six single-wire pairs cut by a page break. A line's stub has no port.
"""

import importlib.util
from pathlib import Path

import pytest
from fransys_render._markers import box_origin, geometry_facing

from fransys_model.derive import draws_as_line, page_destination
from fransys_model.derive.page_nav import reference_links
from fransys_model.layout import LinkMarker, Page, layout_of


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name[:-3], Path(__file__).with_name(name))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _pairs():
    return _load("test_dd_cut_end.py")._build(pairs=6, pins=1, boundary=None).model


def _star():
    wires = (("K1.A1", "K2.A2"), ("K1.A1", "K3.A2"), ("K1.A1", "K4.A2"))
    return _load("test_dd_gap_rules.py")._star(*wires)


@pytest.mark.parametrize("build", [_pairs, _star], ids=["plain pairs", "star reference"])
def test_every_marker_at_a_port_stores_the_facing_its_port_leaves_by(build) -> None:
    model = build()
    markers = list(layout_of(model, LinkMarker).values())
    assert len(markers) >= 4
    for marker in markers:
        if marker.carrier is not None and draws_as_line(model, marker.carrier):
            continue
        assert marker.facing is not None
        assert marker.facing.name == geometry_facing(model, marker).name, (marker.id, marker.star)


def test_a_marker_links_the_box_render_draws_to_its_partners_page() -> None:
    """The link box is the box drawn from the port's geometry, aimed at the partner's sheet."""
    model = _pairs()
    pages = layout_of(model, Page)
    markers = layout_of(model, LinkMarker)
    found = 0
    for page in pages.values():
        links = {
            (link.x, link.y, link.width, link.height): link.target
            for link in reference_links(model, page.id, set(pages))
        }
        for marker in markers.values():
            if marker.page != page.id or markers[marker.partner].page == page.id:
                continue
            x, y = box_origin(marker, geometry_facing(model, marker))
            target = page_destination(model, pages[markers[marker.partner].page])
            assert links[x, y, marker.width, marker.height] == target
            found += 1
    assert found >= 4
