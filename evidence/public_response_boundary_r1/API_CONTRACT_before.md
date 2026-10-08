# 接客範囲API追補（2026-10-07）

- `POST /api/sessions`: `{mode, property_id?: null|string}`。未指定は一般相談。公開版がなくても作成でき、version=null のまま固定。未選択Customerのsnapshotに物件情報を返さない。
- `POST /api/sessions/{id}/property`: `{property_id}`。Session tokenと開始版で検証。明示選択時のみ当該物件文脈を設定。公開済みで有効な対象だけを使用。
- 確認データ `document.scope`: `general/company/property`（旧資料の既定はproperty）。共通・会社はsource_name/source_url/checked_at/effective_date/valid_untilを必須とし、propertyの混在を拒否。確認・公開制御は従来経路を維持。
- `POST /api/sessions/{id}/mortgage`: 未選択は `{loan_amount, years, rate_id, property_price?}`。融資率条件の商品はproperty_price必須。選択済み物件の頭金経路も維持。AI Toolは明示商品選択と顧客申告額を検証し、独自計算・既定房価使用はしない。
- Controlled Tools: `list_properties`（自動選択なし）、`search_consultation_knowledge(query,scope=general|company)`。具体物件Toolは未選択時PROPERTY_CONTEXT_REQUIRED。検索範囲を偽装して物件資料を取得することも拒否。
- version=null の一般相談でもStaff呼出・受付・対応完了が可能。会社データがない時は会社固有情報を補わない。内部の接客安全方針は会社の営業サービスや承諾を意味しない。

以下は従来の認証・業務API一覧です。上記追補が既定物件前提を上書きします。

# Demo API contract

Base `/api`; frontend Vite proxies to `127.0.0.1:8000`.
Errors `{error:{code,message}}`, no fake success. JSON unless upload/SDP.
Admin Basic auth username `admin`; staff username `staff` (admin also allowed).
Customer session endpoints require header `X-Session-Token` from session creation.

- GET `/health` → `{status,sdk_version,demo_mode,ai_configured,realtime_configured}`
- GET `/property` → latest published snapshot or 409. Snapshot `{version,published_at,property,knowledge,rates,faq,references,document_ids}`. Property fields: property_name,lot,price,address,station,walking_minutes,layout,land_area,building_area,parking,completion_date,equipment,source_url,source_name,checked_at,effective_date,valid_until,scope_notes. Knowledge `{text,reference}`; references `{document_id,filename,location,source_url?}`.
- POST `/sessions` body `{mode:"text"|"voice"}` → `{id,token,version,snapshot,status,created_at}`
- GET `/sessions/{id}` → session, messages, tool_events, staff_calls, realtime status
- POST `/sessions/{id}/messages` body `{text}` → `{answer,references,tool_results,staff_call?,provider:"openai",version}`. Missing key 503.
- POST `/sessions/{id}/end` → session ended
- POST `/sessions/{id}/staff-calls` body `{reason,last_customer_question?}` → staff call
- POST `/sessions/{id}/mortgage` body `{down_payment,years,rate_id}` → calculator card with all amounts, rate, monthly_payment, calculation_date, notes. Property price and verified rate loaded by backend.
- POST `/sessions/{id}/realtime` raw `application/sdp` offer → raw SDP answer. Backend OpenAI sideband controls tools; frontend handles subtitles/state only.

Admin:
- GET `/admin/documents` → array metadata `{id,filename,status,created_at,parsed_at,confirmed_at,published_version,error?}`
- POST `/admin/documents` multipart `file` → uploaded metadata
- POST `/admin/documents/{id}/parse` → detail
- GET `/admin/documents/{id}` → metadata plus `{raw,normalized,reviewed,confirmation_note}`
- POST `/admin/documents/{id}/confirm` body `{reviewed:{property:{},knowledge:[],rates:[],faq:[]},note:"..."}` → confirmed detail. Every reference tied to same document by backend.
- POST `/admin/publish` body `{document_ids:[ids]}` → new immutable complete snapshot replacing previous selection. All selected must confirmed/published. New sessions pin version; existing sessions stay pinned.
- GET `/admin/sessions` → array session history, messages, tool_events, staff_calls.
- GET `/admin/versions` → array snapshots.

Staff:
- GET `/staff/calls` → array `{id,session_id,property_name,created_at,reason,last_customer_question,status}`
- POST `/staff/calls/{id}/accept` → accepted
- POST `/staff/calls/{id}/complete` → completed (only accepted calls)
Customer and staff poll every 2s. No fake local notification.

Rate fields `{id,bank,product,rate_type,rate,effective_date,valid_until,notes,source_url,source_name,checked_at,reference}`. Rate is annual percent e.g. 1.195. Expired rates blocked by backend.

UI defaults: no data initially, upload docs and explicitly review/confirm/publish; no auto-publish. Japanese. Customer starts voice via user gesture/mic then WebRTC; separate `文字で開始` works without mic. Display AI misconfiguration honestly. No mock frontend responses. Client voice events: input_audio_buffer.speech_started/stopped; conversation.item.input_audio_transcription.completed; response.output_audio_transcript.delta/done; response.created/done; output_audio_buffer.started/stopped; error. Sideband persists real transcripts/tools, UI polls their results.
