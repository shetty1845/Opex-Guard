from agent.state import ExpenseReviewState
from services.anomalies import detect_anomalies
from services.summary import generate_executive_summary


def anomaly_detector_node(state: ExpenseReviewState) -> ExpenseReviewState:
    txs = state.get("parsed_transactions", [])
    hist_txs = state.get("historical_transactions", [])
    anomalies = detect_anomalies(txs, hist_txs)
    state["anomalies"] = anomalies
    summary = generate_executive_summary(txs, anomalies, hist_txs)
    state["summary"] = summary
    return state
