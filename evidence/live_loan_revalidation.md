# Live loan revalidation after product-selection guard — 2026-10-07

Separate capture: `live_loan_revalidation.json`. Original nine-turn evidence remains intact. Four new real OpenAI text turns against the isolated test Backend on port 8001, version 3, no retry or model override.

| Requirement | Observation | Result |
| --- | --- | --- |
| Wait for product choice | After down payment ¥5,000,000 and 35 years, AI asked which published product to use; no successful calculation or monthly amount was returned before selection | PASS |
| Actual Flat35 calculation after explicit selection | Model called `calculate_mortgage` with an ID absent from this published snapshot; Backend correctly returned `RATE_NOT_FOUND` | FAIL — intended calculator card was not produced |
| Reference validity grounded in real tool result | Third answer said both products were valid until the end of November; actual `get_mortgage_rates` output says `2026-10-31` | FAIL — answer gave the wrong expiry |
| Explain tool error honestly | Final answer incorrectly said published Flat35 details were unavailable, although the prior actual rate tool result contains that product | FAIL — inaccurate recovery explanation |
| Session isolation | All responses pinned to version 3; four customer/assistant turns and real tool events persisted; test session ended | PASS |

The Backend guard addressed the premature calculation observed in the original capture. It did not resolve the conversation's loss of prior rate-tool IDs/details: the final turn called the calculator without retrieving rates again and used a nonexistent ID. Source inspection shows that successive text requests construct conversation history from message text only, discarding the prior tool-output structure. That supports a targeted correction that supplies the current validated rate result, including exact IDs and dates, to each relevant loan request. This capture alone does not certify the completed loan flow.
