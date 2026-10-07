from pathlib import Path

import fransys_parts
import pytest

DEMO = (
    next(p for p in Path(__file__).resolve().parents if (p / "examples").is_dir())
    / "examples"
    / "demo-parts"
    / "demo_parts"
)

pytestmark = pytest.mark.wp("parts")


def test_demo_library_loads_and_freezes():
    from fransys_model.kernel import freeze

    model = freeze(fransys_parts.load_path(DEMO))
    assert set(model.tables["part"])
    assert set(model.tables["function_template"])


def test_overload_relays_take_class_code_b():
    """Owner 2026-09-23: an overload relay is B (IEC 81346-2:2019), the 3-pole one too."""
    from fransys_model.kernel import freeze
    from fransys_model.vocab import parts

    model = freeze(fransys_parts.load_path(DEMO))
    codes = {p.mpn: p.class_code for p in parts(model).values() if "OVERLOAD" in p.mpn}
    assert codes == {"DEMO-OVERLOAD-A2": "B", "DEMO-OVERLOAD-3P": "B"}


def test_demo_switch_takes_class_code_b():
    """DEMO-SWITCH-2P is a position switch: class B, not K (decision parts-0014)."""
    from fransys_model.kernel import freeze
    from fransys_model.vocab import parts

    model = freeze(fransys_parts.load_path(DEMO))
    codes = {p.mpn: p.class_code for p in parts(model).values() if p.mpn == "DEMO-SWITCH-2P"}
    assert codes == {"DEMO-SWITCH-2P": "B"}


def test_demo_library_is_lint_clean():
    assert fransys_parts.lint(DEMO) == ()


def test_origin_names_the_part_file():
    from fransys_model.kernel import freeze

    model = freeze(fransys_parts.load_path(DEMO))
    assert any(o.file.endswith("relay-2co-24vdc.toml") for o in model.origins.values())


def test_a_float_in_a_part_file_is_a_finding(tmp_path):
    (tmp_path / "library.toml").write_text('schema = 1\nname = "bad"\nversion = "0.0.0"\n')
    (tmp_path / "parts").mkdir()
    (tmp_path / "parts" / "x.toml").write_text("schema = 1\n[part]\nmpn = 1.5\n")
    assert fransys_parts.lint(tmp_path) != ()


def test_part_library_error_holds_every_finding_warnings_included(tmp_path):
    """spec P5 (corrected): `findings` is the whole `lint()` report, not only the `ERROR`s."""
    from fransys_model.kernel import Severity

    (tmp_path / "library.toml").write_text('schema = 1\nname = "bad"\nversion = "0.0.0"\n')
    (tmp_path / "parts").mkdir()
    # BOARD_WITHOUT_PCB is a WARNING; class_code "Xx" is an ERROR (CLASS_CODE).
    (tmp_path / "parts" / "Bad Name.toml").write_text(
        "schema = 1\n\n"
        "[part]\n"
        'mpn = "X-1"\n'
        'manufacturer = "Demo"\n'
        'description = "d"\n'
        'category = "board"\n'
        'class_code = "Xx"\n'
    )
    with pytest.raises(fransys_parts.PartLibraryError) as excinfo:
        fransys_parts.load_path(tmp_path)
    severities = {f.severity for f in excinfo.value.findings}
    assert Severity.ERROR in severities
    assert Severity.WARNING in severities


def test_connector_facet_origin_is_its_own_header_line():
    """spec P6 (corrected): a `[function.connector]` facet's origin is its own header line."""
    from fransys_model.kernel import freeze

    text = (DEMO / "parts" / "connector-header-2p.toml").read_text()
    connector_header_line = next(
        i
        for i, line in enumerate(text.splitlines(), start=1)
        if line.strip() == "[function.connector]"
    )
    model = freeze(fransys_parts.load_path(DEMO))
    # NEW (unit-documents worked example, designer's own choice): the demo library also
    # carries `switch-2p.toml`'s own `[function.connector]` (DEMO-SWITCH-2P's `x1`) now, so
    # `facet.connector` has two entries, not one -- filtered to the one under test.
    facet = next(
        f
        for f in model.tables["facet.connector"].values()
        if model.origins[f.id].file.endswith("connector-header-2p.toml")
    )
    origin = model.origins[facet.id]
    assert origin.line == connector_header_line
    assert origin.file.endswith("connector-header-2p.toml")


