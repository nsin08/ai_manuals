"""Unit tests for _detect_intent() — Phase 2 procedure intent extension."""
from __future__ import annotations

import pytest

from packages.application.use_cases.search_evidence import _detect_intent


# ── table intent ─────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "query",
    [
        "parameter table for the drive",
        "what are the torque specifications",
        "show me the specification sheet",
        "clearance tolerance values in mm",
        "schedule interval for maintenance",
        "fault code list",
    ],
)
def test_table_intent_detection(query: str) -> None:
    assert _detect_intent(query) == "table"


# ── diagram intent ────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "query",
    [
        "wiring diagram for motor terminals",
        "block diagram of control section",
        "show me the schematic",
        "connector pin layout",
    ],
)
def test_diagram_intent_detection(query: str) -> None:
    assert _detect_intent(query) == "diagram"


# ── procedure intent ──────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "query",
    [
        "how to install the pump unit",
        "what are the commissioning steps",
        "configure the speed controller",
        "wiring steps for motor startup",
        "operation sequence for startup",
        "setup procedure for the drive",
    ],
)
def test_procedure_intent_detection(query: str) -> None:
    assert _detect_intent(query) == "procedure", (
        f"Expected 'procedure' for query: {query!r}, got {_detect_intent(query)!r}"
    )


# ── general intent (no keywords) ─────────────────────────────────────────────
@pytest.mark.parametrize(
    "query",
    [
        "tell me about the product",
        "what does this device do",
        "overview of the system",
    ],
)
def test_general_intent_detection(query: str) -> None:
    assert _detect_intent(query) == "general"


# ── priority: table wins over procedure when score is equal-or-higher ─────────
def test_table_beats_procedure_when_tied() -> None:
    # "parameter schedule" → 2 table hits ("parameter", "schedule"), 0 procedure
    assert _detect_intent("parameter schedule table") == "table"


# ── priority: diagram beats procedure when score is higher ───────────────────
def test_diagram_beats_procedure_when_higher() -> None:
    # "wiring diagram schematic" → 3 diagram hits, 1 procedure (wiring)
    assert _detect_intent("wiring diagram schematic") == "diagram"


# ── priority: procedure wins when it has more hits than diagram ───────────────
def test_procedure_wins_when_more_hits_than_diagram() -> None:
    # "wiring steps commissioning setup" → diagram=1(wiring), procedure=4 → procedure
    assert _detect_intent("wiring steps commissioning setup") == "procedure"
