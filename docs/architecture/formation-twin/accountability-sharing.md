# Accountability Sharing

Support roles are labels, not permissions. Adding a spouse, pastor, mentor,
friend or professional grants no access to the Formation Twin. The contact table
stores a display alias and an external reference rather than duplicating a full
contact profile.

The default action is `DRAFT_MESSAGE_ONLY`. A draft is not sent. Time-limited
sharing requires a selected contact, explicit fields, purpose, expiry and current
user confirmation; requested fields must be a subset of the contact's existing
authorization. Revocation immediately cancels pending access.

Batch 7 records `READY_FOR_USER_SEND` but does not claim an external message was
delivered because no delivery adapter is wired. Contact failure never fans out
to additional people. Event payloads exclude aliases, message text, cycle names,
behavior details and third-party identity.
