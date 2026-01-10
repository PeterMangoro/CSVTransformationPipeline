import pytest
from datetime import datetime
from backend.constituents import (
    determine_constituent_type,
    standardize_name,
    parse_date_multiple_formats,
    map_title,
    format_background_information,
    transform_constituent,
)


class TestDetermineConstituentType:
    """Test constituent type determination."""
    
    def test_company_with_valid_company_name(self):
        row = {'Company': 'Acme Corp'}
        ctype, company_name = determine_constituent_type(row)
        assert ctype == "Company"
        assert company_name == 'Acme Corp'
    
    def test_person_with_empty_company(self):
        row = {'Company': ''}
        ctype, company_name = determine_constituent_type(row)
        assert ctype == "Person"
        assert company_name == ""
    
    def test_person_with_none_company(self):
        row = {'Company': 'None'}
        ctype, company_name = determine_constituent_type(row)
        assert ctype == "Person"
        assert company_name == ""
    
    def test_person_with_na_company(self):
        row = {'Company': 'N/A'}
        ctype, company_name = determine_constituent_type(row)
        assert ctype == "Person"
    
    def test_person_with_retired(self):
        row = {'Company': 'Retired'}
        ctype, company_name = determine_constituent_type(row)
        assert ctype == "Person"
    
    def test_person_with_used_to_work_here(self):
        row = {'Company': 'Used to work here.'}
        ctype, company_name = determine_constituent_type(row)
        assert ctype == "Person"
    
    def test_company_with_whitespace(self):
        row = {'Company': '  Acme Corp  '}
        ctype, company_name = determine_constituent_type(row)
        assert ctype == "Company"
        assert company_name == 'Acme Corp'  # Already stripped in determine_constituent_type


class TestStandardizeName:
    """Test name standardization."""
    
    def test_capitalize_first_lowercase_rest(self):
        assert standardize_name('JOHN') == 'John'
        assert standardize_name('john') == 'John'
        assert standardize_name('JOHN DOE') == 'John doe'
    
    def test_empty_string(self):
        assert standardize_name('') == ''
        assert standardize_name('   ') == ''
        assert standardize_name(None) == ''
    
    def test_compound_names_preserved(self):
        assert standardize_name('Katherine & Dan') == 'Katherine & dan'
        assert standardize_name('Robert & Emily') == 'Robert & emily'
        # Note: capitalize() only capitalizes first letter
    
    def test_already_capitalized(self):
        assert standardize_name('James') == 'James'
    
    def test_whitespace_stripped(self):
        assert standardize_name('  john  ') == 'John'


class TestParseDateMultipleFormats:
    """Test date parsing with multiple formats."""
    
    def test_format_jan_date(self):
        result = parse_date_multiple_formats("Jan 19, 2020")
        assert result is not None
        assert result.year == 2020
        assert result.month == 1
        assert result.day == 19
    
    def test_format_numeric_date(self):
        result = parse_date_multiple_formats("04/19/2022")
        assert result is not None
        assert result.year == 2022
        assert result.month == 4
        assert result.day == 19
    
    def test_format_with_time(self):
        result = parse_date_multiple_formats("12/07/2017 12:34")
        assert result is not None
        assert result.year == 2017
        assert result.month == 12
        assert result.day == 7
        assert result.hour == 12
        assert result.minute == 34
    
    def test_iso_format(self):
        result = parse_date_multiple_formats("2023-01-15")
        assert result is not None
        assert result.year == 2023
        assert result.month == 1
        assert result.day == 15
    
    def test_empty_string(self):
        assert parse_date_multiple_formats("") is None
        assert parse_date_multiple_formats("   ") is None
        assert parse_date_multiple_formats(None) is None
    
    def test_invalid_format(self):
        assert parse_date_multiple_formats("Invalid Date") is None
        assert parse_date_multiple_formats("32/13/2020") is None
    
    def test_strips_quotes(self):
        result = parse_date_multiple_formats('"Jan 19, 2020"')
        assert result is not None
        assert result.year == 2020


class TestMapTitle:
    """Test title mapping function."""
    
    def test_allowed_titles(self):
        assert map_title('Mr') == 'Mr.'
        assert map_title('Mrs') == 'Mrs.'
        assert map_title('Ms') == 'Ms.'
        assert map_title('Dr') == 'Dr.'
        assert map_title('mr') == 'Mr.'  # Case insensitive
        assert map_title('MRS') == 'Mrs.'
    
    def test_rev_maps_to_empty(self):
        assert map_title('Rev') == ''
        assert map_title('rev') == ''
    
    def test_mr_and_mrs_maps_to_empty(self):
        assert map_title('Mr. and Mrs.') == ''
        assert map_title('mr. and mrs.') == ''
    
    def test_empty_string(self):
        assert map_title('') == ''
        assert map_title(None) == ''
        assert map_title('   ') == ''
    
    def test_unknown_title(self):
        assert map_title('Unknown') == ''
        assert map_title('XYZ') == ''
    
    def test_with_period(self):
        # Periods are removed for lookup, so "Mr." -> "mr" -> "Mr."
        assert map_title('Mr.') == 'Mr.'
        assert map_title('Dr.') == 'Dr.'
        assert map_title('Mrs.') == 'Mrs.'
        assert map_title('Ms.') == 'Ms.'


