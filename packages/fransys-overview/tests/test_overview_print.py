"""O20: print hides the panels, the PNG button has its function, only the theme is stored."""

import re

from fransys_overview._app import APP_JS
from fransys_overview._template import TEMPLATE


def test_print_hides_the_features_panel_and_the_side_panels():
    rule = re.search(r"@media print \{(.*?)\n\}", TEMPLATE, re.DOTALL)
    assert rule is not None
    hidden = rule.group(1)
    assert "display: none" in hidden
    assert all(name in hidden for name in ("#features", "#tree", "#detail"))


def test_the_png_button_has_the_function_behind_it():
    assert 'id="png"' in TEMPLATE
    assert "window.overviewPng = pngUrl;" in APP_JS


def test_only_the_theme_choice_is_stored_in_local_storage():
    keys = set(re.findall(r"localStorage\.\w+\('([^']+)'", APP_JS))
    assert keys == {"overview-theme"}
