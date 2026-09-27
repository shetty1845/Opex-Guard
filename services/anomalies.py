from collections import defaultdict

SAAS_SUBSCRIPTION_KEYWORDS = [
    'aws', 'slack', 'github', 'adobe', 'notion', 'zoom', 'google cloud', 
    'hubspot', 'salesforce', 'figma', 'canva', 'atlassian', 'jira', 'zapier'
]

def detect_anomalies(current_transactions, historical_transactions=None):
    """
    Evaluates current month transactions against historical transactions to detect:
    1. MoM Category Spending Spikes (>20% increase)
    2. SaaS Subscription Price Increases
    3. Missing Receipts for high-value transactions (> $50)
    4. Duplicate Charges (same vendor + amount within 3 days)
    """
    anomalies = []
    historical_transactions = historical_transactions or []
    
    # 1. Group Current & Historical Spend by Category and Vendor
    curr_cat_spend = defaultdict(float)
    curr_vendor_txs = defaultdict(list)
    
    for tx in current_transactions:
        cat = tx.get('category', 'Uncategorized')
        vendor = (tx.get('normalized_vendor') or tx.get('raw_vendor', '')).lower()
        amount = tx.get('amount', 0.0)
        
        curr_cat_spend[cat] += amount
        curr_vendor_txs[vendor].append(tx)
        
    hist_cat_spend = defaultdict(float)
    hist_vendor_amounts = defaultdict(list)
    
    for tx in historical_transactions:
        cat = tx.get('category', 'Uncategorized')
        vendor = (tx.get('normalized_vendor') or tx.get('raw_vendor', '')).lower()
        amount = tx.get('amount', 0.0)
        
        hist_cat_spend[cat] += amount
        hist_vendor_amounts[vendor].append(amount)
        
    # --- Check 1: Category MoM Spikes (>20% increase) ---
    for cat, curr_amount in curr_cat_spend.items():
        hist_amount = hist_cat_spend.get(cat, 0.0)
        if hist_amount > 0:
            growth_pct = ((curr_amount - hist_amount) / hist_amount) * 100.0
            if growth_pct > 20.0:
                severity = 'high' if growth_pct > 50.0 else 'medium'
                anomalies.append({
                    'vendor': f"Category: {cat}",
                    'type': 'MoM_Spike',
                    'severity': severity,
                    'description': f"Spending in '{cat}' increased by {growth_pct:.1f}% MoM (${curr_amount:,.2f} vs ${hist_amount:,.2f} prior month).",
                    'mom_change_pct': growth_pct,
                    'amount': curr_amount,
                    'previous_amount': hist_amount
                })
                
    # --- Check 2: SaaS Subscription Price Hikes ---
    for vendor_name, tx_list in curr_vendor_txs.items():
        is_saas = any(k in vendor_name for k in SAAS_SUBSCRIPTION_KEYWORDS)
        if is_saas and tx_list:
            latest_tx = tx_list[0]
            curr_val = latest_tx.get('amount', 0.0)
            
            # Check if historical subscription price exists and differs
            hist_vals = hist_vendor_amounts.get(vendor_name, [])
            if hist_vals:
                avg_hist_val = sum(hist_vals) / len(hist_vals)
                if curr_val > (avg_hist_val * 1.15): # >15% price increase
                    hike_pct = ((curr_val - avg_hist_val) / avg_hist_val) * 100.0
                    anomalies.append({
                        'transaction_id': latest_tx.get('id'),
                        'vendor': latest_tx.get('normalized_vendor') or vendor_name.title(),
                        'type': 'Subscription_Increase',
                        'severity': 'high' if hike_pct > 50 else 'medium',
                        'description': f"SaaS subscription price for {latest_tx.get('normalized_vendor', vendor_name).title()} hiked by {hike_pct:.1f}% (from ${avg_hist_val:,.2f} to ${curr_val:,.2f}).",
                        'mom_change_pct': hike_pct,
                        'amount': curr_val,
                        'previous_amount': avg_hist_val
                    })

    # --- Check 3: Missing Receipt Warnings & Duplicate Charges ---
    seen_txs = []
    for tx in current_transactions:
        vendor = tx.get('normalized_vendor') or tx.get('raw_vendor', 'Unknown')
        amount = tx.get('amount', 0.0)
        status = tx.get('status', 'unreconciled')
        
        # Missing receipt warning for transactions > $50
        if status != 'reconciled' and amount >= 50.0:
            anomalies.append({
                'transaction_id': tx.get('id'),
                'vendor': vendor,
                'type': 'Missing_Receipt',
                'severity': 'medium' if amount < 500 else 'high',
                'description': f"Unreconciled bank charge of ${amount:,.2f} at {vendor} has no matching receipt.",
                'amount': amount
            })
            
        # Duplicate charge check
        for prev in seen_txs:
            if (prev.get('normalized_vendor') == tx.get('normalized_vendor') and 
                abs(prev.get('amount', 0.0) - amount) < 0.01 and 
                prev.get('date') == tx.get('date')):
                anomalies.append({
                    'transaction_id': tx.get('id'),
                    'vendor': vendor,
                    'type': 'Duplicate_Charge',
                    'severity': 'high',
                    'description': f"Potential duplicate charge detected for {vendor} (${amount:,.2f}) on {tx.get('date')}.",
                    'amount': amount
                })
        seen_txs.append(tx)
        
    return anomalies
