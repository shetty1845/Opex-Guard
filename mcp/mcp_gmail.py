import os


class GmailMCPConnection:
    def __init__(self):
        self.name = "Gmail"
        self.connected = True

    def search_receipts(self, vendor, amount, date):
        return {
            "vendor": vendor,
            "amount": amount,
            "date": date,
            "found": False,
            "snippet": "No matching receipt attachment found in inbox.",
        }

    def scan_mock_inbox(self):
        base_dir = os.path.join('static', 'uploads', 'receipts')
        os.makedirs(base_dir, exist_ok=True)

        sample_items = [
            {
                'email_sender': 'receipts@stripe.com',
                'email_subject': 'Receipt: Stripe payment received',
                'email_date': '2026-07-10',
                'parsed_vendor': 'Stripe',
                'parsed_amount': 129.0,
                'parsed_currency': 'USD',
                'parsed_category': 'Payment Processing',
                'parsed_date': '2026-07-10',
                'attachment_path': os.path.join(base_dir, 'stripe_receipt.pdf')
            },
            {
                'email_sender': 'billing@aws.amazon.com',
                'email_subject': 'Invoice: AWS monthly billing',
                'email_date': '2026-07-12',
                'parsed_vendor': 'AWS',
                'parsed_amount': 342.5,
                'parsed_currency': 'USD',
                'parsed_category': 'SaaS & Software',
                'parsed_date': '2026-07-12',
                'attachment_path': os.path.join(base_dir, 'aws_invoice.pdf')
            },
            {
                'email_sender': 'receipts@uber.com',
                'email_subject': 'Order Confirmation: Uber ride',
                'email_date': '2026-07-13',
                'parsed_vendor': 'Uber',
                'parsed_amount': 24.5,
                'parsed_currency': 'USD',
                'parsed_category': 'Travel & Entertainment',
                'parsed_date': '2026-07-13',
                'attachment_path': os.path.join(base_dir, 'uber_receipt.png')
            }
        ]
        return sample_items
