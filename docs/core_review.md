# Core workflow independent review

Review date: 2026-10-07 (Asia/Tokyo).

The review inspected the SDK adapter, upload/confirmation/publication services, immutable SQLite versions, session authorization, controlled tool reads, API access controls and corresponding frontend consumers. Reproductions used the final SANZO-generated business PDFs, the installed SDK public API and isolated temporary SQLite databases. No live Demo database was changed, and no OpenAI request was made.

## Resolved findings

1. **A later document could extend the deadline of an expired price source.**
   The original publication merge overwrote `property.valid_until` with the last selected document's date. An expired overview plus a future-dated equipment deadline allowed a new session to retrieve the expired overview's price. Original reproduction evidence: `evidence/documents/core_review_reproduction.json`.
   The publication service now checks every relevant document's deadline, rejects an expired source and records `document_validity`. The snapshot deadline is the earliest source deadline. Regression tests also advance the clock after publication: existing sessions lose fact/tool access, new sessions fail to start, and a staff call remains available.

2. **Malformed reviewed property types could reach the customer view.**
   `reviewed.property.property_name` accepted a JSON object, which could be confirmed, published and returned to a session. The frontend expects a string and renders the property name directly. Original reproduction evidence: `evidence/documents/core_review_shape.json`.
   Confirmation now rejects non-string scalar fields, malformed equipment/surroundings arrays and invalid numeric fields. Failed confirmation leaves the document parsed, preserves the original SDK raw result and creates no confirmation event.

3. **Future source dates are blocked.**
   Publication now rejects a document whose information-effective date is in the future. The regression verifies that no version is created.

## Verification

```text
backend/.venv/bin/python -m pytest backend/tests/test_review_regressions.py -q
9 passed in 0.34s
```

The regressions are in `backend/tests/test_review_regressions.py`. They cover expired-source publication, transactional rejection, minimum validity, existing/new session expiry, staff handoff after expiry, future-effective publication, six malformed property shapes and unchanged SDK raw evidence after rejected confirmation.

The reviewed source retains raw SDK results separately from normalized and human-confirmed data. Publication accepts only confirmed/published documents; sessions are pinned to immutable publication versions. Uploads use UUID storage names, extension/signature/size checks and SDK limits. Admin and Staff APIs use independent password-based access checks; session APIs verify random session tokens. API errors omit internal exception text and system paths.

This is a focused code review and regression result. It does not establish live OpenAI text-answer behavior, microphone/WebRTC behavior, production security, physical Tablet behavior or semantic acceptance of every possible uploaded document. Live AI/voice acceptance requires separately recorded runtime evidence.
