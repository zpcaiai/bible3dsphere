# Pattern Lifecycle

The lifecycle is explicit and audited:

`CANDIDATE → PENDING_USER_REVIEW → CONFIRMED_ACTIVE / CONFIRMED_CONTEXTUAL →
WEAKENING → DORMANT → RESOLVED → ARCHIVED`.

Candidates can instead become REJECTED. Incorrect source data can invalidate a
pattern. A changed Life Season can make it OUTDATED. Only the user can confirm a
pattern or mark it resolved. The system may propose review, weakening, dormancy,
or invalidation based on changed evidence, but cannot declare the user changed.

Every transition records previous status, new status, reason code, initiator,
and timestamp. Current snapshots exclude REJECTED, OUTDATED, INVALIDATED,
RESOLVED, and ARCHIVED records. Historical views can still show them. Reopening
a resolved or outdated pattern returns it to review; rejection remains protected
during rebuild and discovery cooldown.

All active patterns have `review_due_at`. No pattern remains permanently active
because a scheduled review was skipped.
