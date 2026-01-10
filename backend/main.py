#!/usr/bin/env python3

import csv
import json
import logging
import re
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Base directory (project root, parent of backend/)
BASE_DIR = Path(__file__).parent.parent

# Input file paths
INPUT_CONSTITUENTS_FILE = BASE_DIR / "InputConstituents.csv"
INPUT_EMAILS_FILE = BASE_DIR / "InputEmails.csv"
INPUT_DONATION_HISTORY_FILE = BASE_DIR / "InputDonationHistory.csv"

# Output directory
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)  # Create output directory if it doesn't exist

# Output file paths
OUTPUT_CONSTITUENTS_FILE = OUTPUT_DIR / "OutputFormatCueBoxConstituents.csv"
OUTPUT_TAGS_FILE = OUTPUT_DIR / "OutputFormatCueBoxTags.csv"

# Tag mapping API URL
TAG_API_URL = "https://6719768f7fc4c5ff8f4d84f1.mockapi.io/api/v1/tags"
TAG_API_TIMEOUT = 10  # seconds

# Date parsing formats (in order of preference)
DATE_FORMATS = [
    "%b %d, %Y",      # "Jan 19, 2020"
    "%m/%d/%Y",       # "04/19/2022"
    "%m/%d/%Y %H:%M", # "12/07/2017 12:34"
    "%Y-%m-%d",       # ISO format
]

INVALID_COMPANY_VALUES = ["", "None", "N/A", "n/a", "Retired", "Used to work here."]

TITLE_MAPPING = {
    "mr": "Mr.",
    "mrs": "Mrs.",
    "ms": "Ms.",
    "dr": "Dr.",
    "rev": "",  # Not in allowed list
    "mr. and mrs.": "",  # Not in allowed list
}

# Email domain corrections to fix typos
EMAIL_DOMAIN_CORRECTIONS = {
    "gmaill.com": "gmail.com",
    "hotmal.com": "hotmail.com",
    "yaho.com": "yahoo.com",
    "gmal.com": "gmail.com",
    "outlok.com": "outlook.com",
}

# CSV field names
CONSTITUENT_FIELDS = [
    "CB Constituent ID",
    "CB Constituent Type",
    "CB First Name",
    "CB Last Name",
    "CB Company Name",
    "CB Created At",
    "CB Email 1 (Standardized)",
    "CB Email 2 (Standardized)",
    "CB Title",
    "CB Tags",
    "CB Background Information",
    "CB Lifetime Donation Amount",
    "CB Most Recent Donation Date",
    "CB Most Recent Donation Amount",
]

TAG_OUTPUT_FIELDS = [
    "CB Tag Name",
    "CB Tag Count",
]

# Email validation regex pattern
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

# LOGGING SETUP

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)

