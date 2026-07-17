# Model Evaluation

Models are evaluated by fixed provider, model identifier, version or immutable deployment reference, configuration, prompt version, dataset version, and runner version. The implicit version `latest` is forbidden.

Required checks include task usefulness, unsupported certainty, hallucinated sources, theological overclaim, medical or crisis boundary violations, privacy leakage, cross-tenant access, prompt injection, and safe degradation. A model change is a release change even when the API schema is unchanged.

Batch 10 includes the registry and offline safety runner; it does not certify any external model for general production use. Provider-specific live evaluations remain an environment gate.
