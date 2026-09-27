from agent.state import ExpenseReviewState
from services.reconciliation import reconcile_transactions_with_receipts


def reconcile_node(state: ExpenseReviewState) -> ExpenseReviewState:
    txs = state.get("parsed_transactions", [])
    rcs = state.get("parsed_receipts", [])
    updated_txs, updated_rcs, matches = reconcile_transactions_with_receipts(txs, rcs)
    state["parsed_transactions"] = updated_txs
    state["parsed_receipts"] = updated_rcs
    state["reconciled_matches"] = matches
    return state
