import pytest
from backend.email_utils import standardize_email, is_valid_email, get_valid_emails, select_emails


class TestStandardizeEmail:
    """Test email standardization function."""
    
    def test_lowercase_and_trim(self):
        assert standardize_email('  JOHN.DOE@EXAMPLE.COM  ') == 'john.doe@example.com'
    
    def test_empty_string(self):
        assert standardize_email('') == ''
        assert standardize_email(None) == ''
    
    def test_domain_typo_gmaill(self):
        assert standardize_email('user@gmaill.com') == 'user@gmail.com'
    
    def test_domain_typo_hotmal(self):
        assert standardize_email('user@hotmal.com') == 'user@hotmail.com'
    
    def test_domain_typo_yaho(self):
        assert standardize_email('user@yaho.com') == 'user@yahoo.com'
    
    def test_domain_typo_gmal(self):
        assert standardize_email('user@gmal.com') == 'user@gmail.com'
    
    def test_domain_typo_outlok(self):
        assert standardize_email('user@outlok.com') == 'user@outlook.com'
    
    def test_no_typo_no_change(self):
        assert standardize_email('user@gmail.com') == 'user@gmail.com'
    
    def test_multiple_typos_in_same_email(self):
        # Should only fix the domain
        assert standardize_email('user@gmaill.com') == 'user@gmail.com'


class TestIsValidEmail:
    """Test email validation function."""
    
    def test_valid_email(self):
        assert is_valid_email('user@example.com') is True
        assert is_valid_email('user.name@example.co.uk') is True
    
    def test_invalid_email_no_at(self):
        assert is_valid_email('notanemail') is False
    
    def test_invalid_email_no_domain(self):
        assert is_valid_email('user@') is False
    
    def test_invalid_email_no_username(self):
        assert is_valid_email('@example.com') is False
    
    def test_empty_string(self):
        assert is_valid_email('') is False
        assert is_valid_email(None) is False
    
    def test_valid_after_standardization(self):
        standardized = standardize_email('user@gmaill.com')
        assert is_valid_email(standardized) is True


class TestGetValidEmails:
    """Test valid email filtering function."""
    
    def test_empty_list(self):
        assert get_valid_emails([]) == []
    
    def test_all_valid(self):
        emails = ['user1@example.com', 'user2@example.com']
        result = get_valid_emails(emails)
        assert len(result) == 2
        assert 'user1@example.com' in result
        assert 'user2@example.com' in result
    
    def test_filters_invalid(self):
        emails = ['valid@example.com', 'invalid', 'another@example.com']
        result = get_valid_emails(emails)
        assert len(result) == 2
        assert 'valid@example.com' in result
        assert 'another@example.com' in result
    
    def test_deduplicates(self):
        emails = ['user@example.com', 'user@example.com', 'user@example.com']
        result = get_valid_emails(emails)
        assert len(result) == 1
    
    def test_standardizes_and_validates(self):
        emails = ['USER@GMAILL.COM', 'valid@example.com']
        result = get_valid_emails(emails)
        assert len(result) == 2
        assert 'user@gmail.com' in result  # Standardized and corrected
        assert 'valid@example.com' in result
    
    def test_handles_empty_strings(self):
        emails = ['valid@example.com', '', None, 'another@example.com']
        result = get_valid_emails(emails)
        assert len(result) == 2


class TestSelectEmails:
    """Test email selection function."""
    
    def test_no_emails(self):
        email_1, email_2 = select_emails(None, [])
        assert email_1 == ''
        assert email_2 == ''
    
    def test_primary_email_valid(self):
        email_1, email_2 = select_emails('primary@example.com', ['secondary@example.com'])
        assert email_1 == 'primary@example.com'
        assert email_2 == 'secondary@example.com'
    
    def test_primary_email_invalid(self):
        email_1, email_2 = select_emails('invalid', ['valid@example.com'])
        assert email_1 == 'valid@example.com'
        assert email_2 == ''
    
    def test_no_primary_uses_first_valid(self):
        email_1, email_2 = select_emails(None, ['first@example.com', 'second@example.com'])
        assert email_1 == 'first@example.com'
        assert email_2 == 'second@example.com'
    
    def test_email_2_only_if_email_1_exists(self):
        email_1, email_2 = select_emails(None, [])
        assert email_1 == ''
        assert email_2 == ''
    
    def test_primary_in_list_uses_primary(self):
        email_1, email_2 = select_emails('primary@example.com', ['primary@example.com', 'secondary@example.com'])
        assert email_1 == 'primary@example.com'
        assert email_2 == 'secondary@example.com'
    
    def test_standardizes_domain_typos(self):
        email_1, email_2 = select_emails('user@gmaill.com', ['user2@example.com'])
        assert email_1 == 'user@gmail.com'  # Corrected
        assert email_2 == 'user2@example.com'
