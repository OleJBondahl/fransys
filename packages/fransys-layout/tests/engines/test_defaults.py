"""The schematic engine's shipped defaults (docs/design/stages.md 6.1, docs/design/engine.md 7)."""

from fransys_layout.engines.schematic.defaults import DEFAULT_RULES
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.engines.schematic.read.house import DEFAULT_PROFILE, DEFAULT_SHEET
from fransys_layout.geometry import symbol_geometry
from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.layout import Profile as ModelProfile
from fransys_model.layout import SheetFormat as ModelSheetFormat
from fransys_model.layout import default_profile, default_sheet_format

_ORIGIN = Origin(file="tests/engines/test_defaults.py", line=1, note="defaults.py unit tests")


def test_the_default_sheet_is_the_model_house_sheet_in_grid_units() -> None:
    """One copy of the numbers (model-0029, model-0033, model-0051, spec page-frame R11.1):
    content box 410 x 267 mm at module 2.5 mm is floor(410*8/2.5) x floor(267*8/2.5) =
    1312 x 854.
    """
    house = default_sheet_format()
    assert (DEFAULT_SHEET.content_width, DEFAULT_SHEET.content_height) == (1312, 854)
    assert (DEFAULT_SHEET.frame_columns, DEFAULT_SHEET.frame_rows) == (
        house.frame_columns,
        house.frame_rows,
    )
    assert DEFAULT_SHEET.name == house.name


def test_default_rules_are_unique_by_kind_and_category() -> None:
    """`resolve` assumes it: a duplicate row would make the result depend on tuple order."""
    keys = [(rule.kind, rule.category, rule.gender) for rule in DEFAULT_RULES]
    assert len(set(keys)) == len(keys)


def test_every_default_rule_names_a_symbol_in_the_library() -> None:
    """A wrong key would raise `UnknownSymbolError` for every function of that kind."""
    for rule in DEFAULT_RULES:
        assert symbol_geometry(rule.symbol).key == rule.symbol


def test_default_rules_map_the_kinds_design_names() -> None:
    """docs/design/stages.md 6.1's six kinds, plus D6's `plc-channel` and D8's connector contacts.

    D6: a wired PLC channel is drawn with `plc-channel`. D8 and the mated-pair spec: a connector
    pin view is drawn with `contact`, or `contact-female` / `contact-male` by the connector
    facet's gender. `switch` -> `make-contact` is the prototype's stand-in (R7 B1); no D rule
    names it.
    """
    assert {(rule.kind, rule.category, rule.gender): rule.symbol for rule in DEFAULT_RULES} == {
        ("coil", None, None): "operating-device",
        ("connector", None, None): "contact",
        ("connector", None, "female"): "contact-female",
        ("connector", None, "male"): "contact-male",
        ("contact_co", None, None): "change-over-contact",
        ("contact_nc", None, None): "break-contact",
        ("contact_no", None, None): "make-contact",
        ("plc_channel", None, None): "plc-channel",
        ("protection", None, None): "circuit-breaker",
        ("switch", None, None): "make-contact",
        ("terminal", None, None): "terminal",
    }


def test_default_profile_is_the_model_house_profile() -> None:
    """One copy of the numbers (decision model-0036): `DEFAULT_PROFILE` is `default_profile()`."""
    house = default_profile()
    assert len(house.band_ranks) == 13
    assert DEFAULT_PROFILE.column_gap == house.column_gap
    assert DEFAULT_PROFILE.row_gap == house.row_gap
    assert DEFAULT_PROFILE.route_margin == house.route_margin
    assert DEFAULT_PROFILE.text_height == house.text_height
    assert DEFAULT_PROFILE.marker_padding == house.marker_padding
    assert DEFAULT_PROFILE.route_turn_penalty == house.route_turn_penalty
    assert DEFAULT_PROFILE.route_crossing_penalty == house.route_crossing_penalty
    assert DEFAULT_PROFILE.band_ranks == house.band_ranks
    assert DEFAULT_PROFILE.group_ranks == house.group_ranks


def test_default_profile_converges_with_an_authored_profile_of_the_same_values() -> None:
    """`DEFAULT_PROFILE` is the SAME conversion an authored profile gets, not a second copy.

    A model that authors `layout.sheet_format` and `layout.profile` with every field
    equal to the house defaults, read through `read_inputs`, must produce exactly
    `DEFAULT_PROFILE`: both the "no profile authored" and "profile authored" branches of
    `profile_and_sheet` go through `to_stage_profile` (decision model-0036).
    """
    house = default_profile()
    house_sheet = default_sheet_format()
    sheet_key = ("test", "profile-convergence-sheet")
    sheet = ModelSheetFormat(
        id=make_id(ModelSheetFormat, sheet_key),
        key=sheet_key,
        name=house_sheet.name,
        width_mm=house_sheet.width_mm,
        height_mm=house_sheet.height_mm,
        content_x_mm=house_sheet.content_x_mm,
        content_y_mm=house_sheet.content_y_mm,
        content_width_mm=house_sheet.content_width_mm,
        content_height_mm=house_sheet.content_height_mm,
        frame_columns=house_sheet.frame_columns,
        frame_rows=house_sheet.frame_rows,
        module_mm=house_sheet.module_mm,
    )
    profile_key = ("test", "profile-convergence-profile")
    profile = ModelProfile(
        id=make_id(ModelProfile, profile_key),
        key=profile_key,
        sheet_format=sheet.id,
        column_gap=house.column_gap,
        row_gap=house.row_gap,
        route_margin=house.route_margin,
        text_height=house.text_height,
        marker_padding=house.marker_padding,
        route_turn_penalty=house.route_turn_penalty,
        route_crossing_penalty=house.route_crossing_penalty,
        band_ranks=house.band_ranks,
        group_ranks=house.group_ranks,
    )
    draft = Draft()
    draft.extend((sheet, profile), origin=_ORIGIN)
    model = freeze(draft)

    inputs = read_inputs(model)

    assert inputs.profile == DEFAULT_PROFILE


def test_a_profile_of_only_its_identity_reads_as_the_house_profile_and_sheet() -> None:
    """Every field at its default and no `sheet_format` (`None`): the house profile on the
    house sheet, which is no record, so the page carries no sheet id (decision model-0060).
    """
    key = ("test", "profile-identity-only")
    draft = Draft()
    draft.extend((ModelProfile(id=make_id(ModelProfile, key), key=key),), origin=_ORIGIN)

    inputs = read_inputs(freeze(draft))

    assert inputs.profile == DEFAULT_PROFILE
    assert inputs.sheet == DEFAULT_SHEET
    assert inputs.sheet_format is None
