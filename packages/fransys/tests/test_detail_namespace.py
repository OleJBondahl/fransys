"""`d.detail` holds the detail calls, and the old names on `d` raise (author-0042, A2)."""

import re
from pathlib import Path

import fransys as fr
import pytest
from fransys.colours import BK
from fransys_author.errors import AuthorAttributeError
from fransys_author.surface._removed import REMOVED

# The digest of this design built with d.wire, d.net and d.busbar at main 8650e4af9, without the rail_bond call (RAIL-FLAG R900 G3 deleted it).
# The digest covers the demo part library, so it moved with the library, never with the move:
# 54c87f08d (main f6f5720e4), 60889bbd4 (DEMO-LAMP-24 rating, parts-0022) and 7597e12be (demo
# motor and relay coil draw, model-0232). At the batch merge of each of the last two, the merged
# tree with that change's part files set back gave the digest from before it (API-BATCH), and
# COIL-FAN-PINS's `plc-do-16ch.toml` (layout-0208 R1), checked the same way.
# SCHEMA_VERSION 19 to 20 (model-0256) moved it too. LEGACY-SHORTS (2026-10-15) adds the demo
# parts `actuator-4p-2sw.toml` and `cable-8g0_75.toml`; with those two files removed the digest is
# the pin before it (2e734886c..., checked at base 121e32099 and at HEAD minus the two files).
# CORPUS-MCC (2026-10-15) adds five demo parts (`switch-disconnector-4p`, `pb-no`,
# `timer-star-delta`, `vfd-4kw`, `motor-11kw-star-delta`); with those five files removed the
# digest is the pin before it (7449c9999..., checked on a copy of the library at HEAD).
# CORPUS-BOARD (2026-10-15) adds `rcd-4p.toml` and `mcb-3pn.toml`; with those two files removed the
# digest is the pin before it (fe7d8f55c..., checked on a copy of the merged library without them).
# CORPUS-PANEL (2026-10-15) adds ten demo parts; with all
# seventeen added files (MCC 5, BOARD 2, PANEL 10) removed the digest is the pin before them
# (7449c9999..., checked on a copy of the merged library).
# PLC-CHANNEL-ORDER-FIX (2026-10-15) adds `plc-dio-mixed.toml`; with that file removed the digest
# is the pin before it (d8f37d280..., checked on a copy of the library without it).
# TYPED-PINS (2026-10-15) adds `contactor-1p-marked.toml` and `psu-24v-marked.toml`; with those two
# files removed the digest is the pin before them (810ebd7ff..., checked on the library without).
# WIRE-ROWS P6 (model-0260) adds `source_row` to the demo `vfd-4kw.toml` outputs; with that file
# set back the digest is the pin before it (8a8774887..., checked on a copy of the merged tree).
# GRID-HOME-A (decision 0230, designer ruling Q1 2026-10-16) writes the `layout.drawing_library`
# record into every built model, so the digest moves once; the pin before it ended 8463a3d4fdc1...
# CLEANUP-ROUND-2-A rider R sets `psu-24v-dcok.toml` `dc_ok` to `contact_no` (pin before it
# b5bc2973599f...). SETTINGS-A1 (0237, model-0312) writes `layout.paper` and two sheet formats:
# it moves again; the pin before it ended cc38391d2251... Ruling 91 (DEMO-LAMP-24 draws the lamp
# symbol: `lamp-24v.toml` symbol and port map) moves it again; the pin before it ended
# 68a5c7009a99... SYMBOL-RULES E sets the star-delta demo motor's `end` function to kind `generic`:
# it moves; the pin before the merge of the two ended 8fd14fdf0932...
# SETTINGS-OPEN SO-B writes the twelve house text records into every built model, and INK-HEIGHT
# (layout-0385) swaps `capital_ratio` for `em_heights` in the drawing library record: each moves
# it; the pin before them ended 2f72879e404b... SO-B2 makes `[revision_table] columns` hold
# `[words]` keys: it moves again; the pin before it ended a56b3546e1f7... R493 (c) moves it again
# on the merge with SO-B: the pin is recomputed on the merged tree. R498 and R503 W3 delete the
# `[conductors]` record and the phase angles, R509 drops `[rails] ac` and R513 the whole
# `[rails]` record; SO-E (model-0365) swaps `em_heights` for `ems` and `lines` in the same record
# (R511: no `dash`): it moves again; the pin before them ended 4312e1068d46... SO-C L1 adds the
# `[lists]` house record to every built model (R519): it moves again; the pin before it ended
# 89d0ce6b4983... SO-C B and C add the `[export]` and `[designation]` house records: it moves again;
# the pin before it ended d0cb99189b71... model-0378 deletes ColourCodes: it moves again; model-0370
# bumps SCHEMA_VERSION to 21, which the digest carries: it moves again; the pin before them ended ba1adcb7cbb8... (main, schema 20)
# ADOPT-PARTS-3 (model-0381, R783) stores rating and operating as elecdef values and the fuse in a
# `facet.block` row, "ac" becomes "AC" (R848, R783 Q1/Q3, accepted by class): it moves again; the pin before it ended 4100bf40afed...
# R860 adds the two reference heights to the `[title_block]` house record: it moves again; the pin before it ended 51e3fda1c185...
# parts-0024 adds a `[footprint]` to four demo parts (the part library is in the digest): it moves again; the pin before it ended 6bf1c857aaec...
# DETAIL-WIRE-LABEL renames the `wires` list column field `label` to `ends` in settings (digest carries them): it moves again;
# the pin before it ended f4e89ec83ec7...
# RAIL-FLAG (R921) drops the design's rail_bond call and DETAIL-WIRE-LABEL renames a settings field:
# merged, they move it once more; the pin before it ended 1507d9ac4899...
# the id seed rename (S2-TRACE-B-5, R1070) moves it again; the pin before it ended 37afb35c9889...
# PE-AS-RAIL (R1289) deletes the four demo pe-bar parts (the part library is in the digest): it moves again; the pin before it ended 1699b9d755e7...
# LAV-B (R1266) adds the two twin terminal demo parts (the part library is in the digest): it moves again; the pin before it ended 6ae6eaa66db4d
# API-FACTS (R1499 4) deletes d.detail.net, so the design drops its net call: it moves again; the pin before it ended 1d18c486efda...
# API-CLOSE (R1486) adds `marker_padding` to the `[profile]` house record and API-022 P2 deletes the hint kinds, and
# API-WIRE (R1496) deletes the wire label= the design carried (label="W1"): it moves again; the pin before them ended b45c195b49ad...
# STUB-PER-CONDUCTOR (layout-0533) bumps SCHEMA_VERSION 22 -> 23, which the digest holds: only that moves it; it ended e755c0bb2d24...
# MATES-LIB (R1740) stores the connector Gender by its elecdef name (MALE, not male): it moves again; the pin before it ended ede710deb701...
# DEMO-TB-2.5-X12 left the demo library (R1778); DEMO-CTRL-SUPPLY-2DO-1AI (N5c) joined it: the merge moves it; it ended dcb48ccd9eca...
# DEMO-GAS-DETECTOR, DEMO-TRAFO-400-230, DEMO-MCB-2P-C2 (DET-CND) and DEMO-BOARD-4J (MARK-DOOR-FIX) joined the demo library: it moves again.
# ONE-PAGE (R1830): the house [reference] record lost `location_sign` and `set_sep`, so the merge digest moves again; it ended c8b1536b4f9e...
# HIDE-PE (R1830) adds `hide_pe` to the `[export]` house record: merged with ONE-PAGE it moves once more; it ended 0fd1ae32af13...
# WAGO-CDP (R1824) bumps SCHEMA_VERSION 23 -> 24 (plc_request and part fields): it moves once more; it ended 08294f7055b2...
# ORDER-HINT (model-0442) adds Conductor.block, SCHEMA_VERSION 24 -> 25 (WAGO-CDP took 24): the digest moves again; it ended cf829c7b6778...
# PLC-DESCRIPTION (model-0443) adds PlcRequestFacet.description, SCHEMA_VERSION 25 -> 26: the digest moves again; it ended c6b2d9f0f569...
# CONNECTOR-FACET-ELECDEF (model-0446): ConnectorFacet holds an elecdef Connector, the demo parts say `poles`; it moves again, ended d300a4f316e6...
# RING-OUT (R2008) adds the ring_* keys to [words]: the digest moves again; it ended b1224a935cb6...
# RING-OUT-DOCS (R2023) adds `ring_out_skip` to the `[export]` house record: it moves again; it ends 6d0ef4c52c79...
# CONNECTOR-FACET-2: SCHEMA_VERSION 26 -> 27 moves it once more; the pin is recomputed on the merge with RING-OUT-DOCS: 35be4a84e32b...
# PORT-CONNECTOR (model-0448): SCHEMA_VERSION 27 -> 28 moves it once more (35be4a84e32b... before).
# BOX-SIDE (model-0449, R2070): SCHEMA_VERSION 28 -> 29 writes box_side always; it moves once more (7062cea82cfc... before).
_DIGEST_BEFORE_THE_MOVE = "70e3b4c02ed6e0f9186f7d886fe96e25fc8690cf15cd846f57f3be31f7ec363a"