def test_demo_library_record_counts_and_keys():
    """P3, P7: 16 demo parts (units WP added pcb-io, a part-less-container board part; the
    unit-documents worked example added `switch-2p.toml`'s field switch, 2 functions/4
    ports/1 internal link/2 symbol choices more, measured directly against this build; the
    connector-sub-part work added `io-2-connectors.toml`, 2 functions/4 ports/2 symbol choices
    more; `io-clamps-and-sockets.toml` (lint-print) adds a part with 4 functions/33 ports, no
    symbol choice, so 14 parts; the ratings work adds `terminal-dual-rated-2p.toml`, 1
    function/2 ports/1 internal link/1 symbol choice, and `cell-3v6.toml`, 1 function/2 ports;
    RATINGS-2 adds `fuse-abat.toml`, 1 function/2 ports/1 internal link/1 symbol choice, and
    `string-864v.toml`, 1 function/2 ports; the check adds `contactor-dc.toml`, 1 function/2
    ports/1 internal link/1 symbol choice, so 19 parts; CONTACT-STATES adds `changeover-4p.toml`,
    `mcb-2p.toml` and `psu-24v.toml`, 3 more parts, so 22; MARKER-CLEAR adds
    `overload-a2.toml`, 1 function/1 port/1 symbol choice, so 23; ACCESSORY-BLOCK adds
    `contact-block-addon.toml`, 2 functions/4 ports/2 internal links/2 symbol choices, so 24;
    ITEM-BOX adds `plc-di-4ch-pwr.toml` (5 functions/6 ports), `psu-24v-dcok.toml` (3/6) and
    `redundancy-2in.toml` (3/6), no link or symbol choice, so 27; I2b adds
    `contactor-3p-aux-nc.toml` (4 functions/12 ports/5 links/4 symbol choices), so 28;
    EA-PARTS-MODULE adds `mcb-3p.toml` (1 function/6 ports/3 links),
    `overload-3p.toml` (2/8/4/1 symbol choice) and `pb-nc.toml` (1/2/1/1), so 31;
    EA-SERIES-FIX adds `terminal-pe-2_5.toml` (1/2/1/1), so 32;
    the 16-channel DI module adds `plc-di-16ch.toml` (16 functions/16 ports), so 33;
    CONTAINER-GAPS adds `connector-header-4p.toml` and `connector-header-4p-mixed.toml`
    (1 function/4 ports/1 symbol choice each), so 35;
    HIDDEN-PINS adds `plc-ai-4ch.toml` (4 functions/8 ports, no link or symbol choice), so 36;
    DRAWN-ENDS gave the DC-OK contact of `psu-24v-dcok.toml` its switched link, so 41 links;
    BOX-CONTACT gave `redundancy-2in.toml` a DC-OK contact: 83 functions, 194 ports, 42 links;
    GROUP-FUNCTION-ID adds `redundancy-2in-net.toml` (4/8/1 symbol choice), so 37;
    the guide's current check adds `fuse-dc-160.toml` (1/2/1/1), so 38; FUSE-LINK adds
    `fuse-holder-pcb.toml` (1 function/2 ports/1 link/1 symbol choice), `switch-dc-2a.toml`
    (1/2/1/1) and two function-less fuse links (`fuse-link-4a-t.toml`, `fuse-link-500ma-t.toml`);
    RR-O6 adds `connector-header-2p-lettered.toml` (1/2/0/1),
    FEEDER-PORTS adds `psu-24v-5out.toml` (2 functions/7 ports),
    PIN-LABELS adds `ctrl-8.toml` (4 functions/16 ports),
    ACCESSORY-HOLDER adds `jumper-bar-3p.toml` (no function, no port),
    GND-NAME adds `psu-24v-pm.toml` (2 functions/4 ports),
    HA7 adds `housing-4f.toml` and `housing-4m.toml` (1 function/4 ports/1 symbol choice each),
    HA8 adds `crimp-contact-f.toml` and `crimp-contact-m.toml` (no function, no port),
    HA4 adds `relay-mod-2.toml` (5 functions/12 ports/4 symbol choices, 6 header joins),
    HA5 adds `contactor-leads.toml` (2 functions/4 ports/2 symbol choices, 1 link),
    so 53 parts, 108 templates, 261 ports, 46 links, 48 symbol choices)."""
    from fransys_model.kernel import freeze
    from fransys_model.vocab import function_templates, internal_links, parts, port_templates

    model = freeze(fransys_parts.load_path(DEMO))
    assert len(parts(model)) == 53
    assert len(function_templates(model)) == 108
    assert len(port_templates(model)) == 261
    assert len(internal_links(model)) == 46
    assert len(model.tables["layout.symbol_choice"]) == 48

    relay = next(p for p in parts(model).values() if p.mpn == "DEMO-RLY-2CO-24")
    assert relay.key == ("part", "Demo", "DEMO-RLY-2CO-24")
    coil = next(
        t for t in function_templates(model).values() if t.part == relay.id and t.name == "coil"
    )
    assert coil.key == (*relay.key, "function", "coil")
    a1 = next(p for p in port_templates(model).values() if p.function == coil.id and p.name == "A1")
    assert a1.key == (*coil.key, "port", "A1")


