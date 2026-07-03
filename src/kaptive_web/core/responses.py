import orjson
from starlette.responses import JSONResponse
from typing import Any

class KaptiveORJSONResponse(JSONResponse):
    """
    A custom JSONResponse that specifically serializes NumPy arrays and dataclasses 
    extremely fast using orjson's native C hooks.
    """
    media_type = "application/json"

    def render(self, content: Any) -> bytes:
        return orjson.dumps(
            content, 
            option=orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_SERIALIZE_DATACLASS
        )
