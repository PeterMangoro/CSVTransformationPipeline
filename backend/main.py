import logging
import sys
from collections import defaultdict
from pathlib import Path

from .config import (
    INPUT_CONSTITUENTS_FILE,
    INPUT_EMAILS_FILE,
    INPUT_DONATION_HISTORY_FILE,
    OUTPUT_CONSTITUENTS_FILE,
    OUTPUT_TAGS_FILE,
    CONSTITUENT_FIELDS,
    TAG_OUTPUT_FIELDS,
)
from .io_utils import read_csv, read_constituents_csv, write_csv
from .donations import aggregate_donations_by_patron
from .constituents import transform_all_constituents
from .tags import count_tags_by_constituent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)


def group_emails_by_patron(emails: list) -> dict:
    """Group email records by Patron ID"""
    emails_by_patron = defaultdict(list)
    
    for email_row in emails:
        patron_id = email_row.get('Patron ID', '').strip()
        if patron_id:
            emails_by_patron[patron_id].append(email_row)
    
    logger.info(f"Grouped emails for {len(emails_by_patron)} patrons")
    return emails_by_patron


def generate_tags_output(constituents: list) -> list:
    """Generate the tags output file with tag names and counts"""
    tag_counts = count_tags_by_constituent(constituents)
    
    output_rows = []
    for tag_name in sorted(tag_counts.keys()):
        output_rows.append({
            "CB Tag Name": tag_name,
            "CB Tag Count": str(tag_counts[tag_name]),
        })
    
    logger.info(f"Generated {len(output_rows)} tag entries")
    return output_rows


def main():
    """Main function to orchestrate the data transformation pipeline"""
    logger.info("Starting CueBox data import transformation pipeline")
    
    try:
        # Step 1: Load input files
        logger.info("Loading input files...")
        constituents = read_constituents_csv(INPUT_CONSTITUENTS_FILE)  # Uses normalized column names
        emails = read_csv(INPUT_EMAILS_FILE)
        donation_history = read_csv(INPUT_DONATION_HISTORY_FILE)
        
        logger.info(f"Loaded {len(constituents)} constituents, {len(emails)} email records, {len(donation_history)} donation records")
        
        # Step 2: Group data by Patron ID
        logger.info("Grouping data by Patron ID...")
        emails_by_patron = group_emails_by_patron(emails)
        donations_by_patron = aggregate_donations_by_patron(donation_history)
        
        # Step 3: Filter out orphaned donations (donations for Patron IDs not in constituents)
        valid_patron_ids = {row.get('Patron ID', '').strip() for row in constituents if row.get('Patron ID')}
        orphaned_patron_ids = set(donations_by_patron.keys()) - valid_patron_ids
        
        if orphaned_patron_ids:
            orphaned_count = sum(len(donations_by_patron[pid]) for pid in orphaned_patron_ids)
            logger.warning(f"Found {orphaned_count} donation(s) for {len(orphaned_patron_ids)} orphaned Patron ID(s): {sorted(orphaned_patron_ids)}")
            logger.warning("These donations will be excluded from output")
        
        # Step 4: Transform constituents
        logger.info("Transforming constituents...")
        output_constituents = transform_all_constituents(
            constituents,
            emails_by_patron,
            donations_by_patron,
        )
        
        # Step 5: Generate tags output
        logger.info("Generating tags output...")
        output_tags = generate_tags_output(constituents)
        
        # Step 6: Write output files
        logger.info("Writing output files...")
        write_csv(OUTPUT_CONSTITUENTS_FILE, CONSTITUENT_FIELDS, output_constituents)
        write_csv(OUTPUT_TAGS_FILE, TAG_OUTPUT_FIELDS, output_tags)
        
        logger.info("=" * 60)
        logger.info("Transformation completed successfully!")
        logger.info(f"Output files written:")
        logger.info(f"  - {OUTPUT_CONSTITUENTS_FILE} ({len(output_constituents)} rows)")
        logger.info(f"  - {OUTPUT_TAGS_FILE} ({len(output_tags)} rows)")
        logger.info("=" * 60)
        
    except FileNotFoundError as e:
        logger.error(f"Input file not found: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error during transformation: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
