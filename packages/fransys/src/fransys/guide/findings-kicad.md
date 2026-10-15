# Finding codes: KiCad

> Offline copy. Read the official docs for your version at https://olejbondahl.github.io/fransys/X.Y.Z/ (X.Y.Z is `fransys.__version__`), or https://olejbondahl.github.io/fransys/X.Y.Z/llms.txt. Use this copy only offline.

Codes the KiCad import emits. Who acts is explained in [`findings.md`](findings.md).

| Code | Severity | Stage | Who acts | Meaning | Fix |
| --- | --- | --- | --- | --- | --- |
| NET_NAME_DUPLICATE | ERROR | kicad | consumer | Two or more KiCad netlist nets share a name, so KiCad would merge them on import. | Give each net a distinct name. |
| NET_SINGLE_PIN | INFO | kicad | note | A KiCad netlist net has one pin. | Nothing is wrong; wire a second end only if one was meant. |
| NODE_WITHOUT_COMPONENT | WARNING | kicad | consumer | A netlist pin belongs to an item with no footprint (or is the board's own pin), so KiCad drops it on import. | Give the item a footprint, or model the connector as a child item with one. |
| PAD_ON_MULTIPLE_NETS | ERROR | kicad | consumer | One component pad is in more than one KiCad netlist net. | Fix the wiring so each pad is on exactly one net. |
| PART_WITHOUT_FOOTPRINT | WARNING | kicad | consumer | A board item's part has no footprint, so the KiCad netlist omits it. | Add a footprint to the part. |
| REFERENCE_DUPLICATE | ERROR | kicad | consumer | Two board parts share one reference designation in the KiCad netlist. | Give each part a distinct designation. |
| UNCONNECTED_PIN | INFO | kicad | note | A pin of a board part is in no net in the KiCad netlist. | Usually nothing to fix unless a connection was meant. |
