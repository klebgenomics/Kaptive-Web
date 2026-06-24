import orjson
from fastapi.responses import ORJSONResponse
from typing import Any

class KaptiveORJSONResponse(ORJSONResponse):
    """
    A custom ORJSONResponse that specifically serializes NumPy arrays and dataclasses 
    extremely fast using orjson's native C hooks.
    """
    def render(self, content: Any) -> bytes:
        return orjson.dumps(
            content, 
            option=orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_SERIALIZE_DATACLASS
        )
