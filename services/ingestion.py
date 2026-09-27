import csv
import io
import re
import os
from datetime import datetime

DEFAULT_CATEGORY_RULES = {
    'aws': 'SaaS & Software',
    'amazon web services': 'SaaS & Software',
    'slack': 'SaaS & Software',
    'github': 'SaaS & Software',
    'adobe': 'SaaS & Software',
    'notion': 'SaaS & Software',
    'zoom': 'SaaS & Software',
    'google cloud': 'SaaS & Software',
    'google ads': 'Marketing & Ads',
    'facebook ads': 'Marketing & Ads',
    'meta ads': 'Marketing & Ads',
    'linkedin': 'Marketing & Ads',
    'hubspot': 'Marketing & Ads',
    'uber': 'Travel & Entertainment',
    'lyft': 'Travel & Entertainment',
    'delta airlines': 'Travel & Entertainment',
    'united airlines': 'Travel & Entertainment',
    'hilton': 'Travel & Entertainment',
    'marriott': 'Travel & Entertainment',
    'staples': 'Office Supplies',
    'office depot': 'Office Supplies',
    'amazon': 'Office Supplies',
    'gusto': 'Payroll',
    'adp': 'Payroll',
    'rippling': 'Payroll',
    'wework': 'Rent & Facilities',
    'regus': 'Rent & Facilities',
    'comcast': 'Utilities',
    'conedison': 'Utilities',
    'pge': 'Utilities',
    'verizon': 'Utilities',
    'att': 'Utilities',
    'legalzoom': 'Professional Services',
    'deloitte': 'Professional Services',
    'kpmg': 'Professional Services'
}

def normalize_vendor(raw_name):
    if not raw_name:
        return 'Unknown Vendor'
    clean = re.sub(r'[^a-zA-Z0-9\s]', '', raw_name).strip()
    # Remove common banking noise like POS, CARD, DEBIT, REF#, INC, LLC, CO
    clean_no_noise = re.sub(r'\b(POS|CARD|DEBIT|CREDIT|REF\d+|INC|LLC|CO|CORP|PAYMENT|ONLINE)\b', '', clean, flags=re.IGNORECASE).strip()
    return clean_no_noise if clean_no_noise else clean

def categorize_vendor(normalized_vendor, custom_rules=None):
    if custom_rules:
        for pattern, cat in custom_rules.items():
            if pattern.lower() in normalized_vendor.lower():
                return cat, 1.0
                
    vendor_lower = normalized_vendor.lower()
    for keyword, cat in DEFAULT_CATEGORY_RULES.items():
        if keyword in vendor_lower:
            return cat, 0.95
            
    # Prohibit returning generic OPEX if vendor keywords match specific buckets
    if any(k in vendor_lower for k in ['software', 'cloud', 'app', 'saas']):
        return 'SaaS & Software', 0.85
    if any(k in vendor_lower for k in ['ad', 'ads', 'marketing', 'promo']):
        return 'Marketing & Ads', 0.85
    if any(k in vendor_lower for k in ['office', 'supplies', 'paper', 'depot', 'desk']):
        return 'Office Supplies', 0.85
    if any(k in vendor_lower for k in ['air', 'flight', 'hotel', 'taxi', 'ride', 'travel']):
        return 'Travel & Entertainment', 0.85
    if any(k in vendor_lower for k in ['rent', 'lease', 'workspace', 'suite', 'realty']):
        return 'Rent & Facilities', 0.85
    if any(k in vendor_lower for k in ['law', 'legal', 'consulting', 'advisor', 'cpa']):
        return 'Professional Services', 0.85
    if any(k in vendor_lower for k in ['electric', 'power', 'water', 'gas', 'telecom', 'internet']):
        return 'Utilities', 0.85

    return 'General OPEX', 0.60

