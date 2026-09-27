from typing import TypedDict, List, Dict, Any, Optional

class ExpenseReviewState(TypedDict):
    raw_transactions: List[Dict[str, Any]]
    raw_receipts: List[Dict[str, Any]]
    historical_transactions: List[Dict[str, Any]]
    custom_rules: Dict[str, str]

    parsed_transactions: List[Dict[str, Any]]
    parsed_receipts: List[Dict[str, Any]]
    reconciled_matches: List[Dict[str, Any]]
    anomalies: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    summary: Dict[str, Any]
    error: Optional[str]
