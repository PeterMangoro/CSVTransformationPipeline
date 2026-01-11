import pytest
from backend.donations import (
    parse_amount,
    format_amount,
    filter_non_refunded,
    aggregate_donations_by_patron,
    calculate_lifetime_donation_amount,
    get_most_recent_donation,
    get_fallback_created_date,
)


class TestParseAmount:
    """Test amount parsing function."""
    
    def test_format_with_dollar_and_comma(self):
        assert parse_amount("$3,000.00") == 3000.0
    
    def test_format_with_dollar_no_comma(self):
        assert parse_amount("$100.00") == 100.0
    
    def test_format_without_dollar(self):
        assert parse_amount("100.00") == 100.0
    
    def test_format_with_quotes(self):
        assert parse_amount('"$3,000.00"') == 3000.0
        assert parse_amount("'$100.00'") == 100.0
    
    def test_empty_string(self):
        assert parse_amount("") == 0.0
        assert parse_amount(None) == 0.0
    
    def test_invalid_string(self):
        assert parse_amount("invalid") == 0.0
        assert parse_amount("abc123") == 0.0
    
    def test_whitespace(self):
        assert parse_amount("  $100.00  ") == 100.0


class TestFormatAmount:
    """Test amount formatting function."""
    
    def test_positive_amount(self):
        assert format_amount(100.0) == "$100.00"
        assert format_amount(3000.0) == "$3000.00"
    
    def test_decimal_places(self):
        assert format_amount(100.5) == "$100.50"
        assert format_amount(100.999) == "$101.00"  # Rounding
    
    def test_zero_or_negative(self):
        assert format_amount(0) == ""
        assert format_amount(-10) == ""
        assert format_amount(0.0) == ""


class TestFilterNonRefunded:
    """Test refund filtering function."""
    
    def test_all_paid(self):
        donations = [
            {'Status': 'Paid', 'Amount': '100'},
            {'Status': 'Paid', 'Amount': '200'},
        ]
        result = filter_non_refunded(donations)
        assert len(result) == 2
    
    def test_with_refunded(self):
        donations = [
            {'Status': 'Paid', 'Amount': '100'},
            {'Status': 'Refunded', 'Amount': '50'},
            {'Status': 'Paid', 'Amount': '200'},
        ]
        result = filter_non_refunded(donations)
        assert len(result) == 2
        assert all(d['Status'] == 'Paid' for d in result)
    
    def test_all_refunded(self):
        donations = [
            {'Status': 'Refunded', 'Amount': '100'},
            {'Status': 'Refunded', 'Amount': '200'},
        ]
        result = filter_non_refunded(donations)
        assert len(result) == 0
    
    def test_missing_status(self):
        donations = [
            {'Amount': '100'},  # No Status field
            {'Status': 'Paid', 'Amount': '200'},
        ]
        result = filter_non_refunded(donations)
        # Should include rows without Status field (treats as non-refunded)
        assert len(result) == 2


class TestAggregateDonationsByPatron:
    """Test donation aggregation by patron."""
    
    def test_group_by_patron_id(self):
        donations = [
            {'Patron ID': '123', 'Amount': '100'},
            {'Patron ID': '123', 'Amount': '200'},
            {'Patron ID': '456', 'Amount': '300'},
        ]
        result = aggregate_donations_by_patron(donations)
        assert '123' in result
        assert '456' in result
        assert len(result['123']) == 2
        assert len(result['456']) == 1
    
    def test_empty_list(self):
        result = aggregate_donations_by_patron([])
        assert result == {}
    
    def test_missing_patron_id(self):
        donations = [
            {'Patron ID': '', 'Amount': '100'},  # Empty ID
            {'Patron ID': '123', 'Amount': '200'},
        ]
        result = aggregate_donations_by_patron(donations)
        assert '123' in result
        assert len(result) == 1  # Empty ID skipped


