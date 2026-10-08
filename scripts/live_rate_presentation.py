"""One authorized real turn for reference-rate conditions before product choice.

Independent evidence; preserves every prior capture. Never retries an error,
changes a model, confirms/publishes documents, or accesses a production DB.
"""
import argparse
import json
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "evidence/live_rate_presentation.json"
QUESTION = "頭金500万円、35年を希望。参考金利商品の条件を教えてください。まだ商品は選んでいません。"


def main():
    if OUTPUT.exists():
        raise RuntimeError("Existing one-turn evidence must be preserved")
    client = httpx.Client(base_url="http://127.0.0.1:8001/api", timeout=180)
    health = client.get("/health")
    health.raise_for_status()
    assert health.json()["demo_mode"] == "test" and health.json()["ai_configured"]
    response = client.post("/sessions", json={"mode": "text"})
    response.raise_for_status()
    session = response.json()
    headers = {"X-Session-Token": session["token"]}
    ident = session["id"]
    result = {
        "mode": "isolated_test_http_one_real_openai_rate_conditions_turn",
        "customer_turn_limit": 1, "upstream_retry_count": 0, "model_override": False,
        "session_id": ident, "published_version": session["version"],
        "question": QUESTION, "checks": {},
    }
    def save():
        OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    save()
    try:
        response = client.post(f"/sessions/{ident}/messages", headers=headers, json={"text": QUESTION})
    except httpx.HTTPError as exc:
        result["transport_error"] = type(exc).__name__
        result["status"] = "TRANSPORT_ERROR_NO_RETRY"
    else:
        result["http_status"] = response.status_code
        if response.is_error:
            error = response.json().get("error", {})
            result["error"] = {k: error[k] for k in ["code", "message"] if k in error}
            result["status"] = "UPSTREAM_ERROR_NO_RETRY"
        else:
            result["response"] = response.json()
    save()
    state_response = client.get(f"/sessions/{ident}", headers=headers)
    state_response.raise_for_status()
    state = state_response.json()
    result["persisted_messages"] = state["messages"]
    result["persisted_tool_events"] = state["tool_events"]
    if "response" in result:
        answer = result["response"]["answer"].replace("％", "%")
        checks = result["checks"]
        checks["real_openai_answer"] = result["response"]["provider"] == "openai"
        checks["no_calculation_without_product_selection"] = not any(e["name"] == "calculate_mortgage" for e in state["tool_events"])
        checks["flat35_lower_ltv_rate_qualified"] = "3.83%" in answer and ("9割以下" in answer or "90%以下" in answer)
        checks["flat35_higher_ltv_rate_qualified"] = "3.94%" in answer and ("9割超" in answer or "90%超" in answer or "90%を超" in answer)
        checks["correct_reference_basis_and_expiry"] = ("2026-10-01" in answer or "10月1日" in answer) and ("2026-10-31" in answer or "10月31日" in answer) and "11月" not in answer
        checks["reference_caveat"] = "参考" in answer and ("審査" in answer or "条件" in answer)
        checks["source_and_version"] = bool(result["response"]["references"]) and result["response"]["version"] == session["version"]
        result["status"] = "LIVE_CAPTURED_REQUIRES_MANUAL_QUALIFIER_REVIEW" if all(checks.values()) else "REQUIRES_SEMANTIC_REVIEW"
    ended = client.post(f"/sessions/{ident}/end", headers=headers)
    ended.raise_for_status()
    result["session_final_status"] = ended.json()["status"]
    save()
    print(json.dumps({"status": result["status"], "checks": result["checks"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-name", choices=["live_rate_presentation", "live_rate_final"], default="live_rate_presentation")
    args = parser.parse_args()
    OUTPUT = ROOT / "evidence" / (args.output_name + ".json")
    main()
