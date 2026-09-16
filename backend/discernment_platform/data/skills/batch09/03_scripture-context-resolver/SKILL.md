---
id: scripture-context-resolver
name: 经文上下文解析
version: 0.9.0
batch: 9
type: theology-knowledge-runtime-skill
---

# Purpose

获取段落、全书、文体、说话者、受众和结构位置。

# Inputs

- normalized theology query
- source registry
- rights policy
- scripture and theology graph
- tradition scope
- requested depth
- human review level

# Outputs

Structured output containing:
- retrieved and filtered evidence
- source and edition metadata
- context and original-language analysis
- doctrinal tier and tradition scope
- citations
- contradictions and qualifications
- generated claims
- evidence graph trace
- limitations and review status

# Processing Contract

1. Resolve verse, paragraph, book and canonical context.
2. Separate textual observation from theological synthesis.
3. Require context for lexical claims.
4. Preserve textual variants and translation options.
5. Use primary and authoritative sources where possible.
6. Label doctrine tier and denominational scope.
7. Verify quotations and locators.
8. Filter sources by rights status.
9. Retrieve counter-evidence and major alternative readings.
10. Trace every generated claim to evidence nodes.

# Guardrails

- No proof-texting.
- No Strong-number-only word studies.
- No fabricated quotation or page number.
- No denomination-specific claim presented as universal without label.
- No new revelation claims.
- No copyright leakage.
- No unsupported certainty.
- No abusive scripture application.

# Failure Handling

Return:
- REFERENCE_AMBIGUOUS
- CONTEXT_INSUFFICIENT
- SOURCE_NOT_LICENSED
- QUOTATION_UNVERIFIED
- DOCTRINAL_SCOPE_REQUIRED
- INSUFFICIENT_EVIDENCE
- HUMAN_REVIEW_REQUIRED
- RIGHTS_BLOCKED

# Acceptance Tests

- Every major claim has source support.
- Original-language claims include context and grammar.
- Quotes include source and locator.
- Tradition differences are labeled.
- Misuse risks are surfaced.
