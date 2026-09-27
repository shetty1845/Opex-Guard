from agent.state import ExpenseReviewState
from mcp.mcp_gmail import GmailMCPConnection
from mcp.mcp_slack import SlackMCPConnection
from mcp.mcp_xero import XeroMCPConnection
from workflows.hitl import build_action_queue


def action_orchestrator_node(state: ExpenseReviewState) -> ExpenseReviewState:
    anomalies = state.get("anomalies", [])
    txs = state.get("parsed_transactions", [])
    gmail = GmailMCPConnection()
    slack = SlackMCPConnection()
    xero = XeroMCPConnection()

    actions = build_action_queue(
        anomalies=anomalies,
        transactions=txs,
        gmail_client=gmail,
        slack_client=slack,
        xero_client=xero,
    )
    state["actions"] = actions
    return state
