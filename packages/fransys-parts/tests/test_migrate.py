"""`fransys_parts.migrate.migrate_part_text` (MIGRATE-022-DROP): schema 1 part files and `library.toml` as schema 2 (decision model-0369)."""

from decimal import Decimal

import fransys_parts
import pytest
from fransys_parts._errors import PartTextError
from fransys_parts.migrate import migrate_part_text

from fransys_model.elecdef import Fuse, Quantity, Unit
from fransys_model.kernel import Severity, freeze
from fransys_model.vocab import BlockFacet, OperatingFacet, RatingFacet, facets_of

_OLD = """schema = 1

[part]
mpn = "X-1"
manufacturer = "Demo"
description = "d"
category = "generic"
class_code = "X"

[rating]
voltage_ac_v = "500"

[[function]]
name = "f1"
kind = "protection"
ports = [{ name = "1", role = "generic" }]

[function.rating]
voltage_dc_v = "1000"
current_dc_a = "400"
power_loss_w = "12"
breaking_dc = [{ voltage_v = "1000", current_a = "15000", time_constant_ms = "15" }]
min_breaking_current_a = "4000"

[function.protection]
type = "fuse"

[function.operating]
nominal_voltage_v = "24"
voltage_dc_v = "24"
min_voltage_v = "18"
max_current_ac_a = "5"
max_current_dc_a = "6"
capacity_ah = "7.2"
"""
_INLINE = _OLD.split("[function.rating]", maxsplit=1)[0].replace(
    'ports = [{ name = "1", role = "generic" }]', 'ports = [{ name = "1", role = "generic" }]\nrating = { voltage_dc_v = "3" }'
)
_BLOCK = '[function.block]\ntype = "fuse"\nbreaking_capacity = [{ min = "4000 A" }, { max = "15000 A", at = ["DC", "1000 V", "15 ms"] }]\n'


def test_a_schema_1_file_becomes_schema_2_tables():
    new = migrate_part_text(_OLD)
    assert new.startswith("schema = 2\n")
    assert 'voltage = [{ nom = "500 V", at = ["AC"] }]' in new
    assert 'power_loss = { nom = "12 W" }' in new
    assert 'voltage = [{ nom = "24 V", min = "18 V", at = ["DC"] }]\n' in new
    assert 'max_current = [{ max = "5 A", at = ["AC"] }, { max = "6 A", at = ["DC"] }]\ncapacity = "7.2 Ah"\n' in new
    assert _BLOCK in new


def test_the_migrated_file_loads_with_the_same_figures(tmp_path):
    root = tmp_path / "lib"
    (root / "parts").mkdir(parents=True)
    (root / "library.toml").write_text('schema = 2\nname = "l"\nversion = "0.1.0"\ndescription = "d"\n')
    (root / "parts" / "p.toml").write_text(migrate_part_text(_OLD))
    assert not [f for f in fransys_parts.lint(root) if f.severity is Severity.ERROR]
    model = freeze(fransys_parts.load_path(root))
    (facet,) = facets_of(model, RatingFacet).values()
    assert facet.rating.power_loss is not None
    assert (facet.rating.voltage[0].nom, facet.rating.power_loss.nom) == (Quantity(Decimal(1000), Unit.V), Quantity(Decimal(12), Unit.W))
    (block,) = facets_of(model, BlockFacet).values()
    assert isinstance(block.block, Fuse)
    assert [r.min or r.max for r in block.block.breaking_capacity] == [Quantity(Decimal(4000), Unit.A), Quantity(Decimal(15000), Unit.A)]
    (operating,) = facets_of(model, OperatingFacet).values()
    assert operating.operating.capacity == Quantity(Decimal("7.2"), Unit.AH)


def test_migrating_twice_changes_nothing():
    once = migrate_part_text(_OLD)
    assert migrate_part_text(once) == once


def test_part_level_breaking_points_become_a_fuse_block():
    old = _OLD.replace(
        'voltage_ac_v = "500"', 'voltage_ac_v = "500"\nmin_breaking_current_a = "4000"\nbreaking_ac = [{ voltage_v = "400", current_a = "10000" }]'
    )
    new = migrate_part_text(old)
    assert '[block]\ntype = "fuse"\n' in new
    assert 'breaking_capacity = [{ min = "4000 A" }, { max = "10000 A", at = ["AC", "400 V"] }]\n' in new


_MCB = _OLD.replace('type = "fuse"', 'type = "mcb"')


def test_an_mcb_with_one_point_states_it_as_icu():
    new = migrate_part_text(
        _MCB.replace(
            'breaking_dc = [{ voltage_v = "1000", current_a = "15000", time_constant_ms = "15" }]\nmin_breaking_current_a = "4000"\n',
            'breaking_ac = [{ voltage_v = "400", current_a = "10000" }]\n',
        )
    )
    assert '[function.block]\ntype = "mcb"\nicu = { max = "10000 A", at = ["AC", "400 V"] }\n' in new


def test_a_voltage_window_and_both_currents_become_one_window_and_one_figure_each():
    old = _OLD.replace('voltage_dc_v = "24"\nmin_voltage_v = "18"', 'voltage_dc_v = "24"\nvoltage_ac_v = "230"\nmin_voltage_v = "18"')
    assert 'voltage = [{ nom = "24 V", min = "18 V" }, { nom = "230 V", at = ["AC"] }, { nom = "24 V", at = ["DC"] }]\n' in migrate_part_text(old)


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        (_OLD.replace('voltage_dc_v = "1000"', 'voltage_dc_v = "1000"  # volts'), "comment"),
        (_INLINE, "left"),
        ("schema = 1\n[part\n", "not valid TOML"),
        (_MCB, "cannot convert"),
        (_OLD.replace('type = "fuse"', "kind_note = 1").replace("[function.protection]", "[function.note]"), "need a"),
    ],
)
def test_a_file_it_cannot_convert_is_refused(text, reason):
    with pytest.raises(PartTextError, match=reason):
        migrate_part_text(text)


def test_the_refusal_names_the_part_and_the_fix():
    with pytest.raises(PartTextError) as refused:
        migrate_part_text(_MCB)
    assert "part X-1:" in str(refused.value)
    assert "split the breaker's breaking points into one per kind" in str(refused.value)


def test_a_library_toml_only_changes_its_schema_line():
    old = 'schema = 1\nname = "l"\nversion = "0.1.0"\ndescription = "d"\n'
    assert migrate_part_text(old) == old.replace("schema = 1", "schema = 2")