def test_two_loads_give_equal_drafts():
    """Loading the same library twice is deterministic: same records, same origins."""
    first = fransys_parts.load_path(DEMO)
    second = fransys_parts.load_path(DEMO)
    assert first.records() == second.records()
    assert first.origins() == second.origins()


def test_port_marking_loads_onto_the_port_template(tmp_path):
    """model-0053 (F2): `ports[].marking` loads onto `PortTemplate.marking`, one case each --
    an explicit marking, an explicit empty marking (no printed text) and no key at all."""
    from fransys_model.kernel import freeze
    from fransys_model.vocab import port_templates

    (tmp_path / "library.toml").write_text(
        'schema = 1\nname = "t"\nversion = "0.0.0"\ndescription = "d"\n'
    )
    (tmp_path / "parts").mkdir()
    (tmp_path / "parts" / "x.toml").write_text(
        "schema = 1\n\n"
        "[part]\n"
        'mpn = "X-1"\n'
        'manufacturer = "Demo"\n'
        'description = "d"\n'
        'category = "generic"\n'
        'class_code = "X"\n\n'
        "[[function]]\n"
        'name = "main"\n'
        'kind = "generic"\n'
        "ports = [\n"
        '    { name = "1", role = "generic", marking = "X9" },\n'
        '    { name = "2", role = "generic", marking = "" },\n'
        '    { name = "3", role = "generic" },\n'
        "]\n"
    )
    model = freeze(fransys_parts.load_path(tmp_path))
    markings = {p.name: p.marking for p in port_templates(model).values()}
    assert markings == {"1": "X9", "2": "", "3": None}