def read_csv(file_path: Path) -> List[Dict[str, str]]:
    """Read a CSV file and return a list of dictionaries."""
    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")
    
    logger.info(f"Reading CSV file: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    logger.info(f"Read {len(rows)} rows from {file_path.name}")
    return rows


def write_csv(file_path: Path, fieldnames: List[str], rows: List[Dict[str, str]]) -> None:
    """Write data to a CSV file."""
    # Ensure output directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Writing CSV file: {file_path} ({len(rows)} rows)")
    
    with open(file_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    logger.info(f"Successfully wrote {file_path.name}")

def standardize_email(email: str) -> str:
    """Standardize an email address by lowercasing and fixing common domain typos."""
    if not email:
        return ""
    
    email = email.lower().strip()
    
    # Fix domain typos
    if "@" in email:
        parts = email.split("@")
        domain = parts[1]
        if domain in EMAIL_DOMAIN_CORRECTIONS:
            corrected_domain = EMAIL_DOMAIN_CORRECTIONS[domain]
            email = f"{parts[0]}@{corrected_domain}"
            logger.debug(f"Corrected email domain: {domain} -> {corrected_domain}")
    
    return email


def is_valid_email(email: str) -> bool:
    """Check if an email address is syntactically valid."""
    if not email:
        return False
    
    return bool(EMAIL_PATTERN.match(email))


def get_valid_emails(emails: List[str]) -> List[str]:
    """Standardize and filter a list of emails, returning only valid ones."""
    valid_emails = []
    seen = set()
    
    for email in emails:
        if not email:
            continue
        
        standardized = standardize_email(email)
        if standardized and standardized not in seen:
            if is_valid_email(standardized):
                valid_emails.append(standardized)
                seen.add(standardized)
            else:
                logger.debug(f"Invalid email format (kept original): {email}")
    
    return valid_emails


def select_emails(primary_email: Optional[str], all_emails: List[str]) -> tuple[str, str]:
    """Select Email 1 and Email 2 for a constituent."""
    
    email_list = []
    if primary_email:
        email_list.append(primary_email)
    email_list.extend(all_emails)
    
    valid_emails = get_valid_emails(email_list)
    
    if not valid_emails:
        return "", ""
    
    # Select Email 1 (prefer primary if it's valid)
    standardized_primary = standardize_email(primary_email) if primary_email else ""
    if standardized_primary in valid_emails:
        email_1 = standardized_primary
    else:
        email_1 = valid_emails[0]
    
    # Select Email 2 (first different from Email 1)
    email_2 = ""
    for email in valid_emails:
        if email != email_1:
            email_2 = email
            break
    
    return email_1, email_2

# Cache for tag mapping (fetched once per run)
_tag_mapping_cache: Optional[Dict[str, str]] = None


def fetch_tag_mapping() -> Dict[str, str]:
    """Fetch tag mapping from API and return a dictionary mapping original names to mapped names."""
    global _tag_mapping_cache
    
    # Return cached mapping if available
    if _tag_mapping_cache is not None:
        return _tag_mapping_cache
    
    try:
        logger.info(f"Fetching tag mapping from API: {TAG_API_URL}")
        
        with urllib.request.urlopen(TAG_API_URL, timeout=TAG_API_TIMEOUT) as response:
            data = json.loads(response.read())
            
            # Create mapping: normalize by trimming both API names and keys
            mapping = {}
            for item in data:
                original_name = item['name'].strip()  # Normalize API name
                mapped_name = item['mapped_name'].strip()
                # Store normalized mapping (both sides trimmed for consistency)
                mapping[original_name] = mapped_name
            
            logger.info(f"Successfully fetched {len(mapping)} tag mappings from API")
            _tag_mapping_cache = mapping
            return mapping
            
    except Exception as e:
        logger.warning(f"Tag API failed: {e}. Using original tag names (no mapping).")
        _tag_mapping_cache = {}  # Cache empty dict to avoid retrying
        return {}


def process_tags(tags_str: str, tag_mapping: Optional[Dict[str, str]] = None) -> str:
    """Process a tags string: split, deduplicate, map via API, and return comma-separated string."""
    if not tags_str or not tags_str.strip():
        return ""
    
    tag_list = [t.strip() for t in tags_str.split(',')]
    tag_list = [t for t in tag_list if t]  # Remove empty strings
    
    if not tag_list:
        return ""
    
    tag_list = list(dict.fromkeys(tag_list))
    
    if tag_mapping is None:
        tag_mapping = fetch_tag_mapping()
    
    mapped_tags = []
    for tag in tag_list:
        normalized_tag = tag.strip()  # Normalize input tag
        if normalized_tag in tag_mapping:
            mapped_tags.append(tag_mapping[normalized_tag])
        else:
            # Tag not in API, keep original (normalized)
            mapped_tags.append(normalized_tag)
    
    mapped_tags = list(dict.fromkeys(mapped_tags))
    
    return ", ".join(mapped_tags)


def count_tags_by_constituent(constituents: List[Dict[str, str]], tag_mapping: Optional[Dict[str, str]] = None) -> Dict[str, int]:
    """Count how many constituents have each tag (after mapping)."""
    if tag_mapping is None:
        tag_mapping = fetch_tag_mapping()
    
    tag_counts = {}
    
    for constituent in constituents:
        tags_str = constituent.get('Tags', '').strip()
        if tags_str:
            processed_tags = process_tags(tags_str, tag_mapping)
            if processed_tags:
                tag_list = [t.strip() for t in processed_tags.split(',')]
                mapped_tags = set(tag_list)
                for mapped_tag in mapped_tags:
                    tag_counts[mapped_tag] = tag_counts.get(mapped_tag, 0) + 1
    
    return tag_counts

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
                    created_date = earliest_date - timedelta(days=1)
                    return created_date.isoformat()
            except (ValueError, KeyError) as e:
                logger.warning(f"Error parsing earliest donation date for patron {patron_id}: {e}")
    
    return datetime.now().isoformat()

def parse_date_multiple_formats(date_str: str) -> Optional[datetime]:
    """Parse a date string using multiple format patterns."""
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
    """Determine constituent type (Person or Company) based on Company field."""
    company_value = row.get('Company', '').strip()
    
    if company_value not in INVALID_COMPANY_VALUES:
        return "Company", company_value
    else:
        return "Person", ""


def standardize_name(name: str) -> str:
    """Standardize a name by capitalizing first letter, lowercase rest."""
    if not name or not name.strip():
        return ""
    
    return name.strip().capitalize()


def format_created_at(date_entered: str, patron_id: str, donations_by_patron: Dict[str, List[Dict[str, str]]]) -> str:
    """Format Created At timestamp from Date Entered field, with fallback."""
    if date_entered and date_entered.strip():
        parsed_date = parse_date_multiple_formats(date_entered)
        if parsed_date:
            return parsed_date.isoformat()
    
    # Fallback: use earliest donation date or current date
    logger.debug(f"Using fallback date for patron {patron_id}")
    return get_fallback_created_date(patron_id, donations_by_patron)


def map_title(salutation: Optional[str]) -> str:
    """Map Salutation to allowed Title values: "Mr.", "Mrs.", "Ms.", "Dr.", or empty string."""
    if not salutation or not salutation.strip():
        return ""
    
    key = salutation.strip().lower()
    return TITLE_MAPPING.get(key, "")


def format_background_information(job_title: Optional[str], marital_status: Optional[str]) -> str:
    """Format Background Information string from job title and marital status."""
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
    """Transform a single constituent row into CueBox output format."""
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
    
    job_title = row.get('Title', '')  
    marital_status = row.get('Gender', '')
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
    """Transform all constituents into CueBox output format."""
    # Fetch tag mapping once for all constituents
    tag_mapping = fetch_tag_mapping()
    
    # Filter out orphaned donations (Patron IDs not in constituents)
    valid_patron_ids = {row.get('Patron ID', '').strip() for row in constituents if row.get('Patron ID')}
    filtered_donations = {
        pid: donations 
        for pid, donations in donations_by_patron.items() 
        if pid in valid_patron_ids
    }
    
    orphaned_count = len(donations_by_patron) - len(filtered_donations)
    if orphaned_count > 0:
        logger.warning(f"Skipped {orphaned_count} patron(s) with donations not found in constituents file")
    
    # Transform each constituent
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

def group_emails_by_patron(emails: list) -> dict:
    """Group email records by Patron ID."""
    emails_by_patron = defaultdict(list)
    
    for email_row in emails:
        patron_id = email_row.get('Patron ID', '').strip()
        if patron_id:
            emails_by_patron[patron_id].append(email_row)
    
    logger.info(f"Grouped emails for {len(emails_by_patron)} patrons")
    return emails_by_patron


def generate_tags_output(constituents: list) -> list:
    """Generate the tags output file with tag names and counts."""
    tag_counts = count_tags_by_constituent(constituents)
    
    output_rows = []
    for tag_name in sorted(tag_counts.keys()):
        output_rows.append({
            "CB Tag Name": tag_name,
            "CB Tag Count": str(tag_counts[tag_name]),
        })
    
    logger.info(f"Generated {len(output_rows)} tag entries")
    return output_rows


def main():
    """Main function to orchestrate the data transformation pipeline."""
    logger.info("Starting CueBox data import transformation pipeline")
    
    try:
        # Step 1: Load input files
        logger.info("Loading input files...")
        constituents = read_csv(INPUT_CONSTITUENTS_FILE)
        emails = read_csv(INPUT_EMAILS_FILE)
        donation_history = read_csv(INPUT_DONATION_HISTORY_FILE)
        
        logger.info(f"Loaded {len(constituents)} constituents, {len(emails)} email records, {len(donation_history)} donation records")
        
        # Step 2: Group data by Patron ID
        logger.info("Grouping data by Patron ID...")
        emails_by_patron = group_emails_by_patron(emails)
        donations_by_patron = aggregate_donations_by_patron(donation_history)
        
        # Step 3: Filter out orphaned donations (donations for Patron IDs not in constituents)
        valid_patron_ids = {row.get('Patron ID', '').strip() for row in constituents if row.get('Patron ID')}
        orphaned_patron_ids = set(donations_by_patron.keys()) - valid_patron_ids
        
        if orphaned_patron_ids:
            orphaned_count = sum(len(donations_by_patron[pid]) for pid in orphaned_patron_ids)
            logger.warning(f"Found {orphaned_count} donation(s) for {len(orphaned_patron_ids)} orphaned Patron ID(s): {sorted(orphaned_patron_ids)}")
            logger.warning("These donations will be excluded from output")
        
        # Step 4: Transform constituents
        logger.info("Transforming constituents...")
        output_constituents = transform_all_constituents(
            constituents,
            emails_by_patron,
            donations_by_patron,
        )
        
        # Step 5: Generate tags output
        logger.info("Generating tags output...")
        output_tags = generate_tags_output(constituents)
        
        # Step 6: Write output files
        logger.info("Writing output files...")
        write_csv(OUTPUT_CONSTITUENTS_FILE, CONSTITUENT_FIELDS, output_constituents)
        write_csv(OUTPUT_TAGS_FILE, TAG_OUTPUT_FIELDS, output_tags)
        
        logger.info("=" * 60)
        logger.info("Transformation completed successfully!")
        logger.info(f"Output files written:")
        logger.info(f"  - {OUTPUT_CONSTITUENTS_FILE} ({len(output_constituents)} rows)")
        logger.info(f"  - {OUTPUT_TAGS_FILE} ({len(output_tags)} rows)")
        logger.info("=" * 60)
        
    except FileNotFoundError as e:
        logger.error(f"Input file not found: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error during transformation: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
