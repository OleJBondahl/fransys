"""The overview engine's name; its version is the schematic engine's, one for the package."""

from fransys_layout._engine_version import ENGINE_VERSION

ENGINE_NAME = "overview"
PACK_SHAPE = (1050, 920)  # the page canvas at 1600 by 1000 px: the shape pieces are packed to

__all__ = ("ENGINE_NAME", "ENGINE_VERSION", "PACK_SHAPE")
