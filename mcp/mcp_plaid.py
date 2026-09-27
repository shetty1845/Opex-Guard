class PlaidMCPConnection:
    def __init__(self):
        self.name = "Plaid"
        self.connected = True

    def sync_transactions(self, account_id="default"):
        return {
            "account_id": account_id,
            "status": "synced",
            "transactions": [
                {"merchant": "AWS", "amount": 342.5, "date": "2026-07-02"},
                {"merchant": "Adobe", "amount": 59.98, "date": "2026-07-05"},
            ],
        }
