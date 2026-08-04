"""Responses module."""

from typing import Any

import orjson
from starlette.responses import JSONResponse


# Classes --------------------------------------------------------------------------------------------------------------
class KaptiveORJSONResponse(JSONResponse):
    """A custom JSONResponse that specifically serializes NumPy arrays and dataclasses.

    It is extremely fast using orjson's native C hooks.
    """

    media_type = "application/json"

    def render(self, content: Any) -> bytes:  # noqa: ANN401
        """Render response content."""
        return orjson.dumps(content, option=orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_SERIALIZE_DATACLASS)
