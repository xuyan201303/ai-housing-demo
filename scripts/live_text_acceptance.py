"""Bounded real OpenAI acceptance against an explicitly isolated HTTP instance.

This script never prints credentials, persists session tokens, publishes documents,
retries an upstream error, or changes a model. Expected facts come from the already
SDK-parsed, confirmed, published fixture and its recorded research source data.
"""
import json
import math
import os
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]
URL = os.getenv("ACCEPTANCE_URL", "http://127.0.0.1:8001")
OUTPUT = ROOT / "evidence/live_text_acceptance.json"
MAX_CUSTOMER_TURNS = 10


def sanitized(value):
    if isinstance(value, dict):
        return {
            k: sanitized(v)
            for k, v in value.items()
            if k.lower() not in {"token", "api_key", "authorization", "password"}
        }
    if isinstance(value, list):
        return [sanitized(v) for v in value]
    return value


def main():
    env = dotenv_values(ROOT / ".env")
    client = httpx.Client(base_url=URL + "/api", timeout=180)
    staff = httpx.Client(
        base_url=URL + "/api", timeout=30, auth=("staff", env["STAFF_PASSWORD"])
    )
    health = client.get("/health")
    health.raise_for_status()
    assert health.json()["demo_mode"] == "test", "Only an explicit test instance is allowed"
    assert health.json()["ai_configured"], "Backend has not loaded OPENAI_API_KEY"
    snapshot_response = client.get("/property")
    snapshot_response.raise_for_status()
    snapshot = snapshot_response.json()
    research = json.loads((ROOT / "research/public_data.json").read_text())
    assert snapshot["property"]["price"] == research["property"]["price"]
    assert snapshot["document_ids"], "Published SDK fixture is required"
    flat_rate = next(r for r in snapshot["rates"] if "フラット35" in r["product"])
    evidence = {
        "mode": "isolated_test_real_openai_http",
        "url": URL,
        "started_at": datetime.now().astimezone().isoformat(),
        "health": health.json(),
        "published_version": snapshot["version"],
        "document_ids": snapshot["document_ids"],
        "source_fixture": "research/public_data.json + existing SDK parsed/confirmed/published documents",
        "customer_turn_limit": MAX_CUSTOMER_TURNS,
        "customer_turn_count": 0,
        "upstream_retry_count": 0,
        "model_override": False,
        "cases": [],
        "checks": {},
    }
    upstream_blocked = False

    def save():
        OUTPUT.write_text(json.dumps(sanitized(evidence), ensure_ascii=False, indent=2))

    def session(case):
        response = client.post("/sessions", json={"mode": "text"})
        response.raise_for_status()
        data = response.json()
        case["session_id"] = data["id"]
        case["session_version"] = data["version"]
        assert data["version"] == snapshot["version"]
        return data["id"], {"X-Session-Token": data["token"]}

    def ask(case, ident, headers, question):
        nonlocal upstream_blocked
        if evidence["customer_turn_count"] >= MAX_CUSTOMER_TURNS:
            raise RuntimeError("Customer turn limit reached; no extra request permitted")
        evidence["customer_turn_count"] += 1
        record = {"question": question}
        case["turns"].append(record)
        save()
        try:
            response = client.post(f"/sessions/{ident}/messages", headers=headers, json={"text": question})
        except httpx.HTTPError as exc:
            record["transport_error"] = type(exc).__name__
            upstream_blocked = True
            save()
            return None
        record["http_status"] = response.status_code
        data = response.json()
        if response.is_error:
            error = data.get("error", {})
            record["error"] = {k: error[k] for k in ("code", "message") if k in error}
            upstream_blocked = True
            evidence["upstream_error"] = record["error"]
            save()
            return None
        record["response"] = sanitized(data)
        save()
        return data

    def finish(case, ident, headers):
        response = client.get(f"/sessions/{ident}", headers=headers)
        response.raise_for_status()
        state = response.json()
        case["persisted_messages"] = state["messages"]
        case["persisted_tool_events"] = state["tool_events"]
        case["persisted_staff_calls"] = state["staff_calls"]
        response = client.post(f"/sessions/{ident}/end", headers=headers)
        response.raise_for_status()
        case["ended_status"] = response.json()["status"]
        save()

    facts = {"name": "published_property_facts", "turns": []}
    evidence["cases"].append(facts)
    ident, headers = session(facts)
    for question in [
        "No.15の販売価格と土地・建物の面積を教えてください。",
        "No.15の食洗機と太陽光発電、エアコンはどのような設備ですか？",
        "No.15から八千代中央駅までは正確に何メートルで何分ですか？資料の適用範囲も教えてください。",
    ]:
        if upstream_blocked:
            break
        ask(facts, ident, headers, question)
    finish(facts, ident, headers)

    if not upstream_blocked:
        unknown = {"name": "G_unlisted_specific_fact", "turns": []}
        evidence["cases"].append(unknown)
        ident, headers = session(unknown)
        ask(unknown, ident, headers, "No.15の駐車場にはEVの6kW充電器が標準設置されていますか？")
        finish(unknown, ident, headers)

    if not upstream_blocked:
        loan = {"name": "C_conversational_mortgage", "turns": []}
        evidence["cases"].append(loan)
        ident, headers = session(loan)
        for question in [
            "住宅ローンだったら月いくら？",
            "頭金は500万円です。",
            "返済期間は35年を希望します。",
            "フラット35（新機構団信付きの21～35年）で、登録されている参考金利を使って概算をお願いします。",
        ]:
            if upstream_blocked:
                break
            ask(loan, ident, headers, question)
        finish(loan, ident, headers)
        calculations = [
            t["result"] for t in loan["persisted_tool_events"]
            if t["name"] == "calculate_mortgage" and "error" not in t["result"]
        ]
        checks = evidence["checks"]
        checks["loan_backend_tool_used"] = bool(calculations)
        checks["loan_no_calculation_before_product_selection"] = not any(
            t["name"] == "calculate_mortgage"
            for turn in loan["turns"][:-1]
            for t in turn.get("response", {}).get("tool_results", [])
        )
        if calculations:
            calc = calculations[-1]
            principal = research["property"]["price"] - 5_000_000
            expected_rate = next(r for r in research["mortgage_rates"] if r["id"] == "jhf-flat35-2026-10")["rate_over_90_percent"]
            monthly_rate = expected_rate / 1200
            months = 35 * 12
            expected_payment = math.floor(principal * monthly_rate * (1 + monthly_rate) ** months / ((1 + monthly_rate) ** months - 1) + 0.5)
            checks["loan_price_downpayment_principal"] = (calc["property_price"], calc["down_payment"], calc["loan_amount"]) == (76_900_000, 5_000_000, principal)
            checks["loan_product_years_and_ltv_rate"] = calc["rate_id"] == flat_rate["id"] and calc["years"] == 35 and calc["annual_interest_rate"] == expected_rate
            checks["loan_independent_equal_payment_comparison"] = calc["monthly_payment"] == expected_payment
            checks["loan_reference_disclaimer_dates"] = bool(calc["references"]) and "概算" in calc["notes"] and calc["effective_date"] == "2026-10-01" and calc["valid_until"] == "2026-10-31"
            evidence["independent_loan_expectation"] = {"monthly_payment": expected_payment, "annual_interest_rate": expected_rate, "method": "independent standard positive-power equal-payment formula, half-up yen"}

    # Scenario D is an explicit backend policy; it creates no OpenAI request.
    handoff = {"name": "D_loan_approval_handoff", "turns": []}
    evidence["cases"].append(handoff)
    ident, headers = session(handoff)
    result = ask(handoff, ident, headers, "年収500万円なら絶対ローン通りますか？")
    if result:
        call = result.get("staff_call")
        listed = staff.get("/staff/calls")
        listed.raise_for_status()
        evidence["checks"]["D_no_approval_guarantee"] = result["provider"] == "backend_policy" and "確定的なご案内はできません" in result["answer"]
        evidence["checks"]["D_real_staff_record_visible"] = bool(call) and any(c["id"] == call["id"] for c in listed.json())
        if call:
            for transition in ["accept", "complete"]:
                response = staff.post(f"/staff/calls/{call['id']}/{transition}")
                response.raise_for_status()
                handoff["staff_" + transition] = response.json()
                customer = client.get(f"/sessions/{ident}", headers=headers)
                customer.raise_for_status()
                current = next(c for c in customer.json()["staff_calls"] if c["id"] == call["id"])
                evidence["checks"]["D_customer_readback_" + transition] = current["status"] == {"accept": "accepted", "complete": "completed"}[transition]
    finish(handoff, ident, headers)

    turns = [t for case in evidence["cases"] for t in case["turns"] if "response" in t]
    evidence["checks"]["real_openai_provider_received"] = any(t["response"]["provider"] == "openai" for t in turns)
    evidence["checks"]["session_version_pinned"] = all(t["response"]["version"] == snapshot["version"] for t in turns)
    evidence["checks"]["references_present_for_openai_answers"] = all(t["response"]["references"] for t in turns if t["response"]["provider"] == "openai")
    evidence["completed_at"] = datetime.now().astimezone().isoformat()
    evidence["status"] = "UPSTREAM_ERROR_RECORDED_NO_RETRY" if upstream_blocked else "LIVE_RESPONSES_CAPTURED_REQUIRES_SEMANTIC_REVIEW"
    save()
    print(json.dumps({"status": evidence["status"], "customer_turn_count": evidence["customer_turn_count"], "checks": evidence["checks"], "error": evidence.get("upstream_error")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
