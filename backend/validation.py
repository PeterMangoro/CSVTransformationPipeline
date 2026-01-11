import csv
import re
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

from .config import (
    INPUT_CONSTITUENTS_FILE,
    INPUT_DONATION_HISTORY_FILE,
    OUTPUT_CONSTITUENTS_FILE,
    OUTPUT_TAGS_FILE,
)

logger = logging.getLogger(__name__)


def is_valid_email_format(email: str) -> bool:
    """Check if email is syntactically valid."""
    if not email or not email.strip():
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))


def parse_amount_to_float(amount_str: str) -> float:
    """Parse amount string to float for comparison."""
    if not amount_str or not amount_str.strip():
        return 0.0
    # Remove $, commas, quotes
    cleaned = amount_str.strip().replace('$', '').replace(',', '').strip('"').strip("'")
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0


def validate_row_count() -> Tuple[bool, str]:
    """Validate that output row count matches input constituents."""
    logger.info("Validating row count...")
    
    # Count input constituents
    with open(INPUT_CONSTITUENTS_FILE, 'r', encoding='utf-8') as f:
        input_reader = csv.DictReader(f)
        input_rows = list(input_reader)
        input_count = len(input_rows)
    
    # Count output constituents
    with open(OUTPUT_CONSTITUENTS_FILE, 'r', encoding='utf-8') as f:
        output_reader = csv.DictReader(f)
        output_rows = list(output_reader)
        output_count = len(output_rows)
    
    if input_count == output_count:
        return True, f"Row count matches: {input_count} constituents"
    else:
        return False, f"Row count mismatch: {input_count} input vs {output_count} output"