def test_port_marking_round_trips_from_the_part_file_to_an_instance(tmp_path):
    """model-0053 (F2): a marking loaded from TOML survives `instantiate` onto the `Port`,
    unchanged, for all three cases."""
    from fransys_model.kernel import freeze
    from fransys_model.vocab import (
        PartBundle,
        function_templates,
        instantiate,
        internal_links,
        parts,
        port_templates,
    )
    from fransys_model.vocab.core import Port

    (tmp_path / "library.toml").write_text(
        'schema = 1\nname = "t"\nversion = "0.0.0"\ndescription = "d"\n'
    )
    (tmp_path / "parts").mkdir()
    (tmp_path / "parts" / "x.toml").write_text(
        "schema = 1\n\n"
        "[part]\n"
        'mpn = "X-1"\n'
        'manufacturer = "Demo"\n'
        'description = "d"\n'
        'category = "generic"\n'
        'class_code = "X"\n\n'
        "[[function]]\n"
        'name = "main"\n'
        'kind = "generic"\n'
        "ports = [\n"
        '    { name = "1", role = "generic", marking = "X9" },\n'
        '    { name = "2", role = "generic", marking = "" },\n'
        '    { name = "3", role = "generic" },\n'
        "]\n"
    )
    model = freeze(fransys_parts.load_path(tmp_path))
    (part,) = parts(model).values()
    bundle = PartBundle(
        part=part,
        function_templates=tuple(function_templates(model).values()),
        port_templates=tuple(port_templates(model).values()),
        internal_links=tuple(internal_links(model).values()),
    )
    records = instantiate(bundle, ("t", "instance"))
    markings = {p.name: p.marking for p in records if isinstance(p, Port)}
    assert markings == {"1": "X9", "2": "", "3": None}


def test_connector_marking_loads_onto_the_connector_facet(tmp_path):
    """parts-0003: `[function.connector].marking` loads onto `ConnectorFacet.marking`, read like
    `Port.marking`: no key loads `None` (the function's name), `""` stays `""` (no label)."""
    from fransys_model.kernel import freeze
    from fransys_model.vocab import function_templates
    from fransys_model.vocab.facets.connector import ConnectorFacet
    from fransys_model.vocab.tables import facets_of

    (tmp_path / "library.toml").write_text(
        'schema = 1\nname = "t"\nversion = "0.0.0"\ndescription = "d"\n'
    )
    (tmp_path / "parts").mkdir()
    head = (
        "schema = 1\n\n"
        "[part]\n"
        'mpn = "X-1"\n'
        'manufacturer = "Demo"\n'
        'description = "d"\n'
        'category = "generic"\n'
        'class_code = "X"\n\n'
    )
    function = (
        "[[function]]\n"
        'name = "{name}"\n'
        'kind = "connector"\n'
        'ports = [{{ name = "{name}1", role = "generic" }}]\n\n'
        "[function.connector]\n"
        'style = "s"\n'
        "pincount = 1\n"
        'gender = "male"\n'
    )
    (tmp_path / "parts" / "x.toml").write_text(
        head
        + function.format(name="a")
        + 'marking = "X1"\n\n'
        + function.format(name="b")
        + "\n"
        + function.format(name="c")
        + 'marking = ""\n'
    )
    model = freeze(fransys_parts.load_path(tmp_path))
    by_subject = {f.subject: f.marking for f in facets_of(model, ConnectorFacet).values()}
    names = {t.id: t.name for t in function_templates(model).values()}
    assert {names[subject]: marking for subject, marking in by_subject.items()} == {
        "a": "X1",
        "b": None,
        "c": "",
    }


def test_moving_a_part_file_to_another_name_changes_no_id(tmp_path):
    """P7: authoring keys come from content, never from a file name or position."""
    relay_text = (DEMO / "parts" / "relay-2co-24vdc.toml").read_text()
    library_text = (DEMO / "library.toml").read_text()
    root_a, root_b = tmp_path / "a", tmp_path / "b"
    for root, file_name in ((root_a, "relay-2co-24vdc.toml"), (root_b, "renamed-relay.toml")):
        (root / "parts").mkdir(parents=True)
        (root / "library.toml").write_text(library_text)
        (root / "parts" / file_name).write_text(relay_text)
    ids_a = {r.id for r in fransys_parts.load_path(root_a).records()}
    ids_b = {r.id for r in fransys_parts.load_path(root_b).records()}
    assert ids_a == ids_b


