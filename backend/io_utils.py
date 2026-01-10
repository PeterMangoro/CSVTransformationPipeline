import csv
from pathlib import Path
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


def read_csv(file_path: Path) -> List[Dict[str, str]]:
    """Read a CSV file and return a list of dictionaries"""
    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")
    
    logger.info(f"Reading CSV file: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    logger.info(f"Read {len(rows)} rows from {file_path.name}")
    return rows


def read_constituents_csv(file_path: Path) -> List[Dict[str, str]]:
    """Read constituents CSV file and normalize column names to match actual content"""
    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")
    
    logger.info(f"Reading CSV file: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            normalized_row = {
                'Patron ID': row.get('Patron ID', ''),
                'First Name': row.get('First Name', ''),
                'Last Name': row.get('Last Name', ''),
                'Date Entered': row.get('Date Entered', ''),
                'Primary Email': row.get('Primary Email', ''),
                'Company': row.get('Company', ''),
                'Salutation': row.get('Salutation', ''),  # Used for CB Title
                'Job Title': row.get('Title', ''),  # RENAME: Title -> Job Title (actual content is job title)
                'Tags': row.get('Tags', ''),
                'Marital Status': row.get('Gender', ''),  # RENAME: Gender -> Marital Status (actual content is marital status)
            }
            rows.append(normalized_row)
    
    logger.info(f"Read {len(rows)} rows from {file_path.name} (columns normalized)")
    return rows


def write_csv(file_path: Path, fieldnames: List[str], rows: List[Dict[str, str]]) -> None:
    """Write data to a CSV file"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Writing CSV file: {file_path} ({len(rows)} rows)")
    
    with open(file_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    logger.info(f"Successfully wrote {file_path.name}")