class TestFormatBackgroundInformation:
    """Test background information formatting."""
    
    def test_both_present(self):
        result = format_background_information('Software Engineer', 'Married')
        assert result == 'Job Title: Software Engineer; Marital Status: Married'
    
    def test_only_job_title(self):
        result = format_background_information('Software Engineer', None)
        assert result == 'Job Title: Software Engineer'
    
    def test_only_marital_status(self):
        result = format_background_information(None, 'Married')
        assert result == 'Marital Status: Married'
    
    def test_neither_present(self):
        result = format_background_information(None, None)
        assert result == ''
        result = format_background_information('', '')
        assert result == ''
    
    def test_whitespace_stripped(self):
        result = format_background_information('  Engineer  ', '  Married  ')
        assert result == 'Job Title: Engineer; Marital Status: Married'
    
    def test_empty_strings(self):
        result = format_background_information('', 'Married')
        assert result == 'Marital Status: Married'
        result = format_background_information('Engineer', '')
        assert result == 'Job Title: Engineer'


class TestTransformConstituent:
    """Test full constituent transformation."""
    
    def test_person_type_transformation(self, sample_constituent_row):
        emails_by_patron = {
            '12345': [
                {'Email': 'john.doe@example.com'},
                {'Email': 'john.doe.work@company.com'},
            ]
        }
        donations_by_patron = {
            '12345': [
                {'Donation Amount': '$100.00', 'Donation Date': '2023-01-15', 'Status': 'Paid'},
            ]
        }
        tag_mapping = {'Top Donor': 'Major Donor'}
        
        result = transform_constituent(
            sample_constituent_row,
            emails_by_patron,
            donations_by_patron,
            tag_mapping
        )
        
        assert result['CB Constituent ID'] == '12345'
        assert result['CB Constituent Type'] == 'Person'
        assert result['CB First Name'] == 'John'  # Standardized
        assert result['CB Last Name'] == 'Doe'  # Standardized
        assert result['CB Company Name'] == ''
        assert result['CB Title'] == 'Mr.'
        assert 'Major Donor' in result['CB Tags']  # Mapped
        assert 'Job Title: Software Engineer' in result['CB Background Information']
        assert 'Marital Status: Married' in result['CB Background Information']
        assert result['CB Lifetime Donation Amount'] == '$100.00'
        assert result['CB Most Recent Donation Date'] == '2023-01-15'
    
    def test_company_type_transformation(self, sample_company_row):
        emails_by_patron = {'67890': [{'Email': 'info@company.com'}]}
        donations_by_patron = {}
        tag_mapping = {}
        
        result = transform_constituent(
            sample_company_row,
            emails_by_patron,
            donations_by_patron,
            tag_mapping
        )
        
        assert result['CB Constituent Type'] == 'Company'
        assert result['CB Company Name'] == 'Acme Corp'
        assert result['CB First Name'] == ''
        assert result['CB Last Name'] == ''
    
    def test_missing_date_uses_fallback(self, sample_constituent_row):
        """Test that missing Date Entered uses fallback."""
        emails_by_patron = {}
        donations_by_patron = {
            '12345': [
                {'Donation Date': '2023-01-15', 'Status': 'Paid'},
            ]
        }
        tag_mapping = {}
        
        sample_constituent_row['Date Entered'] = ''  # Missing date
        
        result = transform_constituent(
            sample_constituent_row,
            emails_by_patron,
            donations_by_patron,
            tag_mapping
        )
        
        # Should use fallback (earliest donation - 1 day)
        assert '2023-01-14' in result['CB Created At']
    
    def test_no_donations(self, sample_constituent_row):
        emails_by_patron = {}
        donations_by_patron = {}
        tag_mapping = {}
        
        result = transform_constituent(
            sample_constituent_row,
            emails_by_patron,
            donations_by_patron,
            tag_mapping
        )
        
        assert result['CB Lifetime Donation Amount'] == ''
        assert result['CB Most Recent Donation Date'] == ''
        assert result['CB Most Recent Donation Amount'] == ''
    
    def test_no_tags(self, sample_constituent_row):
        emails_by_patron = {}
        donations_by_patron = {}
        tag_mapping = {}
        
        sample_constituent_row['Tags'] = ''
        
        result = transform_constituent(
            sample_constituent_row,
            emails_by_patron,
            donations_by_patron,
            tag_mapping
        )
        
        assert result['CB Tags'] == ''
    
    def test_email_selection(self, sample_constituent_row):
        emails_by_patron = {
            '12345': [
                {'Email': 'secondary@example.com'},
                {'Email': 'tertiary@example.com'},
            ]
        }
        donations_by_patron = {}
        tag_mapping = {}
        
        sample_constituent_row['Primary Email'] = 'primary@example.com'
        
        result = transform_constituent(
            sample_constituent_row,
            emails_by_patron,
            donations_by_patron,
            tag_mapping
        )
        
        assert result['CB Email 1 (Standardized)'] == 'primary@example.com'
        assert result['CB Email 2 (Standardized)'] == 'secondary@example.com'
