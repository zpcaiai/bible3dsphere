# Consent, privacy, and retention

- Authentication and ownership reuse the platform session identity; every query is scoped to the current email subject.
- Manual input defaults to `STORE_ONLY`. Users can explicitly choose future authorized analysis or exclusion from twin processing.
- Every module source has an independent pause/resume control and an explicit field boundary.
- Journal and transcript text uses AES-256-GCM with per-record nonces and subject/content associated data.
- Voice audio is transient and is not persisted after transcription. No life event is created until the user reviews and confirms the transcript.
- Delete operations purge ciphertext and mark the related canonical event deleted. Purged sensitive content is intentionally not restorable.
- Timeline controls allow per-event exclusion, reinclusion, and deletion.
- The owner-scoped export returns canonical metadata plus decrypted copies of the owner's check-ins, journals, and transcripts over the authenticated connection.
- `DELETE /api/v1/formation-twin/erase` requires an exact confirmation token and permanently removes all Formation Twin rows for the current user.
- Production should configure a dedicated 64-hex-character `FORMATION_TWIN_ENCRYPTION_KEY`; `JWT_SECRET_KEY` derivation exists for local/test compatibility and key separation.
