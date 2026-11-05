"""SWITCH-SYMBOLS: an overload relay draws one thermal-overload box per pole; only 95-96 opens."""

import fransys as fr
from fransys_el import symbol_kit

from electrical_symbols import LIBRARY
from fransys_model.derive import internal_links, port_templates
from fransys_model.elecdef import LinkKind
from fransys_model.vocab import functions


def test_the_overload_main_path_draws_one_thermal_overload_box_for_three_poles() -> None:
    d = fr.design("demo_parts")
    f = d.device("F13", "DEMO-OVERLOAD-3P")
    pick = symbol_kit(fr.build(d).model, LIBRARY)[f.main.id]
    assert (pick.key, pick.poles) == ("thermal-overload", 3)


def test_only_the_overload_auxiliary_contact_opens() -> None:
    d = fr.design("demo_parts")
    f = d.device("F13", "DEMO-OVERLOAD-3P")
    model = fr.build(d).model
    kit = symbol_kit(model, LIBRARY)
    assert kit[f.aux.id].key == "break-contact"
    assert kit[f.main.id].key not in {"circuit-breaker", "make-contact", "break-contact"}
    own = {t.id: t.function for t in port_templates(model).values()}
    links: dict[object, list[tuple[LinkKind, bool | None]]] = {}
    for link in internal_links(model).values():
        links.setdefault(own[link.a], []).append((link.kind, link.closed_at_rest))
    main_fn = functions(model)[f.main.id].template
    aux_fn = functions(model)[f.aux.id].template
    assert {kind for kind, _ in links[main_fn]} == {LinkKind.CONDUCTIVE}
    assert links[aux_fn] == [(LinkKind.SWITCHED, True)]
