from datetime import datetime
from typing import Dict, List, Optional
import logging

from .config import (
    INVALID_COMPANY_VALUES,
    TITLE_MAPPING,
    DATE_FORMATS,
)
from .email_utils import select_emails
from .tags import process_tags, fetch_tag_mapping
from .donations import (
    calculate_lifetime_donation_amount,
    get_most_recent_donation,
    get_fallback_created_date,
)

logger = logging.getLogger(__name__)


def parse_date_multiple_formats(date_str: str) -> Optional[datetime]:
    """Parse a date string using multiple format patterns"""
    if not date_str or not date_str.strip():
        return None
    
    date_str = date_str.strip().strip('"').strip("'")
    
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError):
            continue
    
    logger.warning(f"Failed to parse date: {date_str}")
    return None


def determine_constituent_type(row: Dict[str, str]) -> tuple[str, str]:
    """Determine constituent type (Person or Company) based on Company field"""
    company_value = row.get('Company', '').strip()
    
    if company_value not in INVALID_COMPANY_VALUES:
        return "Company", company_value
    else:
        return "Person", ""


def standardize_name(name: str) -> str:
    """Standardize a name by capitalizing first letter, lowercase rest"""
    if not name or not name.strip():
        return ""
    
    return name.strip().capitalize()


def format_created_at(date_entered: str, patron_id: str, donations_by_patron: Dict[str, List[Dict[str, str]]]) -> str:
    """Format Created At timestamp from Date Entered field, with fallback"""
    if date_entered and date_entered.strip():
        parsed_date = parse_date_multiple_formats(date_entered)
        if parsed_date:
            return parsed_date.isoformat()
    
    # Fallback: use earliest donation date or current date
    logger.debug(f"Using fallback date for patron {patron_id}")
    return get_fallback_created_date(patron_id, donations_by_patron)


def map_title(salutation: Optional[str]) -> str:
    """Map Salutation to allowed Title values: "Mr.", "Mrs.", "Ms.", "Dr.", or empty string"""
    if not salutation or not salutation.strip():
        return ""
    
    key = salutation.strip().lower().replace('.', '')
    return TITLE_MAPPING.get(key, "")


def format_background_information(job_title: Optional[str], marital_status: Optional[str]) -> str:
    """Format Background Information string from job title and marital status"""
    parts = []
    
    if job_title and job_title.strip():
        parts.append(f"Job Title: {job_title.strip()}")
    
    if marital_status and marital_status.strip():
        parts.append(f"Marital Status: {marital_status.strip()}")
    
    return "; ".join(parts) if parts else ""


def transform_constituent(
    row: Dict[str, str],
    emails_by_patron: Dict[str, List[Dict[str, str]]],
    donations_by_patron: Dict[str, List[Dict[str, str]]],
    tag_mapping: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """Transform a single constituent row into CueBox output format"""
    patron_id = row.get('Patron ID', '').strip()
    
    cb_constituent_id = patron_id
    
    cb_type, cb_company_name = determine_constituent_type(row)
    
    if cb_type == "Person":
        cb_first_name = standardize_name(row.get('First Name', ''))
        cb_last_name = standardize_name(row.get('Last Name', ''))
    else:
        cb_first_name = ""
        cb_last_name = ""
    
    date_entered = row.get('Date Entered', '')
    cb_created_at = format_created_at(date_entered, patron_id, donations_by_patron)
    
    primary_email = row.get('Primary Email', '')
    all_emails = [e['Email'] for e in emails_by_patron.get(patron_id, [])]
    cb_email_1, cb_email_2 = select_emails(primary_email, all_emails)
    
    salutation = row.get('Salutation', '')
    cb_title = map_title(salutation)
    
    tags_str = row.get('Tags', '')
    cb_tags = process_tags(tags_str, tag_mapping)
    
    job_title = row.get('Job Title', '')  # Normalized column name (was 'Title')
    marital_status = row.get('Marital Status', '')  # Normalized column name (was 'Gender')
    cb_background_info = format_background_information(job_title, marital_status)
    
    donations = donations_by_patron.get(patron_id, [])
    cb_lifetime_donation = calculate_lifetime_donation_amount(donations)
    
    cb_most_recent_date, cb_most_recent_amount = get_most_recent_donation(donations)
    
    output_row = {
        "CB Constituent ID": cb_constituent_id,
        "CB Constituent Type": cb_type,
        "CB First Name": cb_first_name,
        "CB Last Name": cb_last_name,
        "CB Company Name": cb_company_name,
        "CB Created At": cb_created_at,
        "CB Email 1 (Standardized)": cb_email_1,
        "CB Email 2 (Standardized)": cb_email_2,
        "CB Title": cb_title,
        "CB Tags": cb_tags,
        "CB Background Information": cb_background_info,
        "CB Lifetime Donation Amount": cb_lifetime_donation,
        "CB Most Recent Donation Date": cb_most_recent_date,
        "CB Most Recent Donation Amount": cb_most_recent_amount,
    }
    
    return output_row


def transform_all_constituents(
    constituents: List[Dict[str, str]],
    emails_by_patron: Dict[str, List[Dict[str, str]]],
    donations_by_patron: Dict[str, List[Dict[str, str]]],
) -> List[Dict[str, str]]:
    """Transform all constituents into CueBox output format"""
    # Fetch tag mapping once for all constituents
    tag_mapping = fetch_tag_mapping()
    
    valid_patron_ids = {row.get('Patron ID', '').strip() for row in constituents if row.get('Patron ID')}
    filtered_donations = {
        pid: donations 
        for pid, donations in donations_by_patron.items() 
        if pid in valid_patron_ids
    }
    
    orphaned_count = len(donations_by_patron) - len(filtered_donations)
    if orphaned_count > 0:
        logger.warning(f"Skipped {orphaned_count} patron(s) with donations not found in constituents file")
    
    output_rows = []
    for row in constituents:
        try:
            output_row = transform_constituent(row, emails_by_patron, filtered_donations, tag_mapping)
            output_rows.append(output_row)
        except Exception as e:
            logger.error(f"Error transforming constituent {row.get('Patron ID', 'unknown')}: {e}")
            raise
    
    logger.info(f"Transformed {len(output_rows)} constituents")
    return output_rows
