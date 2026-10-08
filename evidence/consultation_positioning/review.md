# Company concierge positioning — current review

2026-10-07. Existing project, SDK 1.8.0 distribution, venv/dependencies, configured models, .env and normal/TEST storage are retained. No SDK core/source repository changes, reinstall, DB copying or normal human-confirmation impersonation.

## Current normal environment

Authoritative runtime readback: `final_readback.json`. Normal Customer/Admin/Staff are on localhost:5173; Backend127.0.0.1:8000, DB `data/housing.db`. Six files are SDK-parsed, zero confirmed, no published version, zero active normal Session records. Local hashes match uploaded files. Both AI configuration flags are present; actual upstream use is verified in the isolated environment using the retained configuration.

The four existing documents remain. Two additional native-text general FAQ PDFs were uploaded and actually parsed via SDK1.8.0. Normal confirmation/publication has not been performed. Mortgage workbook review scope/source/date fields are prepared as a **human-review draft** from SDK rate rows; raw and normalized records are unchanged. `rate_draft_validation.json` verifies backend validation without writing confirmation. Company service/hours/guarantee/own purchase-process materials remain **MISSING**.

Admin workflow and six-file source/date/scope table: [CONSULTATION_POSITIONING](../../docs/CONSULTATION_POSITIONING.md). General FAQ provenance: `research/consultation_sources.json`. FAQ dates are SANZO's check date and Demo recheck deadline, not invented official publication/expiry dates.

## A–G evidence

| Requirement | Actual evidence and limit |
|---|---|
| A Start without property | Normal installed-Chrome default center and text start with version=null/property_id=null: `chrome_ui.json`, `normal-centered-home.png`. No default No.15/price/address/property side panel. Facts from unconfirmed documents remain unavailable. |
| B General inquiry stays general | Real text `live_text.json` first purchase question and real Realtime `../live_consultation_voice/result.json` general/ambiguous checks. Published v4 general FAQ answers, no property-tool use or No.15 introduction. Latest targeted Realtime greeting remains general. |
| C Explicit property only | Backend property Tool guard/unit tests, masked new Customer snapshot. Actual 15号地 voice question in `../live_consultation_voice_final/result.json` reads No.15 price7690万円/equipment and opens the card. Latest real text switch from loan to No.15: `text_materials_chrome.json`. Unknown/deselected object does not fall back to No.15. |
| D On-demand closeable materials | Real general voice card automatically opens/closes without reopening on polling; latest real text loan/property cards and close persist: `text_materials_chrome.json`. Desktop expanded cards leave controls unobstructed. Narrow1000/390px actual HTTP calculator/UI end checks: `narrow_material_controls.json` (zero AI calls, not a physical-tablet test). |
| E No implicit default price | Actual loan3000万円,35years,MUFG1.195%,87439JPY/month; property_price/down_payment null. Real Backend Tool and correct Session/pinned v4, actual audio output transcript/subtitle/card agree: `targeted_text_final.json`, `../live_consultation_voice_end/result.json`. Three-turn voice loan condition retention and first reference conditions are in `../live_consultation_voice_recheck/result.json`; that run's later UI failure remains recorded. Flat35 requires explicit acquisition price by tested Backend guard; it does not use No.15. |
| F Text/voice share behavior | Shared observed-customer context, source-scoped Tools, product/amount guards and underwriting policy. Actual text and synthetic-input/real-Realtime paths above. Latest Source selection after text loan is separately verified. Physical mic, speaker intelligibility, echo, actual user acceptance are **NOT_VERIFIED**. |
| G Sources/publication/Staff | Real SDK source PDFs; unit tests for unconfirmed, pinned version, source scope, date expiry and property-tool guard. Underwriting voice does not guarantee approval and creates real Staff record. Latest real Staff UI pending→accepted→completed and Customer polling in same general Session: `../live_consultation_voice_end/result.json` and screenshots. |

Latest automated checks: Backend **138 passed**, one preexisting Starlette deprecation warning; Frontend production build PASS. Scripted unit providers/sockets are TEST-only and are not counted as live AI acceptance.

