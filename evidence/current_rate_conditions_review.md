# Current reference-rate presentation review — 2026-10-07

**Current implementation review: PASS. No business-code change or new OpenAI call was needed for this audit.** The historical first-listing caveat in `live_loan_final.md` is retained, but a later real text capture, `live_rate_final.json` / `live_rate_final.md`, records the corrected complete per-product explanation. This is not a new normal-Demo or physical-microphone acceptance.

## Historical evidence and current code

| Evidence / implementation | Reviewed finding |
| --- | --- |
| `live_loan_final.{md,json}` | Four real text turns correctly used the selected Flat35 over-90% reference 3.94% and Backend ¥315,773/month, while the initial base-rate listing omitted the 9割以下 qualifier. This earlier wording caveat remains historical. |
| `live_rate_presentation.{md,json}` | Subsequent text check paired both Flat35 rates with their bands, but transferred an unsupported 9割以下 restriction to MUFG. This failure remains preserved. |
| `live_rate_final.{md,json}` | Later real one-turn text answer, isolated version 3, stated both Flat35 bands and rates together, all stated term/amount limits and October dates correctly, and MUFG's LTV categories/maximum as unregistered. It did not calculate a monthly amount before product selection. |
| `ai.py` shared `INSTRUCTIONS` | Explicitly requires `rate` with 9割以下 and `rate_over_90_percent` with 9割超 even in a preselection listing, and requires each product's own `loan_to_value_conditions`. It forbids transferring another product's 90% restriction. |
| `tools.py:get_mortgage_rates` | Returns date-valid rows from the Session's pinned publication, with product-local LTV explanatory data. It copies each row, so adding this field does not mutate the published snapshot. |
| `realtime.py` | Imports the same `INSTRUCTIONS`, exposes the same controlled `get_mortgage_rates`, and executes requested calculations through `ToolService(..., ai_requested=True)`. The Backend product-selection gate therefore also applies to recognized customer voice transcripts. |

The text service injects fresh pinned rate-tool data on each loan conversation turn. The Realtime service revalidates the pinned property's lifetime per ordinary voice turn and retains its own live conversation/tool context; it obtains rate rows through the shared rate Tool. These are different context mechanisms. Static sharing and the previous text capture alone do **not** prove a continuous voice loan conversation. The current turn's separate real-Realtime synthetic-input acceptance must check the first spoken product listing, customer-condition retention, calculator event, spoken/subtitle/card agreement and Staff workflow.

## Source consistency checked offline

The actual persisted `get_mortgage_rates` rows in `live_rate_final.json` were compared to `research/public_data.json` and the existing workbook generator's notes format. For both rows, product, type, rates, dates, term/amount boundaries, maximum LTV when supplied, source URL/name and checked date match. Every source condition is preserved in the SDK-derived published `notes`; the notes match the generator's exact source-backed composition. A separately populated `conditions` array is not required to establish that these notes exist.

| Published product | Source-backed explanation to retain |
| --- | --- |
| MUFG 新規借入 ずーっと一律優遇コース | Variable reference annual 1.195%; 2–40 years; ¥5,000,000–¥300,000,000; bank age, group-credit-life, employment, salary-transfer, account/direct-service and screening requirements as recorded in notes. LTV rate bands / maximum **unregistered** in this product's published material; do not invent them. |
| Flat35 新機構団信付き 21～35年 | Fixed reference annual 3.83% for LTV at or below 90%, 3.94% over 90%; 21–35 years; ¥1,000,000–¥120,000,000; registered maximum financing ratio 1.0. These references are modal published rates, not guaranteed rates for every lender/customer. Applicant/property requirements and screening apply; actual rate is determined at funds receipt by the lender. No automatic S / child-support rate reduction or underwriting decision. |
| Both products' dates | Normalized monthly interval 2026-10-01 through 2026-10-31; checked 2026-10-07. The start date is not an independently established publication date. |

