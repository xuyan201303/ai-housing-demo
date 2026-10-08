# Voice mortgage form synchronization — 2026-10-07

Source inspection found a visible mismatch risk in the existing Customer loan panel: an external voice calculation only updated the result card, while the form retained its initial product (MUFG), down payment and term. A successful Flat35 voice calculation could therefore appear below an unrelated selected product.

The narrow Frontend correction applies the actual Backend result's `rate_id`, `down_payment` and `years` to the form. Customer passes the existing persisted Tool `event_id`; Mortgage applies each event once, so normal two-second polling does not reset subsequent customer form edits. The calculator, rate master, business confirmation, SDK, models and voice transport are unchanged.

Changed files for this form correction: `frontend/src/Mortgage.tsx`, `frontend/src/Customer.tsx`. TypeScript / Vite build passed after the final edit (36 modules). This form correction does not change Backend code or require SDK reinstallation. The separate first-rate-description prompt correction is reviewed in `current_rate_conditions_review.md`.

The first UI edit was hot-reloaded during the partial continuous voice run at 10:49:35 JST. That Session ended at 10:49:39 with `REALTIME_SIDEBAND`; its last received response lacked playback-stop/final-idle evidence. The timing coincides with the update, but the sideband's direct exception subtype was not captured, so no specific network cause is inferred. The partial run remains failed/incomplete. The complete revalidation uses frozen application code and records hashes before/after; no Frontend edits occur during that run.

Actual same-Session Chrome verification is recorded with the continuous synthetic-input / real-Realtime business result. Its screenshot and result should establish the selected Flat35 product, down payment ¥5,000,000, term 35 years, and Backend result ¥315,773 at 3.94%. This is a UI consistency fix, not physical microphone or normal-Demo acceptance.
