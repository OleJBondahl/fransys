import xml.etree.ElementTree as ET
from decimal import Decimal
from pathlib import Path

import pytest
from fransys_wago import modules_xml
from fransys_wago.signals import SIGNALS

from fransys_model.derive import plc_rack_modules
from fransys_model.kernel import SchemaError
from fransys_model.vocab.enums import SignalType

GOLDEN = Path(__file__).resolve().parent / "golden" / "rack.xml"

# The table of the order, spelled out here so that a change to it in the package shows up.
EXPECTED = {
    SignalType.DI: ("DI", "0", "bool", "Digital input channel"),
    SignalType.DO: ("DO", "1", "bool", "Digital output channel"),
    SignalType.AI_CURRENT: ("AI", "0", "short", "Analog input channel"),
    SignalType.AI_VOLTAGE: ("AI", "0", "short", "Analog input channel"),
    SignalType.AO_CURRENT: ("AO", "1", "short", "Analog output channel"),
    SignalType.AO_VOLTAGE: ("AO", "1", "short", "Analog output channel"),
    SignalType.RTD: ("RTD", "0", "short", "Analog input channel"),
    SignalType.RELAY: ("RO", "1", "bool", "Relay output channel"),
}


def _parse(text):
    return ET.fromstring(text)  # noqa: S314 -- the package's own output


def _one_module_rack(new_rack, signals, names=None, mpn="750-X"):
    """A rack with one module of `signals`, its channels bound to devices named by `names`."""
    rack = new_rack()
    module = rack.module(rack.part("p", mpn, signals), "m", "A1", 1)
    for index, (designation, signal_name) in enumerate(names or ()):
        rack.device(f"dev{index}", designation, signal_name, module.channels[index])
    return rack, module


def _channel_names(rack):
    root = _parse(modules_xml(rack.freeze(), rack.rack))
    return [channel.get("Name") for channel in root.iter("Channel")]


def test_the_fragment_has_the_shape_of_the_spec(demo_rack):
    text = modules_xml(demo_rack.freeze(), demo_rack.rack)
    assert text.startswith("<Modules>\n  <Module ")
    assert text.endswith("  </Module>\n</Modules>\n")
    assert "<?xml" not in text
    assert "/>" not in text
    assert "\r" not in text
    assert "xmlns" not in text
    assert all((len(line) - len(line.lstrip(" "))) % 2 == 0 for line in text.splitlines())


def test_the_golden_is_exact_bytes(demo_rack):
    text = modules_xml(demo_rack.freeze(), demo_rack.rack)
    assert GOLDEN.read_bytes() == text.encode("utf-8")
    assert b"\r" not in GOLDEN.read_bytes()


def test_every_module_and_channel_matches_the_rows(demo_rack):
    model = demo_rack.freeze()
    rows = [row for row in plc_rack_modules(model, demo_rack.rack) if row.channels]
    modules = list(_parse(modules_xml(model, demo_rack.rack)))
    assert len(modules) == len(rows) == 4
    for module, row in zip(modules, rows, strict=True):
        assert module.tag == "Module"
        assert module.get("Model") == "WagoIOModules.IOModule"
        assert module.get("Description") == row.description
        channels = list(module)
        assert len(channels) == len(row.channels)
        for nr, (channel, source) in enumerate(zip(channels, row.channels, strict=True)):
            _, input_, kind, description = EXPECTED[source.signal]
            assert channel.tag == "Channel"
            assert channel.get("Input") == input_
            assert channel.get("Model") == f"CDPSignalChannel<{kind}>"
            assert channel.get("NetworkConvert") == "1"
            assert channel.get("Nr") == str(nr)
            assert channel.get("Type") == kind
            assert channel.get("Value") == "0"
            assert channel.get("Description") == description
            assert (channel.get("Unit") is not None) == (source.scaling is not None)
            operators = list(channel)
            if source.scaling is None:
                assert operators == []
                continue
            assert channel.get("Unit") == source.scaling.unit
            (operator,) = operators
            assert operator.attrib == {
                "Interpolation": "Linear",
                "Model": "Automation.ScalingOperator<double>",
                "Name": "Scale",
                "Type": "double",
            }
            low, high = list(operator)
            for point, name, raw, eng in (
                (low, "ScalingPoint", source.scaling.raw_min, source.scaling.eng_min),
                (high, "ScalingPoint1", source.scaling.raw_max, source.scaling.eng_max),
            ):
                assert point.attrib == {
                    "InValue": str(raw),
                    "OutValue": str(eng),
                    "Model": "Automation.ScalingPoint<double>",
                    "Name": name,
                    "Type": "double",
                }


