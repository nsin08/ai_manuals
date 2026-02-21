from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class CatalogEntry:
    doc_id: str
    title: str
    filename: str
    status: str
    notes: str = ""


@dataclass(frozen=True)
class GoldenQuestion:
    question_id: str
    doc: str
    intent: str
    evidence: str
    question: str
    question_type: str = "straightforward"
    difficulty: str = "easy"
    rag_mode: str = "text"
    turn_count: int = 1
    expected_keywords: list[str] = field(default_factory=list)
    min_keyword_hits: int = 1


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def is_valid(self) -> bool:
        return not self.errors



def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"YAML file not found: {path}")

    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict):
        raise ValueError(f"Top-level YAML object must be a mapping: {path}")

    return data



def load_catalog(path: Path) -> list[CatalogEntry]:
    data = _load_yaml(path)
    rows = data.get("documents", [])

    if not isinstance(rows, list):
        raise ValueError("`documents` must be a list in document catalog")

    entries: list[CatalogEntry] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Each document entry must be a mapping")

        entries.append(
            CatalogEntry(
                doc_id=str(row.get("doc_id", "")).strip(),
                title=str(row.get("title", "")).strip(),
                filename=str(row.get("filename", "")).strip(),
                status=str(row.get("status", "")).strip().lower(),
                notes=str(row.get("notes", "")).strip(),
            )
        )

    return entries



def load_golden_questions(path: Path) -> tuple[set[str], list[GoldenQuestion]]:
    data = _load_yaml(path)
    meta = data.get("meta", {})
    docs = meta.get("docs", {})
    rows = data.get("questions", [])

    if not isinstance(docs, dict):
        raise ValueError("`meta.docs` must be a mapping in golden questions")
    if not isinstance(rows, list):
        raise ValueError("`questions` must be a list in golden questions")

    questions: list[GoldenQuestion] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Each golden question entry must be a mapping")

        expected_keywords_raw = row.get("expected_keywords") or []
        if not isinstance(expected_keywords_raw, list):
            expected_keywords_raw = [expected_keywords_raw]

        questions.append(
            GoldenQuestion(
                question_id=str(row.get("id", "")).strip(),
                doc=str(row.get("doc", "")).strip(),
                intent=str(row.get("intent", "")).strip(),
                evidence=str(row.get("evidence", "")).strip(),
                question=str(row.get("question", "")).strip(),
                question_type=str(row.get("question_type", "straightforward")).strip() or "straightforward",
                difficulty=str(row.get("difficulty", "easy")).strip() or "easy",
                rag_mode=str(row.get("rag_mode", row.get("evidence", "text"))).strip() or "text",
                turn_count=max(1, int(row.get("turn_count", 1) or 1)),
                expected_keywords=[str(item).strip() for item in expected_keywords_raw if str(item).strip()],
                min_keyword_hits=max(1, int(row.get("min_keyword_hits", 1) or 1)),
            )
        )

    return set(docs.keys()), questions



def validate_contracts(
    catalog_path: Path,
    golden_path: Path,
    strict_files: bool = False,
) -> ValidationResult:
    result = ValidationResult()

    catalog = load_catalog(catalog_path)
    golden_doc_ids, questions = load_golden_questions(golden_path)

    seen: set[str] = set()
    by_doc: dict[str, CatalogEntry] = {}

    for entry in catalog:
        if not entry.doc_id:
            result.errors.append("Catalog entry has empty doc_id")
            continue

        if entry.doc_id in seen:
            result.errors.append(f"Duplicate doc_id in catalog: {entry.doc_id}")
            continue

        seen.add(entry.doc_id)
        by_doc[entry.doc_id] = entry

        if entry.status not in {"present", "missing"}:
            result.errors.append(
                f"Catalog status for {entry.doc_id} must be 'present' or 'missing'"
            )

        if entry.status == "present":
            if not entry.filename:
                result.errors.append(f"Catalog entry {entry.doc_id} is present but filename is empty")
            else:
                file_path = catalog_path.parent / entry.filename
                if not file_path.exists():
                    result.errors.append(
                        f"Catalog file does not exist for {entry.doc_id}: {entry.filename}"
                    )

        if entry.status == "missing":
            msg = f"Catalog marks missing document: {entry.doc_id}"
            if strict_files:
                result.errors.append(msg)
            else:
                result.warnings.append(msg)

    for doc_id in sorted(golden_doc_ids):
        if doc_id not in by_doc:
            result.errors.append(f"Golden meta doc id missing from catalog: {doc_id}")

    for q in questions:
        if not q.question_id:
            result.errors.append("Golden question has empty id")
        if not q.question:
            result.errors.append(f"Golden question {q.question_id or '<unknown>'} has empty question")
        if q.doc != "multiple" and q.doc not in by_doc:
            result.errors.append(
                f"Golden question {q.question_id} references unknown doc id: {q.doc}"
            )

    return result
