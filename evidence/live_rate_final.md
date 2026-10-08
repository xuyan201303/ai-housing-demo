# Final one-turn per-product rate-conditions review — 2026-10-07

PASS. Exactly one actual OpenAI customer turn against the isolated test Backend on port 8001, version 3, with no product selection, calculator invocation, upstream error, retry or model change. Previous failed and successful evidence remains intact.

Question: `頭金500万円、35年を希望。参考金利商品の条件を教えてください。まだ商品は選んでいません。`

The complete answer was manually checked against the actual persisted `get_mortgage_rates` rows:

| Answer statement | Actual published/tool evidence | Result |
| --- | --- | --- |
| MUFG variable reference 1.195%, 2–40 years, ¥5,000,000–¥300,000,000 | Matches the MUFG row | PASS |
| MUFG age, employment, salary-transfer and bank screening conditions | Matches source-backed product notes | PASS |
| MUFG LTV categories/maximum unregistered | Explicitly stated as unregistered; no Flat35 90% restriction transferred | PASS |
| Flat35 fixed reference 3.83% at 9割以下, 3.94% at 9割超 | Both rates paired with the correct Flat35-only bands | PASS |
| Flat35 21–35 years, ¥1,000,000–¥120,000,000, financing maximum 100% | Matches year/amount boundaries and `max_loan_to_value=1` | PASS |
| Basis / expiry | Correctly stated 2026-10-01–2026-10-31; no November expiry | PASS |
| Input interpretation | ¥5,000,000 down payment / ¥76,900,000 price → ¥71,900,000 principal, approximately 93.5% financing, hence the Flat35 over-90% reference 3.94% | PASS |
| Calculation gate | Asked customer to select a product before a payment calculation; no `calculate_mortgage` tool event or monthly amount returned | PASS |
| Persistence / source / version | Actual user/assistant text and controlled source-tool events persisted, source reference supplied, version pinned to 3; test session ended | PASS |

The earlier unsupported MUFG `融資率は9割以下` statement is absent. The correction addresses the complete condition presentation observed in this single turn; selected-product monthly calculation is separately recorded in `live_loan_final.json`. All sanitized questions, actual answer, tool results and checks for this turn are preserved in `live_rate_final.json`.
