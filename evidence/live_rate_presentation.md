# Single-turn reference-rate presentation review — 2026-10-07

Targeted Flat35 qualifier correction: PASS. Full answer grounding: REQUIRES CORRECTION. Exactly one real OpenAI customer turn against the isolated test Backend on port 8001, version 3; no calculator invocation, upstream error, retry or model override. All earlier captures remain intact.

Question: `頭金500万円、35年を希望。参考金利商品の条件を教えてください。まだ商品は選んでいません。`

The answer correctly paired Flat35 **3.83% with financing 9割以下** and **3.94% with 9割超**; it stated the correct October 1 basis / October 31 expiry, described reference conditions and asked for a product selection before calculation. Source references and session version were preserved. The real test session ended.

Manual review also found an unsupported additional fact in the separate MUFG section: `融資率は9割以下`. The actual published MUFG row and recorded research source do not establish a maximum 90% LTV condition. The 90% bands belong to the Flat35 row; the answer applied a 90%-only statement to the MUFG product too. Therefore the narrow Flat35 qualifier checks pass, but this complete answer cannot be accepted as fully grounded in the published source.

Sanitized actual answer, real persisted messages/rate-tool results and structured checks are preserved in `live_rate_presentation.json`. No further AI call was made after this finding.
