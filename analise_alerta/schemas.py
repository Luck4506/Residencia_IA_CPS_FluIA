from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RagChunk:
    chunk_id: str
    source: str
    content: str
    score: float
    section: Optional[str] = None


@dataclass
class AlertAnalysisInput:
    alert_id: str
    alert_type: str
    alert_summary: str
    user_profile: dict = field(default_factory=dict)
    user_goals: dict = field(default_factory=dict)
    usage_data: dict = field(default_factory=dict)
    rag_status: str = "empty"  # "ok" | "empty" | "low_relevance" | "error"
    rag_chunks: List[RagChunk] = field(default_factory=list)


@dataclass
class AlertAnalysisOutput:
    alert_id: str
    is_valid: bool
    importance: str  # "baixa" | "media" | "alta" | "critica"
    conclusion: str
    justification: str
    supporting_data: List[str]
    citations: List[dict]
    limitations: List[str]