# Real Chrome text acceptance — 2026-10-07

Exactly one real customer turn was sent to the isolated `demo_mode=test` instance (`5174` → `8001`), using installed Google Chrome and the actual OpenAI Responses provider. No API mock, fallback, retry, document publication, model override, or additional customer turn was used. API keys and session tokens are excluded from evidence.

The captured answer reports maximum 12 minutes / 920–950 m, explicitly identifies the four-sale-lot scope, and says `No.15単独の正確な値ではありません`. This is a truthful limitation, not a precise No.15-only claim. The initial harness regex did not recognize this wording and stopped early. `initial_result.json` preserves that initial failure; the regex was broadened, and `result.json` records the offline semantic review rather than inventing another successful request.

The original Chrome screenshot `failure.png` visibly shows the actual answer and four reference rows. That screenshot was pixel-reviewed. The dynamic source-DOM assertion was skipped after the false-negative matcher, so source visibility is supported by the actual screenshot, not by a claimed rerun of that assertion.

`offline_readback.json` verifies the exact captured session through a read-only SQLite connection: one stored customer question, one identical actual assistant answer, pinned version 3, and ended status. No HTTP/OpenAI call was needed for this readback. Original uncaught page errors: zero. One unspecified HTTP 404 resource console entry occurred in the initial run.

After adding the requested SVG favicon and price wrapping fix, `--offline-review` loaded only the landing page: zero session POSTs, zero added customer turns, zero console/page errors or failed resources, favicon HTTP 200, single-line price, and no desktop horizontal overflow. `customer-after-polish-desktop.png` was pixel-reviewed: price and layout are legible, station-scope notes are visible, and the illustration disclaimer remains visible.

The initial automatic approval review rejected the live command before execution. Read-only public-payload inspection and the original user attachment's explicit real OpenAI/public-property/demo-question instructions were then provided; the same action was approved. `approval_block.json` preserves the initial rejection as history. No alternative execution path bypassed the rejection.

Live voice and microphone verification are separate acceptance work owned by the root agent. The frontend change preserving listening/thinking when an interrupted greeting clears the audio buffer passed TypeScript/Vite compilation; this text test does not verify that voice-state correction.