def test_file_order_on_disk_does_not_matter(tmp_path):
    names = ["relay-2co-24vdc.toml", "terminal-feedthrough-2_5.toml", "cable-4g1_5.toml"]
    library_text = (DEMO / "library.toml").read_text()
    root_a, root_b = tmp_path / "a", tmp_path / "b"
    for root, order in ((root_a, names), (root_b, list(reversed(names)))):
        (root / "parts").mkdir(parents=True)
        (root / "library.toml").write_text(library_text)
        for name in order:
            (root / "parts" / name).write_text((DEMO / "parts" / name).read_text())
    first = fransys_parts.load_path(root_a)
    second = fransys_parts.load_path(root_b)
    assert first.records() == second.records()
    assert first.origins() == second.origins()


def test_load_reads_an_installed_data_package():
    """`load(package)` via `importlib.resources`, against the installed `demo_parts` package."""
    assert fransys_parts.load("demo_parts").records() == fransys_parts.load_path(DEMO).records()


def test_a_loaded_cable_product_carries_its_colours_and_no_core_count():
    """SC4: the part file's `core_count` is the author's checksum; the facet holds no count."""
    from fransys_model.vocab.facets.cable import CableProductFacet

    (facet,) = (
        r for r in fransys_parts.load_path(DEMO).records() if isinstance(r, CableProductFacet)
    )
    assert facet.core_colours == ("BN", "BK", "GY", "GNYE")
    assert not hasattr(facet, "core_count")


def test_internal_link_loads_the_same_record_whichever_end_is_written_first(tmp_path):
    """model-0096 (SC7): `InternalLink.__post_init__` orders its ends itself, so the loader
    no longer normalizes `a`/`b`; the stored record's ends are the same regardless of which
    port name a part file's `links` entry writes first as `a`."""
    from fransys_model.kernel import freeze
    from fransys_model.vocab import internal_links

    library_text = 'schema = 1\nname = "t"\nversion = "0.0.0"\ndescription = "d"\n'
    part_text = (
        "schema = 1\n\n"
        "[part]\n"
        'mpn = "X-1"\n'
        'manufacturer = "Demo"\n'
        'description = "d"\n'
        'category = "generic"\n'
        'class_code = "X"\n\n'
        "[[function]]\n"
        'name = "main"\n'
        'kind = "generic"\n'
        "ports = [\n"
        '    {{ name = "P1", role = "generic" }},\n'
        '    {{ name = "P2", role = "generic" }},\n'
        "]\n"
        'links = [{{ a = "{a}", b = "{b}", kind = "conductive" }}]\n'
    )
    root_a, root_b = tmp_path / "a", tmp_path / "b"
    for root, a, b in ((root_a, "P1", "P2"), (root_b, "P2", "P1")):
        (root / "parts").mkdir(parents=True)
        (root / "library.toml").write_text(library_text)
        (root / "parts" / "x.toml").write_text(part_text.format(a=a, b=b))
    model_a = freeze(fransys_parts.load_path(root_a))
    model_b = freeze(fransys_parts.load_path(root_b))
    (link_a,) = internal_links(model_a).values()
    (link_b,) = internal_links(model_b).values()
    assert link_a.a == link_b.a
    assert link_a.b == link_b.b


def _header_line(text: str, header: str) -> int:
    return next(i for i, line in enumerate(text.splitlines(), start=1) if line.strip() == header)