## Issues and targeted fixes

- New Session no longer silently binds the sole property. Customer payload also withholds unselected property details. Legacy persisted property Sessions retain their old meaning.
- Text and recognized speech establish context only after an explicit published object. General/ company/property source domains stay distinct. Company absence is stated without an invented confirmation promise.
- Explicit-loan route uses only customer's declared principal and optional acquisition price. Backend remains the calculator. Japanese ASR currency notation such as 三千万円/借り入れ額 is parsed as the customer's declaration, not an SDK fact.
- A property's 未定 statement no longer revokes a separately explicit mortgage-product choice. Product-undecided/refusal guards remain.
- First real positioning voice run asked unnecessary down payment/acquisition price for MUFG. Conditional input guidance and controlled customer declarations/calculation-input hints were added. Registered product conditions remain unchanged.
- The second voice run reached the real87439JPY calculator but an interim assistant message overwrote the loan drawer with a sources drawer. Event/message precedence was fixed, and form/result synchronization is shared by text and voice.
- Polling kept the unselected startup snapshot, preventing later selected-property details. Polling now uses the backend's pinned, current-context projection.
- A later run verified loan/property/Staff but could not click End because the overlay covered it. Expanded desktop geometry and narrow in-flow cards were fixed. Policy responses clear stale property references. The latest targeted real voice run verifies input stopped, playback paused/cleared, peer closed, Avatar idle, Session ended and upstream hangup200 while the loan drawer remains expanded.
- Text's controlled rate refresh after earlier loan history could supersede a subsequent property's card. Explicit property questions take priority; latest real text Chrome loan→property→close→end passes.

No 3D/avatar replacement, CRM, nationwide/multi-store search, deployment, SDK modification or environment rebuild.

## Honest history and correlation

Preserve `live_text.json`'s wrong Staff endpoint harness failure and targeted Staff UI recovery (`text_review.json`). Preserve `targeted_text.json`'s unnecessary down-payment clarification; final targeted text passes without it. Preserve all three voice attempts: initial unnecessary inputs/Japanese amount issue, loan-card race, and blocked End/unhandled harness timeout. The third attempt's cleanup is explicitly a Backend cleanup, **not a successful UI End acceptance**. Its Staff completion is corroborated by real Staff events and screenshots. The latest targeted ending run is the successful End evidence.

The latest end run deliberately repeats only loan/Staff/end after the layout fix; it does not repeat already evidenced FAQ/property questions. This report cites each successful subcheck, rather than relabeling failed runs as PASS. General voice and segmented condition retention evidence precede targeted loan/UI fixes; their data version is v4. Latest voice end source hashes match within that run. Subsequent changes cover text-property material priority, Admin rate review drafts, narrow layout and a general borrowing-capacity question boundary; these were separately tested without repeating Realtime API costs. Existing isolated v1–v3 historical data and legacy rate-scope tags are retained.

The isolated DB still contains two preexisting active historical Session records, unchanged from baseline. This does not imply two live microphones. All Sessions created by this turn's acceptance scripts were ended; the normal runtime has zero active records. Historical failed/disconnected metadata is not rewritten to closed200.

## Remaining human gates

**WAITING_FOR_USER_ADMIN_CONFIRMATION_AND_PUBLICATION**: On normal Admin, check the three property PDFs, general mortgage-rate draft and two general FAQs; confirm each and select all six to publish. No duplicate upload is necessary.

**WAITING_FOR_USER_MIC_TEST**: After publication, use normal5173 for genuine Mac microphone/speaker purchase/general/property/loan/Staff/end acceptance. Observe subtitles, exact amounts/conditions, latency, self-voice recognition and end-of-capture. Synthetic inputs and received WebRTC audio do not substitute for this.

**READY_FOR_CUSTOMER_DEMO=NO** until those two gates are satisfied. Company facts remain unavailable until actual company materials are provided, checked and published; current fallback explicitly reports their absence.