def parse_bank_statement_csv(csv_content, custom_rules=None):
    """
    Parses CSV content string into a list of transaction dictionaries.
    Expected columns can be Date, Description/Vendor, Amount, Category (optional).
    """
    transactions = []
    reader = csv.DictReader(io.StringIO(csv_content))
    
    for row in reader:
        # Standardize field lookup (case-insensitive keys)
        keys = {k.strip().lower(): v.strip() for k, v in row.items() if k}
        
        raw_date = keys.get('date') or keys.get('transaction date') or keys.get('dt')
        raw_vendor = keys.get('description') or keys.get('vendor') or keys.get('payee') or keys.get('name')
        raw_amount = keys.get('amount') or keys.get('total') or keys.get('debit') or keys.get('value')
        csv_cat = keys.get('category')
        
        if not raw_vendor or not raw_amount:
            continue
            
        try:
            # Clean amount ($ sign, commas)
            amount_str = re.sub(r'[\$,]', '', raw_amount)
            amount = abs(float(amount_str))
        except ValueError:
            continue
            
        # Parse date to YYYY-MM-DD
        date_str = datetime.now().strftime('%Y-%m-%d')
        if raw_date:
            for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d', '%b %d, %Y'):
                try:
                    dt = datetime.strptime(raw_date, fmt)
                    date_str = dt.strftime('%Y-%m-%d')
                    break
                except ValueError:
                    pass
                    
        month_str = date_str[:7]
        normalized = normalize_vendor(raw_vendor)
        category, confidence = categorize_vendor(normalized, custom_rules)
        
        # Override generic 'OPEX' from CSV if categorized vendor rule provides a specific bucket
        if csv_cat and csv_cat.upper() != 'OPEX' and csv_cat.upper() != 'UNCATEGORIZED':
            final_category = csv_cat
        else:
            final_category = category

        transactions.append({
            'date': date_str,
            'month': month_str,
            'raw_vendor': raw_vendor,
            'normalized_vendor': normalized,
            'amount': amount,
            'category': final_category,
            'confidence': confidence,
            'status': 'unreconciled'
        })
        
    return transactions

def parse_receipt_file(file_bytes, filename, text_content=None):
    """
    Extracts date, vendor, amount, tax, raw text from receipt file bytes or text.
    """
    raw_text = text_content or ""
    
    if not raw_text and filename.lower().endswith('.pdf'):
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            text_pages = [page.extract_text() for page in reader.pages if page.extract_text()]
            raw_text = "\n".join(text_pages)
        except Exception:
            raw_text = f"Receipt File: {filename}"
    elif not raw_text:
        try:
            raw_text = file_bytes.decode('utf-8', errors='ignore')
        except Exception:
            raw_text = f"Receipt File: {filename}"

    # Extract vendor name (first non-empty line or keyword match)
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    vendor = "Unknown Vendor"
    if lines:
        vendor = lines[0][:100]
        
    # Extract total amount ($ pattern)
    amount = 0.0
    amounts = re.findall(r'\$?\s*([0-9]+\.[0-9]{2})', raw_text)
    if amounts:
        float_amounts = [float(a) for a in amounts]
        amount = max(float_amounts) # Total is usually the max amount
        
    # Extract tax if present
    tax = 0.0
    tax_match = re.search(r'tax\s*:?\s*\$?\s*([0-9]+\.[0-9]{2})', raw_text, re.IGNORECASE)
    if tax_match:
        tax = float(tax_match.group(1))
        
    # Extract date if present
    date_str = datetime.now().strftime('%Y-%m-%d')
    date_match = re.search(r'\b(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})\b', raw_text)
    if date_match:
        raw_d = date_match.group(1)
        for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y'):
            try:
                date_str = datetime.strptime(raw_d, fmt).strftime('%Y-%m-%d')
                break
            except ValueError:
                pass

    return {
        'vendor': normalize_vendor(vendor),
        'date': date_str,
        'amount': amount,
        'tax': tax,
        'raw_text': raw_text[:2000],
        'file_path': filename,
        'status': 'unmatched'
    }
