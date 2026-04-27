from pydantic import BaseModel, ConfigDict
from typing import Any, Optional, List, Dict


class JobSubmitResponse(BaseModel):
    job_id: str
    status: str
    species: str
    assemblies_queued: int
    databases_to_run: List[str]
    message: str


class AssemblyResultItem(BaseModel):
    assembly: str
    match: str
    coverage: float
    confidence: str


class JobStatusResponse(BaseModel):
    """The payload sent to the polling JavaScript."""
    status: str
    data: Optional[List[AssemblyResultItem]] = None
    error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
