"""Four real turns checking explicit mortgage product selection after a fix.

No retry, model override, document mutation, or production database access.
The initial nine-turn capture is never overwritten.
"""
import argparse
import json
import math
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "evidence/live_loan_revalidation.json"


def main():
    if OUTPUT.exists():
        raise RuntimeError("Existing evidence must be preserved; choose a new explicit run")
    client = httpx.Client(base_url="http://127.0.0.1:8001/api", timeout=180)
    health = client.get("/health")
    health.raise_for_status()
    assert health.json()["demo_mode"] == "test" and health.json()["ai_configured"]
    response = client.post("/sessions", json={"mode": "text"})
    response.raise_for_status()
    session = response.json()
    ident = session["id"]
    headers = {"X-Session-Token": session["token"]}
    result = {
        "mode": "isolated_test_real_openai_http_loan_revalidation",
        "customer_turn_limit": 4,
        "upstream_retry_count": 0,
        "model_override": False,
        "session_id": ident,
        "published_version": session["version"],
        "turns": [],
        "checks": {},
    }
    def save():
        OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    save()
    for text in [
        "住宅ローンだったら月いくら？",
        "頭金は500万円です。",
        "返済期間は35年を希望します。",
        "フラット35（新機構団信付きの21～35年）で、登録されている参考金利を使って概算をお願いします。",
    ]:
        turn = {"question": text}
        result["turns"].append(turn)
        save()
        try:
            response = client.post(f"/sessions/{ident}/messages", headers=headers, json={"text": text})
        except httpx.HTTPError as exc:
            turn["transport_error"] = type(exc).__name__
            result["status"] = "TRANSPORT_ERROR_NO_RETRY"
            break
        turn["http_status"] = response.status_code
        if response.is_error:
            error = response.json().get("error", {})
            turn["error"] = {k: error[k] for k in ["code", "message"] if k in error}
            result["status"] = "UPSTREAM_ERROR_NO_RETRY"
            break
        turn["response"] = response.json()
        save()
    state_response = client.get(f"/sessions/{ident}", headers=headers)
    state_response.raise_for_status()
    state = state_response.json()
    result["persisted_messages"] = state["messages"]
    result["persisted_tool_events"] = state["tool_events"]
    checks = result["checks"]
    checks["four_real_openai_answers"] = len(result["turns"]) == 4 and all(t.get("response", {}).get("provider") == "openai" for t in result["turns"])
    checks["no_successful_calculation_before_product_selection"] = not any(
        t["name"] == "calculate_mortgage" and "error" not in t["result"]
        for turn in result["turns"][:3] for t in turn.get("response", {}).get("tool_results", [])
    )
    checks["no_payment_quoted_before_selection"] = not any(
        any(v in turn.get("response", {}).get("answer", "").replace(",", "") for v in ["209563", "315773", "20万9", "31万5"])
        for turn in result["turns"][:3]
    )
    selected_calcs = [
        t["result"] for t in result["turns"][-1].get("response", {}).get("tool_results", [])
        if t["name"] == "calculate_mortgage" and "error" not in t["result"]
    ]
    checks["selected_product_real_calculator"] = bool(selected_calcs)
    if selected_calcs:
        calc = selected_calcs[-1]
        monthly_rate = 3.94 / 1200
        expected = math.floor(71_900_000 * monthly_rate * (1 + monthly_rate) ** 420 / ((1 + monthly_rate) ** 420 - 1) + 0.5)
        checks["flat35_inputs_and_ltv_rate"] = "フラット35" in calc["product"] and (calc["down_payment"], calc["years"], calc["loan_amount"], calc["annual_interest_rate"]) == (5_000_000, 35, 71_900_000, 3.94)
        checks["independent_monthly_formula"] = calc["monthly_payment"] == expected
        conditions_present = bool(calc.get("conditions")) or "利用条件" in calc.get("product_notes", "")
        checks["references_conditions_disclaimer"] = bool(calc["references"]) and conditions_present and "本結果は概算です" in calc["notes"]
    checks["version_pinned"] = all(t.get("response", {}).get("version") == session["version"] for t in result["turns"] if "response" in t)
    ended = client.post(f"/sessions/{ident}/end", headers=headers)
    ended.raise_for_status()
    result["session_final_status"] = ended.json()["status"]
    result.setdefault("status", "PASS" if all(checks.values()) else "REQUIRES_SEMANTIC_REVIEW")
    save()
    print(json.dumps({"status": result["status"], "checks": checks}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-name", choices=["live_loan_revalidation", "live_loan_final"], default="live_loan_revalidation")
    args = parser.parse_args()
    OUTPUT = ROOT / "evidence" / (args.output_name + ".json")
    main()
