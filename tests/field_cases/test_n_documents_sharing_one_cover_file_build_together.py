"""Field case: documents of different subjects may share one cover file.

The engineering shape: a project with two cabinets, each printed as its own document, and one
cover template for both.

The bug: a document's key was its cover's file stem, so the second document with the same cover
carried the first one's id with other content, and `fr.build` raised `MergeConflict: two different
records share one id` with no hint of the cover. Fixed by API-FRICTION-1 F7 (RIO7): the key also
holds the preset and the subject, so one cover path serves any number of documents.
"""

import pathlib
import tempfile

import fransys as fr

from fransys_model.vocab.tables import documents


def test_two_documents_on_one_cover_path_build() -> None:
    d = fr.design("demo_parts")
    cabs = [d.location(tag, f"Cabinet {tag}") for tag in ("CA", "CB")]
    for tag in ("CA", "CB"):
        with d.function(f"F{tag}", "Feed"):
            d.device(f"F{tag}1", "DEMO-FUSE-DC-160", place=tag)
    cover = pathlib.Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# cover\n", encoding="utf-8")
    docs = [fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover) for cab in cabs]
    result = fr.build(d, *docs)
    assert len(documents(result.model)) == 2
