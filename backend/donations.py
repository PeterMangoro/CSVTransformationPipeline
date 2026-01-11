from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


def parse_amount(amount_str: str) -> float:
    """Parse a donation amount string to float."""
    if not amount_str:
        return 0.0
    
    cleaned = amount_str.replace('$', '').replace(',', '').strip().strip('"').strip("'")
    
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        logger.warning(f"Failed to parse amount: {amount_str}, using 0.0")
        return 0.0


def format_amount(amount: float) -> str:
    """Format a donation amount as currency string."""
    if amount <= 0:
        return ""
    
    return f"${amount:.2f}"


def filter_non_refunded(donations: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Filter out refunded donations."""
    return [d for d in donations if d.get('Status', '').strip() != 'Refunded']


def aggregate_donations_by_patron(donation_history: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    """Group donations by Patron ID."""
    donations_by_patron: Dict[str, List[Dict[str, str]]] = {}
    
    for donation in donation_history:
        patron_id = donation.get('Patron ID', '').strip()
        if patron_id:
            if patron_id not in donations_by_patron:
                donations_by_patron[patron_id] = []
            donations_by_patron[patron_id].append(donation)
    
    logger.info(f"Aggregated donations for {len(donations_by_patron)} patrons")
    return donations_by_patron


def calculate_lifetime_donation_amount(donations: List[Dict[str, str]]) -> str:
    """Calculate lifetime donation amount (sum of non-refunded donations)."""
    non_refunded = filter_non_refunded(donations)
    
    if not non_refunded:
        return ""
    
    total = sum(parse_amount(d.get('Donation Amount', '0')) for d in non_refunded)
    return format_amount(total)


def get_most_recent_donation(donations: List[Dict[str, str]]) -> tuple[str, str]:
    """Get the most recent non-refunded donation date and amount."""
    non_refunded = filter_non_refunded(donations)
    
    if not non_refunded:
        return "", ""
    
    try:
        most_recent = max(non_refunded, key=lambda x: x.get('Donation Date', ''))
        date_str = most_recent.get('Donation Date', '').strip()
        amount = parse_amount(most_recent.get('Donation Amount', '0'))
        amount_str = format_amount(amount)
        
        return date_str, amount_str
    except (ValueError, KeyError) as e:
        logger.warning(f"Error finding most recent donation: {e}")
        return "", ""


def get_fallback_created_date(patron_id: str, donations_by_patron: Dict[str, List[Dict[str, str]]]) -> str:
    """Get fallback Created At date for a constituent missing Date Entered."""
    if patron_id in donations_by_patron:
        donations = donations_by_patron[patron_id]
        non_refunded = filter_non_refunded(donations)
        
        if non_refunded:
            try:
                earliest = min(non_refunded, key=lambda x: x.get('Donation Date', ''))
                earliest_date_str = earliest.get('Donation Date', '').strip()
                
                if earliest_date_str:
                    earliest_date = datetime.fromisoformat(earliest_date_str)
                    return earliest_date.isoformat()
            except (ValueError, KeyError) as e:
                logger.warning(f"Error parsing earliest donation date for patron {patron_id}: {e}")
    
    return datetime.now().isoformat()
