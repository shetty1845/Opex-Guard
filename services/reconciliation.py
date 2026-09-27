from datetime import datetime
from difflib import SequenceMatcher

def string_similarity(a, b):
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def days_between(date_str1, date_str2):
    try:
        d1 = datetime.strptime(date_str1, '%Y-%m-%d')
        d2 = datetime.strptime(date_str2, '%Y-%m-%d')
        return abs((d1 - d2).days)
    except Exception:
        return 999

def reconcile_transactions_with_receipts(transactions, receipts):
    """
    Reconciles list of BankTransaction dicts/objects with list of Receipt dicts/objects.
    Returns matched pairs, confidence scores, and updated statuses.
    """
    reconciled_matches = []
    unmatched_receipts = list(receipts)
    
    for tx in transactions:
        tx_vendor = tx.get('normalized_vendor') or tx.get('raw_vendor', '')
        tx_amount = tx.get('amount', 0.0)
        tx_date = tx.get('date', '')
        
        best_match = None
        best_score = 0.0
        
        for rc in unmatched_receipts:
            rc_vendor = rc.get('vendor', '')
            rc_amount = rc.get('amount', 0.0)
            rc_date = rc.get('date', '')
            
            # Amount score (exact match = 1.0, close match = delta ratio)
            amount_diff = abs(tx_amount - rc_amount)
            if amount_diff < 0.01:
                amount_score = 1.0
            elif amount_diff <= (tx_amount * 0.1): # within 10% or tax variance
                amount_score = 0.8
            else:
                amount_score = 0.0
                
            # Vendor similarity score
            vendor_score = string_similarity(tx_vendor, rc_vendor)
            
            # Date proximity score (within 5 days)
            days_diff = days_between(tx_date, rc_date) if tx_date and rc_date else 0
            if days_diff <= 2:
                date_score = 1.0
            elif days_diff <= 5:
                date_score = 0.7
            else:
                date_score = 0.3
                
            # Combined match score (weight: Amount 50%, Vendor 35%, Date 15%)
            total_score = (amount_score * 0.50) + (vendor_score * 0.35) + (date_score * 0.15)
            
            if total_score > best_score and total_score >= 0.65:
                best_score = total_score
                best_match = rc
                
        if best_match:
            tx['status'] = 'reconciled'
            tx['matched_receipt'] = best_match
            tx['matched_receipt_id'] = best_match.get('id')
            tx['confidence'] = best_score
            best_match['status'] = 'matched'
            unmatched_receipts.remove(best_match)
            reconciled_matches.append({
                'transaction': tx,
                'receipt': best_match,
                'match_confidence': best_score
            })
        else:
            if tx.get('status') != 'flagged':
                tx['status'] = 'unreconciled'

    return transactions, receipts, reconciled_matches
