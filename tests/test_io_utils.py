import pytest
import csv
from pathlib import Path
from backend.io_utils import read_csv, read_constituents_csv, write_csv


class TestReadCSV:
    """Test general CSV reading function."""
    
    def test_read_valid_csv(self, temp_csv_file):
        data = [
            {'Name': 'John', 'Age': '30'},
            {'Name': 'Jane', 'Age': '25'},
        ]
        file_path = temp_csv_file(data, ['Name', 'Age'])
        
        result = read_csv(file_path)
        
        assert len(result) == 2
        assert result[0]['Name'] == 'John'
        assert result[1]['Name'] == 'Jane'
    
    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            read_csv(Path("nonexistent_file.csv"))
    
    def test_empty_csv(self, temp_csv_file):
        file_path = temp_csv_file([], ['Name', 'Age'])
        result = read_csv(file_path)
        assert result == []


class TestReadConstituentsCSV:
    """Test constituents CSV reading with normalization."""
    
    def test_normalizes_title_column(self, temp_csv_file):
        """Test that 'Title' column is renamed to 'Job Title'."""
        data = [
            {
                'Patron ID': '123',
                'First Name': 'John',
                'Last Name': 'Doe',
                'Date Entered': '2020-01-01',
                'Primary Email': 'john@example.com',
                'Company': '',
                'Salutation': 'Mr',
                'Title': 'Engineer',  # Original column name
                'Tags': '',
                'Gender': 'Married',  # Original column name
            }
        ]
        file_path = temp_csv_file(data, [
            'Patron ID', 'First Name', 'Last Name', 'Date Entered',
            'Primary Email', 'Company', 'Salutation', 'Title', 'Tags', 'Gender'
        ])
        
        result = read_constituents_csv(file_path)
        
        assert len(result) == 1
        assert 'Job Title' in result[0]  # Normalized
        assert result[0]['Job Title'] == 'Engineer'
        assert 'Title' not in result[0]  # Old name removed
    
    def test_normalizes_gender_column(self, temp_csv_file):
        """Test that 'Gender' column is renamed to 'Marital Status'."""
        data = [
            {
                'Patron ID': '123',
                'First Name': 'John',
                'Last Name': 'Doe',
                'Date Entered': '2020-01-01',
                'Primary Email': 'john@example.com',
                'Company': '',
                'Salutation': 'Mr',
                'Title': '',
                'Tags': '',
                'Gender': 'Married',  # Original column name
            }
        ]
        file_path = temp_csv_file(data, [
            'Patron ID', 'First Name', 'Last Name', 'Date Entered',
            'Primary Email', 'Company', 'Salutation', 'Title', 'Tags', 'Gender'
        ])
        
        result = read_constituents_csv(file_path)
        
        assert len(result) == 1
        assert 'Marital Status' in result[0]  # Normalized
        assert result[0]['Marital Status'] == 'Married'
        assert 'Gender' not in result[0]  # Old name removed
    
    def test_preserves_other_columns(self, temp_csv_file):
        """Test that other columns are preserved correctly."""
        data = [
            {
                'Patron ID': '123',
                'First Name': 'John',
                'Last Name': 'Doe',
                'Date Entered': '2020-01-01',
                'Primary Email': 'john@example.com',
                'Company': 'Acme',
                'Salutation': 'Mr',
                'Title': 'Engineer',
                'Tags': 'Tag1, Tag2',
                'Gender': 'Married',
            }
        ]
        file_path = temp_csv_file(data, [
            'Patron ID', 'First Name', 'Last Name', 'Date Entered',
            'Primary Email', 'Company', 'Salutation', 'Title', 'Tags', 'Gender'
        ])
        
        result = read_constituents_csv(file_path)
        
        assert result[0]['Patron ID'] == '123'
        assert result[0]['First Name'] == 'John'
        assert result[0]['Last Name'] == 'Doe'
        assert result[0]['Company'] == 'Acme'
        assert result[0]['Salutation'] == 'Mr'
        assert result[0]['Tags'] == 'Tag1, Tag2'
    
    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            read_constituents_csv(Path("nonexistent_file.csv"))
    
    def test_handles_missing_columns(self, temp_csv_file):
        """Test that missing columns are handled gracefully."""
        data = [
            {
                'Patron ID': '123',
                'First Name': 'John',
                # Missing other columns
            }
        ]
        file_path = temp_csv_file(data, ['Patron ID', 'First Name'])
        
        result = read_constituents_csv(file_path)
        
        assert len(result) == 1
        assert result[0]['Patron ID'] == '123'
        assert result[0].get('Job Title', '') == ''  # Missing but normalized


class TestWriteCSV:
    """Test CSV writing function."""
    
    def test_write_valid_csv(self, tmp_path):
        file_path = tmp_path / "output.csv"
        fieldnames = ['Name', 'Age']
        rows = [
            {'Name': 'John', 'Age': '30'},
            {'Name': 'Jane', 'Age': '25'},
        ]
        
        write_csv(file_path, fieldnames, rows)
        
        assert file_path.exists()
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            result = list(reader)
            assert len(result) == 2
            assert result[0]['Name'] == 'John'
            assert result[1]['Name'] == 'Jane'
    
    def test_creates_output_directory(self, tmp_path):
        """Test that output directory is created if it doesn't exist."""
        output_dir = tmp_path / "subdir"
        file_path = output_dir / "output.csv"
        fieldnames = ['Name']
        rows = [{'Name': 'John'}]
        
        write_csv(file_path, fieldnames, rows)
        
        assert output_dir.exists()
        assert file_path.exists()
    
    def test_empty_rows(self, tmp_path):
        file_path = tmp_path / "output.csv"
        fieldnames = ['Name', 'Age']
        rows = []
        
        write_csv(file_path, fieldnames, rows)
        
        assert file_path.exists()
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            result = list(reader)
            assert result == []
            # Header should still be written
            f.seek(0)
            header = f.readline().strip()
            assert 'Name' in header
    
    def test_unicode_handling(self, tmp_path):
        """Test that Unicode characters are handled correctly."""
        file_path = tmp_path / "output.csv"
        fieldnames = ['Name']
        rows = [
            {'Name': 'José'},
            {'Name': 'François'},
        ]
        
        write_csv(file_path, fieldnames, rows)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            result = list(reader)
            assert result[0]['Name'] == 'José'
            assert result[1]['Name'] == 'François'
