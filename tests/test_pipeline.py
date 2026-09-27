import unittest
import os
import sys

# Ensure d:\OpEx_Guard is in python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))

from app import app, db
from models import BankTransaction, Receipt, Anomaly, CategoryRule, ExecutiveSummary, ActionQueue, PendingEmailAction
from agent.workflow import run_expense_review

class OpExGuardTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_agentic_workflow_pipeline(self):
        raw_txs = [
            {'date': '2026-07-02', 'month': '2026-07', 'raw_vendor': 'AWS POS DEBIT', 'amount': 342.50},
            {'date': '2026-07-05', 'month': '2026-07', 'raw_vendor': 'ADOBE CREATIVE', 'amount': 59.98},
            {'date': '2026-07-08', 'month': '2026-07', 'raw_vendor': 'GOOGLE ADS', 'amount': 1250.00}
        ]
        raw_rcs = [
            {'vendor': 'AWS', 'amount': 342.50, 'date': '2026-07-02', 'raw_text': 'AWS Cloud Invoice $342.50', 'file_path': 'aws.txt'}
        ]
        hist_txs = [
            {'date': '2026-06-05', 'month': '2026-06', 'raw_vendor': 'ADOBE CREATIVE', 'normalized_vendor': 'Adobe', 'amount': 29.99, 'category': 'SaaS & Software'}
        ]

        state = run_expense_review(raw_txs, raw_rcs, hist_txs)

        self.assertIn('summary', state)
        self.assertEqual(len(state['parsed_transactions']), 3)
        self.assertEqual(len(state['reconciled_matches']), 1)
        self.assertGreater(len(state['anomalies']), 0)

    def test_seed_api_endpoint(self):
        res = self.client.post('/api/seed')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])

        with app.app_context():
            tx_count = BankTransaction.query.count()
            anom_count = Anomaly.query.count()
            self.assertGreater(tx_count, 0)
            self.assertGreater(anom_count, 0)

    def test_category_feedback_api(self):
        self.client.post('/api/seed')
        with app.app_context():
            tx = BankTransaction.query.first()
            tx_id = tx.id
            
        res = self.client.post('/api/feedback/categorize', json={
            'transaction_id': tx_id,
            'category': 'Marketing & Ads',
            'save_rule': True
        })
        self.assertEqual(res.status_code, 200)

        with app.app_context():
            updated_tx = db.session.get(BankTransaction, tx_id)
            self.assertEqual(updated_tx.category, 'Marketing & Ads')
            rule = CategoryRule.query.filter_by(vendor_pattern=updated_tx.normalized_vendor.lower()).first()
            self.assertIsNotNone(rule)

    def test_actions_page_and_hitl_approval(self):
        self.client.post('/api/seed')

        res = self.client.get('/actions')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Action Queue', res.data)

        with app.app_context():
            action = ActionQueue.query.filter_by(status='pending').first()
            self.assertIsNotNone(action)
            action_id = action.id

        approve_res = self.client.post(f'/api/actions/{action_id}/approve', json={'note': 'Approved by test'})
        self.assertEqual(approve_res.status_code, 200)

        with app.app_context():
            updated_action = db.session.get(ActionQueue, action_id)
            self.assertEqual(updated_action.status, 'approved')

    def test_scan_inbox_creates_pending_email_actions(self):
        res = self.client.post('/api/scan-inbox')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertGreater(data['count'], 0)

        with app.app_context():
            pending_items = PendingEmailAction.query.filter_by(status='pending_review').all()
            self.assertGreater(len(pending_items), 0)

    def test_email_action_approval_creates_transaction(self):
        self.client.post('/api/scan-inbox')

        with app.app_context():
            pending_item = PendingEmailAction.query.filter_by(status='pending_review').first()
            self.assertIsNotNone(pending_item)
            item_id = pending_item.id

        res = self.client.post(f'/api/email-actions/{item_id}/approve', json={'category': 'SaaS & Software'})
        self.assertEqual(res.status_code, 200)

        with app.app_context():
            updated_item = db.session.get(PendingEmailAction, item_id)
            self.assertEqual(updated_item.status, 'approved')
            created_tx = BankTransaction.query.filter_by(raw_vendor=updated_item.parsed_vendor).first()
            self.assertIsNotNone(created_tx)

if __name__ == '__main__':
    unittest.main()
