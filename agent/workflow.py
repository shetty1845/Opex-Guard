from langgraph.graph import StateGraph, START, END
from agent.state import ExpenseReviewState
from agent.nodes import parse_node, reconcile_node, anomaly_detector_node


def build_expense_review_graph():
    """
    Assembles the LangGraph StateGraph pipeline for OpEx_Guard.
    """
    workflow = StateGraph(ExpenseReviewState)

    workflow.add_node("parser", parse_node)
    workflow.add_node("reconciler", reconcile_node)
    workflow.add_node("anomaly_detector", anomaly_detector_node)

    workflow.add_edge(START, "parser")
    workflow.add_edge("parser", "reconciler")
    workflow.add_edge("reconciler", "anomaly_detector")
    workflow.add_edge("anomaly_detector", END)

    return workflow.compile()


expense_review_app = build_expense_review_graph()


def run_expense_review(raw_transactions, raw_receipts, historical_transactions=None, custom_rules=None):
    """
    Convenience function to execute the compiled LangGraph state workflow.
    """
    initial_state: ExpenseReviewState = {
        "raw_transactions": raw_transactions or [],
        "raw_receipts": raw_receipts or [],
        "historical_transactions": historical_transactions or [],
        "custom_rules": custom_rules or {},
        "parsed_transactions": [],
        "parsed_receipts": [],
        "reconciled_matches": [],
        "anomalies": [],
        "actions": [],
        "summary": {},
        "error": None
    }

    return expense_review_app.invoke(initial_state)