def test_each_moved_call_builds_the_model_it_built_on_d():
    d = fr.design("demo_parts", place="CAB")
    d.location("CAB", "Cabinet")
    strip = d.terminal_strip("X1", "DEMO-TB-2.5", 6)
    k1 = d.device("K1", "DEMO-CTR-3P-24")
    t = [strip[i] for i in range(1, 7)]
    d.detail.busbar(t[0], t[1])
    d.series(k1.main["1"], t[0].outer, wire=(BK, 1.5))
    assert fr.build(d).model.digest == _DIGEST_BEFORE_THE_MOVE


_GUIDE = Path(__file__).parents[1] / "src" / "fransys" / "guide" / "moving-to-0.22.md"


def _owner(name: str):
    d = fr.design("demo_parts")
    handles = {"fr": fr, "Design": d, "Detail": d.detail, "Layout": d.layout}
    handles["Fn"] = d.device("S1", "DEMO-PB-NC").sw
    handles["Terminal"] = d.terminal_strip("X4", "DEMO-TB-2.5", 2)[1]
    return handles[name]


@pytest.mark.parametrize("row", REMOVED, ids=lambda r: f"{r.owner}.{r.name}")
def test_a_removed_name_raises_its_table_text(row):
    obj = _owner(row.owner)
    with pytest.raises(AuthorAttributeError, match=re.escape(f"{row.text}; see moving-to-0.22#{row.anchor}")):
        getattr(obj, row.name)
    assert getattr(obj, row.name, None) is None


def test_the_moved_busbar_still_lives_on_detail():
    assert callable(fr.design("demo_parts").detail.busbar)


@pytest.mark.parametrize("owner", ["fr", "Design", "Detail", "Layout", "Terminal"])
def test_an_unknown_or_private_name_names_no_removal(owner):
    for name in ("no_such_name", "__wrapped__"):
        with pytest.raises(AttributeError) as raised:
            getattr(_owner(owner), name)
        assert "removed in 0.22" not in str(raised.value)


def test_every_table_anchor_is_in_the_moving_to_page():
    page = _GUIDE.read_text(encoding="utf-8")
    assert [row for row in REMOVED if f'id="{row.anchor}"' not in page] == []
