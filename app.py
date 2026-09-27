import json
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from models import db, BankTransaction, Receipt, Anomaly, CategoryRule, ExecutiveSummary, ActionQueue, PendingEmailAction
from services.ingestion import parse_bank_statement_csv, parse_receipt_file
from agent.orchestrator import run_expense_review
from mcp.mcp_gmail import GmailMCPConnection

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'opex_guard_secret_key_2026_secure')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///opex_guard.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

with app.app_context():
    db.create_all()

def get_custom_rules_map():
    rules = CategoryRule.query.all()
    return {r.vendor_pattern.lower(): r.category for r in rules}

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    summary_obj = ExecutiveSummary.query.order_by(ExecutiveSummary.id.desc()).first()
    summary = summary_obj.to_dict() if summary_obj else None
    
    active_month = summary['month'] if summary else '2026-07'
    
    # Filter transactions strictly by active month so UI metrics are 100% consistent!
    transactions = BankTransaction.query.filter_by(month=active_month).order_by(BankTransaction.date.desc()).all()
    tx_dicts = [t.to_dict() for t in transactions]
    
    reconciled_count = sum(1 for t in tx_dicts if t['status'] == 'reconciled')
    total_count = len(tx_dicts)
    
    # Scoped active unresolved anomalies for active month
    active_anomalies = Anomaly.query.filter_by(resolved=False, month=active_month).all()
    
    return render_template(
        'dashboard.html',
        summary=summary,
        transactions=tx_dicts,
        reconciled_count=reconciled_count,
        total_count=total_count,
        active_anomalies_count=len(active_anomalies)
    )

@app.route('/upload', methods=['GET', 'POST'])
def upload_page():
    summary_obj = ExecutiveSummary.query.order_by(ExecutiveSummary.id.desc()).first()
    active_month = summary_obj.month if summary_obj else '2026-07'

    if request.method == 'POST':
        statement_file = request.files.get('statement_file')
        receipt_files = request.files.getlist('receipt_files')
        
        parsed_txs = []
        parsed_rcs = []
        custom_rules = get_custom_rules_map()
        
        if statement_file and statement_file.filename:
            content = statement_file.read().decode('utf-8', errors='ignore')
            parsed_txs = parse_bank_statement_csv(content, custom_rules)
            
        for rf in receipt_files:
            if rf and rf.filename:
                file_bytes = rf.read()
                rc_dict = parse_receipt_file(file_bytes, rf.filename)
                parsed_rcs.append(rc_dict)
                
        if parsed_txs:
            # Fetch existing historical transactions for MoM comparison
            hist_txs = [t.to_dict() for t in BankTransaction.query.all()]
            
            # Execute LangGraph Workflow
            graph_result = run_expense_review(
                raw_transactions=parsed_txs,
                raw_receipts=parsed_rcs,
                historical_transactions=hist_txs,
                custom_rules=custom_rules
            )
            
            # Persist Receipts
            receipt_id_map = {}
            for rc in graph_result.get('parsed_receipts', []):
                db_rc = Receipt(
                    vendor=rc.get('vendor'),
                    amount=rc.get('amount', 0.0),
                    tax=rc.get('tax', 0.0),
                    raw_text=rc.get('raw_text', ''),
                    file_path=rc.get('file_path', ''),
                    status=rc.get('status', 'unmatched')
                )
                db.session.add(db_rc)
                db.session.flush()
                receipt_id_map[rc.get('file_path')] = db_rc.id
                
            # Persist Transactions
            for tx in graph_result.get('parsed_transactions', []):
                matched_rc_path = tx.get('matched_receipt', {}).get('file_path') if tx.get('matched_receipt') else None
                matched_rc_id = receipt_id_map.get(matched_rc_path) if matched_rc_path else tx.get('matched_receipt_id')
                
                db_tx = BankTransaction(
                    date=tx.get('date'),
                    month=tx.get('month'),
                    raw_vendor=tx.get('raw_vendor'),
                    normalized_vendor=tx.get('normalized_vendor'),
                    amount=tx.get('amount'),
                    category=tx.get('category', 'Uncategorized'),
                    confidence=tx.get('confidence', 1.0),
                    status=tx.get('status', 'unreconciled'),
                    matched_receipt_id=matched_rc_id
                )
                db.session.add(db_tx)
                db.session.flush()
                
                # Link anomalies if present
                for a in graph_result.get('anomalies', []):
                    if a.get('vendor') == tx.get('normalized_vendor') or a.get('transaction_id') == tx.get('id'):
                        db_anomaly = Anomaly(
                            transaction_id=db_tx.id,
                            month=tx.get('month', '2026-07'),
                            vendor=a.get('vendor', db_tx.normalized_vendor),
                            type=a.get('type'),
                            severity=a.get('severity', 'medium'),
                            description=a.get('description'),
                            mom_change_pct=a.get('mom_change_pct'),
                            amount=a.get('amount'),
                            previous_amount=a.get('previous_amount')
                        )
                        db.session.add(db_anomaly)

            # Persist Executive Summary
            sum_data = graph_result.get('summary', {})
            exec_sum = ExecutiveSummary(
                month=parsed_txs[0].get('month', '2026-07'),
                total_spend=sum_data.get('total_spend', 0.0),
                mom_growth_pct=sum_data.get('mom_growth_pct', 0.0),
                reconciled_pct=sum_data.get('reconciled_pct', 0.0),
                anomalies_count=sum_data.get('anomalies_count', 0),
                top_categories_json=json.dumps(sum_data.get('top_categories', [])),
                top_anomalies_json=json.dumps(sum_data.get('top_anomalies', [])),
                summary_text=sum_data.get('summary_text', '')
            )
            db.session.add(exec_sum)
            db.session.commit()
            
            return redirect(url_for('dashboard'))

    active_anomalies = Anomaly.query.filter_by(resolved=False, month=active_month).all()
    return render_template('upload.html', active_anomalies_count=len(active_anomalies))

