import pytest
from unittest.mock import patch, MagicMock
import json
import backend.tags as tags_module
from backend.tags import (
    fetch_tag_mapping,
    process_tags,
    count_tags_by_constituent,
)


class TestFetchTagMapping:
    """Test tag mapping API fetch function."""
    
    def setup_method(self):
        """Reset cache before each test."""
        tags_module._tag_mapping_cache = None
    
    @patch('backend.tags.urllib.request.urlopen')
    def test_successful_fetch(self, mock_urlopen):
        """Test successful API fetch."""
        # Reset cache
        tags_module._tag_mapping_cache = None
        
        # Mock API response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps([
            {'name': 'Top Donor', 'mapped_name': 'Major Donor', 'id': '1'},
            {'name': 'Camp 2016 ', 'mapped_name': 'Summer 2016', 'id': '2'},  # Note trailing space
        ]).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        result = fetch_tag_mapping()
        
        assert 'Top Donor' in result
        assert result['Top Donor'] == 'Major Donor'
        assert 'Camp 2016' in result
        assert result['Camp 2016'] == 'Summer 2016'
        assert 'Camp 2016 ' not in result
    
    @patch('backend.tags.urllib.request.urlopen')
    def test_api_failure(self, mock_urlopen):
        """Test API failure handling."""
        # Reset cache
        tags_module._tag_mapping_cache = None
        
        mock_urlopen.side_effect = Exception("API Error")
        
        result = fetch_tag_mapping()
        
        assert result == {}
        result2 = fetch_tag_mapping()  # Second call should use cache
        assert result2 == {}
    
    @patch('backend.tags.urllib.request.urlopen')
    def test_caching(self, mock_urlopen):
        """Test that API response is cached."""
        # Reset cache
        tags_module._tag_mapping_cache = None
        
        # Mock API response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps([
            {'name': 'Tag1', 'mapped_name': 'Mapped1', 'id': '1'},
        ]).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        # First call - should hit API
        result1 = fetch_tag_mapping()
        assert mock_urlopen.called
        assert result1['Tag1'] == 'Mapped1'
        
        # Reset mock call count
        mock_urlopen.reset_mock()
        
        # Second call - should use cache (API not called)
        result2 = fetch_tag_mapping()
        assert not mock_urlopen.called
        assert result2 == result1


class TestProcessTags:
    """Test tag processing function."""
    
    def test_empty_string(self):
        assert process_tags("") == ""
        assert process_tags("   ") == ""
        assert process_tags(None) == ""
    
    def test_single_tag(self):
        tag_mapping = {'Tag1': 'MappedTag1'}
        assert process_tags("Tag1", tag_mapping) == "MappedTag1"
    
    def test_multiple_tags(self):
        tag_mapping = {'Tag1': 'MappedTag1', 'Tag2': 'MappedTag2'}
        result = process_tags("Tag1, Tag2", tag_mapping)
        assert 'MappedTag1' in result
        assert 'MappedTag2' in result
    
    def test_deduplicates_tags(self):
        tag_mapping = {}
        result = process_tags("Tag1, Tag1, Tag2, Tag1", tag_mapping)
        assert result.count('Tag1') == 1
        assert 'Tag2' in result
    
    def test_whitespace_handling(self):
        tag_mapping = {}
        result = process_tags("  Tag1  ,  Tag2  ,  Tag3  ", tag_mapping)
        assert 'Tag1' in result
        assert 'Tag2' in result
        assert 'Tag3' in result
    
    def test_tags_not_in_mapping(self):
        tag_mapping = {'Tag1': 'MappedTag1'}
        result = process_tags("Tag1, Tag2", tag_mapping)
        assert 'MappedTag1' in result
        assert 'Tag2' in result  # Original kept
    
    def test_all_tags_mapped(self):
        tag_mapping = {
            'Top Donor': 'Major Donor',
            'Board Member': 'Board Member',
        }
        result = process_tags("Top Donor, Board Member", tag_mapping)
        assert 'Major Donor' in result
        assert 'Board Member' in result
    
    def test_multiple_tags_map_to_same(self):
        """Test when multiple original tags map to same mapped tag."""
        tag_mapping = {
            'Top Donor': 'Major Donor',
            'Major Donor 2021': 'Major Donor',
        }
        result = process_tags("Top Donor, Major Donor 2021", tag_mapping)
        assert result == "Major Donor"
    
    def test_trailing_spaces_in_api_mapping(self):
        """Test handling of trailing spaces in API mapping."""
        tag_mapping = {
            'Camp 2016 ': 'Summer 2016',  # API has trailing space
        }
        result = process_tags("Camp 2016", tag_mapping)  # Input doesn't have space
        assert result == "Camp 2016"
    
    def test_empty_tags_after_filtering(self):
        result = process_tags(", , ,", {})
        assert result == ""


class TestCountTagsByConstituent:
    """Test tag counting by constituent."""
    
    def test_single_constituent_single_tag(self):
        constituents = [
            {'Tags': 'Tag1'},
        ]
        tag_mapping = {}
        result = count_tags_by_constituent(constituents, tag_mapping)
        assert result['Tag1'] == 1
    
    def test_multiple_constituents_same_tag(self):
        constituents = [
            {'Tags': 'Tag1'},
            {'Tags': 'Tag1'},
            {'Tags': 'Tag2'},
        ]
        tag_mapping = {}
        result = count_tags_by_constituent(constituents, tag_mapping)
        assert result['Tag1'] == 2
        assert result['Tag2'] == 1
    
    def test_constituent_with_multiple_tags(self):
        constituents = [
            {'Tags': 'Tag1, Tag2, Tag3'},
        ]
        tag_mapping = {}
        result = count_tags_by_constituent(constituents, tag_mapping)
        assert result['Tag1'] == 1
        assert result['Tag2'] == 1
        assert result['Tag3'] == 1
    
    def test_constituent_counts_once_per_tag(self):
        """Constituent with duplicate tags should only count once per tag."""
        constituents = [
            {'Tags': 'Tag1, Tag1, Tag2'},  # Tag1 appears twice
        ]
        tag_mapping = {}
        result = count_tags_by_constituent(constituents, tag_mapping)
        assert result['Tag1'] == 1  # Counted once, not twice
        assert result['Tag2'] == 1
    
    def test_tag_mapping_applied(self):
        constituents = [
            {'Tags': 'Top Donor'},
            {'Tags': 'Major Donor 2021'},
        ]
        tag_mapping = {
            'Top Donor': 'Major Donor',
            'Major Donor 2021': 'Major Donor',
        }
        result = count_tags_by_constituent(constituents, tag_mapping)
        assert result['Major Donor'] == 2  # Both map to same tag
        assert 'Top Donor' not in result
        assert 'Major Donor 2021' not in result
    
    def test_empty_tags_ignored(self):
        constituents = [
            {'Tags': ''},
            {'Tags': 'Tag1'},
        ]
        tag_mapping = {}
        result = count_tags_by_constituent(constituents, tag_mapping)
        assert result['Tag1'] == 1
        assert len(result) == 1
    
    def test_no_tags(self):
        constituents = [
            {},
            {'Tags': ''},
        ]
        tag_mapping = {}
        result = count_tags_by_constituent(constituents, tag_mapping)
        assert result == {}
    
    def test_mixed_mapped_and_unmapped_tags(self):
        constituents = [
            {'Tags': 'Top Donor, UnmappedTag'},
        ]
        tag_mapping = {
            'Top Donor': 'Major Donor',
        }
        result = count_tags_by_constituent(constituents, tag_mapping)
        assert result['Major Donor'] == 1
        assert result['UnmappedTag'] == 1
