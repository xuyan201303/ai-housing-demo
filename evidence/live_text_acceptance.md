# Real OpenAI text acceptance — 2026-10-07

Target: explicit isolated `demo_mode=test` Backend on port 8001, existing SDK-parsed / confirmed / published version 3. Four new isolated sessions, nine customer turns: eight real OpenAI text responses and one Backend policy response. No document upload, confirmation or publication was performed by this run. The normal Demo database was not used.

Raw sanitized evidence: `live_text_acceptance.json`; repeatable bounded harness: `../scripts/live_text_acceptance.py`. Session tokens, Basic-auth credentials and API keys are excluded. No upstream retry, model change or upstream error occurred.

| Check | Actual observation | Review |
| --- | --- | --- |
| Price / areas | No.15: ¥76,900,000, land 139.85m², building 93.25m²; source document cited | PASS |
| Equipment | Panasonic front-open dishwasher, solar 3.0kW, two air conditioners; source document cited | PASS |
| Station scope | Explicitly described 920–950m / maximum 12 minutes as four-sale-lot scope; No.15 exact distance and time unknown | PASS |
| Scenario G: unlisted fact | EV 6kW standard charger installation was not asserted; stated document absence and referred to staff | PASS |
| Scenario C: collected inputs | Requested down payment and years; received ¥5,000,000 and 35 years | PASS |
| Scenario C: selected Flat35 | After explicit customer product selection, called real `calculate_mortgage`; price ¥76,900,000, principal ¥71,900,000, 35 years, annual 3.94%, ¥315,773/month | PASS |
| Independent monthly comparison | Standard positive-power equal-payment formula and half-up yen rounding produced ¥315,773; matches the real tool result | PASS |
| Loan source / conditions | Tool result includes 9割超 basis, October 1–31 reference applicability, conditions, source references, required approximation disclaimer and excluded charges | PASS |
| Scenario D | Deterministic Backend policy refused guaranteed loan approval; created actual `call_staff` record | PASS |
| Staff record/readback | Staff-authenticated list contained that record; accepted and completed states were read back from the customer session | PASS |
| Persistence / version | Actual customer and assistant messages, tool events, staff calls persisted; all answers pinned to version 3 | PASS |
| Product selection sequence | At the years-confirmation turn, before customer selected a product, the model called the calculator for both MUFG and Flat35 and answered both amounts | FINDING — verify correction before accepting the intended sequential product-confirmation flow |

The fixture facts were reviewed against `research/public_data.json` and the published SDK-derived snapshot. The observed calculator outputs and required disclaimer come from actual persisted Backend tool results, not AI arithmetic. The third loan turn returned real amounts, but it did so before the explicit Flat35 selection; the subsequent fourth loan turn correctly used the selected product. This finding is preserved rather than silently treating the whole sequence as passed.

The initial checker incorrectly compared a published document-local rate ID to the research-only ID. It was corrected offline to compare the published Flat35 product; no extra API request was made for that correction.

Voice, real microphone capture, WebRTC, browser subtitle synchronization and product UI layout are outside this text-only evidence record.