@app.route('/transactions')
def transactions_page():
    summary_obj = ExecutiveSummary.query.order_by(ExecutiveSummary.id.desc()).first()
    active_month = summary_obj.month if summary_obj else '2026-07'
    
    transactions = BankTransaction.query.filter_by(month=active_month).order_by(BankTransaction.date.desc()).all()
    tx_dicts = [t.to_dict() for t in transactions]
    active_anomalies = Anomaly.query.filter_by(resolved=False, month=active_month).all()
    return render_template('transactions.html', transactions=tx_dicts, active_anomalies_count=len(active_anomalies))

@app.route('/anomalies')
def anomalies_page():
    summary_obj = ExecutiveSummary.query.order_by(ExecutiveSummary.id.desc()).first()
    active_month = summary_obj.month if summary_obj else '2026-07'
    
    anomalies = Anomaly.query.filter_by(month=active_month).order_by(Anomaly.resolved.asc(), Anomaly.id.desc()).all()
    anom_dicts = [a.to_dict() for a in anomalies]
    active_anomalies = Anomaly.query.filter_by(resolved=False, month=active_month).all()
    return render_template('anomalies.html', anomalies=anom_dicts, active_anomalies_count=len(active_anomalies))

@app.route('/actions')
def actions_page():
    summary_obj = ExecutiveSummary.query.order_by(ExecutiveSummary.id.desc()).first()
    active_month = summary_obj.month if summary_obj else '2026-07'
    active_anomalies = Anomaly.query.filter_by(resolved=False, month=active_month).all()
    actions = ActionQueue.query.order_by(ActionQueue.created_at.desc()).all()
    inbox_items = PendingEmailAction.query.order_by(PendingEmailAction.created_at.desc()).all()
    return render_template(
        'actions.html',
        actions=[a.to_dict() for a in actions],
        inbox_items=[i.to_dict() for i in inbox_items],
        active_anomalies_count=len(active_anomalies)
    )

@app.route('/api/scan-inbox', methods=['POST'])
def scan_inbox():
    try:
        client = GmailMCPConnection()
        parsed_items = client.scan_mock_inbox()

        os.makedirs(os.path.join('static', 'uploads', 'receipts'), exist_ok=True)
        created = []
        for item in parsed_items:
            existing = PendingEmailAction.query.filter_by(email_subject=item['email_subject'], email_sender=item['email_sender']).first()
            if existing:
                continue

            attachment_path = item.get('attachment_path', '')
            if attachment_path:
                attachment_dir = os.path.dirname(attachment_path)
                if attachment_dir:
                    os.makedirs(attachment_dir, exist_ok=True)
                if not os.path.exists(attachment_path):
                    with open(attachment_path, 'a', encoding='utf-8'):
                        pass

            email_action = PendingEmailAction(
                email_sender=item['email_sender'],
                email_subject=item['email_subject'],
                email_date=item['email_date'],
                parsed_vendor=item['parsed_vendor'],
                parsed_amount=item['parsed_amount'],
                parsed_currency=item['parsed_currency'],
                parsed_category=item['parsed_category'],
                parsed_date=item['parsed_date'],
                attachment_path=attachment_path,
                status='pending_review'
            )
            db.session.add(email_action)
            db.session.flush()
            created.append(email_action.to_dict())

        db.session.commit()
        return jsonify({'success': True, 'count': len(created), 'items': created})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/seed', methods=['POST'])
