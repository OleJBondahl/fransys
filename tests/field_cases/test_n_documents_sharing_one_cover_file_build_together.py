"""Field case: two cabinets, each printed as its own document, share one cover template file.
The bug: a document's key was its cover's file stem, so the second carried the first's id and fr.build raised MergeConflictError.
Fixed by API-FRICTION-1 F7 (RIO7), the key also holds the preset and subject, so one cover path serves any number of documents."""

import pathlib
import tempfile

import fransys as fr

from fransys_model.vocab.tables import documents


def test_two_documents_on_one_cover_path_build() -> None:
    d = fr.design("demo_parts")
    cabs = [d.location(tag, f"Cabinet {tag}") for tag in ("CA", "CB")]
    for tag in ("CA", "CB"):
        with d.function(f"F{tag}", "Feed"):
            fuse = d.device(f"F{tag}1", "DEMO-FUSE-DC-160", place=tag)
            twin = d.device(f"F{tag}2", "DEMO-FUSE-DC-160", place=tag)
            for pin in (1, 2):
                d.series(fuse.element[pin], twin.element[pin], wire=("BU", 0.5))
    cover = pathlib.Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# cover\n", encoding="utf-8")
    docs = [fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover) for cab in cabs]
    result = fr.build(d, *docs)
    assert len(documents(result.model)) == 2
