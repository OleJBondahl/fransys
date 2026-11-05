"""Field case: a core numbered past its cable product's cores is a finding, not a crash.
The bug: `core_colour` raised `SchemaError` for the index outside the product, so every list built on it crashed.
Fixed by model-0266 (G1): the validator gives ERROR `CORE_INDEX_PAST_PRODUCT`; `core_colour` returns an empty string past the product."""

import dataclasses

import fransys as fr
from fransys.colours import BK, BN

from fransys_model.checks import ALL_VALIDATORS
from fransys_model.derive import cable_items, cable_rows, core_colour, open_core_rows
from fransys_model.kernel import Origin, evolve
from fransys_model.vocab import facets_of
from fransys_model.vocab.facets.cable import CoreFacet

_CODE = "CORE_INDEX_PAST_PRODUCT"


def _loaded() -> fr.BuildResult:
    d = fr.design("demo_parts")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 8)
    h1 = d.device("H1", "DEMO-LAMP-24")
    w1 = d.cable("W1", "DEMO-CBL-4G1.5", length_m=5)
    w1.core(BN, x1[1], h1[1])
    w1.core(BK, x1[2], h1[2])
    result = fr.build(d)
    facet = max(facets_of(result.model, CoreFacet).values(), key=lambda f: f.index)
    origin = Origin(file="<field case>", line=1, note="core 5")
    model = evolve(result.model, remove=[facet.id], put=[dataclasses.replace(facet, index=5)], origin=origin)
    return dataclasses.replace(result, model=model)


def test_a_core_past_its_product_gives_the_error_and_no_list_raises() -> None:
    result = _loaded()
    found = [f for v in ALL_VALIDATORS for f in v(result.model) if f.code == _CODE]
    assert len(found) == 1
    assert found[0].severity is fr.Severity.ERROR
    assert "5" in found[0].message
    assert "use a core from 1 to 4 or a part with more cores" in found[0].message
    model = result.model
    (cable,) = cable_items(model)
    cable_rows(model, cable)
    open_core_rows(model, cable)
    colours = [core_colour(model, f.subject) for f in facets_of(model, CoreFacet).values()]
    assert "" in colours
