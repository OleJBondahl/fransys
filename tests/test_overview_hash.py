"""The overview page's URL hash holds the switch states (O23).

The browser behaviour is checked by internal/scripts/overview_smoke.py; this guards the script.
"""

from fransys_overview._app import APP_JS


def test_the_hash_writes_and_reads_the_switches_and_k() -> None:
    """Breaks if encode drops the feature switches or k, or decode stops restoring them."""
    assert "p.set('f'" in APP_JS
    assert "p.set('k'" in APP_JS
    assert "state.feat[id] = on.has(id)" in APP_JS
    assert "p.get('k')" in APP_JS


def test_changes_only_is_a_choice_inside_the_changes_switch_not_a_switch() -> None:
    """Breaks if Changes only returns to the switch list or leaves the changes hash token."""
    assert "['changesonly'" not in APP_JS
    assert "id === 'changes'" in APP_JS
    assert "'changes.only'" in APP_JS
    assert "state.feat.changesonly = on.has('changes.only')" in APP_JS
