"""Cross-package acceptance: a relay from the demo part library, drawn via `template` choices.

`fransys_parts` (spec P2) writes one `layout.symbol_choice` per function that names a
`symbol`, selecting by `template`. This is the layout-side half of that acceptance item: a
relay instantiated from `examples/demo-parts`' `relay-2co-24vdc.toml` is drawn with its coil
and contact symbols chosen through those `template` records, not by falling back to
`DEFAULT_RULES` by coincidence. `test_boundaries.py` only walks `src/`, so a test here may
import `fransys_parts` (WP `parts` build order step 5).
"""

import fransys_parts
from workspace_root import WORKSPACE_ROOT

from fransys_layout.engines.schematic.defaults import DEFAULT_RULES
from fransys_layout.engines.schematic.read import reading
from fransys_layout.geometry import SymbolPortError
from fransys_layout.stages import resolve
from fransys_model.derive.indexes import build_indexes
from fransys_model.kernel import Draft, Origin, freeze, merge
from fransys_model.vocab import (
    PartBundle,
    function_templates,
    instantiate,
    internal_links,
    parts,
    port_templates,
)
from fransys_model.vocab.tables import ports as model_ports

DEMO = WORKSPACE_ROOT / "examples" / "demo-parts" / "demo_parts"
_ORIGIN = Origin(file="tests/engines/test_parts_acceptance.py", line=1, note="stamp a relay")


def _relay_model():
    """One `K1` relay, instantiated from the demo library's `DEMO-RLY-2CO-24` part."""
    library_model = freeze(fransys_parts.load_path(DEMO))
    part = next(p for p in parts(library_model).values() if p.mpn == "DEMO-RLY-2CO-24")
    templates = tuple(t for t in function_templates(library_model).values() if t.part == part.id)
    template_ids = {t.id for t in templates}
    ports = tuple(p for p in port_templates(library_model).values() if p.function in template_ids)
    port_ids = {p.id for p in ports}
    links = tuple(link for link in internal_links(library_model).values() if link.a in port_ids)
    bundle = PartBundle(
        part=part, function_templates=templates, port_templates=ports, internal_links=links
    )

    draft = Draft()
    draft.extend(instantiate(bundle, ("k1",), tag="K1"), origin=_ORIGIN)
    return freeze(merge(library_model, draft)), part.id


def _drawn_by_kind(model):
    indexes = build_indexes(model)
    functions = reading.drawn_functions(model, indexes)
    choices = reading.symbol_choices(model)
    drawn, findings = resolve(functions, rules=DEFAULT_RULES, choices=choices)
    return {d.kind: d for d in drawn}, findings


def test_relay_coil_and_contacts_are_drawn_through_the_template_choice():
    model, _part_id = _relay_model()
    by_kind, findings = _drawn_by_kind(model)
    assert findings == ()
    assert by_kind["coil"].geometry.key == "operating-device"
    assert by_kind["contact_co"].geometry.key == "change-over-contact"
    coil_ports = {p.symbol_port for p in by_kind["coil"].ports}
    assert coil_ports == {"in", "out"}


def test_the_demo_relay_changeovers_bind_by_their_roles_as_their_symbol_port_did():
    """CS3 step 4: the part files dropped `symbol_port`; 11/12/14 and 21/22/24 still draw at
    `com`/`nc`/`no`, the binding the removed `symbol_port` entries gave."""
    model, _part_id = _relay_model()
    functions = reading.drawn_functions(model, build_indexes(model))
    drawn, findings = resolve(functions, rules=DEFAULT_RULES, choices=reading.symbol_choices(model))
    assert findings == ()
    bound = {
        model_ports(model)[p.port].name: p.symbol_port
        for d in drawn
        if d.kind == "contact_co"
        for p in d.ports
    }
    assert bound == {
        "11": "com",
        "12": "nc",
        "14": "no",
        "21": "com",
        "22": "nc",
        "24": "no",
    }


def test_without_the_template_choice_the_relay_cannot_bind_its_ports():
    """Can-fail proof: the demo relay's coil pins (`A1`/`A2`) only bind to their symbol
    through the choice's `port_map` (P2); `DEFAULT_RULES` carries none for `coil`, and the coil
    has no internal link to fall back to a pole pair, so dropping the choices breaks binding
    for it. (The changeovers bind by their throw roles, choice or none.)
    """
    model, _part_id = _relay_model()
    indexes = build_indexes(model)
    functions = reading.drawn_functions(model, indexes)
    try:
        resolve(functions, rules=DEFAULT_RULES, choices=())
    except SymbolPortError:
        pass
    else:
        msg = "expected SymbolPortError with no authored symbol choices"
        raise AssertionError(msg)
