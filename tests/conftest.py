"""
Pytest configuration and shared fixtures for tests.
"""

import pytest
from pathlib import Path
from typing import Dict, List
from datetime import datetime

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_constituent_row() -> Dict[str, str]:
    """Sample constituent row with normalized column names."""
    return {
        'Patron ID': '12345',
        'First Name': 'john',
        'Last Name': 'DOE',
        'Date Entered': 'Jan 15, 2020',
        'Primary Email': 'john.doe@example.com',
        'Company': '',
        'Salutation': 'Mr',
        'Job Title': 'Software Engineer',
        'Tags': 'Board Member, Top Donor',
        'Marital Status': 'Married',
    }


@pytest.fixture
def sample_company_row() -> Dict[str, str]:
    """Sample company constituent row."""
    return {
        'Patron ID': '67890',
        'First Name': '',
        'Last Name': '',
        'Date Entered': '2020-01-15',
        'Primary Email': 'info@company.com',
        'Company': 'Acme Corp',
        'Salutation': '',
        'Job Title': '',
        'Tags': 'Major Donor 2021',
        'Marital Status': '',
    }


@pytest.fixture
def sample_emails() -> List[Dict[str, str]]:
    """Sample email records."""
    return [
        {'Patron ID': '12345', 'Email': 'john.doe@example.com'},
        {'Patron ID': '12345', 'Email': 'john.doe.work@company.com'},
    ]


@pytest.fixture
def sample_donations() -> List[Dict[str, str]]:
    """Sample donation records."""
    return [
        {'Patron ID': '12345', 'Donation Amount': '$100.00', 'Donation Date': '2023-01-15', 'Status': 'Paid'},
        {'Patron ID': '12345', 'Donation Amount': '$250.00', 'Donation Date': '2023-06-20', 'Status': 'Paid'},
        {'Patron ID': '12345', 'Donation Amount': '$50.00', 'Donation Date': '2023-03-10', 'Status': 'Refunded'},
    ]


@pytest.fixture
def sample_tag_mapping() -> Dict[str, str]:
    """Sample tag mapping from API."""
    return {
        'Top Donor': 'Major Donor',
        'Board Member': 'Board Member',
        'Major Donor 2021': 'Major Donor',
        'Camp 2016 ': 'Summer 2016',  # Note trailing space
    }


@pytest.fixture
def temp_csv_file(tmp_path):
    """Create a temporary CSV file for testing."""
    def _create_csv(content: List[Dict[str, str]], fieldnames: List[str]):
        file_path = tmp_path / "test.csv"
        import csv
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(content)
        return file_path
    return _create_csv