def test_supply_footprint_cable_product_and_pcb_facets_load_their_fields_and_origins(tmp_path):
    """mutmut triage rank 1: no other test in this package puts a `[footprint]` table in a
    part file, or reads back a `SupplyFacet.note`, a `FootprintFacet`'s fields, a
    `CableProductFacet`'s `gauge_mm2`/`shielded`, or a `PcbFacet.revision` -- so this loads
    every one of them at once, through `load_path` + `freeze`, and checks each facet's own
    header line is its origin (spec P6)."""
    from decimal import Decimal

    from fransys_model.kernel import Origin, freeze
    from fransys_model.vocab.facets.cable import CableProductFacet
    from fransys_model.vocab.facets.pcb import FootprintFacet, PcbFacet
    from fransys_model.vocab.facets.supply import SupplyFacet
    from fransys_model.vocab.tables import facets_of

    (tmp_path / "library.toml").write_text(
        'schema = 1\nname = "t"\nversion = "0.0.0"\ndescription = "d"\n'
    )
    (tmp_path / "parts").mkdir()
    part_text = (
        "schema = 1\n\n"
        "# comment padding so [part] is not line 1\n"
        "[part]\n"
        'mpn = "X-1"\n'
        'manufacturer = "Demo"\n'
        'description = "d"\n'
        'category = "cable"\n'
        'class_code = "W"\n\n'
        "[[function]]\n"
        'name = "f1"\n'
        'kind = "generic"\n'
        'ports = [{ name = "1", role = "generic" }]\n\n'
        "# comment padding\n"
        "[[supply]]\n"
        'supplier = "Acme"\n'
        'supplier_part_number = "ACME-1"\n'
        'note = "bulk"\n\n'
        "# comment padding\n"
        "[footprint]\n"
        'library = "MyLib"\n'
        'name = "MyFootprint"\n\n'
        "# comment padding\n"
        "[cable_product]\n"
        "core_count = 2\n"
        'core_colours = ["BN", "BK"]\n'
        'gauge_mm2 = "1.5"\n'
        "shielded = false\n\n"
        "# comment padding\n"
        "[pcb]\n"
        'revision = "A"\n'
    )
    (tmp_path / "parts" / "x.toml").write_text(part_text)

    assert fransys_parts.lint(tmp_path) == ()

    rel_path = "parts/x.toml"
    supply_line = _header_line(part_text, "[[supply]]")
    footprint_line = _header_line(part_text, "[footprint]")
    cable_product_line = _header_line(part_text, "[cable_product]")
    pcb_line = _header_line(part_text, "[pcb]")

    model = freeze(fransys_parts.load_path(tmp_path))

    (supply,) = facets_of(model, SupplyFacet).values()
    assert supply.supplier == "Acme"
    assert supply.supplier_part_number == "ACME-1"
    assert supply.note == "bulk"
    assert model.origins[supply.id] == Origin(file=rel_path, line=supply_line, note="")

    (footprint,) = facets_of(model, FootprintFacet).values()
    assert footprint.library == "MyLib"
    assert footprint.name == "MyFootprint"
    assert model.origins[footprint.id] == Origin(file=rel_path, line=footprint_line, note="")

    (cable_product,) = facets_of(model, CableProductFacet).values()
    assert cable_product.core_colours == ("BN", "BK")
    assert cable_product.gauge_mm2 == Decimal("1.5")
    assert cable_product.shielded is False
    assert model.origins[cable_product.id] == Origin(
        file=rel_path, line=cable_product_line, note=""
    )

    (pcb,) = facets_of(model, PcbFacet).values()
    assert pcb.revision == "A"
    assert model.origins[pcb.id] == Origin(file=rel_path, line=pcb_line, note="")


def test_footprint_missing_name_is_a_field_missing_finding_on_its_header_line(tmp_path):
    """mutmut triage rank 9: `[footprint]` is only checked by `_check_footprint` when a
    `[footprint]` table exists, which also never happens in the current suite, so its own
    `line = _line(origins, ("footprint",))` default and `table_name="footprint"` argument
    survive uncaught too. `FIELD_MISSING` names the missing field and the table's own header
    line, not line 1."""
    (tmp_path / "library.toml").write_text(
        'schema = 1\nname = "t"\nversion = "0.0.0"\ndescription = "d"\n'
    )
    (tmp_path / "parts").mkdir()
    part_text = (
        "schema = 1\n\n"
        "[part]\n"
        'mpn = "X-1"\n'
        'manufacturer = "Demo"\n'
        'description = "d"\n'
        'category = "generic"\n'
        'class_code = "X"\n\n'
        "# comment padding\n"
        "[footprint]\n"
        'library = "MyLib"\n'
    )
    (tmp_path / "parts" / "x.toml").write_text(part_text)

    footprint_line = _header_line(part_text, "[footprint]")
    findings = fransys_parts.lint(tmp_path)

    field_missing = [f for f in findings if f.code == "FIELD_MISSING" and "footprint" in f.message]
    assert len(field_missing) == 1
    assert field_missing[0].message == f"parts/x.toml:{footprint_line}: footprint is missing 'name'"