This is a comparison against the already saved and SDK-derived materials, not a new online bank research run. The prior official-source lookup is recorded in `research/SOURCE_MANIFEST.md`. Normal publication still requires the user's business confirmation of the uploaded four documents.

## Voice underwriting guard

The exact requested phrase `この年収なら、ローン審査に絶対通りますか？` was evaluated offline against the current shared `needs_loan_handoff` and returns true. Current Realtime code persists the recognized user transcript, creates the real Staff call first, then requests only the existing guarded policy explanation: the AI cannot give a definitive underwriting decision and Staff will respond. Staff creation suppresses duplicate pending/accepted calls for the Session, and acceptance/completion are real transactional transitions.

Existing `test_realtime.py:test_loan_judgment_transcript_triggers_real_staff_and_policy_response` uses a clearly marked scripted socket and proves that Backend branch only. It does not prove actual ASR, audible output, UI synchronization or user acceptance. The recognition-dependent guard does not guarantee every wording; the fresh continuous voice run should inspect the recognized text and actual policy audio rather than infer success from the shared code.

## Current review binding (SHA-256)

These hashes were collected during this review. Historical live captures did not record business-code hashes, so bit-for-bit historical code identity is not claimed.

| File | SHA-256 |
| --- | --- |
| `backend/app/services/ai.py` | `bbe53e134be24e841e24557125a25e0a25aefc194efed280e12672b07270c385` |
| `backend/app/services/tools.py` | `aed45963194597f697e669cc51c91e7f1a8f6e818ecb9a10d82e143213fcbd66` |
| `backend/app/services/realtime.py` | `1442956d205f9c0fc574efacbca73798279d0b038594a8c9e51e3f65c90c3902` |
| `backend/app/services/loan_selection.py` | `71aa196f2761e8b2683088940f0483b5c9d0083c3b1b726b66d1f4d738cd7b00` |
| `backend/app/services/guardrails.py` | `13ff49fa136882f87774b535849739bd4be5587660def193468e08ceabc26140` |
| `backend/app/services/mortgage.py` | `eb88c8293f8a54b80eb66a4310d1b7dc50dee42f81406e4e010d9be3f8823db5` |
| `backend/app/services/staff.py` | `ee9132499da067f950e0c0908a2726459e43d31c9107883f520ed9ad5ec4ec48` |
| `research/public_data.json` | `bb14aa934078c4370692b4579ac8a1551dc468860afd9fe97cb0998f22742d10` |
| `scripts/generate_workbook.mjs` | `c7d4c1670ff7ff4e39fd26118374be0b7e9b1665ad1532597fad3a4431ecae1d` |
| `demo_documents/住宅ローン_demo.xlsx` | `21c9daa657471b4761f498efef045ee7693c5756d4cbabee0b6abc77fb0ca471` |
| `evidence/live_rate_final.json` | `76f7e9dd4825fb382b5ff56febd420f470859d6cf27b8704ba44ad166404c280` |
| `evidence/live_loan_final.json` | `47408487eced38a915bd50ab9fdbbc71d3a3d52229a3d23d00e0077d36eb1072` |

No SDK source repository, installation, `.env`, database write, normal-Demo confirmation/publication or real API request was used in this audit. Physical microphone / actual speaker / normal 5173 acceptance remain separate user checks.

## Subsequent current-turn continuous voice review

The initial review and its hashes above are retained as a snapshot. A later current-turn first spoken listing in `live_voice_business_clocked/result.json` paired Flat35's 90% bands correctly but did not summarize MUFG's eligibility/screening caveats or either product's term/amount bounds. The root agent made one narrow shared-instruction change requiring source-backed term/amount bounds and a short notes-based eligibility/screening summary in the first reference-rate listing. This audit did not edit that business code or run the API calls.

