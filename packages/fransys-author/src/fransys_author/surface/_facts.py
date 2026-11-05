"""Facts: `project` and `revision`."""

from typing import TYPE_CHECKING

from fransys_author.design import Design as EngineDesign
from fransys_author.errors import AuthorError

if TYPE_CHECKING:
    from fransys_author.surface.design import Design


class Facts:
    """The fact calls of the surface `Design`."""

    def project(  # noqa: PLR0913 -- the engine's own title-block keywords, passed through [public keyword API kept, decision 0444]
        self: "Design",
        *,
        title: str,
        number: str,
        customer: str,
        revision: int,
        author: str,
        notice: str | None = None,
        version: int = 1,
    ) -> None:
        """State the title-block facts of the project, at most one per model.

        Does not rename or default a field: the keywords are the engine's own. `notice` moved to
        `fr.document(..., notice=...)`: passing it raises an `AuthorError`.
        """
        if notice is not None:
            msg = "the notice moved to fr.document(..., notice=...)"
            raise AuthorError(msg)
        self._engine.project(
            title=title,
            number=number,
            customer=customer,
            revision=revision,
            author=author,
            version=version,
        )

    def revision(  # noqa: PLR0913 -- the engine's own history keywords, passed through [public keyword API kept, decision 0444]
        self: "Design",
        revision: int,
        *,
        date: str,
        text: str,
        created: str,
        checked: str = "",
        approved: str = "",
        version: int | None = None,
    ) -> None:
        """Write one history entry of the project.

        Does not rename or default a field; a unit's child design refuses it.
        """
        if not isinstance(self._engine, EngineDesign):
            msg = "a unit's history is @fr.unit(history=), not d.revision"
            raise AuthorError(msg)
        self._engine.revision(
            revision,
            date=date,
            text=text,
            created=created,
            checked=checked,
            approved=approved,
            version=version,
        )
