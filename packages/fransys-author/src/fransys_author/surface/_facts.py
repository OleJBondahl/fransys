"""Facts: `project`, `revision`, `rating` and `operating` (EA-COVERAGE P2)."""

from typing import TYPE_CHECKING

from fransys_author.design import Design as EngineDesign
from fransys_author.errors import AuthorError
from fransys_author.surface._device import _one_maker, part_mpn

if TYPE_CHECKING:
    from fransys_author.surface._device import Device
    from fransys_author.surface.design import Design
    from fransys_model.vocab import Operating, Rating


class Facts:
    """The fact calls of the surface `Design`."""

    def project(  # noqa: PLR0913 -- the engine's own title-block keywords, passed through
        self: Design,
        *,
        title: str,
        number: str,
        customer: str,
        revision: int,
        author: str,
        notice: str = "",
        version: int = 1,
    ) -> None:
        """State the title-block facts of the project, at most one per model.

        Does not rename or default a field: the keywords are the engine's own.
        """
        self._engine.project(
            title=title,
            number=number,
            customer=customer,
            revision=revision,
            author=author,
            notice=notice,
            version=version,
        )

    def revision(  # noqa: PLR0913 -- the engine's own history keywords, passed through
        self: Design,
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

    def rating(
        self: Design, part: str | type[Device], function: str | None = None
    ) -> Rating | None:
        """Read the rating of a part, or of one of its function templates.

        Does not take a `(manufacturer, mpn)` pair: an MPN made by two makers raises.
        """
        mpn = part_mpn(part)
        _one_maker(self, mpn)
        return self._engine.rating(mpn, function)

    def operating(self: Design, part: str | type[Device], function: str) -> Operating | None:
        """Read the operating envelope of one function template of a part.

        Does not take a `(manufacturer, mpn)` pair: an MPN made by two makers raises.
        """
        mpn = part_mpn(part)
        _one_maker(self, mpn)
        return self._engine.operating(mpn, function)