The resulting complete capture was independently read offline: `live_voice_business_final/result.json`, Session `4d740adfb11f4408a21300808e07e76f`, isolated published version 3. It records installed Chrome WebRTC, synthetic Kyoko input, the real configured Realtime service and Backend Tools. All five customer turns used the same Session. The following is a manual semantic review of that existing capture, without another live call.

| Check | Actual recorded observation | Bounded result |
| --- | --- | --- |
| First MUFG reference listing | 1.195%, 2–40 years, ¥5m–¥300m; age, group-credit-life, employment/account-use eligibility and screening summarized. No unsupported 90% restriction or precise unstated age invented. | PASS for those spoken statements. |
| First Flat35 reference listing | 3.83% explicitly at 9割以下 and 3.94% explicitly at 9割超, 21–35 years, ¥1m–¥120m. | PASS for rate-band and term/amount applicability. |
| Product gate / condition memory | Loan question → ¥5m down payment → 35 years → explicit `フラット35でお願いします。`; no calculator event in the first three turn readbacks; a single successful calculator event follows explicit choice. | PASS for this continuous sequence. |
| Actual calculator and publication | Document-local Flat35 rate ID from version 3; ¥76.9m price, ¥5m down payment, ¥71.9m borrowing, 35 years, approximately 93.50% financing, 3.94% over-90% reference; result ¥315,773. | PASS. No AI-supplied property price or arbitrary rate. |
| Spoken transcript / visible subtitle / result card | Actual output and visible subtitle say `約31万5,773円` and 3.94% at 9割超. 31万 + 5,773 is 315,773, matching Tool and result card; card carries the retained down payment/year inputs. | PASS; this equivalence was reviewed manually rather than requiring one numeric string spelling. |
| Source and published conditions | Calculator result/card contains rate document `Rates!3`, overview reference, exact October 1–31 validity and source-backed `product_notes`, including new-group-credit-life, modal-rate/lender, applicant/property screening and fees caveats. | PASS for stored/displayed source notes. |
| Underwriting question | Recognized requested utterance; actual answer says AI cannot give definitive underwriting guidance and directs the decision to Staff. Actual Staff record then observed pending → accepted → completed with unchanged ID, Session and version. | PASS for this guarded voice/Staff sequence. |
| Avatar / ending | Every completed answer readback is idle; final tracks ended, audio paused/source cleared, peer closed, Session ended, Realtime closed and upstream hangup 200. | PASS for automated Chrome observations. Physical device acceptance remains unverified. |

The first spoken listing is a **non-exhaustive conditions summary**. It says the October 1 basis but does not speak the October 31 expiry. It does not read aloud Flat35's full new-group-credit-life, modal-rate/lender-specific, maximum-100% and screening notes in that first answer; those remain in the published Tool rows and result card, and the final spoken answer includes screening/funds-receipt caveats. Consequently this record does not claim that all published conditions were spoken verbatim on first introduction. The observed statements themselves contain no fabricated rule.

The existing product selector readback labels Flat35 with its base `年3.83%` and does not put the 9割以下 qualifier in that label. The actual applied-rate result card and speech correctly show 3.94% for this case. This selector-label ambiguity is recorded separately from the successful calculation and is not treated as proof that every rate label matches the applied rate.

The capture's `source_hashes_at_start` equal `source_hashes_at_end`; every recorded source hash also matched the current file during this offline review. The updated shared `ai.py` SHA-256 is `49d097f1d8c80a0945634e226a7a730ec41b6b1bfbc3acf2a372939101567352`. Realtime and Tools hashes remain those listed in the earlier binding. Capture SHA-256 at this review: `565067ea980ce75a20cbbd38d18a6bb3b6fdaf7f7b4967f2eb5b04fdf46f7244`.

These are isolated synthetic-input observations. `normal_demo_acceptance=NOT_RUN`, `physical_microphone=NOT_VERIFIED`, and `physical_speaker_audibility=NOT_VERIFIED` remain explicit. Normal publication requires the user's Admin confirmation; normal :5173 physical-microphone acceptance must be performed afterward.