class TestCalculateLifetimeDonationAmount:
    """Test lifetime donation calculation."""
    
    def test_single_donation(self):
        donations = [
            {'Donation Amount': '$100.00', 'Status': 'Paid'},
        ]
        assert calculate_lifetime_donation_amount(donations) == "$100.00"
    
    def test_multiple_donations(self):
        donations = [
            {'Donation Amount': '$100.00', 'Status': 'Paid'},
            {'Donation Amount': '$250.00', 'Status': 'Paid'},
            {'Donation Amount': '$50.00', 'Status': 'Paid'},
        ]
        assert calculate_lifetime_donation_amount(donations) == "$400.00"
    
    def test_excludes_refunded(self):
        donations = [
            {'Donation Amount': '$100.00', 'Status': 'Paid'},
            {'Donation Amount': '$50.00', 'Status': 'Refunded'},
            {'Donation Amount': '$250.00', 'Status': 'Paid'},
        ]
        assert calculate_lifetime_donation_amount(donations) == "$350.00"
    
    def test_all_refunded(self):
        donations = [
            {'Donation Amount': '$100.00', 'Status': 'Refunded'},
        ]
        assert calculate_lifetime_donation_amount(donations) == ""
    
    def test_no_donations(self):
        assert calculate_lifetime_donation_amount([]) == ""
    
    def test_handles_various_amount_formats(self):
        donations = [
            {'Donation Amount': "$3,000.00", 'Status': 'Paid'},
            {'Donation Amount': '$100.00', 'Status': 'Paid'},
            {'Donation Amount': '50.00', 'Status': 'Paid'},
        ]
        result = calculate_lifetime_donation_amount(donations)
        assert result == "$3150.00"


class TestGetMostRecentDonation:
    """Test most recent donation retrieval."""
    
    def test_single_donation(self):
        donations = [
            {'Donation Date': '2023-01-15', 'Donation Amount': '$100.00', 'Status': 'Paid'},
        ]
        date, amount = get_most_recent_donation(donations)
        assert date == '2023-01-15'
        assert amount == "$100.00"
    
    def test_multiple_donations_chronological(self):
        donations = [
            {'Donation Date': '2023-01-15', 'Donation Amount': '$100.00', 'Status': 'Paid'},
            {'Donation Date': '2023-06-20', 'Donation Amount': '$250.00', 'Status': 'Paid'},
            {'Donation Date': '2023-03-10', 'Donation Amount': '$50.00', 'Status': 'Paid'},
        ]
        date, amount = get_most_recent_donation(donations)
        assert date == '2023-06-20'
        assert amount == "$250.00"
    
    def test_excludes_refunded(self):
        donations = [
            {'Donation Date': '2023-01-15', 'Donation Amount': '$100.00', 'Status': 'Paid'},
            {'Donation Date': '2023-06-20', 'Donation Amount': '$250.00', 'Status': 'Refunded'},  # Most recent but refunded
            {'Donation Date': '2023-03-10', 'Donation Amount': '$50.00', 'Status': 'Paid'},
        ]
        date, amount = get_most_recent_donation(donations)
        assert date == '2023-03-10'
        assert amount == "$50.00"
    
    def test_all_refunded(self):
        donations = [
            {'Donation Date': '2023-01-15', 'Donation Amount': '$100.00', 'Status': 'Refunded'},
        ]
        date, amount = get_most_recent_donation(donations)
        assert date == ''
        assert amount == ""
    
    def test_no_donations(self):
        date, amount = get_most_recent_donation([])
        assert date == ''
        assert amount == ""


class TestGetFallbackCreatedDate:
    """Test fallback created date function."""
    
    def test_with_earliest_donation(self):
        donations_by_patron = {
            '12345': [
                {'Donation Date': '2023-03-10', 'Status': 'Paid'},
                {'Donation Date': '2023-01-15', 'Status': 'Paid'},  # Earliest
                {'Donation Date': '2023-06-20', 'Status': 'Paid'},
            ]
        }
        result = get_fallback_created_date('12345', donations_by_patron)
        # Should be the earliest donation date
        assert '2023-01-15' in result
        assert result.startswith('2023-01-15')
    
    def test_no_donations_uses_current_date(self):
        result = get_fallback_created_date('12345', {})
        # Should be current date in ISO format
        assert 'T' in result or len(result) > 10  # ISO format
    
    def test_excludes_refunded_from_earliest(self):
        donations_by_patron = {
            '12345': [
                {'Donation Date': '2023-01-15', 'Status': 'Refunded'},  # Earliest but refunded
                {'Donation Date': '2023-03-10', 'Status': 'Paid'},  # Should use this
            ]
        }
        result = get_fallback_created_date('12345', donations_by_patron)
        assert '2023-03-10' in result  # Earliest non-refunded donation date
