"""Agent tools. Business rules live in plain Python, NOT in the prompt,
so the LLM can never talk its way into an invalid refund."""
import json
import os
import uuid
from datetime import datetime, timezone

from langchain_core.tools import tool

from app import config

NOT_FOUND = "No order found matching that order ID and email. Ask the customer to double-check both."


def _read(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _verified_order(order_id, email):
    """Identity guardrail: order ID AND email must both match."""
    for o in _read(config.ORDERS_FILE, []):
        if o["order_id"] == str(order_id).strip() and o["email"].lower() == email.strip().lower():
            return o
    return None


def evaluate_refund(order, reason):
    """Pure rule engine. Returns (eligible, explanation, amount)."""
    status = order["status"]
    if status == "processing":
        return True, "Order has not shipped yet; it can be cancelled for a full refund.", order["total"]
    if status == "shipped":
        return False, "Order is still in transit. It cannot be cancelled; the customer can return it after delivery.", 0.0
    days = order["delivered_days_ago"]
    final_sale = any(i["final_sale"] for i in order["items"])
    if reason in ("damaged", "wrong_item"):
        if days <= 7:
            return True, f"Reported {days} days after delivery (limit is 7 days). Full refund applies.", order["total"]
        return False, f"Reported {days} days after delivery; the limit for damaged/wrong items is 7 days.", 0.0
    if reason == "changed_mind":
        if final_sale:
            return False, "Contains a final sale item, which cannot be returned for change of mind.", 0.0
        if days <= 30:
            return True, f"Within the 30-day return window ({days} days since delivery).", order["total"]
        return False, f"Delivered {days} days ago; the return window is 30 days.", 0.0
    return False, "Reason not recognised for automatic refund; escalate to a human.", 0.0


@tool
def lookup_order(order_id: str, email: str) -> str:
    """Get order details (status, items, total). Requires BOTH the order ID and the
    customer's email for identity verification. Never call without both."""
    o = _verified_order(order_id, email)
    if not o:
        return NOT_FOUND
    return json.dumps({k: o[k] for k in ("order_id", "status", "items", "total", "delivered_days_ago")})


@tool
def track_shipment(order_id: str, email: str) -> str:
    """Get shipment tracking events for an order. Requires order ID and customer email."""
    o = _verified_order(order_id, email)
    if not o:
        return NOT_FOUND
    return json.dumps({"order_id": o["order_id"], "status": o["status"], "events": o["tracking"]})


@tool
def search_policies(question: str) -> str:
    """Search company policies (returns, refunds, shipping, warranty). Use this for ANY
    policy question and quote what it returns; never answer policy questions from memory."""
    from app.rag import search
    hits = search(question)
    return "\n\n".join(f"[{h['source']}]\n{h['text']}" for h in hits)


@tool
def check_refund_eligibility(order_id: str, email: str, reason: str) -> str:
    """Check whether an order qualifies for a refund WITHOUT creating one.
    reason must be one of: damaged, wrong_item, changed_mind."""
    o = _verified_order(order_id, email)
    if not o:
        return NOT_FOUND
    ok, why, amt = evaluate_refund(o, reason)
    return json.dumps({"eligible": ok, "explanation": why, "refund_amount": amt})


@tool
def request_refund(order_id: str, email: str, reason: str) -> str:
    """Submit a refund request for human approval. Only call AFTER the customer has
    clearly confirmed they want to proceed. reason: damaged, wrong_item or changed_mind.
    This does NOT issue the refund; a human agent must approve it."""
    o = _verified_order(order_id, email)
    if not o:
        return NOT_FOUND
    ok, why, amt = evaluate_refund(o, reason)
    if not ok:
        return json.dumps({"submitted": False, "explanation": why})
    refunds = _read(config.REFUNDS_FILE, [])
    rid = "R" + uuid.uuid4().hex[:6].upper()
    refunds.append({"refund_id": rid, "order_id": o["order_id"], "reason": reason, "amount": amt,
                    "status": "pending_human_approval",
                    "created_at": datetime.now(timezone.utc).isoformat()})
    _write(config.REFUNDS_FILE, refunds)
    return json.dumps({"submitted": True, "refund_id": rid, "amount": amt,
                       "status": "pending_human_approval",
                       "note": "A support agent will review within 2 business days."})


@tool
def escalate_to_human(summary: str, order_id: str = "") -> str:
    """Hand the conversation to a human agent. Use when the customer is angry, asks for
    a human/manager, the case is outside policy, or you are unsure. Provide a short summary."""
    items = _read(config.ESCALATIONS_FILE, [])
    tid = "T" + uuid.uuid4().hex[:6].upper()
    items.append({"ticket_id": tid, "order_id": order_id, "summary": summary,
                  "created_at": datetime.now(timezone.utc).isoformat()})
    _write(config.ESCALATIONS_FILE, items)
    return json.dumps({"escalated": True, "ticket_id": tid})


TOOLS = [lookup_order, track_shipment, search_policies, check_refund_eligibility,
         request_refund, escalate_to_human]
