from langgraph.graph import StateGraph, START, END

from agent.state import ExpenseReviewState
from agent.nodes.parser_agent import parse_node
from agent.nodes.recon_agent import reconcile_node
from agent.nodes.auditor_agent import anomaly_detector_node
from agent.nodes.action_agent import action_orchestrator_node


def build_expense_review_graph():
    workflow = StateGraph(ExpenseReviewState)
    workflow.add_node("parser", parse_node)
    workflow.add_node("reconciler", reconcile_node)
    workflow.add_node("auditor", anomaly_detector_node)
    workflow.add_node("action_orchestrator", action_orchestrator_node)
    workflow.add_edge(START, "parser")
    workflow.add_edge("parser", "reconciler")
    workflow.add_edge("reconciler", "auditor")
    workflow.add_edge("auditor", "action_orchestrator")
    workflow.add_edge("action_orchestrator", END)
    return workflow.compile()


expense_review_app = build_expense_review_graph()


def run_expense_review(raw_transactions, raw_receipts, historical_transactions=None, custom_rules=None):
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
        "error": None,
    }
    return expense_review_app.invoke(initial_state)
