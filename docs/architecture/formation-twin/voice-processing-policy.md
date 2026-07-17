# Voice-processing policy

Voice recording is user-triggered and separately consented. The browser or selected file sends audio to the existing server-side transcription path. The server caps size, accepts audio MIME types only, sends bytes to Deepgram, stores only the encrypted transcript, and records `audio_deleted_at` in the same transaction. Audio bytes are never persisted by Formation Twin.

The transcript remains `USER_REVIEW_REQUIRED`. The user may edit or delete it. Only explicit confirmation creates a canonical `VOICE_JOURNAL` event; crisis screening runs before that event is accepted.
