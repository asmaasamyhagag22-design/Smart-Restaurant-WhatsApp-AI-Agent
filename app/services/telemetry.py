"""Lightweight telemetry — Prometheus counters per turn (docs §12)."""
from __future__ import annotations

from prometheus_client import Counter, Histogram

TURNS = Counter("agent_turns_total", "Conversation turns", ["intent", "escalated"])
LATENCY = Histogram("agent_turn_seconds", "End-to-end turn latency (s)")


def record_turn(intent: str | None, escalated: bool) -> None:
    TURNS.labels(intent=intent or "none", escalated=str(escalated).lower()).inc()
