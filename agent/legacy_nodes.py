from agent.state import ExpenseReviewState
from services.ingestion import normalize_vendor, categorize_vendor
from services.reconciliation import reconcile_transactions_with_receipts
from services.anomalies import detect_anomalies
from services.summary import generate_executive_summary

def parse_node(state: ExpenseReviewState) -> ExpenseReviewState:
    """
    State Graph Node 1: Normalizes vendor names and applies categorization rules.
    """
    raw_txs = state.get("raw_transactions", [])
    raw_rcs = state.get("raw_receipts", [])
    rules = state.get("custom_rules", {})
    
    parsed_txs = []
    for tx in raw_txs:
        normalized = tx.get("normalized_vendor") or normalize_vendor(tx.get("raw_vendor", ""))
        cat, conf = categorize_vendor(normalized, rules)
        
        parsed_tx = dict(tx)
        parsed_tx["normalized_vendor"] = normalized
        parsed_tx["category"] = tx.get("category") if tx.get("category") and tx.get("category") != 'Uncategorized' else cat
        parsed_tx["confidence"] = conf
        parsed_txs.append(parsed_tx)
        
    parsed_rcs = []
    for rc in raw_rcs:
        parsed_rc = dict(rc)
        parsed_rc["vendor"] = normalize_vendor(rc.get("vendor", ""))
        parsed_rcs.append(parsed_rc)
        
    state["parsed_transactions"] = parsed_txs
    state["parsed_receipts"] = parsed_rcs
    return state

def reconcile_node(state: ExpenseReviewState) -> ExpenseReviewState:
    """
    State Graph Node 2: Reconciles parsed transactions with receipts.
    """
    txs = state.get("parsed_transactions", [])
    rcs = state.get("parsed_receipts", [])
    
    updated_txs, updated_rcs, matches = reconcile_transactions_with_receipts(txs, rcs)
    
    state["parsed_transactions"] = updated_txs
    state["parsed_receipts"] = updated_rcs
    state["reconciled_matches"] = matches
    return state

def anomaly_detector_node(state: ExpenseReviewState) -> ExpenseReviewState:
    """
    State Graph Node 3: Detects spending spikes, subscription price hikes, and missing receipts.
    """
    txs = state.get("parsed_transactions", [])
    hist_txs = state.get("historical_transactions", [])
    
    anomalies = detect_anomalies(txs, hist_txs)
    
    state["anomalies"] = anomalies
    return state

def summarizer_node(state: ExpenseReviewState) -> ExpenseReviewState:
    """
    State Graph Node 4: Formulates executive summary insights.
    """
    txs = state.get("parsed_transactions", [])
    anomalies = state.get("anomalies", [])
    hist_txs = state.get("historical_transactions", [])
    
    summary = generate_executive_summary(txs, anomalies, hist_txs)
    state["summary"] = summary
    return state