def seed_sample_data():
    """
    Seeds sample bank statements (June baseline & July statement) and receipts,
    executes the LangGraph state graph review, and persists to SQLite.
    """
    try:
        # Clear existing tables for clean seed test
        db.drop_all()
        db.create_all()

        june_path = os.path.join('sample_data', 'bank_statement_june.csv')
        july_path = os.path.join('sample_data', 'bank_statement_july.csv')
        receipts_dir = os.path.join('sample_data', 'sample_receipts')
        
        custom_rules = get_custom_rules_map()

        # Parse June baseline
        june_txs = []
        if os.path.exists(june_path):
            with open(june_path, 'r', encoding='utf-8') as f:
                june_txs = parse_bank_statement_csv(f.read(), custom_rules)
                
        # Parse July current statement
        july_txs = []
        if os.path.exists(july_path):
            with open(july_path, 'r', encoding='utf-8') as f:
                july_txs = parse_bank_statement_csv(f.read(), custom_rules)

        # Parse sample receipts
        sample_rcs = []
        if os.path.exists(receipts_dir):
            for fn in os.listdir(receipts_dir):
                fp = os.path.join(receipts_dir, fn)
                with open(fp, 'r', encoding='utf-8') as f:
                    text = f.read()
                    rc = parse_receipt_file(text.encode('utf-8'), fn, text_content=text)
                    sample_rcs.append(rc)

        # 1. Run June baseline through workflow first
        graph_june = run_expense_review(
            raw_transactions=june_txs,
            raw_receipts=[],
            historical_transactions=[],
            custom_rules=custom_rules
        )
        
        # Persist June Transactions
        june_db_txs = []
        for tx in graph_june.get('parsed_transactions', []):
            db_tx = BankTransaction(
                date=tx.get('date'),
                month=tx.get('month'),
                raw_vendor=tx.get('raw_vendor'),
                normalized_vendor=tx.get('normalized_vendor'),
                amount=tx.get('amount'),
                category=tx.get('category', 'Uncategorized'),
                confidence=tx.get('confidence', 1.0),
                status=tx.get('status', 'unreconciled')
            )
            db.session.add(db_tx)
            june_db_txs.append(db_tx)
        db.session.commit()

        # 2. Run July statement against June baseline
        hist_dicts = [t.to_dict() for t in june_db_txs]
        graph_july = run_expense_review(
            raw_transactions=july_txs,
            raw_receipts=sample_rcs,
            historical_transactions=hist_dicts,
            custom_rules=custom_rules
        )

        # Persist July Receipts
        receipt_id_map = {}
        for rc in graph_july.get('parsed_receipts', []):
            db_rc = Receipt(
                vendor=rc.get('vendor'),
                amount=rc.get('amount', 0.0),
                tax=rc.get('tax', 0.0),
                raw_text=rc.get('raw_text', ''),
                file_path=rc.get('file_path', ''),
                status=rc.get('status', 'unmatched')
            )
            db.session.add(db_rc)
            db.session.flush()
            receipt_id_map[rc.get('file_path')] = db_rc.id

        # Persist July Transactions & Link Receipts
        for tx in graph_july.get('parsed_transactions', []):
            matched_rc_path = tx.get('matched_receipt', {}).get('file_path') if tx.get('matched_receipt') else None
            matched_rc_id = receipt_id_map.get(matched_rc_path) if matched_rc_path else None
            
            db_tx = BankTransaction(
                date=tx.get('date'),
                month=tx.get('month'),
                raw_vendor=tx.get('raw_vendor'),
                normalized_vendor=tx.get('normalized_vendor'),
                amount=tx.get('amount'),
                category=tx.get('category', 'Uncategorized'),
                confidence=tx.get('confidence', 1.0),
                status=tx.get('status', 'unreconciled'),
                matched_receipt_id=matched_rc_id
            )
            db.session.add(db_tx)

        # Persist July Anomalies
        for a in graph_july.get('anomalies', []):
            db_anomaly = Anomaly(
                month='2026-07',
                vendor=a.get('vendor'),
                type=a.get('type'),
                severity=a.get('severity', 'medium'),
                description=a.get('description'),
                mom_change_pct=a.get('mom_change_pct'),
                amount=a.get('amount'),
                previous_amount=a.get('previous_amount')
            )
            db.session.add(db_anomaly)

        # Persist generated HITL actions
        persisted_actions = graph_july.get('actions', []) or [{
            'type': 'manual_review',
            'title': 'Review latest anomaly set',
            'description': 'A review action was generated for the latest expense cycle.',
            'status': 'pending',
            'payload': {}
        }]
        for action in persisted_actions:
            db_action = ActionQueue(
                type=action.get('type', 'manual_review'),
                title=action.get('title', 'Review action'),
                description=action.get('description', ''),
                status=action.get('status', 'pending'),
                payload_json=json.dumps(action.get('payload', {}))
            )
            db.session.add(db_action)

        # Persist Executive Summary
        sum_data = graph_july.get('summary', {})
        exec_sum = ExecutiveSummary(
            month='2026-07',
            total_spend=sum_data.get('total_spend', 0.0),
            mom_growth_pct=sum_data.get('mom_growth_pct', 0.0),
            reconciled_pct=sum_data.get('reconciled_pct', 0.0),
            anomalies_count=sum_data.get('anomalies_count', 0),
            top_categories_json=json.dumps(sum_data.get('top_categories', [])),
            top_anomalies_json=json.dumps(sum_data.get('top_anomalies', [])),
            summary_text=sum_data.get('summary_text', '')
        )
        db.session.add(exec_sum)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Sample data seeded and reviewed.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/feedback/categorize', methods=['POST'])
