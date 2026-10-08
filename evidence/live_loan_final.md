# Final live loan acceptance after rate-context correction — 2026-10-07

PASS for the requested sequential loan calculation. Separate evidence: `live_loan_final.json`; the initial nine-turn capture and first four-turn revalidation remain unchanged. Exactly four new actual OpenAI text answers against the isolated test Backend on port 8001, version 3; no upstream error, retry or model override.

| Check | Actual observation | Result |
| --- | --- | --- |
| Missing-input collection | Asked for down payment, years and product; received ¥5,000,000 and 35 years | PASS |
| Product-choice gate | Asked which product to use after the years answer; no successful calculator call or monthly amount before explicit selection | PASS |
| Explicit Flat35 selection | Customer selected registered Flat35, new group-credit-life 21–35 years; actual `calculate_mortgage` succeeded using the published document-local ID | PASS |
| Price / principal / selected rate | ¥76,900,000 price, ¥5,000,000 down payment, ¥71,900,000 principal, 35 years, 3.94% for financing over 90% | PASS |
| Monthly payment | Real tool output and final answer: ¥315,773; independent equal-payment formula agrees | PASS |
| Every-answer date review | First answer correctly states October 1 basis / October 31 expiry; subsequent collection answers do not invent dates; final answer correctly states October 1 basis. Actual calculator remains valid October 1–31. No November expiry claim appears | PASS |
| Source / conditions / disclaimer | Actual calculator card contains loan-product conditions in `product_notes` / `notes`, cited rate and price documents, 9割超 rate basis, and the complete required approximation disclaimer | PASS |
| Error recovery / persistence | No invalid ID or missing-product explanation; actual messages and controlled rate-tool/calculation events persisted at version 3; test session ended | PASS |

The calculator returned the correct rate and the final answer explicitly called it `3.94%（融資率9割超の参考金利）`. During product collection, the AI listed the base published Flat35 reference of 3.83% without repeating its 9割以下 qualifier. That wording remains a presentation caveat; the selected-product calculation and final answer used the correct 9割超 rate.

The original harness required a nonempty `conditions` array, but the actual SDK-derived workbook represents product conditions in the source-backed notes. The checker was corrected offline to recognize those existing notes; no extra AI call was made. This correction does not modify any observed response, tool result, source document or previous evidence.
