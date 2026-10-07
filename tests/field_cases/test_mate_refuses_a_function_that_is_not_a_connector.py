"""Field case: a harness plug mated with the coil function of a relay.

The engineering shape: a plug on a harness is plugged into a relay's coil, a function that is
neither a connector nor a terminal. A mate joins two connector or terminal functions and makes
same-named pins conductive; a coil takes no plug.

The bug: `d.mate` accepted the coil, the model froze, and the plug's pins joined the coil's
same-named pins without a word. Nothing checked the kind of a mate's ends.
The rule (decision model-0169): a mate whose end is neither a connector nor a terminal function
is the ERROR `MATE_NOT_CONNECTOR`.
"""

import fransys as fr

_PLUG = "DEMO-CONN-2P"
_RELAY = "DEMO-RLY-2CO-24"


def _findings() -> tuple[fr.Finding, ...]:
    d = fr.design("demo_parts", place="EXT")
    d.location("EXT", "External")
    relay = d.device("K1", _RELAY, external=True)
    harness = d.harness("W3")
    plug = d.device(None, _PLUG, name="p1", parent=harness)
    d.mate(plug, relay.coil)
    return fr.build(d).findings


def test_a_plug_mated_to_a_coil_is_an_error() -> None:
    codes = [f.code for f in _findings() if f.severity.name == "ERROR"]
    assert "MATE_NOT_CONNECTOR" in codes
