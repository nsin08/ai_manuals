from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Citation:
    doc_id: str
    page: int
    section_path: str | None = None
    figure_id: str | None = None
    table_id: str | None = None


@dataclass(frozen=True)
class Answer:
    text: str
    citations: list[Citation] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    filename: str


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    content_type: str
    page_start: int
    page_end: int
    content_text: str
    section_path: str | None = None
    figure_id: str | None = None
    table_id: str | None = None
    caption: str | None = None
    asset_ref: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
