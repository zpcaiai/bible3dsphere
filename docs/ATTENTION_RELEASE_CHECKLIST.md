# Attention Stewardship Release Checklist

This checklist is privacy-first. Do not paste user prayer, review, ledger notes,
diagnosis raw output, challenge reflection, or share payload into release notes.

## Required Automated Checks

- `python3 -m py_compile backend/attention_integration.py backend/routers/attention.py backend/main.py`
- `PYTHONPATH=backend .venv/bin/python backend/scripts/attention/audit_attention_security.py`
- `PYTHONPATH=backend .venv/bin/python backend/scripts/attention/generate_attention_release_report.py`
- Frontend: `npm run attention:audit:logs`
- Frontend: `npm run test -- src/test/attention.test.js src/test/attentionApi.contract.test.js src/test/AttentionPage.test.jsx src/test/attentionIntegration.test.ts`
- Frontend: `npm run build`

## Manual QA

- `/attention` dashboard loads with covenant, focus, ledger, review, diagnosis, warfare, weekly, accountability, groups, and privacy summaries.
- `/attention/privacy` defaults to `status_only` and hides sensitive categories.
- `/attention/accountability` only shares selected summaries and can revoke a share.
- `/attention/groups` challenge participants are not ranked.
- `/attention/admin` rejects ordinary users.
- Admin dashboard displays aggregate counts only, not raw prayer, note, review, diagnosis, challenge reflection, or share payload.
- Low score and captured-attention copy does not shame the user.
- AI provider missing still uses fallback behavior.
- Demo seed scripts are not enabled in production.
