from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class RightsStatus(str, Enum):
    PUBLIC_DOMAIN = "public_domain"
    OPEN_LICENSE = "open_license"
    LICENSED_INTERNAL = "licensed_internal"
    USER_OWNED = "user_owned"
    QUOTATION_ONLY = "quotation_only"
    METADATA_ONLY = "metadata_only"
    PROHIBITED_FOR_EMBEDDING = "prohibited_for_embedding"
    PROHIBITED_FOR_GENERATION = "prohibited_for_generation"


class QualityTier(str, Enum):
    Q0 = "Q0"
    Q1 = "Q1"
    Q2 = "Q2"
    Q3 = "Q3"
    Q4 = "Q4"


class DoctrineTier(str, Enum):
    D1 = "D1"
    D2 = "D2"
    D3 = "D3"


class SourceDocument(BaseModel):
    source_id: str
    title: str
    source_type: str
    language: str
    rights_status: RightsStatus
    version: str
    author: list[str] = Field(default_factory=list)
    edition: str = ""
    publisher: str = ""
    year: str = ""
    quality_tier: QualityTier = QualityTier.Q1
    limitations: list[str] = Field(default_factory=list)


class CitationRecord(BaseModel):
    citation_id: str
    source_id: str
    locator: str
    quote_text: str
    extraction_method: str = "manual"
    verification_status: str = "unverified"
    rights_status: str = ""
    limitations: list[str] = Field(default_factory=list)


class RagQuery(BaseModel):
    query_id: str
    question: str
    intent: str
    allowed_rights: list[str]
    required_source_types: list[str]
    scripture_refs: list[str] = Field(default_factory=list)
    tradition_scope: list[str] = Field(default_factory=list)
    depth: str = "standard"
    human_review_level: str = "R0"


class EvidenceGraph(BaseModel):
    graph_id: str
    query_id: str
    nodes: list[dict]
    edges: list[dict]
    generated_statements: list[dict]
    retrieval_metadata: dict = Field(default_factory=dict)
    model_metadata: dict = Field(default_factory=dict)
    human_reviews: list[dict] = Field(default_factory=list)
    quality_gates: list[dict] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
