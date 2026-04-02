from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Artifact:
    path: Path
    header: dict
    body: str
    headings: list[str]
    trace_units: list[dict]
    relation_edges: list[dict]

    @property
    def artifact_id(self) -> str:
        return self.header["artifact_id"]

    @property
    def artifact_type(self) -> str:
        return self.header["artifact_type"]

    @property
    def title(self) -> str:
        return self.header["title"]

    @property
    def status(self) -> str:
        return self.header["status"]

    @property
    def scope(self) -> dict:
        return self.header["scope"]
