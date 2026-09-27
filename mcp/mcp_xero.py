class XeroMCPConnection:
    def __init__(self):
        self.name = "Xero"
        self.connected = True

    def post_entry(self, vendor, amount, memo):
        return {
            "vendor": vendor,
            "amount": amount,
            "memo": memo,
            "posted": True,
        }
