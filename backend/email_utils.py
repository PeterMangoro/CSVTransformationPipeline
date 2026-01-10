import re
from typing import Optional, List
import logging

from .config import EMAIL_DOMAIN_CORRECTIONS

logger = logging.getLogger(__name__)

# Email validation regex pattern
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


def standardize_email(email: str) -> str:
    """Standardize an email address by lowercasing and fixing common domain typos."""
    if not email:
        return ""
    
    email = email.lower().strip()
    
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
    
    standardized_primary = standardize_email(primary_email) if primary_email else ""
    if standardized_primary in valid_emails:
        email_1 = standardized_primary
    else:
        email_1 = valid_emails[0]
    
    email_2 = ""
    for email in valid_emails:
        if email != email_1:
            email_2 = email
            break
    
    return email_1, email_2