def test_the_demo_rack_reads_as_the_spec_says(demo_rack):
    root = _parse(modules_xml(demo_rack.freeze(), demo_rack.rack))
    assert [(m.get("Name"), m.get("Description")) for m in root] == [
        ("750-1405_3DI_a", "16-channel digital input"),
        ("750-1504_2DO_a", "4-channel digital output"),
        ("750-455_3AI_a", "4-channel 4-20 mA"),
        ("750-1405_1DI_b", "16-channel digital input"),
    ]
    assert [[c.get("Name") for c in module] for module in root] == [
        ["B1_Door", "B2_Gate", "A1_2"],
        ["K1_Fan", "A2_1"],
        ["T1_Level", "T2_Flow", "A3_2"],
        ["A4_0"],
    ]
    assert [[c.get("Nr") for c in module] for module in root] == [
        ["0", "1", "2"],
        ["0", "1"],
        ["0", "1", "2"],
        ["0"],
    ]


def test_attributes_come_in_the_order_of_the_spec(demo_rack):
    text = modules_xml(demo_rack.freeze(), demo_rack.rack)
    root = _parse(text)
    assert list(root[0].attrib) == ["Model", "Name", "Description"]
    assert list(root[0][0].attrib) == [
        "Input",
        "Model",
        "Name",
        "NetworkConvert",
        "Nr",
        "Type",
        "Value",
        "Description",
    ]
    scaled = root[2][0]
    assert list(scaled.attrib)[-2:] == ["Description", "Unit"]
    assert list(scaled[0].attrib) == ["Interpolation", "Model", "Name", "Type"]
    assert list(scaled[0][0].attrib) == ["InValue", "OutValue", "Model", "Name", "Type"]
    assert '\n    <Channel Input="0" Model="CDPSignalChannel&lt;bool&gt;" Name="B1_Door"' in text
    assert (
        '<ScalingPoint InValue="4" OutValue="0" Model="Automation.ScalingPoint&lt;double&gt;" '
        'Name="ScalingPoint" Type="double"></ScalingPoint>'
    ) in text


def test_a_module_without_channels_is_not_emitted(demo_rack):
    model = demo_rack.freeze()
    rows = plc_rack_modules(model, demo_rack.rack)
    assert [row.designation for row in rows if not row.channels] == ["-A0"]
    text = modules_xml(model, demo_rack.rack)
    assert "750-352" not in text
    assert text.count("<Module ") == len(rows) - 1


def test_a_channel_less_module_takes_no_letter(new_rack):
    rack = new_rack()
    coupler = rack.part("coupler", "750-X", ())
    card = rack.part("card", "750-X", (SignalType.DI,))
    rack.module(coupler, "m0", "A0", 0)
    rack.module(card, "m1", "A1", 1)
    root = _parse(modules_xml(rack.freeze(), rack.rack))
    assert [m.get("Name") for m in root] == ["750-X_1DI_a"]


def test_letters_run_a_to_z_then_aa_and_restart_per_mpn(new_rack):
    rack = new_rack()
    part = rack.part("card", "750-X", (SignalType.DI,))
    other = rack.part("other", "750-Y", (SignalType.DI,))
    for number in range(27):
        rack.module(part, f"m{number:02}", f"A{number}", number)
    rack.module(other, "y", "Y1", 100)
    names = [m.get("Name") for m in _parse(modules_xml(rack.freeze(), rack.rack))]
    letters = [name.rsplit("_", 1)[1] for name in names]
    assert letters[:27] == [*"abcdefghijklmnopqrstuvwxyz", "aa"]
    assert names[-1] == "750-Y_1DI_a"


def test_letters_continue_past_zz(new_rack):
    rack = new_rack()
    part = rack.part("card", "750-X", (SignalType.DI,))
    for number in range(704):
        rack.module(part, f"m{number:03}", f"A{number}", number)
    names = [m.get("Name") for m in _parse(modules_xml(rack.freeze(), rack.rack))]
    letters = [name.rsplit("_", 1)[1] for name in names]
    assert (letters[25], letters[26], letters[27], letters[51], letters[52]) == (
        "z",
        "aa",
        "ab",
        "az",
        "ba",
    )
    assert (letters[701], letters[702], letters[703]) == ("zz", "aaa", "aab")
    assert len(set(letters)) == 704