def validate_constituent_ids() -> Tuple[bool, str]:
    """Validate that all CB Constituent ID values are unique and non-null."""
    logger.info("Validating constituent IDs...")
    
    ids = []
    null_ids = []
    
    with open(OUTPUT_CONSTITUENTS_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            constituent_id = row.get('CB Constituent ID', '').strip()
            if not constituent_id:
                null_ids.append(row)
            ids.append(constituent_id)
    
    # Check for nulls
    if null_ids:
        return False, f"Found {len(null_ids)} rows with null/empty CB Constituent ID"
    
    # Check for duplicates
    seen = set()
    duplicates = []
    for i, constituent_id in enumerate(ids):
        if constituent_id in seen:
            duplicates.append(constituent_id)
        seen.add(constituent_id)
    
    if duplicates:
        return False, f"Found duplicate CB Constituent IDs: {duplicates[:5]}"
    
    return True, f"All {len(ids)} constituent IDs are unique and non-null"


def validate_lifetime_donation_amounts() -> Tuple[bool, str, List[str]]:
    """Validate that CB Lifetime Donation Amount equals sum of non-refunded donations."""
    logger.info("Validating lifetime donation amounts...")
    
    donations_by_patron = defaultdict(list)
    with open(INPUT_DONATION_HISTORY_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            patron_id = row.get('Patron ID', '').strip()
            if patron_id:
                donations_by_patron[patron_id].append(row)
    
    errors = []
    
    with open(OUTPUT_CONSTITUENTS_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            patron_id = row.get('CB Constituent ID', '').strip()
            expected_amount_str = row.get('CB Lifetime Donation Amount', '').strip()
            expected_amount = parse_amount_to_float(expected_amount_str)
            
            donations = donations_by_patron.get(patron_id, [])
            actual_amount = 0.0
            for donation in donations:
                status = donation.get('Status', '').strip()
                if status != 'Refunded':
                    amount_str = donation.get('Donation Amount', '')
                    actual_amount += parse_amount_to_float(amount_str)
            
            if abs(actual_amount - expected_amount) > 0.01:
                errors.append(
                    f"Patron {patron_id}: Expected ${expected_amount:.2f}, "
                    f"calculated ${actual_amount:.2f}"
                )
    
    if errors:
        return False, f"Found {len(errors)} mismatches in lifetime donation amounts", errors[:10]
    else:
        return True, f"All lifetime donation amounts match calculated sums", []


def validate_most_recent_donation() -> Tuple[bool, str, List[str]]:
    """Validate that CB Most Recent Donation fields match latest non-refunded donation."""
    logger.info("Validating most recent donations...")
    
    donations_by_patron = defaultdict(list)
    with open(INPUT_DONATION_HISTORY_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            patron_id = row.get('Patron ID', '').strip()
            if patron_id:
                donations_by_patron[patron_id].append(row)
    
    errors = []
    
    with open(OUTPUT_CONSTITUENTS_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            patron_id = row.get('CB Constituent ID', '').strip()
            output_date = row.get('CB Most Recent Donation Date', '').strip()
            output_amount_str = row.get('CB Most Recent Donation Amount', '').strip()
            output_amount = parse_amount_to_float(output_amount_str)
            
            donations = donations_by_patron.get(patron_id, [])
            non_refunded = [d for d in donations if d.get('Status', '').strip() != 'Refunded']
            
            if not non_refunded:
                if output_date or output_amount_str:
                    errors.append(
                        f"Patron {patron_id}: Expected empty most recent donation, "
                        f"but found date={output_date}, amount={output_amount_str}"
                    )
                continue
            
            sorted_donations = sorted(
                non_refunded,
                key=lambda d: d.get('Donation Date', ''),
                reverse=True
            )
            most_recent = sorted_donations[0]
            expected_date = most_recent.get('Donation Date', '').strip()
            expected_amount = parse_amount_to_float(most_recent.get('Donation Amount', ''))
            
            # Compare date (normalize format)
            expected_date_normalized = expected_date.replace('-', '')
            output_date_normalized = output_date.replace('-', '').split('T')[0].replace('-', '')
            
            if expected_date_normalized != output_date_normalized:
                errors.append(
                    f"Patron {patron_id}: Expected date={expected_date}, "
                    f"found date={output_date}"
                )
            
            # Compare amount
            if abs(expected_amount - output_amount) > 0.01:
                errors.append(
                    f"Patron {patron_id}: Expected amount=${expected_amount:.2f}, "
                    f"found amount=${output_amount:.2f}"
                )
    
    if errors:
        return False, f"Found {len(errors)} mismatches in most recent donations", errors[:10]
    else:
        return True, f"All most recent donation fields match correctly", []


def validate_email_formats() -> Tuple[bool, str, List[str]]:
    """Validate that all CB Email 1/2 values are syntactically valid."""
    logger.info("Validating email formats...")
    
    errors = []
    
    with open(OUTPUT_CONSTITUENTS_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            patron_id = row.get('CB Constituent ID', '').strip()
            email_1 = row.get('CB Email 1 (Standardized)', '').strip()
            email_2 = row.get('CB Email 2 (Standardized)', '').strip()
            
            # Email 1 should be valid if present (it's required)
            if email_1 and not is_valid_email_format(email_1):
                errors.append(
                    f"Patron {patron_id}: Invalid CB Email 1 format: '{email_1}'"
                )
            
            # Email 2 should be valid if present (optional)
            if email_2 and not is_valid_email_format(email_2):
                errors.append(
                    f"Patron {patron_id}: Invalid CB Email 2 format: '{email_2}'"
                )
    
    if errors:
        return False, f"Found {len(errors)} invalid email formats", errors[:10]
    else:
        return True, f"All email formats are valid", []


def validate_constituent_types() -> Tuple[bool, str, List[str]]:
    """Validate that constituent types match Company field logic."""
    logger.info("Validating constituent types...")
    
    input_constituents = {}
    with open(INPUT_CONSTITUENTS_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            patron_id = row.get('Patron ID', '').strip()
            if patron_id:
                input_constituents[patron_id] = row
    
    errors = []
    
    with open(OUTPUT_CONSTITUENTS_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            patron_id = row.get('CB Constituent ID', '').strip()
            output_type = row.get('CB Constituent Type', '').strip()
            output_company = row.get('CB Company Name', '').strip()
            output_first_name = row.get('CB First Name', '').strip()
            output_last_name = row.get('CB Last Name', '').strip()
            
            input_row = input_constituents.get(patron_id)
            if not input_row:
                errors.append(f"Patron {patron_id}: Not found in input file")
                continue
            
            input_company = input_row.get('Company', '').strip()
            
            from .config import INVALID_COMPANY_VALUES
            should_be_company = input_company and input_company not in INVALID_COMPANY_VALUES
            
            if should_be_company and output_type != 'Company':
                errors.append(
                    f"Patron {patron_id}: Should be Company (has company='{input_company}'), "
                    f"but type is '{output_type}'"
                )
            elif not should_be_company and output_type != 'Person':
                errors.append(
                    f"Patron {patron_id}: Should be Person (company='{input_company}'), "
                    f"but type is '{output_type}'"
                )
            
            if output_type == 'Company' and (output_first_name or output_last_name):
                errors.append(
                    f"Patron {patron_id}: Company type but has names: "
                    f"'{output_first_name}' '{output_last_name}'"
                )
            
            if output_type == 'Person' and output_company:
                pass
    
    if errors:
        return False, f"Found {len(errors)} constituent type mismatches", errors[:10]
    else:
        return True, f"All constituent types are correct", []


def validate_tag_counts() -> Tuple[bool, str]:
    """Validate that tag counts match actual usage in constituents."""
    logger.info("Validating tag counts...")
    
    tag_usage = defaultdict(int)
    
    with open(OUTPUT_CONSTITUENTS_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tags_str = row.get('CB Tags', '').strip()
            if tags_str:
                tags = [t.strip() for t in tags_str.split(',')]
                unique_tags = set(tags)
                for tag in unique_tags:
                    if tag:
                        tag_usage[tag] += 1
    
    # Load tag counts output
    tag_counts_output = {}
    with open(OUTPUT_TAGS_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tag_name = row.get('CB Tag Name', '').strip()
            count_str = row.get('CB Tag Count', '').strip()
            try:
                tag_counts_output[tag_name] = int(count_str)
            except (ValueError, TypeError):
                pass
    
    # Compare
    mismatches = []
    for tag, expected_count in tag_usage.items():
        output_count = tag_counts_output.get(tag, 0)
        if expected_count != output_count:
            mismatches.append(f"Tag '{tag}': Expected {expected_count}, found {output_count}")
    
    # Check for tags in output that don't appear in constituents
    for tag, output_count in tag_counts_output.items():
        if tag not in tag_usage and output_count > 0:
            mismatches.append(f"Tag '{tag}': In output but not in any constituent")
    
    if mismatches:
        return False, f"✗ Found {len(mismatches)} tag count mismatches: {mismatches[:5]}"
    else:
        return True, f"✓ All tag counts match usage in constituents"


def run_all_validations() -> Dict[str, Tuple[bool, str, List[str]]]:
    """Run all validation checks and return results."""
    results = {}
    
    is_valid, message = validate_row_count()
    results['row_count'] = (is_valid, message, [])
    
    is_valid, message = validate_constituent_ids()
    results['constituent_ids'] = (is_valid, message, [])
    
    is_valid, message, errors = validate_lifetime_donation_amounts()
    results['lifetime_donations'] = (is_valid, message, errors)
    
    is_valid, message, errors = validate_most_recent_donation()
    results['most_recent_donations'] = (is_valid, message, errors)
    
    is_valid, message, errors = validate_email_formats()
    results['email_formats'] = (is_valid, message, errors)
    
    is_valid, message, errors = validate_constituent_types()
    results['constituent_types'] = (is_valid, message, errors)
    
    is_valid, message = validate_tag_counts()
    results['tag_counts'] = (is_valid, message, [])
    
    return results


def print_validation_report(results: Dict[str, Tuple[bool, str, List[str]]]) -> None:
    """Print a formatted validation report."""
    print("\n" + "="*70)
    print("VALIDATION REPORT")
    print("="*70)
    
    all_passed = True
    for check_name, (is_valid, message, errors) in results.items():
        status = "PASS" if is_valid else "FAIL"
        print(f"\n[{status}] {check_name.replace('_', ' ').title()}")
        print(f"  {message}")
        
        if errors:
            print(f"  Errors:")
            for error in errors:
                print(f"    - {error}")
            if len(errors) > 10:
                print(f"    ... and {len(errors) - 10} more errors")
        
        if not is_valid:
            all_passed = False
    
    print("\n" + "="*70)
    if all_passed:
        print("ALL VALIDATIONS PASSED")
    else:
        print("SOME VALIDATIONS FAILED")
    print("="*70 + "\n")
    
    return all_passed