def test_part_records_its_library_and_the_part_headers_own_line(tmp_path):
    """mutmut triage rank 2: no test in this package ever reads `Part.library` back, or puts
    `[part]` after a comment and checks the resulting `Origin.line` against the real header
    line, so `_build_part_file`'s `library=library_id` and `origins.get(("part",), 1)` survive
    untested (spec P6)."""
    from fransys_model.kernel import Origin, freeze, make_id
    from fransys_model.vocab import PartLibrary, parts

    (tmp_path / "library.toml").write_text(
        'schema = 1\nname = "t"\nversion = "0.0.0"\ndescription = "d"\n'
    )
    (tmp_path / "parts").mkdir()
    part_text = (
        "schema = 1\n\n"
        "# padding\n"
        "# more padding\n"
        "[part]\n"
        'mpn = "X-1"\n'
        'manufacturer = "Demo"\n'
        'description = "d"\n'
        'category = "generic"\n'
        'class_code = "X"\n\n'
        "[[function]]\n"
        'name = "f1"\n'
        'kind = "generic"\n'
        'ports = [{ name = "1", role = "generic" }]\n'
    )
    (tmp_path / "parts" / "x.toml").write_text(part_text)

    part_line = _header_line(part_text, "[part]")

    model = freeze(fransys_parts.load_path(tmp_path))
    (part,) = parts(model).values()

    library_id = make_id(PartLibrary, ("part_library", "t"))
    assert part.library == library_id
    assert model.origins[part.id] == Origin(file="parts/x.toml", line=part_line, note="")


def test_demo_redundancy_module_takes_class_code_r():
    """DEMO-RED-2IN blocks back-flow: class R, not U or T (DEMO-RENAMES); the IO parts stay U."""
    from fransys_model.kernel import freeze
    from fransys_model.vocab import parts

    model = freeze(fransys_parts.load_path(DEMO))
    codes = {p.mpn: p.class_code for p in parts(model).values() if p.mpn.startswith("DEMO-RED")}
    assert codes == {"DEMO-RED-2IN": "R", "DEMO-RED-2IN-NET": "R"}
    assert {p.class_code for p in parts(model).values() if p.mpn.startswith("DEMO-IO-")} == {"U"}


def test_demo_housings_name_the_parts_they_mate_with():
    """HA7 / parts-0016: `mates` is data on the connector facet; schema version 10."""
    from fransys_model.kernel import SCHEMA_VERSION, freeze
    from fransys_model.vocab import function_templates, parts
    from fransys_model.vocab.facets.connector import ConnectorFacet
    from fransys_model.vocab.tables import facets_of

    model = freeze(fransys_parts.load_path(DEMO))
    mpn_of = {p.id: p.mpn for p in parts(model).values()}
    template_mpn = {t.id: mpn_of[t.part] for t in function_templates(model).values()}
    mates = {
        template_mpn[f.subject]: f.mates
        for f in facets_of(model, ConnectorFacet).values()
        if template_mpn[f.subject].startswith("DEMO-HSG-")
    }
    assert mates == {
        "DEMO-HSG-4F": ("DEMO-HSG-4M", "DEMO-CONN-4P"),
        "DEMO-HSG-4M": ("DEMO-HSG-4F",),
    }
    assert SCHEMA_VERSION == 10
