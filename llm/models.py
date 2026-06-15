from dataclasses import dataclass
from enum import Enum


class TriageResult(str, Enum):
    RESPOND = "respond"   # Resposta completa
    BRIEF   = "brief"     # Resposta curta / casual
    QUIET   = "quiet"     # Não responder


@dataclass
class BrainDecision:
    triage: TriageResult = TriageResult.QUIET
    answer: str = ""
    needs_search: bool = False
    search_query: str = ""


# ── Legado: mantido para não quebrar imports que ainda existam ──
class DecisionType(str, Enum):
    ANSWER       = "answer"
    IGNORE       = "ignore"
    SUGGEST_RULE = "suggest_rule"
    ESCALATE     = "escalate"


@dataclass
class LLMDecision:
    intent: DecisionType = DecisionType.IGNORE
    answer: str = ""
    rule_name: str | None = None
    confidence: float = 0.0
    reason: str = ""
    needs_search: bool = False
    search_query: str = ""

    def public_text(self) -> str:
        return (self.answer or "").strip()
