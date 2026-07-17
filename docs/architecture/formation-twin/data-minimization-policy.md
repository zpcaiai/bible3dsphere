# Data-minimization policy

Canonical events contain only explicit user reports, observable source facts, and the least metadata needed for provenance. Complete journal, prayer, transcript, confession, crisis, medical, legal, pastoral, browsing, contact, and location body is forbidden.

The model recursively rejects sensitive keys. Adapter allowlists run before normalization. Provenance records accepted field names and discarded field names with `discarded_values_stored=false`. Domain-event payloads contain only event ID, type, source, version, and whether an encrypted reference exists.