def update_category_feedback():
    data = request.get_json() or {}
    tx_id = data.get('transaction_id')
    new_category = data.get('category')
    save_rule = data.get('save_rule', True)

    if not tx_id or not new_category:
        return jsonify({'success': False, 'error': 'Missing parameters'}), 400

    tx = db.session.get(BankTransaction, tx_id)
    if not tx:
        return jsonify({'success': False, 'error': 'Transaction not found'}), 404

    tx.category = new_category
    tx.confidence = 1.0 # User confirmed

    if save_rule:
        pattern = tx.normalized_vendor.lower()
        existing_rule = CategoryRule.query.filter_by(vendor_pattern=pattern).first()
        if existing_rule:
            existing_rule.category = new_category
        else:
            rule = CategoryRule(vendor_pattern=pattern, category=new_category, user_defined=True)
            db.session.add(rule)

    db.session.commit()
    return jsonify({'success': True, 'message': 'Category updated and rule saved.'})

@app.route('/api/anomalies/<int:anomaly_id>/resolve', methods=['POST'])
def resolve_anomaly(anomaly_id):
    data = request.get_json() or {}
    note = data.get('note', 'Unflagged by user')

    anomaly = db.session.get(Anomaly, anomaly_id)
    if not anomaly:
        return jsonify({'success': False, 'error': 'Anomaly not found'}), 404

    anomaly.resolved = True
    anomaly.resolution_note = note
    db.session.commit()

    return jsonify({'success': True, 'message': 'Anomaly resolved.'})

@app.route('/api/actions/<int:action_id>/approve', methods=['POST'])
def approve_action(action_id):
    action = db.session.get(ActionQueue, action_id)
    if not action:
        return jsonify({'success': False, 'error': 'Action not found'}), 404

    action.status = 'approved'
    db.session.commit()
    return jsonify({'success': True, 'message': 'Action approved and queued for execution.'})

@app.route('/api/actions/<int:action_id>/reject', methods=['POST'])
def reject_action(action_id):
    action = db.session.get(ActionQueue, action_id)
    if not action:
        return jsonify({'success': False, 'error': 'Action not found'}), 404

    action.status = 'rejected'
    db.session.commit()
    return jsonify({'success': True, 'message': 'Action rejected.'})


@app.route('/api/email-actions/<int:item_id>/approve', methods=['POST'])
def approve_email_action(item_id):
    data = request.get_json() or {}
    pending_item = db.session.get(PendingEmailAction, item_id)
    if not pending_item:
        return jsonify({'success': False, 'error': 'Email action not found'}), 404

    if pending_item.status != 'pending_review':
        return jsonify({'success': False, 'error': 'Email action already processed'}), 400

    category = data.get('category') or pending_item.parsed_category or 'Uncategorized'
    tx = BankTransaction(
        date=pending_item.parsed_date or pending_item.email_date or '2026-07-01',
        month='2026-07',
        raw_vendor=pending_item.parsed_vendor,
        normalized_vendor=pending_item.parsed_vendor,
        amount=pending_item.parsed_amount,
        category=category,
        confidence=0.95,
        status='reconciled'
    )
    db.session.add(tx)
    db.session.flush()

    pending_item.status = 'approved'
    db.session.commit()
    return jsonify({'success': True, 'message': 'Email receipt approved and added to ledger.'})


@app.route('/api/email-actions/<int:item_id>/reject', methods=['POST'])
def reject_email_action(item_id):
    pending_item = db.session.get(PendingEmailAction, item_id)
    if not pending_item:
        return jsonify({'success': False, 'error': 'Email action not found'}), 404

    pending_item.status = 'rejected'
    db.session.commit()
    return jsonify({'success': True, 'message': 'Email receipt dismissed.'})

if __name__ == '__main__':
    print("Starting OpEx_Guard Small Business Expense Review Agent...")
    app.run(host='127.0.0.1', port=5000, debug=True)
