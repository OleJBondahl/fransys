"""SETTINGS-OPEN SO1: every key of `[pdf]`, `[look]` and `[layout]` is overridable, key by key."""

import tomllib
from importlib import resources
lazy from collections.abc import Mapping
lazy from pathlib import Path

import fransys as fr
import pytest
from fransys_el import house_conventions

from electrical_symbols import LIBRARY

pytestmark = pytest.mark.wp("facade")

TABLES = ("pdf", "look", "layout")


def _file(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "fransys.toml"
    path.write_text(text, encoding="utf-8")
    return path


def _ours() -> dict[str, dict[str, object]]:
    s = fr.settings()
    return {"pdf": dict(s.pdf), "look": dict(s.look), "layout": dict(s.layout)}


def _toml_text(table: str, key: str, value: object) -> str:
    """A one-key TOML file whose value is ours, written as JSON (a valid TOML literal here)."""
    import json

    return f"[{table}]\n{key} = {json.dumps(value)}\n"


def _as_lists(value: object) -> object:
    if isinstance(value, tuple | list):
        return [_as_lists(v) for v in value]
    return value


def _toml_like(table: Mapping[str, object]) -> dict[str, object]:
    return {k: _as_lists(v) for k, v in dict(table).items()}


SWEEP = [(t, k) for t, keys in _ours().items() for k in keys]


@pytest.mark.parametrize(
    ("text", "table", "key", "value"),
    [
        ("[layout]\nrow_gap = 32\n", "layout", "row_gap", 32),
        ("[pdf]\nlist_share_pct = 30\n", "pdf", "list_share_pct", 30),
        ('[look]\nref_tints = ["#000000"]\n', "look", "ref_tints", ("#000000",)),
    ],
)
def test_one_consumer_key_per_table_changes_only_that_value(
    tmp_path: Path, text: str, table: str, key: str, value: object
) -> None:
    s = fr.settings(_file(tmp_path, text))
    ours = _ours()
    got = {"pdf": dict(s.pdf), "look": dict(s.look), "layout": dict(s.layout)}
    assert got[table] == {**ours[table], key: value}
    assert {t: got[t] for t in TABLES if t != table} == {t: ours[t] for t in TABLES if t != table}


@pytest.mark.parametrize(("table", "key"), SWEEP)
def test_a_file_that_sets_our_own_value_round_trips(tmp_path: Path, table: str, key: str) -> None:
    value = _as_lists(_ours()[table][key])
    s = fr.settings(_file(tmp_path, _toml_text(table, key, value)))
    assert _ours() == {
        "pdf": dict(s.pdf),
        "look": dict(s.look),
        "layout": dict(s.layout),
    }


@pytest.mark.parametrize("table", TABLES)
def test_an_unknown_key_raises_and_names_that_tables_keys(tmp_path: Path, table: str) -> None:
    keys = ", ".join(_ours()[table])
    with pytest.raises(fr.SettingsError, match="known: " + keys.replace(",", r"\,")):
        fr.settings(_file(tmp_path, f"[{table}]\nfrobnicate = 1\n"))


@pytest.mark.parametrize(
    ("text", "word"),
    [
        ("[layout]\ncontact_tables = 1\n", "true or false"),
        ("[layout]\nrow_gap = 1.5\n", "a whole number"),
        ('[layout]\ncorner_order = "TL"\n', "a list"),
        ('[layout]\nslack = ["a"]\n', "a list"),
        ('[layout]\nrow_gap = "x"\n', "a whole number"),
        ("[pdf]\nlist_share_pct = true\n", "a whole number"),
        ("[look]\nref_tints = [1]\n", "a list"),
    ],
)
def test_a_value_of_another_type_raises(tmp_path: Path, text: str, word: str) -> None:
    with pytest.raises(fr.SettingsError, match=f"must be {word}"):
        fr.settings(_file(tmp_path, text))


def test_an_int_is_accepted_where_ours_is_a_float(tmp_path: Path) -> None:
    assert fr.settings(_file(tmp_path, "[layout]\nw_tag = 2\n")).layout["w_tag"] == 2


def test_a_list_may_differ_in_length(tmp_path: Path) -> None:
    s = fr.settings(_file(tmp_path, "[layout]\nslack = [0, 4]\n"))
    assert s.layout["slack"] == (0, 4)


def test_frobnicate_in_layout_names_the_known_layout_keys(tmp_path: Path) -> None:
    with pytest.raises(fr.SettingsError, match=r'\[layout\] "frobnicate" is not a setting') as e:
        fr.settings(_file(tmp_path, "[layout]\nfrobnicate = 1\n"))
    assert "row_gap" in str(e.value)


def test_a_consumer_layout_key_reaches_the_core_options(tmp_path: Path) -> None:
    layout = dict(fr.settings(_file(tmp_path, "[layout]\nrow_gap = 32\n")).layout)
    assert house_conventions(layout, LIBRARY).options.row_gap == 32


def test_defaults_equal_the_packaged_toml_files() -> None:
    def load(package: str, name: str) -> dict[str, dict[str, object]]:
        text = (resources.files(package) / name).read_text(encoding="utf-8")
        return tomllib.loads(text)

    s = fr.settings()
    assert _toml_like(s.layout) == load("fransys_layout", "layout.toml")["layout"]
    ours = load("fransys", "settings.toml")
    assert _toml_like(s.look) == ours["look"]
    assert _toml_like(s.pdf) == ours["pdf"]


def test_an_open_table_accepts_a_new_key_and_every_other_refuses_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """OPEN_TABLES names the data-keyed tables (SETTINGS-OPEN); a new key must fit (A2)."""
    from fransys import _settings_merge

    path = _file(tmp_path, "[layout]\nfrobnicate = [1, 2]\n")
    with pytest.raises(fr.SettingsError, match="is not a setting"):
        fr.settings(path)
    monkeypatch.setattr(_settings_merge, "OPEN_TABLES", ("layout",))
    assert fr.settings(path).layout["frobnicate"] == (1, 2)
