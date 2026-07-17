# Journal encryption

Journal and check-in body is encrypted using AES-256-GCM with a random 96-bit nonce. Associated data binds ciphertext to the owner email and content record ID. The store keeps ciphertext, nonce, SHA-256 integrity reference, key version, retention policy, and processing preference.

Production uses `FORMATION_TWIN_ENCRYPTION_KEY`. Rotation is tracked by key version; old key material must remain available until content is re-encrypted. Deletion overwrites the ciphertext and marks the content deleted before the related event is excluded from active queries. Purged body is not restorable.
