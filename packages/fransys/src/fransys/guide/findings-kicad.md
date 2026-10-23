# Finding codes: KiCad

> Offline copy. Read the official docs for your version at https://olejbondahl.github.io/fransys/X.Y.Z/ (X.Y.Z is `fransys.__version__`), or https://olejbondahl.github.io/fransys/X.Y.Z/llms.txt. Use this copy only offline.

Codes the KiCad import emits. Who acts is explained in [`findings.md`](findings.md).

| Code | Severity | Stage | Who acts | Meaning | Fix |
| --- | --- | --- | --- | --- | --- |
| NET_NAME_DUPLICATE | ERROR | kicad | consumer | Two or more KiCad netlist nets share a name, so KiCad would merge them on import. | Give each net a distinct name. Write: d.detail.net(<distinct name>, *ports) |
| NET_SINGLE_PIN | INFO | kicad | note | A KiCad netlist net has one pin. | Nothing is wrong; wire a second end only if one was meant. |
| NODE_WITHOUT_COMPONENT | WARNING | kicad | consumer | A netlist pin belongs to an item with no footprint (or is the board's own pin), so KiCad drops it on import. | No call clears this: give the item's part a footprint, or model the connector as a child item with one. |
| PAD_ON_MULTIPLE_NETS | ERROR | kicad | consumer | One component pad is in more than one KiCad netlist net. | No call clears this: fix the wiring so each pad is on exactly one net. |
| PART_WITHOUT_FOOTPRINT | WARNING | kicad | consumer | A board item's part has no footprint, so the KiCad netlist omits it. | No call clears this: add a footprint to the part's data. |
| PIN_ID_COLLISION | ERROR | kicad | part author | Two pins of one board part would write one KiCad pin id, because KiCad keys a pin by its name, which is the footprint pad name. A labelled connector may repeat a pin name in the drawing; the netlist cannot. | No call clears this: rename the part's pins so each is its footprint pad name, in the part file. |
| REFERENCE_DUPLICATE | ERROR | kicad | consumer | Two board parts share one reference designation in the KiCad netlist. | Give each part a distinct tag, which sets its designation. Write: d.device(<tag>, <mpn>) |
| UNCONNECTED_PIN | INFO | kicad | note | A pin of a board part is in no net in the KiCad netlist. | Usually nothing to fix unless a connection was meant. |
