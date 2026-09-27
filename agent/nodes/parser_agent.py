from agent.state import ExpenseReviewState
from services.ingestion import normalize_vendor, categorize_vendor


def parse_node(state: ExpenseReviewState) -> ExpenseReviewState:
    raw_txs = state.get("raw_transactions", [])
    raw_rcs = state.get("raw_receipts", [])
    rules = state.get("custom_rules", {})

    parsed_txs = []
    for tx in raw_txs:
        normalized = tx.get("normalized_vendor") or normalize_vendor(tx.get("raw_vendor", ""))
        category, confidence = categorize_vendor(normalized, rules)
        parsed_tx = dict(tx)
        parsed_tx["normalized_vendor"] = normalized
        parsed_tx["category"] = tx.get("category") if tx.get("category") and tx.get("category") != "Uncategorized" else category
        parsed_tx["confidence"] = confidence
        parsed_txs.append(parsed_tx)

    parsed_rcs = []
    for rc in raw_rcs:
        parsed_rc = dict(rc)
        parsed_rc["vendor"] = normalize_vendor(rc.get("vendor", ""))
        parsed_rcs.append(parsed_rc)

    state["parsed_transactions"] = parsed_txs
    state["parsed_receipts"] = parsed_rcs
    return state