@pytest.mark.parametrize(
    ("signals", "suffix"),
    [
        ((SignalType.DI,) * 4, "4DI"),
        ((SignalType.RELAY,) * 2, "2RO"),
        ((SignalType.AI_VOLTAGE,) * 3, "3AI"),
        ((SignalType.DI, SignalType.DO), "2MIX"),
        ((SignalType.AI_CURRENT,) * 2 + (SignalType.AI_VOLTAGE,) * 2, "4MIX"),
    ],
)
def test_the_module_name_counts_channels_and_names_one_signal_or_mix(new_rack, signals, suffix):
    rack, _ = _one_module_rack(new_rack, signals)
    (module,) = _parse(modules_xml(rack.freeze(), rack.rack))
    assert module.get("Name") == f"750-X_{suffix}_a"


@pytest.mark.parametrize("signal", list(SignalType))
def test_each_signal_type_reads_from_the_table(new_rack, signal):
    rack, _ = _one_module_rack(new_rack, (signal,))
    ((channel,),) = [list(m) for m in _parse(modules_xml(rack.freeze(), rack.rack))]
    abbr, input_, kind, description = EXPECTED[signal]
    assert channel.get("Input") == input_
    assert channel.get("Type") == kind
    assert channel.get("Model") == f"CDPSignalChannel<{kind}>"
    assert channel.get("Description") == description
    assert SIGNALS[signal].abbr == abbr


def test_the_signal_table_covers_every_signal_type():
    assert set(SIGNALS) == set(SignalType)
    assert set(EXPECTED) == set(SignalType)


@pytest.mark.parametrize("signal", list(SignalType))
def test_the_package_table_is_the_spelled_out_one(signal):
    entry = SIGNALS[signal]
    assert (entry.abbr, "1" if entry.output else "0", entry.kind, entry.description) == EXPECTED[
        signal
    ]


@pytest.mark.parametrize(
    ("designation", "signal_name", "expected"),
    [
        ("B1", "Door", "B1_Door"),
        ("B-1", "Door open", "B_1_Door_open"),
        ("B1", 'a<b>&"c"', "B1_a_b_c"),
        ("1B", "x", "N_1B_x"),
        ("7", "8", "N_7_8"),
        ("__a--", "--b__", "a_b"),
        ("Tür", "Höhe", "T_r_H_he"),
        ("=A1+C1", "Lvl", "A1_C1_Lvl"),
        ("--", "!!", ""),
        ("-X", "Y", "X_Y"),
    ],
)
def test_a_bound_channel_name_is_the_sanitised_designation_and_signal_name(
    new_rack, designation, signal_name, expected
):
    rack, _ = _one_module_rack(new_rack, (SignalType.DI,), [(designation, signal_name)])
    assert _channel_names(rack) == [expected]


@pytest.mark.parametrize(
    ("module_designation", "expected"),
    [("A1", ["A1_0", "A1_1"]), ("3rd", ["N_3rd_0", "N_3rd_1"]), ("A-1", ["A_1_0", "A_1_1"])],
)
def test_a_spare_channel_name_is_the_module_designation_and_the_zero_based_number(
    new_rack, module_designation, expected
):
    rack = new_rack()
    rack.module(rack.part("p", "750-X", (SignalType.DI,) * 2), "m", module_designation, 1)
    assert _channel_names(rack) == expected


def test_a_channel_with_a_device_but_no_signal_name_is_named_as_a_spare(new_rack):
    rack = new_rack()
    module = rack.module(rack.part("p", "750-X", (SignalType.DI,) * 2), "m", "A1", 1)
    rack.device("dev", "B1", None, module.channels[1])
    assert _channel_names(rack) == ["A1_0", "A1_1"]


def test_two_channels_with_one_name_are_both_kept_as_they_are(new_rack):
    rack = new_rack()
    module = rack.module(rack.part("p", "750-X", (SignalType.DI,) * 2), "m", "A1", 1)
    rack.device("d1", "B-1", "Door", module.channels[0])
    rack.device("d2", "B_1", "Door", module.channels[1])
    assert _channel_names(rack) == ["B_1_Door", "B_1_Door"]


