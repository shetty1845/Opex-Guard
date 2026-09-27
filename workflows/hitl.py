from mcp.mcp_gmail import GmailMCPConnection
from mcp.mcp_slack import SlackMCPConnection
from mcp.mcp_xero import XeroMCPConnection


def build_action_queue(anomalies, transactions, gmail_client=None, slack_client=None, xero_client=None):
    gmail_client = gmail_client or GmailMCPConnection()
    slack_client = slack_client or SlackMCPConnection()
    xero_client = xero_client or XeroMCPConnection()

    actions = []
    for anomaly in anomalies:
        anomaly_type = anomaly.get("type", "")
        vendor = anomaly.get("vendor", "Unknown")
        amount = anomaly.get("amount", 0.0)
        tx_id = anomaly.get("transaction_id")

        if anomaly_type == "Missing_Receipt":
            search_result = gmail_client.search_receipts(vendor, amount, "")
            action = {
                "type": "receipt_followup",
                "title": f"Request missing receipt for {vendor}",
                "description": f"No receipt was found for a ${amount:,.2f} charge. Draft a Slack reminder for the cardholder.",
                "status": "pending",
                "payload": {
                    "vendor": vendor,
                    "amount": amount,
                    "slack_message": f"Please share the receipt for {vendor} (${amount:,.2f}) so it can be reconciled.",
                    "gmail_search": search_result,
                },
            }
            if tx_id is not None:
                action["transaction_id"] = tx_id
            actions.append(action)

        elif anomaly_type == "Duplicate_Charge":
            action = {
                "type": "duplicate_dispute",
                "title": f"Draft dispute email for {vendor}",
                "description": f"Prepare a dispute draft for the duplicate charge of ${amount:,.2f}.",
                "status": "pending",
                "payload": {
                    "vendor": vendor,
                    "amount": amount,
                    "email_body": (
                        f"Dear {vendor} Support,\n\n"
                        f"I am disputing a duplicate charge for ${amount:,.2f}. Please review the transaction and advise on resolution.\n\n"
                        "Best regards,\nFinance Ops"
                    ),
                },
            }
            if tx_id is not None:
                action["transaction_id"] = tx_id
            actions.append(action)

        elif anomaly_type == "Subscription_Increase":
            action = {
                "type": "xero_post",
                "title": f"Post verified adjustment for {vendor}",
                "description": "Record the verified subscription adjustment in the general ledger.",
                "status": "pending",
                "payload": {
                    "vendor": vendor,
                    "amount": amount,
                    "memo": f"Verified adjustment for {vendor}",
                },
            }
            if tx_id is not None:
                action["transaction_id"] = tx_id
            actions.append(action)

    if not actions:
        actions.append({
            "type": "manual_review",
            "title": "No actions required",
            "description": "The current review did not generate any agent actions.",
            "status": "pending",
            "payload": {},
        })

    return actions
