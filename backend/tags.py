import urllib.request
import json
import logging
from typing import Dict, List, Optional

from .config import TAG_API_URL, TAG_API_TIMEOUT

logger = logging.getLogger(__name__)

# Cache for tag mapping (fetched once per run)
_tag_mapping_cache: Optional[Dict[str, str]] = None


def fetch_tag_mapping() -> Dict[str, str]:
    """Fetch tag mapping from API and return a dictionary mapping original names to mapped names"""
    global _tag_mapping_cache
    
    # Return cached mapping if available
    if _tag_mapping_cache is not None:
        return _tag_mapping_cache
    
    try:
        logger.info(f"Fetching tag mapping from API: {TAG_API_URL}")
        
        with urllib.request.urlopen(TAG_API_URL, timeout=TAG_API_TIMEOUT) as response:
            data = json.loads(response.read())

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
    """Process a tags string: split, deduplicate, map via API, and return comma-separated string"""
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


def collect_all_tags(constituents: List[Dict[str, str]], tag_mapping: Optional[Dict[str, str]] = None) -> List[str]:
    """Collect all unique tags from all constituents (after mapping)"""
    if tag_mapping is None:
        tag_mapping = fetch_tag_mapping()
    
    all_tags_set = set()
    
    for constituent in constituents:
        tags_str = constituent.get('Tags', '').strip()
        if tags_str:
            processed_tags = process_tags(tags_str, tag_mapping)
            if processed_tags:
                tag_list = [t.strip() for t in processed_tags.split(',')]
                all_tags_set.update(tag_list)
    
    return sorted(all_tags_set)


def count_tags_by_constituent(constituents: List[Dict[str, str]], tag_mapping: Optional[Dict[str, str]] = None) -> Dict[str, int]:
    """Count how many constituents have each tag (after mapping)"""
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
