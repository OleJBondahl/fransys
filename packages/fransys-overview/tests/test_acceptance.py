import pytest
from fransys_overview import html

pytestmark = pytest.mark.wp("overview")


def test_html_is_self_contained(demo_cabinet):
    page = html(demo_cabinet)
    assert '<script src="http' not in page
    assert "<link" not in page or 'rel="stylesheet" href="http' not in page


def test_every_item_is_a_node(demo_cabinet):
    page = html(demo_cabinet)
    for item in demo_cabinet.tables["item"].values():
        assert item.id.value in page
