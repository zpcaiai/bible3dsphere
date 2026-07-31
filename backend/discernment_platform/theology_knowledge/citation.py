from __future__ import annotations

from .models import CitationRecord, SourceDocument


def verify_citation(citation: CitationRecord, source: SourceDocument) -> dict:
    issues = []

    if citation.source_id != source.source_id:
        issues.append("source_mismatch")
    if not citation.locator.strip():
        issues.append("locator_missing")
    if not citation.quote_text.strip():
        issues.append("quote_missing")
    if citation.verification_status == "unverified":
        issues.append("not_verified")
    if not source.edition and source.source_type not in {"user_document", "article"}:
        issues.append("edition_missing")

    return {
        "valid": not issues,
        "issues": issues,
        "source_title": source.title,
        "source_version": source.version,
    }
