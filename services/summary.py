from collections import defaultdict

def generate_executive_summary(current_transactions, anomalies, historical_transactions=None):
    """
    Generates a structured 2-Minute Executive Summary.
    """
    total_spend = sum(t.get('amount', 0.0) for t in current_transactions)
    reconciled_count = sum(1 for t in current_transactions if t.get('status') == 'reconciled')
    total_count = len(current_transactions)
    reconciled_pct = (reconciled_count / total_count * 100.0) if total_count > 0 else 0.0
    
    # Calculate MoM growth %
    hist_total_spend = sum(t.get('amount', 0.0) for t in (historical_transactions or []))
    if hist_total_spend > 0:
        mom_growth_pct = ((total_spend - hist_total_spend) / hist_total_spend) * 100.0
    else:
        mom_growth_pct = 0.0
        
    # Top spend categories
    cat_totals = defaultdict(float)
    for t in current_transactions:
        cat_totals[t.get('category', 'Uncategorized')] += t.get('amount', 0.0)
        
    top_categories = sorted(
        [{'category': k, 'amount': round(v, 2), 'pct': round((v / total_spend * 100.0) if total_spend > 0 else 0, 1)} 
         for k, v in cat_totals.items()],
        key=lambda x: x['amount'],
        reverse=True
    )[:5]

    # Format summary text bullets
    summary_bullets = []
    
    summary_bullets.append(f"💰 **Total Spend:** ${total_spend:,.2f} across {total_count} transactions ({reconciled_pct:.1f}% reconciled with audit receipts).")
    
    if hist_total_spend > 0:
        trend_direction = "increased" if mom_growth_pct >= 0 else "decreased"
        summary_bullets.append(f"📈 **MoM Spend Trend:** Overall spending {trend_direction} by {abs(mom_growth_pct):.1f}% compared to prior month (${hist_total_spend:,.2f}).")
        
    if top_categories:
        top_cat = top_categories[0]
        summary_bullets.append(f"🏆 **Primary Cost Driver:** '{top_cat['category']}' represents the largest expense bucket at ${top_cat['amount']:,.2f} ({top_cat['pct']}% of total budget).")
        
    # Key Anomalies Highlights
    unresolved_anomalies = [a for a in anomalies if not a.get('resolved', False)]
    high_anomalies = [a for a in unresolved_anomalies if a.get('severity') == 'high']
    saas_hikes = [a for a in unresolved_anomalies if a.get('type') == 'Subscription_Increase']
    missing_receipts = [a for a in unresolved_anomalies if a.get('type') == 'Missing_Receipt']

    if high_anomalies:
        summary_bullets.append(f"🚨 **Critical Alerts:** {len(high_anomalies)} high-severity anomalies detected requiring immediate review.")
        
    if saas_hikes:
        hike_names = ", ".join([a.get('vendor', 'Unknown') for a in saas_hikes[:3]])
        summary_bullets.append(f"⚡ **Subscription Hikes:** Price increases identified for recurring SaaS providers: {hike_names}.")
        
    if missing_receipts:
        missing_total = sum(a.get('amount', 0.0) for a in missing_receipts)
        summary_bullets.append(f"📄 **Audit Warning:** {len(missing_receipts)} high-value bank transactions (${missing_total:,.2f} total) lack supporting receipt documentation.")

    summary_text = "\n\n".join(summary_bullets)
    
    return {
        'total_spend': total_spend,
        'mom_growth_pct': mom_growth_pct,
        'reconciled_pct': reconciled_pct,
        'anomalies_count': len(unresolved_anomalies),
        'top_categories': top_categories,
        'top_anomalies': [a.get('description') for a in unresolved_anomalies[:5]],
        'summary_text': summary_text
    }
