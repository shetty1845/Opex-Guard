from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class BankTransaction(db.Model):
    __tablename__ = 'bank_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10), nullable=False) # YYYY-MM-DD
    month = db.Column(db.String(7), nullable=False) # YYYY-MM
    raw_vendor = db.Column(db.String(255), nullable=False)
    normalized_vendor = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100), nullable=False, default='Uncategorized')
    confidence = db.Column(db.Float, nullable=False, default=1.0)
    status = db.Column(db.String(20), nullable=False, default='unreconciled') # reconciled, unreconciled, flagged
    matched_receipt_id = db.Column(db.Integer, db.ForeignKey('receipts.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    receipt = db.relationship('Receipt', backref='transactions', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date,
            'month': self.month,
            'raw_vendor': self.raw_vendor,
            'normalized_vendor': self.normalized_vendor,
            'amount': self.amount,
            'category': self.category,
            'confidence': round(self.confidence, 2),
            'status': self.status,
            'matched_receipt_id': self.matched_receipt_id,
            'matched_receipt': self.receipt.to_dict() if self.receipt else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else ''
        }

class Receipt(db.Model):
    __tablename__ = 'receipts'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10), nullable=True) # YYYY-MM-DD
    vendor = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    tax = db.Column(db.Float, nullable=True, default=0.0)
    raw_text = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(512), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='unmatched') # matched, unmatched
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date or '',
            'vendor': self.vendor,
            'amount': self.amount,
            'tax': self.tax or 0.0,
            'raw_text': self.raw_text or '',
            'file_path': self.file_path or '',
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else ''
        }

class Anomaly(db.Model):
    __tablename__ = 'anomalies'
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('bank_transactions.id'), nullable=True)
    month = db.Column(db.String(7), nullable=False, default='2026-07') # YYYY-MM
    vendor = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50), nullable=False) # MoM_Spike, Subscription_Increase, Missing_Receipt, Duplicate_Charge
    severity = db.Column(db.String(10), nullable=False, default='medium') # high, medium, low
    description = db.Column(db.Text, nullable=False)
    mom_change_pct = db.Column(db.Float, nullable=True)
    amount = db.Column(db.Float, nullable=True)
    previous_amount = db.Column(db.Float, nullable=True)
    resolved = db.Column(db.Boolean, nullable=False, default=False)
    resolution_note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transaction = db.relationship('BankTransaction', backref='anomalies', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'month': self.month,
            'vendor': self.vendor,
            'type': self.type,
            'severity': self.severity,
            'description': self.description,
            'mom_change_pct': round(self.mom_change_pct, 1) if self.mom_change_pct is not None else None,
            'amount': self.amount,
            'previous_amount': self.previous_amount,
            'resolved': self.resolved,
            'resolution_note': self.resolution_note or '',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else ''
        }

class CategoryRule(db.Model):
    __tablename__ = 'category_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    vendor_pattern = db.Column(db.String(255), unique=True, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    user_defined = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'vendor_pattern': self.vendor_pattern,
            'category': self.category,
            'user_defined': self.user_defined
        }

class ExecutiveSummary(db.Model):
    __tablename__ = 'executive_summaries'
    
    id = db.Column(db.Integer, primary_key=True)
    month = db.Column(db.String(7), nullable=False)
    total_spend = db.Column(db.Float, nullable=False, default=0.0)
    mom_growth_pct = db.Column(db.Float, nullable=False, default=0.0)
    reconciled_pct = db.Column(db.Float, nullable=False, default=0.0)
    anomalies_count = db.Column(db.Integer, nullable=False, default=0)
    top_categories_json = db.Column(db.Text, nullable=False, default='[]')
    top_anomalies_json = db.Column(db.Text, nullable=False, default='[]')
    summary_text = db.Column(db.Text, nullable=False, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'month': self.month,
            'total_spend': round(self.total_spend, 2),
            'mom_growth_pct': round(self.mom_growth_pct, 1),
            'reconciled_pct': round(self.reconciled_pct, 1),
            'anomalies_count': self.anomalies_count,
            'top_categories': json.loads(self.top_categories_json) if self.top_categories_json else [],
            'top_anomalies': json.loads(self.top_anomalies_json) if self.top_anomalies_json else [],
            'summary_text': self.summary_text,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else ''
        }


class ActionQueue(db.Model):
    __tablename__ = 'action_queue'

    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('bank_transactions.id'), nullable=True)
    type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    payload_json = db.Column(db.Text, nullable=False, default='{}')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transaction = db.relationship('BankTransaction', backref='actions', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'type': self.type,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'payload': json.loads(self.payload_json) if self.payload_json else {},
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else ''
        }


class PendingEmailAction(db.Model):
    __tablename__ = 'pending_email_actions'

    id = db.Column(db.Integer, primary_key=True)
    email_sender = db.Column(db.String(255), nullable=False)
    email_subject = db.Column(db.String(255), nullable=False)
    email_date = db.Column(db.String(20), nullable=True)
    parsed_vendor = db.Column(db.String(255), nullable=False)
    parsed_amount = db.Column(db.Float, nullable=False, default=0.0)
    parsed_currency = db.Column(db.String(10), nullable=False, default='USD')
    parsed_category = db.Column(db.String(100), nullable=False, default='Uncategorized')
    parsed_date = db.Column(db.String(20), nullable=True)
    attachment_path = db.Column(db.String(512), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='pending_review')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'email_sender': self.email_sender,
            'email_subject': self.email_subject,
            'email_date': self.email_date or '',
            'parsed_vendor': self.parsed_vendor,
            'parsed_amount': self.parsed_amount,
            'parsed_currency': self.parsed_currency,
            'parsed_category': self.parsed_category,
            'parsed_date': self.parsed_date or '',
            'attachment_path': self.attachment_path or '',
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else ''
        }
