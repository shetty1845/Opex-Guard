class SlackMCPConnection:
    def __init__(self):
        self.name = "Slack"
        self.connected = True

    def post_notification(self, message, channel="#finance-ops"):
        return {
            "channel": channel,
            "message": message,
            "posted": True,
        }