def test_a_name_that_sanitises_to_nothing_is_emitted_empty(new_rack):
    rack, _ = _one_module_rack(new_rack, (SignalType.DI,), [("--", "!!")])
    text = modules_xml(rack.freeze(), rack.rack)
    assert 'Name="" NetworkConvert' in text


def test_scaling_prints_the_numbers_as_they_are(new_rack):
    rack = new_rack()
    module = rack.module(rack.part("p", "750-X", (SignalType.AI_CURRENT,) * 2), "m", "A1", 1)
    rack.device(
        "t1",
        "T1",
        "Lvl",
        module.channels[0],
        signal=SignalType.AI_CURRENT,
        scaling=("bar", 0, 32767, Decimal("0.50"), Decimal("-1E+2")),
    )
    rack.device(
        "t2",
        "T2",
        "Flw",
        module.channels[1],
        signal=SignalType.AI_CURRENT,
        scaling=("m", 4, 20, Decimal(0), Decimal(5)),
    )
    text = modules_xml(rack.freeze(), rack.rack)
    assert 'InValue="0" OutValue="0.50"' in text
    assert 'InValue="32767" OutValue="-1E+2"' in text
    assert 'InValue="4" OutValue="0"' in text
    assert 'InValue="20" OutValue="5"' in text
    assert 'OutValue="0.5"' not in text


def test_scaling_follows_the_row_whatever_the_signal(new_rack):
    rack = new_rack()
    module = rack.module(rack.part("p", "750-X", (SignalType.DI,)), "m", "A1", 1)
    rack.device("d", "B1", "Door", module.channels[0], scaling=("x", 0, 1, Decimal(0), Decimal(1)))
    ((channel,),) = [list(m) for m in _parse(modules_xml(rack.freeze(), rack.rack))]
    assert channel.get("Unit") == "x"
    assert [child.tag for child in channel] == ["Operator"]


def test_a_channel_without_scaling_has_no_unit_and_no_operator(demo_rack):
    root = _parse(modules_xml(demo_rack.freeze(), demo_rack.rack))
    unscaled = root[2][1]
    assert unscaled.get("Name") == "T2_Flow"
    assert "Unit" not in unscaled.attrib
    assert list(unscaled) == []


def test_xml_special_characters_are_escaped_and_round_trip(new_rack):
    description = 'Module <A> & "B"\nline two\ttab\rend'
    unit = 'a<b>&"c"\nd'
    rack = new_rack()
    part = rack.part("p", "750-X", (SignalType.AI_CURRENT,), description=description)
    module = rack.module(part, "m", "A1", 1)
    rack.device(
        "t1",
        "T1",
        "Lvl",
        module.channels[0],
        signal=SignalType.AI_CURRENT,
        scaling=(unit, 4, 20, Decimal(0), Decimal(100)),
    )
    text = modules_xml(rack.freeze(), rack.rack)
    assert "Module <A>" not in text
    assert "Module &lt;A&gt; &amp; &quot;B&quot;&#10;line two&#9;tab&#13;end" in text
    (module_element,) = _parse(text)
    assert module_element.get("Description") == description
    assert module_element[0].get("Unit") == unit


def test_an_empty_rack_is_an_empty_modules_element(new_rack):
    rack = new_rack()
    assert modules_xml(rack.freeze(), rack.rack) == "<Modules></Modules>\n"


def test_a_rack_of_channel_less_modules_is_an_empty_modules_element(new_rack):
    rack = new_rack()
    rack.module(rack.part("coupler", "750-352", ()), "m0", "A0", 0)
    assert modules_xml(rack.freeze(), rack.rack) == "<Modules></Modules>\n"


def test_the_same_model_gives_the_same_bytes(demo_rack):
    model = demo_rack.freeze()
    assert modules_xml(model, demo_rack.rack) == modules_xml(model, demo_rack.rack)


@pytest.mark.parametrize("seed", range(6))
def test_insertion_order_does_not_change_the_bytes(demo_rack, seed):
    assert modules_xml(demo_rack.freeze(seed), demo_rack.rack) == modules_xml(
        demo_rack.freeze(), demo_rack.rack
    )


def test_a_rack_that_is_not_an_item_is_refused(demo_rack):
    model = demo_rack.freeze()
    (facet_owner,) = [r for r in demo_rack.records if getattr(r, "mpn", "") == "750-352"]
    with pytest.raises(SchemaError):
        modules_xml(model, facet_owner.id)
